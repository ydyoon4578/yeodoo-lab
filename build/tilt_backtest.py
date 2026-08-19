# -*- coding: utf-8 -*-
"""build/tilt_backtest.py — 틸트(NDX 종목별 비중 틸팅) → data/tilt.json

규약: build/PREREG-2026-08-20-TILT.md (계산 전 커밋 · 예측 P1~P5 포함).

  기준: 벤더 NDX 지수 비중(주말 스냅샷 · data/_ndx_weights_cache.json · gitignore).
  틸트: w' ∝ w × (1 + K·clip(z(dist200), ±2)), 재정규화 · 공매도 없음 · 상시 100%.
  🚨 비중 원자료는 커밋 금지(사용자 규약 2026-08-19) — 이 측정은 러너가 재생산할 수
    없다(얼린 측정). 산출물엔 시계열·요약만 싣는다.

    python build/tilt_backtest.py
"""
from __future__ import annotations
import datetime as dt
import io
import json
import math
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "tilt.json")
sys.path.insert(0, HERE)
from aegis_backtest import load_px, week_ends, Sig, metrics, bench_track, tstat  # noqa: E402

K_TILT = 0.3
Z_CLIP = 2.0
COST = 0.0005          # 편도 5bp — §1
START = "2017-04"
# 🚨 등록(§1)의 시작은 2014-07 이었다. 그러나 2014-06~2017-03 은 편출종목(CELG·PCLN·
#   YHOO·ATVI 등 — 야후 사망·DB 겹침일 0이라 기준 정렬 불가) 탈락 비중이 10~15%로,
#   「기준을 못 맞추면 안 넣는다」(pit_px_db 규약)에 걸려 재현 불가다. 규칙·상수는
#   그대로 두고 **구간만 자료가 받치는 2017-04 부터**로 좁힌다 — 결과를 보고 바꾼 것이
#   아니라 자료 제약이고, 그 사실은 산출물·세 번째 목록에 그대로 적는다.
#   근본 해결은 상장폐지 종목의 조정가 벤더(EODHD 등 — delisted_names.json KNOWN 참조).
DIV_NDX = 0.8          # 배당보정(%p/yr) — §0


def load_weights():
    p = os.path.join(DATA, "_ndx_weights_cache.json")
    if not os.path.exists(p):
        raise SystemExit("비중 캐시가 없다(data/_ndx_weights_cache.json) — DB 자격으로 "
                         "받아야 한다. 러너에서는 이 측정을 재생산할 수 없다(등록 §0).")
    return json.load(io.open(p, encoding="utf-8"))


def alias_map():
    """옛 티커 → 같은 CIK 의 다른 티커들(index_history.json cik_hist) — 손 표 금지."""
    out = {}
    ch = (json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8"))
          or {}).get("cik_hist") or {}
    for _cik, ts in ch.items():
        for t in ts:
            out.setdefault(t, set()).update(x for x in ts if x != t)
    return out


def zscores(vals):
    xs = [v for v in vals.values() if v is not None]
    if len(xs) < 30:
        return {}
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
    if sd <= 0:
        return {}
    return {t: max(-Z_CLIP, min(Z_CLIP, (v - m) / sd))
            for t, v in vals.items() if v is not None}


