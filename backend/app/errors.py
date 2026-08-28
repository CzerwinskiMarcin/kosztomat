from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status_code: int, detail: str, code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={'detail': exc.detail, 'code': exc.code},
        )
