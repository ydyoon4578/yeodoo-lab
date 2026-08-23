# -*- coding: utf-8 -*-
"""build/style_pit_panel.py — 스타일 백테스트용 **시점정확(PIT) 패널** 한 벌.

왜 따로 떼어냈나(2026-08-23 사용자 요청 «스타일 전략들도 pit 으로 바꿔줘»).
종전에는 이 준비 코드가 build/style_pit.py **안에만** 있었고, 그 파일은 «편향이 얼마나
되는지 재는» 용도였다. 즉 랩은 PIT 로 돌릴 줄 알면서도 **배포하는 곡선은 소급**이었다.
배포 쪽에서 같은 일을 다시 짜면 두 벌이 되고, 그때는 «편향을 재는 쪽» 과 «배포하는 쪽»
중 어느 것이 틀렸는지 알 수 없게 된다 — 이 저장소가 되풀이 밟은 사고다.
그래서 준비를 여기 한 곳에 두고 둘이 같이 쓴다.

🚨 순환 임포트를 피하려고 **ST(style_top_pdf 모듈)를 인자로 받는다.** import 로 끌어오면
  style_top_pdf 를 스크립트로 실행할 때 그 모듈이 __main__ 과 별개로 한 번 더 로드되어
  STYLES·WINDOW 가 두 벌이 된다(WINDOW 는 5년 창 레그가 실제로 바꾸는 값이다).

## 두 단계인 이유

  prepare(ST)  … 멤버십·가격캐시·주입 대상까지. **아직 주입 안 한** 깨끗한 패널.
  inject(prep) … 그 패널에 편출 종목을 넣는다(px·uni·fx 세 축).

style_pit 은 그 사이에서 «주입 전» 앵커 레그를 돌려 배포 수치를 재현하는지 확인한다.
배포 쪽(style_top_pdf)은 둘을 잇달아 부르면 된다.
"""
from __future__ import annotations
import io, json, os, sys

import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 ⚠·— 출력 시 죽지 않게
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(DATA, "_pit_px_cache.json")   # 뚱뚱한 로컬 캐시(gitignore)
SLIM = os.path.join(DATA, "pit_px.json")           # 커밋되는 얇은 기록 — 러너가 이걸 쓴다
FX_PIT = os.path.join(DATA, "fx_pit")


def need(path, what):
    if not os.path.exists(path):
        raise SystemExit("%s 가 없다(%s) — 자료 없이 돌려 'PIT' 라고 적힌 생존자 "
                         "백테스트를 내보내지 않는다." % (what, path))
    return json.load(io.open(path, encoding="utf-8"))


def narrowed(fn, pool_of):
    """채점 모집단까지 그 시점 후보로 좁힌 채점 함수.

    🚨 이것이 'PIT' 의 정확한 뜻이다. backtest 의 마스크는 **채점 뒤**에 걸리므로, 좁히지
      않으면 모든 레그가 같은 큰 모집단으로 z 표준화·윈저화를 한다. 실제로 그때 규칙을
      돌렸다면 모집단도 그 시점 후보였다.
    P.uni·P.px 를 임시로 좁혀 부르고 반드시 되돌린다(finally).
    """
    def g(P, i):
        pool = pool_of(i)
        su, sp = P.uni, P.px
        P.uni = {t: v for t, v in su.items() if t in pool}
        P.px = {t: v for t, v in sp.items() if t in pool}
        try:
            return fn(P, i)
        finally:
            P.uni, P.px = su, sp
    return g


