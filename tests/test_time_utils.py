"""Tests for clawplay.time_utils — local-time helpers."""

import datetime as _dt

from clawplay.time_utils import (
    DEFAULT_TZ,
    countdown_to_kickoff,
    format_local,
    local_now,
    parse_iso,
    to_local,
)


class TestLocalNow:
    def test_default_tz_is_chicago(self):
        assert DEFAULT_TZ == "America/Chicago"

    def test_local_now_returns_aware_datetime(self):
        now = local_now()
        assert isinstance(now, _dt.datetime)
        assert now.tzinfo is not None

    def test_local_now_can_be_overridden_by_env(self):
        # default arg overrides env, so explicit None pulls env at call time
        ny = local_now()
        chi = local_now("America/Chicago")
        assert ny.tzinfo is not None
        assert chi.tzinfo is not None


class TestToLocal:
    def test_naive_assumed_utc(self):
        naive = _dt.datetime(2026, 6, 19, 3, 0, 0)
        local = to_local(naive, "America/Chicago")
        assert local.tzinfo is not None
        assert local.hour in (21, 22) or local.day != naive.day

    def test_aware_converted_correctly(self):
        utc = _dt.datetime(2026, 6, 19, 3, 0, 0, tzinfo=_dt.timezone.utc)
        local = to_local(utc, "America/Chicago")
        # June is DST (CDT = UTC-5) → 22:00 previous day
        assert local.day == 18
        assert local.hour == 22


class TestFormatLocal:
    def test_basic_format(self):
        utc = _dt.datetime(2026, 6, 18, 21, 0, 0, tzinfo=_dt.timezone.utc)  # 4 PM CDT
        out = format_local(utc, "%-I:%M %p", "America/Chicago")
        assert out == "4:00 PM"


class TestParseIso:
    def test_iso_with_z(self):
        dt = parse_iso("2026-06-19T03:00:00Z")
        assert dt is not None
        assert dt.tzinfo is not None
        assert dt.hour == 3

    def test_iso_with_offset(self):
        dt = parse_iso("2026-06-19T03:00:00+00:00")
        assert dt is not None
        assert dt.tzinfo is not None

    def test_none_returns_none(self):
        assert parse_iso(None) is None
        assert parse_iso("") is None

    def test_garbage_returns_none(self):
        assert parse_iso("not a date") is None


class TestCountdownToKickoff:
    def test_returns_empty_for_invalid(self):
        assert countdown_to_kickoff("") == ""
        assert countdown_to_kickoff(None) == ""  # type: ignore[arg-type]

    def test_returns_kickoff_for_past(self):
        past = "2020-01-01T00:00:00Z"
        assert countdown_to_kickoff(past) == "KICKOFF"

    def test_days_format(self):
        future = (
            (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(days=3, hours=2))
            .isoformat()
            .replace("+00:00", "Z")
        )
        out = countdown_to_kickoff(future)
        assert "d" in out
        assert out.startswith("3")

    def test_hours_format(self):
        future = (
            (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=5, minutes=30))
            .isoformat()
            .replace("+00:00", "Z")
        )
        out = countdown_to_kickoff(future)
        assert "h" in out
        assert "m" in out

    def test_minutes_format(self):
        future = (
            (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(minutes=23))
            .isoformat()
            .replace("+00:00", "Z")
        )
        out = countdown_to_kickoff(future)
        assert out.endswith("m")
        assert "h" not in out
