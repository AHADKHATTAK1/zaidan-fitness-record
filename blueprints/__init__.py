from flask import Blueprint
from blueprints.auth import auth_bp
from blueprints.members import members_bp
from blueprints.inventory import inventory_bp
from blueprints.pos import pos_bp
from blueprints.settings import settings_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(pos_bp)
    app.register_blueprint(settings_bp)
