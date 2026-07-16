"""Time utilities with timezone-aware UTC defaults."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(tz=UTC)


def require_timezone_aware(value: datetime, field_name: str) -> datetime:
    """Validate that a datetime is timezone-aware."""
    if value.tzinfo is None or value.utcoffset() is None:
        msg = f"{field_name} must be timezone-aware"
        raise ValueError(msg)
    return value
