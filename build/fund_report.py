# -*- coding: utf-8 -*-
"""build/fund_report.py — 펀드 전략 리포트 공용 양식(S&P500 90% + 바스켓 10% 틀) → HTML · Chrome 헤드리스 PDF

양식(사용자 지시 2026-09-24 · C:/Project/fund_reports/펀드전략_작성원칙.md):
  핵심 수치 → **이 전략을 쓰는 근본 이유** → 1 성과(연도별 차트·표) → 2 위험(낙폭 · 36개월 이동 초과 · 상승/하락 월) →
  3 급락 구간 · 급등 구간(따로 묶는다) → 4 전략 요약 → 5 방법론(단계 · 보유 · 매매와 비용) → 부록 A 최근 매매 · 부록 B 한계.
  선정 경위 · 후보 비교 · 섞기 · 기계적 구간은 싣지 않는다. 숫자는 소수 둘째 자리까지.
입력은 qg_lab.World.evaluate() 가 내는 결과 사전 하나(series · monthly · yearly · episodes · holdings · trades · all/3y/h1/h2 · mdd) + 설명 사전.
여기서는 새 검정을 하지 않는다(이동 평균 · 낙폭 · 상승/하락 월 같은 서술 통계만). 🚨 PDF 는 «내부용» — 저장소 밖에 쓴다.
"""
from __future__ import annotations
import html, io, math, os, subprocess, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import numpy as np

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
COL = {"s1": "#2a78d6", "s2": "#eb6834", "s3": "#1baf7a", "s4": "#eda100", "neg": "#e34948", "pos": "#2a78d6",
       "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7", "surf": "#fcfcfb"}
SECKO = {"Information Technology": "IT", "Health Care": "헬스케어", "Financials": "금융", "Consumer Discretionary": "경기소비재",
         "Communication Services": "커뮤니케이션", "Industrials": "산업재", "Consumer Staples": "필수소비재", "Energy": "에너지",
         "Utilities": "유틸리티", "Real Estate": "부동산", "Materials": "소재"}
R3 = "2023-09"


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
def page_head(t, p, date):
    return '<div class="ph"><span>%s — 펀드전략</span><span>%s · 내부용 · - %d -</span></div>' % (esc(t), date, p)




