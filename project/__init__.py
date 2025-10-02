from flask import Flask
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
import os


def create_app():
    load_dotenv()
    GAMMA_ROOT = 'https://auth.chalmers.it'
    auth_uri = f'{GAMMA_ROOT}/oauth2/authorize'
    token_uri = f'{GAMMA_ROOT}/oauth2/token'
    user_info_uri = f'{GAMMA_ROOT}/oauth2/userinfo'
    redirect_uri = 'http://127.0.0.1:5000/api/auth/callbacks/gamma'
    client_id = os.getenv('GAMMA_CLIENT_ID', '')
    client_secret = os.getenv('GAMMA_CLIENT_SECRET', '')
 
    oauth = OAuth()
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('APP_SECRET_KEY', '')

    # Initialize OAuth with the Flask app
    oauth = OAuth(app)

    # Register Gamma OAuth client for OAuth2 (disable OpenID Connect)
    oauth.register(
        name='gamma',
        client_id=client_id,
        client_secret=client_secret,
        access_token_url=token_uri,
        authorize_url=auth_uri,
        api_base_url=GAMMA_ROOT,
        client_kwargs={
            'scope': 'openid profile email',  # Keep working scopes
        },
    )

    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
