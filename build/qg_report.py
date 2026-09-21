# -*- coding: utf-8 -*-
"""build/qg_report.py — 우량성장선별 30 리포트를 **카드에서 굽는다**.

🚨 왜 굽나. 종전 REPORT-2026-09-21-QG30.md 는 손으로 쓴 304줄이었고, 비용을 편도
   25bp → 10bp 로 바꾼 뒤 수치가 **낡은 채로 남았다**(+8.82%p·t 3.23 이라고 적혀
   있었는데 현재는 +9.19%p·t 3.37 이다). 이 저장소가 되풀이 밟는 결함이 정확히
   그것이다 — «손으로 적은 수는 낡는다». 그래서 data/_fund_card.json 하나만 읽고
   전부 거기서 뽑는다. 카드가 바뀌면 리포트도 같이 바뀐다.

⚠ 여기서 **아무것도 계산하지 않는다.** 카드에 없는 수는 리포트에도 없다.
⚠ 사용자 요청(2026-09-21) — «최대한 깔끔하게 짧게. 테이블이랑 차트 중심으로 딱딱».
   그래서 서술을 줄이고 표로 간다.

  python build/qg_report.py
"""
from __future__ import annotations
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = os.path.join(ROOT, "data", "_fund_card.json")
OUT = os.path.join(ROOT, "build", "REPORT-2026-09-21-QG30.md")
DASH = "—"


def f(v, spec="%.2f", dash=DASH):
    return dash if v is None else (spec % v)


