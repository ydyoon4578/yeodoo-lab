# -*- coding: utf-8 -*-
"""build/r_cov.py — 배치 R(RBATCH) §F 커버리지 F0 와 T · 2026-09-26 등록 전 결정판 · 개수만(표지-수익 통계 없음).

🔒 등록 전 결정(오케스트레이터가 이 판 전에 정했다 · PREREG §0b · r_stagem.build_panel 머리말과 같은 규칙 — 여기서 바꾸지 않는다):
  세계(분모) = 그달 말 S&P 500 ∪ NASDAQ 100 멤버(r_stagem._members = pit_panel.union_members + 가격 키 없는 멤버) 가운데
    비금융(Wd.sector) · FPI 아님(지도 등록 표지 fpi_registered.tm_index = 7) · 지도 F0 위반 멤버-월 아님
    = r_stagem.build_panel 의 커버리지 분모(Stage M 세계).
  덮임 = 월말 가격 ∧ 시총(시총 가격 × 주식수 — 주식수 관측 나이 ≤ 550일(tech_backtest.TTM_STALE_DAYS) ∧ 그 관측 날짜를 덮는
    펀드 파일 CIK 구간(파일 최상위 "ciks")의 CIK 가 그달 §A0 CIK 집합에 있다 · 덮는 구간이 없으면 «출처 모름» = 불일치)
    ∧ 장부가(≤ 0 허용 · 같은 나이 · 같은 CIK 규칙) ∧ 12-2 모멘텀(t−13 · t−2 달 말 가격 · 앞 5거래일 안 마지막 값).
  통과 = 개수 몫 ≥ 0.90 ∧ 시총 몫 ≥ 0.95 ∧ 지도 F0(그달 위반율 ≤ 2%) ∧ 그달 패널 행이 있다(r_stagem.f0_coverage 그대로).
  시총 몫의 가중 = 자기 시총 → 그 티커의 마지막 자기 시총(12개월까지 · CAP_CARRY) → 그달 같은 지수(S&P 500 멤버면 S&P 500 ·
    아니면 NASDAQ 100)의 가격 키 멤버(금융 · FPI 포함) 자기 시총 중앙값. 시총 몫 분자 = 덮인 멤버의 자기 시총.
  T = 2016-08..2026-07 통과 달 수 — 나온 값이 최종이다(이 파일은 T 를 재기만 한다 · 규칙은 r_stagem 에서 가져온다).

r_stagem 과의 관계 — 같은 규칙을 **따로 짠** 판이다(대조가 뜻이 있게): 펀드 파일 CIK 구간은 이 파일이 직접 읽고(Prov),
  관측 고르기(주식수 = 가격 키 → 명단 티커 · sh 가 선 첫 파일 / 장부가 = 가격 키 파일이 있으면 그것 · 90일 지연)와 나이 · CIK ·
  가중 · 통과 판정을 여기서 다시 한다. r_stagem 에서 빌리는 것은 멤버 명단(_members) · 시총 가격(_cap_px — 원 종가 · 없으면 pxd)
  · 과거 가격(_px_at) · 지도(IssuerMap) · 수(상수)뿐이다. --check 가 r_stagem.build_panel + f0_coverage 와 달마다
  (분모 · 덮인 수 · 개수 몫 · 시총 몫 · 시총 모름 · 통과) · 행마다(시총) · 이름마다(낡음 · CIK 불일치) 맞춘다 — 어긋나면 종료 1.

묶는 성분(bind) — 통과 못 한 달의 덮이지 않은 멤버를 «첫 결측»(price → shares → book → mom 차례 · shares/book 은 none · stale ·
  cik 로 나눈다)으로 나눈 가장 큰 칸 + 걸린 선(count · cap · map · rows) + 모자란 멤버 수(short_n) + 그 달을 통과시키는 완화
  (flips — 나이 제한 없음 · 365/450/730일 · CIK 대조 끔 · 출처 모름 = 파일 CIK · 장부가 · 모멘텀 · 주식수+장부가 요구를 뺀 판).
  완화 판은 보고용이다(T 는 main 하나 · 나온 대로 최종).
550일 경계에 기대는 이름 — main 에서 덮인 멤버-월 가운데 주식수 · 장부가 관측 나이 최대가 365일을 넘는 것(> 450 은 따로 센다)
  과 550일을 넘겨 빠진 것(stale)을 이름별로 싣는다. T 가 경계에 얼마나 기대는지는 fresh365 · fresh450 · fresh730 · fresh_none 의 T.
위생(세계 수준 · 표지 없음) — ① pit_panel.month_rows('spx' · 'ndx') 시총가중 멤버 월수익 대 S&P 500 · NASDAQ 100 PR 연도별 상관
  (G4 와 같은 식) ② Stage M 패널(build_panel 행 · y 가 선 행 · 시총 가중) 보유월 수익 대 S&P 500 PR 연도별 상관(--check 때)
  ③ ② 가르기 — 랩 spx 비금융(① 에서 금융을 뺀 것) 대 S&P 500 · ② 패널 대 랩 비금융(금융을 뺀 세계 탓인지 자료 탓인지).
표지 F0 밀도(--check 때 · 개수만) — 최종 패널(build_panel) 위에서 R1 OS · RS(cikmonth · months_ok 안 달) · R2 CH(r_r2flags 정본 ·
  등록 판 v3 · Q1 = B-B 무변경) 의 월 종목 수 중앙값 · 최소(쓸 달 T 와 창 전체 둘 다) + R2 문서 F0(연 유효 짝 · 분리 실패율).

🚨 표지와 미래 수익의 관계는 계산하지 않는다. 보유월 수익은 «판정 칸(y_rule · y_stop)» 만 세고, 수익 값은 위생 상관 ②에서
   세계 수준(표지 없이)으로만 쓴다.

  python -X utf8 build/r_cov.py --out <json> [--tsv <tsv>] [--label x] [--check] [--no-hygiene]
      자료는 이 파일 옆 data/(RBATCH_DATA 를 주면 지도 · 내부자 · 10-Q · _px_raw · _r_ytrunc 는 그곳) — 자료 판 작업 사본에서 돌린다.
  RBATCH_PX_OVERLAY=<저장소 밖 파일> 를 주면 r_stagem.load_world 가 선언된 내부 가격 오버레이를 얹는다(가격이 빈 멤버-날만 ·
      있는 값은 안 바꾼다) — 세계 · 대조 · 위생이 모두 그 판이고, 적용 요약(sha256 · 수)이 prov.px_overlay 에 실린다. 없으면 공개 판.
      🚨 오버레이 판의 --out 은 저장소 밖에만 쓴다(내부 자료에서 나온 수).
"""
from __future__ import annotations
import argparse, collections, datetime as dt, hashlib, io, json, math, os, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔(랩 규약)
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from qbatch_core import mshift, months_between   # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
SENS = ("2014-07", "2016-07")                     # 미리 등록한 넓힌 창(r_stagem.SENS_FROM[0]) — 보고만
MARGIN_AGE = (365, 450)                           # «550일 경계에 기대는» 나이 칸(보고만)

