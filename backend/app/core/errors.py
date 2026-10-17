"""Domain errors shared by the REST API and the MCP server.

Services raise these; the API maps them to HTTP responses (see main.py) and the
MCP tools turn them into tool errors the model can read.
"""
from __future__ import annotations


class TroveError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NotFound(TroveError):
    status_code = 404


class Forbidden(TroveError):
    status_code = 403


class Conflict(TroveError):
    status_code = 409


class Invalid(TroveError):
    status_code = 422


class TooLarge(TroveError):
    status_code = 413
