# -*- coding: utf-8 -*-
"""build/eg_best_pdf.py — EGBEST 선택 결과 → 펀드 전략 리포트 **한 편**(차트 포함) · 저장소 밖 C:/Project/fund_reports/

자료는 data/_eg_best.json(뽑힌 전략 · 후보 · 섞기)과 data/_fund_mix.json(정리한 전략들의 펀드 틀 성과)뿐이다 —
저장된 계열을 다시 묶어 보여 줄 뿐 새 검정을 하지 않는다(이동 평균·낙폭·상승/하락 월 같은 서술 통계만 낸다).
차트는 인라인 SVG(인쇄용 정적). HTML 을 짓고 Chrome 헤드리스로 PDF 를 찍는다. 🚨 PDF 는 «내부용» 이라 저장소에 넣지 않는다.

숫자 규칙 — 소수점은 **둘째 자리까지만**(사용자 지시 2026-09-24). 급락·급등 구간은 따로 묶는다(같은 지시).
색 — dataviz 기준 팔레트(라이트 · 인쇄). 계열 1~4 는 검증기 통과(인접 CVD ΔE ≥ 9.1) · 3·4번은 3:1 미만이라 끝점 라벨+범례를 같이 단다.

  python build/eg_best_pdf.py [자료.json]
"""
from __future__ import annotations
import html, io, json, math, os, subprocess, sys

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "_eg_best.json")
MIX = os.path.join(ROOT, "data", "_fund_mix.json")
OUTDIR = os.environ.get("FUND_REPORT_DIR", r"C:\Project\fund_reports")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DATE = "2026-09-24"
R3 = "2023-09"
COL = {"s1": "#2a78d6", "s2": "#eb6834", "s3": "#1baf7a", "s4": "#eda100", "neg": "#e34948", "pos": "#2a78d6",
       "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7", "surf": "#fcfcfb"}
EG_DEF = ("다음 해 투자증가율 예측값(Eg) — 시장가치÷자산 · 현금 기준 영업이익÷자산 · ROE 변화 셋에 과거 120개월 회귀계수 평균을 곱해 더한 값"
          " · 재무는 분기말 90일 뒤부터")
META = {
 "EG_BASE": {"title": "S&P500 기대성장(Eg) 상위 30", "file": "EG30",
             "select": "Eg 상위 30개 회사",
             "steps": [("Eg", EG_DEF, "점수"), ("선정", "Eg 상위 30개 회사", "30개")]},
 "C1": {"title": "S&P500 기대성장·모멘텀 30", "file": "EG모멘텀30",
        "select": "⅔ × Eg 백분위 + ⅓ × 12-1 모멘텀 백분위 상위 30개 회사",
        "steps": [("Eg", EG_DEF + " → 백분위", "0~1"), ("모멘텀", "최근 252거래일 수익 − 최근 21거래일 수익(형성일 값) → 백분위", "0~1"),
                  ("통합", "⅔ × Eg + ⅓ × 모멘텀 — 두 점수가 다 선 회사만", "—"), ("선정", "통합 점수 상위 30개 회사", "30개")]},
 "C2": {"title": "S&P500 기대성장 30 · 모멘텀 거르기", "file": "EG30_모멘텀거르기",
        "select": "Eg 상위 45개 중 12-1 모멘텀 하위 15개를 뺀 30개 회사",
        "steps": [("Eg", EG_DEF, "점수"), ("후보", "Eg 상위 45개", "45개"),
                  ("거르기", "그중 12-1 모멘텀(252일 − 21일 수익) 하위 15개 제외(모멘텀이 없는 회사를 먼저)", "30개")]},
}
SECKO = {"Information Technology": "IT", "Health Care": "헬스케어", "Financials": "금융", "Consumer Discretionary": "경기소비재",
         "Communication Services": "커뮤니케이션", "Industrials": "산업재", "Consumer Staples": "필수소비재", "Energy": "에너지",
         "Utilities": "유틸리티", "Real Estate": "부동산", "Materials": "소재"}
MIXT = {"P_M": "EG30 ½ + 모멘텀 상위 10 ½", "P_B": "EG30 ½ + B/M 로테이션 ½", "P_A": "EG30 ½ + 알파 개선 10 ½", "P_Q": "EG30 ½ + 우량성장 30 ½"}
OLD = [("Q", "우량성장선별 30 (ROE + Eg · 6개월 평활 · 랩 판)"), ("C", "조합 (B/M · Eg · 모멘텀 1/3씩)"), ("M", "12-1 모멘텀 상위 10"),
       ("A", "알파 개선 상위 10"), ("B", "B/M 금리 국면 로테이션")]


# ── 숫자(소수 둘째 자리까지) ────────────────────────────────────────────────
def pct(v, d=2, sign=True):
    if v is None or v != v:
        return "—"
    return (("%+." if sign else "%.") + str(min(d, 2)) + "f%%") % v


def pp(v, d=2):
    return "—" if v is None or v != v else ("%+." + str(min(d, 2)) + "f%%p") % v


def num(v, d=2):
    return "—" if v is None or v != v else ("%." + str(min(d, 2)) + "f") % v


def esc(s):
    return html.escape(str(s))


# ── SVG 차트(정적) ────────────────────────────────────────────────────────
def nice_ticks(lo, hi, n=5):
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    a = math.floor(lo / step + 1e-9) * step
    b = math.ceil(hi / step - 1e-9) * step
    out, x = [], a
    while x <= b + step * 1e-6:
        out.append(round(x, 10))
        x += step
    return out


def tick_label(v, unit):
    whole = abs(v - round(v)) < 1e-9
    body = ("%.0f" if whole else ("%.1f" if abs(v * 10 - round(v * 10)) < 1e-9 else "%.2f")) % v
    return body + ("%" if unit == "%" else "")


def _text(x, y, s, anchor="start", size=9, fill=None, weight=400):
    return '<text x="%.1f" y="%.1f" text-anchor="%s" font-size="%d" fill="%s" font-weight="%d">%s</text>' % (
        x, y, anchor, size, fill or COL["muted"], weight, esc(s))


def _svg(w, h):
    return '<svg viewBox="0 0 %d %d" width="100%%" xmlns="http://www.w3.org/2000/svg" font-family="Malgun Gothic, sans-serif">' % (w, h)


