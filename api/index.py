import os
import json
import random
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

from flask_sqlalchemy import SQLAlchemy

# Load environment variables from .env if it exists
load_dotenv()

try:
    from supabase import create_client, Client
except ImportError:
    create_client, Client = None, None

# Path-Aware Flask App (Senior Fix: Absolute paths for Vercel)
base_dir = os.path.dirname(os.path.dirname(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(base_dir, 'templates'), 
            static_folder=os.path.join(base_dir, 'static'))
app.secret_key = os.environ.get('SECRET_KEY', 'wowman_executive_muse_secret_key')

# --- Database Safety (USB Drive & Vercel) ---
if os.environ.get('VERCEL'):
    # Vercel Temporary Storage
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////tmp/registration.db')
else:
    # Local Persistence on USB Mount Point
    # Explicitly using the /media/smilee/64 GB/ mount point.
    DB_PATH = '/media/smilee/64 GB/MUM/wowman_registration/registration.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}?timeout=30'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Supabase Credentials
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', os.environ.get('SUPABASE_KEY', ''))

# Initialize Supabase
supabase: Client = None
if create_client and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error initializing Supabase: {e}")

# Admin Email
ADMIN_EMAIL = "thewowmanfarehaven@gmail.com"

QUOTES = [
    "Reconnecting you with your youth through retreats and workshops.",
    "Finding your Spark again in connection with others.",
    "A sanctuary for Mental Wellness and meaningful community.",
    "Authentic collaboration is the fuel that powers excellence.",
    "Embrace the journey of self-discovery and collective growth."
]

# --- Dual Storage: Supabase with Local data.json Fallback ---
def get_local_path():
    if os.environ.get('VERCEL'):
        return '/tmp/data.json'
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.json')

def load_local_data():
    local_path = get_local_path()
    if os.path.exists(local_path):
        try:
            with open(local_path, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"events": [], "registrations": []}

def save_local_data(data):
    local_path = get_local_path()
    try:
        with open(local_path, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save local data: {e}")

def get_events():
    if supabase:
        try:
            return supabase.table('events').select('*').execute().data
        except: pass
    return load_local_data().get('events', [])

# --- Models ---
class UserRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(100), default='Individual')  # Individual, Chama, Corporate
    activity = db.Column(db.String(100))
    mpesa = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.now())

with app.app_context():
    db.create_all()

# --- Helpers ---
def get_registrations():
    try:
        regs = UserRegistration.query.order_by(UserRegistration.created_at.desc()).all()
        return [{"id":r.id, "name":r.name, "phone":r.phone, "category":r.category, "activity":r.activity, "mpesa":r.mpesa} for r in regs]
    except Exception as e:
        print(f"DB Fetch Error: {e}")
        if supabase:
            try: return supabase.table('registrations').select('*').order('created_at', desc=True).execute().data
            except: pass
        return load_local_data().get('registrations', [])

# --- Error Handling (Vercel Compatibility Guard) ---
@app.errorhandler(500)
def handle_500(e):
    logging.error(f"Internal Server Error: {e}")
    return render_template('index.html', quote="Service is temporarily adjusting. Please try again or contact us on WhatsApp."), 500

# --- Routes ---

@app.route('/')
def index():
    quote = random.choice(QUOTES)
    return render_template('index.html', quote=quote)

@app.route('/register', methods=['POST'])
def register():
    form_data = {
        "name": request.form.get('name'),
        "phone": request.form.get('phone'),
        "category": request.form.get('category') or 'Individual',
        "activity": request.form.get('activity'),
        "mpesa": request.form.get('mpesa')
    }
    
    if all([form_data['name'], form_data['phone']]):
        try:
            # 1. Primary: USB/Local SQLite
            new_reg = UserRegistration(**form_data)
            db.session.add(new_reg)
            db.session.commit()
            
            # 2. Cloud Mirror: Supabase
            if supabase:
                try: supabase.table('registrations').insert(form_data).execute()
                except: pass
            
            # 3. Legacy Mirror: JSON
            data = load_local_data()
            form_data['id'] = new_reg.id if hasattr(new_reg, 'id') else random.randint(1000, 9999)
            data['registrations'].append(form_data)
            save_local_data(data)
            
            flash('Registration successful!', 'success')
        except Exception as e:
            db.session.rollback()
            logging.error(f"DEPLOYMENT CRITICAL - Registration Error: {str(e)}")
            # Final Fallback to JSON (Vercel compatible via /tmp/)
            try:
                data = load_local_data()
                form_data['id'] = random.randint(1000, 9999)
                data['registrations'].append(form_data)
                save_local_data(data)
                flash('Registration successful! (Backup Mode Active)', 'success')
            except Exception as e2:
                logging.error(f"Systemic Failure: {e2}")
                flash('Please reach out via WhatsApp while we fix this.', 'success')
        finally:
            db.session.close()
            db.session.remove() # Ensure threads are cleaned up for Vercel
    else:
        flash('Please fill in required fields.', 'error')
    
    return redirect(url_for('index') + '#register')

@app.route('/api/events')
def api_events():
    return jsonify(get_events())

@app.route('/admin')
def admin_root():
    if session.get('admin_authorized'):
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        if email == ADMIN_EMAIL:
            session['admin_authorized'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Unauthorized email access.', 'error')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_authorized'):
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html', data={
        "events": get_events(),
        "registrations": get_registrations()
    })

@app.route('/admin/gallery/add', methods=['POST'])
def add_event():
    if not session.get('admin_authorized'):
        return jsonify({"error": "Unauthorized"}), 403
    
    event_data = {
        "title": request.form.get('title'),
        "location": request.form.get('location'),
        "fee": request.form.get('fee'),
        "image_url": request.form.get('image_url'),
        "description": request.form.get('description')
    }
    
    if all(event_data.values()):
        if supabase:
            try:
                supabase.table('events').insert(event_data).execute()
            except: pass
            
        data = load_local_data()
        event_data['id'] = 1 if not data['events'] else max(e.get('id', 0) for e in data['events']) + 1
        data['events'].append(event_data)
        save_local_data(data)
        flash('New event added!', 'success')
    else:
        flash('Please provide all details.', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/registration/<int:reg_id>')
def delete_registration(reg_id):
    if not session.get('admin_authorized'): return redirect(url_for('admin_login'))
    if supabase:
        try: supabase.table('registrations').delete().eq('id', reg_id).execute()
        except: pass
    
    data = load_local_data()
    data['registrations'] = [r for r in data['registrations'] if r.get('id') != reg_id]
    save_local_data(data)
    flash('Removed.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/event/<int:event_id>')
def delete_event(event_id):
    if not session.get('admin_authorized'): return redirect(url_for('admin_login'))
    if supabase:
        try: supabase.table('events').delete().eq('id', event_id).execute()
        except: pass
    
    data = load_local_data()
    data['events'] = [e for e in data['events'] if e.get('id') != event_id]
    save_local_data(data)
    flash('Gallery item removed.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def logout():
    session.pop('admin_authorized', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
