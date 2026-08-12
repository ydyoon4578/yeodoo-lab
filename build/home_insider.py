# -*- coding: utf-8 -*-
r"""홈 '내부자 거래' 구획 — data/ins/*.json → data/home_insider.json

무엇을 만드나.
  **기준일이 속한 달**의 장내 내부자 거래를 종목별로 합쳐 순매수/순매도 상위를 뽑는다
  (as_of 2026-06-30 이면 2026년 6월 한 달). 사용자 지시(2026-08-12): 최근월만.
  화면에 사실을 적는 것이지 **신호가 아니다.** 이 랩은 내부자 매수가 초과수익으로
  이어지는지 검증한 적이 없다(data/insider.json 의 limits 에 그렇게 적혀 있다).
  점수도 판정도 만들지 않고, 홈 카드에도 그 문장을 그대로 싣는다.

🚨 순위는 **금액**으로 매긴다. 건수로 매기면 안 된다 — 실측: TPL 은 장내매수 34건으로
  건수 1위인데 총액이 $15,059 다(1~4주씩, 한 10% 주주가 33건). 건수는 '얼마나 자주'이지
  '얼마나 크게'가 아니다.

🚨 공시 지연을 지킨다. Form 4 는 거래 후 2영업일 내 제출이지만 SEC 가 **분기 데이터셋**으로
  묶어 내놓아 수십 일이 밀린다(insider.json 의 lag_days 가 실측치다). 그래서 창을 자를 때
  거래일(d)만 보지 않고 **제출일(fd)** 도 함께 본다 — 그 시점에 이미 공개돼 있던 것만 센다.

⚠ 최신 달의 **마지막 2영업일은 원래 비어 있다.** SEC 분기 데이터셋은 제출일 기준으로 끊기는데
  (실측: 최대 fd = 2026-06-30 = as_of) Form 4 제출 지연 중앙값이 2일이라, 그 이틀치 거래는
  다음 분기 파일에 실린다. 실측 6/29 8건·6/30 3건(평소 70~100건). 창 설계 결함이 아니라
  자료의 경계이고 **다음 분기에 저절로 메워진다** — 직전 경계인 3/30·3/31 은 19·16건으로
  정상이다. 6월 전체 대비 거래 0.7%·금액 0.33% 라 상위 순위를 흔들지 않는다. 그래서 이
  이틀을 화면에서 따로 경고하지 않는다.
  ⚠ last_d(자료에 실제로 있는 마지막 거래일)로는 이 잘림을 알 수 없다 — 6/30 에도 3건이
    남아 있어 last_d 는 2026-06-30 으로 '월말까지 있다'고 말한다. last_d 가 막는 것은 더
    거친 고장, 즉 분기 파일이 달 중간에서 끝나 버리는 경우다. 화면에는 그때만 덧붙인다.

⚠ 코드 P(장내매수)·S(장내매도)만 쓴다. A(주식보상)·M(옵션행사)·F(세금 대납 반납)은 본인이
  고른 거래가 아니라 보상 제도가 굴러간 결과다. 합쳐 세면 '내부자가 샀다'가 틀린 말이 된다.

🚨 **공동보고 중복을 반드시 걷어낸다.** 하나의 거래를 여러 보고자가 각자 Form 4 로 내면 같은
  거래가 사람 수만큼 들어온다. 실측: NRG 2026-03-04 의 14,300,000주 @ $164 가 LS Power
  Equity Advisors(펀드)와 Nanus David(그 소속 이사) 이름으로 두 번 — 순매도가 $2.65B 대신
  $5.29B 로 두 배가 됐다. ⚠ **accession 기준으로는 안 잡힌다** — 두 사람이 각자 다른 접수번호로
  내기 때문이다(…3624 / …3625). 같은 accession 안 완전중복은 전체의 0.2%뿐이었다.
  그래서 키를 (일자·코드·수량·단가)로 잡는다. 서로 다른 내부자가 같은 날 같은 수량을 같은
  단가에 팔면 하나로 합쳐지지만, 실측 최대 영향이 $2.7M 인 반면 놓쳤을 때는 $2.6B 를
  틀리게 적는다 — 비대칭이 명백하다.

🚨 **역할을 같이 적는다.** 금액 상위는 임원이 아니라 10% 주주가 많다 — RSG +$202M 은
  빌 게이츠의 Cascade, WRB +$163M 은 미쓰이스미토모, NRG 매도는 LS Power PE 펀드의
  지분 정리다. 금액만 적으면 '임원이 샀다'로 읽힌다. 지분구조 이벤트와 임원의 판단은 다른
  것이라 한 칸을 내준다.
"""
from __future__ import annotations

