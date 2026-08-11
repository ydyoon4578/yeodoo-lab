# -*- coding: utf-8 -*-
"""전략별 상세 리포트를 굽는다 — 판정이 아니라 **복제 결과**를 낸다.

🚨 2026-08-07 · 왜 만들었나 (사용자 요청).
  "쓸모있고 없는지 결정하지말고, 전략을 그대로 따라하고 복제해 결과를 상세하게 뽑는 데
   집중해. 전략별로 상세하게 리포트 형식으로. 전체 전략에 대해서."

  이 랩은 그동안 **판정**을 앞세웠다 — 통과/구별 불가/열위. 그 판정은 문턱 하나로 압축한
  요약이라, 그 규칙이 실제로 무엇을 했는지는 뒤로 밀렸다. 이 리포트는 순서를 뒤집는다:
  **잰 것을 전부 늘어놓고, 판정은 그중 한 줄로만 적는다.**

  ⚠ 새로 재지 않는다. 전부 tech_strategies·asset_strategies·pit_strategies 가 이미 실은
    값을 옮긴다. 여기서 다시 계산하면 채점기가 두 벌이 되고, 두 화면이 다른 숫자를
    말하는 사고가 난다 — 이 저장소가 이미 여러 번 당한 그것이다.

## 두 랩의 스키마가 다르다 — 여기서 맞춘다

  | | 자산 랩(51) | 종목 랩(66) |
  |---|---|---|
  | 비용 | `cost_bp` **왕복 5bp** 한 점 | `net.sens` **편도** 5·10·20bp |
  | 위험 부트스트랩 | 있다(48/51) | 없다 |
  | PIT 레그 | 없다 | 34종 |
  | 매매대상 대비 | 없다 | 66종 |
  | 후보 풀 | 없다 | 45종(횡단면) |
  | 초과 CAGR | 필드 없음(= CAGR 차) | `excess_cagr` |

  🚨 **비용은 왕복으로 통일한다.** 자산 랩 5 와 종목 랩 5 는 같은 5 가 아니다
    (전자는 왕복, 후자는 편도=왕복 10). 한 열에 그대로 놓으면 자산 랩이 두 배 비싸
    보인다. tech_backtest.py:3595 가 미리 경고해 둔 자리다.
  ⚠ 왕복으로 맞춰도 **크기를 나란히 비교하면 안 된다** — 자산 랩은 ETF 를, 종목 랩은
    개별주 10종을 매매한다. 같은 왕복 20bp 가 서로 다른 현실성을 갖는다.

## 값이 없으면 '—' 로 두고 왜 없는지 적는다

  빈칸을 지우면 그 규칙이 그 항목을 **통과한 것처럼** 읽힌다. 없는 이유는 대개
  "그 족에 그 측정이 아예 없다"이지 "재 봤더니 안 나왔다"가 아니다 — 그 구별을 남긴다.
"""
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "strategy_report.json")

DROP = ("dates", "nav", "bnav", "chart")   # 리포트가 안 쓰는 계열 — 그대로 실으면 수 MB 다


def _load(fn):
    try:
        return json.load(io.open(os.path.join(DATA, fn), encoding="utf-8"))
    except FileNotFoundError:
        return {}


def _f(x, nd=2):
    """숫자 한 칸. None 은 '—'. 🚨 0 으로 채우지 않는다 — 0 은 '쟀는데 0' 이라는 뜻이다."""
    if x is None or (isinstance(x, float) and x != x):
        return None
    try:
        return round(float(x), nd)
    except (TypeError, ValueError):
        return None


def _sub(a, b, nd=2):
    a, b = _f(a, nd), _f(b, nd)
    return round(a - b, nd) if (a is not None and b is not None) else None


def _perf(m, b):
    """전략·대조군·차를 **같은 줄에** 놓는다. 따로 적으면 읽는 사람이 뺄셈을 해야 한다."""
    m, b = m or {}, b or {}
    rows = []
    for k, lab, nd in (("cagr", "연복리수익률", 2), ("vol", "변동성", 2),
                       ("sharpe", "샤프", 3), ("mdd", "최대낙폭", 2)):
        rows.append({"k": lab, "s": _f(m.get(k), nd), "b": _f(b.get(k), nd),
                     "d": _sub(m.get(k), b.get(k), nd)})
    return rows


