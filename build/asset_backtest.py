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
#   위험 축(risk_bootstrap·BOOT_*)도 여기서 가져온다 — 처음엔 이 파일에 있었는데
#   ml_backtest 가 못 써서 ML 여섯 줄이 통째로 '판정 불가'였다. 지표는 한 곳에만 둔다.
from tech_backtest import (ann_stats, tstat, maxdd, curve_pack, load_index_tr,  # noqa: E402
                           risk_bootstrap, BOOT_N, BOOT_BLOCK)
import tech_backtest as TB          # noqa: E402  증분 알파 계산기를 다시 구현하지 않는다

_GRID = {}


def dates_for(nav, ds):
    """nav 와 **같은 길이**의 날짜 축. 길이가 어긋나면 날짜 정합 회귀가 통째로 안 돈다.

    nav 는 기준점 100.0 으로 시작해 구간마다 append 하므로 대개 len(ds)+1 이다.
    그 한 칸은 첫 구간의 시작점이므로 앞을 한 번 더 쓴다.
    """
    ds = list(ds)
    if not ds:
        return []
    if len(ds) == len(nav):
        return ds
    if len(ds) == len(nav) - 1:
        return [ds[0]] + ds
    return ds[:len(nav)] if len(ds) > len(nav) else ds + [ds[-1]] * (len(nav) - len(ds))


def gthin(ds, nav, bnav, every=5):
    """전략마다 다른 `step` 으로 얇게 만들면 **날짜 격자가 서로 안 맞는다.**

    🚨 2026-08-05 실측: 그래서 이 랩의 incr5 가 전부 None 이었다. incr_multi 는 6계열의
      **공통 날짜**에서만 회귀하는데, 전략마다 시작일이 달라 step 이 다르고(len//220)
      그 결과 교집합이 사실상 비었다. 종목 랩은 전 규칙이 같은 격자라 이 문제가 없었다.
    → 절대 위치로 자른다. 어느 전략이든 '전체 격자의 every 번째 날'만 남기므로 서로의
      부분집합이 되고, 교집합이 짧은 쪽 길이만큼 남는다.
    """
    ds = dates_for(nav, ds)
    keep = [i for i, d in enumerate(ds) if _GRID.get(d, i) % every == 0]
    if len(keep) < 60:                      # 너무 짧아지면 그대로 둔다(회귀가 아예 안 도는 것보다 낫다)
        keep = list(range(len(ds)))
    return ([ds[i] for i in keep],
            [round(nav[i], 2) for i in keep],
            [round(bnav[i], 2) for i in keep])


def attach_incr(rows, label):
    """랩 안에서 서로 얼마나 겹치는지 잰다 — **재기만 한다.**

    ⚠ 2026-08-17 로 강등 기능과 tcrit 인자를 걷었다(문턱 제거). 이름은 그대로 두었다 —
      산출물의 incr·incr5 필드와 짝이라 바꾸면 읽는 쪽이 갈린다.

    🚨 2026-08-05. 이 검정은 종목 랩에만 있었다. 그래서 ML 계열 5종이 서로 초과수익 상관
      0.86~0.93 인 채로 '통과 후보' 배지를 다섯 개 달고 있었다 — 한 규칙이 다섯 번 실린 것을
      다섯 개의 독립 검증으로 세면서 본페로니 분모까지 그만큼 올린 셈이다.
      계산기는 tech_backtest 의 모듈 함수를 그대로 쓴다(다시 구현하지 않는다 — 두 벌을 두면
      한쪽만 고쳐진다는 것이 오늘의 교훈이다).
    ⚠ 이웃은 **같은 랩 안에서만** 고른다. 자산배분 규칙을 종목선택 규칙으로 통제하는 것은
      '이미 들고 있는 사람에게 새로 주는 것이 있느냐'라는 이 검정의 질문과 맞지 않는다.
    ⚠ 강등만 한다. 넘었다고 등급을 올리지 않는다.
    """
    ok = [r for r in rows if r.get("dates") and r.get("nav") and r.get("bnav")]
    for r in ok:
        nb = []
        for o in ok:
            if o is r:
                continue
            c = TB.corr_of(*TB.paired_excess(r, o))
            if c is not None:
                nb.append((abs(c), c, o["name"], o))
        if not nb:
            continue
        nb.sort(key=lambda z: -z[0])
        a, b = TB.paired_excess(r, nb[0][3])
        inc = TB.incr1(a, b)
        if inc:
            r["incr"] = {"vs": nb[0][2], "corr": round(nb[0][1], 3),
                         "alpha": inc["alpha"], "t": inc["t"], "beta": inc["beta"]}
        if len(nb) >= 5:
            m5 = TB.incr_multi(r, [z[3] for z in nb[:5]])
            if m5:
                r["incr5"] = dict(m5, vs=[z[2] for z in nb[:5]])
    # 🚨 2026-08-17 — 여기 있던 **증분알파 게이트를 걷었다**(사용자 지시 "문턱 다 없애").
    #   그 게이트는 |incr5.t| < 2.0 인 규칙을 '통과 후보' 에서 '구별 불가' 로 강등했다.
    #   ⚠ 실은 이미 **한 번도 발화하지 않는 상태**였다. 첫 줄이
    #     `if r.get("verdict") != "통과 후보": continue` 인데, 관문을 걷은 뒤로 이 랩의
    #     71종이 전부 '측정만' 이라 조건에 걸리는 행이 0 이다. 죽은 코드가 살아 있는
    #     문턱처럼 보였다 — 읽는 사람에게는 «이 랩은 t 2.0 으로 거른다» 로 읽힌다.
    #   incr5 **측정은 그대로 둔다.** 없앤 것은 그 수로 등급을 매기던 자리뿐이고,
    #   값은 위에서 r["incr5"] 로 실려 화면과 산출물에 그대로 간다.
    # incr5 를 못 잰 규칙을 로그에 남긴다. 게이트는 없어졌지만 **못 잰 것과 잰 것을
    # 구별해 적는 일은 남는다** — 값이 없는 칸이 «작다» 로 읽히면 안 된다.
    _blind = [r["name"] for r in rows if (r.get("incr5") or {}).get("t") is None]
    if _blind:
        print("  [%s 증분알파] incr5 미산출 %d종: %s" % (label, len(_blind), " · ".join(_blind[:6])))


# ── 거래비용 ────────────────────────────────────────────────────────────
# 왜 넣나. 이 표는 지금까지 전부 무비용(gross)이었다. 그런데 회전이 0인 상시보유와 연 50회
# 갈아타는 달력 규칙을 같은 줄에 놓고 견주면 비교 자체가 기울어 있다 — 후자만 실제로는
# 없는 돈을 벌고 있는 셈이다. 전량교체 한 번당 왕복 5bp 를 떼고 다시 잰다.
#   5bp 근거 — 이 파일의 매매 대상은 전부 대형 ETF(SPY·SHY·TLT·GLD…)다. 호가 스프레드가
#   1~2bp 수준이고 여기에 체결 충격을 얹은 값이다. 개별주 10종목 포트라면 더 물어야 하므로
#   이 수치를 종목 전략에 그대로 옮기면 안 된다.
#   ⚠ 무비용 숫자를 없애지 않는다. 판정(verdict)은 기존대로 gross 로 두고 비용 후는 **따로**
#     싣는다 — 비용 가정 하나로 과거 판정이 통째로 흔들리면 그것대로 못 믿을 표가 된다.
COST_RT = 0.0005


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "asset_strategies.json")

A = None          # 자산 패널
DTS = []          # 날짜
RF = {}

# 🚨 백테스트 길이 상한 — 사용자 결정 2026-08-13. tech_backtest.py 의 MAX_YEARS 와 같은 값이다.
#   "전략은 최근일자부터 최대 10년. 어떤건 14.4년, 16.6년 등 더 길게 비교한 것도 있더라."
#   실측으로 이 파일의 62종은 창이 7.2~20.5년으로 흩어져 있었다 — 창이 다르면 전략끼리
#   비교가 성립하지 않는다. 종목 랩만 자르고 여기를 두면 한 화면에서 10년짜리와 20년짜리가
#   같은 표에 놓인다.
#   ⚠ 이 상한은 **성과 측정 구간**만 자른다. 신호 계산은 그 앞의 가격을 그대로 쓴다.
#   ⚠ 두 파일이 같은 값을 따로 들고 있다. 한쪽만 고치면 조용히 갈리므로, 바꿀 때는 둘 다.
MAX_YEARS = 10


# 성과를 재는 마지막 위치(전월말). main() 이 채우고 cap_start·지표 자르기가 읽는다.
# 🚨 2026-08-23 사용자 결정 — 곡선·구간수익은 오늘까지, 지표는 전월말. 종목 랩
#   (tech_backtest.ASOF_N)과 **같은 설계**다. 두 랩이 같은 표로 들어가므로 여기만
#   다르게 두면 한 열에 기준일 둘이 섞인다.
ASOF_N = [None]


def _mcut(dd):
    """지표용 길이 — dd 중 전월말 이하인 칸 수. 절단할 것이 없으면 전체 길이."""
    import tech_backtest as _TB
    return _TB.mcut(dd)


def cap_start(st):
    """측정 시작점에 10년 상한을 건다. 자산이 늦게 생긴 전략은 원래 시작점을 그대로 쓴다.

    ⚠ 상한을 **절단점(전월말)** 에서 센다. len(DTS)(오늘)로 세면 격자가 하루 길어질 때마다
      시작일이 하루씩 밀려 지표가 매일 바뀐다 — 고정하려던 것이 도로 풀린다.
    """
    return max(st, (ASOF_N[0] or len(DTS)) - int(MAX_YEARS * 252))

# 🚨 지수 대조군은 **가격지수(PR)** 로 통일한다 — 2026-08-13 사용자 결정.
#   종전에는 이 랩만 SPY(배당 재투자 = 사실상 TR)를 썼고 종목 랩 98종은 ^GSPC(PR)를 써서,
#   한 화면에서 "S&P 500(PR)" 옆에 "SPY 상시보유"가 나란히 놓였다. 표기가 갈리면 세로로
#   못 읽는다는 것이 사용자 지적이다.
#   ⚠ **이 통일에는 값이 붙는다.** 전략 수익은 전부 TR(조정종가)인데 대조군만 PR이 되므로
#     대조군이 배당만큼 불리해진다 — 실측 연 2.00%p(2006~2026: SPY 11.19% vs ^GSPC 9.19%).
#     이 랩 35종 중 13종이 CAGR 열세에서 우위로 뒤집힌다. 전략이 좋아진 것이 아니라
#     대조군이 배당을 잃은 것이다. 화면(explorer)이 그 사실을 카드마다 적어야 한다.
#   ⚠ ^GSPC 는 **살 수 없는 계열**이다. 살 수 있는 것과 겨루던 것을 못 사는 것과 겨루게 됐다.
#   ⚠ 지수형 대조군만 바꾼다. 포트폴리오 대조군(60/40·9자산 동일가중)과 원계열 대조군
#     ('타이밍 없는 원계열'·'종가→종가')은 그대로다 — 그것들은 PR/TR 표기가 없고,
#     같은 것을 다르게 굴린 비교라 지수로 바꾸면 비교 자체가 성립하지 않는다.
IDX_LAB = {"^GSPC": "S&P 500(PR)", "^NDX": "NASDAQ 100(PR)"}


def blabel(fn, i0, i1):
    """대조군 가중치 함수 → 화면에 적을 이름. 대조군은 결국 '무엇을 얼마나 드나'가 전부라
    35개 호출부에 이름을 하나씩 붙이는 대신 가중치에서 뽑는다.
    시작과 끝의 구성이 다르면 정적 이름이 거짓이 되므로 '동적'이라고 적는다."""
    try:
        w0, w1 = fn(i0) or {}, fn(i1) or {}
    except Exception:
        return None
    if not w0:
        return None
    if set(w0) != set(w1) or any(abs(w0[k] - w1.get(k, 0)) > 1e-9 for k in w0):
        return "동적 배분(%d자산)" % len(set(w0) | set(w1))
    tot = sum(w0.values()) or 1.0
    parts = sorted(((k, 100 * v / tot) for k, v in w0.items()), key=lambda z: -z[1])
    if len(parts) == 1:
        t0 = parts[0][0]
        # 지수는 종목 랩 98종과 **글자까지 같은** 이름을 쓴다("S&P 500(PR) 매수후보유").
        # 한 글자만 달라도 화면에서 다른 대조군으로 읽힌다.
        return (IDX_LAB[t0] + " 매수후보유") if t0 in IDX_LAB else ("%s 상시보유" % t0)
    if len(parts) <= 4:
        return " · ".join("%s %d%%" % (k, round(p)) for k, p in parts)
    return "%d자산 동일가중" % len(parts)


# 🚨 판정 대조군은 **예외 없이 지수(PR)** 다 — 2026-08-13 사용자 결정(2차).
#   1차에서는 지수형 대조군만 PR 로 바꾸고 포트폴리오 대조군(9자산 동일가중 …)은 그대로 뒀는데,
#   그러면 전략 랩 한 화면에 "S&P 500(PR)" 과 "9자산 동일가중" 이 섞여 세로로 못 읽는다.
#   → 판정선은 전부 지수로 올리고, **원래 대조군은 보조로 내린다**(버리지 않는다).
#   ⚠ 그냥 갈아 끼우면 안 되는 이유가 여기 있다. '크로스에셋 RP vs 9자산 동일가중'은
#     "같은 자산을 굴린 것이 그냥 든 것보다 나은가"를 묻는데, 지수로 바꾸면 그 질문이
#     통째로 사라지고 "분산 포트폴리오가 미국 주식보다 나은가"라는 다른 질문이 된다.
#     둘 다 잴 자리가 있으므로(bench2) 둘 다 잰다. 판정은 위, 원래 질문은 아래.
#   ⚠ 위험감축형이 지수와 CAGR·샤프로 겨루면 지는 것이 정상이다 — strategy_index 의
#     cmp_note 가 그 사실을 화면에 적는다. 판정이 나빠지는 것과 전략이 나빠지는 것은 다르다.
def _bench_idx(i):
    return {"^GSPC": 1.0}


def _is_idx(fn, i0):
    """이미 지수 하나만 드는 대조군인가 — 그러면 내릴 것이 없다."""
    try:
        return set((fn(i0) or {})) <= set(IDX_LAB)
    except Exception:
        return False


def idx_monthly(tk, months):
    """'YYYY-MM' 격자에서 지수 **월간 수익** 목록. 못 만들면 None.

    슬리브 결합 랩(월간 계열)에도 같은 판정선을 주려고 둔다.
    🚨 첫 달의 기준은 **그 전달 말**이다. 여기서 0 을 채우면 지수만 한 달치 수익을 잃어
      대조군이 그만큼 낮게 잡힌다 — 판정선을 몰래 낮추는 짓이라 그럴 바엔 안 만든다.
    """
    last = {}
    for i, d in enumerate(DTS):
        last[d[:7]] = i
    keys = sorted(last)
    m0 = months[0]
    before = [k for k in keys if k < m0]
    if not before:
        return None                      # 전달 말이 없으면 첫 달 수익을 정직하게 못 만든다
    s = ser(tk)
    if not s:
        return None
    idx = [last[before[-1]]] + [last.get(m) for m in months]
    if any(i is None or s[i] is None for i in idx):
        return None
    return [s[idx[i]] / s[idx[i - 1]] - 1 for i in range(1, len(idx))]


def idx_leg(tk, st, n):
    """지수 매수후보유를 **일간 격자 그대로** 굴린다 → (nav, rets).

    run_weights 를 안 쓰고 손으로 짠 랩(오버나이트 2종)에도 같은 판정선을 주려고 둔다.
    ⚠ 그 랩들은 일 왕복이라 월말 주기가 성립하지 않는다 — 대조군도 일간이어야 짝이 맞는다.
    """
    s = ser(tk)
    nav, rets = [100.0], []
    for i in range(st + 1, n):
        r = (s[i] / s[i - 1] - 1) if (s[i] is not None and s[i - 1]) else 0.0
        rets.append(r)
        nav.append(nav[-1] * (1 + r))
    return nav, rets


# ── 도우미 ──────────────────────────────────────────────────────────────
def ser(t):
    return A["px"].get(t)


_TRUE_PX = {}


def ser_true(t):
    """배당 **재투자 조정 전**의 실제 주가 계열을 되돌린다.

    🚨 2026-08-04 버그 수정. `A["px"]` 는 `auto_adjust=True` 로 받은 배당조정가다. 과거로
      갈수록 실제 주가보다 낮으므로, **실제 분배금 ÷ 조정가** 는 분배수익률이 아니라 과거일수록
      부푼 값이다. 부푸는 배수가 자산마다 다르다는 것이 더 나쁘다(고배당일수록 크다) —
      실측 첫날 기준 배수: HYG 3.31 · EMB 2.46 · VNQ 2.35 · LQD 2.27 · TLT 1.92 … SPY 1.46.
      그래서 크로스에셋 캐리의 횡단면 순위가 캐리가 아니라 '누적 배당조정 배수'로도 만들어졌다.
      실측: 코드가 계산하던 HYG 12개월 분배수익률이 2008-06 24.31% · 2010-06 23.46% 였다
      (실제는 8% 안팎).

    되돌리는 식. adj[i] = true[i] × Π_{k>i} (1 − d_k / true[k−1]) 이므로 f[i] = adj[i]/true[i]
    를 뒤에서부터 세운다(마지막 날은 adj == true 라 f = 1):
        f[i] = f[i+1] / (1 + f[i+1] · d_{i+1} / adj[i])
    """
    if t in _TRUE_PX:
        return _TRUE_PX[t]
    s = A["px"].get(t)
    if not s:
        _TRUE_PX[t] = None
        return None
    d = (A.get("div") or {}).get(t) or {}
    n = len(s)
    out = [None] * n
    f = 1.0
    for i in range(n - 1, -1, -1):
        if s[i]:
            out[i] = s[i] / f
        if i > 0 and s[i - 1]:
            dv = d.get(DTS[i]) or 0.0        # i일이 배당락일이면 그 금액
            f = f / (1.0 + f * dv / s[i - 1]) if dv else f
    _TRUE_PX[t] = out
    return out


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


def _eom(k):
    """'YYYY-MM-01' → 그 달의 말일(date)."""
    y, mo = int(k[:4]), int(k[5:7])
    return dt.date(y + (mo == 12), (mo % 12) + 1, 1) - dt.timedelta(days=1)


def macro_asof_m(sid, d, lag_days, n=1):
    """월간 거시 계열 — **발표 시차를 반영한** 최신 n개(오래된→최신). 모자라면 [].

    ⚠ FRED 월간 계열의 키는 **관측월 1일**이다(UNRATE['2026-06-01'] = 6월 실업률).
      실제 발표는 그 달이 끝난 뒤다 — 6월치는 7월 초에 나온다. macro_asof 를 그대로 쓰면
      6월 30일에 6월 실업률을 아는 셈이 되어, 그날 세상에 없던 정보로 매매하게 된다.
      일간 계열(T10Y2Y·VIXCLS 등)은 키가 곧 관측일이라 이 문제가 없다 — 월간만 이 함수를 쓴다.
    """
    m = A["macro"].get(sid) or {}
    out = []
    for k in sorted(m):
        if (_eom(k) + dt.timedelta(days=lag_days)).isoformat() <= d:
            out.append(m[k])
        else:
            break
    return out[-n:] if len(out) >= n else []


def sma(s, i, n):
    """s[i] 까지의 n일 단순이동평균. 결측이 20%를 넘으면 None."""
    if s is None or i < n:
        return None
    v = [s[j] for j in range(i - n + 1, i + 1) if s[j] is not None]
    return sum(v) / len(v) if len(v) >= n * 0.8 else None


def pct1(w):
    """{티커: 비중} → [(티커, %)…] 내림차순. **소수 1자리이고 합이 정확히 100.0** 이다.

    🚨 2026-08-10. 종전에는 항목마다 따로 round(100*v/tot, 1) 했다. 반올림이 각자 놀아서
      50전략 중 7개의 합이 99.9 또는 100.1 로 나왔다(a7-fidelity·bond-trend·tsmom-multi·
      a7b-gate-sector·a7-conover·rp-extended·rp-voltarget). 화면은 이 값을 그대로 1자리로
      그리므로, 더해 보는 사람에게는 비중이 100이 아닌 포트폴리오로 보인다.

    최대잔여법(largest remainder) — 0.1%p 단위로 내림한 뒤 남은 몫을 **잘린 소수가 큰
      순서로** 하나씩 나눠 준다. 어느 항목도 0.1%p 넘게 움직이지 않으면서 합이 맞는다.
      ⚠ 비율을 다시 계산하는 것이 아니라 **표시 단위에 맞춰 배분**하는 것이다.
      동점이면 비중이 큰 쪽, 그다음 티커 순으로 가른다 — 안 그러면 같은 입력이 실행마다
      다른 표를 낸다(이 저장소가 동점 정렬로 여러 번 데었다).
    ⚠ 0 이하는 담지 않는다. 그래서 분모도 **담기는 것들의 합**이어야 한다 — 전체 합으로
      나누면 담긴 것들끼리는 100 이 안 된다.
    """
    pos = {k: float(v) for k, v in (w or {}).items() if v and v > 0}
    tot = sum(pos.values())
    if tot <= 0:
        return []
    tenths = {k: (1000.0 * v / tot) for k, v in pos.items()}      # 0.1%p 단위
    base = {k: int(x) for k, x in tenths.items()}                 # 내림
    rest = 1000 - sum(base.values())
    order = sorted(pos, key=lambda k: (-(tenths[k] - base[k]), -pos[k], k))
    for k in order[:max(0, rest)]:
        base[k] += 1
    return sorted(((k, round(base[k] / 10.0, 1)) for k in base), key=lambda z: (-z[1], z[0]))


