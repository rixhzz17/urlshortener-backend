from datetime import datetime
from app.extensions import db

class URL(db.Model):
    __tablename__ = 'urls'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    original_url = db.Column(db.Text, nullable=False)
    short_code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=True)
    qr_code = db.Column(db.Text, nullable=True) # Storing QR code as Base64 encoded string
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)

    def __init__(self, user_id, original_url, short_code, title=None, qr_code=None, expires_at=None, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.original_url = original_url
        self.short_code = short_code
        self.title = title
        self.qr_code = qr_code
        self.expires_at = expires_at

    def is_expired(self):
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False

    def to_dict(self, click_count=0):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'original_url': self.original_url,
            'short_code': self.short_code,
            'title': self.title,
            'qr_code': self.qr_code,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'clicks': click_count
        }
