# -*- coding: utf-8 -*-
"""build/pit_facts.py — 지수에서 빠진 종목의 SEC 재무를 받는다 → data/fx_pit/

## 왜 따로 있나

퀄리티·가치·성장은 시점별 재무가 필요한데 data/fx/ 는 **오늘의 유니버스뿐**이다. 게다가
build/refresh_facts.py:551 이 오늘 유니버스에 없는 fx 파일을 지운다 — 편출 종목 재무를
fx 에 넣으면 다음 주 갱신에 사라진다. 그래서 지워지지 않는 별 디렉터리에 둔다.
이것이 채워지면 build/style_pit.py 가 여섯 스타일 전부를 PIT 로 잴 수 있다.

## 🚨 러너에서만 돌린다

SEC(data.sec.gov)는 사내 PC 의 로컬 호출 화이트리스트에 없다. 이 랩은 이미 SEC 를
GitHub Actions 러너에서만 받고 있고(build/refresh_facts.py ← .github/workflows/refresh-facts.yml),
이 파일도 같은 경로를 쓴다 — 사내망을 타지 않는다. 사내망 PC 에서 실행하지 말 것
(집 PC 재생성은 아래 로컬 옵션 — SEC_UA 를 명시하고 초당 호출을 낮춘다).
수집·파싱·CIK 해석은 refresh_facts 를 **import 해서 그대로 쓴다**. 구현이 둘이면 어긋난다.

## 무엇을 받는지 러너가 어떻게 아나

명단은 네 곳의 합이다(wanted 참조) — data/pit_universe.json · data/style_pit.json 의
universe.gone_tickers · 🚨 2026-09-25 부터 **§A0 발행사 지도(data/_issuer_map.json)의 편출 이름 전부**
(오늘 유니버스에 없는 SPX ∪ NDX 멤버, 2014-06~) · 이미 있는 data/fx_pit 파일.
  왜 지도를 더했나: 앞 두 명단은 S&P·스타일 창 기준이라 NDX 편출(ALXN·CELG·MXIM·XLNX …)과
  인수로 사라진 이름(SGEN·SPLK)이 빠졌다. 사내 DB 로 그 이름들의 가격을 메웠는데 주식수·자기자본이
  없어 커버리지 F0 에서 여전히 빠졌다(배치 R §F — 14종이 그랬다).

## CIK 해석(2026-09-25 — 지도가 먼저다)

  ① data/fx_splice.json(refresh_facts --build-splices · 지도의 재편 판정) — prepend 면 후계 CIK 를
     본으로 선행 CIK 역사를 앞에 붙이고, cut(FTI) 이면 기간말로 두 법인을 가른다.
  ② §A0 지도의 **마지막 재임 구간 주 CIK** — company_tickers.json 에 없는 인수·비상장 이름도 풀린다.
     index_history 의 평면 CIK 와 다른 곳은 EVHC 하나였다(AmSurg 895930 → Envision Healthcare 1678531).
  ③ 당시 CIK(index_history) → SEC 현행(company_tickers) + cik_map → 이미 있는 파일의 CIK.

## 새 파일을 만들지 않는 이름(기존 파일은 늘 다시 짓는다 — 지우지 않는다)

  · FPI(지도 fpi_q 가 재임 내내 1)·ADR(SHPG) — 20-F·10-K 주식수가 보통주 기준이라 ADR 가격 × 주식수가 틀린다.
  · 트래킹 주식 그룹(TRACKING) — 연결 재무를 트래킹 주식 한 종에 붙이면 시총이 몇 배로 틀린다.
  · 같은 발행사 그룹의 다른 티커가 **같은 달에** 멤버이고 그 티커가 오늘 유니버스거나 파일이 있을 때
    (NXP → NXPI 유령 · KLA → KLAC · 이중 클래스 둘째) — 단 index_history CIK 가 같아 패널이 한 종으로
    접는 짝은 만든다(해가 없다).
    🚨 2026-09-26 — 단 build/pit_alias.py 가 명단 티커를 보내는 **가격 키**(TFCFA 등 · '@' 키 제외)는 이 규칙에서 뺀다.
    패널은 주식수 · 장부가를 «가격 키 → 명단 티커» 차례로 찾는다. 21CF 시절 FOXA 의 가격 키는 TFCFA 인데 TFCFA 파일이
    없으면 명단 티커 FOXA 파일(= 뒤의 Fox Corp · CIK 1754301)로 떨어져 CIK 가 어긋났다(21CF 30 멤버-월이 덮임에서 빠졌다).
    TFCFA 파일은 TFCF 와 같은 법인(21CF · CIK 1308161)의 재무다.

## 한계

· 재무는 **as-reported 최신본**이다. 정정 이전의 원본을 주지 않으므로 정정된 항목에는
  약한 룩어헤드가 남는다 — data/fx/ 도 같은 성질이라 두 쪽이 대칭이다.
· 빈칸 메우기·선행 CIK 잇기·칸별 출처 CIK 는 refresh_facts 와 같다(그쪽 머리말 ①②③).

  python build/pit_facts.py                                             (러너)
  python build/pit_facts.py --rate 2 --cache DIR [--offline] [--only T1,T2]   (로컬 · SEC_UA 필수)
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(DATA, "fx_pit")

sys.path.insert(0, HERE)
import refresh_facts as RF      # extract·make_doc·get_facts·load_cik_map·FACTS_URL·LABEL 를 그대로 쓴다
import edgar
import pit_alias as PA          # 날짜 인식 별칭의 가격 키(형제 규칙 예외 · 2026-09-26)

# 별칭이 명단 티커를 보내는 가격 키 — 패널이 재무를 이 키로 먼저 찾는다(형제 규칙에서 뺀다 · 머리말)
ALIAS_PRICE_KEYS = frozenset(a["key"] for a in PA.ALIASES if "@" not in a["key"])

# 새 파일을 만들지 않는 발행사 그룹 — 트래킹 주식(연결 재무 하나를 여러 트래킹 주식이 나눠 쓴다)
TRACKING = {
    "g1560385": "Liberty Media — LMCA/LMCK 와 2016-04 재편 뒤 BATRA/BATRK(Braves 트래킹)",
    "g1355096": "Liberty Interactive — QVCA(QVC 그룹) · LVNTA(Ventures) · LINTA · QRTEA 트래킹",
    "g1570585": "Liberty Global — LBTYA/LBTYK 와 LILA/LILAK(LiLAC 트래킹 2015-07 ~ 2017-11)",
}
ADR = {"SHPG": "1 ADS = 보통주 3주(Shire) — 10-K 주식수는 보통주 기준"}


def _issuer_map():
    p = os.path.join(DATA, "_issuer_map.json")
    if not os.path.exists(p):
        return {}
    return json.load(io.open(p, encoding="utf-8"))


def wanted(M=None):
    """받을 명단 → {티커: 마지막 멤버월 or None}.

    정본은 data/pit_universe.json(build/pit_backtest.py --universe-only 가 낸다) — PIT 창
    (pit_backtest.START 부터 · 현재 2021-07)의 편출 종목이라 펀더멘털 규칙까지 덮는다. 스타일 창만 담은
    style_pit.json 의 gone_tickers 도 합친다(둘의 창이 달라 서로를 포함하지 않는다).
    2026-09-25 — §A0 지도의 편출 이름(오늘 유니버스에 없는 tm 티커)과 이미 있는 fx_pit 파일도 합친다.
    """
    out = {}
    p = os.path.join(DATA, "pit_universe.json")
    if os.path.exists(p):
        for t, v in (json.load(io.open(p, encoding="utf-8")).get("tickers") or {}).items():
            out[t] = (v or {}).get("last")
    q = os.path.join(DATA, "style_pit.json")
    if os.path.exists(q):
        for t in ((json.load(io.open(q, encoding="utf-8")).get("universe") or {})
                  .get("gone_tickers") or []):
            out.setdefault(t, None)
    if not out:
        raise SystemExit("편출 명단이 없다 — 사내망 PC 에서 "
                         "build/pit_backtest.py --universe-only 를 돌려 "
                         "data/pit_universe.json 을 커밋할 것.")
    M = M if M is not None else _issuer_map()
    today = set(t for t, _n in RF.load_universe())
    for t, rows in (M.get("tm") or {}).items():
        if t in today or t.replace(".", "-") in today or t.replace("-", ".") in today:
            continue
        last = max(r[1] for r in rows) if rows else None
        if out.get(t) is None or (last and last > (out.get(t) or "")):
            out[t] = last
    if os.path.isdir(OUT_DIR):
        for f in os.listdir(OUT_DIR):
            if f.endswith(".json"):
                out.setdefault(f[:-5], None)
    return out


def _sec_tickers(offline=False):
    """SEC company_tickers.json → {티커: CIK}. 로컬 캐시(--cache)가 있으면 거기 두고 다시 읽는다(--offline 재현)."""
    d = RF._FETCH.get("dir")
    p = os.path.join(d, "company_tickers.map.json") if d else None
    if p and os.path.exists(p):
        return json.load(io.open(p, encoding="utf-8"))
    if offline:
        return {}
    m = dict(edgar.ticker_cik_map())
    if p and m:
        os.makedirs(d, exist_ok=True)
        json.dump(m, io.open(p, "w", encoding="utf-8"))
    return m


def earliest_period(tags):
    """이 법인이 보고한 가장 이른 기간말. 티커 재사용 판정에 쓴다."""
    ds = []
    for v in (tags or {}).values():
        for row in ((v or {}).get("q") or []) + ((v or {}).get("a") or []) + ((v or {}).get("i") or []):
            if isinstance(row, list) and row and isinstance(row[0], str):
                ds.append(row[0])
    return min(ds) if ds else None


def _tenure(rows):
    """tm 행 → 주 CIK 가 바뀌는 구간 [[주 CIK, 첫 달, 끝 달]]."""
    out = []
    for r in rows or []:
        if out and out[-1][0] == int(r[3]):
            out[-1][2] = r[1]
        else:
            out.append([int(r[3]), r[0], r[1]])
    return out


def _skip_new(t, M, hcik, today, have_file):
    """새 파일을 만들지 않을 이유(없으면 None). 기존 파일에는 쓰지 않는다."""
    rows = (M.get("tm") or {}).get(t) or []
    if t in ADR:
        return "adr: " + ADR[t]
    if rows and all(r[7] == 1 for r in rows):
        return "fpi(지도 fpi_q · 재임 내내 20-F/40-F)"
    groups = set(r[2] for r in rows if r[2])
    for g in groups:
        if g in TRACKING:
            return "tracking: " + TRACKING[g]
    if t in ALIAS_PRICE_KEYS:
        return None                       # 별칭의 가격 키 — 패널이 이 키로 재무를 먼저 찾는다(머리말 · TFCFA)
    for g in groups:
        mine = set()                      # 이 그룹에 속한 달만(AGN 은 2015-02 까지 다른 그룹 — Allergan Inc)
        for r in rows:
            if r[2] != g:
                continue
            for k in range(int(r[0][:4]) * 12 + int(r[0][5:7]) - 1, int(r[1][:4]) * 12 + int(r[1][5:7])):
                mine.add(k)
        for s, (a, b) in ((M.get("groups") or {}).get(g, {}).get("tickers") or {}).items():
            if s == t:
                continue
            ks = set(range(int(a[:4]) * 12 + int(a[5:7]) - 1, int(b[:4]) * 12 + int(b[5:7])))
            if not (ks & mine):
                continue
            if not (s in today or s.replace(".", "-") in today or have_file(s)):
                continue
            h_t, h_s = hcik.get(t), hcik.get(s)
            if h_t and h_s and int(h_t) == int(h_s):
                continue                  # 패널이 한 종으로 접는 이중 클래스 — 만들어도 해가 없다
            return "sibling: 같은 그룹 %s 의 %s 가 같은 달 멤버이고 재무가 있다" % (g, s)
    return None


def main() -> int:
    A = RF.local_args()
    M = _issuer_map()
    want = wanted(M)
    only = set(x.strip() for x in (A.only or "").split(",") if x.strip())
    if only:
        want = {t: v for t, v in want.items() if t in only}
    # 🚨 RF.load_cik_map() 을 쓰면 안 된다 — 그것은 data/cik_map.json(오늘 518종)을 먼저
    #   읽으므로 편출 종목 CIK 가 **전부 없다**(실측: 첫 실행에서 32/32 실패).
    #   여기 필요한 것은 SEC 전체 등록 목록이다. cik_map.json 은 보조로만 얹는다
    #   (그쪽에 전신 법인 보정이 들어 있어 겹치는 티커는 그 값이 더 정확하다).
    cmap = _sec_tickers(A.offline)
    n_sec = len(cmap)
    try:
        aux, src2 = RF.load_cik_map()
        if src2 == "data/cik_map.json":
            cmap.update(aux)
    except Exception:
        pass
    if not cmap:
        raise SystemExit("SEC company_tickers.json 을 못 읽었다 — 러너의 SEC 응답을 확인할 것")
    # 🚨 2026-08-11 — **그때의 CIK 를 먼저 본다.** 위 cmap 은 SEC 의 *현행* 티커→CIK 라
    #   티커가 그 뒤 다른 법인에 넘어간 종목은 **남의 회사 재무**를 가져온다. 실측으로
    #   6종이 그랬다: BBT 는 BB&T(0000092230) 가 아니라 BEACON FINANCIAL(0001108134),
    #   AA 는 구 Alcoa(0000004281) 가 아니라 Alcoa Corp(0001675149) 를 받고 있었다.
    #   아래 '법인 최초 보고기간 > 멤버 마지막월' 가드는 이걸 못 잡는다 — 티커를 물려받은
    #   쪽이 **더 오래된 법인**이면 최초 보고기간이 앞서기 때문이다.
    #   (같은 날 build/pit_backtest.py 는 가격 쪽에 같은 방어를 넣었다. 한쪽만 고치면
    #    같은 종목이 가격은 A 회사, 재무는 B 회사가 되어 더 나쁘다.)
    # 🚨 2026-09-25 — 그 위에 **§A0 지도**를 먼저 본다(머리말 'CIK 해석'). 지도는 DERA 티커 몫 ·
    #   submissions · 수작업 검증으로 (티커, 월) → 발행사를 풀었다 — 평면 CIK 한 개보다 정확하다.
    hcik = {}
    _ih = os.path.join(DATA, "index_history.json")
    if os.path.exists(_ih):
        hcik = (json.load(io.open(_ih, encoding="utf-8")).get("cik") or {})
    splices = RF.load_splices()
    tm = M.get("tm") or {}
    today = set(t for t, _n in RF.load_universe())
    old_cik = {}
    for f in (os.listdir(OUT_DIR) if os.path.isdir(OUT_DIR) else []):
        if f.endswith(".json"):
            try:
                old_cik[f[:-5]] = int(json.load(io.open(os.path.join(OUT_DIR, f), encoding="utf-8")).get("cik") or 0)
            except Exception:
                pass
    n_hist = sum(1 for t in want if hcik.get(t))
    n_diff = sum(1 for t in want if hcik.get(t) and cmap.get(t)
                 and str(hcik[t]).zfill(10) != str(cmap[t]).zfill(10))
    print("편출 명단 %d종 · 티커→CIK: SEC 전체 %d개(+보조 %d개) · 당시 CIK %d종 · 지도 tm %d종 · 잇기 표 %d종"
          % (len(want), n_sec, len(cmap) - n_sec, n_hist, sum(1 for t in want if tm.get(t)), len(splices)))
    if n_diff:
        print("  🚨 당시 CIK 와 SEC 현행이 다른 종목 %d종 — 당시 것을 쓴다(티커 재배정)" % n_diff)
    os.makedirs(OUT_DIR, exist_ok=True)

    written = set(old_cik)

    def have_file(s):
        return (s in written or os.path.exists(os.path.join(RF.DIR_FX, s + ".json"))
                or os.path.exists(os.path.join(RF.DIR_FX, s.replace(".", "-") + ".json")))

    got, no_cik, no_facts, reused, skipped, changed, new = [], [], [], [], {}, 0, []
    cik_src = {}
    for n, t in enumerate(sorted(want), 1):
        last = want[t]
        exists = t in old_cik
        sp = splices.get(t)
        cik, how = None, None
        if sp:
            cik = int(sp["cur"]) if sp["mode"] == "prepend" else int(sp["segs"][-1][0])
            how = "splice:" + sp["mode"]
        elif tm.get(t):
            cik, how = _tenure(tm[t])[-1][0], "a0"
        else:
            c = hcik.get(t) or hcik.get(t.upper()) or cmap.get(t) or cmap.get(t.upper()) or old_cik.get(t)
            if c:
                cik, how = int(c), ("hist" if (hcik.get(t) or hcik.get(t.upper())) else
                                   ("sec" if (cmap.get(t) or cmap.get(t.upper())) else "file"))
        if not cik:
            no_cik.append(t); continue
        if not exists:
            why = _skip_new(t, M, hcik, today, have_file)
            if why:
                skipped[t] = why; continue
        cik_src[t] = how
        j = RF.get_facts(cik)
        tags = RF.extract(j) if j else {}
        used_pred = 0
        if not tags:                      # 지주회사 전환 — 전신 법인 아래에 재무가 있다
            for pcik in edgar.PREDECESSOR.get(t.upper(), []):
                pj = RF.get_facts(pcik)
                ptags = RF.extract(pj) if pj else {}
                if ptags:
                    j, tags, cik, used_pred = pj, ptags, pcik, 1
                    break
        if not tags and hcik.get(t) and cmap.get(t) and int(cmap[t]) != int(cik) and not sp:
            # ⚠ 당시 CIK 에 재무가 없으면 현행 CIK 로 물러선다. 위키 표가 분사 달에 전신
            #   법인의 CIK 를 적어 두는 경우가 있어서다(실측 NAVI: 2014-06 행에 SLM 의
            #   1084750 이 적혀 있고 그 아래엔 Navient 재무가 없다). 아래 재사용 가드는
            #   그대로 걸리므로, 물러서도 '그 시점에 없던 회사' 는 걸러진다.
            j2 = RF.get_facts(cmap[t])
            t2 = RF.extract(j2) if j2 else {}
            if t2:
                print("  ~ %s CIK %s 에 재무 없음 → 현행 %s 로 물러섬(%s)"
                      % (t, str(cik).zfill(10), str(cmap[t]).zfill(10),
                         (j2.get("entityName") or "")[:30]))
                j, tags, cik = j2, t2, cmap[t]
        if not j or not tags:
            no_facts.append(t); continue
        # 🚨 티커 재사용 가드 — 이 티커가 지수 멤버였던 마지막 달보다 법인의 **최초** 보고기간이
        #   뒤면, SEC 가 준 것은 그 티커를 뒤에 물려받은 **다른 회사**다(FB → ProShares 선례).
        #   그 재무를 쓰면 '그 시점에 존재하지도 않던 회사의 숫자로 과거를 채점' 하게 된다.
        ep = earliest_period(tags)
        if last and ep and ep[:7] > last:
            reused.append("%s(법인 최초 %s > 멤버 마지막 %s · %s)"
                          % (t, ep[:7], last, (j.get("entityName") or "")[:24]))
            continue
        lg = []
        doc = RF.make_doc(t, cik, j, tags, name=t, used_pred=used_pred, splice=sp, get=RF.get_facts, log=lg)
        for x in lg:
            print("    ~ %s %s" % (t, x))
        if any(x.startswith(RF.SPLICE_FAIL) for x in lg):
            # 선행 법인을 못 받았다(일시 장애) — 지난 파일을 그대로 둔다(있으면)
            print("  ⚠ %s 선행 CIK 재무를 못 받아 이번 실행에서는 파일을 안 바꾼다" % t)
            no_facts.append(t)
            continue
        body = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
        fn = os.path.join(OUT_DIR, "%s.json" % t.replace("/", "_"))
        old = io.open(fn, encoding="utf-8").read() if os.path.exists(fn) else None
        if old != body:
            io.open(fn, "w", encoding="utf-8", newline="").write(body)
            changed += 1
        if old is None:
            new.append(t)
        if exists and old_cik.get(t) and int(old_cik[t]) != int(doc["cik"]):
            print("  🔁 %s 본 CIK %d → %d (%s)" % (t, old_cik[t], doc["cik"], how))
        written.add(t)
        got.append(t)
        # 스타일 셋이 실제로 쓰는 항목만 세어 본다 — 파일이 있어도 이게 없으면 못 채점한다.
        tg = doc["tags"]
        need = [k for k in ("ni", "eq", "liab", "eps", "rev", "sh") if k not in tg]
        print("  %3d/%d %-6s %-42s %-12s %s" % (n, len(want), t, (doc["nm"] or "")[:42], how,
                                                ("결손 " + ",".join(need)) if need else "완비"))

    print()
    print("받음 %d종(변경 %d · 새 파일 %d) · CIK 없음 %d종 %s · 재무 없음 %d종 %s"
          % (len(got), changed, len(new), len(no_cik), no_cik, len(no_facts), no_facts))
    print("새 파일: %s" % " ".join(new))
    if skipped:
        print("새 파일을 안 만든 이름 %d종:" % len(skipped))
        for t, why in sorted(skipped.items()):
            print("    %-6s %s" % (t, why))
    if reused:
        print("⚠ 티커 재사용으로 제외 %d종: %s" % (len(reused), " · ".join(reused)))
    if RF.FILL_LOG["cells"]:
        print("태그 빈칸 메우기: %d칸 (%s)" % (RF.FILL_LOG["cells"],
              " ".join("%s %d" % kv for kv in sorted(RF.FILL_LOG["keys"].items()))))
    if RF._FETCH["dir"]:
        print("companyfacts: 캐시 %d · SEC %d" % (RF._FETCH["n_cache"], RF._FETCH["n_net"]))
    if not got:
        raise SystemExit("한 종목도 못 받았다 — CIK 해석이나 SEC 응답을 확인할 것")
    sz = sum(os.path.getsize(os.path.join(OUT_DIR, f)) for f in os.listdir(OUT_DIR)) / 1024
    print("→ %s · 파일 %d개 · %.0fKB" % (OUT_DIR, len(os.listdir(OUT_DIR)), sz))
    return 0


if __name__ == "__main__":
    # 멈춤 사유를 체크런 주석으로 올린다 — 로그 본문은 사내 PC 에서 못 받는다(build/gate.py 참조)
    import gate
    gate.run(main, "편출 종목 재무")
