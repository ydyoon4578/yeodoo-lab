# -*- coding: utf-8 -*-
"""build/intraday_backtest.py — 장중(1일) 규칙 6종 측정 → data/intraday_strategies.json

명세는 `PREREG-2026-08-17-INTRADAY6.md` 다. 이 파일은 그 등록서를 옮긴 것이고,
등록에 없는 규칙·구간·바스켓을 여기서 만들지 않는다.

🚨 **판정을 만들지 않는다.** 표본이 60거래일이다. 「통과/유효」라는 말을 산출물에 안 쓴다 —
  잰 값과 표본 크기를 적고, 읽는 사람이 그 둘을 같이 보게 한다.

🚨 대조군은 지수가 아니라 **그날 안 고른 것**(같은 구간·같은 날 후보 전체 동일가중)이다.
  지수를 대면 「종목을 골랐나」가 아니라 「그 구간이 좋았나」를 재게 된다.

  python build/intraday_backtest.py
"""
from __future__ import annotations
import io
import json
import math
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
HIST = os.path.join(DATA, "intraday_hist.json")
OUT = os.path.join(DATA, "intraday_strategies.json")

TOPN = 10           # 등록서 §2 — 바스켓
VOL_WIN = 20        # 등록서 §2⑤ — 거래량 중앙값 창
COSTS = [0, 5, 10, 20]   # 등록서 §4 — 왕복 bp
MIN_POOL = 100      # 후보가 이보다 적은 날은 그 규칙을 쉰다

# ⚠ gap 은 2026-08-18 에 **끝에** 붙였다. 옛 행은 6칸이라 길이로 가른다 —
#   자리로만 읽으면 6칸 행에서 IndexError 가 나거나(운이 좋으면) 조용히 다른 값을 집는다.
F = {"r": 0, "r_open": 1, "r_close": 2, "clv": 3, "vs_vwap": 4, "v": 5, "gap": 6}


def fv(row, key):
    """행에서 필드 하나. 그 행에 그 칸이 없으면 None(옛 스키마 대비)."""
    i = F[key]
    return row[i] if (row is not None and len(row) > i) else None


