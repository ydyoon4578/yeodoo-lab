# -*- coding: utf-8 -*-
"""build/asset_backtest.py — 아카이브의 '못 돌린 것'을 실제로 돌린다 → data/asset_strategies.json

배경. 아카이브는 38건을 '이 저장소 데이터로는 재현할 수 없다'로 두고 있었다. 다시 점검해 보니
그중 대부분은 **세상에 데이터가 없는 게 아니라 이 저장소가 안 갖고 있었을 뿐**이었다 —
자산 단위 패널(build/refresh_assets.py)을 만들자 ETF 가격과 FRED 거시만으로 돌아간다.
여기서 돌릴 수 있는 것을 돌리고, 정말 못 도는 것은 **무엇이 없어서인지**만 남긴다.

규약은 이 랩의 기본값 그대로다 — 월말 리밸런스·동일가중(또는 규칙이 정한 가중)·무비용(gross).
지표 정의(CAGR·샤프·MDD·t)는 build/tech_backtest.py에서 import한다. 복제하면 표가 갈린다.

판정. 각 전략은 **자기에게 정당한 대조군**과 겨룬다. 지수(SPY)를 아무 데나 갖다 붙이면
'벤치 부정합' 기각이 되는데, 그건 전략이 아니라 비교의 잘못이다(아카이브에 그 사고가 있다).
대조군은 전략마다 명시한다.

  python build/asset_backtest.py
"""
from __future__ import annotations
import datetime as dt
import io, json, math, os, sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tech_backtest import ann_stats, tstat, maxdd, curve_pack  # noqa: E402  정의를 복제하지 않는다

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "asset_strategies.json")

A = None          # 자산 패널
DTS = []          # 날짜
RF = {}


# ── 도우미 ──────────────────────────────────────────────────────────────
def ser(t):
    return A["px"].get(t)


def ret(s, i, n):
    if i < n or s[i] is None or s[i - n] is None or s[i - n] == 0:
        return None
    return s[i] / s[i - n] - 1


def vol(s, i, n):
    if i < n:
        return None
    rs = []
    for j in range(i - n + 1, i + 1):
        if s[j] is not None and s[j - 1]:
            rs.append(s[j] / s[j - 1] - 1)
    if len(rs) < n // 2:
        return None
    m = sum(rs) / len(rs)
    return math.sqrt(sum((x - m) ** 2 for x in rs) / max(1, len(rs) - 1))


def alive(t, i):
    s = ser(t)
    return s is not None and s[i] is not None


def month_ends(lo, hi):
    return [i for i in range(lo, hi - 1) if DTS[i][:7] != DTS[i + 1][:7]]


def macro_asof(sid, d):
    """발표일 기준 최신값 — 미래 값을 끌어오지 않는다."""
    m = A["macro"].get(sid) or {}
    k = None
    for key in sorted(m):
        if key <= d:
            k = key
        else:
            break
    return m.get(k) if k else None