def _cost(r, fam):
    """비용 — **왕복 bp** 로 통일한다. 두 랩의 원 단위가 다르다(모듈 머리말 참조)."""
    rows, unit = [], None
    net = r.get("net") or {}
    sens = net.get("sens") or {}
    if sens:                                  # 종목 랩 — 편도 5·10·20 을 왕복으로 환산
        unit = "종목 랩은 편도 bp 로 재고 여기서 왕복(×2)으로 적는다"
        for ow in ("5", "10", "20"):
            s = sens.get(ow) or {}
            if not s:
                continue
            rows.append({"rt": int(ow) * 2, "cagr": _f(s.get("cagr")),
                         "sharpe": _f(s.get("sharpe"), 3),
                         "excess": _f(s.get("excess_cagr")), "t": _f(s.get("t")),
                         "main": int(ow) == (net.get("bps") or 10)})
    elif r.get("cost_bp") is not None:        # 자산 랩 — 왕복 한 점뿐
        unit = "자산 랩은 왕복 bp 한 점만 잰다 — 감응 곡선이 없다"
        mn, bn = r.get("metrics_net") or {}, r.get("bench_net") or {}
        rows.append({"rt": _f(r.get("cost_bp"), 1), "cagr": _f(mn.get("cagr")),
                     "sharpe": _f(mn.get("sharpe"), 3),
                     "excess": _sub(mn.get("cagr"), bn.get("cagr")), "t": None,
                     "main": True})
    if not rows:
        return None
    return {"unit": unit, "rows": rows,
            "drag": _f(r.get("cost_drag")),
            "traded": _f(net.get("traded")) if net else None,
            "kill": r.get("cost_kill"), "sensitive": r.get("cost_sensitive"),
            "bench_pays": (fam == "자산배분"),
            # 🚨 대조군이 비용을 무는지가 두 랩에서 다르다. 종목 랩 대조군은 매수후보유라
            #   회전이 0 이고, 자산 랩 대조군(60/40 등)은 리밸런싱을 해서 비용을 문다.
            #   이걸 모르면 "종목 랩은 비용에 강하다"고 잘못 읽는다.
            "note": ("대조군도 같은 비용을 문다(리밸런싱한다)" if fam == "자산배분"
                     else "대조군은 매수후보유라 비용 0 이다 — 전략만 비용을 문다")}


def _risk(r):
    """위험 축 — 부트스트랩 p 를 값 옆에 붙인다. p 없이 차이만 보면 잡음을 읽는다."""
    rk = r.get("risk")
    if not rk:
        return None
    return {"rows": [{"k": "최대낙폭 개선(%p)", "v": _f(rk.get("d_mdd")), "p": _f(rk.get("p_mdd"), 4)},
                     {"k": "꼬리위험 CVaR 개선", "v": _f(rk.get("d_cvar"), 3), "p": _f(rk.get("p_cvar"), 4)},
                     {"k": "낙폭조정수익 Calmar 개선", "v": _f(rk.get("d_calmar"), 3), "p": _f(rk.get("p_calmar"), 4)}],
            "n_boot": rk.get("n_boot"), "block": rk.get("block"),
            "verdict": r.get("risk_verdict")}


def _incr(r, dup_of):
    """증분알파 — **이웃 이름까지** 낸다. 't 1.2' 만으로는 무엇에 막혔는지 알 수 없다."""
    i1, i5 = r.get("incr") or {}, r.get("incr5") or {}
    out = {
        "one": ({"vs": i1.get("vs"), "corr": _f(i1.get("corr"), 3), "alpha": _f(i1.get("alpha")),
                 "t": _f(i1.get("t")), "beta": _f(i1.get("beta"), 3)} if i1 else None),
        "five": ({"alpha": _f(i5.get("alpha")), "t": _f(i5.get("t")), "n": i5.get("n"),
                  "vs": i5.get("vs") or []} if i5 else None),
        "absorbed": dup_of,
        "note": "이웃은 **이 랩 안에서만** 고른다. 랩 밖의 무언가와 겹치는지는 재지 않았다.",
    }
    return out


