from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    current_app,
    g,
)
from authlib.integrations.flask_client import OAuth
from functools import wraps
from dotenv import load_dotenv
import os
import requests


# Allow HTTP for local development (required for OAuth2Session)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

load_dotenv()
gamma_root = os.getenv("GAMMA_ROOT", "https://auth.chalmers.it")
auth_header = os.getenv("AUTH_HEADER", "")
client_api_root = f"{gamma_root}/api/client/v1"
client_api_groups = f"{client_api_root}/groups"
client_api_groups_for = f"{client_api_groups}/for"


auth = Blueprint("auth", __name__)


def get_gamma():
    oauth: OAuth = current_app.extensions["authlib.integrations.flask_client"]
    return oauth.gamma


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("auth.login"))
        g.user = session.get("user")
        return f(*args, **kwargs)

    return decorated_function


@auth.route("/login")
def login():
    if session.get("authenticated"):
        return redirect(url_for("main.profile"))
    return render_template("login.html")


@auth.route("/authorize")
def authorize():
    gamma = get_gamma()
    return gamma.authorize_redirect(url_for("auth.callback", _external=True))


@auth.route("/api/auth/callbacks/gamma")
def callback():
    gamma = get_gamma()

    token = gamma.authorize_access_token()

    try:
        user_info_response = gamma.get("/oauth2/userinfo", token=token)
        user_info = user_info_response.json()
    except Exception as e:
        user_info = {
            "message": f"UserInfo unavailable: {e}",
            "scopes": token.get("scope", "N/A"),
        }

    if "scope" not in user_info and token.get("scope"):
        user_info["scopes"] = token.get("scope")

    try:
        id = user_info.get("sub")
        r = requests.Session()
        r.headers.update({"Authorization": auth_header})
        groups_response = r.get(F"{client_api_groups_for}/{id}").json()

        # Filter groups to only include committees
        active_groups = [
            {
                "name": group.get("prettyName", {}),
                "post": group.get("post", {}).get("enName"),
            }
            for group in groups_response
            if group.get("superGroup", {}).get("type") != "alumni"
        ]
    except Exception as e:
        print(f"Failed to get api information: {e}")
        active_groups = "No data."

    essential_user_info = {
        "name": user_info.get("name"),
        "email": user_info.get("email"),
        "cid": user_info.get("cid"),
        "groups": active_groups,
    }

    # Store user info in session
    session["user"] = essential_user_info
    # Don't store the full token to save space
    session["authenticated"] = True

    return redirect(url_for("main.profile"))


def clear_auth_session():
    """
    Clear authentication-related session data.

    `user` and `authenticated` keys are removed from the session.
    """
    session.pop("user", None)
    session.pop("authenticated", None)


@auth.route("/logout")
def logout():
    clear_auth_session()
    return redirect(url_for("main.index"))
