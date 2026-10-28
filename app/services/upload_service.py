"""Secure image upload handling. Never trusts the filename or the browser MIME type."""
import os
import uuid
from flask import current_app
from PIL import Image, UnidentifiedImageError

EXT_BY_FORMAT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


class UploadError(Exception):
    pass


def save_image(file_storage):
    """Validate with Pillow, re-encode (strips EXIF/GPS + any hidden payload), and store
    under a random name. Returns the stored filename, or None if no file was given."""
    if file_storage is None or not getattr(file_storage, "filename", ""):
        return None
    max_bytes = current_app.config["MAX_UPLOAD_MB"] * 1024 * 1024
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size == 0:
        raise UploadError("The uploaded file is empty.")
    if size > max_bytes:
        raise UploadError(f"Image is too large (max {current_app.config['MAX_UPLOAD_MB']} MB).")
    try:
        probe = Image.open(file_storage.stream)
        fmt = probe.format
        probe.verify()  # checks the file is a real, uncorrupted image
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise UploadError("File is not a valid image.")
    if fmt not in current_app.config["ALLOWED_IMAGE_FORMATS"]:
        raise UploadError("Only JPEG, PNG and WebP images are allowed.")
    file_storage.stream.seek(0)
    img = Image.open(file_storage.stream)
    img.load()
    if img.width * img.height > 40_000_000:
        raise UploadError("Image dimensions are too large.")
    img.thumbnail((1920, 1920))
    if fmt == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    filename = f"{uuid.uuid4().hex}.{EXT_BY_FORMAT[fmt]}"
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    img.save(os.path.join(folder, filename), format=fmt)
    return filename


def delete_image(filename):
    if filename:
        try:
            os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(filename)))
        except OSError:
            pass
