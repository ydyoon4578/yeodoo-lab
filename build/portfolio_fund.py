# -*- coding: utf-8 -*-
r"""build/portfolio_fund.py — 운용 포트폴리오 페이지(portfolio.html)의 본문 조각을 만든다.

무엇을 만드나. 실펀드 2종(2Z30=나스닥100 · 2A81=S&P500)의
  ① 펀드 개요 — NAV·기준가, 연초 후 기준가 vs 지수(원화환산), 자산 구성
  ② 보유 vs 지수 — 종목별 지수비중/펀드비중/액티브 틸트, 패시브 대비 수량 괴리
  ③ 전략 매매 내역 — mp.strategy_trade 원장 그대로 + 현재가 평가
  ④ 전략 성과·기여 — 매매 시점 일치 BM 대비 초과손익과 NAV 기여(bp)
를 렌더 완료된 HTML 조각으로 _build/pages/portfolio_content.html 에 쓴다.

🚨 이 조각은 **평문 그대로 저장소에 들어가지 않는다.** _build/ 는 gitignore 이고,
   배포는 build/kb_lock.py --page portfolio 가 AES-256-GCM 으로 잠가 portfolio.html 의
   PAYLOAD 에 넣는다(kb.html 과 같은 규약 — 열람 암호 없이는 소스를 봐도 못 푼다).
   실펀드 NAV·보유 수량·매매 내역이라 공개 사이트에 평문으로 나가면 안 된다.

입력 셋 — 전부 이 사내 PC 에서만 접근 가능하다(러너 이식 불가, 로컬 수동 잡).
  · 사내 export(엑셀): C:\HANSSAK\SecureGate\download\2Z30_MP_*.xlsm 중 최신
      NAV(날짜·펀드코드·NAV·좌수·기준가) · 환율(기준일자·통화·환율) · 해외(보유 원장)
      ⚠ 시트 이름·컬럼이 사내 시스템 export 규격이다. 바뀌면 여기가 아니라 규격이 바뀐 것.
  · 사내 DB(10.206.103.174): public.index_constituents(지수 비중·GICS) ·
      market.ohlcv_factset(종목 종가) · public.price_major_index(지수 레벨) ·
      mp.strategy_trade(전략 매매 원장 — MP 엑셀 VBA 가 쓴다)

자산구분 코드(해외 시트, 실측 2026-08-18): 1=개별주식 · 3=지수 ETF · 4=지수선물(평가액=노셔널)
  · 5=예금 · B=증거금. 선물 노셔널은 NAV 에 없고 노출에만 더한다 — 섞으면 합이 100%를 넘는다.

정의(화면 각주와 같아야 한다 — 렌더가 이 문서를 그대로 옮긴다):
  · 펀드비중 = 종목 평가액(원화) ÷ 개별주식 슬리브 합. 지수비중과 같은 눈금이 되도록
    주식 슬리브 안에서 정규화한다(펀드는 주식+ETF+선물로 지수를 복제하므로 NAV 분모로는
    전 종목이 일괄 언더웨이트로 보인다 — 그건 틸트가 아니라 구조다).
  · 패시브 수량 = 지수비중 × 주식슬리브(원) ÷ (종가 × USD환율). 괴리 = 실제 − 패시브.
  · 전략 수익률 = Σ수량×(현재가−체결가) ÷ 매수원금. 체결가는 원장의 trade_price 로,
    **당시 종가이지 실제 체결가가 아니다**(MP 엑셀 VBA 가 종가를 박는다).
  · BM 대조 = 같은 날 같은 금액을 지수에 넣었을 때의 손익(매매 시점 일치). 초과 = 차이.
  · NAV 기여(bp) = 초과손익(USD) × 기준일 환율 ÷ 기준일 NAV × 10,000.

한계(화면에 싣는다):
  · 배당 미반영 — ohlcv 종가는 수정주가가 아니다. 보유 2개월 내외라 왜곡은 작지만 0이 아니다.
  · 분할 가드 — 매매~기준일 사이 일수익 |40%| 초과가 있으면 해당 종목·전략에 ⚠를 단다
    (벤더가 분할을 소급 안 하는 사고를 랩이 실측했다: MNST 2026-08-11).

사용:  python build/portfolio_fund.py            # 조각 생성
       python build/kb_lock.py --page portfolio  # 잠가서 portfolio.html 에 기록(암호 입력)
"""
from __future__ import annotations

