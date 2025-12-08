from flask import Blueprint, render_template, request, jsonify, session
from extensions import db
from models import Sale, SaleItem, Product, User
from datetime import datetime
import secrets

pos_bp = Blueprint('pos', __name__)

def login_required(f):
    from functools import wraps
    from flask import redirect, url_for
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@pos_bp.route('/pos')
@login_required
def index():
    return render_template('pos.html')

@pos_bp.route('/api/pos/checkout', methods=['POST'])
@login_required
def checkout():
    data = request.json
    items = data.get('items', [])
    if not items:
        return jsonify({'error': 'No items'}), 400
        
    try:
        # Calculate totals and verify stock
        subtotal = 0.0
        sale_items = []
        
        for item in items:
            product = db.session.get(Product, item['product_id'])
            if not product:
                continue
            
            qty = int(item['quantity'])
            if product.stock < qty:
                return jsonify({'error': f'Insufficient stock for {product.name}'}), 400
                
            product.stock -= qty
            line_total = product.price * qty
            subtotal += line_total
            
            sale_items.append(SaleItem(
                product_id=product.id,
                name=product.name,
                quantity=qty,
                unit_price=product.price,
                total_price=line_total
            ))
            
        tax = 0.0 # Implement tax logic if needed
        discount = float(data.get('discount', 0))
        total = subtotal + tax - discount
        
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"
        
        sale = Sale(
            invoice_number=invoice_number,
            customer_name=data.get('customer_name'),
            subtotal=subtotal,
            tax=tax,
            discount=discount,
            total=total,
            payment_method=data.get('payment_method', 'cash'),
            user_id=session.get('user_id'),
            verification_hash=secrets.token_hex(16)
        )
        
        db.session.add(sale)
        db.session.commit() # Commit to get sale ID
        
        for si in sale_items:
            si.sale_id = sale.id
            db.session.add(si)
            
        db.session.commit()
        
        return jsonify({'ok': True, 'invoice_number': invoice_number, 'sale_id': sale.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@pos_bp.route('/api/sales', methods=['GET'])
@login_required
def list_sales():
    sales = Sale.query.order_by(Sale.created_at.desc()).limit(50).all()
    return jsonify([s.to_dict() for s in sales])
