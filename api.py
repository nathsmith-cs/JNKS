"""Thin re-export so `uvicorn api:app` keeps working.

The real application lives in pipeline.server.
"""

from pipeline.server import app  # noqa: F401
