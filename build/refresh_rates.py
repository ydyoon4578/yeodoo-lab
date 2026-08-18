# -*- coding: utf-8 -*-
"""build/refresh_rates.py — 금리 자료 + 금리 민감도 실측 → data/rates.json

왜 별도 탭인가.
  regime.html 이 이미 39지표를 보여 주고 그 안에 금리 7종이 있다. 그런데 그것은
  **현재값 스냅샷**이라 「지금 금리가 얼마다」까지만 답한다. 사용자가 묻는 것은
  그 다음이다 — 「금리가 올라서 시장이 안 좋다는데, 무엇이 얼마나 맞았나」.
  그 질문에는 **이력**과 **회귀**가 있어야 답한다.

🚨 자료 경로가 둘이 되지 않게 한다.
  regime.py 는 fredapi(키 필요)로, 여기는 FRED 공개 CSV(키 불필요)로 같은 계열을 받는다.
  두 경로가 갈리면 한 사이트가 두 숫자를 말한다. 그래서 **같은 날짜의 값이 같은지
  매 실행마다 대조하고, 다르면 멈춘다**(check_against_regime). 실측(2026-08-19):
  날짜를 맞추면 7종 7개 다 소수점까지 일치했다.
  ⚠ regime 이 하루 뒤진 값을 싣는 것은 버그가 아니다 — 그 잡이 06:56 KST 에 도는데
    그 시각엔 당일 H.15 가 아직 안 나와 있다. 그래서 «최신값» 이 아니라 «같은 날짜»로 댄다.

🚨 이 파일은 예측하지 않는다. 전부 **서술 통계**다. 베타는 「과거에 같이 움직인 정도」이지
  「금리가 오르면 이만큼 빠진다」가 아니다. 화면이 그 말을 그대로 적는다.

  python build/refresh_rates.py
"""
from __future__ import annotations
import csv
import io
import json
import os
import sys
import urllib.request

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "rates.json")
START = "2006-01-03"          # assets.json 과 같은 시작일 — 회귀 표본을 맞춘다

# (FRED 코드, 화면 이름, 묶음). 순서가 화면 순서다.
CODES = [
    ("DGS3MO",       "국채 3개월",        "curve"),
    ("DGS2",         "국채 2년",          "curve"),
    ("DGS10",        "국채 10년",         "curve"),
    ("DGS30",        "국채 30년",         "curve"),
    ("DFII10",       "10년 실질금리",      "decomp"),
    ("T10YIE",       "기대인플레(10Y)",    "decomp"),
    ("DFF",          "연방기금금리",       "policy"),
    ("MORTGAGE30US", "30년 모기지",       "policy"),
    ("BAMLH0A0HYM2", "하이일드 스프레드",   "credit"),
]
CURVE_PTS = [("DGS3MO", 0.25), ("DGS2", 2), ("DGS10", 10), ("DGS30", 30)]
FACTOR = "DGS10"              # 민감도를 재는 축


def fred(code):
    """FRED 공개 CSV — 키가 필요 없다. {날짜: 값}."""
    # ⚠ cosd 를 안 주면 계열마다 «기본 그래프 구간» 만 온다. 실측: BAMLH0A0HYM2 가
    #   785관측(2023-08~)만 왔다 — 1996년부터 있는 계열인데 3년치만 받고 있었다.
    url = ("https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s&cosd=1990-01-01" % code)
    for _ in range(3):
        try:
            txt = urllib.request.urlopen(url, timeout=60).read().decode("utf-8")
            break
        except Exception as e:
            print("  ⚠ %s 재시도 (%s)" % (code, str(e)[:50]))
            txt = None
    if txt is None:
        raise SystemExit("❌ FRED %s 를 못 받았다 — 추정치로 채우지 않는다." % code)
    out = {}
    rd = csv.reader(io.StringIO(txt))
    head = next(rd)
    for row in rd:
        if len(row) < 2:
            continue
        try:
            out[row[0]] = float(row[1])
        except Exception:
            pass          # '.' = 휴일. 채우지 않는다
    return out