# 규칙 판 — main 이 등록 규칙 · 나머지는 보고용 완화(T 는 main 하나)
NEED_MAIN = ("shares", "book", "mom")
RULES = collections.OrderedDict([
    ("main",        {"fresh": "FRESH", "cik": "ranges", "need": NEED_MAIN}),
    ("fresh365",    {"fresh": 365, "cik": "ranges", "need": NEED_MAIN}),
    ("fresh450",    {"fresh": 450, "cik": "ranges", "need": NEED_MAIN}),
    ("fresh730",    {"fresh": 730, "cik": "ranges", "need": NEED_MAIN}),
    ("fresh_none",  {"fresh": None, "cik": "ranges", "need": NEED_MAIN}),
    ("cik_off",     {"fresh": "FRESH", "cik": None, "need": NEED_MAIN}),
    ("cik_base",    {"fresh": "FRESH", "cik": "ranges_or_base", "need": NEED_MAIN}),   # 출처 모름 → 파일 최상위 CIK
    ("fresh_none_cik_off", {"fresh": None, "cik": None, "need": NEED_MAIN}),
    ("no_book",     {"fresh": "FRESH", "cik": "ranges", "need": ("shares", "mom")}),
    ("no_mom",      {"fresh": "FRESH", "cik": "ranges", "need": ("shares", "book")}),
    ("price_mom",   {"fresh": "FRESH", "cik": "ranges", "need": ("mom",)}),              # 주식수 · 장부가 요구를 뺀 가격 쪽 상한
    ("with_next",   {"fresh": "FRESH", "cik": "ranges", "need": NEED_MAIN + ("next",)}), # F0 + 보유월 y 가 선다(정보)
])
FLIP_RULES = ("fresh_none", "fresh730", "cik_off", "cik_base", "fresh_none_cik_off", "no_book", "no_mom", "price_mom")
Y_PRESENT = ("full", "gapcut", "gap0", "delisted", "grid_end")   # y_rule 이 값을 주는 판정(kept_trading · unclassified = 결측)


def _sha(p):
    if not p or not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _dir_sha(d):
    """디렉터리 안 .json 파일들(이름 · 바이트)의 합친 sha256 · 파일 수."""
    if not os.path.isdir(d):
        return None, 0
    h, n = hashlib.sha256(), 0
    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            h.update(f.encode("utf-8"))
            h.update((_sha(os.path.join(d, f)) or "").encode())
            n += 1
    return h.hexdigest(), n


def _git(root=ROOT):
    import subprocess
    try:
        h = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20).stdout.strip()
        d = subprocess.run(["git", "-C", root, "status", "--porcelain"], capture_output=True, text=True, timeout=120).stdout
        lines = [x for x in d.splitlines() if x.strip()]
        return {"head": h or None, "modified_tracked": sum(1 for x in lines if not x.startswith("??")),
                "untracked": sum(1 for x in lines if x.startswith("??"))}
    except Exception:
        return {"head": None, "modified_tracked": None, "untracked": None}


def _age(d, od):
    return (dt.date.fromisoformat(d) - dt.date.fromisoformat(od)).days


# ══ 펀드 파일 CIK 구간(r_stagem.FundCik 와 따로 짠 읽개) ═══════════════════════════════════════════
class Prov:
    """tech_backtest.load_fund 와 같은 파일(data/fx → data/fx_pit · 이름순 · 키 = "t" 또는 파일 이름)의 CIK 출처.
    at(키, 관측 기간말) → 그 날짜를 덮는 구간의 CIK 집합 | None(구간 칸 없음 · 덮는 구간 없음 = 출처 모름)."""

    def __init__(self, root=DATA):
        self.rng, self.base, self.stat = {}, {}, collections.Counter()
        for sub in ("fx", "fx_pit"):
            dd = os.path.join(root, sub)
            if not os.path.isdir(dd):
                continue
            for f in sorted(os.listdir(dd)):
                if not f.endswith(".json"):
                    continue
                try:
                    j = json.load(io.open(os.path.join(dd, f), encoding="utf-8"))
                except Exception:
                    self.stat["unreadable"] += 1
                    continue
                key = j.get("t") or f[:-5]
                rows = None
                rr = j.get("ciks") or j.get("cik_ranges")
                if rr:
                    rows = []
                    for x in rr:
                        if isinstance(x, dict):
                            rows.append((int(x["cik"]), x.get("from"), x.get("to")))
                        else:
                            rows.append((int(x[0]), x[1] if len(x) > 1 else None, x[2] if len(x) > 2 else None))
                self.stat["files_" + sub] += 1
                self.stat["with_ranges"] += int(rows is not None)
                self.stat["multi_cik"] += int(bool(rows) and len({c for c, _, _ in rows}) > 1)
                self.stat["key_twice"] += int(key in self.rng)
                self.rng[key] = rows
                c = j.get("cik")
                self.base[key] = int(c) if c not in (None, "") else None

    def at(self, key, od):
        rows = self.rng.get(key)
        if not rows:
            return None
        s = {c for c, a, b in rows if (a is None or a <= od) and (b is None or od <= b)}
        return s or None


_YF0, _YFB = {}, {}


def _yf_back(c, sh):
    """야후 «앞 채움» 관측 날짜 | None — r_stagem.yf_backfill_date 와 같은 규칙을 따로 짠 판(2026-09-26 · 3차 검토 BHGE).
    tech_backtest.merge_shares_yf 는 야후 첫 관측 y0(data/shares_yf.json 의 그 키 가장 이른 날짜) 앞 SHYF_BACK_DAYS 날짜에 y0 의 값을
    하나 더 둔다 — y0 에야 알려진 값이라 시점정확 읽기는 그 줄을 y0 에 본다(같은 값의 y0 관측이 이미 있으니 뺀다). 판정: 계열의 가장
    이른 날짜 = y0 − SHYF_BACK_DAYS ∧ 둘째로 이른 날짜 = y0."""
    import tech_backtest as TB
    if not sh or len(sh) < 2:
        return None
    if c not in _YF0:
        raw = TB.load_shares_yf().get(c) or []
        y0 = min((x[0] for x in raw), default=None)
        _YF0[c] = None if y0 is None else (
            (dt.date.fromisoformat(y0) - dt.timedelta(days=TB.SHYF_BACK_DAYS)).isoformat(), y0)
    b = _YF0[c]
    if b is None:
        return None
    key = (c, id(sh), len(sh))
    if key not in _YFB:
        lo = hi = None
        for x, _v in sh:                              # 가장 이른 두 날짜(한 번 훑기)
            if lo is None or x < lo:
                lo, hi = x, lo
            elif x != lo and (hi is None or x < hi):
                hi = x
        _YFB[key] = b[0] if (lo == b[0] and hi == b[1]) else None
    return _YFB[key]


