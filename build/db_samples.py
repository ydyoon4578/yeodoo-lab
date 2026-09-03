# -*- coding: utf-8 -*-
"""build/db_samples.py — 사내 DB 지도에 실을 **표본 몇 줄**을 모은다. 로컬 전용.

왜 필요한가. 설명 한 줄로는 그 테이블이 실제로 어떤 값을 담는지 안 보인다. 특히
코드표(id ↔ 이름)는 값을 한 번 보는 편이 어떤 설명보다 빠르다. 그래서 테이블마다
앞 5행을 떠서 페이지에 함께 싣는다.

두 가지를 지킨다.
  ① **컬럼은 앞 8개만.** 재무 테이블은 컬럼이 540~938개다. 전부 뜨면 표가 아니라 벽이 된다.
  ② **값은 서버에서 자른다.** `left(col::text, 40)` 로 보내므로 공시 원문 같은 대용량
     TOAST 컬럼을 통째로 끌어오지 않는다. 이걸 클라이언트에서 자르면 이미 늦다.

접속은 MCP 게이트웨이(HTTP)를 그대로 쓴다 — 5432 직결은 이 PC에서 막혀 있다.
출력 build/db_samples.json 은 gitignore 다(사내 데이터).

    python build/db_samples.py            전 DB
    python build/db_samples.py kbam-dart  한 곳만
"""
from __future__ import annotations
import io, json, os, ssl, sys, time, urllib.request

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "build", "db_samples.json")
CAT  = os.path.join(ROOT, "build", "db_catalog.json")
NOTES = os.path.join(ROOT, "build", "db_notes.json")

# 🚨 게이트웨이 주소는 여기 적지 않는다 — 이 파일은 공개 저장소에 추적되고,
#   validate_site.py 가 사내망 IP 리터럴을 실패로 잡는다(실제로 잡혔다).
#   주소와 인증서 경로는 gitignore 되는 build/db_notes.json 의 mcp 블록에서 읽는다.
def _conf():
    if not os.path.exists(NOTES):
        sys.exit("build/db_notes.json 이 없다 — mcp.base 와 mcp.ca 를 적어 둘 것(로컬 전용 파일)")
    m = (json.load(io.open(NOTES, encoding="utf-8")) or {}).get("mcp") or {}
    if not m.get("base"):
        sys.exit("db_notes.json 에 mcp.base 가 없다")
    return m["base"], m.get("ca") or os.path.join(
        os.path.expanduser("~"), ".claude", "certs", "kbam-mcp.crt")


BASE, CA = _conf()

NCOL, NROW, CELL = 8, 5, 40

ctx = ssl.create_default_context(cafile=CA)
ctx.check_hostname = False          # 자체서명·SAN 없음 — 체인 검증은 유지


def _post(url, payload, sid=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if sid: req.add_header("mcp-session-id", sid)
    with urllib.request.urlopen(req, context=ctx, timeout=90) as r:
        return r.headers.get("mcp-session-id"), r.read().decode("utf-8", "replace")


class Session:
    """DB 하나에 대한 MCP 세션. 테이블마다 새로 열면 345번 핸드셰이크가 된다."""
    def __init__(self, db):
        self.url = BASE + db
        self.sid, _ = _post(self.url, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "samples", "version": "1"}}})
        try: _post(self.url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, self.sid)
        except Exception: pass

    def query(self, sql):
        _, raw = _post(self.url, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "run_query", "arguments": {"sql": sql}}}, self.sid)
        for line in raw.splitlines():
            if line.startswith("data:"):
                msg = json.loads(line[5:].strip())
                if "error" in msg: raise RuntimeError(str(msg["error"])[:160])
                txt = "".join(c.get("text", "") for c in msg["result"].get("content", [])
                              if c.get("type") == "text")
                if msg["result"].get("isError"): raise RuntimeError(txt[:160])
                return json.loads(txt)
        raise RuntimeError("응답 파싱 실패")


# 🚨 run_query 는 1000행에서 자른다. 컬럼 목록은 컬럼 하나가 한 행이라 그냥 물으면
#   938열짜리 재무 테이블 몇 개가 예산을 다 먹고 나머지 테이블이 통째로 빈다(실제로 82개가 그랬다).
#   그래서 ① 앞 NCOL 개만 받고 ② OFFSET 으로 나눠 받는다.
COLSQL = """SELECT n.nspname AS s, c.relname AS t, a.attname AS col
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
WHERE c.relkind IN ('r','v','m','p') AND n.nspname NOT IN ('pg_catalog','information_schema')
  AND a.attnum <= %d
ORDER BY n.nspname, c.relname, a.attnum
LIMIT %d OFFSET %d"""

NCOLSQL = """SELECT n.nspname AS s, c.relname AS t, count(*)::int AS ncol
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
WHERE c.relkind IN ('r','v','m','p') AND n.nspname NOT IN ('pg_catalog','information_schema')
GROUP BY 1,2 ORDER BY 1,2"""

PAGE = 900


def collect(db, tables):
    s = Session(db)
    cols, off = {}, 0
    while True:
        page = s.query(COLSQL % (NCOL, PAGE, off))
        for r in page:
            cols.setdefault((r["s"], r["t"]), []).append(r["col"])
        if len(page) < PAGE: break
        off += PAGE
    ncols = {(r["s"], r["t"]): r["ncol"] for r in s.query(NCOLSQL)}
    out, ok, err = {}, 0, 0
    for schema, table in tables:
        key = "%s.%s" % (schema, table)
        cl = cols.get((schema, table), [])[:NCOL]
        if not cl:
            out[key] = {"error": "컬럼을 못 찾음"}; err += 1; continue
        # 값 절단은 서버에서 — 대용량 TOAST 컬럼을 끌어오지 않기 위해
        sel = ", ".join('left(%s::text, %d) AS %s' % ('"%s"' % c, CELL, '"%s"' % c) for c in cl)
        try:
            rows = s.query('SELECT %s FROM "%s"."%s" LIMIT %d' % (sel, schema, table, NROW))
            out[key] = {"cols": cl, "rows": [[r.get(c) for c in cl] for r in rows],
                        "ncol_total": ncols.get((schema, table), len(cl))}
            ok += 1
        except Exception as e:
            out[key] = {"error": str(e)[:120]}; err += 1
        time.sleep(0.05)
    print("  %-16s 표본 %d · 실패 %d" % (db, ok, err))
    return out


def main(argv):
    cat = json.load(io.open(CAT, encoding="utf-8"))
    dbs = argv or list(cat)
    res = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    for db in dbs:
        ts = cat.get(db) or []
        keep = [(t["schema_name"], t["table_name"]) for t in ts
                if not t["table_name"].startswith(("tmptable_", "awsdms_", "_"))
                and t["schema_name"] != "cron"]
        try:
            res[db] = collect(db, keep)
        except Exception as e:
            print("  %-16s 세션 실패: %s" % (db, e))
        io.open(OUT, "w", encoding="utf-8", newline="").write(json.dumps(res, ensure_ascii=False))
    print("기록:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
