# -*- coding: utf-8 -*-
"""build/mech_episodes.py — 기계적 급락·반등 구간(지수만) → data/mech_episodes.json

왜: 랩의 «급등·급락 구간» 12개(market_episodes.json · qg_lab.EPIS)는 이름을 붙여 **사후에 고른** 구간이다. 사용자 기준
  («꾸준히, 그리고 급등락 구간에서 지수를 이기는 게 제일 중요») 으로 전략을 판정하려면 문턱을 미리 정한 기계적 구간이 필요하다.
  라이브러리 결합 설계(2026-09-24 · 설계 워크플로 §B)가 정한 규칙을 그대로 옮긴다. 전략 수익은 한 줄도 읽지 않는다.

규칙(고정):
  · 지그재그 — ^GSPC PR 일간 종가(bench_px.json spx) · 하락 문턱 hd = 10% · 상승 문턱 hu = 10%.
    첫 방향: 누적 고점 H·저점 L 을 따라가다 L → H(저점이 먼저)로 +hu 면 «상승», H → L(고점이 먼저)로 −hd 면 «하락».
    «상승» 중에는 극고점 E 를 따라가고 가격이 E·(1 − hd) 이하가 되면 [피벗, E] 상승 다리가 **그날 확정**, 피벗 = E, «하락» 으로.
    «하락» 은 대칭(E·(1 + hu) 이상).
  · 급락(CRASH) = 확정된 하락 다리 [고점 a, 저점 b].
  · 반등(REBOUND · 사용자의 «급등») = [급락 저점 b, min(b + 63거래일, 그 뒤 상승 다리의 끝)].
  · 상승장(BULL) = 확정된 상승 다리 — «급등» 이 아니라 «상승장 포착» 으로만 쓴다(거래일의 대부분을 덮는다).
  · 월 구간 — SPY 총수익(assets.json px.SPY 수정종가) 월말 수익이 −σ_pre 이하면 CRASH-M · +σ_pre 이상이면 SURGE-M.
    σ_pre = 2006-02 ~ 2016-08 SPY 총수익 월 수익의 표본 표준편차(판정 창 앞 — 창의 정보를 쓰지 않는다).
  · 민감도(서술만): hd = hu ∈ {0.09, 0.12, 0.15} · 로그 대칭(−10% / +11.11%) · 반등 길이 42 · 126 거래일.
  · 창: 2016-08-31 부터. 얼린 판(frozen)은 2026-08-31 까지 · 최신 판(current)은 자료 끝까지(전방 집계용 — 등록 뒤 시작한 다리만 센다).

  python build/mech_episodes.py
"""
from __future__ import annotations
import hashlib, io, json, os, statistics, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "mech_episodes.json")
START, FROZEN_END = "2016-08-31", "2026-08-31"
HD = HU = 0.10
REB_TD = 63
PRE = ("2006-02", "2016-08")


def zigzag(D, P, hd, hu, start, end):
    """(확정 다리 [(side, a, b, move, confirm)], 열린 다리 (side, a, b, move))."""
    idx = [i for i, d in enumerate(D) if start <= d <= end and P[i] is not None]
    i0 = idx[0]
    legs = []
    hi = lo = i0
    mode, piv, ext = None, i0, i0
    for i in idx[1:]:
        p = P[i]
        if mode is None:
            if p > P[hi]:
                hi = i
            if p < P[lo]:
                lo = i
            if P[hi] / P[lo] - 1 >= hu and hi > lo:
                mode, piv, ext = "up", lo, hi
            elif 1 - P[lo] / P[hi] >= hd and lo > hi:
                mode, piv, ext = "dn", hi, lo
            continue
        if mode == "up":
            if p > P[ext]:
                ext = i
            elif 1 - p / P[ext] >= hd:
                legs.append(("rally", D[piv], D[ext], P[ext] / P[piv] - 1, D[i]))
                piv, ext, mode = ext, i, "dn"
        else:
            if p < P[ext]:
                ext = i
            elif p / P[ext] - 1 >= hu:
                legs.append(("crash", D[piv], D[ext], P[ext] / P[piv] - 1, D[i]))
                piv, ext, mode = ext, i, "up"
    return legs, (mode, D[piv], D[ext], P[ext] / P[piv] - 1)


