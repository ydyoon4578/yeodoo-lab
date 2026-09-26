# -*- coding: utf-8 -*-
"""Phase 2 (before --merge) -- restore the pre-exit price history of names that just LEFT the lab universe.

Why: refresh_stocks deletes data/sd/<T>.json when T leaves stocks.json, and pit_px_refresh then adds T to
data/pit_px.json only from its last recorded day (its own warning: «새로 들어온 편출 이름 … 편입 기간 과거 가격이
없다(편출 전 sd 이력을 넘겨야 한다)»). The 2026-09 rebalance drops BLDR · TAP · TTD. Without their history the
DB fill (--merge) would fill only 2025-04-16.. from the company DB, mark them closed, and T would lose members.

What (the build/pit_px_repair.py BACKFILL rule, generalised, idempotent):
  for each T: source = the commit just before data/sd/T.json was deleted on the given ref (git log --diff-filter=D);
  series = that commit's sd pxd on that commit's stocks.json pxd_dates; days are placed on THIS pit_px.json's grid
  (rec["dates"], unchanged); only EMPTY days before the key's first value are added (never overwrite); the boundary
  day must agree within 0.5% (else stop -- another security); repairs[T] records source, counts and boundary.
  No same-day overlap (2026-09-26: CI deleted sd/T.json in the same run that brought the record's first close, so
  the sd history ends the grid day BEFORE the record starts): the check bridges through the SAME commit's intraday
  file data/id/T.json of the record's first day -- its previous close must equal the sd last close and its last bar
  the record's first close, both within 0.5% (two same-day comparisons); otherwise stop as above.
usage: python -X utf8 p2_leaver_backfill.py --lab LAB [--ref origin/main] [--tickers BLDR,TAP,TTD] [--dry]
       without --tickers: T = keys of pit_px.json with no data/sd/T.json whose first value is within 15 days of the
       grid end and whose sd file existed on --ref's history.
"""
import argparse
import datetime as dt
import io
import json
import os
import subprocess
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TOL = 0.005
ap = argparse.ArgumentParser()
ap.add_argument("--lab", required=True)
ap.add_argument("--ref", default="origin/main")
ap.add_argument("--tickers")
ap.add_argument("--dry", action="store_true")
a = ap.parse_args()
OUT = os.path.join(a.lab, "data", "pit_px.json")


