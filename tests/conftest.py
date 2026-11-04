import pytest
from backend.app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({'TESTING':True,'DATABASE':str(tmp_path/'test.sqlite'),'SECRET_KEY':'testing'})


@pytest.fixture
def client(app):
    return app.test_client()


def call(c,method,path,data=None,headers=None,**kwargs):
    token=c.get('/api/session').json['csrf_token']
    return c.open('/api'+path,method=method,json=data,headers={'X-CSRF-Token':token,**(headers or {})},**kwargs)


def sign_in(c,role='customer'):
    r=call(c,'POST','/auth/login',{'email':role+'@mosa.local','password':'Mosa@12345'})
    assert r.status_code==200,r.json
    return r.json