def line_chart(series, x_labels, unit="%", w=680, h=210, zero=None, area=None, legend=True, end_labels=True, vline=None):
    """series: [{"name", "short", "y", "color", "fmt"}] 같은 x 격자 · x_labels: [(인덱스, 글)] · zero: 기준선 · area: 면을 칠할 계열 이름."""
    L, R, T, B = 46, (96 if end_labels else 14), 10, 24
    n = max(len(s["y"]) for s in series)
    ys = [v for s in series for v in s["y"] if v is not None and v == v]
    ext = ys + ([zero] if zero is not None else [])
    lo, hi = min(ext), max(ext)
    pad = (hi - lo) * 0.06 or 1
    tk = nice_ticks(lo - pad, hi + pad)
    y0, y1 = tk[0], tk[-1]
    X = lambda i: L + (w - L - R) * (i / max(1, n - 1))
    Y = lambda v: T + (h - T - B) * (1 - (v - y0) / (y1 - y0))
    o = [_svg(w, h)]
    for v in tk:
        o.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (L, w - R, Y(v), Y(v), COL["grid"]))
        o.append(_text(L - 6, Y(v) + 3, tick_label(v, unit), "end", 8))
    if zero is not None:
        o.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (L, w - R, Y(zero), Y(zero), COL["axis"]))
    for i, lab in x_labels:
        o.append(_text(X(i), h - 8, lab, "middle", 8))
    if vline is not None:
        i, lab = vline
        o.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="%s" stroke-width="1"/>' % (X(i), X(i), T, h - B, COL["axis"]))
        o.append(_text(X(i) + 4, T + 9, lab, "start", 8, COL["ink2"]))
    ends = []
    for s in series:
        pts = [(X(i), Y(v)) for i, v in enumerate(s["y"]) if v is not None and v == v]
        if not pts:
            continue
        if area == s["name"]:
            base = Y(zero if zero is not None else y0)
            o.append('<path d="M%.1f %.1f L%s L%.1f %.1f Z" fill="%s" fill-opacity="0.10" stroke="none"/>' % (
                pts[0][0], base, " L".join("%.1f %.1f" % p for p in pts), pts[-1][0], base, s["color"]))
        o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>' % (
            " ".join("%.1f,%.1f" % p for p in pts), s["color"]))
        o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s" stroke="%s" stroke-width="2"/>' % (pts[-1][0], pts[-1][1], s["color"], COL["surf"]))
        last = [v for v in s["y"] if v is not None and v == v][-1]
        ends.append({"y": pts[-1][1], "ly": pts[-1][1], "s": s, "v": last})
    if end_labels:
        ends.sort(key=lambda e: e["y"])
        for k in range(1, len(ends)):                  # 겹치면 아래로 벌리고 리더선으로 잇는다
            if ends[k]["ly"] - ends[k - 1]["ly"] < 11:
                ends[k]["ly"] = ends[k - 1]["ly"] + 11
        for e in ends:
            if abs(e["ly"] - e["y"]) > 0.5:
                o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (w - R + 5, w - R + 9, e["y"], e["ly"], COL["axis"]))
            f = e["s"].get("fmt") or (lambda v: tick_label(v, unit))
            o.append(_text(w - R + 11, e["ly"] + 3, "%s %s" % (e["s"].get("short", e["s"]["name"]), f(e["v"])), "start", 8, COL["ink2"]))
    o.append("</svg>")
    lg = ""
    if legend and len(series) >= 2:
        lg = '<div class="lg">' + "".join('<span><i style="background:%s"></i>%s</span>' % (s["color"], esc(s["name"])) for s in series) + "</div>"
    return lg + "".join(o)


def _vbar(x, y_base, y_end, bw, r=4):
    """세로 막대 — 데이터 끝만 4px 둥글게, 기준선 쪽은 각지게."""
    hgt = abs(y_base - y_end)
    r = min(r, hgt, bw / 2)
    s = -1 if y_end < y_base else 1                  # 위로 자라면 −1
    return "M%.1f %.1f V%.1f Q%.1f %.1f %.1f %.1f H%.1f Q%.1f %.1f %.1f %.1f V%.1f Z" % (
        x, y_base, y_end - s * r, x, y_end, x + r, y_end, x + bw - r, x + bw, y_end, x + bw, y_end - s * r, y_base)


def col_chart(labels, values, w=680, h=190, fmt=None):
    """세로 막대(양수 파랑 · 음수 빨강) · 값은 막대 끝에 · 굵기 ≤ 24px."""
    fmt = fmt or (lambda v: "%+.2f" % v)
    L, R, T, B = 40, 10, 16, 30
    vals = [v if (v is not None and v == v) else 0.0 for v in values]
    tk = nice_ticks(min(0.0, min(vals)), max(0.0, max(vals)), 4)
    y0, y1 = tk[0], tk[-1]
    Y = lambda v: T + (h - T - B) * (1 - (v - y0) / (y1 - y0))
    n = len(vals)
    slot = (w - L - R) / max(1, n)
    bw = min(24.0, slot * 0.6)
    o = [_svg(w, h)]
    for v in tk:
        o.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (L, w - R, Y(v), Y(v), COL["grid"]))
        o.append(_text(L - 6, Y(v) + 3, tick_label(v, None), "end", 8))
    o.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (L, w - R, Y(0), Y(0), COL["axis"]))
    for k, (lab, v) in enumerate(zip(labels, vals)):
        x = L + slot * k + (slot - bw) / 2
        if abs(Y(v) - Y(0)) >= 0.5:
            o.append('<path d="%s" fill="%s"/>' % (_vbar(x, Y(0), Y(v), bw), COL["pos"] if v >= 0 else COL["neg"]))
        ty = Y(v) - 4 if v >= 0 else Y(v) + 10
        o.append(_text(x + bw / 2, ty, fmt(v), "middle", 8, COL["ink2"]))
        o.append(_text(x + bw / 2, h - 14, lab, "middle", 8))
    o.append("</svg>")
    return "".join(o)


