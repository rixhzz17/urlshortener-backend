from flask import Blueprint, request, redirect, jsonify, current_app, render_template_string
from datetime import datetime
from app.extensions import db, mongo_db
from app.models.url import URL
from app.utils.analytics_parser import parse_user_agent, get_ip_location

redirect_bp = Blueprint('redirect', __name__)

@redirect_bp.route('/s/<short_code>', methods=['GET'])
def redirect_to_url(short_code):
    # Find link
    url_entry = URL.query.filter_by(short_code=short_code).first()
    
    if not url_entry:
        # Render a simple professional 404 page
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Link Not Found - Linkly</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
            <style>
                body { font-family: 'Inter', sans-serif; background-color: #f8fafc; color: #0f172a; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
                .card { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05); text-align: center; max-width: 450px; border: 1px solid #e2e8f0; }
                h1 { font-size: 24px; font-weight: 700; color: #1e293b; margin-top: 0; margin-bottom: 12px; }
                p { color: #64748b; font-size: 16px; line-height: 24px; margin-bottom: 24px; }
                .btn { background-color: #2563eb; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px; display: inline-block; transition: background-color 0.2s; }
                .btn:hover { background-color: #1d4ed8; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Link Not Found</h1>
                <p>The link you are trying to access does not exist on Linkly, or it has been deleted by its owner.</p>
                <a href="/" class="btn">Go to Linkly</a>
            </div>
        </body>
        </html>
        """), 404

    # Check if expired
    if url_entry.is_expired():
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Link Expired - Linkly</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
            <style>
                body { font-family: 'Inter', sans-serif; background-color: #f8fafc; color: #0f172a; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }
                .card { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05); text-align: center; max-width: 450px; border: 1px solid #e2e8f0; }
                h1 { font-size: 24px; font-weight: 700; color: #941111; margin-top: 0; margin-bottom: 12px; }
                p { color: #64748b; font-size: 16px; line-height: 24px; margin-bottom: 24px; }
                .btn { background-color: #475569; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px; display: inline-block; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Link Expired</h1>
                <p>This Linkly shortcut has reached its expiration date and is no longer active.</p>
                <a href="/" class="btn">Back to Home</a>
            </div>
        </body>
        </html>
        """), 410

    # Capture and record analytics in MongoDB (Phase 6)
    ua_string = request.headers.get('User-Agent', '')
    referrer = request.referrer or request.headers.get('Referer', 'Direct')
    
    # Extract IP
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr or '127.0.0.1'

    # Parse UA
    browser, os_name, device = parse_user_agent(ua_string)

    # Get Geolocation
    country, city = get_ip_location(ip)

    # Store click log in MongoDB
    if mongo_db is not None:
        try:
            click_log = {
                'short_code': short_code,
                'original_url': url_entry.original_url,
                'browser': browser,
                'operating_system': os_name,
                'device': device,
                'ip_address': ip,
                'country': country,
                'city': city,
                'timestamp': datetime.utcnow(),
                'referrer': referrer,
                'user_agent': ua_string
            }
            mongo_db.clicks.insert_one(click_log)
        except Exception as mongo_err:
            # We catch it so we don't break the user's redirection experience if MongoDB goes offline
            current_app.logger.error(f"Failed to save click to MongoDB: {mongo_err}")
    else:
        current_app.logger.warning("MongoDB not active. Skipping click analytics save.")

    # Redirect user to destination
    return redirect(url_entry.original_url, code=302)
