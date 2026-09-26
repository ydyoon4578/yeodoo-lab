# -*- coding: utf-8 -*-
"""build/v_ear.py — 배치 V 실적발표 입력: V05 EAR(CAR[−2,+1] · 윈저 · ATTN 특성 · CH 제외) · V03 LIQ(IRRX 의 발표 3일 CAR · 섹터 VW 수익).

설계 원본(구속): vbatch_research.json final.slate V03 base_signal · V05(base_signal · static_steps · in_book_lever) · data_plan.earnings_dates · tenq.
  발표일 f = data/earn_dates.json(8-K Item 2.02 EDGAR 접수일 · 2008-01-01+ · 795사 · 54,125건 · 접수일은 발표 당일 또는 다음날 — 잡음 공개).
  위치 j(f) = f 이상인 첫 NYSE 거래일(격자). 초과수익 = 이름 일 수익(수정종가) − SPY 총수익 일 수익(랩 assets.json).
  V05 EAR  CAR = Σ_{d=f−2}^{f+1}(R_i,d − R_SPY,d) · f = 가장 최근 발표 · 유효 날 ≥ 2 · j(f) ≤ i(결정일) − 2(월말 2거래일 이상 앞) · f ≥ d − 6개월 ·
           그달 자격 이름 사이 1/99% 윈저(명세).
  V03 IRRX = 지난달 수익 − 섹터 VW 수익(그달 합집합 · 같은 GICS 섹터 · 가중 = 전달 말 시총) − CAR3 · CAR3 = Σ_{f−1}^{f+1} · f = «가장 최근» 발표(j(f) + 1 ≤ i ·
           f ≥ d − 6개월 · 없으면 0 · Dai w30917 Table 2 정의 · 섹터는 FF49 대신 GICS — 이탈 공개).
  ATTN(V05 책 안 기울기 특성): 금요일 표지 1[weekday(f) = 금] · 같은 날 합집합 8-K 2.02 접수 수(그달 명단 가운데 f 가 같은 이름 수)와 그 백분위(자격 이름 사이).
    🔎 문헌 판정(data/_vb_lit_open.json 한 곳 · v_cond.strand_status 「ATTN_sameday」): 주 판 = 판정이 primary 면 명세 정의 a_i = ½·1[금] + ½·pct(같은 날 수) ·
    아니면 a_i = 1[금요일]. 2026-09-27 판정: HLT 2006-10-25 작업 논문 판을 열었다(표 3 · 4 · 5 · 7 — 같은 날 발표가 많으면 드리프트가 세다 · 호재 부분표본 FE×NRANK
    +0.115 · 1% 유의) → primary · 주 판 = 명세 정의 · 금요일 단독 판은 attn_twin(보고용 칸 · 팔 없음).
  CH 제외(RBATCH R2 등록 규칙 복사 · r_r2flags 는 import 하지 않는다 — D22): data/_tenq_rf.json 문서 표의 v3 열(형태 · 짝 상태 · SimRF_v3 · 앞 형태) ·
    유효 짝(pair_status_v3 = ok) · B-B 짝은 변경 없음(SimRF := 1 · 경계 분포에도 1 · REG_Q1_RULE bb_nochange) ·
    경계 = 직전 달력연도에 공개된 경계 세계 유효 짝 SimRF 의 하위 20%(np.quantile linear) · 경계 세계 = in_world(그 공개월에 비금융 멤버) ∧ 공개월 2015-01..2026-07 ∧
    FPI 아님(issuer_map fpi_q) ∧ 지도 F0 위반 멤버-월 아님 · Q1 = SimRF < 경계 · CH_active(그룹, t) = 공개월 t−2..t 의 10-Q 가운데 Q1 이 있으면 1 ·
    유효 짝이 없는 창(분리 실패 · 1A 없음 · 짝 없음 · 형태 전환)은 0 + «결측» 표지 · 창에 10-Q 가 없으면 0. 개수 짝맞춤은 v_audit(허용 목록 별도 프로세스).

🚨 수익 · 신호-수익 통계를 계산하지 않는다. CAR 은 신호 원값(발표 창 반응)이고 이 모듈은 값을 찍지 않는다(연기 시험은 모양만).

  python build/v_ear.py --selftest
"""
from __future__ import annotations

import bisect
import collections
import copy
import datetime as _dt
import json
import math
import os
import sys
import traceback

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import v_data as VD          # noqa: E402