def hbar_chart(labels, values, w=330, fmt=None, color=None, lw=118, mark=None):
    """가로 막대 · 값은 끝에 · mark = 강조할 라벨(굵게)."""
    fmt = fmt or (lambda v: "%.2f%%" % v)
    rh, gap = 13, 5
    h = (rh + gap) * len(values) + 6
    vmax = max(values) if values else 1
    L, R = lw, 52
    o = [_svg(w, h)]
    for k, (lab, v) in enumerate(zip(labels, values)):
        y = 3 + k * (rh + gap)
        bl = (w - L - R) * (v / vmax) if vmax > 0 else 0
        r = min(4, bl / 2)
        if bl > 0.5:
            o.append('<path d="M%.1f %.1f H%.1f Q%.1f %.1f %.1f %.1f V%.1f Q%.1f %.1f %.1f %.1f H%.1f Z" fill="%s"/>' % (
                L, y, L + bl - r, L + bl, y, L + bl, y + r, y + rh - r, L + bl, y + rh, L + bl - r, y + rh, L, color or COL["s1"]))
        o.append(_text(L - 6, y + rh - 3, lab, "end", 8, COL["ink"] if lab == mark else COL["ink2"], 700 if lab == mark else 400))
        o.append(_text(L + bl + 4, y + rh - 3, fmt(v), "start", 8, COL["ink2"]))
    o.append("</svg>")
    return "".join(o)


def year_ticks(dates, every=2):
    out, seen = [], set()
    for i, d in enumerate(dates):
        y = d[:4]
        if y not in seen and d[5:7] == "01" and int(y) % every == 0:
            seen.add(y)
            out.append((i, y))
    return out


# ── 서술 통계(저장 계열에서) ────────────────────────────────────────────────
def drawdown(v):
    v = np.asarray(v, float)
    return (v / np.maximum.accumulate(v) - 1) * 100


def updown(fund_m, index_m):
    f, x = np.asarray(fund_m, float), np.asarray(index_m, float)
    up, dn = x > 0, x < 0
    ex = f - x
    return {"up_n": int(up.sum()), "dn_n": int(dn.sum()), "up_ex": float(ex[up].mean()), "dn_ex": float(ex[dn].mean()),
            "up_win": float((ex[up] > 0).mean() * 100), "dn_win": float((ex[dn] > 0).mean() * 100),
            "up_cap": float(f[up].mean() / x[up].mean() * 100), "dn_cap": float(f[dn].mean() / x[dn].mean() * 100),
            "beta": float(np.cov(x, f, ddof=1)[0, 1] / x.var(ddof=1))}


# ── 본문 ─────────────────────────────────────────────────────────────────
def page_head(t, p):
    return '<div class="ph"><span>%s — 펀드전략</span><span>%s · 내부용 · - %d -</span></div>' % (esc(t), DATE, p)


def title_of(k):
    return META[k]["title"] if k in META else MIXT.get(k, k)


def mix_line(J):
    """섞기 넷의 결론 — 결과에서 짓는다(측정만 · 선택 대상 아님)."""
    MX, sel = J.get("mix_results", {}), J["selection"]
    base = J["results"]["EG_BASE"]["all"]
    up = [k for k in MX if (MX[k]["all"]["ir"] or -9) > (base["ir"] or 0)]
    more = [k for k in MX if MX[k]["all"]["ann_ex"] > base["ann_ex"]]
    ok = [k for k in MX if sel[k]["pass"]]
    if not up and not more:
        return "다른 전략과 반반 섞은 넷은 IR·초과 모두 EG30 단독보다 낮았다(측정)."
    parts = []
    if up:
        parts.append("IR 이 EG30 보다 높은 섞기: " + ", ".join("%s(IR %s · 연 초과 %s)" % (MIXT[k], num(MX[k]["all"]["ir"]), pct(MX[k]["all"]["ann_ex"])) for k in up))
    if more:
        parts.append("초과가 EG30 보다 큰 섞기: " + ", ".join("%s(연 초과 %s · IR %s)" % (MIXT[k], pct(MX[k]["all"]["ann_ex"]), num(MX[k]["all"]["ir"])) for k in more))
    parts.append("선택 규칙 (a)~(e) 를 다 넘은 섞기: " + (", ".join(MIXT[k] for k in ok) if ok else "없음"))
    return "다른 전략과 반반 섞기(측정만) — " + " · ".join(parts) + " (EG30 단독 연 초과 %s · IR %s)." % (pct(base["ann_ex"]), num(base["ir"]))


def verdict_line(J):
    win, sel = J["winner"], J["selection"]
    if win == "EG_BASE":
        return ("EG30 유지 — 모멘텀을 한 점수로 통합한 후보 둘이 사전등록 선택 규칙"
                "(기저 대비 짝지은 차이 t ≥ %s · 30개월 토막 3/4 이상 · TE·회전 한도 · 최악 토막 · IR ≥ 기저)을 다 넘지 못했다. "
                "더 복잡한 조합이 이 창에서 EG30 을 확실히 이기지 못했으므로 가장 단순한 EG30 을 쓴다. " % num(J["rule"]["t_min"])) + mix_line(J)
    q = sel[win]
    return ("%s 선택 — 기저 대비 연 %s · NW t %s · 토막 %d/4 · 선택 규칙 다섯을 모두 넘은 후보 중 t 최대. "
            % (title_of(win), pp(q["d_ann_pp"]), num(q["t_nw3"]), sum(b > 0 for b in q["blocks_ann_pp"]))) + mix_line(J)


