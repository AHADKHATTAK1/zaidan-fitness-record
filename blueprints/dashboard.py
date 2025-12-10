from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from extensions import db
from models import Member, Payment, User, AuditLog, Setting, Sale, SaleItem
from datetime import datetime
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    now = datetime.now()
    
    # 1. Member Stats
    total_members = Member.query.count()
    active_members = Member.query.filter_by(is_active=True).count()
    
    # 2. Payment Stats (Current Month)
    paid_count = Payment.query.filter_by(year=now.year, month=now.month, status='Paid').count()
    unpaid_count = Payment.query.filter_by(year=now.year, month=now.month, status='Unpaid').count()
    
    # 3. Revenue Stats (Current Month)
    sales_revenue = db.session.query(func.sum(Sale.total)).filter(
        func.strftime('%Y-%m', Sale.created_at) == now.strftime('%Y-%m')
    ).scalar() or 0.0

    # 4. Recent Activity
    recent_activity = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()

    # 5. Settings
    gym_name_setting = Setting.query.filter_by(key='gym_name').first()
    gym_name = gym_name_setting.value if gym_name_setting else 'Zaidan Fitness'
    
    currency_setting = Setting.query.filter_by(key='currency_code').first()
    currency_code = currency_setting.value if currency_setting else 'USD'
    
    return render_template('dashboard.html',
                           total_members=total_members,
                           active_members=active_members,
                           paid_count=paid_count,
                           unpaid_count=unpaid_count,
                           sales_revenue=round(sales_revenue, 2),
                           recent_activity=recent_activity,
                           gym_name=gym_name,
                           currency_code=currency_code,
                           month=now.strftime('%B'),
                           year=now.year)


@dashboard_bp.route('/api/stats/monthly')
@login_required
def stats_monthly():
    try:
        year = int(request.args.get('year') or datetime.now().year)
    except ValueError:
        return jsonify({"error":"invalid year"}), 400
    
    paid = []
    unpaid = []
    
    for m in range(1, 13):
        p = Payment.query.filter_by(year=year, month=m, status='Paid').count()
        u = Payment.query.filter_by(year=year, month=m, status='Unpaid').count()
        paid.append(p)
        unpaid.append(u)
        
    return jsonify({"year": year, "paid": paid, "unpaid": unpaid})
