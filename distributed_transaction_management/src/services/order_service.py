"""OrderService wrapper to keep module layout clean.

Actual implementation lives in `src/services/user_service.py` for the demo.
"""

from .user_service import OrderService

__all__ = ["OrderService"]
