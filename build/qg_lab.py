# -*- coding: utf-8 -*-
"""build/qg_lab.py — 우량성장 계열 복합점수 바스켓 엔진(시점정확 · 일간 경로 · 펀드 90/10 틀).

사전등록이 후보(신호·가중·평활·N·비중)를 정하면 `CANDIDATES` 에 그대로 적고 돌린다. 엔진 자체는 판정하지 않는다.

틀 — 우량성장선별 30 리포트와 같다: 펀드 = S&P 500 PR 90% + 바스켓 10% · 바스켓 몫은 매월 말 10% 로 되돌림 ·
  편도 10bp · 유니버스 = 그 월말 **S&P 500** 명단(pit_panel · 날짜 인식 키) 중 금융 제외(기본값 — 후보가 index='union'·ex_fin=False
  로 바꿀 수 있다) · 시총이 선 회사만 · 가격은 배당조정 종가(바스켓) 대 PR(지수).

신호(월말 i, 그때 알 수 있던 자료만 — 재무는 분기말 90일 뒤부터 · TB.asof_all):
  roe   최근 분기 순이익 ÷ 그 앞 분기말 자기자본(> 0)
  eg    data/_eg_q5_scores.json 의 그달 예측치
  gp    최근 4분기 매출총이익 합 ÷ 최근 총자산(Novy-Marx)
  mom   252일 − 21일 수익(랩 x-mom12 과 같은 ret)
  sue   tech_backtest.sue()
  ag    총자산 전년 대비 증가율(낮을수록 좋음 — 부호를 뒤집어 쓴다)
백분위는 그달 유니버스 안(신호가 선 종목끼리)에서 잰다.

  python build/qg_lab.py <candidates.json> <out.json>
"""
from __future__ import annotations
import io, json, math, os, sys, time

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pit_panel as PP                # noqa: E402
import stoploss as SL                 # noqa: E402  ret · last_valid
import tech_backtest as TB            # noqa: E402  asof_all · sue

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
F0M, F1M, R3 = "2016-08", "2026-07", "2023-09"
COST, SLEEVE = 0.0010, 0.10
FIN = {"Financials"}
EPIS = [("급락", "코로나19 팬데믹", "2020-02-19", "2020-03-16"), ("급등", "무제한 QE·재정부양 랠리", "2020-03-16", "2020-06-03"),
        ("급락", "2020년 9월 기술주 조정", "2020-09-02", "2020-09-23"), ("급등", "백신 기대·대선 불확실성 해소", "2020-09-23", "2020-12-01"),
        ("급락", "금리 급등 쇼크", "2021-02-12", "2021-03-08"), ("급등", "금리 안정 반등", "2021-03-08", "2021-04-09"),
        ("급락", "인플레이션·연준 급속 긴축", "2021-12-27", "2022-11-03"), ("급등", "생성형 AI 랠리", "2022-11-03", "2023-12-13"),
        ("급락", "엔 캐리 청산 쇼크", "2024-07-10", "2024-08-07"), ("급등", "연준 인하 개시 랠리", "2024-08-07", "2024-11-06"),
        ("급락", "관세 쇼크", "2025-02-19", "2025-04-08"), ("급등", "관세 유예·협상 진전 반등", "2025-04-08", "2025-06-24")]


def pct_rank(d):
    """{키: 값} → {키: 0~1 백분위(평균 순위)}."""
    ks = [k for k, v in d.items() if v is not None and v == v]
    if not ks:
        return {}
    vs = np.array([d[k] for k in ks], float)
    order = vs.argsort(kind="mergesort")
    ranks = np.empty(len(vs))
    ranks[order] = np.arange(len(vs))
    # 같은 값은 평균 순위
    uniq, inv = np.unique(vs, return_inverse=True)
    for u in range(len(uniq)):
        m = inv == u
        if m.sum() > 1:
            ranks[m] = ranks[m].mean()
    denom = max(1, len(vs) - 1)
    return {k: float(r / denom) for k, r in zip(ks, ranks)}


