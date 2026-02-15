import logging
import re
from datetime import datetime

from iptcinfo3 import IPTCInfo
from PIL.ExifTags import GPSTAGS, TAGS


logger = logging.getLogger(__name__)

SUSPICIOUS_SOFTWARE = (
    "photoshop",
    "lightroom",
    "midjourney",
    "dalle",
    "stable diffusion",
    "stablediffusion",
)

SUSPICIOUS_KEYWORD_PHRASES = (
    "midjourney",
    "dalle",
    "photoshop",
    "stable diffusion",
    "stablediffusion",
    "ai generated",
)

AI_HINT_TERMS = (
    "midjourney",
    "dalle",
    "stable diffusion",
    "stablediffusion",
    "ai",
)


def _to_text(value):
    if value is None:
        return None

    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="ignore").strip()
        return text or None

    if isinstance(value, str):
        text = value.strip()
        return text or None

    try:
        text = str(value).strip()
    except Exception:
        return None

    return text or None


def _to_json_scalar(value):
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    text = _to_text(value)
    return text


def _to_float(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, (tuple, list)) and len(value) == 2:
        num = _to_float(value[0])
        den = _to_float(value[1])
        if num is None or den in (None, 0.0):
            return None
        return num / den

    numerator = getattr(value, "numerator", None)
    denominator = getattr(value, "denominator", None)
    if numerator is not None and denominator is not None:
        den = _to_float(denominator)
        num = _to_float(numerator)
        if den in (None, 0.0) or num is None:
            return None
        return num / den

    try:
        text = _to_text(value)
        if text is None:
            return None
        return float(text)
    except Exception:
        return None


def _normalize_keywords(raw_value):
    if raw_value is None:
        return []

    if isinstance(raw_value, (str, bytes)):
        values = [raw_value]
    elif isinstance(raw_value, (list, tuple, set)):
        values = list(raw_value)
    else:
        values = [raw_value]

    keywords = []
    for item in values:
        text = _to_text(item)
        if text:
            keywords.append(text)

    return keywords


def _contains_ai_token(keywords):
    tokens = set()
    for keyword in keywords:
        tokens.update(re.findall(r"[a-z0-9]+", keyword.lower()))
    return "ai" in tokens


