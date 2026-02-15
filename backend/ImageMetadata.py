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
        self.iptc_date_created = None

        # Extract metadata
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
            if hasattr(self.image, 'filename') and self.image.filename:
                info = IPTCInfo(self.image.filename)
            else:
                return

            # Extract IPTC fields
            self._caption = info.get("caption/abstract")
            self.keywords = info.get("keywords") or []
            if isinstance(self.keywords, str):
                self.keywords = [self.keywords]
            self.author = info.get("byline")

            # IPTC date
            date_str = info.get("date created")
            time_str = info.get("time created")
            if date_str:
                try:
                    dt = datetime.strptime(date_str, "%Y%m%d")
                    if time_str:
                        dt = datetime.combine(dt.date(), datetime.strptime(time_str, "%H%M%S").time())
                    self.iptc_date_created = dt
                except:
                    self.iptc_date_created = None

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
    
    @property
    def software(self):
        val = self.exif.get("Software")
        if val:
            return str(val)  # ensure it’s a string
        return None
    
    @property
    def is_likely_edited(self):
        if self.gps_longitude is not None and self.gps_lattitude is not None:
            return "Likely Real"
        
        # Check software for editing or AI tools
        suspicious_software = ["photoshop", "lightroom", "midjourney", "dalle", "stable diffusion"]
        if self.software and any(word in self.software.lower() for word in suspicious_software):
            return "Likely Edited"

        # Check IPTC keywords
        if self.keywords:
            lower_keywords = [k.lower() for k in self.keywords if isinstance(k, str)]
            if any(word in lower_keywords for word in ["ai", "midjourney", "dalle", "photoshop"]):
                return "Likely Edited"

