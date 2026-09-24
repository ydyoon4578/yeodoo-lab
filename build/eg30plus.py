# -*- coding: utf-8 -*-
"""build/eg30plus.py — EG30+ = EG30 에 단계를 더해 약점을 보완 · 사슬 V0 → V1(S1) → V2(B1) → V3(S2) · 대조군 · 위약 · 강건성 → data/_eg30plus.json

사전등록: build/PREREG-2026-09-24-EG30PLUS.md
사용자 원칙(2026-09-24 · C:/Project/fund_reports/펀드전략_작성원칙.md): 전략을 섞지 않고 단계를 더해 단점을 보완 · 하락장 방어 우선 · 근본 이유.

단계(파라미터는 문헌·지수 방법론의 표준값 — EG30 에 맞추지 않았다):
  S1 업종 안에서 고르고 업종 비중은 지수 가까이 — 시점정확 GICS 업종 안 Eg z(±3 윈저 · MSCI 업종중립 퀄리티) · 업종 비중 ±5%p(MSCI 최소변동성)
     · 금융(Eg 없음)은 S&P 500 금융 비중만큼 지수 구성 그대로 · 바닥이 선 업종은 다음 z 순으로 채운다.
  B1 바스켓 사전 베타 ≤ 1.00 — Frazzini–Pedersen 베타(252일 변동성 · 1260일 3일 겹침 상관 · 0.6/0.4 축소) · 업종 폭·종목 한도를 지키며
     S1 비중에서 가장 적게 움직이는(Σ(w − w1)²/w1) 비중을 SLSQP 로.
  S2 MSCI 10/40 발행사 한도(편입 때 9% · 4.5% — MSCI 10% 여유) — 20% 상한 대신 · 같은 문제를 이 한도로 다시 푼다.
판정 기준(사전등록 §4): 총수익 기준(펀드 = 0.9 × SPY TR + 0.1 × 바스켓 대 SPY TR) · 하락월 = S&P 500 PR 월 수익 < 0 인 보유월.

🚨 --dry 는 등록 전 구조 점검(제약 · V0 재현 — 공개된 EG30 만)만 한다. 후보 수익은 찍지 않는다.
🚨 실행은 EG30PLUS_COMMIT(사전등록 커밋)이 있어야 한다. 한 번 굽는 측정이다.

  python build/eg30plus.py --dry
  EG30PLUS_COMMIT=<커밋> python build/eg30plus.py
"""
from __future__ import annotations
import io, json, math, os, subprocess, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pit_panel as PP               # noqa: E402
import qg_lab as QL                  # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_eg30plus.json")
PREREG = "build/PREREG-2026-09-24-EG30PLUS.md"
FROZEN = ("build/eg30plus.py", "build/qg_lab.py", "build/pit_gics.py", "build/eg_q5.py", PREREG,
          "data/pit_gics_sectors.json", "data/_eg_q5_scores_pitgics.json", "data/_eg_q5_scores_pitgics_pre.json",
          "build/pit_panel.py", "build/pit_quarantine.py", "build/stoploss.py", "build/tech_backtest.py", "build/rally_pattern.py",
          "build/index_members.py", "data/_eg_best.json", "data/_eg_q5_scores.json", "data/mech_episodes.json")
SNAP, SNAP_FILES = "940f0bda", ("data/stocks.json", "data/pit_px.json", "data/sd")
SNAP_BASE = "bef4eea8"                                             # 작업 사본의 가격 밖 입력이 선 커밋(EGBEST 와 같은 바탕)
BASE_FILES = ("data/bench_px.json", "data/rf_monthly.json", "data/index_history.json", "data/index_ledger.json",
              "data/pit_universe.json", "data/pit_reuse.json", "data/fx", "data/fx_pit", "data/assets.json",
              "data/splits.json", "data/shares_yf.json")
MARK = os.path.join(DATA, "_eg30plus.started")                     # 한 번 굽기 표식 — 결과가 찍히기 전에 쓴다
FIN = "Financials"
SEC_NORM = {"Telecommunications Services": "Telecommunication Services"}   # 위키 옛 표기(2014-06 ~ 2017-02) → 표준 이름
# 위키 표에 한 번도 없고 오늘 분류도 빈 회사(등록 전 코드 검토) — 바이오 BMRN · 케이블 Liberty Global(2018-09 GICS 개편 전 경기소비재 미디어 → 뒤 커뮤니케이션)
_LBTY = lambda m: "Consumer Discretionary" if m < "2018-09" else "Communication Services"
SEC_MANUAL = {"BMRN": "Health Care", "LBTYA": _LBTY, "LBTYK": _LBTY, "LBTYB": _LBTY}
BAND, CAP20 = 0.05, 0.20
S2_TOP, S2_REST, S2_NTOP = 0.09, 0.045, 4
BETA_MAX = 1.00
FP_VOL, FP_VOL_MIN, FP_COR, FP_COR_MIN, FP_W = 252, 120, 1260, 750, 0.6
NPERM, SEED0 = 1000, 20260924
EG_BASE = {"signals": ["eg"], "weights": {"eg": 1}, "smooth": 1, "n": 30, "wt": "cap", "cap": 0.20, "reb": 3,
           "index": "union", "ex_fin": False, "eg": "pitgics", "mode": "base"}
ALPHA = 0.025                      # 발견 관문 — 고정 순서(S1 → B1) · 각 한쪽 2.5%(앞서 본 것이 많아 5% 가 아니다) · 임계 = t(n_d − 1)
X_IR = 0.10
S2_NI = 0.02                       # S2 비열등 여유 — 하락월 평균 Δ ≥ −0.02%p/월(V0 하락월 부진 −0.075 의 약 ¼)
M2_TOL = 5.5                       # M2 12개월 적중 여유 %p(창 약 6개)
CVAR_Q = 0.10                      # 굴린 창 하위 10% 평균(최악 한 창 대신)
SOLVER_LOG = []                    # 편입마다 쓴 풀이(기록만)


# ── 세계 ─────────────────────────────────────────────────────────────────
class World(QL.World):
    """qg_lab.World 에 ① 시점정확 GICS 업종 ② SPY 총수익 일간 ③ 목표 비중 끼워 넣기를 더한다."""

    def __init__(self):
        super().__init__()
        G = json.load(io.open(os.path.join(DATA, "pit_gics_sectors.json"), encoding="utf-8"))["months"]
        self.G = G
        self.Gm = sorted(G)
        cikmap = self.W["cikmap"]
        self.cikmap = cikmap
        tl = {}                                              # 회사 연표: 키 → [(달, 섹터)]
        self.Gidx = {}
        for ym, v in G.items():
            tk2s = {}
            for sec, ts in v["sec"].items():
                for t in ts:
                    tk2s[t] = SEC_NORM.get(sec, sec) or None
            c2s = {c: tk2s.get(t) for t, c in v["cik"].items()}
            self.Gidx[ym] = (tk2s, c2s)
            for t, s in tk2s.items():
                if s:
                    tl.setdefault("t:" + t, []).append((ym, s))
            for c, s in c2s.items():
                if s:
                    tl.setdefault("c:" + c, []).append((ym, s))
        self.Gtl = tl
        self.sec_stat = {"month": 0, "near": 0, "today": 0}
        A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
        pos = {d: i for i, d in enumerate(A["dates"])}
        spy = [A["px"]["SPY"][pos[d]] if d in pos else None for d in self.dates]
        tr = np.array([np.nan if v is None else float(v) for v in spy])
        for j in range(1, len(tr)):
            if tr[j] != tr[j]:
                tr[j] = tr[j - 1]
        self.IX_PR = self.IX.copy()
        self.IX_TR = tr
        self.logpx = {}
        self._targets = None
        self._beta_cache = {}
        self._sec, self._src, self._mc, self._bench = {}, {}, {}, {}
        # 창 이전 Eg(eg_q5.py --pit-gics --from 2014-06 · 2014-06 ~ 2016-07) 를 같은 판에 잇는다 — 달이 겹치지 않는다
        sc = self.eg_scores("pitgics")
        pre = json.load(io.open(os.path.join(DATA, "_eg_q5_scores_pitgics_pre.json"), encoding="utf-8"))["months"]
        if set(pre) & set(sc):
            raise SystemExit("🚨 창 이전 Eg 가 창 안 달과 겹친다")
        sc.update(pre)

    def mcap(self, t, k, i):
        ck = (t, k, i)
        if ck not in self._mc:
            self._mc[ck] = super().mcap(t, k, i)
        return self._mc[ck]

    # 섹터(그달 표 → 가장 가까운 달 → 오늘) · CIK 먼저, 없으면 티커 · 조회 출처는 처음 한 번만 센다
    def sector(self, t, k, m):
        ck = (t, k, m)
        if ck not in self._sec:
            before = dict(self.sec_stat)
            self._sec[ck] = self._sector_lookup(t, k, m)
            self._src[ck] = next(s for s in self.sec_stat if self.sec_stat[s] != before[s])
        return self._sec[ck]

    def sector_src(self, t, k, m):
        self.sector(t, k, m)
        return self._src[(t, k, m)]

    def _sector_lookup(self, t, k, m):
        cks =[c for c in (self.cikmap.get(t), self.cikmap.get(k), self.cikmap.get((t or "").replace("-", "."))) if c]
        tks = [x.replace("-", ".") for x in (t, k) if x]
        if m in self.Gidx:
            tk2s, c2s = self.Gidx[m]
            for c in cks:
                if c2s.get(c):
                    self.sec_stat["month"] += 1
                    return c2s[c]
            for x in tks:
                if tk2s.get(x):
                    self.sec_stat["month"] += 1
                    return tk2s[x]
        # 가까운 달 — 이전 달을 먼저(미래 분류를 덜 쓴다) · 이전 달이 없을 때만 이후 달
        best = None
        mm = int(m[:4]) * 12 + int(m[5:7])
        for key in ["c:" + c for c in cks] + ["t:" + x for x in tks]:
            for ym_, s in self.Gtl.get(key, ()):
                d = (int(ym_[:4]) * 12 + int(ym_[5:7])) - mm
                rk = (0, -d) if d <= 0 else (1, d)
                if best is None or rk < best[0]:
                    best = (rk, s)
        if best is not None:
            self.sec_stat["near"] += 1
            return best[1]
        self.sec_stat["today"] += 1
        sct = PP._sector(self.W, t, k)
        if not sct or sct == "?":
            base = (t or k or "").split("@")[0]
            if base in SEC_MANUAL:
                sct = SEC_MANUAL[base] if isinstance(SEC_MANUAL[base], str) else SEC_MANUAL[base](m)
        return sct

    # 목표 비중 끼워 넣기 — qg_lab.sleeve 가 부르는 weights 를 바꾼다
    def weights(self, cand, m):
        if cand.get("targets") is not None:
            tg = cand["targets"][m]
            return dict(tg["w"]), dict(tg["names"])
        return super().weights(cand, m)

    def run(self, targets, basis="TR", cost=None):
        """목표 비중 경로 → evaluate() 결과(basis TR: 판정선 SPY 총수익 · PR: 공개 리포트와 같은 S&P 500 PR)."""
        self.IX = self.IX_TR if basis == "TR" else self.IX_PR
        old = QL.COST
        if cost is not None:
            QL.COST = cost
        try:
            cand = dict(EG_BASE, targets=targets)
            return self.evaluate(cand, self.sleeve(cand))
        finally:
            QL.COST = old
            self.IX = self.IX_PR

    # 로그 가격
    def lp(self, k):
        if k not in self.logpx:
            p = np.asarray(self.PX[k], float)
            with np.errstate(divide="ignore", invalid="ignore"):
                self.logpx[k] = np.where(p > 0, np.log(p), np.nan)
        return self.logpx[k]

    def fp_beta(self, k, i):
        """Frazzini–Pedersen: σ_i(252일 · ≥ 120) · ρ(1260일 3일 겹침 로그수익 · ≥ 750) · β = 0.6 ρ σ_i/σ_m + 0.4. 모자라면 None."""
        ck = (k, i)
        if ck in self._beta_cache:
            return self._beta_cache[ck]
        lx, lm = self.lp(k), np.log(self.IX_PR)
        r1 = np.diff(lx[max(0, i - FP_VOL):i + 1]); m1 = np.diff(lm[max(0, i - FP_VOL):i + 1])
        ok = ~np.isnan(r1) & ~np.isnan(m1)
        out = None
        if ok.sum() >= FP_VOL_MIN:
            si, sm = np.std(r1[ok], ddof=1), np.std(m1[~np.isnan(m1)], ddof=1)
            a, b = lx[max(0, i - FP_COR):i + 1], lm[max(0, i - FP_COR):i + 1]
            r3, m3 = a[3:] - a[:-3], b[3:] - b[:-3]
            ok3 = ~np.isnan(r3) & ~np.isnan(m3)
            if ok3.sum() >= FP_COR_MIN and sm > 0:
                rho = float(np.corrcoef(r3[ok3], m3[ok3])[0, 1])
                out = FP_W * rho * si / sm + (1 - FP_W) * 1.0
        self._beta_cache[ck] = out
        return out

    def ols_beta(self, k, i):
        lx, lm = self.lp(k), np.log(self.IX_PR)
        r1 = np.diff(lx[max(0, i - FP_VOL):i + 1]); m1 = np.diff(lm[max(0, i - FP_VOL):i + 1])
        ok = ~np.isnan(r1) & ~np.isnan(m1)
        if ok.sum() < FP_VOL_MIN:
            return None
        return float(np.cov(m1[ok], r1[ok], ddof=1)[0, 1] / np.var(m1[ok], ddof=1))


