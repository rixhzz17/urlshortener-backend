from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app.extensions import db, mongo_db
from app.models.url import URL

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

@analytics_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_analytics_summary():
    user_id = get_jwt_identity()

    # 1. SQL Statistics
    now = datetime.utcnow()
    start_of_today = datetime(now.year, now.month, now.day)
    start_of_month = datetime(now.year, now.month, 1)

    total_urls = URL.query.filter_by(user_id=int(user_id)).count()
    urls_today = URL.query.filter_by(user_id=int(user_id)).filter(URL.created_at >= start_of_today).count()
    urls_this_month = URL.query.filter_by(user_id=int(user_id)).filter(URL.created_at >= start_of_month).count()

    # Get list of user short codes
    user_urls = URL.query.filter_by(user_id=int(user_id)).all()
    short_codes = [url.short_code for url in user_urls]
    # Initialize empty analytics structure in case MongoDB is missing or user has no URLs
    empty_res = {
        'total_urls': total_urls,
        'urls_today': urls_today,
        'urls_this_month': urls_this_month,
        'total_clicks': 0,
        'most_clicked': [],
        'clicks_over_time': [],
        'browser_distribution': [],
        'device_distribution': [],
        'country_distribution': [],
        'os_distribution': []
    }

    if not short_codes:
        return jsonify(empty_res), 200

    if mongo_db is None:
        current_app.logger.warning("MongoDB is offline or not configured. Returning SQL metrics only.")
        return jsonify(empty_res), 200

    try:
        clicks_col = mongo_db.clicks

        # Match only user's short codes
        match_stage = {'$match': {'short_code': {'$in': short_codes}}}

        # 2. Total clicks
        total_clicks = clicks_col.count_documents({'short_code': {'$in': short_codes}})

        # 3. Browser Distribution
        browser_agg = clicks_col.aggregate([
            match_stage,
            {'$group': {'_id': '$browser', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ])
        browser_dist = [{'label': x['_id'] or 'Unknown', 'value': x['count']} for x in browser_agg]

        # 4. Device Distribution
        device_agg = clicks_col.aggregate([
            match_stage,
            {'$group': {'_id': '$device', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ])
        device_dist = [{'label': x['_id'] or 'Unknown', 'value': x['count']} for x in device_agg]

        # 5. OS Distribution
        os_agg = clicks_col.aggregate([
            match_stage,
            {'$group': {'_id': '$operating_system', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ])
        os_dist = [{'label': x['_id'] or 'Unknown', 'value': x['count']} for x in os_agg]

        # 6. Country Distribution
        country_agg = clicks_col.aggregate([
            match_stage,
            {'$group': {'_id': '$country', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ])
        country_dist = [{'label': x['_id'] or 'Unknown', 'value': x['count']} for x in country_agg]

        # 7. Most Clicked URLs (Top 5)
        clicks_by_url_agg = clicks_col.aggregate([
            match_stage,
            {'$group': {'_id': '$short_code', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 5}
        ])
        
        # Resolve titles from SQL and build list
        most_clicked = []
        url_map = {url.short_code: url for url in user_urls}
        for item in clicks_by_url_agg:
            code = item['_id']
            count = item['count']
            url_obj = url_map.get(code)
            most_clicked.append({
                'short_code': code,
                'title': url_obj.title if url_obj else 'Deleted URL',
                'original_url': url_obj.original_url if url_obj else '',
                'clicks': count
            })

        # 8. Clicks Over Time (Daily - Last 14 Days)
        fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
        daily_agg = clicks_col.aggregate([
            {'$match': {
                'short_code': {'$in': short_codes},
                'timestamp': {'$gte': fourteen_days_ago}
            }},
            {'$group': {
                '_id': {
                    'year': {'$year': '$timestamp'},
                    'month': {'$month': '$timestamp'},
                    'day': {'$dayOfMonth': '$timestamp'}
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id.year': 1, '_id.month': 1, '_id.day': 1}}
        ])
        
        clicks_over_time = []
        for x in daily_agg:
            date_str = f"{x['_id']['year']}-{x['_id']['month']:02d}-{x['_id']['day']:02d}"
            clicks_over_time.append({'date': date_str, 'clicks': x['count']})

        response_data = {
            'total_urls': total_urls,
            'urls_today': urls_today,
            'urls_this_month': urls_this_month,
            'total_clicks': total_clicks,
            'most_clicked': most_clicked,
            'clicks_over_time': clicks_over_time,
            'browser_distribution': browser_dist,
            'device_distribution': device_dist,
            'country_distribution': country_dist,
            'os_distribution': os_dist
        }

        return jsonify(response_data), 200

    except Exception as e:
        current_app.logger.error(f"Error aggregating analytics: {e}")
        # Return fallback structures on crash
        return jsonify(empty_res), 200


@analytics_bp.route('/url/<int:url_id>', methods=['GET'])
@jwt_required()
def get_url_analytics(url_id):
    user_id = get_jwt_identity()
    url_entry = URL.query.filter_by(id=url_id, user_id=int(user_id)).first()
    
    if not url_entry:
        return jsonify({'error': 'URL not found or unauthorized.'}), 404

    empty_res = {
        'total_clicks': 0,
        'browser_distribution': [],
        'device_distribution': [],
        'country_distribution': [],
        'clicks_over_time': []
    }

    if mongo_db is None:
        return jsonify(empty_res), 200

    try:
        clicks_col = mongo_db.clicks
        match_stage = {'$match': {'short_code': url_entry.short_code}}

        total_clicks = clicks_col.count_documents({'short_code': url_entry.short_code})

        # Browser
        browser_agg = clicks_col.aggregate([
            match_stage,
            {'$group': {'_id': '$browser', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ])
        browser_dist = [{'label': x['_id'] or 'Unknown', 'value': x['count']} for x in browser_agg]

        # Device
        device_agg = clicks_col.aggregate([
            match_stage,
            {'$group': {'_id': '$device', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ])
        device_dist = [{'label': x['_id'] or 'Unknown', 'value': x['count']} for x in device_agg]

        # Country
        country_agg = clicks_col.aggregate([
            match_stage,
            {'$group': {'_id': '$country', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ])
        country_dist = [{'label': x['_id'] or 'Unknown', 'value': x['count']} for x in country_agg]

        # Clicks Over Time (Daily)
        fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
        daily_agg = clicks_col.aggregate([
            {'$match': {
                'short_code': url_entry.short_code,
                'timestamp': {'$gte': fourteen_days_ago}
            }},
            {'$group': {
                '_id': {
                    'year': {'$year': '$timestamp'},
                    'month': {'$month': '$timestamp'},
                    'day': {'$dayOfMonth': '$timestamp'}
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id.year': 1, '_id.month': 1, '_id.day': 1}}
        ])
        clicks_over_time = []
        for x in daily_agg:
            date_str = f"{x['_id']['year']}-{x['_id']['month']:02d}-{x['_id']['day']:02d}"
            clicks_over_time.append({'date': date_str, 'clicks': x['count']})

        return jsonify({
            'total_clicks': total_clicks,
            'browser_distribution': browser_dist,
            'device_distribution': device_dist,
            'country_distribution': country_dist,
            'clicks_over_time': clicks_over_time
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error querying URL analytics: {e}")
        return jsonify(empty_res), 200
