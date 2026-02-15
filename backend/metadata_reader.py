from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from ImageMetadata import ImageMetadata

# This is for testing
filepath = "images/432y4z4brb91m8d3jy5eyv039d.jpg"

image = Image.open(filepath)

# Pass filepath so IPTC works
metadata = ImageMetadata(image)

def show_metadata(meta):
    print("\n--- BASIC INFO ---")
    print("Format:", meta.format)
    print("Size:", meta.width, "x", meta.height)
    print("Mode:", meta.mode)

    print("\n--- CAMERA INFO ---")
    print("Camera:", meta.camera_type)
    print("ISO:", meta.iso)
    print("Aperture:", meta.aperture)
    print("Shutter Speed:", meta.shutter_speed)
    print("Focal Length:", meta.focal_length)
    print("Flash:", meta.flash)
    print("Capture Time:", meta.capture_time)

    print("\n--- GPS ---")
    print("Latitude:", meta.gps_latitude)
    print("Longitude:", meta.gps_longitude)

    print("\n--- IPTC ---")
    print("Caption:", meta.caption)
    print("Keywords:", meta.keywords)
    print("Author:", meta.author)

    print("\n--- RAW EXIF ---")
    for tag, value in meta.exif.items():
        print(tag, ":", value)

# This is what actually looks at the results
def check_metadata(meta):
    # This is because if an image has gps coordinates, it is likely to be real
    if meta.gps_longitude != None and meta.gps_lattitude != None:
        return "Likely Real"
    
    # If metadata has keywords like ai or photoshop, it is likely to be fake
    if meta.keywords:
        if any(name in [k.lower() for k in meta.keywords] for name in ["ai", "midjourney", "dalle", "photoshop"]):
            return "Likely Edited"
    
    else:
        return "Unknown"

show_metadata(metadata)
print(check_metadata(metadata))