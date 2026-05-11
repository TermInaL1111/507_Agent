import os
import requests
from app.core.logger_handler import logger

DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://127.0.0.1:8001")

# Try to get user from Redis cache first, then Django API.
# Uses the token stored in agent contextvar for Django auth.

# ContextVar for passing JWT token to agent tools
import contextvars
_agent_jwt_token = contextvars.ContextVar("agent_jwt_token", default="")


def set_agent_jwt_token(token: str):
    _agent_jwt_token.set(token)


def fetch_user_profile(user_id: str) -> dict | None:
    """Fetch user profile from Django /user/detail/ using stored JWT token."""
    token = _agent_jwt_token.get("")
    if not token:
        logger.warning("No JWT token in agent context, cannot fetch user profile")
        return None
    try:
        url = f"{DJANGO_API_URL}/user/detail/"
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            logger.info(f"Fetched user profile for {user_id}")
            return data
        logger.warning(f"Django profile fetch failed: {resp.status_code}")
        return None
    except Exception as e:
        logger.warning(f"Django profile fetch error: {e}")
        return None
