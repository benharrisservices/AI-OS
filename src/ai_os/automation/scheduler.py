"""Schedule computation — one-time, recurring, cron, delayed."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from ai_os.automation.models import ScheduleSpec, ScheduleType, utc_now


def compute_next_run(schedule: ScheduleSpec, *, after: datetime | None = None) -> datetime | None:
    """Return the next run time for a schedule, or None if exhausted."""
    now = after or utc_now()

    if schedule.schedule_type == ScheduleType.ONE_TIME:
        if schedule.run_at and schedule.run_at > now:
            return schedule.run_at
        return None

    if schedule.schedule_type == ScheduleType.DELAYED:
        delay = schedule.delay_seconds or 0
        return now + timedelta(seconds=delay)

    if schedule.schedule_type == ScheduleType.RECURRING:
        interval = schedule.interval_seconds or 3600
        return now + timedelta(seconds=interval)

    if schedule.schedule_type == ScheduleType.CRON and schedule.cron_expression:
        return _next_cron_run(schedule.cron_expression, now)

    return None


def is_due(automation_next_run: datetime | None, *, now: datetime | None = None) -> bool:
    if automation_next_run is None:
        return False
    current = now or utc_now()
    return automation_next_run <= current


def _next_cron_run(expression: str, after: datetime) -> datetime:
    """Compute next run for a 5-field cron expression (minute hour dom month dow)."""
    fields = expression.strip().split()
    if len(fields) != 5:
        raise ValueError(f"Invalid cron expression: {expression}")

    minute_f, hour_f, dom_f, month_f, dow_f = fields
    candidate = after.astimezone(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=1)

    for _ in range(525_600):  # max 1 year of minutes
        if (
            _field_matches(minute_f, candidate.minute, 0, 59)
            and _field_matches(hour_f, candidate.hour, 0, 23)
            and _field_matches(dom_f, candidate.day, 1, 31)
            and _field_matches(month_f, candidate.month, 1, 12)
            and _field_matches(dow_f, candidate.weekday(), 0, 6)
        ):
            return candidate
        candidate += timedelta(minutes=1)

    raise ValueError(f"Could not find next run for cron: {expression}")


def _field_matches(field: str, value: int, min_val: int, max_val: int) -> bool:
    if field == "*":
        return True

    for part in field.split(","):
        if "/" in part:
            base, step_str = part.split("/", 1)
            step = int(step_str)
            if base == "*":
                if value % step == 0:
                    return True
            else:
                start = int(base)
                if value >= start and (value - start) % step == 0:
                    return True
            continue

        if "-" in part:
            start, end = part.split("-", 1)
            if int(start) <= value <= int(end):
                return True
            continue

        if part.isdigit() and int(part) == value:
            return True

    return False


def validate_cron(expression: str) -> bool:
    return bool(re.match(r"^[\d\*\-/,]+$", expression.replace(" ", ""))) or expression == "*"