import datetime as dt
import glob
import html
import io
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_build", "pages", "portfolio_content.html")
XLSM_GLOB = r"C:\HANSSAK\SecureGate\download\2Z30_MP_*.xlsm"
DB = dict(host="10.206.103.174", port=5432, dbname="postgres",
          user="postgres", password="kbam", connect_timeout=12)

FUNDS = [
    ("2Z30", "NDX Index", "ndx", "나스닥100"),
    ("2A81", "SPX Index", "spx", "S&P500"),
]
SPLIT_GUARD = 0.40      # 매매 구간 일수익 절대값이 이걸 넘으면 분할 의심 ⚠


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def num(v, nd=2):
    """천 단위 구분 표기. None 은 —."""
    if v is None:
        return "—"
    if nd == 0:
        return format(int(round(float(v))), ",")
    return format(round(float(v), nd), ",.%df" % nd)


def pct(v, nd=2, signed=False):
    if v is None:
        return "—"
    s = ("%+." if signed else "%.") + str(nd) + "f"
    return (s % (v * 100)) + "%"


def cls_sign(v):
    return "pos" if (v or 0) > 0 else ("neg" if (v or 0) < 0 else "")


# ── 1) 사내 export 읽기 ──────────────────────────────────────────────────────
def load_xlsm():
    files = sorted(glob.glob(XLSM_GLOB), key=os.path.getmtime)
    if not files:
        raise SystemExit("사내 export 없음 — %s 에 2Z30_MP_*.xlsm 을 내려받을 것" % os.path.dirname(XLSM_GLOB))
    path = files[-1]
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)

    def d10(v):
        if isinstance(v, dt.datetime):
            return v.strftime("%Y-%m-%d")
        return str(v)[:10]

    nav = {}          # fund → {date: (nav, base_price)}
    for r in wb["NAV"].iter_rows(min_row=11, values_only=True):
        if not r[0]:
            break
        nav.setdefault(str(r[1]).strip(), {})[d10(r[0])] = (float(r[2]), float(r[4]))

    fx = {}           # date → USD 환율(종가 기준)
    for r in wb["환율"].iter_rows(min_row=11, values_only=True):
        if not r[0]:
            break
        if str(r[1]).strip() == "USD":
            fx[d10(r[0])] = float(r[2])

    hold = {}         # fund → {date: [보유행…]}
    for r in wb["해외"].iter_rows(min_row=11, values_only=True):
        if not r[0]:
            break
        hold.setdefault(str(r[0]).strip(), {}).setdefault(d10(r[4]), []).append({
            "ticker": (str(r[2]).strip() if r[2] else ""),
            "name": (str(r[3]).strip() if r[3] else ""),
            "qty": float(r[7] or 0), "val_usd": float(r[10] or 0),
            "val_krw": float(r[11] or 0), "asset": str(r[13]).strip(),
            "px": (float(r[18]) if r[18] not in (None, "") else None),
        })
    return path, nav, fx, hold


# ── 2) 사내 DB 읽기 ──────────────────────────────────────────────────────────
def load_db(asof_by_fund):
    import psycopg2
    cn = psycopg2.connect(**DB)
    cur = cn.cursor()

    cons = {}         # index → (dt, {ticker: (정규화 비중, 이름, GICS)})
    for _f, idx, _s, _l in FUNDS:
        cur.execute('SELECT max(dt) FROM public.index_constituents WHERE "index"=%s AND dt<=%s',
                    (idx, asof_by_fund[_f]))
        d = cur.fetchone()[0]
        cur.execute('SELECT ticker, index_weight, name, gics_name FROM public.index_constituents '
                    'WHERE "index"=%s AND dt=%s', (idx, d))
        rows = cur.fetchall()
        tot = sum(float(w or 0) for _t, w, _n, _g in rows) or 1.0
        cons[idx] = (str(d), {t: (float(w or 0) / tot, n, g) for t, w, n, g in rows})

    cur.execute('SELECT "index", dt, strategy, ticker, trade_qty, trade_price '
                'FROM mp.strategy_trade ORDER BY dt, strategy, ticker')
    trades = [dict(index=i, dt=str(d), strategy=s, ticker=t, qty=float(q), px=float(p or 0))
              for i, d, s, t, q, p in cur.fetchall()]

    px = {}           # ticker → {date: close}
    tickers = sorted({t["ticker"] for t in trades})
    if tickers:
        t0 = min(t["dt"] for t in trades)
        cur.execute("SELECT ticker, dt, value FROM market.ohlcv_factset "
                    "WHERE value_type='c' AND dt>=%s AND ticker = ANY(%s) ORDER BY ticker, dt",
                    (t0, [t + " EQUITY" for t in tickers]))
        for tk, d, v in cur.fetchall():
            if v is not None:
                px.setdefault(tk[:-7], {})[str(d)] = float(v)

    lvl = {}          # index → {date: level}
    cur.execute("SELECT ticker, dt, value FROM public.price_major_index "
                "WHERE ticker IN ('NDX Index','SPX Index') AND value_type='price' "
                "AND dt>='2025-12-30' ORDER BY dt")
    for tk, d, v in cur.fetchall():
        if v is not None:
            lvl.setdefault(tk, {})[str(d)] = float(v)
    cn.close()
    return cons, trades, px, lvl