import datetime
import glob
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIR_INS = os.path.join(DATA, "ins")
OUT = os.path.join(DATA, "home_insider.json")

TOPN = 8            # 홈 카드에 넣을 줄 수


ROLES = ("임원", "이사", "10%주주", "기타")


def _role(rel: str) -> str:
    """SEC rel 문자열 → 화면용 짧은 태그. refresh_insider._role 과 같은 규칙이어야 한다.

    실측 분포: Officer 2319 · Director 1129 · Director,Officer 899 · TenPercentOwner 223 ·
    Director,Officer,TenPercentOwner 60 · Other 48 · Director,TenPercentOwner 26 · Director,Other 8.
    ⚠ 겸직이 있다. 임원·이사를 겸한 10% 주주는 '10%주주'가 아니라 임원으로 읽어야 맞다 —
      그 사람의 매매는 지분 정리가 아니라 본인 판단일 수 있다. 그래서 순수 10% 주주만 따로 뗀다.
    """
    r = rel or ""
    if "Officer" in r:
        return "임원"
    if "Director" in r:
        return "이사"
    if "TenPercentOwner" in r:
        return "10%주주"
    return "기타"


def _from_monthly(mo, as_of):
    """data/ins_monthly.json(절단 전 원본에서 만든 종목×월 합계) → 집계 dict.

    🚨 이게 정본이다. data/ins/*.json 을 직접 합산하면 회사별 보관 상한(KEEP_PER_CO)에 걸린
      종목의 '그 달'이 며칠치가 된다 — 실측 2026-06 에 21종이 6월 앞부분을 잃었고, 홈 순매도
      4위 AVGO 는 평일 22일 중 10일치(6/17~)를 '한 달'이라 표시했다(보정하면 −$261M 이
      아니라 −$575M, 순위도 3위다).
    ⚠ 없으면 None 을 준다 — 부르는 쪽이 대체 경로로 내려가고, 그 사실을 화면에 적는다.
      조용히 옛 방식으로 돌아가면 이 결함이 되살아나도 아무도 모른다.
    """
    p = os.path.join(DATA, "ins_monthly.json")
    if not os.path.exists(p):
        return None
    try:
        j = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None
    if j.get("as_of") != as_of:
        print("⚠ ins_monthly.json 의 기준일(%s)이 insider.json(%s)과 다르다 — 쓰지 않는다"
              % (j.get("as_of"), as_of))
        return None
    got = set(j.get("roles") or ())
    if not got <= set(ROLES):
        print("⚠ ins_monthly.json 의 역할 라벨이 낯설다(%s) — 수집기와 규칙이 갈라졌다"
              % ", ".join(sorted(got - set(ROLES))))
        return None
    out = {}
    for t, ms in (j.get("by_t") or {}).items():
        v = ms.get(mo)
        if not v:
            continue
        out[t] = {"buy": float(v.get("b") or 0), "sell": float(v.get("s") or 0),
                  "nb": v.get("nb") or 0, "ns": v.get("ns") or 0,
                  "who": v.get("who") or 0, "roles": dict(v.get("roles") or {}),
                  "nd": v.get("nd") or 0, "part": False, "d0": ""}
    return out


