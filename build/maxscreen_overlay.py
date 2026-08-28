# -*- coding: utf-8 -*-
"""build/maxscreen_overlay.py — E18 「구현 A」 네거티브 스크린 오버레이 → data/maxscreen.json

규약: build/PREREG-2026-08-29-ASWRITTEN.md §2 (x-maxlow-n52 · x-max5low-n52 행).

  전략 탐색 풀 E18(복권선호 회피 / MAX 효과)의 entry 가 권장 구현을 이렇게 적었다:

    "구현 A(권장, 롱온리 필터): **챔피언/모멘텀 후보 바스켓에서 MAX(5) 상위 10~20% 종목을
     사전 배제한 뒤 동일가중 top-N 구성.**"

  이것은 바스켓 크기 문제가 아니라 **오버레이**다. 그래서 x-maxlow-n52 · x-max5low-n52
  자체는 안 고치고(그 둘은 여전히 «십분위 정렬» 판이다) 여기서 따로 잰다.

🚨 **자유 파라미터를 내가 고르지 않는다.** 이 등록의 요지가 그것이다(§1: 「원문에 없는 수를
  내가 정하면 방금 없앤 자유도를 옮기는 것이다」). 카드가 정하지 않은 것이 둘 —
    ① 배제 비율 — 카드는 «10~20%» 라는 **구간**을 준다. 하나를 고르지 않고 **양 끝을 다
       돌려 나란히 싣는다.** 둘이 갈리면 그 자체가 결과다.
    ② 챔피언 집합 — 카드는 «챔피언/모멘텀 후보» 라고만 한다. 새로 고르지 않고 **이 랩에
       이미 등록된 챔피언 넷**을 그대로 쓴다(PREREG-2026-08-28-REVSCREEN.md §1-1 이
       돌리기 전에 못박은 목록이다). 여기서 다시 고르면 그것이 새 선택이다.

🚨 엔진(tech_backtest.py)을 고치지 않는다. 밖에서 `xsec_score_at` 을 감싸 pool 만 좁힌다 —
  build/revscreen_overlay.py 와 **같은 갈고리**다. 마스킹은 그 함수 한 자리에서만 한다고
  엔진 머리말이 못박아 두었고(사전패스까지 같이 좁아진다 — 갈래마다 거르면 선견이 된다),
  PIT 레그가 쓰는 경로가 그것이다.
🚨 사이트 산출물을 덮어쓰지 않는다 — TB.OUT 을 밑줄 접두 캐시로 돌린다.

    python build/maxscreen_overlay.py            # 두 판(10% · 20%)을 차례로 돌린다
    python build/maxscreen_overlay.py --report   # 이미 있는 캐시로 표만 다시 짠다
"""
from __future__ import annotations
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)

OUT = os.path.join(DATA, "maxscreen.json")
BASE = os.path.join(DATA, "tech_strategies.json")     # 기준선 = 엔진이 이미 낸 값


def RAW(q):
    return os.path.join(DATA, "_maxscreen_raw_%d.json" % int(q * 100))   # 밑줄 = 커밋 금지


def FIREP(q):
    return os.path.join(DATA, "_maxscreen_fire_%d.json" % int(q * 100))


# ── 사전등록의 상수 — 결과를 보고 만지지 않는다 ─────────────────────────────
# ⚠ 챔피언 넷은 PREREG-2026-08-28-REVSCREEN.md §1-1 의 목록 그대로다. 새로 안 고른다.
CHAMPS = ["x-sp", "x-dist200", "x-custconc", "x-sue"]
DROP_QS = (0.10, 0.20)     # 카드의 «상위 10~20%» — 양 끝을 다 돌린다(하나를 안 고른다)
MAX_WIN = 21               # 직전 1개월(약 21거래일) — 카드 그대로
MAX_K = 5                  # MAX(5) — 카드가 구현 A 에서 지정한 것은 MAX(5) 다