def last_leq(series_dict, date):
    """{date: v} 에서 date 이하 마지막 (date, v). 없으면 (None, None)."""
    best = None
    for d in series_dict:
        if d <= date and (best is None or d > best):
            best = d
    return (best, series_dict[best]) if best else (None, None)


# ── 3) 전략 성과 계산 ────────────────────────────────────────────────────────
def strat_perf(trades, px, lvl_idx, asof_us):
    """전략 → {curve, last, rows, warn_split}. BM 은 매매 시점 일치 지수 투자.

    손익 = Σ qty×(px_t − 체결가). 매도(qty<0)도 같은 식이 성립한다 — 매도 시점에
    잠근 손익이 이후 가격변동과 상쇄되어 실현분으로 남는다.
    """
    out = {}
    dates = sorted(d for d in lvl_idx if d <= asof_us)
    for tr in trades:
        s = out.setdefault(tr["strategy"], {"trades": [], "tickers": {}})
        s["trades"].append(tr)
        s["tickers"].setdefault(tr["ticker"], []).append(tr)

    for _sname, s in out.items():
        t0 = min(t["dt"] for t in s["trades"])
        curve = []
        for d in [x for x in dates if x >= t0]:
            pnl = bm = inv = 0.0
            for tr in s["trades"]:
                if tr["dt"] > d:
                    continue
                _pd, p = last_leq(px.get(tr["ticker"], {}), d)
                if p is None:
                    continue
                pnl += tr["qty"] * (p - tr["px"])
                i_t = lvl_idx.get(d) or last_leq(lvl_idx, d)[1]
                i_0 = lvl_idx.get(tr["dt"]) or last_leq(lvl_idx, tr["dt"])[1]
                if i_t and i_0:
                    bm += tr["qty"] * tr["px"] * (i_t / i_0 - 1)
                if tr["qty"] > 0:
                    inv += tr["qty"] * tr["px"]
            curve.append((d, pnl, bm, inv))
        s["curve"] = curve

        # 분할 가드 — 보유 구간에 하루 ±40% 를 넘는 변동이 있으면 의심 표기
        warn = set()
        for tk, trs in s["tickers"].items():
            t_first = min(t["dt"] for t in trs)
            rows = sorted((d, p) for d, p in px.get(tk, {}).items() if t_first <= d <= asof_us)
            for (d1, p1), (d2, p2) in zip(rows, rows[1:]):
                if p1 and abs(p2 / p1 - 1) > SPLIT_GUARD:
                    warn.add(tk)
        s["warn_split"] = sorted(warn)

        if curve:
            d, pnl, bm, inv = curve[-1]
            s["last"] = dict(dt=d, pnl=pnl, bm=bm, inv=inv,
                             ret=(pnl / inv if inv else None), bm_ret=(bm / inv if inv else None))

        rows = []
        for tk, trs in sorted(s["tickers"].items()):
            _pd, p = last_leq(px.get(tk, {}), asof_us)
            if p is None:
                continue
            inv_t = sum(t["qty"] * t["px"] for t in trs if t["qty"] > 0)
            pnl_t = sum(t["qty"] * (p - t["px"]) for t in trs)
            bm_t = 0.0
            i_t = last_leq(lvl_idx, asof_us)[1]
            for t in trs:
                i_0 = lvl_idx.get(t["dt"]) or last_leq(lvl_idx, t["dt"])[1]
                if i_t and i_0:
                    bm_t += t["qty"] * t["px"] * (i_t / i_0 - 1)
            rows.append(dict(ticker=tk, qty=sum(t["qty"] for t in trs), inv=inv_t, px=p,
                             pnl=pnl_t, ret=(pnl_t / inv_t if inv_t else None),
                             exc=pnl_t - bm_t, warn=(tk in s["warn_split"])))
        rows.sort(key=lambda r: -r["exc"])
        s["rows"] = rows
    return out


