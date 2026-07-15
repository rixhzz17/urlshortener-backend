from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import string
import random
import re
from app.extensions import db, mongo_db
from app.models.url import URL
from app.services.qrcode import generate_qr_code_base64
from app.utils.validators import is_valid_url

urls_bp = Blueprint('urls', __name__, url_prefix='/api/urls')

def generate_random_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def get_click_count(short_code):
    if mongo_db is not None:
        try:
            return mongo_db.clicks.count_documents({'short_code': short_code})
        except Exception:
            return 0
    return 0

@urls_bp.route('', methods=['POST'])
@jwt_required()
def create_url():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    original_url = data.get('original_url', '').strip()
    custom_code = data.get('custom_code', '').strip()
    title = data.get('title', '').strip()
    expires_at_str = data.get('expires_at', None)

    # Validation
    if not original_url:
        return jsonify({'error': 'Original URL is required.'}), 400

    if not is_valid_url(original_url):
        return jsonify({'error': 'Invalid URL format. Make sure it starts with http:// or https://'}), 400

    # Parse expiry date
    expires_at = None
    if expires_at_str:
        try:
            # Handle ISO string like "2026-07-14T00:00:00"
            # Strip timezone if present
            clean_date = re.sub(r'\.\d+Z$|Z$', '', expires_at_str)
            expires_at = datetime.fromisoformat(clean_date).replace(tzinfo=None)
            if expires_at < datetime.utcnow():
                return jsonify({'error': 'Expiration date must be in the future.'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid expiration date format.'}), 400

    # Handle short code
    short_code = ""
    if custom_code:
        # Check custom code format (alphanumeric, dash, underscore, between 3 and 30 chars)
        if not re.match(r'^[a-zA-Z0-9\-_]{3,30}$', custom_code):
            return jsonify({'error': 'Custom code must be between 3 and 30 characters and only contain letters, numbers, hyphens, and underscores.'}), 400
        
        # Check duplicate custom code
        existing = URL.query.filter_by(short_code=custom_code).first()
        if existing:
            return jsonify({'error': 'This custom short code is already taken.'}), 409
        short_code = custom_code
    else:
        # Generate random unique short code
        for _ in range(10):
            code = generate_random_code()
            if not URL.query.filter_by(short_code=code).first():
                short_code = code
                break
        if not short_code:
            return jsonify({'error': 'Failed to generate unique short code. Please try again.'}), 500

    # Base title on URL hostname or default
    if not title:
        match = re.match(r'https?://(?:www\.)?([^/]+)', original_url)
        title = match.group(1) if match else "Short Link"

    # Construct the full short URL link pointing to redirect endpoint
    # E.g. http://localhost:5000/s/short_code
    # Wait, in production it will use host from request or env.
    base_url = request.url_root.rstrip('/')
    full_short_url = f"{base_url}/s/{short_code}"

    # Generate QR Code
    qr_code_base64 = generate_qr_code_base64(full_short_url)

    try:
        new_url = URL(
            user_id=int(user_id),
            original_url=original_url,
            short_code=short_code,
            title=title,
            qr_code=qr_code_base64,
            expires_at=expires_at
        )
        db.session.add(new_url)
        db.session.commit()

        return jsonify(new_url.to_dict(click_count=0)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create URL: {str(e)}'}), 500


@urls_bp.route('', methods=['GET'])
@jwt_required()
def list_urls():
    user_id = get_jwt_identity()
    search = request.args.get('search', '').strip()
    sort = request.args.get('sort', 'created_at_desc')
    filter_type = request.args.get('filter', 'all')

    query = URL.query.filter_by(user_id=int(user_id))

    # Apply search filter
    if search:
        query = query.filter(
            db.or_(
                URL.title.ilike(f'%{search}%'),
                URL.original_url.ilike(f'%{search}%'),
                URL.short_code.ilike(f'%{search}%')
            )
        )

    # Apply type filter (active, expired)
    now = datetime.utcnow()
    if filter_type == 'active':
        query = query.filter(db.or_(URL.expires_at == None, URL.expires_at > now))
    elif filter_type == 'expired':
        query = query.filter(URL.expires_at != None, URL.expires_at <= now)

    urls = query.all()

    # Map to dictionary and attach click count from MongoDB
    url_list = []
    for u in urls:
        clicks = get_click_count(u.short_code)
        url_list.append(u.to_dict(click_count=clicks))

    # Apply sorting
    if sort == 'created_at_asc':
        url_list.sort(key=lambda x: x['created_at'])
    elif sort == 'created_at_desc':
        url_list.sort(key=lambda x: x['created_at'], reverse=True)
    elif sort == 'clicks_asc':
        url_list.sort(key=lambda x: x['clicks'])
    elif sort == 'clicks_desc':
        url_list.sort(key=lambda x: x['clicks'], reverse=True)
    elif sort == 'title_asc':
        url_list.sort(key=lambda x: (x['title'] or '').lower())
    elif sort == 'title_desc':
        url_list.sort(key=lambda x: (x['title'] or '').lower(), reverse=True)

    return jsonify({'urls': url_list}), 200


@urls_bp.route('/<int:url_id>', methods=['PUT'])
@jwt_required()
def update_url(url_id):
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    original_url = data.get('original_url', '').strip()
    expires_at_str = data.get('expires_at', None)

    url_entry = URL.query.filter_by(id=url_id, user_id=int(user_id)).first()
    if not url_entry:
        return jsonify({'error': 'URL not found or unauthorized.'}), 404

    if original_url:
        if not is_valid_url(original_url):
            return jsonify({'error': 'Invalid URL format.'}), 400
        url_entry.original_url = original_url

    if title:
        url_entry.title = title

    if expires_at_str is not None:
        if expires_at_str == '':
            url_entry.expires_at = None
        else:
            try:
                clean_date = re.sub(r'\.\d+Z$|Z$', '', expires_at_str)
                expires_at = datetime.fromisoformat(clean_date).replace(tzinfo=None)
                if expires_at < datetime.utcnow():
                    return jsonify({'error': 'Expiration date must be in the future.'}), 400
                url_entry.expires_at = expires_at
            except ValueError:
                return jsonify({'error': 'Invalid expiration date format.'}), 400

    try:
        # Re-generate QR Code in case the base server changed or redirect route updated
        base_url = request.url_root.rstrip('/')
        full_short_url = f"{base_url}/s/{url_entry.short_code}"
        url_entry.qr_code = generate_qr_code_base64(full_short_url)

        db.session.commit()
        return jsonify(url_entry.to_dict(click_count=get_click_count(url_entry.short_code))), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update URL: {str(e)}'}), 500


@urls_bp.route('/<int:url_id>', methods=['DELETE'])
@jwt_required()
def delete_url(url_id):
    user_id = get_jwt_identity()
    url_entry = URL.query.filter_by(id=url_id, user_id=int(user_id)).first()
    if not url_entry:
        return jsonify({'error': 'URL not found or unauthorized.'}), 404

    try:
        # Delete click history from MongoDB to keep clean
        if mongo_db is not None:
            try:
                mongo_db.clicks.delete_many({'short_code': url_entry.short_code})
            except Exception as mongo_err:
                current_app.logger.error(f"Failed to delete clicks in MongoDB: {mongo_err}")
        
        db.session.delete(url_entry)
        db.session.commit()
        return jsonify({'message': 'URL and its analytics deleted successfully.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete URL: {str(e)}'}), 500
