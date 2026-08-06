# -*- coding: utf-8 -*-
"""갱신 피드(data/updates.json) 기록 — 날짜 + 시각(KST).

지금까지 커밋마다 인라인 파이썬으로 이벤트를 밀어 넣었다. 매번 다시 쓰면 형식이 갈리므로
여기 한 곳으로 모은다. 시각을 붙이는 이유는 하루에 여러 번 갱신될 때 순서가 보이지 않아서다.

  python build/log_update.py <target> "<제목>"        # 지금 시각(KST)으로 기록
  python build/log_update.py <target> "<제목>" 14:35  # 시각 지정

target: 아래 TARGETS 참조. **홈의 UPD 맵(index.html)과 반드시 같은 집합**이어야 한다 —
어긋나면 그 이벤트가 홈에서 '기타'로 떨어지고, validate_site.py가 실패시킨다.
"""
from __future__ import annotations
import io, json, os, re, sys
from datetime import datetime, timedelta, timezone
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

KST = timezone(timedelta(hours=9))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = os.path.join(ROOT, "data", "updates.json")
# 도구가 늘면 여기에 먼저 넣어야 기록할 수 있다. 안 넣으면 log_update가 거부하고,
# 그러면 그 화면의 변경은 갱신 피드에 영원히 안 남는다(실제로 2026-07-23~25 사흘이 그렇게 비었다).
TARGETS = {
    "rotation", "explorer", "archive", "stocks", "regime", "sentiment", "holdings",
    "market", "sector", "macro", "screener", "relvalue", "valuation", "portfolio",
    "company", "method", "roadmap", "sources", "site",
    "filings",
    # 🚨 industry.html 은 2026-08-06 에 삭제했지만(사용자 결정) 이 target 은 **남긴다.**
    #   updates.json 에 industry 로 남긴 갱신이 4건 있다 — 지우면 그 기록들이 갱신 피드에서
    #   '기타'로 떨어진다. 슬롯이 없어진 것과 그 슬롯의 역사가 없어지는 것은 다른 일이다.
    #   ⚠ 그래서 updates.html 의 UPD 에도 같이 남겨야 한다(둘은 짝이고 검사가 대조한다).
    #   ⚠ 처음에 "0건이라 잃을 것이 없다"며 뺐는데, 그건 내가 updates.json 을 잘못된 키
    #     (items)로 세어 0 이 나온 것이었다. 실제 키는 events 다. 검사가 곧바로 잡았다.
    "industry",
    # 13F 계열(거장 포트폴리오·운용사 복제 진단). 예전엔 이 영역 변경을 site 로 뭉뚱그려
    # 기록해서 갱신 피드에서 어디가 바뀐 건지 알 수 없었다.
    "guru",
}


def add(target: str, title: str, hm: str | None = None) -> dict:
    if target not in TARGETS:
        raise SystemExit(f"target은 {sorted(TARGETS)} 중 하나여야 한다: {target}")
    now = datetime.now(KST)
    if hm is None:
        hm = now.strftime("%H:%M")
    if not re.fullmatch(r"[0-2]\d:[0-5]\d", hm):
        raise SystemExit(f"시각 형식은 HH:MM: {hm}")
    doc = json.load(io.open(P, encoding="utf-8"))
    ev = {"dt": now.strftime("%Y-%m-%d"), "hm": hm, "target": target, "title": title}
    # 같은 날·같은 대상·같은 제목이 이미 있으면 시각만 갱신(중복 누적 방지)
    for e in doc["events"]:
        if (e["dt"], e["target"], e["title"]) == (ev["dt"], ev["target"], ev["title"]):
            e["hm"] = hm
            break
    else:
        doc["events"].insert(0, ev)
    # 최신순 정렬 — 시각이 없는 옛 이벤트는 그날 마지막으로 취급(하루 안 순서만 영향)
    doc["events"].sort(key=lambda e: (e["dt"], e.get("hm") or "99:99"), reverse=True)
    doc["updated"] = ev["dt"]
    json.dump(doc, io.open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return ev


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    e = add(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print(f"기록: {e['dt']} {e['hm']} [{e['target']}] {e['title']}")
