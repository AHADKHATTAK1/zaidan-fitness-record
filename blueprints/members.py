from flask import Blueprint, render_template, request, jsonify, session
from extensions import db
from models import Member, Payment, Setting, PaymentTransaction
from datetime import datetime
import os
from io import BytesIO
from flask import send_file
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as _pdf_canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.colors import HexColor
    HAVE_PDF = True
except ImportError:
    HAVE_PDF = False

members_bp = Blueprint('members', __name__)

def login_required(f):
    from functools import wraps
    from flask import redirect, url_for
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@members_bp.route('/members')
@login_required
def index():
    members = Member.query.all()
    # Fetch settings for context
    currency_code = Setting.query.filter_by(key='currency_code').first()
    currency_code = currency_code.value if currency_code else 'USD'
    
    monthly_price = Setting.query.filter_by(key='monthly_price').first()
    monthly_price = monthly_price.value if monthly_price else '8'
    
    gym_name = Setting.query.filter_by(key='gym_name').first()
    gym_name = gym_name.value if gym_name else 'Gym'
    
    return render_template('members.html', 
                           members=members, 
                           gym_name=gym_name, 
                           currency_code=currency_code, 
                           monthly_price=monthly_price)

@members_bp.route('/api/members', methods=['GET'])
@login_required
def list_members():
    q = request.args.get('search', '').lower().strip()
    status = request.args.get('status')
    active = request.args.get('active')
    training = request.args.get('training_type')
    
    query = Member.query
    
    if active is not None:
        is_active = active == '1'
        query = query.filter(Member.is_active == is_active)
        
    if training:
        query = query.filter(Member.training_type == training)
        
    members = query.all()
    
    # Filter in python for complex logic or search
    results = []
    for m in members:
        if q:
            if q not in m.name.lower() and q not in (m.phone or '') and q != str(m.id):
                continue
        
        # Status filter requires computing status
        m_dict = m.to_dict()
        if status and m_dict['current_fee_status'] != status:
            continue
            
        results.append(m_dict)
        
    return jsonify(results)

@members_bp.route('/api/members', methods=['POST'])
@login_required
def add_member():
    data = request.json
    try:
        m = Member(
            name=data['name'],
            phone=data.get('phone'),
            admission_date=datetime.strptime(data['admission_date'], '%Y-%m-%d').date(),
            training_type=data.get('training_type', 'standard'),
            monthly_fee=float(data.get('monthly_fee') or 0),
            special_tag=bool(data.get('special_tag')),
            is_active=True
        )
        db.session.add(m)
        db.session.commit()
        return jsonify(m.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@members_bp.route('/api/members/<int:id>', methods=['PUT'])
@login_required
def update_member(id):
    m = db.session.get(Member, id)
    if not m: return jsonify({'error': 'Not found'}), 404
    data = request.json
    
    if 'name' in data: m.name = data['name']
    if 'phone' in data: m.phone = data['phone']
    if 'admission_date' in data: 
        m.admission_date = datetime.strptime(data['admission_date'], '%Y-%m-%d').date()
    if 'monthly_price' in data: m.monthly_fee = float(data['monthly_price'] or 0)
    if 'training_type' in data: m.training_type = data['training_type']
    if 'special_tag' in data: m.special_tag = bool(data['special_tag'])
    
    db.session.commit()
    return jsonify({'ok': True})

@members_bp.route('/api/members/<int:id>', methods=['DELETE'])
@login_required
def delete_member(id):
    m = db.session.get(Member, id)
    if not m: return jsonify({'error': 'Not found'}), 404
    db.session.delete(m)
    db.session.commit()
    return jsonify({'ok': True})

@members_bp.route('/api/members/<int:id>/photo', methods=['POST'])
@login_required
def upload_member_photo(id):
    m = db.session.get(Member, id)
    if not m: return jsonify({'error': 'Not found'}), 404
    
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo'}), 400
        
    f = request.files['photo']
    if f.filename == '':
        return jsonify({'error': 'Empty file'}), 400
        
    # Save file
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
        return jsonify({'error': 'Invalid format'}), 400
        
    filename = f"member_{id}{ext}"
    path = os.path.join('static', 'uploads', filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f.save(path)
    
    return jsonify({'ok': True, 'url': f"/{path}"})

@members_bp.route('/api/member/<int:id>/payment-history', methods=['GET'])
@login_required
def get_payment_history(id):
    m = db.session.get(Member, id)
    if not m: return jsonify({'error': 'Not found'}), 404
    
    payments = Payment.query.filter_by(member_id=id).order_by(Payment.year.desc(), Payment.month.desc()).all()
    history = []
    
    for p in payments:
        paid_date = None
        amount = None
        if p.status == 'Paid':
            tx = PaymentTransaction.query.filter_by(member_id=id, year=p.year, month=p.month).first()
            if tx:
                paid_date = tx.created_at.strftime('%Y-%m-%d')
                amount = tx.amount
        
        history.append({
            'year': p.year,
            'month': p.month,
            'status': p.status,
            'paid_date': paid_date,
            'amount': amount
        })
        
    return jsonify({
        'member': m.to_dict(),
        'payments': history
    })

@members_bp.route('/api/members/<int:id>/card', methods=['GET'])
@login_required
def download_card(id):
    if not HAVE_PDF:
        return jsonify({'error': 'PDF support missing'}), 500
        
    m = db.session.get(Member, id)
    if not m: return jsonify({'error': 'Not found'}), 404
    
    buffer = BytesIO()
    c = _pdf_canvas.Canvas(buffer, pagesize=A4)
    
    # Draw Card
    c.setFillColor(HexColor('#1E1E1E'))
    c.rect(50, 600, 300, 180, fill=1)
    
    c.setFillColor(HexColor('#FFFFFF'))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(70, 750, "GYM MEMBERSHIP")
    
    c.setFont("Helvetica", 12)
    c.drawString(70, 720, f"Name: {m.name}")
    c.drawString(70, 700, f"ID: {m.id}")
    c.drawString(70, 680, f"Phone: {m.phone}")
    c.drawString(70, 660, f"Type: {m.training_type.title()}")
    
    c.save()
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f"card_{m.id}.pdf", mimetype='application/pdf')
