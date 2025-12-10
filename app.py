from flask import Flask, session, redirect, url_for
from extensions import db, migrate, oauth
from blueprints import register_blueprints
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from blueprints.communications import send_bulk_template_reminders, send_bulk_text_reminders
from datetime import datetime

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key')
    
    # Database Configuration
    db_url = os.getenv('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    if not db_url:
        # Fallback to absolute path SQLite
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, 'gym.db')
        db_url = 'sqlite:///' + db_path

    print(f"--> Using Database: {db_url}") # Debug log
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    oauth.init_app(app)
    
    # Ensure tables exist (Import models first!)
    with app.app_context():
        # Explicitly import models to ensure valid registration before create_all
        import models 
        db.create_all()
        print("--> Tables created successfully.")
    
    # Register blueprints
    register_blueprints(app)
    
    # Scheduler Setup
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler = BackgroundScheduler()
        hour = int(os.getenv('SCHEDULE_TIME_HH', '9'))
        minute = int(os.getenv('SCHEDULE_TIME_MM', '0'))
        
        def scheduled_job():
            with app.app_context():
                now = datetime.now()
                try:
                    if os.getenv('WHATSAPP_TEMPLATE_FEE_REMINDER_NAME'):
                        send_bulk_template_reminders(now.year, now.month)
                    else:
                        send_bulk_text_reminders(now.year, now.month)
                except Exception:
                    pass
                    
        scheduler.add_job(scheduled_job, CronTrigger(hour=hour, minute=minute))
        scheduler.start()
    
    @app.route('/')
    def home():
        if 'user_id' in session:
            return redirect(url_for('dashboard.dashboard'))
        return redirect(url_for('auth.login'))

    @app.route('/offline')
    def offline():
        return render_template('offline.html')

    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
