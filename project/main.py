from flask import Blueprint, render_template, session, redirect, url_for

main = Blueprint('main', __name__)


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/profile')
def profile():
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))
    return render_template('profile.html', user=user)
