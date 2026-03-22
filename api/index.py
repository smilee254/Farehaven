import os
import json
import random
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from dotenv import load_dotenv

# Load environment variables from .env if it exists
load_dotenv()

try:
    from supabase import create_client, Client
except ImportError:
    create_client, Client = None, None

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.environ.get('SECRET_KEY', 'wowman_executive_muse_secret_key')

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
def load_local_data() -> dict:
    """Load local data and ensure a consistent dictionary structure."""
    local_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.json')
    default_structure = {"events": [], "registrations": []}
    
    if os.path.exists(local_path):
        with open(local_path, 'r') as f:
            try:
                data = json.load(f)
                if not isinstance(data, dict):
                    return default_structure
                # Ensure keys exist
                for key in default_structure:
                    if key not in data:
                        data[key] = []
                return data
            except:
                return default_structure
    return default_structure

def save_local_data(data: dict):
    """Save dictionary to local file atomically if possible."""
    local_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.json')
    with open(local_path, 'w') as f:
        json.dump(data, f, indent=4)

def get_events():
    if supabase:
        try:
            return supabase.table('events').select('*').execute().data
        except: pass
    return load_local_data().get('events', [])

def get_registrations():
    if supabase:
        try:
            return supabase.table('registrations').select('*').order('created_at', desc=True).execute().data
        except: pass
    return load_local_data().get('registrations', [])

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
        "category": request.form.get('category'),
        "activity": request.form.get('activity'),
        "mpesa": request.form.get('mpesa')
    }
    
    if all([form_data['name'], form_data['phone'], form_data['category'], form_data['activity']]):
        if supabase:
            try:
                supabase.table('registrations').insert(form_data).execute()
                flash('Registration successful! [Cloud]', 'success')
            except: pass
        
        # Always allow local write for preview/offline mode
        data = load_local_data()
        form_data['id'] = 1 if not data['registrations'] else max(r.get('id', 0) for r in data['registrations']) + 1
        data['registrations'].append(form_data)
        save_local_data(data)
        flash('Registration successful!', 'success')
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
    """
    Delete a user registration with Safety Rails to prevent 500 errors.
    Optimized for low-resource environments with detailed error logging.
    """
    if not session.get('admin_authorized'):
        return jsonify({"error": "Unauthorized"}), 403

    print(f"[LOG] Attempting to delete registration ID: {reg_id}")
    
    success = False
    error_detail = "Unknown error"

    try:
        # 1. Supabase Deletion (Primary)
        if supabase:
            try:
                # Potential Foreign Key issues handled here if specific tables were known
                # Currently handling general database interaction with logging
                response = supabase.table('registrations').delete().eq('id', reg_id).execute()
                print(f"[LOG] Supabase Delete Response: {response}")
                success = True
            except Exception as se:
                error_detail = f"Supabase Error: {str(se)}"
                print(f"[ERROR] Database Integrity/Connection Failure: {error_detail}")
                # We don't return here yet; we still try to sync with local fallback

        # 2. Local JSON Synchronization (Fallback/Redundancy)
        try:
            data: dict = load_local_data()
            original_registrations = data.get('registrations', [])
            original_count = len(original_registrations)
            
            # Use explicit list comprehension with local variable to assist type inference
            data['registrations'] = [r for r in original_registrations if r.get('id') != reg_id]
            
            if len(data['registrations']) < original_count:
                save_local_data(data)
                print(f"[LOG] Local record {reg_id} removed successfully.")
                success = True
            else:
                if not success: # Only if Supabase also failed or didn't run
                    error_detail = "Record ID not found in local storage."
                    print(f"[WARN] {error_detail}")
        except Exception as le:
            error_detail = f"Local Storage Error: {str(le)}"
            print(f"[ERROR] IO Failure: {error_detail}")
            # If local saving fails on Celeron, it might be disk IO/timeout issues

        if success:
            flash(f'Registration {reg_id} removed.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            return jsonify({"status": "fail", "reason": error_detail}), 400

    except Exception as e:
        # Catch-all for extreme failures (e.g. system crashes)
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e), "trace": "Check server logs"}), 500

@app.route('/admin/delete/event/<int:event_id>')
def delete_event(event_id):
    """
    Delete a gallery event with similar Safety Rails.
    """
    if not session.get('admin_authorized'):
        return jsonify({"error": "Unauthorized"}), 403

    print(f"[LOG] Attempting to delete event ID: {event_id}")
    
    try:
        if supabase:
            try:
                supabase.table('events').delete().eq('id', event_id).execute()
                print(f"[LOG] Supabase Event {event_id} deleted.")
            except Exception as se:
                print(f"[ERROR] Supabase Event Delete Failure: {se}")

        data: dict = load_local_data()
        original_events = data.get('events', [])
        data['events'] = [e for e in original_events if e.get('id') != event_id]
        save_local_data(data)
        
        flash('Gallery item removed.', 'success')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        print(f"[CRITICAL] Delete Event Failed: {e}")
        return jsonify({"status": "error", "reason": str(e)}), 500

@app.route('/admin/logout')
def logout():
    session.pop('admin_authorized', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