# ── 4) SVG (파이썬에서 그린다 — 조각은 스크립트를 못 싣는다) ─────────────────
def svg_lines(series, labels=None, w=760, h=210, pad=40):
    """series = [(이름, [(x라벨, y)…])…]. y 눈금 상하한 + 0선만 — 장식은 셸 CSS 가 한다."""
    if not series or not series[0][1]:
        return ""
    ys = [y for _n, pts in series for _x, y in pts]
    lo, hi = min(ys), max(ys)
    if hi - lo < 1e-9:
        hi = lo + 1.0
    n = max(len(p) for _n, p in series)
    colors = ["var(--accent)", "var(--champ)", "var(--rp)", "var(--hot)", "var(--deploy)"]

    def X(i):
        return pad + (w - pad - 10) * (i / max(1, n - 1))

    def Y(v):
        return (h - 24) - (h - 44) * ((v - lo) / (hi - lo))

    parts = ['<svg viewBox="0 0 %d %d" role="img" style="width:100%%;height:auto">' % (w, h)]
    if lo < 0 < hi:
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="var(--line)" stroke-dasharray="3 3"/>'
                     % (pad, Y(0), w - 10, Y(0)))
    for k, (_name, pts) in enumerate(series):
        d = " ".join("%s%.1f,%.1f" % ("M" if i == 0 else "L", X(i), Y(v)) for i, (_x, v) in enumerate(pts))
        parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.8"/>' % (d, colors[k % len(colors)]))
    parts.append('<text x="2" y="14" font-size="10" fill="var(--muted)" font-family="var(--mono)">%.1f</text>' % hi)
    parts.append('<text x="2" y="%d" font-size="10" fill="var(--muted)" font-family="var(--mono)">%.1f</text>' % (h - 24, lo))
    x0 = series[0][1][0][0] if series[0][1] else ""
    x1 = series[0][1][-1][0] if series[0][1] else ""
    parts.append('<text x="%d" y="%d" font-size="10" fill="var(--muted)" font-family="var(--mono)">%s → %s</text>'
                 % (pad, h - 10, esc(x0), esc(x1)))
    if labels:
        lx = pad + 170
        for k, lb in enumerate(labels):
            parts.append('<text x="%d" y="%d" font-size="11" fill="%s" font-family="var(--mono)">━ %s</text>'
                         % (lx, h - 10, colors[k % len(colors)], esc(lb)))
            lx += 11 * len(lb) + 44
    parts.append("</svg>")
    return "".join(parts)


