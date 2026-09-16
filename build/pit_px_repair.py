# -*- coding: utf-8 -*-
"""편출 가격 기록(data/pit_px.json) 일회성 수리 — 2026-09-14. 다시 돌려도 결과가 같다(멱등).

발견 경위: PREREG-2026-09-14-DNBETA 의 생존편향 수치를 의심해 편출 종목 137종을 전수 점검했다.

① AVB·EQR — **과거 가격 복구.** 둘은 2026-08-17 합병해 Vivmark Residential(VMRK)이 됐다
   (AVB 1주 → EQR 2.793주 · EQR 이 VMRK 로 개명). 오늘 유니버스를 떠나면서
   refresh_stocks.py 가 data/sd/AVB.json · EQR.json 을 지웠고, pit_px_refresh.py 는 새 이름을
   «기록의 마지막 날짜부터» 만 받아(주석은 «전체를 받는다» 였다) 편입 12년치(2014-06~2026-08)
   가격이 랩 어디에도 없었다. 지워지기 직전 커밋(a40bcf060^)의 sd 파일에서 되살린다.
② AVB — **전환 뒤 꼬리 제거.** 야후 AVB 가 08-21 부터 전환 뒤 가격을 줘 기록의 08-20 값 184.06
   뒤에 65.90 이 붙었다(184.06 ÷ 65.90 = 2.793 — 전환비 그대로). 하루 −64% 는 가짜다.
   08-20 뒤 값을 지운다(편출 규약 «끊기면 마지막 가격까지» 와 같다).
③ PARA·COL — **격리.** 편입 기간 전체가 믿을 수 없는 계열이다.
   PARA 57.80 ~ 113,900 · 하루 걸러 두 배로 오르내림(야후 PARA 는 지금 1달러대 — 다른 증권)
   COL  0.01 ~ 1.80 · 록웰 콜린스가 1달러 미만(야후에 자료 없음)
   믿을 원천이 없으므로(git 에 sd 이력 없음 · 사내 DB 는 이 PC 에서 못 닿음) 값을 지우고
   «quarantine» 에 사유와 함께 남긴다. pit_px_refresh.py 가 격리 이름을 다시 받지 않는다.
   ⚠ 사내 DB 가 닿는 PC 에서 pit_px_db.py 로 편입 기간 원종가를 메우는 것은 막지 않는다.
④ 로컬 캐시(data/_pit_px_cache.json, gitignore)에도 PARA·COL 오염이 있어 같이 지운다
   — index_ledger._pitpx() 가 기록과 캐시를 합쳐 읽는다.

⚠ AIV 는 처음에 오염으로 의심했으나 **아니다** — 편입 기간 연변동성 29.3%(동종 리츠 24~26%),
   최대 급변은 2020-03 코로나. 배당재투자 조정이 과거 수준을 낮춘 것뿐이라 손대지 않는다.

    python build/pit_px_repair.py
"""
from __future__ import annotations

import datetime
import io
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "pit_px.json")
CACHE = os.path.join(DATA, "_pit_px_cache.json")
TODAY = "2026-09-14"

SRC_COMMIT = "a40bcf060^"        # data/sd/AVB.json · EQR.json 이 지워지기 직전 커밋
MERGER = ("2026-08-17 AvalonBay·Equity Residential 합병 → Vivmark Residential(VMRK) · "
          "AVB 1주 = EQR 2.793주 · EQR 이 VMRK 로 개명")
BACKFILL = {"AVB": MERGER, "EQR": MERGER}
CUT_AFTER = {"AVB": ("2026-08-20", "야후 AVB 가 08-21 부터 전환 뒤 가격을 준다 — 184.06 ÷ 65.90 = 2.793(전환비)")}
QUAR = {
    "PARA": "편입 기간(2022-02~2025-07) 계열이 57.80~113,900 · 하루 걸러 두 배로 오르내림. "
            "야후 PARA 는 지금 1달러대로 다른 증권이다. git 에 sd 이력 없음.",
    "COL": "편입 기간(2014-06~2018-11) 가격이 0.01~1.80달러 — 록웰 콜린스가 1달러 미만일 수 없다. "
           "야후에 자료 없음. git 에 sd 이력 없음.",
}
BOUNDARY_TOL = 0.005


def git_json(path):
    r = subprocess.run(["git", "show", "%s:%s" % (SRC_COMMIT, path)], cwd=ROOT,
                       capture_output=True, check=True)
    return json.loads(r.stdout.decode("utf-8"))