def run(dts, px, sig, W, AL, we_idx, k_tilt=K_TILT, cost=COST, monthly=False):
    d2i = {d: i for i, d in enumerate(dts)}
    nav_t = nav_r = 100.0
    daily_d, dv_t, dv_r = [], [], []
    wk = {"d": [], "rt": [], "rr": [], "turn_t": [], "turn_r": [], "drop_w": [], "n": [],
          "i0": [], "i1": []}
    prev_wt, prev_wr = None, None
    held_wt = None                     # 월간 리밸(§5) — 스킵 주엔 직전 틸트 비중 유지
    for j in range(len(we_idx) - 1):
        i0, i1 = we_idx[j], we_idx[j + 1]
        d0 = dts[i0]
        if d0[:7] < START:
            continue
        rows = W["w"].get(d0)
        if not rows:
            continue
        # 티커 → 랩 가격 키(개명은 cik_hist 별칭으로)
        port = []
        drop = 0.0
        for t, w in rows:
            key = None
            if px.get(t) and px[t][i0] and px[t][i1]:
                key = t
            else:
                for a in sorted(AL.get(t, ())):
                    if px.get(a) and px[a][i0] and px[a][i1]:
                        key = a
                        break
            if key is None:
                drop += w
            else:
                port.append((key, w))
        if not port or drop > 0.10:
            continue                    # 탈락 10% 초과 주는 신뢰 불가 — 세지 않는다
        s = sum(w for _t, w in port)
        base = {t: w / s for t, w in port}
        # 신호 z → 틸트 비중
        do_tilt = (not monthly) or (held_wt is None) or (dts[i1][:7] != d0[:7])
        if do_tilt:
            z = zscores({t: sig.dist(t, i0) for t in base})
            wt = {t: w * (1 + k_tilt * z.get(t, 0.0)) for t, w in base.items()}
            sw = sum(wt.values())
            wt = {t: w / sw for t, w in wt.items()}
            held_wt = wt
        else:
            wt = {t: w for t, w in held_wt.items() if t in base}
            sw = sum(wt.values())
            wt = {t: w / sw for t, w in wt.items()} if sw > 0 else dict(base)

        def week(nav, w_now, prev, dvs):
            # 실회전(드리프트 보정) → 비용 → 일간 경로
            if prev is None:
                turn = 1.0
            else:
                drift = {}
                tot = 0.0
                for t, w in prev.items():
                    g = (px[t][i0] / prev["__p0"][t]) if t != "__p0" and px.get(t) and prev["__p0"].get(t) else None
                    if t == "__p0" or g is None:
                        continue
                    drift[t] = w * g
                    tot += w * g
                drift = {t: v / tot for t, v in drift.items()} if tot > 0 else {}
                turn = sum(abs(w_now.get(t, 0.0) - drift.get(t, 0.0))
                           for t in set(w_now) | set(drift))
            nav0 = nav * (1 - cost * turn)
            p0 = {t: px[t][i0] for t in w_now}
            cur = dict(p0)
            path = []
            for d in range(i0 + 1, i1 + 1):
                acc = 0.0
                for t, w in w_now.items():
                    v = px[t][d]
                    if v:
                        cur[t] = v
                    acc += w * (cur[t] / p0[t])
                path.append(nav0 * acc)
            keep = dict(w_now)
            keep["__p0"] = p0
            return path[-1], path, keep, turn

        n_t, path_t, prev_wt, turn_t = week(nav_t, wt, prev_wt, dv_t)
        n_r, path_r, prev_wr, turn_r = week(nav_r, base, prev_wr, dv_r)
        if not daily_d:
            daily_d.append(d0); dv_t.append(nav_t); dv_r.append(nav_r)
        daily_d.extend(dts[i0 + 1:i1 + 1])
        dv_t.extend(path_t); dv_r.extend(path_r)
        wk["d"].append(d0)
        wk["i0"].append(i0); wk["i1"].append(i1)
        wk["rt"].append(n_t / nav_t - 1)
        wk["rr"].append(n_r / nav_r - 1)
        wk["turn_t"].append(turn_t); wk["turn_r"].append(turn_r)
        wk["drop_w"].append(drop); wk["n"].append(len(base))
        nav_t, nav_r = n_t, n_r
    return daily_d, dv_t, dv_r, wk


