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
from tech_backtest import (ann_stats, tstat, maxdd, curve_pack,  # noqa: E402
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


def attach_incr(rows, tcrit, label):
    """랩 안에서 서로 얼마나 겹치는지 재고, 겹침이 남기는 것이 없으면 등급을 내린다.

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
    dg = []
    for r in rows:
        if r.get("verdict") != "통과 후보":
            continue
        i5 = (r.get("incr5") or {}).get("t")
        if i5 is None or abs(i5) >= 2.0:
            continue
        dg.append((r["name"], r.get("t"), i5, (r.get("incr5") or {}).get("vs") or []))
        r["verdict"] = "구별 불가"
        r["why"] = (r.get("why") or "") + (
            " ⚠ 이웃 5개를 동시에 통제하면 증분 알파 t가 %.2f로 게이트(2.0)에 못 미친다"
            "(이웃: %s). 단독 t %s만 보면 문턱을 넘지만, 이 랩의 중복 판정 잣대는 "
            "보유 겹침이 아니라 초과수익 상관이고 이웃 하나가 아니라 다섯이다."
            % (i5, " · ".join((r.get("incr5") or {}).get("vs") or [])[:200], r.get("t")))
    if dg:
        print("  [%s 증분알파 게이트] 통과 후보 → 구별 불가 %d종:" % (label, len(dg)))
        for nm, t0, i5, vs in dg:
            print("    · %-30s t %s → incr5 %.2f" % (nm[:30], t0, i5))
    return dg


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
    msc, mbc = ann_stats(nav_c, dd, RF), ann_stats(bnav_c, dd, RF)   # 비용 후
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
            "t": tstat(rets, brets), "risk": risk_bootstrap(rets, brets),
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
    "ml-xsec": "수익엔진", "ml-xsec-inter": "수익엔진", "ml-xsec-tree": "수익엔진",
    "ml-xsec-w-ridge": "수익엔진", "ml-xsec-w-forest": "수익엔진",
    "guru-clone": "수익엔진",
    # 고전 타이밍 규칙 — 전부 '언제 들어가 있을까'만 정하므로 타이밍오버레이다.
    # 변동성 타깃은 노출을 위로 늘리지 않고 줄이기만 해 성격이 다르다(위험감축).
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
                "t": tstat(rets, brs), "risk": risk_bootstrap(rets, brs), "turnover": 252.0,
                # 🚨 2026-08-05 추가. 증분 알파(incr/incr5)는 **날짜 정합** 회귀라 dates 가 없으면
                #   아예 못 돈다. 종전에는 nav·bnav 만 실어 이 랩들이 그 검정을 한 번도 못 받았다.
                "dates": (_gt := gthin(dd, nav, bn))[0],
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
                "t": tstat(rets, brs), "risk": risk_bootstrap(rets, brs), "turnover": 252.0,
                # 🚨 2026-08-05 추가. 증분 알파(incr/incr5)는 **날짜 정합** 회귀라 dates 가 없으면
                #   아예 못 돈다. 종전에는 nav·bnav 만 실어 이 랩들이 그 검정을 한 번도 못 받았다.
                "dates": (_gt := gthin(dd, nav, bn))[0],
                "nav": _gt[1],
                "bnav": _gt[2]}
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
            # ⚠ EBP 도 월간이다(연준이 관측월 뒤에 낸다). macro_asof 로 읽으면 그달 말일에
            #   그달 EBP 를 아는 셈이 된다 — 발표 시차 30일을 넣는다.
            _e = macro_asof_m("EBP", DTS[i], 30)
            e = _e[-1] if _e else None
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
                # 🚨 2026-08-05 추가. 증분 알파(incr/incr5)는 **날짜 정합** 회귀라 dates 가 없으면
                #   아예 못 돈다. 종전에는 nav·bnav 만 실어 이 랩들이 그 검정을 한 번도 못 받았다.
                "dates": (_gt := gthin(months, nav, bn))[0],
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
    # 대조군은 전부 **SPY 상시보유**다. 이 규칙들은 '무엇을 살까'가 아니라 '언제 들어가 있을까'만
    # 정한다 — 들어가 있을 때 사는 것이 SPY 이므로, 정당한 귀무가설은 '그냥 계속 들고 있기'다.
    # 전략도 대조군도 같은 SPY 계열이라 TR/PR 표기 차이가 양쪽에서 상쇄된다.
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
        add(sid, arch, lambda: run_weights(w, st, label, lambda i: {"SPY": 1.0},
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
        return run_weights(w, st, "타이밍 3규칙 다수결", lambda i: {"SPY": 1.0},
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
                           lambda i: {"SPY": 1.0},
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
                           lambda i: {"SPY": 1.0},
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
        add(sid, None, lambda: run_weights(w, st, label, lambda i: {"SPY": 1.0},
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
    DTS = A["dates"]
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

    attach_incr(rows, tcrit, "자산")

    # ── 위험 축 판정 ── 수익 축(verdict)과 **따로** 매긴다. 덮어쓰지 않는다.
    #   두 축은 다른 질문에 답한다 — verdict 는 '더 벌었나', risk_verdict 는 '덜 깨졌나'다.
    #   한 전략이 '수익 축 구별 불가 · 위험 축 확인'일 수 있고, 그게 이 축을 만든 이유다.
    #   문턱은 수익 축과 같은 규율을 쓴다(본페로니 0.05/n). 축을 하나 더 열었다고 해서
    #   검정 횟수만 늘고 문턱이 헐거워지면 그건 그냥 다중검정을 늘린 것이다.
    pcrit = 0.05 / max(1, n)
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
            "마지막 측정: CAGR 12.46%% · 샤프 0.700 · t −1.46 — 대조군 열위. "
            "2026-08-05 에 목록에서 뺐다(사용자 결정) — 사유는 성과가 아니라 **운영 비용**이다. "
            "ML 랩 전체가 한 번 도는 데 55분이 걸렸고, 얻는 것이 없었다.",
        "ml-stock-selection":
            "2026-08-04 에 재현해 일곱 판(릿지·로지스틱·고신뢰·상호작용·랜덤포레스트·특징20 둘)을 "
            "돌렸다. 마지막 측정: 단독 t 3.19~4.24 로 전부 문턱을 넘었으나, 서로의 초과수익 상관이 "
            "0.868~0.975 이고 이웃 5개 동시 통제 증분알파(incr5)가 −1.20~1.20 이라 게이트(2.0)를 "
            "하나도 못 넘었다 — 한 규칙을 일곱 번 판 것이었다. 2026-08-05 에 목록에서 뺐다.",
    }
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