def _pit(r, pit_rec):
    """PIT — 같은 창의 소급 레그(retro)를 **나란히** 놓는다.

    🚨 랩 본편(더 긴 창)과 직접 빼면 안 된다. 창이 달라 구간 차이가 편향으로 위장한다.
      pit_strategies 의 retro 는 **같은 창**에서 오늘 유니버스로 다시 돌린 것이다.
    🚨 편향은 bias_cagr(전략 CAGR 기준)로 읽는다. bias_excess 는 두 레그의 대조군이
      각자의 동일가중 지수라 벤치에 실린 편향(bench_bias_cagr)이 상쇄돼, '편향 없음' 과
      'PIT 가 유리' 를 구별하지 못한다(pit_strategies.limits 가 적어 둔 사고다).
    """
    p = pit_rec or r.get("pit")
    if not p:
        return None
    ret = p.get("retro") or {}
    rm, rb = ret.get("metrics") or {}, ret.get("bench") or {}
    emb = r.get("pit") or {}
    return {
        "window": emb.get("window"), "start": p.get("start"), "n_days": p.get("n_days"),
        "pit": {"cagr": _f((p.get("metrics") or {}).get("cagr") or p.get("cagr")),
                "sharpe": _f((p.get("metrics") or {}).get("sharpe") or p.get("sharpe"), 3),
                "mdd": _f((p.get("metrics") or {}).get("mdd")),
                "bench_cagr": _f((p.get("bench") or {}).get("cagr") or emb.get("bench_cagr")),
                "excess": _f(p.get("excess_cagr")), "t": _f(p.get("t")),
                "d_sharpe": _f(p.get("d_sharpe"), 3), "turnover": _f(p.get("turnover"))},
        "retro": ({"cagr": _f(rm.get("cagr")), "sharpe": _f(rm.get("sharpe"), 3),
                   "mdd": _f(rm.get("mdd")), "bench_cagr": _f(rb.get("cagr")),
                   "excess": _f(ret.get("excess_cagr")), "t": _f(ret.get("t"))} if ret else None),
        "bias": {"cagr": _f(p.get("bias_cagr")), "excess": _f(p.get("bias_excess")),
                 "sharpe": _f(p.get("bias_sharpe"), 3),
                 "bench_cagr": _f(p.get("bench_bias_cagr"))},
        "t_crit": _f(emb.get("t_crit")), "t_crit_lab": _f(emb.get("t_crit_lab")),
        "holdings": (p.get("holdings") or {}).get("tickers"),
    }


def _refs(sid, fam, kind, refs, fund_sids, has_pit):
    """전략별 참고 — 논문과 **이 규칙이 실제로 쓴 자료**.

    🚨 URL 을 지어내지 않는다. 저장소가 가진 링크가 아니면 제목으로 학술검색 질의를
      만들어 화면이 건다(결정적이고 항상 열린다). 논문을 특정 못 한 규칙은 **비운다** —
      없는 것을 지어 채우면 독자가 원문을 못 찾고 그 사실조차 모른다.

    ⚠ 자료 쪽은 추측이 아니다. 어느 규칙이 재무를 쓰는지는 tech_backtest.FUND_SIDS 가,
      PIT 레그가 있는지는 산출물이 알고 있다 — 그 두 사실에서 만든다.
    """
    papers = (refs.get("papers") or {}).get(sid) or []
    src = []
    if fam == "종목·타이밍":
        src.append({"k": "일봉 OHLCV", "v": "yfinance — S&P 500 ∪ NASDAQ 100 오늘의 518종목"})
        if sid in fund_sids:
            src.append({"k": "재무", "v": "SEC XBRL 회사팩트(data/fx) — 공시지연 반영 후에만 읽는다"})
        if has_pit:
            src.append({"k": "지수 편입 이력", "v": "위키백과 과거 리비전(data/index_history.json) — PIT 레그"})
        if sid == "x-custconc":
            src.append({"k": "고객 집중도", "v": "SEC 10-K 본문 추출(data/cust_conc.json)"})
    else:
        src.append({"k": "가격", "v": "yfinance — ETF·지수 종가"})
        src.append({"k": "거시", "v": "FRED 공개 CSV(무인증) · 일부는 연준 공개 CSV"})
        if sid == "guru-clone":
            src.append({"k": "13F", "v": "SEC 13F 보유(제출 마감 45일 지연 반영)"})
    src.append({"k": "무위험이자율", "v": "FRED DGS3MO 월평균을 일할로 환산해 차감"})
    return {"papers": papers, "src": src,
            "no_paper": (not papers),
            "note": ("원 논문을 특정하지 못했다 — 이 랩이 자료 사정에 맞춰 만든 변형이거나 "
                     "실무 관행이라 단일 출처가 없다. **비워 두는 것이 정직하다.**"
                     if not papers else None)}


