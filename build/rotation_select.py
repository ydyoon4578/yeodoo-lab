# -*- coding: utf-8 -*-
"""오늘(KST)의 로테이션 10선 id/name 출력 — rotation.html의 pick()과 **동일 알고리즘**
(FNV1a 시드 + LCG 셔플로 풀 전체를 섞어 앞에서 10개, 날짜는 KST 고정).
⚠ rotation.html의 pick()/n을 바꾸면 이 파일도 반드시 같이 바꿀 것 — 어긋나면 화면의 10선과 갱신 대상이 달라진다.
   (build/validate_site.py 가 n·Math.imul·KST 보정·쿼터 부재를 양쪽에서 대조해 CI 에서 강제한다.)
헤드리스 Claude 일일 갱신 작업이 '오늘 표시되는 10개'만 최근동향을 갱신하도록 사용.

🚨 절차 순서 — **신규 카드를 먼저 넣고 그 다음에 뽑는다.** (2026-08-11 에 고쳤다)
   pick() 은 풀 전체를 셔플하므로 카드를 하나만 더해도 **10선이 통째로 달라진다.**
   종전 절차는 ①뽑고 ②갱신하고 ③신규 추가 였는데, ③이 ①을 무효로 만들었다.
   실측(2026-08-07 갱신분): 그날 화면에 뜬 10선 중 **8종이 갱신 대상이 아니었다.**
   갱신을 하고도 방문자는 갱신 안 된 카드를 봤다는 뜻이다.
   → 올바른 순서:
      ① 신규 전략 카드를 data/rotation_pool.json 에 **먼저** 추가한다
      ② 이 스크립트를 돌려 10선 + 방치 3종을 뽑는다
      ③ 뽑힌 13종의 recent/recent_at 을 갱신하고 generated 를 오늘로 올린다
      ④ 이 스크립트를 한 번 더 돌려 10선의 recent_at 이 전부 오늘인지 확인한다
   ⚠ 신규 카드를 안 넣는 날은 순서 문제가 없다(풀 길이가 안 변한다).
"""
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
    # 🚨 위 독스트링 ④ 를 사람이 기억하지 않게 기계가 말한다(2026-08-11).
    #   갱신을 끝낸 뒤 다시 돌려서 FRESH_OK 가 뜨면, 방문자가 오늘 보는 10선이 전부 오늘 것이다.
    #   NOTFRESH 가 뜨는 경우는 둘 중 하나다 — 아직 갱신 전이거나, 신규 카드를 갱신 **뒤에**
    #   넣어 10선이 어긋났거나. 후자가 2026-08-07 에 실제로 났던 사고다(그날 화면 10선 중 8종).
    notfresh = [s["id"] for s in sel if (s.get("recent_at") or "") != today]
    # ⚠ generated 도 같이 본다. 카드를 다 갱신하고 이것만 안 올리면 카드는 최신인데
    #   화면 통계줄의 '갱신'과 3영업일 정체 경고가 옛 날짜를 말한다 — 같은 화면이
    #   두 가지를 말하게 된다. recent_at 만 검사하면 그 어긋남이 안 잡힌다.
    if (d.get("generated") or "") != today:
        notfresh.append("generated=" + (d.get("generated") or "없음"))
    print("FRESH_OK" if not notfresh else "NOTFRESH\t" + " ".join(notfresh))


if __name__ == "__main__":
    main()
