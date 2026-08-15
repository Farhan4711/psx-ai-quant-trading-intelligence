"""PKT-aware date/time helpers.

`date.today()` / `datetime.now()` use the server's local clock, which in
production is UTC — not Pakistan Standard Time (UTC+5). PSX-facing dates
(trained-at timestamps, benchmark aggregation windows) should use PKT.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

PKT = ZoneInfo("Asia/Karachi")


def today_pkt() -> date:
    return datetime.now(tz=PKT).date()
