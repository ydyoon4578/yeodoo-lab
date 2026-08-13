# -*- coding: utf-8 -*-
"""build/strategy_index.py — 전 전략을 한 목록으로 → data/strategy_index.json

왜 만드는가. 전략이 네 군데(배포 원장·종목 랩·자산 랩·기각 재검)에 흩어져 있었다. 그 나눔은
**전략이 무엇을 하는가가 아니라 어느 파일에서 나왔는가**를 따른 것이라, 보는 사람에게는
같은 것을 네 번 다르게 보여주는 셈이었다. 여기서 하나로 합친다.

묶는 축은 **성격(role)** 이다 — strategy_kinds.json의 어휘를 그대로 쓴다.
  수익엔진      무엇을 살지 고르는 전략(초과수익이 목적)
  배분기        얼마씩 담을지 정하는 전략
  위험감축      모전략의 노출을 줄여 낙폭을 관리
  타이밍오버레이 한 자산에 들어갈지 나갈지만 결정

같은 숫자를 세로로 비교하면 안 되기 때문에 성격이 첫 축이다 — 종목을 고르는 전략은 수익으로,
배분기는 샤프로, 오버레이는 낙폭으로 본다.

⚠ 수치는 **원본에서 그대로 옮긴다**. 여기서 새로 계산하지 않는다. 구간·대조군이 전략마다
   다르므로 그 사실을 record마다 싣고, 화면이 "같은 눈금이 아니다"를 말할 수 있게 한다.

  python build/strategy_index.py
"""
from __future__ import annotations
import io, json, os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from asset_backtest import pct1 as _pct1     # 비중 → 소수1자리·합 100.0(최대잔여법)
except Exception:                                # 임포트가 막히면 원값을 그대로 둔다
    def _pct1(w):                                # (틀린 척도로 그리느니 손대지 않는 편이 낫다)
        return [(k, v) for k, v in (w or {}).items() if v is not None]
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "strategy_index.json")

# 등급 — '배포북에 넣을 것인가'에 대한 답. 랩 판정은 그 어휘로 옮긴다.
GRADE = {
    "deploy": "배포", "marginal": "제한적 유효", "reject": "미채택",
    "통과 후보": "통과 후보", "관례대로 유효": "통과 후보",
    # 2026-08-13 — 관문을 전부 끄면서 랩 규칙이 받는 등급(build/tech_backtest.py).
    "측정만": "측정만",
    # ⚠ "대조군 열위" 는 2026-08-08 에 정본에서 "열위" 로 통일했다. 옛 산출물을
    #   다시 읽을 때를 위해 매핑은 남긴다(지우면 옛 파일이 조용히 "판정 불가" 가 된다).
    "구별 불가": "구별 불가", "대조군 열위": "열위", "열위": "열위",
    "표본 부족 · 판정 불가": "판정 불가", "판정 불가": "판정 불가",
    "관례와 반대로 유의": "역방향 유의", "소수 사건 의존": "소수 사건 의존",
}
_PRW = None      # 같은 구간 지수(PR) 기준선을 계산하는 함수. main()에서 한 번 만든다.

GRADE_ORDER = ["배포", "제한적 유효", "측정만", "통과 후보", "역방향 유의", "구별 불가",
               "소수 사건 의존", "열위", "미채택", "판정 불가"]
ROLE_ORDER = ["수익엔진", "배분기", "위험방어", "타이밍오버레이", "미분류"]


# ── 대조군을 나란히 볼 수 있는가 ──────────────────────────────────────────
# 같은 표에 있다고 같은 잣대로 볼 수 있는 건 아니다. 대조군이 전략과 **같은 것을 목표로 할 때만**
# Δ샤프·초과수익을 우열로 읽을 수 있다.
#   수익엔진·배분기·타이밍오버레이 → 대조군과 목표가 같다(더 벌거나, 같은 위험에서 더 벌거나)
#   위험감축                      → 목표가 낙폭이다. 상시보유와 CAGR·샤프로 겨루면 지는 게 정상이고,
#                                 그 패배는 전략이 나쁘다는 뜻이 아니다 — 그래서 따로 뺀다.
# 여기에 표본 부족·대조군 현금(샤프 분모가 0에 가까워 Δ가 허수)을 더한다.
# ⚠ 방어보험은 2026-07-27 에 목록에서 사라졌지만(전 종목 제외) 여기에는 남긴다 — 제외를 되돌리면
#   대조군 판정이 먼저 필요해지고, 그때 이 집합에 없으면 CAGR·샤프로 우열을 매기는 오독이 되살아난다.
CMP_OFF_ROLE = {"위험방어", "위험감축", "방어보험"}   # 뒤 둘은 옛 어휘(호환용)


def comparability(role, grade, unstable, n_days=None):
    if unstable:
        return False, "대조군이 현금성이라 샤프 분모가 0에 가깝다 — Δ샤프가 허수가 된다(t만 본다)."
    if grade == "판정 불가":
        return False, "검정 구간이 짧아 어떤 수치가 나와도 실력과 운을 가를 수 없다."
    if role in CMP_OFF_ROLE:
        return False, ("목표가 수익이 아니라 낙폭·보험이다. 상시보유와 CAGR·샤프로 겨루면 지는 것이 "
                       "정상이고, 그 패배는 전략이 나쁘다는 뜻이 아니다 — 낙폭과 위기 구간으로 본다.")
    return True, None


def holds_kind(h):
    """지금 무엇을 들고 있는지 **종목 단위로** 보여줄 수 있는가."""
    if not h:
        return "없음"
    k = h.get("kind")
    if k == "xsec" and h.get("tickers"):
        return "종목"
    # 페어 롱숏 — 보유 단위가 종목이 아니라 **쌍**이다. 티커 목록으로 접으면 'AEE 를
    # 들고 있다'로 읽히는데 실제로 들고 있는 것은 AEE 롱 + CNP 숏이고, 그 방향조차
    # 형성 시점에는 정해져 있지 않다(스프레드가 ±2σ 벌어질 때 정해진다).
    if k == "pair" and h.get("weights"):
        return "페어"
    if k in ("asset", "sleeve") and h.get("weights"):
        return "비중"
    if k == "timing":
        return "노출"
    return "없음"


def load(fn):
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        return None
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None


def thin(a, k=60):
    """NAV 곡선을 k점으로 줄인다. 목록의 스파크라인은 폭이 320px라 그보다 촘촘할 이유가 없다 —
    원본을 그대로 실으면 290KB가 되고, 그 대부분이 화면에서 같은 픽셀에 찍힌다."""
    if not a or len(a) <= k:
        return a
    step = (len(a) - 1) / (k - 1)
    out = [a[min(len(a) - 1, round(i * step))] for i in range(k)]
    out[-1] = a[-1]          # 끝점은 반드시 실제 마지막 값(수익률이 잘리면 안 된다)
    return out


# ── 같은 구간 지수(PR) 기준선 ─────────────────────────────────────────────
# 전략마다 대조군이 다르다(동일가중 유니버스·SPY·60/40·현금…). 그래서 "그래서 좋은 건가"를
# 물으면 답이 전략마다 다른 잣대로 나온다. 누구나 아는 눈금 하나를 같이 얹는다 —
# **같은 구간의 S&P 500·NASDAQ 100 가격지수(PR)**다.
#
# ⚠ 이 줄은 판정용이 아니다. 전략 수익은 배당을 재투자한 총수익(TR) 기준인데 지수는 PR이라
#   배당이 빠져 있다. 2006년 이후 그 격차가 연 2.0%p다 — PR과 겨루면 전략이 그만큼 유리해
#   보인다.
# 🚨 2026-08-13 — 종전에는 여기에 "판정은 각 전략의 대조군(TR 대 TR)으로 한다"고 적혀 있었다.
#   **그 말이 이제 거짓이다.** 사용자 결정으로 판정 대조군도 전부 PR 이 됐다(자산 랩 SPY→^GSPC,
#   배포 원장 NDX/SPX TR→PR). 즉 이 줄과 판정선이 같은 눈금을 쓰게 됐지만, 그 대신
#   TR(전략) 대 PR(대조군)의 비대칭이 판정 안으로 들어왔다. pr_note 가 화면에 그렇게 적는다.
#
# 🚨 **주기가 곧 눈금이다 — 전략과 같은 주기로 재지 않으면 나란히 못 놓는다.**
#   같은 SPX·같은 구간인데 일간이냐 월말이냐로 값이 이만큼 갈린다(2006~2026 실측):
#     샤프 0.351(일간) vs 0.535(월말) · 변동성 19.35 vs 15.15 · MDD -56.78 vs -52.56.
#   CAGR만 싣던 동안은 티가 안 났지만(9.01 vs 9.00) 나머지 지표는 그대로 거짓 비교가 된다.
#
# ⚠ 그런데 **전략마다 주기가 다르다.** 원천 파일에는 그 사실이 안 적혀 있고 nav·chart 는
#   원천에서 이미 얇게 만들어 길이로도 못 읽는다(종목 전략 448점/8.9년, 13F 156점/13년).
#   실측으로 갈린다 — 12-1 모멘텀의 대조군 SPX 는 vol 18.93·MDD -33.92(일간)인데
#   13F 의 대조군 SPX 는 vol 14.45·MDD -24.77(월말)이다.
#   → 두 주기를 다 계산해 두고, **대조군이 지수인 전략은 그 대조군 수치에 맞는 쪽**을 고른다.
#     고를 근거가 없으면 다수인 일간으로 두고 화면에 그렇게 적는다(pr_basis).
def pr_baseline():
    A = load("assets.json") or {}
    dts, px = A.get("dates") or [], A.get("px") or {}
    if not dts:
        return None
    rf = (load("rf_monthly.json") or {}).get("monthly") or {}
    import sys as _s
    _s.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from tech_backtest import ann_stats            # noqa: E402  일간 — 원천 다수가 쓰는 것
    from strategy_metrics import series_block      # noqa: E402  월말 — 지표표가 쓰는 것

    # 계열은 한 번만 만든다 — 전략마다 다시 만들 이유가 없다.
    DAY, MON = {}, {}
    for tk, lab in (("^GSPC", "spx"), ("^NDX", "ndx")):
        a = px.get(tk)
        if not a:
            continue
        DAY[lab] = [(dts[i], a[i]) for i in range(len(dts)) if a[i]]
        last = {}
        for d, v in DAY[lab]:
            last[d[:7]] = (d, v)
        MON[lab] = [(m, last[m][0], last[m][1]) for m in sorted(last)]

    def window(start, end, rf_from="*"):
        """[start, end] 의 SPX·NDX 가격지수(PR)를 **두 주기 다** 잰다 → {'D':{...}, 'M':{...}}.

        rf_from 은 무위험이자율을 어디부터 평균 낼지다 — 원천이 쓴 규약을 그대로 따른다.
        ⚠ ann_stats 는 건네받은 rf **전체**의 평균을 쓴다. 그래서 어디서부터 잘라 주느냐가
          곧 샤프가 된다. 원천마다 규약이 다르다:
            · 종목 전략(tech_backtest)  rf[k] for k >= 패널 시작(2017-08)
            · 자산배분·ML(asset/ml)     rf 파일 전체(1981-09~ · 연 3.7%)
          같은 SPX·같은 구간인데 여기서 다른 규약을 쓰면 대조군 열과 지수 열이 어긋난다
          (실측 0.627 vs 0.557). series_block 은 달마다 찾아 쓰므로 이 문제가 없다.
        """
        if not (start and end):
            return None
        out = {"D": {}, "M": {}}
        rfw = rf if rf_from == "*" else ({k: v for k, v in rf.items() if k >= rf_from} or rf)
        for lab in DAY:
            sel = [x for x in DAY[lab] if start <= x[0] <= end]
            if len(sel) >= 120:                    # 반년도 안 되면 눈금이 못 된다
                base = sel[0][1]
                out["D"][lab] = ann_stats([100.0 * x[1] / base for x in sel],
                                          [x[0] for x in sel], rfw)
            sel = [x for x in MON[lab] if start <= x[1] <= end]
            if len(sel) >= 7:
                base = sel[0][2]
                b = series_block([100.0 * x[2] / base for x in sel], [x[0] for x in sel], rf)
                for k in ("_ex", "_r", "label"):   # 관계지표용 원계열은 직렬화하지 않는다
                    b.pop(k, None)
                out["M"][lab] = b
        return out if (out["D"] or out["M"]) else None
    return window