# ── 구성 도구 ─────────────────────────────────────────────────────────────
def cap_weights(mc, cap):
    """시총 비례 + 발행사 상한(넘친 몫 비례 재배분 · qg_lab 과 같은 반복)."""
    tot = sum(mc.values())
    w = {x: v / tot for x, v in mc.items()}
    for _ in range(100):
        over = {x: v for x, v in w.items() if v > cap + 1e-12}
        if not over:
            break
        ex = sum(v - cap for v in over.values())
        free = {x: v for x, v in w.items() if v < cap - 1e-12}
        fs = sum(free.values())
        if fs <= 0:
            break
        for x in over:
            w[x] = cap
        for x in free:
            w[x] += ex * free[x] / fs
    return w


def water_fill(mc, total, cap):
    """업종 안 배분 — total 을 시총 비례로, 한 이름 cap 을 넘지 않게(넘치면 나머지에 비례)."""
    names = list(mc)
    w = {x: 0.0 for x in names}
    free = set(names)
    rem = total
    for _ in range(len(names) + 1):
        if not free or rem <= 1e-15:
            break
        s = sum(mc[x] for x in free)
        prop = {x: rem * mc[x] / s for x in free}
        over = [x for x in free if w[x] + prop[x] > cap + 1e-12]
        if not over:
            for x in free:
                w[x] += prop[x]
            rem = 0.0
            break
        for x in over:
            rem -= cap - w[x]
            w[x] = cap
            free.discard(x)
    return w, rem


def clamp_targets(nat, lo, hi, total):
    """업종 목표 — 자연 비중을 total 로 맞춘 뒤 [lo, hi] 로 자르고, 잘리지 않은 업종에 비례로 다시 채우기를 반복(1e-9 · 50번)."""
    secs = sorted(set(lo) | set(nat))
    s = sum(nat.get(k, 0.0) for k in secs)
    T = {k: (nat.get(k, 0.0) / s * total if s > 0 else total / len(secs)) for k in secs}
    fixed = {}
    for _ in range(50):
        for k in secs:
            if k in fixed:
                continue
            if T[k] < lo.get(k, 0.0) - 1e-12:
                T[k] = lo.get(k, 0.0); fixed[k] = "lo"
            elif T[k] > hi.get(k, 1.0) + 1e-12:
                T[k] = hi.get(k, 1.0); fixed[k] = "hi"
        gap = total - sum(T.values())
        if abs(gap) < 1e-9:
            break
        free = [k for k in secs if k not in fixed]
        if not free:
            # 모두 묶였다 — 여유가 있는 쪽으로(바닥/천장 안에서) 나눈다
            room = [k for k in secs if (gap > 0 and T[k] < hi.get(k, 1.0) - 1e-12) or (gap < 0 and T[k] > lo.get(k, 0.0) + 1e-12)]
            if not room:
                break
            for k in room:
                T[k] += gap / len(room)
            fixed = {}
            continue
        base = sum(T[k] for k in free)
        for k in free:
            T[k] += gap * (T[k] / base if base > 0 else 1 / len(free))
    return T


# ── S1 · B1 · S2 ──────────────────────────────────────────────────────────
def bench_at(Wd, m, index="spx"):
    """PIT S&P 500 구성(시총 · 업종) → (업종 비중 b_k, 금융 구성 [(t, k, 시총)], 이름 → 업종)."""
    if (m, index) in Wd._bench:
        return Wd._bench[(m, index)]
    i = Wd.me[m]
    rows = []
    for t, k in Wd.universe(m, index, False):
        mc = Wd.mcap(t, k, i)
        if mc:
            rows.append((t, k, mc, Wd.sector(t, k, m)))
    tot = sum(r[2] for r in rows)
    b = {}
    for t, k, mc, s in rows:
        b[s] = b.get(s, 0.0) + mc / tot
    fin = [(t, k, mc) for t, k, mc, s in rows if s == FIN]
    Wd._bench[(m, index)] = (b, fin, rows)
    return b, fin, rows


def s1_build(Wd, m, band=BAND, fin_mode="complete", shuffle=None, universe="union", bench_index="spx"):
    """S1 → {"w": {k: 비중}, "names": {k: t}, "sec": {k: 업종}, "meta": {...}} — 금융 구성 포함."""
    i = Wd.me[m]
    eg = Wd.raw("eg", m, universe, False, "pitgics")
    b, fin_rows, _ = bench_at(Wd, m, bench_index)
    b_fin = b.get(FIN, 0.0)
    elig = []
    for (t, k), v in eg.items():
        s = Wd.sector(t, k, m)
        mc = Wd.mcap(t, k, i)
        if s == FIN or not mc:
            continue
        elig.append([t, k, float(v), s, mc])
    if shuffle is not None:                                   # 위약 — 업종 라벨만 섞는다(업종별 수 그대로)
        labs = [e[3] for e in elig]
        shuffle.shuffle(labs)
        for e, s in zip(elig, labs):
            e[3] = s
    by = {}
    for e in elig:
        by.setdefault(e[3], []).append(e)
    allv = np.array([e[2] for e in elig])
    pm, ps = float(allv.mean()), float(allv.std(ddof=1))
    z = {}
    for s, es in by.items():
        v = np.array([e[2] for e in es])
        mu, sd = (float(v.mean()), float(v.std(ddof=1))) if len(es) >= 3 and v.std(ddof=1) > 0 else (pm, ps)
        for e in es:
            z[e[1]] = float(np.clip((e[2] - mu) / sd, -3, 3))
    rank = sorted(elig, key=lambda e: (-z[e[1]], e[0]))
    sel = rank[:30]
    nat = cap_weights({e[1]: e[4] for e in sel}, CAP20)
    info = {e[1]: e for e in elig}
    total = 1.0 - b_fin if fin_mode == "complete" else 1.0
    if fin_mode == "complete":
        bb = {s: v for s, v in b.items() if s != FIN}
    else:                                                     # SNQ 이웃 — 금융 몫을 다른 업종에 비례로
        nb = sum(v for s, v in b.items() if s != FIN)
        bb = {s: v / nb for s, v in b.items() if s != FIN}
    lo = {s: max(0.0, v - band) for s, v in bb.items()}
    hi = {s: v + band for s, v in bb.items()}
    for e in sel:                                             # 벤치에 없는 업종(드묾)은 [0, 폭]
        lo.setdefault(e[3], 0.0); hi.setdefault(e[3], band)
    natsec = {}
    for e in sel:
        natsec[e[3]] = natsec.get(e[3], 0.0) + nat[e[1]]
    chosen = {e[1] for e in sel}
    fill = []
    for _ in range(40):
        T = clamp_targets(natsec, lo, hi, total)
        short = False
        for s, tv in T.items():
            if tv <= 1e-12:
                continue
            names = [x for x in sorted(chosen) if info[x][3] == s]
            if len(names) * CAP20 + 1e-12 < tv:                # 바닥 채우기 — 다음 z 순
                nxt = [e for e in rank if e[3] == s and e[1] not in chosen]
                if nxt:
                    chosen.add(nxt[0][1]); fill.append((m, nxt[0][0], s))
                    natsec[s] = natsec.get(s, 0.0) + 1e-9       # 그 업종에 자연 몫이 없던 경우
                    short = True
                    break
                hi[s] = min(hi[s], len(names) * CAP20); lo[s] = min(lo[s], hi[s])
                short = True
                break
        if not short:
            break
    w = {}
    for s, tv in sorted(T.items()):
        names = [x for x in sorted(chosen) if info[x][3] == s]
        if not names or tv <= 1e-12:
            continue
        ws, rem = water_fill({x: info[x][4] for x in names}, tv, CAP20)
        if rem > 1e-9:
            raise RuntimeError("S1 업종 안 배분이 목표를 못 채웠다(%s %s · 남음 %.2e)" % (m, s, rem))
        w.update(ws)
    names = {x: info[x][0] for x in w}
    sec = {x: info[x][3] for x in w}
    if fin_mode == "complete" and b_fin > 0:
        ft = sum(r[2] for r in fin_rows)
        for t, k, mc in fin_rows:
            w[k] = w.get(k, 0.0) + b_fin * mc / ft
            names[k] = t; sec[k] = FIN
    tot = sum(w.values())
    if abs(tot - 1.0) > 1e-9:
        raise RuntimeError("S1 비중 합 %.12f ≠ 1 (%s)" % (tot, m))
    w = {k: v / tot for k, v in w.items()}
    return {"w": w, "names": names, "sec": sec, "b": b, "b_fin": b_fin, "lo": lo, "hi": hi, "T": T, "rank": rank,
            "fill": fill, "nonfin": [k for k in w if sec[k] != FIN], "z": {k: z.get(k) for k in w if k in z}}