class World:
    def __init__(self):
        self.W = W = PP.load_world()
        self.dates, self.D, self.PX, self.me = W["dates"], W["D"], W["PX"], W["me"]
        self.di = {d: i for i, d in enumerate(self.dates)}
        self.RF = json.load(io.open(os.path.join(DATA, "rf_monthly.json"), encoding="utf-8"))["monthly"]
        Bj = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
        bidx = {d: i for i, d in enumerate(Bj["dates"])}
        ix = [np.nan if (bidx.get(d) is None or Bj["series"]["spx"]["px"][bidx[d]] is None)
              else float(Bj["series"]["spx"]["px"][bidx[d]]) for d in self.dates]
        self.IX = np.array(ix)
        for j in range(1, self.D):
            if self.IX[j] != self.IX[j]:
                self.IX[j] = self.IX[j - 1]
        self.EG = json.load(io.open(os.path.join(DATA, "_eg_q5_scores.json"), encoding="utf-8"))["months"]
        self._EGV = {"frozen": self.EG}
        S = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
        self.NAME = {s["t"]: (s.get("name") or s["t"]) for s in S["stocks"]}
        self.all_m = sorted(self.me)
        self.months = [m for m in self.all_m if F0M <= m <= F1M]
        self._raw = {}

    # ── 유니버스 ──────────────────────────────────────────────────────────
    def universe(self, m, index="spx", ex_fin=True):
        """그 월말 명단 → [(명단 티커, 가격 키)].

        index 'spx'·'ndx' = 그 지수 명단 · 'union' = S&P 500 ∪ NASDAQ 100(`pit_panel.union_members` — EG30 · FUNDMIX 와 같은 규칙).
        이중클래스 회사당 하나(KEEP_DUAL) · 재배정 티커의 마지막 멤버월 제외 · 날짜 인식 키.
        🚨 시가총액이 서는 회사만(가격 > 0 · 주식수) — **선정 전에** 거른다. 뽑은 뒤 시총이 없어 빠지면 바스켓이 30 이 안 된다
          (FUNDMIX rule_E 도 시총이 선 회사 안에서 줄을 세운다).
        ex_fin — 오늘 GICS 로 금융을 뺀다(시점정확 아님 · 사전등록마다 공개).
        """
        W, i = self.W, self.me[m]
        if index == "union":
            pairs = PP.union_members(W, m, i)[0]
        else:
            mem = W["lists"][index].get(m) or []
            by = {}
            for t in mem:
                c = W["cikmap"].get(t) or W["cikmap"].get(t.replace("-", "."))
                by.setdefault(c or ("_" + t), []).append(t)
            keep = []
            for c, ts in by.items():
                if len(ts) == 1 or c.startswith("_"):
                    keep.extend(ts)
                    continue
                k_ = [t for t in ts if t in PP.KEEP_DUAL]
                keep.append(k_[0] if k_ else sorted(ts)[0])
            pairs = []
            for t in sorted(keep):
                if t in W["reassigned"] and m >= W["reassigned"][t].get("last", "9999"):
                    continue
                k = PP._key(W, t, i)
                if k is not None:
                    pairs.append((t, k))
        out = []
        for t, k in pairs:
            if ex_fin and PP._sector(W, t, k) in FIN:
                continue
            if self.mcap(t, k, i) is None:
                continue
            out.append((t, k))
        return out

    def eg_scores(self, egv="frozen"):
        """Eg 판 — 'frozen' = _eg_q5_scores.json(PREREG-2026-09-23-EG 얼린 판 · 금융은 오늘 GICS)
        · 'pitgics' = _eg_q5_scores_pitgics.json(eg_q5.py --pit-gics · 2023-03 결제 처리 재분류 전은 비금융)."""
        if egv not in self._EGV:
            fn = {"pitgics": "_eg_q5_scores_pitgics.json"}[egv]
            self._EGV[egv] = json.load(io.open(os.path.join(DATA, fn), encoding="utf-8"))["months"]
        return self._EGV[egv]

    def fund(self, t, k):
        return self.W["FUND"].get(k) or self.W["FUND"].get(t) or {}

    def mcap(self, t, k, i):
        sh = PP._shares(self.W, t, k, self.dates[i])
        p = self.PX[k][i]
        return (p * sh) if (sh and p == p and p > 0) else None

    # ── 원신호 ────────────────────────────────────────────────────────────
    def raw(self, sig, m, index="spx", ex_fin=True, egv="frozen"):
        key = (sig, m, index, ex_fin, egv if sig == "eg" else None)
        if key in self._raw:
            return self._raw[key]
        i, d = self.me[m], self.dates[self.me[m]]
        out = {}
        for t, k in self.universe(m, index, ex_fin):
            f = self.fund(t, k)
            v = None
            if sig == "roe":
                ni = TB.asof_all(f.get("ni") or [], d) if f.get("ni") else None
                eq = TB.asof_all(f.get("eq") or [], d) if f.get("eq") else None
                if ni and eq and len(eq) >= 2 and ni[0][1] is not None and eq[1][1] and eq[1][1] > 0:
                    v = ni[0][1] / eq[1][1]
            elif sig == "eg":
                sc = self.eg_scores(egv).get(m) or {}
                v = sc.get(t, sc.get(k))
            elif sig == "gp":
                gp = TB.asof_all(f.get("gp") or [], d) if f.get("gp") else None
                at = TB.asof_all(f.get("asset") or [], d) if f.get("asset") else None
                if gp and at and len(gp) >= 4 and at[0][1] and at[0][1] > 0 and all(x[1] is not None for x in gp[:4]):
                    v = sum(x[1] for x in gp[:4]) / at[0][1]
            elif sig == "mom":
                a = SL.ret(self.PX[k], i, 252)
                if a is not None:
                    b = SL.ret(self.PX[k], i, 21)
                    v = a - (b or 0.0)
            elif sig == "sue":
                v = TB.sue(f.get("eps") or [], d)
            elif sig == "droe":
                v = self._droe(f, d)
            elif sig == "ag":
                at = TB.asof_all(f.get("asset") or [], d) if f.get("asset") else None
                if at and len(at) >= 5 and at[0][1] and at[4][1] and at[4][1] > 0:
                    v = -(at[0][1] / at[4][1] - 1.0)       # 낮은 성장이 좋다 → 부호 반전
            if v is not None and v == v and abs(v) < 1e6:
                out[(t, k)] = float(v)
        self._raw[key] = out
        return out

    @staticmethod
    def _roe_at(ni_obs, eq_obs, j):
        """ni 관측 j(최신순)의 분기 ROE = 그 분기 순이익 ÷ 그 분기말 **직전** 자기자본 관측(> 0). 없으면 None."""
        dq, nv = ni_obs[j]
        if nv is None:
            return None, dq
        prev = [e for e in eq_obs if e[0] < dq]           # 그 분기말보다 앞선 자기자본 관측(최신순이라 첫 것이 직전)
        if not prev or prev[0][1] is None or prev[0][1] <= 0:
            return None, dq
        return nv / prev[0][1], dq

    def _droe(self, f, d):
        """dROE = 최근 분기 ROE − 1년 전 같은 분기 ROE(날짜로 찾는다 — 320~410일 · tech_backtest.yoy_eps 와 같은 규약)."""
        ni = TB.asof_all(f.get("ni") or [], d) if f.get("ni") else None
        eq = TB.asof_all(f.get("eq") or [], d) if f.get("eq") else None
        if not ni or not eq:
            return None
        r0, d0 = self._roe_at(ni, eq, 0)
        if r0 is None:
            return None
        best = None
        for j in range(1, len(ni)):
            gap = TB._days_between(d0, ni[j][0])
            if gap > 410:
                break
            if 320 <= gap <= 410 and (best is None or gap < best[0]):
                best = (gap, j)
        if best is None:
            return None
        r1, _ = self._roe_at(ni, eq, best[1])
        return None if r1 is None else r0 - r1

    # ── 복합점수 · 선정 ────────────────────────────────────────────────────
    def composite(self, cand, m):
        """후보의 신호 백분위 가중평균(모든 신호가 선 종목만) → {(t,k): 점수}."""
        pr = {s: pct_rank(self.raw(s, m, cand.get("index", "spx"), cand.get("ex_fin", True), cand.get("eg", "frozen"))) for s in cand["signals"]}
        ws = cand["weights"]
        keys = set.intersection(*[set(p) for p in pr.values()]) if pr else set()
        return {x: sum(ws[s] * pr[s][x] for s in cand["signals"]) / sum(ws.values()) for x in keys}

    def smoothed(self, cand, m):
        """최근 L 형성월 중 원점수가 있던 달만 평균(우량성장 30 과 같은 평활) — L = cand['smooth']."""
        L = cand.get("smooth", 1)
        hist, mm = [], m
        for _ in range(L):
            if mm not in self.me:
                break
            hist.append(self.composite(cand, mm))
            mm = PP.mshift(mm, -1)
        cur = hist[0]
        out = {}
        for x in cur:
            vals = [h[x] for h in hist if x in h]
            out[x] = float(np.mean(vals))
        return out

    def score(self, cand, m):
        """최종 선정 점수 → (정렬할 목록 [(키, 점수)] 상위부터).

        mode 'base'  — 평활 QG 그대로.
        mode 'blend' — pct(평활 QG) × (1 − w) + pct(add 신호, 형성일 값 · 평활 없음) × w. 둘 다 선 종목만 —
                       🚨 두 백분위 모두 **둘 다 선 종목 안에서** 잰다. add 를 유니버스 전체(Eg 가 없는 금융 포함)에서 재면
                       그달 금융주 모멘텀 분포에 따라 add 의 실효 가중이 ⅓ 에서 흔들린다(적대 검토 2차가 잡았다).
                       평활 QG 는 두 백분위의 평균이라 퍼짐이 좁다 — 다시 백분위로 펴서 섞어야 w 가 제 뜻이다.
        mode 'screen'— 평활 QG 상위 pool 을 뽑고 그중 add 신호 하위 drop 개를 뺀다(add 가 없는 종목을 먼저 뺀다).
        """
        qg = self.smoothed(cand, m)
        mode = cand.get("mode", "base")
        if mode == "base":
            return sorted(qg.items(), key=lambda kv: (-kv[1], kv[0][0]))
        add = self.raw(cand["add"], m, cand.get("index", "spx"), cand.get("ex_fin", True), cand.get("eg", "frozen"))
        if mode == "blend":
            w = cand["add_w"]
            both = [x for x in qg if x in add]
            pq = pct_rank({x: qg[x] for x in both})
            pa = pct_rank({x: add[x] for x in both})
            sc = {x: (1 - w) * pq[x] + w * pa[x] for x in both}
            return sorted(sc.items(), key=lambda kv: (-kv[1], kv[0][0]))
        if mode == "screen":
            pool = sorted(qg.items(), key=lambda kv: (-kv[1], kv[0][0]))[:cand["pool"]]
            miss = [x for x, _ in pool if x not in add]
            have = sorted([x for x, _ in pool if x in add], key=lambda x: (add[x], x[0]))   # add 오름차순
            drop = set((miss + have)[:cand["drop"]])
            return [(x, s) for x, s in pool if x not in drop]
        raise ValueError(mode)

    def weights(self, cand, m):
        i = self.me[m]
        top = self.score(cand, m)[:cand["n"]]
        if cand.get("wt", "cap") == "eq":
            w = {x: 1.0 / len(top) for x, _ in top}
        else:
            mc = {x: self.mcap(x[0], x[1], i) for x, _ in top}
            mc = {x: v for x, v in mc.items() if v}
            tot = sum(mc.values())
            w = {x: v / tot for x, v in mc.items()}
            cap = cand.get("cap", 0.20)
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
        return {x[1]: v for x, v in w.items()}, {x[1]: x[0] for x in w}

    # ── 바스켓 일간 경로 ───────────────────────────────────────────────────
    def sleeve(self, cand):
        PX, me = self.PX, self.me
        every = cand.get("reb", 3)
        path, units, cash, last = {}, {}, 1.0, {}
        turns, books = [], []
        for j, m in enumerate(self.months):
            i, i1 = me[m], me[PP.mshift(m, 1)]
            is_reb = (j == 0) or (int(m[5:7]) % every == 0 if every in (3, 6, 12) else True)
            val = {k: units[k] * PX[k][last[k]] for k in units}
            V = cash + sum(val.values())
            if is_reb:
                tgt, names = self.weights(cand, m)
                tgt = {k: x for k, x in tgt.items() if PX[k][i] == PX[k][i] and PX[k][i] > 0}
                tv = {k: V * x for k, x in tgt.items()}
                traded = sum(abs(tv.get(k, 0.0) - val.get(k, 0.0)) for k in set(tv) | set(val))
                V2 = V - COST * traded
                units = {k: (V2 * x) / PX[k][i] for k, x in tgt.items()}
                cash = V2 - sum(V2 * x for x in tgt.values())
                last = {k: i for k in units}
                turns.append(traded / V)
                prev_names = books[-1]["names"] if books else {}
                books.append({"sig": m, "names": names,
                              "w": {names[k]: x for k, x in tgt.items()},
                              "prev": {prev_names.get(k, k): val.get(k, 0.0) / V for k in val}})
                path[i] = V2
            else:
                turns.append(0.0)
                path[i] = V
            rf_d = (1 + float(self.RF.get(PP.mshift(m, 1), 0.0))) ** (1.0 / max(1, i1 - i)) - 1
            for d in range(i + 1, i1 + 1):
                cash *= (1 + rf_d)
                for k in units:
                    p = PX[k][d]
                    if p == p and p > 0:
                        last[k] = d
                path[d] = cash + sum(units[k] * PX[k][last[k]] for k in units)
        return path, float(np.mean(turns) / 2 * 12), books

    # ── 펀드 · 통계 ───────────────────────────────────────────────────────
    def evaluate(self, cand, path_turn_books):
        path, bturn, books = path_turn_books
        me = self.me
        months = self.months
        i_start, i_end = me[months[0]], me[PP.mshift(months[-1], 1)]
        days = list(range(i_start, i_end + 1))
        mends = [me[m] for m in months] + [i_end]
        R = {d: path[d] / path[d - 1] - 1.0 for d in days[1:]}
        IX = self.IX
        fp = {days[0]: 1.0}
        ixv, slv, resets = 0.9, 0.1, []
        for d in days[1:]:
            ixv *= IX[d] / IX[d - 1]
            slv *= (1 + R[d])
            v = ixv + slv
            if d in mends[1:]:
                dev = abs(slv / v - SLEEVE)
                v -= COST * 2 * dev * v
                resets.append(dev)
                ixv, slv = v * 0.9, v * 0.1
            fp[d] = v
        reset_turn = float(np.mean(resets) * 12)

        def monthly(p):
            return np.array([p[mends[j + 1]] / p[mends[j]] - 1.0 for j in range(len(months))])
        ixp = {d: IX[d] / IX[days[0]] for d in days}
        fr, sr, im = monthly(fp), monthly(path), monthly(ixp)
        hold = [PP.mshift(m, 1) for m in months]
        rfm = np.array([float(self.RF.get(h, 0.0)) for h in hold])

        def st(r, rf):
            nav = np.cumprod(1 + r)
            ex = r - rf
            return {"cagr": float((nav[-1] ** (12 / len(r)) - 1) * 100), "vol": float(r.std(ddof=1) * math.sqrt(12) * 100),
                    "sharpe": float(ex.mean() / ex.std(ddof=1) * math.sqrt(12))}

        def mdd(p, a, z):
            xs = np.array([p[d] for d in days if a <= d <= z])
            return float(np.min(xs / np.maximum.accumulate(xs) - 1) * 100)

        def block(sel):
            e = (fr - im)[sel]
            n = int(sel.sum())
            te = e.std(ddof=1) * math.sqrt(12)
            be = (sr - im)[sel]
            return {"n": n, "ann_ex": float(e.mean() * 1200),
                    "cum_ex": float((np.prod(1 + fr[sel]) - np.prod(1 + im[sel])) * 100),
                    "te": float(te * 100), "ir": float(e.mean() * 12 / te) if te > 0 else None,
                    "t": float(e.mean() / (e.std(ddof=1) / math.sqrt(n))), "win": float(np.mean(e > 0) * 100),
                    "fund": st(fr[sel], rfm[sel]), "index": st(im[sel], rfm[sel]), "basket": st(sr[sel], rfm[sel]),
                    "basket_ann_ex": float(be.mean() * 1200),
                    "basket_ir": float(be.mean() * 12 / (be.std(ddof=1) * math.sqrt(12)))}
        sel_all = np.ones(len(months), bool)
        sel_3y = np.array([h >= R3 for h in hold])
        sel_h1 = np.array([h < "2021-09" for h in hold])
        yrs = {}
        for h, a, b, c in zip(hold, fr, im, sr):
            y = yrs.setdefault(h[:4], [1, 1, 1])
            y[0] *= 1 + a; y[1] *= 1 + b; y[2] *= 1 + c
        epi = []
        for kind, nm, a, z in EPIS:
            ia, iz = self.di.get(a), self.di.get(z)
            if ia is None or iz is None or ia < days[0] or iz > days[-1]:
                continue
            ri, rfu, rsl = IX[iz] / IX[ia] - 1, fp[iz] / fp[ia] - 1, path[iz] / path[ia] - 1
            epi.append({"kind": kind, "name": nm, "a": a, "z": z, "index": ri * 100, "fund": rfu * 100,
                        "ex": (rfu - ri) * 100, "basket": rsl * 100, "basket_ex": (rsl - ri) * 100})
        i3 = me[PP.mshift(R3, -1)]
        last_b = books[-1]
        top = sorted(last_b["w"].items(), key=lambda kv: -kv[1])
        # 리포트 차트용 계열(판정에 쓰지 않는다) — 일간 NAV(첫날 1) · 월 수익 · 최신 바스켓 섹터
        sec_of = {t: PP._sector(self.W, t, k) for k, t in last_b["names"].items()}
        sectors = {}
        for t, x in last_b["w"].items():
            sectors[sec_of.get(t, "?")] = sectors.get(sec_of.get(t, "?"), 0.0) + x * 100
        p0 = path[days[0]]
        series = {"d": [self.dates[d] for d in days], "fund": [round(fp[d], 6) for d in days],
                  "index": [round(ixp[d], 6) for d in days], "basket": [round(path[d] / p0, 6) for d in days]}
        tr = []
        for t in set(last_b["prev"]) | set(last_b["w"]):
            dl = (last_b["w"].get(t, 0.0) - last_b["prev"].get(t, 0.0)) * SLEEVE * 100
            if abs(dl) > 1e-6:
                kind = ("신규 매수" if last_b["prev"].get(t, 0) == 0 else
                        "전량 매도" if t not in last_b["w"] else ("늘림" if dl > 0 else "줄임"))
                tr.append({"t": t, "name": self.NAME.get(t, t), "kind": kind, "pct": dl, "eok": dl * 100})
        return {"cand": cand, "all": block(sel_all), "3y": block(sel_3y), "h1": block(sel_h1), "h2": block(~sel_h1),
                "mdd": {"fund_all": mdd(fp, days[0], days[-1]), "index_all": mdd(ixp, days[0], days[-1]),
                        "fund_3y": mdd(fp, i3, days[-1]), "index_3y": mdd(ixp, i3, days[-1]),
                        "basket_all": mdd(path, days[0], days[-1])},
                "yearly": {y: {"index": (v[1] - 1) * 100, "fund": (v[0] - 1) * 100, "ex": (v[0] - v[1]) * 100,
                               "basket": (v[2] - 1) * 100} for y, v in sorted(yrs.items())},
                "episodes": epi, "basket_turn_oneway": bturn, "reset_turn": reset_turn,
                "nav_turn_oneway": bturn * SLEEVE + reset_turn,
                "holdings": {"sig": last_b["sig"], "n": len(top), "eff_n": float(1 / sum(w * w for _, w in top)),
                             "top": [{"t": t, "name": self.NAME.get(t, t), "w": w * 100, "sector": sec_of.get(t, "?")} for t, w in top[:15]],
                             "top3": float(sum(w for _, w in top[:3]) * 100),
                             "sectors": dict(sorted(sectors.items(), key=lambda kv: -kv[1]))},
                "trades": sorted(tr, key=lambda x: (x["kind"], -abs(x["pct"]))),
                "name_turnover_median": float(np.median([len(set(b["w"]) - set(books[j - 1]["w"]))
                                                         for j, b in enumerate(books) if j])),
                "monthly_ex": [round(float(x) * 100, 5) for x in (fr - im)],
                "monthly": {"fund": [round(float(x) * 100, 5) for x in fr], "index": [round(float(x) * 100, 5) for x in im],
                            "basket": [round(float(x) * 100, 5) for x in sr]},
                "series": series,
                "hold_months": hold}


def main() -> int:
    t0 = time.time()
    cands = json.load(io.open(sys.argv[1], encoding="utf-8"))
    W = World()
    out = {}
    for name, cand in cands.items():
        res = W.evaluate(cand, W.sleeve(cand))
        out[name] = res
        a = res["all"]
        print("%-10s IR %.2f · t %.2f · 연초과 %+.2f%% · TE %.2f%% · 3y IR %.2f · h1 %.2f · h2 %.2f · 회전 %.0f%% (%.0fs)" % (
            name, a["ir"], a["t"], a["ann_ex"], a["te"], res["3y"]["ir"], res["h1"]["ir"], res["h2"]["ir"],
            res["basket_turn_oneway"] * 100, time.time() - t0))
    io.open(sys.argv[2], "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