class ImageMetadata:
    def __init__(self, image):
        self.image = image
        self.exif = {}
        self.iptc = {}

        self.width, self.height = image.size
        self.format = image.format
        self.mode = image.mode

        self.camera_type = None
        self.gps_latitude = None
        self.gps_longitude = None

        self._caption = None
        self.keywords = []
        self.author = None
        self.iptc_date_created = None

        self._extract_exif()
        self._extract_iptc()

    def _extract_exif(self):
        exif_data = self.image.getexif()
        if not exif_data:
            return

        gps_info = {}
        make = None
        model = None

        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            self.exif[tag] = value

            if tag == "Make":
                make = _to_text(value)
            elif tag == "Model":
                model = _to_text(value)
            elif tag == "GPSInfo" and isinstance(value, dict):
                for gps_id, gps_value in value.items():
                    sub_tag = GPSTAGS.get(gps_id, gps_id)
                    gps_info[sub_tag] = gps_value

        self.camera_type = f"{make} {model}" if make and model else (make or model)

        if gps_info:
            self.gps_latitude = self._convert_gps(
                gps_info.get("GPSLatitude"),
                gps_info.get("GPSLatitudeRef"),
            )
            self.gps_longitude = self._convert_gps(
                gps_info.get("GPSLongitude"),
                gps_info.get("GPSLongitudeRef"),
            )

    def _convert_gps(self, value, ref):
        if not value:
            return None

        if not isinstance(value, (tuple, list)) or len(value) < 3:
            return None

        d = _to_float(value[0])
        m = _to_float(value[1])
        s = _to_float(value[2])

        if d is None or m is None or s is None:
            return None

        decimal = d + (m / 60.0) + (s / 3600.0)
        ref_text = (_to_text(ref) or "").upper()

        if ref_text in {"S", "W"}:
            decimal = -decimal

        return round(decimal, 8)

    def _extract_iptc(self):
        filename = getattr(self.image, "filename", None)
        if not filename:
            return

        try:
            info = IPTCInfo(filename)
        except Exception as exc:
            logger.warning("IPTC extraction failed: %s", exc)
            return

        def iptc_get(field_name):
            try:
                value = info[field_name]
            except Exception:
                return None

            if value in (b"", "", None, []):
                return None
            return value

        self._caption = _to_text(iptc_get("caption/abstract"))
        self.keywords = _normalize_keywords(iptc_get("keywords"))
        self.author = _to_text(iptc_get("byline"))

        date_str = _to_text(iptc_get("date created"))
        time_str = _to_text(iptc_get("time created"))

        if not date_str:
            return

        try:
            dt = datetime.strptime(date_str, "%Y%m%d")

            if time_str:
                digits = "".join(ch for ch in time_str if ch.isdigit())
                if len(digits) >= 6:
                    tm = datetime.strptime(digits[:6], "%H%M%S").time()
                    dt = datetime.combine(dt.date(), tm)

            self.iptc_date_created = dt
        except Exception:
            self.iptc_date_created = None

    @property
    def caption(self):
        return self._caption

    @property
    def shutter_speed(self):
        value = self.exif.get("ExposureTime")
        parsed = _to_float(value)
        return parsed if parsed is not None else _to_json_scalar(value)

    @property
    def aperture(self):
        value = self.exif.get("FNumber")
        parsed = _to_float(value)
        return parsed if parsed is not None else _to_json_scalar(value)

    @property
    def iso(self):
        return _to_json_scalar(self.exif.get("ISOSpeedRatings"))

    @property
    def focal_length(self):
        value = self.exif.get("FocalLength")
        parsed = _to_float(value)
        return parsed if parsed is not None else _to_json_scalar(value)

    @property
    def flash(self):
        return _to_json_scalar(self.exif.get("Flash"))

    @property
    def capture_time(self):
        raw_value = _to_text(self.exif.get("DateTimeOriginal"))
        if not raw_value:
            return None

        try:
            return datetime.strptime(raw_value, "%Y:%m:%d %H:%M:%S")
        except Exception:
            return raw_value

    @property
    def software(self):
        return _to_text(self.exif.get("Software"))

    def _matched_suspicious_software(self):
        software_text = (self.software or "").lower()
        if not software_text:
            return None

        for term in SUSPICIOUS_SOFTWARE:
            if term in software_text:
                return term
        return None

    def _matched_keyword_signal(self):
        if not self.keywords:
            return None

        keyword_blob = " ".join(self.keywords).lower()
        for term in SUSPICIOUS_KEYWORD_PHRASES:
            if term in keyword_blob:
                return term

        if _contains_ai_token(self.keywords):
            return "ai"

        return None

    def metadata_signal_details(self):
        signals = []

        if self.gps_longitude is not None and self.gps_latitude is not None:
            signals.append("gps_coordinates")
            return {
                "classification": "Likely Real",
                "reason": "GPS coordinates are present in image metadata.",
                "signals": signals,
                "confidence": "high",
            }

        matched_software = self._matched_suspicious_software()
        if matched_software:
            signals.append("software_tag")
            if matched_software in AI_HINT_TERMS:
                signals.append("ai_tool_hint")
            return {
                "classification": "Likely Edited",
                "reason": f"Suspicious software tag detected: {matched_software}.",
                "signals": signals,
                "confidence": "high",
            }

        matched_keyword = self._matched_keyword_signal()
        if matched_keyword:
            signals.append("iptc_keyword")
            if matched_keyword in AI_HINT_TERMS:
                signals.append("ai_keyword_hint")
            return {
                "classification": "Likely Edited",
                "reason": f"Suspicious IPTC keyword detected: {matched_keyword}.",
                "signals": signals,
                "confidence": "medium",
            }

        if not self.exif and not self.keywords and not self.author and not self.caption:
            signals.append("no_strong_metadata")
            return {
                "classification": "Unknown",
                "reason": "No strong EXIF/IPTC signal found.",
                "signals": signals,
                "confidence": "low",
            }

        return {
            "classification": "Unknown",
            "reason": "Metadata is present but not strongly indicative.",
            "signals": signals,
            "confidence": "low",
        }

    @property
    def is_likely_edited(self):
        return self.metadata_signal_details()["classification"]

    def to_dict(self):
        capture_time = self.capture_time
        signal_details = self.metadata_signal_details()

        return {
            "camera_type": self.camera_type,
            "capture_time": str(capture_time) if capture_time else None,
            "gps_latitude": self.gps_latitude,
            "gps_longitude": self.gps_longitude,
            "shutter_speed": self.shutter_speed,
            "aperture": self.aperture,
            "iso": self.iso,
            "focal_length": self.focal_length,
            "flash": self.flash,
            "caption": self.caption,
            "keywords": self.keywords,
            "author": self.author,
            "software": self.software,
            "iptc_date_created": str(self.iptc_date_created) if self.iptc_date_created else None,
            "likely_edited": signal_details["classification"],
            "metadata_reason": signal_details["reason"],
            "metadata_signals": signal_details["signals"],
            "metadata_confidence": signal_details["confidence"],
        }
