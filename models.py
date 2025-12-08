from datetime import datetime
from extensions import db
import os
import json

# Helper functions that models depend on
def get_setting(key: str, default: str | None = None) -> str | None:
    # Avoid circular import by importing inside function if needed, 
    # but Setting is in this file so it's fine.
    s = Setting.query.filter_by(key=key).first()
    return s.value if s else default

def _normalize_phone(phone: str) -> str:
    # Simplified version of the one in app.py to avoid circular dependency if possible.
    # Ideally this utility should be in a utils.py
    return phone.strip()

def find_member_image_url(member_id: int):
    # This depends on UPLOAD_FOLDER which is config. 
    # For now, return a placeholder or move logic to a utility.
    # We'll keep it simple for the model method.
    return f"/static/uploads/member_{member_id}.jpg" 

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50))
    admission_date = db.Column(db.Date, nullable=False)
    plan_type = db.Column(db.String(20), default='monthly')
    referral_code = db.Column(db.String(32), unique=True)
    referred_by = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=True)
    access_tier = db.Column(db.String(20), default='standard')
    email = db.Column(db.String(255), nullable=True)
    training_type = db.Column(db.String(30), default='standard')
    special_tag = db.Column(db.Boolean, default=False)
    custom_training = db.Column(db.String(50), nullable=True)
    monthly_fee = db.Column(db.Float, nullable=True)
    last_contact_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        # Simplified to_dict to avoid complex queries in model for now
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "admission_date": self.admission_date.isoformat(),
            "plan_type": self.plan_type,
            "training_type": self.training_type,
            "monthly_fee": self.monthly_fee,
            "is_active": self.is_active,
            "current_fee_status": "Unknown" # Populated by service layer
        }

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), default='staff')

class OAuthAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    provider_id = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PaymentTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    plan_type = db.Column(db.String(20), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=True)
    amount = db.Column(db.Float, nullable=True)
    method = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(1000), nullable=True)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(100), nullable=False)
    data_json = db.Column(db.Text, nullable=False)
    prev_hash = db.Column(db.String(64), nullable=True)
    hash = db.Column(db.String(64), nullable=False)

class UploadedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    content_hash = db.Column(db.String(64), nullable=False, unique=True)
    rows_count = db.Column(db.Integer, nullable=False, default=0)
    rows_json = db.Column(db.Text, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0.0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    category = db.Column(db.String(80), nullable=True)
    sku = db.Column(db.String(60), unique=True, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(32), unique=True, nullable=False)
    customer_name = db.Column(db.String(120), nullable=True)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    tax = db.Column(db.Float, nullable=False, default=0.0)
    discount = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)
    payment_method = db.Column(db.String(40), nullable=True)
    note = db.Column(db.String(255), nullable=True)
    channel = db.Column(db.String(30), nullable=False, default='pos')
    status = db.Column(db.String(30), nullable=False, default='paid')
    verification_hash = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    synced_from_offline = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('SaleItem', backref='sale', cascade='all, delete-orphan')

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    name = db.Column(db.String(140), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    total_price = db.Column(db.Float, nullable=False, default=0.0)

class LoginLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    username = db.Column(db.String(120), nullable=False)
    method = db.Column(db.String(30), nullable=False)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
