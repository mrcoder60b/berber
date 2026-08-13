from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User.query.filter_by(role='admin').first()
    if admin:
        admin.password_hash = generate_password_hash('B60!nes')
        db.session.commit()
        print('Sifre basariyla B60!nes olarak degistirildi. Kullanici:', admin.username)
    else:
        print('Sistemde admin yetkisine sahip bir kullanici bulunamadi.')
