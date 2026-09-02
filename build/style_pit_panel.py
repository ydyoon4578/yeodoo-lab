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

    # 🚨 2026-09-03 — **달 경계 이월.** 이 지도는 «월 키» 로 조회하는데 갱신 주기가 다르다:
    #   가격 패널은 매일이고 index_history 는 **주 1회**(refresh-members, 금 21:45 UTC)다.
    #   그래서 새 달 첫 거래일이 패널에 들어온 뒤 그 주 토요일까지 그 달 키가 **빈다**.
    #   그동안 members_at(end) 가 빈 집합을 돌려주고 → pool 이 비고 → 채점 0종이 되어
    #   style_top_pdf 가 전 스타일 «자료 부족» 으로 죽었다.
    #   실측 2026-09-02: refresh-assets 두 슬롯 연속 실패. 실패 지점이 커밋보다 **앞**이라
    #   이미 성공한 자산 패널·시장판·홈 기간별 수익률까지 통째로 버려졌고, 화면의
    #   «3영업일 지연» 경고로 사용자가 알아챘다. 8월 경계에 안 걸린 것은 이 파일이
    #   08-02 에 만들어지며 8월 키를 이미 담고 있었기 때문이다 — 9월이 첫 경계였다.
    #   ⚠ **마지막 알려진 달보다 뒤인 달만** 이월한다. 창 안쪽 결손을 이월로 덮으면
    #     마스크가 풀린 것을 못 보게 되는데, 그것이 바로 아래 gapless 검사가 막으려는 실패다.
    #   ⚠ 이월은 선견이 아니다 — 9월 1일에 알 수 있는 최신 명단은 8월 명단이다.
    #     pit_backtest.py 는 같은 자리를 `if m: cur = m`(직전 달 유지)로 이미 이렇게 다룬다.
    _MK = sorted(k for k, v in mem.items() if v)
    _LAST = _MK[-1] if _MK else None
    CARRY_MAX_M = 2          # 주 1회 갱신이라 정상 최대치는 1달. 2를 넘으면 수집이 죽은 것이다.

    def _months_after(k):
        """월 키 k 가 마지막 알려진 달보다 몇 달 뒤인가(같으면 0, 앞이면 음수)."""
        return (int(k[:4]) - int(_LAST[:4])) * 12 + (int(k[5:7]) - int(_LAST[5:7]))

    _carry_gap = 0
    if _LAST:
        _carry_gap = max(0, _months_after(P.dates[end][:7]))
        if _carry_gap > CARRY_MAX_M:
            raise SystemExit(
                "멤버십 지도가 %s 에서 멈췄는데 가격 패널은 %s 다(%d달 차) — 이월 한도 %d달을 "
                "넘었다. 한 분기 묵은 명단을 «PIT» 이라 부르며 내보내지 않는다. "
                "`python build/refresh_index_history.py` 가 왜 안 도는지 볼 것"
                % (_LAST, P.dates[end], _carry_gap, CARRY_MAX_M))
        if _carry_gap:
            say("  ⚠ 멤버십 %s 까지만 있다 — %s 은 %s 명단을 이월한다(주 1회 갱신이라 정상)"
                % (_LAST, P.dates[end][:7], _LAST))

    def members_at(i):
        """그 달 멤버 — pit_backtest.py 와 같은 정의(월 키 조회).

        마지막 알려진 달 **뒤**의 달만 그 달 명단으로 이월한다(위 주석). 안쪽은 이월하지 않는다.
        """
        k = P.dates[i][:7]
        v = mem.get(k)
        if v:
            return set(v)
        if _LAST and k > _LAST:
            return set(mem.get(_LAST) or [])
        return set()

    # 멤버십이 창을 덮는지 먼저 본다. 한 달이라도 비면 그 달은 마스크가 통째로 풀려
    # 조용히 생존자 백테스트로 되돌아간다 — 그것이 막아야 할 실패다.
    # ⚠ **원본 지도**(mem)로 본다. members_at 로 보면 위의 꼬리 이월이 결손을 덮어
    #   이 검사가 이빨을 잃는다. 꼬리(마지막 키 뒤)는 CARRY_MAX_M 이 따로 지킨다.
    gapless = [i for i in P.me if start - 252 * 3 <= i <= end
               and not mem.get(P.dates[i][:7]) and (not _LAST or P.dates[i][:7] <= _LAST)]
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