def betas_for(Wd, m, keys, secs, universe_keys, kind="fp"):
    """이름별 베타 — 모자라면 그 업종(시점정확) 적격 이름들의 FP 베타 중앙값."""
    i = Wd.me[m]
    f = Wd.fp_beta if kind == "fp" else Wd.ols_beta
    raw = {k: f(k, i) for k in keys}
    med = {}
    if any(v is None for v in raw.values()):
        pool = {}
        for t, k in universe_keys:
            bv = Wd.fp_beta(k, i) if kind == "fp" else Wd.ols_beta(k, i)
            if bv is not None:
                pool.setdefault(Wd.sector(t, k, m), []).append(bv)
        med = {s: float(np.median(v)) for s, v in pool.items()}
        allb = [x for v in pool.values() for x in v]
        med["_all"] = float(np.median(allb)) if allb else 1.0
    return {k: (raw[k] if raw[k] is not None else med.get(secs[k], med.get("_all", 1.0))) for k in keys}, sum(v is None for v in raw.values())


def constrained(w1, beta, secs, lo, hi, bounds, fixed_w, fixed_beta):
    """min Σ (w − w1)²/w1 · Σ w = 1 − 고정몫 · 업종 [lo, hi] · 0 ≤ w ≤ bound · Σ w β + 고정 β 몫 ≤ 1(안 되면 가장 낮은 β 로)."""
    from scipy.optimize import minimize, linprog
    ks = sorted(w1)
    x0 = np.array([w1[k] for k in ks])
    b = np.array([beta[k] for k in ks])
    ub = np.array([bounds[k] for k in ks])
    tot = 1.0 - fixed_w
    S = sorted(set(secs[k] for k in ks))
    M = np.array([[1.0 if secs[k] == s else 0.0 for k in ks] for s in S])
    los = np.array([min(lo.get(s, 0.0), sum(w1[k] for k in ks if secs[k] == s)) for s in S])
    his = np.array([max(hi.get(s, 1.0), sum(w1[k] for k in ks if secs[k] == s)) for s in S])
    cap_b = BETA_MAX - fixed_beta
    # 도달 가능한 가장 낮은 β(선형계획)
    A_ub = np.vstack([M, -M]); b_ub = np.concatenate([his, -los])
    lp = linprog(b, A_ub=A_ub, b_ub=b_ub, A_eq=np.ones((1, len(ks))), b_eq=[tot], bounds=list(zip([0] * len(ks), ub)), method="highs")
    if lp.status != 0:
        raise RuntimeError("B1 선형계획 실패: %s" % lp.message)
    bmin = float(lp.fun)
    infeasible = bmin > cap_b + 1e-9
    target = max(cap_b, bmin + 1e-9)
    # 풀이 — 변수를 u = w/√w1 로 바꿔(목적이 ‖u − √w1‖² · 조건이 좋다) SLSQP 를 두 출발점(선형계획 해 · w1 자름)에서 돌리고,
    #   제약을 지키는 해 중 목적이 가장 작은 것을 쓴다. 둘 다 못 지키면 trust-constr. 풀이 방법은 기록한다(파라미터가 아니다).
    sc = np.sqrt(x0)
    bs, Ms = b * sc, M * sc
    obj = lambda u: float(((u - sc) ** 2).sum())
    jac = lambda u: 2 * (u - sc)
    cons = [{"type": "eq", "fun": lambda u: sc @ u - tot, "jac": lambda u: sc},
            {"type": "ineq", "fun": lambda u: target - bs @ u, "jac": lambda u: -bs},
            {"type": "ineq", "fun": lambda u: his - Ms @ u, "jac": lambda u: -Ms},
            {"type": "ineq", "fun": lambda u: Ms @ u - los, "jac": lambda u: Ms}]
    ubu = ub / sc
    bnds = list(zip([0.0] * len(ks), ubu))

    def viol_of(x):
        return max(abs(x.sum() - tot), max(0.0, b @ x - target), float(np.max(np.maximum(0, M @ x - his))),
                   float(np.max(np.maximum(0, los - M @ x))), float(np.max(np.maximum(0, x - ub))), float(np.max(np.maximum(0, -x))))
    start2 = np.clip(x0, 0, ub)
    start2 = start2 * (tot / start2.sum())
    best, msgs = None, []
    for tag, st in (("lp", lp.x), ("w1", start2)):
        r = minimize(obj, np.clip(st / sc, 0, ubu), jac=jac, method="SLSQP", bounds=bnds, constraints=cons,
                     options={"ftol": 1e-14, "maxiter": 2000})
        x = sc * r.x
        v = viol_of(x)
        msgs.append("%s: %s · 위반 %.1e" % (tag, r.message, v))
        if v <= 1e-6 and (best is None or obj(r.x) < best[0] - 1e-15):
            best = (obj(r.x), x, "slsqp-" + tag)
    if best is None:
        from scipy.optimize import LinearConstraint
        A = np.vstack([sc[None, :], bs[None, :], Ms])
        lc = LinearConstraint(A, np.concatenate([[tot], [-np.inf], los]), np.concatenate([[tot], [target], his]))
        r = minimize(obj, np.clip(lp.x / sc, 0, ubu), jac=jac, hess=lambda u: 2 * np.eye(len(u)), method="trust-constr",
                     bounds=bnds, constraints=[lc], options={"gtol": 1e-12, "xtol": 1e-14, "maxiter": 20000})
        x = sc * r.x
        v = viol_of(x)
        msgs.append("trust-constr: %s · 위반 %.1e" % (r.message, v))
        if v <= 1e-6:
            best = (obj(r.x), x, "trust-constr")
    if best is None:
        raise RuntimeError("B1/S2 제약 위반 — %s" % " | ".join(msgs))
    x = best[1]
    SOLVER_LOG.append(best[2])
    return {k: float(max(0.0, v)) for k, v in zip(ks, x)}, infeasible, bmin + fixed_beta


def b1_apply(Wd, m, S, universe="union", bound="cap20", beta_kind="fp", beta_shuffle=None, anchor=None):
    """S1 결과 S 에 베타 상한(또는 S2 한도)을 건다 → 새 목표 비중 · 기록."""
    i = Wd.me[m]
    keys = list(S["w"])
    ukeys = Wd.universe(m, universe, False)
    betas, n_fb = betas_for(Wd, m, keys, S["sec"], ukeys, beta_kind)
    nonfin = sorted(k for k in keys if S["sec"][k] != FIN)       # 정렬 — 위약의 섞기가 해시 씨앗에 매이지 않게
    finK = sorted(k for k in keys if S["sec"][k] == FIN)
    fixed_w = sum(S["w"][k] for k in finK)
    fixed_beta = sum(S["w"][k] * betas[k] for k in finK)
    if beta_shuffle is not None:                               # 위약 — S1 이름들 사이에서 β 만 섞고, 비금융 β̂ 몫이 진짜와 같게 비례로 되맞춘다
        vals = [betas[k] for k in nonfin]
        true_nf = sum(S["w"][k] * betas[k] for k in nonfin)
        beta_shuffle.shuffle(vals)
        sh = sum(S["w"][k] * v for k, v in zip(nonfin, vals))
        sc_ = true_nf / sh if sh > 0 else 1.0
        betas = dict(betas); betas.update({k: v * sc_ for k, v in zip(nonfin, vals)})
    w1 = {k: S["w"][k] for k in nonfin}
    base = anchor or w1
    names = dict(S["names"]); secs = dict(S["sec"])
    bhat = sum(S["w"][k] * betas[k] for k in keys)
    if bound == "cap20":
        bnd = {k: CAP20 for k in nonfin}
    elif bound == "s2":
        order = sorted(nonfin, key=lambda k: (-base.get(k, 0.0), S["names"][k]))
        bnd = {k: (S2_TOP if r < S2_NTOP else S2_REST) for r, k in enumerate(order)}
    elif bound == "cap5":
        bnd = {k: 0.05 for k in nonfin}
    else:
        raise ValueError(bound)
    # 한도 때문에 업종 바닥을 못 채우면 S1 의 바닥 채우기처럼 그 업종의 다음 z 이름을 더한다(기준 비중 1e-6 · 나머지 한도)
    added = []
    lo_ = dict(S["lo"])
    capped = []
    rest = S2_REST if bound == "s2" else (0.05 if bound == "cap5" else CAP20)
    for sct in sorted(set(secs[k] for k in nonfin)):
        need_lo = lo_.get(sct, 0.0)
        while sum(bnd[k] for k in w1 if secs[k] == sct) + 1e-12 < need_lo:
            nxt = [e for e in S.get("rank", []) if e[3] == sct and e[1] not in w1]
            if not nxt:                                          # 이름이 떨어졌다 — 바닥 = 한도 안에서 닿는 최대
                lo_[sct] = sum(bnd[k] for k in w1 if secs[k] == sct)
                capped.append(sct)
                break
            k = nxt[0][1]
            w1[k] = 1e-6; bnd[k] = rest; names[k] = nxt[0][0]; secs[k] = sct; added.append(nxt[0][0])
            if k not in betas:
                bb, _ = betas_for(Wd, m, [k], secs, ukeys, beta_kind)
                betas[k] = bb[k]
    need = bhat > BETA_MAX + 1e-12 or any(w1[k] > bnd[k] + 1e-12 for k in nonfin)
    rec = {"m": m, "beta_pre": bhat, "fallback": n_fb, "bound": bound}
    if not need:
        rec.update({"beta_post": bhat, "bind": False, "infeasible": False})
        return dict(S["w"]), rec, names
    w, infeas, bmin = constrained(w1, betas, secs, lo_, S["hi"], bnd, fixed_w, fixed_beta)
    out = {k: v for k, v in w.items() if v > 1e-12}
    for k in finK:
        out[k] = S["w"][k]
    rec.update({"beta_post": sum(out[k] * betas[k] for k in out), "bind": True, "infeasible": infeas, "beta_min": bmin, "added": added,
                "floor_capped": capped, "solver": SOLVER_LOG[-1]})
    return out, rec, names


