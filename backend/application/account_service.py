from .audit_service import audit
from backend.data_infrastructure.database.connection import get_db, now
from backend.data_infrastructure.database.connection import one
from backend.data_infrastructure.database.connection import rows
from backend.shared.validation import boolean
from backend.shared.validation import require
from backend.shared.validation import text
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
import hashlib
import re
import secrets
import time


def public_user(user):
    return {k: user[k] for k in ['id', 'name', 'email', 'phone', 'role', 'active']}


def get_session_user(user_id, token):
    if not isinstance(token, str):
        return None
    return one('SELECT u.* FROM users u JOIN auth_sessions a ON a.user_id=u.id WHERE u.id=? AND u.active=1 AND a.token_hash=?', (user_id, hashlib.sha256(token.encode()).hexdigest()))


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    get_db().execute('INSERT INTO auth_sessions VALUES(?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), user_id, now()))
    return token


def logout(token):
    if isinstance(token, str):
        get_db().execute('DELETE FROM auth_sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))
        get_db().commit()


def login(user, guest_owner):
    from .cart_service import merge_guest_cart
    merge_guest_cart(guest_owner, user['id'])
    token = create_session(user['id'])
    get_db().commit()
    return {'user': public_user(user), 'auth_token': token}


def register(*, data, guest_owner):
    d = data
    name = text(d.get('name'), 'Tên', 2, 100)
    email = text(d.get('email'), 'Email', 5, 254).lower()
    require(re.fullmatch('[^\\s@]+@[^\\s@]+\\.[^\\s@]+', email), 'Email không hợp lệ.')
    password = text(d.get('password'), 'Mật khẩu', 10, 128)
    require(not one('SELECT id FROM users WHERE email=?', (email,)), 'Email đã được sử dụng.', 409)
    cur = get_db().execute('INSERT INTO users(name,email,password) VALUES(?,?,?) RETURNING id', (name, email, generate_password_hash(password)))
    return (login(one('SELECT * FROM users WHERE id=?', (cur.fetchone()['id'],)), guest_owner=guest_owner), 201)


def sign_in(*, data, guest_owner):
    d = data
    email = text(d.get('email'), 'Email', 3, 254).lower()
    password = text(d.get('password'), 'Mật khẩu', 1, 128)
    user = one('SELECT * FROM users WHERE email=?', (email,))
    require(user and user['active'] and check_password_hash(user['password'], password), 'Email hoặc mật khẩu không đúng.', 401)
    return login(user, guest_owner=guest_owner)


def account(*, data, user):
    d = data
    name = text(d.get('name'), 'Tên', 2, 100)
    phone = text(d.get('phone', ''), 'Điện thoại', 0, 20)
    email = text(d.get('email', user['email']), 'Email', 5, 254).lower()
    require(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email), 'Email không hợp lệ.')
    get_db().execute('UPDATE users SET name=?,email=?,phone=? WHERE id=?', (name, email, phone, user['id']))
    get_db().commit()
    return {'user': public_user(one('SELECT * FROM users WHERE id=?', (user['id'],)))}


def change_password(*, data, user):
    d = data
    require(check_password_hash(user['password'], text(d.get('current_password'), 'Mật khẩu hiện tại', 1, 128)), 'Mật khẩu hiện tại không đúng.', 403)
    password = text(d.get('password'), 'Mật khẩu mới', 10, 128)
    db = get_db()
    db.execute('UPDATE users SET password=? WHERE id=?', (generate_password_hash(password), user['id']))
    db.execute('DELETE FROM reset_tokens WHERE user_id=?', (user['id'],))
    db.execute('DELETE FROM auth_sessions WHERE user_id=?', (user['id'],))
    token = create_session(user['id'])
    db.commit()
    return {'ok': True, 'auth_token': token}


def recovery(*, data, config):
    email = text(data.get('email'), 'Email', 3, 254).lower()
    u = one('SELECT id FROM users WHERE email=? AND active=1', (email,))
    result = {'message': 'Nếu tài khoản hợp lệ, yêu cầu khôi phục đã được ghi nhận.'}
    if u:
        token = secrets.token_urlsafe(32)
        db = get_db()
        db.execute('DELETE FROM reset_tokens WHERE user_id=?', (u['id'],))
        db.execute('INSERT INTO reset_tokens VALUES(?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), u['id'], time.time() + 900))
        db.commit()
        if config['DEMO_MODE']:
            result['demo_reset_url'] = '/reset?token=' + token
    return result


def reset(*, data):
    d = data
    token = text(d.get('token'), 'Token', 20, 200)
    password = text(d.get('password'), 'Mật khẩu', 10, 128)
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    r = one('SELECT * FROM reset_tokens WHERE token=?', (hashlib.sha256(token.encode()).hexdigest(),))
    require(r and r['expires'] > time.time(), 'Link khôi phục hết hạn hoặc đã sử dụng.', 400)
    db.execute('UPDATE users SET password=? WHERE id=?', (generate_password_hash(password), r['user_id']))
    db.execute('DELETE FROM reset_tokens WHERE user_id=?', (r['user_id'],))
    db.execute('DELETE FROM auth_sessions WHERE user_id=?', (r['user_id'],))
    db.commit()
    return {'ok': True}


def customer_status(uid, *, data, user):
    require(one("SELECT id FROM users WHERE id=? AND role='customer'", (uid,)), 'Không có khách hàng.', 404)
    active = boolean(data.get('active'), 'Trạng thái')
    db = get_db()
    db.execute('UPDATE users SET active=? WHERE id=?', (active, uid))
    db.execute('DELETE FROM auth_sessions WHERE user_id=?', (uid,))
    audit(user['id'], 'customer.status', uid)
    db.commit()
    return {'ok': True}
