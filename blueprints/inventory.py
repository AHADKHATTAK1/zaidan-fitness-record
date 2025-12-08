from flask import Blueprint, render_template, request, jsonify
from extensions import db
from models import Product
from datetime import datetime

inventory_bp = Blueprint('inventory', __name__)

def login_required(f):
    from functools import wraps
    from flask import session, redirect, url_for
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@inventory_bp.route('/products')
@login_required
def index():
    return render_template('inventory.html')

@inventory_bp.route('/api/products', methods=['GET'])
@login_required
def list_products():
    q = request.args.get('search', '').lower().strip()
    query = Product.query.filter_by(is_active=True)
    
    if q:
        query = query.filter(Product.name.ilike(f'%{q}%') | Product.sku.ilike(f'%{q}%'))
        
    products = query.order_by(Product.name).all()
    return jsonify([p.to_dict() for p in products])

@inventory_bp.route('/api/products', methods=['POST'])
@login_required
def add_product():
    data = request.json
    try:
        p = Product(
            name=data['name'],
            price=float(data.get('price', 0)),
            stock=int(data.get('stock', 0)),
            category=data.get('category'),
            sku=data.get('sku'),
            is_active=True
        )
        db.session.add(p)
        db.session.commit()
        return jsonify(p.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@inventory_bp.route('/api/products/<int:id>', methods=['PUT'])
@login_required
def update_product(id):
    p = db.session.get(Product, id)
    if not p: return jsonify({'error': 'Not found'}), 404
    data = request.json
    
    if 'name' in data: p.name = data['name']
    if 'price' in data: p.price = float(data['price'])
    if 'stock' in data: p.stock = int(data['stock'])
    if 'category' in data: p.category = data['category']
    if 'sku' in data: p.sku = data['sku']
    
    db.session.commit()
    return jsonify(p.to_dict())

@inventory_bp.route('/api/products/<int:id>', methods=['DELETE'])
@login_required
def delete_product(id):
    p = db.session.get(Product, id)
    if not p: return jsonify({'error': 'Not found'}), 404
    p.is_active = False # Soft delete
    db.session.commit()
    return jsonify({'ok': True})
