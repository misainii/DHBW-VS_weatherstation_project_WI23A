import gzip

import requests

from app.aws_client import AWSGHCNClient


class _DummyResponse:
    def __init__(self, status_code=200, content=b"", exc=None):
        self.status_code = status_code
        self.content = content
        self._exc = exc

    def raise_for_status(self):
        if self._exc is not None:
            raise self._exc


def test_parse_csv_bytes_supports_gzip_payloads():
    client = AWSGHCNClient()
    raw_csv = (
        "GME00102380,20200101,TMIN,15,,,\n"
        "GME00102380,20200102,TMAX,35,,,\n"
    ).encode("utf-8")

    rows = client._parse_csv_bytes(gzip.compress(raw_csv), "https://example.test/file.csv.gz")

    assert len(rows) == 2
    assert rows[0]["value"] == 1.5
    assert rows[1]["element"] == "TMAX"


def test_parse_csv_bytes_skips_invalid_and_flagged_rows():
    client = AWSGHCNClient()
    raw_csv = (
        "GME00102380,20200101,TMIN,15,,,\n"
        "GME00102380,20200102,TMAX,-9999,,,\n"
        "GME00102380,20200103,TMAX,35,,X,\n"
        "GME00102380,broken,TMIN,17,,,\n"
        "GME00102380,20200104,PRCP,99,,,\n"
    ).encode("utf-8")

    rows = client._parse_csv_bytes(raw_csv, "https://example.test/file.csv")

    assert rows == [
        {
            "station_id": "GME00102380",
            "date": "20200101",
            "year": 2020,
            "month": 1,
            "day": 1,
            "element": "TMIN",
            "value": 1.5,
            "qflag": None,
        }
    ]


def test_fetch_bytes_returns_none_on_404(monkeypatch):
    client = AWSGHCNClient()

    monkeypatch.setattr(
        client._session,
        "get",
        lambda url, timeout: _DummyResponse(status_code=404),
    )

    assert client._fetch_bytes("https://example.test/missing") is None


def test_fetch_bytes_retries_until_success(monkeypatch):
    client = AWSGHCNClient(max_retries=3)
    calls = {"count": 0}

    def fake_get(url, timeout):
        calls["count"] += 1
        if calls["count"] < 3:
            raise requests.RequestException("temporary failure")
        return _DummyResponse(content=b"ok")

    monkeypatch.setattr(client._session, "get", fake_get)

    data = client._fetch_bytes("https://example.test/retry")

    assert data == b"ok"
    assert calls["count"] == 3


def test_get_station_period_data_uses_cache(monkeypatch):
    client = AWSGHCNClient()
    calls = {"count": 0}

    def fake_fetch_bytes(url):
        calls["count"] += 1
        return b"GME00102380,20200101,TMIN,15,,,\n"

    monkeypatch.setattr(client, "_fetch_bytes", fake_fetch_bytes)

    first = client.get_station_period_data("GME00102380")
    second = client.get_station_period_data("GME00102380")

    assert first == second
    assert calls["count"] == 1