# ── 5) 렌더 ──────────────────────────────────────────────────────────────────
def render_fund(fund, idx, slug, label, nav, fx, hold, cons, trades, px, lvl):
    H = []
    asof = max(hold[fund])
    rows = hold[fund][asof]
    nav_d, nav_pair = last_leq(nav[fund], asof)
    nav_v, base_p = nav_pair
    _fx_d, fx_v = last_leq(fx, asof)

    by_asset = {}
    for r in rows:
        by_asset[r["asset"]] = by_asset.get(r["asset"], 0.0) + r["val_krw"]
    stocks = [r for r in rows if r["asset"] == "1"]
    sleeve = sum(r["val_krw"] for r in stocks) or 1.0
    w_stk = by_asset.get("1", 0) / nav_v
    w_etf = by_asset.get("3", 0) / nav_v
    w_fut = by_asset.get("4", 0) / nav_v          # 노셔널 — NAV 구성이 아니라 노출
    w_cash = (by_asset.get("5", 0) + by_asset.get("B", 0)) / nav_v

    # 연초 후 — 기준가 vs 지수(원화환산), 시작일 = 100
    lvl_i = lvl[idx]
    nav_ser = sorted(nav[fund].items())
    d0 = nav_ser[0][0]
    bp0 = nav[fund][d0][1]
    _i0d, i0 = last_leq(lvl_i, d0)
    _f0d, f0 = last_leq(fx, d0)
    fund_pts, bm_pts = [], []
    for d, (_n, bp) in nav_ser:
        _id, iv = last_leq(lvl_i, d)
        _fd, fv = last_leq(fx, d)
        if iv and fv and i0 and f0:
            fund_pts.append((d, bp / bp0 * 100))
            bm_pts.append((d, (iv * fv) / (i0 * f0) * 100))
    ytd_f = fund_pts[-1][1] / 100 - 1 if fund_pts else None
    ytd_b = bm_pts[-1][1] / 100 - 1 if bm_pts else None

    cons_d, cmap = cons[idx]

    my_trades = [t for t in trades if t["index"] == idx]
    asof_us = max((d for d in lvl_i if d <= asof), default=asof)
    perf = strat_perf(my_trades, px, lvl_i, asof_us) if my_trades else {}
    tot_exc = sum(s["last"]["pnl"] - s["last"]["bm"] for s in perf.values() if s.get("last"))
    tot_bp = tot_exc * fx_v / nav_v * 1e4 if perf else 0.0

    H.append('<section class="tabpane" id="pane-%s"%s>' % (slug, "" if slug == "ndx" else " hidden"))
    H.append('<div class="fhead"><h2>%s <span class="fcode">%s · %s</span></h2>'
             '<div class="asofline">보유·NAV·환율 %s · 지수비중 %s · 미국 종가 %s · USD %s</div></div>'
             % (esc(label), esc(fund), esc(idx), esc(asof), esc(cons_d), esc(asof_us), num(fx_v)))

    # ① 개요
    H.append('<h3>① 펀드 개요</h3><div class="cards">')
    cards = [
        ("순자산(NAV)", "%s억원" % num(nav_v / 1e8, 0), "기준가 " + num(base_p), 0),
        ("연초 후(기준가)", pct(ytd_f, 2, True), "지수(원화환산) " + pct(ytd_b, 2, True), ytd_f or 0),
        ("연초 후 초과", pct((ytd_f - ytd_b) if None not in (ytd_f, ytd_b) else None, 2, True),
         "기준가 − 지수·원화", (ytd_f - ytd_b) if None not in (ytd_f, ytd_b) else 0),
        ("전략 NAV 기여", ("%+.1f bp" % tot_bp) if perf else "—", "매매 시점 일치 BM 대비", tot_bp),
    ]
    for k, v, sub, sign in cards:
        H.append('<div class="card"><div class="ck">%s</div><div class="cv %s">%s</div><div class="cs">%s</div></div>'
                 % (esc(k), cls_sign(sign), esc(v), esc(sub)))
    H.append("</div>")
    H.append('<div class="chart">%s</div>' % svg_lines(
        [("펀드", fund_pts), ("지수", bm_pts)],
        labels=["펀드 기준가", "%s 원화환산" % idx.split()[0]]))
    H.append('<table class="mini"><thead><tr><th>자산 구성</th><th class="tnum">NAV 대비</th></tr></thead><tbody>')
    for lbl2, w in (("개별주식", w_stk), ("지수 ETF", w_etf), ("현금·증거금", w_cash)):
        H.append('<tr><td>%s</td><td class="tnum">%s</td></tr>' % (esc(lbl2), pct(w, 1)))
    H.append('<tr><td>지수선물 노셔널(별도)</td><td class="tnum">%s</td></tr>' % pct(w_fut, 1))
    H.append('<tr><td><b>총 지수 노출</b></td><td class="tnum"><b>%s</b></td></tr>' % pct(w_stk + w_etf + w_fut, 1))
    H.append("</tbody></table>")

    # ② 보유 vs 지수
    held = {}
    for r in stocks:
        h = held.setdefault(r["ticker"], {"qty": 0.0, "val": 0.0, "px": r["px"], "name": r["name"]})
        h["qty"] += r["qty"]
        h["val"] += r["val_krw"]
    n_match = sum(1 for t in held if t in cmap)
    tbl = []
    for t, h in held.items():
        w_f = h["val"] / sleeve
        w_i = cmap.get(t, (0.0, None, None))[0]
        gics = cmap.get(t, (None, None, ""))[2] or ""
        p_qty = (w_i * sleeve / (h["px"] * fx_v)) if (h["px"] and fx_v) else None
        tbl.append(dict(t=t, name=h["name"], gics=gics, wi=w_i, wf=w_f, d=(w_f - w_i) * 1e4,
                        qty=h["qty"], pq=p_qty, dq=(h["qty"] - p_qty) if p_qty is not None else None))
    tbl.sort(key=lambda r: -r["wf"])
    only_idx = sorted(((t, v[0], v[1]) for t, v in cmap.items() if t not in held and v[0] > 0.0005),
                      key=lambda x: -x[1])

    H.append('<h3>② 보유 vs 지수 <span class="hnote">주식 슬리브 %d종 · 지수 %d종</span></h3>'
             % (len(held), len(cmap)))
    H.append('<div class="filterbar"><input type="search" class="rowfilter" data-target="tb-%s" '
             'placeholder="티커·이름으로 거르기" aria-label="표 필터"></div>' % slug)
    H.append('<div class="tblwrap tall"><table class="big" id="tb-%s"><thead><tr>'
             '<th>티커</th><th>이름</th><th>섹터</th><th class="tnum">지수비중</th><th class="tnum">펀드비중</th>'
             '<th class="tnum">차이(bp)</th><th class="tnum">수량</th><th class="tnum">패시브수량</th><th class="tnum">괴리</th>'
             '</tr></thead><tbody>' % slug)
    for r in tbl:
        H.append('<tr><td class="tk">%s</td><td>%s</td><td class="sec">%s</td>'
                 '<td class="tnum">%s</td><td class="tnum">%s</td><td class="tnum %s">%+.0f</td>'
                 '<td class="tnum">%s</td><td class="tnum">%s</td><td class="tnum %s">%s</td></tr>'
                 % (esc(r["t"]), esc(r["name"][:26]), esc((r["gics"] or "")[:16]),
                    pct(r["wi"], 2), pct(r["wf"], 2), cls_sign(r["d"]), r["d"],
                    num(r["qty"], 0), num(r["pq"], 0) if r["pq"] is not None else "—",
                    cls_sign(r["dq"] or 0), ("%+d" % round(r["dq"])) if r["dq"] is not None else "—"))
    H.append("</tbody></table></div>")
    if only_idx:
        H.append('<details><summary>지수에 있는데 미보유 %d종 (지수비중 0.05%% 이상)</summary>'
                 '<div class="tblwrap"><table class="mini"><tbody>' % len(only_idx))
        for t, w, nm in only_idx[:80]:
            H.append('<tr><td class="tk">%s</td><td>%s</td><td class="tnum">%s</td></tr>'
                     % (esc(t), esc((nm or "")[:30]), pct(w, 2)))
        H.append("</tbody></table></div></details>")

    # ③ 매매 내역
    H.append('<h3>③ 전략 매매 내역 <span class="hnote">mp.strategy_trade 원장 · 체결가 = 당시 종가(실제 체결가 아님)</span></h3>')
    if my_trades:
        H.append('<div class="tblwrap"><table class="big"><thead><tr><th>일자</th><th>전략</th><th>티커</th>'
                 '<th class="tnum">수량</th><th class="tnum">체결가</th><th class="tnum">금액(USD)</th>'
                 '<th class="tnum">현재가</th><th class="tnum">평가손익</th></tr></thead><tbody>')
        for t in my_trades:
            _pd, p = last_leq(px.get(t["ticker"], {}), asof_us)
            pnl = t["qty"] * (p - t["px"]) if p is not None else None
            H.append('<tr%s><td>%s</td><td>%s</td><td class="tk">%s</td><td class="tnum">%s</td>'
                     '<td class="tnum">%s</td><td class="tnum">%s</td><td class="tnum">%s</td>'
                     '<td class="tnum %s">%s</td></tr>'
                     % (' class="warnrow"' if t["qty"] == 0 else "",
                        esc(t["dt"]), esc(t["strategy"]), esc(t["ticker"]), num(t["qty"], 0),
                        num(t["px"]), num(t["qty"] * t["px"], 0), num(p) if p is not None else "—",
                        cls_sign(pnl or 0), num(pnl, 0) if pnl is not None else "—"))
        H.append("</tbody></table></div>")
        zeros = [t for t in my_trades if t["qty"] == 0]
        if zeros:
            H.append('<p class="warn">⚠ 수량 0 인 행 %d건 — 매매가 아니라 입력 흔적이다. 원장에서 지우는 게 맞다.</p>' % len(zeros))
    else:
        H.append("<p>이 지수에는 아직 전략 매매가 없다.</p>")

    # ④ 성과·기여
    H.append('<h3>④ 전략 성과·기여 <span class="hnote">BM = 같은 날 같은 금액을 지수에(매매 시점 일치)</span></h3>')
    if perf:
        H.append('<div class="tblwrap"><table class="big"><thead><tr><th>전략</th><th class="tnum">매수원금(USD)</th>'
                 '<th class="tnum">손익</th><th class="tnum">수익률</th><th class="tnum">BM</th>'
                 '<th class="tnum">초과</th><th class="tnum">NAV 기여(bp)</th></tr></thead><tbody>')
        for sname, s in sorted(perf.items()):
            L = s.get("last") or {}
            exc = L.get("pnl", 0) - L.get("bm", 0)
            contrib = exc * fx_v / nav_v * 1e4
            wmark = (" ⚠분할의심 " + ",".join(s["warn_split"])) if s["warn_split"] else ""
            H.append('<tr><td>%s%s</td><td class="tnum">%s</td><td class="tnum %s">%s</td>'
                     '<td class="tnum">%s</td><td class="tnum">%s</td><td class="tnum %s">%s</td>'
                     '<td class="tnum %s">%+.1f</td></tr>'
                     % (esc(sname), esc(wmark), num(L.get("inv"), 0), cls_sign(L.get("pnl")), num(L.get("pnl"), 0),
                        pct(L.get("ret"), 2, True), pct(L.get("bm_ret"), 2, True),
                        cls_sign(exc), num(exc, 0), cls_sign(contrib), contrib))
        H.append("</tbody></table></div>")
        series = []
        for sname, s in sorted(perf.items()):
            pts = [(d, (pnl - bm) / inv * 100 if inv else 0.0) for d, pnl, bm, inv in s["curve"]]
            if pts:
                series.append((sname, pts))
        if series:
            H.append('<div class="chart"><div class="chtitle">전략별 누적 초과수익(%%, 매수원금 대비)</div>%s</div>'
                     % svg_lines(series, labels=[n[:16] for n, _p in series]))
        for sname, s in sorted(perf.items()):
            if not s.get("rows"):
                continue
            H.append('<details><summary>%s — 종목별 분해</summary><div class="tblwrap"><table class="mini"><thead><tr>'
                     '<th>티커</th><th class="tnum">순수량</th><th class="tnum">현재가</th><th class="tnum">손익(USD)</th>'
                     '<th class="tnum">수익률</th><th class="tnum">초과(USD)</th></tr></thead><tbody>' % esc(sname))
            for r in s["rows"]:
                H.append('<tr><td class="tk">%s%s</td><td class="tnum">%s</td><td class="tnum">%s</td>'
                         '<td class="tnum %s">%s</td><td class="tnum">%s</td><td class="tnum %s">%s</td></tr>'
                         % (esc(r["ticker"]), " ⚠" if r["warn"] else "", num(r["qty"], 0), num(r["px"]),
                            cls_sign(r["pnl"]), num(r["pnl"], 0), pct(r["ret"], 2, True),
                            cls_sign(r["exc"]), num(r["exc"], 0)))
            H.append("</tbody></table></div></details>")
    else:
        H.append("<p>전략 매매가 없어 성과를 계산할 것이 없다.</p>")

    H.append("</section>")
    return "\n".join(H), dict(fund=fund, asof=asof, nav_d=nav_d, sleeve_ratio=w_stk,
                              n_stocks=len(held), n_match=n_match, n_cons=len(cmap))



