# Senior Review: Clean Structure & Lint Fix (frontend/backend)
from flask import Flask, request, jsonify, render_template, Response
import csv, io, os, json, random, sys
from datetime import datetime

# 1. Portable Library Path (Now within backend/)
lib_path = os.path.join(os.path.dirname(__file__), '.lib_v3')
if os.path.exists(lib_path):
    sys.path.insert(0, lib_path)

# Path-Aware Flask App (Points to ../frontend/)
app = Flask(__name__, 
            template_folder='../frontend/templates', 
            static_folder='../frontend/static')

# Global State (Hardware Optimized for Intel Celeron: Moved to separate vars to assist type inference)
QUOTE = "Empowering journeys, enriching lives. Welcome to The Wow'Man."
BUS_PULSE_ACTIVE = True
BOOKINGS = [
    {'id': 1, 'type': 'event', 'name': 'Alice Smith', 'is_chama': True, 'details': 'Women empowerment seminar', 'date': '2026-03-20'},
    {'id': 2, 'type': 'transport', 'name': 'Bob Jones', 'school': 'Nairobi Primary', 'grade': 'Grade 4', 'date': '2026-03-21'}
]

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return render_template('index.html')

@app.route('/api/quote', methods=['GET'])
def get_quote():
    return jsonify({'quote': QUOTE})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({'bus_pulse_active': BUS_PULSE_ACTIVE})

@app.route('/api/status', methods=['POST'])
def update_status():
    global BUS_PULSE_ACTIVE
    data = request.json or {}
    if 'bus_pulse_active' in data:
        BUS_PULSE_ACTIVE = bool(data['bus_pulse_active'])
        return jsonify({'success': True, 'bus_pulse_active': BUS_PULSE_ACTIVE})
    return jsonify({'error': 'Invalid request'}), 400

@app.route('/api/book', methods=['POST'])
def create_booking():
    data = request.json or {}
    booking = {
        'id': len(BOOKINGS) + 1,
        'type': data.get('type', 'general'),
        'timestamp': datetime.now().isoformat()
    }
    booking.update(data)
    BOOKINGS.append(booking)
    return jsonify({'success': True, 'booking_id': booking['id']})

@app.route('/api/export', methods=['GET'])
def export_csv():
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(['ID', 'Type', 'Name', 'Date/Timestamp', 'Details', 'Is Chama', 'School', 'Grade'])
    for b in BOOKINGS:
        writer.writerow([
            b.get('id', ''), b.get('type', ''), b.get('name', ''),
            b.get('date', b.get('timestamp', '')), b.get('details', ''),
            'Yes' if b.get('is_chama') else ('No' if b.get('is_chama') is False else ''),
            b.get('school', ''), b.get('grade', '')
        ])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=master_bookings.csv"})

@app.route('/api/term_progress', methods=['GET'])
def term_progress():
    start_date = datetime(2026, 1, 12); end_date = datetime(2026, 4, 10); now = datetime(2026, 3, 17)
    total_days = max(1, (end_date - start_date).days)
    elapsed_days = (now - start_date).days
    progress = max(0.0, min(100.0, (float(elapsed_days) / float(total_days)) * 100.0))
    return jsonify({
        'term': 'Term 1, 2026',
        'progress_percent': round(progress, 1),
        'weeks_elapsed': elapsed_days // 7,
        'total_weeks': total_days // 7
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
