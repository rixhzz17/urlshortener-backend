from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app.extensions import db
from app.models.user import User, EmailVerification, PasswordReset
from app.services.mail import send_verification_email, send_password_reset_email
from app.utils.validators import is_valid_email, is_strong_password

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    # Validations
    if not first_name or not last_name or not email or not password or not confirm_password:
        return jsonify({'error': 'All fields are required.'}), 400

    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email address format.'}), 400

    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match.'}), 400

    if not is_strong_password(password):
        return jsonify({
            'error': 'Password is weak. It must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one number, and one special character.'
        }), 400

    # Check duplicate email
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'An account with this email already exists.'}), 409

    try:
        # Create user
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            is_verified=False
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush() # Populate user.id

        # Generate Email Verification Token
        verification = EmailVerification(user_id=new_user.id)
        db.session.add(verification)
        db.session.commit()

        # Send Verification Email
        send_verification_email(email, first_name, verification.token)

        return jsonify({
            'message': 'Registration successful! Please check your email to verify your account.'
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500


@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    data = request.get_json() or {}
    token = data.get('token', '').strip()

    if not token:
        return jsonify({'error': 'Verification token is missing.'}), 400

    verification = EmailVerification.query.filter_by(token=token).first()
    if not verification:
        return jsonify({'error': 'Invalid verification token.'}), 400

    if verification.is_expired():
        # Clean up expired token
        db.session.delete(verification)
        db.session.commit()
        return jsonify({'error': 'Verification token has expired. Please register again.'}), 400

    user = db.session.get(User, verification.user_id)
    if not user:
        return jsonify({'error': 'Associated user not found.'}), 404

    try:
        user.is_verified = True
        db.session.delete(verification)
        db.session.commit()
        return jsonify({'message': 'Email verified successfully! You can now log in.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Email verification failed: {str(e)}'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    remember_me = data.get('remember_me', False)

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password.'}), 401

    if not user.is_verified:
        return jsonify({'error': 'Email not verified. Please verify your email first.'}), 403

    # Generate JWT token
    # If remember me is set, make it expire in 30 days, otherwise 2 hours
    expires = timedelta(days=30) if remember_me else timedelta(hours=2)
    access_token = create_access_token(identity=str(user.id), expires_delta=expires)

    return jsonify({
        'message': 'Login successful.',
        'access_token': access_token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'Email is required.'}), 400

    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email address format.'}), 400

    user = User.query.filter_by(email=email).first()
    
    # Security: always return success to prevent user enumeration
    success_response = jsonify({
        'message': 'If the email exists in our system, a password reset link has been sent.'
    }), 200

    if not user:
        return success_response

    try:
        # Check if they already have reset token and delete it
        PasswordReset.query.filter_by(user_id=user.id).delete()
        
        # Create and store secure reset token
        reset_entry = PasswordReset(user_id=user.id)
        db.session.add(reset_entry)
        db.session.commit()

        # Send Reset Email
        send_password_reset_email(email, user.first_name, reset_entry.token)
        return success_response

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to trigger password reset: {str(e)}'}), 500


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    token = data.get('token', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not token or not password or not confirm_password:
        return jsonify({'error': 'All fields are required.'}), 400

    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match.'}), 400

    if not is_strong_password(password):
        return jsonify({
            'error': 'Password must be at least 8 characters long, contain an uppercase letter, lowercase letter, number, and special character.'
        }), 400

    reset_entry = PasswordReset.query.filter_by(token=token).first()
    if not reset_entry:
        return jsonify({'error': 'Invalid reset token.'}), 400

    if reset_entry.is_expired():
        db.session.delete(reset_entry)
        db.session.commit()
        return jsonify({'error': 'Reset token has expired. Please request a new link.'}), 400

    user = db.session.get(User, reset_entry.user_id)
    if not user:
        return jsonify({'error': 'Associated user not found.'}), 404

    try:
        user.set_password(password)
        # Delete token so it cannot be reused
        db.session.delete(reset_entry)
        db.session.commit()

        return jsonify({'message': 'Password has been reset successfully. You can now log in.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to reset password: {str(e)}'}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if not user:
        return jsonify({'error': 'User not found.'}), 404
    return jsonify({'user': user.to_dict()}), 200
