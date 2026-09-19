# -*- coding: utf-8 -*-
"""build/fetch_ff.py — Fama-French 일별 팩터를 data/ff_daily.json 으로 만든다.

🚨 이 랩에 없던 자료다. E60(자산가격결정 트리) 카드가 «오늘 data/ 에서 3팩터 계열
   파일을 찾지 못했다» 고 적었고, 그래서 특이변동성(IdioVol)을 정의대로 못 만들어
   원문 36개 교차단면 중 10개만 만들 수 있다고 했다. 그 구멍을 메운다.

무엇이 들어오나 — Kenneth French 자료실(공개)
  · 5팩터 일별 : Mkt-RF · SMB · HML · RMW · CMA · RF
  · 모멘텀 일별 : Mom

쓰임 셋
  ① 국면 정의 — 가치/성장 · 대형/소형 · 추세 지속 여부를 **수로** 가른다
  ② 특이변동성(IdioVol) — 3팩터 회귀 잔차. E60 · 여러 카드가 요구한다
  ③ 귀속 — 우량성장 30 의 2016 손실 분해가 이 계열로 된 것이다(팩터 기여)

⚠ 이 계열은 **미국 전 종목** 기준이다. 이 랩 유니버스(대형 518종)와 구성이 다르다.
  국면을 «가르는» 데는 쓰되, 성과를 «설명»할 때는 그 차이를 적는다.

  python build/fetch_ff.py            내려받아 data/ff_daily.json 을 만든다
  python build/fetch_ff.py --check    지금 파일의 신선도·결측만 본다
"""
from __future__ import annotations
import io, json, os, sys, zipfile

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "ff_daily.json")
SRC = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FILES = {"F-F_Research_Data_5_Factors_2x3_daily_CSV.zip": ("mkt_rf", "smb", "hml", "rmw", "cma", "rf"),
         "F-F_Momentum_Factor_daily_CSV.zip": ("mom",)}


def parse(raw, cols):
    """머리말을 건너뛰고 «YYYYMMDD,수,수,…» 줄만 읽는다."""
    out = {}
    for ln in raw.replace("\r", "").split("\n"):
        p = [x.strip() for x in ln.split(",")]
        if len(p) < 2 or not (len(p[0]) == 8 and p[0].isdigit()):
            continue
        try:
            v = [float(x) for x in p[1:1 + len(cols)]]
        except ValueError:
            continue
        if len(v) != len(cols):
            continue
        d = "%s-%s-%s" % (p[0][:4], p[0][4:6], p[0][6:])
        out.setdefault(d, {}).update(dict(zip(cols, v)))
    return out


def main():
    if "--check" in sys.argv:
        if not os.path.exists(OUT):
            print("❌ %s 없음 — python build/fetch_ff.py 로 만든다" % OUT); return 1
        d = json.load(io.open(OUT, encoding="utf-8"))
        print("ff_daily.json — %s ~ %s · %d일 · 팩터 %s"
              % (d["start"], d["end"], d["n"], " ".join(d["factors"])))
        return 0

    import urllib.request
    rows = {}
    for fn, cols in FILES.items():
        cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_ffcache", fn)
        cache = os.path.abspath(cache)
        if os.path.exists(cache):
            blob = io.open(cache, "rb").read()
        else:
            req = urllib.request.Request(SRC + fn, headers={"User-Agent": "Mozilla/5.0"})
            blob = urllib.request.urlopen(req, timeout=120).read()
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            io.open(cache, "wb").write(blob)
        z = zipfile.ZipFile(io.BytesIO(blob))
        raw = z.read(z.namelist()[0]).decode("latin-1")
        got = parse(raw, cols)
        print("  %-52s %6d일 · %s" % (fn.replace("_CSV.zip", ""), len(got), " ".join(cols)))
        for d, v in got.items():
            rows.setdefault(d, {}).update(v)

    # 여섯 팩터가 모두 있는 날만 남긴다 — 반쪽 줄을 두면 회귀가 조용히 짧아진다
    need = ("mkt_rf", "smb", "hml", "rmw", "cma", "rf", "mom")
    full = {d: v for d, v in rows.items() if all(k in v for k in need)}
    drop = len(rows) - len(full)
    dates = sorted(full)
    doc = {"note": "Kenneth French 자료실 일별 팩터(%). 미국 전 종목 기준 — 이 랩 유니버스"
                   "(대형 518종)와 구성이 다르다. 국면을 가르는 데 쓰고, 성과 설명에 쓸 때는"
                   " 그 차이를 함께 적는다.",
           "source": SRC, "files": list(FILES), "unit": "percent",
           "factors": list(need), "start": dates[0], "end": dates[-1], "n": len(dates),
           "dropped_partial_days": drop,
           "dates": dates,
           "series": {k: [full[d][k] for d in dates] for k in need}}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False) + "\n")
    print("\n→ %s\n   %s ~ %s · %d일 · 반쪽 줄 제외 %d일 · %.1f MB"
          % (OUT, dates[0], dates[-1], len(dates), drop, os.path.getsize(OUT) / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
