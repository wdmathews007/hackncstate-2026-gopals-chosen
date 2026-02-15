import base64
import os
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, File, HTTPException, Query, UploadFile


router = APIRouter(tags=["spread"])

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "source",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


class VisionAPIError(Exception):
    def __init__(self, message: str, *, status: str | None = None, code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


def _sanitize_error_message(message: str | None) -> str:
    text = " ".join(str(message or "Vision API error").split())
    if len(text) > 260:
        return f"{text[:257]}..."
    return text


def _canonicalize_url(url: str | None) -> str | None:
    if not url:
        return None

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    if not parsed.netloc:
        return None

    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")

    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=False)
        if key.lower() not in TRACKING_QUERY_KEYS
    ]
    query = urlencode(filtered_query, doseq=True)

    return urlunparse((parsed.scheme, host, path, "", query, ""))


def _platform_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()

    if "reddit.com" in host:
        return "reddit"
    if "twitter.com" in host or "x.com" in host:
        return "twitter"
    if "facebook.com" in host:
        return "facebook"
    if "instagram.com" in host:
        return "instagram"
    if "tiktok.com" in host:
        return "tiktok"
    if "4chan.org" in host:
        return "4chan"
    if "imgur.com" in host:
        return "imgur"
    return "news"


def _label_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    path_segments = [segment for segment in parsed.path.split("/") if segment]

    if path_segments:
        return f"{host}/{path_segments[0]}"
    return host or "unknown source"


def _vision_web_detection(image_bytes: bytes, api_key: str) -> dict:
    endpoint = "https://vision.googleapis.com/v1/images:annotate"
    body = {
        "requests": [
            {
                "image": {"content": base64.b64encode(image_bytes).decode("ascii")},
                "features": [{"type": "WEB_DETECTION", "maxResults": 20}],
            }
        ]
    }

    try:
        response = requests.post(
            endpoint,
            params={"key": api_key},
            json=body,
            timeout=20,
        )
    except requests.RequestException as exc:
        raise VisionAPIError("Unable to reach Google Vision API", status="UNAVAILABLE") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise VisionAPIError("Google Vision API returned a non-JSON response") from exc

    if response.status_code >= 400:
        error_data = payload.get("error") if isinstance(payload, dict) else None
        message = _sanitize_error_message((error_data or {}).get("message"))
        status = (error_data or {}).get("status")
        code = (error_data or {}).get("code")
        raise VisionAPIError(message, status=status, code=code)

    responses = payload.get("responses") or []
    if not responses:
        raise VisionAPIError("Vision API returned no responses")

    response_payload = responses[0]
    if response_payload.get("error"):
        error_data = response_payload["error"]
        message = _sanitize_error_message(error_data.get("message"))
        raise VisionAPIError(
            message,
            status=error_data.get("status"),
            code=error_data.get("code"),
        )

    return response_payload.get("webDetection", {})


def _extract_source_and_urls(web_detection: dict) -> tuple[str | None, list[str]]:
    pages = web_detection.get("pagesWithMatchingImages") or []
    full_images = web_detection.get("fullMatchingImages") or []
    partial_images = web_detection.get("partialMatchingImages") or []
    similar_images = web_detection.get("visuallySimilarImages") or []

    def first_valid_url(items: list[dict]) -> str | None:
        for item in items:
            normalized = _canonicalize_url(item.get("url"))
            if normalized:
                return normalized
        return None

    source_url = (
        first_valid_url(pages)
        or first_valid_url(full_images)
        or first_valid_url(partial_images)
        or first_valid_url(similar_images)
    )

    seen = set()
    urls = []

    def add_url(candidate: str | None):
        normalized = _canonicalize_url(candidate)
        if not normalized:
            return
        if normalized == source_url or normalized in seen:
            return
        seen.add(normalized)
        urls.append(normalized)

    for page in pages:
        add_url(page.get("url"))

    for image_data in full_images:
        add_url(image_data.get("url"))

    for image_data in partial_images:
        add_url(image_data.get("url"))

    for image_data in similar_images:
        add_url(image_data.get("url"))

    return source_url, urls


