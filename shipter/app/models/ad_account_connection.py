from datetime import datetime, timezone
from app.extensions import db
from app.services.crypto_service import encrypt_dict, decrypt_dict


class AdAccountConnection(db.Model):
    __tablename__ = 'ad_account_connections'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    platform = db.Column(db.String(20), nullable=False, default='meta')
    encrypted_config = db.Column(db.Text, nullable=False)  # access_token, ad_account_id, page_id
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = db.relationship('Project', backref=db.backref('ad_account_connections', lazy='dynamic', cascade='all, delete-orphan'))

    def set_config(self, config: dict):
        self.encrypted_config = encrypt_dict(config)

    def get_config(self) -> dict:
        return decrypt_dict(self.encrypted_config)
