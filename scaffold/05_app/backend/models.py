"""Model Serving calls for residual value, days-to-turn, and default risk.

Each helper is best-effort: if the endpoint isn't reachable, it returns None (or leaves
the row unchanged) so the API still responds with the SQL data.
"""
import os
import requests
from databricks.sdk.core import Config

# In Databricks Apps the host env var is a bare hostname — normalize to a full URL.
_raw_host = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
HOST = _raw_host if _raw_host.startswith("http") else (f"https://{_raw_host}" if _raw_host else "")
ENDPOINT_RESIDUAL = os.environ.get("ENDPOINT_RESIDUAL", "experian-residual-value")
ENDPOINT_DTT = os.environ.get("ENDPOINT_DTT", "experian-days-to-turn")
ENDPOINT_DEFAULT = os.environ.get("ENDPOINT_DEFAULT", "experian-default-risk")


def _token() -> str:
    # App SP uses OAuth (Config().token is None) — mint a bearer via authenticate().
    cfg = Config()
    token = os.environ.get("DATABRICKS_TOKEN") or cfg.token
    if not token:
        token = cfg.authenticate().get("Authorization", "").removeprefix("Bearer ").strip()
    return token


def _invoke(endpoint: str, record: dict):
    if not HOST:
        return None
    url = f"{HOST}/serving-endpoints/{endpoint}/invocations"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        json={"dataframe_records": [record]},
        timeout=20,
    )
    resp.raise_for_status()
    preds = resp.json().get("predictions")
    return preds[0] if preds else None


# The residual / default models were trained on the per-VIN fusion feature set.
# The operational record carries display fields too, so send only these columns.
_VIN_FEATURES = [
    "make", "model", "title_brand", "state", "model_year", "mileage",
    "owner_count", "accident_count", "auction_count", "accs_score",
    "local_market_share_pct", "local_avg_days_to_turn", "local_vio_count",
    "segment_avg_apr", "segment_avg_ltv_pct", "segment_default_rate",
    "segment_delinquency_rate",
]


def _features(vehicle: dict) -> dict:
    return {k: vehicle[k] for k in _VIN_FEATURES if k in vehicle}


def predict_residual(vehicle: dict):
    try:
        return round(float(_invoke(ENDPOINT_RESIDUAL, _features(vehicle))), 0)
    except Exception:
        return None


def predict_default(vehicle: dict):
    try:
        return round(float(_invoke(ENDPOINT_DEFAULT, _features(vehicle))), 4)
    except Exception:
        return None


def enrich_days_to_turn(rows: list[dict]) -> list[dict]:
    for r in rows:
        try:
            pred = _invoke(ENDPOINT_DTT, r)
            if pred is not None:
                r["predicted_days_to_turn"] = round(float(pred))
        except Exception:
            pass
    return rows
