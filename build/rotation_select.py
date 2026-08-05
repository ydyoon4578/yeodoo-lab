# -*- coding: utf-8 -*-
"""오늘(KST)의 로테이션 20선 id/name 출력 — rotation.html의 pick()과 **동일 알고리즘**
(FNV1a 시드 + LCG 셔플, 카테고리 균형 A4·B4·C4·D4·E4, 날짜는 KST 고정).
⚠ rotation.html의 pick()/QUOTA를 바꾸면 이 파일도 반드시 같이 바꿀 것 — 어긋나면 화면의 20선과 갱신 대상이 달라진다.
   (build/validate_site.py 가 QUOTA·CATORD·Math.imul·KST 보정을 양쪽에서 대조해 CI 에서 강제한다.)
헤드리스 Claude 일일 갱신 작업이 '오늘 표시되는 20개'만 최근동향을 갱신하도록 사용."""
import json, io, os, sys, datetime
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
HERE = os.path.dirname(os.path.abspath(__file__))
POOL = os.path.join(HERE, "..", "data", "rotation_pool.json")
CATORD = ["A", "B", "C", "D", "E"]
# 2026-08-06 10선 → 20선(사용자 결정). 쿼터를 그대로 두 배로 올려 카테고리 균형은 유지한다.
# 풀 98종 기준 재등장 주기 약 9.8일 → 4.9일.
# ⚠ 카테고리별 풀 크기가 달라 주기는 여전히 균일하지 않다(B 8종 → 2일 · E 42종 → 10.5일).
#   균일하게 하려면 쿼터를 풀 크기 비례(A4·B2·C3·D3·E8)로 바꿔야 하는데, 그건 화면이
#   내세우는 "카테고리 균형"의 정의를 바꾸는 별도 결정이라 여기서는 하지 않았다.
QUOTA = {"A": 4, "B": 4, "C": 4, "D": 4, "E": 4}


def pick(arr, n, seed_str):
    seed = 2166136261
    for ch in seed_str:
        seed ^= ord(ch); seed = (seed * 16777619) & 0xffffffff

    def rnd():
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) & 0xffffffff
        return seed / 4294967296

    def sh(a):
        a = list(a)
        for i in range(len(a) - 1, 0, -1):
            j = int(rnd() * (i + 1)); a[i], a[j] = a[j], a[i]
        return a

    by = {}
    for s in arr:
        by.setdefault(s.get("cat"), []).append(s)
    out, rest = [], []
    for c in CATORD:
        p = sh(by.get(c, [])); q = QUOTA.get(c, 0)
        out += p[:q]; rest += p[q:]
    if len(out) < n:
        out += sh(rest)[:n - len(out)]
    return out[:n]


def main():
    d = json.load(io.open(POOL, encoding="utf-8"))
    S = d["strategies"]
    KST = datetime.timezone(datetime.timedelta(hours=9))
    today = datetime.datetime.now(KST).strftime("%Y-%m-%d")   # rotation.html의 today()와 동일하게 KST 고정
    sel = pick(S, 20, today)
    print(f"KST_DATE={today}")
    for s in sel:
        print(f'{s["id"]}\t{s["name"]}')
    # 쿼터가 균형이라 카테고리별 재등장 주기가 다르다(쿼터 균형이라 카테고리별로 다름).
    # 오늘의 20선에 없으면서 recent_at이 가장 오래된(또는 없는) 3종을 추가 갱신 대상으로 지정해 방치 카드를 없앤다.
    shown = {s["id"] for s in sel}
    rest = [s for s in S if s["id"] not in shown]
    rest.sort(key=lambda s: (s.get("recent_at") or "0000-00-00", s["id"]))
    print("STALE3")
    for s in rest[:3]:
        print(f'{s["id"]}\t{s["name"]}\t(최근갱신 {s.get("recent_at") or "없음"})')


if __name__ == "__main__":
    main()
