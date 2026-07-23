from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.subscription import Subscription
from tests.conftest import get_csrf_token


def _register_user(app, db, email='user@shipter.com', password='password123', tier='trial'):
    with app.app_context():
        user = User.create_with_trial(email=email, password=password, name='Test User')
        user.email_verified = True
        user.tier = tier
        db.session.add(user)
        db.session.commit()
        return user.id


def _login(client, email, password):
    r = client.get('/auth/login')
    csrf = get_csrf_token(r.get_data(as_text=True))
    return client.post('/auth/login', data={'csrf_token': csrf, 'email': email, 'password': password})


def test_anonymous_landing_shows_marketing_page(client):
    r = client.get('/')
    assert r.status_code == 200
    assert 'Начать бесплатно' in r.get_data(as_text=True)


def test_logged_in_root_redirects_to_dashboard(app, db, client):
    """Regression test: '/' used to be permanently shadowed by the public
    blueprint, making the dashboard unreachable for every logged-in user."""
    user_id = _register_user(app, db)
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

    r = client.get('/', follow_redirects=False)
    assert r.status_code == 302
    assert '/dashboard' in r.headers['Location']

    r = client.get('/', follow_redirects=True)
    html = r.get_data(as_text=True)
    assert 'Проекты' in html


def test_register_login_logout_flow(client):
    r = client.get('/auth/register')
    csrf = get_csrf_token(r.get_data(as_text=True))
    r = client.post('/auth/register', data={
        'csrf_token': csrf, 'email': 'newuser@shipter.com', 'password': 'password123', 'name': 'New',
    }, follow_redirects=True)
    assert r.status_code == 200

    user = User.query.filter_by(email='newuser@shipter.com').first()
    assert user is not None
    assert user.password_hash is not None

    # not verified yet -> login should be refused
    r = _login(client, 'newuser@shipter.com', 'password123')
    assert 'Пожалуйста, подтвердите email' in r.get_data(as_text=True)

    user.email_verified = True
    from app.extensions import db as _db
    _db.session.commit()

    r = _login(client, 'newuser@shipter.com', 'password123')
    assert r.status_code == 302

    r = client.get('/auth/logout', follow_redirects=True)
    assert r.status_code == 200


def test_password_reset_flow(app, db, client):
    user_id = _register_user(app, db, email='reset@shipter.com')

    r = client.get('/auth/forgot-password')
    csrf = get_csrf_token(r.get_data(as_text=True))
    r = client.post('/auth/forgot-password', data={'csrf_token': csrf, 'email': 'reset@shipter.com'}, follow_redirects=True)
    assert r.status_code == 200

    with app.app_context():
        user = User.query.get(user_id)
        assert user.reset_token is not None
        token = user.reset_token

    r = client.get(f'/auth/reset-password/{token}')
    assert r.status_code == 200
    csrf2 = get_csrf_token(r.get_data(as_text=True))

    r = client.post(f'/auth/reset-password/{token}', data={'csrf_token': csrf2, 'password': 'newpassword456'}, follow_redirects=True)
    assert r.status_code == 200

    with app.app_context():
        user = User.query.get(user_id)
        assert user.reset_token is None
        assert user.check_password('newpassword456')
        assert not user.check_password('password123')

    # invalid/expired token must not work
    r = client.get('/auth/reset-password/not-a-real-token', follow_redirects=True)
    assert 'недействительна' in r.get_data(as_text=True)


def test_login_rate_limit_blocks_after_threshold(app, db, client):
    _register_user(app, db, email='bruteforce@shipter.com')

    for _ in range(10):
        r = client.get('/auth/login')
        csrf = get_csrf_token(r.get_data(as_text=True))
        r = client.post('/auth/login', data={'csrf_token': csrf, 'email': 'bruteforce@shipter.com', 'password': 'wrong'})
        assert r.status_code == 200

    r = client.get('/auth/login')
    csrf = get_csrf_token(r.get_data(as_text=True))
    r = client.post('/auth/login', data={'csrf_token': csrf, 'email': 'bruteforce@shipter.com', 'password': 'wrong'})
    assert r.status_code == 429


def test_payment_grace_period_keeps_access_then_final_cancel(app, db):
    from types import SimpleNamespace
    from app.services import payment_service

    with app.app_context():
        user_id = _register_user(app, db, email='pastdue@shipter.com', tier='starter')
        user = User.query.get(user_id)

        sub = Subscription(
            user_id=user.id, stripe_subscription_id='sub_ci_test', tier='starter', status='active',
            current_period_end=datetime.now(timezone.utc) + timedelta(days=15),
        )
        db.session.add(sub)
        db.session.commit()

        assert user.is_active() is True

        payment_service._mark_past_due(SimpleNamespace(subscription='sub_ci_test'))
        db.session.refresh(sub)
        db.session.refresh(user)
        assert sub.status == 'past_due'
        assert user.is_active() is True  # grace period: still has access

        status = payment_service.get_subscription_status(user)
        assert status['active'] is True
        assert status['past_due'] is True

        payment_service._cancel_subscription(SimpleNamespace(id='sub_ci_test'))
        db.session.refresh(sub)
        db.session.refresh(user)
        assert user.tier == 'expired'
        assert user.is_active() is False


def test_resend_verification_unblocks_locked_out_user(app, db, client):
    """Regression test: without this, a failed/lost verification email
    permanently locks a new user out with no recourse."""
    user_id = _register_user(app, db, email='unverified@shipter.com')
    with app.app_context():
        user = User.query.get(user_id)
        user.email_verified = False
        import secrets as _secrets
        user.email_verify_token = _secrets.token_urlsafe(32)
        db.session.commit()

    r = _login(client, 'unverified@shipter.com', 'password123')
    assert 'подтвердите email' in r.get_data(as_text=True)

    r = client.get('/auth/resend-verification')
    assert r.status_code == 200
    csrf = get_csrf_token(r.get_data(as_text=True))
    r = client.post('/auth/resend-verification', data={'csrf_token': csrf, 'email': 'unverified@shipter.com'}, follow_redirects=True)
    assert r.status_code == 200

    with app.app_context():
        user = User.query.get(user_id)
        token = user.email_verify_token
        assert token is not None

    r = client.get(f'/auth/verify/{token}', follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        assert User.query.get(user_id).email_verified is True

    r = _login(client, 'unverified@shipter.com', 'password123')
    assert r.status_code == 302


def test_settings_export_and_account_deletion(app, db, client):
    user_id = _register_user(app, db, email='deleteme@shipter.com')
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

    r = client.get('/settings/export')
    assert r.status_code == 200
    assert r.content_type == 'application/json'

    r = client.get('/settings')
    csrf = get_csrf_token(r.get_data(as_text=True))

    # wrong confirmation email must not delete the account
    r = client.post('/settings/delete', data={'csrf_token': csrf, 'confirm_email': 'wrong@example.com'})
    with app.app_context():
        assert User.query.get(user_id) is not None

    r = client.post('/settings/delete', data={'csrf_token': csrf, 'confirm_email': 'deleteme@shipter.com'})
    with app.app_context():
        assert User.query.get(user_id) is None