WIN_EAR = (-2, 1)
WIN_IRRX = (-1, 1)
EAR_MIN_VALID = 2
EAR_EDGE = 2                  # f 가 월말 2거래일 이상 앞
LOOK_MONTHS = 6
WINSOR = (0.01, 0.99)
Q_LO = 0.20
BOUNDARY_WORLD = ("2015-01", "2026-07")


def months_back(d, k):
    """d(YYYY-MM-DD) 에서 k 달 앞 같은 날(말일 보정)."""
    y, m, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
    n = y * 12 + (m - 1) - k
    y2, m2 = n // 12, n % 12 + 1
    import calendar
    return "%04d-%02d-%02d" % (y2, m2, min(dd, calendar.monthrange(y2, m2)[1]))


def winsorize(vals, lo=WINSOR[0], hi=WINSOR[1]):
    """{이름: 값} → 단면 1/99% 윈저(np.quantile linear · 값이 셋 미만이면 그대로)."""
    ks = [k for k, v in vals.items() if v is not None and np.isfinite(v)]
    if len(ks) < 3:
        return dict(vals)
    arr = np.array([vals[k] for k in ks], float)
    a, b = np.quantile(arr, lo), np.quantile(arr, hi)
    out = dict(vals)
    for k in ks:
        out[k] = float(min(max(vals[k], a), b))
    return out


def pct_rank(vals):
    """{이름: 값} → 백분위(0..1 · 동점 평균 순위) — 값이 없는 이름은 None."""
    ks = [k for k, v in vals.items() if v is not None and np.isfinite(v)]
    out = {k: None for k in vals}
    if not ks:
        return out
    arr = np.array([vals[k] for k in ks], float)
    order = arr.argsort(kind="mergesort")
    ranks = np.empty(len(arr))
    i = 0
    while i < len(arr):
        j = i
        while j + 1 < len(arr) and arr[order[j + 1]] == arr[order[i]]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0
        i = j + 1
    n = len(arr)
    for k, r in zip(ks, ranks):
        out[k] = float(r / (n - 1)) if n > 1 else 0.5
    return out


def attn_sameday_primary(path=None):
    """ATTN «같은 날 발표 수» 절반이 주 판인가 — 문헌 판정 파일 한 곳(data/_vb_lit_open.json · v_cond.strand_status 와 같은 파일 · 같은 규칙:
    판정이 없으면 〔초록〕 기본 = 쌍둥이). 코드를 고치지 않고 파일이 정한다."""
    import v_cond as VC
    return (VC.strand_status(path).get("ATTN_sameday") or {}).get("status") == "primary"


