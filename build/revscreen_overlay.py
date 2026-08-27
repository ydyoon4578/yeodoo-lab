# -*- coding: utf-8 -*-
"""build/revscreen_overlay.py — 하향 리비전 네거티브 스크린 오버레이 → data/revscreen.json

규약: build/PREREG-2026-08-28-REVSCREEN.md (계산 전 커밋 c5cbc0fd · 규칙·예상·실패 조건).

  전략 탐색 풀 E21 을 **오버레이**로 세운다. 챔피언이 이미 고른 것에서 하향 리비전
  하위 10% 를 빼기만 한다. 뺀 자리는 챔피언 차순위가 자동으로 올라온다.

🚨 엔진(tech_backtest.py)을 고치지 않는다. 밖에서 `xsec_score_at` 을 감싸 pool 만 좁힌다.
  ① 마스킹은 그 함수 한 자리에서만 한다고 엔진 머리말이 못 박아 두었고(사전패스까지
     같이 좁아진다 — 갈래마다 거르면 선견이 된다), PIT 레그가 쓰는 경로가 그것이다.
  ② 다른 세션이 같은 저장소에서 일하는 중이라 공용 엔진은 안 건드리는 편이 안전하다.
  ③ 채점·선택 규칙을 **한 줄도 베끼지 않는다.** 사본을 만들면 두 벌이 되고 한쪽만
     고쳐지는 날이 온다(이 저장소가 되풀이 밟은 사고다).

🚨 사이트 산출물을 덮어쓰지 않는다 — TB.OUT 을 로컬 캐시로 돌린다(밑줄 접두 규약).
🚨 등급 원자료(data/_ratings_cache.json)는 커밋 금지다. 이 측정은 러너가 재생산할 수 없는
  얼린 측정이고 산출물엔 요약만 싣는다.

    python build/revscreen_overlay.py
"""
from __future__ import annotations
import io
import json
import math
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

OUT = os.path.join(DATA, "revscreen.json")
RAW = os.path.join(DATA, "_revscreen_raw.json")      # 밑줄 = 로컬 전용(커밋 금지)
FIREP = os.path.join(DATA, "_revscreen_fire.json")   # 발동률 집계 — report() 가 단독으로 돌게
BASE = os.path.join(DATA, "tech_strategies.json")    # 기준선 = 엔진이 이미 낸 값

# ── 사전등록 §1 의 상수 — 결과를 보고 만지지 않는다 ─────────────────────────
CHAMPS = ["x-sp", "x-dist200", "x-custconc", "x-sue"]
CAL_DAYS = 91          # 63영업일 ≈ 3개월. x-revdrift-q 와 같은 창(새 상수를 만들지 않는다)
DROP_Q = 0.10          # 하위 10% — Loh-Stulz 의 «영향력 있는 변경 12%» 에 맞춘 값

FIRE = {}              # (sid, 날짜) → 스크린 때문에 바스켓에서 빠진 자리 수
SEEN = {}              # (sid, 날짜) → 그날 바스켓 크기
DROPN = {}             # 날짜 → 그날 제외한 종목 수


