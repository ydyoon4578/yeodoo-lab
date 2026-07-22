# -*- coding: utf-8 -*-
"""펀더멘털 스크리닝 — **계산의 유일한 구현**.

왜 여기 한 곳뿐인가
    화면(JS)과 로더(파이썬)가 같은 규칙을 각자 계산하면 결국 어긋난다. 실제로 어긋났다:
    동점(같은 베타 값) 처리 순서가 달라 CMCSA가 화면에선 탈락(69종), 로더에선 통과(70종)했다.
    정의 파일(data/screens.json)을 공유해도 '구현이 둘'이면 드리프트는 남는다.
    → 빌드 때 여기서 한 번 계산해 data/stocks.json에 굽고, 화면·로더는 **읽기만** 한다.

동점 처리
    백분위는 동점 그룹의 **평균 순위**로 준다(중간값 방식). 정렬 순서에 의존하지 않으므로
    구현·언어가 달라도 같은 값이 나온다. 예전처럼 '먼저 나온 놈이 낮은 순위'로 두면
    입력 순서가 결과를 바꾼다.

지문(screens_fp)
    결과에 영향을 주는 부분(dir·keys·qualify)만 해시한다. 이름·설명만 고치면 재생성이 필요 없다.
    정의를 바꿔놓고 stocks.json을 다시 굽지 않으면 CI가 지문 불일치로 잡아준다.
"""
from __future__ import annotations
import hashlib, json


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f     # NaN 제외


def fingerprint(screens_doc) -> str:
    """결과를 바꾸는 정의만 담은 지문 — 이름·설명 변경으로는 흔들리지 않는다."""
    core = {
        "dir": screens_doc.get("dir") or {},
        "screens": {k: {"keys": v.get("keys") or [], "qualify": v.get("qualify") or {},
                        "qualify_max": v.get("qualify_max") or {}}
                    for k, v in (screens_doc.get("screens") or {}).items()},
    }
    blob = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


def _pct_tie_avg(pairs):
    """[(값, 티커)] → {티커: 0~100 백분위}. 동점은 평균 순위(순서 무관)."""
    pairs = sorted(pairs, key=lambda x: x[0])
    n = len(pairs)
    out = {}
    if n == 0:
        return out
    if n == 1:
        return {pairs[0][1]: 50.0}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        mid = (i + j) / 2.0 / (n - 1) * 100.0      # 동점 그룹은 같은 백분위
        for k in range(i, j + 1):
            out[pairs[k][1]] = mid
        i = j + 1
    return out


def compute(stocks, screens_doc):
    """{스크린키: [{"t":티커, "s":적합도}, ...]} — 적합도 내림차순, 동점은 티커순."""
    DIR = screens_doc.get("dir") or {}
    SCR = screens_doc.get("screens") or {}
    pct = {k: _pct_tie_avg([(_num((s.get("fund") or {}).get(k)), s["t"]) for s in stocks
                            if _num((s.get("fund") or {}).get(k)) is not None]) for k in DIR}

    def good(t, k):
        v = pct.get(k, {}).get(t)
        if v is None:
            return None
        return 100.0 - v if DIR.get(k) == "low" else v

    res = {}
    for key, sc in SCR.items():
        keys = sc.get("keys") or []
        rows = []
        for s in stocks:
            t = s["t"]
            ok = True
            for qk, th in (sc.get("qualify") or {}).items():
                g = good(t, qk)
                if g is None or g < th:           # 결측은 실격 — 모르면 넣지 않는다
                    ok = False
                    break
            # 상한 — '이 지표는 오히려 낮아야 한다'(예: 마진 주도 성장은 매출 증가가 하위권)
            if ok:
                for qk, th in (sc.get("qualify_max") or {}).items():
                    g = good(t, qk)
                    if g is None or g > th:
                        ok = False
                        break
            if not ok:
                continue
            gs = [good(t, k) for k in keys if good(t, k) is not None]
            rows.append({"t": t, "s": round(sum(gs) / len(gs), 2) if gs else 0.0})
        rows.sort(key=lambda r: (-r["s"], r["t"]))
        res[key] = rows
    return res


def apply(doc, screens_doc):
    """stocks.json 문서에 결과를 굽는다. 화면·로더는 이 결과를 읽기만 한다."""
    doc["screens"] = compute(doc.get("stocks") or [], screens_doc)
    doc["screens_fp"] = fingerprint(screens_doc)
    return doc


if __name__ == "__main__":
    import io, os, sys
    R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    sp = os.path.join(R, "data", "screens.json")
    op = os.path.join(R, "data", "stocks.json")
    sd = json.load(io.open(sp, encoding="utf-8"))
    doc = json.load(io.open(op, encoding="utf-8"))
    apply(doc, sd)
    if "--check" in sys.argv:
        cur = json.load(io.open(op, encoding="utf-8"))
        same = (cur.get("screens") == doc["screens"] and cur.get("screens_fp") == doc["screens_fp"])
        print("일치" if same else "불일치 — 재생성 필요")
        raise SystemExit(0 if same else 1)
    json.dump(doc, io.open(op, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("스크린 결과 반영:", " · ".join(f"{k} {len(v)}종" for k, v in doc["screens"].items()), "· 지문", doc["screens_fp"])
