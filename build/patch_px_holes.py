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


_GIT_CACHE = {}


def _git_json(rel):
    """직전 커밋(HEAD)의 그 파일. 없으면 None.

    ⚠ 새 원천이 아니다 — 같은 야후에서 어제 받아 **이 저장소가 이미 검증하고 커밋한** 값이다.
    """
    if rel in _GIT_CACHE:
        return _GIT_CACHE[rel]
    import subprocess
    try:
        out = subprocess.run(["git", "show", "HEAD:" + rel], cwd=ROOT,
                             capture_output=True, timeout=30)
        v = json.loads(out.stdout.decode("utf-8")) if out.returncode == 0 else None
    except Exception:
        v = None
    _GIT_CACHE[rel] = v
    return v


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

    # ── 🚨 2026-08-19 — 여기서 끝내면 안 된다는 것을 CI 가 알려 줬다 ──────────
    #   실측(런 32190459286): 배치가 30종을 받아 왔는데 **채운 칸이 0개**였다.
    #   야후가 그 순간 그 30종의 2026-08-11 행을 NaN 으로 준 것이다(같은 날 다른
    #   30종을 로컬에서 받아 보면 08-11 이 멀쩡히 있다 — 원천의 공백이 아니다).
    #   종전 코드는 그대로 포기하고 관문이 잡을 실패시켰다. **잡이 매일 죽는다.**
    #   → 두 겹을 더 둔다. 한 겹이 실패해도 다음이 받는다.
    need = [(t, dates[i]) for i in sorted(holes) for t in holes[i]
            if not (got.get(t) or {}).get(dates[i])]
    if need:
        # ① 개별 재시도 — 배치가 행을 빠뜨리는 것이 이 스크립트의 전제다(머리말).
        #    그렇다면 **한 종목씩** 받는 것이 그 전제의 자연스러운 다음 수다.
        print("  [2단] 배치가 못 준 %d칸 — 종목별로 다시 받는다" % len(need))
        for t in sorted({t for t, _d in need}):
            try:
                one = yf.download(_yf(t), start=start, end=end, auto_adjust=True,
                                  progress=False, threads=False)
            except Exception:
                continue
            if one is None or not len(one):
                continue
            if hasattr(one.columns, "levels"):
                one.columns = one.columns.get_level_values(0)
            for ts, row in one.iterrows():
                c = row.get("Close")
                if c is None or c != c:
                    continue
                got.setdefault(t, {})[str(ts)[:10]] = (
                    float(c),
                    float(row.get("High")) if row.get("High") == row.get("High") else None,
                    float(row.get("Low")) if row.get("Low") == row.get("Low") else None,
                    float(row.get("Volume")) if row.get("Volume") == row.get("Volume") else None)
        need = [(t, d) for t, d in need if not (got.get(t) or {}).get(d)]

    from_git = 0
    if need:
        # ② 그래도 없으면 **우리가 이미 갖고 있던 값**으로 채운다.
        #    ⚠ 두 번째 가격 원천이 아니다 — 같은 야후에서 어제 받아 커밋해 둔 같은 칸이다.
        #    ⚠ 다만 auto_adjust 라 배당이 생기면 과거 종가가 소급 조정된다. 이렇게 채운
        #      칸은 그만큼(보통 0.1~0.5%) 어제 기준으로 남는다. **구멍보다는 낫다** —
        #      구멍은 그날 유니버스를 조용히 줄여 전 전략이 좁아진 후보에서 고르게 한다
        #      (2026-07-31 에 실제로 78% 유니버스에서 성과가 나왔다).
        #    그래서 이 경로로 채운 수를 반드시 찍는다.
        print("  [3단] 야후가 끝내 안 준 %d칸 — 직전 커밋(HEAD)의 같은 칸으로 채운다" % len(need))
        gdates = _git_json("data/stocks.json")
        gidx = {d: k for k, d in enumerate((gdates or {}).get("pxd_dates") or [])}
        for t, d in need:
            k = gidx.get(d)
            if k is None:
                continue
            gj = _git_json("data/sd/%s.json" % t)
            if not gj:
                continue
            gp = gj.get("pxd") or []
            if k >= len(gp) or gp[k] is None:
                continue
            got.setdefault(t, {})[d] = (
                float(gp[k]),
                (gj.get("hd") or [None] * (k + 1))[k] if k < len(gj.get("hd") or []) else None,
                (gj.get("ld") or [None] * (k + 1))[k] if k < len(gj.get("ld") or []) else None,
                (gj.get("vd") or [None] * (k + 1))[k] if k < len(gj.get("vd") or []) else None)
            from_git += 1
        print("       → %d칸 복구" % from_git)

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
    print("→ 파일 %d개 수정 · 채운 칸 %s%s"
          % (touched, filled, (" (그중 %d칸은 직전 커밋에서)" % from_git) if from_git else ""))
    left = find_holes(dates, files)
    print("   남은 구멍: %s" % ({dates[i]: len(v) for i, v in left.items()} or "없음 ✅"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
