from flask import Blueprint, request, jsonify, session
import os
import requests
import smtplib
from email.message import EmailMessage
from io import BytesIO
from datetime import datetime
from extensions import db
from models import Member, Payment, User, Setting

communications_bp = Blueprint('communications', __name__)

def get_setting(key, default=None):
    s = Setting.query.filter_by(key=key).first()
    return s.value if s else default

def get_gym_name():
    return get_setting('gym_name', 'Zaidan Fitness')

def login_required(f):
    from functools import wraps
    from flask import redirect, url_for
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    from flask import redirect, url_for
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        user_id = session.get('user_id')
        user = db.session.get(User, user_id)
        if not user or (user.role or 'staff') != 'admin':
             return jsonify({'ok': False, 'error': 'Admin required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- WhatsApp Logic ---

def _normalize_phone(phone: str) -> str:
    if not phone:
        return ''
    phone = phone.strip()
    if phone.startswith('+'):
        return phone
    # Prefer DB setting, fallback to env, default Pakistan '92'
    cc = (get_setting('whatsapp_default_country_code') or os.getenv('WHATSAPP_DEFAULT_COUNTRY_CODE') or '92')
    if cc and not phone.startswith(cc):
        if not cc.startswith('+'):
            cc = '+' + cc
        return cc + phone
    return phone

def send_whatsapp_message(to_phone: str, text: str) -> tuple[bool, str]:
    token = os.getenv('WHATSAPP_TOKEN')
    phone_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    if not token or not phone_id:
        return False, 'WhatsApp configuration missing (token/phone id)'
    url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'messaging_product': 'whatsapp',
        'to': to_phone,
        'type': 'text',
        'text': {'preview_url': False, 'body': text}
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
    except Exception as e:
        return False, f"request error: {e}"
    ok = 200 <= r.status_code < 300
    try:
        data = r.json()
    except Exception:
        data = {'text': r.text}
    return ok, (data if ok else f"{r.status_code}: {data}")

def send_whatsapp_template(to_phone: str, template_name: str, lang_code: str = 'en', body_params: list[str] | None = None) -> tuple[bool, str]:
    token = os.getenv('WHATSAPP_TOKEN')
    phone_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    if not token or not phone_id:
        return False, 'WhatsApp configuration missing (token/phone id)'
    url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    components = []
    if body_params:
        components = [{
            'type': 'body',
            'parameters': [{'type': 'text', 'text': str(v)} for v in body_params]
        }]
    payload = {
        'messaging_product': 'whatsapp',
        'to': to_phone,
        'type': 'template',
        'template': {
            'name': template_name,
            'language': {'code': lang_code},
            'components': components
        }
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
    except Exception as e:
        return False, f"request error: {e}"
    ok = 200 <= r.status_code < 300
    try:
        data = r.json()
    except Exception:
        data = {'text': r.text}
    return ok, (data if ok else f"{r.status_code}: {data}")

def send_bulk_text_reminders(year: int, month: int) -> dict:
    unpaid = Payment.query.filter_by(year=year, month=month, status='Unpaid').all()
    sent, failed = 0, 0
    price = (get_setting('monthly_price') or '8')
    currency = (get_setting('currency_code') or 'USD')
    gym = get_gym_name()
    for p in unpaid:
        member = db.session.get(Member, p.member_id)
        if not member:
            continue
        phone = _normalize_phone(member.phone or '')
        if not phone:
            failed += 1
            continue
        msg = f"Hi {member.name}, your {gym} fee ({price} {currency}) for {month}/{year} is pending. Please pay to stay active."
        ok, _ = send_whatsapp_message(phone, msg)
        if ok:
            sent += 1
        else:
            failed += 1
    return {"ok": True, "sent": sent, "failed": failed}

def send_bulk_template_reminders(year: int, month: int) -> dict:
    template_name = os.getenv('WHATSAPP_TEMPLATE_FEE_REMINDER_NAME')
    lang = os.getenv('WHATSAPP_TEMPLATE_LANG', 'en')
    if not template_name:
        return {"ok": False, "error": "WHATSAPP_TEMPLATE_FEE_REMINDER_NAME not set"}
    unpaid = Payment.query.filter_by(year=year, month=month, status='Unpaid').all()
    sent, failed = 0, 0
    for p in unpaid:
        m = db.session.get(Member, p.member_id)
        if not m:
            continue
        phone = _normalize_phone(m.phone or '')
        if not phone:
            failed += 1
            continue
        month_name = datetime(year, month, 1).strftime('%B')
        body_params = [m.name, month_name, str(year)]
        ok, _ = send_whatsapp_template(phone, template_name, lang, body_params)
        if ok:
            sent += 1
        else:
            failed += 1
    return {"ok": True, "sent": sent, "failed": failed}


# --- Email Logic ---

def send_email(subject: str, body: str, to_email: str, attachments: list[tuple[str, bytes]]|None=None) -> tuple[bool, str]:
    host = os.getenv('SMTP_HOST')
    port = int(os.getenv('SMTP_PORT', '587'))
    user = os.getenv('SMTP_USER')
    pwd = os.getenv('SMTP_PASSWORD')
    use_tls = os.getenv('SMTP_TLS', '1') not in ('0','false','False')
    if not (host and user and pwd and to_email):
        return False, 'SMTP config missing (host/user/password or recipient)'
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = to_email
    msg.set_content(body)
    if attachments:
        for filename, content in attachments:
            msg.add_attachment(content, maintype='application', subtype='octet-stream', filename=filename)
    try:
        if use_tls:
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.ehlo(); s.starttls(); s.ehlo(); s.login(user, pwd); s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.login(user, pwd); s.send_message(msg)
        return True, 'sent'
    except Exception as e:
        return False, str(e)

# --- Routes ---

@communications_bp.route('/api/fees/remind', methods=['POST'])
@login_required
def fees_remind():
    try:
        year = int(request.args.get('year') or datetime.now().year)
        month = int(request.args.get('month') or datetime.now().month)
    except ValueError:
        return jsonify({"ok": False, "error": "invalid year/month"}), 400
    # Determine which method to use from environment
    if os.getenv('WHATSAPP_TEMPLATE_FEE_REMINDER_NAME'):
         result = send_bulk_template_reminders(year, month)
    else:
         result = send_bulk_text_reminders(year, month)
    return jsonify(result)

@communications_bp.route('/api/fees/remind/template', methods=['POST'])
@login_required
def fees_remind_template():
    try:
        year = int(request.args.get('year') or datetime.now().year)
        month = int(request.args.get('month') or datetime.now().month)
    except ValueError:
        return jsonify({"ok": False, "error": "invalid year/month"}), 400
    result = send_bulk_template_reminders(year, month)
    status = 200 if result.get('ok') else 400
    return jsonify(result), status

@communications_bp.route('/admin/schedule/run-now', methods=['POST'])
@admin_required
def schedule_run_now():
    now = datetime.now()
    if os.getenv('WHATSAPP_TEMPLATE_FEE_REMINDER_NAME'):
         res = send_bulk_template_reminders(now.year, now.month)
    else:
         res = send_bulk_text_reminders(now.year, now.month)
    status = 200 if res.get('ok') else 400
    return jsonify(res), status