def _names():
    """티커 → 회사명. stocks.json 이 정본."""
    p = os.path.join(DATA, "stocks.json")
    try:
        with io.open(p, encoding="utf-8") as f:
            return {s["t"]: (s.get("name") or s["t"]) for s in json.load(f)["stocks"]}
    except Exception:
        return {}


def main() -> int:
    if not os.path.isdir(DIR_INS):
        print("❌ data/ins 가 없다 — build/refresh_insider.py 를 먼저 돌릴 것")
        return 1

    try:
        summ = json.load(io.open(os.path.join(DATA, "insider.json"), encoding="utf-8"))
        as_of, lag = summ.get("as_of"), summ.get("lag_days")
    except Exception:
        as_of, lag = None, None
    if not as_of:
        print("❌ insider.json 의 as_of 가 없다")
        return 1
    mo = as_of[:7]      # 기준일이 속한 달. 분기 데이터셋이라 as_of 는 늘 분기말=월말이다.
    y0, m0 = int(mo[:4]), int(mo[5:])

    nm = _names()
    src = _from_monthly(mo, as_of)      # 정본: 절단 전 원본에서 만든 월별 합계
    agg = {}
    n_tx = n_dup = n_bad = 0
    last_d = ""         # 자료에 실제로 있는 마지막 거래일 — 달 이름만 적으면 안 되는 이유는 위 참조
    days_seen = set()   # 기준월에 거래가 실제로 있던 날짜 — 아래 완전성 게이트가 이걸로 판단한다
    files = sorted(glob.glob(os.path.join(DIR_INS, "*.json")))
    docs = []
    for p in files:
        try:
            docs.append(json.load(io.open(p, encoding="utf-8")))
        except Exception:
            # 🚨 세지 않고 넘기면 79% 가 깨져도 종료 코드 0 으로 발행됐다(적대감사 실측).
            #   파싱 실패는 '자료가 적은 것'이 아니라 '자료를 못 읽은 것'이다 — 아래에서 죽인다.
            n_bad += 1
    # 회사별 보관 상한을 자료에서 읽어 낸다(손으로 적지 않는다). 같은 행 수에 여러 파일이
    # 몰려 있으면 그건 우연이 아니라 상한이다.
    lens = [len(d.get("tr") or []) for d in docs]
    cap_obs = max(lens) if lens else 0
    capped_at_max = lens.count(cap_obs)
    is_cap = cap_obs > 0 and capped_at_max >= 2

    for j in docs:
        t = j.get("t")
        if not t:
            continue
        rows = j.get("tr") or []
        # 🚨 이 종목의 '그 달'이 잘렸는가. 상한에 걸린 파일은 최신순으로 잘리므로 달 앞부분이
        #   통째로 없을 수 있다. 달 시작 **이전** 거래가 파일에 하나라도 있으면 그 달은
        #   잘리지 않았다(최신순 보관이라 그 앞이 남아 있을 수 없다). 이 판정은 정확하다.
        # ⚠ 여기서는 '잘렸을 수 있다'까지만 정한다. 실제로 달 안쪽을 파고들었는지는 관측
        #   첫 거래일이 나온 뒤에 정한다 — 첫 영업일부터 자료가 있으면 잘림이 그 하루
        #   안에 그쳐서, 표시할 만한 결손이 아니다(ABNB 가 그 경우다).
        cut = (is_cap and len(rows) >= cap_obs
               and not any((r.get("d") or "") < mo + "-01" for r in rows))
        seen = set()        # 🚨 공동보고 중복 제거 — 종목 안에서 (일자·코드·수량·단가)
        for r in rows:
            c = r.get("c")
            if c not in ("P", "S"):
                continue
            d, fd = r.get("d"), r.get("fd")
            # 제출일이 기준일 이전인 것만 — 그때 이미 공개돼 있던 것.
            # ⚠ 이 자료에서는 사실상 무해하다(최대 fd == as_of). 그래도 남긴다 — 수집 범위가
            #   넓어지면 그때부터 실제로 일한다.
            if not d or not fd or d > as_of or fd > as_of:
                continue
            amt = (r.get("sh") or 0) * (r.get("px") or 0)
            if amt <= 0:
                continue
            key = (d, c, r.get("sh"), r.get("px"))
            if key in seen:
                if d[:7] == mo:
                    n_dup += 1
                continue
            seen.add(key)
            if d[:7] != mo:
                continue
            n_tx += 1
            days_seen.add(d)
            if d > last_d:
                last_d = d
            a = agg.setdefault(t, {"buy": 0.0, "sell": 0.0, "nb": 0, "ns": 0,
                                   "who": set(), "roles": {}, "cut": cut, "days": set()})
            a["days"].add(d)
            a["d0"] = d if d < a.get("d0", "9") else a["d0"]
            # 역할별 금액 — 어느 쪽이 그 종목의 순액을 끌었는지 화면에 적기 위한 것.
            role = _role(r.get("rel"))
            a["roles"][role] = a["roles"].get(role, 0.0) + amt
            if c == "P":
                a["buy"] += amt; a["nb"] += 1
                a["who"].add(r.get("nm") or "")
            else:
                a["sell"] += amt; a["ns"] += 1

    # 🚨 정본이 있으면 정본을 쓴다. 파일 스캔은 상한에 걸린 종목의 달을 며칠치로 만든다.
    #    스캔 결과는 버리지 않고 **대조**에 쓴다 — 두 경로가 크게 어긋나면 둘 중 하나가 고장이다.
    src_name = "ins_monthly.json(절단 전 원본)"
    if src is None:
        src_name = "data/ins 스캔(⚠ 보관 상한에 걸린 종목은 그 달이 며칠치다)"
        # 달의 첫 영업일. 잘림이 이 날 이후까지 파고들었을 때만 '부분월'로 부른다.
        d1 = next(datetime.date(y0, m0, i).isoformat()
                  for i in range(1, 8) if datetime.date(y0, m0, i).weekday() < 5)
        src = {t: {"buy": a["buy"], "sell": a["sell"], "nb": a["nb"], "ns": a["ns"],
                   "who": len([x for x in a["who"] if x]), "roles": a["roles"],
                   "nd": len(a["days"]), "d0": a.get("d0", ""),
                   "part": bool(a["cut"] and a.get("d0", "") > d1)}
               for t, a in agg.items()}
    n_part = sum(1 for v in src.values() if v.get("part"))
    # 🚨 거래 수는 **쓰는 자료**에서 센다. 정본을 쓰면서 스캔값(절단본)을 적으면 화면 금액과
    #   건수가 서로 다른 자료를 말하게 된다 — 러너에서는 정본이 스캔보다 많다.
    # ⚠ 날짜 축(days_seen·cov)만은 스캔에서 그대로 쓴다. 정본은 종목별 일수만 갖고 있어
    #   날짜 합집합을 만들 수 없고, 합집합은 507종이 함께 깔아 주므로 절단에 둔감하다.
    n_scan = n_tx
    n_tx = sum((v.get("nb") or 0) + (v.get("ns") or 0) for v in src.values())

    rows = []
    for t, a in src.items():
        net = a["buy"] - a["sell"]
        rows.append({
            "t": t, "n": nm.get(t, t),
            "net": round(net), "buy": round(a["buy"]), "sell": round(a["sell"]),
            "nb": a["nb"], "ns": a["ns"],
            # 서로 다른 내부자 수 — 3인 이상 동시 매수가 '클러스터'로 불리는 형태다.
            # ⚠ 이 랩은 그 형태가 수익으로 이어지는지 재지 않았다. 개수만 적는다.
            "who": a["who"],
            # 금액이 가장 큰 역할. 겸직은 _role 에서 임원 쪽으로 접었다.
            "role": max(a["roles"].items(), key=lambda kv: kv[1])[0] if a["roles"] else "",
            # 🚨 그 달이 며칠치인지. True 면 화면에 '부분'이라고 적는다 — 안 적으면 열흘치
            #    금액이 한 달치인 척 옆줄과 나란히 정렬된다(AVGO 실측: 10/22일치로 4위).
            "part": bool(a.get("part")),
            # 관측된 첫 거래일과 거래일 수 — 부분월 줄에서 '어디부터 보이는지'를 적기 위한 것.
            "d0": a.get("d0", ""), "nd": a.get("nd", 0),
        })
    buys = sorted([r for r in rows if r["net"] > 0], key=lambda r: -r["net"])[:TOPN]
    sells = sorted([r for r in rows if r["net"] < 0], key=lambda r: r["net"])[:TOPN]

    # ── 완전성 게이트 ──────────────────────────────────────────────────
    # 🚨 창이 6개월일 때는 한 달이 통째로 비어도 나머지 다섯 달이 가려 줬다. 한 달로 좁힌
    #   지금은 그 달이 비면 카드가 통째로 빈다 — 그리고 '내부자 거래가 없었다'로 읽힌다.
    #   실제 고장은 그게 아니라 '자료를 아직 안 받았다'다. 그래서 조용히 내보내지 않는다.
    if n_bad:
        # 🚨 '읽다 실패한 파일'을 조용히 건너뛰면 안 된다. 적대감사 실측: 507개 중 400개(79%)를
        #   깨뜨려도 종료 코드 0 으로 발행됐고 거래는 1547→362건으로 줄었는데 로그에 한 줄도
        #   안 남았다. 한 개만 깨져도 화면 1위가 바뀔 수 있다(FANG 하나로 −$2.07B→−$738M).
        print("❌ data/ins 파일 %d/%d 개를 읽지 못했다 — 자료가 적은 게 아니라 못 읽은 것이다"
              % (n_bad, len(files)))
        return 2
    if n_tx == 0 or not buys or not sells:
        print("❌ %s 에 장내 거래가 없다(거래 %d · 매수 %d · 매도 %d) — data/ins 갱신부터 확인할 것"
              % (mo, n_tx, len(buys), len(sells)))
        return 2

    # 🚨 두께는 **날짜 축**으로 잰다. 건수를 다른 달과 견주는 방식은 두 번 헛돌았다:
    #   ① 낙수 달(수집 창 가장자리라 늦게 낸 것만 걸린 달 — 2025-08 1건·2025-10 3건·2025-12 3건)이
    #      중앙값을 3 으로 끌어내려 118건짜리 달이 유유히 통과했다.
    #   ② 그리고 애초에 방향이 틀렸다 — 2026-01 은 120건으로 얇지만 **거래일 커버리지 91%** 인
    #      진짜 '조용한 달'이다. 건수 게이트는 조용한 달을 고장으로 오인한다. 잡아야 할 것은
    #      '조용한 달'이 아니라 '자료가 덜 들어온 달'이다.
    # 실측이 둘을 깨끗이 가른다 — 진짜 달 91·95·105·95·95·95%, 낙수 달 4·9·5·9·5·13·13%.
    # 겹치는 구간이 없어 절반(50%)은 넉넉한 자리다(공휴일 때문에 100%는 원래 안 나온다).
    y, m = y0, m0
    _n = (datetime.date(y + (m == 12), (m % 12) + 1, 1) - datetime.timedelta(days=1)).day
    wd = sum(1 for i in range(1, _n + 1) if datetime.date(y, m, i).weekday() < 5)
    cov = 100.0 * len(days_seen) / wd if wd else 0.0
    if cov < 50.0:
        print("❌ %s 는 거래가 %d일에만 있다(평일 %d일 중 %.0f%%) — 조용한 달이 아니라 수집이 "
              "덜 된 것으로 본다" % (mo, len(days_seen), wd, cov))
        return 2

    # 🚨 날짜 축만으로는 **종목 축 결손**을 못 본다. 적대감사 실측: 종목 파일을 절반 지워도
    #   커버리지는 95.5% 그대로였고(날짜는 남은 종목들이 그대로 깔아 준다), 90%를 지워도
    #   72.7%로 문턱을 넘어 통과했다 — 그때 화면 순매도 1위는 FANG −$2.07B 가 아니라
    #   AVGO −$261M 이었다. 축이 둘이니 게이트도 둘이어야 한다.
    # ⚠ 눈금은 **직전 산출물**이다(같은 저장소에 이미 있는 값). 손으로 적은 절대 문턱이 아니라
    #   지난주의 자기 자신과 견주므로, 자료가 커지든 작아지든 따라 움직인다.
    prev_p = OUT
    if os.path.exists(prev_p):
        try:
            pv = json.load(io.open(prev_p, encoding="utf-8"))
        except Exception:
            pv = None
        # 같은 달을 두 번 만들 때만 견준다. 달이 바뀌면 종목 수가 달라지는 게 정상이다.
        if pv and pv.get("month") == mo:
            p_co, p_tx = pv.get("n_co") or 0, pv.get("n_tx") or 0
            if p_co and len(src) < p_co * 0.5:
                print("❌ %s 종목이 직전 %d → %d 로 반토막 났다 — 수집 결손으로 본다"
                      % (mo, p_co, len(src)))
                return 2
            if p_tx and n_tx < p_tx * 0.5:
                print("❌ %s 거래가 직전 %d → %d 로 반토막 났다 — 수집 결손으로 본다"
                      % (mo, p_tx, n_tx))
                return 2

    doc = {
        "note": ("기준일이 속한 한 달의 장내 내부자 거래(SEC Form 4 코드 P·S)를 종목별 순금액으로 "
                 "합친 것. 옵션행사·주식보상·세금 반납은 본인이 고른 거래가 아니라 제외했다. "
                 "달의 마지막 2영업일은 SEC 분기 데이터셋이 제출일에서 끊겨 아직 얇고 "
                 "다음 분기에 메워진다(실측 거래 0.7%·금액 0.33%). "
                 "🚨 이 랩은 내부자 매수가 초과수익으로 이어지는지 검증한 적이 없다 — "
                 "신호가 아니라 사실 표시다."),
        "as_of": as_of, "lag_days": lag, "month": mo, "last_d": last_d,
        "src": src_name, "n_part": n_part,
        "n_tx": n_tx, "n_scan": n_scan, "n_co": len(src), "n_dup": n_dup,
        "n_days": len(days_seen), "day_cov": round(cov, 1),
        "n_buy_side": sum(1 for r in rows if r["net"] > 0),
        "n_sell_side": sum(1 for r in rows if r["net"] < 0),
        "buys": buys, "sells": sells,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("→ %s · %s(자료 마지막 거래일 %s · 지연 %s일) · 거래 %d건 · 종목 %d · 공동보고 중복 제거 %d건"
          % (OUT, mo, last_d or "없음", lag, n_tx, len(src), n_dup))
    print("   출처 %s · 거래일 %d/%d(%.0f%%)%s"
          % (src_name, len(days_seen), wd, cov, (" · ⚠ 부분월 %d종" % n_part) if n_part else ""))
    print("   순매수 %d종 · 순매도 %d종" % (doc["n_buy_side"], doc["n_sell_side"]))
    for r in buys[:3]:
        print("   매수 %-6s %14s  %-7s %d건·%d인%s" % (r["t"], format(r["net"], ","), r["role"],
                                                     r["nb"], r["who"], " ⚠부분" if r["part"] else ""))
    for r in sells[:3]:
        print("   매도 %-6s %14s  %-7s %d건%s" % (r["t"], format(r["net"], ","), r["role"],
                                                r["ns"], " ⚠부분" if r["part"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
