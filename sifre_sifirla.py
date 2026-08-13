import sqlite3
# pyrefly: ignore [missing-import]
from werkzeug.security import generate_password_hash
import sys

DB_PATH = 'berber.db'

def reset_admin_password():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get the first admin user
        c.execute("SELECT id, username, name FROM user WHERE role='admin' LIMIT 1")
        admin = c.fetchone()
        
        if not admin:
            print("Sistemde kayitli admin (Usta) bulunamadi.")
            return
            
        print(f"--- SIFRE SIFIRLAMA ---")
        print(f"Bulunan Usta: {admin[2]} (Kullanici Adi: {admin[1]})")
        
        # Check if Python is running interactively
        new_password = input("Yeni sifrenizi girin: ")
        
        if not new_password.strip():
            print("Sifre bos olamaz. Islem iptal edildi.")
            return
            
        hashed = generate_password_hash(new_password)
        c.execute("UPDATE user SET password_hash = ? WHERE id = ?", (hashed, admin[0]))
        conn.commit()
        conn.close()
        print("\nBasarili! Sifre degistirildi. Artik yeni sifrenizle web panelinden giris yapabilirsiniz.")
    except Exception as e:
        print(f"Bir hata olustu: {e}")

if __name__ == '__main__':
    reset_admin_password()
