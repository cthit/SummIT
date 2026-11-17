from io import BytesIO

from flask import Flask, request
from jinja2 import DictLoader
from werkzeug.exceptions import RequestEntityTooLarge

from project.error import handle_file_too_large
from project.i18n import t


def test_oversized_upload_returns_file_too_large_message():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16
    app.jinja_loader = DictLoader(
        {"error.html": "{{ error_code }}: {{ message }}"}
    )
    app.jinja_env.globals["t"] = t
    app.register_error_handler(
        RequestEntityTooLarge,
        handle_file_too_large,
    )

    @app.post("/upload")
    def upload():
        request.files
        return "ok"

    response = app.test_client().post(
        "/upload",
        data={"file": (BytesIO(b"0123456789"), "document.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 413
    assert b"File is too large" in response.data
