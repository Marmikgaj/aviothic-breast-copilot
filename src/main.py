"""Application entrypoint.

Exposes the FastAPI ``app`` instance for uvicorn::

    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
"""

from src.api.app import create_app

app = create_app()
