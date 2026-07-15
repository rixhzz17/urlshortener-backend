# pyrefly: ignore [missing-import]
import pytest
import json
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User, EmailVerification, PasswordReset
from app.models.url import URL

@pytest.fixture
def flask_app():
    # Use testing config
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(flask_app):
    return flask_app.test_client()

def test_auth_and_url_lifecycle(client, flask_app):
    # 1. Registration
    reg_data = {
        'first_name': 'Test',
        'last_name': 'User',
        'email': 'test@example.com',
        'password': 'SecurePassword123!',
        'confirm_password': 'SecurePassword123!'
    }
    
    response = client.post('/api/auth/register', json=reg_data)
    assert response.status_code == 201
    assert 'Registration successful' in response.json['message']

    # 2. Duplicate Registration Check
    response_dup = client.post('/api/auth/register', json=reg_data)
    assert response_dup.status_code == 409

    # 3. Direct Login (no email verification required)
    login_data = {
        'email': 'test@example.com',
        'password': 'SecurePassword123!'
    }
    response_login = client.post('/api/auth/login', json=login_data)
    assert response_login.status_code == 200
    token = response_login.json['access_token']
    assert token is not None

    # 4. Verify User is Verified by default in Database
    with flask_app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.is_verified

    headers = {'Authorization': f'Bearer {token}'}

    # 6. Create URL
    url_data = {
        'original_url': 'https://google.com',
        'custom_code': 'ggl',
        'title': 'Google Search',
        'expires_at': (datetime.utcnow() + timedelta(days=2)).isoformat()
    }
    response_url = client.post('/api/urls', json=url_data, headers=headers)
    assert response_url.status_code == 201
    assert response_url.json['short_code'] == 'ggl'
    assert response_url.json['original_url'] == 'https://google.com'

    # 7. Duplicate URL Custom Code Check
    response_url_dup = client.post('/api/urls', json=url_data, headers=headers)
    assert response_url_dup.status_code == 409

    # 8. List URLs
    response_list = client.get('/api/urls', headers=headers)
    assert response_list.status_code == 200
    assert len(response_list.json['urls']) == 1
    assert response_list.json['urls'][0]['short_code'] == 'ggl'

    # 9. Redirect URL (Public Route, No Headers)
    response_redirect = client.get('/s/ggl')
    assert response_redirect.status_code == 302
    assert response_redirect.location == 'https://google.com'

    # 10. Forgot Password & Reset
    response_forgot = client.post('/api/auth/forgot-password', json={'email': 'test@example.com'})
    assert response_forgot.status_code == 200

    with flask_app.app_context():
        reset_entry = PasswordReset.query.first()
        assert reset_entry is not None
        reset_token = reset_entry.token

    reset_payload = {
        'token': reset_token,
        'password': 'NewSecurePassword456!',
        'confirm_password': 'NewSecurePassword456!'
    }
    response_reset = client.post('/api/auth/reset-password', json=reset_payload)
    assert response_reset.status_code == 200

    # 11. Login with New Password
    new_login_data = {
        'email': 'test@example.com',
        'password': 'NewSecurePassword456!'
    }
    response_new_login = client.post('/api/auth/login', json=new_login_data)
    assert response_new_login.status_code == 200
    assert response_new_login.json['access_token'] is not None
