# -*- coding: utf-8 -*-
"""월별 지수 편입 원장 — data/index_ledger.json

무엇을 만드나.
  S&P 500 · 나스닥 100 의 **매월말 실제 편입 종목**을 눈으로 넘겨 볼 수 있는 표와,
  "그 시점 종목 자료를 몇 % 갖고 있나" 를 달마다 잰 값.

왜 만드나(사용자 요청 2026-08-13).
  이 랩의 시점정확(PIT) 레그가 쓰는 멤버십이 어떤 것인지 화면에서 볼 수가 없었다.
  pit_backtest.py 는 커버리지를 전체 한 숫자(96.7%)로만 냈고, 그 숫자가 어느 달에
  어느 종목에서 빠진 것인지는 산출물에 없었다. 편향을 재는 레그의 입력이 안 보이면
  그 레그의 수치도 못 믿는다.

원천.
  · 멤버십 — data/index_history.json (위키백과 지수 목록 문서의 **과거 리비전**, CC BY-SA).
    2014-06 부터다. 그 아래는 위키 표에 CIK 컬럼이 없어 개명과 티커 재사용을 구별할 수 없다.
  · 가격  — data/sd/*.json (오늘의 유니버스 518종) + data/_pit_px_cache.json (편출 종목).
    🚨 뒤쪽 캐시는 **gitignore** 라 저장소에 없다. 그래서 커버리지는 **여기서 미리 세어**
      산출물에 숫자로 박는다 — 화면이 11MB 캐시를 읽게 두지 않는다.

⚠ 사내 DB(public.index_constituents)는 쓰지 않는다. 이 저장소는 공개이고,
  사내 DB 산출물은 커밋 금지다(data/pit_members.json 이 그 사유로 걷혔다).
  위키 리비전은 출처·리비전 번호까지 같이 실을 수 있어 오히려 검증이 된다.
"""
import io
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "index_ledger.json")

IDX = [("spx", "S&P 500", "List_of_S%26P_500_companies"),
       ("ndx", "나스닥 100", "Nasdaq-100")]


def _load(name, default=None):
    try:
        return json.load(io.open(os.path.join(DATA, name), encoding="utf-8"))
    except Exception:
        return default


def month_end_index(dates):
    """거래일 격자에서 각 달의 **마지막 거래일** 위치. 커버리지를 그날 기준으로 잰다.

    왜 월말인가. PIT 레그가 월말에 리밸런스하고 그 시점 점수로 종목을 고른다.
    달 중간의 아무 날이 아니라 **실제로 후보를 세는 날**의 커버리지를 재야 뜻이 있다.
    """
    last = {}
    for i, d in enumerate(dates):
        last[d[:7]] = i
    return last


def px_months():
    """티커 → 가격이 실제로 있는 달의 집합.

    🚨 '파일이 있다' 와 '그달 값이 있다' 는 다르다. 오늘의 유니버스에 있어도 2014년에
      상장 전이면 pxd 가 None 이다 — 파일 유무로 세면 그 시절 커버리지가 100% 로 나온다.
      값이 None 이 아닌 달만 센다.
    """
    st = _load("stocks.json") or {}
    dates = st.get("pxd_dates") or []
    mend = month_end_index(dates)
    have = {}
    sd = os.path.join(DATA, "sd")
    if os.path.isdir(sd):
        for fn in os.listdir(sd):
            if not fn.endswith(".json"):
                continue
            t = fn[:-5]
            try:
                pxd = (json.load(io.open(os.path.join(sd, fn), encoding="utf-8")) or {}).get("pxd")
            except Exception:
                continue
            if not pxd:
                continue
            ms = set()
            for m, i in mend.items():
                if i < len(pxd) and pxd[i] is not None:
                    ms.add(m)
            if ms:
                have[t] = ms
    # 편출 종목 캐시 — {티커: {날짜: 종가}}. 로컬에만 있다.
    cache = _load("_pit_px_cache.json") or {}
    for t, ser in cache.items():
        if not isinstance(ser, dict):
            continue
        ms = have.setdefault(t, set())
        # 월말 거래일이 캐시에 그대로 있진 않을 수 있다(편출 후 잘린 계열). 그달에 값이
        # 하나라도 있으면 '자료를 갖고 있다' 로 센다 — 후보로 세울 수 있다는 뜻이다.
        for d in ser:
            ms.add(d[:7])
    return have, dates


