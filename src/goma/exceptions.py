class GomaError(Exception):
    """Base class for all errors raised by the goma client."""


class NotLoggedInError(GomaError):
    """There is no session, or goma no longer accepts it. Log in again with an email code."""


class InvalidCodeError(GomaError):
    """goma rejected the email code: it is wrong or has expired. Request a new one."""


class GomaUnreachableError(GomaError):
    """goma could not be reached (connection error or timeout). Retry later."""


class UnexpectedResponseError(GomaError):
    """goma answered with something the client does not understand."""
