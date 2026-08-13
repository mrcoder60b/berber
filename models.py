import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'berber.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'employee',
            profile_photo TEXT DEFAULT 'default.png',
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS appointment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barber_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            service_type TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (barber_id) REFERENCES user(id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_open_time TEXT DEFAULT '09:00',
            shop_close_time TEXT DEFAULT '20:00',
            closed_days TEXT DEFAULT '6',
            slot_duration INTEGER DEFAULT 30,
            shop_name TEXT DEFAULT '',
            shop_address TEXT DEFAULT '',
            shop_phone TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS blocked_time (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barber_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            FOREIGN KEY (barber_id) REFERENCES user(id)
        );
    ''')

    # Settings tablosunda veri yoksa varsayilan ekle
    if conn.execute('SELECT COUNT(*) FROM settings').fetchone()[0] == 0:
        conn.execute("INSERT INTO settings (shop_open_time, shop_close_time, closed_days, slot_duration, shop_name, shop_address, shop_phone) VALUES ('09:00', '20:00', '6', 30, '', '', '')")
        conn.commit()

    # Mevcut DB'de yeni sütunlar yoksa ekle (migration)
    existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(settings)").fetchall()]
    for col, definition in [
        ('shop_name',    "TEXT DEFAULT ''"),
        ('shop_address', "TEXT DEFAULT ''"),
        ('shop_phone',   "TEXT DEFAULT ''"),
    ]:
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE settings ADD COLUMN {col} {definition}")
    conn.commit()

    conn.close()