# 🚨 2026-08-17 — BONFERRONI · T_CRIT_PLAIN · AX_T 를 지웠다. 셋 다 **정의만 있고 쓰는
#   자리가 없었다**(AX_T 는 2026-08-13 에 축 문턱이 t 에서 크기로 바뀌며 쓸모를 잃었다).
#   남겨 두면 이 파일을 읽는 사람이 «이 랩은 t 2.0 으로 거른다» 로 읽는다 — 실제로 오늘
#   내가 그렇게 잘못 읽고 사용자에게 «71종 판정이 바뀐다» 고 보고했다. 죽은 상수가 산
#   문턱처럼 보이는 것이 그 자체로 결함이다.
# ⚠ 축 판정(알파 %p · 하락포착 · 12개월 승률 · 침체 낙차)은 **t 가 아니라 크기**로 가른다.
#   그건 유의성 선이 아니라 경제적 크기라 이번 «t 문턱 걷기» 의 대상이 아니다.


# ── 판정 축 ────────────────────────────────────────────────────────────
# 🚨 2026-08-12 사용자 지시 "판정 푹 늘려". 종전 자산 랩의 판정은 **t 하나**였다 —
#   '대조군보다 더 벌었나'만 묻는다. 그런데 이 랩의 배포 3종은 t 로 통과한 적이 없다
#   (Multi-Sleeve Core 의 ΔSharpe p=0.22 · 배포 근거는 CAPM 알파와 낙폭 −18.5 vs −32.6).
#   즉 **이 랩 자신이 배포를 결정할 때 쓴 잣대가 판정표에는 없었다.** 그것을 세운다.
# ⚠ 축을 늘리는 것은 문턱을 낮추는 것과 다르다. 각 축은 자기 질문에만 답하고 서로 덮어쓰지
#   않는다. 한 축이 통과해도 다른 축의 실패가 지워지지 않는다.
def _ols_alpha(rets, brets):
    """CAPM 알파(연율 %)와 t. 무위험 대비가 아니라 **대조군 대비** 회귀다 —
    이 랩의 대조군이 무위험이 아니라 포트폴리오이기 때문이다."""
    n = min(len(rets), len(brets))
    if n < 250:
        return None
    x, y = brets[:n], rets[:n]
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((v - mx) * (v - mx) for v in x)
    if sxx <= 0:
        return None
    beta = sum((v - mx) * (w - my) for v, w in zip(x, y)) / sxx
    a = my - beta * mx
    resid = [y[i] - a - beta * x[i] for i in range(n)]
    s2 = sum(v * v for v in resid) / max(1, n - 2)
    se = math.sqrt(s2 * (1.0 / n + mx * mx / sxx))
    return {"alpha": round(a * 252 * 100, 2), "beta": round(beta, 3),
            "t": round(a / se, 2) if se > 0 else None}


def _capture(rets, brets):
    """상승·하락 포착률 — 대조군이 오른 날/내린 날에 전략이 그 몇 배를 따라갔나."""
    n = min(len(rets), len(brets))
    up_s = up_b = dn_s = dn_b = 0.0
    nu = nd = 0
    for i in range(n):
        if brets[i] > 0:
            up_s += rets[i]
            up_b += brets[i]
            nu += 1
        elif brets[i] < 0:
            dn_s += rets[i]
            dn_b += brets[i]
            nd += 1
    if nu < 60 or nd < 60 or up_b == 0 or dn_b == 0:
        return None
    return {"up": round(up_s / up_b, 3), "down": round(dn_s / dn_b, 3),
            "n_up": nu, "n_dn": nd}


def _roll12(nav, bnav):
    """12개월(252거래일) 롤링 초과 승률과 최악 12개월 — 꾸준함 축."""
    n = min(len(nav), len(bnav))
    if n < 252 * 2:
        return None
    win = tot = 0
    wv = None
    for i in range(252, n):
        a = nav[i] / nav[i - 252] - 1
        b = bnav[i] / bnav[i - 252] - 1
        if a > b:
            win += 1
        if wv is None or a < wv:
            wv = a
        tot += 1
    return {"win12": round(100.0 * win / max(1, tot), 1),
            "worst12": round((wv or 0) * 100, 2), "n": tot}


def _regime_split(rets, brets, dates):
    """침체(NBER USREC=1) 구간과 그 밖을 갈라 잰다.

    ⚠ USREC 은 **사후 확정치**다(NBER 이 나중에 선언한다). 이 축은 '그때 알 수 있었나'가
      아니라 '지나고 보니 침체에 어땠나'만 말한다 — 매매 규칙으로 쓰면 안 되고 규칙의
      성격을 읽는 용도다. 화면에도 그렇게 적는다.
    """
    m = (A.get("macro") or {}).get("USREC") or {}
    if not m:
        return None
    ks = sorted(m)
    pos, out = 0, {}
    lab = []
    for d in dates:
        while pos + 1 < len(ks) and ks[pos + 1] <= d:
            pos += 1
        v = m[ks[pos]] if ks and ks[pos] <= d else None
        lab.append(None if v is None else int(v))
    for key, want in (("rec", 1), ("exp", 0)):
        s = b = 0.0
        c = 0
        for i in range(min(len(rets), len(lab))):
            if lab[i] == want:
                s += rets[i]
                b += brets[i]
                c += 1
        if c >= 120:
            out[key] = {"s": round(s * 252 / c * 100, 2),
                        "b": round(b * 252 / c * 100, 2), "n": c}
    return out or None


def axes_pack(rets, brets, nav, bnav, dates):
    """네 축을 한 번에. 각 축은 수치와 **자기 판정**을 함께 낸다."""
    out = {}
    al = _ols_alpha(rets, brets)
    if al:
        # 🚨 2026-08-13 — 여기 있던 t 문턱(AX_T=2.0)을 없앴다(사용자 지시 "t 문턱 다 없애").
        #   나머지 세 축은 원래 **크기**로 가른다(하락포착 0.90/1.10 · 승률 60/40 · 침체 ±5%p).
        #   알파 축만 t 로 갈라 축 넷이 서로 다른 규율을 쓰고 있었다. 크기 규율로 통일한다.
        #
        # 🚨 **배당을 먼저 뺀 뒤에 가른다.** 대조군이 배당 없는 PR 지수라 알파에 연 2.0%p 가
        #   공짜로 얹혀 있다(strategy_index.PR_TR_GAP · 실측 SPY 11.19 vs ^GSPC 9.19).
        #   그것을 안 빼고 문턱만 2.0%p 로 두면 **배당만 받아도 통과한다** — 실측으로
        #   66종 중 48종(73%)이 '알파 확인'이 됐다. 걸러내려던 것을 못 거르는 문턱이다.
        #   빼고 나면 30 · 6 · 30 이고, 이는 옛 t 문턱(35종)과 같은 자리다.
        # ⚠ 화면에는 **원값 alpha 를 그대로 보여준다**(회귀가 낸 값이다). 판정에 쓴 보정값은
        #   alpha_adj 로 따로 실어, 화면이 둘을 나란히 적을 수 있게 한다.
        PR_GAP = 2.0
        av = al.get("alpha")
        aj = None if av is None else round(av - PR_GAP, 2)
        out["alpha"] = dict(al, alpha_adj=aj, pr_gap=PR_GAP,
                            v=("알파 확인" if (aj is not None and aj >= 2.0) else
                               ("음의 알파" if (aj is not None and aj <= -2.0) else "구별 불가")))
    cp = _capture(rets, brets)
    if cp:
        # 하락 포착이 1보다 작을수록 덜 따라 내려갔다는 뜻이다.
        out["capture"] = dict(cp, v=("하락 방어" if cp["down"] < 0.90 else
                                     ("하락 증폭" if cp["down"] > 1.10 else "구별 불가")))
    rl = _roll12(nav, bnav)
    if rl:
        out["roll"] = dict(rl, v=("꾸준함 확인" if rl["win12"] >= 60 else
                                  ("꾸준히 뒤짐" if rl["win12"] <= 40 else "구별 불가")))
    rg = _regime_split(rets, brets, dates)
    if rg and "rec" in rg:
        d = rg["rec"]["s"] - rg["rec"]["b"]
        out["regime"] = dict(rg, d_rec=round(d, 2),
                             v=("침체에 강함" if d > 5 else
                                ("침체에 약함" if d < -5 else "구별 불가")))
    return out or None