def v0_s2(Wd, m, universe="union"):
    """V0 + S2 — EG30 선택 · 시총 비례 · 10/40 한도(넘친 몫 비례)."""
    w, names = QL.World.weights(Wd, dict(EG_BASE, index=universe), m)
    order = sorted(w, key=lambda k: -w[k])
    bnd = {k: (S2_TOP if r < S2_NTOP else S2_REST) for r, k in enumerate(order)}
    for _ in range(200):
        over = {k: v for k, v in w.items() if v > bnd[k] + 1e-12}
        if not over:
            break
        ex = sum(v - bnd[k] for k, v in over.items())
        free = {k: v for k, v in w.items() if v < bnd[k] - 1e-12}
        fs = sum(free.values())
        if fs <= 0:
            break
        for k in over:
            w[k] = bnd[k]
        for k in free:
            w[k] += ex * free[k] / fs
    return w, names


def v0_b1(Wd, m, universe="union"):
    """V0 + B1(업종 폭 없음) — EG30 비중에서 베타만 ≤ 1."""
    i = Wd.me[m]
    w0, names = QL.World.weights(Wd, dict(EG_BASE, index=universe), m)
    secs = {k: Wd.sector(names[k], k, m) for k in w0}
    betas, n_fb = betas_for(Wd, m, list(w0), secs, Wd.universe(m, universe, False))
    bhat = sum(w0[k] * betas[k] for k in w0)
    if bhat <= BETA_MAX:
        return w0, names, bhat
    w, _, _ = constrained(w0, betas, secs, {}, {}, {k: CAP20 for k in w0}, 0.0, 0.0)
    return w, names, bhat


# ── 판정 ─────────────────────────────────────────────────────────────────
def nw_t(x, lag=3):
    x = np.asarray(x, float)
    n = len(x)
    if n < 5:
        return None
    e = x - x.mean()
    s = (e @ e) / n
    for L in range(1, min(lag, n - 1) + 1):
        s += 2.0 * (1.0 - L / (lag + 1.0)) * (e[L:] @ e[:-L]) / n
    return float(x.mean() / math.sqrt(s / n)) if s > 0 else None


def down_months(Wd, hold):
    """S&P 500 PR 월 수익 < 0 인 보유월."""
    me = Wd.me
    out = []
    for h in hold:
        a, b = me[QL.PP.mshift(h, -1)], me[h]
        if Wd.IX_PR[b] / Wd.IX_PR[a] - 1 < 0:
            out.append(h)
    return out


def rolling12(ex, ix):
    """12개월 굴린 초과 = 펀드 12개월 복리 수익 − 지수 12개월 복리 수익(%p) · 펀드 월 = 지수 월 + 월 초과.
    cvar10 = 하위 10% 창(올림 · 109창이면 11개)의 평균 — 최악 한 창보다 한 사건에 덜 매인다."""
    ex, ix = np.asarray(ex, float) / 100, np.asarray(ix, float) / 100
    f = ix + ex
    r = np.array([(np.prod(1 + f[k - 12:k]) - np.prod(1 + ix[k - 12:k])) * 100 for k in range(12, len(ex) + 1)])
    q = max(1, int(math.ceil(CVAR_Q * len(r))))
    return {"n": len(r), "hit": float(np.mean(r > 0) * 100), "worst": float(r.min()), "sd": float(r.std(ddof=1)),
            "cvar10": float(np.sort(r)[:q].mean()), "cvar_n": q}


def roll(res):
    _, ex, _, ix = arr(res)
    return rolling12(ex, ix)


def frozen_check():
    """사전등록 커밋과 파일이 같아야 돈다(EGBEST 와 같은 다섯 겹).
    ① EG30PLUS_COMMIT 이 사전등록 문서를 처음 더한 커밋 ② origin/main 의 조상 ③ FROZEN 이 그 커밋과 바이트 단위로 같다(CRLF 무시)
    ④ 가격 파일이 자료 판 SNAP 과 · 가격 밖 입력이 SNAP_BASE 와 같다 ⑤ 산출물 · 시작 표식이 없고 origin/main 에도 없다
    (다시 돌리려면 EG30PLUS_RERUN=사유 — JSON 에 남는다) · scipy 1.18.1."""
    c = os.environ.get("EG30PLUS_COMMIT")
    if not c:
        raise SystemExit("🚨 EG30PLUS_COMMIT(사전등록 커밋)을 넘겨라 — 등록 전에는 --dry 만 된다.")
    g = lambda *a: subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True)
    full = g("rev-parse", c + "^{commit}").stdout.strip()
    added = g("log", "--format=%H", "--diff-filter=A", full, "--", PREREG).stdout.split()
    if not added or added[-1] != full:
        raise SystemExit("🚨 %s 는 사전등록 문서를 처음 더한 커밋이 아니다." % full[:8])
    if g("merge-base", "--is-ancestor", full, "origin/main").returncode != 0:
        raise SystemExit("🚨 사전등록 커밋이 origin/main 에 없다 — 먼저 푸시.")
    rerun = os.environ.get("EG30PLUS_RERUN")
    if (os.path.exists(OUT) or os.path.exists(MARK)) and not rerun:
        raise SystemExit("🚨 %s 또는 시작 표식이 이미 있다 — 한 번 굽는 측정이다." % OUT)
    for ref in ("origin/main:data/_eg30plus.json", "origin/main:build/PREREG-2026-09-24-EG30PLUS-RESULT.md"):
        if g("cat-file", "-e", ref).returncode == 0 and not rerun:
            raise SystemExit("🚨 %s 가 이미 커밋돼 있다 — 한 번 굽는 측정이다." % ref)
    if g("diff", "--quiet", SNAP, "--", *SNAP_FILES).returncode != 0:
        raise SystemExit("🚨 자료 판이 %s 가 아니다." % SNAP)
    if g("diff", "--quiet", SNAP_BASE, "--", *BASE_FILES).returncode != 0:
        raise SystemExit("🚨 가격 밖 입력이 %s 와 다르다." % SNAP_BASE)
    for p in FROZEN:
        if not os.path.exists(os.path.join(ROOT, p)):
            raise SystemExit("🚨 %s 가 없다 — 사전등록 커밋에서 그 경로만 꺼내 온다." % p)
        want = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (full, p)], capture_output=True).stdout
        have = open(os.path.join(ROOT, p), "rb").read()
        if want.replace(b"\r\n", b"\n") != have.replace(b"\r\n", b"\n"):
            raise SystemExit("🚨 %s 가 사전등록 커밋과 다르다." % p)
    import scipy
    if scipy.__version__ != "1.18.1" or np.__version__ != "2.5.3":
        raise SystemExit("🚨 scipy %s ≠ 1.18.1 또는 numpy %s ≠ 2.5.3" % (scipy.__version__, np.__version__))
    return full


def formations(Wd):
    return [m for j, m in enumerate(Wd.months) if j == 0 or int(m[5:7]) % 3 == 0]


def build_chain(Wd, universe="union", band=BAND, fin_mode="complete", beta_kind="fp", s1_shuffle=None, b1_shuffle=None, s2_bound="s2"):
    """V1 · V2 · V3 목표 경로(편입월마다)와 기록."""
    T = {"V1": {}, "V2": {}, "V3": {}}
    rec = {"S1": [], "B1": [], "S2": []}
    for m in formations(Wd):
        S = s1_build(Wd, m, band=band, fin_mode=fin_mode, shuffle=s1_shuffle, universe=universe)
        T["V1"][m] = {"w": S["w"], "names": S["names"]}
        rec["S1"].append({"m": m, "n": len(S["w"]), "n_nonfin": len(S["nonfin"]), "b_fin": S["b_fin"], "fill": S["fill"]})
        w2, r2, n2 = b1_apply(Wd, m, S, universe, "cap20", beta_kind, b1_shuffle)
        T["V2"][m] = {"w": w2, "names": n2}
        rec["B1"].append(r2)
        # S2 는 B1 의 문제를 한도만 바꿔 다시 푼다 — 기준(anchor)은 S1 비중, 순위는 V2 비중
        S1w = S["w"]
        Sx = dict(S)
        w3, r3, n3 = b1_apply(Wd, m, Sx, universe, s2_bound, beta_kind, None, anchor={k: w2.get(k, 0.0) for k in S1w})
        T["V3"][m] = {"w": w3, "names": n3}
        rec["S2"].append(dict(r3, max_w=max(v for k, v in w3.items())))
    return T, rec


def v0_targets(Wd, universe="union"):
    out = {}
    for m in formations(Wd):
        w, names = QL.World.weights(Wd, dict(EG_BASE, index=universe), m)
        out[m] = {"w": w, "names": names}
    return out


# ── 빠른 평가 — evaluate() 의 펀드 규칙만(위약 1000번 · 창 이전) · dry 가 evaluate 와 맞춰 본다 ──
def quick(Wd, targets, basis="TR", cost=None):
    Wd.IX = Wd.IX_TR if basis == "TR" else Wd.IX_PR
    old = QL.COST
    if cost is not None:
        QL.COST = cost
    try:
        path, bturn, _ = Wd.sleeve(dict(EG_BASE, targets=targets))
        me, months, IX, SLV = Wd.me, Wd.months, Wd.IX, QL.SLEEVE
        i0, iE = me[months[0]], me[PP.mshift(months[-1], 1)]
        mends = [me[m] for m in months] + [iE]
        ms = set(mends[1:])
        fp = {i0: 1.0}
        ixv, slv = 1 - SLV, SLV
        for d in range(i0 + 1, iE + 1):
            ixv *= IX[d] / IX[d - 1]
            slv *= path[d] / path[d - 1]
            v = ixv + slv
            if d in ms:
                v -= QL.COST * 2 * abs(slv / v - SLV) * v
                ixv, slv = v * (1 - SLV), v * SLV
            fp[d] = v
        f = lambda p: np.array([p[mends[j + 1]] / p[mends[j]] - 1.0 for j in range(len(months))])
        fr, im, sr = f(fp), f(IX), f(path)
        return {"hold": [PP.mshift(m, 1) for m in months], "ex": (fr - im) * 100, "basket": sr * 100, "index": im * 100, "turn": bturn}
    finally:
        QL.COST = old
        Wd.IX = Wd.IX_PR