def main():
    import tech_backtest as TB

    TB.OUT = RAW                       # 🚨 사이트 산출물을 덮어쓰지 않는다
    _orig = TB.xsec_score_at
    _memo = {}

    def drop_at(sig_date):
        """그 신호일에 뺄 종목 — 신호가 있는 종목 중 하위 DROP_Q."""
        if sig_date in _memo:
            return _memo[sig_date]
        vals = []
        for t in (TB._RAT or {}):
            v = TB.rat_signal(t, sig_date, CAL_DAYS)
            if v is not None and v == v:
                vals.append((v, t))
        # ⚠ 신호가 **없는** 종목은 빼지 않는다 — 모르는 것을 나쁜 것이라 부르지 않는다.
        vals.sort()                                        # 오름차순 = 하향이 앞
        k = int(len(vals) * DROP_Q)
        out = {t for _v, t in vals[:k]}
        _memo[sig_date] = out
        DROPN[sig_date] = len(out)
        return out

    def screened(S, i, X, pool=None):
        sig = X["dates"][i - 1]
        drop = drop_at(sig)
        base = set(X["tickers"]) if pool is None else set(pool)
        sc = _orig(S, i, X, base - drop)
        # 발동률 — 챔피언에 한해 «스크린이 없었다면 뽑혔을 자리» 중 몇이 빠졌나를 센다.
        #   ⚠ 이걸 안 재면 «오버레이가 아무것도 안 했는데 성적이 같다» 를 «효과 없음» 으로
        #     잘못 읽는다. 사전등록 §4-1 의 공허 판정이 이 수로 갈린다.
        if TB._BASE_SID(S["sid"]) in CHAMPS:
            # ⚠ xsec_score_at 은 (sc, ind_raw, comp_raw) 3-튜플이다. 그냥 자르면
            #   튜플이 잘려 나온다 — 한 번 밟았다.
            sc0, _ir0, _cr0 = _orig(S, i, X, base)
            n = S.get("topn") or TB.TOPN
            top0 = [t for _v, t in sc0[:n]]
            key = (S["sid"], sig)
            FIRE[key] = sum(1 for t in top0 if t in drop)
            SEEN[key] = len(top0)
        return sc

    TB.xsec_score_at = screened
    print("스크린 걸었다 — 챔피언 %s · 창 %d일 · 하위 %.0f%%"
          % ("·".join(CHAMPS), CAL_DAYS, DROP_Q * 100))
    print("산출물은 %s 로 돌린다(사이트 파일 안 건드림)\n" % os.path.basename(RAW))
    TB.run()
    # 발동률을 파일로 남긴다 — 안 남기면 report() 를 다시 부를 때마다 랩을 통째로
    #   다시 돌려야 한다(10분). 키는 튜플이라 문자열로 접어서 담는다.
    io.open(FIREP, "w", encoding="utf-8").write(json.dumps(
        {"fire": {"%s|%s" % k: v for k, v in FIRE.items()},
         "seen": {"%s|%s" % k: v for k, v in SEEN.items()},
         "dropn": DROPN}, ensure_ascii=False))
    report()


