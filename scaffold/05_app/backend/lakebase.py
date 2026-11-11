"""Lakebase (Postgres OLTP) access for low-latency single-VIN lookups.

The analytical estate (market_360, lending, fusion) is served from Unity Catalog
via the SQL warehouse (see db.py). The per-VIN point lookup that backs
`GET /api/vin/{vin}` is the app's hot path, so it is served from Lakebase Postgres
instead — a primary-key index lookup returns in well under a millisecond.

Connection follows the official Databricks Apps + Lakebase pattern: a psycopg
ConnectionPool whose connection class mints a fresh OAuth credential per physical
connection via WorkspaceClient.postgres.generate_database_credential(). In a
deployed app, PGHOST/PGUSER/PGPORT/PGDATABASE are injected by the attached
`postgres` (Lakebase) resource; ENDPOINT_NAME points at the compute endpoint.

If psycopg isn't installed or the Lakebase env vars aren't set, is_configured()
returns False and main.py transparently falls back to the SQL-warehouse path.
"""
import os

ENDPOINT_NAME = os.environ.get("ENDPOINT_NAME", "")
PGHOST = os.environ.get("PGHOST", "")
PGUSER = os.environ.get("PGUSER", "")
PGPORT = os.environ.get("PGPORT", "5432")
PGDATABASE = os.environ.get("PGDATABASE", "databricks_postgres")
PGSSLMODE = os.environ.get("PGSSLMODE", "require")
# Postgres copy maintained by the Lakebase synced table over the Lakeflow-built Delta
# source <catalog>.<schema>.vin_serving. The Postgres schema is the UC schema name.
LAKEBASE_TABLE = os.environ.get("LAKEBASE_TABLE", "experian_auto.vin_serving_online")

_pool = None
_init_error = None


def is_configured() -> bool:
    return bool(PGHOST and PGUSER and ENDPOINT_NAME) and _init_error is None


def _mint_token(w) -> str:
    """Mint a short-lived Lakebase OAuth credential for the app's service principal.

    Uses the generic API client (POST /api/2.0/postgres/credentials) so it works
    regardless of whether the installed databricks-sdk exposes the typed
    `w.postgres` surface.
    """
    resp = w.api_client.do(
        "POST", "/api/2.0/postgres/credentials",
        body={"endpoint": ENDPOINT_NAME},
    )
    return resp["token"]


def _build_pool():
    """Lazily build a connection pool that refreshes its OAuth token per connection."""
    global _pool, _init_error
    if _pool is not None or _init_error is not None:
        return
    try:
        import psycopg
        from psycopg_pool import ConnectionPool
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()

        class OAuthConnection(psycopg.Connection):
            @classmethod
            def connect(cls, conninfo="", **kwargs):
                kwargs["password"] = _mint_token(w)
                return super().connect(conninfo, **kwargs)

        _pool = ConnectionPool(
            conninfo=(f"dbname={PGDATABASE} user={PGUSER} host={PGHOST} "
                      f"port={PGPORT} sslmode={PGSSLMODE}"),
            connection_class=OAuthConnection,
            min_size=1,
            max_size=5,
            max_lifetime=2700,  # recycle before the 1-hour OAuth token expires
            open=True,
        )
    except Exception as e:  # psycopg missing, bad config, unreachable db
        _init_error = str(e)


# The serving row carries the display fields AND the full model feature set
# (local_* / segment_* + `state`), so the residual/default model calls work
# directly off the operational record.
_COLS = [
    "vin", "make", "model", "trim", "model_year", "mileage", "owner_count",
    "accident_count", "title_brand", "odometer_rollback_flag", "auction_count",
    "accs_score", "state", "garaged_state", "garaged_zip", "last_reported_date",
    "local_market_share_pct", "local_avg_days_to_turn", "local_vio_count",
    "segment_avg_apr", "segment_avg_ltv_pct", "segment_delinquency_rate",
    "segment_default_rate",
]


def get_vin(vin: str):
    """Return one vehicle dict from Lakebase, or None if not found.

    Raises if Lakebase isn't configured/reachable so the caller can fall back.
    """
    _build_pool()
    if _init_error:
        raise RuntimeError(f"Lakebase not available: {_init_error}")
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {', '.join(_COLS)} FROM {LAKEBASE_TABLE} WHERE vin = %s LIMIT 1",
                (vin,),
            )
            row = cur.fetchone()
    if not row:
        return None
    rec = dict(zip(_COLS, row))
    if rec.get("last_reported_date") is not None:
        rec["last_reported_date"] = rec["last_reported_date"].isoformat()
    return rec