def check_against_regime(S):
    """🚨 두 FRED 경로가 **같은 날짜에서** 같은 값을 주는지. 다르면 멈춘다."""
    p = os.path.join(DATA, "regime.json")
    if not os.path.exists(p):
        print("  ⚠ regime.json 없음 — 대조를 건너뛴다(통과가 아니라 미검증이다)")
        return
    reg = {s["k"]: s for s in json.load(io.open(p, encoding="utf-8"))["indicators"]}
    ok = miss = 0
    bad = []
    for code, _nm, _g in CODES:
        if code not in reg or code not in S:
            continue
        v, ser = reg[code]["v"], S[code]
        prev = (reg[code].get("sp") or {}).get("prev")
        ds = sorted(ser)
        # v 와 prev 가 **연속한 두 관측**으로 맞는 날짜를 찾는다
        hit = None
        for i in range(len(ds) - 1, max(len(ds) - 12, 0), -1):
            if abs(ser[ds[i]] - v) < 5e-3 and (prev is None or abs(ser[ds[i - 1]] - prev) < 5e-3):
                hit = ds[i]
                break
        if hit:
            ok += 1
        else:
            near = [(d, ser[d]) for d in ds[-4:]]
            bad.append((code, v, prev, near))
    if bad:
        for code, v, prev, near in bad:
            print("  🚨 %s regime=%s(prev %s) vs FRED 최근 %s" % (code, v, prev, near))
        raise SystemExit(
            "❌ regime.json 과 FRED 공개 CSV 가 **같은 날짜에서도 안 맞는다**(%d종). "
            "두 경로가 갈리면 사이트가 두 숫자를 말한다 — 손으로 확인할 것." % len(bad))
    print("  [대조] regime.json 과 날짜를 맞춰 %d종 일치 · 대조 못 한 것 %d" % (ok, miss))


def grid(S):
    """모든 계열을 하나의 날짜 격자에 올린다(값 없는 날은 None — 채우지 않는다).

    ⚠ 격자는 **DGS10 이 있는 날**(=미국 국채 영업일)로 잡는다. 모든 계열의 합집합으로
      잡으면 DFF 가 주말·휴일에도 값을 내보내서 격자가 7,533일로 부풀고(영업일은 약
      5,150일) 파일이 40% 커진다. 주말 칸은 이 화면이 쓰지도 않는다.
    """
    dates = sorted(d for d in S["DGS10"] if d >= START)
    cols = {code: [S[code].get(d) for d in dates] for code, _n, _g in CODES}
    return dates, cols


def last_at(dates, col, i=None):
    """가장 최근 (날짜, 값). 구멍을 앞으로 훑는다."""
    j = (len(dates) - 1) if i is None else i
    while j >= 0:
        if col[j] is not None:
            return dates[j], col[j]
        j -= 1
    return None, None


def back(dates, col, days):
    """대략 days 달력일 전의 (날짜, 값)."""
    import datetime as _dt
    tgt = (_dt.date.fromisoformat(dates[-1]) - _dt.timedelta(days=days)).isoformat()
    j = 0
    for k, d in enumerate(dates):
        if d <= tgt:
            j = k
    return last_at(dates, col, j)


def _nw_t(x, y, b, a, lag=5):
    """Newey-West(lag) t. 일간 회귀라 잔차에 자기상관이 있을 수 있다."""
    n = len(x)
    if n < 30:
        return None
    e = [y[i] - a - b * x[i] for i in range(n)]
    xm = sum(x) / n
    sxx = sum((v - xm) ** 2 for v in x)
    if sxx <= 0:
        return None
    u = [(x[i] - xm) * e[i] for i in range(n)]
    s = sum(v * v for v in u) / n
    for l in range(1, lag + 1):
        c = sum(u[i] * u[i - l] for i in range(l, n)) / n
        s += 2 * (1 - l / (lag + 1)) * c
    var = n * s / (sxx ** 2)
    if var <= 0:
        return None
    return b / (var ** 0.5)


def _ols(x, y):
    n = len(x)
    if n < 30:
        return None
    xm, ym = sum(x) / n, sum(y) / n
    sxx = sum((v - xm) ** 2 for v in x)
    if sxx <= 0:
        return None
    sxy = sum((x[i] - xm) * (y[i] - ym) for i in range(n))
    b = sxy / sxx
    a = ym - b * xm
    sst = sum((v - ym) ** 2 for v in y)
    ssr = sum((y[i] - a - b * x[i]) ** 2 for i in range(n))
    r2 = (1 - ssr / sst) if sst > 0 else None
    return b, a, r2, _nw_t(x, y, b, a), n


