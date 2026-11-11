"""Unity Catalog access via a Databricks SQL warehouse."""
import os

CATALOG = os.environ.get("CATALOG", "")
SCHEMA = os.environ.get("SCHEMA", "experian_auto")
HOST = os.environ.get("DATABRICKS_HOST", "").replace("https://", "").rstrip("/")
WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
TOKEN = os.environ.get("DATABRICKS_TOKEN", "")


def tbl(name: str) -> str:
    return f"{CATALOG}.{SCHEMA}.{name}"


def is_configured() -> bool:
    return bool(HOST and WAREHOUSE_ID)


def query(sql: str, params: dict) -> list[dict]:
    """Run a parameterized query and return rows as dicts.

    Raises if the warehouse isn't configured — callers fall back to sample data.
    """
    if not is_configured():
        raise RuntimeError("SQL warehouse not configured (set DATABRICKS_HOST/WAREHOUSE_ID)")

    from databricks import sql as dbsql
    from databricks.sdk.core import Config

    # In Databricks Apps the identity is an OAuth service principal, so Config().token
    # is None — mint a bearer via authenticate() and extract it. Fall back to a PAT
    # (DATABRICKS_TOKEN) or Config().token for local/dev runs.
    cfg = Config()
    token = TOKEN or cfg.token
    if not token:
        auth_headers = cfg.authenticate()  # returns {"Authorization": "Bearer <token>"}
        token = auth_headers.get("Authorization", "").removeprefix("Bearer ").strip()

    conn = dbsql.connect(
        server_hostname=HOST,
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        access_token=token,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()
