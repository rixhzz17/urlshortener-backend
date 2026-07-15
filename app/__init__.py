import os
from flask import Flask
from config import config_by_name
from app.extensions import db, bcrypt, jwt, mail, migrate, cors, init_mongodb

def create_app(config_name):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name[config_name])

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize Extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize MongoDB
    init_mongodb(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.urls import urls_bp
    from app.routes.analytics import analytics_bp
    from app.routes.redirect import redirect_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(urls_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(redirect_bp)

    @app.route('/')
    def index():
        return {
            'message': 'Linkly Backend Running',
            'status': 'success'
        }, 200

    @app.route('/health')
    def health():
        return {'status': 'healthy'}, 200

    # Ensure tables are created for SQL
    with app.app_context():
        from app.models import user, url
        db.create_all()

    return app
