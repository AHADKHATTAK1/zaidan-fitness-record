from flask import Blueprint, render_template, request, jsonify, session, url_for
from extensions import db
from models import Member, Payment, PaymentTransaction, Setting
from datetime import datetime
from sqlalchemy import func

fees_bp = Blueprint('fees', __name__)

def login_required(f):
    from functools import wraps
    from flask import redirect, url_for
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_setting(key, default=None):
    s = Setting.query.filter_by(key=key).first()
    return s.value if s else default

def get_gym_name():
    return get_setting('gym_name', 'Zaidan Fitness')

def ensure_payment_rows(member, year):
    # Ensure 12 months exist for this year
    for m in range(1, 13):
        p = Payment.query.filter_by(member_id=member.id, year=year, month=m).first()
        if not p:
            # If admission date is in future of this month, N/A, else Unpaid
            status = 'Unpaid'
            if member.admission_date:
                first_of_month = datetime(year, m, 1).date()
                if first_of_month < member.admission_date:
                    status = 'N/A'
            
            db.session.add(Payment(member_id=member.id, year=year, month=m, status=status))
    db.session.commit()

# --- Helpers for Receipt ---
def _render_receipt_context(tx: PaymentTransaction):
    member = db.session.get(Member, tx.member_id)
    gym_name = get_gym_name()
    currency = get_setting('currency_code') or 'PKR'
    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    month_name = month_names[(tx.month or 1) - 1] if tx.month else '-'
    return {
        'gym_name': gym_name,
        'currency': currency,
        'tx': tx,
        'member': member,
        'month_name': month_name,
    }

# --- Routes ---

@fees_bp.route('/fees')
@login_required
def fees_page():
    currency_code = get_setting('currency_code') or 'USD'
    monthly_price = get_setting('monthly_price') or '8'
    return render_template(
        'fees.html', # Assuming fees.html exists or will be created
        gym_name=get_gym_name(),
        currency_code=currency_code,
        monthly_price=monthly_price,
    )

@fees_bp.route('/api/fees', methods=['GET'])
@login_required
def fees_api():
    try:
        year = int(request.args.get('year') or datetime.now().year)
        month = int(request.args.get('month') or datetime.now().month)
    except ValueError:
        return jsonify({"error": "invalid year/month"}), 400
    
    members = Member.query.order_by(Member.id).all()
    results = []
    
    for m in members:
        ensure_payment_rows(m, year)
        p = Payment.query.filter_by(member_id=m.id, year=year, month=month).first()
        status = p.status if p else 'Unpaid'
        
        amount = 0
        paid_date = None
        if status == 'Paid':
            tx = PaymentTransaction.query.filter_by(member_id=m.id, year=year, month=month).first()
            if tx:
                amount = tx.amount
                paid_date = tx.created_at.strftime('%Y-%m-%d')

        results.append({
            'member': m.to_dict(),
            'year': year,
            'month': month,
            'status': status,
            'amount': amount,
            'paid_date': paid_date
        })
    return jsonify(results)

@fees_bp.route('/api/fees/summary', methods=['GET'])
@login_required
def fees_summary():
    try:
        year = int(request.args.get('year') or datetime.now().year)
        month = int(request.args.get('month') or datetime.now().month)
    except ValueError:
        return jsonify({"error": "invalid year/month"}), 400
        
    paid_count = Payment.query.filter_by(year=year, month=month, status='Paid').count()
    unpaid_count = Payment.query.filter_by(year=year, month=month, status='Unpaid').count()
    
    # Revenue (Actual collected)
    paid_total = db.session.query(func.coalesce(func.sum(PaymentTransaction.amount), 0.0)).filter(
        PaymentTransaction.year == year,
        PaymentTransaction.month == month
    ).scalar()
    
    # Projected (Unpaid)
    monthly_price = float(get_setting('monthly_price') or 0)
    unpaid_total = unpaid_count * monthly_price
    
    total_members = paid_count + unpaid_count
    payment_percent = float((paid_count / total_members) * 100.0) if total_members else 0.0
    
    return jsonify({
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'paid_total': round(paid_total or 0, 2),
        'unpaid_total': round(unpaid_total, 2),
        'payment_percent': round(payment_percent, 2)
    })

