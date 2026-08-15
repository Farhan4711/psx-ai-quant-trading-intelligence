"""PKT-aware date/time helpers.

`date.today()` / `datetime.now()` use the server's local clock, which in
production is UTC — not Pakistan Standard Time (UTC+5). For anything tied
to PSX/FBR conventions (fiscal years, tax brackets, billing periods, goal
timelines), that's wrong for roughly five hours a day (PKT 00:00-04:59).
Use these helpers instead of the naive stdlib calls.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

PKT = ZoneInfo("Asia/Karachi")


def today_pkt() -> date:
    return datetime.now(tz=PKT).date()