# 이 전략의 지표가 어느 주기로 계산됐나 — 대조군이 지수면 그 수치가 답을 알려 준다.
# 변동성·MDD 는 주기에 크게 갈리므로(위 주석 실측) 둘의 합으로 맞춰 보면 판정이 선명하다.
PR_BASIS_TOL = 1.5          # %p 합. 이보다 멀면 '맞춘 것'으로 치지 않는다.


def pick_basis(bench, both, hint="D"):
    """('D'|'M', 실측여부). 못 맞추면 원천이 쓰는 규약(hint)으로 되돌린다.

    hint 는 빌더를 읽어서 정한다 — strategy_metrics.series_block 를 거치는 원천
    (배포 원장·기각 재검·거장 겹침)은 월말이고, tech/asset/ml 은 일간 ann_stats 다.
    이걸 안 주면 배포 원장 7종·기각 재검 2종이 월간 지표인데 일간 지수와 겨루게 된다.
    """
    lab = (bench or {}).get("label") or ""
    key = "spx" if "S&P 500" in lab else ("ndx" if ("NASDAQ" in lab or "NDX" in lab) else None)
    bv, bm = (bench or {}).get("vol"), (bench or {}).get("mdd")
    if key and bv is not None and bm is not None:
        sc = {}
        for b in ("D", "M"):
            ix = (both.get(b) or {}).get(key)
            if ix and ix.get("vol") is not None and ix.get("mdd") is not None:
                sc[b] = abs(bv - ix["vol"]) + abs(bm - ix["mdd"])
        if sc:
            win = min(sc, key=sc.get)
            if sc[win] <= PR_BASIS_TOL:
                return win, True
    if both.get(hint):
        return hint, False
    return ("D" if both.get("D") else "M"), False


def _regime_months():
    """월(YYYY-MM) → 국면 키. data/regime.json 의 history 가 단일 출처다."""
    R = load("regime.json") or {}
    return {h["dt"][:7]: h["r"] for h in (R.get("history") or []) if h.get("dt") and h.get("r")}


def _regime_meta(months):
    """국면별 표본 크기 — **개월 수와 '연속 구간' 수를 둘 다** 싣는다.

    🚨 이것이 이 표의 핵심이다. 과열은 26개월이지만 **전부 한 덩어리**(2021-04~2023-05)이고
      후기사이클은 4개월 한 덩어리다. 즉 '과열에 강한 전략'은 26개의 독립 관측이 아니라
      **사건 하나**에서 좋았던 전략이라는 뜻이다. 개월 수만 적으면 화면이 그 사실을 숨긴다.
    ⚠ 이 랩은 이미 '7국면이 다음 달을 못 가른다'를 정식으로 검정했다(data/regime.json 의
      fwd_note). 그러므로 이 표는 **검정이 아니라 서술**이다 — 국면을 보고 전략을 고르라는
      뜻으로 읽으면 안 된다.
    """
    cyc = load("regime_cycle.json") or {}
    ko = {p["k"]: p.get("ko") or p["k"] for p in (cyc.get("phases") or [])}
    order = [p["k"] for p in (cyc.get("phases") or [])]
    n, runs, prev, eps = {}, {}, None, {}
    for m in sorted(months):
        k = months[m]
        n[k] = n.get(k, 0) + 1
        if k != prev:
            runs[k] = runs.get(k, 0) + 1
            eps.setdefault(k, []).append([m, m])
        else:
            eps[k][-1][1] = m
        prev = k
    return {"order": [k for k in order if k in n] or sorted(n),
            "ko": {k: ko.get(k, k) for k in n},
            "now": (cyc.get("now") or {}).get("r"),
            "now_ko": (cyc.get("now") or {}).get("ko"),
            # 🚨 실제 시기를 같이 싣는다. '과열 26개월'만 적으면 26개의 관측처럼 보이는데
            #   실제로는 2021-04~2023-05 한 덩어리다. 화면이 그 날짜를 그대로 적어야
            #   읽는 사람이 '아 그 인플레 구간 얘기구나' 하고 제대로 값을 깎아 읽는다.
            "episodes": eps,
            "n": n, "runs": runs,
            "span": (min(months) + "~" + max(months)) if months else None,
            "note": "국면별 **월평균 수익**이다. ⚠ 검정이 아니라 서술이다 — 이 랩은 7국면이 "
                    "다음 달을 못 가른다는 것을 이미 검정했다(regime.json 의 fwd_note). "
                    "🚨 개월 수보다 **연속 구간 수**를 먼저 보라. 과열 26개월은 전부 한 덩어리"
                    "(2021-04~2023-05)이고 후기사이클은 4개월 한 덩어리다 — 그 칸의 순위는 "
                    "관측 26개가 아니라 **사건 하나**에서 나온 것이다. 구간이 여럿인 것은 "
                    "골디락스(6)와 회복(6)뿐이다."}


def _monthly_rets(rec_):
    """전략 레코드에서 월별 수익(%) 목록 [(YYYY-MM, r)] 을 꺼낸다.

    두 모양을 받는다 — chart.monthly(랩·자산 랩)와 dates+nav(배포 원장). 배포 쪽은 월별
    수익 배열이 아예 없어서 nav 에서 만든다. ⚠ 여기서 만든 값은 화면에 그리지 않는다.
    국면 평균을 내는 데만 쓴다(그림은 원본 nav 를 그대로 쓴다).
    """
    ch = rec_.get("chart") or {}
    mo = ch.get("monthly") or rec_.get("monthly")
    if mo:
        out = []
        for row in mo:
            if not isinstance(row, dict):
                continue
            m, r = row.get("m") or row.get("dt"), row.get("r")
            if m and isinstance(r, (int, float)):
                out.append((str(m)[:7], float(r)))
        if out:
            return out
    dts, nav = rec_.get("dates") or ch.get("dates"), rec_.get("nav") or ch.get("nav")
    if dts and nav and len(dts) == len(nav) and len(str(dts[0])) == 7:
        return [(str(dts[i])[:7], (nav[i] / nav[i - 1] - 1) * 100.0)
                for i in range(1, len(nav)) if nav[i - 1]]
    return []


def _regime_stats(rets, months, min_n=8):
    """국면별 월평균. 표본이 min_n 미만인 국면은 **넣지 않는다**(칸이 비고 '—' 로 나간다).

    ⚠ 0 이나 전체 평균으로 채우지 않는다 — 후기사이클(4개월)처럼 못 재는 칸을 숫자로 채우면
      화면이 없는 것을 지어내게 된다.
    """
    g = {}
    for m, r in rets:
        k = months.get(m)
        if k:
            g.setdefault(k, []).append(r)
    out = {}
    for k, v in g.items():
        if len(v) >= min_n:
            out[k] = {"v": round(sum(v) / len(v), 2), "n": len(v)}
    return out or None