# ── 판정 통계 ─────────────────────────────────────────────────────────────
def arr(res):
    """evaluate 결과 또는 quick 결과 → (보유월, 펀드 월 초과 %, 바스켓 월 %, 지수 월 %)."""
    if "ex" in res:
        return res["hold"], np.asarray(res["ex"], float), np.asarray(res["basket"], float), np.asarray(res["index"], float)
    return (res["hold_months"], np.array(res["monthly_ex"], float), np.array(res["monthly"]["basket"], float),
            np.array(res["monthly"]["index"], float))


def basket_beta(res):
    _, _, b, x = arr(res)
    return float(np.cov(x, b, ddof=1)[0, 1] / np.var(x, ddof=1))


def capture(res, mask):
    """바스켓 포착 — 그 달들의 바스켓 평균 월 수익 ÷ 지수 평균 월 수익(산술)."""
    _, _, b, x = arr(res)
    return float(b[mask].mean() / x[mask].mean())


def h1_mask(hold):
    return np.array([h < "2021-09" for h in hold])


def down_t(d, dmask, lag=3):
    """판정 통계 — 달력 시간 점수 HAC. Δ_t 를 [D_t, 1 − D_t] 에 회귀하면 하락 계수 = 하락월 Δ 평균 ·
    그 점수 g_t = D_t (Δ_t − 평균) 에 Bartlett 시차 3(달력 달)을 걸고 n_d/(n_d − 1) 로 보정한다. 임계는 t(n_d − 1)."""
    d = np.asarray(d, float)
    D = np.asarray(dmask, bool)
    nd = int(D.sum())
    if nd < 5:
        return None
    mu = float(d[D].mean())
    g = np.where(D, d - mu, 0.0)
    S = float(g @ g)
    for L in range(1, lag + 1):
        S += 2.0 * (1.0 - L / (lag + 1.0)) * float(g[L:] @ g[:-L])
    var = S / nd ** 2 * nd / (nd - 1)
    return float(mu / math.sqrt(var)) if var > 0 else None


def t_crit(nd):
    from scipy.stats import t as _t
    return float(_t.ppf(1 - ALPHA, nd - 1))


def cluster_t(d, dmask, hold):
    """민감도(관문 아님) — 보유 연도 군집 t · 임계 t(G − 1)."""
    d = np.asarray(d, float)
    D = np.asarray(dmask, bool)
    mu = float(d[D].mean())
    G = {}
    for x, dm, h in zip(d, D, hold):
        if dm:
            G[h[:4]] = G.get(h[:4], 0.0) + (x - mu)
    g = np.array(list(G.values()))
    nd, nG = int(D.sum()), len(g)
    var = float(g @ g) / nd ** 2 * nG / (nG - 1)
    from scipy.stats import t as _t
    return {"t": float(mu / math.sqrt(var)) if var > 0 else None, "G": nG, "crit": float(_t.ppf(1 - ALPHA, nG - 1))}


def step_stats(prev, cur, dmask):
    """V_k − V_{k−1} 월 초과 차 Δ — 하락월 평균 · 달력 HAC t(판정) · 부분열 NW t · 연도 군집 t(민감도) · 하락월 안 기울기 ·
    상승월 평균 · 전·후반 · 30개월 토막."""
    hold, a, _, ix = arr(prev)
    _, b, _, _ = arr(cur)
    d = b - a
    dd = d[dmask]
    t = down_t(d, dmask)
    try:
        sb, st_ = nw_ols(dd, np.column_stack([np.ones(len(dd)), ix[dmask]]))
        slope = {"b": float(sb[1]), "t": float(st_[1])}
    except Exception:
        slope = None
    h1 = h1_mask(hold)
    blk = np.arange(len(d)) // 30
    blocks = [float(d[(blk == q) & dmask].mean()) if ((blk == q) & dmask).any() else None for q in range(int(blk.max()) + 1)]
    return {"down_mean": float(dd.mean()), "down_t": t, "down_t_sub": nw_t(dd), "cluster": cluster_t(d, dmask, hold), "down_slope": slope,
            "down_se": (abs(float(dd.mean()) / t) if t else None), "down_sum": float(dd.sum()),
            "up_mean": float(d[~dmask].mean()), "all_mean": float(d.mean()), "all_ann": float(d.mean() * 12),
            "half1": float(d[dmask & h1].mean()), "half2": float(d[dmask & ~h1].mean()),
            "blocks": blocks, "blocks_pos": int(sum(1 for x in blocks if x is not None and x > 0))}


def summary(res, dmask):
    hold, ex, bk, ix = arr(res)
    h1 = h1_mask(hold)
    yrs = {y: v["ex"] for y, v in res["yearly"].items()}
    return {"ann_ex": res["all"]["ann_ex"], "te": res["all"]["te"], "ir": res["all"]["ir"], "t": res["all"]["t"], "nw_t": nw_t(ex),
            "down_mean": float(ex[dmask].mean()), "down_sum": float(ex[dmask].sum()), "down_win": float(np.mean(ex[dmask] > 0) * 100),
            "up_mean": float(ex[~dmask].mean()),
            "basket_down_capture": capture(res, dmask), "basket_up_capture": capture(res, ~dmask), "basket_beta": basket_beta(res),
            "roll12": rolling12(ex, ix), "roll12_h1": rolling12(ex[h1], ix[h1]), "turn": res["basket_turn_oneway"],
            "years": yrs, "years_won": int(sum(v > 0 for v in yrs.values())), "n_years": len(yrs),
            "crash_won": int(sum(e["ex"] > 0 for e in res["episodes"] if e["kind"] == "급락")),
            "surge_won": int(sum(e["ex"] > 0 for e in res["episodes"] if e["kind"] == "급등")),
            "episodes": [{"kind": e["kind"], "name": e["name"], "ex": e["ex"], "basket_ex": e["basket_ex"]} for e in res["episodes"]],
            "mdd_fund": res["mdd"]["fund_all"], "mdd_index": res["mdd"]["index_all"], "eff_n_last": res["holdings"]["eff_n"]}


def dilution(prev_ex, cur_ex):
    """수익 맞춘 희석 대조 — V_{k−1} 의 바스켓을 덜 드는 것(c* = 평균 초과 비 · [0, 1] 로 자름)으로 V_k 와 같은 평균 초과를 내는 판.
    V_{k−1} 평균 초과 ≤ 0 이면 c* = 1(V_{k−1} 그대로)."""
    m0 = float(np.mean(prev_ex))
    c = 1.0 if m0 <= 0 else float(np.clip(np.mean(cur_ex) / m0, 0.0, 1.0))
    return c, c * np.asarray(prev_ex, float)


def mech_frame(res):
    """랩의 기계적 틀(data/mech_episodes.json frozen · PREREG-2026-09-24-LIBMETA S0)로 잰 초과 — RESULT 에만 싣는다(관문 아님 · 펀드 리포트에 넣지 않는다).
    급락월 · 급등월(SPY 총수익 ±σ_pre 월) 펀드 월 초과 · 급락 다리(지그재그 10%) · 반등 창(63거래일) 펀드 경로 초과(%p)."""
    ME = json.load(io.open(os.path.join(DATA, "mech_episodes.json"), encoding="utf-8"))
    hold, ex, _, _ = arr(res)
    pos = {h: j for j, h in enumerate(hold)}
    S = res["series"]
    di = {d: j for j, d in enumerate(S["d"])}
    f, x = np.array(S["fund"]), np.array(S["index"])

    def seg(a, b):
        ia = di.get(a); ib = di.get(b)
        if ia is None or ib is None:
            return None
        return float((f[ib] / f[ia] - x[ib] / x[ia]) * 100)
    out = {}
    for key in ("crash_m", "surge_m"):
        js = [pos[m] for m in ME["months"][key] if m in pos]
        e = ex[js]
        out[key] = {"n": len(js), "mean": float(e.mean()) if len(js) else None, "sum": float(e.sum()), "win": int((e > 0).sum())}
    legs = [seg(l["a"], l["b"]) for l in ME["frozen"]["legs"] if l["side"] == "crash"]
    rebs = [seg(r["a"], r["b"]) for r in ME["frozen"]["rebounds"]]
    for key, v in (("crash_legs", legs), ("rebounds", rebs)):
        vv = [y for y in v if y is not None]
        out[key] = {"n": len(vv), "mean": float(np.mean(vv)) if vv else None, "win": int(sum(y > 0 for y in vv)), "each": v}
    return out


def nw_ols(y, X, lag=3):
    """OLS 계수와 Newey–West(시차 3) t."""
    y, X = np.asarray(y, float), np.asarray(X, float)
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ X.T @ y
    e = y - X @ b
    n = len(y)
    g = X * e[:, None]
    S = g.T @ g
    for L in range(1, lag + 1):
        G = g[L:].T @ g[:-L]
        S += (1 - L / (lag + 1)) * (G + G.T)
    V = XtXi @ S @ XtXi
    return b, b / np.sqrt(np.diag(V))


def beta_shift(prev, cur):
    """교환 탐지(랩 LIBMETA 와 같은 뜻) — Δ_t = a + b · 지수 월 수익. b < 0 이고 a ≈ 0 이면 «베타를 낮춘 것» 일 뿐이다. 싣기만."""
    _, a0, _, ix = arr(prev)
    _, a1, _, _ = arr(cur)
    b, t = nw_ols(a1 - a0, np.column_stack([np.ones(len(ix)), ix]))
    return {"alpha_m": float(b[0]), "alpha_t": float(t[0]), "slope": float(b[1]), "slope_t": float(t[1])}