def main() -> int:
    rec = json.load(io.open(OUT, encoding="utf-8"))
    dates, px = rec["dates"], rec["px"]
    flat = {t: {dates[v["i0"] + k]: p for k, p in enumerate(v["p"]) if p is not None}
            for t, v in px.items()}
    repairs = dict(rec.get("repairs") or {})
    quar = dict(rec.get("quarantine") or {})
    n_before = len(flat)

    st = git_json("data/stocks.json")
    dd = st["pxd_dates"]
    for t, why in BACKFILL.items():
        sd = git_json("data/sd/%s.json" % t)
        if len(sd["pxd"]) != len(dd):
            raise SystemExit("❌ %s sd 길이 %d ≠ 격자 %d — 날짜를 맞출 수 없다" % (t, len(sd["pxd"]), len(dd)))
        ser = {d: p for d, p in zip(dd, sd["pxd"]) if p}
        cur = dict(flat.get(t) or {})
        first = min(cur) if cur else None
        last_sd = max(ser)
        bnd = None
        if first:
            ref = ser.get(first, ser[last_sd])
            bnd = {"sd_date": first if first in ser else last_sd, "sd": ref,
                   "record_date": first, "record": cur[first], "ratio": round(cur[first] / ref, 6)}
            if abs(cur[first] / ref - 1.0) > BOUNDARY_TOL:
                raise SystemExit("❌ %s 경계 불일치 %s — 같은 증권이 아닐 수 있다. 멈춘다." % (t, bnd))
        added = {d: p for d, p in ser.items() if first is None or d < first}
        for d, p in added.items():
            cur.setdefault(d, p)
        cut = {}
        if t in CUT_AFTER:
            lim, _w = CUT_AFTER[t]
            cut = {d: p for d, p in cur.items() if d > lim}
            for d in cut:
                del cur[d]
        flat[t] = cur
        prev = repairs.get(t) or {}
        repairs[t] = {
            "date": prev.get("date") or TODAY,
            "why": why,
            "backfill_from": "git %s:data/sd/%s.json" % (SRC_COMMIT, t),
            "n_added": (prev.get("n_added") or 0) + len(added),
            "range_added": prev.get("range_added") or ([min(added), max(added)] if added else None),
            "boundary": prev.get("boundary") or bnd,
            "cut_after": CUT_AFTER[t][0] if t in CUT_AFTER else None,
            "cut_why": CUT_AFTER[t][1] if t in CUT_AFTER else None,
            "n_cut": (prev.get("n_cut") or 0) + len(cut),
        }
        print("  %s 복구 +%d점 (%s) · 꼬리 제거 %d점 · 경계 %s"
              % (t, len(added), ("%s~%s" % (min(added), max(added))) if added else "추가 없음",
                 len(cut), bnd))

    removed = []
    for t, why in QUAR.items():
        if t in flat:
            n = len(flat.pop(t))
            removed.append(t)
            quar[t] = {"since": TODAY, "n_removed": n, "why": why}
        elif t not in quar:
            quar[t] = {"since": TODAY, "n_removed": 0, "why": why}
    print("  격리 %s (이번에 지운 것 %s)" % (sorted(quar), removed or "없음 — 이미 격리됨"))

    alld = sorted({d for v in flat.values() for d in v})
    idx = {d: i for i, d in enumerate(alld)}
    out, n_pts = {}, 0
    for t, v in sorted(flat.items()):
        a = [None] * len(alld)
        for d, p in v.items():
            a[idx[d]] = p
        lo = next((i for i, x in enumerate(a) if x is not None), None)
        if lo is None:
            continue
        hi = next(i for i in range(len(a) - 1, -1, -1) if a[i] is not None)
        seg = a[lo:hi + 1]
        n_pts += sum(1 for x in seg if x is not None)
        out[t] = {"i0": lo, "p": seg}
    if len(out) != n_before - len(removed):
        raise SystemExit("❌ 티커 수 %d → %d · 격리로 지운 것 %d — 맞지 않는다. 멈춘다."
                         % (n_before, len(out), len(removed)))

    rec.update({
        "coverage": {"start": alld[0], "end": alld[-1], "n_dates": len(alld),
                     "n_tickers": len(out), "n_points": n_pts},
        "quarantine": quar,
        "n_quarantine": len(quar),
        "quarantine_note": "격리 = 편입 기간 값이 믿을 수 없어 지운 이름. pit_px_refresh.py 가 다시 받지 "
                           "않는다. 사내 DB 원종가로 메우는 것(pit_px_db.py)은 막지 않는다.",
        "repairs": repairs,
        "dates": alld,
        "px": out,
    })
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ data/pit_px.json · 티커 %d → %d · %s ~ %s · 관측 %d"
          % (n_before, len(out), alld[0], alld[-1], n_pts))

    if os.path.exists(CACHE):
        c = json.load(io.open(CACHE, encoding="utf-8"))
        gone = [t for t in QUAR if t in c]
        for t in gone:
            del c[t]
        if gone:
            io.open(CACHE, "w", encoding="utf-8", newline="").write(
                json.dumps(c, ensure_ascii=False, separators=(",", ":")) + chr(10))
        print("→ data/_pit_px_cache.json(로컬) · 격리 이름 지움 %s" % (gone or "없음"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
