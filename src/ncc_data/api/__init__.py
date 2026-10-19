"""HTTP application factory; runtime implementation lives in app."""

from .app import create_app

__all__ = ["create_app"]