def _normalize_graph(web_detection: dict, max_nodes: int) -> dict:
    source_url, urls = _extract_source_and_urls(web_detection)
    urls = urls[:max_nodes]

    source_date = date.today() - timedelta(days=len(urls) + 2)
    source = {
        "id": "src",
        "label": _label_from_url(source_url) if source_url else "unknown source",
        "platform": _platform_from_url(source_url) if source_url else "news",
        "date": source_date.isoformat(),
        "url": source_url,
    }

    nodes = []
    edges = []
    platforms = set()

    for idx, url in enumerate(urls, start=1):
        node_id = f"n{idx}"
        platform = _platform_from_url(url)
        platforms.add(platform)
        nodes.append(
            {
                "id": node_id,
                "label": _label_from_url(url),
                "platform": platform,
                "date": (source_date + timedelta(days=idx)).isoformat(),
                "url": url,
            }
        )

        if idx <= 2:
            edges.append({"from": "src", "to": node_id})
        else:
            edges.append({"from": f"n{idx - 1}", "to": node_id})

    return {
        "source": source,
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "total_matches": len(nodes),
            "platforms": sorted(platforms),
            "mode": "live",
        },
    }


def _fallback_reason_for_error(exc: VisionAPIError) -> str:
    status = (exc.status or "").upper()
    message = (exc.message or "").lower()

    if "bad image data" in message:
        return "vision_bad_image_data"
    if "billing" in message:
        return "vision_billing_required"
    if "disabled" in message or "not been used" in message:
        return "vision_api_disabled"

    if status == "PERMISSION_DENIED":
        return "vision_permission_denied"

    if status == "INVALID_ARGUMENT":
        return "vision_invalid_argument"

    if status == "UNAUTHENTICATED":
        return "vision_unauthenticated"
    if status == "RESOURCE_EXHAUSTED":
        return "vision_quota_exceeded"
    if status == "UNAVAILABLE":
        return "vision_unavailable"
    if status:
        return f"vision_{status.lower()}"
    return "vision_api_error"


def _http_detail_for_error(exc: VisionAPIError) -> str:
    message = _sanitize_error_message(exc.message)
    if exc.status:
        return f"Vision API error ({exc.status}): {message}"
    return f"Vision API error: {message}"


def _mock_graph(filename: str | None, max_nodes: int, reason: str) -> dict:
    seed_label = Path(filename).stem if filename else "uploaded-image"
    count = max(3, min(max_nodes, 6))

    source_date = date.today() - timedelta(days=count + 2)
    source = {
        "id": "src",
        "label": f"origin/{seed_label}",
        "platform": "4chan",
        "date": source_date.isoformat(),
        "url": None,
    }

    mock_platforms = ["reddit", "twitter", "facebook", "news", "instagram", "imgur"]
    nodes = []
    edges = []

    for idx in range(1, count + 1):
        platform = mock_platforms[(idx - 1) % len(mock_platforms)]
        node_id = f"n{idx}"
        nodes.append(
            {
                "id": node_id,
                "label": f"{platform}/post-{idx}",
                "platform": platform,
                "date": (source_date + timedelta(days=idx)).isoformat(),
                "url": f"https://example.com/{platform}/post-{idx}",
            }
        )

        if idx <= 2:
            edges.append({"from": "src", "to": node_id})
        else:
            edges.append({"from": f"n{idx - 1}", "to": node_id})

    platforms = sorted({node["platform"] for node in nodes})
    return {
        "source": source,
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "total_matches": len(nodes),
            "platforms": platforms,
            "mode": "fallback",
            "fallback": True,
            "reason": reason,
        },
    }


@router.post("/spread")
async def spread_from_image(
    file: UploadFile = File(...),
    max_nodes: int = Query(8, ge=1, le=20),
    use_mock_fallback: bool = Query(True),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()
    await file.close()

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    api_key = os.getenv("GOOGLE_CLOUD_VISION_KEY", "").strip()
    if not api_key:
        if use_mock_fallback:
            return _mock_graph(file.filename, max_nodes, "missing_google_vision_key")
        raise HTTPException(status_code=500, detail="Google Vision API key is missing")

    try:
        web_detection = _vision_web_detection(image_bytes, api_key)
        return _normalize_graph(web_detection, max_nodes)
    except VisionAPIError as exc:
        if use_mock_fallback:
            return _mock_graph(file.filename, max_nodes, _fallback_reason_for_error(exc))
        raise HTTPException(status_code=502, detail=_http_detail_for_error(exc)) from exc