def rebounds(D, P, legs, openleg, td):
    pos = {d: i for i, d in enumerate(D)}
    rallies = [l for l in legs if l[0] == "rally"] + ([("rally", openleg[1], openleg[2], openleg[3], None)] if openleg[0] == "up" else [])
    out = []
    for l in legs:
        if l[0] != "crash":
            continue
        t = pos[l[2]]
        nxt = [x for x in rallies if x[1] == l[2]]
        endr = pos[nxt[0][2]] if nxt else t + td
        e = min(t + td, endr, len(D) - 1)
        out.append({"a": D[t], "b": D[e], "td": e - t, "move": round(P[e] / P[t] - 1, 6)})
    return out


def pack(legs, openleg):
    return {"legs": [{"side": s, "a": a, "b": b, "move": round(m, 6), "confirm": c} for s, a, b, m, c in legs],
            "open": {"side": openleg[0], "a": openleg[1], "b": openleg[2], "move": round(openleg[3], 6)}}


def main() -> int:
    B = json.load(io.open(os.path.join(DATA, "bench_px.json"), encoding="utf-8"))
    D, P = B["dates"], B["series"]["spx"]["px"]
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    me = {}
    for d, p in zip(A["dates"], A["px"]["SPY"]):
        if p is not None:
            me[d[:7]] = p
    ms = sorted(me)
    ret = {ms[i]: me[ms[i]] / me[ms[i - 1]] - 1 for i in range(1, len(ms))}
    pre = [ret[m] for m in ret if PRE[0] <= m <= PRE[1]]
    sig = statistics.stdev(pre)
    last_full = ms[-2] if ms else None                   # 진행 중인 달은 뺀다
    win = [m for m in ret if "2016-09" <= m <= last_full]
    doc = {"note": "기계적 급락·반등 구간(지수만 · 전략 수익을 읽지 않는다). 규칙은 build/mech_episodes.py 머리말 — 사후에 고른 12구간을 대신하는 판정용.",
           "params": {"hd": HD, "hu": HU, "rebound_td": REB_TD, "start": START, "frozen_end": FROZEN_END, "index": "^GSPC PR (bench_px spx)",
                      "month_judge": "SPY TR (assets px.SPY)", "sigma_pre_window": list(PRE)},
           "sigma_pre": round(sig, 6), "sigma_pre_n": len(pre)}
    for tag, end in (("frozen", FROZEN_END), ("current", D[-1])):
        legs, op = zigzag(D, P, HD, HU, START, end)
        doc[tag] = dict(pack(legs, op), end=end, rebounds=rebounds(D, P, legs, op, REB_TD))
    doc["months"] = {"crash_m": [m for m in win if ret[m] <= -sig], "surge_m": [m for m in win if ret[m] >= sig],
                     "down_m": [m for m in win if ret[m] < 0], "window": [win[0], win[-1]], "spy_tr": {m: round(ret[m], 6) for m in win}}
    sens = {}
    for key, hd, hu in (("h09", 0.09, 0.09), ("h12", 0.12, 0.12), ("h15", 0.15, 0.15), ("logsym", 0.10, 1 / 0.9 - 1)):
        legs, op = zigzag(D, P, hd, hu, START, FROZEN_END)
        sens[key] = dict(pack(legs, op), rebounds=rebounds(D, P, legs, op, REB_TD))
    legs, op = zigzag(D, P, HD, HU, START, FROZEN_END)
    sens["reb42"] = rebounds(D, P, legs, op, 42)
    sens["reb126"] = rebounds(D, P, legs, op, 126)
    doc["sensitivity"] = sens
    body = json.dumps({k: v for k, v in doc.items() if k != "current"}, ensure_ascii=False, sort_keys=True)
    doc["frozen_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    fz = doc["frozen"]
    print("σ_pre %.2f%% (n %d) · 월 %s ~ %s · CRASH-M %d · SURGE-M %d · 하락월 %d" % (
        sig * 100, len(pre), win[0], win[-1], len(doc["months"]["crash_m"]), len(doc["months"]["surge_m"]), len(doc["months"]["down_m"])))
    for l in fz["legs"]:
        if l["side"] == "crash":
            print("  급락 %s → %s %+.1f%% (확정 %s)" % (l["a"], l["b"], l["move"] * 100, l["confirm"]))
    for r in fz["rebounds"]:
        print("  반등 %s → %s %+.1f%% (%d거래일)" % (r["a"], r["b"], r["move"] * 100, r["td"]))
    print("  열린 다리 %s %s → %s %+.1f%% · 최신 판 확정 다리 %d" % (fz["open"]["side"], fz["open"]["a"], fz["open"]["b"], fz["open"]["move"] * 100, len(doc["current"]["legs"])))
    print("→ %s · 얼린 판 sha256 %s" % (OUT, doc["frozen_sha256"][:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