def main():
    hist = _load("index_history.json")
    if not hist:
        raise SystemExit("data/index_history.json 이 없다 — build/refresh_index_history.py 를 먼저 돌릴 것.")
    months = sorted(hist["months"])
    have, dates = px_months()
    if not have:
        raise SystemExit("가격 자료를 하나도 못 읽었다 — data/sd 와 data/stocks.json 을 확인할 것.")
    grid = set(d[:7] for d in dates)

    # ── 종목 메타(이름·섹터) ────────────────────────────────────────────
    # 오늘의 518종은 members.json, 편출 종목은 pit_sector.json 이 섹터만 준다.
    # ⚠ 이름이 없는 편출 종목은 **티커만** 적는다. 없는 것을 지어내지 않는다.
    meta = {}
    for t, r in ((_load("members.json") or {}).get("members") or {}).items():
        meta[t] = [r.get("name") or "", r.get("sector") or ""]
    for t, s in ((_load("pit_sector.json") or {}).get("sector") or {}).items():
        if t not in meta:
            meta[t] = ["", s or ""]

    out = {}
    seen = set()
    for key, label, wiki in IDX:
        prev, mm, base = None, {}, None
        for m in months:
            cur = hist["months"][m].get(key)
            if not cur:
                continue                      # 그달 리비전을 못 읽은 것(hist.gaps 에 사유가 있다)
            cur = sorted(cur)
            seen.update(cur)
            rec = {"n": len(cur), "rev": hist["months"][m].get(key + "_rev")}
            if prev is None:
                base = {"month": m, "t": cur}
            else:
                rec["add"] = sorted(set(cur) - set(prev))
                rec["drop"] = sorted(set(prev) - set(cur))
            # 커버리지 — 그달 월말에 가격이 있는 멤버 수.
            # ⚠ 격자에 없는 달(오늘 이후·거래일 없음)은 '0%' 가 아니라 **못 잼**이다.
            if m in grid:
                miss = [t for t in cur if m not in have.get(t, ())]
                rec["px"] = len(cur) - len(miss)
                rec["pct"] = round(100.0 * rec["px"] / len(cur), 1)
                rec["miss"] = miss
            mm[m] = rec
            prev = cur
        out[key] = {"label": label, "wiki": wiki, "base": base, "m": mm}

    # 한 번이라도 멤버였던 티커 중 메타가 없는 것 — 지어내지 않고 개수만 적는다.
    n_nometa = len([t for t in seen if t not in meta])

    doc = {
        "as_of": hist.get("as_of"),
        "source": hist.get("source"),
        "months": [m for m in months if any(m in out[k]["m"] for k, _l, _w in IDX)],
        "idx": out,
        "meta": {t: meta[t] for t in sorted(seen) if t in meta},
        "n_seen": len(seen),
        "n_nometa": n_nometa,
        "note": "매월말 지수 편입 종목과, 그 시점 가격 자료를 몇 %나 갖고 있는지. "
                "멤버십은 위키백과 지수 목록 문서의 과거 리비전(data/index_history.json)이고 "
                "달마다 리비전 번호를 같이 실어 원문을 확인할 수 있게 했다.",
        "limits": [
            "🚨 커버리지 100%가 '자료가 완전하다'는 뜻은 아니다. 여기서 세는 것은 **그달 "
            "월말에 종가가 있는 멤버의 비율**이고, 종가는 (ㄱ) 오늘의 유니버스 518종과 "
            "(ㄴ) 편출 종목 캐시에서 온다. (ㄴ)은 yfinance 가 주는 것뿐이라 M&A·상장폐지로 "
            "심볼 자체가 사라진 회사는 애초에 안 잡힌다 — 그 종목들은 분모에는 있고 분자에는 "
            "없으니 %로 드러나지만, 재무·거래량 같은 다른 축의 결손은 이 표가 재지 않는다.",
            "구간이 2014-06 부터인 것은 자료의 한계다 — 위키 표에 CIK 컬럼이 생긴 첫 달이고, "
            "그 아래는 티커로만 조인하게 되어 개명(BBWI←LB)과 티커 재사용을 구별할 수 없다. "
            "명단 자체는 더 깊다(SPX 2007-04 · NDX 2008-03).",
            "편입·편출은 **월말 스냅샷의 차이**다. 한 달 안에 들어왔다 나간 종목은 안 잡히고, "
            "위키 문서가 늦게 갱신된 달은 실제 변경일보다 한 달 뒤로 잡힐 수 있다.",
            "🚨 랩 전략의 PIT 레그가 쓰는 창은 이 표 전체가 아니라 **2021-07 부터**다 "
            "(세 커버리지가 모두 90%를 넘고 다시 안 내려가는 첫 달). 이 표에서 그 이전 달의 "
            "커버리지가 낮은 것이 그 문턱의 근거다.",
        ],
    }
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"))
    kb = os.path.getsize(OUT) / 1024.0
    print("→ %s · %d개월 · %.0fKB" % (os.path.relpath(OUT, ROOT), len(doc["months"]), kb))
    for key, label, _w in IDX:
        mm = out[key]["m"]
        cov = [(r["pct"], m) for m, r in mm.items() if "pct" in r]
        cov.sort()
        if cov:
            print("   %-10s %d개월 · 커버리지 최저 %.1f%%(%s) → 최근 %.1f%%"
                  % (label, len(mm), cov[0][0], cov[0][1],
                     mm[max(m for m in mm if "pct" in mm[m])]["pct"]))
    if n_nometa:
        print("   ⚠ 이름·섹터가 없는 티커 %d종 — 티커만 표시한다." % n_nometa)


if __name__ == "__main__":
    main()
