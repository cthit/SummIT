from flask import render_template, current_app
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

_MESSAGES = {
    401: "You do not have permission to do that.",
    403: "You do not have permission to do that.",
    404: "The page or document you asked for does not exist.",
    500: "Something went wrong on our end. Please try again.",
}


def handle_http_exception(e: HTTPException):
    message = _MESSAGES.get(e.code, e.description)
    return render_template("error.html", error_code=e.code, message=message), e.code


def handle_file_too_large(e: RequestEntityTooLarge):
    max_mb = current_app.config["MAX_CONTENT_LENGTH"] // 1_000_000
    message = f"File is too large. Maximum size is {max_mb} MB."
    return render_template("error.html", error_code=413, message=message), 413


def handle_unexpected_error(e: Exception):
    if current_app.debug:
        raise e
    current_app.logger.exception("Unhandled exception")
    return render_template("error.html", error_code=500, message=_MESSAGES[500]), 500
