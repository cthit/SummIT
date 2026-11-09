from flask import render_template, current_app
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from .i18n import t

_MESSAGE_KEYS = {
    401: "error.forbidden",
    403: "error.forbidden",
    404: "error.not_found",
    500: "error.server",
}


def handle_http_exception(e: HTTPException):
    key = _MESSAGE_KEYS.get(e.code)
    message = t(key) if key else e.description
    return render_template("error.html", error_code=e.code, message=message), e.code


def handle_file_too_large(e: RequestEntityTooLarge):
    max_mb = current_app.config["MAX_CONTENT_LENGTH"] // 1_000_000
    message = t("error.file_too_large", max_mb=max_mb)
    return render_template("error.html", error_code=413, message=message), 413


def handle_unexpected_error(e: Exception):
    if current_app.debug:
        raise e
    current_app.logger.exception("Unhandled exception")
    return (
        render_template("error.html", error_code=500, message=t("error.server")),
        500,
    )
