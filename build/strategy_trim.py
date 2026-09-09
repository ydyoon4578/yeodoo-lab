# -*- coding: utf-8 -*-
r"""전략(액티브 틸트) 비중 조정 주문 계산기 — 2Z30 / 2A81.

화면(portfolio.html)의 «전략(%)» 은 소수 2자리 반올림 표시값이다. 그걸로 역산하면
종목당 수십 주가 틀어진다(MU 와 LITE 는 화면엔 0.11·0.12 로 달라 보이지만 실제로는
둘 다 0.1150%). 그래서 portfolio_fund.py 와 **같은 원천·같은 산식**으로 다시 잰다.

    전략비중 w_s = 전략순수량 × 종가(USD) × 환율 ÷ NAV
    목표수량      = 목표비중 × NAV ÷ (종가 × 환율)
    주문수량      = 목표수량 − 전략순수량        (음수 = 매도)

🚨 환율은 «보유일 환율»(fx_hold). 최신 환율을 섞으면 원장 평가액과 자기모순이 되어
   화면 비중과 다른 답이 나온다(portfolio_fund.py 의 같은 주석 참조).
🚨 전략순수량은 원장의 **누적 순수량**이다. 체결 후 원장에 반대매매를 안 적으면
   다음 계산이 옛 수량으로 돌아간다.

── 쓰는 순서 ────────────────────────────────────────────────────────────────
  1) 현황 보기          python build/strategy_trim.py --list
  2) 계획서 만들기      python build/strategy_trim.py --make-plan plan.csv
     엑셀에서 «목표비중%» 열만 고친다. 종목마다 다르게 줘도 되고 0 이면 전량 청산.
  3) 주문 뽑기          python build/strategy_trim.py --plan plan.csv --proceeds-to QQQM
  4) 체결가 확정 후     python build/strategy_trim.py --plan plan.csv --px-file 체결가.csv

  계획서 없이 간단히:
      --target 0.05          모든 전략 종목을 각 0.05% 로
      --target-total 0.5     합계 0.5% 를 종목 수로 균등 배분
      --only MU,AMD          그 종목만 대상
"""
import argparse
import csv as _csv
import io
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import portfolio_fund as P    # noqa: E402


def collect(fund):
    """render_fund 앞부분과 같은 방식으로 한 펀드의 상태를 뽑는다."""
    path, nav, fx, hold = P.load_xlsm()
    if fund not in hold:
        raise SystemExit("해외 시트에 펀드 %s 가 없다 (있는 것: %s)"
                         % (fund, ", ".join(sorted(hold))))
    asof = max(hold[fund])
    rows = hold[fund][asof]
    nav_d = max(nav[fund])
    nav_v, _base = nav[fund][nav_d]
    _fxd, fx_hold = P.last_leq(fx, asof)

    held, etf = {}, {}
    for r in rows:
        if r["asset"] == "1":
            h = held.setdefault(r["ticker"], {"qty": 0.0, "px": r["px"], "name": r["name"]})
            h["qty"] += r["qty"]
        elif r["asset"] == "3":
            e = etf.setdefault(r["ticker"], {"qty": 0.0, "px": r["px"],
                                             "name": r["name"], "val": 0.0})
            e["qty"] += r["qty"]
            e["val"] += r["val_krw"]

    asof_by_fund = {f: max(hold[f]) for f, _i, _s, _l in P.FUNDS if f in hold}
    all_tk = {r["ticker"] for f in asof_by_fund
              for r in hold[f][asof_by_fund[f]] if r["asset"] == "1" and r["ticker"]}
    cons, seed = P.load_db(asof_by_fund, all_tk)
    P.load_splits()
    uni = set(all_tk) | {t["ticker"] for t in seed}
    for _d, _cmap in cons.values():
        uni |= set(_cmap)
    P.load_web(uni)

    # 🚨 원장은 펀드가 아니라 «지수»로 갈린다(FUNDS 두 번째 칸) — main() 과 같은 기준.
    idx = dict((f, i) for f, i, _s, _l in P.FUNDS)[fund]
    strat_q = {}
    for t in seed:
        if t["index"] != idx:
            continue
        f = P.split_factor(t["ticker"], t["dt"])
        q = t["qty"] * f if f != 1.0 else t["qty"]
        strat_q[t["ticker"]] = strat_q.get(t["ticker"], 0.0) + q

    sleeve = sum(r["val_krw"] for r in rows if r["asset"] == "1")
    return dict(path=path, asof=asof, nav_d=nav_d, nav=nav_v, fx=fx_hold,
                held=held, etf=etf, strat_q=strat_q, sleeve=sleeve)


