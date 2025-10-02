from flask import (Blueprint, render_template, redirect, url_for, session,
                   request, jsonify, current_app)
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os

# Allow HTTP for local development (required for OAuth2Session)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

load_dotenv()

# Get redirect URI for OAuth callbacks
redirect_uri = 'http://127.0.0.1:5000/api/auth/callbacks/gamma'

auth = Blueprint('auth', __name__)


@auth.route('/login')
def login():
    return render_template('login.html')


@auth.route('/authorize')
def authorize():
    oauth = current_app.extensions['authlib.integrations.flask_client']
    gamma = oauth.gamma
    
    return gamma.authorize_redirect(redirect_uri)


@auth.route('/api/auth/callbacks/gamma')
def callback():
    oauth = current_app.extensions['authlib.integrations.flask_client']
    gamma = oauth.gamma
    
    # Get the access token from the callback
    token = gamma.authorize_access_token()
    
    # Try to get user info
    try:
        user_info_response = gamma.get('/oauth2/userinfo', token=token)
        user_info = user_info_response.json()
    except Exception as e:
        print(f"UserInfo API Exception: {e}")
        # Fallback to basic info from token
        user_info = {
            'message': 'UserInfo unavailable',
            'scopes': token.get('scope', 'N/A')
        }
    
    # Store user info in session
    session['user'] = user_info
    session['token'] = token
    
    return redirect(url_for('main.index'))


@auth.route('/logout')
def logout():
    session.clear()
    return render_template('logout.html')