# ── 최근 구간 수익 ────────────────────────────────────────────────────────
# 홈 맨 아래 '최근 성과 상위' 목록이 쓴다(2026-08-13 사용자 요청).
# 🚨 **여기서만 잴 수 있다.** rec() 이 nav 를 60점으로 얇게 만들기 직전이 원해상도가 남아
#   있는 유일한 자리다(원천은 주간 격자 833~980점). 얇아진 뒤에 재면 한 점이 넉 달을
#   덮어 '최근 1개월'이 실제로는 한 분기가 된다.
# ⚠ 기준일을 목표일에 **가장 가까운 실제 관측**으로 잡고, 그 날짜를 함께 싣는다. 주간
#   격자라 최대 ±7일이 어긋나는데, 그 사실을 안 적으면 화면이 없는 정밀도를 말하게 된다.
# ⚠ 전략마다 계열이 끝나는 날이 다르다(171종 2026-08-12 · 11종은 6~8주 먼저). 그래서
#   end 도 같이 싣는다 — 나란히 세우면 안 되는 줄이 어느 것인지 화면이 알아야 한다.
# ⚠ home_perf.HZ 와 **같은 목록**이어야 한다 — 홈의 두 블록이 같은 기간 버튼을 쓴다.
TR_HOR = [("1W", 7), ("1M", 30), ("3M", 91), ("6M", 181), ("12M", 365)]
# 🚨 월간 격자(배포 원장 8종 + 슬리브 3종)에서는 이보다 짧은 구간을 만들지 않는다.
#   한 점이 한 달이라 "최근 1주"를 물으면 전달 말 대비가 나온다 — 1주가 아니라 한 달이고,
#   그 줄이 주간 격자 전략들과 같은 열에 앉으면 순위가 통째로 거짓이 된다.
MONTHLY_MIN_DAYS = 28


# 지수 일간 계열 — trails 와 **같은 창**에서 재려고 여기 한 번만 만든다.
# 🚨 market_board 의 구간 수익을 가져다 쓰면 안 된다. 그쪽 기준일은 고정인데 전략의 창은
#   줄마다 다르다(기준일 08-07/07-31 · 끝 08-12/08-07/06-30 …). 다른 창의 두 수를 빼면
#   그 차이는 초과수익이 아니라 창 차이다 — 짧은 구간일수록 통째로 그것만 잰다.
_IXPX = None


def _ix_load():
    global _IXPX
    if _IXPX is not None:
        return _IXPX
    A = load("assets.json") or {}
    d, px = A.get("dates") or [], A.get("px") or {}
    _IXPX = {"d": d, "spx": px.get("^GSPC"), "ndx": px.get("^NDX"),
             "pos": {x: i for i, x in enumerate(d)},
             "last": {}}
    for i, x in enumerate(d):
        _IXPX["last"][x[:7]] = i            # 그 달의 마지막 거래일(월간 격자용)
    return _IXPX


def _ix_at(ix, day):
    """그 날짜(또는 그 이전 마지막 거래일)의 위치. 'YYYY-MM' 이면 그 달 말."""
    s_ = str(day)[:10]
    if len(s_) == 7:
        return ix["last"].get(s_)
    i = ix["pos"].get(s_)
    if i is not None:
        return i
    ks = [j for j, x in enumerate(ix["d"]) if x <= s_]
    return ks[-1] if ks else None


def trails_ix_of(base, end):
    """전략의 각 구간 [기준일 ~ 계열 끝] 에서 지수 수익(%). 못 재면 그 칸을 안 만든다."""
    if not base or not end:
        return None
    ix = _ix_load()
    if not ix["d"]:
        return None
    i1 = _ix_at(ix, end)
    if i1 is None:
        return None
    out = {}
    for k, d0 in base.items():
        i0 = _ix_at(ix, d0)
        if i0 is None or i0 >= i1:
            continue
        cell = {}
        for lab in ("spx", "ndx"):
            a = ix.get(lab)
            if a and a[i0] and a[i1]:
                cell[lab] = round((a[i1] / a[i0] - 1) * 100, 2)
        if cell:
            out[k] = cell
    return out or None


def trails_of(dates, nav):
    """구간별 누적수익(%) 과 그때 실제로 쓴 기준일. 못 재면 그 칸을 안 만든다."""
    if not dates or not nav or len(dates) != len(nav) or len(nav) < 3:
        return None, None
    import datetime as _dt
    # 🚨 격자가 **월말('YYYY-MM')로 들어오기도 한다** — 배포 원장 8종과 슬리브 결합 3종이
    #   그렇다. 그걸 일간으로 파싱하면 fromisoformat 이 터져 11종이 조용히 빠진다
    #   (실제로 그랬다). load_index_tr 이 같은 사유로 같은 분기를 갖고 있다.
    monthly = all(len(str(d)) == 7 for d in dates)
    try:
        d1 = (_dt.date(int(str(dates[-1])[:4]), int(str(dates[-1])[5:7]), 1) if monthly
              else _dt.date.fromisoformat(str(dates[-1])[:10]))
    except Exception:
        return None, None
    last = nav[-1]
    if not last:
        return None, None
    out, base = {}, {}
    tgts = [(k, (d1 - _dt.timedelta(days=nd)).isoformat()) for k, nd in TR_HOR]
    tgts.append(("YTD", "%d-12-31" % (d1.year - 1)))
    _cut = 7 if monthly else 10
    for k, tgt in tgts:
        if monthly and k != "YTD" and dict(TR_HOR).get(k, 999) < MONTHLY_MIN_DAYS:
            continue                      # 월간 격자에 1주 칸을 만들지 않는다(위 주석)
        ks = [i for i, d in enumerate(dates) if str(d)[:_cut] <= tgt[:_cut]]
        if not ks:
            continue                      # 구간이 그만큼 안 된다 — 0 으로 채우지 않는다
        i0 = ks[-1]
        # 🚨 **가장 가까운 관측**을 쓴다. '목표일 이하의 마지막' 만 보면 주간 격자에서
        #   기준일이 최대 한 주 더 뒤로 밀린다 — 실측으로 '1주' 칸이 12일(07-31~08-12)을
        #   재고 있었다. 라벨이 1주인데 12일을 재면 그것이 거짓이다.
        #   ⚠ 미래참조가 아니다. 뒤 후보(i0+1)도 기준일이지 수익 끝점이 아니고, 언제나
        #     오늘보다 과거다. 창이 짧아질 뿐 없는 정보를 쓰지 않는다.
        if k != "YTD" and i0 + 1 < len(dates) - 1:
            _t = _dt.date.fromisoformat(tgt) if not monthly else None
            if _t is not None:
                try:
                    _a = abs((_dt.date.fromisoformat(str(dates[i0])[:10]) - _t).days)
                    _b = abs((_dt.date.fromisoformat(str(dates[i0 + 1])[:10]) - _t).days)
                    if _b < _a:
                        i0 = i0 + 1
                except Exception:
                    pass
        if not nav[i0]:
            continue
        out[k] = round((last / nav[i0] - 1) * 100, 2)
        base[k] = str(dates[i0])[:10]
    # ⚠ 월간 격자는 눈금이 굵다 — '최근 1개월'이 실제로는 한 달 전 월말 대비다.
    #   화면이 기준일을 적으므로 숨겨지지 않는다.
    return (out or None), (base or None)


def rec(**kw):
    # ⚠ thin() 앞에서 잰다(위 주석). 순서를 바꾸면 조용히 값이 뭉개진다.
    # ⚠ dates 는 재고 나서 **버린다.** 원해상도(833~980점)로 실으면 파일이 커지고,
    #   더 나쁘게는 60점으로 얇아진 nav 와 길이가 어긋나 짝이 안 맞는 배열 둘이 남는다.
    _tr, _trb = trails_of(kw.get("dates"), kw.get("nav"))
    kw.pop("dates", None)
    if _tr:
        kw["trails"], kw["trails_base"] = _tr, _trb
        # 같은 창의 지수 수익 — 화면이 'vs S&P 500' 열을 만들 수 있게(위 _ix_load 주석).
        _ti = trails_ix_of(_trb, kw.get("end"))
        if _ti:
            kw["trails_ix"] = _ti
    for key in ("nav", "bnav"):
        if kw.get(key):
            kw[key] = thin(kw[key])
    kw.setdefault("role", "미분류")
    kw.setdefault("grade", "판정 불가")
    # 분류는 여기 한 곳에서만 매긴다. 출처마다 따로 계산하면 같은 전략이 화면에서
    # 다른 칸에 들어가는 일이 생긴다.
    kw["holds"] = holds_kind(kw.get("holdings"))
    ok, why = comparability(kw["role"], kw["grade"], kw.get("bench_unstable"))
    kw["cmp_ok"] = ok
    if why:
        kw["cmp_why"] = why
    if _PRW:
        both = _PRW(kw.get("start"), kw.get("end"), kw.pop("rf_from", "*"))
        if both:
            # 대조군 이름은 bench 안에 있기도 하고(종목 전략) 레코드 최상위에만 있기도 하다
            # (자산배분 31종). 주기 판정은 둘 다 봐야 한다.
            _b = dict(kw.get("bench") or {})
            _b.setdefault("label", None)
            if not _b["label"]:
                _b["label"] = kw.get("bench_label")
            _k, _sure = pick_basis(_b, both, kw.pop("pr_hint", "D"))
            pr = both.get(_k) or {}
            if pr:
                kw["pr"] = pr
                kw["pr_basis"] = ("월말" if _k == "M" else "일간") + ("" if _sure else " (원천 규약)")
                _s = pr_split(kw)
                if _s:
                    kw["pr_split"] = _s
    return kw