def build(J, X):
    win = J["winner"]
    MX = J.get("mix_results", {})
    is_mix = win in MX
    s = J["results"]["EG_BASE"] if is_mix else J["results"][win]      # 섞기가 뽑히면 일간 계열은 EG_BASE 것(사전등록 §3-2)
    m = META.get(win) or {"title": MIXT[win], "file": win, "select": MIXT[win], "steps": META["EG_BASE"]["steps"]}
    A = MX[win]["all"] if is_mix else s["all"]
    T3 = MX[win]["3y"] if is_mix else s["3y"]
    hold = s["hold_months"]
    w0, w1 = hold[0], hold[-1]
    r3 = [x for x in hold if x >= R3]
    sel = J["selection"]
    p = [0]

    def ph():
        p[0] += 1
        return ('<div class="pb"></div>' if p[0] > 1 else "") + page_head(m["title"], p[0])
    S = s["series"]
    dates = S["d"]
    fundv, idxv = np.array(S["fund"]), np.array(S["index"])
    ex_cum = (fundv - idxv) * 100                                    # 누적수익 차(%p) — 성과표의 «누적 초과수익» 과 같은 정의
    mex = np.array(MX[win]["monthly_ex"] if is_mix else s["monthly_ex"])
    UD = updown(s["monthly"]["fund"], s["monthly"]["index"])
    md = s["mdd"]
    FZ = J["results"].get("EG_FROZEN")
    h = [ph()]
    h.append("<h1>%s — 펀드전략</h1>" % esc(m["title"]))
    h.append('<p class="sub">작성 %s · 벤치마크 S&amp;P500 PR(가격지수) · 백테스트 보유 %s ~ %s(120개월) · 펀드 = S&amp;P500 90%% + 바스켓 10%% · '
             '거래비용 편도 10bp · NAV 1조 원 가정 · 시점정확 명단(편출 포함) · 금융 판정 시점정확</p>' % (DATE, w0, w1))
    tiles = [("연 초과수익", pct(A["ann_ex"]), "최근 3년 %s" % pct(T3["ann_ex"])), ("정보비율 (IR)", num(A["ir"]), "최근 3년 %s" % num(T3["ir"])),
             ("트래킹에러", pct(A["te"], sign=False), "월 승률 %s" % pct(A["win"], sign=False)),
             ("펀드 MDD", pct(md["fund_all"], sign=False), "S&amp;P500 %s" % pct(md["index_all"], sign=False)),
             ("t값", num(A["t"]), "누적 초과 %s" % pp(s["all"]["cum_ex"]))]
    h.append('<div class="tiles">' + "".join('<div class="tile"><div class="tl">%s</div><div class="tv">%s</div><div class="ts">%s</div></div>' % t for t in tiles) + "</div>")
    qs = sel.get("REF_QG") or {}
    h.append("<div class='box'><b>왜 이 전략 하나인가.</b> 펀드 틀(S&amp;P500 90%% + 바스켓 10%%)로 잰 전략 여섯 가운데 EG30 과 우량성장선별 30 이 가장 높았고, "
             "둘은 월 초과 상관 %s · 초과 차이 연 %s 로 사실상 같은 전략이라 더 단순한 EG30 을 남겼다(금융 판정은 시점정확으로 고쳤다). "
             "그 위에 모멘텀 통합 둘을 결과를 보기 전에 등록해 짝지어 비교했고(부록 A), 다른 전략과 반반 섞기 넷을 같이 쟀다(부록 B). <b>%s</b></div>"
             % (num(qs.get("corr_with_base")), pp(qs.get("d_ann_pp")), esc(verdict_line(J))))
    if is_mix:
        h.append("<p class='note'>섞기는 일간 경로가 없어 아래 일간 차트·낙폭·급등락 구간은 EG30(기저)의 것이다(사전등록 §3-2). 표의 월간 수치는 섞기 그대로.</p>")
    xt = year_ticks(dates)
    h.append("<h3>누적 성과 — 펀드와 S&amp;P500 PR (시작 = 100)</h3>")
    h.append(line_chart([{"name": "펀드", "short": "펀드", "y": list(fundv * 100), "color": COL["s1"], "fmt": lambda v: "%.0f" % v},
                         {"name": "S&P500 PR", "short": "S&P500", "y": list(idxv * 100), "color": COL["s2"], "fmt": lambda v: "%.0f" % v}],
                        xt, unit="x", h=185))
    h.append("<h3>누적 초과수익 — 펀드 누적수익 − S&amp;P500 누적수익 (%p)</h3>")
    h.append(line_chart([{"name": "누적 초과", "short": "누적", "y": list(ex_cum), "color": COL["s1"], "fmt": lambda v: "%+.2f%%p" % v}],
                        xt, unit="%", h=150, zero=0.0, area="누적 초과", legend=False))
    # 1. 성과
    h.append(ph())
    h.append("<h2>1. 성과 — S&amp;P500 PR 대비</h2><table><tr><th></th><th>전체 (%s ~ %s)</th><th>최근 3년 (%s ~ %s)</th></tr>" % (w0, w1, r3[0], r3[-1]))
    for lab, k, fmt in (("연 초과수익", "ann_ex", lambda v: pct(v)), ("트래킹에러", "te", lambda v: pct(v, sign=False)),
                        ("정보비율 (IR)", "ir", num), ("t값", "t", num), ("월 승률 (S&amp;P500 PR 대비)", "win", lambda v: pct(v, sign=False))):
        h.append("<tr><td>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (lab, fmt(A.get(k)), fmt(T3.get(k))))
    if not is_mix:
        h.append("<tr><td>누적 초과수익 (누적수익 차)</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (pp(A["cum_ex"]), pp(T3["cum_ex"])))
    h.append("</table><p class='note'>월 초과수익 = 펀드 − S&amp;P500 PR(거래비용 차감). 연 초과수익 = 월평균 × 12. 전반(~2021-08) IR %s · 후반 IR %s.%s</p>"
             % (num(s["h1"]["ir"]), num(s["h2"]["ir"]),
                ((" 금융 판정을 오늘 GICS 로 한 얼린 판은 연 초과 %s · IR %s(부록 A)." if win == "EG_BASE" else
                  " 기저 EG30 의 얼린 판(금융 오늘 GICS)은 연 초과 %s · IR %s(부록 A).") % (pct(FZ["all"]["ann_ex"]), num(FZ["all"]["ir"])) if FZ else "")))
    yrs = list(s["yearly"].items())
    h.append("<h3>연도별 초과수익 (%%p · %s 와 %s 는 부분 연도)</h3>" % (w0[:4], w1[:4]))
    h.append(col_chart([y for y, _ in yrs], [v["ex"] for _, v in yrs], h=165))
    h.append("<table><tr><th>연도</th><th>S&amp;P500 PR</th><th>펀드</th><th>초과</th><th>바스켓 단독</th></tr>")
    for y, v in yrs:
        part = " (부분)" if y in (w0[:4], w1[:4]) else ""
        h.append("<tr><td>%s%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n b'>%s</td><td class='n'>%s</td></tr>"
                 % (y, part, pct(v["index"]), pct(v["fund"]), pp(v["ex"]), pct(v["basket"])))
    h.append("</table>")
    # 2. 위험
    h.append(ph())
    h.append("<h2>2. 위험</h2><table><tr><th></th><th>S&amp;P500 PR (전체)</th><th>펀드 (전체)</th><th>S&amp;P500 PR (최근 3년)</th><th>펀드 (최근 3년)</th><th>바스켓 단독 (전체)</th></tr>")
    SA, S3 = s["all"], s["3y"]
    for lab, k in (("CAGR", "cagr"), ("연변동성", "vol")):
        h.append("<tr><td>%s</td>%s</tr>" % (lab, "".join("<td class='n'>%s</td>" % pct(x[k], 2, k == "cagr") for x in (SA["index"], SA["fund"], S3["index"], S3["fund"], SA["basket"]))))
    h.append("<tr><td>Sharpe</td>%s</tr>" % "".join("<td class='n'>%s</td>" % num(x["sharpe"]) for x in (SA["index"], SA["fund"], S3["index"], S3["fund"], SA["basket"])))
    h.append("<tr><td>MDD (일간)</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr></table>"
             % (pct(md["index_all"], 2, False), pct(md["fund_all"], 2, False), pct(md["index_3y"], 2, False), pct(md["fund_3y"], 2, False), pct(md["basket_all"], 2, False)))
    h.append("<h3>낙폭 — 고점 대비 (일간)</h3>")
    h.append(line_chart([{"name": "펀드", "short": "펀드", "y": list(drawdown(fundv)), "color": COL["s1"], "fmt": lambda v: "%.2f%%" % v},
                         {"name": "S&P500 PR", "short": "S&P500", "y": list(drawdown(idxv)), "color": COL["s2"], "fmt": lambda v: "%.2f%%" % v}],
                        xt, unit="%", h=155, zero=0.0))
    roll = [None] * 35 + [float(mex[k - 35:k + 1].mean() * 12) for k in range(35, len(mex))]
    mt = [(k, hm[:4]) for k, hm in enumerate(hold) if hm[5:7] == "01" and int(hm[:4]) % 2 == 0]
    h.append("<h3>36개월 이동 연 초과수익 — 초과가 한 시기에 몰렸는지</h3>")
    h.append(line_chart([{"name": "36개월 이동 연 초과", "short": "최근", "y": roll, "color": COL["s1"], "fmt": lambda v: "%+.2f%%" % v}],
                        mt, unit="%", h=135, zero=0.0, legend=False))
    h.append("<h3>시장이 오를 때와 내릴 때 (월간)</h3><table><tr><th></th><th>S&amp;P500 상승 월 (%d)</th><th>S&amp;P500 하락 월 (%d)</th></tr>" % (UD["up_n"], UD["dn_n"]))
    h.append("<tr><td>펀드 월평균 초과</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (pp(UD["up_ex"]), pp(UD["dn_ex"])))
    h.append("<tr><td>초과가 난 달</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (pct(UD["up_win"], sign=False), pct(UD["dn_win"], sign=False)))
    h.append("<tr><td>포착률 (펀드 ÷ 지수 월평균)</td><td class='n'>%s</td><td class='n'>%s</td></tr></table>" % (pct(UD["up_cap"], sign=False), pct(UD["dn_cap"], sign=False)))
    h.append("<p class='note'>지수 대비 베타 %s. 상승 포착률과 하락 포착률이 둘 다 100%% 를 넘으면 «더 오르고 더 내린다» — 바스켓의 성장주 쏠림이 만드는 모양이다.</p>" % num(UD["beta"]))
    # 3. 급락 · 급등 — 따로 묶는다
    h.append(ph())
    h.append("<h2>3. 급락 구간과 급등 구간</h2>")
    for kind, cls in (("급락", "dn"), ("급등", "up")):
        es = [e for e in s["episodes"] if e["kind"] == kind]
        if not es:
            continue
        av = lambda k: sum(e[k] for e in es) / len(es)
        h.append("<h3>%s 구간 %d개 — 펀드가 앞선 구간 %d/%d · 평균 초과 %s</h3>" % (kind, len(es), sum(e["ex"] > 0 for e in es), len(es), pp(av("ex"))))
        h.append(col_chart([e["name"][:9] for e in es], [e["ex"] for e in es], h=140))
        h.append("<table><tr><th>구간</th><th>기간</th><th>S&amp;P500 PR</th><th>펀드</th><th>초과</th><th>바스켓 단독</th><th>바스켓 초과</th></tr>")
        for e in es:
            h.append("<tr><td>%s</td><td class='nw'>%s → %s</td><td class='n %s'>%s</td><td class='n'>%s</td><td class='n b'>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>"
                     % (esc(e["name"]), e["a"][2:], e["z"][2:], cls, pct(e["index"]), pct(e["fund"]), pp(e["ex"]), pct(e["basket"]), pp(e["basket_ex"])))
        h.append("<tr class='avg'><td>%d구간 평균</td><td></td><td class='n'>%s</td><td class='n'>%s</td><td class='n b'>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr></table>"
                 % (len(es), pct(av("index")), pct(av("fund")), pp(av("ex")), pct(av("basket")), pp(av("basket_ex"))))
    h.append("<p class='note'>시작일 종가 → 끝일 종가, 일간 가격. 초과 = 펀드 − S&amp;P500 PR. 바스켓 단독 = NAV 전부를 바스켓에 넣었을 때.</p>")
    # 4·5. 전략 요약 · 방법론 · 보유
    h.append(ph())
    h.append("<h2>4. 전략 요약</h2><table class='kv'>")
    rows = [("목표", "S&amp;P500 인덱스 펀드 NAV의 10%를 이 바스켓으로 바꿔 S&amp;P500 PR을 넘는다"),
            ("종목 선정", esc(m["select"])),
            ("비중", "바스켓 안은 시가총액 비례 · 한 회사 최대 20% (넘친 몫은 나머지에 비례 재배분)"),
            ("리밸런스", "바스켓은 분기(3·6·9·12월 말) 교체 → 다음 3개월 보유 · 바스켓 비중은 매월 말 NAV 10%로 맞춤"),
            ("투자 규모", "NAV의 10%% — S&amp;P500 보유를 종목마다 10%%씩 줄이고 그 돈으로 바스켓을 담는다 · 나머지 90%%는 지수 그대로 "
                        "(바스켓 단독이면 연 초과 %s · IR %s)" % (pct(SA["basket_ann_ex"]), num(SA["basket_ir"]))),
            ("위험 조건", "공매도 · 파생 · 차입 없음 · 바스켓 안 한 회사 최대 20% (NAV의 2%)"),
            ("비용 · 기준", "편도 10bp · 벤치는 가격수익 — 바스켓 종가는 배당조정이라 배당만큼(바스켓 배당률 × 10%) 유리하다"),
            ("랩 판정", esc(verdict_line(J)))]
    for k, v in rows:
        h.append("<tr><th>%s</th><td>%s</td></tr>" % (k, v))
    cov = J.get("coverage") or {}
    ck = sorted(cov)
    h.append("</table><h2>5. 방법론</h2><h3>5-1. 종목 선정</h3><table><tr><th>단계</th><th>내용</th><th>값</th></tr>")
    h.append("<tr><td class='k'>유니버스</td><td>그 월말 S&amp;P500 ∪ NASDAQ100 구성종목(시점정확 · 편출 종목 포함) · 같은 회사의 두 종목은 하나로 · 금융은 Eg 가 없어 빠진다"
             "(금융 판정은 그때의 GICS — 2023-03 전 결제 처리 회사는 비금융 · 2016-09 전 리츠는 금융)</td><td class='n'>%s</td></tr>"
             % ("약 %d개" % cov[ck[-1]]["eg"] if ck else "—"))
    for a, b, c in m["steps"]:
        h.append("<tr><td class='k'>%s</td><td>%s</td><td class='n'>%s</td></tr>" % (esc(a), esc(b), c))
    h.append("<tr><td class='k'>시점 규칙</td><td>그때 공개되지 않은 재무·명단은 쓰지 않는다 · 편출 종목의 가격을 포함한다(한계는 부록 D)</td><td class='n'>—</td></tr></table>")
    H = s["holdings"]
    tops = H["top"][:15]
    secs = list((H.get("sectors") or {}).items())
    h.append("<h3>5-2. 현재 바스켓 — %s 형성 · %d종목 · 유효 종목 수 %s개 · 상위 3 합 %s</h3>" % (H["sig"], H["n"], num(H["eff_n"]), pct(H["top3"], sign=False)))
    h.append("<div class='two'><div><div class='cap'>바스켓 비중 상위 15</div>%s</div><div><div class='cap'>섹터 비중</div>%s</div></div>" % (
        hbar_chart([x["t"] for x in tops], [x["w"] for x in tops], lw=52),
        hbar_chart([SECKO.get(k, k) for k, _ in secs], [v for _, v in secs], lw=70)))
    h.append("<table><tr><th>회사</th><th>티커</th><th>섹터</th><th>바스켓 비중</th><th>NAV 비중</th></tr>")
    for x in tops:
        h.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (
            esc(x["name"]), x["t"], esc(SECKO.get(x.get("sector"), x.get("sector") or "—")), pct(x["w"], sign=False), pct(x["w"] * 0.1, sign=False)))
    h.append("</table><h3>5-3. 매매와 비용</h3><table class='kv'>")
    h.append("<tr><th>명단 교체</th><td>리밸런스마다 새로 들어오는 종목 중앙 %s개</td></tr>" % num(s.get("name_turnover_median"), 0))
    h.append("<tr><th>회전율</th><td>연 편도 NAV 대비 %s (바스켓 자체 %s × 10%% + 10%% 되돌리기)</td></tr>" % (pct(s["nav_turn_oneway"] * 100, sign=False), pct(s["basket_turn_oneway"] * 100, sign=False)))
    h.append("<tr><th>거래비용</th><td>연 약 %s (NAV 1조 원이면 연 %.2f억 원)</td></tr></table>" % (pct(s["nav_turn_oneway"] * 2 * 0.1, sign=False), s["nav_turn_oneway"] * 2 * 0.001 * 1e4))
    # 부록 A — 후보 비교
    h.append(ph())
    h.append("<h2>부록 A. 후보 비교 — 결과를 보기 전에 등록한 후보와 기저 (선택 대상: C1 · C2)</h2>")
    rowsA = [("EG_BASE", "EG30 (기저)", J["results"]["EG_BASE"]["all"], J["results"]["EG_BASE"]["3y"], J["results"]["EG_BASE"]["basket_turn_oneway"]),
             ("C1", META["C1"]["title"], J["results"]["C1"]["all"], J["results"]["C1"]["3y"], J["results"]["C1"]["basket_turn_oneway"]),
             ("C2", META["C2"]["title"], J["results"]["C2"]["all"], J["results"]["C2"]["3y"], J["results"]["C2"]["basket_turn_oneway"])]
    for k, v in MX.items():
        rowsA.append((k, MIXT[k], v["all"], v["3y"], v["basket_turn_oneway"]))
    for k, t in (("EG_FROZEN", "EG30 얼린 판 (금융 오늘 GICS · 참고)"), ("REF_QG", "우량성장 30 랩 판 (참고)")):
        if k in J["results"]:
            rowsA.append((k, t, J["results"][k]["all"], J["results"][k]["3y"], J["results"][k]["basket_turn_oneway"]))
    h.append("<div class='cap'>정보비율 (IR) — 전체 창</div>")
    h.append(hbar_chart([r[0] for r in rowsA], [max(0.0, r[2]["ir"] or 0.0) for r in rowsA], w=680, lw=72, fmt=lambda v: "%.2f" % v, mark=win))
    h.append("<table><tr><th>후보</th><th>연 초과</th><th>TE</th><th>IR</th><th>t</th><th>최근 3년 IR</th><th>바스켓 회전</th></tr>")
    for k, t, a, a3, tu in rowsA:
        h.append("<tr%s><td>%s · %s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n b'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>"
                 % (" class='avg'" if k == win else "", k, esc(t), pct(a["ann_ex"]), pct(a["te"], sign=False), num(a["ir"]), num(a["t"]), num(a3["ir"]), pct(tu * 100, sign=False)))
    h.append("</table><h3>기저(EG30) 대비 짝지은 차이 — 선택 규칙 (섞기 넷은 참고로 같은 셈)</h3>")
    h.append("<table><tr><th>후보</th><th>차이 연</th><th>NW t</th><th>30개월 토막 넷 (연 %%p)</th><th>상관</th><th>(a) t ≥ %s</th><th>(b)</th><th>(c)</th><th>(d)</th><th>(e)</th></tr>" % num(J["rule"]["t_min"]))
    ok = lambda b: "통과" if b else "—"
    for k in ("C1", "C2", "P_M", "P_B", "P_A", "P_Q"):
        q = sel[k]
        h.append("<tr><td>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                 % (k, pp(q["d_ann_pp"]), num(q["t_nw3"]), " · ".join("%+.2f" % b for b in q["blocks_ann_pp"]), num(q["corr_with_base"]),
                    ok(q["a"]), ok(q["b"]), ok(q["c"]), ok(q["d"]), ok(q["e"])))
    h.append("</table><p class='note'>차이 = 후보 펀드 월 초과 − 기저 펀드 월 초과. (a) 짝지은 차이의 Newey-West t · (b) 네 토막 중 셋 이상 양수 · (c) TE ≤ 1.2% · 회전 ≤ 기저의 2배 · "
             "(d) 최악 토막 ≥ 연 −0.30%p · (e) IR ≥ 기저. 다섯 다 넘는 후보 중 t 최대, 없으면 기저가 남는다(사전등록 PREREG-2026-09-24-EGBEST). "
             "120개월에서 IR 표준오차는 약 0.32 — IR 차이 0.4 미만은 운과 구별되지 않는다.</p>")
    # 부록 B — 섞기
    h.append(ph())
    h.append("<h2>부록 B. 다른 전략과 섞으면 나아지나</h2>")
    h.append("<p class='note'>바스켓 10% 를 EG30 과 다른 전략이 나눠 담는다(매월 말 비율로 되돌림). 등록한 비율은 반반 하나이고, 아래 곡선은 비율을 0~100% 로 바꿔 본 <b>서술</b>이다 — "
             "곡선에서 가장 좋은 점을 고르면 그 자체가 과적합이라 선택에 쓰지 않았다.</p>")
    cv = J["mix_curve"]
    names = {"M": "모멘텀 10", "B": "B/M 로테이션", "A": "알파 개선 10", "Q": "우량성장 30"}
    cols = {"M": COL["s1"], "B": COL["s2"], "A": COL["s3"], "Q": COL["s4"]}
    xl = [(k, "%d%%" % (k * 10)) for k in range(0, 11, 2)]
    h.append("<h3>짝 전략 비중에 따른 IR (0% = EG30 단독 · 100% = 짝 단독)</h3>")
    h.append(line_chart([{"name": names[x], "short": names[x], "y": [r["ir"] for r in cv[x]], "color": cols[x], "fmt": lambda v: "%.2f" % v} for x in ("M", "B", "A", "Q")],
                        xl, unit="x", h=185, vline=(5, "등록한 반반")))
    h.append("<h3>짝 전략 비중에 따른 연 초과수익</h3>")
    h.append(line_chart([{"name": names[x], "short": names[x], "y": [r["ann_ex"] for r in cv[x]], "color": cols[x], "fmt": lambda v: "%+.2f%%" % v} for x in ("M", "B", "A", "Q")],
                        xl, unit="%", h=185, zero=0.0, vline=(5, "등록한 반반")))
    h.append("<table><tr><th>반반 섞기</th><th>연 초과</th><th>TE</th><th>IR</th><th>최근 3년 IR</th><th>짝과 EG30 상관</th><th>기저 대비 차이 연</th><th>NW t</th></tr>")
    for k, v in MX.items():
        q = sel[k]
        h.append("<tr><td>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n b'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>"
                 % (MIXT[k], pct(v["all"]["ann_ex"]), pct(v["all"]["te"], sign=False), num(v["all"]["ir"]), num(v["3y"]["ir"]), num(v["corr_partner_base"]), pp(q["d_ann_pp"]), num(q["t_nw3"])))
    h.append("</table>")
    base = J["results"]["EG_BASE"]["all"]
    bk, bv = max(MX.items(), key=lambda kv: kv[1]["all"]["ir"] or -9)
    if (bv["all"]["ir"] or 0) > (base["ir"] or 0):
        scale = base["te"] / bv["all"]["te"]
        why_ = (" — 짝과의 상관이 %s 라 TE 가 %s 로 줄기 때문이다" % (num(bv["corr_partner_base"]), pct(bv["all"]["te"], sign=False))
                if (bv["corr_partner_base"] < 0 and bv["all"]["te"] < base["te"]) else "")
        h.append("<div class='box'><b>읽는 법.</b> %s 는 IR 이 %s 로 EG30 단독(%s)보다 높다%s. "
                 "10%% 틀 안의 초과는 %s 로 EG30 단독(%s)과 비교해야 한다. 바스켓을 약 %s%% 로 바꿔 TE 를 EG30 과 같게 맞추면 초과는 약 %s 가 된다 — "
                 "펀드 틀(10%%)을 바꾸는 결정이라 이 등록의 선택 대상이 아니고, 따로 등록해 재야 한다.</div>"
                 % (MIXT[bk], num(bv["all"]["ir"]), num(base["ir"]), why_,
                    pct(bv["all"]["ann_ex"]), pct(base["ann_ex"]), num(10 * scale, 0), pct(bv["all"]["ann_ex"] * scale)))
    else:
        h.append("<div class='box'><b>읽는 법.</b> 반반 섞기 넷 모두 IR 이 EG30 단독(%s)보다 낮다 — 섞어서 좋아지는 조합이 이 창에는 없다.</div>" % num(base["ir"]))
    # 부록 C · D · E
    h.append(ph())
    h.append("<h2>부록 C. 정리한 전략 (old 폴더) — 같은 펀드 틀</h2><table><tr><th>전략</th><th>연 초과</th><th>TE</th><th>IR</th><th>t</th><th>최근 3년 IR</th><th>정리 이유</th></tr>")
    qs = sel.get("REF_QG") or {}
    why = {"Q": "EG30 과 월 초과 상관 %s · 초과 차이 연 %s — ROE·평활을 더해도 사실상 같은 전략" % (num(qs.get("corr_with_base")), pp(qs.get("d_ann_pp"))),
           "C": "1/3씩 섞으면 B/M 이 희석(사전등록 FUNDMIX 기각)",
           "M": "10종목 동일가중 — TE 가 크고 최근 3년 약함", "A": "펀드 틀에서 IR 0.24 · 최근 3년 음수", "B": "펀드 틀에서 초과가 거의 0"}
    for c, t in OLD:
        r = J["results"]["REF_QG"] if c == "Q" else X["strategies"][c]
        h.append("<tr><td>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td>%s</td></tr>"
                 % (esc(t), pct(r["all"]["ann_ex"]), pct(r["all"]["te"], sign=False), num(r["all"]["ir"]), num(r["all"]["t"]), num(r["3y"]["ir"]), why[c]))
    h.append("</table><p class='note'>우량성장 30 랩 판은 금융을 오늘 GICS 로 빼 공식 판(MA 포함)과 다르다 — 공식 판 IR 1.12(내부 자료 · 가격수익 기준).</p>")
    c0 = cov[ck[0]] if ck else None
    h.append("<h2>부록 D. 한계와 주의</h2><ul class='lim'>")
    lims = ["<b>백테스트다.</b> 120개월 · IR 표준오차 약 0.32 — 전체 IR %s 의 95%% 구간은 대략 %s ~ %s." % (num(A["ir"]), num(A["ir"] - 0.63), num(A["ir"] + 0.63)),
            "<b>생존 편향.</b> 편출 종목 중 가격 자료가 없는 회사가 빠진다 — %s 형성 때 명단 회사 %s 중 가격이 선 회사 %s. 초기일수록 비고, 빠진 쪽이 주로 인수합병으로 사라진 회사다."
            % (ck[0] if ck else "—", c0["companies"] if c0 else "—", c0["keyed"] if c0 else "—"),
            "<b>금융 판정.</b> 월말 위키 S&amp;P500 표(과거 리비전)의 GICS 로 가른다 — 위키 편집 지연이 있다(부동산 분리가 표에 2개월 늦게 보인다). "
            "표에 한 번도 없던 회사는 오늘 분류로 메운다. FIS 는 재무 자료(연간 영업현금흐름)가 FY2022 부터라 창 내내 빠진다.",
            "<b>시가총액은 배당조정 종가 × 주식수.</b> 과거 시총이 그 뒤 배당만큼 작게 잡혀 2016~2018 비중이 약 5% 흔들린다.",
            "<b>재무는 최신 제출본.</b> 뒤에 공시된 재작성이 과거 값에 들어간다(예: MSFT FY2017 ASC 606).",
            "<b>배당.</b> 바스켓은 배당 포함 · 벤치는 가격지수 — 초과의 일부(바스켓 배당률 × 10%, 연 약 0.1%p)는 배당이다.",
            "<b>집중.</b> 상위 3종목이 바스켓의 %s(NAV 의 %s) — 한 회사 20%% 상한에 붙어 있다. 대형 기술주 한두 개가 초과를 좌우한다." % (pct(H["top3"], sign=False), pct(H["top3"] * 0.1, sign=False))]
    h.append("".join("<li>%s</li>" % x for x in lims) + "</ul>")
    if s.get("trades"):
        h.append(ph())
        h.append("<h2>부록 E. 최근 매매 — %s 리밸런스 (펀드 NAV 대비 · %d종목)</h2>" % (H["sig"], len(s["trades"])))
        for kind in ("신규 매수", "전량 매도", "늘림", "줄임"):
            tt = [x for x in s["trades"] if x["kind"] == kind]
            if not tt:
                continue
            h.append("<h3>%s %d종목</h3><table><tr><th>티커</th><th>회사</th><th>매매 (NAV %%)</th><th>금액 (억 원)</th></tr>" % (kind, len(tt)))
            for x in sorted(tt, key=lambda x: -abs(x["pct"]))[:20]:
                h.append("<tr><td>%s</td><td>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (x["t"], esc(x["name"]), pct(x["pct"]), "%+.2f" % x["eok"]))
            h.append("</table>")
    css = """<style>@page{size:A4;margin:13mm 13mm}body{font-family:'Malgun Gothic',sans-serif;font-size:9.4pt;color:#0b0b0b;background:#fff}
    h1{font-size:15pt;margin:4px 0}h2{font-size:12pt;margin:12px 0 6px;border-bottom:1.5px solid #2a78d6;padding-bottom:2px}h3{font-size:10pt;margin:9px 0 3px}
    table{border-collapse:collapse;width:100%;margin:2px 0 6px}th,td{border-bottom:1px solid #e1e0d9;padding:3px 6px;text-align:left}th{background:#f3f2ee;font-weight:700}
    td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}td.nw,th{white-space:nowrap}td.k{white-space:nowrap;width:9%}td.b{font-weight:700}tr.avg td{background:#f7f6f2;font-weight:600}
    table.kv th{width:17%}.sub{color:#52514e;font-size:8.4pt}.note{color:#52514e;font-size:8pt;margin:2px 0 8px}
    .ph{display:flex;justify-content:space-between;color:#898781;font-size:8pt;border-bottom:1px solid #e1e0d9;margin-bottom:6px}
    .box{border:1px solid #cfd8e3;background:#f5f8fb;padding:6px 9px;margin:8px 0;font-size:9pt}.pb{page-break-after:always}
    .tiles{display:flex;gap:6px;margin:8px 0}.tile{flex:1;border:1px solid #e1e0d9;border-radius:6px;padding:6px 8px;background:#fcfcfb}
    .tl{font-size:8pt;color:#52514e}.tv{font-size:15pt;font-weight:600;margin:2px 0}.ts{font-size:7.8pt;color:#898781}
    .lg{display:flex;gap:14px;font-size:8pt;color:#52514e;margin:2px 0 0 46px}.lg i{display:inline-block;width:14px;height:2px;margin:0 5px 3px 0;vertical-align:middle}
    .two{display:flex;gap:12px}.two>div{flex:1}.cap{font-size:8.4pt;color:#52514e;margin:2px 0}ul.lim{margin:4px 0 0 16px;padding:0}ul.lim li{margin:3px 0}
    svg{display:block;break-inside:avoid}h3{break-after:avoid}</style>"""
    return "<!doctype html><html><head><meta charset='utf-8'><title>%s</title>%s</head><body>%s</body></html>" % (esc(m["title"]), css, "\n".join(h))


def main() -> int:
    J = json.load(io.open(SRC, encoding="utf-8"))
    X = json.load(io.open(MIX, encoding="utf-8"))
    outdir = os.environ.get("FUND_REPORT_DIR", OUTDIR)
    os.makedirs(os.path.join(outdir, "old"), exist_ok=True)
    win = J["winner"]
    m = META.get(win) or {"file": win}
    hp = os.path.join(outdir, "old", "%s_src.html" % m["file"])
    pp_ = os.path.join(outdir, "펀드전략_%s_%s.pdf" % (m["file"], DATE))
    io.open(hp, "w", encoding="utf-8").write(build(J, X))
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--print-to-pdf=" + pp_, "file:///" + hp.replace("\\", "/")], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("→", pp_)
    return 0


if __name__ == "__main__":
    sys.exit(main())
