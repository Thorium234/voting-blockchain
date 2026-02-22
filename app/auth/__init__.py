"""Authentication module."""
from app.auth import routes
from app.auth import password, jwt_handler, dependencies

__all__ = ["routes", "password", "jwt_handler", "dependencies"]
