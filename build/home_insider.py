# -*- coding: utf-8 -*-
r"""홈 '내부자 거래' 구획 — data/ins/*.json → data/home_insider.json

무엇을 만드나.
  최근 6개월 **장내** 내부자 거래를 종목별로 합쳐 순매수/순매도 상위를 뽑는다.
  화면에 사실을 적는 것이지 **신호가 아니다.** 이 랩은 내부자 매수가 초과수익으로
  이어지는지 검증한 적이 없다(data/insider.json 의 limits 에 그렇게 적혀 있다).
  점수도 판정도 만들지 않고, 홈 카드에도 그 문장을 그대로 싣는다.

🚨 순위는 **금액**으로 매긴다. 건수로 매기면 안 된다 — 실측: TPL 은 장내매수 34건으로
  건수 1위인데 총액이 $15,059 다(1~4주씩, 한 10% 주주가 33건). 건수는 '얼마나 자주'이지
  '얼마나 크게'가 아니다.

🚨 공시 지연을 지킨다. Form 4 는 거래 후 2영업일 내 제출이지만 SEC 가 **분기 데이터셋**으로
  묶어 내놓아 수십 일이 밀린다(insider.json 의 lag_days 가 실측치다). 그래서 창을 자를 때
  거래일(d)만 보지 않고 **제출일(fd)** 도 함께 본다 — 그 시점에 이미 공개돼 있던 것만 센다.

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

WIN_DAYS = 182      # 트레일링 6개월
TOPN = 8            # 홈 카드에 넣을 줄 수


def _role(rel: str) -> str:
    """SEC rel 문자열 → 화면용 짧은 태그.

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
    lo = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=WIN_DAYS)).isoformat()

    nm = _names()
    agg = {}
    n_tx = n_dup = 0
    for p in sorted(glob.glob(os.path.join(DIR_INS, "*.json"))):
        try:
            j = json.load(io.open(p, encoding="utf-8"))
        except Exception:
            continue
        t = j.get("t")
        if not t:
            continue
        seen = set()        # 🚨 공동보고 중복 제거 — 종목 안에서 (일자·코드·수량·단가)
        for r in (j.get("tr") or []):
            c = r.get("c")
            if c not in ("P", "S"):
                continue
            d, fd = r.get("d"), r.get("fd")
            # 거래일이 창 안 + 제출일이 기준일 이전(=그때 공개돼 있던 것)
            if not d or not fd or not (lo < d <= as_of) or fd > as_of:
                continue
            amt = (r.get("sh") or 0) * (r.get("px") or 0)
            if amt <= 0:
                continue
            key = (d, c, r.get("sh"), r.get("px"))
            if key in seen:
                n_dup += 1
                continue
            seen.add(key)
            n_tx += 1
            a = agg.setdefault(t, {"buy": 0.0, "sell": 0.0, "nb": 0, "ns": 0,
                                   "who": set(), "roles": {}})
            # 역할별 금액 — 어느 쪽이 그 종목의 순액을 끌었는지 화면에 적기 위한 것.
            role = _role(r.get("rel"))
            a["roles"][role] = a["roles"].get(role, 0.0) + amt
            if c == "P":
                a["buy"] += amt; a["nb"] += 1
                a["who"].add(r.get("nm") or "")
            else:
                a["sell"] += amt; a["ns"] += 1

    rows = []
    for t, a in agg.items():
        net = a["buy"] - a["sell"]
        rows.append({
            "t": t, "n": nm.get(t, t),
            "net": round(net), "buy": round(a["buy"]), "sell": round(a["sell"]),
            "nb": a["nb"], "ns": a["ns"],
            # 서로 다른 내부자 수 — 3인 이상 동시 매수가 '클러스터'로 불리는 형태다.
            # ⚠ 이 랩은 그 형태가 수익으로 이어지는지 재지 않았다. 개수만 적는다.
            "who": len([x for x in a["who"] if x]),
            # 금액이 가장 큰 역할. 겸직은 _role 에서 임원 쪽으로 접었다.
            "role": max(a["roles"].items(), key=lambda kv: kv[1])[0] if a["roles"] else "",
        })
    buys = sorted([r for r in rows if r["net"] > 0], key=lambda r: -r["net"])[:TOPN]
    sells = sorted([r for r in rows if r["net"] < 0], key=lambda r: r["net"])[:TOPN]

    doc = {
        "note": ("최근 6개월 장내 내부자 거래(SEC Form 4 코드 P·S)를 종목별 순금액으로 합친 것. "
                 "옵션행사·주식보상·세금 반납은 본인이 고른 거래가 아니라 제외했다. "
                 "🚨 이 랩은 내부자 매수가 초과수익으로 이어지는지 검증한 적이 없다 — "
                 "신호가 아니라 사실 표시다."),
        "as_of": as_of, "lag_days": lag, "win_days": WIN_DAYS,
        "n_tx": n_tx, "n_co": len(agg), "n_dup": n_dup,
        "n_buy_side": sum(1 for r in rows if r["net"] > 0),
        "n_sell_side": sum(1 for r in rows if r["net"] < 0),
        "buys": buys, "sells": sells,
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("→ %s · 기준일 %s(지연 %s일) · 거래 %d건 · 종목 %d · 공동보고 중복 제거 %d건"
          % (OUT, as_of, lag, n_tx, len(agg), n_dup))
    print("   순매수 %d종 · 순매도 %d종" % (doc["n_buy_side"], doc["n_sell_side"]))
    for r in buys[:3]:
        print("   매수 %-6s %14s  %-7s %d건·%d인" % (r["t"], format(r["net"], ","), r["role"], r["nb"], r["who"]))
    for r in sells[:3]:
        print("   매도 %-6s %14s  %-7s %d건" % (r["t"], format(r["net"], ","), r["role"], r["ns"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
