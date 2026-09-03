# -*- coding: utf-8 -*-
"""갱신 신선도 게이트 — 자동 갱신 잡이 '돌았는데 낡은 데이터'를 남기면 잡을 실패시킨다.

왜 필요한가
    GitHub 스케줄 크론은 지연·드롭이 잦다(실측: regime 정시 07:45 안 뜨고 백업 08:20이 24분 늦게
    발화, stocks·sentiment는 아예 커밋 없이 07-21에 고착). 잡이 '성공'으로 끝나거나 '변경 없음'으로
    조용히 스킵하면 아무도 모른다. 이 스크립트를 갱신 스텝 뒤에 두어, 산출물의 기준일이 오늘 기준으로
    2영업일 이상 밀려 있으면 **exit 1**로 잡을 빨갛게 만든다 → GitHub 기본 실패 알림 메일이 소유자에게 간다
    (외부 알림 채널 없음 — 텔레그램 등은 사내망 보안으로 미채택).

    '아예 안 뜬' 케이스(스케줄러가 잡을 시작조차 안 함)는 이걸로 못 잡는다(잡이 안 돌았으니 검사도 못 함).
    그건 사이트 자체의 신선도 배지(sources.html)가 접속 시 눈에 보이게 드러낸다 — 두 층이 상보적이다.

영업일 계산은 기존 페이지의 '3영업일 지연 경고' JS와 같은 규약이다(as_of 다음날부터 오늘 직전까지,
주말 제외). 해외(미국) 데이터는 해외=국내 T-1이라 정상 일일 갱신의 기준일이 '어제'가 되어 n=1이고,
2영업일 이상(n>=2)은 갱신이 최소 한 번 이상 누락됐다는 뜻이다.

  python build/check_freshness.py <json_path> <label> [max_biz_days=2] [--key 필드명]

  --key 는 «실행 시점을 나타내는 필드» 를 고른다(기본 as_of). 랩 산출물은 as_of 가
  성과 기준일(전월말)이라 실행 시점이 아니어서 generated 를 봐야 하는 것들이 있다.
"""
from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timedelta, timezone
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

KST = timezone(timedelta(hours=9))


def biz_days_behind(as_of: str, today) -> int:
    """(as_of, today] 구간의 영업일 수. 기존 페이지 '3영업일 지연 경고' JS와 동일 규약.

    해외=국내 T-1이라 정상 일일 갱신은 기준일=어제 → n=1. 갱신이 한 번 누락되면 n=2.
    (주말·월요일 경계 검증 완료: 토요일 조회 n=0, 월요일 정상 n=1.)
    """
    # 🚨 2026-09-03 — **월 키('YYYY-MM')도 받는다.** data/index_history.json 의 as_of 가
    #   월 단위라(위키 리비전이 월 단위다) 종전 코드가 ValueError 로 죽었다 —
    #   그 파일에 감시를 걸려던 시도가 «검사가 터진다» 로 끝났고, 그래서 20일 고착을
    #   아무도 못 봤다. 검사를 못 거는 것도 검사가 없는 것과 같다.
    # ⚠ 그 달의 **첫날**로 읽는다. 말일로 읽으면 이번 달 키가 미래 날짜가 되어 지연이
    #   영원히 0 이 된다 — 「항상 신선」은 무검사와 구별되지 않는다. 첫날은 «그 키를 안다는
    #   것이 보장하는 가장 이른 시점» 이라 지연을 조금 크게 보는 쪽이고, 안전한 방향이다.
    _p = str(as_of)[:10].split("-")
    if len(_p) == 2:
        _p = _p + ["01"]
    y, m, d = (int(x) for x in _p)
    cur = datetime(y, m, d, tzinfo=KST).date()
    n = 0
    while cur < today and n < 60:
        cur = cur + timedelta(days=1)
        if cur.weekday() < 5:      # 0=월 … 4=금
            n += 1
    return n


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    path, label = sys.argv[1], sys.argv[2]
    # 🚨 --key 를 나중에 더했다(2026-08-16). 처음에는 as_of 만 봤는데, 랩 산출물의 as_of 는
    #   **성과 기준일(전월말)** 이라 실행 시점이 아니다. tech_strategies.json 의 as_of 는
    #   2026-07-31 이고 generated 가 2026-08-16 이다 — as_of 로 주간 문턱을 걸면 잡이
    #   정상으로 돌아도 매번 실패한다. 그래서 «무엇이 실행을 나타내는 키인가» 를 호출부가
    #   정하게 한다. 기본값은 그대로 as_of 라 기존 호출 10곳은 하나도 안 바뀐다.
    argv = list(sys.argv[3:])
    key = "as_of"
    if "--key" in argv:
        i = argv.index("--key")
        key = argv[i + 1]
        del argv[i:i + 2]
    max_biz = int(argv[0]) if argv else 2
    try:
        doc = json.load(io.open(path, encoding="utf-8"))
    except Exception as e:
        print(f"::error::[{label}] {path} 읽기 실패: {e}")
        return 1
    as_of = doc.get(key)
    if not as_of:
        # ⚠ 키가 없으면 **통과시키지 않는다.** 스키마가 바뀌어 키가 사라졌을 때 조용히
        #   넘어가면, 그 순간부터 이 잡은 영원히 검사받지 않는다.
        print(f"::error::[{label}] '{key}' 없음 — 산출물이 비었거나 스키마가 바뀌었다 "
              f"(가진 키: {', '.join(sorted(doc)[:8])})")
        return 1
    today = datetime.now(KST).date()
    n = biz_days_behind(as_of, today)
    if n >= max_biz:
        # 🚨 "재실행하라"만 적으면 안 된다. 지연의 원인이 **둘**이고 처방이 정반대다.
        #   실측(2026-08-04): 잡은 정상으로 돌았는데 야후가 08-03 바를 **종가 NaN** 으로 주고
        #   있었다(10/10 종목 전부). 같은 날 01:02 UTC 에는 실제 종가를 줬으니 원천이 오락가락한
        #   것이다. 그 상태에서 재실행하면 같은 NaN 을 다시 받아 또 실패한다 — 기다리는 게 맞다.
        print(f"::error::[{label}] 기준일 {as_of} — 오늘({today}) 기준 {n}영업일 지연(허용 {max_biz - 1}).")
        print("::error::원인을 먼저 가를 것 — 처방이 정반대다.")
        print("::error::  (A) 잡이 안 돌았거나 죽었다 → Actions 에서 재실행한다.")
        print("::error::  (B) 원천에 아직 자료가 없다 → 재실행해도 같다. 원천이 채워지길 기다린다.")
        print("::error::  가르는 법: 이 잡 로그에 수집 단계가 정상으로 찍혔는데 기준일만 안 움직였으면 (B)다.")
        print("::error::  가격이면 원천을 직접 본다 — Ticker('SPY').history(period='5d') 의 "
              "최근 행 Close 가 NaN 이면 (B)다.")
        return 1
    print(f"[{label}] 기준일 {as_of} · {n}영업일 — 신선(OK)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
