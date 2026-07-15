from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_cors import CORS
from pymongo import MongoClient

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
mail = Mail()
migrate = Migrate()
cors = CORS()

# MongoDB Client will be initialized dynamically in app factory
mongo_client = None
mongo_db = None

def init_mongodb(app):
    global mongo_client, mongo_db
    mongo_uri = app.config.get('MONGO_URI')
    if mongo_uri:
        try:
            mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
            # Test connection
            mongo_client.server_info()
            mongo_db = mongo_client.get_default_database()
            app.logger.info("Successfully connected to MongoDB!")
        except Exception as e:
            app.logger.error(f"Failed to connect to MongoDB: {e}")
            mongo_client = None
            mongo_db = None
    else:
        app.logger.warning("MONGO_URI not configured. MongoDB functionality will be disabled.")
