from flask import Blueprint, render_template, request, jsonify, session
from extensions import db
from models import Member, Payment, Setting, PaymentTransaction
from datetime import datetime
import os
import secrets
from io import BytesIO
from flask import send_file
import pandas as pd
from datetime import datetime, timezone
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

# --- AI Excel/CSV Upload Logic ---

def _smart_column_mapper(df_columns):
    """AI-powered automatic field mapping for Excel/CSV uploads"""
    column_map = {}
    
    # Enhanced column mapping patterns (case-insensitive, multi-language support)
    patterns = {
        'name': ['name', 'member name', 'full name', 'fullname', 'student name', 'customer', 'client', 
                 'naam', 'نام', 'member', 'first name', 'fname', 'last name', 'lname'],
        'phone': ['phone', 'mobile', 'contact', 'number', 'phone number', 'mobile number', 'whatsapp', 
                  'contact number', 'cell', 'telephone', 'tel', 'ph', 'رابطہ', 'موبائل'],
        'email': ['email', 'e-mail', 'mail', 'email address', 'ای میل', 'gmail', 'inbox'],
        'admission_date': ['admission', 'admission date', 'join date', 'joining date', 'date', 'start date', 
                          'reg date', 'registration date', 'registered', 'enrolled', 'enroll date', 
                          'داخلہ', 'تاریخ', 'admission_date', 'joining_date'],
        'plan_type': ['plan', 'plan type', 'subscription', 'package', 'membership', 'پلان', 
                      'plan_type', 'subscription_type'],
        'access_tier': ['access', 'tier', 'access tier', 'level', 'category', 'type', 
                        'رسائی', 'access_tier'],
        'training_type': ['training', 'training type', 'workout', 'workout type', 'exercise', 'gym type',
                         'تربیت', 'training_type', 'workout_type'],
        'special_tag': ['special', 'special tag', 'vip', 'star', 'premium', 'featured', 
                       'خاص', 'special_tag', 'vip_member'],
        'monthly_fee': ['fee', 'monthly fee', 'price', 'amount', 'monthly price', 'monthly_fee', 
                       'payment', 'cost', 'فیس', 'قیمت'],
        'cnic': ['cnic', 'id', 'national id', 'identity', 'id card', 'شناختی کارڈ'],
        'address': ['address', 'location', 'area', 'city', 'پتہ', 'مقام'],
        'gender': ['gender', 'sex', 'جنس', 'male/female'],
        'date_of_birth': ['dob', 'date of birth', 'birth date', 'birthday', 'پیدائش'],
        'referred_by': ['referred', 'referred by', 'referrer', 'reference', 'حوالہ'],
        'status': ['status', 'member status', 'active', 'is_active', 'active status', 'membership status', 
                   'حالت', 'صورتحال', 'account status'],
    }
    
    df_cols_lower = {col.lower().strip(): col for col in df_columns}
    
    # First pass: exact and partial matches
    for field, possible_names in patterns.items():
        for poss in possible_names:
            poss_lower = poss.lower()
            # Exact match
            if poss_lower in df_cols_lower:
                column_map[field] = df_cols_lower[poss_lower]
                break
            # Partial match (column contains pattern)
            for df_col_lower, original_col in df_cols_lower.items():
                if poss_lower in df_col_lower or df_col_lower in poss_lower:
                    if field not in column_map:  # Don't override exact matches
                        column_map[field] = original_col
                        break
    
    # Second pass: Fuzzy matching for close spellings
    import difflib
    for field, possible_names in patterns.items():
        if field not in column_map:
            for df_col_lower, original_col in df_cols_lower.items():
                for poss in possible_names:
                    # Check similarity ratio (>0.7 means close match)
                    if difflib.SequenceMatcher(None, poss.lower(), df_col_lower).ratio() > 0.7:
                        column_map[field] = original_col
                        break
                if field in column_map:
                    break
    
    return column_map

def _gen_referral_code():
    return secrets.token_hex(4).upper()

