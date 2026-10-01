from http import HTTPStatus

from ddf.application.exceptions import ApplicationError


class UnauthorizedError(ApplicationError):
    status_code = HTTPStatus.UNAUTHORIZED
    error_code = "unauthorized"