def run_weights(wfn, start, label, bench_w, rule, why, note=None,
                cadence="month", bench_cadence=None):
    """wfn(i) -> {티커: 비중}. 정해진 주기에만 호출하고 그 사이는 보유.
    ⚠ bench_cadence를 안 주면 대조군도 같은 주기를 쓴다. '주기 변형' 전략에서 이걸 빠뜨리면
      전략과 대조군이 **완전히 같은 계열**이 되어 t가 정의되지 않는다(실제로 그렇게 났다)."""
    n = len(DTS)
    def _ends(c):
        if c == "month":
            return set(month_ends(start, n))
        if c == "quarter":
            return {i for i in month_ends(start, n) if DTS[i][5:7] in ("03", "06", "09", "12")}
        return set(range(start, n))
    ends = _ends(cadence)
    bends = _ends(bench_cadence or cadence)
    def walk(fn, ends):
        hold, nav, rets, turn = {}, [100.0], [], 0.0
        for i in range(start + 1, n):
            if (i - 1) in ends or not hold:
                w = fn(i - 1) or {}
                tot = sum(w.values())
                if tot > 0:
                    w = {k: v / tot for k, v in w.items() if v > 0}
                    turn += sum(abs(w.get(k, 0) - hold.get(k, 0)) for k in set(w) | set(hold))
                    hold = w
            r = 0.0
            for t, wt in hold.items():
                s = ser(t)
                if s and s[i] is not None and s[i - 1]:
                    r += wt * (s[i] / s[i - 1] - 1)
            rets.append(r)
            nav.append(nav[-1] * (1 + r))
        return nav, rets, turn
    nav, rets, turn = walk(wfn, ends)
    bnav, brets, _ = walk(bench_w, bends)

    # 대조군이 무엇인지 화면에 적으려면 이름이 있어야 한다. 35개 호출부에 인자를 하나씩
    # 더 붙이는 대신 가중치에서 뽑는다 — 대조군은 결국 '무엇을 얼마나 들고 있나'가 전부다.
    # 시작과 끝의 구성이 다르면 정적 라벨이 거짓이 되므로 '동적'이라고 적는다.
    def _blabel(fn):
        try:
            w0, w1 = fn(start) or {}, fn(n - 1) or {}
        except Exception:
            return None
        if not w0:
            return None
        if set(w0) != set(w1) or any(abs(w0[k] - w1.get(k, 0)) > 1e-9 for k in w0):
            return "동적 배분(%d자산)" % len(set(w0) | set(w1))
        tot = sum(w0.values()) or 1.0
        parts = sorted(((k, 100 * v / tot) for k, v in w0.items()), key=lambda z: -z[1])
        if len(parts) == 1:
            return "%s 상시보유" % parts[0][0]
        if len(parts) <= 4:
            return " · ".join("%s %d%%" % (k, round(p)) for k, p in parts)
        return "%d자산 동일가중" % len(parts)
    bench_label = _blabel(bench_w)

    # 대조군 구성 티커 — 라벨은 5자산 이상이면 "N자산 동일가중"으로 접혀 티커를 잃는다.
    # 화면·필터가 "이 대조군에 채권이 섞였나" 같은 질문을 하려면 구성을 알아야 하는데,
    # 한글 라벨을 파싱해 알아내는 건 부서지기 쉽다 — 구조로 싣는다.
    def _btk(fn):
        try:
            w = fn(start) or {}
        except Exception:
            return []
        return sorted(w)
    bench_tickers = _btk(bench_w)
    # 지금 뭘 들고 있나 — 이게 안 보이면 규칙을 읽어도 실제로 쓸 수가 없다.
    try:
        _w = wfn(n - 1) or {}
        _tot = sum(_w.values())
        hold_now = {"kind": "asset", "as_of": DTS[-1],
                    "weights": sorted(((k, round(100 * v / _tot, 1)) for k, v in _w.items() if v > 0),
                                      key=lambda z: -z[1])} if _tot > 0 else None
    except Exception:
        hold_now = None
    dd = DTS[start:]
    ms, mb = ann_stats(nav, dd, RF), ann_stats(bnav, dd, RF)
    yrs = max(1e-9, (n - start) / 252)
    step = max(1, len(nav) // 220)
    # ⚠ 대조군이 현금성(변동성 ~0)이면 샤프 차이가 허수가 된다 — 분모가 0에 가까워
    #   작은 수익 차이가 샤프 몇 단위로 증폭된다(실측: MNA vs SHY에서 Δ샤프 +1.67).
    #   그 경우 Δ샤프를 판정에 쓰지 않고 t만 본다. 화면에도 그 사실을 표시한다.
    unstable = (mb.get("vol") or 0) < 2.0
    chart = curve_pack(dd, nav, bnav)
    return {"name": label, "rule": rule, "why": why, "note": note, "chart": chart,
            "start": DTS[start], "end": DTS[-1], "n_days": n - start,
            "metrics": ms, "bench": mb, "bench_label": bench_label, "bench_tickers": bench_tickers,
            "bench_unstable": unstable, "holdings": hold_now,
            "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
            "t": tstat(rets, brets), "turnover": round(turn / 2 / yrs, 1),
            "nav": [round(x, 2) for x in nav[::step]],
            "bnav": [round(x, 2) for x in bnav[::step]]}


def first_common(ts, pad=260):
    """전 자산이 살아 있는 첫 인덱스 + 워밍업."""
    for i in range(len(DTS)):
        if all(alive(t, i) for t in ts):
            return min(len(DTS) - 1, i + pad)
    return len(DTS)


# ── 전략 ────────────────────────────────────────────────────────────────
OUT_ROWS = []


# 성격(role) — 통합 목록에서 '무엇을 하는 전략인가'로 묶는 축(strategy_kinds.json 어휘).
# 파일 출처가 아니라 역할로 나눠야 읽는 사람이 비교할 수 있다. 자산 전략은 규칙마다 하는 일이
# 달라 하나로 못 묶는다 — 비중을 정하면 배분기, 들어갈지 말지만 정하면 타이밍오버레이,
# 위기에만 값을 하면 방어보험, 초과수익 자체가 목적이면 수익엔진.
ROLE = {
    "curve-carry": "타이밍오버레이", "tsmom-multi": "타이밍오버레이", "tail-hedge": "방어보험",
    "macro-rot": "타이밍오버레이", "infl-real": "타이밍오버레이", "hrp-alloc": "배분기",
    "commod-tsmom": "타이밍오버레이", "rp-extended": "배분기", "vix-ts": "타이밍오버레이",
    "gem": "타이밍오버레이", "vol-roll": "방어보험", "real-yield": "타이밍오버레이",
    "crypto-sat": "배분기", "sector-rp": "배분기", "bond-trend": "타이밍오버레이",
    "mf-satellite": "배분기", "credit-gate": "타이밍오버레이", "overnight": "수익엔진",
    "merger-arb": "수익엔진", "min-cvar": "배분기", "rp-voltarget": "위험감축",
    "rp-cadence": "배분기", "rp-horizon": "타이밍오버레이", "overnight-ndx": "수익엔진",
    "vrp-shortvol": "수익엔진", "credit-bond-gate": "타이밍오버레이", "ebp-gate": "타이밍오버레이",
    "quality-tilt": "수익엔진", "carry": "수익엔진", "hrp-sleeve": "배분기",
    "regime-switch": "타이밍오버레이", "ml-timing": "타이밍오버레이",
    "ml-xsec": "수익엔진", "guru-clone": "수익엔진",
}


def add(sid, arch, fn):
    OUT_ROWS.append((sid, arch, fn))


def build():
    # 1) 상품 커브 캐리 — GLD/DBC
    def s_curve():
        ts = ["GLD", "DBC", "SHY"]
        st = first_common(ts)
        def w(i):
            # 12-1 모멘텀이 양수인 실물만 편입, 없으면 단기채로 대피
            picks = {t: 1.0 for t in ("GLD", "DBC")
                     if (ret(ser(t), i, 252) or -1) - (ret(ser(t), i, 21) or 0) > 0}
            return picks or {"SHY": 1.0}
        return run_weights(w, st, "상품 커브 캐리 (GLD/DBC)",
                           lambda i: {"GLD": 0.5, "DBC": 0.5},
                           "월말에 GLD·DBC 중 12-1 모멘텀이 양수인 것만 동일가중, 없으면 SHY.",
                           "아카이브 사유는 '95%CI가 0을 교차하고 유니버스가 얕다'였다. "
                           "얕은 것은 사실이지만 데이터가 없어서 못 돌 이유는 없었다 — 대조군을 "
                           "GLD·GLD/DBC 상시보유로 두고 실제로 겨룬다.")
    add("curve-carry", "commodity-curve-carry", s_curve)

    # 2) 멀티에셋 시계열 모멘텀(CTA)
    def s_tsmom():
        ts = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "VNQ", "SHY"]
        st = first_common(ts)
        risky = ts[:-1]
        def w(i):
            picks = {t: 1.0 for t in risky if (ret(ser(t), i, 252) or -1) > 0}
            return picks or {"SHY": 1.0}
        return run_weights(w, st, "시계열 모멘텀 — 멀티에셋 (CTA)",
                           lambda i: {t: 1.0 for t in risky},
                           "월말에 8자산 중 12개월 수익이 양수인 것만 동일가중, 없으면 SHY.",
                           "CTA의 교과서판. 대조군은 같은 8자산 상시 동일가중 — "
                           "'고르는 것'이 '다 들고 있기'를 이기는지만 본다.")
    add("tsmom-multi", "tsmom-multiasset", s_tsmom)

    # 3) 테일 리스크 헤지 (long-vol 위성)
    def s_tail():
        ts = ["SPY", "VIXY"]
        st = first_common(ts, pad=20)
        return run_weights(lambda i: {"SPY": 0.95, "VIXY": 0.05}, st,
                           "테일 리스크 헤지 (SPY 95% + VIXY 5%)",
                           lambda i: {"SPY": 1.0},
                           "월말에 SPY 95% · VIXY 5%로 되돌린다(상시 보험).",
                           "상시 비용을 내고 꼬리를 사는 구조. 대조군은 보험을 안 든 SPY 100%다. "
                           "낙폭이 얼마나 줄고 그 대가가 얼마인지가 전부다.")
    add("tail-hedge", "tail-risk-hedge", s_tail)

    # 4) 매크로 레짐 안전자산 로테이션
    def s_macro():
        ts = ["SPY", "TLT", "GLD", "SHY"]
        st = first_common(ts)
        def w(i):
            d = DTS[i]
            sp = macro_asof("T10Y2Y", d)          # 기간스프레드
            un = macro_asof("UNRATE", d)
            risk_off = (sp is not None and sp < 0) or (un is not None and un > 5.5)
            return {"TLT": 0.5, "GLD": 0.5} if risk_off else {"SPY": 1.0}
        return run_weights(w, st, "매크로 레짐 안전자산 로테이션",
                           lambda i: {"SPY": 0.6, "TLT": 0.3, "GLD": 0.1},
                           "장단기 금리차가 역전이거나 실업률이 5.5%를 넘으면 TLT·GLD로, "
                           "아니면 SPY 100%.",
                           "거시 국면으로 위험을 켜고 끈다. 대조군은 같은 자산의 정적 60/30/10 — "
                           "'국면 판단'이 '그냥 섞어두기'를 이기는지 본다.")
    add("macro-rot", "macro-regime-defensive-rotation", s_macro)

    # 5) 인플레 국면 실물자산
    def s_infl():
        ts = ["SPY", "TIP", "GLD", "DBC", "VNQ"]
        st = first_common(ts)
        real = ["TIP", "GLD", "DBC", "VNQ"]
        def w(i):
            be = macro_asof("T10YIE", DTS[i])     # 기대인플레
            hot = be is not None and be > 2.3
            return {t: 1.0 for t in real} if hot else {"SPY": 1.0}
        return run_weights(w, st, "인플레이션 국면 실물자산 배분",
                           lambda i: {t: 1.0 for t in real},
                           "10년 기대인플레가 2.3%를 넘으면 실물 4종 동일가중, 아니면 SPY.",
                           "아카이브 재검에서 '실체는 인플레 헤지가 아니라 금 추세추종'이었다. "
                           "대조군을 패시브 실물 바스켓으로 두고 그 판정이 유지되는지 본다.")
    add("infl-real", "inflation-regime-real-assets", s_infl)

    # 6) 계층적 리스크패리티(HRP) 배분
    def s_hrp():
        ts = ["SPY", "EFA", "EEM", "TLT", "IEF", "LQD", "GLD", "DBC", "VNQ"]
        st = first_common(ts)
        def w(i):
            # 완전한 HRP(덴드로그램)까지 가지 않고, 그 핵심인 **역분산 재귀 이등분**만 쓴다.
            # 상관 군집을 추정할 표본이 짧을수록 트리가 불안정해 오히려 잡음을 키우기 때문이다.
            iv = {}
            for t in ts:
                v = vol(ser(t), i, 120)
                if v and v > 0:
                    iv[t] = 1.0 / v
            return iv
        return run_weights(w, st, "계층적 리스크패리티 배분 (역분산판)",
                           lambda i: {t: 1.0 for t in ts},
                           "월말에 120일 실현변동성의 역수로 9자산을 가중.",
                           "HRP의 실질은 '변동성 큰 자산의 비중을 줄이는 것'이다. "
                           "대조군은 같은 9자산 동일가중 — 가중 방식만 다르다.")
    add("hrp-alloc", "hrp-allocation", s_hrp)

    # 7) 원자재 TSMOM
    def s_ctsmom():
        ts = ["GLD", "SLV", "DBC", "USO", "UNG", "SHY"]
        st = first_common(ts)
        cm = ts[:-1]
        def w(i):
            picks = {t: 1.0 for t in cm if (ret(ser(t), i, 252) or -1) > 0}
            return picks or {"SHY": 1.0}
        return run_weights(w, st, "원자재 시계열 모멘텀",
                           lambda i: {t: 1.0 for t in cm},
                           "월말에 원자재 5종 중 12개월 수익이 양수인 것만 동일가중, 없으면 SHY.",
                           "롤 캐리는 선물 커브가 있어야 계산되지만, 추세 부분은 ETF만으로 된다. "
                           "즉 '롤 캐리 없는 반쪽'을 정직하게 돌린 것이다.",
                           note="원 규칙의 롤 캐리 항은 무료 선물 커브가 없어 뺐다 — 추세 항만이다.")
    add("commod-tsmom", "commodity-tsmom-roll-carry", s_ctsmom)

    # 8) 크로스에셋 RP 확장 유니버스
    def s_rpx():
        base = ["SPY", "TLT", "GLD", "DBC"]
        ext = base + ["TIP", "EMB", "SLV"]
        st = first_common(ext)
        def iv(ts):
            def f(i):
                o = {}
                for t in ts:
                    v = vol(ser(t), i, 120)
                    if v and v > 0:
                        o[t] = 1.0 / v
                return o
            return f
        return run_weights(iv(ext), st, "크로스에셋 RP — 자산군 확장 (TIP·EMB·SLV)",
                           iv(base),
                           "월말에 역변동성 가중. 확장 유니버스(7자산) vs 기본(4자산).",
                           "아카이브 사유는 '넓은 분산 희석 Δ−0.007'이었다. 같은 비교를 "
                           "공개 데이터로 재현해 그 수치가 서는지 본다.")
    add("rp-extended", "cross-asset-rp-extended", s_rpx)

    # 9) VIX 기간구조 신호
    def s_vixts():
        ts = ["SPY", "SHY"]
        st = first_common(ts + ["^VIX", "^VIX3M"])
        v1, v3 = ser("^VIX"), ser("^VIX3M")
        def w(i):
            if v1[i] is None or v3[i] is None or not v3[i]:
                return {"SPY": 1.0}
            return {"SPY": 1.0} if (v1[i] / v3[i]) < 1.0 else {"SHY": 1.0}   # 콘탱고면 편입
        return run_weights(w, st, "VIX 기간구조 신호 (VIX/VIX3M)",
                           lambda i: {"SPY": 1.0},
                           "VIX/VIX3M이 1 미만(콘탱고)이면 SPY, 1 이상(백워데이션)이면 SHY. 월말 판정.",
                           "아카이브 사유는 '실현변동성 타깃과 중복 corr 0.988'이었다. "
                           "중복 여부와 별개로 단독 성과는 잰 적이 없어 여기서 잰다.")
    add("vix-ts", "vix-term-structure", s_vixts)

    # 10) 글로벌 듀얼 모멘텀(GEM)
    def s_gem():
        ts = ["SPY", "VEU", "BND", "SHY"]
        st = first_common(ts)
        def w(i):
            rs, rv = ret(ser("SPY"), i, 252), ret(ser("VEU"), i, 252)
            rb = ret(ser("SHY"), i, 252) or 0
            best = "SPY" if (rs or -9) >= (rv or -9) else "VEU"
            return {best: 1.0} if (ret(ser(best), i, 252) or -9) > rb else {"BND": 1.0}
        return run_weights(w, st, "글로벌 듀얼 모멘텀 (GEM)",
                           lambda i: {"SPY": 0.6, "BND": 0.4},
                           "12개월 수익이 큰 쪽(SPY vs VEU)을 고르되, 단기채보다 낮으면 BND. 월말.",
                           "아카이브 사유는 'SPY·60/40 열위'였다. 대조군을 60/40으로 명시해 재현한다.")
    add("gem", "dual-momentum-gem", s_gem)

    # 11) 변동성 기간구조 롤 (VIXY/VXZ)
    def s_volroll():
        ts = ["VIXY", "VXZ"]
        st = first_common(ts, pad=20)
        return run_weights(lambda i: {"VXZ": 1.0}, st,
                           "변동성 기간구조 롤 (VXZ 보유)",
                           lambda i: {"VIXY": 1.0},
                           "중기 VIX 선물(VXZ)을 보유. 대조군은 단기(VIXY).",
                           "단기물의 롤 손실이 중기물보다 크다는 명제를 직접 건다. "
                           "둘 다 장기 우하향이라 '덜 잃는 쪽'을 가리는 비교다.",
                           note="2018년 재상장 이후 구간만 존재한다 — 그 전 이력은 상품이 없다.")
    add("vol-roll", "vol-term-structure-roll", s_volroll)

    # 12) 실질금리 레짐 오버레이
    def s_realyield():
        ts = ["SPY", "GLD", "SHY"]
        st = first_common(ts)
        def w(i):
            ry = macro_asof("DFII10", DTS[i])
            if ry is None:
                return {"SPY": 1.0}
            return {"GLD": 1.0} if ry < 0.5 else {"SPY": 1.0}
        return run_weights(w, st, "실질금리 레짐 오버레이 (DFII10)",
                           lambda i: {"SPY": 0.5, "GLD": 0.5},
                           "10년 실질금리가 0.5% 미만이면 GLD, 이상이면 SPY. 월말 판정.",
                           "낮은 실질금리가 금에 유리하다는 통설을 규칙으로 건다. "
                           "대조군은 SPY·GLD 반반 상시보유다.")
    add("real-yield", "real-yield-regime-overlay", s_realyield)

    # 13) 크립토 변동성 타깃 위성
    def s_crypto():
        ts = ["SPY", "BTC-USD", "SHY"]
        st = first_common(ts, pad=120)
        def w(i):
            v = vol(ser("BTC-USD"), i, 60)
            if not v or v <= 0:
                return {"SPY": 1.0}
            k = min(0.05, 0.10 / (v * math.sqrt(252)))   # 목표 연 10% 기여, 상한 5%
            return {"SPY": 1.0 - k, "BTC-USD": k}
        return run_weights(w, st, "디지털자산 변동성 타깃 위성",
                           lambda i: {"SPY": 1.0},
                           "BTC 비중을 60일 실현변동성 기준 목표에 맞춰 0~5%로 조절, 나머지 SPY. 월말.",
                           "변동성으로 크기를 조인 위성이 본체를 개선하는지. 대조군은 SPY 100%.")
    add("crypto-sat", "crypto-vol-target-satellite", s_crypto)

    # 14) 섹터 리스크패리티
    def s_sectrp():
        ts = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]
        st = first_common(ts)
        def w(i):
            o = {}
            for t in ts:
                v = vol(ser(t), i, 120)
                if v and v > 0:
                    o[t] = 1.0 / v
            return o
        return run_weights(w, st, "섹터 리스크패리티",
                           lambda i: {t: 1.0 for t in ts},
                           "월말에 9섹터를 120일 실현변동성의 역수로 가중.",
                           "대조군은 같은 9섹터 동일가중. 가중 방식만 다르므로 "
                           "'리스크패리티가 동일가중을 이기는가'만 남는다.")
    add("sector-rp", "sector-risk-parity", s_sectrp)

    # 15) 채권 추세 게이트 — 4자산
    def s_bondtrend():
        ts = ["TLT", "IEF", "LQD", "HYG", "SHY"]
        st = first_common(ts)
        bonds = ts[:-1]
        def w(i):
            picks = {t: 1.0 for t in bonds
                     if ser(t)[i] is not None and (ret(ser(t), i, 252) or -1) > 0}
            return picks or {"SHY": 1.0}
        return run_weights(w, st, "채권 추세 게이트 — 4자산",
                           lambda i: {t: 1.0 for t in bonds},
                           "월말에 채권 4종 중 12개월 수익이 양수인 것만 동일가중, 없으면 SHY.",
                           "2022년 채권 급락을 피할 수 있었는지가 이 규칙의 존재 이유다. "
                           "대조군은 같은 4종 상시 동일가중.")
    add("bond-trend", "bond-trend-gate", s_bondtrend)

    # 16) 매니지드 퓨처스 위성
    def s_mf():
        ts = ["SPY", "AGG", "DBMF"]
        st = first_common(ts, pad=20)
        return run_weights(lambda i: {"SPY": 0.5, "AGG": 0.3, "DBMF": 0.2}, st,
                           "매니지드 퓨처스 위성 배분 (DBMF 20%)",
                           lambda i: {"SPY": 0.6, "AGG": 0.4},
                           "월말에 SPY 50% · AGG 30% · DBMF 20%로 되돌린다.",
                           "60/40에 CTA를 20% 섞는다. 대조군은 그 60/40 자체다 — "
                           "'섞어서 나아지는가'만 남긴다.",
                           note="DBMF 상장(2019-05) 이후만 존재한다 — 2022 채권 급락 1회가 표본의 중심이다.")
    add("mf-satellite", "managed-futures-satellite", s_mf)

    # 17) 신용 스프레드 게이트(HYG/LQD 프록시)
    def s_credit():
        ts = ["HYG", "LQD", "SPY", "SHY"]
        st = first_common(ts)
        def w(i):
            h, l = ser("HYG"), ser("LQD")
            if h[i] is None or l[i] is None:
                return {"SPY": 1.0}
            rr = h[i] / l[i]
            hist = [h[j] / l[j] for j in range(max(0, i - 252), i)
                    if h[j] is not None and l[j] is not None and l[j]]
            if not hist:
                return {"SPY": 1.0}
            med = sorted(hist)[len(hist) // 2]
            return {"SPY": 1.0} if rr >= med else {"SHY": 1.0}
        return run_weights(w, st, "신용 레짐 게이트 (HYG/LQD 프록시)",
                           lambda i: {"SPY": 1.0},
                           "HYG/LQD 가격비가 1년 중앙값 이상이면 SPY, 미만(신용 스트레스)이면 SHY. 월말.",
                           "ICE BofA OAS는 공개 CSV가 3년치뿐이라 장기로는 못 쓴다. "
                           "가격비는 같은 정보를 담고 전 구간이 있어 이걸로 대신한다.",
                           note="원 규칙의 OAS 대신 HYG/LQD 가격비를 썼다 — 프록시임을 명시한다.")
    add("credit-gate", "credit-regime-gate", s_credit)

    # 18) 오버나이트 드리프트 (종가 매수 → 시가 매도)
    def s_overnight():
        st = 260
        c, o = ser("SPY"), (A.get("open") or {}).get("SPY")
        if not o:
            return None
        n = len(DTS)
        nav, rets = [100.0], []
        bn, brs = [100.0], []
        for i in range(st + 1, n):
            r = 0.0
            if o[i] is not None and c[i - 1]:
                r = o[i] / c[i - 1] - 1        # 밤사이만 보유
            rets.append(r); nav.append(nav[-1] * (1 + r))
            br = (c[i] / c[i - 1] - 1) if (c[i] is not None and c[i - 1]) else 0.0
            brs.append(br); bn.append(bn[-1] * (1 + br))
        dd = DTS[st:]
        ms, mb = ann_stats(nav, dd, RF), ann_stats(bn, dd, RF)
        step = max(1, len(nav) // 220)
        return {"name": "오버나이트 드리프트 (종가 매수 → 시가 매도)",
                "chart": curve_pack(dd, nav, bn),
                "holdings": {"kind": "asset", "as_of": DTS[-1],
                             "weights": [("SPY(밤에만)", 100.0)],
                             "note": "매일 종가에 사서 다음 시가에 판다 — 낮에는 아무것도 안 들고 있다."},
                "rule": "매 거래일 종가에 SPY를 사서 다음 날 시가에 판다(밤사이만 보유).",
                "why": "아카이브 사유는 '일별 왕복이라 월말 컨벤션과 비양립·BE 2bp'였다. "
                       "규약과 안 맞는 것과 성과가 없는 것은 다른 말이므로, 성과 자체를 잰다.",
                "note": "일 왕복 252회/년이라 무비용 결과를 그대로 읽으면 안 된다 — "
                        "왕복 2bp만 붙어도 연 5%p가 사라진다.",
                "start": DTS[st], "end": DTS[-1], "n_days": n - st,
                "metrics": ms, "bench": mb, "bench_label": "SPY 상시보유(종가→종가)",
                "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
                "t": tstat(rets, brs), "turnover": 252.0,
                "nav": [round(x, 2) for x in nav[::step]],
                "bnav": [round(x, 2) for x in bn[::step]]}
    add("overnight", "overnight-drift", s_overnight)

    # 19) 합병차익거래 (MNA ETF)
    def s_mna():
        ts = ["MNA", "SHY", "SPY"]
        st = first_common(ts, pad=20)
        return run_weights(lambda i: {"MNA": 1.0}, st,
                           "합병차익거래 (MNA ETF)",
                           lambda i: {"SHY": 1.0},
                           "MNA(합병차익 ETF)를 보유. 대조군은 단기국채 SHY.",
                           "아카이브 사유는 '단독 Sharpe 0.39·2020-03 tail dependence 폭발'이었다. "
                           "절대수익형이므로 대조군을 현금성 자산으로 둔다(SPY 비교는 부정합이다).")
    add("merger-arb", "merger-arbitrage", s_mna)

    # ── 크로스에셋 RP 변형 3종 ──────────────────────────────────────
    RP4 = ["SPY", "TLT", "GLD", "DBC"]

    def _iv(ts, win=120):
        def f(i):
            o = {}
            for t in ts:
                v = vol(ser(t), i, win)
                if v and v > 0:
                    o[t] = 1.0 / v
            return o
        return f

    def s_rpgrid():
        st = first_common(RP4)
        base = _iv(RP4)
        def w(i):
            # 목표 연변동성 8%에 맞춰 전체 노출을 스케일(현금은 SHY)
            raw = base(i)
            if not raw:
                return {"SHY": 1.0}
            tot = sum(raw.values())
            wts = {k: v / tot for k, v in raw.items()}
            pv = 0.0
            for t, wt in wts.items():
                v = vol(ser(t), i, 120)
                if v:
                    pv += wt * v * math.sqrt(252)
            if not pv:
                return wts
            k = min(1.0, 0.08 / pv)
            out = {t: wt * k for t, wt in wts.items()}
            out["SHY"] = out.get("SHY", 0) + (1 - k)
            return out
        return run_weights(w, st, "크로스에셋 RP — 목표변동성 8%",
                           base,
                           "역변동성 RP에 목표 연변동성 8% 스케일을 씌우고 나머지는 SHY. 월말.",
                           "아카이브 사유는 '격자 탐색에서 개선 없음'이었다. 격자 전부가 아니라 "
                           "대표값 하나를 걸어, 목표변동성을 씌우는 것 자체가 도움이 되는지만 본다.",
                           note="원 규칙의 '격자 탐색'은 다중검정 그 자체다 — 여기선 한 점(8%)만 건다.")
    add("rp-voltarget", "cross-asset-rp-voltarget-grid", s_rpgrid)

    def s_rpcadence():
        st = first_common(RP4)
        return run_weights(_iv(RP4), st, "크로스에셋 RP — 분기 리밸런스",
                           _iv(RP4),
                           "같은 역변동성 RP를 분기 말에만 리밸런스(대조군은 월말).",
                           "리밸런스 주기를 바꾸면 성과가 바뀌는지. 규칙은 완전히 같고 "
                           "주기만 다르므로 차이는 전부 주기 효과다.",
                           note="주기 차이만 남기려고 전략·대조군의 가중식을 동일하게 두었다.",
                           cadence="quarter", bench_cadence="month")
    add("rp-cadence", "cross-asset-rp-cadence", s_rpcadence)

    def s_rphorizon():
        st = first_common(RP4)
        def gate(mo):
            def f(i):
                raw = _iv(RP4)(i)
                on = {t: v for t, v in raw.items()
                      if (ret(ser(t), i, 21 * mo) or -1) > 0}
                return on or {"SHY": 1.0}
            return f
        return run_weights(gate(6), st, "크로스에셋 RP — 추세 게이트 6개월",
                           gate(12),
                           "역변동성 RP에 6개월 추세 게이트(대조군은 12개월).",
                           "게이트 길이만 다른 두 규칙. 어느 쪽이 맞는지가 아니라 "
                           "길이 선택이 결과를 얼마나 좌우하는지를 보는 것이 목적이다.")
    add("rp-horizon", "cross-asset-rp-trend-horizon", s_rphorizon)

    # ── 오버나이트 보유(NDX) ──
    def s_overnight_ndx():
        st = 260
        c, o = ser("QQQ"), (A.get("open") or {}).get("QQQ")
        if not o:
            return None
        n = len(DTS)
        nav, rets, bn, brs = [100.0], [], [100.0], []
        for i in range(st + 1, n):
            r = (o[i] / c[i - 1] - 1) if (o[i] is not None and c[i - 1]) else 0.0
            rets.append(r); nav.append(nav[-1] * (1 + r))
            br = (c[i] / c[i - 1] - 1) if (c[i] is not None and c[i - 1]) else 0.0
            brs.append(br); bn.append(bn[-1] * (1 + br))
        dd = DTS[st:]
        ms, mb = ann_stats(nav, dd, RF), ann_stats(bn, dd, RF)
        step = max(1, len(nav) // 220)
        return {"name": "오버나이트 보유 (QQQ 종가→시가)",
                "chart": curve_pack(dd, nav, bn),
                "holdings": {"kind": "asset", "as_of": DTS[-1],
                             "weights": [("QQQ(밤에만)", 100.0)],
                             "note": "매일 종가에 사서 다음 시가에 판다 — 낮에는 아무것도 안 들고 있다."},
                "rule": "매 거래일 종가에 QQQ를 사서 다음 날 시가에 판다.",
                "why": "NASDAQ 100에서 밤사이 수익이 낮에 앉아 있는 것보다 나은지. "
                       "대조군은 QQQ 상시보유(종가→종가).",
                "note": "연 252회 왕복이라 무비용 수치를 그대로 읽으면 안 된다.",
                "start": DTS[st], "end": DTS[-1], "n_days": n - st,
                "metrics": ms, "bench": mb, "bench_unstable": False,
                "bench_label": "QQQ 상시보유(종가→종가)",
                "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
                "t": tstat(rets, brs), "turnover": 252.0,
                "nav": [round(x, 2) for x in nav[::step]],
                "bnav": [round(x, 2) for x in bn[::step]]}
    add("overnight-ndx", "overnight-holding-ndx", s_overnight_ndx)

    # ── 변동성 위험프리미엄 숏볼 ──
    def s_vrp():
        ts = ["SVXY", "SPY"]
        st = first_common(ts, pad=20)
        return run_weights(lambda i: {"SVXY": 0.25, "SHY": 0.75}, st,
                           "변동성 위험프리미엄 숏볼 (SVXY 25%)",
                           lambda i: {"SPY": 1.0},
                           "월말에 SVXY 25% · SHY 75%로 되돌린다(레버리지 없이 숏볼 노출).",
                           "아카이브 사유는 '초과수익=레버리지, 위험조정 0'이었다. 노출을 25%로 "
                           "묶어 레버리지 효과를 뺀 뒤에도 남는 것이 있는지 본다.",
                           note="2018-02 볼마겟돈으로 SVXY의 목표 노출이 −1x에서 −0.5x로 바뀌었다 "
                                "— 표본 안에서 상품 성격이 한 번 변한다.")
    add("vrp-shortvol", "vrp-short-vol", s_vrp)

    # ── 채권 슬리브 신용 스프레드 게이트 ──
    def s_creditbond():
        ts = ["HYG", "LQD", "IEF", "SHY"]
        st = first_common(ts)
        def w(i):
            h, l = ser("HYG"), ser("LQD")
            if h[i] is None or l[i] is None:
                return {"HYG": 0.5, "LQD": 0.5}
            rr = h[i] / l[i]
            hist = [h[j] / l[j] for j in range(max(0, i - 252), i)
                    if h[j] is not None and l[j] is not None and l[j]]
            if not hist:
                return {"HYG": 0.5, "LQD": 0.5}
            med = sorted(hist)[len(hist) // 2]
            return {"HYG": 0.5, "LQD": 0.5} if rr >= med else {"IEF": 1.0}
        return run_weights(w, st, "채권 슬리브 신용 게이트",
                           lambda i: {"HYG": 0.5, "LQD": 0.5},
                           "신용 스트레스(HYG/LQD 비율이 1년 중앙값 미만)면 국채(IEF)로 대피, "
                           "아니면 HYG·LQD 반반. 월말.",
                           "아카이브 사유는 '2022 통증은 신용이 아니라 듀레이션이었다'였다. "
                           "그 판정이 재현되는지 — 신용 게이트가 듀레이션 손실을 못 막는지 본다.",
                           note="OAS 대신 HYG/LQD 가격비 프록시를 썼다(공개 OAS는 3년치뿐).")
    add("credit-bond-gate", "credit-spread-gate", s_creditbond)

    # ── 초과채권프리미엄(EBP) 게이트 ──
    def s_ebp():
        ts = ["SPY", "SHY"]
        st = first_common(ts)
        if not (A["macro"].get("EBP")):
            return None
        def w(i):
            e = macro_asof("EBP", DTS[i])
            if e is None:
                return {"SPY": 1.0}
            return {"SHY": 1.0} if e > 0.3 else {"SPY": 1.0}
        return run_weights(w, st, "초과채권프리미엄(EBP) 리스크선호 게이트",
                           lambda i: {"SPY": 1.0},
                           "연준 EBP가 +0.3을 넘으면(리스크선호 위축) SHY, 아니면 SPY. 월말.",
                           "EBP는 FRED에 없어 '구할 수 없다'로 분류돼 있었는데, 연준이 공개 CSV로 "
                           "낸다. 실제로 받아서 돌린다.",
                           note="EBP는 월간이고 발표 지연이 있다 — 발표일 기준 최신값만 쓴다.")
    add("ebp-gate", "ebp-risk-appetite-gate", s_ebp)

    # ── 퀄리티 롱숏(ETF 프록시) ──
    def s_quality():
        ts = ["QUAL", "SIZE", "SPY"]
        st = first_common(ts, pad=20)
        return run_weights(lambda i: {"QUAL": 1.0}, st,
                           "퀄리티 틸트 (QUAL, ETF 프록시)",
                           lambda i: {"SPY": 1.0},
                           "QUAL(퀄리티 팩터 ETF)을 보유. 대조군은 SPY.",
                           "원 규칙은 퀄리티 롱 · 정크 숏이지만 무료 데이터로 정크 바스켓을 "
                           "시점정합하게 만들 수 없다. 그래서 '롱 다리'만 프록시로 돌린다.",
                           note="롱숏이 아니라 롱온리 프록시다 — 같은 이름의 다른 규칙임을 명시한다. "
                                "숏 다리의 기여는 여기서 알 수 없다.")
    add("quality-tilt", "quality-long-short", s_quality)

    # ── 슬리브 결합 2종 ───────────────────────────────────────────────
    # 입력은 자산이 아니라 **이 랩이 실제로 배포한 슬리브의 월간 NAV**다
    # (data/strategy_backtests.json). '못 돌린다'고 적혀 있었지만 그 파일이 이미 있었다.
    def _sleeves():
        p2 = os.path.join(DATA, "strategy_backtests.json")
        if not os.path.exists(p2):
            return None
        S = json.load(io.open(p2, encoding="utf-8")).get("strategies") or {}
        want = {}
        for k, v in S.items():
            if "EPS Revision Drift · NDX 100" in k:
                want["eps"] = v
            elif "Cross-Asset Risk Parity" in k:
                want["rp"] = v
        if len(want) < 2:
            return None
        # 공통 월만 남긴다 — 한쪽이 없는 달을 0으로 채우면 그 달의 성과가 조작된다
        rs = {}
        for key, v in want.items():
            nav, dts = v["nav"], v["dates"]
            rs[key] = {dts[i]: nav[i] / nav[i - 1] - 1 for i in range(1, len(nav)) if nav[i - 1]}
        months = sorted(set(rs["eps"]) & set(rs["rp"]))
        return months, rs

    def _sleeve_run(name, wfn, bwfn, rule, why, note=None):
        got = _sleeves()
        if not got:
            return None
        months, rs = got
        nav, bn, a_, b_ = [100.0], [100.0], [], []
        for j, m in enumerate(months):
            we, wr = wfn(j, months, rs)
            r = we * rs["eps"][m] + wr * rs["rp"][m]
            be, br_ = bwfn(j, months, rs)
            rb = be * rs["eps"][m] + br_ * rs["rp"][m]
            a_.append(r); b_.append(rb)
            nav.append(nav[-1] * (1 + r)); bn.append(bn[-1] * (1 + rb))
        # 월간 계열이므로 연율화를 월 기준으로 다시 한다(ann_stats는 일간 가정이다)
        def mstats(x, nv):
            mu = sum(x) / len(x)
            sd = math.sqrt(sum((v - mu) ** 2 for v in x) / max(1, len(x) - 1))
            yrs = len(x) / 12
            return {"cagr": round(((nv[-1] / nv[0]) ** (1 / yrs) - 1) * 100, 2),
                    "vol": round(sd * math.sqrt(12) * 100, 2),
                    "sharpe": round(mu / sd * math.sqrt(12), 3) if sd > 0 else None,
                    "mdd": round(maxdd(nv) * 100, 2)}
        ms, mb = mstats(a_, nav), mstats(b_, bn)
        d = [x - y for x, y in zip(a_, b_)]
        mu = sum(d) / len(d)
        sd = math.sqrt(sum((v - mu) ** 2 for v in d) / max(1, len(d) - 1))
        step = max(1, len(nav) // 220)
        we_, wr_ = wfn(len(months) - 1, months, rs)
        return {"name": name, "rule": rule, "why": why, "note": note,
                "chart": curve_pack(months, nav, bn),
                "holdings": {"kind": "sleeve", "as_of": months[-1],
                             "weights": [("EPS 리비전 드리프트", round(we_ * 100, 1)),
                                         ("크로스에셋 리스크패리티", round(wr_ * 100, 1))],
                             "note": "배포 슬리브 둘의 현재 배분이다."},
                "start": months[0], "end": months[-1], "n_days": len(months),
                "metrics": ms, "bench": mb, "bench_unstable": False,
                "bench_label": "배포 슬리브 둘 50:50 고정",
                "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
                "t": round(mu / (sd / math.sqrt(len(d))), 2) if sd > 0 else None,
                "turnover": None, "monthly": True,
                "nav": [round(x, 2) for x in nav[::step]],
                "bnav": [round(x, 2) for x in bn[::step]]}

    def s_hrpsleeve():
        def w(j, months, rs):
            if j < 12:
                return 0.5, 0.5
            win = months[max(0, j - 12):j]
            def sd(k):
                xs = [rs[k][m] for m in win]
                mu = sum(xs) / len(xs)
                return math.sqrt(sum((v - mu) ** 2 for v in xs) / max(1, len(xs) - 1)) or 1e-9
            ie, ir = 1 / sd("eps"), 1 / sd("rp")
            t = ie + ir
            return ie / t, ir / t
        return _sleeve_run("계층적 리스크패리티 결합가중 (HRP Sleeve)", w,
                           lambda j, m, r: (0.5, 0.5),
                           "두 배포 슬리브를 직전 12개월 변동성의 역수로 가중(월 갱신). 대조군은 반반.",
                           "아카이브 사유는 '2슬리브에서 ERC=역변동성이라 현 가중과 수학적으로 동일'이었다. "
                           "명제가 맞다면 차이가 0에 붙어야 한다 — 그것을 수치로 확인한다.",
                           note="슬리브가 둘뿐이라 HRP의 군집 단계가 의미를 갖지 않는다. 역변동성판이다.")
    add("hrp-sleeve", "hrp-sleeve-weighting", s_hrpsleeve)

    def s_regimeswitch():
        def w(j, months, rs):
            if j < 6:
                return 0.5, 0.5
            win = months[max(0, j - 6):j]
            se = sum(rs["eps"][m] for m in win)
            sr = sum(rs["rp"][m] for m in win)
            return (1.0, 0.0) if se >= sr else (0.0, 1.0)     # 최근 6개월 강한 쪽으로
        return _sleeve_run("레짐 조건부 슬리브 스위칭", w,
                           lambda j, m, r: (0.5, 0.5),
                           "직전 6개월 누적수익이 큰 슬리브에 100% 몰아준다(월 갱신). 대조군은 반반.",
                           "아카이브 사유는 '서브기간 반대 틸트가 상쇄'였다. 스위칭이 분산을 버리고 "
                           "얻는 것이 있는지 — 반반과 직접 겨룬다.")
    add("regime-switch", "regime-conditional-switch", s_regimeswitch)

    # ── 크로스에셋 캐리 ───────────────────────────────────────────────
    # 캐리 = 가격이 안 움직여도 들어오는 몫. ETF에서는 직전 12개월 분배금 / 현재가다.
    # ⚠ 원자재의 롤 수익은 여기 안 들어간다 — 무료 선물 커브가 없다. DBC의 분배는 담보로 든
    #   단기국채 이자이지 롤이 아니다. 그래서 이건 '캐리 전체'가 아니라 '분배 캐리'다.
    def s_carry():
        ts = ["SPY", "EFA", "EEM", "TLT", "IEF", "LQD", "HYG", "EMB", "TIP", "VNQ"]
        st = first_common(ts)
        DIV = A.get("div") or {}
        def yld(t, i):
            s_ = ser(t)
            if s_ is None or s_[i] is None or not s_[i]:
                return None
            d = DIV.get(t)
            if d is None:
                return None
            hi_ = DTS[i]
            lo_ = DTS[max(0, i - 252)]
            tot = sum(v for k, v in d.items() if lo_ < k <= hi_)
            return tot / s_[i] * 100
        def w(i):
            ys = [(t, yld(t, i)) for t in ts]
            ys = [(t, y) for t, y in ys if y is not None]
            if len(ys) < 6:
                return {t: 1.0 for t in ts}
            ys.sort(key=lambda z: -z[1])
            return {t: 1.0 for t, _y in ys[:4]}        # 캐리 상위 4개 동일가중
        return run_weights(w, st, "크로스에셋 캐리 (분배수익률 상위 4)",
                           lambda i: {t: 1.0 for t in ts},
                           "월말에 직전 12개월 분배금/현재가가 가장 높은 4자산을 동일가중.",
                           "아카이브 사유는 '60/40 동률은 GFC 산물'이었다. 대조군을 같은 10자산 "
                           "동일가중으로 두어 '캐리로 고르는 것'이 '다 들고 있기'를 이기는지만 본다.",
                           note="원자재 롤 수익은 빠졌다(무료 선물 커브 없음) — 분배 캐리만이다. "
                                "같은 이름의 좁은 규칙임을 명시한다.")
    add("carry", "cross-asset-carry", s_carry)

    # 20) 최소 CVaR — 4자산
    def s_cvar():
        ts = ["SPY", "TLT", "GLD", "DBC"]
        st = first_common(ts)
        def w(i):
            # 격자 탐색으로 과거 250일 5% CVaR을 최소화하는 가중(0.1 단위)
            R = {}
            for t in ts:
                s = ser(t)
                R[t] = [(s[j] / s[j - 1] - 1) if (s[j] is not None and s[j - 1]) else 0.0
                        for j in range(i - 250, i)]
            best, bw = None, None
            g = [x / 10 for x in range(0, 11)]
            for a in g:
                for b in g:
                    if a + b > 1:
                        continue
                    for cq in g:
                        if a + b + cq > 1:
                            continue
                        d = round(1 - a - b - cq, 4)
                        wt = {"SPY": a, "TLT": b, "GLD": cq, "DBC": d}
                        pr = [sum(wt[t] * R[t][k] for t in ts) for k in range(250)]
                        pr.sort()
                        cv = sum(pr[:12]) / 12          # 하위 5% 평균
                        if best is None or cv > best:
                            best, bw = cv, wt
            return bw or {t: 0.25 for t in ts}
        return run_weights(w, st, "최소 CVaR 최적화 (4자산)",
                           lambda i: {t: 1.0 for t in ts},
                           "월말에 과거 250일 5% CVaR을 최소화하는 가중(0.1 격자)으로 배분.",
                           "아카이브 사유는 '개선 없음 — 현 가중이 강건 교차점'이었다. "
                           "대조군을 동일가중으로 두고 그 명제를 재현한다.")
    add("min-cvar", "min-cvar", s_cvar)


def main() -> int:
    global A, DTS, RF
    p = os.path.join(DATA, "assets.json")
    if not os.path.exists(p):
        print("❌ data/assets.json 없음 — python build/refresh_assets.py 먼저 실행"); return 1
    A = json.load(io.open(p, encoding="utf-8"))
    DTS = A["dates"]
    RF = json.load(io.open(os.path.join(DATA, "rf_monthly.json"),
                           encoding="utf-8")).get("monthly") or {}
    build()

    rows = []
    for sid, arch, fn in OUT_ROWS:
        try:
            r = fn()
        except Exception as e:
            print("  ❌ %-16s %s: %s" % (sid, type(e).__name__, e)); continue
        if not r:
            print("  ❌ %-16s 산출 없음" % sid); continue
        r["sid"] = sid
        r["arch"] = arch
        r["role"] = ROLE.get(sid, "배분기")
        rows.append(r)

    # 머신러닝·13F 복제는 별도 스크립트(build/ml_backtest.py)가 낸다 — 규약이 다르기 때문이다
    # (사전등록·워크포워드). 표는 여기 하나로 합친다. 두 곳에 두면 갈린다.
    mlp = os.path.join(DATA, "ml_strategies.json")
    if os.path.exists(mlp):
        for r in (json.load(io.open(mlp, encoding="utf-8")).get("strategies") or []):
            r.setdefault("turnover", None)
            r["role"] = ROLE.get(r.get("sid"), "수익엔진")
            rows.append(r)
    else:
        print("  ⚠ ml_strategies.json 없음 — python build/ml_backtest.py 를 먼저 돌릴 것")

    # 판정 — 다중검정 보정 후 대조군 대비
    n = len(rows)
    lo, hi = 0.0, 12.0
    for _ in range(200):
        m = (lo + hi) / 2
        if math.erfc(m / math.sqrt(2)) > 0.05 / max(1, n):
            lo = m
        else:
            hi = m
    tcrit = round((lo + hi) / 2, 2)
    for r in rows:
        t = r.get("t")
        if r.get("verdict") == "표본 부족 · 판정 불가":
            continue                      # 검정 구간이 짧아 이미 판정을 막아둔 건 그대로 둔다
        if t is None:
            r["verdict"] = "판정 불가"
        elif r.get("bench_unstable"):
            # 대조군이 현금성이면 Δ샤프가 허수다 — t만으로 가른다
            r["verdict"] = "통과 후보" if (t >= tcrit) else ("구별 불가" if t > 0 else "대조군 열위")
        elif r["d_sharpe"] <= 0:
            r["verdict"] = "대조군 열위"
        elif abs(t) >= tcrit:
            r["verdict"] = "통과 후보"
        else:
            r["verdict"] = "구별 불가"

    # 정렬은 t 우선 — Δ샤프로 줄 세우면 현금성 대조군을 쓴 전략이 허수로 맨 위에 온다
    rows.sort(key=lambda x: -(x.get("t") if x.get("t") is not None else -9))

    # ── 지수 기준표 ────────────────────────────────────────────────────
    # 전략 하나하나의 숫자만 보면 '좋은지'를 알 수 없다. 같은 구간에 지수가 얼마를 냈는지가
    # 옆에 있어야 판단이 된다. 연도별로도 낸다 — 어떤 국면에 어떤 전략이 먹히는지는
    # 전 구간 평균이 아니라 해마다 갈리기 때문이다.
    #
    # ⚠ 지수는 **가격지수(PR)** 다. ^GSPC·^NDX는 배당을 안 담는다. 배당까지 담은 총수익(TR)은
    #   SPY·QQQ 쪽이고, 실측 격차가 연 2.0%p다(SPY 10.99% vs ^GSPC 8.98%, 2006~).
    #   PR을 대조군으로 쓰면 전략이 그만큼 유리해 보인다 — 그 사실을 표에 함께 적는다.
    IDX = [("^GSPC", "S&P 500 (SPX)", "PR"), ("^NDX", "NASDAQ 100 (NDX)", "PR"),
           ("SPY", "SPY (배당 재투자)", "TR"), ("QQQ", "QQQ (배당 재투자)", "TR")]

    def stats_range(a, lo, hi):
        v = [(i, a[i]) for i in range(lo, hi + 1) if a[i] is not None]
        if len(v) < 30:
            return None
        px_ = [x for _i, x in v]
        rs = [px_[k] / px_[k - 1] - 1 for k in range(1, len(px_)) if px_[k - 1]]
        if not rs:
            return None
        m = sum(rs) / len(rs)
        sd = math.sqrt(sum((x - m) ** 2 for x in rs) / max(1, len(rs) - 1))
        yrs = len(px_) / 252
        peak, mdd = px_[0], 0.0
        for x in px_:
            peak = max(peak, x)
            mdd = min(mdd, x / peak - 1)
        return {"ret": round(((px_[-1] / px_[0]) ** (1 / yrs) - 1) * 100, 2),
                "vol": round(sd * math.sqrt(252) * 100, 2),
                "mdd": round(mdd * 100, 2),
                "sharpe": round(m / sd * math.sqrt(252), 3) if sd > 0 else None,
                "n_days": len(px_)}

    years = sorted({d[:4] for d in DTS})
    idx_ref = {"note": "전략을 볼 때 옆에 두고 읽는 지수 기준표. 지수는 가격지수(PR)이고 "
                       "배당이 빠져 있다 — 배당까지 담은 총수익(TR)은 SPY·QQQ 줄이며 "
                       "2006년 이후 격차가 연 2.0%p다. PR을 대조군으로 쓰면 전략이 그만큼 "
                       "유리해 보이므로 둘을 같이 싣는다.",
               "as_of": DTS[-1], "rows": [], "years": years[1:]}
    for tk, label, kind in IDX:
        a = ser(tk)
        if not a:
            continue
        row = {"t": tk, "label": label, "kind": kind,
               "all": stats_range(a, 0, len(DTS) - 1), "by_year": {}}
        for y in years:
            ii = [i for i, d in enumerate(DTS) if d[:4] == y]
            if len(ii) > 100:
                st_ = stats_range(a, ii[0], ii[-1])
                if st_:
                    row["by_year"][y] = {"ret": st_["ret"], "vol": st_["vol"], "mdd": st_["mdd"]}
        idx_ref["rows"].append(row)

    # ── 재현 가능성 판정표 ─────────────────────────────────────────────
    # 아카이브가 '재현 불가'로 두었던 38건 전부에 대해, 무엇이 있으면 되는지와
    # 실제로 구해지는지를 적는다. 못 도는 것은 **무엇이 없어서인지**를 남긴다.
    done = {r["arch"] for r in rows}
    # 단독 재검(archive_backtests.json)으로 돌린 것도 '돌림'이다. 재검 경로가 둘인데
    # 한쪽만 세면, 다른 쪽으로 돌린 항목이 재점검표에서 조용히 사라진다 —
    # 실제로 t-ndxvol(종목 쪽 NDX 전용판)을 없앴을 때 vol-targeting-ndx가 그렇게 빠졌다.
    _sa = {}
    try:
        _sa = (json.load(io.open(os.path.join(DATA, "archive_backtests.json"),
                                 encoding="utf-8")).get("strategies") or {})
    except Exception:
        pass
    STANDALONE = set(_sa)
    # 돌리지 못한 것 — 사유를 사실대로 나눈다. '데이터가 세상에 없다'와
    # '있는데 아직 안 만들었다'는 다른 말이고, 섞으면 영원히 안 하게 된다.
    # 유료 데이터라 영원히 못 도는 항목들은 2026-07-26에 아카이브에서 **삭제**했다.
    # 남겨둬 봐야 매번 '불가'만 찍히고 재검 대상도 아니었다. 사유는 커밋 메시지에 남는다.
    PENDING = {
        "cross-asset-carry": ("가능 · 미구현",
            "주식 이익수익률·채권 기간스프레드·원자재 롤·FX 금리차를 한 축으로 묶어야 한다. "
            "네 축 모두 이미 받은 데이터(FRED·ETF)로 만들 수 있으나 캐리 정의가 자산군마다 "
            "달라 규칙을 먼저 정해야 한다 — 데이터 문제가 아니라 설계 문제다."),
                                                            }
    try:
        _ai = json.load(io.open(os.path.join(DATA, "archive_index.json"), encoding="utf-8"))
        _idx = {x["sid"]: x for x in (_ai.get("items") or [])}
    except FileNotFoundError:
        _idx = {}
    audit = []
    for sid, x in _idx.items():
        if sid in done:
            r = next(rr for rr in rows if rr["arch"] == sid)
            audit.append({"sid": sid, "n": x["n"], "c": x.get("c", ""),
                          "status": "돌림", "why": (r.get("note") or
                          "공개 데이터(yfinance·FRED)로 재현했다."), "res": r["sid"]})
        elif sid in STANDALONE:
            audit.append({"sid": sid, "n": x["n"], "c": x.get("c", ""), "status": "돌림",
                          "why": "기각 재검(단독 검정)으로 돌렸다 — 원 기각 사유가 "
                                 "'배포 포트폴리오에 얹으면 개선이 없다'는 상대 판정이었기 때문이다.",
                          "res": "r-" + sid})
        elif sid in PENDING:
            st, why = PENDING[sid]
            audit.append({"sid": sid, "n": x["n"], "c": x.get("c", ""),
                          "status": st, "why": why})
    doc_audit = {
        "note": "아카이브가 '이 저장소 데이터로는 재현할 수 없다'고 두었던 항목을 다시 점검한 결과. "
                "대부분은 데이터가 세상에 없어서가 아니라 이 저장소가 안 갖고 있었을 뿐이었다.",
        "n_total": len(audit),
        "n_done": sum(1 for a in audit if a["status"] == "돌림"),
        "n_pending": sum(1 for a in audit if a["status"].startswith("가능")),
        "n_blocked": sum(1 for a in audit if a["status"].startswith("불가")),
        "items": sorted(audit, key=lambda a: (a["status"] != "돌림", a["status"], a["n"])),
    }
    doc = {
        "note": "아카이브에서 '재현 불가'로 두었던 전략들을 공개 데이터로 실제로 돌린 결과. "
                "좋은 것만 고르지 않고 돌린 것을 전부 싣는다.",
        "as_of": DTS[-1], "t_crit": tcrit, "n": n,
        "source": "가격 yfinance · 거시 FRED 공개 CSV(키 불필요) — 둘 다 무료·무인증",
        "protocol": [
            "월말 리밸런스·무비용(gross). 이 랩의 기본 규약 그대로다.",
            "대조군은 전략마다 다르다 — 절대수익형에 지수를 붙이면 '벤치 부정합' 기각이 되는데 "
            "그건 전략이 아니라 비교의 잘못이다(아카이브에 그 사고가 있다).",
            "구간은 전략마다 다르다. 쓰는 ETF의 상장일에 묶이기 때문이며, 그건 데이터 결손이 "
            "아니라 그 전략의 실제 제약이다.",
            "전략 %d개를 같은 표본에서 돌렸으므로 본페로니로 임계를 |t|≥%.2f로 올렸다." % (n, tcrit),
            "대조군이 현금성(연변동성 2%% 미만)인 전략은 샤프 차이가 허수가 된다 — 분모가 0에 "
            "가까워 작은 수익 차이가 몇 단위로 증폭된다. 그런 행은 Δ샤프를 판정에 쓰지 않고 "
            "t만 보며, 화면에 '대조군 현금성'으로 표시한다.",
        ],
        "limits": [
            "무비용이다. 오버나이트 드리프트처럼 연 252회 왕복하는 규칙은 무비용 수치를 "
            "그대로 읽으면 안 된다 — 함께 적은 회전율을 반드시 볼 것.",
            "ETF는 그 자체가 수수료를 뗀 실현 수익이라 지수 백테스트보다 보수적이다. "
            "반대로 상장 전 구간은 존재하지 않아 표본이 짧아진다.",
            "원 규칙에서 무료 데이터로 못 옮긴 항이 있는 경우(선물 롤 캐리·OAS 등) 그 사실을 "
            "전략별 비고에 적었다. 같은 이름의 다른 규칙임을 숨기지 않는다.",
        ],
        "strategies": rows,
        "audit": doc_audit,
        "index_ref": idx_ref,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")

    vc = {}
    for r in rows:
        vc[r["verdict"]] = vc.get(r["verdict"], 0) + 1
    print("\n재현 점검 %d건 — 돌림 %d · 가능하나 미실행 %d · 불가 %d"
          % (doc_audit["n_total"], doc_audit["n_done"],
             doc_audit["n_pending"], doc_audit["n_blocked"]))
    print("돌린 전략 %d개 · 판정 %s · 임계 |t|≥%.2f" % (n, vc, tcrit))
    print("%-34s %9s %8s %8s %8s %7s  %s" % ("전략", "구간", "CAGR", "샤프", "Δ샤프", "t", "판정"))
    for r in rows:
        m = r["metrics"]
        print("%-34s %9s %8s %8s %8s %7s  %s"
              % (r["name"][:34], r["start"][:7], m.get("cagr"), m.get("sharpe"),
                 r["d_sharpe"], r.get("t"), r["verdict"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
