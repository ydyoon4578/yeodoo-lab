# -*- coding: utf-8 -*-
"""build/guru_clone.py — 13F 컨빅션 복제를 한 번만 돌린다 → data/guru_clone.json

🚨 2026-08-05 에 build/ml_backtest.py 에서 **떼어 온 것**이다. 그 파일은 삭제했다
   (사용자 결정 — 실행 55분에 얻는 것이 없었다. 사유는 build/DATA-FACTS.md 17번).
   이 규칙은 머신러닝이 아니라 13F 공시 복제라 같이 지울 이유가 없었다.
   산식·규약은 옮기면서 한 글자도 바꾸지 않았다.

무엇을 재는가. 13F 를 낸 운용사 여럿이 **동시에** 들고 있는 종목을 상위 TOPN 만큼 사서,
그 '컨빅션 겹침'이 초과수익을 주는지 본다. 공시는 분기말 45일 뒤에 나오므로 그 지연을
그대로 태운다(안 태우면 순수 선견이다).

  python build/guru_clone.py
"""
from __future__ import annotations
import io, json, math, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tech_backtest import (ann_stats, tstat, maxdd, curve_pack, load_index_tr,  # noqa: E402
                           risk_bootstrap)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "guru_clone.json")
TOPN = 10
_GRID = {}           # gthin 이 쓰는 절대 위치표 — main 에서 채운다

def dates_for(nav, ds):
    """nav 와 **같은 길이**의 날짜 축. 길이가 어긋나면 날짜 정합 회귀가 통째로 안 돈다.

    nav 는 기준점 100.0 으로 시작해 구간마다 append 하므로 대개 len(ds)+1 이다.
    그 한 칸은 첫 구간의 시작점이므로 앞을 한 번 더 쓴다.
    """
    ds = list(ds)
    if not ds:
        return []
    if len(ds) == len(nav):
        return ds
    if len(ds) == len(nav) - 1:
        return [ds[0]] + ds
    return ds[:len(nav)] if len(ds) > len(nav) else ds + [ds[-1]] * (len(nav) - len(ds))


def gthin(ds, nav, bnav, every=5):
    """전략마다 다른 `step` 으로 얇게 만들면 **날짜 격자가 서로 안 맞는다.**

    🚨 2026-08-05 실측: 그래서 이 랩의 incr5 가 전부 None 이었다. incr_multi 는 6계열의
      **공통 날짜**에서만 회귀하는데, 전략마다 시작일이 달라 step 이 다르고(len//220)
      그 결과 교집합이 사실상 비었다. 종목 랩은 전 규칙이 같은 격자라 이 문제가 없었다.
    → 절대 위치로 자른다. 어느 전략이든 '전체 격자의 every 번째 날'만 남기므로 서로의
      부분집합이 되고, 교집합이 짧은 쪽 길이만큼 남는다.
    """
    ds = dates_for(nav, ds)
    keep = [i for i, d in enumerate(ds) if _GRID.get(d, i) % every == 0]
    if len(keep) < 60:                      # 너무 짧아지면 그대로 둔다(회귀가 아예 안 도는 것보다 낫다)
        keep = list(range(len(ds)))
    return ([ds[i] for i in keep],
            [round(nav[i], 2) for i in keep],
            [round(bnav[i], 2) for i in keep])