class Earnings:
    """발표일 표 + 우주(v_pit.Universe) — ed = earn_dates.json 의 co 꼴({티커: [날짜 …]})."""

    def __init__(self, U, ed=None, sameday_primary=None):
        self.U = U
        ed = ed if ed is not None else (VD.read_json(VD.lab_path("data/earn_dates.json")).get("co") or {})
        self.ed = {k: sorted(v) for k, v in ed.items()}
        self._key = {}
        self._r = {}
        self.sameday_primary = attn_sameday_primary() if sameday_primary is None else bool(sameday_primary)

    def key_of(self, t, k):
        ck = (t, k)
        if ck in self._key:
            return self._key[ck]
        sp = (self.U.W.get("splice") or {})
        for c in (t, t.replace("-", "."), k, (k or "").split("@")[0], sp.get(t), sp.get(t.replace("-", "."))):
            if c and c in self.ed:
                self._key[ck] = c
                return c
        self._key[ck] = None
        return None

    def jpos(self, f):
        """f 이상인 첫 격자 거래일 위치(없으면 None)."""
        j = bisect.bisect_left(self.U.dates, f)
        return j if j < self.U.D else None

    def last_f(self, t, k, i, edge):
        """결정일 격자 위치 i 에서 쓸 수 있는 가장 최근 발표 — j(f) + edge ≤ i · f ≥ d − 6개월 · (f, j) | None."""
        ek = self.key_of(t, k)
        if ek is None:
            return None
        d = self.U.dates[i]
        lo = months_back(d, LOOK_MONTHS)
        L = self.ed[ek]
        p = bisect.bisect_right(L, d) - 1
        while p >= 0 and L[p] >= lo:
            j = self.jpos(L[p])
            if j is not None and j + edge <= i:
                return L[p], j
            p -= 1
        return None

    def _xr(self, k):
        if k not in self._r:
            self._r[k] = self.U.daily_ret(k) - self.U.spy_r
        return self._r[k]

    def car(self, k, j, win):
        """Σ_{j+lo..j+hi}(R_i − R_SPY) · 유효 날 수 — 창은 격자 안만."""
        xr = self._xr(k)
        a, b = j + win[0], j + win[1]
        if a < 0 or b >= len(xr):
            return None, 0
        seg = xr[a:b + 1]
        ok = np.isfinite(seg)
        return (float(seg[ok].sum()) if ok.any() else None), int(ok.sum())

    def ear_inputs(self, m):
        """V05 — {명단 티커: {car_raw, car(윈저), f, friday, sameday_n, sameday_pct, eligible}}. 자격 = 발표 있음 · 유효 ≥ 2 · 월말 2거래일 앞."""
        U = self.U
        i = U.me_idx[m]
        mem = U.members(m)
        rows = {}
        for r in mem:
            x = self.last_f(r["t"], r["k"], i, EAR_EDGE)
            if x is None:
                rows[r["t"]] = {"eligible": False, "why": "no_announcement"}
                continue
            f, j = x
            c, n = self.car(r["k"], j, WIN_EAR)
            if c is None or n < EAR_MIN_VALID:
                rows[r["t"]] = {"eligible": False, "why": "valid_lt2", "f": f}
                continue
            rows[r["t"]] = {"eligible": True, "car_raw": c, "f": f, "friday": int(_dt.date.fromisoformat(f).weekday() == 4)}
        lo = months_back(U.dates[i], LOOK_MONTHS + 1)
        fs = collections.Counter()                                      # 같은 날 합집합 8-K 2.02 접수 수 — 그달 명단 모두의 접수일(가장 최근만이 아니다)
        for r in mem:
            ek = self.key_of(r["t"], r["k"])
            if ek:
                for x in self.ed[ek][bisect.bisect_left(self.ed[ek], lo):bisect.bisect_right(self.ed[ek], U.dates[i])]:
                    fs[x] += 1
        el = {t: v for t, v in rows.items() if v.get("eligible")}
        w = winsorize({t: v["car_raw"] for t, v in el.items()})
        cnt = {t: float(fs[v["f"]]) for t, v in el.items()}
        pc = pct_rank(cnt)
        for t, v in el.items():
            v["car"] = w[t]
            v["sameday_n"] = int(cnt[t])
            v["sameday_pct"] = pc[t]
            v["attn_friday"] = float(v["friday"])                                       # 금요일 단독 판
            v["attn_mix"] = 0.5 * v["friday"] + 0.5 * (pc[t] if pc[t] is not None else 0.5)   # 명세 정의(½·금 + ½·같은 날 수 백분위)
            v["attn_primary"] = v["attn_mix"] if self.sameday_primary else v["attn_friday"]    # 주 판 = 문헌 판정(attn_sameday_primary)
            v["attn_twin"] = v["attn_friday"] if self.sameday_primary else v["attn_mix"]       # 다른 판(보고용 칸 · 팔 없음)
        return rows

    def irrx_inputs(self, m):
        """V03 — {명단 티커: {r_m, sec_vw, car3, f, irrx, s(= −irrx)}} · 섹터 VW 가중 = 전달 말 시총(v_pit 시총 규칙)."""
        U = self.U
        i = U.me_idx[m]
        prev = VD.mshift(m, -1)
        mem = U.members(m)
        mep = U.me(prev) if prev in U.me_idx else {}
        rm, sec = {}, {}
        for r in mem:
            rm[r["t"]] = U.month_ret(r["k"], m)
            sec[r["t"]] = U.sector(r["t"], m, r.get("ndx_only", False))[0]
        num, den = collections.defaultdict(float), collections.defaultdict(float)
        for r in mem:
            w = (mep.get(r["t"]) or (None, None))[0]
            if w and rm[r["t"]] is not None and sec[r["t"]]:
                num[sec[r["t"]]] += w * rm[r["t"]]
                den[sec[r["t"]]] += w
        out = {}
        for r in mem:
            t = r["t"]
            s = sec[t]
            svw = (num[s] / den[s]) if (s and den[s] > 0) else None
            x = self.last_f(t, r["k"], i, 1)
            car3, f = 0.0, None
            if x is not None:
                f, j = x
                c, n = self.car(r["k"], j, WIN_IRRX)
                car3 = c if c is not None else 0.0
            irrx = (rm[t] - svw - car3) if (rm[t] is not None and svw is not None) else None
            out[t] = {"r_m": rm[t], "sec_vw": svw, "car3": car3, "f": f, "irrx": irrx, "s": (-irrx if irrx is not None else None)}
        return out

    def poison_after(self, m, rng):
        """결정일 뒤 접수 기록을 흔든 표 + 독 넣은 우주(선견 점검용)."""
        U2 = self.U.poison_after(m, rng)
        d = self.U.dates[self.U.me_idx[m]]
        ed2 = {}
        for k, L in self.ed.items():
            keep = [x for x in L if VD.next_session(self.U.dates, x) <= d]
            fut = [x for x in L if VD.next_session(self.U.dates, x) > d]
            shift = [(_dt.date.fromisoformat(d) + _dt.timedelta(days=int(rng.integers(1, 40)))).isoformat() for _ in fut]
            ed2[k] = sorted(keep + shift + [(_dt.date.fromisoformat(d) + _dt.timedelta(days=1)).isoformat()])
        return Earnings(U2, ed2, sameday_primary=self.sameday_primary)