def _one(r, fam, tcrit, audit_of, dup_of, pit_of, lab, refs, fund_sids):
    sid = r.get("sid")
    m, b = r.get("metrics") or {}, r.get("bench") or {}
    vt = r.get("vs_traded") or {}
    pool = r.get("pool") or {}
    hold = r.get("holdings") or {}
    exc = r.get("excess_cagr")
    if exc is None:                       # 자산 랩엔 필드가 없다 — CAGR 차가 곧 그 값이다
        exc = _sub(m.get("cagr"), b.get("cagr"))
    doc = {
        "sid": sid, "name": r.get("name"), "family": fam,
        "role": r.get("role"), "kind": r.get("kind"), "arch": r.get("arch"),
        # ① 무엇을 하는 규칙인가 ─────────────────────────────────
        "rule": r.get("rule"), "why": r.get("why"), "note": r.get("note"),
        "repro": audit_of,                # 재현에서 원문과 달라진 점(자산 랩 audit)
        # ② 구간 ────────────────────────────────────────────────
        # ⚠ 종목 랩은 규칙마다 end·bench_label 을 따로 안 싣는다(랩 전체가 한 값이다).
        #   비워 두면 '이 규칙만 대조군이 없다'로 읽히므로 랩 값으로 채우고 출처를 남긴다.
        "window": {"start": r.get("start"), "end": r.get("end") or lab.get("as_of"),
                   "n_days": r.get("n_days"), "n_thin": r.get("n_thin"),
                   "bench_label": r.get("bench_label") or lab.get("bench_label"),
                   "bench_from_lab": r.get("bench_label") is None,
                   "bench_tickers": r.get("bench_tickers"),
                   "bench_unstable": r.get("bench_unstable")},
        # ③ 성과 ────────────────────────────────────────────────
        "perf": _perf(m, b),
        "excess_cagr": _f(exc), "d_sharpe": _f(r.get("d_sharpe"), 3),
        "t": _f(r.get("t")), "t_crit": _f(tcrit),
        # ④ 비용 · 회전 ──────────────────────────────────────────
        "cost": _cost(r, fam),
        "turnover": _f(r.get("turnover"), 2), "exposure": _f(r.get("exposure"), 1),
        # ⑤ 위험 ────────────────────────────────────────────────
        "risk": _risk(r),
        # ⑥ 중복 ────────────────────────────────────────────────
        "incr": _incr(r, dup_of),
        # ⑦ 대조군을 매매대상으로 바꾸면 ─────────────────────────
        "vs_traded": ({"label": vt.get("label"), "cagr": _f(vt.get("cagr")),
                       "sharpe": _f(vt.get("sharpe"), 3), "excess": _f(vt.get("excess_cagr")),
                       "d_sharpe": _f(vt.get("d_sharpe"), 3), "t": _f(vt.get("t")),
                       "t_net": _f(vt.get("t_net")), "note": vt.get("note")} if vt else None),
        # ⑧ 생존편향 보정 ───────────────────────────────────────
        "pit": _pit(r, pit_of),
        # ⑨ 후보 풀 ────────────────────────────────────────────
        "pool": ({"first": pool.get("first"), "last": pool.get("last"), "min": pool.get("min"),
                  "med": pool.get("med"), "narrow": pool.get("narrow"), "n": pool.get("n"),
                  "d0": pool.get("d0")} if pool else None),
        # ⑩ 지금 무엇을 들고 있나 ───────────────────────────────
        # ⚠ 두 모양이 있다. 종목선택·배분은 **종목/비중**이고, 타이밍은 **노출 한 숫자**다
        #   (유니버스 전체를 그 비율로 든다). exposure_now 를 빠뜨리면 타이밍 21종이
        #   전부 '보유 없음'으로 보인다 — 실제로 처음 판에서 그랬다.
        "holdings": ({"kind": hold.get("kind"), "as_of": hold.get("as_of"), "n": hold.get("n"),
                      "tickers": hold.get("tickers"), "names": hold.get("names"),
                      "weights": hold.get("weights"),
                      "exposure_now": _f(hold.get("exposure_now"), 1),
                      "note": hold.get("note")} if hold else None),
        "verdict": r.get("verdict"),
        # ⑪ 참고 — 논문과 이 규칙이 실제로 쓴 자료(맨 아래)
        "refs": _refs(sid, fam, r.get("kind"), refs, fund_sids, bool(pit_of or r.get("pit"))),
    }
    # 🚨 왜 비었는지를 적는다. 이유는 대개 "그 족에 그 측정이 아예 없다"이지
    #   "재 봤더니 안 나왔다"가 아니다 — 그 구별을 남긴다.
    miss = []
    if doc["pit"] is None:
        miss.append("PIT(생존편향 보정)" + (" — 종목 랩 34종만 돈다(가격·재무가 시점별로 있어야 한다)"
                                          if fam != "자산배분" else
                                          " — 자산 랩은 ETF 라 편입·편출 개념이 없다"))
    if doc["risk"] is None:
        miss.append("위험 부트스트랩" + (" — 종목 랩은 이 측정을 아예 안 돌린다"
                                      if fam != "자산배분" else " — 이 규칙에서 산출에 실패했다"))
    if doc["cost"] is None:
        miss.append("비용 후 성과 — 이 규칙에서 비용 레그가 안 돌았다")
    if doc["incr"]["five"] is None:
        miss.append("증분알파(이웃 5개) — 날짜가 겹치는 이웃이 5개에 못 미쳤다")
    if doc["vs_traded"] is None and fam != "자산배분":
        miss.append("매매대상 대비 — 산출되지 않았다")
    if doc["pool"] is None and r.get("kind") == "xsec":
        miss.append("후보 풀 추이 — 산출되지 않았다")
    doc["missing"] = miss
    return doc


