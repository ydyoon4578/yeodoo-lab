# -*- coding: utf-8 -*-
"""홈 전용 초소형 요약(data/home_reco.json) — **홈이 읽는 유일한 대형 데이터 대체물**.

홈은 stocks.json(raw 691KB · gz 199KB)·rotation_pool.json·strategy_backtests.json 을 절대 fetch하지
않는다. 대신 빌드가 필요한 값만 여기에 구워 1~2KB로 만든다.

담는 것
  ① 스윙 타점 상위 10+10 — 확정/잠정 지위 포함
  ② 확정·잠정 **카운트** — '오늘 표시된 16건이 전부 잠정'인데 카드가 "확정 스윙 타점"을 내세우는
     불일치가 실제로 있었다. 숫자를 함께 실어 화면이 스스로 드러내게 한다.
"""
from __future__ import annotations
import io, json, os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

# GICS 영문 섹터는 홈의 좁은 행에서 잘린다 — 짧은 한글로(stocks.html의 SECKO와 같은 표기)
SECKO = {"Information Technology": "IT", "Health Care": "헬스케어", "Financials": "금융",
         "Consumer Discretionary": "경기소비", "Consumer Staples": "필수소비", "Industrials": "산업재",
         "Communication Services": "커뮤니케이션", "Energy": "에너지", "Utilities": "유틸리티",
         "Real Estate": "부동산", "Materials": "소재"}
WIN = 10          # 최근 N거래일 내 타점만 홈에 노출
TOP = 10


def _lastmk(s, key):
    a = s.get(key) or []
    return a[-1] if a else -1


def _reco(stocks, dates, conf_key, prov_key):
    """확정(conf)·잠정(prov) 중 최신 타점을 취한다. prov가 더 최신이면 아직 이동 가능."""
    N = len(dates)
    c = []
    for s in stocks:
        mc, mp = _lastmk(s, conf_key), _lastmk(s, prov_key)
        m = max(mc, mp)
        if m < 0 or (N - 1 - m) > WIN:
            continue
        c.append((m, mp > mc, s))
    c.sort(key=lambda x: -x[0])
    rows = [{"t": s["t"], "name": (s.get("name") or "")[:16], "dt": dates[m][5:], "ago": N - 1 - m,
             "sec": SECKO.get(s.get("sector") or "", (s.get("sector") or "")[:6]),
             **({"prov": 1} if pv else {})} for m, pv, s in c[:TOP]]
    n_prov = sum(1 for _, pv, _ in c if pv)
    return rows, len(c), len(c) - n_prov, n_prov      # 목록 · 전체 · 확정 · 잠정


# ⚠ SIC 대분류(2자리) 한글 이름표가 여기 있었다 — 2026-08-03 에 하위 분류를 GICS
#   서브산업으로 바꾸면서(사용자 요청 "sic말고 gics") 쓰는 곳이 없어졌다.
#   홈의 섹터가 GICS(위키 S&P 500 표)라 하위도 같은 체계여야 트리가 성립하기 때문이다.
#   그 뒤 industry.html 도 GICS 로 넘어가면서(같은 날) 사이트에 SIC 는 남아 있지 않다.
# GICS 섹터 → 섹터 ETF 티커. **키를 한글 이름이 아니라 티커로 둔다** — 홈이
# market_board.json 의 sector 행과 짝지어 그리는데, 한글 표기가 바뀌는 날 조인이 조용히 끊긴다.
# _breadth(섹터별 폭)와 _industry(섹터-산업 트리)가 같이 쓴다.
SEC_ETF = {"Information Technology": "XLK", "Financials": "XLF", "Health Care": "XLV",
           "Consumer Discretionary": "XLY", "Communication Services": "XLC",
           "Industrials": "XLI", "Consumer Staples": "XLP", "Energy": "XLE",
           "Utilities": "XLU", "Real Estate": "XLRE", "Materials": "XLB"}
SEC_KO = {v: SECKO[k] for k, v in SEC_ETF.items()}
# ETF 티커 → GICS **영문** 섹터명. 산업그룹 이름과 글자로 맞대 보려고 둔다(SEC_KO 는 한글이라
# 'Energy' 와 '에너지'를 같다고 말할 수 없다). 여기서만 쓰지만 SEC_ETF 를 뒤집는 규칙이
# 두 곳에 생기면 한쪽만 고쳐지는 날이 오므로 정본을 하나 둔다.
ETF_GICS = {v: k for k, v in SEC_ETF.items()}

# 티커 → CIK. 시가총액 **합**에서 같은 회사를 두 번 더하지 않으려고 쓴다(agg 참조).
# 파일이 없으면 빈 지도 — 그러면 예전처럼 더해지고, 그 사실이 아래 dual 개수 0 으로 드러난다.
CIK_OF = {}
try:
    CIK_OF = {t: c for t, c in (json.load(io.open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                     "data", "cik_map.json"), encoding="utf-8")).get("co") or {}).items() if c}
except Exception:
    pass
# 실측(2026-08-03, GICS 서브산업 127개): MIN 3 이면 71개·커버 83% · MIN 4 면 49개·커버 70% ·
# MIN 5 면 36개·커버 59%. 섹터 안에 접어 두므로 한 번에 보이는 것은 한 섹터분(6~7줄)이라
# 개수보다 커버를 택했다. 3종 평균은 얇지만 줄마다 종목수를 함께 낸다.
NOM = "그 밖"      # 나머지 줄 이름 — 부모 id 를 만들 때도 쓰므로 한 곳에 둔다
IND_MIN = 3        # 이보다 적은 묶음은 '산업 평균'이라 부를 수 없다 — 종목 몇 개의 평균이다
# 🚨 산업그룹(2차)만 문턱을 따로 둔다 — 2026-08-10.
#   위 IND_MIN=3 의 근거는 **서브산업(4차·127칸)** 실측이다. 그 단은 2026-08-05 에 없앴고
#   지금 이 값이 실제로 거르는 것은 산업그룹(2차·25칸)인데, 거기서는 유니버스 전체를 통틀어
#   딱 한 묶음만 걸린다 — 부동산의 Real Estate Management & Development(CBRE·CSGP 2종).
#   그 하나 때문에 '그 밖' 줄이 남았다.
#   2종을 '그 밖'이라 부르는 것보다 제 이름으로 '2종'이라 적는 것이 더 정확하다 —
#   줄마다 종목수를 함께 내므로 얇다는 사실은 화면이 이미 말한다. 이름을 지울 이유가 없다.
#   ⚠ IND_MIN 은 그대로 둔다. 아래 tiers 표가 '왜 3·4차를 안 쓰는지'를 그 값으로 설명하고
#     있어서, 같이 바꾸면 그 설명문의 수치(MIN 3 이면 71개·커버 83%)가 거짓이 된다.
GRP_MIN = 2        # 산업그룹(2차) 표시 문턱
# ⚠ 기간 규칙은 build/market_board.py 의 HOR 와 **같아야 한다.** 홈에서 섹터 카드 바로
#   아래에 산업 카드가 붙으므로, 두 카드의 '1개월'이 다른 날을 가리키면 나란히 못 읽는다.
#   그쪽은 달력일 차감 후 그 날짜 이하의 마지막 관측을 쓴다(_base_dates + _at) — 같은 규칙이다.
# 구간은 build/market_board.py 의 HOR 와 **글자 그대로 같다**(+YTD). 홈에서 섹터 11행과
# 산업 27행이 **한 표**에 들어가므로(2026-08-03 사용자 요청 "스타일처럼 걍 수익률로"),
# 두 묶음의 '3개월'이 다른 날을 가리키면 같은 열에서 못 읽는다.
IND_HOR = [("1D", 1), ("1W", 7), ("1M", 30), ("3M", 91), ("6M", 181), ("12M", 365)]