def positions(st, only=None):
    """전략 순수량이 있는 종목(비중 내림차순)."""
    out = []
    for t, q in st["strat_q"].items():
        if abs(q) < 1e-9:
            continue
        h = st["held"].get(t)
        if not h or not h["px"]:
            print("  ⚠ %s — 보유 원장에 없거나 종가가 없다. 건너뜀." % t)
            continue
        lab = P.lab_tk(t)
        if only and lab.upper() not in only and t.upper() not in only:
            continue
        out.append(dict(t=t, lab=lab, qty=q, px=h["px"],
                        w=q * h["px"] * st["fx"] / st["nav"]))
    out.sort(key=lambda r: -r["w"])
    return out


def read_csv_map(path, key_col=0, val_col=1):
    """티커 -> 숫자. 머리글·빈 줄은 조용히 건너뛴다."""
    out = {}
    with io.open(path, encoding="cp949", errors="replace", newline="") as f:
        for row in _csv.reader(f):
            if len(row) <= max(key_col, val_col):
                continue
            k = (row[key_col] or "").strip().upper()
            try:
                out[k] = float((row[val_col] or "").replace(",", "").strip())
            except ValueError:
                continue
    if not out:
        raise SystemExit("%s 에서 «티커,숫자» 를 못 읽었다" % path)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fund", default="2Z30")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--make-plan", metavar="CSV", default="")
    ap.add_argument("--plan", metavar="CSV", default="")
    ap.add_argument("--target", type=float, default=None, help="종목당 목표비중(%%)")
    ap.add_argument("--target-total", type=float, default=None, help="합계 목표(%%) 균등배분")
    ap.add_argument("--only", default="")
    ap.add_argument("--px-file", metavar="CSV", default="",
                    help="실제 체결가로 덮어쓰기 (티커,가격USD)")
    ap.add_argument("--proceeds-to", metavar="ETF", default="",
                    help="매도대금으로 살 ETF 티커 (예: QQQM)")
    ap.add_argument("--csv", default="", help="주문지 저장")
    a = ap.parse_args()

    st = collect(a.fund)
    nav, fxh = st["nav"], st["fx"]
    print("원천 %s · 펀드 %s · 보유기준일 %s · NAV %s원 · 환율 %.2f"
          % (os.path.basename(st["path"]), a.fund, st["asof"], format(nav, ",.0f"), fxh))

    only = {x.strip().upper() for x in a.only.split(",") if x.strip()}
    cur = positions(st, only)
    if not cur:
        raise SystemExit("전략 순수량이 있는 종목이 없다 — 원장을 확인할 것")

    if a.px_file:
        ov = read_csv_map(a.px_file)
        n = 0
        for r in cur:
            if r["lab"].upper() in ov:
                r["px"] = ov[r["lab"].upper()]
                r["w"] = r["qty"] * r["px"] * fxh / nav
                n += 1
        cur.sort(key=lambda r: -r["w"])
        print("체결가 덮어쓰기: %d/%d 종목 (%s)"
              % (n, len(cur), os.path.basename(a.px_file)))

    tot_w = sum(r["w"] for r in cur)
    print("전략 %d종 · 합계 %.4f%%\n" % (len(cur), tot_w * 100))

    if a.make_plan:
        with io.open(a.make_plan, "w", encoding="cp949", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["티커", "현재수량", "종가USD", "현재비중%", "목표비중%"])
            for r in cur:
                w.writerow([r["lab"], int(r["qty"]), round(r["px"], 4),
                            round(r["w"] * 100, 4), round(r["w"] * 100, 4)])
        print("계획서 만들었다: %s" % a.make_plan)
        print("  엑셀에서 «목표비중%%» 열만 고친 뒤  --plan %s  로 부르면 된다."
              % os.path.basename(a.make_plan))
        return 0

    if a.list:
        print("%-7s %10s %10s %9s" % ("티커", "전략수량", "종가USD", "비중%"))
        for r in cur:
            print("%-7s %10s %10.2f %8.4f"
                  % (r["lab"], format(r["qty"], ",.0f"), r["px"], r["w"] * 100))
        return 0

    if a.plan:
        tgt = {k: v / 100.0 for k, v in read_csv_map(a.plan, 0, 4).items()}
        missing = [r["lab"] for r in cur if r["lab"].upper() not in tgt]
        if missing:
            raise SystemExit("계획서에 목표가 없는 종목: %s" % ", ".join(missing))
        src = "계획서 %s" % os.path.basename(a.plan)
    elif a.target is not None:
        tgt = {r["lab"].upper(): a.target / 100.0 for r in cur}
        src = "일괄 %.4f%%" % a.target
    elif a.target_total is not None:
        e = (a.target_total / 100.0) / len(cur)
        tgt = {r["lab"].upper(): e for r in cur}
        src = "합계 %.4f%% 균등배분(%d종 x %.4f%%)" % (a.target_total, len(cur), e * 100)
    else:
        raise SystemExit("--target / --target-total / --plan 중 하나를 줄 것 "
                         "(현황만 보려면 --list)")
    print("목표: %s\n" % src)

    out, s_usd, s_krw = [], 0.0, 0.0
    for r in cur:
        unit = r["px"] * fxh
        want = tgt[r["lab"].upper()] * nav / unit
        q_new = int(round(want))
        if want < r["qty"]:                       # 매도는 보유 전략수량을 넘을 수 없다
            q_new = max(0, min(q_new, int(r["qty"])))
        order = q_new - r["qty"]
        out.append(dict(r, tgt=q_new, order=order, w_after=q_new * unit / nav,
                        usd=order * r["px"], krw=order * unit))
        s_usd += order * r["px"]
        s_krw += order * unit

    print("%-7s %9s %9s %9s %8s %8s %13s %16s"
          % ("티커", "현재수량", "목표수량", "주문", "현재%", "목표%", "금액USD", "금액KRW"))
    for r in out:
        print("%-7s %9s %9s %+9s %7.4f %7.4f %13s %16s"
              % (r["lab"], format(r["qty"], ",.0f"), format(r["tgt"], ",.0f"),
                 format(r["order"], ",.0f"), r["w"] * 100, r["w_after"] * 100,
                 format(r["usd"], ",.0f"), format(r["krw"], ",.0f")))
    w_af = sum(r["w_after"] for r in out)
    print("%-7s %9s %9s %+9s %7.4f %7.4f %13s %16s"
          % ("합계", "", "", format(sum(r["order"] for r in out), ",.0f"),
             tot_w * 100, w_af * 100, format(s_usd, ",.0f"), format(s_krw, ",.0f")))
    print("\n순 %s: %s원 (USD %s)"
          % ("매도대금" if s_krw < 0 else "매수금액",
             format(abs(s_krw), ",.0f"), format(abs(s_usd), ",.0f")))

    etf_row = None
    if a.proceeds_to:
        key = a.proceeds_to.strip().upper()
        cand = [(t, e) for t, e in st["etf"].items() if P.lab_tk(t).upper() == key]
        if not cand:
            raise SystemExit("보유 ETF 에 %s 가 없다 (있는 것: %s)"
                             % (key, ", ".join(sorted(P.lab_tk(t) for t in st["etf"]))))
        t, e = cand[0]
        unit = e["px"] * fxh
        n_buy = int(-s_krw // unit)               # 대금 안에서만 산다(내림)
        etf_row = dict(lab=P.lab_tk(t), px=e["px"], qty=e["qty"], n=n_buy,
                       krw=n_buy * unit, usd=n_buy * e["px"],
                       w0=e["val"] / nav, w1=(e["val"] + n_buy * unit) / nav)
        print("\n[매도대금 -> ETF] %s @ %.4f USD (%s원/주)"
              % (etf_row["lab"], etf_row["px"], format(unit, ",.0f")))
        print("  매수 %s주 · %s원 (USD %s) · 잔여현금 %s원"
              % (format(n_buy, ",.0f"), format(etf_row["krw"], ",.0f"),
                 format(etf_row["usd"], ",.0f"),
                 format(-s_krw - etf_row["krw"], ",.0f")))
        print("  %s 비중 %.4f%% -> %.4f%% (보유 %s주 -> %s주)"
              % (etf_row["lab"], etf_row["w0"] * 100, etf_row["w1"] * 100,
                 format(etf_row["qty"], ",.0f"), format(etf_row["qty"] + n_buy, ",.0f")))
        print("  ⚠ 개별주식 슬리브 %.2f%% -> %.2f%%. 표의 지수비중은 슬리브 크기로"
              % (st["sleeve"] / nav * 100, (st["sleeve"] + s_krw) / nav * 100))
        print("     환산되므로 «차이(%p)» 열이 그 10종 말고도 전부 조금씩 움직인다.")

    if a.csv:
        with io.open(a.csv, "w", encoding="cp949", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["펀드", a.fund, "보유기준일", str(st["asof"]),
                        "NAV", round(nav), "환율", round(fxh, 2), "목표", src])
            w.writerow(["티커", "매매구분", "주문수량", "종가USD",
                        "금액USD", "금액KRW", "현재비중%", "목표비중%"])
            for r in out:
                if r["order"] == 0:
                    continue
                w.writerow([r["lab"], "S" if r["order"] < 0 else "B", abs(r["order"]),
                            round(r["px"], 4), round(abs(r["usd"]), 2),
                            round(abs(r["krw"])), round(r["w"] * 100, 4),
                            round(r["w_after"] * 100, 4)])
            if etf_row and etf_row["n"]:
                w.writerow([etf_row["lab"], "B", etf_row["n"], round(etf_row["px"], 4),
                            round(etf_row["usd"], 2), round(etf_row["krw"]),
                            round(etf_row["w0"] * 100, 4), round(etf_row["w1"] * 100, 4)])
        print("\n주문지 저장: %s" % a.csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
