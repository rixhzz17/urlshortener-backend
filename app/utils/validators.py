import re
from email_validator import validate_email, EmailNotValidError

def is_valid_email(email):
    try:
        # Validate and normalize email
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False

def is_strong_password(password):
    # Length >= 8, at least one uppercase, one lowercase, one digit, and one special character
    if len(password) < 8:
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[!@#$%^&*()_+\-=\[\]\{\};':\",./<>?]", password):
        return False
    return True

def is_valid_url(url):
    # Basic URL structure verification
    regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain...
        r'localhost|' # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None
