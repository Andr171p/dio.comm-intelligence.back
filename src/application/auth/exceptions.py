from http import HTTPStatus

from ddf.application.exceptions import ApplicationError


class UnauthorizedError(ApplicationError):
    status_code = HTTPStatus.UNAUTHORIZED
    error_code = "unauthorized"


class PermissionDeniedError(ApplicationError):
    status_code = HTTPStatus.FORBIDDEN
    error_code = "permission_denied"
