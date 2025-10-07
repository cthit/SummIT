from flask import Flask
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
from .auth import auth as auth_blueprint
from .main import main as main_blueprint
import os


def create_app():
    load_dotenv()
    gamma_root = os.getenv("GAMMA_ROOT", "https://auth.chalmers.it")
    client_id = os.getenv("GAMMA_CLIENT_ID", "")
    client_secret = os.getenv("GAMMA_CLIENT_SECRET", "")

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("APP_SECRET_KEY", "")

    # Initialize OAuth with the Flask app
    oauth = OAuth(app)

    # Register Gamma OAuth client with proper JWKS URI
    oauth.register(
        name="gamma",
        client_id=client_id,
        client_secret=client_secret,
        api_base_url=gamma_root,
        client_kwargs={
            "scope": "openid email profile",  # Required scopes for Gamma
        },
        server_metadata_url=f"{gamma_root}/.well-known/openid-configuration",
    )

    app.register_blueprint(auth_blueprint)

    app.register_blueprint(main_blueprint)

    return app