@members_bp.route('/api/members/upload', methods=['POST'])
@login_required
def upload_members_csv():
    # Helper to ensure payment rows
    def ensure_payment_rows_local(member_id, admission_date):
        adm_year = admission_date.year
        for mm in range(1, 12 + 1):
            p = Payment.query.filter_by(member_id=member_id, year=adm_year, month=mm).first()
            if not p:
                first_of_month = datetime(adm_year, mm, 1).date()
                status = "N/A" if first_of_month < admission_date else "Unpaid"
                db.session.add(Payment(member_id=member_id, year=adm_year, month=mm, status=status))

    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400
    f = request.files['file']
    fname_lower = f.filename.lower()
    
    # Support CSV, Excel (.xlsx, .xls), and .xltm
    if not fname_lower.endswith(('.csv', '.xlsx', '.xls', '.xltm')):
        return jsonify({"ok": False, "error": "Supported formats: CSV, Excel (.xlsx, .xls, .xltm)"}), 400
    
    try:
        if fname_lower.endswith('.csv'):
            df = pd.read_csv(f)
        else:
            # Excel formats
            df = pd.read_excel(f, engine='openpyxl' if fname_lower.endswith(('.xlsx', '.xltm')) else None)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to parse file: {str(e)}"}), 400
    
    # Automatic column mapping
    col_map = _smart_column_mapper(df.columns.tolist())
    
    created = 0
    updated = 0
    skipped = 0
    errors = []
    
    for idx, row in df.iterrows():
        try:
            # Extract data using smart mapping
            name = str(row.get(col_map.get('name')) or '').strip() if 'name' in col_map else ''
            phone = str(row.get(col_map.get('phone')) or '').strip() if 'phone' in col_map else ''
            admission = str(row.get(col_map.get('admission_date')) or '').strip() if 'admission_date' in col_map else ''
            
            # Simple fields
            email = str(row.get(col_map.get('email')) or '').strip() if 'email' in col_map else None
            training_type = str(row.get(col_map.get('training_type')) or 'standard').lower().strip() if 'training_type' in col_map else 'standard'
            plan_type = str(row.get(col_map.get('plan_type')) or 'monthly').lower().strip() if 'plan_type' in col_map else 'monthly'
            
            # Special Tag
            special_tag_raw = str(row.get(col_map.get('special_tag')) or '').strip().lower() if 'special_tag' in col_map else ''
            special_tag = special_tag_raw in ('1','true','yes','y', 'vip', '⭐')

            # Status
            status_raw = str(row.get(col_map.get('status')) or 'active').strip().lower() if 'status' in col_map else 'active'
            is_active = status_raw in ('1', 'true', 'yes', 'y', 'active', 'فعال', 'کا رہے ہیں')
            
            if not name:
                skipped += 1
                continue
            
            # Parse admission date
            admission_date = None
            if admission:
                for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                    try:
                        admission_date = datetime.strptime(admission, date_format).date()
                        break
                    except:
                        continue
                if not admission_date:
                    try:
                        admission_date = datetime.fromisoformat(admission).date()
                    except:
                        pass
            
            if not admission_date:
                admission_date = datetime.now(timezone.utc).date()
            
            # Check for duplicate by phone or name
            existing = None
            if phone:
                existing = Member.query.filter_by(phone=phone).first()
            if not existing and name:
                existing = Member.query.filter_by(name=name).first()

            if existing:
                # Update existing
                changed = False
                if email and existing.email != email:
                    existing.email = email
                    changed = True
                if existing.is_active != is_active:
                    existing.is_active = is_active
                    changed = True
                
                # Logic: Only update admission if earlier
                if admission_date < existing.admission_date:
                    existing.admission_date = admission_date
                    changed = True
                    
                if changed:
                    db.session.commit()
                    updated += 1
                else:
                    skipped += 1
                
                # Ensure payments
                ensure_payment_rows_local(existing.id, existing.admission_date)
                db.session.commit()
                continue

            # Create new member
            m = Member(
                name=name,
                phone=phone,
                email=email,
                training_type=training_type,
                special_tag=special_tag,
                admission_date=admission_date,
                is_active=is_active
            )
            # Add other fields if model supports them (plan_type, etc.)
            if hasattr(Member, 'plan_type'): m.plan_type = plan_type
            
            db.session.add(m)
            db.session.commit()

            # Create payment records
            ensure_payment_rows_local(m.id, m.admission_date)
            db.session.commit()
            created += 1
            
        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")
            skipped += 1
            continue
    
    # Enhanced AI detection response
    detection_quality = len(col_map) / 8.0  # approximate score
    response = {
        "ok": True,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "ai_detection": {
            "columns_detected": col_map,
            "detection_quality": round(min(detection_quality, 1.0) * 100, 1),
            "total_columns": len(df.columns),
            "mapped_columns": len(col_map),
            "unmapped_columns": [col for col in df.columns if col not in col_map.values()],
            "confidence": "high" if detection_quality >= 0.75 else "medium"
        }
    }
    if errors and len(errors) <= 5:
        response['errors'] = errors
    
    return jsonify(response)
