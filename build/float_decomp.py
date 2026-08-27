# -*- coding: utf-8 -*-
"""build/float_decomp.py — 부동주 조정과 개별 상한을 분해한다 → data/float_decomp.json

규약: build/PREREG-2026-08-27-FLOAT.md (계산 전 커밋 · 규칙·예상·실패 조건 포함).

  네 벌을 같은 유니버스·같은 격자·같은 비용으로 돌린다.
    A 발행주식수 시총가중            (부동주 ✗ · 상한 ✗)
    B 발행주식수 + 상시 4.5% 상한     (부동주 ✗ · 상한 상시)
    C 발행주식수 + NDX 트리거 상한     (부동주 ✗ · 상한 트리거)
    D 벤더 공식 비중                (부동주 ✓ · 상한 지수 룰)
  B−A = 상시 상한 효과 · C−A = 트리거 효과 · D−C = 부동주 + 룰 잔차

🚨 비중 원자료(_ndx_weights_cache.json)는 **커밋 금지**(사용자 규약 2026-08-19).
  이 측정은 러너가 재생산할 수 없다 — 얼린 측정이다. 산출물엔 시계열·요약만 싣는다.
  같은 제약 아래 도는 선례가 build/tilt_backtest.py 다.

⚠ 상한 계산은 tech_backtest.cap_weights() 를 그대로 부른다. 사본을 만들면 두 벌이 되고
  한쪽만 고쳐지는 날이 온다(이 저장소가 되풀이 밟은 사고다).

    python build/float_decomp.py
"""
from __future__ import annotations
import io
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "float_decomp.json")
sys.path.insert(0, HERE)

START = "2017-04"       # §규칙 — tilt_backtest 와 같다(그 전은 편출 조정가 없음)
COST = 0.0005           # 편도 5bp
CAP_ALWAYS = 0.045      # B: 상시 상한
TRIG_OVER = 0.045       # C: 트리거 판정 문턱(4.5% 초과 종목)
TRIG_SUM = 0.48         # C: 그 합계가 이 값을 넘으면
TRIG_TO = 0.40          # C: 이 값까지 낮춘다
MISS_DROP = 0.05        # §실패조건 — 가격 못 맞춘 비중이 이 값을 넘는 주는 버린다
MISS_FATAL = 0.10       # 이 값을 넘는 주가 전체의 5% 를 넘으면 측정 실패
MAX_GAP_D = 10          # 스냅샷 간격이 이보다 벌어지면 «이어진 주» 로 치지 않는다


def _daydiff(a, b):
    import datetime as _dt
    f = "%Y-%m-%d"
    return (_dt.datetime.strptime(b, f) - _dt.datetime.strptime(a, f)).days


def load_vendor():
    p = os.path.join(DATA, "_ndx_weights_cache.json")
    if not os.path.exists(p):
        raise SystemExit(
            "비중 캐시가 없다(data/_ndx_weights_cache.json) — 사내 DB 자격이 있는 PC 에서만 "
            "만들 수 있다. 이 측정은 얼린 측정이고 러너에선 못 돈다(PREREG §자료).")
    d = json.load(io.open(p, encoding="utf-8"))
    return d["dates"], d["w"]


def trigger_weights(w):
    """NDX 특별 리밸런스 복제 — 4.5% 초과 합계가 48% 를 넘을 때만 40% 로 낮춘다.

    ⚠ 공식 룰과 완전히 같지 않다(공식은 개별 24%→20% 캡·순위 기반 절차가 더 있다).
      그래서 D−C 를 «부동주» 라고 단정하지 않는다(PREREG §실패조건).
    """
    over = {t: x for t, x in w.items() if x > TRIG_OVER + 1e-12}
    if sum(over.values()) <= TRIG_SUM:
        return dict(w), False
    # 초과군 합계를 TRIG_TO 로 눌러 담고 나머지에 비례 재배분
    lo = {t: x for t, x in w.items() if t not in over}
    losum = sum(lo.values())
    if losum <= 0:
        return dict(w), False
    scale = TRIG_TO / sum(over.values())
    out = {t: x * scale for t, x in over.items()}
    add = (1.0 - TRIG_TO) / losum
    for t, x in lo.items():
        out[t] = x * add
    return out, True


