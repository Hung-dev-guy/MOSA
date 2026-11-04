from flask import current_app, g, jsonify, session
from ..http import body, protected, respond
from backend.application.account_service import public_user
from backend.application import account_service
from flask import Blueprint
bp = Blueprint('account_controller', __name__)
import secrets



def finish_login(result):
    status=200
    if isinstance(result,tuple):
        result,status=result
    session.update(user_id=result['user']['id'],version=result.pop('session_version'),csrf=secrets.token_hex(24))
    result['csrf_token']=session['csrf']
    return jsonify(result),status



@bp.get('/api/session')
def bootstrap():
    return jsonify(user=public_user(g.user) if g.user else None, csrf_token=session['csrf'], demo=current_app.config['DEMO_MODE'])


@bp.post('/api/auth/register')
def register():
    result = account_service.register(data=body(), guest_owner=f"g:{session['guest']}")
    return finish_login(result)


@bp.post('/api/auth/login')
def sign_in():
    result = account_service.sign_in(data=body(), guest_owner=f"g:{session['guest']}")
    return finish_login(result)


@bp.post('/api/auth/logout')
def logout():
    session.clear()
    return jsonify(ok=True)


@bp.patch('/api/account')
@protected()
def account():
    return respond(account_service.account(data=body(), user=g.user))


@bp.post('/api/account/password')
@protected()
def change_password():
    result = account_service.change_password(data=body(), user=g.user)
    session['version'] = g.user['session_version'] + 1
    return respond(result)


@bp.post('/api/auth/recovery')
def recovery():
    return respond(account_service.recovery(data=body(), config=current_app.config))


@bp.post('/api/auth/reset')
def reset():
    return respond(account_service.reset(data=body()))
