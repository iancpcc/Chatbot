class DomainError(Exception):
    pass


class ValidationError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class BusinessRuleError(DomainError):
    pass


class InfrastructureError(DomainError):
    """Raised when an external dependency/config prevents completing a request."""
