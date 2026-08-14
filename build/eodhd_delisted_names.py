# -*- coding: utf-8 -*-
"""EODHD 편출 종목 명단에서 **이름만** 추려 data/delisted_names.json 을 만든다.

왜.
  편입 원장(constituents.html)에 이름이 없는 종목이 47종 남아 있었다. 위키 표의 CIK 열로
  대부분 메웠지만, 나스닥 전용 종목(Liberty 계열·Qurate·Trip.com 등)은 그 표에 CIK 열이
  없어 끝까지 안 채워진다. EODHD 의 편출 종목 명단이 그 자리를 메운다.

무엇을 / 무엇을 안 하나.
  · **이름만** 쓴다. 이 명단에는 섹터가 없다(필드는 Code·Name·Country·Exchange·
    Currency·Type·Isin 뿐이다). 섹터 미상 23종은 이걸로 안 줄어든다.
  · 원장이 실제로 쓰는 티커만 남긴다 — 명단 전체는 59,183종·8.5MB 라 저장소에 둘 것이
    아니다. 추려 두면 수십 줄이다.
  · 보통주(Common Stock)만 본다. 같은 티커가 펀드·우선주로도 있어 섞이면 회사가 바뀐다.

🚨 API 토큰은 이 파일 어디에도 없다. 환경변수 EODHD_API_TOKEN 으로 받는다 —
  이 저장소는 공개다. 토큰이 없으면 이미 받아 둔 원본 경로(--src)를 쓴다.

⚠ 무료 플랜으로 확인한 것(2026-08-14, 4콜):
    편출 **명단** 은 열린다(200 · 59,183종).
    편출 종목 **가격** 은 안 열린다 — 403 이 아니라 **빈 배열 200** 이 온다.
    (ANTM·AET 둘 다 [] · 같은 요청형식으로 AAPL 은 정상) 자동화하면 '자료가 없다' 로
    조용히 지나가는 모양이라, 뒤에 이 API 로 가격을 받게 되면 빈 응답을 반드시 실패로
    다뤄야 한다.

    python build/eodhd_delisted_names.py --src <받아둔 json>   # 콜 안 씀
    python build/eodhd_delisted_names.py                        # EODHD_API_TOKEN 으로 1콜
"""
import io
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "delisted_names.json")
URL = "https://eodhd.com/api/exchange-symbol-list/US?api_token=%s&delisted=1&fmt=json"


def _load(name):
    try:
        return json.load(io.open(os.path.join(DATA, name), encoding="utf-8"))
    except Exception:
        return None


def fetch(src=None):
    if src:
        return json.load(io.open(src, encoding="utf-8"))
    tok = os.environ.get("EODHD_API_TOKEN")
    if not tok:
        raise SystemExit("EODHD_API_TOKEN 이 없다 — 환경변수로 주거나 --src 로 받아 둔 "
                         "파일을 가리킬 것(토큰을 코드에 적지 않는다)")
    import urllib.request
    with urllib.request.urlopen(URL % tok, timeout=180) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def main():
    src = None
    if "--src" in sys.argv:
        src = sys.argv[sys.argv.index("--src") + 1]
    rows = fetch(src)
    # 보통주만. 같은 티커가 펀드·우선주로도 있어 섞으면 회사가 바뀐다.
    by = {}
    for x in rows:
        if x.get("Type") == "Common Stock" and x.get("Code"):
            by.setdefault(x["Code"], x)
    print("편출 명단 %d종 (보통주 %d)" % (len(rows), len(by)))

    led = _load("index_ledger.json")
    if not led:
        raise SystemExit("data/index_ledger.json 이 없다 — build/index_ledger.py 를 먼저 돌릴 것")
    seen = set()
    for k in ("spx", "ndx"):
        A = led["idx"][k]
        seen |= set(A["base"]["t"])
        for _m, r in A["m"].items():
            seen |= set(r.get("add") or [])
            seen |= set(r.get("drop") or [])
    meta = led.get("meta") or {}
    # 이름이 비어 있는 것만 — 이미 아는 이름을 이 출처로 덮지 않는다.
    want = [t for t in seen if not (meta.get(t) or ["", ""])[0]]
    out = {}
    for t in sorted(want):
        x = by.get(t)
        if x and x.get("Name"):
            out[t] = {"name": x["Name"][:60], "ex": x.get("Exchange") or "",
                      "isin": x.get("Isin") or ""}
    doc = {
        "note": "편입 원장에서 이름이 비어 있던 티커의 회사명. 출처 EODHD 편출 종목 명단"
                "(exchange-symbol-list/US?delisted=1). 이름만 옮겼고 섹터는 그 명단에 없다.",
        "source": "EODHD — exchange-symbol-list/US?delisted=1 (Common Stock 만)",
        "n_asked": len(want), "n_found": len(out), "names": out,
    }
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"))
    print("→ %s · 물어본 %d종 중 %d종 확보"
          % (os.path.relpath(OUT, ROOT), len(want), len(out)))
    for t in list(out)[:8]:
        print("   %-7s %s" % (t, out[t]["name"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
