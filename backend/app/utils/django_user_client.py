import os
import requests
from app.core.logger_handler import logger

DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://127.0.0.1:8001")


def fetch_user_profile(user_id: str) -> dict | None:
    """Fetch user profile from Django. Returns dict with name, student_id, class_name or None."""
    try:
        url = f"{DJANGO_API_URL}/user/profile/{user_id}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"Django profile fetch failed: {resp.status_code}")
        return None
    except Exception as e:
        logger.warning(f"Django profile fetch error: {e}")
        return None
