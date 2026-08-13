import os
# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
# pyrefly: ignore [missing-import]
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from models import init_db, get_db


def auto_cancel_overdue_appointments(grace_minutes=5):
    """Saati 5+ dakika geçmiş 'pending' randevuları otomatik olarak iptal eder."""
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    cutoff = now - timedelta(minutes=grace_minutes)
    cutoff_time_str = cutoff.strftime('%H:%M')

    conn = get_db()
    # Bugünün pending randevularını al
    pending = conn.execute(
        "SELECT id, time FROM appointment WHERE date = ? AND status = 'pending'",
        (today_str,)
    ).fetchall()

    cancelled_ids = []
    for appt in pending:
        # Randevu saatini karşılaştır
        try:
            appt_time = datetime.strptime(f"{today_str} {appt['time']}", '%Y-%m-%d %H:%M')
        except ValueError:
            continue
        # Şu andan 5 dakika+ önce ise iptal et
        if appt_time <= (now - timedelta(minutes=grace_minutes)):
            conn.execute("UPDATE appointment SET status = 'cancelled' WHERE id = ?", (appt['id'],))
            cancelled_ids.append(appt['id'])

    if cancelled_ids:
        conn.commit()
    conn.close()
    return len(cancelled_ids)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gizli_anahtar_degistir_sonra'
# Upload folder for profile photos
UPLOAD_FOLDER = os.path.join('static', 'images', 'profiles')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

init_db()

# --- Middleware ---
@app.before_request
def check_first_user():
    # If no users exist and not on a static/setup route, redirect to setup
    if not request.path.startswith('/static'):
        conn = get_db()
        user_count = conn.execute('SELECT COUNT(*) FROM user').fetchone()[0]
        conn.close()
        if user_count == 0 and request.path != '/setup':
            return redirect(url_for('setup'))

# --- SETUP (First Time Only) ---
@app.route('/setup', methods=['GET', 'POST'])
def setup():
    conn = get_db()
    if conn.execute('SELECT COUNT(*) FROM user').fetchone()[0] > 0:
        conn.close()
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        
        hashed_pw = generate_password_hash(password)
        conn.execute('INSERT INTO user (username, password_hash, name, role) VALUES (?, ?, ?, ?)',
                     (username, hashed_pw, name, 'admin'))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
        
    conn.close()
    return render_template('setup.html')

# --- CUSTOMER FACING ROUTES ---
@app.route('/')
def index():
    conn = get_db()
    barbers = conn.execute('SELECT * FROM user WHERE is_active = 1').fetchall()
    settings = conn.execute('SELECT * FROM settings LIMIT 1').fetchone()
    conn.close()
    return render_template('index.html', barbers=barbers, settings=settings)

@app.route('/fiyat-listesi')
def fiyat_listesi():
    return render_template('fiyat_listesi.html')

@app.route('/barber/<int:barber_id>')

def barber_calendar(barber_id):
    conn = get_db()
    barber = conn.execute('SELECT * FROM user WHERE id = ?', (barber_id,)).fetchone()
    conn.close()
    if not barber:
        return "Berber bulunamadı", 404
    return render_template('calendar.html', barber=barber)