def run_one(q):
    """배제 비율 q 로 한 판 돌린다. 산출물은 RAW(q), 발동률은 FIREP(q)."""
    import tech_backtest as TB

    TB.OUT = RAW(q)                    # 🚨 사이트 산출물을 덮어쓰지 않는다
    _orig = TB.xsec_score_at
    fire, seen, dropn, memo = {}, {}, {}, {}

    def drop_at(X, i):
        """그 신호일에 뺄 종목 — MAX(5)가 **상위** q 인 것.

        ⚠ MAX 를 못 구하는 종목은 빼지 않는다. 모르는 것을 나쁜 것이라 부르지 않는다
          (revscreen 의 «신호 없는 종목은 제외하지 않는다» 와 같은 규약).
        ⚠ 후보를 X["tickers"] 가 아니라 **그 시점 pool** 에서 받아야 선견이 안 난다 —
          부르는 쪽(screened)이 이미 좁힌 base 를 넘긴다.
        """
        sig = X["dates"][i - 1]
        if sig in memo:
            return memo[sig]
        R = X["R"]
        vals = []
        for t in X["_mask"]:
            rs = R.get(t)
            if not rs:
                continue
            m = TB.maxret(rs, i - 1, MAX_WIN, MAX_K)
            if m is not None:
                vals.append((m, t))
        vals.sort(reverse=True)                       # 내림차순 = 高MAX 가 앞
        k = int(len(vals) * q)
        out = {t for _v, t in vals[:k]}
        memo[sig] = out
        dropn[sig] = len(out)
        return out

    def screened(S, i, X, pool=None):
        base = set(X["tickers"]) if pool is None else set(pool)
        X["_mask"] = base
        drop = drop_at(X, i)
        sc = _orig(S, i, X, base - drop)
        # 발동률 — 챔피언에 한해 «스크린이 없었다면 뽑혔을 자리» 중 몇이 빠졌나를 센다.
        #   ⚠ 이걸 안 재면 «오버레이가 아무것도 안 했는데 성적이 같다» 를 «효과 없음» 으로
        #     잘못 읽는다. 공허 판정이 이 수로 갈린다.
        if TB._BASE_SID(S["sid"]) in CHAMPS:
            sc0, _ir0, _cr0 = _orig(S, i, X, base)
            n = S.get("topn") or TB.TOPN
            top0 = [t for _v, t in sc0[:n]]
            key = (S["sid"], X["dates"][i - 1])
            fire[key] = sum(1 for t in top0 if t in drop)
            seen[key] = len(top0)
        return sc

    TB.xsec_score_at = screened
    # 🚨 두 판을 **한 프로세스에서** 이어 돌린다. TB.run() 은 build_strats() 를 부르고
    #   build_strats() 는 전역 TB.STRATS 에 **덧붙인다** — 그래서 둘째 판에서 목록이
    #   116 → 220종으로 불었다(중복 sid 104개 · 2026-08-29 실측). 중복 행은 값이
    #   바이트로 같아 챔피언 수치는 안 틀렸지만(전수 대조로 확인), 실행 시간이 두 배가 되고
    #   로그가 두 줄씩 찍히며 무엇보다 «돌린 규칙 수» 가 거짓이 된다 — 다중검정 분모가 그 수다.
    #   → 판마다 목록을 비우고 시작한다. 두 판이 서로를 안 오염시키는 것이 요점이다.
    TB.STRATS[:] = []
    print("\n" + "=" * 72)
    print("구현 A — MAX(%d) 상위 %.0f%% 사전 배제 · 챔피언 %s"
          % (MAX_K, q * 100, "·".join(CHAMPS)))
    print("산출물 %s (사이트 파일 안 건드림)" % os.path.basename(RAW(q)))
    print("=" * 72)
    TB.run()
    TB.xsec_score_at = _orig                          # 갈고리를 되돌린다(두 판을 이어 돌린다)
    io.open(FIREP(q), "w", encoding="utf-8").write(json.dumps(
        {"fire": {"%s|%s" % k: v for k, v in fire.items()},
         "seen": {"%s|%s" % k: v for k, v in seen.items()},
         "dropn": dropn}, ensure_ascii=False))