def _obs(FUND, t, k, d, field):
    """(관측 기간말, 값, 쓴 펀드 키) | None — 'sh' 는 pit_panel._shares 차례(가격 키 → 명단 티커 · sh 가 선 첫 파일 · 0 이면 다음) ·
    'eq' 는 eg30plus.World.fund 차례(가격 키 파일이 있으면 그것 · 없으면 명단 티커). tech_backtest.asof_all(90일 지연).
    'sh' 의 야후 앞 채움 관측은 원 관측일에 본다(_yf_back · 그 줄을 빼고 고른다 · 2026-09-26)."""
    import tech_backtest as TB
    if field == "sh":
        for c in (k, t):
            sh = (FUND.get(c) or {}).get("sh")
            if sh:
                o = TB.asof_all(sh, d)
                b = _yf_back(c, sh) if o else None
                if b is not None:
                    o = [x for x in o if x[0] != b]
                if o and o[0][1]:
                    return o[0][0], float(o[0][1]), c
        return None
    c = k if FUND.get(k) else (t if FUND.get(t) else None)
    if c is None:
        return None
    o = TB.asof_all((FUND[c] or {}).get(field), d)
    return (o[0][0], float(o[0][1]), c) if (o and o[0][1] is not None) else None


# ══ 한 달의 멤버 기록(규칙과 무관한 원자료) ══════════════════════════════════════════════════════
def month_recs(Wd, IM, RAW, PV, YT, m):
    import r_stagem as RS
    import pit_panel as PP
    W, PX, me, dates = Wd.W, Wd.PX, Wd.me, Wd.dates
    i, d = me[m], dates[me[m]]
    ip2, ip13 = me[mshift(m, -2)], me[mshift(m, -13)]
    i1 = me.get(mshift(m, 1))
    spx, ndx = set(W["lists"]["spx"].get(m) or []), set(W["lists"]["ndx"].get(m) or [])
    pairs, nokey = RS._members(Wd, m, i)
    out = []
    for t, k in list(pairs) + [(x, None) for x in nokey]:
        kk = k if k is not None else t                   # build_panel: 가격 키 없는 멤버는 excluded(t, t)
        sec = Wd.sector(t, kk, m)
        a = IM.at(t, m)
        ex = ("fin" if sec == RS.FIN else ("fpi" if (a and a["fpi"] == 1) else ("viol" if IM.violated(t, m) else None)))
        r = {"t": t, "k": k, "ex": ex, "spx": t in spx, "ndx": t in ndx, "grp": (a or {}).get("grp"),
             "mciks": frozenset(int(x) for x in ((a or {}).get("ciks") or [])), "priced": False, "cpx": None, "cbasis": None,
             "sh": None, "sh_cs": None, "sh_base": None, "eq": None, "eq_cs": None, "eq_base": None, "mom": False,
             "y_rule": None, "y_stop": None}
        if k is not None:
            p = PX[k]
            pi = p[i]
            r["priced"] = bool(pi == pi and pi > 0)
            if r["priced"]:
                r["cpx"], r["cbasis"] = RS._cap_px(Wd, RAW, k, i)
            for fld in ("sh", "eq"):
                ob = _obs(W["FUND"], t, k, d, fld)
                if ob:
                    r[fld] = (ob[0], ob[1], ob[2], _age(d, ob[0]))
                    r[fld + "_cs"] = PV.at(ob[2], ob[0])
                    r[fld + "_base"] = PV.base.get(ob[2])
            r["mom"] = bool(RS._px_at(p, ip13) and RS._px_at(p, ip2))
            if i1 is not None and r["priced"]:
                r["y_rule"] = RS.y_rule(p, i, i1, k, dates, YT)[1]      # 판정 칸만(값은 버린다)
                r["y_stop"] = PP.y_stop(W, k, i, i1)
        out.append(r)
    return out


def _comp(r, fld, rule, fresh_main):
    """주식수 · 장부가 성분 — (값 | None, 사유 ok · none · stale · cik_unknown · cik_mismatch). r_stagem.fresh_consistent 와 같은 차례
    (관측 없음 → 나이 → CIK → 주식수 양수)."""
    ob = r[fld]
    if ob is None:
        return None, "none"
    od, v, key, age = ob
    fresh = fresh_main if rule["fresh"] == "FRESH" else rule["fresh"]
    if fresh is not None and age > fresh:
        return None, "stale"
    if rule["cik"]:
        cs = r[fld + "_cs"]
        if cs is None and rule["cik"] == "ranges_or_base" and r[fld + "_base"]:
            cs = {r[fld + "_base"]}
        if not cs or not r["mciks"] or not (set(cs) & r["mciks"]):
            return None, ("cik_unknown" if cs is None else "cik_mismatch")
    if fld == "sh" and not (v > 0):
        return None, "none"
    return v, "ok"


def eval_month(m, recs, rule, carry, im_ok, fresh_main, keep=False):
    """한 달 · 한 규칙 — build_panel 의 커버리지 계산을 그대로 다시 한다. carry = {티커: (달 번호, 자기 시총)}(규칙마다 따로)."""
    import r_stagem as RS
    mno = int(m[:4]) * 12 + int(m[5:7])
    own, shw = {}, {}
    for r in recs:                                          # 1) 자기 시총 — 가격 키 멤버 전부(금융 · FPI · 위반 포함)
        if r["k"] is None:
            continue
        if r["priced"]:
            sh, why = _comp(r, "sh", rule, fresh_main)
            own[r["t"]] = (r["cpx"] * sh) if (sh and r["cpx"]) else None
            shw[r["t"]] = why
        else:
            own[r["t"]] = None
            shw[r["t"]] = "noprice"
    med = {}
    for ix in ("spx", "ndx"):
        v = [own[r["t"]] for r in recs if r["k"] is not None and r[ix] and own[r["t"]]]
        med[ix] = float(np.median(v)) if v else None
    n_den = n_full = cap_unknown = 0
    cap_den = cap_full = 0.0
    has_rows = False
    first = collections.Counter()
    wsrc = collections.Counter()
    detail = []
    need = set(rule["need"])
    for r in recs:
        if r["ex"] is not None:
            continue
        t = r["t"]
        n_den += 1
        mc = own.get(t) if r["k"] is not None else None
        if mc:
            carry[t] = (mno, mc)
            if r["grp"] is not None:
                has_rows = True
        if mc:
            w = mc
            wsrc["own"] += 1
        else:
            lc = carry.get(t)
            if lc and mno - lc[0] <= RS.CAP_CARRY:
                w = lc[1]
                wsrc["carry"] += 1
            else:
                w = med["spx" if r["spx"] else "ndx"]
                wsrc["median" if w else "unknown"] += 1
        if w:
            cap_den += w
        else:
            cap_unknown += 1
        be, bwhy = (_comp(r, "eq", rule, fresh_main) if (mc or "shares" not in need) else (None, "nocap"))
        nxt = r["y_rule"] in Y_PRESENT and r["y_stop"] != "missing"   # r_stagem.build_panel 과 같다(y_stop 결측이면 결측 · 2026-09-26)
        ok = (r["priced"] and (bool(mc) or "shares" not in need) and (be is not None or "book" not in need)
              and (r["mom"] or "mom" not in need) and (nxt or "next" not in need))
        if ok:
            n_full += 1
            cap_full += (mc if mc else (w or 0.0))
        if not ok:
            if not r["priced"]:
                c = "price" if r["k"] is not None else "price:nokey"
            elif not mc and "shares" in need:
                c = "shares:" + shw[t]
            elif be is None and "book" in need:
                c = "book:" + bwhy
            elif not r["mom"] and "mom" in need:
                c = "mom"
            else:
                c = "next"
            first[c] += 1
        if keep:
            nl = {"fresh": None, "cik": rule["cik"], "need": rule["need"]}      # 같은 멤버 · 나이 제한만 없앤 판(보고)
            s2, b2 = _comp(r, "sh", nl, fresh_main)[0], _comp(r, "eq", nl, fresh_main)[0]
            detail.append({"t": t, "k": r["k"], "ok": ok, "mc": mc, "w": w, "shw": shw.get(t), "bwhy": bwhy,
                           "ok_nolimit": bool(r["priced"] and s2 and r["cpx"] and b2 is not None and r["mom"]),
                           "sh_age": (r["sh"][3] if r["sh"] else None), "eq_age": (r["eq"][3] if r["eq"] else None),
                           "sh_key": (r["sh"][2] if r["sh"] else None), "eq_key": (r["eq"][2] if r["eq"] else None),
                           "priced": r["priced"], "mom": r["mom"], "y_rule": r["y_rule"], "y_stop": r["y_stop"],
                           "cbasis": r["cbasis"], "grp": r["grp"]})
    cov_n = n_full / n_den if n_den else None
    cov_cap = cap_full / cap_den if cap_den else None
    okc = cov_n is not None and cov_n >= RS.COV_N
    okw = cov_cap is not None and cov_cap >= RS.COV_CAP
    st = {"n_den": n_den, "n_full": n_full, "cov_n": cov_n, "cov_cap": cov_cap, "cap_unknown": cap_unknown, "im_ok": im_ok,
          "rows": has_rows, "pass": bool(okc and okw and im_ok is True and has_rows),
          "line": [x for x, f in (("count", not okc), ("cap", not okw), ("map", im_ok is not True), ("rows", not has_rows)) if f],
          "short_n": max(0, math.ceil(RS.COV_N * n_den - 1e-9) - n_full), "first_miss": dict(first), "wsrc": dict(wsrc),
          "median": med}
    grp = collections.Counter()
    for c, v in first.items():
        grp[c.split(":")[0]] += v
    st["bind"] = max(grp, key=lambda c: (grp[c], -("price", "shares", "book", "mom", "next").index(c))) if grp else None
    return st, detail