# ══════════════════════════════════════════════════════════════════════════
#  CH 제외(R2 등록 규칙 복사)
# ══════════════════════════════════════════════════════════════════════════
class TenQ:
    """10-Q 위험요인 표지 — docs = _tenq_rf.json docs 꼴({cols, rows}) · fpi = {(그룹, 달): fpi_q} · viol = {(그룹, 달)}(지도 F0 위반)."""

    def __init__(self, docs=None, fpi=None, viol=None):
        if docs is None:
            d = VD.read_json(VD.lab_path("data/_tenq_rf.json"))
            docs = d["docs"]
        self.cols = {c: j for j, c in enumerate(docs["cols"])}
        self.rows = docs["rows"]
        if fpi is None or viol is None:
            im = VD.read_json(VD.lab_path("data/_issuer_map.json"))
            fpi, viol = {}, set()
            for t, rows in (im.get("tm") or {}).items():
                for r in rows:
                    if not r[2]:
                        continue
                    for ym in VD.mrange(r[0], r[1]):
                        if (r[7] if len(r) > 7 else r[5]) == 1:
                            fpi[(r[2], ym)] = 1
            for v in ((im.get("f0") or {}).get("violations") or []):
                viol.add((v[2], v[1]))
        self.fpi, self.viol = fpi, viol
        self._build()

    def _c(self, row, name):
        return row[self.cols[name]]

    def _build(self):
        pairs = []
        for r in self.rows:
            if self._c(r, "form") != "10-Q" or not self._c(r, "grp") or not self._c(r, "avail"):
                continue
            ps = self._c(r, "pair_status_v3")
            sim = self._c(r, "SimRF_v3")
            sh, psh = self._c(r, "shape_v3"), self._c(r, "prev_shape_v3")
            ok = ps == "ok" and sim is not None
            if ok and sh == "B" and psh == "B":
                sim = 1.0                                                   # 🔒 bb_nochange — B-B 짝은 변경 없음
            g, pm = self._c(r, "grp"), self._c(r, "pub_m")
            inw = bool(self._c(r, "in_world")) and BOUNDARY_WORLD[0] <= pm <= BOUNDARY_WORLD[1] and not self.fpi.get((g, pm)) and (g, pm) not in self.viol
            pairs.append({"g": g, "pm": pm, "avail": self._c(r, "avail"), "acc": self._c(r, "acc"), "ok": ok, "sim": float(sim) if ok else None,
                          "why": None if ok else ps, "inw": inw})
        by_y = collections.defaultdict(list)
        for p in pairs:
            if p["ok"] and p["inw"]:
                by_y[int(p["pm"][:4])].append(p["sim"])
        self.bounds = {}
        for y in sorted({int(p["pm"][:4]) for p in pairs}):
            v = by_y.get(y - 1) or []
            self.bounds[y] = float(np.quantile(np.asarray(v, float), Q_LO)) if v else None
        for p in pairs:
            cut = self.bounds.get(int(p["pm"][:4]))
            p["q1"] = (p["sim"] < cut) if (p["ok"] and cut is not None) else None
            if p["ok"] and cut is None:
                p["why"] = "no_boundary"
        self.by_g = collections.defaultdict(lambda: collections.defaultdict(list))
        for p in pairs:
            self.by_g[p["g"]][p["pm"]].append(p)
        self.pairs = pairs

    def ch(self, g, t):
        """CH_active(그룹, 달 t) — {"ch": 0/1, "miss": 0/1, "n": 창 안 10-Q 수} · 창 = 공개월 t−2..t."""
        if not g:
            return {"ch": 0, "miss": 1, "n": 0}
        W = []
        for k in (0, 1, 2):
            W += self.by_g[g].get(VD.mshift(t, -k), [])
        if not W:
            return {"ch": 0, "miss": 0, "n": 0}
        chv = any(p["q1"] for p in W)
        bad = any(p["why"] for p in W)
        return {"ch": int(chv), "miss": int((not chv) and bad), "n": len(W)}

    def flags(self, U, m):
        return {r["t"]: self.ch(r["gid"], m) for r in U.members(m)}

    def poison_after(self, d, rng):
        """가용일이 d 뒤인 문서의 SimRF · 형태를 난수로 바꾼 표(선견 점검용)."""
        rows = []
        ja, js, jh = self.cols["avail"], self.cols["SimRF_v3"], self.cols["shape_v3"]
        for r in self.rows:
            if r[ja] and r[ja] > d:
                r = list(r)
                r[js] = float(rng.uniform(0, 1))
                r[jh] = ("B", "U", "F")[int(rng.integers(3))]
            rows.append(r)
        return TenQ({"cols": [c for c, _ in sorted(self.cols.items(), key=lambda z: z[1])], "rows": rows}, fpi=self.fpi, viol=self.viol)


