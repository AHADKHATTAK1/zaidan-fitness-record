from flask import Flask, render_template, session, redirect, url_for
from extensions import db, migrate, oauth
from blueprints import register_blueprints
from models import User, Member, Payment, AuditLog, Setting
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'
    
    db.init_app(app)
    migrate.init_app(app, db)
    oauth.init_app(app)
    
    register_blueprints(app)
    
    @app.route('/')
    def home():
        if 'user_id' in session:
            return redirect(url_for('dashboard.dashboard'))
        return redirect(url_for('auth.login'))

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
