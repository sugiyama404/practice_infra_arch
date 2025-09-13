"""PaymentService wrapper to keep module layout clean.

The actual class implementation is in `src/services/user_service.py` for
this example project; re-export it here so imports like
`from services.payment_service import PaymentService` work.
"""

from .user_service import PaymentService

__all__ = ["PaymentService"]