def cap_buckets(Wd, m, w, nxt_i, universe="union"):
    """시총 순위 구간(1–100 · 101–250 · 251+)별 바스켓 비중과 다음 편입까지 기여(바스켓 %p · 지수 PR 대비 · 매수 뒤 보유)."""
    i = Wd.me[m]
    mc = sorted(((Wd.mcap(t, k, i), k) for t, k in Wd.universe(m, universe, False)), reverse=True)
    rk = {k: r + 1 for r, (_, k) in enumerate(mc)}
    rix = Wd.IX_PR[nxt_i] / Wd.IX_PR[i] - 1
    out = {b: {"w": 0.0, "contrib": 0.0} for b in ("1-100", "101-250", "251+")}
    for k, x in w.items():
        r = rk.get(k, 10 ** 6)
        b = "1-100" if r <= 100 else ("101-250" if r <= 250 else "251+")
        p0, p1 = Wd.PX[k][i], SL_last_valid(Wd.PX[k], nxt_i, i)
        ri = (p1 / p0 - 1) if (p1 and p0 == p0 and p0 > 0) else 0.0
        out[b]["w"] += x
        out[b]["contrib"] += x * (ri - rix) * 100
    return out, rk


def SL_last_valid(p, j, lo):
    for x in range(j, lo - 1, -1):
        if p[x] == p[x] and p[x] > 0:
            return p[x]
    return None


def chain_diag(Wd, T0, T, rec):
    """편입별 구성 기록(판정 아님) — 시총 구간 · 바닥 채움 이름의 순위 · 실효 종목 수 · 섹터 조회 출처."""
    fm = formations(Wd)
    end = [Wd.me[x] for x in fm[1:]] + [Wd.me[PP.mshift(Wd.months[-1], 1)]]
    rows = []
    for j, m in enumerate(fm):
        b0, rk = cap_buckets(Wd, m, T0[m]["w"], end[j])
        b1, _ = cap_buckets(Wd, m, T["V1"][m]["w"], end[j])
        w3 = T["V3"][m]["w"]
        s1 = rec["S1"][j]
        fill_rk = [rk.get(next((k for k, t in T["V1"][m]["names"].items() if t == f[1]), None), None) for f in s1["fill"]]
        rows.append({"m": m, "V0": b0, "V1": b1, "fill": [f[1] for f in s1["fill"]], "fill_rank": fill_rk,
                     "eff_n_V0": 1 / sum(x * x for x in T0[m]["w"].values()),
                     "eff_n_V1": 1 / sum(x * x for x in T["V1"][m]["w"].values()),
                     "eff_n_V2": 1 / sum(x * x for x in T["V2"][m]["w"].values()),
                     "eff_n_V3": 1 / sum(x * x for x in w3.values()),
                     "max_w_V3": max(w3.values()), "max_w_V2": max(T["V2"][m]["w"].values()),
                     "drift_over10_V3": drift_over(Wd, m, w3, end[j], 0.10), "drift_over10_V2": drift_over(Wd, m, T["V2"][m]["w"], end[j], 0.10),
                     "src_V1": src_share(Wd, m, T["V1"][m]), "bench_priced": bench_priced(Wd, m),
                     "fin_max_V1": max([x for k, x in T["V1"][m]["w"].items() if Wd.sector(T["V1"][m]["names"][k], k, m) == FIN] or [0.0])})
    return rows


def drift_over(Wd, m, w, end_i, lim):
    """편입 뒤 다음 편입까지 월말마다 흘러간 비중(매수 뒤 보유) — 한 회사가 lim 을 넘은 월말 수."""
    i0 = Wd.me[m]
    n = 0
    for mm in Wd.all_m:
        e = Wd.me[mm]
        if not (i0 < e <= end_i):
            continue
        v = {}
        for k, x in w.items():
            p0, p1 = Wd.PX[k][i0], SL_last_valid(Wd.PX[k], e, i0)
            v[k] = x * (p1 / p0 if (p1 and p0 == p0 and p0 > 0) else 1.0)
        s = sum(v.values())
        n += int(max(v.values()) / s > lim + 1e-12)
    return n


def src_share(Wd, m, tg):
    """그 편입 바스켓 비금융 비중 중 업종이 그달 표 · 가까운 달 · 오늘 분류에서 온 몫."""
    out = {"month": 0.0, "near": 0.0, "today": 0.0}
    for k, x in tg["w"].items():
        t = tg["names"][k]
        if Wd.sector(t, k, m) == FIN:
            continue
        out[Wd.sector_src(t, k, m)] += x
    return out


def bench_priced(Wd, m):
    """벤치 업종 비중을 재는 S&P 500 명단 중 시총이 선 회사의 비율(이중클래스 하나로 줄이기 전 명단 기준)."""
    mem = Wd.W["lists"]["spx"].get(m) or []
    return len(Wd.universe(m, "spx", False)) / max(1, len(mem))


# ── 창 이전(2014-06 ~ 2016-06 형성 · 보유 2014-07 ~ 2016-07) ─────────────────────
PRE0, PRE1 = "2014-06", "2016-06"


def pre_coverage(Wd, months):
    """F0 커버리지 — 그 월말 S&P 500 ∪ NASDAQ 100 비금융 명단 회사(이중클래스 하나로) 중 가격 · 시총 · Eg 가 선 회사의 비율.
    사전등록 규칙: 모든 편입월에서 ≥ 90% 일 때만 창 이전 거부권이 선다(설계 문서 그대로 — 창 안 첫 편입도 같은 식으로 잰다)."""
    rows = []
    for m in months:
        i = Wd.me[m]
        pairs, n_co = PP.union_members(Wd.W, m, i)
        keyed = {t for t, _ in pairs}
        mem = set(Wd.W["lists"]["spx"].get(m) or []) | set(Wd.W["lists"]["ndx"].get(m) or [])
        by = {}                                                  # 이중클래스 하나로(CIK) — 키가 선 종목이 있는 회사는 키 쪽으로 센다
        for t in mem:
            if t in Wd.W["reassigned"] and m >= Wd.W["reassigned"][t].get("last", "9999"):
                continue                                         # 재배정 티커의 마지막 멤버월 — union_members 와 같이 뺀다
            c = Wd.cikmap.get(t) or Wd.cikmap.get(t.replace("-", "."))
            by.setdefault(c or ("_" + t), []).append(t)
        nonfin_keyed = [(t, k) for t, k in pairs if Wd.sector(t, k, m) != FIN]
        n_unkeyed_nonfin = sum(1 for ts in by.values() if not any(t in keyed for t in ts) and Wd.sector(ts[0], ts[0], m) != FIN)
        sc = Wd.eg_scores("pitgics").get(m) or {}
        ok = [(t, k) for t, k in nonfin_keyed if Wd.mcap(t, k, i) and (t in sc or k in sc)]
        den = len(nonfin_keyed) + n_unkeyed_nonfin
        rows.append({"m": m, "nonfin": den, "keyed": len(nonfin_keyed), "ok": len(ok), "cover": len(ok) / max(1, den)})
    return rows


def pre_window(Wd):
    """창 이전 — V0 ~ V3 와 이웃 팔을 같은 규칙으로 굽는다(측정). 커버리지 규칙이 서면 거부권, 아니면 «창 이전 증거 없음»."""
    keep = Wd.months
    first = pre_coverage(Wd, [keep[0]])[0]                        # 창 안 첫 편입(2016-08) — 같은 식
    try:
        Wd.months = [m for m in Wd.all_m if PRE0 <= m <= PRE1]
        fm = formations(Wd)
        cov = pre_coverage(Wd, fm)
        T0 = v0_targets(Wd)
        T, rec = build_chain(Wd)
        R = {"V0": quick(Wd, T0)}
        for v in ("V1", "V2", "V3"):
            R[v] = quick(Wd, T[v])
        hold = R["V0"]["hold"]
        dm = np.array([h in set(down_months(Wd, hold)) for h in hold])
        arms = {}
        arms["V0+B1"] = quick(Wd, {m: dict(zip(("w", "names"), v0_b1(Wd, m)[:2])) for m in fm})
        arms["V0+S2"] = quick(Wd, {m: dict(zip(("w", "names"), v0_s2(Wd, m))) for m in fm})
        arms["S1 0pp"] = quick(Wd, build_chain(Wd, band=0.0)[0]["V1"])
        arms["S1 SNQ"] = quick(Wd, build_chain(Wd, fin_mode="snq")[0]["V1"])
        arms["B1 OLS"] = quick(Wd, build_chain(Wd, beta_kind="ols")[0]["V2"])
        arms["S2 cap5"] = quick(Wd, build_chain(Wd, s2_bound="cap5")[0]["V3"])
        d = lambda a, b: float((b["ex"] - a["ex"])[dm].mean()) if dm.any() else None
        out = {"months": [fm[0], fm[-1]], "hold": [hold[0], hold[-1]], "n": len(hold), "n_down": int(dm.sum()),
               "coverage": cov, "min_cover": min(r["cover"] for r in cov), "first_in_window": first,
               "S1_down_d": d(R["V0"], R["V1"]), "B1_down_d": d(R["V1"], R["V2"]),
               "S2_sd": [roll(R["V2"])["sd"], roll(R["V3"])["sd"]],
               "ann_ex": {v: float(R[v]["ex"].mean() * 12) for v in R}, "down_mean": {v: float(R[v]["ex"][dm].mean()) for v in R},
               "arms_down_mean": {a: float(r["ex"][dm].mean()) for a, r in arms.items()},
               "arms_ann_ex": {a: float(r["ex"].mean() * 12) for a, r in arms.items()},
               "B1_infeasible": [r["m"] for r in rec["B1"] if r.get("infeasible")]}
        out["pass"] = out["min_cover"] >= 0.90
        out["veto"] = ({"S1": out["S1_down_d"] >= 0, "B1": out["B1_down_d"] >= 0, "S2": out["S2_sd"][1] <= out["S2_sd"][0]}
                       if out["pass"] else {"S1": True, "B1": True, "S2": True})
        out["note"] = "커버리지 통과 — 거부권이 선다" if out["pass"] else "창 이전 증거 없음 — 커버리지 < 90% (거부권 없음 · 측정만)"
        return out
    finally:
        Wd.months = keep


# ── 위약 ─────────────────────────────────────────────────────────────────
def placebos(Wd, S1cache, base_V0, base_V1, dmask, t0):
    import random
    fm = formations(Wd)
    pS1, pB1 = [], []
    for i in range(NPERM):
        rng = random.Random(SEED0 + i)
        Tp = {}
        for m in fm:
            S = s1_build(Wd, m, shuffle=rng)
            Tp[m] = {"w": S["w"], "names": S["names"]}
        pS1.append(float((quick(Wd, Tp)["ex"] - base_V0)[dmask].mean()))
        rng2 = random.Random(SEED0 + i)
        Tq = {}
        for m in fm:
            w2, _, n2 = b1_apply(Wd, m, S1cache[m], "union", "cap20", "fp", rng2)
            Tq[m] = {"w": w2, "names": n2}
        pB1.append(float((quick(Wd, Tq)["ex"] - base_V1)[dmask].mean()))
        if (i + 1) % 50 == 0:
            print("  위약 %d/%d (%.0f초)" % (i + 1, NPERM, time.time() - t0), flush=True)
    return pS1, pB1