def report():
    """두 산출물을 맞대어 data/revscreen.json 을 짠다 — 엔진 재실행 없이도 돈다."""
    def load(p):
        d = json.load(io.open(p, encoding="utf-8"))
        rows = d.get("strategies") or d.get("items") or d.get("rows") or []
        return {r.get("sid"): r for r in rows if r.get("sid")}

    # FIRE 가 비어 있으면(=엔진을 안 돌리고 report 만 부른 경우) 파일에서 되살린다.
    if not FIRE and os.path.exists(FIREP):
        _f = json.load(io.open(FIREP, encoding="utf-8"))
        for k, v in (_f.get("fire") or {}).items():
            FIRE[tuple(k.split("|", 1))] = v
        for k, v in (_f.get("seen") or {}).items():
            SEEN[tuple(k.split("|", 1))] = v
        DROPN.update(_f.get("dropn") or {})

    b, o = load(BASE), load(RAW)

    def grab(r):
        """🚨 turnover·vs_traded 는 **최상위** 필드다. metrics 에는 cagr/vol/sharpe/mdd 뿐이다.
        metrics 안에서 찾으면 None 이 되고 차이가 조용히 0 이 된다 — 한 번 밟았다."""
        m = r.get("metrics") or {}
        mn = r.get("metrics_net") or {}
        vt = r.get("vs_traded") or {}
        return dict(cagr=m.get("cagr"), vol=m.get("vol"), sharpe=m.get("sharpe"),
                    mdd=m.get("mdd"), turnover=r.get("turnover"),
                    net_sharpe=mn.get("sharpe"), net_cagr=mn.get("cagr"),
                    cost_drag=r.get("cost_drag"), cost_kill=r.get("cost_kill"),
                    # 랩 동일가중 유니버스 대비 — x-revdrift 를 죽인 수가 이것이다
                    vt_dsharpe=vt.get("d_sharpe"), vt_excess=vt.get("excess_cagr"),
                    vt_t=vt.get("t"))

    def d(x, y):
        return None if (x is None or y is None) else round(x - y, 4)

    rep = []
    for sid in CHAMPS:
        rb, ro = b.get(sid), o.get(sid)
        if not rb or not ro:
            print("  [!] %s — 기준선 %s · 오버레이 %s" % (sid, bool(rb), bool(ro)))
            continue
        gb, go = grab(rb), grab(ro)
        fired = [(k, v) for k, v in FIRE.items()
                 if k[0] == sid or k[0].startswith(sid + "-")]
        slots = sum(SEEN[k] for k, _v in fired)
        rep.append(dict(
            sid=sid, name=rb.get("name"), base=gb, over=go,
            d_sharpe=d(go["sharpe"], gb["sharpe"]),
            d_cagr=d(go["cagr"], gb["cagr"]),
            d_turnover=d(go["turnover"], gb["turnover"]),
            d_net_sharpe=d(go["net_sharpe"], gb["net_sharpe"]),
            d_vt_dsharpe=d(go["vt_dsharpe"], gb["vt_dsharpe"]),
            fire_slots=sum(v for _k, v in fired), total_slots=slots,
            fire_pct=(round(sum(v for _k, v in fired) / slots * 100, 2) if slots else None),
            months=len(fired),
        ))

    doc = {
        "note": ("하향 리비전 네거티브 스크린 오버레이. 규약 build/PREREG-2026-08-28-REVSCREEN.md. "
                 "🚨 등급 원자료(data/_ratings_cache.json)는 커밋하지 않는다 — 러너가 재생산할 수 "
                 "없는 얼린 측정이고 여기엔 요약만 있다."),
        "screen": {"cal_days": CAL_DAYS, "drop_quantile": DROP_Q,
                   "rule": "rat_signal 하위 10% 를 pool 에서 제외. 신호 없는 종목은 제외하지 않는다.",
                   "hook": "tech_backtest.xsec_score_at 의 pool — 엔진의 유일한 마스킹 자리"},
        "leg": "소급(retrospective). 시점정확 레그는 이 등록에서 안 돈다(PREREG §5).",
        "baseline_note": ("기준선은 엔진 자신이 낸 data/tech_strategies.json 이다 — 같은 배선이라 "
                          "사전등록 §4-5(기준선 불일치)는 구조적으로 만족한다."),
        "vs_traded_note": ("vt_dsharpe 는 «랩 동일가중 유니버스 매수후보유» 대비 샤프차다. "
                           "x-revdrift 3종을 죽인 수가 이것이었다(지수 대비로는 +6.3%p 인데 "
                           "매매 대상 대비로는 −0.062). 지수 대비만 보면 같은 착시를 되풀이한다."),
        "champions": rep,
        "drop_universe_mean": (round(sum(DROPN.values()) / len(DROPN), 1) if DROPN else None),
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    print("\n%-11s %-24s %7s %7s %8s %7s %7s %8s" %
          ("sid", "이름", "기준S", "오버S", "dS", "회전전", "회전후", "d매매대비"))
    for r in rep:
        print("%-11s %-24s %7.3f %7.3f %+8.4f %7.2f %7.2f %+8.4f" %
              (r["sid"], (r["name"] or "")[:22], r["base"]["sharpe"] or 0,
               r["over"]["sharpe"] or 0, r["d_sharpe"] or 0,
               r["base"]["turnover"] or 0, r["over"]["turnover"] or 0,
               r["d_vt_dsharpe"] or 0))
    print()
    for r in rep:
        print("  %-11s 발동 %5.2f%% (%d자리/%d · %d개월) · 비용뒤 샤프 %.3f→%.3f"
              % (r["sid"], r["fire_pct"] or 0, r["fire_slots"], r["total_slots"],
                 r["months"], r["base"]["net_sharpe"] or 0, r["over"]["net_sharpe"] or 0))
    print("\n제외 종목 수 평균 %s / 월 → %s" % (
        (round(sum(DROPN.values()) / len(DROPN), 1) if DROPN else "—"), OUT))


if __name__ == "__main__":
    main()