def build(res, meta, date):
    """res: evaluate() 결과 · meta: {title, sub_extra, reasons:[(제목, 글)], select, weight, reb, steps:[(단계, 내용, 값)], universe, risk, evidence, limits:[글]}"""
    s = res
    A, T3 = s["all"], s["3y"]
    hold = s["hold_months"]
    w0, w1 = hold[0], hold[-1]
    r3 = [x for x in hold if x >= R3]
    p = [0]
    title = meta["title"]

    def ph():
        p[0] += 1
        return ('<div class="pb"></div>' if p[0] > 1 else "") + page_head(title, p[0], date)
    S = s["series"]
    dates = S["d"]
    fundv, idxv = np.array(S["fund"]), np.array(S["index"])
    ex_cum = (fundv - idxv) * 100
    mex = np.array(s["monthly_ex"])
    UD = updown(s["monthly"]["fund"], s["monthly"]["index"])
    md = s["mdd"]
    yrs = list(s["yearly"].items())
    h = [ph()]
    h.append("<h1>%s — 펀드전략</h1>" % esc(title))
    h.append('<p class="sub">작성 %s · 벤치마크 S&amp;P500 PR(가격지수) · 백테스트 보유 %s ~ %s(%d개월) · 펀드 = S&amp;P500 90%% + 바스켓 10%% · '
             '거래비용 편도 10bp · NAV 1조 원 가정 · 시점정확 명단(편출 포함)%s</p>' % (date, w0, w1, len(hold), meta.get("sub_extra", "")))
    tiles = [("연 초과수익", pct(A["ann_ex"]), "최근 3년 %s" % pct(T3["ann_ex"])), ("정보비율 (IR)", num(A["ir"]), "최근 3년 %s" % num(T3["ir"])),
             ("트래킹에러", pct(A["te"], sign=False), "월 승률 %s" % pct(A["win"], sign=False)),
             ("펀드 MDD", pct(md["fund_all"], sign=False), "S&amp;P500 %s" % pct(md["index_all"], sign=False)),
             ("이긴 해", "%d/%d" % (sum(v["ex"] > 0 for _, v in yrs), len(yrs)), "누적 초과 %s" % pp(A["cum_ex"]))]
    h.append('<div class="tiles">' + "".join('<div class="tile"><div class="tl">%s</div><div class="tv">%s</div><div class="ts">%s</div></div>' % t for t in tiles) + "</div>")
    h.append("<h2>이 전략을 쓰는 근본 이유</h2><table class='kv'>")
    for k, v in meta["reasons"]:
        h.append("<tr><th>%s</th><td>%s</td></tr>" % (esc(k), v))
    h.append("</table>")
    xt = year_ticks(dates)
    h.append("<h3>누적 성과 — 펀드와 S&amp;P500 PR (시작 = 100)</h3>")
    h.append(line_chart([{"name": "펀드", "short": "펀드", "y": list(fundv * 100), "color": COL["s1"], "fmt": lambda v: "%.0f" % v},
                         {"name": "S&P500 PR", "short": "S&P500", "y": list(idxv * 100), "color": COL["s2"], "fmt": lambda v: "%.0f" % v}],
                        xt, unit="x", h=175))
    h.append("<h3>누적 초과수익 — 펀드 누적수익 − S&amp;P500 누적수익 (%p)</h3>")
    h.append(line_chart([{"name": "누적 초과", "short": "누적", "y": list(ex_cum), "color": COL["s1"], "fmt": lambda v: "%+.2f%%p" % v}],
                        xt, unit="%", h=140, zero=0.0, area="누적 초과", legend=False))
    # 1. 성과
    h.append(ph())
    h.append("<h2>1. 성과 — S&amp;P500 PR 대비</h2><table><tr><th></th><th>전체 (%s ~ %s)</th><th>최근 3년 (%s ~ %s)</th></tr>" % (w0, w1, r3[0], r3[-1]))
    for lab, k, fmt in (("연 초과수익", "ann_ex", lambda v: pct(v)), ("누적 초과수익 (누적수익 차)", "cum_ex", lambda v: pp(v)),
                        ("트래킹에러", "te", lambda v: pct(v, sign=False)), ("정보비율 (IR)", "ir", num), ("t값", "t", num),
                        ("월 승률 (S&amp;P500 PR 대비)", "win", lambda v: pct(v, sign=False))):
        h.append("<tr><td>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (lab, fmt(A.get(k)), fmt(T3.get(k))))
    h.append("</table><p class='note'>월 초과수익 = 펀드 − S&amp;P500 PR(거래비용 차감). 연 초과수익 = 월평균 × 12. 전반(~2021-08) IR %s · 후반 IR %s.</p>"
             % (num(s["h1"]["ir"]), num(s["h2"]["ir"])))
    h.append("<h3>연도별 초과수익 (%%p · %s 와 %s 는 부분 연도)</h3>" % (w0[:4], w1[:4]))
    h.append(col_chart([y for y, _ in yrs], [v["ex"] for _, v in yrs], h=160))
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
                        xt, unit="%", h=150, zero=0.0))
    roll = [None] * 35 + [float(mex[k - 35:k + 1].mean() * 12) for k in range(35, len(mex))]
    mt = [(k, hm[:4]) for k, hm in enumerate(hold) if hm[5:7] == "01" and int(hm[:4]) % 2 == 0]
    h.append("<h3>36개월 이동 연 초과수익 — 초과가 한 시기에 몰렸는지</h3>")
    h.append(line_chart([{"name": "36개월 이동 연 초과", "short": "최근", "y": roll, "color": COL["s1"], "fmt": lambda v: "%+.2f%%" % v}],
                        mt, unit="%", h=130, zero=0.0, legend=False))
    h.append("<h3>시장이 오를 때와 내릴 때 (월간)</h3><table><tr><th></th><th>S&amp;P500 상승 월 (%d)</th><th>S&amp;P500 하락 월 (%d)</th></tr>" % (UD["up_n"], UD["dn_n"]))
    h.append("<tr><td>펀드 월평균 초과</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (pp(UD["up_ex"]), pp(UD["dn_ex"])))
    h.append("<tr><td>초과가 난 달</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (pct(UD["up_win"], sign=False), pct(UD["dn_win"], sign=False)))
    h.append("<tr><td>포착률 (펀드 ÷ 지수 월평균)</td><td class='n'>%s</td><td class='n'>%s</td></tr></table>" % (pct(UD["up_cap"], sign=False), pct(UD["dn_cap"], sign=False)))
    h.append("<p class='note'>지수 대비 베타 %s. 하락 포착률이 100%% 를 넘으면 지수가 내릴 때 펀드가 더 내린다는 뜻이다.</p>" % num(UD["beta"]))
    # 3. 급락 · 급등
    h.append(ph())
    h.append("<h2>3. 급락 구간과 급등 구간</h2>")
    for kind, cls in (("급락", "dn"), ("급등", "up")):
        es = [e for e in s["episodes"] if e["kind"] == kind]
        if not es:
            continue
        av = lambda k: sum(e[k] for e in es) / len(es)
        h.append("<h3>%s 구간 %d개 — 펀드가 앞선 구간 %d/%d · 평균 초과 %s</h3>" % (kind, len(es), sum(e["ex"] > 0 for e in es), len(es), pp(av("ex"))))
        h.append(col_chart([e["name"][:9] for e in es], [e["ex"] for e in es], h=135))
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
    rows = [("목표", meta.get("goal", "S&amp;P500 인덱스 펀드 NAV의 10%를 이 바스켓으로 바꿔 S&amp;P500 PR을 넘는다")),
            ("종목 선정", esc(meta["select"])), ("비중", esc(meta["weight"])), ("리밸런스", esc(meta["reb"])),
            ("투자 규모", "NAV의 10%% — S&amp;P500 보유를 종목마다 10%%씩 줄이고 그 돈으로 바스켓을 담는다 · 나머지 90%%는 지수 그대로 "
                        "(바스켓 단독이면 연 초과 %s · IR %s)" % (pct(SA["basket_ann_ex"]), num(SA["basket_ir"]))),
            ("위험 조건", esc(meta["risk"])),
            ("비용 · 기준", "편도 10bp · 벤치는 가격수익 — 바스켓 종가는 배당조정이라 배당만큼(바스켓 배당률 × 10%) 유리하다"),
            ("검증 근거", meta["evidence"])]
    for k, v in rows:
        h.append("<tr><th>%s</th><td>%s</td></tr>" % (k, v))
    h.append("</table><h2>5. 방법론</h2><h3>5-1. 종목 선정</h3><table><tr><th>단계</th><th>내용</th><th>값</th></tr>")
    h.append("<tr><td class='k'>유니버스</td><td>%s</td><td class='n'>—</td></tr>" % esc(meta["universe"]))
    for a, b, c in meta["steps"]:
        h.append("<tr><td class='k'>%s</td><td>%s</td><td class='n'>%s</td></tr>" % (esc(a), esc(b), esc(c)))
    h.append("<tr><td class='k'>시점 규칙</td><td>그때 공개되지 않은 재무·명단은 쓰지 않는다 · 편출 종목의 가격을 포함한다(한계는 부록 B)</td><td class='n'>—</td></tr></table>")
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
    # 부록 A 최근 매매 · 부록 B 한계
    if s.get("trades"):
        h.append(ph())
        h.append("<h2>부록 A. 최근 매매 — %s 리밸런스 (펀드 NAV 대비 · %d종목)</h2>" % (H["sig"], len(s["trades"])))
        for kind in ("신규 매수", "전량 매도", "늘림", "줄임"):
            tt = [x for x in s["trades"] if x["kind"] == kind]
            if not tt:
                continue
            h.append("<h3>%s %d종목</h3><table><tr><th>티커</th><th>회사</th><th>매매 (NAV %%)</th><th>금액 (억 원)</th></tr>" % (kind, len(tt)))
            for x in sorted(tt, key=lambda x: -abs(x["pct"]))[:20]:
                h.append("<tr><td>%s</td><td>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (x["t"], esc(x["name"]), pct(x["pct"]), "%+.2f" % x["eok"]))
            h.append("</table>")
    h.append(ph())
    h.append("<h2>부록 B. 한계와 주의</h2><ul class='lim'>")
    h.append("".join("<li>%s</li>" % x for x in meta["limits"]) + "</ul>")
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
    return "<!doctype html><html><head><meta charset='utf-8'><title>%s</title>%s</head><body>%s</body></html>" % (esc(title), css, "\n".join(h))


def render(res, meta, date, pdf_path, html_path):
    io.open(html_path, "w", encoding="utf-8").write(build(res, meta, date))
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--print-to-pdf=" + pdf_path, "file:///" + html_path.replace("\\", "/")], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return pdf_path
