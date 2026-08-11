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
이 파일도 같은 경로를 쓴다 — 사내망을 타지 않는다. 로컬에서 실행하지 말 것.
수집·파싱·CIK 해석은 refresh_facts 를 **import 해서 그대로 쓴다**. 구현이 둘이면 어긋난다.

## 무엇을 받는지 러너가 어떻게 아나

명단은 data/style_pit.json 의 universe.gone_tickers 다(build/style_pit.py 가 로컬에서 넣는다).
선정 시점 멤버십(data/index_history.json)은 저장소에 커밋된다. 러너는
계산할 수 없다 — 커밋된 명단을 읽는 것이 유일한 경로다. 명단이 없으면 크게 죽는다.

## 한계

· 인수·비상장화로 사라진 회사는 SEC company_tickers.json 에 티커가 없어 CIK 해석이 실패한다.
  그 종목은 못 받는다(목록으로 남긴다). 지수에서 빠졌을 뿐 아직 상장돼 있는 종목은 받힌다.
· 재무는 **as-reported 최신본**이다. 정정 이전의 원본을 주지 않으므로 정정된 항목에는
  약한 룩어헤드가 남는다 — data/fx/ 도 같은 성질이라 두 쪽이 대칭이다.

  python build/pit_facts.py           (러너)
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
import refresh_facts as RF      # extract·load_cik_map·FACTS_URL·LABEL 를 그대로 쓴다
import edgar


def wanted():
    """받을 명단 → {티커: 마지막 멤버월 or None}.

    정본은 data/pit_universe.json(build/pit_backtest.py --universe-only 가 낸다) — PIT 창
    (pit_backtest.START 부터 · 현재 2021-07)의 편출 종목이라 펀더멘털 규칙까지 덮는다. 스타일 창만 담은
    style_pit.json 의 gone_tickers 도 합친다(둘의 창이 달라 서로를 포함하지 않는다).
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
    return out


def earliest_period(tags):
    """이 법인이 보고한 가장 이른 기간말. 티커 재사용 판정에 쓴다."""
    ds = []
    for v in (tags or {}).values():
        for row in ((v or {}).get("q") or []) + ((v or {}).get("a") or []) + ((v or {}).get("i") or []):
            if isinstance(row, list) and row and isinstance(row[0], str):
                ds.append(row[0])
    return min(ds) if ds else None


def main() -> int:
    want = wanted()
    # 🚨 RF.load_cik_map() 을 쓰면 안 된다 — 그것은 data/cik_map.json(오늘 518종)을 먼저
    #   읽으므로 편출 종목 CIK 가 **전부 없다**(실측: 첫 실행에서 32/32 실패).
    #   여기 필요한 것은 SEC 전체 등록 목록이다. cik_map.json 은 보조로만 얹는다
    #   (그쪽에 전신 법인 보정이 들어 있어 겹치는 티커는 그 값이 더 정확하다).
    cmap = dict(edgar.ticker_cik_map())
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
    hcik = {}
    _ih = os.path.join(DATA, "index_history.json")
    if os.path.exists(_ih):
        hcik = (json.load(io.open(_ih, encoding="utf-8")).get("cik") or {})
    n_hist = sum(1 for t in want if hcik.get(t))
    n_diff = sum(1 for t in want if hcik.get(t) and cmap.get(t)
                 and str(hcik[t]).zfill(10) != str(cmap[t]).zfill(10))
    print("편출 명단 %d종 · 티커→CIK: SEC 전체 %d개(+보조 %d개) · **당시 CIK 우선** %d종"
          % (len(want), n_sec, len(cmap) - n_sec, n_hist))
    if n_diff:
        print("  🚨 당시 CIK 와 SEC 현행이 다른 종목 %d종 — 당시 것을 쓴다(티커 재배정)" % n_diff)
    os.makedirs(OUT_DIR, exist_ok=True)

    got, no_cik, no_facts, reused, changed = [], [], [], [], 0
    for n, t in enumerate(sorted(want), 1):
        last = want[t]
        cik = hcik.get(t) or hcik.get(t.upper()) or cmap.get(t) or cmap.get(t.upper())
        if not cik:
            no_cik.append(t); continue
        j = edgar.get_json(RF.FACTS_URL % int(cik))
        tags = RF.extract(j) if j else {}
        used_pred = 0
        if not tags:                      # 지주회사 전환 — 전신 법인 아래에 재무가 있다
            for pcik in edgar.PREDECESSOR.get(t.upper(), []):
                pj = edgar.get_json(RF.FACTS_URL % int(pcik))
                ptags = RF.extract(pj) if pj else {}
                if ptags:
                    j, tags, cik, used_pred = pj, ptags, pcik, 1
                    break
        if not tags and hcik.get(t) and cmap.get(t) and int(cmap[t]) != int(cik):
            # ⚠ 당시 CIK 에 재무가 없으면 현행 CIK 로 물러선다. 위키 표가 분사 달에 전신
            #   법인의 CIK 를 적어 두는 경우가 있어서다(실측 NAVI: 2014-06 행에 SLM 의
            #   1084750 이 적혀 있고 그 아래엔 Navient 재무가 없다). 아래 재사용 가드는
            #   그대로 걸리므로, 물러서도 '그 시점에 없던 회사' 는 걸러진다.
            j2 = edgar.get_json(RF.FACTS_URL % int(cmap[t]))
            t2 = RF.extract(j2) if j2 else {}
            if t2:
                print("  ~ %s 당시 CIK %s 에 재무 없음 → 현행 %s 로 물러섬(%s)"
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
        std = "IFRS" if not (((j.get("facts") or {}).get("us-gaap"))) else "us-gaap"
        doc = {"t": t, "cik": int(cik), "nm": j.get("entityName") or t,
               "labels": {k: RF.LABEL[k] for k in tags if k in RF.LABEL},
               "std": std, "tags": tags}
        if used_pred:
            doc["pred"] = 1
        body = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
        fn = os.path.join(OUT_DIR, "%s.json" % t.replace("/", "_"))
        old = io.open(fn, encoding="utf-8").read() if os.path.exists(fn) else None
        if old != body:
            io.open(fn, "w", encoding="utf-8", newline="").write(body)
            changed += 1
        got.append(t)
        # 스타일 셋이 실제로 쓰는 항목만 세어 본다 — 파일이 있어도 이게 없으면 못 채점한다.
        need = [k for k in ("ni", "eq", "liab", "eps", "rev", "sh") if k not in tags]
        print("  %3d/%d %-6s %-42s %s" % (n, len(want), t, (doc["nm"] or "")[:42],
                                          ("결손 " + ",".join(need)) if need else "완비"))

    print()
    print("받음 %d종(변경 %d) · CIK 없음 %d종 %s · 재무 없음 %d종 %s"
          % (len(got), changed, len(no_cik), no_cik, len(no_facts), no_facts))
    if reused:
        print("⚠ 티커 재사용으로 제외 %d종: %s" % (len(reused), " · ".join(reused)))
    if not got:
        raise SystemExit("한 종목도 못 받았다 — CIK 해석이나 SEC 응답을 확인할 것")
    sz = sum(os.path.getsize(os.path.join(OUT_DIR, f)) for f in os.listdir(OUT_DIR)) / 1024
    print("→ %s · 파일 %d개 · %.0fKB" % (OUT_DIR, len(os.listdir(OUT_DIR)), sz))
    return 0


if __name__ == "__main__":
    # 멈춤 사유를 체크런 주석으로 올린다 — 로그 본문은 사내 PC 에서 못 받는다(build/gate.py 참조)
    import gate
    gate.run(main, "편출 종목 재무")