# ── 전략 지도 ────────────────────────────────────────────────────────────
# 🚨 2026-08-08 · 왜 만들었나 (사용자 요청 "지금 구분 너무 복잡해").
#   점검해 보니 실제로 그랬다. 목록 상태가 **6종·5개 파일**에 흩어져 있고, 판정 어휘가
#   **5벌**이고(종목 랩 '열위' vs 자산 랩 '대조군 열위' 처럼 같은 뜻 다른 말 포함),
#   역할 5값 중 2개는 1~2종짜리 고아라 화면 집계에서 조용히 사라지고 있었다.
#
#   어휘는 정본에서 통일했고(asset_backtest·strategy_index·strategy_kinds),
#   여기서는 **축 셋으로 한 장에 접는다**:
#
#     축1 어디 있나 — 화면에 있음 / 화면에서 뺌 / 퇴출 / 돌렸지만 게시 안 함 / 재현 안 함
#     축2 무엇을 하나 — 수익엔진 / 타이밍오버레이 / 배분기 / 위험방어
#     축3 어떻게 됐나 — 통과 / 구별 불가 / 열위 / 측정 불가 / 판정 전
#
# 🚨 **겹쳐 세지 않는다.** 목록을 그냥 더하면 216 이 나오는데 실제 고유 규칙은 169 다
#   (아카이브 48 중 36 은 자산 랩에서 재현돼 이미 세어졌고, hidden 32 는 자산 랩·거장겹침의
#   부분집합이다). 한 규칙은 한 칸에만 넣는다.
_ROLE_CANON = {"방어보험": "위험방어", "위험감축": "위험방어"}   # 옛 어휘 호환
_VERDICT_CANON = {"대조군 열위": "열위", "통과 후보": "통과"}     # 옛 어휘 호환


