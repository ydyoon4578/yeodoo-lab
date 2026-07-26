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
    "rotation": "refresh-metrics.yml",
    "filings": "refresh-filings.yml", "facts": "refresh-facts.yml",
    "calendar": "refresh-calendar.yml", "guru": "refresh-13f.yml",
    "insider": "refresh-insider.yml", "earnings": "refresh-earnings.yml",
    "estimates": "refresh-estimates.yml",
    "assets": "refresh-assets.yml", "tech": "refresh-tech.yml",
}
DOW = ["월", "화", "수", "목", "금", "토", "일"]


def sched_of(wf: str) -> str | None:
    """워크플로의 첫 크론(UTC) → 한국시간 문구. 백업 슬롯은 무시하고 본 슬롯만 쓴다."""
    if not wf:
        return None          # 워크플로가 매핑 안 된 축(수시·외부 갱신) — 예정 시각이 없는 게 맞다
    p = os.path.join(ROOT, ".github", "workflows", wf)
    if not os.path.isfile(p):
        return None
    m = re.search(r"cron:\s*'([^']+)'", io.open(p, encoding="utf-8").read())
    if not m:
        return None
    f = m.group(1).split()
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
        {"key": "price", "label": "가격·테크니컬·EPS", "as_of": primary,
         "cadence": "매 거래일", "note": "대표 기준일"},
        {"key": "regime", "label": "시장 국면(FRED 매크로)", "as_of": regime.get("as_of"),
         "cadence": "매 거래일", "note": "지표별 발표 주기가 달라 최신 공통일 기준"},
        {"key": "sentiment", "label": "시장 심리", "as_of": sent.get("as_of"),
         "cadence": "매 거래일", "note": "상태 요약 — 수익 예측 신호가 아니다"},
        {"key": "short", "label": "공매도잔량(FINRA)", "as_of": finra_asof(stocks),
         "cadence": "격주", "note": "FINRA 공시 주기상 구조적으로 뒤처진다",
         # 고정 요일이 없다 — 기준일이 달력상 15일·말일이라 요일이 매번 다르다.
         # 실측(2026-07-26): 공표된 기준일 7/15(수)·6/30(화)·6/15(월)·5/29(금)·5/15(금).
         "manual": "고정 요일 없음 — 기준일이 15일·말일(주말이면 직전 영업일)이고 "
                   "FINRA 공표는 약 8영업일 뒤다. 그 뒤 첫 08:15 갱신에 들어온다"},
        {"key": "members", "label": "지수 편입(PIT 멤버십)", "as_of": members.get("as_of_members"),
         "cadence": "주 1회 확인", "note": "생존편향 보정에 쓰는 시점별 구성"},
        # 로테이션 풀은 '오늘 10선을 고른 날'과 '풀을 마지막으로 채운 날'이 다르다.
        # 화면에 보이는 선정일은 매일 오늘이라 축이 아니고, 축은 풀의 generated다.
        {"key": "rotation", "label": "전략 탐색 풀", "as_of": (load("rotation_pool.json") or {}).get("generated"),
         "cadence": "수시", "note": "외부 출처 수집분 — 랩이 검증한 것이 아니다"},
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
         "cadence": "매일", "note": "애널리스트 추정 스냅샷 — 과거 시점 값이 없어 백테스트에 못 쓴다. 매일 쌓는 중"},
        {"key": "assets", "label": "자산 패널·아카이브 재검", "as_of": (load("assets.json") or {}).get("as_of"),
         "cadence": "주 1회", "note": "ETF·FRED·연준 EBP. 표본이 15~19년이라 하루로는 판정이 바뀌지 않는다"},
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
