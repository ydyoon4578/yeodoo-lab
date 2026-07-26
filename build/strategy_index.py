# -*- coding: utf-8 -*-
"""build/strategy_index.py — 전 전략을 한 목록으로 → data/strategy_index.json

왜 만드는가. 전략이 네 군데(배포 원장·종목 랩·자산 랩·기각 재검)에 흩어져 있었다. 그 나눔은
**전략이 무엇을 하는가가 아니라 어느 파일에서 나왔는가**를 따른 것이라, 보는 사람에게는
같은 것을 네 번 다르게 보여주는 셈이었다. 여기서 하나로 합친다.

묶는 축은 **성격(role)** 이다 — strategy_kinds.json의 어휘를 그대로 쓴다.
  수익엔진      무엇을 살지 고르는 전략(초과수익이 목적)
  배분기        얼마씩 담을지 정하는 전략
  위험감축      모전략의 노출을 줄여 낙폭을 관리
  방어보험      위기에만 값을 하는 보험(평시 비용)
  타이밍오버레이 한 자산에 들어갈지 나갈지만 결정

같은 숫자를 세로로 비교하면 안 되기 때문에 성격이 첫 축이다 — 종목을 고르는 전략은 수익으로,
배분기는 샤프로, 오버레이는 낙폭으로 본다.

⚠ 수치는 **원본에서 그대로 옮긴다**. 여기서 새로 계산하지 않는다. 구간·대조군이 전략마다
   다르므로 그 사실을 record마다 싣고, 화면이 "같은 눈금이 아니다"를 말할 수 있게 한다.

  python build/strategy_index.py
"""
from __future__ import annotations
import io, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "strategy_index.json")

# 등급 — '배포북에 넣을 것인가'에 대한 답. 랩 판정은 그 어휘로 옮긴다.
GRADE = {
    "deploy": "배포", "marginal": "제한적 유효", "reject": "미채택",
    "통과 후보": "통과 후보", "관례대로 유효": "통과 후보",
    "구별 불가": "구별 불가", "대조군 열위": "열위", "열위": "열위",
    "표본 부족 · 판정 불가": "판정 불가", "판정 불가": "판정 불가",
    "관례와 반대로 유의": "역방향 유의", "소수 사건 의존": "소수 사건 의존",
}
GRADE_ORDER = ["배포", "제한적 유효", "통과 후보", "역방향 유의", "구별 불가",
               "소수 사건 의존", "열위", "미채택", "판정 불가"]
ROLE_ORDER = ["수익엔진", "배분기", "위험감축", "방어보험", "타이밍오버레이", "미분류"]


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


def rec(**kw):
    for key in ("nav", "bnav"):
        if kw.get(key):
            kw[key] = thin(kw[key])
    kw.setdefault("role", "미분류")
    kw.setdefault("grade", "판정 불가")
    return kw


def main() -> int:
    rows = []

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
            rule=x.get("t"), why=x.get("vt"),
            start=b.get("start"), end=b.get("end"),
            metrics={"cagr": m.get("cagr"), "sharpe": m.get("sharpe"), "mdd": b.get("mdd_b") and m.get("mdd") or m.get("mdd")},
            bench={"label": b.get("bench_label"), "cagr": bm.get("cagr"), "sharpe": bm.get("sharpe")},
            nav=b.get("nav"), bnav=b.get("bench"),
            has_detail=True,
        ))

    # ── ② 종목 전략 ──
    t = load("tech_strategies.json") or {}
    for r in (t.get("strategies") or []):
        rows.append(rec(
            sid="t-" + r["sid"], name=r["name"], role=r.get("role") or "미분류",
            grade=GRADE.get(r.get("verdict"), r.get("verdict") or "판정 불가"),
            src="종목 전략", rule=r.get("rule"), why=r.get("why"),
            start=t.get("start"), end=t.get("as_of"),
            metrics=r.get("metrics") or {}, bench=dict(r.get("bench") or {},
                                                       label=t.get("bench_label")),
            d_sharpe=r.get("d_sharpe"), t=r.get("t"), turnover=r.get("turnover"),
            holdings=r.get("holdings"), nav=r.get("nav"), bnav=r.get("bnav"),
            arch=r.get("arch"),
        ))

    # ── ③ 자산배분 · 머신러닝 · 복제 ──
    a = load("asset_strategies.json") or {}
    for r in (a.get("strategies") or []):
        rows.append(rec(
            sid="a-" + r["sid"], name=r["name"], role=r.get("role") or "배분기",
            grade=GRADE.get(r.get("verdict"), r.get("verdict") or "판정 불가"),
            src="자산배분", rule=r.get("rule"), why=r.get("why"), note=r.get("note"),
            start=r.get("start"), end=r.get("end"),
            metrics=r.get("metrics") or {}, bench=r.get("bench") or {},
            d_sharpe=r.get("d_sharpe"), t=r.get("t"), turnover=r.get("turnover"),
            bench_unstable=r.get("bench_unstable"), beta=r.get("beta"),
            holdings=r.get("holdings"), nav=r.get("nav"), bnav=r.get("bnav"),
            arch=r.get("arch"),
        ))

    # ── ④ 기각 재검 ── 배포하지 않는 것이므로 등급은 '미채택'으로 못 박는다.
    # 성격은 규칙이 하는 일로 정한다(재검 산출물에는 role이 없다).
    RECHK_ROLE = {
        "vol-targeting-ndx": "위험감축", "low-beta-weight-tilt": "위험감축",
        "bond-trend-gate": "타이밍오버레이", "cross-asset-rp-extended": "배분기",
        "tail-risk-hedge": "방어보험",
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
            rule="기각한 전략을 단독으로 다시 검정한 결과다. 원 기각 사유가 "
                 "'배포 포트폴리오에 얹으면 개선이 없다'는 상대 판정이었기 때문이다.",
            why=x.get("r"),
            start=b.get("start"), end=b.get("end"),
            metrics={"cagr": m.get("cagr"), "sharpe": m.get("sharpe"), "mdd": m.get("mdd")},
            bench={"label": b.get("bench_label") or (bm.get("label")), "cagr": bm.get("cagr"),
                   "sharpe": bm.get("sharpe")},
            d_sharpe=(round(m["sharpe"] - bm["sharpe"], 3)
                      if m.get("sharpe") is not None and bm.get("sharpe") is not None else None),
            nav=b.get("nav"), bnav=b.get("bench"),
        ))

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
        "n": len(rows),
        "role_order": ROLE_ORDER, "grade_order": GRADE_ORDER,
        "by_role": dict(Counter(r["role"] for r in rows)),
        "by_grade": dict(Counter(r["grade"] for r in rows)),
        "by_src": dict(Counter(r["src"] for r in rows)),
        "items": rows,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("전략 통합 %d개 · %.0fKB" % (len(rows), os.path.getsize(OUT) / 1024))
    print("  성격:", doc["by_role"])
    print("  등급:", doc["by_grade"])
    print("  출처:", doc["by_src"])
    miss = [r["name"] for r in rows if r["role"] == "미분류"]
    if miss:
        print("  ⚠ 성격 미분류 %d건: %s" % (len(miss), ", ".join(m[:20] for m in miss[:6])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
