from datetime import datetime, timedelta, timezone


def is_device_online(last_seen_at: datetime | None, timeout_seconds: int) -> bool:
    if last_seen_at is None:
        return False
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
    return last_seen_at >= datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
