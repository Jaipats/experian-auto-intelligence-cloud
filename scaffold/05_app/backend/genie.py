"""Proxy natural-language questions to a Databricks Genie space via the
Conversations API, exposing the full transparency payload: status progression,
Genie's thoughts/interpretation, the generated SQL, the result table, and
suggested follow-up questions.

The Genie REST API is poll-based (not token-streaming), so `ask()` returns the
completed result and `ask_stream()` yields Server-Sent Events as the message
moves through its statuses for a live UI.
"""
import os
import json
import time
import requests
from databricks.sdk.core import Config

# In Databricks Apps the host env var is a bare hostname — normalize to a full URL.
_raw_host = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
HOST = _raw_host if _raw_host.startswith("http") else (f"https://{_raw_host}" if _raw_host else "")
# Either pin the space id, or let the app resolve it by title at runtime. The bundle's
# job creates the space (07_orchestration/notebooks/05_create_genie_space.py) and grants
# the app's service principal CAN_RUN, so a fresh deployment needs no hardcoded id.
SPACE_ID = os.environ.get("GENIE_SPACE_ID", "")
SPACE_TITLE = os.environ.get("GENIE_SPACE_TITLE", "")
_resolved_space_id = None

# Human-friendly labels for Genie's internal statuses (shown in the UI stepper).
STATUS_LABELS = {
    "FILTERING_CONTEXT": "Understanding the question",
    "ASKING_AI": "Generating SQL",
    "PENDING_WAREHOUSE": "Running the query",
    "EXECUTING_QUERY": "Running the query",
    "COMPLETED": "Done",
    "FAILED": "Failed",
    "CANCELLED": "Cancelled",
}


def is_configured() -> bool:
    return bool(HOST and (SPACE_ID or SPACE_TITLE))


def _space_id() -> str:
    """Pinned GENIE_SPACE_ID, else the space whose title is GENIE_SPACE_TITLE (cached)."""
    global _resolved_space_id
    if SPACE_ID:
        return SPACE_ID
    if _resolved_space_id:
        return _resolved_space_id
    page_token = None
    while True:
        params = {"page_token": page_token} if page_token else {}
        r = requests.get(f"{HOST}/api/2.0/genie/spaces", headers=_headers(),
                         params=params, timeout=30)
        r.raise_for_status()
        body = r.json()
        for sp in body.get("spaces", []):
            if sp.get("title") == SPACE_TITLE:
                _resolved_space_id = sp.get("space_id") or sp.get("id")
                return _resolved_space_id
        page_token = body.get("next_page_token")
        if not page_token:
            raise RuntimeError(f"Genie space titled {SPACE_TITLE!r} not found "
                               "(has the job's create_genie_space task run?)")


def _headers():
    # App SP uses OAuth (Config().token is None) — mint a bearer via authenticate().
    cfg = Config()
    token = os.environ.get("DATABRICKS_TOKEN") or cfg.token
    if not token:
        token = cfg.authenticate().get("Authorization", "").removeprefix("Bearer ").strip()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _base():
    return f"{HOST}/api/2.0/genie/spaces/{_space_id()}"


def _start(question: str, conversation_id: str | None):
    if conversation_id:
        r = requests.post(f"{_base()}/conversations/{conversation_id}/messages",
                          headers=_headers(), json={"content": question}, timeout=30)
    else:
        r = requests.post(f"{_base()}/start-conversation",
                          headers=_headers(), json={"content": question}, timeout=30)
    r.raise_for_status()
    s = r.json()
    cid = s.get("conversation_id") or s.get("conversation", {}).get("id")
    mid = s.get("message_id") or s.get("message", {}).get("id")
    return cid, mid


def _get_message(cid: str, mid: str) -> dict:
    return requests.get(f"{_base()}/conversations/{cid}/messages/{mid}",
                        headers=_headers(), timeout=30).json()


def _fetch_result(cid: str, mid: str, attachment_id: str) -> dict:
    """Fetch the tabular result for a query attachment. Returns {columns, rows}."""
    try:
        r = requests.get(
            f"{_base()}/conversations/{cid}/messages/{mid}/attachments/{attachment_id}/query-result",
            headers=_headers(), timeout=30)
        r.raise_for_status()
        sr = r.json().get("statement_response", {})
        cols = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
        rows = sr.get("result", {}).get("data_array", []) or []
        return {"columns": cols, "rows": rows}
    except Exception:
        return {"columns": [], "rows": []}


def _parse_message(cid: str, mid: str, msg: dict) -> dict:
    """Pull the full transparency payload out of a completed Genie message."""
    answer, sql, description, thoughts = "", "", "", ""
    row_count, result, suggested = None, {"columns": [], "rows": []}, []

    for att in msg.get("attachments", []):
        if "text" in att and att["text"].get("content"):
            # first text attachment = the answer; keep the longest as the main answer
            c = att["text"]["content"]
            if len(c) > len(answer):
                answer = c
        if "query" in att:
            q = att["query"]
            sql = q.get("query", sql)
            description = q.get("description", description)
            row_count = (q.get("query_result_metadata") or {}).get("row_count", row_count)
            # thoughts is a list of {thought_type, content}
            th = q.get("thoughts")
            if isinstance(th, list):
                thoughts = "\n\n".join(
                    t.get("content", "") for t in th if t.get("content"))
            aid = att.get("attachment_id")
            if aid:
                result = _fetch_result(cid, mid, aid)
        if "suggested_questions" in att:
            suggested = att["suggested_questions"].get("questions", []) or []

    return {
        "conversation_id": cid,
        "message_id": mid,
        "answer": answer,
        "description": description,
        "thoughts": thoughts,
        "sql": sql,
        "row_count": row_count,
        "result": result,
        "suggested_questions": suggested,
    }


def ask(question: str, conversation_id: str | None = None) -> dict:
    """Blocking: start a question, poll to completion, return the full payload."""
    if not is_configured():
        raise RuntimeError("Genie not configured (set GENIE_SPACE_ID or GENIE_SPACE_TITLE, and DATABRICKS_HOST)")
    cid, mid = _start(question, conversation_id)
    for _ in range(60):
        msg = _get_message(cid, mid)
        if msg.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
            payload = _parse_message(cid, mid, msg)
            payload["status"] = msg.get("status")
            return payload
        time.sleep(1)
    return {"conversation_id": cid, "message_id": mid, "status": "TIMEOUT",
            "answer": "", "sql": "", "thoughts": "", "description": "",
            "result": {"columns": [], "rows": []}, "suggested_questions": []}


def ask_stream(question: str, conversation_id: str | None = None):
    """Generator yielding Server-Sent Events as the message progresses.

    Emits {type: 'status', ...} on each status transition and a final
    {type: 'result', ...} with the full payload.
    """
    if not is_configured():
        yield _sse({"type": "error", "message": "Genie not configured"})
        return
    cid, mid = _start(question, conversation_id)
    last_status = None
    for _ in range(90):
        msg = _get_message(cid, mid)
        status = msg.get("status")
        if status != last_status:
            last_status = status
            yield _sse({"type": "status", "status": status,
                        "label": STATUS_LABELS.get(status, status)})
        if status in ("COMPLETED", "FAILED", "CANCELLED"):
            payload = _parse_message(cid, mid, msg)
            payload["type"] = "result"
            payload["status"] = status
            yield _sse(payload)
            return
        time.sleep(1)
    yield _sse({"type": "result", "status": "TIMEOUT", "answer": "",
                "sql": "", "thoughts": "", "description": "",
                "result": {"columns": [], "rows": []}, "suggested_questions": []})


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"
