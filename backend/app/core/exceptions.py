"""Custom exception classes for standardized error handling."""
from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base exception for application errors."""
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)


class ResourceNotFoundError(AppException):
    """Raised when a requested resource is not found."""
    def __init__(self, resource: str, identifier):
        super().__init__(
            detail=f"{resource} with ID {identifier} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class UnauthorizedError(AppException):
    """Raised when user is not authorized to perform an action."""
    def __init__(self, detail: str = "Not authorized to perform this action"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN
        )


class ValidationError(AppException):
    """Raised when input validation fails."""
    def __init__(self, detail: str):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )
