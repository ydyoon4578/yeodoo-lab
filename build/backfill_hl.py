# -*- coding: utf-8 -*-
"""data/sd/<티커>.json 에 고가·저가 시계열(hd·ld)을 채운다 — 1회성 백필.

왜 필요한가. 사이트는 매일 22개 테크니컬 이벤트(스토캐스틱·CCI·Williams·MFI·돈치안·Aroon 등)를
종목별로 발동시켜 보여준다. 그런데 저장된 시계열은 종가(pxd)와 거래량(vd)뿐이라, **그 신호들을
과거로 되돌려 검증할 수가 없었다**. 절반 이상이 고가·저가를 쓰기 때문이다.
신호를 게시하면서 그 신호의 성적을 못 재는 상태는 이 랩의 규약과 맞지 않는다.

안전장치 — 받아온 종가를 이미 저장된 pxd와 대조한다. 티커 매핑이 어긋나거나(BRK.B→BRK-B 등)
분할·배당 조정 기준이 다르면 **다른 종목의 고저가를 붙이는 사고**가 되므로, 어긋나면 그 종목은
건드리지 않고 보고만 한다.

  python build/backfill_hl.py            # 전체
  python build/backfill_hl.py --limit 20 # 앞 20종목만(점검용)

이후 갱신은 build/refresh_stocks.py가 직접 hd·ld를 쓴다 — 이 스크립트는 다시 돌릴 필요가 없다.
"""
from __future__ import annotations
import io, json, os, sys, time

import pandas as pd
import yfinance as yf
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR_SD = os.path.join(DATA, "sd")
BATCH = 60          # 한 번에 받는 티커 수 — 크게 잡으면 야후가 조용히 일부를 비워서 준다
TOL = 0.02          # 종가 대조 허용 오차(2%) — 조정 시점 차이 정도만 허용한다


def yfsym(t: str) -> str:
    return t.replace(".", "-")


def main() -> int:
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    tickers = [s["t"] for s in st["stocks"]]
    if limit:
        tickers = tickers[:limit]
    idx = pd.to_datetime(dates)
    end = (idx[-1] + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    ok = skip_mismatch = skip_missing = skip_nofile = 0
    bad = []
    for i in range(0, len(tickers), BATCH):
        chunk = tickers[i:i + BATCH]
        syms = [yfsym(t) for t in chunk]
        try:
            df = yf.download(syms, start=dates[0], end=end, auto_adjust=True,
                             progress=False, threads=True)
        except Exception as e:
            print("  배치 실패(%d~%d): %s" % (i, i + len(chunk), e))
            continue
        if df is None or df.empty:
            print("  배치 비어 있음(%d~%d)" % (i, i + len(chunk)))
            continue
        # 단일 티커면 컬럼이 1레벨로 내려온다
        single = not isinstance(df.columns, pd.MultiIndex)

        for t, sym in zip(chunk, syms):
            p = os.path.join(DIR_SD, "%s.json" % t)
            if not os.path.exists(p):
                skip_nofile += 1
                continue
            try:
                if single:
                    h, l, c = df["High"], df["Low"], df["Close"]
                else:
                    h, l, c = df[("High", sym)], df[("Low", sym)], df[("Close", sym)]
            except KeyError:
                skip_missing += 1
                bad.append((t, "응답에 없음"))
                continue
            h = h.reindex(idx); l = l.reindex(idx); c = c.reindex(idx)
            if c.notna().sum() < 30:
                skip_missing += 1
                bad.append((t, "유효 종가 %d일" % int(c.notna().sum())))
                continue

            d = json.load(io.open(p, encoding="utf-8"))
            pxd = d.get("pxd") or []
            # ── 대조: 저장된 종가와 받아온 종가가 같은 종목인지 ──
            pairs = [(a, b) for a, b in zip(pxd, c.tolist())
                     if a is not None and b == b and a and b]
            if len(pairs) < 30:
                skip_missing += 1
                bad.append((t, "대조 가능일 %d일" % len(pairs)))
                continue
            worst = max(abs(b / a - 1) for a, b in pairs[-250:])
            if worst > TOL:
                skip_mismatch += 1
                bad.append((t, "종가 불일치 최대 %.1f%%" % (100 * worst)))
                continue

            d["hd"] = [None if x != x else round(float(x), 2) for x in h.tolist()]
            d["ld"] = [None if x != x else round(float(x), 2) for x in l.tolist()]
            json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False,
                      separators=(",", ":"))
            ok += 1
        print("  %d/%d 처리" % (min(i + BATCH, len(tickers)), len(tickers)))
        time.sleep(1.0)

    print("\n백필 완료 — 기록 %d · 파일없음 %d · 결측 %d · 종가불일치 %d" %
          (ok, skip_nofile, skip_missing, skip_mismatch))
    if bad:
        print("건너뛴 종목(%d):" % len(bad))
        for t, why in bad[:40]:
            print("  %-8s %s" % (t, why))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
