# -*- coding: utf-8 -*-
"""사전등록 §5 실행 검산 — 투자의견 리비전 3종이 **규약대로 구현됐는지**만 본다.

🚨 이것은 채점기가 아니다. 수익률을 한 줄도 계산하지 않는다(이 랩의 규칙: 채점기를 두 벌
  두면 한쪽만 고쳐진다). 여기서 답하는 것은 "성적이 좋은가"가 아니라 **"엔진이 규약대로
  골랐는가"** 뿐이고, 답이 아니오면 결과를 읽기 전에 폐기하고 다시 짠다.

검산 여섯(PREREG-2026-08-10-REVDRIFT.md §5) —
  ① 월별 후보 수 ≥ 400
  ② 상위10의 증권사 수 중앙값이 유니버스 중앙값의 0.7~1.4배  ← √n 교정이 걸렸는가
  ③ 동점으로 채워진 자리 0
  ④ 회전율 21일 > 63일                                      ← 백테스트 산출에서 읽는다
  ⑤ 섹터중립판의 보유 섹터가 서로 다를 것
  ⑥ 상위10 신호가 대부분 양수 — 전 종목 음수인 달의 비율을 적는다

  python build/check_revdrift.py               # 하나라도 실패하면 종료코드 1
  python build/check_revdrift.py --registered  # **등록된 실패(③)만** 남았으면 0, 새 실패면 1
                                               # ← CI 는 이쪽을 쓴다(아래 REGISTERED 참조)
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import tech_backtest as TB

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
ok_all = True
FAILED = []          # 실패한 검산 번호 — 어떤 것이 실패했는지가 판정의 근거다

# 🚨 «등록된 실패» — 결과를 보고 문턱을 고치지 않기로 한 자리다.
#   PREREG-2026-08-10-REVDRIFT-RESULT.md §6: 검산③(동점으로 채워진 자리 0)이 29자리로
#   실패했고, 「그래도 문턱을 고쳐 '통과'로 만들지 않는다. 결과를 보고 기준을 움직이면
#   그 검정은 무효다」 라고 적어 실패로 남겼다. 원인도 적혀 있다 — 분자가 이산인 신호에서
#   동점이 정확히 0 이 되는 일은 없는데 프로브의 **중앙값**을 보고 문턱을 0 으로 적었다.
# ⚠ 그래서 --registered 는 «③만 실패하면 통과» 로 판정한다. 문턱을 고친 것이 아니다 —
#   기준은 그대로 두고, 이미 기록된 실패인지 **새로 생긴 실패인지**를 가르는 것뿐이다.
#   ③ 말고 하나라도 더 실패하면 그때는 구현이 바뀐 것이므로 막는다.
REGISTERED = {"③"}


def say(no, ok, msg):
    global ok_all
    ok_all = ok_all and ok
    if not ok:
        FAILED.append(no)
    print("  %s 검산%s %s" % ("통과" if ok else "실패", no, msg))


def main():
    global ok_all
    dates, px, _v, _h, _l, meta, _rf = TB.load()
    FU = TB.load_fund()
    TB._RAT = TB.load_ratings()
    if not TB._RAT:
        print("투자의견 캐시가 없다 — build/fetch_ratings.py 를 먼저 돌린다.")
        return 1
    me = TB.month_ends(dates)
    tick = sorted(px)
    md = lambda a: sorted(a)[len(a) // 2] if a else 0

    for sid, cal in (("x-revdrift", 30), ("x-revdrift-q", 91)):
        print("### %s (달력 %d일)" % (sid, cal))
        pools, ratio, ties, allneg, topmc = [], [], 0, 0, []
        for i in me:
            d = dates[i - 1]
            if d < "2013-01-01":
                continue                       # 이력 시작 전 구간은 후보가 얇다(사전등록 §3)
            sc = []
            for t in tick:
                v = TB.rat_signal(t, d, cal)
                if v is None or v != v:
                    continue
                _c, n = TB._rat_consensus(
                    t, (__import__("datetime").date(int(d[:4]), int(d[5:7]), int(d[8:10]))
                        - __import__("datetime").date(1970, 1, 1)).days)
                sc.append((v, t, n))
            if len(sc) < 10:
                continue
            pools.append(len(sc))
            sc.sort(key=lambda x: (-x[0], x[1]))
            top = sc[:10]
            # ② 커버 두께
            ratio.append(md([n for _v, _t, n in top]) / float(max(1, md([n for _v, _t, n in sc]))))
            # ③ 10위 경계 동점으로 채워진 자리
            cut = top[-1][0]
            nab = sum(1 for v, _t, _n in sc if v > cut)
            nti = sum(1 for v, _t, _n in sc if v == cut)
            if nti > 1 and nab < 10:
                ties += (10 - nab)
            # ⑥ 상위10이 전부 음수인 달
            if all(v < 0 for v, _t, _n in top):
                allneg += 1
            # §8-4 규모 쏠림 — 시총은 랩과 같은 식으로 만든다(주식수 × 종가)
            mc = {}
            for _v, t, _n in sc:
                f = FU.get(t) or {}
                sn = TB.asof_fund(f.get("sh"), d)
                p0 = px[t][i - 1] if px.get(t) else None
                if sn and p0 and sn > 0 and p0 > 0:
                    mc[t] = sn * p0
            tm = [mc[t] for _v, t, _n in top if t in mc]
            um = [mc[t] for _v, t, _n in sc if t in mc]
            if len(tm) >= 5 and len(um) >= 50:
                topmc.append(md(tm) / float(md(um)))
        say("①", md(pools) >= 400, "월별 후보 중앙 %d (기준 ≥400)" % md(pools))
        r = md(ratio)
        say("②", 0.7 <= r <= 1.4,
            "상위10 증권사수 ÷ 유니버스 = %.2f배 (기준 0.7~1.4 — √n 교정 확인)" % r)
        say("③", ties == 0, "동점으로 채워진 자리 누적 %d개 (기준 0)" % ties)
        say("⑥", True, "상위10이 전부 음수인 달 %d/%d (%.0f%%) — 성질로 기록"
            % (allneg, len(pools), 100.0 * allneg / max(1, len(pools))))
        if topmc:
            # §8-4 — 21일 창은 후보의 56%만 신호가 0이 아니다. 그 부분집합이 '뉴스 많은
            # 대형주'로 쏠리면 성적을 만드는 것은 리비전이 아니라 규모다.
            print("       §8-4 상위10 시총 ÷ 유니버스 중앙 = %.2f배 (1.0 이면 규모 중립)"
                  % md(topmc))
        print()

    # ④⑤ 는 백테스트 산출에서 읽는다 — 여기서 다시 계산하지 않는다.
    try:
        j = json.load(io.open(os.path.join(DATA, "tech_strategies.json"), encoding="utf-8"))
    except Exception:
        print("tech_strategies.json 을 못 읽었다 — ④⑤ 는 백테스트 뒤에 다시 돌린다.")
        return 0 if ok_all else 1
    S = {x["sid"]: x for x in j["strategies"]}
    if "x-revdrift" in S and "x-revdrift-q" in S:
        a, b = S["x-revdrift"]["turnover"], S["x-revdrift-q"]["turnover"]
        say("④", a > b, "회전율 21일 %.2f > 63일 %.2f" % (a, b))
    if "x-revdrift-sn" in S:
        h = (S["x-revdrift-sn"].get("holdings") or {}).get("tickers") or []
        secs = [(meta.get(t) or {}).get("sector") or "?" for t in h]
        say("⑤", len(set(secs)) == len(secs),
            "섹터중립판 보유 %d종 · 서로 다른 섹터 %d개" % (len(secs), len(set(secs))))
    print()
    if ok_all:
        print("→ 검산 전부 통과 — 결과를 읽어도 된다.")
        return 0
    fs = sorted(set(FAILED))
    if "--registered" in sys.argv and set(fs) <= REGISTERED:
        print("→ ⚠ 등록된 실패만 남아 있다(검산%s) — PREREG-2026-08-10-REVDRIFT-RESULT.md §6 에 "
              "«완화하지 않는다» 로 적어 둔 자리다. 새 실패가 아니므로 막지 않는다."
              % "·".join(fs))
        print("  🚨 통과라는 뜻이 아니다. x-revdrift 3종은 이 실패를 안은 채로 게시돼 있고, "
              "셋 다 t 가 문턱에 한참 못 미쳐 판정을 못 만든다는 것이 같이 기록돼 있다.")
        return 0
    print("🚨 검산 실패(검산%s) — 구현 오류다. 결과를 읽지 말고 다시 짠다." % "·".join(fs))
    if "--registered" in sys.argv:
        new = sorted(set(fs) - REGISTERED)
        if new:
            print("  🚨 등록에 없는 **새 실패**: 검산%s. 엔진이 규약에서 벗어났다."
                  % "·".join(new))
    return 1


if __name__ == "__main__":
    sys.exit(main())
