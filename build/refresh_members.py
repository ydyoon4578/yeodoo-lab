# -*- coding: utf-8 -*-
"""build/refresh_members.py — 지수 편입 명단(data/members.json) 자동 갱신.

이 파일은 사이트 전체의 출발점이다. 518종목의 티커·이름·GICS 섹터·소속 지수를 담고 있고,
종목 스냅샷·신호·백테스트 유니버스가 전부 여기서 나온다. 그래서 **조용히 틀리는 것이 최악**이다
— 잘못된 명단으로 갱신되면 모든 화면이 함께 틀어지는데 아무도 알려주지 않는다.

그래서 이 스크립트는 '받아서 덮어쓰기'를 하지 않는다. 아래 관문을 전부 통과해야 쓴다.
  1) 두 소스 합의  : S&P 500은 위키백과 목록과 SSGA SPY 보유내역이 겹쳐야 한다(95% 이상).
                     ETF 보유내역은 운용사가 매일 내는 1차 자료라 위키 오타를 걸러준다.
  2) 개수 범위     : SPX 480~520 · NDX 95~105. 벗어나면 파싱이 깨진 것이다.
  3) 변동 상한     : 현재 명단 대비 편입+편출이 SPX 12·NDX 8을 넘으면 **쓰지 않고 실패**한다.
                     지수 리밸런스는 그렇게 크지 않다 — 크면 소스가 바뀐 것이다.
  4) 섹터 완전성   : 모든 종목에 GICS 11개 중 하나가 있어야 한다.

한계 — 숨기지 않고 적는다.
  · 이 명단은 **오늘 스냅샷**이다. 과거 시점의 편입 이력이 아니다. 백테스트의 생존편향은
    그대로 남아 있으며 각 결과 화면에 이미 명시돼 있다.
  · NASDAQ 100 위키 표의 분류는 GICS가 아니라 ICB다. 그래서 섹터는 S&P 500 표(GICS)에서 가져오고,
    NDX 전용 종목은 기존 명단의 섹터를 잇는다. 둘 다 없는 신규 종목이 나오면 관문 4에서 멈춘다
    — 추측해서 채우지 않는다.
  · 위키백과는 누구나 고칠 수 있다. 그래서 SPX는 ETF 보유내역과 교차 확인하고, NDX는 교차할
    1차 자료를 못 찾아 **변동 상한에만 의존한다**. 이 비대칭을 산출물에 적어 둔다.

  python build/refresh_members.py           # 관문 통과 시에만 기록
  python build/refresh_members.py --dry     # 비교만 하고 쓰지 않음
"""
from __future__ import annotations
import html as H
import io, json, os, re, sys, urllib.request, zipfile
import datetime as dt
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "members.json")
UA = {"User-Agent": "Mozilla/5.0 (compatible; yeodoo-lab/1.0; globalkbam@gmail.com)"}

WIKI_SPX = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKI_NDX = "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies"
SPY_XLSX = ("https://www.ssga.com/us/en/intermediary/library-content/products/"
            "fund-data/etfs/us/holdings-daily-us-en-spy.xlsx")

GICS = {"Communication Services", "Consumer Discretionary", "Consumer Staples", "Energy",
        "Financials", "Health Care", "Industrials", "Information Technology", "Materials",
        "Real Estate", "Utilities"}
LIM_SPX, LIM_NDX = (480, 520), (95, 105)
MAXCHG_SPX, MAXCHG_NDX = 12, 8
AGREE_MIN = 0.95


def get(u, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout).read()


