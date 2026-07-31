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
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

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
_PRW = None      # 같은 구간 지수(PR) 기준선을 계산하는 함수. main()에서 한 번 만든다.

GRADE_ORDER = ["배포", "제한적 유효", "통과 후보", "역방향 유의", "구별 불가",
               "소수 사건 의존", "열위", "미채택", "판정 불가"]
ROLE_ORDER = ["수익엔진", "배분기", "위험감축", "타이밍오버레이", "미분류"]


# ── 대조군을 나란히 볼 수 있는가 ──────────────────────────────────────────
# 같은 표에 있다고 같은 잣대로 볼 수 있는 건 아니다. 대조군이 전략과 **같은 것을 목표로 할 때만**
# Δ샤프·초과수익을 우열로 읽을 수 있다.
#   수익엔진·배분기·타이밍오버레이 → 대조군과 목표가 같다(더 벌거나, 같은 위험에서 더 벌거나)
#   위험감축                      → 목표가 낙폭이다. 상시보유와 CAGR·샤프로 겨루면 지는 게 정상이고,
#                                 그 패배는 전략이 나쁘다는 뜻이 아니다 — 그래서 따로 뺀다.
# 여기에 표본 부족·대조군 현금(샤프 분모가 0에 가까워 Δ가 허수)을 더한다.
# ⚠ 방어보험은 2026-07-27 에 목록에서 사라졌지만(전 종목 제외) 여기에는 남긴다 — 제외를 되돌리면
#   대조군 판정이 먼저 필요해지고, 그때 이 집합에 없으면 CAGR·샤프로 우열을 매기는 오독이 되살아난다.
CMP_OFF_ROLE = {"위험감축", "방어보험"}


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
#   보인다. 판정은 각 전략의 대조군(TR 대 TR)으로 하고, 이 줄은 '세상의 눈금'으로만 읽는다.
def pr_baseline():
    A = load("assets.json") or {}
    dts, px = A.get("dates") or [], A.get("px") or {}
    if not dts:
        return None
    rf = (load("rf_monthly.json") or {}).get("monthly") or {}
    import sys as _s
    _s.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from tech_backtest import ann_stats            # noqa: E402  같은 계산을 두 번 쓰지 않는다
    idx = {d: i for i, d in enumerate(dts)}

    def window(start, end):
        """[start, end] 구간의 SPX·NDX 가격지수 성과. 구간이 자료 밖이면 None."""
        if not (start and end):
            return None
        ks = next((i for i, d in enumerate(dts) if d >= start), None)
        ke = next((i for i in range(len(dts) - 1, -1, -1) if dts[i] <= end), None)
        if ks is None or ke is None or ke - ks < 120:      # 반년도 안 되면 눈금이 못 된다
            return None
        out = {}
        for tk, lab in (("^GSPC", "spx"), ("^NDX", "ndx")):
            a = px.get(tk)
            if not a:
                continue
            nv = [x for x in a[ks:ke + 1] if x]
            if len(nv) < 120:
                continue
            base = nv[0]
            out[lab] = ann_stats([100.0 * x / base for x in nv], dts[ks:ke + 1], rf)
        return out or None
    return window


