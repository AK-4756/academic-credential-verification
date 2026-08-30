# backend/middleware/__init__.py
# Custom middleware package.
#
# Contains:
#   request_id_middleware.py — Generates UUID per request, attaches to state + response header
#   logging_middleware.py   — Structured JSON logging of request/response metadata
