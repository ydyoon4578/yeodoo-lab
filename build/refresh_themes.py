# -*- coding: utf-8 -*-
"""테마 채점기 — 손으로 쓴 명단(build/themes_defs.py)이 무엇을 설명하는지 잰다.

돌리는 것: 최근 N거래일 로그수익 → 등가중 시장 차감 → **GICS 네 단 전부** 횡단면 차감
→ 군내 평균 쌍상관 → 같은 크기 무작위 표본 대비 z.

🚨 통제는 반드시 **GICS 네 단 전부**(산업그룹 grp + 서브산업 sub)여야 한다.
  화면이 쓰는 것은 두 단(섹터·산업그룹)뿐이지만, 채점을 두 단으로만 하면 **버리기로 한
  3·4차의 값이 테마의 값으로 둔갑한다.** 실측(2023-07-31~2026-08-04, 505종):

      우주·방산   두 단 통제 +0.250 (z +13.4)  →  네 단 통제 −0.007 (z −0.4)
      사이버보안  두 단 통제 +0.299 (z  +4.7)  →  네 단 통제 −0.076 (z −1.5)

  부호가 뒤집힌다. 라벨로 안 쓰는 것과 통제로 안 쓰는 것은 다른 일이다.

🚨 이 파일은 명단을 **읽기만** 한다. 명단은 build/themes_defs.py 에 있고 사람이 쓴다.
  기계가 명단을 만들면 성적을 보고 자라는 것을 막을 방법이 없다.

⚠ 이 성적은 화면 표시용이다. 명단을 2026-08-05 에 결과를 알고 썼으므로 정의상
  미래참조이며 **전략 입력으로 쓸 수 없다.** 같은 명단을 과거 창에 대면 통과한 셋이
  6~9년 전에는 전부 탈락한다(AI −1.1 · 전력 −1.5 · 크립토는 종목이 1종이라 측정불가) —
  지금 통과했다는 것은 '최근 3년 동안 그렇게 움직였다' 이상을 뜻하지 않는다.
"""
import glob
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "themes.json")

sys.path.insert(0, HERE)
from themes_defs import CANDIDATES                      # noqa: E402  명단은 여기서만 온다

WIN = 756            # 최근 3년(거래일). 창을 바꾸면 성적이 바뀐다 — 화면에 창을 함께 낸다.
NSIM = 2000          # 무작위 표본 횟수
SEED = 20260805      # 고정. 매 실행 같은 값이 나와야 한다(재현 가능해야 채점이다).
MIN_N = 3            # 이보다 적으면 널 분포가 벌어져 z 를 읽을 수 없다 → 측정불가
MAX_SUB_NA = 0.5     # 명단 안에서 GICS 서브산업 결측이 이 비율을 넘으면 통제가 샌다 → 측정불가


def _z_crit(k):
    """본페로니 양측 문턱. 분모는 **시험한 후보 전부**다(통과한 것만 세면 분모가 숨는다)."""
    from math import erf, sqrt
    a = 0.05 / (2.0 * k)
    lo, hi = 0.0, 10.0
    for _ in range(200):                      # 표준정규 역함수 — scipy 없이 이분법
        mid = (lo + hi) / 2
        if 0.5 * (1 - erf(mid / sqrt(2))) > a:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 3)


