# -*- coding: utf-8 -*-
"""저장 정밀도보다 화면 정밀도가 높은 자리를 찾는다.

🚨 2026-08-10 MSFT 사고에서 나왔다. home_summary 가 종목 수익률을 round(v,1) 로 저장하는데
  화면은 toFixed(2) 로 그려서, +0.026% 가 '0.00%' 로 나갔다. 518종 **전부** 둘째 자리가
  0 이었는데 아무도 못 봤다 — 없는 자리는 0 으로 보이지 빈칸으로 보이지 않기 때문이다.

재는 법 — 추측하지 않고 **실제 저장된 값**을 센다. 어떤 필드의 값들이 소수 N자리를
  넘지 않으면 그 필드의 정밀도는 N이다. 그것을 화면의 toFixed(M) 과 맞춰 본다.

⚠ 정밀도가 낮다는 것 자체는 잘못이 아니다. 잘못은 **낮게 저장하고 높게 그리는 것**이다.
  그러면 화면이 없는 정밀도를 있는 것처럼 말한다 — 마지막 자리가 항상 0 이라는 사실은
  화면만 봐서는 알 수 없다.
"""
import io
import json
import os
import re
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
MIN_N = 40          # 이보다 표본이 적은 필드는 판단하지 않는다(우연히 다 0일 수 있다)


def dec_of(x):
    """부동소수를 짧게 적었을 때의 소수 자릿수. 0.1+0.2 같은 잡음에 안 속게 repr 로 센다."""
    s = repr(float(x))
    if "e" in s or "E" in s:
        return 9
    return len(s.split(".")[1].rstrip("0")) if "." in s else 0


def walk(o, path, acc):
    if isinstance(o, dict):
        for k, v in o.items():
            walk(v, path + "." + str(k), acc)
    elif isinstance(o, list):
        for v in o:
            walk(v, path + "[]", acc)
    elif isinstance(o, bool):
        pass
    elif isinstance(o, (int, float)):
        if o == o and abs(o) != float("inf"):
            acc[path].append(dec_of(o))


def main():
    files = sorted(f for f in os.listdir(DATA) if f.endswith(".json") and not f.startswith("_"))
    rows = []
    for f in files:
        p = os.path.join(DATA, f)
        if os.path.getsize(p) > 12_000_000:
            continue
        try:
            j = json.load(io.open(p, encoding="utf-8"))
        except Exception:
            continue
        acc = defaultdict(list)
        walk(j, "", acc)
        for path, ds in acc.items():
            if len(ds) < MIN_N:
                continue
            mx = max(ds)
            # 정수만 나오는 필드는 대상이 아니다(개수·연도 등)
            if mx == 0:
                continue
            rows.append((f, path, mx, len(ds),
                         sum(1 for d in ds if d == mx) / float(len(ds))))

    # 화면 쪽 — 어떤 파일이 toFixed(M) 을 몇 번 쓰나
    tf = defaultdict(lambda: defaultdict(int))
    for h in sorted(x for x in os.listdir(ROOT) if x.endswith(".html")):
        s = io.open(os.path.join(ROOT, h), encoding="utf-8").read()
        for m in re.finditer(r"toFixed\(\s*(\d)\s*\)", s):
            tf[h][int(m.group(1))] += 1

    print("── ① 저장 정밀도가 낮은 필드(소수 1자리 이하로만 저장됨) ──")
    print("   화면이 2자리로 그리면 마지막 자리가 항상 0 이 된다.")
    print("%-26s %-40s %5s %7s" % ("파일", "필드", "자릿수", "표본"))
    print("-" * 84)
    n1 = 0
    for f, path, mx, n, _share in sorted(rows, key=lambda r: (r[2], -r[3])):
        if mx <= 1:
            n1 += 1
            print("%-26s %-40s %5d %7d" % (f[:24], path[:38], mx, n))
    if not n1:
        print("   (없음)")

    print()
    print("── ② 화면의 toFixed 분포 ──")
    for h in sorted(tf):
        d = tf[h]
        print("   %-18s %s" % (h, " · ".join("toFixed(%d) x%d" % (k, d[k]) for k in sorted(d))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