# ── 대조군 판정 ↔ 지수 눈금이 엇갈리는가 ──────────────────────────────────
# 왜 필요한가. 전략은 자기 대조군(동일가중 유니버스·모전략·같은 풀 1/N …)으로 판정한다.
# 그런데 그 판정과 '세상의 눈금(지수)'이 반대로 나오는 전략이 있다 — 그때 초과수익의 정체가
# 갈린다. 동일가중은 못 이겼는데 지수는 이겼다면 그 초과분은 종목선택이 아니라 **동일가중이
# 만든 사이즈 틸트**일 수 있다. 반대면 고르기는 됐지만 살 수 있는 대안을 못 넘은 것이다.
# 어느 한쪽만 보면 이 구분이 사라지므로, 엇갈릴 때만 표시한다.
#
# ⚠ TR/PR 보정. 전략 수익은 배당 재투자(TR)인데 지수는 가격지수(PR)라 배당이 빠져 있다.
#   보정 없이 비교하면 전략이 연 2%p 유리해 보여 '지수를 이겼다'가 과다 발생한다.
#   pr_baseline()의 주석과 같은 값(연 2.0%p)을 지수 쪽에 더해 TR 근사로 맞춘 뒤 비교한다.
PR_TR_GAP = 2.0        # 지수 PR→TR 근사 보정(%p/년). 2006년 이후 실측 격차.


def pr_split(kw):
    m = kw.get("metrics") or {}
    b = kw.get("bench") or {}
    pr = kw.get("pr") or {}
    sc, bc = m.get("cagr"), b.get("cagr")
    if sc is None or bc is None or not kw.get("cmp_ok"):
        return None                      # 판정 자체가 성립 안 하면 엇갈림도 말하지 않는다
    win_bench = sc > bc
    out = []
    for k, lab in (("spx", "S&P 500"), ("ndx", "NASDAQ 100")):
        ic = (pr.get(k) or {}).get("cagr")
        if ic is None:
            continue
        win_idx = sc > (ic + PR_TR_GAP)
        if win_idx != win_bench:
            out.append({"k": k, "label": lab,
                        "d_bench": round(sc - bc, 2),
                        "d_idx": round(sc - (ic + PR_TR_GAP), 2)})
    if not out:
        return None
    # 🚨 2026-08-13 — 판정 대조군을 전부 PR 로 통일한 뒤로 이 패널의 성격이 **바뀌었다.**
    #   종전에는 '서로 다른 두 기준선'의 엇갈림이었는데, 이제 129종은 기준선도 눈금도 같은
    #   S&P 500(PR)이라 남은 차이가 **배당 하나뿐**이다(d_idx 는 PR_TR_GAP 을 더한 값).
    #   그런데 문구는 여전히 "두 기준이 서로 다른 답을 준다"고 말한다 — 같은 지수를 두 번
    #   비교해 놓고 다른 기준이라 부르면 읽는 사람이 없는 대조군을 상상하게 된다.
    #   대조군 이름에 (PR)이 있으면 **배당이 원인이라고 곧바로 적는다.**
    _bl = (kw.get("bench_label") or (kw.get("bench") or {}).get("label") or "")
    if "(PR)" in _bl:
        why = ("차이는 배당 하나다 — 판정 기준이 배당 없는 지수(PR)라 "
               + ("초과분이 있는 것으로 나오지만, 배당까지 넣은 눈금(연 +%.1f%%p)으로는 못 넘는다. "
                  "즉 이 초과분은 전략이 만든 것이 아니라 대조군이 배당을 못 받아 생긴 것이다."
                  % PR_TR_GAP
                  if win_bench else
                  "초과분이 없는 것으로 나오지만, 배당까지 넣은 눈금으로는 넘는다."))
    else:
        # 🚨 2026-08-12 — '대조군'이라는 말을 화면에서 뺐다(사용자 요청). 두 비교 기준을
        #   각각의 이름으로 부른다: 이 전략이 판정에 쓰는 기준선 vs 실제로 살 수 있는 지수.
        why = ("두 기준이 서로 다른 답을 준다 — "
               + ("이 전략이 쓰는 기준선으로는 초과분이 없는데 실제 살 수 있는 지수는 넘었다. "
                  "기준선 자체의 성격에서 온 이득일 수 있다."
                  if not win_bench else
                  "기준선은 넘었지만 실제 살 수 있는 지수는 못 넘었다."))
    return {"win_bench": win_bench, "vs": out, "why": why}


