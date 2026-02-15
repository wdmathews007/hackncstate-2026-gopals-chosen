from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

try:
    from ..ImageMetadata import ImageMetadata
    from ..analyze.inference import predict as classify_image
except ImportError:
    from ImageMetadata import ImageMetadata
    from analyze.inference import predict as classify_image


router = APIRouter(tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent / "pictures"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
LATEST_UPLOAD_BASENAME = "latest_upload"


def _safe_image_suffix(file_name: str | None, content_type: str | None) -> str:
    suffix = Path(file_name or "").suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".heic"}:
        return suffix

    content_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff",
        "image/heic": ".heic",
    }
    return content_map.get(content_type or "", ".img")


def _purge_previous_uploads() -> None:
    for candidate in UPLOAD_DIR.iterdir():
        if candidate.name == ".gitkeep":
            continue
        if candidate.is_file():
            candidate.unlink(missing_ok=True)


def _is_image_upload(upload: UploadFile) -> bool:
    return bool(upload.content_type and upload.content_type.startswith("image/"))


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not _is_image_upload(file):
        raise HTTPException(status_code=400, detail="File must be an image")

    stored_name = f"{LATEST_UPLOAD_BASENAME}{_safe_image_suffix(file.filename, file.content_type)}"
    saved_path = UPLOAD_DIR / stored_name
    temp_path = UPLOAD_DIR / f".{stored_name}.tmp"

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        _purge_previous_uploads()

        temp_path.write_bytes(content)
        temp_path.replace(saved_path)

        with Image.open(saved_path) as image:
            metadata = ImageMetadata(image).to_dict()
            classification = classify_image(image)

    except UnidentifiedImageError as exc:
        if saved_path.exists():
            saved_path.unlink(missing_ok=True)
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Invalid image file") from exc
    except HTTPException:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if saved_path.exists():
            saved_path.unlink(missing_ok=True)
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Failed to process uploaded image") from exc
    finally:
        await file.close()

    return {
        "filename": stored_name,
        "status": "uploaded",
        "file_path": str(saved_path),
        "analysis": {
            "label": classification["label"],
            "confidence": classification["confidence"],
            "classifier_subtype": classification.get("classifier_subtype"),
            "class_probs": classification.get("class_probs"),
            "metadata": metadata,
            "heatmap_url": None,
        },
    }
