"""공통 에러 규약 — 03-기능명세서 §4.1.

응답 바디: { "error": { "code", "message", "detail" } }
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """계약 에러 코드를 그대로 실어 던지는 예외."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail or {}
        super().__init__(message)


# §4.1 표의 단축 생성자들
def unauthorized(message: str = "로그인이 필요합니다.", detail: dict | None = None) -> ApiError:
    return ApiError(status.HTTP_401_UNAUTHORIZED, "unauthorized", message, detail)


def forbidden(message: str = "권한이 없습니다.", detail: dict | None = None) -> ApiError:
    return ApiError(status.HTTP_403_FORBIDDEN, "forbidden", message, detail)


def not_found(message: str = "리소스를 찾을 수 없습니다.", detail: dict | None = None) -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, "not_found", message, detail)


def conflict(message: str = "상태가 충돌합니다.", detail: dict | None = None) -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, "conflict", message, detail)


def validation_error(message: str = "요청이 올바르지 않습니다.", detail: dict | None = None) -> ApiError:
    return ApiError(status.HTTP_400_BAD_REQUEST, "validation_error", message, detail)


def rate_limited(message: str = "호출 한도를 초과했습니다.", detail: dict | None = None) -> ApiError:
    return ApiError(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited", message, detail)


def ai_unavailable(message: str = "AI 제공자 오류입니다.", detail: dict | None = None) -> ApiError:
    return ApiError(status.HTTP_503_SERVICE_UNAVAILABLE, "ai_unavailable", message, detail)


def _envelope(code: str, message: str, detail: dict[str, Any]) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "detail": detail}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_envelope("validation_error", "요청이 올바르지 않습니다.", {"errors": exc.errors()}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {401: "unauthorized", 403: "forbidden", 404: "not_found", 409: "conflict"}
        code = code_map.get(exc.status_code, "internal_error")
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, str(exc.detail), {}),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("internal_error", "서버 오류가 발생했습니다.", {}),
        )
