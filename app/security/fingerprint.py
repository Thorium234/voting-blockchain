"""Device fingerprinting for security."""
import hashlib
from typing import Optional


def generate_fingerprint(
    user_agent: str = "",
    screen_resolution: str = "",
    timezone: str = "",
    ip_address: str = ""
) -> str:
    """Generate a device fingerprint from various signals."""
    # Combine signals
    fingerprint_data = f"{user_agent}:{screen_resolution}:{timezone}:{ip_address}"
    
    # Hash to create fingerprint
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()


def verify_fingerprint(
    stored_fingerprint: Optional[str],
    provided_fingerprint: Optional[str]
) -> bool:
    """Verify if provided fingerprint matches stored one."""
    if not stored_fingerprint or not provided_fingerprint:
        return False
    
    return stored_fingerprint == provided_fingerprint


def extract_client_info(request) -> dict:
    """Extract client information from request for fingerprinting."""
    return {
        "user_agent": request.headers.get("user-agent", ""),
        "accept_language": request.headers.get("accept-language", ""),
        "accept_encoding": request.headers.get("accept-encoding", ""),
        "ip_address": request.client.host if request.client else ""
    }
