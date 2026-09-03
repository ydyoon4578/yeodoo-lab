#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""기준일 정본 생성기 → data/asof.json

이 사이트의 1순위 원칙은 "모든 데이터의 as-of를 통일하고 메인에 표기한다"이다.
그런데 기준일은 실제로 하나가 아니다 — 가격은 매일, FINRA 공매도잔량은 격주,
지수 편입은 리밸런스 때만 바뀐다. 원칙의 진짜 뜻은 '전부 같은 날짜'가 아니라
**'축이 몇 개이고 각각 언제인지를 숨기지 않는다'** 이다.

그래서 축을 한 파일에 모아 정본으로 두고, 전 페이지 내비 칩·홈 기준일 표·
sources.html이 이 파일 하나만 읽게 한다. 페이지마다 자기 날짜를 따로 적으면
어긋나는 날 어느 쪽이 맞는지 아무도 모른다(그 사고가 이미 있었다).

  primary   = 대표 기준일(가격·테크니컬 — 화면 상단에 크게 뜨는 그 날짜)
  axes[]    = 축별 기준일과 갱신 주기
  lag_days  = primary 대비 뒤처진 영업일 수(0이면 통일)

사용: python3 build/asof_index.py
"""
from __future__ import annotations

import datetime as dt
import io
import json, re
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "asof.json")


def load(fn: str):
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        return None
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def bdays(frm: str, to: str) -> int:
    """frm에서 to까지 흐른 영업일(미 휴장은 세지 않는다 — 근사치로 충분하다)."""
    try:
        a = dt.date.fromisoformat(str(frm)[:10])
        b = dt.date.fromisoformat(str(to)[:10])
    except Exception:
        return 0
    if a >= b:
        return 0
    n = 0
    while a < b:
        a += dt.timedelta(days=1)
        if a.weekday() < 5:
            n += 1
    return n


def finra_asof(stocks: dict) -> str | None:
    """공매도잔량 기준일. stocks.json의 factor_defs가 정본이고(sources.html도 여기를 읽는다),
    없으면 종목 상세 sd/의 dtc.dt로 물러선다."""
    fd = (stocks or {}).get("factor_defs") or {}
    for k in ("dtc", "sipct"):
        d = (fd.get(k) or {}).get("as_of")
        if d:
            return d
    sd = os.path.join(DATA, "sd")
    if not os.path.isdir(sd):
        return None
    for fn in sorted(os.listdir(sd))[:40]:
        if not fn.endswith(".json"):
            continue
        try:
            with io.open(os.path.join(sd, fn), encoding="utf-8") as f:
                sig = (json.load(f) or {}).get("sig") or {}
        except Exception:
            continue
        d = (sig.get("dtc") or {}).get("dt") or (sig.get("sipct") or {}).get("dt")
        if d:
            return d
    return None


# 축 → 그 축을 굽는 워크플로. 예정 시각은 **크론에서 직접 읽는다** — 손으로 적으면
# 워크플로를 고칠 때 화면만 옛 시각을 말하게 된다(그 사고를 이미 한 번 냈다).
WF = {
    "price": "refresh-stocks.yml", "signals": "refresh-stocks.yml",
    "regime": "refresh-regime.yml", "sentiment": "refresh-sentiment.yml",
    # ⚠ refresh-holdings.yml은 strategy_holdings.json을 만들 뿐 members.json은 건드리지 않는다.
    #   그걸 걸어두면 없는 일정을 화면이 말한다(실제로 '매월 2일'이라고 잘못 적혀 있었다).
    #   2026-07-26부터 전용 잡(refresh-members.yml)이 공개 소스에서 갱신한다.
    "members": "refresh-members.yml",
    # ⚠ rotation 은 워크플로가 없다. refresh-metrics.yml 은 strategy_backtests/rf 만 다시 계산할 뿐
    #   rotation_pool.json 을 만들지 않는다(생산자는 로컬 작업 스케줄러 KB_RotationDaily + 헤드리스
    #   Claude — 등록은 build/rotation_task_install.ps1, 러너는 build/rotation_daily.ps1,
    #   지시서는 build/rotation_daily_prompt.md 다. 2026-08-11 에 회사 PC 에서 이 PC 로 옮기며
    #   저장소 안으로 들여왔다 — 그 전에는 '무엇이 어디서 도는지'가 어느 파일에도 없어서
    #   나흘 멈춘 것을 아무도 몰랐다).
    #   그걸 걸어두니 화면이 '매주 토 10:05'라는 없는 일정을 말했고, 같은 축을 cron 에서
    #   파생하는 data/schedule.json 은 '수시 (자동 잡 아님)'이라 두 화면이 서로 다른 말을 했다.
    #   members 사례(위 주석)와 같은 실수 — 매핑하지 않고 manual 문구로 둔다.
    "filings": "refresh-filings.yml", "facts": "refresh-facts.yml",
    "calendar": "refresh-calendar.yml", "guru": "refresh-13f.yml",
    "insider": "refresh-insider.yml", "earnings": "refresh-earnings.yml",
    "estimates": "refresh-estimates.yml",
    "assets": "refresh-assets.yml", "tech": "refresh-tech.yml",
    "cot": "refresh-cot.yml",
}
DOW = ["월", "화", "수", "목", "금", "토", "일"]


def sched_of(wf: str) -> str | None:
    """워크플로의 크론(UTC) → 한국시간 문구. 백업 슬롯은 무시하고 본 슬롯만 쓴다.

    🚨 2026-08-20 점검 — 종전엔 **첫 크론만** 읽었다. refresh-tech 은 크론이 둘(매월 1일 +
      매주 토)이라 화면이 월간 것만 말했다 — 전부 읽어 « · » 로 잇는다."""
    if not wf:
        return None          # 워크플로가 매핑 안 된 축(수시·외부 갱신) — 예정 시각이 없는 게 맞다
    p = os.path.join(ROOT, ".github", "workflows", wf)
    if not os.path.isfile(p):
        return None
    ms = re.findall(r"cron:\s*'([^']+)'", io.open(p, encoding="utf-8").read())
    if not ms:
        return None
    outs = []
    for cexp in ms[:2]:                      # 본 슬롯 최대 둘 — 백업 슬롯은 대개 셋째 이후
        one = _sched_one(cexp)
        if one and one not in outs:
            outs.append(one)
    return " · ".join(outs) if outs else None


def _sched_one(cexp: str) -> str | None:
    f = cexp.split()
    if len(f) != 5:
        return None
    mi, hh, dom, mon, dow = f
    try:
        mi_i, hh_i = int(mi), int(hh)
    except ValueError:
        return None
    kh = (hh_i + 9) % 24
    rolled = (hh_i + 9) >= 24          # UTC→KST에서 날짜가 넘어가는가
    hm = "%02d:%02d" % (kh, mi_i)
    if dom != "*":
        # 매월 N일. 날짜가 넘어가면 하루 뒤가 된다.
        try:
            d0 = int(dom.split(",")[0]) + (1 if rolled else 0)
        except ValueError:
            return "매월 " + hm
        return "매월 %d일 %s" % (d0, hm)
    if dow == "*":
        return "매일 " + hm
    # 요일 집합을 펼친 뒤 KST 이월을 반영한다. 'UTC 월~금'은 KST로 **화~토**가 된다 —
    # 여기서 '평일'이라 적으면 토요일 갱신을 화면이 숨기는 셈이다.
    days = set()
    for part in dow.split(","):
        if "-" in part:
            try:
                a0, b0 = (int(x) for x in part.split("-"))
            except ValueError:
                continue
            k = a0
            while True:
                days.add(k % 7)
                if k % 7 == b0 % 7:
                    break
                k += 1
        else:
            try:
                days.add(int(part) % 7)
            except ValueError:
                pass
    if not days:
        return hm
    idxs = sorted(((d - 1) % 7 + (1 if rolled else 0)) % 7 for d in days)
    if len(idxs) == 1:
        return "매주 %s %s" % (DOW[idxs[0]], hm)
    if idxs == [0, 1, 2, 3, 4]:
        return "평일 " + hm
    # 연속 구간이면 'A~B'로 줄인다(화~토처럼)
    if all(idxs[i] + 1 == idxs[i + 1] for i in range(len(idxs) - 1)):
        return "%s~%s %s" % (DOW[idxs[0]], DOW[idxs[-1]], hm)
    return "%s %s" % ("·".join(DOW[i] for i in idxs), hm)


def main() -> int:
    stocks = load("stocks.json") or {}
    regime = load("regime.json") or {}
    sent = load("sentiment.json") or {}
    members = load("members.json") or {}

    primary = stocks.get("as_of")
    if not primary:
        print("❌ stocks.json as_of 없음 — 정본을 만들 수 없다")
        return 1

    axes = [
        # 🚨 2026-08-18 — 「대표 기준일」 넉 자로는 왜 어제 날짜인지가 안 읽힌다.
        #   사용자가 KST 월요일에 «금요일로 뜬다, 국내 대체공휴일 때문인가» 라고 물었다.
        #   아니다 — 이 축은 **미국 거래일**이 정하고 국내 달력과 무관하다. 그 사실을
        #   날짜 옆에 적어 두면 같은 물음이 다시 안 나온다.
        {"key": "price", "label": "가격·테크니컬·EPS", "as_of": primary,
         "cadence": "매 거래일",
         # ⚠ 이 값은 esc() 를 타고 화면에 그대로 나간다 — 마크다운 ** 를 쓰지 않는다.
         "note": "대표 기준일. 미국 직전 거래일 종가다 — 한국 시각으로 그다음 날 오전에 "
                 "들어오므로 KST 월요일에 지난 금요일 날짜가 서는 것이 정상이다. 미국 "
                 "휴장일에도 그대로 서고, 국내 공휴일과는 무관하다(갱신은 전부 UTC 크론이다)"},
        {"key": "regime", "label": "시장 국면(FRED 매크로)", "as_of": regime.get("as_of"),
         # ⚠ '최신 공통일'이라고 적었던 적이 있으나 사실과 반대다 — refresh_regime.py L73 은
         #   max(각 시리즈 최신일)이다. 공통일(=최솟값)이면 2026-04 대 날짜가 나온다.
         #   39개 중 이 날짜의 관측이 있는 건 커브·기대인플레 4개뿐이고 실물지표 13개는 전월분,
         #   주택가격은 석 달 전 분이다. 한 날짜로 묶인 것처럼 읽히지 않게 적는다.
         "cadence": "매 거래일",
         "note": "지표마다 발표 주기가 달라 가장 최근에 갱신된 지표의 날짜다 — 39개가 모두 이 날짜는 아니다"},
        {"key": "sentiment", "label": "시장 심리", "as_of": sent.get("as_of"),
         # 축 날짜는 종합점수의 마지막 관측일이다. 하위 성분(VIX·기간구조·MOVE 등)은 발표가
         # 늦거나 결측이면 직전 값을 끌어다 쓰므로(ffill), 성분 하나하나가 이 날짜의 관측이라는
         # 뜻은 아니다 — 그렇게 읽히지 않게 적는다.
         "cadence": "매 거래일",
         "note": "상태 요약 — 수익 예측 신호가 아니다. 성분별로는 직전 값을 끌어다 쓴 것이 있어 전부 이 날짜의 관측은 아니다"},
        # COT 는 축 날짜와 '알 수 있게 된 날'이 3일 다르다 — 기준은 화요일 장마감, 발표는 그 주
        # 금요일 15:30 ET 다. 다른 축은 둘이 같아서 as_of 만 적어도 됐지만 여기는 그러면 읽는
        # 사람이 3일치 룩어헤드를 공짜로 가진 것으로 오해한다. note 에 그 간격을 명시한다.
        {"key": "cot", "label": "시장 포지션(CFTC COT)", "as_of": (load("cot.json") or {}).get("as_of"),
         "cadence": "주 1회",
         "note": "기준은 화요일 장마감 포지션이고 발표는 그 주 금요일이다 — 백테스트는 발표 이후 첫 거래일부터만 쓸 것"},
        {"key": "short", "label": "공매도잔량(FINRA)", "as_of": finra_asof(stocks),
         "cadence": "격주", "note": "FINRA 공시 주기상 구조적으로 뒤처진다",
         # 고정 요일이 없다 — 기준일이 달력상 15일·말일이라 요일이 매번 다르다.
         # 실측(2026-07-26): 공표된 기준일 7/15(수)·6/30(화)·6/15(월)·5/29(금)·5/15(금).
         "manual": "고정 요일 없음 — 기준일이 15일·말일(주말이면 직전 영업일)이고 "
                   "FINRA 공표는 약 8영업일 뒤다. 그 뒤 첫 정기 갱신에 들어온다"},
        # 🚨 2026-09-03 — **축을 둘로 갈랐다.** 종전에는 이 한 줄이 members.json 의
        #   as_of_members 를 읽으면서 라벨을 「지수 편입(PIT 멤버십) · 생존편향 보정에 쓰는
        #   시점별 구성」이라 달았다. 그런데 members.json 은 스스로 note 에
        #   「**오늘 스냅샷이며 과거 편입 이력이 아니다**」라고 적어 뒀다.
        #   생존편향 보정이 실제로 읽는 것은 data/index_history.json 이고, 그쪽은
        #   굽는 잡이 없어 2026-08-14 이후 **20일 고착**이었다.
        #   즉 화면이 「4일 전 것」이라 말하는 동안 실물은 20일 얼어 있었다 — **거짓 초록**이
        #   그 사이 새 달 키가 안 생기는 것을 가려 줬고, 그것이 NDX 계열 다섯을 2026-10-02 에
        #   무보유로 만들 뻔했다(build/index_members.py 의 꼬리 규약 주석).
        #   ⚠ 한 축이 두 파일을 대표하면 낡은 쪽이 신선한 쪽 뒤에 숨는다. 갈라서 각자 말하게 한다.
        {"key": "members", "label": "지수 편입 명단(오늘 스냅샷)", "as_of": members.get("as_of_members"),
         # ⚠ 2026-09-04 — 「주 1회 확인」이었는데 백업 슬롯을 붙이자 크론과 어긋났다.
         #   validate_site 의 «갱신 주기 라벨 ↔ 크론» 검사가 잡았다 — cadence 는 손으로
         #   적는 값이라 크론을 바꿀 때 같이 안 고쳐진다는 것을 그 검사가 이미 적어 뒀고,
         #   내가 정확히 그 함정을 밟았다.
         "cadence": "주 1회(토) · 백업 슬롯",
         "note": "**오늘의** 편입 명단이다 — 과거 편입 이력이 아니다(그쪽은 아래 «시점정합 "
                 "편입 이력» 축이다). 유니버스를 정하는 데 쓴다"},
        {"key": "members_hist", "label": "시점정합 편입 이력(생존편향 보정)",
         "as_of": (load("index_history.json") or {}).get("as_of"),
         "cadence": "주 1회(토)",
         "note": "생존편향·선견 보정이 **실제로 읽는** 파일이다(위 «오늘 스냅샷» 이 아니다). "
                 "위키백과 지수 목록 문서의 과거 리비전에서 월 단위로 만든다 — 월 키라 "
                 "새 달 첫 거래일부터 그 주 갱신까지는 직전 달을 이월한다"
                 "(build/index_members.at · 한도 2달)"},
        # 로테이션 풀은 '오늘 10선을 고른 날'과 '풀을 마지막으로 채운 날'이 다르다.
        # 화면에 보이는 선정일은 매일 오늘이라 축이 아니고, 축은 풀의 generated다.
        {"key": "rotation", "label": "전략 탐색 풀", "as_of": (load("rotation_pool.json") or {}).get("generated"),
         "cadence": "수시", "note": "외부 출처 수집분 — 랩이 검증한 것이 아니다",
         "manual": "자동 잡 아님 — 로컬 작업 스케줄러(KB_RotationDaily)가 매일 07:55 웹리서치로 갱신해 푸시한다"},
        # 공시는 '수집한 날'이 아니라 '가장 최근에 접수된 제출일'이 기준이다. 회사가 안 내면
        # 우리가 매일 돌아도 축은 안 움직인다 — 그 사실을 감추지 않으려고 접수일을 쓴다.
        {"key": "filings", "label": "SEC 공시(8-K)", "as_of": (load("filings.json") or {}).get("as_of"),
         "cadence": "주 1회 수집", "note": "제출 접수일 기준 — 회사가 안 내면 이 날짜는 안 움직인다"},
        # 재무는 '분기 결산 기간말'이라 분기에 한 번 움직인다. 가격과 나란히 놓고 '뒤처졌다'고
        # 읽으면 안 되는 축이라, cadence에 그 성격을 적는다.
        {"key": "facts", "label": "SEC 재무(XBRL)", "as_of": (load("facts.json") or {}).get("as_of"),
         "cadence": "분기(실적 발표 시)", "note": "회사의 최근 보고 기간말 — 구조적으로 분기마다 한 번 움직인다"},
        # 내부자 거래는 SEC가 분기 단위로 묶어 내놓는다. 뒤처지는 게 아니라 원래 그런 축이다.
        # 발표 일정만은 as_of가 '수집한 날'이다 — 다른 축처럼 '데이터의 기준일'이 아니라
        # 앞으로의 예정표라, 언제 받아온 표인지가 그 표의 신선도다.
        {"key": "calendar", "label": "발표 일정(FRED)", "as_of": (load("calendar.json") or {}).get("as_of"),
         "cadence": "주 1회 수집", "note": "앞으로의 예정표 — as_of는 데이터 기준일이 아니라 수집일이다"},
        # 13F는 분기말 잔고를 45일 뒤에 낸다 — 뒤처지는 게 아니라 원래 그런 축이다.
        {"key": "guru", "label": "13F 보유", "as_of": (load("guru.json") or {}).get("as_of"),
         "cadence": "분기 데이터셋", "note": "분기말 잔고를 45일 뒤 제출 — 최대 4.5개월 묵는다"},
        {"key": "insider", "label": "내부자 거래(Form 4)", "as_of": (load("insider.json") or {}).get("as_of"),
         "cadence": "분기 데이터셋", "note": "SEC가 분기로 묶어 내놓아 수십 일 지연이 구조적이다 — 실시간이 아니다"},
        {"key": "earnings", "label": "실적 발표 일정", "as_of": (load("earnings.json") or {}).get("as_of"),
         "cadence": "매일", "note": "예정일은 회사가 바꾼다 — 조회 시점의 예정일이며 확정이 아니다"},
        {"key": "estimates", "label": "선행 컨센서스 지표", "as_of": (load("estimates.json") or {}).get("as_of"),
         # 🚨 2026-08-05 — "매일"이라 적혀 있었는데 크론은 `30 22 * * 5`(매주 토)다.
         #   2026-07-29 에 주간으로 내리면서 이 라벨을 안 고쳤다. 화면에는 그 결과
         #   "매일 · 매주 토 07:30 KST"라는 자기모순이 찍혔고, 3영업일 지연이 고장처럼 보였다.
         "cadence": "주 1회 수집", "note": "애널리스트 추정 스냅샷 — 과거 시점 값이 없어 백테스트에 못 쓴다. 주 1회 쌓는 중"},
        {"key": "assets", "label": "자산 패널·아카이브 재검", "as_of": (load("assets.json") or {}).get("as_of"),
         # 🚨 2026-08-05 — "주 1회"라 적혀 있었는데 크론은 `40 23 * * 0-5`(월~토 매일)다.
         #   반대 방향으로 어긋난 짝이다. 판정이 하루로 안 바뀌는 것은 맞지만, 잡은 매일 돈다.
         "cadence": "매 거래일", "note": "ETF·FRED·연준 EBP. 잡은 매일 돌지만 표본이 15~19년이라 하루로는 판정이 바뀌지 않는다"},
        {"key": "signals", "label": "지표별 타이밍 신호", "as_of": (load("signal_lab.json") or {}).get("as_of"),
         "cadence": "매 거래일", "note": "종목 스냅샷과 같은 잡에서 같은 기준일로 굽는다 — 어긋나면 그건 사고다"},
        {"key": "tech", "label": "전략 랩 백테스트", "as_of": (load("tech_strategies.json") or {}).get("as_of"),
         "cadence": "주 1회", "note": "일봉 입력이라 하루 단위로는 판정이 바뀌지 않는다 — 주말에만 다시 돌린다"},
    ]
    axes = [a for a in axes if a.get("as_of")]

    # ── 수집일 vs 데이터 기준일 ────────────────────────────────────────
    # 아래 축들은 '언제 받았나'를 기준일로 적고 있었다. 그래서 토요일에 받으면 토요일이,
    # 일요일에 받으면 일요일이 대표 기준일(마지막 거래일)보다 **앞서** 표시된다 —
    # 표를 보는 사람은 "대표보다 최신 데이터가 있다"로 읽지만 시장은 그날 열리지도 않았다.
    # 기준일은 그 데이터가 반영하는 **시장 날짜**로 맞추고, 실제 수집일은 따로 남긴다.
    # members도 여기 든다 — 자동 갱신으로 바꾸면서 '받은 날'을 기준일로 찍게 됐고,
    # 그 순간 대표(마지막 거래일)를 다시 앞질렀다. 수집일 축은 예외 없이 이 규칙을 탄다.
    COLLECTED = {"earnings", "calendar", "rotation", "members", "estimates"}
    for a in axes:
        if a["key"] in COLLECTED and a["as_of"] > primary:
            a["collected"] = a["as_of"]
            a["as_of"] = primary

    # ── 시장일 축이 대표보다 앞설 수 있다 ──────────────────────────────────
    # 위 COLLECTED 처리는 '받은 날을 기준일로 찍은' 오기입을 되돌리는 것이다. 그런데 아래 축들은
    # as_of 가 **실제 거래일**에서 나온다(예: assets 는 거래일 격자의 마지막 날 dates[-1]).
    # 이들이 대표보다 앞서는 것은 오기입이 아니라 **그 축이 먼저 돌았다**는 뜻이다.
    #
    # 언제 생기나(실측 2026-07-27): 자산 패널 잡을 평일에 수동 실행하면 미국장 마감 뒤라
    # 그날 종가가 잡히는데, 대표(종목 패널)는 아직 그날 것을 안 받아 하루 뒤처져 있다.
    # 정기 실행(토 10:25 KST)에서는 둘 다 직전 금요일이라 이 일이 안 생겨 오래 안 보였다.
    #
    # 예전엔 이걸 구분하지 않아 validate 가 '수집일을 기준일로 찍고 있다'로 막았다. 그 바람에
    # 같은 잡의 13F 재수집 결과까지 커밋 단계 전에 폐기됐다. 날짜를 대표로 끌어내리는 것은
    # 거짓이므로(그 데이터는 정말 그날 것이다) 사실대로 두고 '앞섬'을 표시만 한다.
    # 🚨 2026-08-15 — filings(8-K)를 여기 넣는다. 검사기가 "COLLECTED 에 넣을 것" 이라고
    #   안내했지만 **그건 이 축에 틀린 처방이다.** refresh_filings.py 는
    #       as_of = feed[0]["d"]      # 가장 최근 8-K 의 실제 공시일
    #   로 잡는다 — 받은 날이 아니라 자료가 말하는 날이다. COLLECTED 에 넣으면 진짜
    #   공시일을 대표(마지막 거래일)로 끌어내려 **없던 거짓을 만든다.**
    #   실제로 걸린 경우: 8-K 는 2026-08-14 에 나왔는데 가격 격자는 아직 08-13 이었다.
    #   공시는 장 마감 뒤·휴장일에도 나오므로 이 축은 원래 가격보다 앞설 수 있다.
    # ⚠ 검사기 메시지를 그대로 따르지 않은 자리다. 메시지는 '수집일 오기입' 이라는 가장
    #   흔한 사유를 전제로 쓰였고, 이 축은 그 사유가 아니다. 사유를 확인하지 않고 처방만
    #   따르면 검사는 통과하되 화면이 틀린 날짜를 말하게 된다.
    MARKET = {"price", "assets", "signals", "tech", "regime", "sentiment", "filings"}
    for a in axes:
        if a["key"] in MARKET and (a["as_of"] or "") > primary:
            a["ahead"] = True
    for a in axes:
        sc = sched_of(WF.get(a["key"], ""))
        if sc:
            a["sched"] = sc + " KST"
    for a in axes:
        a["lag_days"] = bdays(a["as_of"], primary)

    uni = sorted({a["as_of"] for a in axes})
    doc = {
        "note": "기준일 정본. build/asof_index.py가 만들고, 전 페이지 내비 칩·홈·sources.html이 "
                "이 파일만 읽는다. 페이지에 날짜를 직접 적지 말 것.",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "primary": primary,
        "unified": len(uni) == 1,
        "axes": axes,
        # 그날 종가를 원천의 일봉이 아니라 분봉 집계로 되살렸으면 그 사실을 여기로 옮긴다.
        # sources.html 은 날짜 하나 때문에 stocks.json(971KB)을 받지 않는 규약이라, 2KB 인
        # 이 정본이 나르는 것이 맞다. 정상일에는 stocks.json 의 px_recon 이 null 이라 이 키도 null 이다.
        # ⚠ 값이 있는데 화면이 안 읽으면 '복구한 종가를 복구했다고 말하지 않는' 상태가 된다 —
        #   이 랩이 가장 경계하는 실패다. sources.html 의 가격 행이 이 키를 읽는다.
        "px_recon": stocks.get("px_recon"),
        # 화면에 그대로 쓰는 한 줄 — '통일했다'는 주장을 데이터로만 하게 한다
        "summary": ("전 축 %s 통일" % primary) if len(uni) == 1 else
                   ("대표 %s · 축 %d개(%s)" % (primary, len(axes),
                    " · ".join("%s %s" % (a["label"], a["as_of"]) for a in axes if a["as_of"] != primary))),
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("기준일 정본: primary %s · 축 %d개 · %s"
          % (primary, len(axes), "통일" if doc["unified"] else "분리"))
    for a in axes:
        print("  %-22s %s%s" % (a["label"], a["as_of"],
                                "" if not a["lag_days"] else "  (−%d영업일)" % a["lag_days"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
