from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db, oauth
from models import User, OAuthAccount, LoginLog
import os
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

def _log_login_event(user, method):
    try:
        entry = LoginLog(
            user_id=user.id if user else None,
            username=user.username if user else 'unknown',
            method=method,
            ip_address=request.remote_addr,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            _log_login_event(user, 'password')
            next_url = request.args.get('next') or url_for('dashboard')
            return redirect(next_url)
        flash('Invalid username or password', 'danger')
    
    # Google OAuth context
    gid = os.getenv('GOOGLE_CLIENT_ID')
    google_ready = bool(gid)
    return render_template('login_modern.html', gym_name="Zaidan Fitness", google_ready=google_ready, google_client_id=gid or '')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm') or ''
        
        if len(username) < 3:
            flash('Username too short', 'warning')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match', 'warning')
            return render_template('register.html')
            
        if User.query.filter_by(username=username).first():
            flash('Username taken', 'warning')
            return render_template('register.html')

        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        session['username'] = user.username
        return redirect(url_for('dashboard'))
    return render_template('register.html')
