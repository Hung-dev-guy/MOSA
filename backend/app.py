"""Composition root: configure infrastructure and register Presentation controllers."""
import os
import secrets

from flask import Flask

from backend.data_infrastructure.database.connection import init_db, is_postgres
from backend.presentation.http import register_http
from backend.presentation.controllers import (
    account_controller, administration_controller, cart_controller,
    order_controller, product_controller, search_controller,
)
from backend.presentation.web import bp as web
from backend.shared.paths import PROJECT_ROOT


def create_app(config=None):
    app=Flask(__name__,static_folder=None)
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
        DATABASE=os.environ.get('DATABASE_URL') or os.environ.get('DATABASE',str(PROJECT_ROOT/'instance/mosa.sqlite')),
        DEMO_MODE=os.environ.get('DEMO_MODE','1')=='1',
        MAX_CONTENT_LENGTH=5*1024*1024+65536,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE')=='1',
    )
    app.config.update(config or {})
    from pathlib import Path
    media_root = PROJECT_ROOT/'instance' if is_postgres(app.config['DATABASE']) else Path(app.config['DATABASE']).parent
    app.config.setdefault('QUERY_MEDIA_DIRECTORY', os.environ.get('QUERY_MEDIA_DIRECTORY', str(media_root/'query-media')))
    init_db(app.config['DATABASE'],app.config['DEMO_MODE'])
    register_http(app)
    for controller in (
        account_controller, product_controller, search_controller,
        cart_controller, order_controller, administration_controller,
    ):
        app.register_blueprint(controller.bp)
    app.register_blueprint(web)
    return app