def run(Wd, IM, RAW, PV, YT, months, rules=RULES):
    """달 목록(차례대로) → {규칙: {달: 통계}} · main 의 멤버 상세 {달: [..]} · 원자료 기록 수."""
    import r_stagem as RS
    carry = {nm: {} for nm in rules}
    res = {nm: {} for nm in rules}
    detail = {}
    for m in months:
        if m not in Wd.me or mshift(m, 1) not in Wd.me or mshift(m, -13) not in Wd.me:
            continue
        recs = month_recs(Wd, IM, RAW, PV, YT, m)
        im_ok = IM.month_ok(m)
        for nm, rule in rules.items():
            st, det = eval_month(m, recs, rule, carry[nm], im_ok, RS.FRESH_DAYS, keep=(nm == "main"))
            res[nm][m] = st
            if nm == "main":
                detail[m] = det
    return res, detail


# ══ 요약 · 이름 ═══════════════════════════════════════════════════════════════════════════════
def summarize(res, detail, lo, hi):
    import r_stagem as RS
    main = {m: s for m, s in res["main"].items() if lo <= m <= hi}
    T = {nm: sum(1 for m, s in by.items() if lo <= m <= hi and s["pass"]) for nm, by in res.items()}
    fails = [m for m, s in sorted(main.items()) if not s["pass"]]
    for m in fails:
        main[m]["flips"] = [nm for nm in FLIP_RULES if res[nm][m]["pass"]]
    yrs = collections.OrderedDict()
    for m, s in sorted(main.items()):
        y = yrs.setdefault(m[:4], {"months": 0, "pass": 0, "n_den": 0, "n_full": 0, "cov_n_min": 1.0, "cov_cap_min": 1.0,
                                   "first_miss": collections.Counter()})
        y["months"] += 1
        y["pass"] += int(s["pass"])
        y["n_den"] += s["n_den"]
        y["n_full"] += s["n_full"]
        y["cov_n_min"] = min(y["cov_n_min"], s["cov_n"] or 0)
        y["cov_cap_min"] = min(y["cov_cap_min"], s["cov_cap"] or 0)
        for c, v in s["first_miss"].items():
            y["first_miss"][c] += v
    for y in yrs.values():
        y["first_miss"] = dict(y["first_miss"])
        y["cov_n_min"], y["cov_cap_min"] = round(y["cov_n_min"], 4), round(y["cov_cap_min"], 4)
    pass_m = [m for m, s in sorted(main.items()) if s["pass"]]
    slack = {m: main[m]["n_full"] - math.ceil(RS.COV_N * main[m]["n_den"] - 1e-9) for m in pass_m}
    return {"T": T, "T_min": RS.T_MIN, "measure_only": T["main"] < RS.T_MIN, "months": len(main), "pass_months": pass_m,
            "fail_months": fails, "count_ok": sum(1 for s in main.values() if (s["cov_n"] or 0) >= RS.COV_N),
            "cap_ok": sum(1 for s in main.values() if (s["cov_cap"] or 0) >= RS.COV_CAP),
            "bind_in_fail_months": dict(collections.Counter(main[m]["bind"] for m in fails)),
            "line_in_fail_months": dict(collections.Counter("+".join(main[m]["line"]) for m in fails)),
            "slack_in_pass_months": slack, "min_slack": (min(slack.values()) if slack else None),
            "by_year": yrs}