def git(*args):
    r = subprocess.run(["git", "-C", a.lab] + list(args), capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", "replace").strip()


def git_json(commit, path):
    rc, out = git("show", "%s:%s" % (commit, path))
    if rc:
        raise SystemExit("git show %s:%s failed" % (commit, path))
    return json.loads(out)


rec = json.load(io.open(OUT, encoding="utf-8"))
dates, px = rec["dates"], rec["px"]
di = {d: i for i, d in enumerate(dates)}
if a.tickers:
    cand = [t.strip() for t in a.tickers.split(",") if t.strip()]
else:
    lim = (dt.date.fromisoformat(dates[-1]) - dt.timedelta(days=15)).isoformat()
    cand = [k for k, o in sorted(px.items()) if "@" not in k and dates[o["i0"]] >= lim
            and not os.path.exists(os.path.join(a.lab, "data", "sd", k + ".json"))]
repairs = dict(rec.get("repairs") or {})
today = dt.date.today().isoformat()
changed = []
for t in cand:
    rc, dcommit = git("log", "-1", "--format=%H", "--diff-filter=D", a.ref, "--", "data/sd/%s.json" % t)
    if rc or not dcommit:
        print("  %s: no deletion of data/sd/%s.json on %s -- skipped" % (t, t, a.ref))
        continue
    src = dcommit + "^"
    st = git_json(src, "data/stocks.json")
    sd = git_json(src, "data/sd/%s.json" % t)
    dd = st["pxd_dates"]
    if len(sd.get("pxd") or []) != len(dd):
        raise SystemExit("%s: sd length %d != grid %d at %s" % (t, len(sd.get("pxd") or []), len(dd), src))
    ser = {d: p for d, p in zip(dd, sd["pxd"]) if p}
    o = px.get(t)
    arr = [None] * len(dates)
    if o:
        for j, v in enumerate(o["p"]):
            arr[o["i0"] + j] = v
    have = [i for i, v in enumerate(arr) if v is not None]
    first = dates[have[0]] if have else None
    bnd = None
    if first:
        ref_d = first if first in ser else max(d for d in ser if d <= first) if any(d <= first for d in ser) else None
        if ref_d is None:
            raise SystemExit("%s: sd history does not reach the record's first day %s" % (t, first))
        ratio = arr[have[0]] / ser[ref_d]
        bnd = {"sd_date": ref_d, "sd": ser[ref_d], "record_date": first, "record": arr[have[0]], "ratio": round(ratio, 6)}
        if abs(ratio - 1.0) > TOL:
            br = None
            if ref_d != first and ref_d in di and di[first] - di[ref_d] == 1:
                rc_i, out_i = git("show", "%s:data/id/%s.json" % (src, t))
                idj = json.loads(out_i) if rc_i == 0 and out_i else None
                bars = [x for x in (idj or {}).get("c") or [] if x is not None]
                if idj and idj.get("d") == first and idj.get("pc") and bars:
                    r1, r2 = idj["pc"] / ser[ref_d], arr[have[0]] / bars[-1]
                    br = {"via": "git %s^:data/id/%s.json" % (dcommit[:12], t),
                          "id_d": idj["d"], "pc": idj["pc"], "last_bar": bars[-1],
                          "pc_vs_sd": round(r1, 6), "record_vs_last_bar": round(r2, 6)}
                    if abs(r1 - 1.0) > TOL or abs(r2 - 1.0) > TOL:
                        br = None
            if br is None:
                raise SystemExit("%s: boundary mismatch %s -- maybe another security; stop" % (t, bnd))
            bnd["bridge"] = br
    add = {d: p for d, p in ser.items() if d in di and (first is None or d < first) and arr[di[d]] is None}
    if not add:
        print("  %s: nothing to add (first %s)" % (t, first))
        continue
    for d, p in add.items():
        arr[di[d]] = p
    idx = [i for i, v in enumerate(arr) if v is not None]
    px[t] = {"i0": idx[0], "p": arr[idx[0]:idx[-1] + 1]}
    prev = repairs.get(t) or {}
    repairs[t] = {"date": prev.get("date") or today,
                  "why": "2026-09 분기 변경으로 오늘 유니버스를 떠나 data/sd/%s.json 이 지워졌다 — pit_px_refresh 가 "
                         "마지막 기록일부터만 받아 편입 기간 과거 가격이 없었다. 지워지기 직전 커밋의 sd 에서 되살린다" % t,
                  "backfill_from": "git %s^:data/sd/%s.json" % (dcommit[:12], t),
                  "n_added": (prev.get("n_added") or 0) + len(add),
                  "range_added": prev.get("range_added") or [min(add), max(add)],
                  "boundary": prev.get("boundary") or bnd}
    changed.append(t)
    print("  %s +%d days %s..%s from %s^ · boundary %s" % (t, len(add), min(add), max(add), dcommit[:12], bnd))
if changed and not a.dry:
    rec["px"] = dict(sorted(px.items()))
    rec["repairs"] = repairs
    cov = dict(rec.get("coverage") or {})
    if cov:
        cov["n_tickers"] = len(rec["px"])
        cov["n_points"] = sum(sum(1 for x in o["p"] if x is not None) for o in rec["px"].values())
        rec["coverage"] = cov
    io.open(OUT, "w", encoding="utf-8", newline="").write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
print("restored: %s%s" % (changed or "none", " (dry run)" if a.dry else ""))
