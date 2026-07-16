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

    mongo_uri = app.config.get("MONGO_URI")

    app.logger.info("=" * 60)
    app.logger.info(f"MONGO_URI = {mongo_uri}")
    app.logger.info("=" * 60)

    if not mongo_uri:
        app.logger.error("MONGO_URI NOT FOUND")
        mongo_client = None
        mongo_db = None
        return

    try:
        mongo_client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000
        )

        # Test MongoDB connection
        mongo_client.admin.command("ping")

        mongo_db = mongo_client.get_database()

        app.logger.info("✅ MongoDB Connected Successfully!")

    except Exception as e:
        app.logger.error(f"❌ MongoDB Connection Error: {e}")
        mongo_client = None
        mongo_db = None
