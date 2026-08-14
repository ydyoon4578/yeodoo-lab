# -*- coding: utf-8 -*-
"""가격 격자의 구멍만 메운다 — data/sd/*.json 의 pxd 중 **None 인 칸만**.

왜 필요한가(2026-08-14 실측).
  data/stocks.json 의 거래일 격자 4429일 가운데 세 날이 뚫려 있었다:
      2026-07-21  결측 192종 / 518    2026-07-22  결측 192종    2026-07-31  결측 113종
  17.6년 격자에서 이 셋뿐이고 전후 거래일은 멀쩡하다. yfinance 를 개별로 받아 보면
  그 날짜 봉이 **있다** — 원천의 공백이 아니라 우리 수집이 빠뜨린 것이다.
  refresh_stocks.py 는 period="max" 로 매번 전체를 받는데도 3주째 구멍이 남았다.
  120종씩 묶어 받는 배치 다운로드가 조용히 행을 빠뜨리는 것으로 보인다(재현되지 않는
  종류라 재실행으로 확실히 낫는다는 보장이 없다).

🚨 왜 그냥 두면 안 되나. **2026-07-31 은 월말이자 주간 리밸런스 날이다.** 그날 이 랩의
  전 횡단면 전략은 518종이 아니라 405종에서 골랐다. 후보 커버리지 게이트(XSEC_MIN_POOL=30)는
  한참 위라 아무 경고도 안 났다 — 성과가 조용히 78% 유니버스에서 나왔다.

무엇을 하나 / 안 하나.
  · **None 인 칸만** 채운다. 이미 값이 있는 칸은 절대 덮지 않는다 — 덮기 시작하면
    이 스크립트가 두 번째 가격 원천이 되고, 그건 이 저장소가 되풀이 금지해 온 것이다.
  · 상장 전 구간의 None 은 건드리지 않는다(그건 결측이 아니라 '아직 없음'이다).
    첫 유효값 이후의 None 만 대상으로 한다.
  · 고가·저가(hd/ld)·거래량(vd)도 같은 규칙으로 채운다 — 종가만 채우면 그날
    고저가 기반 규칙(x-52wh·x-clv·x-hlspread)이 여전히 그 종목을 못 본다.

    python build/patch_px_holes.py            # 실제로 채운다
    python build/patch_px_holes.py --dry-run  # 무엇을 채울지만 본다
"""
import io
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SD = os.path.join(DATA, "sd")

# 한 날짜에 이만큼 넘게 비면 '수집 실패' 로 본다. 개별 종목의 거래정지·상장폐지는
# 이 수를 넘지 않는다(실측: 정상일의 상장 후 결측은 0~1종).
HOLE_MIN = 20


def _yf(t):
    return t.replace(".", "-")


def find_holes(dates, sd_files):
    """(날짜, 결측 티커들) — 상장 후 생긴 구멍만."""
    n = len(dates)
    miss = {}
    for fn in sd_files:
        t = fn[:-5]
        try:
            pxd = (json.load(io.open(os.path.join(SD, fn), encoding="utf-8")) or {}).get("pxd") or []
        except Exception:
            continue
        seen = False
        for i in range(min(n, len(pxd))):
            if pxd[i] is not None:
                seen = True
            elif seen:
                miss.setdefault(i, []).append(t)
    return {i: ts for i, ts in miss.items() if len(ts) >= HOLE_MIN}


def main():
    dry = "--dry-run" in sys.argv
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = st["pxd_dates"]
    files = sorted(f for f in os.listdir(SD) if f.endswith(".json"))
    holes = find_holes(dates, files)
    if not holes:
        print("구멍 없음 — 채울 것이 없다")
        return 0
    tickers = sorted({t for ts in holes.values() for t in ts})
    print("구멍 %d일 · 대상 %d종" % (len(holes), len(tickers)))
    for i in sorted(holes):
        print("   %s  결측 %d종" % (dates[i], len(holes[i])))
    if dry:
        print("(--dry-run — 파일을 건드리지 않는다)")
        return 0

    import yfinance as yf
    lo, hi = min(holes), max(holes)
    start, end = dates[max(0, lo - 3)], dates[min(len(dates) - 1, hi + 3)]
    print("내려받기 %s ~ %s · %d종 (개별 배치 30종씩 — 큰 배치가 행을 빠뜨린다)"
          % (start, end, len(tickers)))
    got = {}
    for k in range(0, len(tickers), 30):
        ch = tickers[k:k + 30]
        try:
            df = yf.download([_yf(t) for t in ch], start=start, end=end,
                             auto_adjust=True, progress=False, group_by="ticker", threads=True)
        except Exception as e:
            print("  [yf] 배치 실패 %s" % str(e)[:60])
            continue
        for t in ch:
            y = _yf(t)
            try:
                sub = df[y] if y in df.columns.get_level_values(0) else None
            except Exception:
                sub = None
            if sub is None:
                continue
            for ts, row in sub.iterrows():
                d = str(ts)[:10]
                c = row.get("Close")
                if c is None or c != c:
                    continue
                got.setdefault(t, {})[d] = (
                    float(c),
                    float(row.get("High")) if row.get("High") == row.get("High") else None,
                    float(row.get("Low")) if row.get("Low") == row.get("Low") else None,
                    float(row.get("Volume")) if row.get("Volume") == row.get("Volume") else None,
                )
        print("  … %d/%d" % (min(k + 30, len(tickers)), len(tickers)))

    filled = {"pxd": 0, "hd": 0, "ld": 0, "vd": 0}
    touched = 0
    for fn in files:
        t = fn[:-5]
        if t not in got:
            continue
        p = os.path.join(SD, fn)
        j = json.load(io.open(p, encoding="utf-8"))
        ch = False
        for i in sorted(holes):
            if t not in holes[i]:
                continue
            v = got[t].get(dates[i])
            if not v:
                continue
            for key, val in (("pxd", v[0]), ("hd", v[1]), ("ld", v[2]), ("vd", v[3])):
                arr = j.get(key)
                # 🚨 None 인 칸만. 값이 있으면 절대 덮지 않는다.
                if isinstance(arr, list) and i < len(arr) and arr[i] is None and val is not None:
                    arr[i] = round(val, 4) if key != "vd" else val
                    filled[key] += 1
                    ch = True
        if ch:
            json.dump(j, io.open(p, "w", encoding="utf-8"), ensure_ascii=False,
                      separators=(",", ":"))
            touched += 1
    print("→ 파일 %d개 수정 · 채운 칸 %s" % (touched, filled))
    left = find_holes(dates, files)
    print("   남은 구멍: %s" % ({dates[i]: len(v) for i, v in left.items()} or "없음 ✅"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
