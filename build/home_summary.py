# -*- coding: utf-8 -*-
"""홈 전용 초소형 요약(data/home_reco.json) — **홈이 읽는 유일한 대형 데이터 대체물**.

홈은 stocks.json(354KB)·rotation_pool.json(364KB)·strategy_backtests.json(85KB)을 절대 fetch하지
않는다. 대신 빌드가 필요한 값만 여기에 구워 1~2KB로 만든다.

담는 것
  ① 스윙 타점 상위 8+8 — 확정/잠정 지위 포함
  ② 확정·잠정 **카운트** — '오늘 표시된 16건이 전부 잠정'인데 카드가 "확정 스윙 타점"을 내세우는
     불일치가 실제로 있었다. 숫자를 함께 실어 화면이 스스로 드러내게 한다.
  ③ 배포 판정 3종의 백테스트 지표·구간·축약 NAV — 판정 원장(verdicts.json)이 정한 3종만.
     전략 이름을 여기 적지 않는다. 원장이 바뀌면 자동으로 따라간다.
"""
from __future__ import annotations
import io, json, os

# GICS 영문 섹터는 홈의 좁은 행에서 잘린다 — 짧은 한글로(stocks.html의 SECKO와 같은 표기)
SECKO = {"Information Technology": "IT", "Health Care": "헬스케어", "Financials": "금융",
         "Consumer Discretionary": "경기소비", "Consumer Staples": "필수소비", "Industrials": "산업재",
         "Communication Services": "커뮤니케이션", "Energy": "에너지", "Utilities": "유틸리티",
         "Real Estate": "부동산", "Materials": "소재"}
WIN = 10          # 최근 N거래일 내 타점만 홈에 노출
TOP = 8
SPARK = 60        # 스파크라인 점 개수(홈 카드용 — 원본 NAV를 균등 추출)


def _lastmk(s, key):
    a = s.get(key) or []
    return a[-1] if a else -1


def _reco(stocks, dates, conf_key, prov_key):
    """확정(conf)·잠정(prov) 중 최신 타점을 취한다. prov가 더 최신이면 아직 이동 가능."""
    N = len(dates)
    c = []
    for s in stocks:
        mc, mp = _lastmk(s, conf_key), _lastmk(s, prov_key)
        m = max(mc, mp)
        if m < 0 or (N - 1 - m) > WIN:
            continue
        c.append((m, mp > mc, s))
    c.sort(key=lambda x: -x[0])
    rows = [{"t": s["t"], "name": (s.get("name") or "")[:16], "dt": dates[m][5:], "ago": N - 1 - m,
             "sec": SECKO.get(s.get("sector") or "", (s.get("sector") or "")[:6]),
             **({"prov": 1} if pv else {})} for m, pv, s in c[:TOP]]
    n_prov = sum(1 for _, pv, _ in c if pv)
    return rows, len(c), len(c) - n_prov, n_prov      # 목록 · 전체 · 확정 · 잠정


def _deploy_perf(root):
    """판정 원장이 '배포'로 분류한 전략의 성과만 굽는다(이름을 여기 하드코딩하지 않는다)."""
    vp = os.path.join(root, "data", "verdicts.json")
    bp = os.path.join(root, "data", "strategy_backtests.json")
    if not (os.path.exists(vp) and os.path.exists(bp)):
        return []
    V = json.load(io.open(vp, encoding="utf-8"))
    B = (json.load(io.open(bp, encoding="utf-8")) or {}).get("strategies") or {}
    out = []
    for d in V.get("deploy") or []:
        b = B.get(d["n"])
        if not b:
            continue                      # 백테스트 없는 배포 전략은 조용히 빼지 않고 아래에서 검증한다
        m = b.get("metrics") or {}
        nav = b.get("nav") or []
        step = max(1, len(nav) // SPARK)
        out.append({
            "n": d["n"], "slug": d["slug"], "alias": d.get("alias"),
            "cagr": m.get("cagr"), "sharpe": m.get("sharpe"), "mdd": m.get("mdd"),
            "mdd_b": b.get("mdd_b"), "bench": b.get("bench_label"),
            "start": b.get("start"), "end": b.get("end"),
            "nav": [round(x, 3) for x in nav[::step][:SPARK]],
        })
    return out


def build(stocks, dates, as_of, root):
    buy, nb, nb_c, nb_p = _reco(stocks, dates, "bms", "bmw")
    sell, ns, ns_c, ns_p = _reco(stocks, dates, "sms", "smw")
    return {
        "as_of": as_of, "win": WIN,
        "buy": buy, "sell": sell, "nbuy": nb, "nsell": ns,
        "buy_conf": nb_c, "buy_prov": nb_p, "sell_conf": ns_c, "sell_prov": ns_p,
        "deploy": _deploy_perf(root),
    }


def write(stocks, dates, as_of, root):
    """실패를 삼키지 않는다 — 홈의 핵심 모듈이라 조용히 빈 채로 배포되면 안 된다."""
    doc = build(stocks, dates, as_of, root)
    if not doc["buy"] and not doc["sell"]:
        raise SystemExit("home_reco: 최근 타점이 하나도 없다 — 마커 산출이 깨졌는지 확인")
    nd = len(doc["deploy"])
    vp = os.path.join(root, "data", "verdicts.json")
    want = len(json.load(io.open(vp, encoding="utf-8")).get("deploy") or []) if os.path.exists(vp) else 0
    if want and nd != want:
        raise SystemExit(f"home_reco: 배포 전략 {want}종 중 {nd}종만 백테스트가 있다 — 이름 불일치 의심")
    p = os.path.join(root, "data", "home_reco.json")
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    return p, doc


if __name__ == "__main__":
    R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    d = json.load(io.open(os.path.join(R, "data", "stocks.json"), encoding="utf-8"))
    p, doc = write(d["stocks"], d["pxd_dates"], d["as_of"], R)
    print(f"→ {os.path.basename(p)} ({os.path.getsize(p)//1024 or 1}KB) "
          f"매수 {doc['nbuy']}(확정 {doc['buy_conf']}·잠정 {doc['buy_prov']}) · "
          f"매도 {doc['nsell']}(확정 {doc['sell_conf']}·잠정 {doc['sell_prov']}) · 배포 {len(doc['deploy'])}종")
