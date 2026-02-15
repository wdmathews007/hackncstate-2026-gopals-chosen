from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from iptcinfo3 import IPTCInfo
from datetime import datetime

class ImageMetadata:
    def __init__(self, image):
        self.image = image
        self.exif = {}
        self.iptc = {}

        # Basic info
        self.width, self.height = image.size
        self.format = image.format
        self.mode = image.mode

        # EXIF Info
        self.camera_type = None
        self.gps_latitude = None
        self.gps_longitude = None

        # IPTC Info
        self._caption = None
        self.keywords = []
        self.author = None
        self.date_created = None
        self.time_created = None

        self._extract_exif()
        self._extract_iptc()

    def _extract_exif(self):
        exif_data = self.image.getexif()
        if not exif_data:
            return
        
        gps_info = {}
        make = model = None

        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            self.exif[tag] = value
            # Camera info
            if tag == "Make":
                make = value
            elif tag == "Model":
                model = value
            # GPS info
            elif tag == "GPSInfo":
                for gps_id in value:
                    sub_tag = GPSTAGS.get(gps_id, gps_id)
                    gps_info[sub_tag] = value[gps_id]

        # Combined camera type
        self.camera_type = f"{make} {model}" if make and model else make or model

        # Convert GPS
        if gps_info:
            self.gps_latitude = self._convert_gps(
                gps_info.get("GPSLatitude"),
                gps_info.get("GPSLatitudeRef")
            )
            self.gps_longitude = self._convert_gps(
                gps_info.get("GPSLongitude"),
                gps_info.get("GPSLongitudeRef")
            )

    
    def _convert_gps(self, value, ref):
        if not value:
            return None

        def to_deg(x):
            return float(x[0]) / float(x[1])

        d = to_deg(value[0])
        m = to_deg(value[1])
        s = to_deg(value[2])

        decimal = d + (m / 60.0) + (s / 3600.0)

        if ref in ["S", "W"]:
            decimal = -decimal

        return decimal

    def _extract_iptc(self):
        try:
            if not hasattr(self.image, "filename") or not self.image.filename:
                return

            info = IPTCInfo(self.image.filename, force=True)

            for key in info._data:
                value = info[key]
                if value:
                    self.iptc[key] = value

            # Extract specific fields safely
            self._caption = self.iptc.get("caption/abstract")

            keywords = self.iptc.get("keywords", [])
            if isinstance(keywords, bytes):
                keywords = [keywords.decode()]
            elif isinstance(keywords, list):
                keywords = [
                    k.decode() if isinstance(k, bytes) else k
                    for k in keywords
                ]

            self.keywords = keywords
            self.author = self.iptc.get("by-line")
            self.date_created = self.iptc.get("date created")
            self.time_created = self.iptc.get("time created")

        except Exception as e:
            print(f"IPTC extraction failed: {e}")

    @property
    def caption(self):
        return self._caption

    @property
    def shutter_speed(self):
        val = self.exif.get("ExposureTime")
        if isinstance(val, tuple) and len(val) == 2:
            return val[0] / val[1]
        return val

    @property
    def aperture(self):
        val = self.exif.get("FNumber")
        if isinstance(val, tuple) and len(val) == 2:
            return val[0] / val[1]
        return val

    @property
    def iso(self):
        return self.exif.get("ISOSpeedRatings")

    @property
    def focal_length(self):
        val = self.exif.get("FocalLength")
        if isinstance(val, tuple) and len(val) == 2:
            return val[0] / val[1]
        return val

    @property
    def flash(self):
        return self.exif.get("Flash")

    @property
    def capture_time(self):
        dt = self.exif.get("DateTimeOriginal")
        if dt:
            try:
                return datetime.strptime(dt, "%Y:%m:%d %H:%M:%S")
            except:
                return dt
        return None