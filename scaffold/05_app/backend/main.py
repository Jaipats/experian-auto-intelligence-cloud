"""
Inventory & Risk Co-Pilot — FastAPI backend.

Four API groups back the four UI modules:
  GET  /api/acquire        -> ranked acquisition candidates (market_360 + days_to_turn model)
  GET  /api/vin/{vin}      -> per-VIN condition + residual + default risk
  GET  /api/market-radar   -> lending share shifts / underserved segments
  POST /api/ask            -> proxy a natural-language question to the Genie space

The backend queries Unity Catalog through a Databricks SQL warehouse, calls Model Serving
endpoints, and proxies to the Genie Conversations API. If dependencies/resources aren't
configured yet, each endpoint returns illustrative sample data so the UI is demoable
standalone (see data.py).
"""
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db, models, genie, data, lakebase

app = FastAPI(title="Experian Auto Intelligence — Inventory & Risk Co-Pilot")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.get("/api/health")
def health():
    return {"status": "ok", "sql_configured": db.is_configured(),
            "genie_configured": genie.is_configured(),
            "lakebase_configured": lakebase.is_configured()}


@app.get("/api/acquire")
def acquire(state: str = "CA", body_style: str = "SUV", limit: int = 10):
    """Ranked acquisition candidates for a dealer's geography."""
    try:
        rows = db.query(
            f"""
            SELECT make, model, model_year, body_style, state,
                   avg_days_to_turn, market_share_pct, avg_accs_score, clean_title_rate,
                   avg_orig_amount
            FROM {db.tbl('analytics_market_360')}
            WHERE state = %(state)s AND body_style = %(body_style)s
              AND snapshot_month = (SELECT MAX(snapshot_month) FROM {db.tbl('analytics_market_360')})
            ORDER BY avg_days_to_turn ASC, market_share_pct DESC
            LIMIT %(limit)s
            """,
            {"state": state, "body_style": body_style, "limit": limit},
        )
        # enrich with a predicted days-to-turn from the model (best-effort)
        rows = models.enrich_days_to_turn(rows)
        return {"source": "live", "rows": rows}
    except Exception as e:
        return {"source": "sample", "note": str(e), "rows": data.SAMPLE_ACQUIRE}


@app.get("/api/vin/{vin}")
def vin_detail(vin: str):
    """Per-VIN condition + residual value + segment default risk.

    Served from Lakebase Postgres (operational hot path, sub-ms PK lookup) when
    configured; falls back to the Unity Catalog SQL warehouse, then to sample data.
    """
    served_by = None
    vehicle = None
    try:
        # 1) operational serving from Lakebase (preferred)
        if lakebase.is_configured():
            vehicle = lakebase.get_vin(vin)
            served_by = "lakebase"
        # 2) fall back to the analytical warehouse if Lakebase is unavailable
        if vehicle is None and served_by != "lakebase":
            rows = db.query(
                f"SELECT * FROM {db.tbl('gold_autocheck_vin')} WHERE vin = %(vin)s LIMIT 1",
                {"vin": vin},
            )
            vehicle = rows[0] if rows else None
            served_by = "warehouse"
        if vehicle is None:
            return JSONResponse({"error": "VIN not found"}, status_code=404)
        vehicle["predicted_residual_value"] = models.predict_residual(vehicle)
        vehicle["segment_default_risk"] = models.predict_default(vehicle)
        return {"source": "live", "served_by": served_by, "vehicle": vehicle}
    except Exception as e:
        # last-resort warehouse attempt if Lakebase raised, else sample
        try:
            rows = db.query(
                f"SELECT * FROM {db.tbl('gold_autocheck_vin')} WHERE vin = %(vin)s LIMIT 1",
                {"vin": vin},
            )
            if rows:
                vehicle = rows[0]
                vehicle["predicted_residual_value"] = models.predict_residual(vehicle)
                vehicle["segment_default_risk"] = models.predict_default(vehicle)
                return {"source": "live", "served_by": "warehouse",
                        "note": f"lakebase fallback: {e}", "vehicle": vehicle}
        except Exception:
            pass
        return {"source": "sample", "note": str(e), "vehicle": data.SAMPLE_VIN}


@app.get("/api/market-radar")
def market_radar(region: str = "Midwest"):
    """Lending share by lender type + underserved (high days-to-turn, low lender count) segments."""
    try:
        share = db.query(
            f"""
            SELECT lender_type, COUNT(*) AS loans,
                   ROUND(AVG(apr),2) AS avg_apr,
                   ROUND(AVG(delinquency_30d_flag),3) AS delinquency_rate
            FROM {db.tbl('gold_lending')}
            WHERE region = %(region)s
            GROUP BY lender_type ORDER BY loans DESC
            """,
            {"region": region},
        )
        underserved = db.query(
            f"""
            SELECT make, model, model_year, avg_days_to_turn, lender_count, market_share_pct
            FROM {db.tbl('analytics_market_360')}
            WHERE lender_count IS NOT NULL
            ORDER BY (avg_days_to_turn / NULLIF(lender_count,0)) DESC
            LIMIT 10
            """,
            {},
        )
        return {"source": "live", "lender_share": share, "underserved": underserved}
    except Exception as e:
        return {"source": "sample", "note": str(e),
                "lender_share": data.SAMPLE_LENDER_SHARE,
                "underserved": data.SAMPLE_UNDERSERVED}


class AskBody(BaseModel):
    question: str
    conversation_id: str | None = None


@app.post("/api/ask")
def ask(body: AskBody):
    """Proxy a natural-language question to the Genie space (blocking, full payload)."""
    try:
        return {"source": "live", **genie.ask(body.question, body.conversation_id)}
    except Exception as e:
        return {"source": "sample", "note": str(e), **data.SAMPLE_ASK}


@app.post("/api/ask/stream")
def ask_stream(body: AskBody):
    """Stream Genie's progress (status stepper) then the full result via SSE.

    Falls back to a single sample event if Genie isn't reachable.
    """
    if not genie.is_configured():
        import json as _json

        def _sample():
            yield f"data: {_json.dumps({'type':'status','status':'COMPLETED','label':'Done'})}\n\n"
            yield f"data: {_json.dumps({'type':'result','source':'sample',**data.SAMPLE_ASK})}\n\n"

        return StreamingResponse(_sample(), media_type="text/event-stream")

    def _gen():
        try:
            for chunk in genie.ask_stream(body.question, body.conversation_id):
                yield chunk
        except Exception as e:
            import json as _json
            yield f"data: {_json.dumps({'type':'error','message':str(e)})}\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")


# ---- serve the frontend ----
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
