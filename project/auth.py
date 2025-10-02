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
        print("=== USER INFO FROM GAMMA ===")
        print(f"User info: {user_info}")
    except Exception as e:
        print(f"UserInfo API Exception: {e}")
        # Fallback to basic info from token
        user_info = {
            'message': 'UserInfo unavailable',
            'scopes': token.get('scope', 'N/A')
        }
    
    # Add token scope info to user data for display
    if 'scope' not in user_info and token.get('scope'):
        user_info['scopes'] = token.get('scope')
    
    # Store only the most essential user info in session (reduce session size)
    essential_user_info = {
        'sub': user_info.get('sub'),
        'name': user_info.get('name'),
        'email': user_info.get('email'),
        'cid': user_info.get('cid')
    }
    
    # Store user info in session
    session['user'] = essential_user_info
    # Don't store the full token to save space
    session['authenticated'] = True
    
    print("=== SESSION DATA ===")
    print(f"User data stored in session: {essential_user_info}")
    print(f"Token scopes: {token.get('scope', 'N/A')}")
    print(f"Full user info: {user_info}")
    
    return redirect(url_for('main.profile'))


@auth.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('authenticated', None)
    return redirect(url_for('main.index'))