def margin_names(res, detail, lo, hi):
    """550일 경계에 기대는 이름(main) — ① 덮였는데 주식수·장부가 나이 최대 > 365(> 450 따로) ② 550일을 넘겨 빠진 것(stale) ·
    ③ CIK 로 빠진 것(출처 모름 · 불일치). 이름별 멤버-월 · 나이 · 달 · 통과 달 안의 수 · 경계에서 뒤집히는 달 안의 수."""
    main = res["main"]
    flip365 = {m for m, s in main.items() if lo <= m <= hi and s["pass"] and not res["fresh365"][m]["pass"]}
    flip450 = {m for m, s in main.items() if lo <= m <= hi and s["pass"] and not res["fresh450"][m]["pass"]}
    gain_none = {m for m, s in main.items() if lo <= m <= hi and not s["pass"] and res["fresh_none"][m]["pass"]}
    rely, stale, cik = {}, {}, {}
    per_m = {}
    for m, det in sorted(detail.items()):
        if not (lo <= m <= hi):
            continue
        pm = per_m.setdefault(m, {"rely365": 0, "rely450": 0, "stale": 0, "cik": 0})
        for x in det:
            ages = [a for a in (x["sh_age"], x["eq_age"]) if a is not None]
            amax = max(ages) if ages else None
            if x["ok"] and amax is not None and amax > MARGIN_AGE[0]:
                pm["rely365"] += 1
                pm["rely450"] += int(amax > MARGIN_AGE[1])
                n = rely.setdefault(x["t"], {"mm": 0, "mm_gt450": 0, "age_max": 0, "first": m, "last": m, "which": collections.Counter(),
                                             "in_pass": 0, "in_flip365": 0, "in_flip450": 0, "months": []})
                n["mm"] += 1
                n["mm_gt450"] += int(amax > MARGIN_AGE[1])
                n["age_max"] = max(n["age_max"], amax)
                n["last"] = m
                n["months"].append(m)
                n["which"]["sh" if (x["sh_age"] or 0) > MARGIN_AGE[0] else "eq"] += 1
                if (x["sh_age"] or 0) > MARGIN_AGE[0] and (x["eq_age"] or 0) > MARGIN_AGE[0]:
                    n["which"]["both"] += 1
                n["in_pass"] += int(main[m]["pass"])
                n["in_flip365"] += int(m in flip365)
                n["in_flip450"] += int(m in flip450)
            why = [w for w in (x["shw"], x["bwhy"]) if w]
            if x["priced"] and "stale" in why:
                pm["stale"] += 1
                n = stale.setdefault(x["t"], {"mm": 0, "age_min": None, "age_max": 0, "first": m, "last": m, "which": collections.Counter(),
                                              "in_gain_none": 0, "otherwise_ok": 0})
                n["mm"] += 1
                sa = [a for a, w in ((x["sh_age"], x["shw"]), (x["eq_age"], x["bwhy"])) if w == "stale" and a is not None]
                n["age_max"] = max([n["age_max"]] + sa)
                n["age_min"] = min([v for v in [n["age_min"]] + sa if v is not None])
                n["last"] = m
                n["which"]["sh" if x["shw"] == "stale" else "eq"] += 1
                n["in_gain_none"] += int(m in gain_none)
                n["otherwise_ok"] += int(x["ok_nolimit"])                  # 나이 제한만 없으면 덮이는 멤버-월
            if x["priced"] and any(w.startswith("cik") for w in why):
                pm["cik"] += 1
                n = cik.setdefault(x["t"], {"mm": 0, "first": m, "last": m, "why": collections.Counter(), "keys": set()})
                n["mm"] += 1
                n["last"] = m
                for w, fld, key in ((x["shw"], "sh", x["sh_key"]), (x["bwhy"], "eq", x["eq_key"])):
                    if w and w.startswith("cik"):
                        n["why"][fld + ":" + w] += 1
                        n["keys"].add(key)
    for d_ in (rely, stale, cik):
        for n in d_.values():
            for kk in ("which", "why"):
                if kk in n:
                    n[kk] = dict(n[kk])
            if "keys" in n:
                n["keys"] = sorted(k for k in n["keys"] if k)
    srt = lambda d_: dict(sorted(d_.items(), key=lambda kv: (-kv[1]["mm"], kv[0])))
    return {"flip365_months": sorted(flip365), "flip450_months": sorted(flip450), "gain_if_no_limit_months": sorted(gain_none),
            "rely_gt365": srt(rely), "stale_gt550": srt(stale), "cik_excluded": srt(cik), "per_month": per_m}


def y_crosstab(detail, lo, hi):
    """보유월 y 판정 두 벌 — r_stagem.y_rule(data/_r_ytrunc.json) 대 pit_panel.y_stop(pit_px closed[].stops) · Stage M 가격 멤버."""
    ct = collections.Counter()
    dis = []
    for m, det in sorted(detail.items()):
        if not (lo <= m <= hi):
            continue
        for x in det:
            if not x["priced"]:
                continue
            ct[(x["y_rule"], x["y_stop"])] += 1
            miss_r = x["y_rule"] in ("kept_trading", "unclassified")
            miss_s = x["y_stop"] == "missing"
            if miss_r != miss_s:
                dis.append([m, x["t"], x["k"], x["y_rule"], x["y_stop"]])
    return {"table": {"%s|%s" % k: v for k, v in sorted(ct.items(), key=lambda kv: str(kv[0]))}, "missing_disagree": dis}


# ══ 위생(세계 수준 · 표지 없음) ══════════════════════════════════════════════════════════════════
def hygiene_lab(Wd, lo="2014-07", hi="2026-07"):
    """① pit_panel.month_rows 시총가중 멤버 월수익 대 지수 PR — 연도별 상관(G4 와 같은 식)."""
    import pit_panel as PP
    CH = json.load(io.open(os.path.join(DATA, "strategy_charts.json"), encoding="utf-8"))["idx_monthly"]
    out = {}
    for ix, lab in (("spx", "S&P 500"), ("ndx", "NASDAQ 100")):
        sig = [m for m in sorted(Wd.W["me"]) if lo <= m <= hi]
        rows, _ = PP.month_rows(Wd.W, ix, sig, mshift(hi, 1))
        bm = CH.get(lab) or {}
        by = collections.defaultdict(list)
        for x in rows:
            if x["m"] in bm:
                by[x["m"][:4]].append((sum(x["wb"][t] * x["r"][t] for t in x["names"]) * 100, bm[x["m"]], len(x["names"])))
        out[ix] = _corr_by_year(by)
    return out


def hygiene_panel(P, lo, hi):
    """② Stage M 패널(build_panel 행 · y 가 선 행 · 자기 시총 가중) 보유월 수익 대 S&P 500 PR — 연도별 상관(세계 수준)."""
    CH = json.load(io.open(os.path.join(DATA, "strategy_charts.json"), encoding="utf-8"))["idx_monthly"]
    bm = CH.get("S&P 500") or {}
    by = collections.defaultdict(list)
    for m in P["months"]:
        if not (lo <= m <= hi):
            continue
        D = P["m"][m]
        y, w = np.asarray(D["y"], float), np.asarray(D["mc"], float)
        ok = np.isfinite(y) & np.isfinite(w) & (w > 0)
        h = mshift(m, 1)
        if ok.sum() >= 40 and h in bm:
            by[h[:4]].append((float(np.sum(y[ok] * w[ok]) / np.sum(w[ok])), bm[h], int(ok.sum())))
    return _corr_by_year(by)


def hygiene_exfin(Wd, P, lo, hi):
    """③ ②가 낮은 해의 까닭 가르기 — pit_panel.month_rows('spx') 에서 금융(Wd.sector)을 뺀 시총가중 월수익(랩 spx 비금융)과
    ② 패널 · S&P 500 PR 의 연도별 상관(세계 수준). 패널 ≈ 랩 비금융이면 ② 의 낮은 상관은 금융을 뺀 세계 탓이다(자료 결함이 아니다)."""
    import pit_panel as PP
    import r_stagem as RS
    CH = json.load(io.open(os.path.join(DATA, "strategy_charts.json"), encoding="utf-8"))["idx_monthly"]
    bm = CH.get("S&P 500") or {}
    rows, _ = PP.month_rows(Wd.W, "spx", [m for m in P["months"] if lo <= m <= hi], mshift(hi, 1))
    lab = {x["sig"]: x for x in rows}
    by = collections.defaultdict(list)
    for m in P["months"]:
        h = mshift(m, 1)
        if not (lo <= m <= hi) or m not in lab or h not in bm:
            continue
        D = P["m"][m]
        y, w = np.asarray(D["y"], float), np.asarray(D["mc"], float)
        ok = np.isfinite(y) & np.isfinite(w) & (w > 0)
        x = lab[m]
        nf = [t for t in x["names"] if Wd.sector(t, x["key"][t], m) != RS.FIN]
        wn = sum(x["wb"][t] for t in nf)
        if ok.sum() < 40 or not nf:
            continue
        by[h[:4]].append((float(np.sum(y[ok] * w[ok]) / np.sum(w[ok])), sum(x["wb"][t] * x["r"][t] for t in nf) / wn * 100,
                          bm[h], 1 - wn))
    out = {}
    for yr, pr in sorted(by.items()):
        if len(pr) < 3:
            continue
        c = lambda a, b: round(float(np.corrcoef([r[a] for r in pr], [r[b] for r in pr])[0, 1]), 4)
        out[yr] = {"n": len(pr), "panel_vs_idx": c(0, 2), "lab_exfin_vs_idx": c(1, 2), "panel_vs_lab_exfin": c(0, 1),
                   "fin_weight_mean": round(float(np.mean([r[3] for r in pr])), 3), "idx_sd_pp": round(float(np.std([r[2] for r in pr])), 3)}
    return out