def rec(**kw):
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
        pr = _PRW(kw.get("start"), kw.get("end"))
        if pr:
            kw["pr"] = pr
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
    return {"win_bench": win_bench, "vs": out,
            "why": ("대조군 판정과 지수 눈금이 반대다 — "
                    + ("초과분이 대조군 대비로는 없는데 지수는 넘었다(대조군 성격에서 오는 이득일 수 있다)."
                       if not win_bench else
                       "대조군은 넘었지만 살 수 있는 지수는 못 넘었다."))}


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
                "weights": [(x.get("t") or x.get("n"), x.get("w")) for x in pos
                            if x.get("w") is not None],
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
            rule=x.get("t"), why=x.get("vt"),
            start=b.get("start"), end=b.get("end"),
            metrics={"cagr": m.get("cagr"), "sharpe": m.get("sharpe"), "mdd": b.get("mdd_b") and m.get("mdd") or m.get("mdd")},
            bench={"label": b.get("bench_label"), "cagr": bm.get("cagr"), "sharpe": bm.get("sharpe")},
            nav=b.get("nav"), bnav=b.get("bench"),
            bench_label=b.get("bench_label"),
            holdings=HOLD_DEP.get(n),
            has_detail=True,
        ))

    # ── ② 종목 전략 ──
    t = load("tech_strategies.json") or {}
    # SPX(TR) Sharpe 미달 종목선택 제외는 2026-07-28 에 **되돌렸다**(사용자 결정).
    # 종목 전략은 전부 목록에 싣는다 — 판정(등급)이 이미 그 정보를 담고 있고, 목록에서까지
    # 빼면 '무엇을 재고 무엇을 버렸나'가 화면에서 사라진다.
    _hidden, _hidden_bond, _hidden_sids = [], [], set()
    for r in (t.get("strategies") or []):
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
            metrics=r.get("metrics") or {}, bench=dict(r.get("bench") or {},
                                                       label=t.get("bench_label")),
            d_sharpe=r.get("d_sharpe"), t=r.get("t"), turnover=r.get("turnover"),
            holdings=r.get("holdings"), nav=r.get("nav"), bnav=r.get("bnav"),
            arch=r.get("arch"),
            # 시점정확(PIT) 실측 — build/pit_backtest.py 가 같은 창에서 소급 레그와 함께 잰 것.
            # ⚠ 전에는 이 값이 판정 강등에만 쓰이고 **화면에는 숫자가 안 나갔다**. 편향을 재
            #   놓고 안 보여주면 독자는 소급 수치만 보게 된다 — 목록에 실어 카드가 적게 한다.
            pit=r.get("pit"),
            # 가장 닮은 규칙 대비 증분 알파 — '이걸 이미 들고 있으면 이게 더 주는 게 있나'.
            # 단독 t 만 보면 같은 베팅을 여러 번 센다(에코 모멘텀 단독 3.80 → 증분 0.85).
            incr=r.get("incr"),
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
            bench_label=r.get("bench_label"),
            start=r.get("start"), end=r.get("end"),
            metrics=r.get("metrics") or {}, bench=r.get("bench") or {},
            d_sharpe=r.get("d_sharpe"), t=r.get("t"), turnover=r.get("turnover"),
            bench_unstable=r.get("bench_unstable"), beta=r.get("beta"),
            holdings=r.get("holdings"), nav=r.get("nav"), bnav=r.get("bnav"),
            arch=r.get("arch"),
            # 위험 축 — 수익 축(grade)과 다른 질문에 답한다. 같이 실어야 '덜 벌었지만
            # 덜 깨졌다'가 화면에서 읽힌다. 자산 전략에만 있다(다른 원천은 없음).
            risk_verdict=r.get("risk_verdict"), risk=r.get("risk"),
            # 비용 후 — 회전이 큰 규칙은 무비용 숫자만 보면 안 된다. gross 를 대체하지 않고 함께 싣는다.
            metrics_net=r.get("metrics_net"), bench_net=r.get("bench_net"),
            cost_bp=r.get("cost_bp"), cost_drag=r.get("cost_drag"),
            cost_kill=r.get("cost_kill"), cost_sensitive=r.get("cost_sensitive"),
        ))

    # ── ④ 기각 재검 ── 배포하지 않는 것이므로 등급은 '미채택'으로 못 박는다.
    # 성격은 규칙이 하는 일로 정한다(재검 산출물에는 role이 없다).
    RECHK_ROLE = {
        # vol-targeting-ndx 는 2026-07-30 에 삭제됐다(archive_index·archive_backtests 양쪽에서).
        "low-beta-weight-tilt": "위험감축",
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
            bench_label=b.get("bench_label") or ((b.get("metrics") or {}).get("b") or {}).get("label"),
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
    }
    # ⚠ 이 가드는 'sid 가 바뀌어 제외가 조용히 풀렸나'를 보는 것이다. 그런데 앞의 채권 대조군
    #   필터가 먼저 지운 전략은 rows 에 없어 '못 찾음'으로 오인된다 — 두 제외는 공존해야 한다.
    #   그래서 이미 다른 사유로 빠진 sid 도 찾은 것으로 센다.
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
        "n": len(rows),
        # 의도적으로 목록에서 뺀 것들. validate 의 '원본 합계와 맞나' 가드가 이 수를 더해
        # 검사하므로, 여기 기록하지 않으면 낡은 목록 검출이 무력해진다.
        "n_hidden": len(_hidden) + len(_hid2),
        "hidden": ([{"name": _n, "sharpe": _s} for _n, _s in sorted(_hidden, key=lambda x: -x[1])]
                   + [{"name": _n, "role": _r} for _n, _r in sorted(_hid2, key=lambda x: (x[1], x[0]))]),
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
        "holds_order": ["종목", "비중", "노출", "없음"],
        "pr_note": "‘같은 구간 지수(PR)’는 판정용이 아니라 세상의 눈금이다. 전략 수익은 배당을 "
                   "재투자한 총수익(TR)인데 지수는 가격지수(PR)라 배당이 빠져 있고, 2006년 이후 "
                   "그 격차가 연 2.0%p다 — PR과 겨루면 전략이 그만큼 유리해 보인다. "
                   "판정은 각 전략의 대조군(TR 대 TR)으로 한다.",
        "cmp_note": "대조군이 전략과 같은 것을 목표로 할 때만 Δ샤프를 우열로 읽을 수 있다. "
                    "위험감축은 목표가 낙폭이라 상시보유와 CAGR·샤프로 겨루면 "
                    "지는 것이 정상이고, 대조군이 현금성이면 샤프 분모가 0에 가까워 Δ가 허수가 된다. "
                    "그런 전략은 따로 묶어 낙폭·위기 구간으로 본다.",
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
