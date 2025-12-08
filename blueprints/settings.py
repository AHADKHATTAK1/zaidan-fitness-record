from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from extensions import db
from models import Setting

settings_bp = Blueprint('settings', __name__)

def get_setting(key, default=''):
    s = Setting.query.filter_by(key=key).first()
    return s.value if s else default

def set_setting(key, value):
    s = Setting.query.filter_by(key=key).first()
    if not s:
        s = Setting(key=key, value=value)
        db.session.add(s)
    else:
        s.value = value
    db.session.commit()

@settings_bp.route('/settings', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        gym_name = request.form.get('gym_name')
        currency_code = request.form.get('currency_code')
        monthly_price = request.form.get('monthly_price')
        
        if gym_name: set_setting('gym_name', gym_name)
        if currency_code: set_setting('currency_code', currency_code)
        if monthly_price: set_setting('monthly_price', monthly_price)
        
        flash('Settings updated', 'success')
        return redirect(url_for('settings.index'))
        
    settings = {
        'gym_name': get_setting('gym_name', 'Zaidan Fitness'),
        'currency_code': get_setting('currency_code', 'USD'),
        'monthly_price': get_setting('monthly_price', '8'),
    }
    return render_template('settings.html', settings=settings)
