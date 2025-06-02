import os
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Discord webhook URL from environment variable with fallback to provided URL
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1379126417362780190/Ec-Hgr9sMHTDWNZsqpcTnDUQ1AEyFLpANtR48Syj9ufVHGm7L1Hcvd1FpgYIpU5tPKqS")

def send_discord_notification(visitor, geo_data=None):
    """Send visitor notification to Discord via webhook"""
    try:
        # Create embed for rich formatting
        embed = {
            "title": "🌐 New Website Visitor",
            "color": 0x00ff00,  # Green color
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "📍 IP Address",
                    "value": visitor.ip_address,
                    "inline": True
                },
                {
                    "name": "📱 Page Visited",
                    "value": visitor.page_visited,
                    "inline": True
                },
                {
                    "name": "🕒 Time",
                    "value": visitor.visited_at.strftime("%Y-%m-%d %H:%M:%S UTC") if visitor.visited_at else "Unknown",
                    "inline": True
                }
            ]
        }
        
        # Add geolocation information if available
        if geo_data and 'error' not in geo_data:
            location_info = []
            if visitor.district:
                location_info.append(visitor.district)
            if visitor.city:
                location_info.append(visitor.city)
            if visitor.region:
                location_info.append(visitor.region)
            if visitor.country:
                location_info.append(visitor.country)
            
            if location_info:
                embed["fields"].append({
                    "name": "🌍 Location",
                    "value": ", ".join(location_info),
                    "inline": True
                })
            
            # Add postal code if available
            if visitor.zipcode:
                embed["fields"].append({
                    "name": "📮 Postal Code",
                    "value": visitor.zipcode,
                    "inline": True
                })
            
            if visitor.isp:
                embed["fields"].append({
                    "name": "🏢 ISP/Organization",
                    "value": visitor.isp,
                    "inline": True
                })
            
            if visitor.timezone:
                embed["fields"].append({
                    "name": "⏰ Timezone",
                    "value": visitor.timezone,
                    "inline": True
                })
            
            # Add coordinates if available
            if visitor.latitude and visitor.longitude:
                embed["fields"].append({
                    "name": "📍 Coordinates",
                    "value": f"{visitor.latitude}, {visitor.longitude}",
                    "inline": True
                })
                
                # Add Google Maps link
                maps_url = f"https://www.google.com/maps?q={visitor.latitude},{visitor.longitude}"
                embed["fields"].append({
                    "name": "🗺️ View on Map",
                    "value": f"[Google Maps]({maps_url})",
                    "inline": True
                })
        
        # Add user agent information
        if visitor.user_agent:
            # Truncate user agent if too long
            user_agent = visitor.user_agent[:1000] + "..." if len(visitor.user_agent) > 1000 else visitor.user_agent
            embed["fields"].append({
                "name": "🖥️ User Agent",
                "value": f"```{user_agent}```",
                "inline": False
            })
        
        # Prepare webhook payload
        payload = {
            "embeds": [embed],
            "username": "Website Monitor",
            "avatar_url": "https://cdn.jsdelivr.net/gh/feathericons/feather@master/icons/monitor.svg"
        }
        
        # Send webhook
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code == 204:
            logger.info("Discord notification sent successfully")
        else:
            logger.error(f"Failed to send Discord notification: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")