def prepare(ST, P=None, window=None, quiet=False):
    """멤버십·가격캐시·주입 대상까지. 반환 dict 의 P 는 **아직 주입 전**이다."""
    say = (lambda *a: None) if quiet else print
    sys.path.insert(0, HERE)
    import index_members                          # noqa: E402  같은 build/ 안
    mem, _carried = index_members.load()
    for _ym, _ix, _n in _carried:
        say("  ⚠ %s %s 결손 — 직전 달 %d종 이월" % (_ym, _ix.upper(), _n))
    # 로컬에 뚱뚱한 캐시가 있으면 그것을 쓰고(가장 신선하다), 없으면 커밋된 기록을 편다.
    if os.path.exists(CACHE):
        cache = json.load(io.open(CACHE, encoding="utf-8"))
        say("  가격 원천: %s(로컬 캐시)" % os.path.basename(CACHE))
    else:
        _sl = need(SLIM, "편출 종목 가격 기록")
        _ds = _sl["dates"]
        cache = {t: {_ds[v["i0"] + k]: p for k, p in enumerate(v["p"]) if p is not None}
                 for t, v in _sl["px"].items()}
        _cv = _sl.get("coverage") or {}
        say("  가격 원천: %s(커밋된 기록) · 티커 %s · ~%s"
            % (os.path.basename(SLIM), _cv.get("n_tickers"), _cv.get("end")))
    if P is None:
        P = ST.Panel()
    win = ST.WINDOW if window is None else window
    end = len(P.dates) - 1
    start = next((i for i in P.me if i >= max(0, end - win)), max(0, end - win))
    di = {d: k for k, d in enumerate(P.dates)}
    today = set(P.uni)

    def members_at(i):
        """그 달 멤버 — pit_backtest.py 와 같은 정의(월 키 조회)."""
        return set(mem.get(P.dates[i][:7]) or [])

    # 멤버십이 창을 덮는지 먼저 본다. 한 달이라도 비면 그 달은 마스크가 통째로 풀려
    # 조용히 생존자 백테스트로 되돌아간다 — 그것이 막아야 할 실패다.
    gapless = [i for i in P.me if start - 252 * 3 <= i <= end and not members_at(i)]
    if gapless:
        raise SystemExit("멤버십이 빈 월말 %d개(%s …) — 마스크가 풀려 PIT 이 성립하지 않는다"
                         % (len(gapless), P.dates[gapless[0]]))

    # 창 안에서 한 번이라도 멤버였던 것 중 오늘 유니버스에 없는 것 = 주입 대상.
    #   ⚠ 창 전에 이미 빠진 종목은 창 안에서 **후보였던 적이 없다**. 넣으면 후보는 안 늘고
    #     z 표준화 모집단만 바뀌어 규칙 자체가 달라진다.
    win_me = [j for j in P.me if start <= j <= end]
    union = set()
    for i in win_me:
        union |= members_at(i)
    gone = sorted(union - today)
    m0 = members_at(start)
    not_yet = sorted(today - m0)

    def load_series(t):
        c = cache.get(t) or {}
        a = np.full(len(P.dates), np.nan)
        n = 0
        for d, v in c.items():
            j = di.get(d)
            if j is not None and v is not None:
                a[j] = float(v); n += 1
        return (a, n)

    inject, missing, gap = {}, [], []
    for t in gone:
        a, n = load_series(t)
        if n < 200:                      # 채점 자체가 안 되는 조각은 넣지 않는다
            missing.append(t); continue
        # 티커 재사용 가드 — 일간 점프가 아니라 **긴 공백 뒤 재개**가 지문이다
        # (상장폐지 후 티커가 남에게 넘어간다). 점프로 판정하면 파산·임상발표를 버리게 되는데,
        # 특히 파산은 생존편향이 감추는 바로 그 사건이라 버리면 편향을 과소평가한다.
        idx = np.flatnonzero(~np.isnan(a))
        if len(idx) > 1 and int(np.max(np.diff(idx))) >= 60:
            gap.append(t); continue
        inject[t] = a
    say("창 편출 %d종 · 주입 가능 %d종 · 가격 부재 %d종: %s"
        % (len(gone), len(inject), len(missing), missing))
    if gap:
        say("  ⚠ 60거래일 이상 공백 뒤 재개(티커 재사용 의심) 제외: %s" % gap)
    return {"ST": ST, "P": P, "mem": mem, "members_at": members_at, "today": today,
            "start": start, "end": end, "win_me": win_me, "inject": inject,
            "missing": missing, "gap": gap, "gone": gone, "not_yet": not_yet, "m0": m0,
            "quiet": quiet}


def inject(prep):
    """준비된 패널에 편출 종목을 넣는다 — px·uni·fx 세 축을 **같이** 넣어야 한다.

    ⚠ px 만 넣으면 뒤 셋(퀄리티·가치·성장)은 P.uni 를 순회하므로 주입이 아무 효과가 없고,
      '편출 기여 0' 이 자료 부재 때문인지 진짜인지 구별이 안 된다.
    """
    say = (lambda *a: None) if prep.get("quiet") else print
    P, inj = prep["P"], prep["inject"]
    for t, a in inj.items():
        P.px[t] = a
    n_fx = 0
    if os.path.isdir(FX_PIT):
        import importlib.util
        _sp = importlib.util.spec_from_file_location("_tb_fx", os.path.join(HERE, "tech_backtest.py"))
        _tb = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_tb)
        P.fx = _tb.load_fund(extra_dirs=[FX_PIT])
        n_fx = len([t for t in inj if t in P.fx])
        say("편출 재무 주입 %d/%d종(data/fx_pit %d개)"
            % (n_fx, len(inj), len(os.listdir(FX_PIT))))
    else:
        say("⚠ data/fx_pit 없음 — 퀄리티·가치·성장은 편출 후보 없이 측정된다"
            "(러너에서 pit-facts 워크플로를 돌릴 것)")
    nm = {}
    if os.path.isdir(FX_PIT):
        for f in os.listdir(FX_PIT):
            try:
                d = json.load(io.open(os.path.join(FX_PIT, f), encoding="utf-8"))
                nm[d.get("t") or f[:-5]] = d.get("nm") or ""
            except Exception:
                pass
    for t in inj:
        if t not in P.uni:
            P.uni[t] = {"t": t, "name": nm.get(t) or t, "idx": []}
    # 🚨 발행사 맵은 P._iss 에 캐시된다(iss_of). 주입 전에 이미 채워졌을 수 있으므로 지운다 —
    #   안 지우면 주입 종목이 발행사 중복제거에서 조용히 빠진다.
    if hasattr(P, "_iss"):
        del P._iss
    cov = []
    for i in prep["win_me"]:
        m = prep["members_at"](i)
        if m:
            cov.append(len([t for t in m if t in P.px]) / len(m))
    if cov:
        say("멤버 대비 가격 보유율: 최저 %.1f%% · 중앙 %.1f%%"
            % (100 * min(cov), 100 * sorted(cov)[len(cov) // 2]))
    prep["n_fx"] = n_fx
    prep["cov"] = cov
    return prep