def med(a):
    b = sorted(a)
    n = len(b)
    return None if not n else (b[n // 2] if n % 2 else 0.5 * (b[n // 2 - 1] + b[n // 2]))


def tstat(xs):
    """평균의 t. 표본이 작을수록 이 수가 무엇을 못 말하는지가 커진다 — 결과서가 그걸 적는다."""
    n = len(xs)
    if n < 3:
        return None
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return None if v <= 0 else m / math.sqrt(v / n)


def load():
    H = json.load(io.open(HIST, encoding="utf-8"))
    days = sorted(H["days"])
    return H, days


def day_ret(row, kind):
    """그 종목의 그날 매매 구간 수익(%).

    ⚠ 당일형은 10:00→종가다. 저장값으로 만든다: (1+r)/(1+r_open) − 1.
      근사가 아니라 항등식이다(둘 다 그날 시가 기준이므로).
    """
    r, ro = row[F["r"]], row[F["r_open"]]
    if kind == "same":
        if r is None or ro is None or (1 + ro / 100.0) == 0:
            return None
        return ((1 + r / 100.0) / (1 + ro / 100.0) - 1) * 100.0
    return r          # 익일형·갭형은 그날 시가→종가


def run_rule(H, days, sid, spec):
    """한 규칙을 하루씩 돌린다 → 일별 (전략 수익, 대조군 수익)."""
    kind = spec["kind"]                 # same | next
    rows = []
    for i, d in enumerate(days):
        D = H["days"][d]
        # 신호를 어느 날에서 읽나 — 당일형은 오늘, 익일형은 어제
        if kind in ("same", "gap"):
            sig_day, trade_day = d, d
        else:
            if i == 0:
                continue
            sig_day, trade_day = days[i - 1], d
        S, T = H["days"][sig_day], H["days"][trade_day]
        # 후보 — 신호와 매매 둘 다 값이 있어야 한다
        cand = []
        for t, sr in S.items():
            tr = T.get(t)
            if tr is None:
                continue
            rr = day_ret(tr, kind)
            if rr is None:
                continue
            sc = spec["score"](t, sr, S, days, i, H)
            if sc is None:
                continue
            cand.append((sc, t, rr))
        if len(cand) < MIN_POOL:
            continue
        cand.sort(reverse=spec.get("desc", True))
        pick = cand[:TOPN]
        bench = sum(c[2] for c in cand) / len(cand)      # 그날 안 고른 것
        rows.append((trade_day, sum(p[2] for p in pick) / len(pick), bench,
                     [p[1] for p in pick]))
    return rows


def volmed_at(t, days, i, H):
    """직전 VOL_WIN 일 거래량 중앙값. 없으면 None(그 종목은 그날 후보에서 빠진다)."""
    vs = []
    for j in range(max(0, i - VOL_WIN), i):
        row = H["days"][days[j]].get(t)
        if row and row[F["v"]]:
            vs.append(row[F["v"]])
    return med(vs) if len(vs) >= VOL_WIN // 2 else None


def build_specs():
    """등록서 §2 의 여섯. 순서를 바꾸지 않는다."""
    def s_open(t, sr, S, days, i, H):
        return sr[F["r_open"]]

    def s_vwap(t, sr, S, days, i, H):
        return sr[F["vs_vwap"]]

    def s_clv(t, sr, S, days, i, H):
        return sr[F["clv"]]

    def s_vsurge(t, sr, S, days, i, H):
        m = volmed_at(t, days, i, H)
        v = sr[F["v"]]
        return None if (not m or not v) else v / m

    def s_openvol(t, sr, S, days, i, H):
        # 그날 거래량이 중앙값 위인 종목만 후보. 중앙값은 **그날 단면**에서 낸다.
        vs = [x[F["v"]] for x in S.values() if x[F["v"]]]
        mv = med(vs)
        v = sr[F["v"]]
        if not mv or not v or v <= mv:
            return None
        return sr[F["r_open"]]

    # ── 갭 5종 — 사전등록 PREREG-2026-08-18-GAP5.md §3 ────────────────
    # 매매는 전부 «그날 시가 진입 · 종가 청산» 이라 수익이 곧 r 이다 → kind="same" 이
    # 아니라 별도 갈래가 필요하다: 신호도 그날, 수익도 그날 r(10:00→종가가 아니다).
    def s_gap(t, sr, S, days, i, H):
        return fv(sr, "gap")

    def s_gapvol(t, sr, S, days, i, H):
        g = fv(sr, "gap")
        if g is None:
            return None
        vs = [fv(x, "v") for x in S.values() if fv(x, "v")]
        mv = med(vs)
        v = fv(sr, "v")
        return None if (not mv or not v or v <= mv) else g

    def s_absgap(t, sr, S, days, i, H):
        g = fv(sr, "gap")
        return None if g is None else abs(g)

    return [
        ("g-up", {"kind": "gap", "score": s_gap, "desc": True,
                  "name": "갭 상승 상위 %d" % TOPN,
                  "rule": "전일 종가 대비 시가가 가장 높은 %d종을 그날 시가에 사서 종가에 "
                          "판다. 동일가중." % TOPN,
                  "why": "「갭은 이어진다(gap-and-go)」는 실무 통념. 이 랩이 검증한 적 없다."}),
        ("g-down", {"kind": "gap", "score": s_gap, "desc": False,
                    "name": "갭 하락 하위 %d" % TOPN,
                    "rule": "전일 종가 대비 시가가 가장 낮은 %d종을 그날 시가에 사서 종가에 "
                            "판다." % TOPN,
                    "why": "①의 반대 끝. 한쪽만 재면 부호를 결과 보고 정하게 된다. "
                           "「갭 메우기」 통념이 맞다면 이쪽이 낫다."}),
        ("g-up-vol", {"kind": "gap", "score": s_gapvol, "desc": True,
                      "name": "갭 상승 상위 %d (거래량 확인)" % TOPN,
                      "rule": "그날 거래량이 단면 중앙값 위인 종목만 후보로 두고 갭 상위 %d종."
                              % TOPN,
                      "why": "「거래량 없는 갭은 못 믿는다」는 통념. ①과의 차이가 곧 그 값어치다."}),
        ("g-fade", {"kind": "gap", "score": s_absgap, "desc": True,
                    "name": "갭 절대값 상위 %d" % TOPN,
                    "rule": "방향을 안 보고 |갭| 이 가장 큰 %d종." % TOPN,
                    "why": "🚨 앞 배치(INTRADAY6)에서 깨진 예측을 정면으로 잰다 — 개장 30분 "
                           "강세·약세가 «둘 다» 졌고 「진 것은 방향이 아니라 변동성 자체」라는 "
                           "가설이 나왔다. 이것도 지면 가설이 서고, 이것만 이기면 깨진다."}),
        ("g-none", {"kind": "gap", "score": s_absgap, "desc": False,
                    "name": "갭 절대값 하위 %d" % TOPN,
                    "rule": "|갭| 이 가장 작은 %d종." % TOPN,
                    "why": "④의 반대 끝. 「조용한 종목이 낫다」가 이 표본에서 서는지 본다."}),
        ("d-openmom", {"kind": "same", "score": s_open, "desc": True,
                       "name": "개장 30분 강세 상위 %d" % TOPN,
                       "rule": "개장 30분 수익 상위 %d종을 10:00 에 사서 종가에 판다. 동일가중." % TOPN,
                       "why": "이 랩의 모멘텀은 전부 일간 이상이다. 「하루 안에서도 강한 것이 "
                              "계속 강한가」를 한 번도 안 물었다."}),
        ("d-openrev", {"kind": "same", "score": s_open, "desc": False,
                       "name": "개장 30분 약세 하위 %d" % TOPN,
                       "rule": "개장 30분 수익 하위 %d종을 10:00 에 사서 종가에 판다. 동일가중." % TOPN,
                       "why": "①과 같은 축의 반대 끝. 둘을 같이 재야 「축이 작동하나」와 "
                              "「방향이 무엇이냐」가 갈린다 — 한쪽만 재면 부호를 결과 보고 정하게 된다."}),
        ("d-vwapclose", {"kind": "next", "score": s_vwap, "desc": True,
                         "name": "종가가 VWAP 위 상위 %d" % TOPN,
                         "rule": "전일 종가가 그날 VWAP 대비 높은 상위 %d종을 다음 날 시가에 "
                                 "사서 종가에 판다." % TOPN,
                         "why": "VWAP 위 마감은 실무에서 널리 쓰이는데 이 랩에 VWAP 을 쓰는 "
                                "규칙이 없었다."}),
        ("d-clv", {"kind": "next", "score": s_clv, "desc": True,
                   "name": "종가 위치 상위 %d" % TOPN,
                   "rule": "전일 종가가 그날 고저 범위의 위쪽에 놓인 상위 %d종을 다음 날 "
                           "시가에 사서 종가에 판다." % TOPN,
                   "why": "③과 분모가 다르다 — 이건 범위 대비, ③은 거래량가중 평균 대비다. "
                          "거래가 아침에 몰린 날 둘은 정반대가 될 수 있다."}),
        ("d-volsurge", {"kind": "next", "score": s_vsurge, "desc": True,
                        "name": "거래량 급증 상위 %d" % TOPN,
                        "rule": "전일 거래량 ÷ 직전 %d거래일 중앙값 상위 %d종을 다음 날 "
                                "시가에 사서 종가에 판다." % (VOL_WIN, TOPN),
                        "why": "이 배치에서 유일하게 가격이 아닌 축이다. ⚠ 중앙값 창 때문에 "
                               "이 규칙만 표본이 짧다."}),
        ("d-openmom-vol", {"kind": "same", "score": s_openvol, "desc": True,
                           "name": "개장 30분 강세 상위 %d (거래량 확인)" % TOPN,
                           "rule": "그날 거래량이 단면 중앙값 위인 종목만 후보로 두고 개장 "
                                   "30분 수익 상위 %d종을 10:00 에 사서 종가에 판다." % TOPN,
                           "why": "①과의 차이가 곧 「거래량 확인이 값어치가 있나」다. 신호와 "
                                  "매매가 같으므로 다른 것이 섞이지 않는다."}),
    ]


def main() -> int:
    if not os.path.exists(HIST):
        print("❌ %s 없음 — build/refresh_intraday.py 를 먼저 돌릴 것" % HIST)
        return 1
    H, days = load()
    print("장중 이력 %d거래일 · %s ~ %s" % (len(days), days[0], days[-1]))
    out = []
    for sid, spec in build_specs():
        rows = run_rule(H, days, sid, spec)
        if len(rows) < 10:
            print("  ⚠ %-15s 매매일 %d — 너무 적어 싣지 않는다" % (sid, len(rows)))
            continue
        ex = [r[1] - r[2] for r in rows]
        st = [r[1] for r in rows]
        bn = [r[2] for r in rows]
        n = len(rows)
        # 회전 — 매일 갈아탄다고 보고 전날 바스켓과의 교체율을 센다.
        turns = []
        for k in range(1, n):
            a, b = set(rows[k - 1][3]), set(rows[k][3])
            turns.append(len(a ^ b) / (len(a) + len(b)))
        tr = sum(turns) / len(turns) if turns else 1.0
        # 비용 — 왕복 bp × 그날 교체율. 등록서 §4.
        net = {}
        for c in COSTS:
            drag = [(c / 100.0) * (turns[k - 1] if k else 1.0) for k in range(n)]
            net[str(c)] = {
                "mean": round(sum(e - d for e, d in zip(ex, drag)) / n, 4),
                "ann": round((sum(e - d for e, d in zip(ex, drag)) / n) * 252, 2),
            }
        rec = {
            "sid": sid, "name": spec["name"], "rule": spec["rule"], "why": spec["why"],
            "kind": spec["kind"],
            "n_days": n, "start": rows[0][0], "end": rows[-1][0],
            "mean": round(sum(st) / n, 4), "bench_mean": round(sum(bn) / n, 4),
            "excess": round(sum(ex) / n, 4),
            "excess_ann": round((sum(ex) / n) * 252, 2),
            "t": None if tstat(ex) is None else round(tstat(ex), 2),
            "win": round(100.0 * sum(1 for e in ex if e > 0) / n, 1),
            "turnover": round(tr, 3),
            "net": net,
            "holdings": {"as_of": rows[-1][0], "tickers": sorted(rows[-1][3])},
        }
        out.append(rec)
        print("  %-15s %3d일 · 전략 %+6.3f%%/일 · 대조 %+6.3f · 초과 %+6.3f (t %5s) · "
              "승률 %4.1f%% · 회전 %.2f"
              % (sid, n, rec["mean"], rec["bench_mean"], rec["excess"],
                 rec["t"], rec["win"], tr))

    doc = {
        "note": "장중(1일) 규칙 — 사전등록 PREREG-2026-08-17-INTRADAY6.md. 대조군은 지수가 "
                "아니라 그날 후보 전체 동일가중이다(같은 구간·같은 날).",
        "generated": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": days[-1],
        "n_days_avail": len(days),
        "topn": TOPN,
        "limits": [
            "🚨 표본이 %d거래일(%s ~ %s)이다. 이 랩은 10년·120개월짜리에도 «판정 불가» 를 "
            "적어 왔다 — 60일로 무엇이 통했다고 말할 수 없다. 이 표는 «지금 답» 이 아니라 "
            "«나중에 답하려고 규칙을 미리 못박아 둔 것» 이다(등록서 §0)."
            % (len(days), days[0], days[-1]),
            "🚨 일간 회전이다. 왕복 10bp 면 연 25%p 가 깎인다 — 무비용 열만 보면 안 된다. "
            "왕복 5·10·20bp 를 나란히 실었다.",
            "⚠ 한 국면이다(2026-05~08). 시장이 한 방향이면 당일 모멘텀은 자동으로 좋아 보인다.",
            "⚠ 체결을 가정한다. 10:00 진입은 그 시점 5분봉 종가로 잡는다 — 실제 체결가·"
            "슬리피지·호가 스프레드는 이 자료에 없다. 소형주일수록 이 가정이 헐겁다.",
            "⚠ 밤샘(오버나이트) 수익을 안 본다. 전일 종가→익일 시가 갭을 안 저장하기 "
            "때문이고, 못 재는 것을 규칙으로 만들지 않았다(등록서 §1).",
            "⚠ 생존편향을 안 잰다. 후보가 오늘의 518종이고 60일 창에는 편출이 사실상 없다 — "
            "없는 것을 잰 척하지 않는다.",
            "⚠ t 에 선을 긋지 않는다(2026-08-17 결정). 잰 값과 표본 크기를 같이 읽을 것.",
        ],
        "n": len(out),
        "strategies": out,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("\n→ %s · %d종 · %.0fKB" % (os.path.relpath(OUT, ROOT), len(out),
                                      os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
