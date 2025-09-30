from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
from urllib.parse import urlencode
import secrets
import requests
import os

client_id=os.getenv('GAMMA_CLIENT_ID', '')
client_secret=os.getenv('GAMMA_CLIENT_SECRET', '')
redirect_uri=os.getenv('GAMMA_REDIRECT_URI', 'http://localhost:5000/api/auth/callbacks/gamma')
auth_uri=os.getenv('GAMMA_AUTH_URL', 'https://auth.chalmers.it/oauth2/authorize')
token_uri=os.getenv('GAMMA_TOKEN_URL', 'https://auth.chalmers.it/oauth2/token')
user_info_uri=os.getenv('GAMMA_USER_INFO_URL', 'https://auth.chalmers.it/oauth2/userinfo')

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/authorize')
def authorize():
    # Generate and store state parameter for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth2_state'] = state
    
    qs = {
        'response_type': 'code',
        'client_id': client_id,
        'scope': 'openid', #profile
        'redirect_uri': redirect_uri,
        'state':state,
    }
    
    return redirect(f"{auth_uri}?{urlencode(qs)}")

@auth.route('/api/auth/callbacks/gamma')
def callback():
    args_dict = dict(request.args)
    print(args_dict)
    
    if 'code' not in args_dict:
        return "Error: Missing authorization code parameter", 400
    
    if 'state' not in args_dict:
        return "Error: Missing state parameter", 400
    
    received_state = args_dict['state']
    stored_state = session.get('oauth2_state')
    
    if not stored_state or received_state != stored_state:
        return "Error: Invalid state parameter", 400

    session.pop('oauth2_state', None)
    
    code = args_dict['code']
    return code

@auth.route('/logout')
def logout():
    return render_template('logout.html')