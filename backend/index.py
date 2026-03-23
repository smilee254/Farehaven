# Senior Review: Clean Structure Optimization (frontend/backend)
import os, sys, json, csv, time, random
from io import StringIO
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 1. Portable Library Path (Weight Reduction)
lib_path = os.path.join(os.path.dirname(__file__), '.lib_v3')
if os.path.exists(lib_path):
    sys.path.insert(0, lib_path)

# 2. Optimized Imports
try: from supabase import create_client, Client
except: create_client, Client = None, None

# 3. Path-Aware Flask App (Points to ../frontend/)
app = Flask(__name__, 
            template_folder='../frontend/templates', 
            static_folder='../frontend/static')
app.secret_key = os.environ.get('SECRET_KEY', 'wowman_executive_muse_secret_key')

# Supabase Credentials
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', os.environ.get('SUPABASE_KEY', ''))
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', "thewowmanfarehaven@gmail.com")

# Initialize Supabase
supabase: Client = None
if create_client and SUPABASE_URL and SUPABASE_KEY:
    try: supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except: pass

QUOTES = [
    "Reconnecting you with your youth through retreats and workshops.",
    "Finding your Spark again in connection with others.",
    "A sanctuary for Mental Wellness.",
    "Authentic collaboration powers excellence.",
    "Embrace your journey of self-discovery."
]

# --- Dual Storage: Supabase with Local data.json Fallback ---
INTERNAL_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data.json')

def load_local_data() -> dict:
    default_structure = {"events": [], "registrations": []}
    if os.path.exists(INTERNAL_DATA_PATH):
        with open(INTERNAL_DATA_PATH, 'r') as f:
            try:
                data = json.load(f)
                if not isinstance(data, dict): return default_structure
                for key in default_structure:
                    if key not in data: data[key] = []
                return data
            except: return default_structure
    return default_structure

def save_local_data(data: dict):
    with open(INTERNAL_DATA_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def get_events():
    if supabase:
        try: return supabase.table('events').select('*').execute().data
        except: pass
    return load_local_data().get('events', [])

def get_registrations():
    if supabase:
        try: return supabase.table('registrations').select('*').order('created_at', desc=True).execute().data
        except: pass
    return load_local_data().get('registrations', [])

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html', quote=random.choice(QUOTES))

@app.route('/register', methods=['POST'])
def register():
    form_data = {k: request.form.get(k) for k in ['name', 'phone', 'category', 'activity', 'mpesa']}
    if all([form_data['name'], form_data['phone'], form_data['category'], form_data['activity']]):
        if supabase:
            try: supabase.table('registrations').insert(form_data).execute()
            except: pass
        data = load_local_data()
        form_data['id'] = 1 if not data['registrations'] else max(r.get('id', 0) for r in data['registrations']) + 1
        data['registrations'].append(form_data)
        save_local_data(data)
        flash('Registration successful!', 'success')
    else: flash('Please fill in required fields.', 'error')
    return redirect(url_for('index') + '#register')

@app.route('/api/events')
def api_events():
    return jsonify(get_events())

@app.route('/admin')
def admin_root():
    return redirect(url_for('admin_dashboard')) if session.get('admin_authorized') else redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('email') == ADMIN_EMAIL:
            session['admin_authorized'] = True; return redirect(url_for('admin_dashboard'))
        flash('Unauthorized.', 'error')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_authorized'): return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html', data={"events": get_events(), "registrations": get_registrations()})

@app.route('/admin/gallery/add', methods=['POST'])
def add_event():
    if not session.get('admin_authorized'): return jsonify({"error": "Unauthorized"}), 403
    event_data = {k: request.form.get(k) for k in ['title','location','fee','image_url','description']}
    if all(event_data.values()):
        if supabase:
            try: supabase.table('events').insert(event_data).execute()
            except: pass
        data = load_local_data()
        event_data['id'] = 1 if not data['events'] else max(e.get('id', 0) for e in data['events']) + 1
        data['events'].append(event_data)
        save_local_data(data)
        flash('New event added!', 'success')
    else: flash('Details missing.', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/registration/<int:reg_id>')
def delete_registration(reg_id):
    if not session.get('admin_authorized'): return jsonify({"error": "Unauthorized"}), 403
    try:
        if supabase:
            try: supabase.table('registrations').delete().eq('id', reg_id).execute()
            except: pass
        data = load_local_data()
        data['registrations'] = [r for r in data['registrations'] if r.get('id') != reg_id]
        save_local_data(data)
        flash('Removed.', 'success')
    except: pass
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/event/<int:event_id>')
def delete_event(event_id):
    if not session.get('admin_authorized'): return jsonify({"error": "Unauthorized"}), 403
    try:
        if supabase:
            try: supabase.table('events').delete().eq('id', event_id).execute()
            except: pass
        data = load_local_data()
        data['events'] = [e for e in data['events'] if e.get('id') != event_id]
        save_local_data(data)
        flash('Removed.', 'success')
    except: pass
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def logout(): session.pop('admin_authorized', None); return redirect(url_for('admin_login'))

if __name__ == '__main__':
    # Optimized: Removed reloader for 2026 Celeron Hardware
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