def _corr_by_year(by):
    res = {}
    for y, pr in sorted(by.items()):
        if len(pr) >= 3:
            c = float(np.corrcoef([a for a, _, _ in pr], [b for _, b, _ in pr])[0, 1])
            res[y] = {"n": len(pr), "corr": round(c, 4), "gap_mean_pp": round(float(np.mean([a - b for a, b, _ in pr])), 3),
                      "names_med": int(np.median([n for _, _, n in pr]))}
    return res


# ══ r_stagem 대조 · 표지 F0 밀도 ═══════════════════════════════════════════════════════════════════
def check_vs_stagem(Wd, IM, res, detail, lo, hi):
    import r_stagem as RS
    P = RS.build_panel(Wd, IM, months_between(lo, hi))
    f0 = RS.f0_coverage(P)
    bad, n = [], 0
    for m in months_between(lo, hi):
        st, mine = P["stat"].get(m) or {}, res["main"].get(m)
        if st.get("skip") or mine is None:
            if bool(st.get("skip")) != (mine is None):
                bad.append({"m": m, "why": "grid", "stagem": st.get("skip"), "mine": mine is not None})
            continue
        n += 1
        fr = f0["by_month"].get(m) or {}
        a = [st["n_den"], st["n_full"], st["cov_n"], st["cov_cap"], st["cap_unknown"], bool(fr.get("use"))]
        b = [mine["n_den"], mine["n_full"], mine["cov_n"], mine["cov_cap"], mine["cap_unknown"], mine["pass"]]
        same = (a[0] == b[0] and a[1] == b[1] and a[4] == b[4] and a[5] == b[5]
                and ((a[2] is None and b[2] is None) or (a[2] is not None and b[2] is not None and abs(a[2] - b[2]) <= 1e-12))
                and ((a[3] is None and b[3] is None) or (a[3] is not None and b[3] is not None and abs(a[3] - b[3]) <= 1e-9)))
        if not same:
            bad.append({"m": m, "stagem": a, "mine": b})
    # 행마다 시총 · 이름마다 낡음/CIK 사유
    row_bad, rows_n, name_bad = [], 0, []
    for m in P["months"]:
        if not (lo <= m <= hi):
            continue
        mymc = {x["t"]: x["mc"] for x in detail.get(m, [])}
        D = P["m"][m]
        for t, v in zip(D["t"], D["mc"]):
            rows_n += 1
            mv = mymc.get(t)
            if mv is None or abs(mv - v) > 1e-9 * max(1.0, abs(v)):
                row_bad.append([m, t, v, mv])
        sc = {(x[0], x[1], x[2]) for x in P["stat"][m]["names"].get("stale_or_cik") or ()}
        mine = set()
        for x in detail.get(m, []):
            shw = x["shw"] if x["shw"] in ("ok", "none", "stale") else ("cik" if (x["shw"] or "").startswith("cik") else x["shw"])
            bw = x["bwhy"] if x["bwhy"] in ("ok", "none", "stale", "nocap") else ("cik" if (x["bwhy"] or "").startswith("cik") else x["bwhy"])
            if x["priced"] and (shw in ("stale", "cik") or bw in ("stale", "cik")):
                mine.add((x["t"], shw, bw))
        if sc != mine:
            name_bad.append({"m": m, "only_stagem": sorted(sc - mine), "only_mine": sorted(mine - sc)})
    out = {"months": n, "mismatch": bad, "rows": rows_n, "row_mc_mismatch": row_bad[:50], "row_mc_mismatch_n": len(row_bad),
           "stale_or_cik_name_mismatch": name_bad[:20], "stale_or_cik_name_mismatch_n": len(name_bad),
           "stagem_T": f0["T"], "stagem_months": f0["months"], "stagem_fail": f0["fail"], "measure_only": f0["measure_only"],
           "cap_basis": P["cap_basis"], "f0_rules": f0["rules"], "y_unclassified": P.get("y_unclassified"),
           "ok": bool(not bad and not row_bad and not name_bad)}
    return out, P, f0


def densities(Wd, IM, P, f0):
    """최종 패널(build_panel) 위의 표지 F0 밀도 — 개수만(수익 없음)."""
    import r_stagem as RS
    out = {"rule": {k: list(v) for k, v in RS.F0_FLAG.items()}}
    allm = list(P["months"])
    use = list(f0["months"])
    ins_p = os.path.join(RS.RDATA, RS.FIELDS["ins"]["file"])
    fp = RS.ins_flags(ins_p)
    mo = fp.months_ok
    out["R1"] = {"src": fp.src, "sha256": _sha(ins_p), "months_ok": [min(mo), max(mo)] if mo else None, "notes": fp.notes}
    for tag, ms in (("T_months", use), ("all_months", allm)):
        ok_m = [m for m in ms if mo is None or m in mo]
        out["R1"][tag] = {"n_months": len(ok_m), "dropped_not_months_ok": [m for m in ms if not (mo is None or m in mo)]}
        for f in ("OS", "RS"):
            dd = RS.f0_density(P, fp, f, ok_m)
            v = sorted(dd["by_month"].items(), key=lambda kv: kv[1])
            out["R1"][tag][f] = {"median": dd["median"], "min": dd["min"], "ok": dd["ok"], "min_months": [m for m, c in v[:3]]}
    bw, bst = RS.boundary_world(Wd, IM, RS.BOUND_FROM, RS.M1)
    got = RS.tenq_canonical(world=bw)
    fp2, R = got
    import r_r2flags as R2
    out["R2"] = {"src": fp2.src, "sha256": _sha(os.path.join(RS.RDATA, RS.FIELDS["tenq"]["file"])),
                 "shape_ver": R2.REG_SHAPE_VER, "q1_rule": R.get("q1_rule"), "reg_q1_rule": R2.REG_Q1_RULE,
                 "bb_nochange_pairs": (R.get("log") or {}).get("bb_nochange"), "boundary_world": bst}
    for tag, ms in (("T_months", use), ("all_months", allm)):
        dd = RS.f0_density(P, fp2, "CH", ms)
        v = sorted(dd["by_month"].items(), key=lambda kv: kv[1])
        out["R2"][tag] = {"n_months": len(ms), "CH": {"median": dd["median"], "min": dd["min"], "ok": dd["ok"],
                                                      "min_months": [m for m, c in v[:3]]}}
    den = R2.r2_density(R, months_between(RS.M0, RS.M1))
    out["R2"]["doc_f0"] = {"f0": den["f0"], "ch_month_world": den["ch_month"],
                           "by_year": {y: {"valid_world": v.get("valid_world"), "fail_rate": (round(v["fail_rate"], 4)
                                           if v.get("fail_rate") is not None else None), "f0_docs": v.get("f0_docs"),
                                           "cut": v.get("cut")} for y, v in den["by_year"].items()}}
    return out


