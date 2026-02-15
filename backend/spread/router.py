import base64
import os
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, File, HTTPException, Query, UploadFile


router = APIRouter(tags=["spread"])

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)


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

    response = requests.post(
        endpoint,
        params={"key": api_key},
        json=body,
        timeout=20,
    )
    response.raise_for_status()

    payload = response.json()
    responses = payload.get("responses") or []
    if not responses:
        raise ValueError("Vision API returned no responses")

    response_payload = responses[0]
    if response_payload.get("error"):
        message = response_payload["error"].get("message", "Vision API error")
        raise ValueError(message)

    return response_payload.get("webDetection", {})


def _extract_source_and_urls(web_detection: dict) -> tuple[str | None, list[str]]:
    pages = web_detection.get("pagesWithMatchingImages") or []
    full_images = web_detection.get("fullMatchingImages") or []
    partial_images = web_detection.get("partialMatchingImages") or []
    similar_images = web_detection.get("visuallySimilarImages") or []

    source_url = None
    if pages and pages[0].get("url"):
        source_url = pages[0]["url"]
    elif full_images and full_images[0].get("url"):
        source_url = full_images[0]["url"]

    seen = set()
    urls = []

    def add_url(candidate: str | None):
        if not candidate or not candidate.startswith("http"):
            return
        if candidate in seen:
            return
        seen.add(candidate)
        urls.append(candidate)

    for page in pages:
        add_url(page.get("url"))

    for image_data in full_images + partial_images + similar_images:
        add_url(image_data.get("url"))

    if source_url:
        urls = [url for url in urls if url != source_url]

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
        },
    }


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
        graph = _normalize_graph(web_detection, max_nodes)

        if graph["summary"]["total_matches"] == 0 and use_mock_fallback:
            return _mock_graph(file.filename, max_nodes, "vision_no_matches")

        return graph
    except requests.RequestException as exc:
        if use_mock_fallback:
            return _mock_graph(file.filename, max_nodes, f"vision_http_error:{type(exc).__name__}")
        raise HTTPException(status_code=502, detail="Vision API request failed") from exc
    except ValueError as exc:
        if use_mock_fallback:
            return _mock_graph(file.filename, max_nodes, f"vision_parse_error:{type(exc).__name__}")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