def report():
    """세 산출물(기준선 · 10% · 20%)을 맞대어 data/maxscreen.json 을 짠다."""
    def load(p):
        d = json.load(io.open(p, encoding="utf-8"))
        rows = d.get("strategies") or []
        return {r.get("sid"): r for r in rows if r.get("sid")}

    def grab(r):
        """🚨 turnover·vs_traded 는 **최상위** 필드다(metrics 안이 아니다)."""
        m = r.get("metrics") or {}
        mn = r.get("metrics_net") or {}
        vt = r.get("vs_traded") or {}
        return dict(cagr=m.get("cagr"), sharpe=m.get("sharpe"), mdd=m.get("mdd"),
                    turnover=r.get("turnover"), t=r.get("t"),
                    net_sharpe=mn.get("sharpe"),
                    vt_dsharpe=vt.get("d_sharpe"), vt_excess=vt.get("excess_cagr"))

    def d(x, y):
        return None if (x is None or y is None) else round(x - y, 4)

    b = load(BASE)
    legs = {}
    for q in DROP_QS:
        if not os.path.exists(RAW(q)):
            print("  [!] %s 없음 — 그 판은 건너뛴다" % os.path.basename(RAW(q)))
            continue
        f = json.load(io.open(FIREP(q), encoding="utf-8")) if os.path.exists(FIREP(q)) else {}
        legs[q] = (load(RAW(q)), f)

    rep = []
    for sid in CHAMPS:
        rb = b.get(sid)
        if not rb:
            print("  [!] %s — 기준선에 없다" % sid)
            continue
        row = {"sid": sid, "name": rb.get("name"), "base": grab(rb), "legs": {}}
        for q, (o, f) in legs.items():
            ro = o.get(sid)
            if not ro:
                continue
            go = grab(ro)
            fire = {k: v for k, v in (f.get("fire") or {}).items() if k.split("|")[0] == sid}
            seen = {k: v for k, v in (f.get("seen") or {}).items() if k.split("|")[0] == sid}
            slots = sum(seen.values())
            row["legs"]["%d" % int(q * 100)] = dict(
                over=go,
                d_sharpe=d(go["sharpe"], row["base"]["sharpe"]),
                d_cagr=d(go["cagr"], row["base"]["cagr"]),
                d_turnover=d(go["turnover"], row["base"]["turnover"]),
                d_net_sharpe=d(go["net_sharpe"], row["base"]["net_sharpe"]),
                d_vt_dsharpe=d(go["vt_dsharpe"], row["base"]["vt_dsharpe"]),
                fire_slots=sum(fire.values()), total_slots=slots,
                fire_pct=(round(sum(fire.values()) / slots * 100, 2) if slots else None),
                months=len(fire))
        rep.append(row)

    doc = {
        "note": ("E18 «구현 A» — 챔피언 바스켓에서 MAX(5) 상위 q 를 사전 배제한 뒤 동일가중 "
                 "top-N. 규약 build/PREREG-2026-08-29-ASWRITTEN.md §2. "
                 "🚨 이것은 규칙이 아니라 측정이다 — x-maxlow-n52 · x-max5low-n52 는 "
                 "이 결과와 무관하게 «십분위 정렬» 판 그대로다."),
        "screen": {"drop_quantiles": list(DROP_QS), "window_days": MAX_WIN, "max_k": MAX_K,
                   "rule": ("MAX(5) 상위 q 를 pool 에서 제외. 신호 없는 종목은 제외하지 않는다."),
                   "hook": "tech_backtest.xsec_score_at 의 pool — 엔진의 유일한 마스킹 자리"},
        "why_two_legs": ("카드가 «상위 10~20%» 라는 구간을 준다. 하나를 고르면 그것이 "
                         "PREREG-2026-08-29-ASWRITTEN §0 이 없앤 바로 그 자유도라, "
                         "양 끝을 다 돌려 나란히 싣는다."),
        "champions_source": ("PREREG-2026-08-28-REVSCREEN.md §1-1 이 돌리기 전에 못박은 목록 "
                             "그대로다 — 이 측정에서 새로 고르지 않았다."),
        "leg": "소급(retrospective). 시점정확 레그는 이 측정에서 안 돈다.",
        "champions": rep,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    print("\n%-12s %-22s %7s %8s %8s %8s %8s"
          % ("sid", "이름", "기준S", "dS(10%)", "dS(20%)", "발동10%", "발동20%"))
    for r in rep:
        l10 = r["legs"].get("10") or {}
        l20 = r["legs"].get("20") or {}
        print("%-12s %-22s %7.3f %+8.4f %+8.4f %7s%% %7s%%"
              % (r["sid"], (r["name"] or "")[:20], r["base"]["sharpe"] or 0,
                 l10.get("d_sharpe") or 0, l20.get("d_sharpe") or 0,
                 l10.get("fire_pct"), l20.get("fire_pct")))
    print("\n→ %s" % OUT)


def main():
    if "--report" not in sys.argv:
        for q in DROP_QS:
            run_one(q)
    report()


if __name__ == "__main__":
    main()
