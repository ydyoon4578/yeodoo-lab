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
선정 시점 멤버십(data/pit_members.json)이 사내 DB 원천이라 gitignore 이므로 러너는 스스로
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
    p = os.path.join(DATA, "style_pit.json")
    if not os.path.exists(p):
        raise SystemExit("data/style_pit.json 이 없다 — 사내망 PC 에서 build/style_pit.py 를 "
                         "먼저 돌려 편출 명단을 커밋할 것.")
    j = json.load(io.open(p, encoding="utf-8"))
    ts = ((j.get("universe") or {}).get("gone_tickers")) or []
    if not ts:
        raise SystemExit("style_pit.json 에 universe.gone_tickers 가 없다 — "
                         "build/style_pit.py 를 다시 돌려 명단을 채울 것.")
    return list(ts)


def main() -> int:
    want = wanted()
    # 🚨 RF.load_cik_map() 을 쓰면 안 된다 — 그것은 data/industry.json(오늘 518종)을 먼저
    #   읽으므로 편출 종목 CIK 가 **전부 없다**(실측: 첫 실행에서 32/32 실패).
    #   여기 필요한 것은 SEC 전체 등록 목록이다. industry.json 은 보조로만 얹는다
    #   (그쪽에 전신 법인 보정이 들어 있어 겹치는 티커는 그 값이 더 정확하다).
    cmap = dict(edgar.ticker_cik_map())
    n_sec = len(cmap)
    try:
        aux, src2 = RF.load_cik_map()
        if src2 == "data/industry.json":
            cmap.update(aux)
    except Exception:
        pass
    if not cmap:
        raise SystemExit("SEC company_tickers.json 을 못 읽었다 — 러너의 SEC 응답을 확인할 것")
    print("편출 명단 %d종 · 티커→CIK: SEC 전체 %d개(+보조 %d개)"
          % (len(want), n_sec, len(cmap) - n_sec))
    os.makedirs(OUT_DIR, exist_ok=True)

    got, no_cik, no_facts, changed = [], [], [], 0
    for n, t in enumerate(want, 1):
        cik = cmap.get(t) or cmap.get(t.upper())
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
        if not j or not tags:
            no_facts.append(t); continue
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
    if not got:
        raise SystemExit("한 종목도 못 받았다 — CIK 해석이나 SEC 응답을 확인할 것")
    sz = sum(os.path.getsize(os.path.join(OUT_DIR, f)) for f in os.listdir(OUT_DIR)) / 1024
    print("→ %s · 파일 %d개 · %.0fKB" % (OUT_DIR, len(os.listdir(OUT_DIR)), sz))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
