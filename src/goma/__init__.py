from importlib.metadata import PackageNotFoundError, version

from .client import GomaClient
from .exceptions import (
    GomaError,
    GomaUnreachableError,
    InvalidCodeError,
    NotLoggedInError,
    UnexpectedResponseError,
)
from .models import ListItem, Product, ShoppingList
from .token_storage import FileTokenStorage, TokenStorage

try:
    __version__ = version("goma")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "FileTokenStorage",
    "GomaClient",
    "GomaError",
    "GomaUnreachableError",
    "InvalidCodeError",
    "ListItem",
    "NotLoggedInError",
    "Product",
    "ShoppingList",
    "TokenStorage",
    "UnexpectedResponseError",
    "__version__",
]