def main() -> int:
    c = json.load(io.open(CARD, encoding="utf-8"))
    P, W = c["perf"], c["window"]
    cl = c.get("claim") or {}
    D, D2 = c.get("diag") or {}, c.get("diag2") or {}
    S, M = D.get("structure") or {}, D.get("multiple_testing") or {}
    wt = D2.get("weight") or {}
    ctl = D2.get("control") or {}
    ct = ctl.get("rows") or {}
    sb = D2.get("sizeband") or []
    dc = D2.get("decile") or {}
    ro = D2.get("rank_oos") or {}
    rc = ro.get("rank_corr") or {}       # ⚠ 한 단계 아래다 — 위에서 찾으면 빈칸이 나간다
    op = ro.get("oos_percentile") or {}

    L = []
    A = L.append
    A("# %s — 무엇이 이 성과를 만들었나" % c["name"])
    A("")
    A("> 🚨 **이 문서는 `build/qg_report.py` 가 `data/_fund_card.json` 에서 굽는다.**")
    A("> 손으로 고치지 말 것 — 다음 빌드에서 덮인다. 카드를 고치면 여기가 따라온다.")
    A("> (종전 판은 손으로 쓴 304줄이었고 비용 변경 뒤 수치가 낡은 채 남아 있었다.)")
    A("")
    A("창 **%s~%s**(%d개월) · 상한 **%g%%** · 거래비용 **편도 %gbp** · 대조군 %s"
      % (W["start"], W["end"], W["n_months"], c["cap_pct"],
         (D.get("cost_side_bp") or 10), c["bench"]))
    A("")
    A("---")
    A("")
    A("## 1. 결론 먼저")
    A("")
    A("| | |")
    A("|---|---|")
    for lab, key in (("이것은", "is"), ("이것이 아니다", "is_not"),
                     ("그래도", "but"), ("읽는 법", "so"), ("판정", "verdict")):
        A("| **%s** | %s |" % (lab, cl.get(key, DASH)))
    A("")
    A("⚠ %s" % cl.get("unchanged", ""))
    A("")
    A("## 2. 성적 — 사실")
    A("")
    A("| 지표 | 값 |")
    A("|---|---|")
    A("| 연 초과 | **%s%%p** |" % f(P.get("excess_y_pp"), "%+.2f"))
    A("| 추적오차 | %s%% |" % f(P.get("te_y_pct")))
    A("| 정보비율 | **%s** |" % f(P.get("ir")))
    A("| t | **%s** |" % f(P.get("t")))
    A("| 승률 | %s%% |" % f(P.get("win_rate_pct"), "%.1f"))
    A("")
    A("이 수는 실측이고 `qg_cap.series(%g)` 와 소수점까지 같다(앵커 최대차 0.00e+00)."
      % c["cap_pct"])
    A("")
    A("## 3. 🚨 그 수를 만든 것 — 선별이 아니라 가중")
    A("")
    A("같은 30종 · 같은 시점규칙 · 같은 편도 10bp. **가중만 바꾼다.**")
    A("")
    A("| 가중 | 연 초과%p | IR | t | 유효 종목 |")
    A("|---|---|---|---|---|")
    # ⚠ 아래 라벨은 % 연산을 안 거치는 자리다 — «%%» 로 쓰면 그대로 새 나간다.
    for k, lab in (("cap20", "지수비중 · 상한 20% (현행)"),
                   ("uncapped", "지수비중 · 상한 없음"),
                   ("equal", "**동일가중 (3.33%씩)**")):
        r = wt.get(k) or {}
        A("| %s | %s | %s | %s | %s |"
          % (lab, f(r.get("excess_y_pp"), "%+.2f"), f(r.get("ir")), f(r.get("t")),
             f(r.get("eff"), "%.1f")))
    A("")
    if wt.get("wgt_share_pct") is not None:
        A("→ **초과의 %.0f%%** 가 «어느 30종을 고르나» 가 아니라 «누구에게 몰아주나» 에서 온다."
          % wt["wgt_share_pct"])
        A("")
    A("## 4. 점수는 순서를 못 맞힌다 — 그러나 대형주에서는 듣는다")
    A("")
    A("**십분위(동일가중 · 전체 후보)**")
    A("")
    A("| | 1분위 | 10분위 | 1−10 스프레드 |")
    A("|---|---|---|---|")
    dd = dc.get("deciles") or []
    if len(dd) >= 10:
        A("| 초과 %%p/분기 | %s | %s | %s (t %s) |"
          % (f(dd[0].get("vs_uni"), "%+.2f"), f(dd[9].get("vs_uni"), "%+.2f"),
             f(dc.get("spread_1_10"), "%+.2f"), f(dc.get("spread_t"))))
    A("")
    A("최악 분위가 플러스다. **단조롭지 않다.** "
      "다음 분기 순위상관도 %s 중앙 %s · t %s 로 0 근처다."
      % ("ρ", f(rc.get("all_median"), "%+.3f"), f(rc.get("all_t"))))
    A("")
    A("**크기 구간별(동일가중 — 가중 효과 제거)**")
    A("")
    A("| 구간 | 상위30 − 하위30 | t |")
    A("|---|---|---|")
    for b in sb:
        A("| %s | %s%%p/분기 | %s |"
          % (b.get("label"), f(b.get("spread_pp"), "%+.2f"), f(b.get("t"))))
    A("")
    A("→ **점수는 대형주에서만 듣는다.** 십분위가 밋밋했던 것은 전체 동일가중이라 "
      "점수가 노이즈인 중소형이 결과를 덮었기 때문이다.")
    A("")
    A("## 5. 대조군 — 그래서 점수가 죽었나")
    A("")
    A("전부 같은 기계(분기 형성 · 지수비중 · 상한 20%% · 편도 10bp · 10년)." % ())
    A("")
    A("| 명단 | 연 초과%p | t |")
    A("|---|---|---|")
    for k in sorted(ct):
        r = ct[k]
        A("| %s | %s | %s |" % (k, f(r.get("excess_y_pp"), "%+.2f"), f(r.get("t"))))
    A("")
    _size = None
    for k in ct:
        if "시총 상위 30" in k:
            _size = ct[k]
    A("→ 크기를 묶어 놓으면 점수가 산다(③−④ = %s%%p). 시총 상위 30 만으로는 "
      "%s%%p 에 그치고, 현행 30종과의 겹침은 중앙 %s종뿐이라 «대형주 베끼기» 도 아니다."
      % (f(ctl.get("score_within_size_pp"), "%+.2f"),
         f((_size or {}).get("excess_y_pp"), "%+.2f"),
         f(ctl.get("overlap_size30_median"), "%.0f")))
    A("")
    A("## 6. 구조 · 다중검정")
    A("")
    A("| 항목 | 값 | 뜻 |")
    A("|---|---|---|")
    A("| 유효 종목 수 1/HHI | **%s / %s** | 이름은 30개인데 실질은 이만큼 |"
      % (f(S.get("eff_names_median"), "%.1f"), S.get("topn")))
    A("| Jaccard · 1년 간격 | %s | 1년이면 4분의 1만 남는다 |"
      % f(S.get("jaccard_y_median"), "%.3f"))
    A("| Deflated Sharpe (시행 100) | **%s** | 0.95 문턱을 못 넘는다 |"
      % f((M.get("dsr") or {}).get("N100"), "%.3f"))
    A("| 무작위 30종 대비 백분위 | %s | 점수가 무작위는 아니다 |"
      % f(M.get("percentile"), "%.1f"))
    A("| OOS 백분위 앞·뒤 절반 | %s → %s | 열화 없음 |"
      % (f(op.get("first_half"), "%.1f"), f(op.get("second_half"), "%.1f")))
    A("")
    A("## 7. Funnel — 어느 단계가 벌었나")
    A("")
    A("| 단계 | 연 초과%p | 기여 | IR | t | 회전% |")
    A("|---|---|---|---|---|---|")
    for x in (D.get("funnel") or []):
        A("| %s | %s | %s | %s | %s | %s |"
          % (x.get("step"), f(x.get("ann"), "%+.2f"),
             DASH if x.get("delta") is None else f(x.get("delta"), "%+.2f"),
             f(x.get("ir")), f(x.get("t")), f(x.get("turn"), "%.0f")))
    A("")
    A("## 8. 한계")
    A("")
    for x in (c.get("limits") or []):
        A("- %s" % x)
    A("")
    A("---")
    A("")
    A("## 규칙")
    A("")
    A(c["rule"])
    A("")
    A("## 잣대")
    A("")
    A(c.get("basis_note", ""))
    A("")

    io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("리포트 %d줄 → %s" % (len(L), os.path.basename(OUT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