# ══════════════════════════════════════════════════════════════════════════
#  합성 시험
# ══════════════════════════════════════════════════════════════════════════
def _st_helpers():
    assert months_back("2016-08-31", 6) == "2016-02-29" and months_back("2016-03-31", 1) == "2016-02-29"
    w = winsorize({str(k): float(k) for k in range(101)})
    assert w["0"] == 1.0 and w["100"] == 99.0 and w["50"] == 50.0
    p = pct_rank({"a": 1.0, "b": 2.0, "c": 2.0, "d": None})
    assert p["a"] == 0.0 and p["b"] == p["c"] == 0.75 and p["d"] is None
    return "6개월 앞 날짜(말일 보정) · 1/99% 윈저 · 백분위(동점 평균)"


def _st_car():
    import v_pit as VP
    U, _ = VP.fake_universe()
    ed = {"N00": ["2015-01-15", "2015-04-15", "2015-07-15", "2015-10-15", "2016-01-15", "2016-03-30"],
          "N01": ["2016-02-19"], "N02": ["2015-01-01"]}
    E = Earnings(U, ed)
    m = "2016-03"
    i = U.me_idx[m]
    ea = E.ear_inputs(m)
    assert ea["N00"]["eligible"] and ea["N00"]["f"] == "2016-01-15"                    # 2016-03-30 은 월말 2거래일 안 → 앞 발표
    assert ea["N01"]["eligible"] and ea["N01"]["friday"] == 1 and ea["N02"]["eligible"] is False
    j = E.jpos("2016-01-15")
    xr = U.daily_ret("N00") - U.spy_r
    assert abs(ea["N00"]["car_raw"] - xr[j - 2:j + 2].sum()) < 1e-15
    assert ea["N00"]["attn_friday"] == 1.0 and ea["N01"]["attn_friday"] == 1.0            # 2016-01-15 · 2016-02-19 모두 금요일
    assert ea["N00"]["sameday_n"] == 1 and abs(ea["N00"]["attn_mix"] - (0.5 + 0.5 * ea["N00"]["sameday_pct"])) < 1e-15
    sd = attn_sameday_primary()                                                           # 문헌 판정 파일(data/_vb_lit_open.json)
    assert E.sameday_primary is sd
    for t in ("N00", "N01"):
        assert ea[t]["attn_primary"] == (ea[t]["attn_mix"] if sd else ea[t]["attn_friday"])
        assert ea[t]["attn_twin"] == (ea[t]["attn_friday"] if sd else ea[t]["attn_mix"])
    for flag in (True, False):                                                            # 판정 두 갈래 — 파일 없이 강제
        ef = Earnings(U, ed, sameday_primary=flag).ear_inputs(m)
        assert ef["N00"]["attn_primary"] == (ef["N00"]["attn_mix"] if flag else ef["N00"]["attn_friday"])
    nof = attn_sameday_primary(os.path.join(VD.cache_guard(), "_no_such_lit.json"))
    assert nof is False                                                                   # 판정 기록 없음 → 〔초록〕 기본 = 쌍둥이(금요일 단독이 주 판)
    ir = E.irrx_inputs(m)
    assert ir["N00"]["f"] == "2016-03-30" or ir["N00"]["f"] == "2016-01-15"
    jj = E.jpos(ir["N00"]["f"])
    assert jj + 1 <= i and abs(ir["N00"]["car3"] - xr[jj - 1:jj + 2].sum()) < 1e-15
    assert ir["N05"]["car3"] == 0.0 and ir["N05"]["f"] is None                         # 발표 없음 → 0
    if ir["N00"]["irrx"] is not None:
        assert abs(ir["N00"]["irrx"] - (ir["N00"]["r_m"] - ir["N00"]["sec_vw"] - ir["N00"]["car3"])) < 1e-15
    # 선견 — 결정일 뒤 접수를 흔들고 가격 · 원장을 독 넣어도 같다
    rng = np.random.default_rng(5)
    E2 = E.poison_after(m, rng)
    ea2, ir2 = E2.ear_inputs(m), E2.irrx_inputs(m)
    for t in ea:
        assert ea[t].get("car") == ea2[t].get("car") and ea[t].get("f") == ea2[t].get("f")
    for t in ir:
        a, b = ir[t]["irrx"], ir2[t]["irrx"]
        assert (a is None and b is None) or abs(a - b) < 1e-12
    return ("EAR CAR[−2,+1](월말 2거래일 앞 · 유효 ≥ 2 · 6개월) · 금요일 · ATTN 주 판 = 문헌 판정(½·금 + ½·같은 날 수 | 금요일 단독) · "
            "IRRX = r − 섹터 VW − CAR3(발표 없으면 0) · 결정일 뒤 접수 · 가격 독 불변")


