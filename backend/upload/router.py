from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

try:
    from ..ImageMetadata import ImageMetadata
except ImportError:
    from ImageMetadata import ImageMetadata


router = APIRouter(tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent / "pictures"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _is_image_upload(upload: UploadFile) -> bool:
    return bool(upload.content_type and upload.content_type.startswith("image/"))


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not _is_image_upload(file):
        raise HTTPException(status_code=400, detail="File must be an image")

    original_name = Path(file.filename or "upload").name
    stored_name = f"{uuid4().hex}_{original_name}"
    saved_path = UPLOAD_DIR / stored_name

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        saved_path.write_bytes(content)

        with Image.open(saved_path) as image:
            metadata = ImageMetadata(image).to_dict()

    except UnidentifiedImageError as exc:
        if saved_path.exists():
            saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Invalid image file") from exc
    finally:
        await file.close()

    return {
        "filename": stored_name,
        "status": "uploaded",
        "file_path": str(saved_path),
        "analysis": {
            "label": "unknown",
            "confidence": 0.0,
            "metadata": metadata,
            "heatmap_url": None,
        },
    }
