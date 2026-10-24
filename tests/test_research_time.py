from datetime import datetime

from solo_harness.research_export import _json_value


def test_research_timestamp_is_serialized_in_ist():
    value = datetime.fromisoformat("2026-10-18T19:33:47.585669+00:00")
    rendered = _json_value(value, "started_at")
    assert rendered == "2026-10-19T01:03:47.585669+05:30"
    assert datetime.fromisoformat(rendered).tzinfo is not None


def test_explicit_utc_field_remains_utc():
    value = datetime.fromisoformat("2026-10-18T19:33:47.585669+00:00")
    assert _json_value(value, "observed_at_utc") == "2026-10-18T19:33:47.585669+00:00"
