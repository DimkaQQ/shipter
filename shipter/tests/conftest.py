import os

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:postgres@localhost/shipter_test')
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('ENCRYPTION_KEY', 'zk78o_dVVOLQOhgBqf3SPB_P85FKuLIPRb1BPHSpXfY=')

import pytest
from app import create_app
from app.extensions import db as _db, mail, redis_client


@pytest.fixture()
def app():
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
    mail.send = lambda msg: None  # никогда не стучимся в реальный SMTP из тестов

    with application.app_context():
        _db.drop_all()
        _db.create_all()
        try:
            redis_client.flushdb()
        except Exception:
            pass
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


def get_csrf_token(html: str) -> str:
    import re
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "csrf_token not found in response HTML"
    return match.group(1)
