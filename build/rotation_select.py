# -*- coding: utf-8 -*-
"""오늘(KST)의 로테이션 10선 id/name 출력 — rotation.html의 pick()과 **동일 알고리즘**
(FNV1a 시드 + LCG 셔플로 풀 전체를 섞어 앞에서 10개, 날짜는 KST 고정).
⚠ rotation.html의 pick()/n을 바꾸면 이 파일도 반드시 같이 바꿀 것 — 어긋나면 화면의 10선과 갱신 대상이 달라진다.
   (build/validate_site.py 가 n·Math.imul·KST 보정·쿼터 부재를 양쪽에서 대조해 CI 에서 강제한다.)
헤드리스 Claude 일일 갱신 작업이 '오늘 표시되는 10개'만 최근동향을 갱신하도록 사용."""
import json, io, os, sys, datetime
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
HERE = os.path.dirname(os.path.abspath(__file__))
POOL = os.path.join(HERE, "..", "data", "rotation_pool.json")
# ── 카테고리 쿼터 없음(2026-08-06 사용자 결정) ──────────────────────────
# 종전에는 A·B·C·D·E 에 같은 쿼터를 줬다. 그러면 **카테고리는 균형이지만 전략은 안 균형**이다 —
# 풀 크기가 달라서 B(8종)는 4일마다 돌아오고 E(42종)는 21일마다 돌아왔다.
# 쿼터를 없애면 모든 전략이 같은 확률로 뽑혀 재등장 주기가 풀 전체에 걸쳐 균일해진다
# (98종·하루 10선 → 약 9.8일). 카테고리 비중은 풀 구성을 그대로 반영한다.
# ⚠ 카테고리는 이제 화면 분류·색상에만 쓴다. 선정에는 관여하지 않는다.

def pick(arr, n, seed_str):
    """날짜 시드로 풀 전체를 섞어 앞에서 n개. rotation.html의 pick()과 한 글자도 다르면 안 된다."""
    seed = 2166136261
    for ch in seed_str:
        seed ^= ord(ch); seed = (seed * 16777619) & 0xffffffff

    def rnd():
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) & 0xffffffff
        return seed / 4294967296

    a = list(arr)
    for i in range(len(a) - 1, 0, -1):
        j = int(rnd() * (i + 1)); a[i], a[j] = a[j], a[i]
    return a[:n]


def main():
    d = json.load(io.open(POOL, encoding="utf-8"))
    S = d["strategies"]
    KST = datetime.timezone(datetime.timedelta(hours=9))
    today = datetime.datetime.now(KST).strftime("%Y-%m-%d")   # rotation.html의 today()와 동일하게 KST 고정
    sel = pick(S, 10, today)
    print(f"KST_DATE={today}")
    for s in sel:
        print(f'{s["id"]}\t{s["name"]}')
    # 쿼터가 없으므로 모든 전략의 재등장 주기가 같다(98종·10선 → 약 9.8일).
    # 그래도 표본이 작아 며칠 안 뽑히는 카드가 생긴다. 오늘의 10선에 없으면서 recent_at이 가장 오래된(또는 없는) 3종을 추가 갱신 대상으로 지정해 방치 카드를 없앤다.
    shown = {s["id"] for s in sel}
    rest = [s for s in S if s["id"] not in shown]
    rest.sort(key=lambda s: (s.get("recent_at") or "0000-00-00", s["id"]))
    print("STALE3")
    for s in rest[:3]:
        print(f'{s["id"]}\t{s["name"]}\t(최근갱신 {s.get("recent_at") or "없음"})')


if __name__ == "__main__":
    main()