def main() -> int:
    dts, px, bench = load_px()
    W = load_weights()
    AL = alias_map()
    sig = Sig(px, len(dts))
    we_idx = week_ends(dts)

    daily_d, dv_t, dv_r, wk = run(dts, px, sig, W, AL, we_idx)
    m_t = metrics(daily_d, dv_t, wk["rt"])
    m_r = metrics(daily_d, dv_r, wk["rr"])
    ndx_ff, last = [], None
    for v in bench["ndx"]:
        if v is not None:
            last = v
        ndx_ff.append(last)                 # 결측일 전방 채움 — 주중 소수 결측 방어
    dd_b, dv_b, _wk_cont = bench_track(dts, {"ndx": ndx_ff}, "ndx", daily_d, we_idx)
    # 🚨 주간 대조는 반드시 채택 주와 같은 (i0,i1) 로 — 연속 주간과 zip 금지(정렬 버그)
    wk_b = [ndx_ff[i1] / ndx_ff[i0] - 1 for i0, i1 in zip(wk["i0"], wk["i1"])]
    m_b = metrics(dd_b, dv_b, wk_b)
    m_b["cagr_div_adj"] = round(m_b["cagr"] + DIV_NDX, 2)

    # 순수 틸트 효과(같은 기저 · 같은 비용) + 복제 검증
    act = [a - b for a, b in zip(wk["rt"], wk["rr"])]
    m_act, t_act = tstat(act)
    te = math.sqrt(sum((x - m_act) ** 2 for x in act) / (len(act) - 1)) * math.sqrt(52)
    yrs = (dt.date.fromisoformat(daily_d[-1]) - dt.date.fromisoformat(daily_d[0])).days / 365.25
    ann_act = (dv_t[-1] / dv_r[-1]) ** (1 / yrs) - 1
    ir = ann_act / te if te > 0 else None
    rep = [a - b for a, b in zip(wk["rr"], wk_b)]
    m_rep, _t_rep = tstat(rep)
    te_rep = math.sqrt(sum((x - m_rep) ** 2 for x in rep) / (len(rep) - 1)) * math.sqrt(52)
    ann_rep = (dv_r[-1] / dv_r[0]) ** (1 / yrs) - (dv_b[-1] / dv_b[0]) ** (1 / yrs)

    gates = {
        "U1_cagr": {"strat": m_t["cagr"], "bm": m_b["cagr"], "bm_div_adj": m_b["cagr_div_adj"],
                    "pass": bool(m_t["cagr"] > m_b["cagr"]),
                    "pass_div_adj": bool(m_t["cagr"] > m_b["cagr_div_adj"])},
        "U2_sharpe": {"strat": m_t["sharpe"], "bm": m_b["sharpe"],
                      "pass": bool(m_t["sharpe"] > m_b["sharpe"])},
        "U3_mdd": {"strat": m_t["mdd"], "bm": m_b["mdd"],
                   "pass": bool(abs(m_t["mdd"]) < abs(m_b["mdd"]))},
    }
    n_pass = sum(1 for v in gates.values() if v["pass"])
    tilt_real = bool(t_act is not None and t_act >= 2)

    # 월별 승률(vs ^NDX · 같은 주간 격자에서 월 합성)
    mret_t, mret_b = {}, {}
    for d, a, b in zip(wk["d"], wk["rt"], wk_b):
        mret_t[d[:7]] = mret_t.get(d[:7], 1.0) * (1 + a)
        mret_b[d[:7]] = mret_b.get(d[:7], 1.0) * (1 + b)
    ms = sorted(mret_t)
    winm = sum(1 for m in ms if mret_t[m] >= mret_b[m])

    # 연도별
    def ytab(dd, vv):
        last = {}
        for d, v in zip(dd, vv):
            last[d[:4]] = v
        out, prev = {}, vv[0]
        for y in sorted(last):
            out[y] = round((last[y] / prev - 1) * 100, 1)
            prev = last[y]
        return out

    pred = {
        "P1_active": {"pred": "연 +0.3~+2.0%p · t 0.8~2.5",
                      "ann_pp": round(ann_act * 100, 2),
                      "t": (None if t_act is None else round(t_act, 2)),
                      "pass": bool(0.3 <= ann_act * 100 <= 2.0 and t_act is not None
                                   and 0.8 <= t_act <= 2.5)},
        "P2_te_ir": {"pred": "TE 1.5~4%p · IR 0.2~0.8", "te_pp": round(te * 100, 2),
                     "ir": (None if ir is None else round(ir, 2)),
                     "pass": bool(1.5 <= te * 100 <= 4 and ir is not None and 0.2 <= ir <= 0.8)},
        "P3_gates": {"pred": "3문 중 2~3 통과 (U1 통과 예상)", "n_pass": n_pass,
                     "pass": bool(n_pass >= 2 and gates["U1_cagr"]["pass"])},
        "P4_winrate": {"pred": "월 승률 52~60%", "pct": round(100.0 * winm / len(ms), 1),
                       "pass": bool(52 <= 100.0 * winm / len(ms) <= 60)},
        "P5_replica": {"pred": "복제-지수 연 +0.4~+1.2%p · TE<=1.5%p",
                       "ann_pp": round(ann_rep * 100, 2), "te_pp": round(te_rep * 100, 2),
                       "pass": bool(0.4 <= ann_rep * 100 <= 1.2 and te_rep * 100 <= 1.5)},
    }

    sens = {}
    for name, kw in (("K015", {"k_tilt": 0.15}), ("K050", {"k_tilt": 0.5}),
                     ("monthly", {"monthly": True}), ("cost20", {"cost": 0.0020})):
        dd2, t2, r2, wk2 = run(dts, px, sig, W, AL, we_idx, **kw)
        mm = metrics(dd2, t2, wk2["rt"])
        act2 = [a - b for a, b in zip(wk2["rt"], wk2["rr"])]
        _m2, t_a2 = tstat(act2)
        ann2 = (t2[-1] / r2[-1]) ** (1 / yrs) - 1
        sens[name] = {"cagr": mm["cagr"], "sharpe": mm["sharpe"], "mdd": mm["mdd"],
                      "active_pp": round(ann2 * 100, 2),
                      "t_active": (None if t_a2 is None else round(t_a2, 2))}

    avg_turn = sum(wk["turn_t"][1:]) / max(1, len(wk["turn_t"]) - 1)
    avg_drop = sum(wk["drop_w"]) / len(wk["drop_w"])
    verdict = ("통과 (3/3)" if n_pass == 3 else "부분 통과 (%d/3)" % n_pass) \
              + (" · 틸트 효과 실재(t>=2)" if tilt_real else " · 틸트 효과 근거 부족(t<2)")

    print("틸트 · %s ~ %s · 주 %d회 · 평균 %d종 · 탈락비중 평균 %.2f%% · 실회전 %.1f%%/주"
          % (daily_d[0], daily_d[-1], len(wk["d"]), sorted(wk["n"])[len(wk["n"]) // 2],
             avg_drop * 100, avg_turn * 100))
    print("%-10s %8s %8s %8s" % ("", "CAGR%", "Sharpe", "MDD%"))
    for nm, m in (("틸트", m_t), ("복제", m_r), ("^NDX", m_b)):
        print("%-10s %8.2f %8.2f %8.2f" % (nm, m["cagr"], m["sharpe"], m["mdd"]))
    print("틸트-복제: 연 %+.2f%%p · t %.2f · TE %.2f%%p · IR %.2f"
          % (ann_act * 100, t_act, te * 100, ir))
    print("복제-지수: 연 %+.2f%%p · TE %.2f%%p (배당 재투자 몫 검증)" % (ann_rep * 100, te_rep * 100))
    for k, v in gates.items():
        print("  %-10s %s %s" % (k, "✅" if v["pass"] else "❌",
                                 {a: b for a, b in v.items() if not a.startswith("pass")}))
    print("월 승률 %.1f%% (%d/%d)" % (100.0 * winm / len(ms), winm, len(ms)))
    print("판정:", verdict)
    print("예측 채점:")
    for k, v in pred.items():
        print("  %-12s %s %s" % (k, "✅" if v["pass"] else "❌",
                                 {a: b for a, b in v.items() if a != "pass"}))
    print("민감도:")
    for k, v in sens.items():
        print("  %-8s CAGR %6.2f · 초과 %+5.2f%%p · t %s · MDD %6.2f"
              % (k, v["cagr"], v["active_pp"], v["t_active"], v["mdd"]))

    doc = {
        "note": "틸트 — NDX 벤더 비중 상대 dist200 비중 틸팅(K=0.3 · 클립 ±2 · 주간 · "
                "상시 100%). 기준 비중은 DB(커밋 금지 · gitignore 캐시)라 러너 재생산 불가 — "
                "얼린 측정. 규칙·예측은 PREREG-2026-08-20-TILT.md 에 계산 전 커밋.",
        "prereg": "build/PREREG-2026-08-20-TILT.md",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {"k_tilt": K_TILT, "z_clip": Z_CLIP, "cost_oneway": COST, "start": START},
        "span": [daily_d[0], daily_d[-1]], "weeks": len(wk["d"]),
        "avg_names": sorted(wk["n"])[len(wk["n"]) // 2],
        "avg_drop_w_pct": round(avg_drop * 100, 2),
        "avg_weekly_turnover_pct": round(avg_turn * 100, 2),
        "strat": m_t, "replica": m_r,
        "bench": m_b,
        "active": {"ann_pp": round(ann_act * 100, 2), "t": round(t_act, 2),
                   "te_pp": round(te * 100, 2), "ir": round(ir, 2)},
        "replica_check": {"ann_pp": round(ann_rep * 100, 2), "te_pp": round(te_rep * 100, 2)},
        "gates": gates, "n_pass": n_pass, "tilt_real": tilt_real, "verdict": verdict,
        "predictions": pred,
        "monthly_winrate_pct": round(100.0 * winm / len(ms), 1),
        "years": {"tilt": ytab(daily_d, dv_t), "replica": ytab(daily_d, dv_r),
                  "ndx": ytab(dd_b, dv_b)},
        "sens": sens,
        "weekly": {"d": wk["d"], "tilt": [round(x, 6) for x in wk["rt"]],
                   "replica": [round(x, 6) for x in wk["rr"]]},
    }
    io.open(OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("→ %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