def wiki_rows(url):
    doc = get(url).decode("utf-8", "replace")
    out = []
    for tbl in re.findall(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>', doc, re.S):
        rows = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tbl, re.S):
            cells = [H.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                     for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
            if cells:
                rows.append(cells)
        if len(rows) > 50:
            out.append(rows)
    return out


def norm(t):
    """위키는 BRK.B, 일부 소스는 BRK-B로 쓴다. 이 저장소 표기는 점이다."""
    return t.strip().upper().replace("-", ".").replace(" ", "")


def spy_symbols():
    """SPY 보유내역 XLSX의 문자열 풀. 정확한 표 파싱 대신 '이 티커가 파일에 있는가'만 본다 —
    교차 확인에는 그걸로 충분하고, 시트 레이아웃이 바뀌어도 안 깨진다."""
    z = zipfile.ZipFile(io.BytesIO(get(SPY_XLSX)))
    name = "xl/sharedStrings.xml"
    if name not in z.namelist():
        return set()
    ss = z.read(name).decode("utf-8", "replace")
    return {norm(s) for s in re.findall(r"<t[^>]*>([^<]*)</t>", ss)
            if re.fullmatch(r"[A-Z]{1,5}(\.[A-Z])?", s.strip().upper())}


def main() -> int:
    dry = "--dry" in sys.argv
    cur = json.load(io.open(OUT, encoding="utf-8"))
    cur_m = cur["members"]

    # ── 수집 ──────────────────────────────────────────────────────────
    spx = {}
    bad_sym = []
    for rows in wiki_rows(WIKI_SPX):
        head = [h.lower() for h in rows[0]]
        if "symbol" in head and any("gics sector" in h for h in head):
            i_t, i_n = head.index("symbol"), head.index("security")
            i_s = next(k for k, h in enumerate(head) if "gics sector" in h)
            for r in rows[1:]:
                if len(r) > max(i_t, i_n, i_s):
                    # 관문 0: 티커 형식. NDX 쪽에는 처음부터 있었는데 여기엔 없었다 —
                    # 위키 심볼 셀에 무엇이 들어오든 members.json → stocks.json → 화면까지
                    # 그대로 흘렀다는 뜻이다. wiki_rows 가 태그를 지운 **뒤** H.unescape 를
                    # 하므로, 엔티티로 적힌 것은 이 지점에서 태그로 되돌아온다.
                    # 아래 관문(개수·교차확인·변동)은 503종 중 한 행이 이상해도 전부 통과한다.
                    # 형식은 여기서만 막을 수 있다.
                    t = norm(r[i_t])
                    if not re.fullmatch(r"[A-Z.]{1,6}", t):
                        bad_sym.append(r[i_t][:40])
                        continue
                    spx[t] = {"name": r[i_n], "sector": r[i_s]}
            break
    ndx = {}
    for rows in wiki_rows(WIKI_NDX):
        head = [h.lower() for h in rows[0]]
        if head and head[0] in ("ticker", "symbol"):
            i_n = 1 if len(head) > 1 else 0
            for r in rows[1:]:
                if len(r) > i_n and re.fullmatch(r"[A-Z.]{1,6}", norm(r[0])):
                    ndx[norm(r[0])] = {"name": r[i_n]}
            break
    print("수집 — SPX %d · NDX %d" % (len(spx), len(ndx)))

    fail = []
    # ── 관문 0: 티커 형식 ──
    # 조용히 버리지 않는다. 원문이 오염됐거나 파싱이 깨진 것인데, 버리고 넘어가면 개수 관문이
    # 잡아 줄 만큼 크게 틀린 날에만 알려지고 한두 건은 영영 안 보인다.
    if bad_sym:
        fail.append("SPX 심볼 형식 위반 %d건: %s — 추측으로 고치지 않는다"
                    % (len(bad_sym), ", ".join(bad_sym[:5])))

    # ── 관문 2: 개수 ──
    if not (LIM_SPX[0] <= len(spx) <= LIM_SPX[1]):
        fail.append("SPX 개수 %d — 정상 범위 %s 밖(파싱이 깨졌을 가능성)" % (len(spx), LIM_SPX))
    if not (LIM_NDX[0] <= len(ndx) <= LIM_NDX[1]):
        fail.append("NDX 개수 %d — 정상 범위 %s 밖" % (len(ndx), LIM_NDX))

    # ── 관문 1: SPX 두 소스 합의 ──
    try:
        spy = spy_symbols()
        hit = len(set(spx) & spy)
        rate = hit / max(1, len(spx))
        print("교차 확인 — SPY 보유내역과 %d/%d 일치 (%.1f%%)" % (hit, len(spx), 100 * rate))
        if rate < AGREE_MIN:
            fail.append("SPX가 SPY 보유내역과 %.1f%%만 일치 — 한쪽이 틀렸다(기준 %.0f%%)"
                        % (100 * rate, 100 * AGREE_MIN))
    except Exception as e:
        fail.append("SPY 보유내역을 못 받아 교차 확인 불가: %s — 확인 없이 쓰지 않는다" % e)

    # ── 조립 ──
    # ⚠ 회사명은 **기존 것을 잇는다**. 위키는 'Apple Inc.', 기존 정본은 'APPLE INC' 꼴이라
    #   그대로 받으면 518개 이름이 한꺼번에 바뀐다 — 요청은 '자동 갱신'이지 '표기 변경'이 아니다.
    #   신규 편입 종목만 위키 이름을 쓴다. 표기를 바꿀 거면 그건 따로 결정할 일이다.
    def nm(t, wiki_name):
        old = cur_m.get(t) or {}
        return old.get("name") or wiki_name

    new = {}
    for t, v in spx.items():
        new[t] = {"name": nm(t, v["name"]), "sector": v["sector"], "idx": ["SPX"]}
    for t, v in ndx.items():
        if t in new:
            new[t]["idx"] = ["NDX", "SPX"]
        else:
            # NDX 전용 — 위키 NDX 표는 ICB 분류라 GICS가 없다. 기존 명단에서 잇는다.
            old = cur_m.get(t) or {}
            new[t] = {"name": nm(t, v["name"]), "sector": old.get("sector", ""), "idx": ["NDX"]}
    name_drift = sorted(t for t in new if t in cur_m
                        and (spx.get(t) or ndx.get(t) or {}).get("name")
                        and cur_m[t].get("name") != (spx.get(t) or ndx.get(t))["name"])
    for t in new:
        new[t]["idx"] = sorted(new[t]["idx"])

    # ── 관문 4: 섹터 완전성 ──
    bad = sorted(t for t, v in new.items() if v["sector"] not in GICS)
    if bad:
        fail.append("GICS 섹터가 없는 종목 %d개: %s — 추측으로 채우지 않는다"
                    % (len(bad), ", ".join(bad[:8])))

    # ── 관문 3: 변동 상한 ──
    add = sorted(set(new) - set(cur_m))
    rem = sorted(set(cur_m) - set(new))
    n_spx_chg = len([t for t in add if "SPX" in new[t]["idx"]]) + \
                len([t for t in rem if "SPX" in (cur_m[t].get("idx") or [])])
    n_ndx_chg = len([t for t in add if "NDX" in new[t]["idx"]]) + \
                len([t for t in rem if "NDX" in (cur_m[t].get("idx") or [])])
    sec_chg = sorted((t, cur_m[t]["sector"], new[t]["sector"]) for t in new
                     if t in cur_m and cur_m[t].get("sector") and cur_m[t]["sector"] != new[t]["sector"])
    print("변동 — 편입 %d %s · 편출 %d %s" % (len(add), add[:6], len(rem), rem[:6]))
    if sec_chg:
        print("섹터 재분류 %d건:" % len(sec_chg))
        for t, o_, n_ in sec_chg[:10]:
            print("   %-6s %s → %s" % (t, o_, n_))
    if name_drift:
        print("표기만 다른 이름 %d건 — 기존 표기를 유지한다(예: %s)"
              % (len(name_drift), ", ".join(name_drift[:4])))
    if n_spx_chg > MAXCHG_SPX:
        fail.append("SPX 변동 %d건 — 상한 %d 초과. 지수 리밸런스가 이렇게 크지 않다"
                    % (n_spx_chg, MAXCHG_SPX))
    if n_ndx_chg > MAXCHG_NDX:
        fail.append("NDX 변동 %d건 — 상한 %d 초과" % (n_ndx_chg, MAXCHG_NDX))

    if fail:
        print("\n❌ 관문 미통과 — 파일을 건드리지 않는다:")
        for f in fail:
            print("   ·", f)
        return 1
    if dry:
        print("\n(--dry) 관문 통과. 쓰지 않고 종료.")
        return 0

    doc = {
        "as_of_members": dt.date.today().isoformat(),
        "note": "지수 편입 명단. 출처 — S&P 500: 위키백과 목록 + SSGA SPY 보유내역 교차 확인, "
                "NASDAQ-100: 위키백과 목록. 오늘 스냅샷이며 과거 편입 이력이 아니다"
                "(백테스트의 생존편향은 각 결과 화면에 별도 명시).",
        "gates": {"spx_n": len(spx), "ndx_n": len(ndx),
                  "added": add, "removed": rem,
                  "cross_check": "SPY 보유내역 대조",
                  "sector_changed": [{"t": t, "from": a, "to": b} for t, a, b in sec_chg],
                  "name_style_kept": len(name_drift),
                  "ndx_caveat": "NASDAQ-100은 교차할 1차 자료를 못 찾아 변동 상한에만 의존한다"},
        "members": dict(sorted(new.items())),
    }
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    io.open(OUT, "a", encoding="utf-8").write("\n")
    print("\n✅ 기록 — %d종목 (SPX %d · NDX %d · 겹침 %d)"
          % (len(new), sum(1 for v in new.values() if "SPX" in v["idx"]),
             sum(1 for v in new.values() if "NDX" in v["idx"]),
             sum(1 for v in new.values() if len(v["idx"]) == 2)))
    return 0


if __name__ == "__main__":
    # 멈춤 사유를 체크런 주석으로 올린다 — 로그 본문은 사내 PC 에서 못 받는다(build/gate.py 참조)
    import gate
    gate.run(main, "지수 편입 명단")
