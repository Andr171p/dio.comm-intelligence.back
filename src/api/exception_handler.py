from ddf.application.exceptions import ApplicationError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    assert isinstance(exc, ApplicationError)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


def setup_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, application_error_handler)


__all__ = ["setup_exception_handlers"]
