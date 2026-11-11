"""HTTP/session concerns shared by controllers, outside application services."""
import secrets
import sqlite3
import time
from functools import wraps

from flask import g, jsonify, request, session
from werkzeug.exceptions import HTTPException

from backend.application.account_service import get_session_user
from backend.data_infrastructure.database.connection import get_db
from backend.shared.validation import Problem, require


def body():
    data=request.get_json(silent=True)
    require(isinstance(data,dict),'Nội dung cần là JSON object.')
    return data


def owner():
    return f'u:{g.user["id"]}' if g.user else f'g:{session["guest"]}'


def respond(result):
    if isinstance(result,tuple):
        payload,status=result
        return jsonify(payload),status
    return jsonify(result)


def protected(*roles):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            require(g.user is not None,'Vui lòng đăng nhập.',401)
            require(not roles or g.user['role'] in roles or g.user['role']=='admin','Bạn không có quyền thao tác.',403)
            return fn(*args,**kwargs)
        return wrapped
    return decorate


def register_http(app):
    attempts={}

    @app.teardown_appcontext
    def close_db(error):
        db=g.pop('db',None)
        if db:
            db.close()

    @app.before_request
    def security():
        if not request.path.startswith('/api/'):
            return
        session.setdefault('guest',secrets.token_hex(24))
        session.setdefault('csrf',secrets.token_hex(24))
        g.user=get_session_user(session.get('user_id'),session.get('auth_token'))
        if not g.user:
            session.pop('user_id',None)
        if request.method not in ('GET','HEAD','OPTIONS'):
            require(secrets.compare_digest(request.headers.get('X-CSRF-Token',''),session['csrf']),'Phiên thao tác hết hạn. Tải lại trang.',403)
        if request.path in ['/api/auth/login','/api/auth/recovery'] and request.method=='POST' and not app.testing:
            key=(request.remote_addr,request.path)
            recent=[t for t in attempts.get(key,[]) if time.time()-t<60]
            require(len(recent)<10,'Thử lại sau một phút.',429)
            attempts[key]=recent+[time.time()]

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        if request.path.startswith('/api/'):
            response.headers['Cache-Control']='no-store'
        return response

    @app.errorhandler(Problem)
    @app.errorhandler(HTTPException)
    def http_error(error):
        get_db().rollback()
        return jsonify(error=error.description,code=error.code),error.code

    @app.errorhandler(sqlite3.IntegrityError)
    def integrity_error(error):
        get_db().rollback()
        return jsonify(error='Dữ liệu trùng hoặc vi phạm ràng buộc.',code=409),409