def main():
    import tech_backtest as TB
    # 개명 별칭은 tilt_backtest.alias_map() 을 그대로 부른다 — 손 표도 사본도 만들지
    #   않는다(FB→META 처럼 개명뿐인데 결측으로 세면 4.2% 를 통째로 버린다).
    from tilt_backtest import alias_map
    AL = alias_map()
    dates, wmap = load_vendor()
    dates = [d for d in dates if d >= START]
    print("벤더 스냅샷 %d주 (%s ~ %s)" % (len(dates), dates[0], dates[-1]))

    # 랩 가격 격자 — 편출 종목까지 있는 PIT 가격을 쓴다
    px_dates, px, vlm, hid, lod, meta, rf = TB.load(full=True)
    FU = TB.load_fund()
    di = {d: i for i, d in enumerate(px_dates)}

    def _px1(t, d):
        s = px.get(t)
        if not s:
            return None
        i = di.get(d)
        if i is None:                      # 스냅샷 날짜가 거래일이 아니면 직전 거래일
            j = max((k for dd, k in di.items() if dd <= d), default=None)
            if j is None:
                return None
            i = j
        for k in range(i, max(-1, i - 8), -1):
            v = s[k] if k < len(s) else None
            if v and v > 0:
                return v
        return None

    def px_on(t, d):
        """그 날 이전 마지막 종가 — 개명이면 별칭으로도 찾는다.

        가격 키를 함께 돌려준다. A·B 의 시총은 **찾은 키**의 발행주식수로 재야 한다
        (FB 로 주식수를 찾으면 없다).
        """
        v = _px1(t, d)
        if v:
            return v, t
        for a in sorted(AL.get(t, ())):
            v = _px1(a, d)
            if v:
                return v, a
        return None, None

    def shares(t, d):
        f = FU.get(t) or {}
        return TB.asof_fund(f.get("sh"), d)

    rows, dropped, fatal = [], [], 0
    for d in dates:
        vend = {t: w for t, w, _g in wmap[d]}
        tot = sum(vend.values()) or 1.0
        vend = {t: w / tot for t, w in vend.items()}
        # 가격을 맞춘 종목만
        ok = {t: px_on(t, d) for t in vend}          # t -> (가격, 가격키)
        miss = sum(w for t, w in vend.items() if not ok[t][0])
        if miss > MISS_DROP:
            dropped.append((d, round(miss, 4)))
            if miss > MISS_FATAL:
                fatal += 1
            continue
        use = {t: p for t, (p, _k) in ok.items() if p}
        keyof = {t: k for t, (p, k) in ok.items() if p}   # 벤더 티커 -> 가격키
        # A — 발행주식수 시총가중
        mc = {}
        for t in use:
            sh = shares(keyof[t], d)          # ⚠ 개명 종목은 별칭 키로 찾아야 한다
            if sh and sh > 0:
                mc[t] = sh * use[t]
        if len(mc) < 50:
            dropped.append((d, "시총 %d종" % len(mc)))
            continue
        # 🚨 기준 명단은 **mc 의 키** 하나다 — 가격과 발행주식수를 둘 다 맞춘 종목.
        #   네 벌이 서로 다른 명단 위에 서면 «부동주 효과» 자리에 유니버스 차이가 섞인다
        #   (사전등록 §규칙: A·B·C 도 같은 명단을 쓴다). 주식수가 없어 빠진 비중은
        #   결측에 더해 같은 실패 조건으로 판정한다 — 조용히 넘기지 않는다.
        miss2 = miss + sum(w for t, w in vend.items() if t in use and t not in mc)
        if miss2 > MISS_DROP:
            dropped.append((d, round(miss2, 4)))
            if miss2 > MISS_FATAL:
                fatal += 1
            continue
        wA = TB.cap_weights(mc, None)
        wB = TB.cap_weights(mc, CAP_ALWAYS)
        wC, fired = trigger_weights(wA)
        # D — 벤더 공식. **같은 명단 위에서** 재정규화한다.
        s2 = sum(vend[t] for t in mc) or 1.0
        wD = {t: vend[t] / s2 for t in mc}
        assert set(wA) == set(wD) == set(wB) == set(wC), "네 벌의 명단이 갈렸다"
        rows.append(dict(d=d, px={t: use[t] for t in mc}, miss=round(miss2, 5),
                         fired=fired, n=len(mc),
                         w={"A": wA, "B": wB, "C": wC, "D": wD}))
    print("자료 되는 주 %d · 못 쓰는 주 %d (그중 결측 10%% 초과 %d)"
          % (len(rows), len(dropped), fatal))

    # 🚨 여기서 버린 주를 그냥 건너뛰고 남은 행끼리 이어 붙이면 **여러 주치 수익률이 한
    #   주로** 계산된다(변동성이 눌리고 연율화 분모가 틀린다). 그래서 이어지지 않는
    #   구간은 붙이지 않고, **끊기지 않는 최장 구간** 하나만 쓴다.
    #   구간을 고르는 기준은 오직 자료 커버리지다 — 수익률은 아직 한 줄도 계산하지 않았다
    #   (재등록 2026-08-27 · PREREG §재등록).
    keep = {r["d"] for r in rows}
    best = cur = []
    for i, d in enumerate(dates):
        gap_ok = (not cur) or _daydiff(cur[-1], d) <= MAX_GAP_D
        if d in keep and gap_ok:
            cur = cur + [d]
        elif d in keep:
            cur = [d]
        else:
            cur = []
        if len(cur) > len(best):
            best = cur
    span = set(best)
    rows = [r for r in rows if r["d"] in span]
    print("끊기지 않는 최장 구간 %d주 (%s ~ %s)" % (len(rows), rows[0]["d"], rows[-1]["d"]))
    if len(rows) < 150:
        raise SystemExit("이어지는 구간이 %d주뿐이다 — 측정 못 함(PREREG §실패조건)" % len(rows))

    # 주간 수익률 — 다음 주 스냅샷 가격으로
    keys = ["A", "B", "C", "D"]
    ret = {k: [] for k in keys}
    labels = []
    turn = {k: [] for k in keys}
    prev = {k: None for k in keys}
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        # ⚠ 검사가 조용히 통과하지 않게 실제로 잰다 — 이어붙임 사고는 이 저장소가 밟은 적이 있다
        if _daydiff(a["d"], b["d"]) > MAX_GAP_D:
            raise SystemExit("구간이 끊겼다: %s → %s (%d일)"
                             % (a["d"], b["d"], _daydiff(a["d"], b["d"])))
        labels.append(b["d"])
        for k in keys:
            w = a["w"][k]
            r = 0.0
            for t, ww in w.items():
                p0, p1 = a["px"].get(t), b["px"].get(t)
                if p0 and p1:
                    r += ww * (p1 / p0 - 1)
            # 회전 — 직전 비중 대비(가격 표류 무시한 근사, 네 벌 모두 같은 근사)
            if prev[k]:
                tv = sum(abs(w.get(t, 0) - prev[k].get(t, 0)) for t in set(w) | set(prev[k])) / 2
            else:
                tv = 1.0
            turn[k].append(tv)
            ret[k].append(r - tv * COST)
            prev[k] = w

    def ann(xs):
        g = 1.0
        for x in xs:
            g *= (1 + x)
        yrs = len(xs) / 52.0
        return (g ** (1 / yrs) - 1) * 100 if yrs > 0 else 0.0

    def vol(xs):
        m = sum(xs) / len(xs)
        return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs)) * math.sqrt(52) * 100

    def mdd(xs):
        g, pk, w = 1.0, 1.0, 0.0
        for x in xs:
            g *= (1 + x)
            pk = max(pk, g)
            w = min(w, g / pk - 1)
        return w * 100

    def tstat(xs):
        if len(xs) < 3:
            return None
        m = sum(xs) / len(xs)
        s = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
        return (m / s * math.sqrt(len(xs))) if s > 0 else None

    summ = {}
    for k in keys:
        xs = ret[k]
        v = vol(xs)
        summ[k] = dict(cagr=round(ann(xs), 3), vol=round(v, 3),
                       sharpe=round(ann(xs) / v, 3) if v else None,
                       mdd=round(mdd(xs), 2),
                       turnover=round(sum(turn[k]) / len(turn[k]) * 52, 2))
    diffs = {}
    for lab, x, y in (("B-A", "B", "A"), ("C-A", "C", "A"), ("D-C", "D", "C"), ("D-A", "D", "A")):
        dd = [p - q for p, q in zip(ret[x], ret[y])]
        diffs[lab] = dict(ann_pp=round(ann(ret[x]) - ann(ret[y]), 3),
                          te=round(vol(dd), 3),
                          t=round(tstat(dd), 2) if tstat(dd) else None)
    fired_n = sum(1 for r in rows if r["fired"])

    # ── 비중 공간 분해 ────────────────────────────────────────────────────────
    # 수익률 차이가 전부 |t|<1 로 나왔다. 그러면 «어느 축이 성적을 만들었나» 는 수익률로
    #   답이 안 된다(PREREG §실패조건 넷째). 대신 두 축이 비중을 얼마나 움직이는지 잰다 —
    #   이건 표본오차 없이 관측된다.
    def effn(w):
        ss = sum(x * x for x in w.values())
        return (1.0 / ss) if ss > 0 else 0.0

    wspace = []
    for r in rows[-52:]:                       # 최근 1년치
        wA_, wB_, wC_, wD_ = (r["w"][k] for k in keys)
        # 부동주 배수 — ⚠ 두 함정이 있다.
        #   ① 상한이 걸린 종목에서 뽑으면 상한 효과가 섞인다 → 3% 미만만 쓴다.
        #   ② 두 비중이 각자 100% 로 정규화돼 있어, D 가 대형주를 눌러 남긴 몫이 작은
        #      종목 전부를 위로 밀어 올린다(그래서 날것의 중앙값이 1.888 로 1 을 넘는다).
        #      부동주 비율은 1 을 넘을 수 없으니 그 수는 부동주가 아니다.
        #      → **자기 중앙값으로 다시 나눠** 정규화 상수를 상쇄시킨다. 남는 것은
        #      «보통 종목 대비 이 종목의 부동주» 라는 상대 차이다.
        _pair = [(t, wD_[t] / wA_[t]) for t in wA_
                 if wA_[t] < 0.03 and wD_[t] < 0.03 and wA_[t] > 1e-6]
        _raw = sorted(v for _t, v in _pair)
        _med0 = _raw[len(_raw) // 2] if _raw else 1.0
        _pair = sorted(((t, v / _med0) for t, v in _pair), key=lambda x: x[1])
        rat = [v for _t, v in _pair]

        def q(p, _r=rat):
            return _r[min(len(_r) - 1, int(len(_r) * p))] if _r else None

        wspace.append(dict(
            d=r["d"], n=r["n"],
            effN={k: round(effn(r["w"][k]), 1) for k in keys},
            wmax={k: round(max(r["w"][k].values()) * 100, 2) for k in keys},
            top5={k: round(sum(sorted(r["w"][k].values(), reverse=True)[:5]) * 100, 1)
                  for k in keys},
            float_ratio=dict(n=len(rat),
                             p10=round(q(0.10), 3) if rat else None,
                             med=round(q(0.50), 3) if rat else None,
                             p90=round(q(0.90), 3) if rat else None,
                             # 극단 종목 — 아래쪽에 창업자·재단 보유가 큰 이름이 와야
                             #   이 지표가 부동주를 재고 있는 것이다(안 그러면 딴 걸 잰다)
                             low=[[t, round(v, 3)] for t, v in _pair[:5]],
                             high=[[t, round(v, 3)] for t, v in _pair[-5:]]),
            # 한쪽 방향으로 옮긴 비중의 합(%p) — 축이 포트폴리오를 얼마나 바꾸나
            move_cap=round(sum(abs(wB_[t] - wA_[t]) for t in wA_) / 2 * 100, 2),
            move_float=round(sum(abs(wD_[t] - wC_[t]) for t in wC_) / 2 * 100, 2),
        ))
    _last = wspace[-1]

    def _avg(f):
        return round(sum(f(x) for x in wspace) / len(wspace), 2)

    doc = {
        "note": ("부동주 조정과 개별 상한의 분해. 규약 build/PREREG-2026-08-27-FLOAT.md. "
                 "🚨 벤더 비중 원자료는 커밋하지 않는다(사용자 규약 2026-08-19) — 이 측정은 "
                 "러너가 재생산할 수 없는 얼린 측정이고 여기엔 시계열·요약만 있다."),
        "generated": rows[-1]["d"],
        "window": [labels[0], labels[-1]],
        "n_weeks": len(labels),
        "start_rule": ("자료 커버리지만으로 고른 «끊기지 않는 최장 구간». 후보는 %s 이후 "
                       "%d주였고 그중 결측 %.0f%% 이하가 연속으로 이어지는 최장 구간을 썼다. "
                       "수익률을 보기 전에 정했다.") % (START, len(dates), MISS_DROP * 100),
        "coverage_note": ("랩 가격 유니버스가 현재 명단(518종)이라 과거 편출 종목이 없다 — "
                          "생존편향 채널이다. 결측 비중이 2017년 평균 14.2%에서 2026년 0.5%로 "
                          "단조 감소하고, 그래서 2017-04 전체 창은 사전등록한 실패 조건에 걸렸다"
                          "(결측 10% 초과인 주가 14%). 이 산출물은 그 조건을 통과하는 구간만 쓴다."),
        "cost_bp_oneway": COST * 1e4,
        "legs": {
            "A": "발행주식수 시총가중 (부동주 ✗ · 상한 ✗)",
            "B": "발행주식수 + 상시 %.1f%% 상한" % (CAP_ALWAYS * 100),
            "C": "발행주식수 + NDX 트리거 상한 (%.0f%% 초과 합 %.0f%% → %.0f%%)"
                 % (TRIG_OVER * 100, TRIG_SUM * 100, TRIG_TO * 100),
            "D": "벤더 공식 비중 (부동주 ✓ · 지수 룰)",
        },
        "summary": summ,
        "diffs": diffs,
        "trigger_fired_weeks": fired_n,
        "trigger_fired_note": ("트리거를 매주 상한없음 비중 위에서 판정한 결과다. 실제 NDX 특별 리밸런스는 "
                               "1998·2011·2023 세 번뿐이므로 이 복제는 «가끔» 이 아니라 "
                               "«거의 늘» 발동한다. 그래서 D−C 에 섞인 룰 잔차가 작지 않고, "
                               "D−C 를 부동주 효과라고 읽으면 안 된다(PREREG §실패조건 셋째)."),
        "weight_space": {
            "note": ("수익률 차이가 전부 |t|<1 이라 «어느 축이 성적을 만들었나» 는 수익률로 "
                     "답이 안 된다. 두 축이 비중을 얼마나 움직이는지는 표본오차 없이 "
                     "관측된다 — 최근 52주. move_cap 은 상한(A→B), move_float 은 "
                     "부동주+룰(C→D) 이 옮기는 비중의 한쪽 방향 합(%p)이다."),
            "avg_move_cap_pp": _avg(lambda x: x["move_cap"]),
            "avg_move_float_pp": _avg(lambda x: x["move_float"]),
            "float_ratio_note": ("배수는 자기 중앙값으로 정규화했다 — 날것은 두 비중이 각자 "
                                 "100%로 맞춰져 있어 D가 대형주를 누른 몫이 작은 종목을 "
                                 "통째로 밀어 올린다(날것 중앙값 1.89). 부동주 비율은 1을 "
                                 "넘을 수 없으니 그 수는 부동주가 아니다. 정규화 뒤 남는 "
                                 "p10~p90 폭이 «보통 종목 대비» 부동주 차이다. "
                                 "🚨 한계 — D의 대형주는 상한에 걸려 있어 그 종목의 부동주는 "
                                 "이 자료로 복원되지 않는다. 카드가 물은 것의 그 부분은 "
                                 "실제 부동주 주식수 자료가 생겨야 닫힌다."),
            "last": _last,
            "series": wspace,
        },
        "dropped_weeks": len(dropped),
        "dropped_fatal": fatal,
        "dropped_sample": dropped[:8],
        "series": {"dates": labels, **{k: [round(x, 6) for x in ret[k]] for k in keys}},
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("\n%-4s %-42s %-8s %-8s %-8s %s" % ("", "", "CAGR", "Vol", "Sharpe", "MDD"))
    for k in keys:
        s = summ[k]
        print("%-4s %-42s %-8.2f %-8.2f %-8.3f %.1f" %
              (k, doc["legs"][k][:40], s["cagr"], s["vol"], s["sharpe"] or 0, s["mdd"]))
    print("\n차이 (연 %p · 추적오차 · t)")
    for lab, v in diffs.items():
        print("   %-5s %+8.3f%%p   TE %6.3f%%   t %s" % (lab, v["ann_pp"], v["te"], v["t"]))
    print("\n트리거 발동 %d주 / %d · 못 쓴 주 %d" % (fired_n, len(rows), len(dropped)))
    print("\n── 비중 공간 (최근 52주) ──")
    print("   상한이 옮기는 비중   A→B  %5.2f%%p" % _avg(lambda x: x["move_cap"]))
    print("   부동주+룰이 옮기는   C→D  %5.2f%%p" % _avg(lambda x: x["move_float"]))
    print("   유효 종목 수  " + " · ".join("%s %.1f" % (k, _last["effN"][k]) for k in keys))
    print("   최대 종목(%%)  " + " · ".join("%s %.2f" % (k, _last["wmax"][k]) for k in keys))
    print("   상위5 합(%%)   " + " · ".join("%s %.1f" % (k, _last["top5"][k]) for k in keys))
    _fr = _last["float_ratio"]
    print("   부동주 배수(상한 무관 %d종 · 중앙값=1 로 정규화) p10 %.3f · p90 %.3f"
          % (_fr["n"], _fr["p10"], _fr["p90"]))
    print("     낮은 쪽 " + " · ".join("%s %.2f" % (t, v) for t, v in _fr["low"]))
    print("     높은 쪽 " + " · ".join("%s %.2f" % (t, v) for t, v in _fr["high"]))
    print("→ %s" % OUT)


if __name__ == "__main__":
    main()