def dry() -> int:
    """등록 전 구조 점검 — 공개된 EG30(V0)의 재현 · quick 과 evaluate 일치 · 제약 · 창 이전 커버리지. 후보 수익 · 걸림 수는 찍지 않는다."""
    t0 = time.time()
    Wd = World()
    E = json.load(io.open(os.path.join(DATA, "_eg_best.json"), encoding="utf-8"))["results"]["EG_BASE"]
    T0 = v0_targets(Wd)
    r0 = Wd.run(T0, basis="PR")
    gap = max(abs(a - b) for a, b in zip(r0["monthly"]["basket"], E["monthly"]["basket"]))
    print("V0 재현: 바스켓 월 최대 차 %.2e · 회전 %.4f vs %.4f" % (gap, r0["basket_turn_oneway"], E["basket_turn_oneway"]))
    rt = Wd.run(T0, basis="TR")
    q = quick(Wd, T0)
    qgap = float(np.max(np.abs(q["ex"] - np.array(rt["monthly_ex"]))))
    hold = rt["hold_months"]
    dm = np.array([h in set(down_months(Wd, hold)) for h in hold])
    s = summary(rt, dm)
    print("quick ↔ evaluate 월 초과 최대 차 %.2e" % qgap)
    print("V0 TR(공개 판 · 설계 문서 값과 대조): 연 %+.2f · TE %.2f · IR %.2f · NW t %.2f · 하락월 %d · 합 %+.2f · 승 %.0f%% · 포착 %.3f/%.3f · 12개월 %d창 적중 %.1f%% 최악 %+.2f SD %.2f"
          % (s["ann_ex"], s["te"], s["ir"], s["nw_t"], dm.sum(), s["down_sum"], s["down_win"], s["basket_down_capture"],
             s["basket_up_capture"], s["roll12"]["n"], s["roll12"]["hit"], s["roll12"]["worst"], s["roll12"]["sd"]))
    print("V0 굴린 창 하위 10%% 평균(%d창) %+.2f · 전반부(%d창) %+.2f · 하락월 초과의 달력 HAC t %.2f · 임계 t(%d) %.3f"
          % (s["roll12"]["cvar_n"], s["roll12"]["cvar10"], s["roll12_h1"]["n"], s["roll12_h1"]["cvar10"],
             down_t(np.array(rt["monthly_ex"]), dm), dm.sum() - 1, t_crit(int(dm.sum()))))
    T, rec = build_chain(Wd)
    bad = 0
    for v in ("V1", "V2", "V3"):
        for m, tg in T[v].items():
            if abs(sum(tg["w"].values()) - 1) > 1e-6 or min(tg["w"].values()) < -1e-9:
                bad += 1
    over = sum(1 for m, tg in T["V3"].items() for k, x in tg["w"].items() if x > S2_TOP + 1e-6)
    print("dry: 편입 %d · 합·음수 위반 %d · S2 9%% 초과 %d · 섹터 조회 %s · %.0f초" % (len(formations(Wd)), bad, over, Wd.sec_stat, time.time() - t0))
    cov = pre_coverage(Wd, [m for m in Wd.all_m if PRE0 <= m <= PRE1 and (m == PRE0 or int(m[5:7]) % 3 == 0)] + [Wd.months[0]])
    for r in cov:
        print("  커버리지 %s 비금융 %d · 키 %d · 가격·시총·Eg %d → %.3f" % (r["m"], r["nonfin"], r["keyed"], r["ok"], r["cover"]))
    return 0 if (bad == 0 and over == 0 and gap <= 1e-6 and qgap <= 1e-4 and dm.sum() == 39) else 1


def _js(o):
    """numpy 값 → 파이썬(JSON)."""
    return o.item() if hasattr(o, "item") else str(o)


