# backend/models/__init__.py
# ORM models package — imports all models so Base.metadata discovers every table.
#
# Architecture Reference: docs/database.md Section 5 (10 tables)
#
# Import order follows FK dependency chain:
#   1. University (no FK deps)
#   2. User (FK → University)
#   3. Student (FK → User, University)
#   4. Employer (FK → User)
#   5. Certificate (FK → University, User x3)
#   6. BlockchainTransaction (FK → Certificate)
#   7. QRVerification (FK → Certificate, User)
#   8. VerificationLog (FK → Certificate, User, QRVerification)
#   9. RefreshToken (FK → User, self-ref)
#   10. AuditLog (no FKs)

from models.university_model import University  # noqa: F401
from models.user_model import User  # noqa: F401
from models.student_model import Student  # noqa: F401
from models.employer_model import Employer  # noqa: F401
from models.certificate_model import Certificate  # noqa: F401
from models.blockchain_transaction_model import BlockchainTransaction  # noqa: F401
from models.qr_verification_model import QRVerification  # noqa: F401
from models.verification_log_model import VerificationLog  # noqa: F401
from models.refresh_token_model import RefreshToken  # noqa: F401
from models.audit_log_model import AuditLog  # noqa: F401

__all__ = [
    "University",
    "User",
    "Student",
    "Employer",
    "Certificate",
    "BlockchainTransaction",
    "QRVerification",
    "VerificationLog",
    "RefreshToken",
    "AuditLog",
]