@fees_bp.route('/api/fees/month', methods=['GET'])
@login_required
def fees_month_detail():
    try:
        year = int(request.args.get('year') or datetime.now().year)
        month = int(request.args.get('month') or datetime.now().month)
    except ValueError:
        return jsonify({"ok": False, "error": "invalid year/month"}), 400
    
    payments = Payment.query.filter_by(year=year, month=month).all()
    paid_count = sum(1 for p in payments if p.status == 'Paid')
    unpaid_count = sum(1 for p in payments if p.status == 'Unpaid')
    
    currency = get_setting('currency_code') or 'PKR'
    collected = 0.0
    members_data = []
    
    for p in payments:
        member = db.session.get(Member, p.member_id)
        if not member:
            continue
        
        amount = 0.0
        paid_date = None
        
        if p.status == 'Paid':
            tx = PaymentTransaction.query.filter_by(
                member_id=member.id,
                year=year,
                month=month
            ).order_by(PaymentTransaction.created_at.desc()).first()
            if tx:
                amount = tx.amount or 0.0
                paid_date = tx.created_at.strftime('%Y-%m-%d') if tx.created_at else None
                collected += amount
        
        members_data.append({
            'member_id': member.id,
            'name': member.name,
            'phone': member.phone,
            'email': member.email,
            'admission_date': member.admission_date.strftime('%Y-%m-%d') if member.admission_date else None,
            'is_active': member.is_active,
            'status': p.status,
            'amount': amount,
            'paid_date': paid_date
        })
    
    return jsonify({
        'ok': True,
        'year': year,
        'month': month,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'collected': round(collected, 2),
        'currency': currency,
        'members': members_data
    })

@fees_bp.route('/api/fees/unpaid-summary', methods=['GET'])
@login_required
def fees_unpaid_summary():
    try:
        monthly_price = float(get_setting('monthly_price') or '8')
    except Exception:
        monthly_price = 8.0
    
    members = Member.query.all()
    unpaid_members = []
    
    for member in members:
        unpaid_payments = Payment.query.filter_by(
            member_id=member.id,
            status='Unpaid'
        ).order_by(Payment.year.desc(), Payment.month.desc()).all()
        
        if not unpaid_payments:
            continue
        
        months_unpaid = len(unpaid_payments)
        total_due = months_unpaid * monthly_price
        
        last_paid = Payment.query.filter_by(
            member_id=member.id,
            status='Paid'
        ).order_by(Payment.year.desc(), Payment.month.desc()).first()
        
        last_paid_month = None
        if last_paid:
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            last_paid_month = f"{month_names[last_paid.month - 1]} {last_paid.year}"
        
        unpaid_members.append({
            'id': member.id,
            'name': member.name,
            'phone': member.phone,
            'last_paid_month': last_paid_month,
            'months_unpaid': months_unpaid,
            'total_due': round(total_due, 2)
        })
    
    return jsonify({
        'ok': True,
        'members': unpaid_members
    })