def main():
    stocks = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = stocks["pxd_dates"]
    mem = (json.load(io.open(os.path.join(DATA, "members.json"), encoding="utf-8")) or {}).get("members") or {}

    px = {}
    for p in glob.glob(os.path.join(DATA, "sd", "*.json")):
        t = os.path.basename(p)[:-5]
        v = json.load(io.open(p, encoding="utf-8")).get("pxd")
        if v and len(v) == len(dates):
            px[t] = np.array([np.nan if (x is None or x <= 0) else x for x in v], float)
    if len(px) < 200 or len(dates) < WIN + 5:
        raise SystemExit("가격 패널이 모자란다(%d종 · %d일) — 채점 중단" % (len(px), len(dates)))

    i0, i1 = len(dates) - WIN, len(dates)
    tk = sorted(t for t in px if not np.isnan(px[t][i0:i1]).any())
    P = np.array([px[t][i0:i1] for t in tk])
    R = np.diff(np.log(P), axis=1)
    R = R - R.mean(0)                                            # 등가중 시장 제거
    for key in ("grp", "sub"):                                   # GICS 네 단 전부
        lab = np.array([(mem.get(t) or {}).get(key) or "?" for t in tk])
        for g in np.unique(lab):
            m = lab == g
            if m.sum() > 1:
                R[m] = R[m] - R[m].mean(0)
    Z = (R - R.mean(1, keepdims=True)) / (R.std(1, keepdims=True) + 1e-12)
    C = Z @ Z.T / R.shape[1]
    pos = {t: i for i, t in enumerate(tk)}
    rng = np.random.default_rng(SEED)

    def score(ix):
        if len(ix) < 2:
            return None
        s = C[np.ix_(ix, ix)]
        n = len(ix)
        return float((s.sum() - np.trace(s)) / (n * (n - 1)))

    zc = _z_crit(len(CANDIDATES))
    defs, lab_rows = [], []
    for key, c in CANDIDATES.items():
        mems = [t for t, _ in c["members"]]
        have = [t for t in mems if t in pos]
        # 🚨 실패 시나리오 (나) 방어 — 명단 안에서 서브산업이 많이 비면 통제가 헐거워지고
        #   z 가 저절로 오른다. 신규상장이 늘수록 심해진다(members.json 은 503/518종만 가진다).
        na = sum(1 for t in have if not (mem.get(t) or {}).get("sub"))
        na_r = (na / len(have)) if have else 1.0
        v = score([pos[t] for t in have])
        row = {"key": key, "n_def": len(mems), "n_used": len(have),
               "sub_na": round(na_r, 3)}
        if len(have) < MIN_N or v is None:
            row.update(verdict="측정불가", why="유니버스 안 종목이 %d종 — %d종 미만이면 "
                                              "널 분포가 벌어져 z 를 읽을 수 없다" % (len(have), MIN_N))
        elif na_r > MAX_SUB_NA:
            row.update(verdict="측정불가", why="명단의 %d%%가 GICS 서브산업 결측 — 통제가 "
                                              "새서 z 가 저절로 오른다" % round(na_r * 100))
        else:
            null = np.array([x for x in (score(list(rng.choice(len(tk), len(have), replace=False)))
                                         for _ in range(NSIM)) if x is not None])
            z = float((v - null.mean()) / (null.std() + 1e-12))
            row.update(corr=round(v, 4), null_mean=round(float(null.mean()), 4),
                       null_sd=round(float(null.std()), 4), z=round(z, 2),
                       verdict="설명력 확인" if z >= zc else "구별 불가",
                       why=("무작위 같은 크기 표본보다 군내 상관이 뚜렷하게 높다"
                            if z >= zc else "무작위 표본과 구별되지 않는다"))
        lab_rows.append(row)
        defs.append({"key": key, "label": c["label"], "why": c["why"],
                     "members": [{"t": t, "added_on": d} for t, d in c["members"]]})

    ok = [r for r in lab_rows if r["verdict"] == "설명력 확인"]
    out = {
        "as_of": stocks.get("as_of"),
        "note": "손으로 쓴 테마 명단(build/themes_defs.py)과 그 명단이 무엇을 설명하는지 잰 성적. "
                "채점: 최근 %d거래일 로그수익에서 등가중 시장과 GICS 네 단(산업그룹·서브산업)을 "
                "모두 빼고 남은 잔차의 군내 평균 쌍상관을, 같은 크기 무작위 표본 %d회와 견준 z. "
                "🚨 명단은 2026-08-05 에 결과를 알고 쓴 것이라 정의상 미래참조다 — "
                "화면 표시용이며 전략 입력으로 쓰지 않는다." % (WIN, NSIM),
        "window": {"days": WIN, "start": dates[i0], "end": dates[-1], "n_stocks": len(tk)},
        "control": "등가중 시장 + GICS 산업그룹 + GICS 서브산업",
        "control_why": "화면은 두 단만 쓰지만 채점은 네 단 전부로 한다. 두 단만 통제하면 "
                       "버리기로 한 3·4차의 값이 테마의 값으로 둔갑한다(우주·방산 z +13.4 → −0.4).",
        "n_candidates": len(CANDIDATES), "z_crit": zc,
        "z_crit_why": "본페로니 양측 0.05/%d — 분모는 통과한 것이 아니라 **시험한 후보 전부**다" % len(CANDIDATES),
        "n_pass": len(ok),
        "defs": defs, "lab": lab_rows,
    }
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("테마 채점 — 후보 %d · 설명력 확인 %d · 문턱 z ≥ %.3f" % (len(CANDIDATES), len(ok), zc))
    print("  창 %s ~ %s (%d거래일 · %d종)" % (dates[i0], dates[-1], WIN, len(tk)))
    for r in sorted(lab_rows, key=lambda x: -(x.get("z") or -99)):
        print("   %-9s n %2d/%2d  %s  %s" % (
            r["key"], r["n_used"], r["n_def"],
            ("상관 %+.3f · z %+6.2f" % (r["corr"], r["z"])) if "z" in r else "        —        ",
            r["verdict"]))
    print("→", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