# ── 거래비용 ────────────────────────────────────────────────────────────
# asset_backtest 의 5bp 를 그대로 옮기면 안 된다. 그쪽은 대형 ETF 하나를 켜고 끄는 것이고
# 이쪽은 개별주 10종목 포트를 매달 갈아엎는다. 가정을 나눠 둔다.
#   COST_RT_STOCK 20bp — S&P500·NASDAQ100 대형주라도 호가 스프레드가 ETF보다 넓고, 10종목에
#     자금을 나눠 담아 종목당 체결 규모가 커지므로 충격이 붙는다. 왕복 20bp(편도 10bp)는
#     대형주 체결에서 흔히 인용되는 범위의 보수적인 쪽으로 잡은 값이다.
#   COST_RT_ETF 5bp — 지수 타이밍판은 SPY 하나를 켜고 끄므로 asset_backtest 와 같은 가정.
# ⚠ 환산식이 함수마다 다르다. 회전을 세는 방법이 다르기 때문이다 —
#     종목선택  turn = Σ(신규 편입 종목수), turnover = turn/TOPN/년
#               → k종목 교체는 포트의 k/TOPN 을 왕복한 것이므로 연 비용 = turnover × RT
#     지수타이밍 turn = Σ|Δ노출|, turnover = turn/년
#               → 0→1→0 한 번이 |Δw| 2 이므로 연 비용 = turnover × RT/2
#   같은 상수를 쓰되 나누는 수가 다르다. 한쪽 식을 다른 쪽에 옮기면 두 배로 틀린다.
# ⚠ 판정(verdict)은 기존대로 무비용이다. 사전등록물의 판정을 비용 가정 하나로 뒤집지 않는다 —
#   비용 후는 나란히 싣는 참고 열이다(asset_backtest 와 같은 규약).
COST_RT_STOCK, COST_RT_ETF = 0.0020, 0.0005

L2 = 1.0            # 고정. 탐색하지 않는다.
REFIT = 21          # 재학습 주기(거래일) ≈ 월 1회
MIN_TRAIN = 504     # 최소 학습 표본(≈2년) — 이보다 짧으면 예측하지 않는다
HOLD = 21           # 종목선택 보유기간(거래일)


def cost_cols(nav_g, nav_c, dd, RF, rt_bp):
    """무비용/비용후 NAV 두 벌 → 화면에 실을 비용 열. 대조군은 매수후보유(회전 0)라
    비용을 물지 않으므로 따로 계산하지 않고 그 사실을 필드로 적는다."""
    mg, mc = ann_stats(nav_g, dd, RF), ann_stats(nav_c, dd, RF)
    drag = round((mg.get("cagr") or 0) - (mc.get("cagr") or 0), 2)
    return {"cost_bp": round(rt_bp * 10000, 1), "metrics_net": mc,
            "cost_drag": drag, "cost_sensitive": bool(drag >= 0.5),
            "cost_note": "대조군은 매수후보유라 회전이 0이다 — 비용을 물지 않는다."}


