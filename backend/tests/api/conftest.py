# backend/tests/api/conftest.py
# Conftest for API endpoint tests — re-exports the svc_db fixture
# from the integration conftest so it is available in tests/api/.

from tests.integration.conftest import svc_db  # noqa: F401
