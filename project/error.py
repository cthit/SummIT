from flask import render_template


def handle_upload_filesize_error(e):
    return render_template("error.html", error_code=413)

