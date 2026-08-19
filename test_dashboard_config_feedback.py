from pathlib import Path


def test_static_dashboard_preserves_422_rejection_details():
    html = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")

    assert "r.status !== 422" in html
    assert "Object.keys(rejectedRaw)" in html
    assert "Configuration partiellement refusée" in html