def ytrunc(Wd, IM):
    import r_stagem as RS
    rows = RS.ytrunc_scan(Wd, IM)
    c = collections.Counter((r["class"] or "unclassified", r["in_sample"]) for r in rows)
    return {"rows": len(rows), "by_class_in_sample": {"%s|%s" % k: v for k, v in sorted(c.items(), key=str)},
            "unclassified_in_sample": [[r["key"], r["last"], r["signal_months"]] for r in rows if r["class"] is None and r["in_sample"]],
            "unclassified_any": sum(1 for r in rows if r["class"] is None)}


# ══ 찍기 ════════════════════════════════════════════════════════════════════════════════════
def _f(x, nd=4):
    return "-" if x is None else ("%.*f" % (nd, x))


def write_tsv(path, res, lo, hi):
    main = res["main"]
    cols = ["month", "n_den", "n_full", "cov_n", "cov_cap", "im_ok", "rows", "pass", "line", "bind", "short_n", "flips",
            "price", "price:nokey", "shares:none", "shares:stale", "shares:cik_unknown", "shares:cik_mismatch",
            "book:none", "book:stale", "book:cik_unknown", "book:cik_mismatch", "mom", "w_carry", "w_median", "w_unknown"] + \
           ["pass_" + nm for nm in RULES if nm != "main"]
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(cols) + "\n")
        for m in sorted(main):
            if not (lo <= m <= hi):
                continue
            s = main[m]
            fm = s["first_miss"]
            row = [m, s["n_den"], s["n_full"], _f(s["cov_n"]), _f(s["cov_cap"]), s["im_ok"], int(s["rows"]), int(s["pass"]),
                   "+".join(s["line"]) or "-", s["bind"] or "-", s["short_n"], ",".join(s.get("flips") or []) or "-"] + \
                  [fm.get(c, 0) for c in cols[12:23]] + [s["wsrc"].get("carry", 0), s["wsrc"].get("median", 0),
                                                         s["wsrc"].get("unknown", 0)] + \
                  [int(res[nm][m]["pass"]) for nm in RULES if nm != "main"]
            fh.write("\t".join(str(x) for x in row) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--tsv")
    ap.add_argument("--label", default="")
    ap.add_argument("--check", action="store_true", help="r_stagem.build_panel + f0_coverage 대조 · 표지 F0 밀도 · 패널 위생")
    ap.add_argument("--no-hygiene", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    import r_stagem as RS
    import tech_backtest as TB
    if RS.px_overlay_path():                                  # 내부 오버레이 판의 보고는 저장소 밖에만(내부 자료에서 나온 수)
        for p_ in (a.out, a.tsv):
            try:
                inside = bool(p_) and os.path.commonpath([os.path.abspath(p_).lower(), ROOT.lower()]) == ROOT.lower()
            except ValueError:                                # 다른 드라이브 — 저장소 밖
                inside = False
            if inside:
                raise SystemExit("🚨 %s 가 있을 때 --out/--tsv %s 는 저장소 밖이어야 한다" % (RS.PX_OVERLAY_ENV, p_))
    if RS.FRESH_DAYS != TB.TTM_STALE_DAYS:
        raise SystemExit("🚨 r_stagem.FRESH_DAYS %s ≠ tech_backtest.TTM_STALE_DAYS %s" % (RS.FRESH_DAYS, TB.TTM_STALE_DAYS))
    Wd = RS.load_world()
    IM = RS.IssuerMap()
    RAW = RS._raw_px(Wd)
    PV = Prov()
    YT, _ = RS.load_ytrunc()
    M0, M1 = RS.M0, RS.M1
    res, detail = run(Wd, IM, RAW, PV, YT, months_between(M0, M1))
    res_s, det_s = run(Wd, IM, RAW, PV, YT, months_between(*SENS), rules={"main": RULES["main"], "fresh_none": RULES["fresh_none"],
                                                                           "price_mom": RULES["price_mom"]})
    summ = summarize(res, detail, M0, M1)
    rep = {"kind": "r_cov", "label": a.label, "version": "2026-09-26 등록 전 결정판",
           "rules": {"universe": "Stage M = 멤버 ∧ 비금융(Wd.sector) ∧ FPI 아님(fpi_registered tm_index %d) ∧ 지도 F0 위반 아님" % IM.fpi_index,
                     "covered": "월말 가격 ∧ 시총(주식수 나이 ≤ %d일 ∧ 펀드 파일 CIK 구간 ∩ 그달 §A0 CIK) ∧ 장부가(≤0 허용 · 같은 규칙) ∧ 12-2 모멘텀"
                                % RS.FRESH_DAYS,
                     "pass": "개수 ≥ %.2f ∧ 시총 ≥ %.2f ∧ 지도 F0(≤ %.0f%%) ∧ 행 있음" % (RS.COV_N, RS.COV_CAP, 100 * RS.IM_VIOL),
                     "cap_weight": "자기 → %d개월 이음 → 같은 지수 중앙값" % RS.CAP_CARRY, "T_min": RS.T_MIN,
                     "variants": {nm: {k: (RS.FRESH_DAYS if v == "FRESH" else v) for k, v in r.items()} for nm, r in RULES.items()}},
           "prov": {"root": ROOT, "git": _git(), "rdata": RS.RDATA, "py_sha256": _sha(os.path.abspath(__file__)),
                    "files": {n: _sha(os.path.join(DATA, n)) for n in ("pit_px.json", "stocks.json", "index_history.json",
                                                                      "pit_universe.json", "pit_reuse.json", "shares_yf.json",
                                                                      "splits.json", "fx_splice.json")},
                    "rdata_files": {n: _sha(os.path.join(RS.RDATA, n)) for n in ("_px_raw.json", "_issuer_map.json",
                                                                               "_issuer_map_sector_manual.json", "_r_ytrunc.json",
                                                                               os.path.join("_ins_pit", "cikmonth.json"), "_tenq_rf.json")},
                    "modules": {n: _sha(os.path.join(HERE, n + ".py")) for n in ("r_stagem", "pit_panel", "pit_alias", "r_r1_flags",
                                                                                "r_r2flags", "tech_backtest", "eg30plus", "qg_lab")},
                    "fx": _dir_sha(os.path.join(DATA, "fx")), "fx_pit": _dir_sha(os.path.join(DATA, "fx_pit")),
                    "prov_stat": dict(PV.stat), "cap_basis": ("raw(_px_raw.json · 키 %d)" % len(RAW)) if RAW else "div_adjusted",
                    "px_overlay": getattr(Wd, "px_overlay", None)},      # 선언된 내부 가격 오버레이(r_stagem.load_world) · None = 공개 판
           "summary": summ, "by_month": res["main"],
           "variants_by_month": {nm: {m: {k: s[k] for k in ("cov_n", "cov_cap", "pass")} for m, s in by.items()}
                                 for nm, by in res.items() if nm != "main"},
           "sens": {"window": list(SENS), "T": {nm: sum(1 for s in by.values() if s["pass"]) for nm, by in res_s.items()},
                    "by_month": {m: {k: s[k] for k in ("n_den", "n_full", "cov_n", "cov_cap", "im_ok", "pass", "bind", "line")}
                                 for m, s in res_s["main"].items()}},
           "margin_550": margin_names(res, detail, M0, M1),
           "y_crosstab": y_crosstab(detail, M0, M1)}
    rc = 0
    if a.check:
        chk, P, f0 = check_vs_stagem(Wd, IM, res, detail, M0, M1)
        rep["check_vs_stagem"] = chk
        rc = 0 if chk["ok"] else 1
        rep["density"] = densities(Wd, IM, P, f0)
        rep["ytrunc_scan"] = ytrunc(Wd, IM)
        if not a.no_hygiene:
            rep["hygiene_panel"] = hygiene_panel(P, M0, M1)
            rep["hygiene_exfin"] = hygiene_exfin(Wd, P, M0, M1)
    if not a.no_hygiene:
        rep["hygiene_lab"] = hygiene_lab(Wd)
    rep["sec_elapsed"] = round(time.time() - t0, 1)
    # 찍기
    s = summ
    print("[%s] Stage M 커버리지 F0 %s..%s · T = %d(%s) · 측정으로 내림 %s" % (a.label, M0, M1, s["T"]["main"], rep["rules"]["pass"],
                                                                s["measure_only"]))
    ovr = rep["prov"]["px_overlay"]
    print("  가격 오버레이(%s) %s" % (RS.PX_OVERLAY_ENV, "없음 — 공개 판" if not ovr else "sha256 %s · %s · 채운 값 %d(키 %d · 새 키 %d) · 건너뜀 %s" % (
        ovr["sha256"][:16], ovr["visibility"], ovr["values_filled"], ovr["keys_filled"], ovr["keys_new"], ovr["skipped"])))
    print("  완화 판 T(보고만): %s" % {k: v for k, v in s["T"].items() if k != "main"})
    print("  개수 통과 달 %d · 시총 통과 달 %d · 실패 달의 선 %s · 묶는 성분 %s · 통과 달 최소 여유 %s" % (
        s["count_ok"], s["cap_ok"], s["line_in_fail_months"], s["bind_in_fail_months"], s["min_slack"]))
    print("  %-7s %4s %4s %7s %7s %4s %-11s %-6s %3s  %s" % ("달", "분모", "덮임", "개수", "시총", "통과", "선", "묶음", "모자람", "첫 결측 · 뒤집는 완화"))
    for m in sorted(res["main"]):
        x = res["main"][m]
        print("  %-7s %4d %4d %7s %7s %4s %-11s %-6s %3d  %s%s" % (
            m, x["n_den"], x["n_full"], _f(x["cov_n"]), _f(x["cov_cap"]), "O" if x["pass"] else ".", "+".join(x["line"]) or "-",
            x["bind"] or "-", x["short_n"], dict(sorted(x["first_miss"].items(), key=lambda kv: -kv[1])) if not x["pass"] else "",
            (" · flips %s" % x.get("flips")) if x.get("flips") else ""))
    for y, v in s["by_year"].items():
        print("  %s 달 %2d 통과 %2d · 최저 개수 %.4f 시총 %.4f · 첫 결측 %s" % (y, v["months"], v["pass"], v["cov_n_min"], v["cov_cap_min"],
                                                                 v["first_miss"]))
    mg = rep["margin_550"]
    print("  550일 경계 — 365일 한도면 뒤집히는 통과 달 %s · 450일 %s · 한도 없으면 통과하는 실패 달 %s" % (
        mg["flip365_months"], mg["flip450_months"], mg["gain_if_no_limit_months"]))
    print("  덮였는데 나이 > 365 이름 %d: %s" % (len(mg["rely_gt365"]), {t: (v["mm"], v["age_max"], v["in_flip365"]) for t, v in
                                                                list(mg["rely_gt365"].items())[:40]}))
    print("  550일 넘겨 빠진 이름 %d: %s" % (len(mg["stale_gt550"]), {t: (v["mm"], v["age_min"], v["age_max"]) for t, v in
                                                            list(mg["stale_gt550"].items())[:40]}))
    print("  CIK 로 빠진 이름 %d: %s" % (len(mg["cik_excluded"]), {t: (v["mm"], v["why"]) for t, v in list(mg["cik_excluded"].items())[:40]}))
    print("  넓힌 창 %s..%s T %s" % (SENS[0], SENS[1], rep["sens"]["T"]))
    print("  y 판정 대조(y_rule|y_stop) %s · 결측 판정 어긋남 %d" % (rep["y_crosstab"]["table"], len(rep["y_crosstab"]["missing_disagree"])))
    if a.check:
        c = rep["check_vs_stagem"]
        print("  대조 r_stagem.build_panel/f0_coverage: 달 %d · 어긋남 %d · 행 %d(시총 어긋남 %d) · 낡음/CIK 이름 어긋난 달 %d · r_stagem T %d · %s" % (
            c["months"], len(c["mismatch"]), c["rows"], c["row_mc_mismatch_n"], c["stale_or_cik_name_mismatch_n"], c["stagem_T"],
            "OK" if c["ok"] else "🚨 어긋남"))
        dn = rep["density"]
        for tag in ("T_months", "all_months"):
            print("  밀도 %-10s R1 OS %s · RS %s · R2 CH %s" % (tag, {k: dn["R1"][tag]["OS"][k] for k in ("median", "min", "ok")},
                                                        {k: dn["R1"][tag]["RS"][k] for k in ("median", "min", "ok")},
                                                        {k: dn["R2"][tag]["CH"][k] for k in ("median", "min", "ok")}))
        print("  R2 문서 F0 %s" % dn["R2"]["doc_f0"]["f0"])
        print("  ytrunc_scan %s" % {k: v for k, v in rep["ytrunc_scan"].items() if k != "unclassified_in_sample"})
        if "hygiene_panel" in rep:
            print("  위생 ② Stage M 패널 대 S&P 500 %s" % {y: v["corr"] for y, v in rep["hygiene_panel"].items()})
            print("  위생 ③ 랩 spx 비금융 대 S&P 500 %s · 패널 대 랩 비금융 %s" % (
                {y: v["lab_exfin_vs_idx"] for y, v in rep["hygiene_exfin"].items()},
                {y: v["panel_vs_lab_exfin"] for y, v in rep["hygiene_exfin"].items()}))
    if "hygiene_lab" in rep:
        print("  위생 ① spx %s" % {y: v["corr"] for y, v in rep["hygiene_lab"]["spx"].items()})
        print("  위생 ① ndx %s" % {y: v["corr"] for y, v in rep["hygiene_lab"]["ndx"].items()})
    if a.out:
        json.dump(rep, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=0, default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else str(o))
    if a.tsv:
        write_tsv(a.tsv, res, M0, M1)
    print("→ %s (%.0f초) · 종료 %d" % (a.out or "-", time.time() - t0, rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())
