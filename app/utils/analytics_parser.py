import re
import urllib.request
import json

def parse_user_agent(ua_string):
    if not ua_string:
        return "Unknown", "Unknown", "Unknown"
    
    # Device parsing
    device = "Desktop"
    if "iPad" in ua_string or "Tablet" in ua_string:
        device = "Tablet"
    elif "Mobi" in ua_string or "Android" in ua_string or "iPhone" in ua_string:
        device = "Mobile"
        
    # OS parsing
    os = "Unknown OS"
    if "Windows NT" in ua_string:
        os = "Windows"
    elif "Macintosh" in ua_string or "Mac OS X" in ua_string:
        os = "macOS"
    elif "Android" in ua_string:
        os = "Android"
    elif "iPhone" in ua_string or "iPad" in ua_string:
        os = "iOS"
    elif "Linux" in ua_string:
        os = "Linux"
        
    # Browser parsing
    browser = "Unknown Browser"
    if "Firefox" in ua_string:
        browser = "Firefox"
    elif "Chrome" in ua_string and "Safari" in ua_string:
        if "Edg" in ua_string:
            browser = "Edge"
        elif "OPR" in ua_string:
            browser = "Opera"
        else:
            browser = "Chrome"
    elif "Safari" in ua_string and "Chrome" not in ua_string:
        browser = "Safari"
    elif "MSIE" in ua_string or "Trident" in ua_string:
        browser = "Internet Explorer"
        
    return browser, os, device

def get_ip_location(ip):
    # Skip localhost / private IPs
    if not ip or ip in ('127.0.0.1', '::1', 'localhost') or ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.16.'):
        return 'Localhost', 'Localhost'
    
    # Clean up proxy IP chain (take first IP if multiple comma-separated IPs)
    if ',' in ip:
        ip = ip.split(',')[0].strip()
        
    try:
        # Query public API with 1.0s timeout
        url = f"http://ip-api.com/json/{ip}?fields=status,country,city"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=1.0) as response:
            data = json.loads(response.read().decode())
            if data.get('status') == 'success':
                return data.get('country', 'Unknown'), data.get('city', 'Unknown')
    except Exception:
        # Fallback in case of timeout or failure
        pass
        
    return 'Unknown', 'Unknown'
