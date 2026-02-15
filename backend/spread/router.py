import base64
import os
import re
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

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".tiff",
    ".svg",
}

LOW_SIGNAL_PATH_HINTS = {
    "/api/",
    "thumbnail",
    "thumb",
    "sprite",
    "logo",
    "icon",
    "visual-guidelines",
}

STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "into",
    "your",
    "about",
    "have",
    "has",
    "are",
    "was",
    "were",
    "will",
    "not",
}


class VisionAPIError(Exception):
    def __init__(self, message: str, *, status: str | None = None, code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


def _error_detail(message: str, *, code: str, **extra) -> dict:
    detail = {"code": code, "message": message}
    for key, value in extra.items():
        if value is not None:
            detail[key] = value
    return detail


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


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    tokens = set(re.findall(r"[a-z0-9]{3,}", text.lower()))
    return {token for token in tokens if token not in STOP_WORDS}


def _query_terms(web_detection: dict) -> set[str]:
    terms = set()

    for item in web_detection.get("bestGuessLabels") or []:
        terms.update(_tokenize(item.get("label")))

    for item in web_detection.get("webEntities") or []:
        score = float(item.get("score") or 0.0)
        if score < 0.5:
            continue
        terms.update(_tokenize(item.get("description")))

    return terms


def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _is_low_signal_url(url: str) -> bool:
    parsed = urlparse(url)
    path = (parsed.path or "").lower()

    if any(path.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return True
    return any(hint in path for hint in LOW_SIGNAL_PATH_HINTS)


def _root_domain(url: str | None) -> str | None:
    if not url:
        return None
    host = (urlparse(url).netloc or "").lower()
    if not host:
        return None
    if host.startswith("www."):
        host = host[4:]
    parts = [part for part in host.split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def _source_affinity_bonus(candidate_url: str, source_root: str | None) -> int:
    if not source_root:
        return 0
    candidate_root = _root_domain(candidate_url)
    if not candidate_root:
        return 0
    if candidate_root == source_root:
        return 16
    return -8


def _node_tokens(node: dict[str, object]) -> set[str]:
    label = node.get("label")
    label_text = label if isinstance(label, str) else None
    url_text = str(node.get("url") or "")
    return _tokenize(label_text) | _tokenize(url_text)


def _edge_affinity(parent: dict[str, object], child: dict[str, object]) -> int:
    parent_url = str(parent.get("url") or "")
    child_url = str(child.get("url") or "")

    affinity = 0
    parent_root = _root_domain(parent_url)
    child_root = _root_domain(child_url)
    if parent_root and child_root and parent_root == child_root:
        affinity += 26

    if parent.get("platform") == child.get("platform"):
        affinity += 8

    overlap = len(_node_tokens(parent) & _node_tokens(child))
    affinity += min(overlap, 8) * 5

    parent_score = _as_int(parent.get("evidence_score"))
    child_score = _as_int(child.get("evidence_score"))
    gap = max(0, parent_score - child_score)
    if gap <= 12:
        affinity += 8
    elif gap <= 24:
        affinity += 4

    return affinity


def _build_path_edges(nodes: list[dict[str, object]]) -> list[dict[str, object]]:
    if not nodes:
        return []

    sorted_nodes = sorted(nodes, key=lambda node: _as_int(node.get("evidence_score")), reverse=True)
    ordered = [dict(node) for node in sorted_nodes]

    edges: list[dict[str, object]] = []
    attached: list[dict[str, object]] = []

    for node in ordered:
        node_id = str(node.get("id"))
        best_parent_id = "src"
        best_affinity = 0

        for parent in attached:
            affinity = _edge_affinity(parent, node)
            if affinity > best_affinity:
                best_affinity = affinity
                best_parent_id = str(parent.get("id"))

        if best_affinity < 20:
            best_parent_id = "src"

        edges.append(
            {
                "from": best_parent_id,
                "to": node_id,
                "inferred": True,
                "affinity": best_affinity,
            }
        )
        attached.append(node)

    return edges


def _apply_domain_cap(matches: list[dict], max_per_domain: int) -> tuple[list[dict], int]:
    if max_per_domain < 1:
        return matches, 0

    kept = []
    dropped = 0
    counts: dict[str, int] = {}

    for match in matches:
        root = _root_domain(match.get("url")) or str(match.get("url") or "")
        seen = counts.get(root, 0)
        if seen >= max_per_domain:
            dropped += 1
            continue

        counts[root] = seen + 1
        kept.append(match)

    return kept, dropped


def _candidate_score(candidate: dict[str, object], terms: set[str]) -> int:
    match_type = str(candidate.get("match_type") or "")
    base = {
        "page_match": 120,
        "full_match": 90,
        "partial_match": 70,
        "similar_match": 45,
    }.get(match_type, 40)

    title = candidate.get("title")
    title_text = title if isinstance(title, str) else None
    url_text = str(candidate.get("url") or "")

    score = base
    score += min(_as_int(candidate.get("full_match_count")), 5) * 10
    score += min(_as_int(candidate.get("partial_match_count")), 5) * 5

    overlap = _tokenize(title_text) | _tokenize(url_text)
    overlap_count = len(overlap & terms)
    score += min(overlap_count, 6) * 12

    if overlap_count == 0:
        score -= 18

    if title_text:
        score += 4
    if _is_low_signal_url(url_text):
        score -= 18

    return score


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


def _extract_source_and_matches(web_detection: dict) -> tuple[str | None, list[dict], list[str]]:
    pages = web_detection.get("pagesWithMatchingImages") or []
    full_images = web_detection.get("fullMatchingImages") or []
    partial_images = web_detection.get("partialMatchingImages") or []
    similar_images = web_detection.get("visuallySimilarImages") or []
    terms = _query_terms(web_detection)

    def first_valid_url(items: list[dict]) -> str | None:
        for item in items:
            normalized = _canonicalize_url(item.get("url"))
            if normalized:
                return normalized
        return None

    page_candidates: list[dict] = []
    for page in pages:
        normalized = _canonicalize_url(page.get("url"))
        if not normalized:
            continue

        title = " ".join(str(page.get("pageTitle") or "").split())
        full_count = len(page.get("fullMatchingImages") or [])
        partial_count = len(page.get("partialMatchingImages") or [])

        candidate = {
            "url": normalized,
            "match_type": "page_match",
            "title": title[:160] if title else None,
            "full_match_count": full_count,
            "partial_match_count": partial_count,
        }
        page_candidates.append(candidate)

    other_candidates: list[dict] = []

    def add_other(items: list[dict], match_type: str):
        for item in items:
            normalized = _canonicalize_url(item.get("url"))
            if not normalized:
                continue
            other_candidates.append(
                {
                    "url": normalized,
                    "match_type": match_type,
                    "title": None,
                    "full_match_count": 0,
                    "partial_match_count": 0,
                }
            )

    add_other(full_images, "full_match")
    add_other(partial_images, "partial_match")
    add_other(similar_images, "similar_match")

    source_url = None
    if page_candidates:
        source_url = max(page_candidates, key=lambda c: _candidate_score(c, terms)).get("url")
    else:
        source_url = (
            first_valid_url(full_images)
            or first_valid_url(partial_images)
            or first_valid_url(similar_images)
        )

    seen = set()
    source_root = _root_domain(source_url)

    ranked: list[dict] = []
    for candidate in page_candidates + other_candidates:
        url = candidate["url"]
        if url == source_url or url in seen:
            continue
        seen.add(url)

        candidate["evidence_score"] = _candidate_score(candidate, terms) + _source_affinity_bonus(url, source_root)
        ranked.append(candidate)

    ranked.sort(
        key=lambda c: (
            int(c.get("evidence_score") or 0),
            int(c.get("full_match_count") or 0),
            int(c.get("partial_match_count") or 0),
            1 if c.get("title") else 0,
        ),
        reverse=True,
    )

    ranked_terms = sorted(terms)[:12]
    return source_url, ranked, ranked_terms


def _normalize_graph(
    web_detection: dict,
    max_nodes: int,
    *,
    strict_filter: bool,
    min_evidence_score: int,
    max_per_domain: int,
) -> dict:
    source_url, matches, query_terms = _extract_source_and_matches(web_detection)
    total_candidates = len(matches)

    if strict_filter:
        matches = [
            match
            for match in matches
            if _as_int(match.get("evidence_score")) >= min_evidence_score
        ]

    strict_filtered_out_count = total_candidates - len(matches)

    matches, domain_capped_out_count = _apply_domain_cap(matches, max_per_domain)
    filtered_out_count = strict_filtered_out_count + domain_capped_out_count
    matches = matches[:max_nodes]

    source = {
        "id": "src",
        "label": _label_from_url(source_url) if source_url else "uploaded image",
        "platform": _platform_from_url(source_url) if source_url else "upload",
        "date": None,
        "url": source_url,
    }

    nodes = []
    platforms = set()

    for idx, match in enumerate(matches, start=1):
        url = match["url"]
        node_id = f"n{idx}"
        platform = _platform_from_url(url)
        platforms.add(platform)
        nodes.append(
            {
                "id": node_id,
                "label": match.get("title") or _label_from_url(url),
                "platform": platform,
                "date": None,
                "url": url,
                "match_type": match.get("match_type"),
                "evidence_score": int(match.get("evidence_score") or 0),
                "full_match_count": int(match.get("full_match_count") or 0),
                "partial_match_count": int(match.get("partial_match_count") or 0),
            }
        )

    edges = _build_path_edges(nodes)

    return {
        "source": source,
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "total_matches": len(nodes),
            "platforms": sorted(platforms),
            "mode": "live",
            "source_url_found": source_url is not None,
            "query_terms": query_terms,
            "strict_filter": strict_filter,
            "min_evidence_score": min_evidence_score,
            "filtered_out_count": filtered_out_count,
            "strict_filtered_out_count": strict_filtered_out_count,
            "domain_capped_out_count": domain_capped_out_count,
            "max_per_domain": max_per_domain,
            "candidate_count": total_candidates,
            "edge_mode": "inferred_path",
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


def _http_detail_for_error(exc: VisionAPIError) -> dict:
    message = _sanitize_error_message(exc.message)
    if exc.status:
        pretty = f"Vision API error ({exc.status}): {message}"
    else:
        pretty = f"Vision API error: {message}"

    return _error_detail(
        pretty,
        code=_fallback_reason_for_error(exc),
        vision_status=exc.status,
        vision_code=exc.code,
    )


@router.post("/spread")
async def spread_from_image(
    file: UploadFile = File(...),
    max_nodes: int = Query(8, ge=1, le=20),
    strict_filter: bool = Query(True),
    min_evidence_score: int = Query(130, ge=0, le=400),
    max_per_domain: int = Query(2, ge=1, le=6),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=_error_detail("File must be an image", code="invalid_image_upload"),
        )

    image_bytes = await file.read()
    await file.close()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail=_error_detail("Uploaded file is empty", code="empty_upload"),
        )

    api_key = os.getenv("GOOGLE_CLOUD_VISION_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=_error_detail(
                "Google Vision API key is missing",
                code="missing_google_vision_key",
            ),
        )

    try:
        web_detection = _vision_web_detection(image_bytes, api_key)
        return _normalize_graph(
            web_detection,
            max_nodes,
            strict_filter=strict_filter,
            min_evidence_score=min_evidence_score,
            max_per_domain=max_per_domain,
        )
    except VisionAPIError as exc:
        raise HTTPException(status_code=502, detail=_http_detail_for_error(exc)) from exc
