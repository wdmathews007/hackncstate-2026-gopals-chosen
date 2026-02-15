import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ImageMetadata import ImageMetadata  # noqa: E402


class FakeImage:
    def __init__(self, *, exif=None, filename=None, size=(64, 64), fmt="JPEG", mode="RGB"):
        self._exif = exif or {}
        self.filename = filename
        self.size = size
        self.format = fmt
        self.mode = mode

    def getexif(self):
        return self._exif


class FakeIPTCInfo:
    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data.get(key)


class ImageMetadataTests(unittest.TestCase):
    def test_no_metadata_returns_unknown_and_json_safe(self):
        image = FakeImage(exif={}, filename=None)

        meta = ImageMetadata(image)
        payload = meta.to_dict()

        self.assertEqual(payload["likely_edited"], "Unknown")
        self.assertIsNone(payload["gps_latitude"])
        self.assertIsNone(payload["gps_longitude"])
        self.assertEqual(payload["keywords"], [])

        json.dumps(payload)

    def test_gps_present_returns_likely_real(self):
        exif = {
            34853: {
                1: "N",
                2: ((35, 1), (30, 1), (0, 1)),
                3: "W",
                4: ((78, 1), (40, 1), (0, 1)),
            }
        }
        image = FakeImage(exif=exif)

        meta = ImageMetadata(image)
        payload = meta.to_dict()

        self.assertEqual(payload["likely_edited"], "Likely Real")
        self.assertAlmostEqual(payload["gps_latitude"], 35.5, places=6)
        self.assertAlmostEqual(payload["gps_longitude"], -78.66666667, places=6)

    def test_suspicious_software_bytes_returns_likely_edited(self):
        exif = {
            305: b"Adobe Photoshop 2024",
        }
        image = FakeImage(exif=exif)

        meta = ImageMetadata(image)
        payload = meta.to_dict()

        self.assertEqual(payload["software"], "Adobe Photoshop 2024")
        self.assertEqual(payload["likely_edited"], "Likely Edited")

    def test_iptc_keyword_bytes_returns_likely_edited(self):
        image = FakeImage(exif={}, filename="/tmp/iptc.jpg")
        iptc_payload = {
            "keywords": [b"AI", b"news"],
            "caption/abstract": b"caption",
            "byline": b"author",
        }

        with patch("ImageMetadata.IPTCInfo", return_value=FakeIPTCInfo(iptc_payload)):
            meta = ImageMetadata(image)

        payload = meta.to_dict()
        self.assertEqual(payload["keywords"], ["AI", "news"])
        self.assertEqual(payload["caption"], "caption")
        self.assertEqual(payload["author"], "author")
        self.assertEqual(payload["likely_edited"], "Likely Edited")

    def test_gps_precedence_over_software_and_keywords(self):
        exif = {
            305: b"Lightroom",
            34853: {
                1: b"N",
                2: ((35, 1), (0, 1), (0, 1)),
                3: b"E",
                4: ((140, 1), (0, 1), (0, 1)),
            },
        }
        image = FakeImage(exif=exif, filename="/tmp/iptc.jpg")
        iptc_payload = {"keywords": [b"AI"]}

        with patch("ImageMetadata.IPTCInfo", return_value=FakeIPTCInfo(iptc_payload)):
            meta = ImageMetadata(image)

        self.assertEqual(meta.to_dict()["likely_edited"], "Likely Real")


if __name__ == "__main__":
    unittest.main()
