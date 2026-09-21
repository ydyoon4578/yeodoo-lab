# -*- coding: utf-8 -*-
"""build/month_map.py — 달마다의 시장 상황과 그달 잘 간 전략 → data/_month_map.json

🚨 **서술이다. 판정도 규칙도 아니다.**
   이 랩은 국면 조건부 규칙을 12번 시도해 11번 기각했고(원장), 시장상태 삼분위 검정은
   1592칸 중 FDR 10% 를 넘은 것이 **3칸**뿐이었다(strategy_diag.fdr).

🚨 그리고 여기 나오는 관계는 전부 **동시대(contemporaneous)** 다 — «그달 급락이었고
   그달 VXZ 가 잘 갔다» 이지 «급락할 것을 알았다» 가 아니다. 롱볼이 급락에 강한 것은
   정의상 그렇고, 어려운 것은 **급락을 미리 아는 것**이다. 그 어려움이 지속성 수치로
   나온다 — 이달 순위와 다음 달 순위의 상관이 **+0.05** 다(사실상 0).
   그러니 이 표의 쓰임은 «다음 달 뭘 살까» 가 아니라
     · 내가 든 전략이 **어떤 달에 다칠지** 미리 아는 것(위험 이해)
     · 두 전략이 **같은 달에 같이 다치는지** 보는 것(분산이 되나)
   까지다.

⚠ 여기서 백테스트를 다시 돌리지 않는다. 전부 커밋된 산출물에서 온다 —
   data/strategy_charts.json  규칙별 월 수익 r 과 그 규칙의 대조군 b
   data/strategy_diag.json    시장 상태 8변수(월말)
   data/strategy_index.json   이름·성격·주기

⚠ 초과 = r − b 이고 b 는 **그 규칙의 대조군**이다. 규칙마다 대조군이 다르므로
   (S&P 184 · 같은 풀 동일가중 10 · 현금 6 · NDX 1) 한 달 안에서 줄 세울 때
   그 사실을 같이 적는다.

  python build/month_map.py
"""
from __future__ import annotations
import io, json, os, statistics as st, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_month_map.json")
TOPN = 5


def J(n):
    return json.load(io.open(os.path.join(DATA, n), encoding="utf-8"))