FRAG_SCRIPT = """<script>
(function(){
  var tabs=document.querySelectorAll('#content .tb');
  function show(id){
    tabs.forEach(function(x){x.setAttribute('aria-selected', x.dataset.tab===id?'true':'false');});
    document.querySelectorAll('#content .tabpane').forEach(function(pn){pn.hidden=(pn.id!=='pane-'+id);});
  }
  tabs.forEach(function(t){t.addEventListener('click',function(){show(t.dataset.tab);});});
  document.querySelectorAll('#content .rowfilter').forEach(function(inp){
    inp.addEventListener('input',function(){
      var q=inp.value.trim().toUpperCase();
      var tb=document.getElementById(inp.dataset.target);
      if(!tb)return;
      tb.querySelectorAll('tbody tr').forEach(function(tr){
        tr.hidden=!!q&&tr.textContent.toUpperCase().indexOf(q)<0;
      });
    });
  });
})();
</script>"""

NOTES = """<div class="notes"><h3>정의·한계</h3><ul>
<li><b>펀드비중</b>은 종목 평가액(원화)을 개별주식 슬리브 합으로 나눈 것이다 — 지수비중과 같은 눈금이 되도록 주식 안에서 정규화했다. 펀드는 주식+ETF+선물로 지수를 복제하므로 NAV 분모로 보면 전 종목이 일괄 언더웨이트로 보인다.</li>
<li><b>패시브 수량</b> = 지수비중 × 주식슬리브(원) ÷ (종가 × USD환율). 괴리 = 실제 − 패시브. 액티브 틸트의 수량 표현이다.</li>
<li><b>체결가는 당시 종가다</b> — 실제 체결가가 아니다(원장을 쓰는 MP 엑셀이 종가를 박는다). 수익률·기여는 그만큼 근사치다.</li>
<li><b>BM 대조</b>는 같은 날 같은 금액을 지수에 넣었을 때의 손익이다(매매 시점 일치). 초과 = 전략 손익 − BM 손익. <b>NAV 기여(bp)</b> = 초과(USD) × 기준일 환율 ÷ NAV × 10,000.</li>
<li><b>배당 미반영</b> — 종가는 수정주가가 아니다. 보유 기간이 짧아 왜곡은 작지만 0이 아니다.</li>
<li>매매~기준일 사이 하루 ±40%를 넘는 가격변동이 있으면 <b>분할 의심 ⚠</b>를 단다 — 벤더가 분할을 소급 반영하지 않은 사고가 실측된 바 있다.</li>
<li>입력: 사내 시스템 export(NAV·환율·보유)와 사내 매매 원장. 갱신은 수동이다 — 상단의 생성 시각이 곧 이 화면의 기준이다.</li>
</ul></div>"""