# ── ③ 13F 컨빅션 복제 ───────────────────────────────────────────────────
def guru_clone(RF, TOPN=10, MIN_MGR=8):
    """분기말 보유를 45일 뒤(제출 마감)부터 쓴다. 이 지연을 안 넣으면 있지도 않은 정보를 쓴다."""
    p = os.path.join(DATA, "guru_history.json")
    if not os.path.exists(p):
        return None
    G = json.load(io.open(p, encoding="utf-8"))
    # 회사명 — 툴팁용. 유니버스 정본에서 가져온다(13F 원문 이름은 표기가 제각각이다).
    try:
        NM = {x["t"]: (x.get("name") or x["t"]) for x in
              json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))["stocks"]}
    except Exception:
        NM = {}
    months, mpx = G.get("months") or [], G.get("mpx") or {}
    if not months or not mpx:
        return None
    mi = {m: i for i, m in enumerate(months)}
    tick = sorted(mpx)
    P = {t: np.array([np.nan if v is None else v for v in mpx[t]], float) for t in tick}

    def q_to_month(q):
        """분기말 + 45일 → 그 정보를 실제로 쓸 수 있는 첫 달."""
        y, mo = int(q[:4]), int(q[5:7])
        mo += 2                      # 45일 ≈ 1.5개월 → 다음다음 달부터 보유
        while mo > 12:
            mo -= 12; y += 1
        return "%04d-%02d" % (y, mo)

    # 분기별 목표 바스켓: 컨빅션(운용사 포트폴리오 내 비중) × 컨센서스(보유 운용사 수)
    basket = {}
    for q, mm in (G.get("holdings") or {}).items():
        if len(mm) < MIN_MGR:
            continue                 # 운용사가 적은 초기 분기는 '컨센서스'가 성립하지 않는다
        score, nheld = {}, {}
        for _cik, h in mm.items():
            tot = sum(h.values())
            if tot <= 0:
                continue
            for t, v in h.items():
                if t not in P:
                    continue
                score[t] = score.get(t, 0.0) + v / tot      # 컨빅션 합
                nheld[t] = nheld.get(t, 0) + 1              # 컨센서스
        rank = sorted(score, key=lambda t: -(score[t] * nheld[t]))
        if rank:
            basket[q_to_month(q)] = rank[:TOPN]

    if len(basket) < 12:
        return None
    st = mi.get(min(basket))
    if st is None or st >= len(months) - 12:
        return None
    # 🚨 백테스트 길이 상한 10년 — 사용자 결정 2026-08-13(tech_backtest.MAX_YEARS 와 같은 값).
    #   이 규칙은 격자가 **월 라벨**이라 asset_backtest 의 cap_start(거래일 인덱스)를 못 쓴다.
    #   자기 파일에서 따로 걸어야 하고, 실제로 이것만 12.9년으로 남아 있었다(실측).
    MAX_YEARS = 10
    st = max(st, len(months) - MAX_YEARS * 12)

    # 대조군 = S&P 500(PR) 월수익. 사용자 결정(2026-07-28) — 동일가중 유니버스는 쓰지 않는다.
    SPXM = spx_monthly(months)
    if SPXM is None:
        raise SystemExit("대조군(S&P 500 PR)을 assets.json 에서 읽지 못했다 — 판정을 낼 수 없다.")
    hold, nav, rets, bn, brs = [], [100.0], [], [100.0], []
    nav_c = [100.0]        # 비용 후
    turn = 0
    for i in range(st + 1, len(months)):
        m = months[i - 1]
        tc = 0.0
        if m in basket:
            new = [t for t in basket[m] if np.isfinite(P[t][i - 1])]
            if new:
                nnew = len(set(new) - set(hold))
                turn += nnew
                tc = nnew / max(1, len(new)) * COST_RT_STOCK   # 교체 비중만큼 왕복
                hold = new
        rr = [P[t][i] / P[t][i - 1] - 1 for t in hold
              if np.isfinite(P[t][i]) and np.isfinite(P[t][i - 1]) and P[t][i - 1]]
        v = float(np.mean(rr)) if rr else 0.0
        b = float(SPXM[i]) if np.isfinite(SPXM[i]) else 0.0
        rets.append(v); nav.append(nav[-1] * (1 + v))
        nav_c.append(nav_c[-1] * (1 + v - tc))
        brs.append(b); bn.append(bn[-1] * (1 + b))

    # 🚨 2026-08-13 — 여기 샤프가 **무위험을 안 빼고 있었다**(mu/sd). 이 랩에서 같은 병이
    #   네 번째다 — style_top_pdf.metrics(2026-08-05) · home_summary.sharpe(2026-08-13) ·
    #   그리고 여기. 왜곡폭이 rf/vol 이라 저변동일수록 부당하게 유리해진다.
    #   실측: 이 규칙의 지수 샤프가 0.892(여기) vs 0.741(strategy_index 의 같은 구간 지수)로
    #   갈려 있었고, 차이 0.151 × 변동성 15.4 ≈ 2.3%p 가 정확히 rf 몫이다.
    # ⚠ 무위험 창은 이 빌더가 이미 자른 RF 를 그대로 쓴다(main 의 pxd_dates[0] 기준).
    # ⚠ 무위험을 **달마다** 뺀다(평균 상수가 아니라). 랩 정본이 strategy_metrics.series_block
    #   이고 그쪽이 달마다 빼기 때문이다 — 평균으로 빼면 같은 구간·같은 지수인데 샤프가
    #   0.058 갈렸다(실측 0.799 vs 0.741). 창이 아니라 차감 방식의 차이였다.
    def _ex(x, mons):
        return [v - (RF.get(m[:7], 0.0) if m else 0.0) for v, m in zip(x, mons)]

    def mstats(x, nv, mons=None):
        ex = _ex(x, mons) if mons else x
        mu = sum(ex) / len(ex)
        sd = math.sqrt(sum((v - (sum(x) / len(x))) ** 2 for v in x) / max(1, len(x) - 1))
        yrs = len(x) / 12
        return {"cagr": round(((nv[-1] / nv[0]) ** (1 / yrs) - 1) * 100, 2),
                "vol": round(sd * math.sqrt(12) * 100, 2),
                "sharpe": round(mu / sd * math.sqrt(12), 3) if sd > 0 else None,
                "mdd": round(maxdd(nv) * 100, 2)}
    # rets/brs 는 months[st+1:] 과 짝이다(위 루프 range(st+1, len(months))).
    _MONS = months[st + 1:]
    ms, mb = mstats(rets, nav, _MONS), mstats(brs, bn, _MONS)
    d = [x - y for x, y in zip(rets, brs)]
    mu = sum(d) / len(d)
    sd = math.sqrt(sum((v - mu) ** 2 for v in d) / max(1, len(d) - 1))
    # 베타 — 아카이브가 '초과수익 전부 베타'라고 적었으므로 그 수치를 직접 낸다
    bmu = sum(brs) / len(brs)
    bvar = sum((v - bmu) ** 2 for v in brs) / max(1, len(brs) - 1)
    beta = (sum((x - mu - 0) * (y - bmu) for x, y in zip(rets, brs)) /
            max(1, len(rets) - 1) / bvar) if bvar > 0 else None
    step = max(1, len(nav) // 220)
    return {
        "sid": "guru-clone", "arch": "13f-best-ideas-clone",
        # 이 판은 월 단위라 날짜 계열이 months다(다른 판은 일별 DTS를 dd에 담는다)
        # 지수 곡선도 같이 싣는다(자산 랩과 같은 사유 — 배선이 없어 안 실리고 있었다).
        "chart": curve_pack(months[st:], nav, bn, idx_rets=load_index_tr(months[st:])),
        "bench_label": "S&P 500(PR) 매수후보유",
        # 🚨 2026-08-13 — 이 레코드는 asset_strategies.json 에 실려 나가는데, 무위험 창은
        #   자산 랩(2006-01)이 아니라 **여기 패널(stocks.json 2009-01)** 이다. 안 적으면
        #   strategy_index 가 파일 머리의 rf_from 을 물려받아 같은 카드에 S&P 500(PR)
        #   샤프가 두 값으로 나온다(실측 0.892 vs 0.741).
        "rf_from": _RF_FROM,
        "name": "13F 컨빅션 복제 (상위 %d종목)" % TOPN,
        "rule": "분기말 13F에서 (운용사 포트폴리오 내 비중 합) × (보유 운용사 수)가 높은 %d종목을 "
                "동일가중 보유. 분기말 45일 뒤부터 적용하고 분기마다 교체." % TOPN,
        "why": "'SEC 벌크 데이터셋이 분기당 180MB라 무거워서 못 한다'가 미뤄둔 이유였다. "
               "운용사별 EDGAR 제출을 직접 읽으면 제출당 44KB라 100배 가볍다 — 그 길로 돌렸다.",
        "note": "제출 마감 45일 지연을 반영했다. 대조군은 같은 종목 풀 동일가중이라 "
                "'고르기'의 값어치만 남는다. 13F는 롱 미국주식만 담아 실제 포트폴리오가 아니다. "
                "베타 %s (아카이브가 '초과수익 전부 베타'라 적은 대목의 실측치)."
                % ("%.2f" % beta if beta else "—"),
        "holdings": {"kind": "xsec", "as_of": months[-1], "n": len(hold),
                     "tickers": sorted(hold), "names": {t: NM.get(t, t) for t in sorted(hold)},
                     "note": "가장 최근 분기 13F(제출 마감 45일 지연 반영)로 고른 %d종목을 "
                             "동일가중 보유 중이다." % len(hold)},
        "start": months[st], "end": months[-1], "n_days": (len(months) - st) * 21,
        "n_months": len(months) - st,
        "metrics": ms, "bench": mb, "bench_unstable": False, "beta": round(beta, 2) if beta else None,
        "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
        "t": round(mu / (sd / math.sqrt(len(d))), 2) if sd > 0 else None,
        "turnover": round(turn / TOPN / max(1e-9, (len(months) - st) / 12), 1),
        # 월별 계열이라 일별용 cost_cols 를 못 쓴다 — 같은 mstats 로 비용 후를 낸다.
        "cost_bp": round(COST_RT_STOCK * 10000, 1),
        "metrics_net": mstats([nav_c[k + 1] / nav_c[k] - 1 for k in range(len(nav_c) - 1)],
                              nav_c, _MONS),
        "cost_drag": round((ms.get("cagr") or 0)
                           - (mstats([nav_c[k + 1] / nav_c[k] - 1
                                      for k in range(len(nav_c) - 1)], nav_c).get("cagr") or 0), 2),
        "cost_note": "대조군은 매수후보유라 회전이 0이다 — 비용을 물지 않는다.",
        # 🚨 2026-08-05 추가. 증분 알파(incr/incr5)는 **날짜 정합** 회귀라 dates 가 없으면
        #   아예 못 돈다. 종전에는 nav·bnav 만 실어 이 랩들이 그 검정을 한 번도 못 받았다.
        "dates": (_gt := gthin(months[st:], nav, bn))[0],
        "nav": _gt[1],
        "bnav": _gt[2],
    }


def spx_monthly(months):
    """months('YYYY-MM') 축에 맞춘 S&P 500(PR) 월수익."""
    try:
        A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    except Exception:
        return None
    ad = A.get("dates") or []
    raw = (A.get("px") or {}).get("^GSPC")
    if not raw:
        return None
    last = {}
    for i, d in enumerate(ad):
        if i < len(raw) and raw[i] is not None:
            last[d[:7]] = float(raw[i])
    out = np.full(len(months), np.nan)
    for j in range(1, len(months)):
        a_, b_ = last.get(months[j - 1]), last.get(months[j])
        if a_ and b_ and a_ > 0:
            out[j] = b_ / a_ - 1.0
    return out



_RF_FROM = None      # 이 빌더가 실제로 쓴 무위험 창(main 이 채운다)


def main() -> int:
    RF = json.load(io.open(os.path.join(DATA, "rf_monthly.json"),
                           encoding="utf-8")).get("monthly") or {}
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    _GRID.clear()
    _GRID.update({d: i for i, d in enumerate(st["pxd_dates"])})
    # 무위험은 패널 구간으로 자른다 — 랩 공통 규약(DATA-FACTS 참조).
    RF = {k: v for k, v in RF.items() if k >= st["pxd_dates"][0][:7]}
    global _RF_FROM
    _RF_FROM = st["pxd_dates"][0][:7]      # 위 레코드가 싣는다 — 손으로 안 적는다
    r = guru_clone(RF)
    if not r:
        print("❌ 산출 없음(표본 부족)"); return 1
    r["sid"] = "guru-clone"
    doc = {"note": "13F 컨빅션 복제. 규약을 코드에 먼저 박고 한 번만 돌린 결과다. "
                   "공시지연 45일을 그대로 태운다.",
           "as_of": st["pxd_dates"][-1], "strategies": [r]}
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("13F 컨빅션 복제 · CAGR %s · 샤프 %s · t %s → %s"
          % (r["metrics"].get("cagr"), r["metrics"].get("sharpe"), r.get("t"), OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