def sensitivity(dates, y10):
    """자산별 «10년물 하루 변화 10bp 당 수익률(%)».

    🚨 새 자료를 만들지 않는다 — data/assets.json(랩 자산 패널 정본)을 읽기만 한다.
    ⚠ 동시성 회귀다. 시차를 두지 않았고, 그래서 인과가 아니다(limits 에 적는다).
    """
    p = os.path.join(DATA, "assets.json")
    if not os.path.exists(p):
        print("  ⚠ assets.json 없음 — 민감도를 건너뛴다")
        return [], {}
    A = json.load(io.open(p, encoding="utf-8"))
    ad, apx, meta = A["dates"], A["px"], (A.get("meta") or {})
    ai = {d: i for i, d in enumerate(ad)}
    # 금리 격자 위에서 «전일 대비 bp 변화» 를 만든다(구멍은 건너뛴다)
    steps = []
    for i in range(1, len(dates)):
        a, b = y10[i - 1], y10[i]
        if a is None or b is None:
            continue
        steps.append((dates[i], round((b - a) * 100.0, 2)))     # %p → bp
    print("  [민감도] 금리 변화 관측 %d일 · 자산 %d종" % (len(steps), len(apx)))

    WIN = [("y1", 252), ("y5", 1260), ("all", 10 ** 9)]
    rows = []
    for t, px in apx.items():
        m = meta.get(t) or {}
        pair = []
        for d, dy in steps:
            j = ai.get(d)
            if j is None or j == 0:
                continue
            p0, p1 = px[j - 1], px[j]
            if not p0 or not p1:
                continue
            pair.append((dy, (p1 / p0 - 1) * 100.0))
        if len(pair) < 60:
            continue
        row = {"t": t, "nm": m.get("desc") or t, "cat": m.get("cat") or "?"}
        for lab, w in WIN:
            sub = pair[-w:] if w < len(pair) else pair
            r = _ols([v[0] for v in sub], [v[1] for v in sub])
            if not r:
                row["b_" + lab] = None
                continue
            b, _a, r2, tt, n = r
            row["b_" + lab] = round(b * 10.0, 4)          # 10bp 당 %
            row["t_" + lab] = (None if tt is None else round(tt, 2))
            row["r2_" + lab] = (None if r2 is None else round(r2, 4))
            row["n_" + lab] = n
        rows.append(row)
    rows.sort(key=lambda r: (r.get("b_y1") is None, r.get("b_y1") or 0))

    # 금리 급등일 — 최근 5년에서 상위 10%
    recent = steps[-1260:] if len(steps) > 1260 else steps
    ups = sorted(v[1] for v in recent)
    cut = ups[int(len(ups) * 0.90)] if ups else 0
    days = set(d for d, dy in recent if dy >= cut)
    sp = []
    for t, px in apx.items():
        m = meta.get(t) or {}
        vs = []
        for d in days:
            j = ai.get(d)
            if j is None or j == 0:
                continue
            p0, p1 = px[j - 1], px[j]
            if p0 and p1:
                vs.append((p1 / p0 - 1) * 100.0)
        if len(vs) >= 20:
            sp.append({"t": t, "nm": m.get("desc") or t, "cat": m.get("cat") or "?",
                       "mean": round(sum(vs) / len(vs), 4), "n": len(vs)})
    sp.sort(key=lambda r: r["mean"])
    spike = {"cut_bp": round(cut, 2), "n_days": len(days),
             "win": "최근 %d거래일" % len(recent), "rows": sp}
    print("  [급등일] 기준 +%.1fbp 이상 · %d일 · 자산 %d종" % (cut, len(days), len(sp)))
    return rows, spike


