"""
Банная аналитика — приложение для маркетплейса YCLIENTS
"""

import os
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'banya-secret-2024')

PARTNER_TOKEN = os.environ.get('PARTNER_TOKEN', 'HFG35p0420g7Q2Pn0K8O')
DB_PATH = os.environ.get('DB_PATH', 'data.db')

# ──────────────────────────────────────────────
# База данных
# ──────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS salons (
            salon_id    INTEGER PRIMARY KEY,
            user_token  TEXT,
            connected_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_salon(salon_id, user_token):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        INSERT OR REPLACE INTO salons (salon_id, user_token, connected_at)
        VALUES (?, ?, ?)
    ''', (salon_id, user_token, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_salon(salon_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        'SELECT user_token FROM salons WHERE salon_id = ?', (salon_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None

def delete_salon(salon_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('DELETE FROM salons WHERE salon_id = ?', (salon_id,))
    conn.commit()
    conn.close()

# ──────────────────────────────────────────────
# YCLIENTS API
# ──────────────────────────────────────────────

def yclients_headers(user_token=None):
    auth = f'Bearer {PARTNER_TOKEN}'
    if user_token:
        auth += f', User {user_token}'
    return {
        'Content-Type': 'application/json',
        'Authorization': auth,
        'Accept': 'application/vnd.yclients.v2+json'
    }

def yclients_get(endpoint, user_token, params=None):
    try:
        url = f'https://api.yclients.com/api/v1/{endpoint}'
        r = requests.get(url, headers=yclients_headers(user_token), params=params, timeout=15)
        data = r.json()
        return data.get('data', []) if data.get('success') else []
    except Exception as e:
        print(f"YCLIENTS GET ERROR {endpoint}: {e}")
        return []

def get_user_token(login, password):
    try:
        r = requests.post(
            'https://api.yclients.com/api/v1/auth',
            headers=yclients_headers(),
            json={'login': login, 'password': password},
            timeout=20
        )
        data = r.json()
        print(f"AUTH RESPONSE: success={data.get('success')} meta={data.get('meta')}")
        if data.get('success'):
            return data['data']['user_token']
        return None
    except Exception as e:
        print(f"AUTH ERROR: {e}")
        return None

# ──────────────────────────────────────────────
# Маршруты
# ──────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/connect')
def connect():
    salon_id = request.args.get('salon_id', '773684')
    return render_template('connect.html', salon_id=salon_id)

@app.route('/activate', methods=['POST'])
def activate():
    salon_id = request.form.get('salon_id')
    login    = request.form.get('login')
    password = request.form.get('password')

    print(f"ACTIVATE: salon_id={salon_id} login={login}")

    if not all([salon_id, login, password]):
        return jsonify({'success': False, 'message': 'Заполните все поля'}), 400

    user_token = get_user_token(login, password)
    if not user_token:
        return jsonify({'success': False, 'message': 'Неверный логин или пароль YCLIENTS'}), 401

    save_salon(int(salon_id), user_token)
    print(f"SAVED salon {salon_id}")

    return jsonify({
        'success': True,
        'message': 'Подключено! Открываем дашборд...',
        'redirect': f'/dashboard/{salon_id}'
    })

@app.route('/disconnect', methods=['POST', 'GET'])
def disconnect():
    try:
        data = request.get_json(silent=True) or {}
        salon_id = data.get('salon_id') or request.form.get('salon_id') or request.args.get('salon_id')
        if salon_id:
            delete_salon(int(salon_id))
            print(f"DISCONNECTED salon {salon_id}")
    except Exception as e:
        print(f"DISCONNECT ERROR: {e}")
    return jsonify({'success': True})

@app.route('/dashboard/<int:salon_id>')
def dashboard(salon_id):
    user_token = get_salon(salon_id)
    if not user_token:
        return redirect(f'/connect?salon_id={salon_id}')
    return render_template('dashboard.html', salon_id=salon_id)

# ──────────────────────────────────────────────
# API данных для дашборда
# ──────────────────────────────────────────────

def date_range(days):
    end = datetime.now()
    start = end - timedelta(days=days)
    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')

@app.route('/api/data/<int:salon_id>')
def api_data(salon_id):
    user_token = get_salon(salon_id)
    if not user_token:
        return jsonify({'error': 'not_connected'}), 401

    days = int(request.args.get('days', 30))
    start, end = date_range(days)

    records  = yclients_get(f'records/{salon_id}', user_token,
                            {'start_date': start, 'end_date': end, 'count': 300})
    finance  = yclients_get(f'finances/transactions/{salon_id}', user_token,
                            {'start_date': start, 'end_date': end, 'count': 300})
    clients  = yclients_get(f'clients/{salon_id}', user_token, {'count': 300})
    staff    = yclients_get(f'staff/{salon_id}', user_token)

    revenue  = sum(f.get('amount', 0) for f in finance if f.get('amount', 0) > 0)
    expenses = sum(abs(f.get('amount', 0)) for f in finance if f.get('amount', 0) < 0)
    completed = [r for r in records if r.get('attendance') == 1 or r.get('status_id') == 4]
    cancelled = [r for r in records if r.get('status_id') in (3, 5, 6)]
    conv_rate = round(len(completed) / len(records) * 100) if records else 0

    month_ago   = (datetime.now() - timedelta(days=30)).isoformat()
    new_clients = [c for c in clients if (c.get('create_date') or '') > month_ago]

    by_day = {}
    for r in records:
        d = (r.get('date') or '')[:10]
        if d: by_day[d] = by_day.get(d, 0) + 1

    rev_by_day = {}
    for f in finance:
        if f.get('amount', 0) > 0:
            d = (f.get('create_date') or f.get('date') or '')[:10]
            if d: rev_by_day[d] = rev_by_day.get(d, 0) + f['amount']

    staff_load = {}
    staff_revenue = {}
    for r in records:
        name = (r.get('staff') or {}).get('name', '')
        if name:
            staff_load[name]    = staff_load.get(name, 0) + 1
            staff_revenue[name] = staff_revenue.get(name, 0) + sum(
                s.get('cost', 0) for s in (r.get('services') or []))

    svc_count, svc_rev = {}, {}
    for r in records:
        for s in (r.get('services') or []):
            t = s.get('title', '')
            if t:
                svc_count[t] = svc_count.get(t, 0) + 1
                svc_rev[t]   = svc_rev.get(t, 0) + s.get('cost', 0)

    top_services = sorted(svc_count.items(), key=lambda x: x[1], reverse=True)[:8]

    recent = sorted(records, key=lambda r: r.get('date',''), reverse=True)[:50]

    return jsonify({
        'metrics': {
            'records':     len(records),
            'revenue':     round(revenue),
            'expenses':    round(expenses),
            'profit':      round(revenue - expenses),
            'conv_rate':   conv_rate,
            'completed':   len(completed),
            'cancelled':   len(cancelled),
            'clients':     len(clients),
            'new_clients': len(new_clients),
            'staff_count': len(staff),
        },
        'by_day':        by_day,
        'rev_by_day':    rev_by_day,
        'staff_load':    sorted(staff_load.items(),    key=lambda x: x[1], reverse=True)[:10],
        'staff_revenue': sorted(staff_revenue.items(), key=lambda x: x[1], reverse=True)[:10],
        'top_services':  top_services,
        'svc_revenue':   {k: round(v) for k, v in svc_rev.items()},
        'recent_records': recent,
        'period': {'start': start, 'end': end, 'days': days},
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})

init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
