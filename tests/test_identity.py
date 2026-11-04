import time
from conftest import call,sign_in
from backend.data_infrastructure.database.connection import get_db


def test_register_login_duplicate_and_csrf(client):
    assert client.post('/api/auth/register',json={}).status_code==403
    d={'name':'Nguyễn An','email':'an@example.com','password':'Secure@12345'}
    assert call(client,'POST','/auth/register',d).status_code==201
    assert call(client,'POST','/auth/register',d).status_code==409
    assert client.get('/api/session').json['user']['name']=='Nguyễn An'
    call(client,'POST','/auth/logout',{})
    assert call(client,'POST','/auth/login',{**d,'password':'wrong'}).status_code==401
    assert call(client,'POST','/auth/login',d).status_code==200


def test_profile_and_password(client):
    sign_in(client)
    assert call(client,'PATCH','/account',{'name':'New Name','phone':'0901234567'}).json['user']['name']=='New Name'
    assert call(client,'POST','/account/password',{'current_password':'wrong','password':'NewPassword123'}).status_code==403
    assert call(client,'POST','/account/password',{'current_password':'Mosa@12345','password':'NewPassword123'}).status_code==200
    assert client.get('/api/session').json['user']


def test_recovery_single_use_and_session_revocation(app,client):
    sign_in(client)
    other=app.test_client()
    url=call(other,'POST','/auth/recovery',{'email':'customer@mosa.local'}).json['demo_reset_url']
    data={'token':url.split('token=')[1],'password':'ResetSecure123'}
    assert call(other,'POST','/auth/reset',data).status_code==200
    assert client.get('/api/session').json['user'] is None
    assert call(other,'POST','/auth/reset',data).status_code==400
    assert call(other,'POST','/auth/recovery',{'email':'absent@somewhere.com'}).json.get('demo_reset_url') is None


def test_expired_token(app,client):
    url=call(client,'POST','/auth/recovery',{'email':'customer@mosa.local'}).json['demo_reset_url']
    with app.app_context():
        get_db().execute('UPDATE reset_tokens SET expires=?',(time.time()-1,))
        get_db().commit()
    assert call(client,'POST','/auth/reset',{'token':url.split('token=')[1],'password':'ResetSecure123'}).status_code==400


def test_bad_input(client):
    for d in [{},{'name':'OK','email':'bad','password':'short'},[]]:
        assert call(client,'POST','/auth/register',d).status_code==400