# ── 겹쳐 볼 자산 — data/rates_overlay.json ──────────────────────────────────
# 왜 따로 파나(2026-08-19 사용자 요청 · "금리 차트랑 S&P500·나스닥100·섹터 ETF 를 같이").
#   화면이 금리 위에 자산을 겹치려면 자산 일간 계열이 필요한데, 그것이 지금
#   assets.json(4.6MB) 안에만 있다. 각주 한 줄 때문에 4MB 를 받던 홈의 사고(2026-08-14)와
#   같은 자리라, 화면이 통째로 받게 두지 않는다. rates.json 에 넣지 않는 이유도 같다 —
#   그 파일은 금리 이력이고 312KB 인데 여기에 13계열을 더하면 두 배가 된다.
#
# 🚨 기준을 하나로 맞춘다 — **전부 ETF 수정종가**(SPY·QQQ·XL*)다.
#   랩의 벤치마크 정본은 지수 PR(^GSPC·^NDX)이지만, 여기서 그것을 쓰면 섹터 ETF(배당
#   재투자 반영)와 지수 PR(배당 없음)을 한 그림에 겹치게 된다 — 연 2%p 짜리 가짜 격차가
#   섹터 쪽에 붙어 «섹터가 지수를 이겼다» 처럼 보인다. 이 화면은 전략을 채점하는 곳이
#   아니라 서로 견주는 곳이므로, 한 바구니 안에서 기준을 통일하는 쪽이 옳다.
#   ⚠ 그 사실을 화면이 적어야 한다(rates.html 겹쳐보기 각주).
# ⚠ XLRE 는 2015-10, XLC 는 2018-06 부터다. 없는 구간은 None 으로 두고 화면이
#   그 구간을 안 그린다 — 0 이나 앞값으로 메우면 «그때도 있었다» 는 거짓이 된다.
OVERLAY = [
    ("SPY",  "S&P 500",      "지수"),
    ("QQQ",  "나스닥 100",    "지수"),
    ("XLK",  "기술",          "섹터"),
    ("XLC",  "커뮤니케이션",   "섹터"),
    ("XLY",  "경기소비",      "섹터"),
    ("XLP",  "필수소비",      "섹터"),
    ("XLE",  "에너지",        "섹터"),
    ("XLF",  "금융",          "섹터"),
    ("XLV",  "헬스케어",      "섹터"),
    ("XLI",  "산업재",        "섹터"),
    ("XLB",  "소재",          "섹터"),
    ("XLRE", "부동산",        "섹터"),
    ("XLU",  "유틸리티",      "섹터"),
]
OVL_OUT = os.path.join(DATA, "rates_overlay.json")


def write_overlay(dates):
    """금리 격자에 맞춘 자산 종가를 얇게 뽑는다 → data/rates_overlay.json.

    ⚠ **금리 격자 위로 옮긴다.** 화면이 두 격자를 맞추게 두면 맞추는 규약이 두 곳이 되고,
      이 랩은 그 유형의 사고를 여러 번 밟았다. 자산에 그 날짜가 없으면 None 이다.
    """
    p = os.path.join(DATA, "assets.json")
    if not os.path.exists(p):
        print("  ⚠ assets.json 없음 — 겹쳐보기 계열을 건너뛴다(이전본 유지)")
        return
    A = json.load(io.open(p, encoding="utf-8"))
    ai = {d: i for i, d in enumerate(A["dates"])}
    apx = A["px"]
    out, miss = {}, []
    for t, nm, cat in OVERLAY:
        a = apx.get(t)
        if not a:
            miss.append(t)
            continue
        arr = []
        for d in dates:
            j = ai.get(d)
            v = None if j is None else a[j]
            arr.append(None if v is None else round(float(v), 2))
        first = next((dates[i] for i, v in enumerate(arr) if v is not None), None)
        out[t] = {"nm": nm, "cat": cat, "first": first,
                  "n": sum(1 for v in arr if v is not None), "px": arr}
    if miss:
        print("  ⚠ 겹쳐보기에서 빠진 티커: %s" % " · ".join(miss))
    doc = {
        "note": "금리 화면이 금리 위에 겹쳐 그리는 자산 종가. 금리 격자(rates.json.dates)에 "
                "맞춰 옮겨 담았다 — 화면이 격자를 맞추지 않게 하려고.",
        "basis": "전부 ETF 수정종가(배당 재투자 반영). 랩 벤치마크 정본인 지수 PR"
                 "(^GSPC·^NDX)과 다른 계열이다 — 섹터 ETF 와 한 그림에 겹치므로 "
                 "바구니 안에서 기준을 통일했다.",
        "as_of": dates[-1], "start": dates[0], "n": len(dates),
        "series": out,
    }
    io.open(OVL_OUT, "w", encoding="utf-8", newline="").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10))
    print("  → %s · %d계열 · %.0fKB"
          % (os.path.relpath(OVL_OUT, ROOT), len(out), os.path.getsize(OVL_OUT) / 1024))


