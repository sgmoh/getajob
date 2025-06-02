import os
import logging
from flask import render_template, request, jsonify
from app import app, db
from models import Visitor
from discord_notifier import send_discord_notification
import requests

logger = logging.getLogger(__name__)

def get_client_ip():
    """Get the real client IP address, accounting for proxies"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def get_geolocation_data(ip_address):
    """Get geolocation data for an IP address using ipapi.co"""
    try:
        # Don't track localhost/private IPs
        if ip_address in ['127.0.0.1', 'localhost'] or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
            return None
            
        response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error getting geolocation data: {e}")
    return None

def track_visitor(page_name):
    """Track visitor and send Discord notification"""
    try:
        ip_address = get_client_ip()
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        # Get geolocation data
        geo_data = get_geolocation_data(ip_address)
        
        # Create visitor record
        visitor = Visitor(
            ip_address=ip_address,
            user_agent=user_agent,
            page_visited=page_name
        )
        
        if geo_data and 'error' not in geo_data:
            visitor.country = geo_data.get('country_name')
            visitor.region = geo_data.get('region')
            visitor.city = geo_data.get('city')
            visitor.latitude = geo_data.get('latitude')
            visitor.longitude = geo_data.get('longitude')
            visitor.isp = geo_data.get('org')
            visitor.timezone = geo_data.get('timezone')
        
        db.session.add(visitor)
        db.session.commit()
        
        # Send Discord notification
        send_discord_notification(visitor, geo_data)
        
        logger.info(f"Tracked visitor: {ip_address} on {page_name}")
        
    except Exception as e:
        logger.error(f"Error tracking visitor: {e}")
        db.session.rollback()

@app.route('/')
def index():
    track_visitor('Home Page')
    return render_template('index.html')

@app.route('/about')
def about():
    track_visitor('About Page')
    return render_template('about.html')

@app.route('/contact')
def contact():
    track_visitor('Contact Page')
    return render_template('contact.html')

@app.route('/api/visitors')
def api_visitors():
    """API endpoint to get visitor statistics (for admin use)"""
    try:
        total_visitors = Visitor.query.count()
        recent_visitors = Visitor.query.order_by(Visitor.visited_at.desc()).limit(10).all()
        
        return jsonify({
            'total_visitors': total_visitors,
            'recent_visitors': [
                {
                    'ip': v.ip_address,
                    'country': v.country,
                    'city': v.city,
                    'page': v.page_visited,
                    'visited_at': v.visited_at.isoformat() if v.visited_at else None
                }
                for v in recent_visitors
            ]
        })
    except Exception as e:
        logger.error(f"Error getting visitor stats: {e}")
        return jsonify({'error': 'Failed to get visitor statistics'}), 500