@app.route('/api/availability')
def api_availability():
    barber_id = request.args.get('barber_id')
    date_str = request.args.get('date') # YYYY-MM-DD
    
    if not barber_id or not date_str:
        return jsonify({'error': 'Missing parameters'}), 400
        
    conn = get_db()
    settings = conn.execute('SELECT * FROM settings LIMIT 1').fetchone()
    
    # Check if closed day
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    weekday = str(date_obj.weekday())
    closed_days = settings['closed_days'].split(',') if settings['closed_days'] else []
    
    if weekday in closed_days:
        conn.close()
        return jsonify({'available_slots': [], 'past_slots': []}) # Closed
        
    # Generate all slots
    open_t = datetime.strptime(settings['shop_open_time'], '%H:%M')
    close_t = datetime.strptime(settings['shop_close_time'], '%H:%M')
    
    slots = []
    curr = open_t
    while curr < close_t:
        slots.append(curr.strftime('%H:%M'))
        curr += timedelta(minutes=settings['slot_duration'])
        
    # Get booked appointments and blocked times
    appointments = conn.execute("SELECT time FROM appointment WHERE barber_id = ? AND date = ? AND status != 'cancelled'", (barber_id, date_str)).fetchall()
    booked = [appt['time'] for appt in appointments]
    
    blocked = conn.execute("SELECT time FROM blocked_time WHERE barber_id = ? AND date = ?", (barber_id, date_str)).fetchall()
    blocked_times = [b['time'] for b in blocked]
    
    # If today, separate past slots (already passed + 5 min grace) from available
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    past_slots = []

    if date_str == today_str:
        # Slots in the past (slot time + slot_duration <= now) are blocked for new bookings
        available = []
        for s in slots:
            slot_dt = datetime.strptime(f"{date_str} {s}", '%Y-%m-%d %H:%M')
            if slot_dt <= now:
                # Past slot — show as past (crossed out), not available to book
                past_slots.append(s)
            elif s not in booked and s not in blocked_times:
                available.append(s)
    else:
        available = [s for s in slots if s not in booked and s not in blocked_times]

    conn.close()
    
    return jsonify({'available_slots': available, 'past_slots': past_slots})