def main() -> int:
    print("FRED 공개 CSV %d계열 받는 중…" % len(CODES))
    S = {}
    for code, nm, _g in CODES:
        S[code] = fred(code)
        d = sorted(S[code])
        print("  %-14s %5d관측 · %s ~ %s" % (code, len(d), d[0], d[-1]))
    check_against_regime(S)

    dates, cols = grid(S)
    print("  격자 %d일 (%s ~ %s)" % (len(dates), dates[0], dates[-1]))

    # ── 수준·변화 ──────────────────────────────────────────────────────
    levels = []
    for code, nm, g in CODES:
        d0, v0 = last_at(dates, cols[code])
        row = {"k": code, "nm": nm, "g": g, "v": v0, "d": d0}
        for lab, nd in (("m1", 30), ("m3", 91), ("y1", 365), ("y3", 1095)):
            _d, _v = back(dates, cols[code], nd)
            row[lab] = (None if (_v is None or v0 is None) else round(v0 - _v, 3))
        levels.append(row)

    # ── 곡선(현재·1개월·1년 전) ─────────────────────────────────────────
    def curve_at(nd):
        out = []
        for code, yrs in CURVE_PTS:
            _d, _v = (last_at(dates, cols[code]) if nd == 0 else back(dates, cols[code], nd))
            out.append({"k": code, "yrs": yrs, "v": _v, "d": _d})
        return out
    curve = {"now": curve_at(0), "m1": curve_at(30), "m3": curve_at(91), "y1": curve_at(365)}

    sens, spike = sensitivity(dates, cols[FACTOR])
    write_overlay(dates)

    doc = {
        "note": "금리 이력과 금리 민감도. FRED 공개 CSV(키 불필요) + data/assets.json. "
                "🚨 전부 서술 통계다 — 예측이 아니다.",
        "generated": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": last_at(dates, cols["DGS10"])[0],
        "start": dates[0],
        "n_days": len(dates),
        "factor": FACTOR,
        # 계열마다 FRED 가 주는 구간이 다르다(실측: BAMLH0A0HYM2 는 2023-08 부터만 온다).
        # 화면이 «이 선은 언제부터인가» 를 말할 수 있게 계열별 시작일을 싣는다.
        "codes": [{"k": c, "nm": n, "g": g,
                   "start": (sorted(S[c])[0] if S[c] else None),
                   "n": len(S[c])} for c, n, g in CODES],
        "dates": dates,
        "series": {c: cols[c] for c, _n, _g in CODES},
        "levels": levels,
        "curve": curve,
        "sens": sens,
        "spike": spike,
        "limits": [
            "🚨 여기 수는 **서술 통계**다. 베타는 「과거에 같이 움직인 정도」이지 "
            "「금리가 오르면 이만큼 빠진다」가 아니다. 인과를 말하지 않는다.",
            "⚠ 금리와 주가는 **같은 뉴스에 함께 반응**한다. 어느 쪽이 원인인지 이 회귀는 "
            "가르지 못한다(동시성 회귀다 — 시차를 두지 않았다).",
            "⚠ 베타는 창에 따라 크게 바뀐다. 1년·5년·전체를 **나란히** 싣는 이유다. "
            "하나만 보고 「이 섹터는 금리에 이만큼 민감하다」고 말할 수 없다.",
            "⚠ 자산은 ETF 다. 보수·추적오차가 섞이고, 상장 전 구간은 없다(계열마다 표본이 다르다).",
            "⚠ 금리 급등일 성과는 **그날 하루** 평균이다. 며칠에 걸친 반응은 안 잡힌다.",
        ],
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    print("  → rates.json · %s 기준 · %.0fKB" % (doc["as_of"], os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
