from app import db
from datetime import datetime

class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.Text)
    country = db.Column(db.String(100))
    region = db.Column(db.String(100))
    city = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    isp = db.Column(db.String(200))
    org = db.Column(db.String(200))
    timezone = db.Column(db.String(50))
    visited_at = db.Column(db.DateTime, default=datetime.utcnow)
    page_visited = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<Visitor {self.ip_address} from {self.city}, {self.country}>'