def main() -> int:
    t0 = time.time()
    commit = frozen_check()
    started = "%s · %s" % (commit, time.strftime("%Y-%m-%d %H:%M:%S"))
    io.open(MARK, "w", encoding="utf-8").write(started + "\n")          # 결과가 찍히기 전에 — 도중에 죽어도 재실행이 막힌다
    Wd = World()
    E = json.load(io.open(os.path.join(DATA, "_eg_best.json"), encoding="utf-8"))["results"]["EG_BASE"]
    T0 = v0_targets(Wd)
    V = {"V0": {"PR": Wd.run(T0, "PR"), "TR": Wd.run(T0, "TR")}}
    gap = max(abs(a - b) for a, b in zip(V["V0"]["PR"]["monthly"]["basket"], E["monthly"]["basket"]))
    if gap > 1e-6 or abs(V["V0"]["PR"]["basket_turn_oneway"] - E["basket_turn_oneway"]) > 1e-9:
        raise SystemExit("🚨 V0 가 공개된 EG30 을 재현하지 못했다(월 최대 차 %.2e)." % gap)
    hold = V["V0"]["TR"]["hold_months"]
    dset = set(down_months(Wd, hold))
    dmask = np.array([h in dset for h in hold])
    T, rec = build_chain(Wd)
    sec_main = dict(Wd.sec_stat)
    for v in ("V1", "V2", "V3"):
        V[v] = {"PR": Wd.run(T[v], "PR"), "TR": Wd.run(T[v], "TR")}
    SUM = {v: summary(V[v]["TR"], dmask) for v in V}
    SUM_PR = {v: summary(V[v]["PR"], dmask) for v in V}
    DIAG = chain_diag(Wd, T0, T, rec)
    print("V0~V3 (%.0f초)" % (time.time() - t0), flush=True)
    ST = {"S1": step_stats(V["V0"]["TR"], V["V1"]["TR"], dmask), "B1": step_stats(V["V1"]["TR"], V["V2"]["TR"], dmask),
          "S2": step_stats(V["V2"]["TR"], V["V3"]["TR"], dmask)}
    # 20bp
    V20 = {"V0": Wd.run(T0, "TR", cost=0.0020)}
    for v in ("V1", "V2", "V3"):
        V20[v] = Wd.run(T[v], "TR", cost=0.0020)
    ST20 = {"S1": step_stats(V20["V0"], V20["V1"], dmask), "B1": step_stats(V20["V1"], V20["V2"], dmask),
            "S2": step_stats(V20["V2"], V20["V3"], dmask)}
    SUM20 = {v: summary(V20[v], dmask) for v in V20}
    fm = formations(Wd)
    fm_of = lambda h: max(x for x in fm if x < h)
    ex0 = arr(V["V0"]["TR"])[1]
    _, ex1, bk1, ix1 = arr(V["V1"]["TR"])
    rfm = np.array([float(Wd.RF.get(h, 0.0)) * 100 for h in hold])
    # 대조 — 수익 맞춘 희석(모든 단계) · B1 은 편입 사전 베타 절감만큼 현금으로 지수를 덜어 낸 헤지도(V1 알파 그대로)
    CTRL = {}
    for step, prev, cur in (("S1", "V0", "V1"), ("B1", "V1", "V2"), ("S2", "V2", "V3")):
        c, ctl = dilution(arr(V[prev]["TR"])[1], arr(V[cur]["TR"])[1])
        CTRL[step + " 희석"] = {"c": c, "ex": ctl}
    cut = {r["m"]: max(0.0, r["beta_pre"] - r["beta_post"]) for r in rec["B1"]}
    cut_t = np.array([cut[fm_of(h)] for h in hold])
    CTRL["B1 헤지"] = {"c": None, "ex": ex1 - 0.1 * cut_t * (ix1 - rfm)}
    bfin = {r["m"]: r["b_fin"] for r in rec["S1"]}
    C1a = ex0 * (1 - np.array([bfin[fm_of(h)] for h in hold]))          # 싣기만 — 금융 채움 몫만큼 능동 몫 축소
    # 강건성 — S&P 500 전용 사슬 · NASDAQ 100 전용(B1 · S2)
    Tspx, _ = build_chain(Wd, universe="spx")
    Rs = {"V0": Wd.run(v0_targets(Wd, "spx"), "TR")}
    for v in ("V1", "V2", "V3"):
        Rs[v] = Wd.run(Tspx[v], "TR")
    RB = {"spx": {"S1": step_stats(Rs["V0"], Rs["V1"], dmask), "B1": step_stats(Rs["V1"], Rs["V2"], dmask),
                  "S2": step_stats(Rs["V2"], Rs["V3"], dmask),
                  "S2_sd": [roll(Rs["V2"])["sd"], roll(Rs["V3"])["sd"]]}}
    Rn0 = Wd.run(v0_targets(Wd, "ndx"), "TR")
    Rn1 = Wd.run({m: dict(zip(("w", "names"), v0_b1(Wd, m, "ndx")[:2])) for m in fm}, "TR")
    Rn2 = Wd.run({m: dict(zip(("w", "names"), v0_s2(Wd, m, "ndx"))) for m in fm}, "TR")
    RB["ndx"] = {"B1": step_stats(Rn0, Rn1, dmask), "S2": step_stats(Rn0, Rn2, dmask),
                 "S2_sd": [roll(Rn0)["sd"], roll(Rn2)["sd"]]}
    # 이웃 · 진단 팔(측정만 · 고를 수 없다)
    ARMS = {}
    ARMS["V0+B1"] = Wd.run({m: dict(zip(("w", "names"), v0_b1(Wd, m)[:2])) for m in fm}, "TR")
    ARMS["V0+S2"] = Wd.run({m: dict(zip(("w", "names"), v0_s2(Wd, m))) for m in fm}, "TR")
    ARMS["S1 0pp"] = Wd.run(build_chain(Wd, band=0.0)[0]["V1"], "TR")
    ARMS["S1 금융→재배분"] = Wd.run(build_chain(Wd, fin_mode="snq")[0]["V1"], "TR")
    ARMS["B1 OLS"] = Wd.run(build_chain(Wd, beta_kind="ols")[0]["V2"], "TR")
    ARMS["S2 cap5"] = Wd.run(build_chain(Wd, s2_bound="cap5")[0]["V3"], "TR")
    ARM_SUM = {a_: summary(r, dmask) for a_, r in ARMS.items()}
    # FP β = 1 을 현금으로(V1 위 · 측정만) — 지수 1 − 0.1β̂ · 바스켓 0.1 · 현금 0.1(β̂ − 1) · β̂ ≤ 1 이면 V1 그대로
    bpre = {r["m"]: r["beta_pre"] for r in rec["B1"]}
    bh = np.array([bpre[fm_of(h)] for h in hold])
    cash_ex = np.where(bh > 1, 0.1 * bk1 + 0.1 * (bh - 1) * rfm - 0.1 * bh * ix1, ex1)
    ARM_SUM["B1 cash"] = {"down_mean": float(cash_ex[dmask].mean()), "ann_ex": float(cash_ex.mean() * 12), "roll12": rolling12(cash_ex, ix1)}
    nb = {"S1 0pp": ARM_SUM["S1 0pp"]["down_mean"] - SUM["V0"]["down_mean"],
          "S1 금융→재배분": ARM_SUM["S1 금융→재배분"]["down_mean"] - SUM["V0"]["down_mean"],
          "B1 OLS": ARM_SUM["B1 OLS"]["down_mean"] - SUM["V1"]["down_mean"],
          "S2 cap5 sd": ARM_SUM["S2 cap5"]["roll12"]["sd"] - SUM["V2"]["roll12"]["sd"]}
    MECH = {v: mech_frame(V[v]["TR"]) for v in V}
    SHIFT = {"S1": beta_shift(V["V0"]["TR"], V["V1"]["TR"]), "B1": beta_shift(V["V1"]["TR"], V["V2"]["TR"]),
             "S2": beta_shift(V["V2"]["TR"], V["V3"]["TR"])}
    print("대조 · 강건 · 이웃 (%.0f초)" % (time.time() - t0), flush=True)
    # 창 이전(측정만 — 커버리지 미달이 등록 전에 확인됐다)
    PRE = pre_window(Wd)
    print("창 이전 — %s (%.0f초)" % (PRE["note"], time.time() - t0), flush=True)
    # 위약 — S1 업종 라벨 · B1 베타 라벨(β̂ 되맞춤) · 각 1000(씨앗 20260924 + i) — 특이성 점검
    S1cache = {m: s1_build(Wd, m) for m in fm}
    qV0, qV1 = quick(Wd, T0)["ex"], quick(Wd, T["V1"])["ex"]
    pS1, pB1 = placebos(Wd, S1cache, qV0, qV1, dmask, t0)
    P = {"S1_p95": float(np.percentile(pS1, 95)), "B1_p95": float(np.percentile(pB1, 95)),
         "S1_rank": float(np.mean(np.array(pS1) < ST["S1"]["down_mean"]) * 100),
         "B1_rank": float(np.mean(np.array(pB1) < ST["B1"]["down_mean"]) * 100),
         "S1_mean": float(np.mean(pS1)), "B1_mean": float(np.mean(pB1))}
    # ── 관문 ──
    nd = int(dmask.sum())
    TC = t_crit(nd)
    G = {}
    for step, prev, cur, ctrls, p95 in (("S1", "V0", "V1", ["S1 희석"], P["S1_p95"]), ("B1", "V1", "V2", ["B1 희석", "B1 헤지"], P["B1_p95"])):
        s_ = ST[step]
        exc = arr(V[cur]["TR"])[1]
        ctrl_ok = {c: bool(exc[dmask].mean() >= CTRL[c]["ex"][dmask].mean()) for c in ctrls}
        nbs = [nb["S1 0pp"], nb["S1 금융→재배분"]] if step == "S1" else [nb["B1 OLS"]]
        rob = {"halves": s_["half1"] > 0 and s_["half2"] > 0, "blocks": s_["blocks_pos"] >= 3, "spx": RB["spx"][step]["down_mean"] > 0,
               "ndx": (RB["ndx"]["B1"]["down_mean"] > 0) if step == "B1" else True, "neighbors": all(x > 0 for x in nbs)}
        G[step] = {"i": s_["down_mean"] >= 0, "ii": (s_["down_t"] or -9) >= TC, "iii": all(ctrl_ok.values()), "iii_detail": ctrl_ok,
                   "iv": s_["down_mean"] > p95, "v": all(rob.values()), "v_detail": rob,
                   "vi": ST20[step]["down_mean"] >= 0 and (ST20[step]["down_t"] or -9) >= TC, "vii": True}
        G[step]["pass"] = all(G[step][g] for g in ("i", "ii", "iii", "iv", "v", "vi", "vii"))
    s_ = ST["S2"]
    r2, r3 = SUM["V2"], SUM["V3"]
    r20_2, r20_3 = SUM20["V2"]["roll12"], SUM20["V3"]["roll12"]
    G["S2"] = {"i'": s_["down_mean"] >= -S2_NI,
               "ii'": (r3["roll12"]["sd"] < r2["roll12"]["sd"] and r3["roll12_h1"]["sd"] < r2["roll12_h1"]["sd"]
                       and r3["roll12"]["cvar10"] > r2["roll12"]["cvar10"] and r3["roll12_h1"]["cvar10"] >= r2["roll12_h1"]["cvar10"] - 0.10),
               "ii''": (r3["ir"] - r2["ir"]) >= -0.05,
               "v'": (nb["S2 cap5 sd"] < 0) == (r3["roll12"]["sd"] < r2["roll12"]["sd"]),
               "vi'": r20_3["sd"] < r20_2["sd"] and r20_3["cvar10"] > r20_2["cvar10"],
               "vii": True}
    G["S2"]["pass"] = all(G["S2"][g] for g in ("i'", "ii'", "ii''", "v'", "vi'", "vii"))
    acc = ["V0"]
    if G["S1"]["pass"]:
        acc.append("V1")
        if G["B1"]["pass"]:
            acc.append("V2")
            if G["S2"]["pass"]:
                acc.append("V3")
    b0 = SUM["V0"]
    FL, MU = {}, {}
    for v in ("V1", "V2", "V3"):
        FL[v] = {"ir": SUM[v]["ir"] >= b0["ir"] - X_IR, "ex": SUM[v]["ann_ex"] >= 0.5 * b0["ann_ex"], "te": SUM[v]["te"] <= 1.20,
                 "turn": SUM[v]["turn"] <= 2 * b0["turn"]}
        ev = arr(V[v]["TR"])[1]
        c0, dil0 = dilution(ex0, ev)
        tm = down_t(ev - dil0, dmask)
        MU[v] = {"c": c0, "M1_t": tm, "M1": (tm or -9) >= TC,
                 "M2_hit": SUM[v]["roll12"]["hit"] >= b0["roll12"]["hit"] - M2_TOL,
                 "M2_cvar": SUM[v]["roll12"]["cvar10"] >= b0["roll12"]["cvar10"]}
        MU[v]["M2"] = MU[v]["M2_hit"] and MU[v]["M2_cvar"]
    # 고르기 — 받아들인 가장 깊은 변형부터 얕은 쪽으로 · 바닥과 필수 둘을 **함께** 넘는 첫 변형
    chosen = next((v for v in reversed(acc[1:]) if all(FL[v].values()) and MU[v]["M1"] and MU[v]["M2"]), None)
    winner = chosen or "V0"
    verdict = "측정만" if chosen else "기각"
    FWD = None
    if chosen:
        dlt = arr(V[chosen]["TR"])[1] - ex0
        FWD = {"sigma_d": float(np.std(dlt, ddof=1) * math.sqrt(12)), "down_mean_d": float(dlt[dmask].mean()),
               "half_down_mean_d": float(dlt[dmask].mean() / 2)}
    src_flag = sum(1 for r in DIAG if (r["src_V1"]["near"] + r["src_V1"]["today"]) > 0.10 * max(1e-12, sum(r["src_V1"].values())))
    strip = lambda r: {k: v for k, v in r.items() if k not in ("cand",)}
    out = {"prereg": PREREG, "prereg_commit": commit, "data_snapshot": SNAP, "data_base": SNAP_BASE, "data_last_date": Wd.dates[-1],
           "worktree_head": subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
           "started": started, "rerun": os.environ.get("EG30PLUS_RERUN"), "solver": {x: SOLVER_LOG.count(x) for x in sorted(set(SOLVER_LOG))},
           "basis": "gates TR(0.9 SPY TR + 0.1 바스켓 대 SPY TR) · results_PR = 공개 리포트 기준(S&P 500 PR)",
           "down_months": sorted(dset), "n_down": int(dmask.sum()),
           "summary_TR": SUM, "summary_PR": SUM_PR, "summary_20bp": SUM20, "steps": ST, "steps_20bp": ST20, "robust": RB,
           "arms": ARM_SUM, "neighbor_d": nb, "placebo": P, "t_crit": TC, "alpha": ALPHA,
           "controls": {c: {"c": x["c"], "down_mean": float(x["ex"][dmask].mean()), "all_mean": float(x["ex"].mean())} for c, x in CTRL.items()},
           "C1a": {"down_mean": float(C1a[dmask].mean()), "all_mean": float(C1a.mean())},
           "gates": G, "accepted": acc, "floors": FL, "musts": MU, "chosen": chosen, "winner": winner, "verdict": verdict, "forward": FWD,
           "mech_frame": MECH, "beta_shift": SHIFT, "src_flag_formations": src_flag, "src_flag": src_flag >= 5,
           "records": rec, "diag": DIAG, "pre_window": PRE, "sector_lookups": sec_main,
           "results_PR": {v: strip(V[v]["PR"]) for v in V}, "results_TR": {v: strip(V[v]["TR"]) for v in V}}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, separators=(",", ":"), default=_js) + "\n")
    for v in ("V0", "V1", "V2", "V3"):
        x = SUM[v]
        print("%s 연 %+.2f%% · TE %.2f%% · IR %.2f · 하락월 평균 %+.3f(합 %+.2f · 승 %.0f%%) · 포착 %.2f/%.2f · β %.2f · 12개월 적중 %.1f%% 하위10%% %+.2f SD %.2f · 이긴 해 %d/%d · 급락 %d/6 · 급등 %d/6"
              % (v, x["ann_ex"], x["te"], x["ir"], x["down_mean"], x["down_sum"], x["down_win"], x["basket_down_capture"],
                 x["basket_up_capture"], x["basket_beta"], x["roll12"]["hit"], x["roll12"]["cvar10"], x["roll12"]["sd"],
                 x["years_won"], x["n_years"], x["crash_won"], x["surge_won"]))
    print("관문", json.dumps(G, ensure_ascii=False, default=bool))
    print("⇒ 받아들인 사슬 %s · 선택 %s · 판정 %s (%.0f초)" % (acc, winner, verdict, time.time() - t0))
    return 0


if __name__ == "__main__":
    if "--dry" in sys.argv:
        sys.exit(dry())
    sys.exit(main())