def terc(vals):
    """삼분위 경계. 결측은 빼고 센다."""
    v = sorted(x for x in vals if x is not None)
    if len(v) < 9:
        return None
    return v[len(v) // 3], v[len(v) * 2 // 3]


def band(v, cut):
    if v is None or cut is None:
        return "?"
    return "하" if v < cut[0] else ("중" if v < cut[1] else "상")


def label(spx, vol, disp, rate, brd):
    """그달을 한 줄로. **분류가 아니라 요약**이다 — 경계값은 표본 삼분위다."""
    d = ("급락" if spx is not None and spx <= -5 else
         "하락" if spx is not None and spx < 0 else
         "급등" if spx is not None and spx >= 5 else "상승")
    return "%s · 변동성%s · 분산%s · 금리%s · 폭%s" % (d, vol, disp, rate, brd)


def main() -> int:
    C, D, I = J("strategy_charts.json"), J("strategy_diag.json"), J("strategy_index.json")
    ch = C["charts"]
    IDX = C.get("idx_monthly") or {}
    SP, ND = IDX.get("S&P 500") or {}, IDX.get("NASDAQ 100") or {}
    META = {x["sid"]: x for x in I["items"]}
    STATE = D["state"]

    # 규칙별 월 초과 — r − b (그 규칙의 대조군 대비)
    ex = {}
    for sid, c in ch.items():
        if sid not in META:
            continue                       # 목록에서 빠진 것은 안 센다
        for z in (c.get("monthly") or []):
            r, b, m = z.get("r"), z.get("b"), z.get("m")
            if m and isinstance(r, (int, float)) and isinstance(b, (int, float)):
                ex.setdefault(m, {})[sid] = r - b

    months = sorted(m for m in ex if m in STATE and m in SP)
    if not months:
        raise SystemExit("겹치는 달이 없다 — 먼저 strategy_charts.py · strategy_diag.py")

    # 상태 변수 삼분위는 **이 구간 전체**로 한 번만 낸다(달마다 다시 자르면 라벨이 흔들린다)
    cuts = {k: terc([STATE[m].get(k) for m in months])
            for k in ("vol1", "disp", "rate12", "breadth12", "conc", "dconc12")}

    rows = []
    for m in months:
        s = STATE[m]
        e = ex[m]
        if len(e) < 30:
            continue
        srt = sorted(e.items(), key=lambda z: -z[1])
        rows.append({
            "m": m, "spx": SP.get(m), "ndx": ND.get(m),
            "vol": s.get("vol1"), "disp": s.get("disp"), "rate12": s.get("rate12"),
            "breadth12": s.get("breadth12"), "conc": s.get("conc"), "dconc12": s.get("dconc12"),
            "band": {k: band(s.get(k), cuts[k]) for k in cuts},
            "label": label(SP.get(m), band(s.get("vol1"), cuts["vol1"]),
                           band(s.get("disp"), cuts["disp"]),
                           band(s.get("rate12"), cuts["rate12"]),
                           band(s.get("breadth12"), cuts["breadth12"])),
            "n": len(e),
            "top": [{"sid": k, "name": META[k]["name"], "ex": round(v, 2)} for k, v in srt[:TOPN]],
            "bot": [{"sid": k, "name": META[k]["name"], "ex": round(v, 2)} for k, v in srt[-3:]],
            "med": round(st.median(e.values()), 2),
        })

    # ── 🚨 지속성 — 이 표가 쓸모 있으려면 이게 0 이 아니어야 한다 ───────────
    hit, tot, rho = 0, 0, []
    for i in range(len(rows) - 1):
        a = {z["sid"] for z in rows[i]["top"]}
        nxt = ex[rows[i + 1]["m"]]
        nb = {z["sid"] for z in rows[i + 1]["top"]}
        hit += len(a & nb); tot += len(a)
        common = [k for k in ex[rows[i]["m"]] if k in nxt]
        if len(common) > 30:
            xa = [ex[rows[i]["m"]][k] for k in common]
            xb = [nxt[k] for k in common]
            ra = sorted(range(len(xa)), key=lambda j: xa[j])
            rb = sorted(range(len(xb)), key=lambda j: xb[j])
            Ra, Rb = [0] * len(xa), [0] * len(xb)
            for q, j in enumerate(ra):
                Ra[j] = q
            for q, j in enumerate(rb):
                Rb[j] = q
            ma, mb = st.mean(Ra), st.mean(Rb)
            cov = sum((Ra[j] - ma) * (Rb[j] - mb) for j in range(len(xa)))
            den = (sum((v - ma) ** 2 for v in Ra) * sum((v - mb) ** 2 for v in Rb)) ** .5
            if den:
                rho.append(cov / den)
    persist = {"top%d_carry_pct" % TOPN: hit / tot * 100 if tot else None,
               "random_pct": TOPN / st.mean([r["n"] for r in rows]) * 100,
               "rank_rho_median": st.median(rho) if rho else None,
               "rank_rho_mean": st.mean(rho) if rho else None}

    # ── 상황별 — **축 하나씩** 본다 ──────────────────────────────────────
    # 🚨 다섯 축을 곱하면 칸이 30개 넘고 한 칸이 4~6개월이 된다. 그 안의 «1등» 은
    #   거의 전부 잡음이다(실제로 처음 그렇게 짰다가 재현율 17~50% 로 흔들렸다).
    #   축을 하나씩 보면 한 칸이 40개월 안팎이라 셀 수 있는 수가 된다.
    # ⚠ 그래도 **검정이 아니다.** FDR 을 안 걸었고 다중검정 보정도 없다.
    AXES = [("dir", "시장 방향", lambda r: ("급락" if r["spx"] <= -5 else "하락" if r["spx"] < 0
                                          else "급등" if r["spx"] >= 5 else "상승")),
            ("vol1", "변동성", lambda r: r["band"]["vol1"]),
            ("disp", "종목 분산", lambda r: r["band"]["disp"]),
            ("rate12", "금리 변화", lambda r: r["band"]["rate12"]),
            ("breadth12", "시장 폭", lambda r: r["band"]["breadth12"]),
            ("dconc12", "집중 변화", lambda r: r["band"]["dconc12"])]
    kinds = []
    for key, ko, fn in AXES:
        for lev in ("급락", "하락", "상승", "급등", "하", "중", "상"):
            rs = [r for r in rows if fn(r) == lev]
            if len(rs) < 12:                    # 12개월 못 되면 세지 않는다
                continue
            cnt = {}
            for r in rs:
                for z in r["top"]:
                    cnt[z["sid"]] = cnt.get(z["sid"], 0) + 1
            # 그 칸의 달 수로 나눈 «상위 진입률». 전 구간 진입률과 견줘 «더» 나오는지 본다.
            base = {}
            for r in rows:
                for z in r["top"]:
                    base[z["sid"]] = base.get(z["sid"], 0) + 1
            top = sorted(cnt.items(),
                         key=lambda z: -(z[1] / len(rs) - base.get(z[0], 0) / len(rows)))[:6]
            kinds.append({
                "axis": key, "axis_ko": ko, "level": lev, "n_months": len(rs),
                "spx_mean": round(st.mean([r["spx"] for r in rs]), 2),
                "med_ex": round(st.median([r["med"] for r in rs]), 2),
                "recur": [{"sid": k, "name": META[k]["name"], "hit": v,
                           "in_pct": round(v / len(rs) * 100, 1),
                           "all_pct": round(base.get(k, 0) / len(rows) * 100, 1),
                           "lift": round(v / len(rs) * 100 - base.get(k, 0) / len(rows) * 100, 1)}
                          for k, v in top]})

    doc = {"note": "달마다의 시장 상황과 그달 잘 간 전략. **서술이지 판정이 아니다.** "
                   "이 랩은 국면 조건부 규칙을 12번 시도해 11번 기각했고 시장상태 삼분위는 "
                   "1592칸 중 3칸만 FDR 10% 를 넘었다.",
           "span": [rows[0]["m"], rows[-1]["m"]], "n_months": len(rows),
           "n_rules_median": int(st.median([r["n"] for r in rows])),
           "topn": TOPN, "cuts": {k: v for k, v in cuts.items()},
           "persistence": persist, "kinds": kinds, "months": rows}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    print("달 %d개(%s~%s) · 규칙 중앙 %d종" % (len(rows), rows[0]["m"], rows[-1]["m"],
                                          doc["n_rules_median"]))
    print("\n🚨 지속성 — 이 표를 규칙으로 쓸 수 있나")
    print("  이달 상위%d 가 다음 달에도 상위%d 에 남는 비율  %.1f%%  (무작위면 %.1f%%)"
          % (TOPN, TOPN, persist["top%d_carry_pct" % TOPN], persist["random_pct"]))
    print("  이달 순위 ↔ 다음 달 순위 상관 중앙 %+.3f · 평균 %+.3f"
          % (persist["rank_rho_median"], persist["rank_rho_mean"]))

    print("\n══ 상황별 — 그 칸에서 «전 구간보다 더» 자주 상위에 온 규칙 ══")
    print("   (진입률 = 그 칸 달 중 상위%d 에 든 비율 · 리프트 = 전 구간 진입률과의 차)" % TOPN)
    for k in kinds:
        print("\n▸ %s = %s   %d개월 · S&P 평균 %+.2f%% · 규칙 중앙초과 %+.2f%%"
              % (k["axis_ko"], k["level"], k["n_months"], k["spx_mean"], k["med_ex"]))
        for z in k["recur"][:4]:
            print("    %-38s 진입 %4.1f%%  전구간 %4.1f%%  리프트 %+5.1f%%p"
                  % (z["name"][:38], z["in_pct"], z["all_pct"], z["lift"]))

    print("\n══ 최근 12개월 ══")
    for r in rows[-12:]:
        print("  %s  S&P %+6.2f  NDX %+6.2f  %-34s  중앙 %+5.2f"
              % (r["m"], r["spx"], r["ndx"], r["label"][:34], r["med"]))
        print("        상위: %s" % " · ".join("%s %+.1f" % (z["name"][:22], z["ex"])
                                            for z in r["top"][:3]))
    print("\n→ %s" % os.path.basename(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
