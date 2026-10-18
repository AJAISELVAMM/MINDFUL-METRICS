from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ml.burnout_model import score_from_proba
from app.ml.preprocessing import validate_frame
from app.main import app
from app.services.recommendation_service import recommendations_from_factors
from fastapi.testclient import TestClient
import pandas as pd

client = TestClient(app)


def test_score_mapping():
    s, level, p, c = score_from_proba(["LOW", "MODERATE", "HIGH"], [0.1, 0.2, 0.7])
    assert 0 <= s <= 100
    assert level in ("LOW", "MODERATE", "HIGH")
    assert abs(p["high"] - 0.7) < 1e-6


def test_validate_requires_label():
    try:
        validate_frame(pd.DataFrame({"stress_score": [1]}))
        assert False
    except ValueError:
        pass


def test_recs():
    r = recommendations_from_factors([{"feature": "workload_score", "importance": 0.3}], "HIGH")
    assert any("task" in x.lower() or "allocation" in x.lower() for x in r)


def test_health_endpoint():
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'


if __name__ == "__main__":
    test_score_mapping()
    test_validate_requires_label()
    test_recs()
    test_health_endpoint()
    print("ok")