def _canon_role(r, kind=None):
    v = _ROLE_CANON.get(r, r)
    if v:
        return v
    return {"xsec": "수익엔진", "timing": "타이밍오버레이"}.get(kind, "미분류")


def _strategy_map(tech, asset, archive, index, deploy):
    """전 규칙을 축 셋에 한 번씩만 넣는다. 겹치면 앞의 상태가 이긴다."""
    hidden = {h.get("name") for h in (index.get("hidden") or [])}
    in_items = {r.get("sid") for r in (index.get("items") or [])}
    # 자산 랩에서 재현된 아카이브 항목 — 이미 자산 랩 sid 로 세었으므로 여기서 또 세지 않는다
    reproduced = {it.get("n") for it in ((asset.get("audit") or {}).get("items") or [])
                  if it.get("res")}

    rows = []

    def add(where, role, verdict, name, sid, lab):
        rows.append({"where": where, "role": _canon_role(role),
                     "verdict": _VERDICT_CANON.get(verdict, verdict) or "판정 전",
                     "name": name, "sid": sid, "lab": lab})

    for r in (tech.get("strategies") or []):
        add("화면에 있음", _canon_role(r.get("role"), r.get("kind")), r.get("verdict"),
            r.get("name"), r.get("sid"), "종목·타이밍")
    for r in (asset.get("strategies") or []):
        # 자산 랩은 절반 가까이가 '측정은 했지만 화면 목록에서 뺀' 상태다(운용 결정).
        # 그 상태를 안 적으면 독자는 51종이 다 화면에 있는 줄 안다.
        w = "화면에 있음" if ("a-" + str(r.get("sid"))) in in_items else "화면에서 뺌"
        if r.get("name") in hidden:
            w = "화면에서 뺌"
        add(w, r.get("role"), r.get("verdict"), r.get("name"), r.get("sid"), "자산배분")
    for r in (tech.get("retired") or []):
        add("퇴출", _canon_role(None, r.get("kind")), "퇴출", r.get("name"), r.get("sid"), "종목·타이밍")
    for r in (tech.get("tested") or []):
        add("돌렸지만 게시 안 함", _canon_role(None, r.get("kind")),
            "측정 불가" if r.get("t") is None else "열위",
            r.get("name"), r.get("sid"), "종목·타이밍")
    for it in (archive.get("items") or []):
        if it.get("n") in reproduced:
            continue                      # 자산 랩에서 이미 세었다
        add("재현 안 함", "미분류", "판정 전", it.get("n"), None, "아카이브")
    # 🚨 배포 원장 — 이 랩에서 **유일하게 '통과'가 있는 목록**이다. 빼면 지도가
    #   "통과 0" 이라고 말하는데, 실제로는 배포 3종이 있다(다른 시기·다른 규약으로
    #   판정된 것이라 랩 본편의 게시 기준과 같은 잣대가 아니다 — 그 사실을 함께 적는다).
    _DV = {"deploy": "배포", "marginal": "제한적 유효", "reject": "미채택"}
    for it in (deploy.get("items") or []):
        add("배포 원장", "미분류", _DV.get(it.get("v"), it.get("v")),
            it.get("n"), it.get("sid"), "배포 원장")

    axes = {"where": ["화면에 있음", "화면에서 뺌", "퇴출", "돌렸지만 게시 안 함",
                      "재현 안 함", "배포 원장"],
            "role": ["수익엔진", "타이밍오버레이", "배분기", "위험방어", "미분류"],
            "verdict": ["배포", "제한적 유효", "통과", "구별 불가", "열위",
                        "측정 불가", "퇴출", "미채택", "판정 전"]}
    grid = {}
    for r in rows:
        grid.setdefault(r["where"], {}).setdefault(r["role"], 0)
        grid[r["where"]][r["role"]] += 1
    vgrid = {}
    for r in rows:
        vgrid.setdefault(r["where"], {}).setdefault(r["verdict"], 0)
        vgrid[r["where"]][r["verdict"]] += 1
    return {
        "n": len(rows), "axes": axes, "by_where_role": grid, "by_where_verdict": vgrid,
        "rows": rows,
        "note": "이 랩이 판 규칙 전부를 축 셋으로 한 번씩만 센다 — 어디 있나 · 무엇을 하나 · "
                "어떻게 됐나. 목록을 그냥 더하면 216 이 나오지만 겹침을 걷으면 %d 다"
                "(아카이브 중 자산 랩에서 재현된 것은 이미 자산 랩으로 세었다)." % len(rows),
        "vocab": "어휘를 2026-08-08 에 통일했다 — 자산 랩만 쓰던 '대조군 열위'는 '열위'로, "
                 "각 1~2종짜리 고아였던 '방어보험'·'위험감축'은 '위험방어' 하나로 합쳤다. "
                 "합치기 전에는 그 셋이 전부 화면에서 빠져 있어 집계에 아예 안 나왔다.",
    }