def main() -> int:
    global _PRW
    _PRW = pr_baseline()
    rows = []

    # 배포 원장의 현재 보유 — 두 파일에 나뉘어 있다(무료 재현본 / 사내 DB 산출본).
    # 통합 목록이 '구성종목을 볼 수 있는 전략인가'로 나누려면 이걸 같이 봐야 한다.
    # 안 그러면 실제로는 보여줄 수 있는 6건이 '없음' 칸으로 떨어진다.
    HOLD_DEP = {}
    for _f in ("strategy_holdings.json", "strategy_holdings_db.json"):
        for _k, _v in ((load(_f) or {}).get("strategies") or {}).items():
            pos = _v.get("positions") or []
            if not pos:
                continue
            HOLD_DEP[_k] = {
                "kind": {"stocks": "xsec"}.get(_v.get("kind"), "asset"),
                "as_of": _v.get("as_of"), "n": len(pos), "note": _v.get("note"),
                "tickers": sorted(x.get("t") for x in pos if x.get("t")),
                "names": {x["t"]: (x.get("n") or x["t"]) for x in pos if x.get("t")},
                # 🚨 2026-08-10 — 척도를 통일한다. 배포 원장의 w 는 **0~1**(합 1.0)인데
                #   자산 랩에서 오는 weights 는 0~100 이고, 화면(explorer·report)은 둘을
                #   구분 없이 toFixed(1)+'%' 로 그린다. 그래서 배포 6건은 0.0435 → '0.0%'
                #   처럼 **전 종목이 0.0%** 로 나갔다. 한 필드에 척도가 둘이면 언젠가 이렇게 된다.
                #   pct1 은 자산 랩이 쓰는 그 함수다(최대잔여법 · 합이 정확히 100.0).
                #   ⚠ 새로 구현하지 않고 가져다 쓴다 — 같은 식을 두 벌 두면 한쪽만 고쳐진다.
                "weights": _pct1({(x.get("t") or x.get("n")): x.get("w")
                                  for x in pos if x.get("w") is not None}),
            }

    # ── ① 배포 원장 ── 성격은 strategy_detail.json이 들고 있다(화면이 쓰던 축 그대로).
    dep = load("deploy_index.json") or {}
    det = load("strategy_detail.json") or {}
    bt = (load("strategy_backtests.json") or {}).get("strategies") or {}
    for x in (dep.get("items") or []):
        n = x["n"]
        d = det.get(n) or {}
        b = bt.get(n) or {}
        m = (b.get("metrics") or {}).get("s") or {}
        bm = (b.get("metrics") or {}).get("b") or {}
        rows.append(rec(
            sid=x["sid"], name=n, alias=x.get("alias"), aka=x.get("aka") or [],
            role=d.get("kind") or "미분류", grade=GRADE.get(x.get("v"), "판정 불가"),
            src="배포 원장", cat=x.get("c"),
            pr_hint="M",   # strategy_metrics.series_block(월말)이 만든 지표다

            rule=x.get("t"), why=x.get("vt"),
            start=b.get("start"), end=b.get("end"),
            # 변동성·MDD 도 옮긴다 — 원천(series_block)에 다 있는데 셋만 옮기고 있었다.
            # 화면의 지수 비교표가 '연변동성 —' 로 비고, 주기 판정도 근거를 잃는다.
            metrics={"cagr": m.get("cagr"), "sharpe": m.get("sharpe"), "vol": m.get("vol"),
                     "mdd": b.get("mdd_b") and m.get("mdd") or m.get("mdd")},
            bench={"label": b.get("bench_label"), "cagr": bm.get("cagr"),
                   "sharpe": bm.get("sharpe"), "vol": bm.get("vol"), "mdd": bm.get("mdd")},
            nav=b.get("nav"), bnav=b.get("bench"), dates=b.get("dates"),
            bench_label=b.get("bench_label"),
            # 🚨 2026-08-13 — 보조 대조군을 원장 카드에도 싣는다. 판정선을 지수로 올리면서
            #   원래 대조군('모전략'·'동일 유니버스 균등'·'SPY 원계열')을 보조로 내렸는데,
            #   여기서 안 넘기면 그 질문이 '판정 축' 칸에서 사라진다 — 낙폭 차트 범례에만
            #   남아 있어서는 "이 변형이 원판보다 나은가"를 아무도 못 읽는다.
            #   ⚠ t 가 아니라 z 를 쓴다. 원장 지표는 월간 계열이라 strategy_metrics 가
            #     ΔSharpe 의 z 를 이미 냈고, 여기서 t 를 새로 만들면 채점기가 두 벌이 된다.
            bench_alt=(lambda _v2, _b2: {
                "label": b.get("bench2_label"), "t": _v2.get("d_sharpe_z"), "tlab": "ΔSharpe z",
                "d_sharpe": _v2.get("d_sharpe"),
                "metrics": {"cagr": _b2.get("cagr"), "sharpe": _b2.get("sharpe"),
                            "vol": _b2.get("vol"), "mdd": _b2.get("mdd")},
            } if (b.get("bench2_label") and _v2.get("d_sharpe_z") is not None) else None)(
                ((b.get("metrics") or {}).get("vs2") or {}),
                ((b.get("metrics") or {}).get("b2") or {})),
            holdings=HOLD_DEP.get(n),
        ))

    # ── ② 종목 전략 ──
    t = load("tech_strategies.json") or {}
    # SPX(TR) Sharpe 미달 종목선택 제외는 2026-07-28 에 **되돌렸다**(사용자 결정).
    # 종목 전략은 전부 목록에 싣는다 — 판정(등급)이 이미 그 정보를 담고 있고, 목록에서까지
    # 빼면 '무엇을 재고 무엇을 버렸나'가 화면에서 사라진다.
    _hidden, _hidden_bond, _hidden_sids = [], [], set()
    # 🚨 시가총액 하한 변형 4종을 **목록에서 뺀다**(사용자 결정 2026-08-13).
    #   사용자 사유는 "필터 없는 전략보다 성과가 별로"였고, 나는 그 사유가 뒤집혀 있다고
    #   실측으로 알렸다 — 이 넷은 성과를 노린 전략이 아니라 **생존편향을 재려고 등록한
    #   진단**이고(PREREG-2026-08-12-MCAPFLOOR), CAGR 이 낮은 것은 성적이 나빠서가 아니라
    #   편향이 절반 빠졌기 때문이다(45.24→20.99 · 43.74→17.42 · 31.01→12.59 %p).
    #   즉 39% 쪽이 53% 쪽보다 진짜에 가깝다. 그 설명을 듣고 사용자가 제거를 재확인했다.
    # ⚠ **빌더는 계속 잰다.** tech_backtest 에서 지우지 않는 이유가 둘이다 —
    #   ① MCAPFLOOR 사전등록 결과(편향 반토막·PIT 불변)가 재현 불가가 되면 안 된다.
    #   ② 이 랩의 규약이 "끄는 것과 안 재는 것은 다르다"이다.
    #   되살리려면 이 집합을 비우면 된다.
    MCF_HIDE = {"x-dist200-mcf", "x-mom12-mcf", "x-hlspread-mcf", "x-hurst-mcf"}
    _mcf = []
    for r in (t.get("strategies") or []):
        if r.get("sid") in MCF_HIDE:
            _mcf.append(r["name"])
            continue
        rows.append(rec(
            sid="t-" + r["sid"], name=r["name"], role=r.get("role") or "미분류",
            grade=GRADE.get(r.get("verdict"), r.get("verdict") or "판정 불가"),
            src="종목 전략", rule=r.get("rule"), why=r.get("why"),
            # 대조군 이름은 파일 머리에 하나로 있다(종목 전략은 전부 같은 대조군을 쓴다).
            # 레코드로 안 옮기면 화면이 '무엇과 겨뤘나'를 못 적는다.
            bench_label=t.get("bench_label"),
            # ⚠ 구간은 **전략별**로 다르다. 펀더멘털이 늦게 채워지는 규칙은 한동안 후보가 없어
            #   실제 시작이 늦다(고ROE 2021-01, 장부가대비저평가 2020-03). 문서 전체 start 를
            #   쓰면 화면이 "2017-08 부터 쟀다"고 잘못 말하고, 같은 표에 놓인 다른 전략과
            #   같은 구간인 것처럼 보인다.
            start=r.get("start") or t.get("start"), end=t.get("as_of"),
            # 무위험 규약 — tech_backtest 는 rf 를 **패널 시작부터** 평균 낸다(전략별 구간이
            # 아니라). 지수 눈금도 같은 규약으로 재야 대조군 열과 어긋나지 않는다.
            rf_from=(t.get("start") or "")[:7] or "*",
            metrics=r.get("metrics") or {}, bench=dict(r.get("bench") or {},
                                                       label=t.get("bench_label")),
            d_sharpe=r.get("d_sharpe"), t=r.get("t"), turnover=r.get("turnover"),
            # 리밸런스 주기(PREREG-2026-08-13-REBAL). 종전엔 전 규칙이 월말이라 설명문에
            # 글자로 박아 두면 됐는데, 주기가 갈린 뒤로는 화면이 자료에서 읽어야 한다.
            reb=r.get("reb"), reb_label=r.get("reb_label"),
            holdings=r.get("holdings"), nav=r.get("nav"), bnav=r.get("bnav"), dates=r.get("dates"),
            arch=r.get("arch"),
            # 채점 후보 수 — '상위 10종'이 몇 종 중에서 골라진 것인가. 이것도 재 놓고 화면에
            # 안 내면 모은 적 없는 것과 같다(바로 아래 pit 이 그랬던 것과 같은 유형이라
            # 붙여 둔다). narrow 는 '그 규칙 자신의 평소 후보 수 절반에도 못 미친 달'이다.
            pool=r.get("pool"), n_thin=r.get("n_thin"),
            # 실제로 담은 종목 수(2026-08-11). pool 이 '몇 종 중에서'라면 이쪽은 '몇 종을'이다.
            # 랩 규칙이 전부 10종이던 동안은 볼 것이 없었는데, 원 전략 크기 6종이 들어오면서
            # 화면이 '155종 중 155종' 과 '52종 중 30종'을 구별해야 한다. short 가 그 눈금이다.
            bask=r.get("bask"),
            # 시점정확(PIT) 실측 — build/pit_backtest.py 가 같은 창에서 소급 레그와 함께 잰 것.
            # ⚠ 전에는 이 값이 판정 강등에만 쓰이고 **화면에는 숫자가 안 나갔다**. 편향을 재
            #   놓고 안 보여주면 독자는 소급 수치만 보게 된다 — 목록에 실어 카드가 적게 한다.
            pit=r.get("pit"),
            # 가장 닮은 규칙 대비 증분 알파 — '이걸 이미 들고 있으면 이게 더 주는 게 있나'.
            # 단독 t 만 보면 같은 베팅을 여러 번 센다(에코 모멘텀 단독 3.80 → 증분 0.85).
            # 바스켓 크기 전수 시험의 선택 기록 — PREREG-2026-08-13-NSWEEP.md §4①.
            #   🚨 이걸 안 넘기면 화면이 '셋 중 골랐다'는 사실을 말할 수 없다. 그 고지가
            #   이 시험을 데이터마이닝이 아니게 하는 유일한 장치라 반드시 같이 간다.
            nsel=r.get("nsel"),
            incr=r.get("incr"),
            # 이웃 5개 동시 통제 증분 알파. incr(이웃 1개)만 보면 붐비는 축의 규칙이
            # 실제보다 독립적으로 보인다 — 실측 2026-08-04: incr t≥2 를 넘던 11종 중
            # 이웃 5개에서도 넘는 것은 7종이다. 화면이 둘을 나란히 낼 수 있게 같이 보낸다.
            incr5=r.get("incr5"),
            # 비용 뒤 성적 — metrics·t 는 전부 무비용(gross)이다. 회전율을 싣기만 하고
            # 안 태우면 연 0.2회전 규칙과 연 83회전 규칙이 같은 t 로 겨룬다. 편도 10bp 를
            # 태운 값이 net, 5·10·20bp 전부가 net.sens 다. 화면이 둘을 나란히 낼 수 있게 보낸다.
            # ⚠ 자산배분·ML 원천에는 아직 이 값이 없다 — 있는 것만 실린다(없으면 필드가 빠진다).
            net=r.get("net"),
            # 자산 랩·ML 랩과 같은 이름의 비용 필드 — explorer 의 '비용 후' 줄이 이것을 읽는다.
            # ⚠ cost_bp 는 **왕복**이다(종목 랩 편도 10bp = 왕복 20bp, 자산 랩은 왕복 5bp).
            #   대상이 개별주 10종이냐 ETF 냐가 달라서 그렇다 — 같은 열에서 크기를 겨루면 안 된다.
            metrics_net=r.get("metrics_net"), bench_net=r.get("bench_net"),
            cost_bp=r.get("cost_bp"), cost_drag=r.get("cost_drag"),
            cost_kill=r.get("cost_kill"), cost_sensitive=r.get("cost_sensitive"),
            # 다중검정 임계 — 화면이 '비용 뒤에 임계 아래로 내려가는가'를 말하려면 필요하다.
            # 원천이 도출한 값을 그대로 옮긴다(화면에 숫자를 박으면 규칙이 늘 때 거짓이 된다).
            t_crit=t.get("t_crit"),
            # 🚨 자기가 실제로 매매하는 것 대비 성적. 타이밍 규칙은 랩 동일가중 유니버스를
            #   사는데 판정 대조군은 S&P 500(PR)이라 두 자산이 다르다 — 노출 1.0 고정의
            #   '아무것도 안 하는 규칙'조차 그 대조군에는 t 4.90 이 나온다. 이 열이 없으면
            #   독자는 그 몫을 타이밍 실력으로 읽는다.
            vs_traded=r.get("vs_traded"),
        ))

    if _hidden_bond:
        print("  대조군에 채권 ETF 가 섞인 %d종을 목록에서 제외:" % len(_hidden_bond))
        for _n, _b in _hidden_bond:
            print("    · %-34s %s" % (_n[:34], ", ".join(_b)))

    # ── ③ 자산배분 · 머신러닝 · 복제 ──
    # 대조군에 채권 ETF 가 섞인 전략은 목록에서 뺀다(사용자 결정 2026-07-28).
    # ⚠ 라벨로 판정하면 안 된다 — 5자산 이상은 "N자산 동일가중"으로 접혀 티커가 안 보이고,
    #   "동적 배분(4자산)" 뒤에도 TLT 가 숨어 있다. asset_backtest 가 싣는 bench_tickers 로 본다.
    #   (라벨만 봤다면 15종 중 7종을 놓쳤다.)
    BOND_ETF = {"TLT", "IEF", "SHY", "AGG", "BND", "LQD", "HYG", "TIP", "EMB"}
    a = load("asset_strategies.json") or {}
    for r in (a.get("strategies") or []):
        _bt = set(r.get("bench_tickers") or [])
        _hit = _bt & BOND_ETF
        if _hit:
            _hidden.append((r["name"], -1.0))
            _hidden_bond.append((r["name"], sorted(_hit)))
            _hidden_sids.add("a-" + r["sid"])
            continue
        rows.append(rec(
            sid="a-" + r["sid"], name=r["name"], role=r.get("role") or "배분기",
            grade=GRADE.get(r.get("verdict"), r.get("verdict") or "판정 불가"),
            src="자산배분", rule=r.get("rule"), why=r.get("why"), note=r.get("note"),
            pr_hint="D",   # asset_backtest/ml_backtest 는 일간 ann_stats 다

            bench_label=r.get("bench_label"),
            start=r.get("start"), end=r.get("end"),
            metrics=r.get("metrics") or {}, bench=r.get("bench") or {},
            d_sharpe=r.get("d_sharpe"), t=r.get("t"), turnover=r.get("turnover"),
            bench_unstable=r.get("bench_unstable"), beta=r.get("beta"),
            holdings=r.get("holdings"), nav=r.get("nav"), bnav=r.get("bnav"), dates=r.get("dates"),
            arch=r.get("arch"),
            # 위험 축 — 수익 축(grade)과 다른 질문에 답한다. 같이 실어야 '덜 벌었지만
            # 덜 깨졌다'가 화면에서 읽힌다. 자산 전략에만 있다(다른 원천은 없음).
            risk_verdict=r.get("risk_verdict"), risk=r.get("risk"),
            # 판정 축 넷(2026-08-12) — CAPM 알파·포착률·꾸준함·침체 국면.
            # 🚨 안 넘기면 재 놓고 안 실은 것이 된다. 수익 축 t 하나로 '구별 불가'였던 규칙의
            #   실제 성격이 여기에만 남아 있다(BAA 균형형: 수익 t 0.06 · 알파 t 3.16).
            axes=r.get("axes"),
            # 보조 대조군(2026-08-12) — 판정에는 안 쓴다. 주대조군 하나로는 잣대가 한쪽으로
            # 기우는 것을 읽는 사람이 알 수 없다(실측: 같은 규칙이 SPY 대비 t −2.10,
            # 60/40 대비 t +1.02 — 정반대 인상이다).
            # ⚠ 이름을 bench2 로 두지 않는다. 배포 카드의 bt.bench2 는 **곡선 배열**이라
            #   같은 이름이 두 모양을 갖게 된다.
            bench_alt=r.get("bench2"),
            # 비용 후 — 회전이 큰 규칙은 무비용 숫자만 보면 안 된다. gross 를 대체하지 않고 함께 싣는다.
            metrics_net=r.get("metrics_net"), bench_net=r.get("bench_net"),
            cost_bp=r.get("cost_bp"), cost_drag=r.get("cost_drag"),
            cost_kill=r.get("cost_kill"), cost_sensitive=r.get("cost_sensitive"),
        ))

    # ── ③-b 페어 트레이딩 ── build/pairs_backtest.py · PREREG-2026-08-12-PAIRS.md
    # 🚨 **대조군이 다른 넷과 다르다.** 앞의 소스는 전부 시장(또는 동일가중 유니버스)과
    #   겨루는데, 페어는 달러중립 롱숏이라 대조군이 **현금**이고 Δ샤프의 분모가 0 이다.
    #   그래서 성격은 수익엔진으로 두되(초과수익이 목적이므로 맞다) `bench_unstable` 로
    #   비교 가능성을 끈다 — 위 comparability() 의 첫 갈래가 정확히 이 경우를 위한 것이다.
    #   ⚠ 새 성격 어휘를 만들지 않았다. strategy_kinds.json 에 '시장중립'을 더하면
    #     strategy_report·strategy_book_pdf·validate_site 의 성격 목록까지 같이 움직여야
    #     하는데, 얻는 것은 라벨 하나이고 잃는 것은 네 파일의 동기화다. 화면이
    #     "같은 눈금이 아니다"를 말할 수 있으면 그것으로 충분하다.
    pz = load("pairs_strategies.json") or {}
    for r in (pz.get("strategies") or []):
        rows.append(rec(
            sid=r["sid"], name=r["name"], role=r.get("role") or "수익엔진",
            grade=GRADE.get(r.get("verdict"), r.get("verdict") or "판정 불가"),
            src="페어 트레이딩", rule=r.get("rule"), why=r.get("why"), note=r.get("note"),
            pr_hint="D",                      # 일간 계열이다(pairs_backtest 의 ann 통계와 같은 주기)
            bench_label=r.get("bench_label") or pz.get("bench_label"),
            bench_unstable=True,
            start=r.get("start"), end=r.get("end"),
            metrics=r.get("metrics") or {}, bench=r.get("bench") or {},
            d_sharpe=r.get("d_sharpe"), t=r.get("t"), beta=r.get("beta"),
            # 지금의 페어북 — 보유 단위가 쌍이라 holds 가 '페어'로 잡힌다(holds_kind 참조).
            # ⚠ 이걸 안 넘기면 목록에 전략만 있고 **무엇을 사는지가 없다.**
            holdings=r.get("holdings"),
            nav=r.get("nav"), bnav=r.get("bnav"), dates=r.get("dates"),
        ))

    # ── ④ 기각 재검 ── 배포하지 않는 것이므로 등급은 '미채택'으로 못 박는다.
    # 성격은 규칙이 하는 일로 정한다(재검 산출물에는 role이 없다).
    RECHK_ROLE = {
        # vol-targeting-ndx 는 2026-07-30 에 삭제됐다(archive_index·archive_backtests 양쪽에서).
        "low-beta-weight-tilt": "위험방어",
        "bond-trend-gate": "타이밍오버레이", "cross-asset-rp-extended": "배분기",
        "tail-risk-hedge": "위험방어",
    }
    ab = load("archive_backtests.json") or {}
    ai = {x["sid"]: x for x in ((load("archive_index.json") or {}).get("items") or [])}
    for sid, b in (ab.get("strategies") or {}).items():
        x = ai.get(sid) or {}
        m = (b.get("metrics") or {}).get("s") or {}
        bm = (b.get("metrics") or {}).get("b") or {}
        rows.append(rec(
            sid="r-" + sid, name=x.get("n") or sid, role=RECHK_ROLE.get(sid, "미분류"),
            grade="미채택", src="기각 재검", cat=x.get("c"),
            pr_hint="M",   # 배포 원장과 같은 파일·같은 함수에서 온다

            bench_label=b.get("bench_label") or ((b.get("metrics") or {}).get("b") or {}).get("label"),
            rule="기각한 전략을 단독으로 다시 검정한 결과다. 원 기각 사유가 "
                 "'배포 포트폴리오에 얹으면 개선이 없다'는 상대 판정이었기 때문이다.",
            why=x.get("r"),
            start=b.get("start"), end=b.get("end"),
            metrics={"cagr": m.get("cagr"), "sharpe": m.get("sharpe"),
                     "vol": m.get("vol"), "mdd": m.get("mdd")},
            bench={"label": b.get("bench_label") or (bm.get("label")), "cagr": bm.get("cagr"),
                   "sharpe": bm.get("sharpe"), "vol": bm.get("vol"), "mdd": bm.get("mdd")},
            d_sharpe=(round(m["sharpe"] - bm["sharpe"], 3)
                      if m.get("sharpe") is not None and bm.get("sharpe") is not None else None),
            nav=b.get("nav"), bnav=b.get("bench"), dates=b.get("dates"),
        ))

    # ── ⑤ 거장 겹침 복제 ──────────────────────────────────────────────────
    # 13F 명단 중 K곳 이상이 들고 있는 종목을 동일가중으로 담는 규칙(build/guru_overlap_backtest.py).
    # 변형 6종을 **전부** 싣는다. 좋은 것만 올리면 목록이 다중검정 분모를 숨기게 된다 —
    # 종목 전략 블록에 적어 둔 것과 같은 이유다("무엇을 재고 무엇을 버렸나"가 사라진다).
    #
    # 대조군은 **같은 풀 동일가중**으로 잡는다. SPY 도 같이 쟀지만 그쪽을 bench 로 놓으면
    # 이 계열이 실제보다 좋아 보인다 — 유니버스가 대형주 518종목이라 SPY 를 넘는 것은
    # 종목선택이 아니라 동일가중이 만든 사이즈 틸트로도 설명된다. 더 어려운 쪽을 잣대로 둔다.
    def _ov_grade(ds, tt):
        """Δ샤프와 t 로 등급을 매긴다. 눈으로 고르지 않으려고 규칙으로 박아 둔다."""
        if ds is None:
            return "판정 불가"
        if ds <= -0.10:
            return "열위"
        if tt is not None and abs(tt) >= 1.96:
            return "통과 후보" if tt > 0 else "역방향 유의"
        return "구별 불가"

    ovd = load("guru_overlap.json") or {}
    _ovn = 0
    for v in ((ovd.get("variants") or []) + (ovd.get("tops") or [])):
        m, pl = v.get("metrics") or {}, v.get("pool") or {}
        bm = pl.get("metrics") or {}
        if not m or not bm:
            continue                     # 표본 부족으로 성과가 없는 변형은 싣지 않는다
        ds = (round(m["sharpe"] - bm["sharpe"], 3)
              if m.get("sharpe") is not None and bm.get("sharpe") is not None else None)
        _nm = ovd.get("n_managers") or 17
        if v.get("rank"):
            sid = "g-overlap-top%d-%s" % (ovd.get("topn") or 10, v["rank"])
            name = "거장 겹침 2곳 이상 · %s" % v.get("label")
            _rule = ("쉽게 말해 — 13F 명단 %d곳 중 2곳 이상이 같이 들고 있는 종목을 추린 뒤, "
                     "그중 %s만 남겨 같은 비중으로 담는다. 같은 회사의 다른 클래스는 하나만 "
                     "담고 밀려난 자리는 다음 순위가 채운다." % (_nm, v.get("label")))
        else:
            sid = "g-overlap-k%d" % v["k"]
            name = "거장 겹침 %d곳 이상 (동일가중)" % v["k"]
            _rule = ("쉽게 말해 — 13F 명단 %d곳 중 %d곳 이상이 같이 들고 있는 종목을 전부 "
                     "같은 비중으로 담는다." % (_nm, v["k"]))
        rows.append(rec(
            sid=sid, name=name, role="수익엔진", grade=_ov_grade(ds, pl.get("t")),
            src="거장 겹침", cat="13F 복제",
            pr_hint="M",   # 월 리밸 계열이다(대조군도 '같은 풀 동일가중(월 리밸)')

            rule=_rule + " 분기마다 다시 고르고, 공시일이 체결일보다 뒤인 운용사는 그 분기 "
                         "세지 않는다(그때는 아직 알 수 없던 정보다).",
            why="<b>%s.</b> 같은 풀(S&P 500 ∪ NASDAQ 100 동일가중) 대비 Δ샤프 %s · "
                "알파 %s%%/yr (t %s). SPY 총수익 대비로는 알파 %s%%/yr (t %s)로 이겼지만, "
                "이 랩은 더 어려운 쪽인 같은 풀을 잣대로 둔다 — 유니버스가 대형주라 지수를 "
                "넘는 것은 동일가중이 만든 사이즈 틸트로도 설명되기 때문이다."
                % (_ov_grade(ds, pl.get("t")), ds,
                   pl.get("alpha"), pl.get("t"),
                   (v.get("spy") or {}).get("alpha"), (v.get("spy") or {}).get("t")),
            note="같은 아이디어의 변형 %d개 중 하나다 — 문턱 4개와 좁힌 판 2개를 함께 쟀고 "
                 "어느 다중검정 보정으로도 통과 0건이다. 명단 17곳이 사후 선택이고 유니버스·"
                 "CUSIP 매핑이 오늘 스냅샷이라 생존편향은 위쪽으로 남는다. 거래비용 0."
                 % ((ovd.get("multiplicity") or {}).get("m") or 6),
            bench_label="같은 풀 동일가중(월 리밸)",
            start=v.get("start"), end=v.get("end"),
            metrics=m, bench=dict(bm, label="같은 풀 동일가중(월 리밸)"),
            d_sharpe=ds, t=pl.get("t"), beta=pl.get("beta"),
            turnover=(v.get("turnover") or {}).get("mean"),
            holdings=({"kind": "xsec", "tickers": (v.get("latest") or {}).get("tickers")}
                      if (v.get("latest") or {}).get("tickers") else None),
        ))
        _ovn += 1
    if _ovn:
        print("  거장 겹침 %d종 추가(대조군 = 같은 풀 동일가중)" % _ovn)

    # ── 목록 제외(운용 결정) ────────────────────────────────────────────────
    # 사용자 결정(2026-07-27). 위험감축 5종·방어보험 3종 + 합병차익 1종을 목록에서 뺀다.
    #
    # ⚠ 위와 같은 원칙이다 — **화면 목록에서만 빼고 측정 기록은 그대로 둔다.**
    #   asset_strategies.json·archive_backtests.json·deploy_index.json 은 손대지 않는다.
    #   진 것을 원본에서 지우면 다중검정 N이 줄어 남은 것이 쉽게 통과한다(자기에게 유리한 보정).
    #
    # 🚨 2026-07-30: 위험감축 7종에 대해서만 이 원칙의 **예외**를 두었다(사용자 결정).
    #   목록 제외가 아니라 원본에서 지웠다 — 등록부(asset_backtest 의 s_voltgt·s_ddgate·
    #   s_volregime)와 수기 정본(deploy_index·strategy_detail·strategy_backtests·
    #   archive_index·archive_backtests)에서 전부 제거했다.
    #   그래서 여기 HIDE_SIDS 에 있던 dynamic-vol-target·duration-scaling·
    #   bond-regime-overlay-agg 세 줄도 같이 없앴다(가리킬 대상이 없어 가드가 '제외가 풀렸다'로 죈다).
    #   ⚠ 지우기 전에 위 우려를 실제로 재 봤다 — **문턱은 거의 안 움직인다.**
    #     자산배분 n 57 → 54 · t_crit 3.33 → 3.31 이고, 그 사이(3.31~3.33)에 들어와 판정이
    #     뒤집히는 전략은 **0종**이다(남는 것 중 최고 |t| 는 머신러닝 횡단면 3.02).
    #     종목전략 t_crit 3.33 은 애초에 이 7종을 안 세므로 **불변**이다.
    #   ⚠ archive_backtests 의 n_tests_total(20)은 줄이지 않았다 — 그 값은 '게시 건수'가 아니라
    #     '재검을 몇 번 돌렸나'이고, 지운 것을 빼면 보정 분모가 관대해진다(validate 게이트의 취지).
    #   ⚠ rotation_pool 의 랩 판정 배지 1건('변동성 타게팅' → 변동성 타깃팅 NDX '기각')은 남겼다.
    #     그 판정은 실제로 내려졌던 것이고 배지는 자립 문안이라, 지우면 기록을 과하게 정리하는 쪽이다.
    #   되살리려면 커밋 78815cd3 다음 커밋의 역패치를 적용하면 된다(git 에 전문이 남아 있다).
    #
    # ⚠⚠ 이 제외는 **성과 판정이 아니다.** 이 전략들의 headline 은 최대낙폭이고, 그 축에서는
    #    낮을수록 좋다 — 빠지는 8종 중 −11.19%·−12.33%·−15.30% 는 전 목록에서 가장 좋은 낙폭이다.
    #    자기 목적(모전략 낙폭 감축) 기준으로는 대체로 성공한 축에 든다:
    #      채권 레짐 오버레이 Sharpe 0.977→0.994 · 듀레이션 스케일링 0.177→0.213 ·
    #      동적 변동성 타깃팅 낙폭 −18.53%→−15.30%(Sharpe −0.021)
    #    벤치 대비 명확히 열위인 것은 3종뿐이다(목표변동성 8% 0.435→0.224 ·
    #    테일 헤지 SPY+VIXY 0.629→0.581 · 테일 헤지 Long-Vol 0.659→0.422).
    #    그럼에도 목록에서 빼는 것은 "이 랩에서 이 계열을 다루지 않는다"는 운용 결정이지
    #    "성과가 나쁘다"는 측정 결과가 아니다. 되살리려면 이 집합에서 sid 를 빼면 된다.
    HIDE_SIDS = {
        # (배포 원장의 위험감축 3종은 2026-07-30 에 원본째로 삭제 — 위 주석 참조)
        "a-rp-voltarget", "a-vol-roll", "a-tail-hedge",                        # 자산배분
        "r-low-beta-weight-tilt", "r-tail-risk-hedge",                         # 기각 재검
        # 합병차익거래(2026-07-27 추가, 사용자 결정). 같은 원칙 — 목록에서만 빼고 기록은 둔다.
        #   실측: CAGR 2.66% · Sharpe −0.109 (대조군 SHY 1.33% · −1.778). Δ샤프 +1.669 는
        #   대조군의 변동성이 1.34%로 극단적으로 작아 생긴 증폭이지 초과수익의 크기가 아니다
        #   (asset_backtest.py 150행에 같은 함정을 적어 뒀다). 절대수익형인데 Sharpe 가 음수다.
        "a-merger-arb",                                                        # 자산배분
        # 섹터 리스크패리티(2026-07-28 추가, 사용자 결정).
        #   실측: CAGR 10.23% vs 대조군(9섹터 동일가중) 10.46% · Sharpe 0.430 vs 0.426 ·
        #   Δ샤프 +0.004 · t −0.96 · MDD −49.24%. 변동성 역수로 가중해도 동일가중과
        #   구별되지 않는다 — 9개 섹터는 서로 충분히 닮아서 가중을 바꿔도 남는 게 없다.
        "a-sector-rp",                                                         # 자산배분
        # 거장 겹침 계열 전부(2026-07-28 추가, 사용자 결정). K=2~5 네 개와 상위 10 변형 두 개.
        #   '명단 운용사 중 K곳 이상이 들고 있는 종목'이라는 규칙 자체를 explorer 에서 다루지
        #   않기로 한 것이지 성과 판정이 아니다. 실측으로도 판정은 이미 갈려 있었다 —
        #   여섯 중 넷이 '구별 불가', 둘이 '열위'로 통과가 하나도 없다.
        #   ⚠ data/guru_overlap.json 은 손대지 않는다. guru.html#overlap 과 진단물은 그대로다.
        "g-overlap-k2", "g-overlap-k3", "g-overlap-k4", "g-overlap-k5",
        "g-overlap-top10-ov", "g-overlap-top10-mc",                            # 거장 겹침
        # 수익엔진 다섯(2026-07-29 추가, 사용자 결정). 판정은 이미 갈려 있었다 —
        #   회전율 밴드 '제한적 유효' · 오버나이트 보유 '구별 불가' · 나머지 셋 '열위'.
        #   통과는 하나도 없다. 목록에서만 빼고 측정 기록은 원본에 그대로 둔다(다중검정 N 유지).
        "eps-revision-turnover-band",                                          # 리비전 변형
        "a-overnight-ndx", "a-vrp-shortvol", "a-overnight", "a-quality-tilt",  # 자산배분
        # 페어 트레이딩 넷(2026-08-12 추가, 사용자 결정). 같은 날 사전등록해 돌린 배치이고
        #   (build/PREREG-2026-08-12-PAIRS.md) **넷 다 '열위'** 로 통과가 하나도 없다.
        #   목록에서만 빼고 측정 기록은 원본에 그대로 둔다 —
        #   data/pairs_strategies.json·pairs_book.json 과 사전등록·결과 문서는 손대지 않는다.
        #   ⚠ 진 것을 원본에서 지우면 다중검정 N 이 줄어 남은 것이 쉽게 통과한다.
        "p-ggr-top5", "p-ggr-top20", "p-comb-top5", "p-comb-top20",            # 페어 트레이딩
    }
    # ⚠ 이 가드는 'sid 가 바뀌어 제외가 조용히 풀렸나'를 보는 것이다. 그런데 앞의 채권 대조군
    #   필터가 먼저 지운 전략은 rows 에 없어 '못 찾음'으로 오인된다 — 두 제외는 공존해야 한다.
    #   그래서 이미 다른 사유로 빠진 sid 도 찾은 것으로 센다.
    # ── 국면별 성적 — 사용자 요청 2026-08-12(경기 사이클과 전략을 잇는다) ──────────
    # 🚨 이름으로 잇는다. 원천마다 sid 접두사가 다른데(t-·a-·r-·접두사 없음) 그 규칙을 여기
    #   또 적으면 한쪽만 고쳐지는 날이 온다. 이름은 이 파일이 이미 배포 원장 조인에 쓰는 키다.
    _RGM = _regime_months()
    if _RGM:
        _mon = {}
        for _f in ("tech_strategies.json", "asset_strategies.json", "guru_clone.json",
                   "pairs_strategies.json"):
            for _x in ((load(_f) or {}).get("strategies") or []):
                if isinstance(_x, dict) and _x.get("name"):
                    _mon.setdefault(_x["name"], _monthly_rets(_x))
        for _nm, _x in ((load("strategy_backtests.json") or {}).get("strategies") or {}).items():
            _mon.setdefault(_nm, _monthly_rets(_x))
        _hit = 0
        for _r in rows:
            _st = _regime_stats(_mon.get(_r["name"]) or [], _RGM)
            if _st:
                _r["rg"] = _st; _hit += 1
        print("  국면별 성적 %d/%d종 (%s)" % (_hit, len(rows), _regime_meta(_RGM)["span"]))

    _found = ({r["sid"] for r in rows if r["sid"] in HIDE_SIDS}
              | {sid for sid in HIDE_SIDS if sid in _hidden_sids})
    _hid2 = [(r["name"], r["role"]) for r in rows if r["sid"] in HIDE_SIDS]
    rows = [r for r in rows if r["sid"] not in HIDE_SIDS]
    if _found != HIDE_SIDS:
        # 원본에서 sid 가 바뀌면 제외가 조용히 풀려 목록에 도로 나타난다. 오타로 처음부터
        # 아무것도 안 지워지는 경우도 같은 방식으로 잡힌다.
        raise SystemExit("제외 대상 sid 를 원본에서 못 찾았다: %s — sid 가 바뀌었는지 확인할 것"
                         % sorted(HIDE_SIDS - _found))
    if _hid2:
        print("  목록 제외 %d종(사용자 결정) — 측정 기록에는 남는다:" % len(_hid2))
        for _n, _r in sorted(_hid2, key=lambda x: (x[1], x[0])):
            print("    · [%s] %s" % (_r, _n[:48]))

    # 정렬 — 성격 → 등급 → 이름. 파일 출처가 아니라 역할로 줄 세운다.
    rows.sort(key=lambda r: (ROLE_ORDER.index(r["role"]) if r["role"] in ROLE_ORDER else 99,
                             GRADE_ORDER.index(r["grade"]) if r["grade"] in GRADE_ORDER else 99,
                             r["name"]))

    from collections import Counter
    doc = {
        "note": "전 전략 통합 목록. 파일 출처가 아니라 **성격**(무엇을 하는 전략인가)으로 묶는다. "
                "수치는 원본에서 그대로 옮긴 것이며 여기서 계산하지 않는다. "
                "구간·대조군이 전략마다 다르므로 같은 숫자를 세로로 비교하면 안 된다.",
        "as_of": (t.get("as_of") or a.get("as_of")),
        # 🚨 게시 관문의 현재 상태를 그대로 옮긴다. 화면이 배지 뜻을 스스로 적으려면
        #   이 값이 필요하다 — 안 옮기면 관문을 껐는데 화면은 계속 "셋을 다 넘었다"고 말한다.
        #   여기서 판단하지 않는다. 정본은 build/tech_backtest.py 의 GATE_* 스위치다.
        "gates": t.get("gates"),
        "gates_note": t.get("gates_note"),
        "n": len(rows),
        # 의도적으로 목록에서 뺀 것들. validate 의 '원본 합계와 맞나' 가드가 이 수를 더해
        # 검사하므로, 여기 기록하지 않으면 낡은 목록 검출이 무력해진다.
        "n_hidden": len(_hidden) + len(_hid2) + len(_mcf),
        "hidden": ([{"name": _n, "sharpe": _s} for _n, _s in sorted(_hidden, key=lambda x: -x[1])]
                   + [{"name": _n, "role": _r} for _n, _r in sorted(_hid2, key=lambda x: (x[1], x[0]))]
                   + [{"name": _n, "why": "시총 하한 변형"} for _n in sorted(_mcf)]),
        # ⚠ 이 문구를 반드시 남긴다. 넷이 화면에서 사라지면 다음 사람은 밑동의 CAGR 53% 만
        #   보게 되는데, 그 값의 44%p 가 생존편향이라는 사실이 이 줄에만 남는다.
        "hidden_note_mcf": (
            "시가총액 하한 변형 %d종을 목록에서 뺐다(사용자 결정 2026-08-13). "
            "⚠ 성적이 나빠서가 아니다 — 이 넷은 생존편향을 재려고 등록한 진단이고"
            "(PREREG-2026-08-12-MCAPFLOOR), 편향이 절반 빠진 만큼 CAGR 이 낮게 나온다"
            "(45.24→20.99 · 43.74→17.42 · 31.01→12.59 %%p). 즉 밑동보다 진짜에 가까운 "
            "숫자다. 측정은 계속한다 — tech_strategies.json 에 그대로 있고 다중검정 N 도 "
            "줄이지 않는다." % len(_mcf)) if _mcf else None,
        "hidden_note_defensive": (
            "위험감축·방어보험·합병차익·섹터RP·거장겹침·수익엔진 %d종을 목록에서 뺐다(사용자 결정). "
            "이 계열들을 이 랩에서 다루지 않기로 한 **운용 결정**이지 성과 판정이 아니다 — "
            "방어 계열의 headline 은 최대낙폭이고 그 축에서는 낮을수록 좋아서, 빠지는 8종 중 "
            "−11.19%%·−12.33%%·−15.30%% 는 전 목록에서 가장 좋은 낙폭이다. "
            "합병차익(a-merger-arb)은 낙폭 계열이 아니라 별건이며, 단독 Sharpe −0.109 로 "
            "절대수익형의 목적을 못 채운 쪽이다. "
            "수익엔진 다섯(회전율 밴드·오버나이트 둘·숏볼·퀄리티 틸트)은 판정이 이미 갈려 "
            "있었다 — 제한적 유효 1·구별 불가 1·열위 3 으로 통과가 없다. "
            "여기서도 **측정 기록은 지우지 않는다** — asset_strategies.json·"
            "archive_backtests.json·deploy_index.json 은 그대로 둔다."
            % len(_hid2)) if _hid2 else None,
        "hidden_note": ("대조군에 채권 ETF 가 섞였거나(잣대가 달라진다) 이 랩에서 다루지 않기로 한 "
                        "%d종은 목록에서 뺐다(사용자 결정). **측정 기록에서 지운 것은 아니다** — "
                        "원본 파일은 전부 그대로이고, 다중검정 N 도 줄이지 않는다."
                        % len(_hidden)) if _hidden else None,
        "role_order": ROLE_ORDER, "grade_order": GRADE_ORDER,
        "by_holds": dict(Counter(r["holds"] for r in rows)),
        "by_cmp": {"가능": sum(1 for r in rows if r["cmp_ok"]),
                   "애매": sum(1 for r in rows if not r["cmp_ok"])},
        "holds_order": ["종목", "비중", "페어", "노출", "없음"],
        "pr_note": "‘같은 구간 지수(PR)’는 판정용이 아니라 세상의 눈금이다. 전략과 같은 함수·같은 "
                   "월말 주기로 재 CAGR·변동성·MDD·샤프를 모두 싣는다. 다만 전략 수익은 배당을 "
                   "재투자한 총수익(TR)인데 지수는 가격지수(PR)라 배당이 빠져 있고, 2006년 이후 "
                   "그 격차가 연 2.0%p다 — 수익 쪽 비교에서 전략이 그만큼 유리해 보인다"
                   "(변동성·MDD·샤프는 이 왜곡이 훨씬 작다). "
                   "🚨 2026-08-13 부터 판정 대조군도 전부 가격지수(PR)다(사용자 결정 — 종전에는 "
                   "종목 랩만 PR, 자산 랩과 배포 원장은 SPY·NDX 총수익이라 한 화면에서 두 표기가 "
                   "갈렸다). 그래서 위 왜곡은 눈금 줄만이 아니라 **판정에도 그대로 들어간다** — "
                   "전략은 배당을 받고 대조군은 못 받는다. 실측으로 자산 랩 35종 중 13종이 그 "
                   "한 가지 때문에 CAGR 열세에서 우위로 바뀌었다. 전략이 좋아진 것이 아니다.",
        "cmp_note": "대조군이 전략과 같은 것을 목표로 할 때만 Δ샤프를 우열로 읽을 수 있다. "
                    "위험감축은 목표가 낙폭이라 상시보유와 CAGR·샤프로 겨루면 "
                    "지는 것이 정상이고, 대조군이 현금성이면 샤프 분모가 0에 가까워 Δ가 허수가 된다. "
                    "그런 전략은 따로 묶어 낙폭·위기 구간으로 본다.",
        "rg_meta": _regime_meta(_RGM) if _RGM else None,
        "by_role": dict(Counter(r["role"] for r in rows)),
        "by_grade": dict(Counter(r["grade"] for r in rows)),
        "by_src": dict(Counter(r["src"] for r in rows)),
        "items": rows,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("전략 통합 %d개 · %.0fKB" % (len(rows), os.path.getsize(OUT) / 1024))
    print("  구성:", doc["by_holds"], "· 대조군 비교", doc["by_cmp"])
    print("  성격:", doc["by_role"])
    print("  등급:", doc["by_grade"])
    print("  출처:", doc["by_src"])
    miss = [r["name"] for r in rows if r["role"] == "미분류"]
    if miss:
        print("  ⚠ 성격 미분류 %d건: %s" % (len(miss), ", ".join(m[:20] for m in miss[:6])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