def _industry(stocks, dates, root):
    """섹터 11개와 그 **하위 산업**을 한 덩어리로 → {"sectors": [...], "rows": [...], ...}

    하위 분류는 **GICS 다.** 위키백과 GICS 문서에서 4단 구조 전문을 받아
    (build/refresh_members.gics_tree) members.json 에 종목마다 산업그룹·산업·서브산업을
    실어 둔다. 홈은 그중 **두 단**을 쓴다 — 섹터(1차) → 산업그룹(2차) → 서브산업(4차).

    왜 이 두 단인가(실측 2026-08-03 · GICS 있는 503종):
        산업그룹(2차)  25개 중 3종이상 24개 · 커버 **100%**   ← 중간 단으로 완벽하다
        산업(3차)      69개 중 3종이상 51개 · 커버  94%
        서브산업(4차)  127개 중 3종이상 71개 · 커버  83%      ← 가장 잘다
      2차는 빠짐 없이 덮고 4차는 가장 잘다. 3차는 둘 사이라 따로 세우면 층만 하나 늘고
      새로 보이는 것이 없다 — 접히는 표에서 층은 비용이다.

    🚨 SIC 를 쓰지 않는다(사용자 결정 2026-08-03). SIC(SEC 부여)와 GICS 섹터는 다른 분류라
      한 SIC 가 여러 섹터에 걸쳤다 — 사업서비스 63종이 IT 26 · 금융 13 · 산업재 9 …(순도 41%),
      순도 90% 미만이 27개 중 14개였다. GICS 는 정의상 트리라 그 문제가 없다.
    ⚠ NDX 전용 15종(ASML·ARM·PDD·SHOP·MELI·MSTR …)은 GICS 가 없다. 위키 NASDAQ-100 표는
      ICB 분류라 GICS 를 싣지 않는다 — 추측으로 채우지 않고 각 단의 '그 밖' 줄로 보낸다.
    ⚠ 하위에 못 들어간 종목은 단마다 '그 밖' 한 줄로 남긴다. 안 남기면 합이 부모에 못 미치는데
      화면은 그 사실을 말하지 않는다.
    """
    mem_p = os.path.join(root, "data", "members.json")
    if not os.path.exists(mem_p):
        return {}
    mem = (json.load(io.open(mem_p, encoding="utf-8")) or {}).get("members") or {}
    if not mem:
        return {}
    import datetime as _dt
    d0 = _dt.date.fromisoformat(dates[-1])
    base = {}
    for k, tgt in [(k, (d0 - _dt.timedelta(days=nd)).isoformat()) for k, nd in IND_HOR] + \
                  [("YTD", "%d-12-31" % (d0.year - 1))]:      # YTD 는 전년 말 — market_board 와 같다
        ks = [i for i, d in enumerate(dates) if d <= tgt]
        base[k] = ks[-1] if ks else None

    # 섹터 → 산업그룹 → 서브산업. GICS 는 트리라 상위 단이 하위 단을 유일하게 결정한다.
    bysec, bygrp, bysub, gsec = {}, {}, {}, {}
    for s in stocks:
        sec = SEC_ETF.get(s.get("sector") or "")
        if not sec:
            continue
        bysec.setdefault(sec, []).append(s)
        m2 = mem.get(s["t"]) or {}
        grp, sub = (m2.get("grp") or "").strip(), (m2.get("sub") or "").strip()
        if grp:
            bygrp.setdefault((sec, grp), []).append(s)
            gsec[grp] = sec
            if sub:
                bysub.setdefault((grp, sub), []).append(s)

    keepg = {k: v for k, v in bygrp.items() if len(v) >= GRP_MIN}
    keeps = {k: v for k, v in bysub.items() if len(v) >= IND_MIN}

    # ── 왜 3차(산업)를 안 쓰는지 **화면이 스스로 말하게** 한다 ──────────────
    # 이 트리는 1차 → 2차 → 4차다. 번호를 그렇게 적어 놓고 3차가 어디 갔는지는
    # 말하지 않아서, 읽는 사람이 곧바로 "3차는?" 하고 묻게 돼 있었다(사용자 지적).
    # 사유는 코드 주석에만 있었다 — 화면에 없으면 없는 것이다. 여기서 재서 실어 보낸다.
    # 🚨 손으로 적지 않는다. 숫자가 바뀌면 문장도 같이 바뀌어야 한다.
    tiers, has = [], [s for s in stocks if (mem.get(s["t"]) or {}).get("sub")]
    for lbl, key in (("섹터", "sector"), ("산업그룹", "grp"), ("산업", "ind"), ("서브산업", "sub")):
        cnt = {}
        for s in has:
            v = ((s.get("sector") if key == "sector" else (mem.get(s["t"]) or {}).get(key)) or "").strip()
            if v:
                cnt[v] = cnt.get(v, 0) + 1
        big = {k: v for k, v in cnt.items() if v >= IND_MIN}
        tiers.append({"nm": lbl, "n": len(cnt), "keep": len(big),
                      "cov": round(sum(big.values()) / max(1, len(has)) * 100)})
    # 3차가 4차와 **구성이 완전히 같은** 칸의 수. 이것이 3차를 뺀 진짜 이유다 —
    # 그 칸들은 층을 하나 더 만들 뿐 새로 갈리는 것이 없다.
    _ci, _cs = {}, {}
    for s in has:
        m2 = mem.get(s["t"]) or {}
        for d, k in ((_ci, "ind"), (_cs, "sub")):
            v = (m2.get(k) or "").strip()
            if v:
                d[v] = d.get(v, 0) + 1
    dup = sum(1 for k, v in _ci.items() if _cs.get(k) == v)
    # 이중클래스(같은 CIK 를 쓰는 티커) — 시총 합에서 뺀 양을 화면이 각주로 적을 수 있게 낸다.
    # 🚨 손으로 적으면 안 된다. 지수에 이중클래스가 하나 더 들어오는 날 문장이 조용히 틀린다.
    _bycik, _dual_mc, _dual_t = {}, 0.0, []
    for s in stocks:
        c = CIK_OF.get(s["t"])
        if c:
            _bycik.setdefault(c, []).append(s)
    for c, ss in _bycik.items():
        if len(ss) < 2:
            continue
        _dual_t.append(sorted(x["t"] for x in ss))
        vs = sorted((float((x.get("fund") or {}).get("mc") or 0) for x in ss), reverse=True)
        _dual_mc += sum(vs[1:])          # 가장 큰 것 하나만 남기고 나머지가 뺀 금액이다
    # 수기로 산업그룹을 채운 종목 수 — 화면이 "이 중 N종은 수기 분류"라고 말한다.
    #   세는 것은 members.json 의 grp_src 다(build/refresh_members.py 가 찍는다).
    #   🚨 손으로 적지 않는다. 위키가 나중에 GICS 를 실으면 grp_src 가 저절로 사라지고
    #     화면의 숫자도 같이 줄어야 한다 — 상수로 박으면 그날 조용히 거짓말이 된다.
    _man = sum(1 for s in stocks if (mem.get(s["t"]) or {}).get("grp_src") == "manual")
    gics_tiers = {"n_gics": len(has), "n_all": len(stocks), "rows": tiers,
                  "ind_dup": dup, "ind_n": len(_ci), "min": IND_MIN, "grp_min": GRP_MIN,
                  "manual_grp": _man,
                  "dual": sorted(_dual_t), "dual_mc": round(_dual_mc) or 0}
    PX = _load_px([s["t"] for v in bysec.values() for s in v], dates, root)
    # 🚨 2026-08-11 — 섹터 줄은 **섹터 ETF 그 자체**를 쓴다(사용자 결정). 종전에는 유니버스
    #   종목의 동일가중이었고, 그래서 같은 화면이 한 섹터에 두 숫자를 말했다(이 표는 동일가중,
    #   시장 보드는 ETF). 어느 쪽이 맞다기보다 **한 화면에 한 정의**여야 한다.
    #   ETF 가격은 data/assets.json 에 2006년부터 다 있다. 격자를 dates 에 맞춘다.
    ETFPX = {}
    try:
        _A = json.load(io.open(os.path.join(root, "data", "assets.json"), encoding="utf-8"))
        _apos = {d: i for i, d in enumerate(_A["dates"])}
        for _t in SEC_ETF.values():
            _a = (_A.get("px") or {}).get(_t)
            if _a:
                ETFPX[_t] = [(_a[_apos[d]] if d in _apos else None) for d in dates]
    except Exception as _e:
        print("  ⚠ 섹터 ETF 가격을 못 읽었다(%s) — 섹터 줄이 빈다" % str(_e)[:50])


    # 샤프 — 스타일 표와 **같은 창**으로 잰다(2026-08-03 사용자 요청으로 두 표가 합쳐졌다).
    # data/style_trails.json 의 start 를 그대로 읽는다. 창을 여기서 따로 정하면 같은 열의
    # 두 숫자가 다른 기간이 되고, 합친 표의 존재 이유가 사라진다.
    #
    # 🚨 2026-08-13 사고 — 사용자가 "섹터 샤프는 다 1도 안 되는데 왜 지수들 샤프는 다 1이
    #   넘어" 라고 물어서 드러났다. 한 열에 **두 잣대**가 섞여 있었다:
    #     섹터 줄(이 함수)  5년 창 · 무위험 미차감 → XLK 0.88 · XLE 0.89 · XLRE 0.27
    #     지수·방법론 줄     1년 창 · 무위험 차감  → SPY 1.34 · QQQ 1.21 · RSP 1.33
    #   실측으로 화면 11칸이 '5년·rf미차감' 과 11/11 일치하고 '1년·rf차감' 과는 0/11 이었다.
    #   ① 창 — 2026-08-12 에 열을 5년으로 옮기며 여기도 start5 로 맞췄는데, 08-13 에 열을
    #     1년으로 되돌리면서(사용자 요청) index.html 만 고치고 이 파일을 안 고쳤다.
    #     ⚠ 아래 코드가 창을 **스스로 정하지 않게** 둔다. style_trails 의 start 하나만 본다.
    #   ② 무위험 — style_top_pdf.metrics() 는 2026-08-05 에 rf 차감으로 고쳐졌는데
    #     이 함수는 안 고쳐졌다(그 파일 _rfd() 독스트링이 "한쪽만 고쳐진 두 벌" 이라 적는다).
    #     같은 병이 같은 열에서 두 번 났다.
    # ⚠ 창과 rf 를 맞춰도 **리밸런스는 여전히 다르다** — 방법론 줄은 월말 리밸런스 백테스트고
    #   이 줄은 ETF 일간 매수후보유다. 화면 툴팁이 그 사실을 적는다(index.html 샤프 열).
    i_sh = None
    try:
        _st = json.load(io.open(os.path.join(root, "data", "style_trails.json"), encoding="utf-8"))
        # ⚠ start5 로 물러서지 않는다. 물러서면 이 줄만 5년이 되어 사고가 그대로 재발한다 —
        #   창을 못 정하면 차라리 샤프를 안 낸다(i_sh=None → sharpe() 가 None 을 돌려준다).
        _d0 = _st.get("start") or ""
        if not _d0:
            print("  ⚠ style_trails.json 에 start 가 없다 — 섹터 샤프를 내지 않는다"
                  " (5년 창으로 물러서면 지수 줄과 잣대가 갈린다)")
        _ks = [i for i, d in enumerate(dates) if d <= _d0] if _d0 else []
        i_sh = _ks[-1] if _ks else None
    except Exception:
        pass

    # 무위험 일할 — **정본은 build/style_top_pdf.py 의 _rfd() 다.** 글자 그대로 같은 식이어야
    # 한다(rf_monthly.json 의 monthly 평균 ÷ 21). 여기서 다르게 재면 같은 열의 두 숫자가
    # 다시 갈린다. ⚠ import 로 공유하지 않는 이유는 그 파일이 numpy·matplotlib 를 끌고
    #   오기 때문이다 — 홈 묶음은 그 의존을 지면 안 된다. 대신 식을 여기 못박고 출처를 적는다.
    _RFD = 0.0
    try:
        _m = (json.load(io.open(os.path.join(root, "data", "rf_monthly.json"),
                                encoding="utf-8")).get("monthly") or {})
        _RFD = (sum(_m.values()) / len(_m) / 21) if _m else 0.0
    except Exception:
        print("  ⚠ rf_monthly.json 을 못 읽었다 — 섹터 샤프가 초과수익 기준이 아니게 된다")

    def sharpe(objs, etf=None):
        # 🚨 2026-08-11 — 수익률을 시총가중으로 바꾸면서 여기도 같이 바꿨다. 한 줄의 수익률은
        #   시총가중인데 샤프만 동일가중이면 같은 줄의 두 숫자가 다른 바스켓을 가리킨다.
        #   창 시작 시점 시총으로 고정 가중한다(매수후보유 바스켓).
        # 🚨 2026-08-13 — **초과수익 기준이다**(위 _RFD 주석 참조). 종전에는 m/sd 로 rf 를
        #   안 뺐고, 같은 열의 지수·방법론 줄은 빼고 있었다. 왜곡폭이 rf/vol 이라 저변동
        #   줄일수록 부당하게 유리해진다 — 실측으로 XLP 0.54→0.27, XLK 0.88→0.73 이었다.
        if i_sh is None or i_sh >= len(dates) - 30:
            return None
        rs = []
        if etf:
            a = ETFPX.get(etf)
            if not a:
                return None
            for k in range(i_sh + 1, len(dates)):
                if a[k] and a[k - 1] and a[k - 1] > 0:
                    rs.append(a[k] / a[k - 1] - 1.0)
        else:
            W = {}
            for s2 in objs:
                w = _w_at(s2, i_sh)
                if w:
                    W[s2["t"]] = w
            for k in range(i_sh + 1, len(dates)):
                num = den = 0.0
                nok = 0
                for s2 in objs:
                    px = PX.get(s2["t"])
                    if px and px[k] and px[k - 1] and px[k - 1] > 0:
                        nok += 1
                        w = W.get(s2["t"])
                        if w:
                            num += w * (px[k] / px[k - 1] - 1.0); den += w
                if den > 0 and nok >= (1 if len(objs) == 1 else max(3, len(objs) // 2)):
                    rs.append(num / den)
        if len(rs) < 60:
            return None
        m = sum(rs) / len(rs)
        v = sum((x - m) ** 2 for x in rs) / (len(rs) - 1)
        sd = v ** 0.5
        return round((m - _RFD) / sd * (252 ** 0.5), 2) if sd > 0 else None

    # ⚠ 예전엔 인자로 sic(=SIC 이름표)을 하나 더 받아 줄마다 실었는데, GICS 로 갈아탄 뒤
    #   그 값이 label 과 글자 그대로 같아졌다(실측 95줄 전부 일치, 나머지는 null).
    #   같은 값을 두 키로 싣지 않는다 — 읽는 곳도 없었다.
    # 🚨 2026-08-11 — 동일가중을 걷어냈다(사용자 결정: "다 시총가중으로해 세부섹터도").
    #   종전 정의는 '종목별 비율의 단순평균' 이었다. 그러면 4조$ 짜리와 300억$ 짜리가 같은
    #   무게라 섹터 ETF 와 다른 숫자가 나오고, 같은 화면이 한 섹터를 두 번 다르게 말했다.
    #   ⚠ 가중치는 **기준일 시총**이어야 한다. 오늘 시총을 그대로 쓰면 '오늘 큰 회사' 가
    #     과거에도 컸던 것처럼 되어 선견이다. 주식수가 그 사이 안 바뀌었다고 보고
    #     mc(기준일) = mc(오늘) × 조정가(기준일) ÷ 조정가(오늘) 로 되돌린다.
    #   ⚠ 이중클래스는 시총 정보원이 **회사 전체 시총**을 양쪽에 똑같이 준다. 가중치로
    #     그냥 쓰면 그 회사가 두 배로 실린다 — 클래스 수로 나눠 회사 합이 한 번만 되게 한다.
    _cls_n = {}
    for _v in bysec.values():
        for _s in _v:
            _k = CIK_OF.get(_s["t"])
            if _k:
                _cls_n[_k] = _cls_n.get(_k, 0) + 1

    # ── 산업그룹 경로(홈 시계열 넷째 판, 2026-08-13 사용자 요청) ────────────────
    # 🚨 아래 agg() 와 **같은 식**이다. agg 는 끝점 하나만 내고 이것은 날짜마다 낸다 —
    #   그래서 마지막 점이 표의 그 칸과 글자 그대로 같다. 다른 식으로 만들면 그림과 표가
    #   같은 줄에서 다른 말을 하게 된다(이 저장소가 여러 번 겪은 그 유형이다).
    # ⚠ 가중치는 **기준일 시총**으로 고정한다(agg 와 같다). 날마다 다시 재면 그건 다른 지수다.
    IND_MAXPT = 90            # build/home_perf.py 의 MAXPT 와 같은 값 — 판끼리 점 수를 맞춘다
    ind_paths = {}
    # 산업그룹 → 부모 섹터(한글). 차트가 **섹터 판과 같은 색**을 쓰려면 이 짝이 있어야 한다
    #   (사용자 요청 2026-08-13). 섹터 색은 끝값 순으로 돌려 쓰므로 고정색이 아니다 —
    #   그래서 색을 여기서 정하지 않고 **짝만 넘긴다.** 색을 정하는 곳은 한 군데여야 한다.
    ind_sec = {}

    def _thin_ix(lo, hi, cap):
        m = hi - lo + 1
        if m <= cap:
            return list(range(lo, hi + 1))
        st = (m - 1) / float(cap - 1)
        out = sorted({lo + int(round(j * st)) for j in range(cap)})
        out[-1] = hi
        return out

    def path_of(objs, k):
        i0 = base.get(k)
        if i0 is None:
            return None
        ws, nok = [], 0
        for s2 in objs:
            px = PX.get(s2["t"])
            if not (px and px[i0] and px[-1] and px[i0] > 0):
                continue
            nok += 1
            w = _w_at(s2, i0)
            if w:
                ws.append((w, px, px[i0]))
        # 🚨 agg() 의 최소관측 규칙을 **그대로** 건다. 안 걸면 표가 '—' 인 줄이 그림에는
        #   선으로 나온다 — 실제로 그랬다(Real Estate Management & Development 2종:
        #   표 '—' vs 그림 −32.13). 같은 식이어야 한다는 계약은 문턱까지 같아야 성립한다.
        need = 1 if len(objs) == 1 else max(3, len(objs) // 2)
        if nok < need:
            return None
        den = sum(w for w, _p, _b in ws)
        if not (ws and den):
            return None
        ix = _thin_ix(i0, len(dates) - 1, IND_MAXPT)
        out = []
        for j in ix:
            num = 0.0
            for w, px, b in ws:
                v = px[j]
                if v is None:
                    num = None
                    break
                num += w * (v / b - 1.0)
            out.append(None if num is None else round(num / den * 100.0, 2))
        return {"ix": ix, "v": out}

    def _w_at(s2, i0):
        """기준일 i0 의 시가총액 가중치. 못 구하면 None(그 종목은 그 구간에서 빠진다)."""
        v = (s2.get("fund") or {}).get("mc")
        if not (isinstance(v, (int, float)) and v > 0):
            return None
        px = PX.get(s2["t"])
        if not (px and px[i0] and px[-1] and px[i0] > 0 and px[-1] > 0):
            return None
        w = float(v) * (px[i0] / px[-1])
        c = CIK_OF.get(s2["t"])
        return w / _cls_n[c] if (c and _cls_n.get(c, 1) > 1) else w

    def agg(objs, label, sec, lv=1, parent=None, sub=None, etf=None):
        r = {}
        for k in base:
            i0 = base[k]
            num = den = 0.0
            nok = 0
            if i0 is not None:
                if etf:
                    # 섹터 줄 — 섹터 ETF 실적을 **그대로** 쓴다(사용자 결정 2026-08-11).
                    # 🚨 2026-08-12 — 그런데 **여기서 재면 안 된다.** 이 빌더는
                    #   refresh-stocks(06:50) 안에서 도는데 assets.json 은
                    #   refresh-assets(07:34)가 굽는다. 47분 먼저 도는 쪽이 47분 뒤에 나올
                    #   파일을 읽으니 ETF 격자의 **마지막 칸이 늘 None** 이고, 아래
                    #   `a[-1]` 가드가 falsy 가 되어 7개 구간이 전부 null 로 나갔다
                    #   (실측 08-12: 11섹터 × 7구간 = 77칸 전부 빔. 기능을 넣은 날부터 계속).
                    #   → 화면이 data/market_board.json 에서 옮긴다(index.html mkSegRows).
                    #     지수 줄이 이미 그 파일에서 오므로 같은 기준일·같은 구간표가 된다.
                    #   ⚠ 여기서 '마지막 유효값으로 물러서기' 를 하면 안 된다. 그러면 섹터
                    #     줄만 어제까지를 재면서 같은 열의 다른 줄과 하루가 어긋난다 —
                    #     표는 멀쩡해 보이고 숫자만 틀린다. 안 재는 편이 낫다.
                    pass
                else:
                    for s in objs:
                        px = PX.get(s["t"])
                        if not (px and px[i0] and px[-1] and px[i0] > 0):
                            continue
                        nok += 1
                        w = _w_at(s, i0)
                        if w:
                            num += w * (px[-1] / px[i0] - 1.0); den += w
            # ⚠ 한 종목짜리 줄(종목 단)은 평균이 아니라 그 종목 자체다 — 최소 3관측 규칙을
            #   그대로 걸면 값이 통째로 빈다. 그 규칙은 '몇 종목의 평균을 산업이라 부르지
            #   말자'는 것이지 단일 종목을 막자는 것이 아니다.
            need = 1 if len(objs) == 1 else max(3, len(objs) // 2)
            r[k] = round(num / den * 100, 2) if (den > 0 and nok >= need) else None
        # 종목 줄은 **가볍게** 싣는다. 한 종목의 PER·폭·국면 통계는 종목 페이지가
        # 훨씬 잘 보여 주고, 417줄에 그것들을 얹으면 파일이 세 배가 된다(실측 166KB).
        # 여기서 답해야 하는 질문은 '이 산업 안에서 어느 종목이 끌었나' 하나다.
        # 시가총액 합(억$). 줄 정렬 기준이다 — 큰 것부터 보는 편이 시장을 읽는 순서에 맞다
        # (사용자 요청 2026-08-03 "종목이나 섹터는 가급적 시총순"). 없는 종목은 0 으로 친다.
        # 🚨 같은 회사를 두 번 더하지 않는다(사용자 지적 2026-08-04). 이중클래스는 티커가
        #   둘인데 시총 정보원(yfinance)이 **회사 전체 시총**을 양쪽에 똑같이 준다 —
        #   실측: GOOG 43,618억$ · GOOGL 43,554억$ 로 둘 다 알파벳 전체다. 그냥 더하면
        #   커뮤니케이션 섹터 시총이 13.05조$ 로 나오는데 그중 4.4조$ 가 알파벳 한 번 더다
        #   (51% 과대). FOX/FOXA · NWS/NWSA 도 같다.
        #   판정은 CIK 로 한다 — 티커 모양으로 추측하면 BRK.B·BF.B 같은 무관한 쌍을 묶는다.
        #   ⚠ 종목 **수**(n)는 줄이지 않는다. 두 클래스는 실제로 지수의 두 구성종목이다.
        #     줄이는 것은 '금액의 합'뿐이고, 그 사실을 화면 각주에 적는다.
        mc, seen = 0.0, set()
        for s2 in objs:
            v = (s2.get("fund") or {}).get("mc")
            if not (isinstance(v, (int, float)) and v > 0):
                continue
            key = CIK_OF.get(s2["t"]) or ("t:" + s2["t"])
            if key in seen:
                continue
            seen.add(key)
            mc += float(v)
        mc = round(mc) or None
        if sub is not None:                     # sub 가 있으면 종목 줄이다
            # 소수 한 자리로 줄인다. 종목 줄 417개가 두 자리를 들고 있으면 gz 가 10KB 늘고
            # (실측 19.7 → 29.7KB), 화면에서 종목 수익률의 둘째 자리를 읽을 일은 없다.
            # 샤프도 싣지 않는다 — 한 종목의 샤프는 종목 페이지가 맥락과 함께 보여 준다.
            # 🚨 2026-08-06 — 종가(px)를 싣는다(사용자 요청). 종전에는 수익률만 있어
            #   화면이 "ACN 이 1일 +2.8%"라고만 말했다 — 무엇이 그만큼 움직였는지는 없었다.
            #   PX 는 이 함수가 이미 들고 있다(수익률을 그것으로 만든다). 안 싣는 것이
            #   안 재는 것보다 나을 이유가 없다.
            #   ⚠ 배당조정가다 — 수익률과 **같은 계열**이어야 한다. 다른 데서 원주가를
            #     가져오면 같은 줄의 두 숫자가 서로 다른 것을 가리킨다.
            #   ⚠ 종목 줄에만 붙인다. 산업·섹터 줄은 여러 종목의 묶음이라 '주가'라는 단일
            #     숫자가 없다(평균가를 채우면 살 수 없는 값을 살 수 있는 것처럼 보인다).
            _p1 = PX.get(objs[0]["t"]) if objs else None
            _last = _p1[-1] if (_p1 and _p1[-1]) else None
            # 🚨 2026-08-12 — 지수 소속(ix)을 싣는다(사용자 요청). 홈 히트맵이 S&P 500 /
            #   나스닥 100 을 따로 볼 수 있어야 하는데, 종전 종목 줄에는 소속이 **아예 없었다**
            #   (st·n·lv 는 518종 전부 1·1·3 인 상수다). 화면이 나눌 근거가 없었다.
            #   ⚠ 새 파일을 만들지 않는다. members.json(113KB)을 홈이 받게 하면 히트맵 하나
            #     때문에 홈의 첫 화면 요청이 늘어난다 — 이 줄에 비트 하나를 붙이는 쪽이 싸다
            #     (실측 +2.6KB raw · 518줄).
            #   ⚠ 정본은 members.json 이다(stocks.json 에도 idx 가 있고 2026-08-12 실측으로
            #     518종 전부 일치하지만, 관문을 통과한 쪽은 members 다 — _idx_counts 와 같은
            #     것을 세야 눈썹의 종목 수와 히트맵 버튼의 종목 수가 어긋나지 않는다).
            #   비트: 1=SPX · 2=NDX · 3=둘 다. 실측 2026-08-10 — 416 / 15 / 87.
            _ix = set((mem.get(label) or {}).get("idx") or [])
            _ixb = (1 if "SPX" in _ix else 0) + (2 if "NDX" in _ix else 0)
            return {"nm": label, "sn": sub, "st": 1, "sec": sec, "n": 1, "mc": mc,
                    **({"px": round(float(_last), 2)} if _last else {}),
                    **({"ix": _ixb} if _ixb else {}),
                    # 🚨 2026-08-10 — 1자리에서 2자리로. 화면은 이 값을 **2자리로 그리는데**
                    #   (toFixed(2)) 1자리로 저장하고 있었다. 그래서 종목 줄의 둘째 자리는
                    #   518종 전부 0 이었고, 작은 움직임이 통째로 사라졌다 —
                    #   실측 MSFT 499.86 → 499.99 = +0.026% 가 '0.00%' 로 나갔고,
                    #   같은 날 그런 종목이 14개였다. 같은 열의 섹터·산업 줄은 반올림 없이
                    #   저장돼 진짜 2자리라, 한 열에 정밀도가 두 가지 섞여 있었다.
                    #   ⚠ 없는 정밀도를 그리는 것이 0 을 그리는 것보다 나쁘다 — 둘 중
                    #     맞추는 방향은 자료 쪽이다(화면을 1자리로 내리면 섹터 줄이 함께 뭉개진다).
                    "r": {k: (None if v is None else round(v, 2)) for k, v in r.items()},
                    "lv": lv, "p": parent}
        full = [s for s in objs if not s.get("part")]
        above = sum(1 for s in full if "200일이탈" not in (s.get("flags") or []))
        return {"nm": label, "sec": sec, "n": len(objs), "r": r, "mc": mc,
                "lv": lv, "p": parent, "above": above, "n_ma200": len(full),
                "sharpe": sharpe(objs, etf), **({"sn": sub} if sub else {}),
                # 🚨 이 줄의 r 은 **비어 있는 것이 정상이다** — 화면이 market_board.json 에서
                #   옮긴다(위 etf 분기 참조). 표시가 없으면 다음 사람이 "왜 null 이지" 하고
                #   여기서 다시 재려 들고, 그러면 어제 값으로 되돌아간다.
                **({"r_src": "market_board.json"} if etf else {}),
                "_ts": [s["t"] for s in objs], **_val(objs)}

    sectors, rows = [], []

    def _stocks(objs, sec, pid, lv):
        """그 묶음의 종목 줄. **나머지('그 밖')에도 붙인다**(사용자 요청 2026-08-03) —
        나머지라고 못 펼치면 그 종목들은 화면 어디에서도 볼 수 없다.
        lv 는 부모+1 이다: 서브산업 아래는 4단, 섹터 직속 나머지 아래는 3단."""
        for s2 in sorted(objs, key=lambda z: z["t"]):
            rows.append(agg([s2], s2["t"], sec, lv, pid, (s2.get("name") or "")[:22]))

    for sec, objs in bysec.items():
        sectors.append(agg(objs, SEC_KO.get(sec, sec), sec, 1, None, etf=sec))
        gs = sorted([(g, v) for (s2, g), v in keepg.items() if s2 == sec],
                    key=lambda kv: -len(kv[1]))
        gused = set()
        for g, gv in gs:
            gid = sec + "|" + g
            _g = agg(gv, g, sec, 2, sec)                    # 산업그룹(2차)
            # 🚨 그 섹터의 산업그룹이 **하나뿐이고 이름도 섹터와 같으면** 표시하지 않는다
            #   (사용자 결정 2026-08-04). 실측 3섹터가 그렇다 — 에너지/Energy · 소재/Materials
            #   · 유틸리티/Utilities. GICS 가 원래 그렇게 생겼다(그 섹터는 2차가 자기 자신이다).
            #   그 줄을 그리면 같은 이름이 두 번 나오고 층만 하나 늘 뿐 갈리는 것이 없다.
            #   ⚠ 데이터에서 빼지는 않는다 — industry.html 이 이 줄로 서브산업의 부모를 찾는다.
            #     화면 쪽이 이 표를 보고 건너뛴다.
            if len(gs) == 1 and g == ETF_GICS.get(sec):
                _g["solo"] = 1
            rows.append(_g)
            # 같은 줄의 경로.
            # 🚨 solo 줄(섹터와 이름이 같은 것 — Energy·Materials·Utilities)도 **만든다**
            #   (사용자 지적 2026-08-13). 표에서 그 줄을 건너뛰는 이유는 **트리라서**다 —
            #   같은 이름이 부모·자식으로 두 번 나오고 층만 하나 는다. 차트는 트리가 아니라
            #   섹터 판과 산업그룹 판이 따로 있으므로 그 이유가 성립하지 않는다. 빼 두면
            #   산업그룹 판에서 세 섹터가 통째로 사라진다(에너지·소재·유틸리티).
            # ⚠ 같은 이름이지만 **같은 값이 아니다.** 섹터 판은 섹터 ETF(XLE…) 실적이고
            #   이쪽은 랩 종목의 기준일 시총가중이다 — 두 판에 나란히 두면 그 차이가 보인다.
            ind_sec[g] = SEC_KO.get(sec, sec)
            for _k in list(base):
                _p = path_of(gv, _k)
                if _p:
                    ind_paths.setdefault(_k, {})[g] = _p
            gused.update(s["t"] for s in gv)
            # 🚨 2026-08-05 — 서브산업(4차) 단을 없앴다(사용자 결정). 3차에 이어 4차도 안 쓴다.
            #   남는 것은 섹터(1차) → 산업그룹(2차) 두 단이고, 종목은 산업그룹에 바로 매단다.
            #   4차는 127칸 중 3종 이상이 71칸뿐이라 커버가 83% 였다 — 나머지 17%는 '그 밖'
            #   줄로 흘렀고, 그 줄들이 표에서 가장 자주 눈에 걸렸다. 2차는 25칸 중 24칸이
            #   3종 이상이고 커버 100% 다. 층을 하나 줄이면 '그 밖'도 함께 사라진다.
            #   ⚠ keeps/bysub 계산은 남겨 둔다 — 아래 tiers 표가 '왜 3·4차를 안 쓰는지'를
            #     화면에서 수치로 말하는 데 쓴다. 재 놓고 안 내면 모은 적 없는 것과 같다.
            _stocks(gv, sec, gid, 3)
        rest = [s for s in objs if s["t"] not in gused]
        if rest:
            rows.append(agg(rest, NOM, sec, 2, sec))
            _stocks(rest, sec, sec + "|" + NOM, 3)
    return {"sectors": sectors, "rows": rows, "mkt": _val(stocks), "px": PX,
            "tiers": gics_tiers, "ind_paths": ind_paths, "ind_dates": dates,
            "ind_sec": ind_sec}


def _load_px(ts, dates, root):
    """티커 → 일별 종가. **종목당 한 번만** 읽는다(중복 티커가 섞여 들어온다)."""
    PX = {}
    for t in set(ts):
        p = os.path.join(root, "data", "sd", "%s.json" % t)
        if not os.path.exists(p):
            continue
        try:
            px = json.load(io.open(p, encoding="utf-8")).get("pxd") or []
        except Exception:
            continue
        if len(px) == len(dates):
            PX[t] = px
    _guard_fresh(PX, dates)
    return PX


# 최신 거래일 결측이 이 비율을 넘으면 세운다. 2%(518종목이면 10종)로 둔 이유 —
# 신규 편입·상장 직후 종목이 한둘 비는 것은 정상이고, 원천 부분 응답은 수십 종씩 빈다.
# 실측: 2026-08-11 사고가 29종(5.6%), 평시는 0종이다. 그 사이에 선이 있다.
FRESH_MAX = 0.02


def _guard_fresh(PX, dates):
    """🚨 최신 두 거래일의 결측을 세고, 도를 넘으면 **빌드를 세운다**.

    2026-08-12 사고: yfinance 가 08-11 하루를 29종에서 빠뜨렸는데 갱신 잡은 성공으로
    끝났고, 홈 히트맵의 기본 기간이 '1일 등락'이라 그 29칸이 통째로 색을 잃었다.
    화면은 "518종목"이라 적으면서 489칸만 칠했다 — **조용히 틀린 것**이 사고의 본체다.

    ⚠ 왜 여기서 세우는가. 히트맵은 한두 종목이 없어도 나머지가 쓸모 있으니 '값 없음 N종'
      으로 적어 내보내면 된다(write_stocks 참조). 하지만 수십 종이 빈 것은 자료가 아니라
      **수집 실패**다. 그것을 실어 내보내면 화면이 없는 하락을 그리게 된다. 세우는 편이 낫다.
      막혔을 때 할 일은 python build/backfill_px.py — 그 칸만 다시 받아 채운다.
    """
    if len(dates) < 2 or not PX:
        return
    n = len(PX)
    bad = []
    for k in (-1, -2):
        m = sum(1 for a in PX.values() if a[k] is None)
        if m:
            bad.append((dates[k], m))
    if not bad:
        return
    worst = max(m for _, m in bad)
    line = " · ".join("%s %d종(%.1f%%)" % (d, m, m * 100.0 / n) for d, m in bad)
    if worst <= n * FRESH_MAX:
        print("  · 최신 종가 결측 %s — 한도(%.0f%%) 안이라 그대로 간다" % (line, FRESH_MAX * 100))
        return
    raise SystemExit(
        "\n🚨 최신 종가가 무더기로 비었다 — %s (전체 %d종, 한도 %.0f%%)\n"
        "   원천 부분 응답이다. 이대로 구우면 히트맵 1일 등락이 그 수만큼 빈 칸이 된다.\n"
        "   → python build/backfill_px.py    (빈 칸만 다시 받아 채운다)\n"
        "   → 그 뒤 python build/home_summary.py 다시" % (line, n, FRESH_MAX * 100))


def _fpe(stocks):
    """ETF 행에 붙일 **12개월 선행 PER** — 홈 '기간별 수익률' 표의 마지막 열(2026-08-12 요청).

    🚨 **평균이 아니라 조화평균이다.** PER 은 비율이라 그냥 평균 내면 PER 1000 짜리 한 종목이
      바스켓 전체를 끌어올린다(실측: 이 유니버스에 fpe 9605 인 종목이 있다). 옳은 집계는
      Σ시총 ÷ Σ이익 이고, 이익 = 시총 ÷ PER 이므로 **시총가중 조화평균**과 같다. 그렇게 하면
      PER 이 큰 종목은 분모에 거의 기여하지 않아 자연히 영향이 작아진다 — 잘라내지 않아도 된다.

    ⚠ **이 랩이 계산한 값이지 그 ETF 가 발표한 값이 아니다.** 후보는 이 랩의 518종이고,
      XLK 의 실제 편입과 'XLK 로 태그된 우리 종목'은 같지 않다. 화면 각주가 그렇게 적는다.
    ⚠ 후보를 못 만드는 행은 **넣지 않는다**(DIA·IWM·스타일 ETF 8종). 편입 명단이 없어서다.
      0 이나 전체 평균으로 채우면 없는 것을 지어내는 것이다 — 화면은 그 칸을 '—' 로 둔다.
    ⚠ fpe 가 음수·0 인 종목은 뺀다. 적자 예상 기업의 PER 은 뜻이 없다(수를 뒤집으면 오히려
      바스켓 PER 을 낮춰 싸 보이게 만든다). 몇 종을 뺐는지 n/of 로 같이 싣는다.
    """
    def agg(sel, cap_weight=True):
        num = den = 0.0; n = 0
        for s in sel:
            f = s.get("fund") or {}
            v, mc = f.get("fpe"), f.get("mc")
            if not (isinstance(v, (int, float)) and v > 0):
                continue
            w = float(mc) if (cap_weight and isinstance(mc, (int, float)) and mc > 0) else (
                None if cap_weight else 1.0)
            if w is None:
                continue
            num += w; den += w / v; n += 1
        return ({"v": round(num / den, 1), "n": n, "of": len(sel)}
                if (den > 0 and n >= 5) else None)

    out = {}
    ix = lambda k: [s for s in stocks if k in (s.get("idx") or [])]
    # ⚠ 스타일 ETF 는 **한 줄도 안 낸다**(사용자 결정 2026-08-13). 종전에는 RSP 만 값이 있었는데
    #   (동일가중 S&P 500 이라 후보가 SPX 와 같아서 계산이 됐다), 그 묶음의 나머지 여덟은
    #   편입 명단이 없어 비어 있었다. **한 줄만 채워진 열은 그 줄이 특별해 보이게 만든다.**
    #   열 머리글도 '스타일 ETF 는 비운다' 고 적고 있어서 그 문장과도 어긋났다.
    for tk, sel, cw in (("SPY", ix("SPX"), True),      # 시총가중 S&P 500
                        ("QQQ", ix("NDX"), True)):     # 시총가중 나스닥 100
        r = agg(sel, cw)
        if r:
            r["basis"] = ("시총가중" if cw else "동일가중")
            out[tk] = r
    for gics, tk in SEC_ETF.items():
        r = agg([s for s in stocks if (s.get("sector") or "") == gics], True)
        if r:
            r["basis"] = "시총가중"
            out[tk] = r
    return out


_IND_PATHS = [(None, None, None)]   # _segments 가 채우고 write() 가 꺼내 쓴다(경로·날짜·부모섹터)


def _segments(stocks, dates, root):
    """홈이 읽는 섹터·산업 한 덩어리. _industry 에 국면 통계를 얹고 내부 필드를 턴다.

    ⚠ **종목 단(lv 4)은 이 파일에 싣지 않는다.** 417줄을 넣으면 gz 10.4 → 26.4KB 가 되는데
      (실측), 이 파일은 홈이 stocks.json 691KB 를 안 받게 하려고 만든 것이라 그 자체가
      무거워지면 존재 이유가 없어진다. 대부분의 방문자는 3단까지 펼치지도 않는다.
      → data/home_stocks.json 으로 떼어내고 **처음 펼칠 때** 받는다(index.html).
    """
    d = _industry(stocks, dates, root)
    if not d:
        return {}
    PX = d.pop("px")
    # 🚨 산업그룹 경로는 **여기 안 싣는다.** home_reco.json 은 홈이 첫 화면에 받는 파일이고
    #   경로 22줄 × 5구간은 그 파일을 배로 만든다 — 이 파일이 생긴 이유가 그 반대다.
    #   차트가 늦게 받는 별도 파일(data/home_ind_perf.json)로 뺀다.
    _IND_PATHS[0] = (d.pop("ind_paths", None), d.pop("ind_dates", None), d.pop("ind_sec", None))
    # 국면 통계는 섹터·산업 **양쪽**에 붙인다. 표에서 부모 줄에도 툴팁이 뜬다.
    # 국면 통계는 상위 단만 — 종목 한 개의 국면별 월평균은 잡음이고, 417줄에 얹으면
    # 파일이 배로 는다. 표에서도 종목 줄 툴팁에는 안 쓴다.
    _, rgn = _by_regime(d["sectors"] + [x for x in d["rows"] if not x.get("st")], PX, dates, root)
    d["regime_n"] = rgn
    d["stocks_url"] = "home_stocks.json"     # 종목 단은 여기서 온다(지연 로딩)
    return d


def _by_regime(rows, PX, dates, root):
    """국면별 산업 월평균 수익률을 rows 에 얹는다(x["rg"]). → (rows, {국면: 개월수})

    data/regime.json 이 이미 sector_perf(섹터 ETF 8종)를 같은 형태로 들고 있다. 그 아래
    한 단을 같은 방식으로 낸다(사용자 요청 2026-08-03).

    🚨 **이 수치는 예측이 아니다.** 국면 라벨은 그 달이 끝난 뒤에 붙고, 여기서는 같은 달의
      수익률을 그 라벨에 묶는다 — '그 국면이었을 때 이 산업이 어땠나'라는 **기술 통계**이지
      '이 국면이 오면 이 산업을 사라'가 아니다. 국면을 미리 알 수 있다는 가정이 들어가면
      그건 다른 주장이고, 이 랩은 그 주장을 하지 않는다.
    🚨 표본이 얕다. 종목 가격이 2016-08 부터라 120개월뿐이고, 국면마다 5~39개월로 갈린다
      (실측: Goldilocks 39 · Recovery 33 · Overheating 27 · SoftLanding 9 · LateCycle 7 ·
      Recession 5). 개월수를 **반드시 함께 낸다** — 5개월 평균과 39개월 평균을 같은 무게로
      보여 주면 그건 자료가 아니라 착시다. MIN 개월 미만은 아예 비운다.
    ⚠ 생존편향도 그대로 있다. 오늘의 518종을 과거로 소급한다(이 랩의 상시 한계).
    """
    RG_MIN = 8
    p = os.path.join(root, "data", "regime.json")
    if not os.path.exists(p):
        return rows, {}
    try:
        hist = (json.load(io.open(p, encoding="utf-8")) or {}).get("history") or []
    except Exception:
        return rows, {}
    lab = {(x.get("dt") or "")[:7]: x.get("r") for x in hist if x.get("r")}
    # 월말 인덱스 — 그 달의 마지막 거래일. 첫 달은 직전 달이 없어 수익률을 못 만든다.
    me = [i for i in range(len(dates) - 1) if dates[i][:7] != dates[i + 1][:7]] + [len(dates) - 1]
    n_by = {}
    for k in range(1, len(me)):
        r = lab.get(dates[me[k]][:7])
        if r:
            n_by[r] = n_by.get(r, 0) + 1
    for x in rows:
        acc = {}
        for k in range(1, len(me)):
            r = lab.get(dates[me[k]][:7])
            if not r:
                continue
            i0, i1 = me[k - 1], me[k]
            vs = []
            for t in x.get("_ts", []):
                px = PX.get(t)
                if px and px[i0] and px[i1] and px[i0] > 0:
                    vs.append(px[i1] / px[i0] - 1.0)
            if len(vs) >= max(3, len(x.get("_ts", [])) // 2):
                acc.setdefault(r, []).append(sum(vs) / len(vs) * 100)
        x["rg"] = {r: round(sum(v) / len(v), 2) for r, v in acc.items() if len(v) >= RG_MIN}
        x.pop("_ts", None)
    return rows, {r: n for r, n in n_by.items() if n >= RG_MIN}


# 밸류에이션은 **중앙값**이다. 평균을 쓰면 PER 300짜리 한 종목이 산업을 통째로 끈다.
# ⚠ 음수 PER(적자)은 뺀다 — 뜻이 흐려지는 값이라 넣으면 중앙값이 아니라 잡음이 된다.
#   그래서 n_pe(실제로 쓴 종목 수)를 함께 싣는다. 5종 중 2종으로 만든 중앙값과
#   63종으로 만든 중앙값을 화면이 같은 무게로 보여 주면 안 된다.
# ⚠ 상한은 이상치 컷이다(PER 200·PBR 50). 중앙값이라 영향은 작지만, 이익이 0에 가까운
#   회사의 PER 수천은 '자료'가 아니라 분모 사고에 가깝다.
VAL_CAP = {"tpe": 200.0, "pb": 50.0}
VAL_MIN_N = 3


def _val(objs):
    """{pe, pb, n_pe, n_pb} — 종목 묶음의 밸류에이션 중앙값."""
    out = {}
    for key, name in (("tpe", "pe"), ("pb", "pb")):
        vs = sorted(v for v in ((s.get("fund") or {}).get(key) for s in objs)
                    if isinstance(v, (int, float)) and 0 < v < VAL_CAP[key])
        if len(vs) >= VAL_MIN_N:
            m = len(vs) // 2
            out[name] = round(vs[m] if len(vs) % 2 else (vs[m - 1] + vs[m]) / 2, 2)
        else:
            out[name] = None
        out["n_" + name] = len(vs)
    return out


def _idx_counts(stocks, root):
    """{'SPX': n, 'NDX': n, 'both': n, 'all': n}. members.json 의 idx 를 센다.

    ⚠ stocks.json 에도 idx 가 있지만 members.json 이 그 정본이다(refresh_members 가 관문
      넷을 통과해야 쓴다). 같은 수를 두 곳에서 세면 언젠가 갈린다.
    못 읽으면 빈 dict 을 준다 — 눈썹은 그때 종목 수를 아예 안 적는다(틀린 수보다 낫다).
    """
    p = os.path.join(root, "data", "members.json")
    try:
        mem = (json.load(io.open(p, encoding="utf-8")) or {}).get("members") or {}
    except Exception:
        return {}
    if not mem:
        return {}
    spx = sum(1 for v in mem.values() if "SPX" in (v.get("idx") or []))
    ndx = sum(1 for v in mem.values() if "NDX" in (v.get("idx") or []))
    both = sum(1 for v in mem.values() if {"SPX", "NDX"} <= set(v.get("idx") or []))
    return {"SPX": spx, "NDX": ndx, "both": both, "all": len(mem)}


def _breadth(stocks):
    """③ 시장 폭 — 지수가 아니라 '몇 종목이 어느 상태인가'.

    홈에 폭 카드를 세우려면 flags/timing 분포가 필요한데, 그것 때문에 홈이 stocks.json
    raw 691KB(gz 199KB)를 받게 하면 이 파일의 존재 이유가 사라진다. 정수 몇 개만 여기서 세어 싣는다(+0.3KB).
    """
    fl, tm = {}, {}
    for s in stocks:
        for f in (s.get("flags") or []):
            fl[f] = fl.get(f, 0) + 1
        t = s.get("timing")
        if t:
            tm[t] = tm.get(t, 0) + 1
    n = len(stocks)

    # 200일선 위 비율의 분모는 **200일선이 산출되는 종목**이어야 한다.
    # part(부분 편입 — 상장 200거래일 미만, refresh_stocks.py:579)는 200일선이 없어서
    # '200일이탈' 플래그가 붙지 않을 뿐인데, 여집합으로 세면 그대로 '위'로 잡혀 비율이 부푼다.
    # 오늘 기준 4종목(Q·FDXF·HONA·SPCX) 차이지만 신규 상장이 몰리면 커진다.
    full = [s for s in stocks if not s.get("part")]
    below_full = sum(1 for s in full if "200일이탈" in (s.get("flags") or []))
    # ── 섹터별 폭 ── 전체 한 숫자로는 '어디가 강한가'를 못 본다(사용자 요청 2026-08-02
    #   "시장을 좀 더 세분화해서 보고싶어"). 같은 분모 규칙(part 제외)을 섹터 안에서 다시 적용한다.
    # ⚠ 키를 **섹터 ETF 티커**로 둔다. 홈이 market_board.json 의 sector 행과 짝지어 그리는데,
    #   한글 이름으로 키를 잡으면 그쪽 표기가 바뀌는 날 조인이 조용히 끊긴다. 티커는 안 바뀐다.
    #   market.html 도 같은 폭을 stocks.json 에서 직접 세지만(그 화면은 원본을 받는다) 분모
    #   규칙이 같아야 두 화면의 숫자가 일치한다 — 여기서 규칙을 바꾸면 그쪽도 볼 것.
    sec = {}
    for s in full:
        tk = SEC_ETF.get(s.get("sector") or "")
        if not tk:
            continue                              # 미분류는 섹터 카드에 세지 않는다
        d = sec.setdefault(tk, {"n": 0, "above": 0})
        d["n"] += 1
        if "200일이탈" not in (s.get("flags") or []):
            d["above"] += 1
    return {
        "n": n,
        "n_ma200": len(full),                     # 200일선이 산출되는 종목 수(비율의 분모)
        "n_partial": n - len(full),               # 이력이 짧아 판정 불가
        "above200": len(full) - below_full,
        "sector": sec,                            # {섹터ETF: {n, above}} — 홈 폭 카드가 쪼개 그린다
        "flags": dict(sorted(fl.items(), key=lambda kv: -kv[1])),
        "timing": tm,
    }


def build(stocks, dates, as_of, root):
    buy, nb, nb_c, nb_p = _reco(stocks, dates, "bms", "bmw")
    sell, ns, ns_c, ns_p = _reco(stocks, dates, "sms", "smw")
    return {
        "as_of": as_of, "win": WIN,
        "buy": buy, "sell": sell, "nbuy": nb, "nsell": ns,
        "buy_conf": nb_c, "buy_prov": nb_p, "sell_conf": ns_c, "sell_prov": ns_p,
        "breadth": _breadth(stocks),
        # 히어로 눈썹이 쓰는 지수별 종목 수(사용자 요청 2026-08-10 — '518종목 · FRED 39지표'
        # 대신 'S&P 500 몇 · 나스닥 100 몇'). 합집합이 518이고 겹침이 있으므로 둘을 더하면
        # 518이 넘는다 — 화면은 두 수를 나란히 적을 뿐 더하지 않는다.
        # ⚠ 손으로 적지 않는다. 지수 리밸런스가 있는 날 조용히 낡는 종류의 숫자다.
        "idx_n": _idx_counts(stocks, root),
        # 섹터(11)와 종목(518) 사이 — GICS 산업그룹·서브산업. 홈 산업 카드가 읽는다.
        "industry": _segments(stocks, dates, root),
        # 홈 '기간별 수익률' 표의 12개월 선행 PER 열. 후보가 있는 행만 담긴다(_fpe 머리말 참조).
        "fpe": _fpe(stocks),
        "fpe_note": "12개월 선행 PER — 이 랩 518종 중 그 바스켓에 해당하는 종목의 "
                    "**시총가중 조화평균**(Σ시총 ÷ Σ이익)이다. ⚠ 이 랩이 계산한 값이지 그 "
                    "ETF 가 발표한 값이 아니다. 적자 예상(PER ≤ 0) 종목은 뺐다 — 몇 종을 "
                    "썼는지 각 행에 n/of 로 적는다. 편입 명단이 없는 행(DIA·러셀2000·스타일 "
                    "ETF)은 칸을 비운다.",
    }


def write_stocks(doc, root):
    """종목 단(lv 4)을 data/home_stocks.json 으로 떼어내고 본체에서 지운다."""
    iv = doc.get("industry") or {}
    rows = iv.get("rows") or []
    deep = [x for x in rows if x.get("st")]
    iv["rows"] = [x for x in rows if not x.get("st")]
    # 🚨 기간별 결측을 **세어 싣는다**(2026-08-13). 2026-08-11 에 29종의 그날 종가가
    #   빠졌는데 갱신 잡은 성공으로 끝났고, 홈 히트맵은 "518종목"이라 적으면서 489칸만
    #   칠했다 — 빈 칸이 회색이라 '안 움직였다'와 구별되지 않았다.
    #   이 랩의 다른 빌더(market_board)는 결손이면 갱신을 세우는데 여기엔 그 관문이 없었다.
    # ⚠ 여기서 세우지는 않는다. 히트맵은 한 종목이 없어도 나머지 517칸이 쓸모 있고,
    #   세우면 화면 전체가 사라진다. 대신 **수를 실어 화면이 스스로 말하게** 한다.
    hz = [k for k, _ in IND_HOR] + ["YTD"]
    na = {k: sum(1 for x in deep if (x.get("r") or {}).get(k) is None) for k in hz}
    na = {k: v for k, v in na.items() if v}
    if na:
        print("  ⚠ 히트맵 결측 — " + " · ".join("%s %d종" % (k, v) for k, v in na.items())
              + " (홈 부제가 이 수를 적는다)")
    p = os.path.join(root, "data", "home_stocks.json")
    json.dump({"as_of": doc.get("as_of"), "note":
               "섹터·산업 트리의 마지막 단(종목). 홈이 3단을 처음 펼칠 때만 받는다 — "
               "data/home_reco.json 에 넣으면 그 파일이 gz 10 → 26KB 가 된다.",
               # 기간별 '값 없는 종목 수'. 없으면 키가 아예 없다(0 을 싣지 않는다).
               "na": na,
               "na_note": ("그 기간의 수익률을 낼 수 없는 종목 수다. 상장이 늦어 과거가 없는 "
                           "종목과, 그날 원천이 값을 안 준 종목이 섞여 있다 — 화면은 둘을 "
                           "구별하지 않고 '값 없음'으로만 적는다. 0 으로 채우지 않는다."),
               "n_rows": len(deep),
               "rows": deep},
              io.open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    return p, len(deep)


def write(stocks, dates, as_of, root):
    """실패를 삼키지 않는다 — 홈의 핵심 모듈이라 조용히 빈 채로 배포되면 안 된다."""
    doc = build(stocks, dates, as_of, root)
    if not doc["buy"] and not doc["sell"]:
        raise SystemExit("home_reco: 최근 타점이 하나도 없다 — 마커 산출이 깨졌는지 확인")
    sp, n_deep = write_stocks(doc, root)
    # 산업그룹 경로 — 홈 시계열 넷째 판. 차트가 늦게 받는 별도 파일이다.
    _paths, _pdates, _psec = _IND_PATHS[0]
    if _paths and _pdates:
        _out = {"note": "홈 '기간별 수익률' 위 시계열의 산업그룹 판. 🚨 끝점이 아래 표의 그 칸과 "
                        "같도록 **표를 만든 그 함수(agg)와 같은 식**으로 날짜마다 잰다 — "
                        "기준일 시총가중, 가중치는 기준일에 고정. 만든 곳 build/home_summary.py.",
                "sec_note": "sec 는 그 산업그룹의 부모 섹터(한글)다. 화면이 섹터 판과 **같은 색**을 "
                            "쓰려고 읽는다 — 색 자체는 여기서 정하지 않는다(섹터 색이 끝값 순으로 "
                            "돌아가므로 정본이 화면 한 곳에만 있어야 한다).",
                "sec": _psec or {},
                "as_of": doc.get("as_of"), "series": {}}
        for _k, _g in _paths.items():
            _ix = sorted({i for p in _g.values() for i in p["ix"]})
            _pos = {i: j for j, i in enumerate(_ix)}
            _rows = {}
            for _nm, _p in _g.items():
                _a = [None] * len(_ix)
                for _i, _v in zip(_p["ix"], _p["v"]):
                    _a[_pos[_i]] = _v
                _rows[_nm] = _a
            _out["series"][_k] = {"dates": [_pdates[i] for i in _ix], "ind": _rows}
        _ip = os.path.join(root, "data", "home_ind_perf.json")
        json.dump(_out, io.open(_ip, "w", encoding="utf-8"), ensure_ascii=False,
                  separators=(",", ":"))
        print("  → home_ind_perf.json (산업그룹 %d줄 · 구간 %d)"
              % (len(next(iter(_out["series"].values()))["ind"]), len(_out["series"])))
    p = os.path.join(root, "data", "home_reco.json")
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("  → %s (종목 %d줄 · 지연 로딩)" % (os.path.basename(sp), n_deep))
    return p, doc


if __name__ == "__main__":
    R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    d = json.load(io.open(os.path.join(R, "data", "stocks.json"), encoding="utf-8"))
    p, doc = write(d["stocks"], d["pxd_dates"], d["as_of"], R)
    print(f"→ {os.path.basename(p)} ({os.path.getsize(p)//1024 or 1}KB) "
          f"매수 {doc['nbuy']}(확정 {doc['buy_conf']}·잠정 {doc['buy_prov']}) · "
          f"매도 {doc['nsell']}(확정 {doc['sell_conf']}·잠정 {doc['sell_prov']})")