def _st_tenq():
    cols = ["acc", "grp", "form", "avail", "pub_m", "in_world", "pair_status_v3", "SimRF_v3", "shape_v3", "prev_shape_v3"]
    rows = []
    for j in range(10):                                                              # 2016 경계 세계: SimRF 0.50 .. 0.95
        rows.append(["a%d" % j, "gW%d" % j, "10-Q", "2016-05-01", "2016-05", True, "ok", 0.5 + 0.05 * j, "U", "U"])
    rows.append(["bb", "gW0", "10-Q", "2016-08-01", "2016-08", True, "ok", 0.10, "B", "B"])      # B-B → 1.0(경계에도 1)
    rows.append(["x1", "gX", "10-Q", "2017-05-01", "2017-05", True, "ok", 0.55, "U", "F"])       # 경계(2016 분포 20%) 아래 → Q1
    rows.append(["x2", "gY", "10-Q", "2017-05-01", "2017-05", True, "ok", 0.90, "U", "U"])
    rows.append(["x3", "gZ", "10-Q", "2017-06-01", "2017-06", True, "shape_switch", None, "F", "B"])
    rows.append(["x4", "gF", "10-Q", "2016-05-01", "2016-05", True, "ok", 0.0, "U", "U"])        # FPI → 경계 세계 밖
    T = TenQ({"cols": cols, "rows": rows}, fpi={("gF", "2016-05"): 1}, viol=set())
    v = sorted([0.5 + 0.05 * j for j in range(10)] + [1.0])
    assert abs(T.bounds[2017] - float(np.quantile(v, 0.2))) < 1e-12
    assert T.ch("gX", "2017-05")["ch"] == 1 and T.ch("gX", "2017-07")["ch"] == 1 and T.ch("gX", "2017-08")["ch"] == 0
    assert T.ch("gY", "2017-05") == {"ch": 0, "miss": 0, "n": 1} and T.ch("gZ", "2017-06") == {"ch": 0, "miss": 1, "n": 1}
    assert T.ch("gQ", "2017-06") == {"ch": 0, "miss": 0, "n": 0} and T.ch(None, "2017-06")["miss"] == 1
    assert T.ch("gW0", "2016-08")["ch"] == 0                                          # B-B 는 Q1 이 될 수 없다
    return "R2 복사: v3 유효 짝 · B-B 변경 없음(경계 분포에도 1) · 직전 해 경계 세계 20% · FPI 밖 · CH_active t−2..t · 결측 표지"


def selftest():
    res, ok = [], True
    for fn in (_st_helpers, _st_car, _st_tenq):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1800:]))
    for st, nm, msg in res:
        print("  %s %-10s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("v_ear selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