def run_weights(wfn, start, label, bench_w, rule, why, note=None,
                cadence="month", bench_cadence=None, bench2_w=None, bench2_label=None):
    """wfn(i) -> {티커: 비중}. 정해진 주기에만 호출하고 그 사이는 보유.
    ⚠ bench_cadence를 안 주면 대조군도 같은 주기를 쓴다. '주기 변형' 전략에서 이걸 빠뜨리면
      전략과 대조군이 **완전히 같은 계열**이 되어 t가 정의되지 않는다(실제로 그렇게 났다)."""
    n = len(DTS)
    # 🚨 10년 상한을 **여기 한 곳**에서 건다(MAX_YEARS 주석 참조). 일간 전략 50종이 전부
    #   이 함수를 지나므로, 호출부 50곳에 흩어 놓지 않는다 — 흩으면 반드시 빠뜨린다.
    #   ⚠ start 는 이 아래에서 대조군 라벨·회귀 구간에도 쓰이므로 맨 앞에서 덮어야 한다.
    start = cap_start(start)
    # 🚨 판정선을 지수로 끌어올리고 원래 대조군을 보조로 내린다(_bench_idx 위 주석 참조).
    #   보조 자리가 이미 차 있으면(60/40 을 병기한 TAA 10종) 그쪽이 이미 지수 판정이라
    #   여기 걸리지 않는다 — 걸리면 그때는 보조를 덮어쓰지 않고 그대로 둔다.
    if not _is_idx(bench_w, start):
        if bench2_w is None:
            bench2_w, bench2_label = bench_w, blabel(bench_w, start, n - 1)
        bench_w = _bench_idx
    def _ends(c):
        if c == "month":
            return set(month_ends(start, n))
        if c == "quarter":
            return {i for i in month_ends(start, n) if DTS[i][5:7] in ("03", "06", "09", "12")}
        return set(range(start, n))
    ends = _ends(cadence)
    bends = _ends(bench_cadence or cadence)
    def walk(fn, ends, cost=0.0):
        """cost 는 **전량교체 한 번당** 떼는 비율(왕복). 그날 갈아탄 만큼만 비례해 뗀다.

        연간 합계로 빼지 않고 매매가 일어난 날의 수익에서 바로 빼는 이유는, 그래야 복리와
        낙폭에도 비용이 반영되기 때문이다. 연말에 한 번 빼면 MDD 는 무비용 그대로 남는다.
        """
        hold, nav, rets, turn = {}, [100.0], [], 0.0
        for i in range(start + 1, n):
            tc = 0.0
            if (i - 1) in ends or not hold:
                w = fn(i - 1) or {}
                tot = sum(w.values())
                if tot > 0:
                    w = {k: v / tot for k, v in w.items() if v > 0}
                    d = sum(abs(w.get(k, 0) - hold.get(k, 0)) for k in set(w) | set(hold))
                    turn += d
                    tc = d / 2 * cost        # d=2 가 전량교체 한 번 → 왕복비용 한 번
                    hold = w
            r = 0.0
            for t, wt in hold.items():
                s = ser(t)
                if s and s[i] is not None and s[i - 1]:
                    r += wt * (s[i] / s[i - 1] - 1)
            r -= tc
            rets.append(r)
            nav.append(nav[-1] * (1 + r))
        return nav, rets, turn
    nav, rets, turn = walk(wfn, ends)
    bnav, brets, _ = walk(bench_w, bends)
    # 비용 후 — 같은 규칙을 왕복 COST_RT 로 다시 걸어 본다. 대조군도 같은 비용을 문다
    # (상시보유는 회전이 0에 가까워 거의 안 물지만, 규칙을 한쪽에만 적용하면 그것 자체가 편향이다).
    nav_c, rets_c, _ = walk(wfn, ends, COST_RT)
    bnav_c, brets_c, _ = walk(bench_w, bends, COST_RT)
    # 🚨 보조 대조군(2026-08-12 사용자 결정). 주대조군 하나로는 어느 쪽으로 두든 한쪽이
    #   유리하다 — 채권으로 빠지는 규칙을 SPY 와 겨루면 '주식이 더 올랐다'를 재고, 60/40 과
    #   겨루면 문턱이 연 3.3%p 낮다(실측 SPY 11.19% vs 60/40 7.93%, 2006~2026).
    #   그래서 **둘 다 재서 나란히 둔다.** 판정은 주대조군으로 하고 보조는 진단으로 적는다.
    b2 = None
    if bench2_w is not None:
        b2nav, b2rets, _ = walk(bench2_w, _ends(bench_cadence or cadence))
        # ⚠ 보조 대조군도 **같은 창**에서 잰다 — 여기만 오늘까지 두면 Δ샤프가 «다른 기간
        #   둘의 차» 가 된다. 아래 _mc 는 이 블록보다 뒤에서 정의되므로 여기서 다시 잡는다.
        _b2d = DTS[start:]
        _b2c = _mcut(_b2d)
        m2 = ann_stats(b2nav[:_b2c], _b2d[:_b2c], RF)
        b2 = {"label": bench2_label or "보조 대조군",
              "metrics": m2,
              "d_sharpe": round((ann_stats(nav[:_b2c], _b2d[:_b2c], RF).get("sharpe") or 0)
                                - (m2.get("sharpe") or 0), 3),
              "t": tstat(rets[:max(0, _b2c - 1)], b2rets[:max(0, _b2c - 1)])}

    # 이름 짓기는 module-level blabel() 하나로 통일했다 — 여기 사본이 따로 있던 동안
    # 보조 대조군은 이름을 못 얻어 "보조 대조군"이라는 빈 말로 나갔다.
    bench_label = blabel(bench_w, start, n - 1)

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
                    "weights": pct1(_w)} if _tot > 0 else None
    except Exception:
        hold_now = None
    dd = DTS[start:]
    # ── 지표는 전월말까지만 ────────────────────────────────────────────────
    # 🚨 곡선(chart·dates·nav)은 오늘까지 가고 지표만 여기서 자른다(ASOF_N 머리말).
    # ⚠ 길이 규약: dd[i] ↔ nav[i] 이고 rets 는 하루 짧다(nav 는 100 에서 시작).
    _mc = _mcut(dd)
    _ddM = dd[:_mc]
    _navM, _bnavM = nav[:_mc], bnav[:_mc]
    _navcM, _bnavcM = nav_c[:_mc], bnav_c[:_mc]
    _retsM, _bretsM = rets[:max(0, _mc - 1)], brets[:max(0, _mc - 1)]
    ms, mb = ann_stats(_navM, _ddM, RF), ann_stats(_bnavM, _ddM, RF)
    msc, mbc = ann_stats(_navcM, _ddM, RF), ann_stats(_bnavcM, _ddM, RF)   # 비용 후
    yrs = max(1e-9, (_mc - 1) / 252)
    step = max(1, len(nav) // 220)
    # ⚠ 대조군이 현금성(변동성 ~0)이면 샤프 차이가 허수가 된다 — 분모가 0에 가까워
    #   작은 수익 차이가 샤프 몇 단위로 증폭된다(실측: MNA vs SHY에서 Δ샤프 +1.67).
    #   그 경우 Δ샤프를 판정에 쓰지 않고 t만 본다. 화면에도 그 사실을 표시한다.
    unstable = (mb.get("vol") or 0) < 2.0
    # 🚨 지수 곡선(S&P 500·NASDAQ 100)을 같이 싣는다. 종목 랩 97종은 전부 싣고 있었는데
    #   자산 랩 61종은 이 인자를 안 넘겨서 **한 종도 못 싣고 있었다** — 자료가 없어서가
    #   아니라 배선이 없어서였다(카드의 지수 표에는 같은 지수 수치가 이미 나오고 있었다).
    #   ⚠ 가격지수(PR)라 배당이 빠져 연 ~2%p 지수가 불리하다. 화면 각주가 그 사실을 적는다.
    chart = curve_pack(dd, nav, bnav, idx_rets=load_index_tr(dd))
    return {"name": label, "rule": rule, "why": why, "note": note, "chart": chart,
            # 🚨 기준일이 둘이다 — end 는 지표를 잰 마지막 날(전월말), px_end 는 곡선이
            #   닿는 날(오늘). 종목 랩의 perf_end/px_end 와 같은 이름 규약이다.
            "start": DTS[start], "end": (_ddM[-1] if _ddM else DTS[-1]),
            "px_end": DTS[-1], "n_days": _mc,
            "metrics": ms, "bench": mb, "bench_label": bench_label, "bench_tickers": bench_tickers,
            "bench_unstable": unstable, "holdings": hold_now,
            "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
            "t": tstat(_retsM, _bretsM), "risk": risk_bootstrap(_retsM, _bretsM),
            # 판정 축을 늘린다(2026-08-12 사용자 지시) — 알파·포착률·꾸준함·국면.
            "axes": axes_pack(_retsM, _bretsM, _navM, _bnavM, _ddM),
            # 보조 대조군 — 판정에는 안 쓴다. 주대조군 하나로는 잣대가 한쪽으로 기우는 것을
            # 읽는 사람이 알 수 없어서 나란히 둔다.
            "bench2": b2,
            "turnover": round(turn / 2 / yrs, 1),
            # 비용 후 — gross 를 대체하지 않고 나란히 싣는다.
            #   cost_kill 은 '무비용에서는 대조군보다 샤프가 높았는데 비용을 물리니 뒤집혔다'는
            #   뜻이다. 회전이 큰 규칙에서만 켜지고, 켜지면 그 줄의 우위는 비용이 먹는다.
            "cost_bp": round(COST_RT * 10000, 1),
            "metrics_net": msc, "bench_net": mbc,
            "cost_drag": round((ms.get("cagr") or 0) - (msc.get("cagr") or 0), 2),
            "cost_kill": bool(((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0)) > 0
                              and ((msc.get("sharpe") or 0) - (mbc.get("sharpe") or 0)) <= 0),
            # 우위가 없던 줄은 cost_kill 이 안 켜진다(뒤집힐 우위가 없으니까). 그래서 '비용에
            # 민감한가'를 따로 표시한다 — 연 0.5%p 넘게 깎이면 무비용 숫자를 그대로 읽으면 안 된다.
            "cost_sensitive": bool((ms.get("cagr") or 0) - (msc.get("cagr") or 0) >= 0.5),
            # 🚨 2026-08-05 추가. 증분 알파(incr/incr5)는 **날짜 정합** 회귀라 dates 가 없으면
            #   아예 못 돈다. 종전에는 nav·bnav 만 실어 이 랩들이 그 검정을 한 번도 못 받았다.
            "dates": (_gt := gthin(dd, nav, bnav))[0],
            "nav": _gt[1],
            "bnav": _gt[2]}


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
# 위기에만 값을 하면 위험방어, 초과수익 자체가 목적이면 수익엔진.
# 🚨 2026-08-08 어휘 통일 — '방어보험'(2종)과 '위험감축'(1종)을 **위험방어** 하나로 합쳤다.
#   둘은 뜻이 같은데 말만 달랐고, 각 1~2종짜리 고아 범주라 화면 집계에서 조용히 사라졌다
#   (strategy_index.by_role 이 3값만 내고 있었다 — 셋 다 hidden 에 들어가 있어서다).
#   판정 어휘도 같이 맞췄다: 자산 랩만 '대조군 열위'였고 종목 랩은 '열위'다. 같은 뜻이다.
ROLE = {
    "curve-carry": "타이밍오버레이", "tsmom-multi": "타이밍오버레이", "tail-hedge": "위험방어",
    "macro-rot": "타이밍오버레이", "infl-real": "타이밍오버레이", "hrp-alloc": "배분기",
    "commod-tsmom": "타이밍오버레이", "rp-extended": "배분기", "vix-ts": "타이밍오버레이",
    "gem": "타이밍오버레이", "vol-roll": "위험방어", "real-yield": "타이밍오버레이",
    "crypto-sat": "배분기", "sector-rp": "배분기", "bond-trend": "타이밍오버레이",
    "mf-satellite": "배분기", "credit-gate": "타이밍오버레이", "overnight": "수익엔진",
    "merger-arb": "수익엔진", "min-cvar": "배분기", "rp-voltarget": "위험방어",
    "rp-cadence": "배분기", "rp-horizon": "타이밍오버레이", "overnight-ndx": "수익엔진",
    "vrp-shortvol": "수익엔진", "credit-bond-gate": "타이밍오버레이", "ebp-gate": "타이밍오버레이",
    "quality-tilt": "수익엔진", "carry": "수익엔진", "hrp-sleeve": "배분기",
    "regime-switch": "타이밍오버레이", "ml-timing": "타이밍오버레이",
    "ml-xsec": "수익엔진", "ml-xsec-inter": "수익엔진", "ml-xsec-tree": "수익엔진",
    "ml-xsec-w-ridge": "수익엔진", "ml-xsec-w-forest": "수익엔진",
    "guru-clone": "수익엔진",
    # 고전 타이밍 규칙 — 전부 '언제 들어가 있을까'만 정하므로 타이밍오버레이다.
    # 변동성 타깃은 노출을 위로 늘리지 않고 줄이기만 해 성격이 다르다(위험감축).
    # 섹터 로테이션 10종(2026-08-12) — 어느 섹터를 살지 고르므로 수익엔진이다.
    "sec-tsmom": "수익엔진", "sec-dual": "수익엔진", "sec-lowvol": "수익엔진",
    "sec-52wh": "수익엔진", "sec-rev1m": "수익엔진", "sec-lowcorr": "수익엔진",
    "sec-sma200": "수익엔진", "sec-term": "수익엔진", "sec-vix": "수익엔진",
    # 거시 축 팩터 전환 4종 — PREREG-2026-08-24-FACTORSWITCH.md.
    #   ⚠ «타이밍오버레이» 가 아니라 «수익엔진» 이다. 위험을 켰다 껐다 하는 것이 아니라
    #     **항상 100% 투자하되 어느 팩터인지**를 바꾼다(현금으로 안 빠진다).
    # ⚠ 이 지도의 키는 **sid** 다(arch 가 아니다). arch=None 이라 sid 로 적는다.
    "fx-factorsw": "수익엔진", "fx-factorsw-mom": "수익엔진",
    "fx-trend-gate": "수익엔진", "curve-factorsw": "수익엔진",
    "sec-halloween": "수익엔진",
    # 다단계 TAA·통계·간단 ML 10종(2026-08-12).
    # ⚠ Keller 계열·국면 스위치·능형회귀는 ‘언제 들어가 있을까’가 아니라 ‘무엇을’도 고른다 — 수익엔진.
    #   최소분산·위험균형은 비중만 정하므로 배분기다.
    "taa-vaa-g4": "수익엔진", "taa-daa-g6": "수익엔진",
    "taa-baa-a": "수익엔진", "taa-baa-b": "수익엔진",
    "st-hurst": "수익엔진", "st-vratio": "수익엔진",
    "st-ou": "수익엔진", "ml-ridge": "타이밍오버레이",
    "st-minvar-lw": "배분기", "st-rp-trend": "배분기",
    "sma200": "타이밍오버레이", "golden-cross": "타이밍오버레이", "abs-mom": "타이밍오버레이",
    "seasonal": "타이밍오버레이", "curve-inv": "타이밍오버레이", "vix-level": "타이밍오버레이",
    "unrate-trend": "타이밍오버레이", "timing-ensemble": "타이밍오버레이",
    # 타이밍 규칙에 따라붙는 반론을 하나씩 검정하는 줄들. 전부 진입 여부를 정하므로 오버레이다.
    # ⚠ 여기 있던 '위험감축' 세 줄(vol-target-spy·dd-gate·vol-regime)은 2026-07-30 에 전략째로
    #   지웠다(사용자 결정) — 아래 s_voltgt·s_ddgate·s_volregime 이 있던 자리다.
    "sma-grid": "타이밍오버레이", "sma200-confirm": "타이밍오버레이",
    "rel-mom3": "타이밍오버레이",
    # 달력·구조 계열 — 가격도 재무도 안 보고 날짜만 본다. 성격은 여전히 진입 여부다.
    "tom": "타이밍오버레이", "opex": "타이밍오버레이", "fomc-even": "타이밍오버레이",
}


# 🚨 2026-08-19 사용자 결정 — **샤프 0.5 미만 삭제.**
#   explorer.html 에서 「샤프 0.5 미만 전략들은 전부 삭제」 요청. 걸린 것 17종 중
#   16종이 여기(자산배분)이고 1종이 종목 전략(t-clvgate)이다.
#   ⚠ 등급은 17종 다 «측정만» 이었다 — 배포·제한적 유효는 하나도 안 걸렸다.
# 🚨 이것은 **판정이 아니라 사용자 결정**이다. 이 랩은 2026-08-13·16 에 t 문턱을
#   폐지했고 게시 기준을 두지 않는다. 그러니 «샤프 0.5» 도 랩의 기준이 아니다 —
#   남은 규칙의 문턱을 낮추지도, 새 문턱을 세우지도 않는다.
# ⚠ 그리고 이 삭제는 **남은 목록을 실제보다 좋아 보이게 만든다**(생존 선택).
#   그래서 삭제 직전 분포를 build/tested_not_published.json 에 통째로 적어 두었다.
# ⚠ 정의를 지우지 않고 여기서 거른다 — 코드를 들어내면 공용 스코어러가 딸려 나가
#   남은 규칙이 조용히 달라질 수 있다. 사유가 사라지지 않게 목록으로 남긴다.
DROPPED = {
    "opex",
    "bond-trend",
    "credit-bond-gate",
    "commod-tsmom",
    "carry",
    "tsmom-multi",
    "st-ou",
    "curve-carry",
    "fomc-even",
    "st-vratio",
    "macro-rot",
    "seasonal",
    "hrp-alloc",
    "gem",
    "sec-lowcorr",
    "sec-rev1m",
}


def add(sid, arch, fn):
    if sid in DROPPED:
        return
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
                           lambda i: {"^GSPC": 1.0},
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
            sp = macro_asof("T10Y2Y", d)          # 기간스프레드 — 일간이라 시차 없음
            # ⚠ 실업률은 월간이고 관측월이 끝난 뒤에 발표된다. 전에는 macro_asof 로 읽어
            #   그달 말일에 그달 실업률을 아는 셈이었다(look-ahead). 발표 시차를 넣는다.
            _u = macro_asof_m("UNRATE", d, 21)
            un = _u[-1] if _u else None
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
                           lambda i: {"^GSPC": 1.0},
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
                           lambda i: {"^GSPC": 1.0},
                           "BTC 비중을 60일 실현변동성 기준 목표에 맞춰 0~5%로 조절, 나머지 SPY. 월말.",
                           "변동성으로 크기를 조인 위성이 본체를 개선하는지. 대조군은 S&P 500(PR).")
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
    # ── 거시 축 팩터 전환 4종 (D1~D4) — PREREG-2026-08-24-FACTORSWITCH.md ──
    # 🚨 앞선 A1(x-realsw · 종목 20개 바스켓 전환)이 실패한 뒤의 후속이다. 두 교훈을 반영했다:
    #   ① 축이 틀렸었다 — 실질금리는 성장/가치를 못 가른다(ETF 대리 재측정: 전환 0.742 <
    #      성장 단독 0.836). 갈리는 짝을 735조합 훑기로 다시 골랐다.
    #   ② 종목 바스켓을 52번 갈아타면 마찰이 이득을 먹는다. **ETF 전환은 거래 2건**이라
    #      여기(자산 랩)에 둔다.
    # ⚠ 후보를 검색으로 골랐으므로 표본 안 성적은 낙관 쪽이다. 등록 문서가 «표본 밖에서만
    #   판정» 을 못박고 있다.
    # ⚠ 창이 2011~ 이다(USMV·SPHB 상장). 이 넷은 **GFC 를 한 번도 안 본다** — 2006 부터
    #   도는 다른 자산 규칙과 같은 표에서 샤프를 비교하면 안 된다.
    def _usd_chg(i, back=63):
        """광의 달러지수의 back 거래일 변화(지수라 비율). 못 구하면 None."""
        d0, d1 = DTS[max(0, i - back)], DTS[i]
        a0, a1 = macro_asof("DTWEXBGS", d0), macro_asof("DTWEXBGS", d1)
        return (a1 / a0 - 1.0) if (a0 and a1 and a0 > 0) else None

    def _curve_chg(i, back=63):
        """10년−2년 스프레드의 back 거래일 변화(%p 차분)."""
        d0, d1 = DTS[max(0, i - back)], DTS[i]
        a0, a1 = macro_asof("T10Y2Y", d0), macro_asof("T10Y2Y", d1)
        return (a1 - a0) if (a0 is not None and a1 is not None) else None

    def _switch(hi, lo, cond, label, rule, why, note=None):
        """상태가 참이면 hi, 아니면 lo 를 100% — 두 다리 ETF 전환의 공통 뼈대.

        ⚠ 뼈대를 하나로 두는 이유는 넷이 **상태만 다르기** 때문이다. 넷을 각자 쓰면
          다리 처리나 결측 규약이 조용히 갈린다.
        ⚠ 상태를 못 구하는 날(창 앞머리·거시 결측)은 **저변동 다리**로 둔다. 임의 선택이
          아니라 «모르면 방어» 라는 한 방향을 미리 정해 둔 것이다 — 결과를 보고 정하면
          그 선택 자체가 자유도가 된다.
        """
        ts = [hi, lo, "SPY"]
        st = first_common(ts)

        def w(i):
            c = cond(i)
            return {hi: 1.0} if c else {lo: 1.0}
        return run_weights(w, st, label, lambda i: {"^GSPC": 1.0}, rule, why, note=note)

    def s_fxsw():
        return _switch("SPHB", "USMV",
                       lambda i: (_usd_chg(i) or 0.0) < 0,
                       "달러 축 팩터 전환 (고베타 ↔ 저변동)",
                       "광의 달러지수(DTWEXBGS)의 63거래일 변화가 음이면 S&P500 고베타(SPHB) "
                       "100%, 아니면 최소변동성(USMV) 100%. 월말 판정.",
                       "달러 약세는 해외매출·실물자산·위험선호가 함께 도는 구간이라 고베타가 "
                       "낫고, 강세면 반대라는 가설이다. 추세를 통제해도 갈림이 남는 것을 "
                       "확인했다 — SPY 가 200일선 위인 152개월만 떼어도 달러약세 69개월 "
                       "고베타-저변동 +2.36%p, 강세 83개월 -0.02%p 였다. "
                       "⚠ 상장이 2011 이라 이 규칙은 금융위기를 한 번도 안 본다.",
                       note="후보를 735조합 훑기로 골랐다 — 표본 안 성적은 낙관 쪽이다.")

    def s_fxsw_mom():
        return _switch("MTUM", "USMV",
                       lambda i: (_usd_chg(i) or 0.0) < 0,
                       "달러 축 팩터 전환 (모멘텀 ↔ 저변동)",
                       "위와 같은 상태, 다리만 모멘텀(MTUM) ↔ 최소변동성(USMV).",
                       "위가 «베타를 켰다 껐다» 라면 이것은 «어느 팩터인가» 다. 두 다리의 "
                       "단독 샤프가 비슷해(0.960·0.947) 전환이 더하는 것이 순수하게 상태 "
                       "정보인지 보기에 낫다 — 고베타 짝은 저변동이 원래 더 좋아서 «약한 "
                       "다리를 덜 드는 것» 만으로도 좋아 보일 수 있다.",
                       note="후보를 735조합 훑기로 골랐다 — 표본 안 성적은 낙관 쪽이다.")

    def s_fxsw_gate():
        def _c(i):
            if (_usd_chg(i) or 0.0) >= 0:
                return False
            sp = ser("SPY")
            m = sma(sp, i, 200)
            return bool(m is not None and sp[i] is not None and sp[i] > m)
        return _switch("SPHB", "USMV", _c,
                       "달러 ∧ 추세 이중관문 (고베타 ↔ 저변동)",
                       "달러지수 63거래일 변화가 음이고 동시에 SPY 종가가 200일 "
                       "이동평균 위일 때만 고베타(SPHB), 아니면 저변동(USMV). 월말 판정.",
                       "랩에 이미 200일선 기반 팩터 로테이션(a-a2-factor-rot)이 있다. 그 "
                       "위에 달러가 무엇을 더하는지 보는 규칙이다 — 추세만 쓰면 고베타 다리를 "
                       "85% 의 달에 드는데, 달러를 겹치면 그 절반으로 준다. "
                       "⚠ 관문 둘을 곱하면 «덜 전환해서» 좋아졌는지 «덜 틀려서» 좋아졌는지 "
                       "가 섞인다. 전환수와 다리 비중을 같이 봐야 갈린다(등록 문서 실패 조건).",
                       note="후보를 735조합 훑기로 골랐다 — 표본 안 성적은 낙관 쪽이다.")

    def s_curvesw():
        return _switch("SPHB", "USMV",
                       lambda i: (_curve_chg(i) or 0.0) > 0,
                       "곡선 축 팩터 전환 (고베타 ↔ 저변동)",
                       "10년-2년 스프레드의 63거래일 변화가 양(곡선 확대)이면 고베타(SPHB), "
                       "아니면 저변동(USMV). 월말 판정.",
                       "달러 축(위)과 같은 다리를 다른 상태로 가른다. 둘이 거의 같은 곡선을 "
                       "내면 축이 하나인 것이고, 갈리면 서로 다른 것을 재고 있다는 뜻이다 — "
                       "랩이 x-ratebeta 와 x-fxbeta 를 쌍으로 둔 것과 같은 이유다. "
                       "⚠ 둘의 상관이 0.95 를 넘으면 별개 검정으로 세면 안 된다(등록 문서).",
                       note="후보를 735조합 훑기로 골랐다 — 표본 안 성적은 낙관 쪽이다.")

    # ⚠ arch=None 이다. arch 는 **기각 원장(archive_index)의 sid 를 가리키는 링크**이고,
    #   이 넷은 아카이브에서 되살린 것이 아니라 새로 등록한 규칙이라 가리킬 곳이 없다.
    #   없는 sid 를 적으면 화면 카드가 빈다(검증기가 그렇게 잡았다).
    add("fx-factorsw", None, s_fxsw)
    add("fx-factorsw-mom", None, s_fxsw_mom)
    add("fx-trend-gate", None, s_fxsw_gate)
    add("curve-factorsw", None, s_curvesw)

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
                           lambda i: {"^GSPC": 1.0},
                           "HYG/LQD 가격비가 1년 중앙값 이상이면 SPY, 미만(신용 스트레스)이면 SHY. 월말.",
                           "ICE BofA OAS는 공개 CSV가 3년치뿐이라 장기로는 못 쓴다. "
                           "가격비는 같은 정보를 담고 전 구간이 있어 이걸로 대신한다.",
                           note="원 규칙의 OAS 대신 HYG/LQD 가격비를 썼다 — 프록시임을 명시한다.")
    add("credit-gate", "credit-regime-gate", s_credit)

    # 18) 오버나이트 드리프트 (종가 매수 → 시가 매도)
    def s_overnight():
        st = cap_start(260)          # 10년 상한 — run_weights 를 안 지나는 경로다
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
        # 🚨 판정선은 지수(PR)다 — 랩 전체가 그렇다(_bench_idx 위 주석). 종전 대조군이던
        #   'SPY 종가→종가'는 **버리지 않고 보조로 내린다.** 그것이 이 전략의 원래 질문
        #   ("밤에만 드는 것이 하루 종일 드는 것보다 나은가")을 재는 유일한 대조군이다.
        inav, irets = idx_leg("^GSPC", st, n)
        # 지표는 전월말까지(ASOF_N 머리말) · 곡선은 오늘까지
        _mc = _mcut(dd); _ddM = dd[:_mc]
        _retsM, _iretsM, _brsM = (rets[:max(0, _mc - 1)], irets[:max(0, _mc - 1)],
                                  brs[:max(0, _mc - 1)])
        ms = ann_stats(nav[:_mc], _ddM, RF)
        mb = ann_stats(inav[:_mc], _ddM, RF)          # 판정용 — S&P 500(PR)
        mo = ann_stats(bn[:_mc], _ddM, RF)            # 보조 — SPY 종가→종가
        step = max(1, len(nav) // 220)
        return {"name": "오버나이트 드리프트 (종가 매수 → 시가 매도)",
                "chart": curve_pack(dd, nav, inav, idx_rets=load_index_tr(dd)),
                "holdings": {"kind": "asset", "as_of": DTS[-1],
                             "weights": [("SPY(밤에만)", 100.0)],
                             "note": "매일 종가에 사서 다음 시가에 판다 — 낮에는 아무것도 안 들고 있다."},
                "rule": "매 거래일 종가에 SPY를 사서 다음 날 시가에 판다(밤사이만 보유).",
                "why": "아카이브 사유는 '일별 왕복이라 월말 컨벤션과 비양립·BE 2bp'였다. "
                       "규약과 안 맞는 것과 성과가 없는 것은 다른 말이므로, 성과 자체를 잰다.",
                "note": "일 왕복 252회/년이라 무비용 결과를 그대로 읽으면 안 된다 — "
                        "왕복 2bp만 붙어도 연 5%p가 사라진다.",
                "start": DTS[st], "end": (_ddM[-1] if _ddM else DTS[-1]),
                "px_end": DTS[-1], "n_days": _mc,
                "metrics": ms, "bench": mb, "bench_label": "S&P 500(PR) 매수후보유",
                "bench2": {"label": "SPY 상시보유(종가→종가)", "metrics": mo,
                           "d_sharpe": round((ms.get("sharpe") or 0) - (mo.get("sharpe") or 0), 3),
                           "t": tstat(_retsM, _brsM)},
                "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
                "t": tstat(_retsM, _iretsM), "risk": risk_bootstrap(_retsM, _iretsM),
                "turnover": 252.0,
                # 🚨 2026-08-05 추가. 증분 알파(incr/incr5)는 **날짜 정합** 회귀라 dates 가 없으면
                #   아예 못 돈다. 종전에는 nav·bnav 만 실어 이 랩들이 그 검정을 한 번도 못 받았다.
                "dates": (_gt := gthin(dd, nav, inav))[0],
                "nav": _gt[1],
                "bnav": _gt[2]}
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

    # ── 🚨 2026-08-19 — 배포 원장의 수동 곡선을 랩 안으로 들여온다(사용자 결정 «수동은
    #   없게 만들어»). 종전에는 이 규칙의 성과 곡선이 data/strategy_backtests.json 에
    #   **손으로 반출한 파일**로 들어 있었다(generated 가 한 날짜에 멈춰 있었다).
    #   규칙 자체는 build/refresh_holdings.py 가 이미 무료 yfinance 로 매일 재현하고
    #   있었으므로(보유 구성), 여기서 **같은 규칙의 곡선**을 매일 굽는다.
    # ⚠ 같은 규칙을 두 곳에 적는 것이 아니다 — refresh_holdings 는 «지금 비중» 하나를,
    #   여기는 «과거 곡선» 을 낸다. 규칙 문구를 아래에 그대로 적어 둬 어긋나면 눈에 띈다.
    RP12 = ["SPY", "QQQ", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "UUP", "HYG", "LQD", "VNQ"]
    RP12_RISKY = {"SPY", "QQQ", "EFA", "EEM", "HYG", "VNQ", "DBC"}

    def _rp12(volwin, target, label, rule, why, note=None):
        st = first_common(RP12)
        def base(i):
            o = {}
            for t in RP12:
                v = vol(ser(t), i, volwin)
                if v and v > 0:
                    # 위험자산은 12개월 추세가 양수일 때만 담는다(추세 게이트)
                    if t in RP12_RISKY and (ret(ser(t), i, 252) or -1) <= 0:
                        continue
                    o[t] = 1.0 / v
            return o
        def w(i):
            raw = base(i)
            if not raw:
                return {"SHY": 1.0}
            tot = sum(raw.values())
            wts = {t: v / tot for t, v in raw.items()}
            # 목표 변동성 스케일 — 30일 실현변동성 기준, 레버 0.3~2.5배(원 규칙과 같다)
            pv = 0.0
            for t, wt in wts.items():
                v = vol(ser(t), i, 30)
                if v:
                    pv += wt * v * math.sqrt(252)
            k = 1.0 if not pv else max(0.3, min(2.5, target / pv))
            out = {t: wt * k for t, wt in wts.items()}
            if k < 1.0:
                out["SHY"] = out.get("SHY", 0.0) + (1.0 - k)
            return out
        return run_weights(w, st, label, base, rule, why, note=note)

    _RP12_NOTE = ("🚨 이 곡선은 2026-08-19 부터 랩이 매일 굽는다. 그 전에는 사내 정본에서 "
                  "손으로 반출한 파일이었다 — 규칙은 같고 가격만 무료 yfinance 다. "
                  "그래서 사내 정본과 소수점에서 다를 수 있다(build/refresh_holdings.py 와 같은 사유).")
    add("rp12", "",
        lambda: _rp12(60, 0.10, "크로스에셋 리스크패리티 (12자산 · 목표변동성 10%)",
                      "월말에 12개 ETF 를 60일 실현변동성의 역수로 가중한다. 위험자산은 12개월 "
                      "추세가 양수일 때만 담고, 전체 연변동성이 10%가 되게 노출을 0.3~2.5배로 "
                      "조절한다(남는 몫은 SHY).",
                      "이 랩의 배포 전략이던 규칙이다. 종전에는 곡선이 수동 반출물이라 자동으로 "
                      "갱신되지 않았다 — 같은 규칙을 랩 안에서 다시 재 자동 갱신되게 한다.",
                      note=_RP12_NOTE))
    add("rp12-vw", "",
        lambda: _rp12(90, 0.10, "크로스에셋 RP 12자산 — 변동성 추정창 90일",
                      "위와 같되 역변동성 추정창을 60일 대신 90일로 둔다.",
                      "추정창 하나만 바꾼 강건성 변형. 창 선택이 결과를 만들었는지 본다.",
                      note=_RP12_NOTE))

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
        st = cap_start(260)          # 10년 상한 — 위 s_overnight 과 같은 사유
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
        # 🚨 판정선은 지수(PR). 여기는 NASDAQ 100 이 짝이다 — 이 규칙이 사는 것이 QQQ 라
        #   S&P 500 을 대면 '나스닥이 더 올랐다'가 섞여 든다. 종전 대조군이던
        #   'QQQ 종가→종가'는 버리지 않고 보조로 내린다(이 전략의 원래 질문이다).
        inav, irets = idx_leg("^NDX", st, n)
        # 지표는 전월말까지(ASOF_N 머리말) · 곡선은 오늘까지
        _mc = _mcut(dd); _ddM = dd[:_mc]
        _retsM, _iretsM, _brsM = (rets[:max(0, _mc - 1)], irets[:max(0, _mc - 1)],
                                  brs[:max(0, _mc - 1)])
        ms = ann_stats(nav[:_mc], _ddM, RF)
        mb = ann_stats(inav[:_mc], _ddM, RF)          # 판정용 — NASDAQ 100(PR)
        mo = ann_stats(bn[:_mc], _ddM, RF)            # 보조 — QQQ 종가→종가
        step = max(1, len(nav) // 220)
        return {"name": "오버나이트 보유 (QQQ 종가→시가)",
                "chart": curve_pack(dd, nav, inav, idx_rets=load_index_tr(dd)),
                "holdings": {"kind": "asset", "as_of": DTS[-1],
                             "weights": [("QQQ(밤에만)", 100.0)],
                             "note": "매일 종가에 사서 다음 시가에 판다 — 낮에는 아무것도 안 들고 있다."},
                "rule": "매 거래일 종가에 QQQ를 사서 다음 날 시가에 판다.",
                "why": "NASDAQ 100에서 밤사이 수익이 낮에 앉아 있는 것보다 나은지. "
                       "판정은 NASDAQ 100(PR) 기준이고, 원래 질문인 QQQ 종가→종가 대비는 보조로 병기한다.",
                "note": "연 252회 왕복이라 무비용 수치를 그대로 읽으면 안 된다.",
                "start": DTS[st], "end": (_ddM[-1] if _ddM else DTS[-1]),
                "px_end": DTS[-1], "n_days": _mc,
                "metrics": ms, "bench": mb, "bench_unstable": False,
                "bench_label": "NASDAQ 100(PR) 매수후보유",
                "bench2": {"label": "QQQ 상시보유(종가→종가)", "metrics": mo,
                           "d_sharpe": round((ms.get("sharpe") or 0) - (mo.get("sharpe") or 0), 3),
                           "t": tstat(_retsM, _brsM)},
                "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
                "t": tstat(_retsM, _iretsM), "risk": risk_bootstrap(_retsM, _iretsM),
                "turnover": 252.0,
                # 🚨 2026-08-05 추가. 증분 알파(incr/incr5)는 **날짜 정합** 회귀라 dates 가 없으면
                #   아예 못 돈다. 종전에는 nav·bnav 만 실어 이 랩들이 그 검정을 한 번도 못 받았다.
                "dates": (_gt := gthin(dd, nav, inav))[0],
                "nav": _gt[1],
                "bnav": _gt[2]}
    add("overnight-ndx", "overnight-holding-ndx", s_overnight_ndx)

    # ── 변동성 위험프리미엄 숏볼 ──
    def s_vrp():
        ts = ["SVXY", "SPY"]
        st = first_common(ts, pad=20)
        return run_weights(lambda i: {"SVXY": 0.25, "SHY": 0.75}, st,
                           "변동성 위험프리미엄 숏볼 (SVXY 25%)",
                           lambda i: {"^GSPC": 1.0},
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
            # ⚠ EBP 도 월간이다(연준이 관측월 뒤에 낸다). macro_asof 로 읽으면 그달 말일에
            #   그달 EBP 를 아는 셈이 된다 — 발표 시차 30일을 넣는다.
            _e = macro_asof_m("EBP", DTS[i], 30)
            e = _e[-1] if _e else None
            if e is None:
                return {"SPY": 1.0}
            return {"SHY": 1.0} if e > 0.3 else {"SPY": 1.0}
        return run_weights(w, st, "초과채권프리미엄(EBP) 리스크선호 게이트",
                           lambda i: {"^GSPC": 1.0},
                           "연준 EBP가 +0.3을 넘으면(리스크선호 위축) SHY, 아니면 SPY. 월말.",
                           "EBP는 FRED에 없어 '구할 수 없다'로 분류돼 있었는데, 연준이 공개 CSV로 "
                           "낸다. 실제로 받아서 돌린다.",
                           note="EBP는 월간이고 발표 지연이 있다 — 발표일 기준 최신값만 쓴다.")
    add("ebp-gate", "ebp-risk-appetite-gate", s_ebp)

    # ── A2 국면 연동 팩터 로테이션 (사전등록 PREREG-2026-08-05-A2FACTOR.md) ──
    # 🚨 이 규칙은 **수익 축으로 판정하지 않는다.** 조사 과정에서 프록시 13개 매핑이 이미
    #   돌아 결과를 봤기 때문이다(Δ샤프 −0.140~+0.080 · 최대 |t| 1.58). 사전등록 §0 참고.
    #   게시 기준은 아무도 안 본 축 — 낙폭조정 수익(Calmar) · 팩터 5종 동일가중 대조군이다.
    # ⚠ 매핑·임계·대조군은 사전등록 문서에 박혀 있다. 여기서 고치면 그 검정은 무효다.
    def s_a2factor():
        FAC = ["MTUM", "VLUE", "SIZE", "QUAL", "USMV"]
        ts = FAC + ["RPG", "IEF", "SPY"]
        # pad=260 — 첫 판정일에 252일 베타가 이미 완전해야 한다(국면3 의 베타 상한 구속).
        st = first_common(ts, pad=260)
        if st >= len(DTS) - 300 or not A["macro"].get("VIXCLS"):
            return None
        spy = A["px"].get("SPY")

        def _beta(t, i, n=252):
            """SPY 대비 추적 n일 OLS 베타. i 일까지만 쓴다(미래참조 없음)."""
            a, b = A["px"].get(t), spy
            if not a or i < n:
                return None
            xs, ys = [], []
            for j in range(i - n + 1, i + 1):
                if a[j] and a[j - 1] and b[j] and b[j - 1]:
                    xs.append(b[j] / b[j - 1] - 1); ys.append(a[j] / a[j - 1] - 1)
            if len(xs) < n * 0.8:
                return None
            mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
            vx = sum((x - mx) ** 2 for x in xs)
            if vx <= 0:
                return None
            return sum((xs[k] - mx) * (ys[k] - my) for k in range(len(xs))) / vx

        def w(i):
            v = macro_asof("VIXCLS", DTS[i])
            m200 = sma(spy, i, 200)
            if v is None or m200 is None or not spy[i]:
                return {"SPY": 1.0}                     # 신호가 없으면 판단하지 않는다
            up = spy[i] > m200
            if up and v < 20:                           # 국면1 — 모멘텀+성장
                return {"MTUM": 0.5, "RPG": 0.5}
            if up and v <= 28:                          # 국면2 — 퀄리티+멀티팩터
                return dict({"QUAL": 0.5}, **{t: 0.125 for t in FAC if t != "QUAL"})
            # 국면3 — 저변동+퀄리티, 포트 베타 ≤ 0.80 을 **구속으로** 건다
            bu, bq = _beta("USMV", i), _beta("QUAL", i)
            if bu is None or bq is None or bu >= bq:
                return {"USMV": 0.5, "QUAL": 0.5}       # 추정 불가 시 원문 그대로
            x = min(1.0, max(0.5, (0.80 - bq) / (bu - bq)))
            bmix = x * bu + (1 - x) * bq
            if bmix <= 0.80:
                return {"USMV": x, "QUAL": 1 - x}
            k = 0.80 / bmix                             # 그래도 넘으면 IEF 로 희석
            return {"USMV": k * x, "QUAL": k * (1 - x), "IEF": 1 - k}

        return run_weights(
            w, st, "국면 연동 팩터 로테이션 (A2)",
            lambda i: {t: 0.2 for t in FAC},            # 대조군 = 팩터 5종 동일가중
            "SPY 종가가 200일선 위이고 VIX<20 이면 MTUM50+RPG50, 200일선 위이고 VIX 20~28 이면 "
            "QUAL50+나머지 팩터 4종 각 12.5%, 200일선 아래이거나 VIX>28 이면 USMV+QUAL 을 "
            "추적 252일 베타로 포트 베타 0.80 이하가 되게 섞는다(그래도 넘으면 IEF 희석). "
            "월말 판정·월 1회 전환. 대조군은 같은 팩터 5종 동일가중.",
            "【문헌】팩터 프리미엄이 변동성·추세 국면에 따라 순환한다는 주장. 【실측】이 랩은 "
            "'정적 팩터 대비 낙폭 축소'를 158개월 팩터 구간에서 한 번도 재본 적이 없다 — "
            "quality-tilt 한 행이 전부다. 그 한 문장만 검정한다.",
            note="🚨 수익 축은 판정에 쓰지 않는다 — 프록시 13매핑이 이미 돌아 결과를 봤다"
                 "(사전등록 §0). 게시 기준은 Calmar 와 팩터 5종 EW 대조군이다. "
                 "⚠ 국면2 는 158개월 중 15개월(에피소드 12·중앙 1개월)뿐이라 이 버킷 단독 "
                 "주장은 하지 않는다. 시간의 73%가 국면1 이라 성과 대부분이 거기서 나온다.")
    add("a2-factor-rot", "regime-factor-rotation", s_a2factor)

    # ── A7 경기순환 섹터 로테이션 (사전등록 PREREG-2026-08-06-A7SECTOR.md) ──
    # 🚨 "출처 그대로 재현" 이 요청이다. 국면별 섹터는 출처 문장 그대로 옮겼고,
    #   출처가 판단에 맡긴 자리(국면 판정식)만 내가 정했다 — 자유도 0 인 2×2 로.
    #   히스테리시스 2개월 · 신호 30일 지연 · 5bp 비용은 전부 출처가 명시한 것이다.
    # ⚠ 규칙을 여기서 고치면 그 검정은 무효다. 고치려면 새로 등록할 것.
    SEC9 = ["XLK", "XLY", "XLF", "XLI", "XLB", "XLE", "XLU", "XLP", "XLV"]
    CYC = ["XLK", "XLY", "XLF", "XLI", "XLB", "XLE"]       # 경기민감
    DEF = ["XLP", "XLV", "XLU"]                            # 방어
    PHASE_W = {                                            # 출처의 국면별 우위 섹터
        "early": ["XLF", "XLY"],                           # 회복 — 부동산(XLRE)은 표본 사유로 제외
        "mid":   ["XLK", "XLI"],                           # 확장
        "late":  ["XLE", "XLB", "XLU"],                    # 둔화
        "rec":   ["XLP", "XLV", "XLU"],                    # 침체
    }

    def _ew(ts):
        return {t: 1.0 / len(ts) for t in ts}

    def _hyst(seq):
        """2개월 연속 같은 신호일 때만 전환. 출처가 권고한 국면 오판 방어다.

        seq[i] = i 월말의 원신호. 돌려주는 것은 '실제로 들고 있는' 라벨.
        ⚠ 미래참조 없음 — i 는 i·i−1 만 본다.
        """
        out, cur = [], None
        for i, v in enumerate(seq):
            if v is not None and i > 0 and seq[i - 1] == v:
                cur = v                                    # 두 달 연속이면 전환
            if cur is None:
                cur = v                                    # 첫 판정은 그대로 받는다
            out.append(cur)
        return out

    def _mstance(i):
        """긴축(True)/완화(False). FEDFUNDS 최신 발표분 vs 12개월 전. 모자라면 None."""
        v = macro_asof_m("FEDFUNDS", DTS[i], 30, n=13)
        return None if len(v) < 13 else (v[-1] > v[0])

    def _phase(i):
        """Fidelity 4국면 — 산업생산 12개월 변화 × 실업률 12개월 변화의 2×2."""
        g = macro_asof_m("INDPRO", DTS[i], 30, n=13)
        u = macro_asof_m("UNRATE", DTS[i], 30, n=13)
        if len(g) < 13 or len(u) < 13:
            return None
        gu, uu = g[-1] > g[0], u[-1] > u[0]                # 성장 +? 실업 +?
        return ("late" if uu else "mid") if gu else ("rec" if uu else "early")

    def _sig_series(fn, st):
        """월말마다 fn(i) 를 재고 히스테리시스를 먹인 뒤 {인덱스: 라벨} 로 돌려준다."""
        ends = month_ends(st, len(DTS))
        raw = [fn(i) for i in ends]
        return dict(zip(ends, _hyst(raw)))

    def s_a7_conover():
        ts = SEC9 + ["SPY"]
        st = first_common(ts, pad=20)
        if not A["macro"].get("FEDFUNDS"):
            return None
        sig = _sig_series(_mstance, st)
        def w(i):
            v = sig.get(i)
            if v is None:
                return _ew(SEC9)                           # 판정 불가 구간은 중립(9섹터 동일가중)
            return _ew(DEF if v else CYC)
        return run_weights(
            w, st, "통화조건 섹터 로테이션 (Conover 2008)",
            lambda i: {"^GSPC": 1.0},
            "연방기금금리(최신 발표분)가 12개월 전보다 높으면 긴축으로 보아 방어 3섹터"
            "(XLP·XLV·XLU) 동일가중, 낮으면 완화로 보아 경기민감 6섹터"
            "(XLK·XLY·XLF·XLI·XLB·XLE) 동일가중. 월말 판정 · 2개월 연속 확인 후 전환 · "
            "거시 발표 30일 지연 반영. 대조군은 S&P 500(PR).",
            "Conover·Jensen·Johnson·Mercer(2008, Journal of Investing) — 33년 자료에서 Fed "
            "완화기 경기민감·긴축기 방어 전환이 낮은 리밸런싱 빈도로도 유의한 초과수익을 냈다"
            "(긴축기 방어 로테이션 수익이 벤치마크의 약 2배·리스크는 더 낮음). 그 주장을 이 "
            "패널에서 그대로 돌린다.",
            note="⚠ 원논문은 연준 재할인율 변경 방향으로 통화조건을 판정한다. 그 계열은 "
                 "1990년대 이후 정책수단이 아니게 됐으므로 같은 뜻의 연방기금금리로 바꿨다 — "
                 "이 재현의 유일한 신호 대체다(사전등록 §2-A).")
    add("a7-conover", "business-cycle-sector-rotation", s_a7_conover)

    def s_a7_fidelity():
        ts = SEC9 + ["SPY"]
        st = first_common(ts, pad=20)
        if not (A["macro"].get("INDPRO") and A["macro"].get("UNRATE")):
            return None
        sig = _sig_series(_phase, st)
        def w(i):
            v = sig.get(i)
            return _ew(PHASE_W[v]) if v else _ew(SEC9)
        return run_weights(
            w, st, "4국면 섹터 로테이션 (Fidelity 프레임워크)",
            lambda i: {"^GSPC": 1.0},
            "산업생산 12개월 변화와 실업률 12개월 변화의 부호로 4국면을 판정하고 국면별 우위 "
            "섹터를 동일가중으로 든다 — 회복 XLF·XLY / 확장 XLK·XLI / 둔화 XLE·XLB·XLU / "
            "침체 XLP·XLV·XLU. 월말 판정 · 2개월 연속 확인 후 전환 · 거시 발표 30일 지연 반영. "
            "대조군은 S&P 500(PR).",
            "Fidelity 4국면 프레임워크가 1962년 이후 자료에서 문서화한 국면별 상대우위 — "
            "초기엔 금융·경기소비재·부동산, 후기엔 에너지·소재, 침체기엔 필수소비재·헬스케어·"
            "유틸리티. 국면별 섹터 배정을 출처 문장 그대로 옮겨 돌린다.",
            note="⚠ 국면 판정식은 출처가 판단에 맡긴 자리다. ISM 은 FRED 에서 받을 수 없어"
                 "(NAPM 404 · 유료) 원문이 함께 지목한 산업생산을 쓴다. 수익률곡선·신용스프레드는 "
                 "쓰지 않는다 — 넷을 다 쓰면 결합이 수십 가지가 되고 그중 하나를 고르는 순간 "
                 "결과를 보고 고른 것과 구별되지 않는다. 2×2 는 결합 자유도가 0 이다. "
                 "회복 국면의 부동산(XLRE)은 2015-10 상장이라 뺐다 — 넣으면 표본에 침체가 "
                 "1회만 남는다(사전등록 §1).")
    add("a7-fidelity", "business-cycle-sector-rotation", s_a7_fidelity)

    # ── A7b 빠른 위험 게이트 + 국면 섹터 선택 (사전등록 PREREG-2026-08-06-A7B.md) ──
    # 🚨 이 설계는 A7 결과를 **보고 나왔다**(사전등록 §0 에 고지). 진단이 가리킨 기전 둘을
    #   고친다: ① 반응 하한 3개월 vs 코로나 급락 23거래일 ② 완벽한 타이밍조차 −40.6 —
    #   주식 안에서 도는 것으로는 안 된다. 그래서 빠른 가격 게이트 + 주식 밖 대피다.
    # ⚠ 국면 판정식은 A7 과 글자 그대로 같다. 여기서 고치면 무엇이 달라졌는지 알 수 없다.
    # ⚠ 이 랩엔 "낙폭은 줄이되 시장은 못 이기는" 게이트가 이미 여섯이고 전부 구별 불가다.
    #   그러므로 낙폭 축소는 증거가 아니라 기대되는 부작용이다 — 판정은 incr5 가 한다.
    def s_a7b():
        ts = SEC9 + ["IEF", "SPY"]
        st = first_common(ts, pad=20)
        if not (A["macro"].get("INDPRO") and A["macro"].get("UNRATE")):
            return None
        sig = _sig_series(_phase, st)
        spy = A["px"].get("SPY")
        def w(i):
            m200 = sma(spy, i, 200)
            # 게이트에는 히스테리시스를 안 건다 — 느린 것이 문제였는데 또 늦추면 고친 게 아니다.
            if m200 is None or not spy[i]:
                return _ew(SEC9)                        # 게이트를 못 재면 중립
            if spy[i] <= m200:
                return {"IEF": 1.0}                     # 위험 회피 — 주식 밖으로 나간다
            v = sig.get(i)
            return _ew(PHASE_W[v]) if v else _ew(SEC9)
        return run_weights(
            w, st, "위험 게이트 + 국면 섹터 (A7b)",
            lambda i: {"^GSPC": 1.0},
            "SPY 종가가 200일 단순이동평균 위면 A7 의 국면별 섹터를 동일가중으로 들고"
            "(회복 XLF·XLY / 확장 XLK·XLI / 둔화 XLE·XLB·XLU / 침체 XLP·XLV·XLU), "
            "아래면 IEF 100% 로 주식 밖으로 나간다. 국면 판정은 A7 과 같다 — 산업생산·실업률 "
            "12개월 변화의 2×2 · 발표 30일 지연 · 히스테리시스 2개월. 게이트에는 히스테리시스 "
            "없음. 월말 판정 · 대조군 S&P 500(PR).",
            "A7 재현이 실패한 두 기전을 고친 것이다. 국면 신호는 반응에 최소 3개월이 걸려 "
            "코로나 급락 23거래일을 못 잡았고(실측: 침체 배분 전환일이 저점 두 달 뒤), "
            "방어섹터는 방어를 못 했다(완벽한 타이밍도 −40.6 vs SPY −33.7). 그래서 게이트를 "
            "가격 기반으로 빠르게 바꾸고 대피처를 주식 밖에 둔다.",
            note="🚨 이 설계는 A7 성적을 보고 나왔다 — 사전등록의 원래 의미를 충족하지 못하며 "
                 "그 사실을 PREREG-2026-08-06-A7B.md §0 에 고지했다. 그래서 게시 기준을 A7 보다 "
                 "하나 더 높게 잡았다(a7-fidelity 대비 증분 t ≥ +2.0). 이 랩엔 낙폭만 줄이는 "
                 "게이트가 이미 여섯이고 전부 구별 불가라, 낙폭 축소는 증거가 아니다.")
    add("a7b-gate-sector", "business-cycle-sector-rotation", s_a7b)

    # ══ 섹터 로테이션 10종 (사전등록 PREREG-2026-08-12-SECROT.md) ══════════
    # 🚨 기존 섹터 축은 '가중'(섹터RP)과 '국면 판정'(4국면·A7b·Conover) 둘뿐이었고 전부
    #   구별 불가·열위였다. 그래서 이 열은 국면 판정식을 또 만들지 않는다 — 가격 자체의
    #   추세·상대강도·변동성·상관·계절성, 그리고 국면을 판정하지 않고 관측치 하나의 부호만
    #   쓰는 것(곡선·VIX)이다. 국면 판정의 자유도가 세 번 진 자리다.
    # 🚨 XLC(2018-06)·XLRE(2015-10)는 안 넣는다. 넣으면 구간이 8년으로 잘리거나 앞구간
    #   후보가 9→11 로 부는 램프가 생긴다(DATA-FACTS #3 과 같은 사고). 그래서 이 열은
    #   통신·부동산을 영영 못 산다 — 등록 §2 에 그렇게 적었다.
    # ⚠ 대조군은 전부 같은 9섹터 동일가중이다. SPY 로 두면 '섹터를 골랐다'가 아니라
    #   '동일가중이 시총가중을 이겼다'를 재게 된다(vs_traded 에서 반복 확인한 것).
    # ⚠ 화면 문구(rule·why)에 마크다운을 쓰지 않는다 — esc() 를 타므로 별표가 그대로 찍힌다.
    CYC6 = ["XLK", "XLY", "XLF", "XLI", "XLB", "XLE"]
    DEF3 = ["XLP", "XLV", "XLU"]
    S9ST = first_common(SEC9)

    def _s9bench(i):
        return {t: 1.0 for t in SEC9}

    def _topn(score, i, n=3, rev=False):
        """그 시점 점수 상위(또는 하위) n섹터 동일가중. 점수가 None 인 섹터는 후보에서 뺀다."""
        sc = [(t, score(t, i)) for t in SEC9]
        sc = [(t, v) for t, v in sc if v is not None]
        if len(sc) < n:
            return {}
        sc.sort(key=lambda x: x[1], reverse=not rev)
        return {t: 1.0 for t, _ in sc[:n]}

    # 🚨 2026-08-13 — 이 열이 **11섹터 중 9개만 산다**는 사실이 화면에 한 글자도 없었다.
    #   위 주석이 "등록 §2 에 그렇게 적었다"고 하는데 등록 문서에만 있고 카드에는 없다 —
    #   재 놓고 안 실으면 잰 적 없는 것과 같다. 실측: XLC 를 적는 자산 전략 0종이었다.
    #   ⚠ 한 자리에서만 붙인다(_sec 호출부 10곳에 각각 적으면 한 곳이 빠지는 날이 온다).
    #   ⚠ 각 규칙 자신의 note 는 지우지 않고 **뒤에 잇는다.**
    _SEC_NOTE = ("이 열은 11섹터 중 9개만 삽니다 — 커뮤니케이션(XLC 2018-06 상장)과 "
                 "부동산(XLRE 2015-10)은 넣으면 구간이 8년으로 잘리거나 앞구간 후보가 "
                 "9→11 로 부는 램프가 생겨 뺐습니다. 그래서 이 규칙들은 통신·부동산을 "
                 "영영 못 삽니다. 대조군도 같은 9섹터 동일가중입니다.")

    def _sec(sid, label, wfn, rule, why, note=None):
        # ⚠ arch 는 기각 아카이브의 '이전 판정' 링크다. 이 열은 새 규칙이라 이전 판정이
        #   없으므로 빈 값으로 둔다 — 기존 항목을 갖다 붙이면 카드가 남의 판정을 자기 것처럼 적는다.
        _n = (note + " " + _SEC_NOTE) if note else _SEC_NOTE
        add(sid, "", lambda: run_weights(wfn, S9ST, label, _s9bench, rule, why, note=_n))

    # ① 시계열 모멘텀 — Moskowitz·Ooi·Pedersen (2012) JFE 104(2)
    _sec("sec-tsmom", "섹터 시계열 모멘텀 (절대 모멘텀 게이트)",
         lambda i: ({t: 1.0 for t in SEC9 if (ret(ser(t), i, 252) or -1) > 0} or {"SHY": 1.0}),
         "월말에 직전 252거래일 수익이 양수인 섹터만 동일가중. 하나도 없으면 SHY 100%.",
         "Moskowitz·Ooi·Pedersen(2012)의 시계열 모멘텀을 섹터에 그대로 적용한 것. "
         "횡단면 순위가 아니라 각 섹터가 자기 과거만 본다 — 전부 음수면 통째로 현금이 된다.")

    # ② 듀얼 모멘텀 — Antonacci (2014)
    def _w_dual(i):
        sh = ret(ser("SHY"), i, 252)
        sc = []
        for t in SEC9:
            m12, m1 = ret(ser(t), i, 252), ret(ser(t), i, 21)
            if m12 is None or m1 is None:
                continue
            if sh is not None and m12 <= sh:        # 절대 모멘텀 관문
                continue
            sc.append((t, m12 - m1))
        if len(sc) < 3:
            return {"SHY": 1.0}
        sc.sort(key=lambda x: -x[1])
        return {t: 1.0 for t, _ in sc[:3]}
    _sec("sec-dual", "섹터 듀얼 모멘텀 상위 3", _w_dual,
         "12-1 모멘텀(252일 − 21일) 상위 3섹터. 단 그 섹터의 252일 수익이 SHY 보다 클 때만 "
         "편입한다(절대 모멘텀 관문). 통과가 3종 미만이면 SHY 100%.",
         "Antonacci(2014)의 듀얼 모멘텀 — 상대강도로 고르고 절대 모멘텀으로 시장 밖 대피를 "
         "정한다. 이 랩의 기존 섹터 규칙에는 대피 장치가 없었다.")

    # ③ 저변동 — Blitz·van Vliet (2007) JPM 34(1)
    # 🚨 2026-08-19 — 배포 원장의 «섹터 모멘텀 로테이션 (Top 4)» 를 랩 안으로 들여온다.
    #   그 곡선도 수동 반출물이었다. 랩에 이미 상위 3 규칙이 둘 있지만(sec-dual·sec-52wh)
    #   N 이 달라 같은 전략이 아니다 — 원장이 쓰던 N=4 를 그대로 건다.
    _sec("sec-mom4", "섹터 모멘텀 로테이션 (12-1 상위 4)",
         lambda i: ({t: 1.0 for t in sorted(
             [x for x in SEC9 if ret(ser(x), i, 252) is not None],
             key=lambda x: -((ret(ser(x), i, 252) or 0) - (ret(ser(x), i, 21) or 0)))[:4]}
             or {"SHY": 1.0}),
         "월말에 12-1 모멘텀(252일 − 21일)이 높은 상위 4섹터를 동일가중.",
         "배포 원장에 있던 규칙이다. 곡선이 수동 반출물이라 자동 갱신되지 않았다 — "
         "같은 규칙을 랩 안에서 다시 재 매일 갱신되게 한다.",
         note="⚠ 랩의 sec-dual(상위 3)과 N 만 다르다. 둘을 나란히 두면 N 선택이 결과를 "
              "만들었는지 보인다.")

    _sec("sec-lowvol", "저변동 섹터 상위 3",
         lambda i: _topn(lambda t, k: vol(ser(t), k, 120), i, 3, rev=True),
         "월말에 120거래일 실현변동성이 가장 낮은 3섹터를 동일가중.",
         "Blitz·van Vliet(2007)의 저변동 이상현상을 섹터 수준에 적용. 종목 랩의 저변동 "
         "규칙과 같은 축이지만 유니버스가 섹터라 분산 효과가 다르다.")

    # ④ 52주 고점 근접 — George·Hwang (2004) JF 59(5)
    def _p52(t, i):
        s = ser(t)
        if i < 252 or s[i] is None:
            return None
        w = [s[j] for j in range(i - 251, i + 1) if s[j] is not None]
        return (s[i] / max(w)) if w and max(w) else None
    _sec("sec-52wh", "52주 고점 근접 섹터 상위 3",
         lambda i: _topn(_p52, i, 3),
         "월말에 252거래일 고점 대비 현재가 비율이 가장 높은 3섹터를 동일가중.",
         "George·Hwang(2004)은 52주 고점 근접도가 모멘텀보다 강한 예측력을 갖는다고 보고한다. "
         "모멘텀과 달리 얼마나 올랐나가 아니라 고점에서 얼마나 안 밀렸나를 본다.")

    # ⑤ 단기 반전 — Jegadeesh (1990) JF 45(3)
    _sec("sec-rev1m", "단기 반전 섹터 하위 3",
         lambda i: _topn(lambda t, k: ret(ser(t), k, 21), i, 3, rev=True),
         "월말에 직전 21거래일 수익이 가장 낮은 3섹터를 동일가중.",
         "Jegadeesh(1990)의 1개월 반전. 섹터 수준에서도 남는지 본다 — 회전율이 이 열에서 "
         "가장 높을 것이고, 무비용 기준이라 그만큼 유리하게 잡힌다.")

    # ⑥ 시장 저상관 — 문헌 규칙이 아니라 분산 착상이다
    def _corr_spy(t, i):
        a, b = ser(t), ser("SPY")
        if i < 252:
            return None
        xs, ys = [], []
        for j in range(i - 251, i + 1):
            if a[j] is not None and a[j - 1] and b[j] is not None and b[j - 1]:
                xs.append(a[j] / a[j - 1] - 1)
                ys.append(b[j] / b[j - 1] - 1)
        if len(xs) < 150:
            return None
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        sxx = sum((x - mx) * (x - mx) for x in xs)
        syy = sum((y - my) * (y - my) for y in ys)
        return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None
    _sec("sec-lowcorr", "시장 저상관 섹터 3",
         lambda i: _topn(_corr_spy, i, 3, rev=True),
         "월말에 직전 252거래일 일간수익의 SPY 대비 상관이 가장 낮은 3섹터를 동일가중.",
         "⚠ 문헌 규칙이 아니라 분산 착상이다. 상관이 낮은 섹터를 모으면 지수와 덜 같이 "
         "움직이지만, 그것이 초과수익으로 이어질 이유는 사전에 없다 — 그래서 재 본다.")

    # ⑦ 섹터별 200일선 게이트 — Faber (2007) JWM 9(4)
    def _sma_ok(t, i):
        s = ser(t)
        if i < 200 or s[i] is None:
            return False
        w = [s[j] for j in range(i - 199, i + 1) if s[j] is not None]
        return bool(w) and s[i] > sum(w) / len(w)
    _sec("sec-sma200", "섹터별 200일선 게이트",
         lambda i: ({t: 1.0 for t in SEC9 if _sma_ok(t, i)} or {"SHY": 1.0}),
         "월말에 종가가 200거래일 단순이동평균 위인 섹터만 동일가중. 하나도 없으면 SHY 100%.",
         "Faber(2007)의 추세 게이트를 섹터마다 따로 건다. 이 랩의 sma200 은 지수 하나에 "
         "걸린 것이고, 이쪽은 섹터별로 켜고 꺼 노출이 0~100% 사이에서 연속으로 움직인다.")

    # ⑧ 기간스프레드 방향 — 국면을 판정하지 않고 부호만 본다(자유도 0)
    _S9ME = None

    def _w_term(i):
        nonlocal _S9ME
        if _S9ME is None:
            _S9ME = month_ends(S9ST, len(DTS))
        prev = None
        for k in _S9ME:
            if k < i:
                prev = k
        a = macro_asof("T10Y2Y", DTS[i])
        b = macro_asof("T10Y2Y", DTS[prev]) if prev is not None else None
        if a is None or b is None:
            return {t: 1.0 for t in SEC9}
        return {t: 1.0 for t in (CYC6 if a > b else DEF3)}
    _sec("sec-term", "기간스프레드 방향 섹터", _w_term,
         "월말에 T10Y2Y(10년 − 2년)가 직전 월말보다 확대면 경기민감 6섹터, 축소면 방어 3섹터를 "
         "동일가중. 값을 못 읽으면 9섹터 동일가중.",
         "곡선이 가팔라지면 경기민감, 평탄해지면 방어라는 통상의 착상을 관측치 하나의 부호로만 "
         "옮긴 것이다. 🚨 국면을 판정하지 않는다 — 이 랩의 국면 판정식 3종이 전부 구별 불가·"
         "열위였고, 그 자유도가 문제였다.")

    # ⑨ 변동성 국면 — 확장창 중앙값(전 표본 중앙값은 룩어헤드다)
    def _w_vix(i):
        m = A["macro"].get("VIXCLS") or {}
        if not m:
            return {t: 1.0 for t in SEC9}
        ks = [k for k in sorted(m) if k <= DTS[i]]
        if len(ks) < 260:
            return {t: 1.0 for t in SEC9}
        rec = [m[k] for k in ks[-20:] if m[k] is not None]
        hist = sorted(m[k] for k in ks if m[k] is not None)
        if not rec or not hist:
            return {t: 1.0 for t in SEC9}
        med = hist[len(hist) // 2]
        cur = sum(rec) / len(rec)
        return {t: 1.0 for t in (DEF3 if cur > med else CYC6)}
    _sec("sec-vix", "변동성 국면 섹터", _w_vix,
         "월말에 VIX 20일 평균이 그 시점까지의 확장창 중앙값보다 높으면 방어 3섹터, "
         "낮으면 경기민감 6섹터를 동일가중.",
         "⚠ 중앙값은 확장창이다(그 시점까지의 관측만). 전 표본 중앙값을 쓰면 미래를 아는 "
         "문턱이 된다 — 이 랩이 반복해 밟은 자리라 명시한다.")

    # ══ 다단계 TAA · 통계 · 간단 ML 10종 (사전등록 PREREG-2026-08-12-TAA10.md) ══
    # 🚨 대조군이 **60/40(SPY 60 · AGG 40)** 이다. 이 랩의 다른 타이밍 규칙은 SPY 상시보유가
    #   대조군이라 **세로로 비교하면 안 된다.** 이 열은 대부분 채권·현금으로 빠지는 규칙이라
    #   SPY 와 겨루면 '주식이 더 올랐다'만 재게 된다.
    # 🚨 원문 티커를 이 패널에 있는 것으로 바꿨다(등록 §2): VWO→EEM · VEA→EFA · BIL→SHY ·
    #   VGK/EWJ→EFA 로 접음. 접은 만큼 원문과 다른 규칙이고, BAA-Balanced 는 12자산이
    #   아니라 11자산이 된다.
    TAA_UNI8 = ["SPY", "QQQ", "EFA", "EEM", "TLT", "GLD", "DBC", "VNQ"]

    # 🚨 대조군을 둘 다 잰다(2026-08-12 사용자 결정). 어느 쪽으로 두든 한쪽이 유리하다 —
    #   채권으로 빠지는 규칙을 SPY 와 겨루면 '주식이 더 올랐다'를 재고, 60/40 과 겨루면
    #   문턱이 연 3.3%p 낮다(SPY 11.19% vs 60/40 7.93%, 2006~2026 실측).
    #   주대조군은 지수 매수후보유 — 랩의 다른 타이밍 43종과 같은 잣대라 세로 비교가 되고,
    #   채권 대조군 필터(2026-07-28)에도 걸리지 않아 목록에 들어온다.
    #   60/40 은 보조로 병기한다(판정에는 안 쓴다).
    # 🚨 2026-08-13 — SPY → ^GSPC(PR). 이름은 남기지만 담는 것은 지수다(IDX_LAB 위 주석 참조).
    #   ⚠ 이름을 _bench_spy 그대로 둔 이유는 35개 호출부를 한꺼번에 건드리지 않으려는 것뿐이다.
    #     읽을 때 SPY 로 오해하지 않도록 여기 적어 둔다.
    def _bench_spy(i):
        return {"^GSPC": 1.0}

    def _bench6040(i):
        return {"SPY": 0.6, "AGG": 0.4}

    def _m13612(t, i):
        """13612W = 12·(p0/p1−1) + 4·(p0/p3−1) + 2·(p0/p6−1) + (p0/p12−1). 월=21거래일."""
        s = ser(t)
        if s is None:
            return None
        out, W = 0.0, ((21, 12.0), (63, 4.0), (126, 2.0), (252, 1.0))
        for n, w in W:
            r = ret(s, i, n)
            if r is None:
                return None
            out += w * r
        return out

    def _sma_rel(t, i, n=252):
        """SMA 상대모멘텀 p0 / 평균(p0…p12). BAA 가 공격·방어 선별에 쓰는 척도."""
        s = ser(t)
        if s is None or i < n or s[i] is None:
            return None
        w = [s[j] for j in range(i - n, i + 1) if s[j] is not None]
        if len(w) < n // 2:
            return None
        m = sum(w) / len(w)
        return (s[i] / m) if m else None

    def _pick(score, ts, i, n):
        sc = [(t, score(t, i)) for t in ts]
        sc = [(t, v) for t, v in sc if v is not None]
        sc.sort(key=lambda x: -x[1])
        return [t for t, _ in sc[:n]]

    # ① VAA-G4 — Keller·Keuning (2017) SSRN 3002624
    VAA_OFF, VAA_DEF = ["SPY", "EFA", "EEM", "AGG"], ["LQD", "IEF", "SHY"]

    def _w_vaa(i):
        sc = [(t, _m13612(t, i)) for t in VAA_OFF]
        if any(v is None for _, v in sc):
            return {"SHY": 1.0}
        if all(v > 0 for _, v in sc):
            return {max(sc, key=lambda x: x[1])[0]: 1.0}
        pick = _pick(_m13612, VAA_DEF, i, 1)
        return {pick[0]: 1.0} if pick else {"SHY": 1.0}
    add("taa-vaa-g4", "", lambda: run_weights(
        _w_vaa, first_common(VAA_OFF + VAA_DEF), "경계형 자산배분 VAA-G4 (Keller 2017)",
        _bench_spy,
        "월말에 공격 4종(SPY·EFA·EEM·AGG)의 13612W 모멘텀이 전부 양수면 그중 최고 1종에 100%. "
        "하나라도 음수면 방어 3종(LQD·IEF·SHY) 중 최고 1종에 100%.",
        "Keller·Keuning(2017). 13612W 는 1·3·6·12개월 수익을 12:4:2:1 로 가중한 빠른 모멘텀이다. "
        "이 랩의 절대모멘텀·GEM 과 달리 공격 유니버스 전체의 폭(breadth)을 보고 한 번에 방어로 "
        "넘어간다 — 하나만 나빠도 전량 방어다.",
        bench2_w=_bench6040, bench2_label="60/40 (SPY 60 · AGG 40)"))

    # ② DAA — Keller·Keuning (2018) SSRN 3212862
    DAA_CAN = ["EEM", "AGG"]
    DAA_OFF = ["SPY", "QQQ", "IWM", "EFA", "EEM", "VNQ", "DBC", "GLD", "TLT", "HYG"]
    DAA_DEF = ["SHY", "IEF", "LQD"]

    def _w_daa(i):
        cs = [_m13612(t, i) for t in DAA_CAN]
        if any(v is None for v in cs):
            return {"SHY": 1.0}
        b = sum(1 for v in cs if v <= 0)
        cf = b / 2.0                                    # 현금비율 = 나쁜 카나리아 수 / 2
        off = _pick(_m13612, DAA_OFF, i, 6)
        dfp = _pick(_m13612, DAA_DEF, i, 1)
        w = {}
        if off and cf < 1.0:
            for t in off:
                w[t] = (1.0 - cf) / len(off)
        if cf > 0 and dfp:
            w[dfp[0]] = w.get(dfp[0], 0.0) + cf
        return w or {"SHY": 1.0}
    add("taa-daa-g6", "", lambda: run_weights(
        _w_daa, first_common(DAA_CAN + DAA_OFF + DAA_DEF), "방어형 자산배분 DAA (카나리아 2종)",
        _bench_spy,
        "월말에 카나리아 2종(EEM·AGG)의 13612W 중 음수인 개수 b 로 현금비율 CF=b/2 를 정한다. "
        "(1−CF) 는 공격 10자산 중 13612W 상위 6종 동일가중, CF 는 방어 3종(SHY·IEF·LQD) 중 최고 1종.",
        "Keller·Keuning(2018). VAA 가 방어 전환을 0/1 로 하는 데 비해 DAA 는 비율로 한다 — "
        "카나리아 하나만 나쁘면 절반만 방어다. 원문 카나리아는 VWO·BND 인데 이 패널의 EEM·AGG 로 "
        "바꿨다(등록 §2).",
        bench2_w=_bench6040, bench2_label="60/40 (SPY 60 · AGG 40)"))

    # ③④ BAA — Keller (2022) SSRN 4166845
    BAA_CAN = ["SPY", "EFA", "EEM", "AGG"]
    BAA_OFF_A = ["QQQ", "EEM", "EFA", "AGG"]
    BAA_OFF_B = ["SPY", "QQQ", "IWM", "EFA", "EEM", "VNQ", "DBC", "GLD", "TLT", "HYG", "LQD"]
    BAA_DEF = ["TIP", "DBC", "SHY", "IEF", "TLT", "LQD", "AGG"]

    def _mk_baa(off, n_off):
        def w(i):
            cs = [_m13612(t, i) for t in BAA_CAN]
            if any(v is None for v in cs):
                return {"SHY": 1.0}
            if all(v > 0 for v in cs):
                pick = _pick(_sma_rel, off, i, n_off)
                return {t: 1.0 / len(pick) for t in pick} if pick else {"SHY": 1.0}
            # 방어 — 상위 3 중 SHY 척도보다 낮은 것은 그 몫을 SHY 로(듀얼 모멘텀)
            base = _sma_rel("SHY", i)
            pick = _pick(_sma_rel, BAA_DEF, i, 3)
            if not pick:
                return {"SHY": 1.0}
            out = {}
            for t in pick:
                v = _sma_rel(t, i)
                k = t if (base is None or (v is not None and v >= base)) else "SHY"
                out[k] = out.get(k, 0.0) + 1.0 / len(pick)
            return out
        return w
    add("taa-baa-a", "", lambda: run_weights(
        _mk_baa(BAA_OFF_A, 1), first_common(BAA_CAN + BAA_OFF_A + BAA_DEF),
        "대담형 자산배분 BAA (공격형 · 1종 집중)", _bench_spy,
        "카나리아 4종(SPY·EFA·EEM·AGG)의 13612W 가 전부 양수면 공격 4종(QQQ·EEM·EFA·AGG) 중 "
        "SMA 상대모멘텀(p0÷12개월 평균) 최고 1종에 100%. 아니면 방어 7종 중 같은 척도 상위 3을 "
        "동일가중하되 SHY 보다 낮은 것은 그 몫을 SHY 로 돌린다.",
        "Keller(2022). 카나리아는 빠른 13612W, 선별은 느린 SMA 상대모멘텀 — 척도가 둘이다. "
        "빠른 것으로 위험을 끄고 느린 것으로 고른다는 설계다.",
        bench2_w=_bench6040, bench2_label="60/40 (SPY 60 · AGG 40)"))
    add("taa-baa-b", "", lambda: run_weights(
        _mk_baa(BAA_OFF_B, 6), first_common(BAA_CAN + BAA_OFF_B + BAA_DEF),
        "대담형 자산배분 BAA (균형형 · 6종 분산)", _bench_spy,
        "③과 같되 공격 유니버스가 11자산이고 SMA 상대모멘텀 상위 6종을 동일가중한다.",
        "원문은 12자산(VGK·EWJ 포함)인데 이 패널에 지역 분해가 없어 EFA 하나로 접었다 — "
        "그만큼 원문과 다른 규칙이다(등록 §2).",
        bench2_w=_bench6040, bench2_label="60/40 (SPY 60 · AGG 40)"))

    # ⑤ 허스트 국면 스위치 — R/S 통계량
    def _hurst(i, n=252):
        s = ser("SPY")
        if i < n:
            return None
        r = [s[j] / s[j - 1] - 1 for j in range(i - n + 1, i + 1)
             if s[j] is not None and s[j - 1]]
        if len(r) < n // 2:
            return None
        out = []
        for m in (16, 32, 64, 128):
            rs = []
            for k in range(0, len(r) - m + 1, m):
                w = r[k:k + m]
                mu = sum(w) / m
                dev, lo, hi, c = 0.0, 0.0, 0.0, 0.0
                for v in w:
                    c += v - mu
                    lo, hi = min(lo, c), max(hi, c)
                sd = math.sqrt(sum((v - mu) * (v - mu) for v in w) / max(1, m - 1))
                if sd > 0:
                    rs.append((hi - lo) / sd)
            if rs:
                out.append((math.log(m), math.log(sum(rs) / len(rs))))
        if len(out) < 3:
            return None
        mx = sum(x for x, _ in out) / len(out)
        my = sum(y for _, y in out) / len(out)
        num = sum((x - mx) * (y - my) for x, y in out)
        den = sum((x - mx) * (x - mx) for x, _ in out)
        return (num / den) if den > 0 else None

    def _regime_alloc(trend, i):
        if trend:
            sc = [(t, (ret(ser(t), i, 252) or None)) for t in TAA_UNI8]
            sc = [(t, v) for t, v in sc if v is not None]
            sc.sort(key=lambda x: -x[1])
        else:
            sc = [(t, (ret(ser(t), i, 21) or None)) for t in TAA_UNI8]
            sc = [(t, v) for t, v in sc if v is not None]
            sc.sort(key=lambda x: x[1])
        return {t: 0.5 for t, _ in sc[:2]} if len(sc) >= 2 else {"SHY": 1.0}
    add("st-hurst", "", lambda: run_weights(
        lambda i: _regime_alloc((_hurst(i) or 0.5) > 0.5, i),
        first_common(TAA_UNI8), "허스트 지수 국면 스위치 (추세 ↔ 반전)", _bench_spy,
        "월말에 SPY 일간수익 252일의 R/S 허스트 H 를 잰다. H>0.5 면 8자산 12개월 모멘텀 상위 2, "
        "H≤0.5 면 같은 8자산 직전 21일 수익 하위 2를 동일가중.",
        "허스트 H 는 계열이 추세적(H>0.5)인지 평균회귀적(H<0.5)인지를 재는 고전 통계량이다. "
        "국면을 거시로 판정하지 않고 가격 계열 자신의 성질로 가른다.",
        bench2_w=_bench6040, bench2_label="60/40 (SPY 60 · AGG 40)"))

    # ⑥ 분산비 — Lo·MacKinlay (1988) RFS 1(1)
    def _vratio(i, n=252, q=5):
        s = ser("SPY")
        if i < n:
            return None
        r = [s[j] / s[j - 1] - 1 for j in range(i - n + 1, i + 1)
             if s[j] is not None and s[j - 1]]
        if len(r) < n // 2:
            return None
        m1 = sum(r) / len(r)
        v1 = sum((x - m1) * (x - m1) for x in r) / max(1, len(r) - 1)
        agg = [sum(r[k:k + q]) for k in range(0, len(r) - q + 1, q)]
        if len(agg) < 5 or v1 <= 0:
            return None
        mq = sum(agg) / len(agg)
        vq = sum((x - mq) * (x - mq) for x in agg) / max(1, len(agg) - 1)
        return vq / (q * v1)
    add("st-vratio", "", lambda: run_weights(
        lambda i: _regime_alloc((_vratio(i) or 1.0) > 1.0, i),
        first_common(TAA_UNI8), "분산비(Lo-MacKinlay) 국면 스위치", _bench_spy,
        "월말에 SPY 252일 분산비 VR(5)=Var(5일수익)÷(5·Var(1일수익)) 을 잰다. VR>1 이면 추세 "
        "국면 배분, VR≤1 이면 반전 국면 배분. 배분 규칙은 허스트판과 글자 그대로 같다.",
        "Lo·MacKinlay(1988)의 분산비 검정. ⚠ 허스트판과 유니버스·배분이 같고 국면 통계량만 "
        "다르다 — 둘이 비슷하면 국면 통계량의 선택이 무의미하다는 뜻이고, 그것을 재려고 "
        "일부러 짝으로 넣었다.",
        bench2_w=_bench6040, bench2_label="60/40 (SPY 60 · AGG 40)"))

    # ⑦ OU 평균회귀 z-score
    def _ou(t, i, n=120):
        s = ser(t)
        if i < n or s[i] is None or s[i] <= 0:
            return None
        lg = [math.log(s[j]) for j in range(i - n + 1, i + 1) if s[j] and s[j] > 0]
        if len(lg) < n - 5:
            return None
        x = lg[:-1]
        dy = [lg[k + 1] - lg[k] for k in range(len(lg) - 1)]
        mx = sum(x) / len(x)
        my = sum(dy) / len(dy)
        den = sum((v - mx) * (v - mx) for v in x)
        if den <= 0:
            return None
        beta = sum((v - mx) * (d - my) for v, d in zip(x, dy)) / den
        k = 1.0 + beta
        if not (0 < k < 1):
            return None
        hl = -math.log(2) / math.log(k)
        mu = sum(lg) / len(lg)
        sd = math.sqrt(sum((v - mu) * (v - mu) for v in lg) / max(1, len(lg) - 1))
        if sd <= 0:
            return None
        return hl, (lg[-1] - mu) / sd

    def _w_ou(i):
        cand = []
        for t in TAA_UNI8:
            o = _ou(t, i)
            if o and 5 <= o[0] <= 120:
                cand.append((t, o[1]))
        if len(cand) < 2:
            return {"SHY": 1.0}
        cand.sort(key=lambda x: x[1])
        return {t: 0.5 for t, _ in cand[:2]}
    add("st-ou", "", lambda: run_weights(
        _w_ou, first_common(TAA_UNI8), "OU 평균회귀 z-score 하위 2", _bench_spy,
        "8자산 각각의 log가격에 120일 OU 과정을 적합해 반감기와 z-score 를 낸다. 반감기가 "
        "5~120일인 자산만 후보로 두고 z-score 가 가장 낮은 2종을 동일가중. 후보 2종 미만이면 SHY.",
        "평균회귀를 '싸 보인다'로만 쓰지 않고 회귀 속도(반감기)가 실제로 있는 자산만 "
        "후보로 둔다. 반감기 관문이 없으면 추세 자산의 눌림목을 평균회귀로 오인한다.",
        bench2_w=_bench6040, bench2_label="60/40 (SPY 60 · AGG 40)"))

    # ⑧ 축소 공분산 최소분산 — Ledoit·Wolf (2004) JMVA 88(2)
    def _w_minvar(i, n=252, delta=0.3):
        ts = [t for t in TAA_UNI8 if i >= n and ser(t)[i] is not None]
        R = {}
        for t in ts:
            s = ser(t)
            r = [s[j] / s[j - 1] - 1 if (s[j] is not None and s[j - 1]) else None
                 for j in range(i - n + 1, i + 1)]
            if sum(1 for v in r if v is not None) >= n - 10:
                R[t] = r
        ts = [t for t in ts if t in R]
        if len(ts) < 4:
            return {"SHY": 1.0}
        ok = [k for k in range(n) if all(R[t][k] is not None for t in ts)]
        if len(ok) < n // 2:
            return {"SHY": 1.0}
        mu = {t: sum(R[t][k] for k in ok) / len(ok) for t in ts}
        S = {}
        for a in ts:
            for b in ts:
                S[(a, b)] = sum((R[a][k] - mu[a]) * (R[b][k] - mu[b])
                                for k in ok) / max(1, len(ok) - 1)
        sd = {t: math.sqrt(S[(t, t)]) if S[(t, t)] > 0 else 0.0 for t in ts}
        cs = [S[(a, b)] / (sd[a] * sd[b]) for a in ts for b in ts
              if a != b and sd[a] > 0 and sd[b] > 0]
        rbar = sum(cs) / len(cs) if cs else 0.0
        # 상수상관 목표로 축소. δ 는 0.3 고정 — 최적 δ 추정은 자유도가 된다.
        C = {}
        for a in ts:
            for b in ts:
                f = S[(a, a)] if a == b else rbar * sd[a] * sd[b]
                C[(a, b)] = delta * f + (1 - delta) * S[(a, b)]
        # 롱온리 최소분산 — 역분산에서 출발해 반복 투영
        w = {t: (1.0 / C[(t, t)] if C[(t, t)] > 0 else 0.0) for t in ts}
        for _ in range(200):
            g = {a: sum(C[(a, b)] * w[b] for b in ts) for a in ts}
            gm = sum(g.values()) / len(ts)
            step = 0.5 / max(1e-12, max(C[(t, t)] for t in ts))
            w = {a: max(0.0, w[a] - step * (g[a] - gm)) for a in ts}
            tot = sum(w.values())
            if tot <= 0:
                return {"SHY": 1.0}
            w = {a: v / tot for a, v in w.items()}
        return {a: v for a, v in w.items() if v > 1e-4}
    add("st-minvar-lw", "", lambda: run_weights(
        _w_minvar, first_common(TAA_UNI8), "축소 공분산 최소분산 (Ledoit-Wolf 목표)", _bench_spy,
        "8자산 252일 표본공분산을 상수상관 목표로 δ=0.3 만큼 축소한 뒤 롱온리 최소분산 비중을 낸다.",
        "Ledoit·Wolf(2004). 표본공분산은 자산 수가 관측 대비 많아지면 불안정해지고 최소분산이 "
        "그 잡음을 극대화한다. ⚠ 최적 δ 를 추정하지 않고 0.3 으로 못박았다 — 추정하면 그게 자유도다.",
        bench2_w=_bench6040, bench2_label="60/40 (SPY 60 · AGG 40)"))

    # ⑨ 위험균형 × 개별 추세 게이트 (2단)
    def _w_rptrend(i):
        w, cash = {}, 0.0
        for t in TAA_UNI8:
            v = vol(ser(t), i, 120)
            if not v or v <= 0:
                continue
            iv = 1.0 / v
            s = ser(t)
            up = False
            if i >= 200 and s[i] is not None:
                win = [s[j] for j in range(i - 199, i + 1) if s[j] is not None]
                up = bool(win) and s[i] > sum(win) / len(win)
            if up:
                w[t] = iv
            else:
                cash += iv
        tot = sum(w.values()) + cash
        if tot <= 0:
            return {"SHY": 1.0}
        out = {t: v / tot for t, v in w.items()}
        if cash > 0:
            out["SHY"] = out.get("SHY", 0.0) + cash / tot
        return out
    add("st-rp-trend", "", lambda: run_weights(
        _w_rptrend, first_common(TAA_UNI8), "위험균형 × 개별 추세 게이트 (2단)", _bench_spy,
        "1단 8자산 120일 역변동성 가중. 2단 각 자산이 200일선 아래면 그 몫만 SHY 로 옮긴다.",
        "이 랩의 rp-* 계열은 게이트가 포트폴리오 전체에 하나 걸려 전량이 들락거린다. "
        "이쪽은 자산마다 따로 걸어 노출이 연속으로 변한다.",
        bench2_w=_bench6040, bench2_label="60/40 (SPY 60 · AGG 40)"))

    # ⑩ 능형회귀 1개월 예측 — 간단 ML(확장창)
    def _w_ridge(i, lam=1.0):
        me = month_ends(0, i + 1)
        if len(me) < 60:
            return {"SHY": 1.0}
        rows, ys = [], []
        for k in range(len(me) - 1):
            a = me[k]
            f = _ridge_feat(a)
            if f is None:
                continue
            s = ser("SPY")
            b = me[k + 1]
            if s[a] and s[b]:
                rows.append(f)
                ys.append(s[b] / s[a] - 1)
        cur = _ridge_feat(i)
        if len(rows) < 48 or cur is None:
            return {"SHY": 1.0}
        p = len(cur)
        mu = [sum(r[j] for r in rows) / len(rows) for j in range(p)]
        sg = [math.sqrt(sum((r[j] - mu[j]) ** 2 for r in rows) / max(1, len(rows) - 1))
              or 1e-9 for j in range(p)]
        X = [[(r[j] - mu[j]) / sg[j] for j in range(p)] for r in rows]
        ym = sum(ys) / len(ys)
        Y = [v - ym for v in ys]
        # (XᵀX + λI) β = XᵀY — 가우스 소거
        A_ = [[sum(X[k][a] * X[k][b] for k in range(len(X))) + (lam if a == b else 0.0)
               for b in range(p)] + [sum(X[k][a] * Y[k] for k in range(len(X)))]
              for a in range(p)]
        for c in range(p):
            pv = max(range(c, p), key=lambda r_: abs(A_[r_][c]))
            if abs(A_[pv][c]) < 1e-12:
                return {"SHY": 1.0}
            A_[c], A_[pv] = A_[pv], A_[c]
            for r_ in range(p):
                if r_ != c:
                    f = A_[r_][c] / A_[c][c]
                    for cc in range(c, p + 1):
                        A_[r_][cc] -= f * A_[c][cc]
        beta = [A_[j][p] / A_[j][j] for j in range(p)]
        z = [(cur[j] - mu[j]) / sg[j] for j in range(p)]
        pred = ym + sum(beta[j] * z[j] for j in range(p))
        return {"SPY": 1.0} if pred > 0 else {"SHY": 1.0}

    def _ridge_feat(i):
        m12 = ret(ser("SPY"), i, 252)
        v60 = vol(ser("SPY"), i, 60)
        ts_ = macro_asof("T10Y2Y", DTS[i])
        vx = A["macro"].get("VIXCLS") or {}
        ks = [k for k in sorted(vx) if k <= DTS[i]][-20:]
        vv = [vx[k] for k in ks if vx[k] is not None]
        if m12 is None or v60 is None or ts_ is None or not vv:
            return None
        return [m12, v60, ts_, sum(vv) / len(vv)]
    add("ml-ridge", "", lambda: run_weights(
        _w_ridge, first_common(["SPY", "SHY"], pad=1600), "능형회귀 1개월 예측 (SPY 롱/현금)",
        _bench_spy,
        "특징 4개(SPY 12개월 모멘텀·60일 실현변동성·T10Y2Y·VIX 20일평균)로 SPY 다음 달 수익을 "
        "확장창 능형회귀(λ=1.0 고정, 표준화)로 예측한다. 예측이 양수면 SPY 100%, 아니면 SHY 100%.",
        "요청대로 가벼운 ML 이다. ⚠ 확장창이다 — 매 월말 그 시점까지의 관측만으로 다시 적합한다. "
        "⚠ λ 를 교차검증으로 고르지 않는다(고르면 그게 자유도다). 이 랩은 ML 랩을 한 번 삭제한 "
        "적이 있고(DATA-FACTS #17) 그 사유는 55분을 써서 얻는 것이 없었다는 것이다.",
        bench2_w=_bench6040, bench2_label="60/40 (SPY 60 · AGG 40)"))

    # ⑩ 핼러윈 — Jacobsen·Visaltanachoti (2009) RFS 22(1)
    _sec("sec-halloween", "핼러윈 섹터 (11~4월 경기민감)",
         lambda i: {t: 1.0 for t in (CYC6 if DTS[i][5:7] in
                    ("11", "12", "01", "02", "03", "04") else DEF3)},
         "11~4월에는 경기민감 6섹터, 5~10월에는 방어 3섹터를 동일가중. 월말 전환.",
         "Jacobsen·Visaltanachoti(2009)는 핼러윈 효과가 경기민감 섹터에 몰려 있다고 보고한다. "
         "신호에 가격이 전혀 안 들어간다 — 달력만 본다.")

    # ── 달러 축: 미국 vs 해외 선진 (사전등록 PREREG-2026-08-06-USDAXIS.md) ──
    # 🚨 이 축을 여기로 데려온 근거는 **아카이브 기각문 둘**이다. 서로 독립인데 같은 것을
    #   지목했다 — HRP: "정체가 배분 알고리즘이 아니라 UUP 평균 24.9% 배분이며 UUP 를 빼면
    #   ΔSharpe 가 +0.057 → −0.136 으로 부호가 반전한다" · 최소분산: "정체는 최적화가 아니라
    #   UUP 평균 30.2% 배분". 그런데 **그 달러를 살 티커가 패널에 없었다.**
    #   2026-08-06 에 UUP·UDN 을 넣었다(2007-03~ · 4,888관측). 통화 축이 이 랩에 처음 든다.
    # ⚠ 이 랩에서 죽은 재구성 12건은 전부 "원판이 incr5 이웃 1번으로 들어와" 죽었다.
    #   통화 축에는 원판이 없다는 것이 이 등록의 유일한 근거다 — 그래서 ③ incr5 가 본 검정이다.
    def s_usd_axis():
        ts = ["SPY", "EFA", "UUP"]
        st = first_common(ts, pad=200)          # UUP 2007-03 + 200일 워밍업
        if "UUP" not in A["px"]:
            return None
        uup = A["px"]["UUP"]
        def w(i):
            m = sma(uup, i, 200)
            if m is None or not uup[i]:
                return {"SPY": 1.0}             # 신호를 못 재면 기본값(미국)
            return {"SPY": 1.0} if uup[i] > m else {"EFA": 1.0}
        return run_weights(
            w, st, "달러 축 — 미국 vs 해외 선진",
            lambda i: {"^GSPC": 1.0},
            "달러 ETF(UUP) 종가가 200일 단순이동평균 위면 SPY 100%, 아래면 EFA 100%. "
            "월말 판정 · 신호가 바뀐 달에만 교체 · 히스테리시스 없음.",
            "달러 강세는 해외 자산의 달러환산 수익을 깎고 달러부채를 진 해외 기업의 조달을 "
            "조인다 — 달러가 오를 때 미국이, 내릴 때 해외가 상대우위라는 관계가 널리 "
            "문서화돼 있다. 이 랩의 기각문 둘(HRP·최소분산)이 '성과의 정체는 UUP 배분'이라고 "
            "적고도 통화 티커가 패널에 없어 그 축을 직접 잰 적이 없다. 처음 잰다.",
            note="자유도를 0 으로 고정했다 — 200일선은 이 저장소가 이미 쓰는 값이고(창을 새로 "
                 "고르면 자유도가 생긴다), EEM 대신 EFA 는 신흥국의 원자재·중국 요인이 달러 축을 "
                 "오염시키기 때문이다. 둘 다 결과와 무관한 사유다. UDN 은 UUP 의 거울상이라 "
                 "규칙에 안 쓴다. ⚠ 대조군 지수는 '달러 신호가 값을 하는가'와 'EFA 가 미국을 "
                 "이기는가'를 섞는다 — SPY/EFA 50:50 대비를 진단으로 병기한다(판정에는 안 쓴다).")
    add("usd-us-intl", "usd-axis-rotation", s_usd_axis)

    # ── 퀄리티 롱숏(ETF 프록시) ──
    def s_quality():
        ts = ["QUAL", "SIZE", "SPY"]
        st = first_common(ts, pad=20)
        return run_weights(lambda i: {"QUAL": 1.0}, st,
                           "퀄리티 틸트 (QUAL, ETF 프록시)",
                           lambda i: {"^GSPC": 1.0},
                           "QUAL(퀄리티 팩터 ETF)을 보유. 대조군은 S&P 500(PR).",
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
        # 🚨 10년 상한(MAX_YEARS). 이 경로만 격자가 **월말 문자열**이라 인덱스로 못 자른다 —
        #   개월 수로 자른다. run_weights 를 안 지나므로 여기서 따로 걸어야 한다.
        months = months[-int(MAX_YEARS * 12):] if len(months) > int(MAX_YEARS * 12) else months
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
        ms, mo = mstats(a_, nav), mstats(b_, bn)
        # 🚨 판정선은 지수(PR)다. 이 결합은 EPS 리비전(NDX 유니버스) + 크로스에셋 RP 라
        #   배포 원장의 Multi-Sleeve Core 와 같은 NASDAQ 100(PR)을 쓴다.
        #   종전 대조군 '배포 슬리브 둘 50:50 고정'은 버리지 않고 보조로 내린다 —
        #   이 랩의 원래 질문("가중을 굴린 것이 반반 고정보다 나은가")을 재는 유일한 대조군이다.
        # ⚠ 지수를 못 만들면 **판정선을 바꾸지 않는다.** 조용히 반반 고정으로 되돌아가는 것이
        #   아니라, 되돌아갔다는 사실을 라벨이 그대로 말한다(아래 _ilab).
        _ir = idx_monthly("^NDX", months)
        if _ir:
            inav = [100.0]
            for r in _ir:
                inav.append(inav[-1] * (1 + r))
            mb, b_cmp, bnav_out = mstats(_ir, inav), _ir, inav
            # ⚠ t 를 반드시 싣는다. 화면(explorer '판정 축')은 b2.t 가 있어야 보조 칸을
            #   그린다 — 없으면 내려놓은 원래 질문이 화면에서 통째로 사라진다.
            _d2 = [x - y for x, y in zip(a_, b_)]
            _mu2 = sum(_d2) / len(_d2)
            _sd2 = math.sqrt(sum((v - _mu2) ** 2 for v in _d2) / max(1, len(_d2) - 1))
            _ilab, _b2 = "NASDAQ 100(PR) 매수후보유", {
                "label": "배포 슬리브 둘 50:50 고정", "metrics": mo,
                "d_sharpe": round((ms.get("sharpe") or 0) - (mo.get("sharpe") or 0), 3),
                "t": round(_mu2 / (_sd2 / math.sqrt(len(_d2))), 2) if _sd2 > 0 else None}
        else:
            print("  ⚠ %s — ^NDX 월간 계열을 못 만들었다. 판정선을 반반 고정으로 둔다." % name)
            mb, b_cmp, bnav_out = mo, b_, bn
            _ilab, _b2 = "배포 슬리브 둘 50:50 고정", None
        d = [x - y for x, y in zip(a_, b_cmp)]
        mu = sum(d) / len(d)
        sd = math.sqrt(sum((v - mu) ** 2 for v in d) / max(1, len(d) - 1))
        step = max(1, len(nav) // 220)
        we_, wr_ = wfn(len(months) - 1, months, rs)
        return {"name": name, "rule": rule, "why": why, "note": note,
                # 이쪽 격자는 월말("YYYY-MM")이다 — load_index_tr 가 그 형식을 알아본다.
                "chart": curve_pack(months, nav, bnav_out, idx_rets=load_index_tr(months)),
                "holdings": {"kind": "sleeve", "as_of": months[-1],
                             "weights": [("EPS 리비전 드리프트", round(we_ * 100, 1)),
                                         ("크로스에셋 리스크패리티", round(wr_ * 100, 1))],
                             "note": "배포 슬리브 둘의 현재 배분이다."},
                "start": months[0], "end": months[-1], "n_days": len(months),
                "metrics": ms, "bench": mb, "bench_unstable": False,
                "bench_label": _ilab,
                **({"bench2": _b2} if _b2 else {}),
                "d_sharpe": round((ms.get("sharpe") or 0) - (mb.get("sharpe") or 0), 3),
                "t": round(mu / (sd / math.sqrt(len(d))), 2) if sd > 0 else None,
                "turnover": None, "monthly": True,
                # 🚨 2026-08-05 추가. 증분 알파(incr/incr5)는 **날짜 정합** 회귀라 dates 가 없으면
                #   아예 못 돈다. 종전에는 nav·bnav 만 실어 이 랩들이 그 검정을 한 번도 못 받았다.
                "dates": (_gt := gthin(months, nav, bnav_out))[0],
                "nav": _gt[1],
                "bnav": _gt[2]}

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
            # 🚨 분모는 **실제 주가**여야 한다(ser_true). 종전에는 배당조정가로 나눠서
            #   같은 분배금이 과거일수록 크게 보였고, 그 부풂이 자산마다 달라 횡단면 순위
            #   자체가 캐리가 아니라 누적 조정배수로도 만들어졌다(ser_true 독스트링 실측).
            s_ = ser_true(t)
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

    # ── 고전 타이밍 규칙 ────────────────────────────────────────────────
    # 왜 이제 넣나. 이 랩에는 타이밍오버레이가 이미 여럿 있지만 **가장 유명한 것들이 통째로
    # 빠져 있었다** — 200일선·골든크로스·단일자산 절대모멘텀·계절성·장단기금리차·VIX 게이트.
    # 사람들이 실제로 입에 올리는 규칙이 목록에 없으면 "그건 안 해 봤잖아"라는 말을 못 막는다.
    # 판정이 어떻게 나오든 목록에 있는 것 자체가 답이 된다.
    #
    # 대조군은 전부 **S&P 500(PR) 매수후보유**다. 이 규칙들은 '무엇을 살까'가 아니라
    # '언제 들어가 있을까'만 정한다 — 정당한 귀무가설은 '그냥 계속 들고 있기'다.
    # 🚨 2026-08-13 이전에는 대조군이 SPY 였고, 그때는 여기에 "전략도 대조군도 같은 SPY 계열이라
    #   TR/PR 표기 차이가 양쪽에서 상쇄된다"고 적혀 있었다. **그 상쇄가 이제 없다.**
    #   전략은 여전히 SPY 조정종가(TR)를 사는데 대조군만 배당 없는 지수(PR)가 됐다 —
    #   대조군이 연 2.00%p 불리하다. 이 랩 35종 중 13종이 그 한 가지 때문에 CAGR 열세에서
    #   우위로 바뀐다. 사용자 결정이고, 화면이 카드마다 그 사실을 적는 것으로 갚는다.
    #
    # 대피처는 SHY(단기국채)로 통일했다. 현금 0%로 두면 '이탈'이 곧 무수익이 되어, 규칙의
    # 값어치가 아니라 그 시기 단기금리의 값어치가 섞여 든다.
    SAFE = "SHY"

    def _gate(sid, arch, label, sigfn, rule, why, note=None, pad=210):
        """SPY ↔ SHY 사이만 오가는 게이트. sigfn(i) -> True 면 위험선호."""
        ts = ["SPY", SAFE]
        st = first_common(ts, pad=pad)

        def w(i):
            try:
                on = sigfn(i)
            except Exception:
                on = True                       # 신호를 못 내면 '가만히 있기'가 기본값이다
            return {"SPY": 1.0} if on is not False else {SAFE: 1.0}
        add(sid, arch, lambda: run_weights(w, st, label, lambda i: {"^GSPC": 1.0},
                                           rule, why, note))

    # 1) 200일 이동평균 — Faber(2007)의 그 규칙
    _gate("sma200", None, "200일 이동평균 (Faber)",
          lambda i: (lambda s, m: None if m is None or s[i] is None else s[i] > m)(
              ser("SPY"), sma(ser("SPY"), i, 200)),
          "월말에 SPY 종가가 200일 단순이동평균 위면 SPY 100%, 아래면 SHY 100%.",
          "가장 널리 인용되는 타이밍 규칙인데 이 랩 목록에 없었다. 원논문의 주장은 "
          "'수익은 비슷하고 낙폭이 준다'이지 '더 번다'가 아니다 — 그래서 CAGR 이 아니라 "
          "MDD·샤프를 같이 봐야 한다.",
          pad=210)

    # 2) 골든크로스 — 50/200 교차
    _gate("golden-cross", None, "골든크로스 (50/200)",
          lambda i: (lambda a, b: None if a is None or b is None else a > b)(
              sma(ser("SPY"), i, 50), sma(ser("SPY"), i, 200)),
          "월말에 SPY 50일 이동평균이 200일 이동평균 위면 SPY, 아래면 SHY.",
          "200일선과 같은 재료(가격)를 쓰지만 신호가 더 늦다. 둘을 같이 실어야 "
          "'교차가 종가보다 나은가'를 비교할 수 있다.",
          pad=210)

    # 3) 절대 모멘텀 — 단일자산 12-1
    _gate("abs-mom", None, "절대 모멘텀 (SPY 12-1)",
          lambda i: (lambda r12, r1: None if r12 is None or r1 is None else (r12 - r1) > 0)(
              ret(ser("SPY"), i, 252), ret(ser("SPY"), i, 21)),
          "월말에 SPY 의 최근 1개월을 뺀 12개월 수익률이 양수면 SPY, 아니면 SHY.",
          "기존 tsmom-multi·gem 은 여러 자산을 함께 고르는 규칙이라 '타이밍'과 '종목선택'이 "
          "섞여 있다. 단일자산으로 두면 타이밍 그 자체만 남는다.",
          pad=285)

    # 4) 계절성 — Sell in May
    _gate("seasonal", None, "계절성 (11~4월만 보유)",
          lambda i: int(DTS[i][5:7]) % 12 + 1 in (11, 12, 1, 2, 3, 4),
          "월말에 다음 달이 11~4월이면 SPY, 5~10월이면 SHY.",
          "달력만 보고 매매하는 규칙이라 경제적 근거가 가장 약하다. 데이터 마이닝 의심이 "
          "제일 큰 축이므로, 통과하더라도 그 사실을 먼저 적어야 한다. 여기 싣는 이유는 "
          "'해 보지 않았다'는 말을 없애기 위해서다.",
          pad=25)

    # 5) 장단기금리차 역전 게이트
    _gate("curve-inv", None, "수익률곡선 역전 게이트",
          lambda i: (lambda v: None if v is None else v >= 0)(macro_asof("T10Y2Y", DTS[i])),
          "월말에 10년-2년 스프레드가 음수(역전)면 SHY, 아니면 SPY.",
          "역전은 침체를 12~18개월 선행한다. 신호 즉시 이탈하면 남은 강세장을 통째로 "
          "버리게 된다 — 그 대가가 숫자로 얼마인지 재는 것이 이 줄의 목적이다.",
          pad=25)

    # 6) VIX 절대수준 게이트
    _gate("vix-level", None, "VIX 수준 게이트 (25)",
          lambda i: (lambda v: None if v is None else v < 25.0)(
              (ser("^VIX") or [None])[i] if ser("^VIX") else None),
          "월말 VIX 종가가 25 미만이면 SPY, 이상이면 SHY.",
          "기존 vix-ts 는 기간구조(콘탱고/백워데이션)를 보고, 이쪽은 절대수준만 본다. "
          "문턱 25 는 흔히 쓰는 값이라 그대로 뒀다 — 최적화하면 그 순간 과최적합이 된다.",
          pad=25)

    # 7) 실업률 추세 — Sahm 계열
    def _sahm(i):
        h = macro_asof_m("UNRATE", DTS[i], 21, 15)      # 관측월 말 + 21일 후에야 볼 수 있다
        if len(h) < 15:
            return None
        ma3 = [sum(h[k - 2:k + 1]) / 3 for k in range(2, len(h))]
        return (ma3[-1] - min(ma3[-13:-1])) < 0.5
    _gate("unrate-trend", None, "실업률 추세 게이트 (Sahm)",
          _sahm,
          "월말에 실업률 3개월 평균이 직전 12개월 최저보다 0.5%p 이상 높으면 SHY, 아니면 SPY.",
          "실업률은 월간이고 관측월이 끝난 뒤에야 발표된다 — 발표 시차 21일을 넣어 "
          "그날 실제로 알 수 있던 값만 쓴다. 시차를 안 넣으면 없던 정보로 매매하게 된다.",
          pad=25)

    # 8) 다수결 앙상블 — 규칙 셋의 합의
    def s_ens():
        ts = ["SPY", SAFE, "^VIX"]
        st = first_common(ts, pad=285)
        def votes(i):
            s = ser("SPY")
            v = []
            m = sma(s, i, 200)
            v.append(None if (m is None or s[i] is None) else s[i] > m)
            r12, r1 = ret(s, i, 252), ret(s, i, 21)
            v.append(None if (r12 is None or r1 is None) else (r12 - r1) > 0)
            vx = (ser("^VIX") or [None])[i] if ser("^VIX") else None
            v.append(None if vx is None else vx < 25.0)
            return [x for x in v if x is not None]
        def w(i):
            v = votes(i)
            if not v:
                return {"SPY": 1.0}
            k = sum(1 for x in v if x) / len(v)          # 찬성 비율만큼만 노출
            return {"SPY": k, SAFE: 1.0 - k} if 0 < k < 1 else ({"SPY": 1.0} if k else {SAFE: 1.0})
        return run_weights(w, st, "타이밍 3규칙 다수결", lambda i: {"^GSPC": 1.0},
                           "200일선·절대모멘텀·VIX 게이트 셋의 찬성 비율만큼 SPY 를 들고 "
                           "나머지는 SHY. 셋 다 찬성이면 100%, 하나면 33%.",
                           "'규칙 하나하나는 약해도 합치면 낫다'는 흔한 주장을 그대로 검정한다. "
                           "세 규칙이 같은 자산의 같은 가격을 보므로 신호가 크게 겹친다 — "
                           "분산 효과를 기대할 자리가 아니라는 것이 사전 예상이다.")
    add("timing-ensemble", None, s_ens)

    # ── 타이밍 규칙에 흔히 따라붙는 반론들 ──────────────────────────────
    # 앞 아홉이 '유명한 규칙을 목록에 올린다'였다면, 여기 다섯은 그 규칙들에 늘 따라붙는
    # 반론을 하나씩 검정한다. 각 줄이 답하는 질문을 note 에 적어 둔다.

    # 9) 이동평균 기간을 바꾸면? — '200이 특별한가'
    def s_smagrid():
        ts = ["SPY", SAFE]
        st = first_common(ts, pad=270)
        LOOK = (100, 150, 200, 250)
        def w(i):
            s = ser("SPY")
            v = [s[i] > m for n_ in LOOK for m in [sma(s, i, n_)]
                 if m is not None and s[i] is not None]
            if not v:
                return {"SPY": 1.0}
            k = sum(v) / len(v)
            return {"SPY": k, SAFE: 1.0 - k} if 0 < k < 1 else ({"SPY": 1.0} if k else {SAFE: 1.0})
        return run_weights(w, st, "이동평균 기간 앙상블 (100·150·200·250)",
                           lambda i: {"^GSPC": 1.0},
                           "네 기간의 이동평균 신호 중 찬성 비율만큼 SPY 를 들고 나머지는 SHY.",
                           "200일이라는 숫자가 특별한지 묻는 줄이다. 네 기간을 고르게 섞은 것이 "
                           "200일 단독과 비슷하면 '200'은 규칙이 아니라 관습이라는 뜻이고, "
                           "크게 나쁘면 그 숫자가 표본에 맞춰진 것이라는 뜻이 된다.")
    add("sma-grid", None, s_smagrid)

    # 10) 확인 지연 — '휩쏘가 문제 아닌가'
    def _confirm_state(nday=5):
        """200일선 신호가 nday 거래일 연속 같아야 실제로 갈아탄다."""
        s = ser("SPY")
        on, run_, last, stt = True, 0, None, []
        for i in range(len(DTS)):
            m = sma(s, i, 200)
            cur = None if (m is None or s is None or s[i] is None) else (s[i] > m)
            if cur is None:
                stt.append(on); continue
            if cur == last:
                run_ += 1
            else:
                run_, last = 1, cur
            if run_ >= nday:
                on = cur
            stt.append(on)
        return stt
    _CF = None

    def s_confirm():
        nonlocal _CF
        _CF = _confirm_state()
        ts = ["SPY", SAFE]
        st = first_common(ts, pad=215)
        def w(i):
            return {"SPY": 1.0} if _CF[i] else {SAFE: 1.0}
        return run_weights(w, st, "200일선 + 확인 지연 5일",
                           lambda i: {"^GSPC": 1.0},
                           "200일선 신호가 5거래일 연속 같은 방향일 때만 갈아탄다.",
                           "이동평균 규칙에 늘 따라붙는 반론이 '경계에서 들락거려 비용만 "
                           "든다'는 것이다. 확인 지연을 넣으면 회전이 줄어드는 대신 신호가 "
                           "늦는다 — 어느 쪽이 큰지 sma200 줄과 나란히 놓고 본다.")
    add("sma200-confirm", None, s_confirm)

    # 11) 자산 간 상대 모멘텀 — '나갈 곳을 현금 말고 딴 자산으로 두면?'
    def s_relmom():
        ts = ["SPY", "TLT", "GLD", SAFE]
        st = first_common(ts, pad=285)
        def w(i):
            sc = {}
            for t in ("SPY", "TLT", "GLD"):
                r12, r1 = ret(ser(t), i, 252), ret(ser(t), i, 21)
                if r12 is not None and r1 is not None:
                    sc[t] = r12 - r1
            pos = {t: v for t, v in sc.items() if v > 0}
            if not pos:
                return {SAFE: 1.0}
            return {max(pos, key=pos.get): 1.0}
        return run_weights(w, st, "3자산 상대 모멘텀 (SPY·TLT·GLD)",
                           lambda i: {"SPY": 1 / 3, "TLT": 1 / 3, "GLD": 1 / 3},
                           "월말에 SPY·TLT·GLD 중 12-1 모멘텀이 가장 큰 하나만 보유. "
                           "셋 다 음수면 SHY.",
                           "앞의 게이트들은 나가면 전부 단기채로 갔다. 나갈 곳을 채권·금으로 "
                           "두면 달라지는지 본다. 대조군은 SPY 가 아니라 같은 세 자산 "
                           "동일가중이다 — 고르는 행위가 그냥 셋 다 들기를 이기는지가 질문이므로.")
    add("rel-mom3", None, s_relmom)

    # ── 달력·구조 계열 ────────────────────────────────────────────────
    # 여기까지는 전부 가격이나 거시를 봤다. 이 셋은 **아무 것도 안 본다** — 날짜만 본다.
    # 팩터(가치·모멘텀·퀄리티…)와 계보가 아예 다른 계열이라 목록에 하나도 없었다.
    # 문헌은 오래됐고 인용도 많은데, 그래서 더 '지금도 되나'를 물어야 하는 쪽이다.
    #
    # ⚠ 셋 다 일간 리밸런스다. 회전이 앞의 월말 규칙들과 자릿수가 다르므로 무비용(gross)
    #   숫자를 그대로 읽으면 안 된다 — 회전 칸을 반드시 같이 볼 것.
    def _day_gate(sid, label, flagfn, rule, why, note=None, st_min=None):
        ts = ["SPY", SAFE]
        st = first_common(ts, pad=25)
        if st_min:
            st = max(st, next((i for i, d in enumerate(DTS) if d >= st_min), len(DTS) - 1))
        fl = flagfn()
        n_ = len(DTS)
        def w(i):
            # run_weights 는 fn(i-1) 의 가중으로 i 일 수익을 낸다 — 하루 뒤 상태를 봐야 한다.
            j = min(i + 1, n_ - 1)
            return {"SPY": 1.0} if fl[j] else {SAFE: 1.0}
        add(sid, None, lambda: run_weights(w, st, label, lambda i: {"^GSPC": 1.0},
                                           rule, why, note, cadence="day"))

    # 12) 월말 효과 — Ariel(1987) · Lakonishok & Smidt(1988)
    def _tom_flags(lo=-1, hi=3):
        n_ = len(DTS)
        me = [i for i in range(n_ - 1) if DTS[i][:7] != DTS[i + 1][:7]] + [n_ - 1]
        f = [False] * n_
        for e in me:
            for k in range(lo, hi + 1):
                if 0 <= e + k < n_:
                    f[e + k] = True
        return f
    _day_gate("tom", "월말 효과 (마지막날 −1 ~ +3)", _tom_flags,
              "월 마지막 거래일 하루 전부터 다음 달 세 번째 거래일까지만 SPY, 나머지 기간은 SHY.",
              "달력만 보는 규칙이다. 월말·월초에 수익이 몰린다는 보고가 1980년대부터 있었고 "
              "연금 납입과 월말 리밸런스 자금이 이유로 거론된다. 한 해 거래일의 약 4분의 1만 "
              "시장에 있으므로, 그 기간이 정말 특별한지가 질문이다.",
              "실측 — 거래일의 23.8%만 시장에 있으면서 연 4.68%를 냈다. 노출 시간만으로 환산하면 "
              "연 21.2%로 상시보유 11.0%의 두 배 가까이다. 월말 닷새가 나머지보다 확실히 "
              "생산적이라는 뜻이다. 다만 연 24회 왕복이다 — 왕복 5bp를 물리면 연 1.25%p가 "
              "깎여 CAGR 4.68% → 3.43%, 샤프는 0.14 → 0.01 로 사실상 0이 된다. "
              "노출당 환산이 커 보이는 것과 실제로 손에 남는 것은 다른 얘기다.")

    # 13) 옵션 만기 주간 — 세 번째 금요일이 낀 주
    def _opex_flags():
        n_ = len(DTS)
        third = {}
        for d in DTS:
            y, m = int(d[:4]), int(d[5:7])
            if (y, m) not in third:
                first = dt.date(y, m, 1)
                third[(y, m)] = first + dt.timedelta(days=(4 - first.weekday()) % 7 + 14)
        f = [False] * n_
        for i, d in enumerate(DTS):
            dd = dt.date.fromisoformat(d)
            fr = third[(dd.year, dd.month)]
            f[i] = (dd - dt.timedelta(days=dd.weekday())) == (fr - dt.timedelta(days=fr.weekday()))
        return f
    _day_gate("opex", "옵션 만기 주간", _opex_flags,
              "매월 세 번째 금요일이 포함된 주(월~금)만 SPY, 나머지는 SHY.",
              "만기 주간에는 델타 헤지 청산과 롤이 겹쳐 수급이 한쪽으로 쏠린다는 관찰이 있다. "
              "가격도 재무도 안 보고 달력만 보는 규칙이라, 되면 구조적 수급이 남아 있다는 뜻이고 "
              "안 되면 그 이야기가 이미 가격에 들어갔다는 뜻이다.",
              "실측 — 노출 23.4%에 연 2.98%. 노출당 환산 13.4%로 상시보유 11.0%보다 조금 나은 "
              "정도다. 월말 효과(노출당 21.2%)와 견주면 만기 주간 쪽은 약하다. 회전은 똑같이 "
              "연 24회이고, 왕복 5bp를 물리면 연 1.23%p가 깎여 CAGR 2.98% → 1.75%, "
              "샤프는 이미 음수(-0.03)에서 -0.16 으로 더 내려간다. 남는 것이 없다.")

    # 14) FOMC 사이클 짝수 주 — Cieslak·Morse·Vissing-Jorgensen (Journal of Finance 2019)
    #   출처 연준 공개 달력(발표일 기준). 2021~ 은 fomccalendars.htm, 2006~2020 은 연도별
    #        과거 페이지 fomchistorical<연도>.htm 에서 옮겼다.
    #   ⚠ **정기 회의만** 담는다. 비정기 전화회의(2008년 6회 · 2020년 3월 등)는 뺐다 —
    #     원논문의 사이클 시계가 정기 8회 일정으로 도는 것이기 때문이다. 비정기는 위기 대응이라
    #     날짜가 시장 급변 자체에 붙어 있어, 넣으면 사이클이 아니라 위기를 재게 된다.
    #   ⚠ 2020년은 7회다. 3월 17~18일 정기 회의가 취소되고 3월 15일 긴급 조치로 대체됐다.
    FOMC = ["2006-01-31", "2006-03-28", "2006-05-10", "2006-06-29", "2006-08-08",
            "2006-09-20", "2006-10-25", "2006-12-12",
            "2007-01-31", "2007-03-21", "2007-05-09", "2007-06-28", "2007-08-07",
            "2007-09-18", "2007-10-31", "2007-12-11",
            "2008-01-30", "2008-03-18", "2008-04-30", "2008-06-25", "2008-08-05",
            "2008-09-16", "2008-10-29", "2008-12-16",
            "2009-01-28", "2009-03-18", "2009-04-29", "2009-06-24", "2009-08-12",
            "2009-09-23", "2009-11-04", "2009-12-16",
            "2010-01-27", "2010-03-16", "2010-04-28", "2010-06-23", "2010-08-10",
            "2010-09-21", "2010-11-03", "2010-12-14",
            "2011-01-26", "2011-03-15", "2011-04-27", "2011-06-22", "2011-08-09",
            "2011-09-21", "2011-11-02", "2011-12-13",
            "2012-01-25", "2012-03-13", "2012-04-25", "2012-06-20", "2012-08-01",
            "2012-09-13", "2012-10-24", "2012-12-12",
            "2013-01-30", "2013-03-20", "2013-05-01", "2013-06-19", "2013-07-31",
            "2013-09-18", "2013-10-30", "2013-12-18",
            "2014-01-29", "2014-03-19", "2014-04-30", "2014-06-18", "2014-07-30",
            "2014-09-17", "2014-10-29", "2014-12-17",
            "2015-01-28", "2015-03-18", "2015-04-29", "2015-06-17", "2015-07-29",
            "2015-09-17", "2015-10-28", "2015-12-16",
            "2016-01-27", "2016-03-16", "2016-04-27", "2016-06-15", "2016-07-27",
            "2016-09-21", "2016-11-02", "2016-12-14",
            "2017-02-01", "2017-03-15", "2017-05-03", "2017-06-14", "2017-07-26",
            "2017-09-20", "2017-11-01", "2017-12-13",
            "2018-01-31", "2018-03-21", "2018-05-02", "2018-06-13", "2018-08-01",
            "2018-09-26", "2018-11-08", "2018-12-19",
            "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19", "2019-07-31",
            "2019-09-18", "2019-10-30", "2019-12-11",
            "2020-01-29", "2020-04-29", "2020-06-10", "2020-07-29", "2020-09-16",
            "2020-11-05", "2020-12-16",
            "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16", "2021-07-28",
            "2021-09-22", "2021-11-03", "2021-12-15",
            "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15", "2022-07-27",
            "2022-09-21", "2022-11-02", "2022-12-14",
            "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14", "2023-07-26",
            "2023-09-20", "2023-11-01", "2023-12-13",
            "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31",
            "2024-09-18", "2024-11-07", "2024-12-18",
            "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30",
            "2025-09-17", "2025-10-29", "2025-12-10",
            "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29"]

    def _fomc_flags():
        ds = sorted(dt.date.fromisoformat(x) for x in FOMC)
        f = [False] * len(DTS)
        for i, d in enumerate(DTS):
            dd = dt.date.fromisoformat(d)
            prev = None
            for x in ds:
                if x - dt.timedelta(days=1) <= dd:
                    prev = x
                else:
                    break
            if prev is None:
                continue
            # 사이클 시간의 0일은 발표 **전날**이다(원논문 정의). 짝수 주 0·2·4·6 이 위험선호.
            f[i] = (((dd - (prev - dt.timedelta(days=1))).days // 7) % 2 == 0)
        return f
    _day_gate("fomc-even", "FOMC 사이클 짝수 주", _fomc_flags,
              "직전 FOMC 발표 전날을 0일로 두고 짝수 주(0·2·4·6주차)에만 SPY, 홀수 주는 SHY.",
              "주식 위험프리미엄이 FOMC 사이클의 짝수 주에 몰려 있다는 보고다(Journal of "
              "Finance 2019). 연준의 비공식 소통 경로가 이유로 거론된다. 발표된 지 오래된 "
              "규칙이라 지금도 남아 있는지가 질문이다.",
              "실측(2006~ · 정기회의 164회) — 시간의 52.8%만 시장에 있으면서 연 9.28%. "
              "노출 시간으로 환산하면 18.3%로 상시보유 11.0%를 크게 웃돈다. 짝수 주가 홀수 주보다 "
              "확실히 생산적이라는 원 보고가 20년 구간에서 재현된다. 낙폭도 -22.7%로 절반 아래다"
              "(상시보유 -55.2%). 처음 넣을 때 쓰던 2021년 이후 구간에서도 노출당 20.2%로 "
              "같은 방향이었다 — 최근에만 나는 현상이 아니다. "
              "다만 회전이 연 50회로 이 파일에서 가장 크다. 왕복 5bp를 물리면 연 2.69%p가 "
              "깎여 CAGR 9.28% → 6.59%, 샤프는 0.427 → 0.256 으로 상시보유(0.447)에 확실히 "
              "진다. 사이클 효과가 실재하는 것과 그것으로 돈을 버는 것은 다른 문제다.")


def main() -> int:
    global A, DTS, RF
    p = os.path.join(DATA, "assets.json")
    if not os.path.exists(p):
        print("❌ data/assets.json 없음 — python build/refresh_assets.py 먼저 실행"); return 1
    A = json.load(io.open(p, encoding="utf-8"))
    # 🚨 성과 기준일 = **전월말**(2026-08-14 사용자 지시). 종목 랩과 **같은 함수**로 자른다 —
    #   자를 자리를 따로 쓰면 두 랩의 마지막 날이 갈리고, 그러면 한 화면에서 창이 다른 두
    #   수치가 나란히 놓인다(이 저장소가 MAX_YEARS 로 이미 한 번 겪은 사고다).
    # ⚠ 여기 격자는 자산 패널(assets.json)이라 종목 격자와 거래일이 다를 수 있다. 자르는
    #   기준은 '전월말' 이라는 **달**이지 특정 날짜가 아니므로 그 차이는 문제되지 않는다.
    import tech_backtest as _TB
    # 🚨 2026-08-23 — **격자를 더 이상 안 자른다.** 종전에는 여기서 전월말로 잘라 곡선도
    #   구간수익도 거기서 멈췄다(사용자 지적 «전략별 성과도 매일 갱신돼야 하는데 7월말이
    #   끝이네»). 이제 격자는 오늘까지 그대로 두고 **지표만** mcut 으로 자른다.
    #   ⚠ 종전 주석은 «패널을 같이 안 자르면 px[t][-1] 이 미래를 본다» 였다. 안 자르는
    #     지금은 격자의 끝이 곧 오늘이라 **볼 미래가 없다** — 그 위험은 절단이 있을 때만
    #     생기던 것이다. 꼬리로 읽는 자리(hold_now 의 as_of 등)는 이제 오늘을 집는 것이
    #     맞고, 그게 «지금 보유» 가 원래 말하려던 것이다.
    DTS = A["dates"]
    ASOF_N[0] = _TB.asof_cut(DTS)
    print("  격자 %s ~ %s (%d일) · 지표는 전월말 %s 까지(%d일)"
          % (DTS[0], DTS[-1], len(DTS), DTS[ASOF_N[0] - 1], ASOF_N[0]))
    _GRID.clear()
    _GRID.update({d: i for i, d in enumerate(DTS)})   # gthin 이 쓰는 절대 위치표
    RF = json.load(io.open(os.path.join(DATA, "rf_monthly.json"),
                           encoding="utf-8")).get("monthly") or {}
    # 🚨 무위험 계열을 **패널 구간으로 자른다**(2026-08-04). 종전에는 rf_monthly.json 전체
    #   (1981-09~, 539개월)를 그대로 넘겼다. ann_stats 가 `sum(rf)/len(rf)` 로 평균만 쓰므로
    #   그것은 **연 3.79%** 인데, 이 패널 구간(2006~)의 실제 평균은 훨씬 낮다. 즉 샤프의
    #   분자에서 있지도 않던 이자를 빼고 있었다 — 전 전략이 같은 방향으로 낮게 나온다.
    #   tech_backtest.load() 는 이미 같은 줄로 자르고 있었다(랩마다 규약이 달랐다는 뜻이다).
    if DTS:
        _n0 = len(RF)
        RF = {k: v for k, v in RF.items() if k >= DTS[0][:7]}
        print("  무위험 계열 %d → %d개월(패널 %s~) · 평균 연 %.2f%% → %.2f%%"
              % (_n0, len(RF), DTS[0][:7],
                 (sum(json.load(io.open(os.path.join(DATA, "rf_monthly.json"),
                                        encoding="utf-8")).get("monthly").values())
                  / _n0 * 12 * 100),
                 (sum(RF.values()) / max(1, len(RF)) * 12 * 100)))
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

    # 13F 복제는 별도 스크립트(build/guru_clone.py)가 낸다 — 규약이 다르기 때문이다
    # (공시지연 45일). 표는 여기 하나로 합친다. 두 곳에 두면 갈린다.
    # 🚨 2026-08-05 — 종전에는 ml_strategies.json(머신러닝 8종 + 13F 복제 1종)을 읽었다.
    #   머신러닝 여덟은 삭제했다(사용자 결정 · 사유는 build/DATA-FACTS.md 17번).
    #   13F 복제는 머신러닝이 아니라 같이 지울 이유가 없어 따로 떼어 냈고, 산식은 그대로다.
    gcp = os.path.join(DATA, "guru_clone.json")
    if os.path.exists(gcp):
        for r in (json.load(io.open(gcp, encoding="utf-8")).get("strategies") or []):
            r.setdefault("turnover", None)
            r["role"] = ROLE.get(r.get("sid"), "수익엔진")
            rows.append(r)
    else:
        print("  ⚠ guru_clone.json 없음 — python build/guru_clone.py 를 먼저 돌릴 것")

    # 판정 — 다중검정 보정 후 대조군 대비
    n = len(rows)
    lo, hi = 0.0, 12.0
    for _ in range(200):
        m = (lo + hi) / 2
        if math.erfc(m / math.sqrt(2)) > 0.05 / max(1, n):
            lo = m
        else:
            hi = m
    tcrit_bonf = round((lo + hi) / 2, 2)
    # 🚨 2026-08-13 사용자 지시 — **t 문턱을 전부 없앤다.** 위 이분탐색 값(tcrit_bonf)은
    #   이제 어디에도 안 쓴다. 남겨 둔 이유는 하나뿐이다: 산출물에 실어, 껐다는 사실과
    #   껐을 때 무엇을 포기했는지를 화면이 계속 말할 수 있게(끄는 것과 안 재는 것은 다르다).
    #
    #   등급을 아예 매기지 않는다(사용자 결정). 종목 랩이 2026-08-13 에 같은 자리에서 같은
    #   결론에 도달했고 그 코드가 이유를 이렇게 적었다 —
    #     "켜진 관문이 하나도 없다 … 그러면 등급은 성적을 말하는 것이 아니라 아무 말도
    #      안 하는 것이어야 한다. 't 가 2 를 넘었다' 같은 배지를 관문 없이 달면 화면이
    #      검정하지 않은 것을 검정한 척하게 된다."
    #   자산 랩만 등급을 매기고 있어 한 사이트가 두 관례를 썼다. 이제 하나다.
    # ⚠ '열위'(Δ샤프≤0)도 같이 없앤다. 문턱 없는 부호 판정은 t 0.02 짜리와 t 2.9 짜리를
    #   같은 말로 부르게 되고, 그것은 없애려던 것보다 더 나쁘다. 수치는 전부 그대로 싣는다.
    # ⚠ 자료 상태만 따로 표시한다 — 그건 성적이 아니라 '잴 수 있었나'다.
    tcrit = None
    for r in rows:
        if r.get("verdict") == "표본 부족 · 판정 불가":
            continue                      # 검정 구간이 짧아 이미 판정을 막아둔 건 그대로 둔다
        r["verdict"] = "판정 불가" if r.get("t") is None else "측정만"

    # ⚠ 이웃 상관과 incr5 수치는 계속 재서 싣는다 — 끄는 것과 안 재는 것은 다르다.
    #   등급을 매기던 자리만 없앴고 측정은 그대로다.
    attach_incr(rows, "자산")

    # ── 위험 축 판정 ── 수익 축(verdict)과 **따로** 매긴다. 덮어쓰지 않는다.
    #   두 축은 다른 질문에 답한다 — verdict 는 '더 벌었나', risk_verdict 는 '덜 깨졌나'다.
    #   한 전략이 '수익 축 구별 불가 · 위험 축 확인'일 수 있고, 그게 이 축을 만든 이유다.
    # 🚨 2026-08-13 — 여기 있던 본페로니 문턱(0.05/n)도 없앤다(사용자 지시). 그것은 n 이
    #   늘 때마다 조여지는 문턱이었고, 사용자가 없애라고 한 것이 정확히 그 성질이다.
    #   ⚠ 위험 축은 t 가 아니라 블록 부트스트랩 p 를 쓴다. 그래서 문턱을 **관례값 0.05 로
    #     고정**한다 — 없애면 이 축은 아무 말도 못 하게 되는데, 수익 축과 달리 여기에는
    #     '덜 깨졌나'라는 단일 질문에 대한 재표본 분포가 실제로 있다.
    #   ⚠ 고정했다는 것은 다중검정을 포기했다는 뜻이다. 71종을 같은 표본에서 돌렸으므로
    #     p<0.05 는 영가설에서도 3~4종이 나온다. 산출물이 그 사실을 적는다.
    pcrit = 0.05
    for r in rows:
        rk = r.get("risk")
        if not rk:
            r["risk_verdict"] = "판정 불가"      # 표본이 블록 4개에 못 미치거나 외부 산출물
            continue
        # 판정은 **CVaR5** 로 가른다. MDD 로 가르지 않는 이유는 검정력이다 — 이 표본에서
        # 큰 낙폭 사건은 사실상 2008 하나이고, 사건이 한 번이면 어떤 재표본법도 힘이 없다.
        # CVaR5 는 수백 일이 들어가 재표본마다 안정적이라 실제로 판정이 선다.
        # 다만 방향은 MDD 와 어긋나면 안 된다 — 둘이 다른 말을 하면 판정을 세우지 않는다.
        if rk["d_cvar"] <= 0 or rk["d_mdd"] <= 0:
            r["risk_verdict"] = "위험 악화" if rk["d_cvar"] <= 0 else "구별 불가"
        elif rk["p_cvar"] < pcrit:
            r["risk_verdict"] = "위험감축 확인"
        else:
            r["risk_verdict"] = "구별 불가"
    r_cnt = {}
    for r in rows:
        r_cnt[r.get("risk_verdict")] = r_cnt.get(r.get("risk_verdict"), 0) + 1
    print("  위험 축(블록 부트스트랩 %d회 · 블록 %d일 · p<%.5f): %s"
          % (BOOT_N, BOOT_BLOCK, pcrit, r_cnt))

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
    # 돌렸다가 목록에서 뺀 아카이브 항목 — 사유와 마지막 수치를 남긴다.
    RETIRED_ARCH = {
        "ml-market-timing":
            "2026-08-04 에 공개 데이터로 재현해 돌렸다(릿지·워크포워드, 특징 7개). "
            "마지막 측정: CAGR 12.46% · 샤프 0.700 · t −1.46 — 대조군 열위. "
            "2026-08-05 에 목록에서 뺐다(사용자 결정) — 사유는 성과가 아니라 **운영 비용**이다. "
            "ML 랩 전체가 한 번 도는 데 55분이 걸렸고, 얻는 것이 없었다.",
        "ml-stock-selection":
            "2026-08-04 에 재현해 일곱 판(릿지·로지스틱·고신뢰·상호작용·랜덤포레스트·특징20 둘)을 "
            "돌렸다. 마지막 측정: 단독 t 3.19~4.24 로 전부 문턱을 넘었으나, 서로의 초과수익 상관이 "
            "0.868~0.975 이고 이웃 5개 동시 통제 증분알파(incr5)가 −1.20~1.20 이라 게이트(2.0)를 "
            "하나도 못 넘었다 — 한 규칙을 일곱 번 판 것이었다. 2026-08-05 에 목록에서 뺐다.",
    }
    # 종목 랩이 재현한 아카이브 아키타입 — 자산 랩이 안 돌리는 것이 정상인 항목이다.
    # ⚠ 파일이 없거나 못 읽으면 빈 집합으로 둔다. 그러면 그 항목들이 '산출 실패'로 찍히는데,
    #   그것은 과대 경보이지 조용한 누락이 아니다 — 둘 중에는 이쪽이 안전하다.
    _TECH_ARCH = set()
    try:
        _tj = json.load(io.open(os.path.join(DATA, "tech_strategies.json"), encoding="utf-8"))
        _TECH_ARCH = ({r["arch"] for r in (_tj.get("strategies") or []) if r.get("arch")}
                      | {r["arch"] for r in (_tj.get("retired") or []) if r.get("arch")})
    except Exception:
        pass

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
        elif sid in RETIRED_ARCH:
            # 🚨 한 번 돌렸다가 목록에서 뺀 것. 여기 안 적으면 그 아카이브 항목이 화면에서
            #   **조용히 사라진다**(validate_site 가 실제로 잡아 줬다). '재현 못 했다'와
            #   '재현했다가 뺐다'는 다른 사실이므로 마지막 수치까지 남긴다.
            audit.append({"sid": sid, "n": x["n"], "c": x.get("c", ""),
                          "status": "돌렸다가 뺌", "why": RETIRED_ARCH[sid]})
        elif sid in _TECH_ARCH:
            # 종목 랩이 재현한 아카이브 항목이다 — 자산 랩이 안 돌리는 것이 정상이다.
            # ⚠ 이 갈래가 없으면 아래 '산출 실패'가 과잉 발동해 **감사표가 거짓말을 한다**
            #   (실측: 11건 중 10건이 이 경우였다. 처음 고칠 때 실제로 그렇게 냈다).
            audit.append({"sid": sid, "n": x["n"], "c": x.get("c", ""),
                          "status": "종목 랩에서 재현",
                          "why": "이 항목은 자산 랩이 아니라 종목·타이밍 랩이 재현했다 — "
                                 "그쪽 규칙 카드에서 성적을 볼 것."})
        else:
            # 🚨 2026-08-09 — 돌리기로 한 전략인데 **그날 산출이 실패한 것**이다
            #   (외부 자료 결손 — FRED 계열이 안 오거나 ETF 가격이 비면 rows 에 안 실린다).
            #   종전에는 여기서 아무것도 안 적었고, 그러면 커버리지 가드가 '아카이브 항목이
            #   화면에서 사라졌다'로 잡아 **잡 전체를 막았다.**
            #
            #   실제로 그 사슬이 이틀 연속 자산 패널을 세웠다(2026-08-07·08-08 CI 실패,
            #   ebp-risk-appetite-gate 1건). 그 바람에 assets.json 이 커밋되지 못해
            #   홈 달력의 8/6·8/7 지수 등락률이 비었다 — 그 전략과 아무 상관 없는 칸이다.
            #
            #   그래서 **빼지 않고 실패를 그대로 적는다.** 가드의 취지(항목이 조용히
            #   사라지지 않게)는 지켜지고, 한 전략의 결손이 나머지를 못 막는다.
            audit.append({"sid": sid, "n": x["n"], "c": x.get("c", ""),
                          "status": "이번 실행 산출 실패",
                          "why": "이번 실행에서 결과가 나오지 않았다 — 외부 자료(FRED 계열·ETF "
                                 "가격)가 그날 안 왔을 때 생긴다. 규칙의 성적이 아니라 수집 실패다. "
                                 "다음 실행에서 자료가 오면 자동으로 되돌아온다."})
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
        # 🚨 2026-08-13 — **이 랩이 무위험을 어디부터 평균 냈는지**를 싣는다.
        #   strategy_index.pr_baseline 이 같은 지수를 다시 잴 때 이 창을 안 쓰면 같은 카드에
        #   S&P 500(PR) 샤프가 두 값으로 나온다(실측 자산 60종 중앙 0.111 차이).
        #   ⚠ 손으로 적지 않는다. 위에서 RF 를 자른 그 값을 그대로 내보낸다 — 갈릴 자리를 없앤다.
        "rf_from": (DTS[0][:7] if DTS else None),
        # 화면이 배지 뜻을 스스로 적으려면 이 값이 필요하다 — 안 실으면 보정을 껐는데
        # 화면은 계속 "다중검정을 넘었다"고 말한다(종목 랩이 같은 사고를 낸 적이 있다).
        # 🚨 t 문턱은 전부 없앴다(2026-08-13). 그래도 **껐다는 사실과 껐을 때 포기한 것**을
        #   싣는다 — 화면이 배지 뜻을 스스로 적으려면 이 값이 필요하고, 안 실으면 다음 사람이
        #   "왜 등급이 없지" 하고 문턱을 다시 만든다.
        "gates": {"bonferroni": False, "t_gate": False,
                  "t_crit_bonferroni_would_be": tcrit_bonf,
                  "risk_p_crit": 0.05,
                  "note": "수익 축은 등급을 매기지 않는다(측정만). 위험 축만 관례 p<0.05 로 "
                          "가르되 n 에 따라 조이지 않는다."},
        "axes_note": ("판정 축을 넷 더 세웠다(2026-08-12) — CAPM 알파 · 상승/하락 포착률 · "
                      "12개월 롤링 초과 승률 · 침체 국면 성과. 수익 축(t)과 위험 축은 그대로 "
                      "두고 덮어쓰지 않는다. ⚠ 침체 축의 USREC 은 사후 확정치라 매매 규칙으로 "
                      "쓸 수 없다 — 규칙의 성격을 읽는 용도다."),
        "source": "가격 yfinance · 거시 FRED 공개 CSV(키 불필요) — 둘 다 무료·무인증",
        "protocol": [
            "월말 리밸런스·무비용(gross). 이 랩의 기본 규약 그대로다.",
            "대조군은 전략마다 다르다 — 절대수익형에 지수를 붙이면 '벤치 부정합' 기각이 되는데 "
            "그건 전략이 아니라 비교의 잘못이다(아카이브에 그 사고가 있다).",
            "구간은 전략마다 다르다. 쓰는 ETF의 상장일에 묶이기 때문이며, 그건 데이터 결손이 "
            "아니라 그 전략의 실제 제약이다.",
            ("🚨 t 문턱을 전부 없앴다(사용자 결정 2026-08-13). 그래서 이 랩은 수익 축에 "
             "**등급을 매기지 않는다** — 전부 '측정만'이다. t·Δ샤프·알파는 그대로 재서 싣되, "
             "그 수치가 어떤 선을 넘었다고 말하지 않는다. 관문이 없는데 배지를 달면 화면이 "
             "검정하지 않은 것을 검정한 척하게 되기 때문이다(종목 랩이 같은 날 같은 결론에 "
             "도달했고 이제 두 랩이 한 관례를 쓴다). 참고로 전략 %d개를 같은 표본에서 "
             "돌렸으므로 본페로니 임계였다면 |t|≥%.2f 였고, 관례값 |t|≥2.0 을 쓰면 "
             "영가설에서도 약 %d종이 그것을 넘는다 — 그 수를 여기 적어 두는 것으로 "
             "다중검정을 포기한 대가를 대신한다." % (n, tcrit_bonf, round(n * 0.05))),
            "대조군이 현금성(연변동성 2% 미만)인 전략은 샤프 차이가 허수가 된다 — 분모가 0에 "
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
    print("돌린 전략 %d개 · 판정 %s · t 문턱 없음(측정만)" % (n, vc))
    print("%-34s %9s %8s %8s %8s %7s  %s" % ("전략", "구간", "CAGR", "샤프", "Δ샤프", "t", "판정"))
    for r in rows:
        m = r["metrics"]
        print("%-34s %9s %8s %8s %8s %7s  %s"
              % (r["name"][:34], r["start"][:7], m.get("cagr"), m.get("sharpe"),
                 r["d_sharpe"], r.get("t"), r["verdict"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
