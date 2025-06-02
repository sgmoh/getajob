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
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def get_geolocation_data(ip_address):
    """Get geolocation data for an IP address using multiple services"""
    try:
        # Don't track localhost/private IPs
        if ip_address in ['127.0.0.1', 'localhost'] or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
            return None
        
        # Try ipgeolocation.io with API key if available
        api_key = '97f60b1cb2bc4b519e8cbfdda86e8435'
        if api_key:
            try:
                response = requests.get(
                    f'https://api.ipgeolocation.io/ipgeo',
                    params={'apiKey': api_key, 'ip': ip_address, 'fields': 'geo,isp,time_zone', 'include': 'security'},
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"IPGeolocation.io response: {data}")
                    # Convert to consistent format
                    return {
                        'country_name': data.get('country_name'),
                        'region': data.get('state_prov'),
                        'city': data.get('city'),
                        'district': data.get('district'),
                        'zipcode': data.get('zipcode'),
                        'latitude': float(data.get('latitude', 0)) if data.get('latitude') else None,
                        'longitude': float(data.get('longitude', 0)) if data.get('longitude') else None,
                        'org': data.get('isp'),
                        'timezone': data.get('time_zone', {}).get('name') if data.get('time_zone') else None
                    }
                else:
                    logger.error(f"IPGeolocation.io API error: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Error with ipgeolocation.io: {e}")
        
        # Fallback to ip-api.com (free, no key needed, higher rate limit)
        try:
            response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return {
                        'country_name': data.get('country'),
                        'region': data.get('regionName'),
                        'city': data.get('city'),
                        'latitude': data.get('lat'),
                        'longitude': data.get('lon'),
                        'org': data.get('isp'),
                        'timezone': data.get('timezone')
                    }
        except Exception as e:
            logger.error(f"Error with ip-api.com: {e}")
            
        # Last fallback to ipapi.co
        try:
            response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'error' not in data:
                    return data
        except Exception as e:
            logger.error(f"Error with ipapi.co: {e}")
            
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
            visitor.district = geo_data.get('district')
            visitor.zipcode = geo_data.get('zipcode')
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
