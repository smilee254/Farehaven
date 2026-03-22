# Senior Review: Clean Structure & Vercel Compatibility
import os, sys, json, csv, time, random, logging
logging.basicConfig(level=logging.DEBUG)
from io import StringIO
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Response

# 1. Portable Library Path (Now within backend/)
lib_path = os.path.join(os.path.dirname(__file__), '.lib_v3')
if os.path.exists(lib_path):
    sys.path.insert(0, lib_path)

# 2. Optimized Imports
try: from supabase import create_client, Client
except: create_client, Client = None, None

from flask_sqlalchemy import SQLAlchemy

# 3. Path-Aware Flask App (Points to ../frontend/)
app = Flask(__name__, 
            template_folder='../frontend/templates', 
            static_folder='../frontend/static')
app.secret_key = os.environ.get('SECRET_KEY', 'wowman_executive_muse_secret_key')

# 4. Environment-Aware Database (Vercel Survival Mode)
# Vercel is Read-Only. We switch to /tmp/ or a real DB URL if available.
DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if os.environ.get('VERCEL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:////tmp/registration.db'
else:
    # Local USB Drive Path
    DB_PATH = os.path.join(os.path.dirname(__file__), 'registration.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}?timeout=30'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 4. Global Config
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', os.environ.get('SUPABASE_KEY', ''))
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', "thewowmanfarehaven@gmail.com")

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

# -- Models --

class UserRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='Individual')
    activity = db.Column(db.String(100))
    mpesa = db.Column(db.String(50))
    term_id = db.Column(db.String(50), default='General')
    timestamp = db.Column(db.DateTime, default=db.func.now())

class GalleryEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(200))
    fee = db.Column(db.String(50))
    image_url = db.Column(db.String(500))
    description = db.Column(db.Text)

with app.app_context(): db.create_all()

# -- Helpers --
def validate_category(c):
    return c if c in ["Individual", "Person", "Team", "Chama"] else "Individual"

# -- Routes --

@app.route('/')
def index():
    return render_template('index.html', quote=random.choice(QUOTES))

@app.route('/register', methods=['POST'])
def register():
    data = {k: request.form.get(k) for k in ['name', 'phone', 'category', 'activity', 'mpesa']}
    data['category'] = validate_category(data['category'])

    if data['name'] and data['phone']:
        try:
            reg = UserRegistration(**data)
            db.session.add(reg); db.session.commit()
            if supabase: 
                try: supabase.table('registrations').insert(data).execute()
                except: pass
            flash('Success!', 'success')
        except:
            db.session.rollback()
            return render_template('503.html', error="USB Busy."), 503
        finally: db.session.close()
    return redirect(url_for('index') + '#register')

@app.route('/api/events')
def api_events():
    try:
        evts = GalleryEvent.query.all()
        return jsonify([{"id":e.id,"title":e.title,"location":e.location,"fee":e.fee,"image_url":e.image_url,"description":e.description} for e in evts])
    finally: db.session.close()

@app.route('/admin')
def admin_root():
    return redirect(url_for('admin_dashboard')) if session.get('is_admin') else redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('email') in [ADMIN_EMAIL, 'admin@wowman.com']:
            session['is_admin'] = True; return redirect(url_for('admin_dashboard'))
        flash('Denied.', 'error')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'): return redirect(url_for('admin_login'))
    try:
        return render_template('admin_dashboard.html', data={"registrations":UserRegistration.query.all(), "events":GalleryEvent.query.all()})
    finally: db.session.close()

@app.route('/admin/download/csv/<term>')
def download_csv(term):
    if not session.get('is_admin'): return redirect(url_for('home'))
    try:
        q = UserRegistration.query
        if term != 'all': q = q.filter_by(term_id=term)
        si = StringIO(); cw = csv.writer(si)
        cw.writerow(['ID', 'Name', 'Category', 'Activity', 'Phone', 'M-Pesa'])
        for r in q.all(): cw.writerow([r.id, r.name, r.category, r.activity, r.phone, r.mpesa])
        return Response(si.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=data_{term}.csv"})
    finally: db.session.close()

@app.route('/admin/gallery/add', methods=['POST'])
def add_event():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 403
    d = {k: request.form.get(k) for k in ['title','location','fee','image_url','description']}
    if all(d.values()):
        try:
            db.session.add(GalleryEvent(**d)); db.session.commit()
            flash('Event added.', 'success')
        except: db.session.rollback()
        finally: db.session.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/registration/<int:reg_id>')
def delete_registration(reg_id):
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 403
    try:
        r = UserRegistration.query.get(reg_id)
        if r: db.session.delete(r); db.session.commit()
    finally: db.session.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/event/<int:event_id>')
def delete_event(event_id):
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 403
    try:
        e = GalleryEvent.query.get(event_id)
        if e: db.session.delete(e); db.session.commit()
    finally: db.session.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def logout(): session.pop('is_admin', None); return redirect(url_for('admin_login'))

if __name__ == '__main__':
    # CRITICAL: use_reloader=False stops the CPU from thrashing on the USB library folder.
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