def main() -> int:
    path, nav, fx, hold = load_xlsm()
    print("입력: %s" % os.path.basename(path))
    for f, _i, _s, _l in FUNDS:
        if f not in hold:
            raise SystemExit("해외 시트에 펀드 %s 가 없다 — export 범위를 확인할 것" % f)
        if f not in nav:
            raise SystemExit("NAV 시트에 펀드 %s 가 없다" % f)
    asof_by_fund = {f: max(hold[f]) for f, _i, _s, _l in FUNDS}
    cons, trades, px, lvl = load_db(asof_by_fund)

    panes, checks = [], []
    for f, idx, slug, label in FUNDS:
        pane, chk = render_fund(f, idx, slug, label, nav, fx, hold, cons, trades, px, lvl)
        panes.append(pane)
        checks.append(chk)

    # ── 실행 검산 — 화면에 내보내기 전에 여기서 막는다 ─────────────────────
    for c in checks:
        if not (0.3 <= c["sleeve_ratio"] <= 1.05):
            raise SystemExit("%s 주식슬리브/NAV=%.2f — 자산구분 해석이 깨졌다" % (c["fund"], c["sleeve_ratio"]))
        if c["n_match"] < c["n_stocks"] * 0.95:
            raise SystemExit("%s 보유 %d종 중 지수 매칭 %d — 티커 형식이 어긋났다"
                             % (c["fund"], c["n_stocks"], c["n_match"]))
        if c["nav_d"] != c["asof"]:
            print("⚠ %s NAV 기준일(%s) ≠ 보유 기준일(%s) — 이하 최근값으로 대체" % (c["fund"], c["nav_d"], c["asof"]))

    gen = dt.datetime.now().strftime("%Y-%m-%d %H:%M KST")
    tabs = "".join('<button class="tb" data-tab="%s" aria-selected="%s">%s · %s</button>'
                   % (slug, "true" if k == 0 else "false", label, f)
                   for k, (f, _i, slug, label) in enumerate(FUNDS))
    frag = ['<div class="pfhead"><div class="tabs" role="tablist">%s</div>'
            '<div class="gen">생성 %s · 입력 %s</div></div>' % (tabs, esc(gen), esc(os.path.basename(path)))]
    frag += panes
    frag.append(NOTES)
    frag.append(FRAG_SCRIPT)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    body = "\n".join(frag)
    io.open(OUT, "w", encoding="utf-8", newline="").write(body)
    print("→ %s (%.0fKB)" % (os.path.relpath(OUT, ROOT), len(body.encode("utf-8")) / 1024))
    for c in checks:
        print("   %s: 보유 %s · 주식 %d종(지수 매칭 %d) · 슬리브/NAV %.1f%%"
              % (c["fund"], c["asof"], c["n_stocks"], c["n_match"], c["sleeve_ratio"] * 100))
    print("다음: python build/kb_lock.py --page portfolio   (열람 암호 입력 → portfolio.html 에 기록)")
    return 0


if __name__ == "__main__":
    import gate
    gate.run(main, "운용 포트폴리오")
