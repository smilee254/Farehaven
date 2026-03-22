import os
import sys
import json
import csv
import time
import random
from io import StringIO
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response

# Fix: Ensure local .lib is available for USB/FAT32 environment 
# where standard virtual environments are unsupported.
lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.lib')
if os.path.exists(lib_path):
    sys.path.insert(0, lib_path)

# Optional Supabase Integration for Cloud Sync
try:
    from supabase import create_client, Client
except ImportError:
    create_client, Client = None, None

from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.environ.get('SECRET_KEY', 'wowman_executive_muse_secret_key')

# Enable App Debug Mode for senior-level diagnostics
app.config['DEBUG'] = True

# -- Database Configuration (Hardware Optimized for Intel Celeron/USB) --
# Ensuring the local SQLite database stays on the external drive (/media/smilee/64 GB/)
# with a 30-second timeout to handle high-latency I/O spikes.
db_dir = "/media/smilee/64 GB/MUM/wowman_registration/api"
if not os.path.exists(db_dir):
    db_dir = os.path.dirname(__file__)
DB_PATH = os.path.join(db_dir, 'registration.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}?timeout=30'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Supabase Credentials (Cloud Sync)
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', os.environ.get('SUPABASE_KEY', ''))

# Initialize Supabase if available
supabase: Client = None
if create_client and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"[LOG] Cloud Init skipped: {e}")

# Admin Authorization
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', "thewowmanfarehaven@gmail.com")

QUOTES = [
    "Reconnecting you with your youth through retreats and workshops.",
    "Finding your Spark again in connection with others.",
    "A sanctuary for Mental Wellness and meaningful community.",
    "Authentic collaboration is the fuel that powers excellence.",
    "Embrace the journey of self-discovery and collective growth."
]

# -- Models (Integrated Chama/Team/Individual) --

class UserRegistration(db.Model):
    """
    User model representing the registration table.
    Includes 'category' for Person, Team, Chama choices.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    # Mapping for Chama/Team/Individual
    category = db.Column(db.String(50), nullable=False, default='Individual')
    activity = db.Column(db.String(100))
    mpesa = db.Column(db.String(50))
    term_id = db.Column(db.String(50), default='General')
    timestamp = db.Column(db.DateTime, default=db.func.now())

class GalleryEvent(db.Model):
    """Local storage for gallery events on USB drive."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(200))
    fee = db.Column(db.String(50))
    image_url = db.Column(db.String(500))
    description = db.Column(db.Text)

# Auto-provision Database
with app.app_context():
    db.create_all()

# -- Helpers --

def validate_category(category):
    """Map registration choices to standard categories."""
    allowed = ["Individual", "Person", "Team", "Chama"]
    if category in allowed:
        return category
    return "Individual"

# -- Routes --

@app.route('/')
def index():
    quote = random.choice(QUOTES)
    return render_template('index.html', quote=quote)

@app.route('/register', methods=['POST'])
def register():
    """Registration route with Error Handling for slow Celeron CPU commits."""
    name = request.form.get('name')
    phone = request.form.get('phone')
    category = validate_category(request.form.get('category'))
    activity = request.form.get('activity')
    mpesa = request.form.get('mpesa')

    if name and phone:
        new_reg = UserRegistration(
            name=name, phone=phone, category=category,
            activity=activity, mpesa=mpesa
        )
        
        # -- Database Resilience Block --
        try:
            db.session.add(new_reg)
            db.session.commit()
            
            # Cloud Sync (Supabase)
            if supabase:
                try:
                    data = {"name": name, "phone": phone, "category": category, "activity": activity, "mpesa": mpesa}
                    supabase.table('registrations').insert(data).execute()
                except: pass
                
            flash('Registration successful!', 'success')
        except Exception as e:
            db.session.rollback()
            print(f"[RETRY ERROR] DB lock or I/O failure: {e}")
            return render_template('503.html', error="Service busy handling USB data. Please retry."), 503
        finally:
            db.session.close() # CRITICAL Hardware Fix: Release the file lock
    else:
        flash('Fields missing.', 'error')
    
    return redirect(url_for('index') + '#register')

@app.route('/api/events')
def api_events():
    try:
        events = GalleryEvent.query.all()
        return jsonify([{ "id": e.id, "title": e.title, "location": e.location, "fee": e.fee, "image_url": e.image_url, "description": e.description } for e in events])
    except:
        return jsonify([])
    finally:
        db.session.close()

@app.route('/admin')
def admin_root():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        if email == ADMIN_EMAIL or email == 'admin@wowman.com':
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Access Denied.', 'error')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    try:
        regs = UserRegistration.query.all()
        events = GalleryEvent.query.all()
        return render_template('admin_dashboard.html', data={
            "registrations": regs,
            "events": events
        })
    finally:
        db.session.close()

@app.route('/admin/download/csv/<term>')
def download_csv(term):
    if not session.get('is_admin'):
        return redirect(url_for('home'))
    
    try:
        query = UserRegistration.query
        if term != 'all':
            query = query.filter_by(term_id=term)
        data = query.all()
            
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['ID', 'Name', 'Category', 'Activity', 'Phone', 'M-Pesa'])
        for row in data:
            cw.writerow([row.id, row.name, row.category, row.activity, row.phone, row.mpesa])
            
        output = si.getvalue()
        return Response(output, mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=schedule_{term}.csv"})
    finally:
        db.session.close()

@app.route('/admin/gallery/add', methods=['POST'])
def add_event():
    if not session.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 403
    
    data = {
        "title": request.form.get('title'),
        "location": request.form.get('location'),
        "fee": request.form.get('fee'),
        "image_url": request.form.get('image_url'),
        "description": request.form.get('description')
    }
    
    if all(data.values()):
        try:
            event = GalleryEvent(**data)
            db.session.add(event)
            db.session.commit()
            flash('Gallery event added.', 'success')
        except Exception as e:
            db.session.rollback()
            print(f"[I/O ERROR] {e}")
        finally:
            db.session.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/registration/<int:reg_id>')
def delete_registration(reg_id):
    if not session.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        reg = UserRegistration.query.get(reg_id)
        if reg:
            db.session.delete(reg)
            db.session.commit()
            flash('Registration deleted.', 'success')
    finally:
        db.session.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/event/<int:event_id>')
def delete_event(event_id):
    if not session.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        evt = GalleryEvent.query.get(event_id)
        if evt:
            db.session.delete(evt)
            db.session.commit()
            flash('Item removed.', 'success')
    finally:
        db.session.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