@app.route('/api/book', methods=['POST'])
def api_book():
    data = request.json
    barber_id = data.get('barber_id')
    name = data.get('name')
    phone = data.get('phone')
    service = data.get('service')
    date = data.get('date')
    time = data.get('time')
    
    # Geçmiş saate randevu alınmasını engelle (backend güvenlik)
    try:
        slot_dt = datetime.strptime(f"{date} {time}", '%Y-%m-%d %H:%M')
        if slot_dt <= datetime.now():
            return jsonify({'error': 'Geçmiş bir saate randevu alınamaz. Lütfen ileriki bir saat seçin.'}), 400
    except ValueError:
        return jsonify({'error': 'Geçersiz tarih veya saat formatı.'}), 400

    conn = get_db()
    # Verify slot is still empty
    existing = conn.execute("SELECT id FROM appointment WHERE barber_id = ? AND date = ? AND time = ? AND status != 'cancelled'", (barber_id, date, time)).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'Bu saat doludur, lütfen başka bir saat seçin.'}), 400
        
    blocked = conn.execute("SELECT id FROM blocked_time WHERE barber_id = ? AND date = ? AND time = ?", (barber_id, date, time)).fetchone()
    if blocked:
        conn.close()
        return jsonify({'error': 'Bu saat müsait değildir.'}), 400
        
    conn.execute('''
        INSERT INTO appointment (barber_id, customer_name, customer_phone, service_type, date, time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (barber_id, name, phone, service, date, time))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Randevu başarıyla alındı.'})


# --- AUTH ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db()
        user = conn.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        flash('Geçersiz kullanıcı adı veya şifre', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- DASHBOARD ROUTES ---
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Saati geçmiş randevuları otomatik iptal et
    auto_cancel_overdue_appointments(grace_minutes=5)

    conn = get_db()
    user = conn.execute('SELECT * FROM user WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Get today's appointments
    today = datetime.now().strftime('%Y-%m-%d')
    appointments = conn.execute('SELECT * FROM appointment WHERE barber_id = ? AND date = ? ORDER BY time ASC', (user['id'], today)).fetchall()
    conn.close()
    
    return render_template('dashboard.html', user=user, appointments=appointments)


@app.route('/api/auto-cancel', methods=['POST'])
def api_auto_cancel():
    """Frontend'den periyodik olarak çağrılabilir — sayfayı yenilemeden iptal işlemi yapar."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    count = auto_cancel_overdue_appointments(grace_minutes=5)
    return jsonify({'success': True, 'cancelled_count': count})

@app.route('/dashboard/cancel/<int:appt_id>', methods=['POST'])
def cancel_appointment(appt_id):
    if 'user_id' not in session:
        return jsonify({'success': False})
    user_id = session['user_id']
    role = session.get('role')
    
    conn = get_db()
    appt = conn.execute('SELECT * FROM appointment WHERE id = ?', (appt_id,)).fetchone()
    if appt and (appt['barber_id'] == user_id or role == 'admin'):
        conn.execute("UPDATE appointment SET status = 'cancelled' WHERE id = ?", (appt_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
        
    conn.close()
    return jsonify({'success': False})

@app.route('/dashboard/employees', methods=['GET', 'POST'])
def manage_employees():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
        
    conn = get_db()
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        
        existing = conn.execute('SELECT id FROM user WHERE username = ?', (username,)).fetchone()
        if existing:
            flash('Kullanıcı adı zaten var.', 'danger')
        else:
            hashed_pw = generate_password_hash(password)
            conn.execute('INSERT INTO user (username, password_hash, name, role) VALUES (?, ?, ?, ?)',
                         (username, hashed_pw, name, 'employee'))
            conn.commit()
            flash('Çalışan başarıyla eklendi.', 'success')
            
    employees = conn.execute("SELECT * FROM user WHERE role = 'employee'").fetchall()
    conn.close()
    return render_template('employees.html', employees=employees)


@app.route('/dashboard/employees/delete/<int:emp_id>', methods=['POST'])
def delete_employee(emp_id):
    """Çalışanı sistemden kalıcı olarak siler. Sadece admin erişebilir."""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Yetkisiz erişim.'}), 403

    conn = get_db()
    emp = conn.execute("SELECT * FROM user WHERE id = ? AND role = 'employee'", (emp_id,)).fetchone()
    if not emp:
        conn.close()
        return jsonify({'success': False, 'error': 'Çalışan bulunamadı.'}), 404

    # Çalışana ait bekleyen/onaylı randevuları iptal et
    conn.execute("UPDATE appointment SET status = 'cancelled' WHERE barber_id = ? AND status IN ('pending', 'confirmed')", (emp_id,))
    # Çalışanı sil
    conn.execute("DELETE FROM user WHERE id = ?", (emp_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/dashboard/settings', methods=['GET', 'POST'])
def manage_settings():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
        
    conn = get_db()
    if request.method == 'POST':
        open_time   = request.form.get('open_time')
        close_time  = request.form.get('close_time')
        days        = request.form.getlist('closed_days')
        closed_days_str = ','.join(days)
        shop_name   = request.form.get('shop_name', '').strip()
        shop_address= request.form.get('shop_address', '').strip()
        shop_phone  = request.form.get('shop_phone', '').strip()

        conn.execute(
            '''UPDATE settings
               SET shop_open_time=?, shop_close_time=?, closed_days=?,
                   shop_name=?, shop_address=?, shop_phone=?
               WHERE id = (SELECT id FROM settings LIMIT 1)''',
            (open_time, close_time, closed_days_str, shop_name, shop_address, shop_phone)
        )
        conn.commit()
        flash('Ayarlar güncellendi.', 'success')

    settings = conn.execute('SELECT * FROM settings LIMIT 1').fetchone()
    conn.close()
    return render_template('settings.html', settings=settings)

@app.route('/dashboard/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    user_id = session['user_id']
    
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        password = request.form.get('password')
        
        update_query = 'UPDATE user SET username = ?, name = ?'
        params = [username, name]
        
        if password:
            update_query += ', password_hash = ?'
            params.append(generate_password_hash(password))
            
        photo = request.files.get('photo')
        if photo and photo.filename:
            filename = f"user_{user_id}_{photo.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(filepath)
            update_query += ', profile_photo = ?'
            params.append(filename)
            
        update_query += ' WHERE id = ?'
        params.append(user_id)
        
        conn.execute(update_query, tuple(params))
        conn.commit()
        flash('Profil güncellendi.', 'success')
        
    user = conn.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return render_template('profile.html', user=user)

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)