def main():
    tech = _load("tech_strategies.json")
    asset = _load("asset_strategies.json")
    pit = _load("pit_strategies.json")
    archive = _load("archive_index.json")
    index = _load("strategy_index.json")
    try:
        refs = json.load(io.open(os.path.join(HERE, "strategy_refs.json"), encoding="utf-8"))
    except Exception:
        refs = {}
    # 어느 규칙이 재무를 쓰는지는 랩이 안다 — 손으로 다시 적지 않는다(두 벌이 되면 갈린다).
    try:
        import tech_backtest as _T
        fund_sids = set(_T.FUND_SIDS)
    except Exception:
        fund_sids = set()
    deploy = _load("deploy_index.json")

    pit_by = {x.get("sid"): x for x in (pit.get("strategies") or [])}
    # 자산 랩 audit — 원문에서 무엇을 못 옮겼는지가 여기 적혀 있다. 복제 리포트의 알맹이다.
    audit_by = {}
    for it in ((asset.get("audit") or {}).get("items") or []):
        if it.get("res"):
            audit_by[it["res"]] = {"src": it.get("n"), "cat": it.get("c"),
                                   "status": it.get("status"), "why": it.get("why")}
    # 종목 랩 dup — '가장 닮은 이웃에 흡수됐나'. 단독 |t|≥2 인 규칙만 센 표다.
    dup_by = {}
    name2sid = {x.get("name"): x.get("sid") for x in (tech.get("strategies") or [])}
    for it in ((tech.get("dup") or {}).get("xsec_absorbed") or []):
        s = name2sid.get(it.get("name"))
        if s:
            dup_by[s] = {"vs": it.get("vs"), "corr": _f(it.get("corr"), 3),
                         "t_solo": _f(it.get("t_solo")), "t_incr": _f(it.get("t_incr"))}

    out = {
        "note": "전략별 상세 복제 결과. **판정이 아니라 잰 것 전부**를 낸다 — 규칙·근거·재현 "
                "한계·구간·성과·비용·회전·위험·증분알파·매매대상 대비·생존편향 보정·후보 풀·"
                "현재 보유. 새로 계산하지 않고 랩이 이미 실은 값을 옮긴다(채점기를 두 벌 두지 "
                "않는다). 값이 없으면 '—' 로 두고 왜 없는지 함께 적는다 — 빈칸을 지우면 그 항목을 "
                "통과한 것처럼 읽힌다.",
        "cost_note": "비용은 **왕복 bp** 로 통일했다. 원 자료의 단위가 다르다 — 종목 랩은 편도 "
                     "5·10·20bp(왕복 10·20·40), 자산 랩은 왕복 5bp 한 점이다. ⚠ 왕복으로 맞춰도 "
                     "두 랩의 크기를 나란히 비교하면 안 된다: 자산 랩은 ETF 를, 종목 랩은 개별주 "
                     "10종을 매매한다.",
        "as_of": {"tech": tech.get("as_of"), "asset": asset.get("as_of"), "pit": pit.get("as_of")},
        "t_crit": {"tech": tech.get("t_crit"), "asset": asset.get("t_crit"),
                   "pit": pit.get("t_crit"), "pit_lab": pit.get("t_crit_lab")},
        "gate": "게시 기준 — ① |t| ≥ 본페로니 임계 ② Δ샤프 > 0 ③ 이웃 5개 동시 통제 증분알파 "
                "t ≥ +2.0 ④ 부호 정합. 이 리포트는 그 기준으로 줄 세우지 않는다.",
        "limits": {"tech": tech.get("limits") or [], "asset": asset.get("limits") or [],
                   "pit": pit.get("limits") or [], "protocol": asset.get("protocol") or []},
        "retired": {"tech": tech.get("retired") or []},
        # 🚨 세 번째 목록 — 돌렸지만 게시된 적 없는 규칙. 이 리포트가 '전 전략'을 낸다고
        #   말하는 이상 이것도 내야 한다. 안 내면 독자는 이 랩이 69종만 팠다고 읽는데
        #   실제로는 95종(69 + 퇴출 13 + 이 13)을 팠다. 그 차이가 다중검정의 크기다.
        "tested": {"tech": tech.get("tested") or []},
        # 전략 지도 — 축 셋으로 접은 한 장(위 _strategy_map 머리말 참조)
        "map": _strategy_map(tech, asset, archive, index, deploy),
        "refs_policy": (refs.get("policy") or ""),
        "refs_search": (refs.get("search") or {}).get("base") or "",
        "items": [],
    }
    for r in (asset.get("strategies") or []):
        out["items"].append(_one(r, "자산배분", asset.get("t_crit"),
                                 audit_by.get(r.get("sid")), None, None, asset, refs, fund_sids))
    for r in (tech.get("strategies") or []):
        out["items"].append(_one(r, "종목·타이밍", tech.get("t_crit"),
                                 None, dup_by.get(r.get("sid")), pit_by.get(r.get("sid")), tech,
                                 refs, fund_sids))
    # 족 → t 내림차순. 같은 족을 나란히 읽게 하고, 그 안에서 t 가 큰 것부터.
    # ⚠ 이 정렬은 **읽는 순서**일 뿐 순위가 아니다 — t 가 큰 것이 좋은 것이라는 뜻이 아니다.
    out["items"].sort(key=lambda x: (x["family"], -(x["t"] if x["t"] is not None else -99)))
    out["n"] = {"asset": len(asset.get("strategies") or []),
                "tech": len(tech.get("strategies") or []),
                "pit": len(pit.get("strategies") or []),
                "total": len(out["items"])}
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    from collections import Counter
    n = len(out["items"])
    print("전략 리포트 — %d건(자산 %d · 종목 %d · PIT 레그 %d)"
          % (n, out["n"]["asset"], out["n"]["tech"], out["n"]["pit"]))
    have = Counter()
    for x in out["items"]:
        for k in ("cost", "risk", "vs_traded", "pit", "pool", "repro"):
            if x.get(k):
                have[k] += 1
        if (x["incr"] or {}).get("five"):
            have["incr5"] += 1
        _h = x.get("holdings") or {}
        if _h.get("tickers") or _h.get("weights") or _h.get("exposure_now") is not None:
            have["holdings"] += 1
    for k, lab in (("cost", "비용 후 성과"), ("risk", "위험 부트스트랩"), ("incr5", "증분알파(이웃5)"),
                   ("vs_traded", "매매대상 대비"), ("pit", "생존편향 보정"), ("pool", "후보 풀"),
                   ("repro", "재현 한계 메모"), ("holdings", "현재 보유")):
        print("  %-14s %3d / %d" % (lab, have[k], n))
    print("→", OUT, "(%.0fKB)" % (os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
