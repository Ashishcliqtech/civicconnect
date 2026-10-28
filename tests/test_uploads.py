import io
import os
import pytest
from werkzeug.datastructures import FileStorage
from app.models import Complaint
from app.services.upload_service import save_image, UploadError

FORM = {"title": "Photo complaint", "category": "Pothole", "address": "Some Road 12",
        "description": "Pothole with photo evidence attached here.", "latitude": "28.6", "longitude": "77.2"}


def _fs(data, name="x.png"):
    return FileStorage(stream=io.BytesIO(data), filename=name)


def test_valid_png_saved_with_random_name(app, png):
    name = save_image(_fs(png().read(), "../../evil name.png"))
    assert name.endswith(".png") and "evil" not in name and len(name) > 20
    assert os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], name))


def test_fake_image_rejected(app):
    with pytest.raises(UploadError):
        save_image(_fs(b"<?php echo 'hi'; ?>", "shell.png"))


def test_gif_rejected(app):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "GIF")
    with pytest.raises(UploadError):
        save_image(_fs(buf.getvalue(), "a.png"))


def test_oversize_rejected(app):
    app.config["MAX_UPLOAD_MB"] = 1
    with pytest.raises(UploadError):
        save_image(_fs(b"0" * (2 * 1024 * 1024)))


def test_no_file_returns_none(app):
    assert save_image(None) is None


def test_upload_through_form_and_extension_blocked(client, login, citizen, png):
    login(client, citizen)
    r = client.post("/citizen/submit", data=dict(FORM, photo=(png(), "p.png")), content_type="multipart/form-data")
    assert r.status_code == 302
    c = Complaint.query.one()
    assert c.photo_filename and c.photo_filename != "p.png"
    r = client.post("/citizen/submit", data=dict(FORM, photo=(io.BytesIO(b"MZ"), "virus.exe")), content_type="multipart/form-data")
    assert r.status_code == 200 and Complaint.query.count() == 1


def test_private_media_access_control(client, login, citizen, make_user, png):
    login(client, citizen)
    client.post("/citizen/submit", data=dict(FORM, photo=(png(), "p.png")), content_type="multipart/form-data")
    fname = Complaint.query.one().photo_filename
    assert client.get(f"/media/{fname}").status_code == 200  # owner
    client.post("/auth/logout")
    assert client.get(f"/media/{fname}").status_code == 302  # anonymous -> login
    stranger = make_user("citizen", email="s@test.local")
    login(client, stranger)
    assert client.get(f"/media/{fname}").status_code == 403