@fees_bp.route('/api/member/<int:member_id>/payment-history', methods=['GET'])
@login_required
def member_payment_history(member_id):
    member = db.session.get(Member, member_id)
    if not member:
        return jsonify({'ok': False, 'error': 'Member not found'}), 404
    
    payments = Payment.query.filter_by(member_id=member_id).order_by(
        Payment.year.desc(),
        Payment.month.desc()
    ).all()
    
    last_paid = None
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    full_month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']
                   
    for p in payments:
        if p.status == 'Paid':
            last_paid = f"{month_names[p.month - 1]} {p.year}"
            break    
    months_unpaid = sum(1 for p in payments if p.status == 'Unpaid')
    
    payment_list = []
    for p in payments:
        amount = None
        paid_date = None
        
        if p.status == 'Paid':
            tx = PaymentTransaction.query.filter_by(
                member_id=member.id,
                year=p.year,
                month=p.month
            ).order_by(PaymentTransaction.created_at.desc()).first()
            if tx:
                amount = tx.amount
                paid_date = tx.created_at.strftime('%Y-%m-%d') if tx.created_at else None
        
        payment_list.append({
            'year': p.year,
            'month': p.month,
            'month_name': full_month_names[p.month - 1],
            'status': p.status,
            'amount': amount,
            'paid_date': paid_date
        })
    
    return jsonify({
        'ok': True,
        'member': {
            'id': member.id,
            'name': member.name,
            'phone': member.phone,
            'email': member.email,
            'admission_date': member.admission_date.strftime('%Y-%m-%d') if member.admission_date else None,
            'monthly_price': float(getattr(member, 'monthly_price', 0) or 0),
            'is_active': member.is_active,
        },
        'last_paid_month': last_paid,
        'months_unpaid': months_unpaid,
        'payments': payment_list,
        'currency': 'PKR' # Default or fetch
    })

@fees_bp.route('/api/payment/pay-now', methods=['POST'])
@login_required
def pay_now():
    data = request.json
    member_id = data.get('member_id')
    month = data.get('month') # can be "YYYY-MM" or separate year/month
    year = data.get('year')
    
    # Check if month is string "YYYY-MM"
    if isinstance(month, str) and '-' in month:
         try:
            year, month = map(int, month.split('-'))
         except:
            pass
            
    if not member_id or not month or not year:
        return jsonify({'error': 'Missing data'}), 400
        
    # Find payment record
    p = Payment.query.filter_by(member_id=member_id, year=year, month=month).first()
    if not p:
        p = Payment(member_id=member_id, year=year, month=month, status='Unpaid')
        db.session.add(p)
    
    if p.status == 'Paid':
        return jsonify({'error': 'Already paid'}), 400
    
    # Calculate amount
    amount = data.get('amount')
    if amount is None:
        member = db.session.get(Member, member_id)
        amount = float(getattr(member, 'monthly_fee', 0) or get_setting('monthly_price') or 0)
        
    p.status = 'Paid'
    
    # Record transaction
    tx = PaymentTransaction(
        member_id=member_id,
        year=year,
        month=month,
        amount=amount,
        plan_type='monthly',
        created_at=datetime.now(),
        method=data.get('method', 'cash')
    )
    db.session.add(tx)
    db.session.commit()
    
    return jsonify({
        'ok': True,
        'transaction_id': tx.id,
        'receipt_url': url_for('fees.receipt_view', tx_id=tx.id)
    })

@fees_bp.route('/api/fees/mark-paid', methods=['POST'])
@login_required
def api_fees_mark_paid():
    # Alias for pay_now with slightly different signature if needed
    return pay_now()

@fees_bp.route('/api/payment/mark-unpaid', methods=['POST'])
@login_required
def mark_unpaid():
    data = request.json
    member_id = data.get('member_id')
    month_str = data.get('month')
    
    if not member_id or not month_str:
        return jsonify({'error': 'Missing data'}), 400
        
    try:
        y, m = map(int, month_str.split('-'))
    except:
        return jsonify({'error': 'Invalid month format'}), 400
        
    p = Payment.query.filter_by(member_id=member_id, year=y, month=m).first()
    if p:
        p.status = 'Unpaid'
        PaymentTransaction.query.filter_by(member_id=member_id, year=y, month=m).delete()
        db.session.commit()
        
    return jsonify({'ok': True})

@fees_bp.route('/receipt/<int:tx_id>')
@login_required
def receipt_view(tx_id: int):
    tx = db.session.get(PaymentTransaction, tx_id)
    if not tx:
        return 'Receipt not found', 404
    ctx = _render_receipt_context(tx)
    return render_template('receipt.html', **ctx)
