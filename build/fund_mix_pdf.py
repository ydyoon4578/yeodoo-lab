# -*- coding: utf-8 -*-
"""build/fund_mix_pdf.py — 펀드 적용 리포트(우량성장선별 30 양식) → 저장소 밖 C:/Project/fund_reports/*.pdf

자료는 data/_fund_mix.json 하나뿐이다(여기서 아무것도 새로 계산하지 않는다 — qg_report 규약).
HTML 을 짓고 이 PC 의 Chrome 헤드리스로 PDF 를 찍는다. 🚨 결과 PDF 는 «내부용» 이라 저장소에 넣지 않는다.

  python build/fund_mix_pdf.py
"""
from __future__ import annotations
import html, io, json, os, subprocess, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "_fund_mix.json")
OUTDIR = os.environ.get("FUND_REPORT_DIR", r"C:\Project\fund_reports")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DATE = "2026-09-24"

META = {
 "E": {"title": "S&P500 기대성장(Eg) 상위 30", "file": "EG30",
       "goal": "S&P500 인덱스 펀드 NAV의 10%를 기대투자성장(Eg) 상위 30개 회사 바스켓으로 바꿔 S&P500 PR을 넘는다",
       "select": "다음 해 투자증가율 예측값(Eg: 시장가치÷자산 · 현금 기준 영업이익÷자산 · ROE 변화에 과거 평균 회귀계수를 곱해 더함) 상위 30개 회사",
       "weight": "바스켓 안은 시가총액 비례 · 한 회사 최대 20% (넘친 몫은 나머지에 비례 재배분)",
       "reb": "바스켓은 분기(3·6·9·12월 말) 교체 → 다음 3개월 보유 · 바스켓 비중은 매월 말 NAV 10%로 맞춤",
       "lab": "보류(PREREG-2026-09-23-EG) — 랩 대형주에서 고Eg − 저Eg 월 +0.67%(t 2.44)로 섰지만 절반쯤은 대형 성장주 베팅. 지수 강화 틀 IR +0.46(8년 t 1.30).",
       "steps": [("유니버스", "그 월말 S&P500 ∪ NASDAQ100 구성종목(편출 종목 포함 · 시점정확)", "중앙 약 480개"),
                 ("Eg", "그달 예측치 — 재무는 분기말 90일 뒤부터(미래 정보 차단)", "점수"),
                 ("선정", "Eg 상위 30개 회사 · 같은 회사의 두 종목은 하나로", "30개")]},
 "M": {"title": "S&P500 12-1 모멘텀 상위 10", "file": "MOM10",
       "goal": "S&P500 인덱스 펀드 NAV의 10%를 12-1 모멘텀 상위 10개 종목 바스켓으로 바꿔 S&P500 PR을 넘는다",
       "select": "최근 252거래일 수익 − 최근 21거래일 수익 상위 10종목",
       "weight": "바스켓 안은 동일가중(각 10%)",
       "reb": "매월 말 교체 · 바스켓 비중은 매월 말 NAV 10%로 맞춤",
       "lab": "측정만(x-mom12) — 이 랩의 모멘텀 기준선. 주도주 급락을 피하는 신호(손절·템플릿·이익 필터·변동성 관리)는 모두 기각됐다 — 크기로 관리한다.",
       "steps": [("유니버스", "그 월말 S&P500 ∪ NASDAQ100 구성종목(편출 종목 포함 · 시점정확)", "중앙 약 480개"),
                 ("점수", "252거래일 수익 − 21거래일 수익(최근 한 달 반전을 뺀다)", "—"),
                 ("선정", "점수 상위 10종목", "10개")]},
 "B": {"title": "S&P500 B/M 금리 국면 로테이션", "file": "BMROT",
       "goal": "S&P500 인덱스 펀드 NAV의 10%를 금리 국면에 따라 가치·성장 비중을 바꾸는 바스켓으로 바꾼다",
       "select": "장부가/시가총액 중앙값으로 반분 — 높은 절반 가치, 낮은 절반 성장",
       "weight": "10년 TIPS 실질금리 3개월 변화 ≥ +0.20%p 가치 70/성장 30 · ≤ −0.20%p 30/70 · 그 사이 50/50 · 다리 안 동일가중",
       "reb": "매월 말 · 바스켓 비중은 매월 말 NAV 10%로 맞춤",
       "lab": "게시(PREREG-2026-09-03-BMROT, 측정만) — 단독으로는 섰지만 펀드 틀(대 S&P500 PR)에서는 초과가 거의 0.",
       "steps": [("유니버스", "그 월말 S&P500 ∪ NASDAQ100 구성종목 중 자기자본 > 0", "중앙 약 470개"),
                 ("B/M", "최근 분기 자기자본(90일 지연) ÷ 시가총액", "—"),
                 ("국면", "DFII10 월말 − 3개월 전 월말", "±0.20%p")]},
 "A": {"title": "S&P500 알파 개선 상위 10", "file": "DALPHA",
       "goal": "S&P500 인덱스 펀드 NAV의 10%를 CAPM 알파가 가장 많이 좋아진 10종목 바스켓으로 바꾼다",
       "select": "월간 CAPM 알파(12개월 창 · 시장 S&P500 PR · 무위험 T-bill)의 6개월 변화 상위 10종목",
       "weight": "바스켓 안은 동일가중",
       "reb": "매월 말 · 바스켓 비중은 매월 말 NAV 10%로 맞춤",
       "lab": "게시(PREREG-2026-09-22-PXSTAT, 측정만) — 펀드 틀에서는 IR 0.24 · 최근 3년 음수.",
       "steps": [("유니버스", "그 월말 S&P500 ∪ NASDAQ100 구성종목", "중앙 약 480개"),
                 ("알파", "최근 12개월 월 초과수익을 시장 초과수익에 회귀한 절편", "—"),
                 ("선정", "알파(t) − 알파(t−6개월) 상위 10", "10개")]},
 "C": {"title": "S&P500 조합 (B/M · Eg · 모멘텀)", "file": "MIX3",
       "goal": "S&P500 인덱스 펀드 NAV의 10%를 B/M 로테이션 · Eg 상위 30 · 모멘텀 상위 10에 1/3씩 나눠 담는다",
       "select": "세 바스켓의 규칙 그대로(각 전략 리포트 참조)",
       "weight": "바스켓 몫 10%를 세 전략에 1/3씩 · 매월 말 1/3로 되돌림",
       "reb": "구성 바스켓 각자의 주기(B·M 월말 · Eg 분기) · 세 몫은 매월 말 되돌림",
       "lab": "기각(PREREG-2026-09-24-FUNDMIX · F1) — 조합 IR 0.82 가 Eg 단독 0.93 보다 낮다. B/M 의 초과가 0 에 가까워 희석됐다.",
       "steps": []},
}
ORDER = ["E", "M", "C", "B", "A"]


def pct(v, d=2, sign=True):
    if v is None:
        return "—"
    return (("%+." if sign else "%.") + str(d) + "f%%") % v


def num(v, d=2):
    return "—" if v is None else ("%." + str(d) + "f") % v


def page_head(t, p):
    return '<div class="ph"><span>%s — 펀드전략</span><span>%s · 내부용 · - %d -</span></div>' % (html.escape(t), DATE, p)


def build(code, J):
    m, s = META[code], J["strategies"][code]
    A, T = s["all"], s["3y"]
    w = J["window"]
    h = []
    h.append(page_head(m["title"], 1))
    h.append("<h1>%s — 펀드전략</h1>" % html.escape(m["title"]))
    h.append('<p class="sub">작성 %s · 벤치마크 S&amp;P500 PR(가격지수) · 백테스트 %s ~ %s · 펀드 = S&amp;P500 90%% + 바스켓 10%% · 거래비용 편도 %.0fbp · NAV 1조 원 가정</p>'
             % (DATE, w[0], w[1], J["cost_bp"]))
    h.append("<h2>1. 성과 — S&amp;P500 PR 대비</h2><table><tr><th></th><th>전체 (%s ~ %s)</th><th>최근 3년 (%s ~ %s)</th></tr>" % (w[0], w[1], J["r3"][0], J["r3"][1]))
    for lab, k, fmt in (("연 초과수익", "ann_ex", lambda v: pct(v)), ("누적 초과수익", "cum_ex", lambda v: pct(v)),
                        ("트래킹에러", "te", lambda v: pct(v, sign=False)), ("정보비율 (IR)", "ir", num), ("t값", "t", num),
                        ("월 승률 (S&amp;P500 PR 대비)", "win", lambda v: pct(v, 1, False))):
        h.append("<tr><td>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (lab, fmt(A[k]), fmt(T[k])))
    h.append("</table><p class='note'>월 초과수익 = 펀드 − S&amp;P500 PR(거래비용 차감). 연 초과수익 = 월평균 × 12.</p>")
    h.append("<h3>연도별</h3><table><tr><th>연도</th><th>S&amp;P500 PR</th><th>펀드</th><th>초과</th><th>바스켓 단독</th></tr>")
    for y, v in s["yearly"].items():
        h.append("<tr><td>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n b'>%s</td><td class='n'>%s</td></tr>" % (y, pct(v["index"]), pct(v["fund"]), pct(v["ex"]), pct(v["basket"])))
    h.append("</table>")
    # 2쪽
    h.append('<div class="pb"></div>' + page_head(m["title"], 2))
    h.append("<h3>펀드와 S&amp;P500 PR</h3><table><tr><th></th><th>S&amp;P500 PR (전체)</th><th>펀드 (전체)</th><th>S&amp;P500 PR (최근 3년)</th><th>펀드 (최근 3년)</th><th>바스켓 단독 (전체)</th></tr>")
    for lab, k in (("CAGR", "cagr"), ("연변동성", "vol")):
        h.append("<tr><td>%s</td>%s</tr>" % (lab, "".join("<td class='n'>%s</td>" % pct(x[k], 2, k == "cagr") for x in (A["index"], A["fund"], T["index"], T["fund"], A["basket"]))))
    h.append("<tr><td>Sharpe</td>%s</tr>" % "".join("<td class='n'>%s</td>" % num(x["sharpe"]) for x in (A["index"], A["fund"], T["index"], T["fund"], A["basket"])))
    md = s["mdd"]
    h.append("<tr><td>MDD (일간)</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr></table>"
             % (pct(md["index_all"], 2, False), pct(md["fund_all"], 2, False), pct(md["index_3y"], 2, False), pct(md["fund_3y"], 2, False), pct(md["basket_all"], 2, False)))
    h.append("<h3>급등락 구간</h3><table><tr><th>구분</th><th>구간</th><th>기간</th><th>S&amp;P500 PR</th><th>펀드</th><th>초과</th><th>바스켓 단독</th><th>바스켓 초과</th></tr>")
    for e in s["episodes"]:
        h.append("<tr><td class='%s'>%s</td><td>%s</td><td>%s → %s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n b'>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>"
                 % ("dn" if e["kind"] == "급락" else "up", e["kind"], html.escape(e["name"]), e["a"][2:], e["z"][2:],
                    pct(e["index"], 1), pct(e["fund"], 1), pct(e["ex"], 2), pct(e["basket"], 1), pct(e["basket_ex"], 1)))
    for kind in ("급락", "급등"):
        es = [e for e in s["episodes"] if e["kind"] == kind]
        if es:
            av = lambda k: sum(e[k] for e in es) / len(es)
            h.append("<tr class='avg'><td>%s</td><td>%d구간 평균</td><td>펀드가 앞선 구간 %d/%d</td><td class='n'>%s</td><td class='n'>%s</td><td class='n b'>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>"
                     % (kind, len(es), sum(e["ex"] > 0 for e in es), len(es), pct(av("index"), 1), pct(av("fund"), 1), pct(av("ex"), 2), pct(av("basket"), 1), pct(av("basket_ex"), 1)))
    h.append("</table><p class='note'>시작일 종가 → 끝일 종가, 일간 가격. 초과 = 펀드 − S&amp;P500 PR. 바스켓 단독 = NAV 전부를 바스켓에 넣었을 때.</p>")
    # 3쪽
    h.append('<div class="pb"></div>' + page_head(m["title"], 3))
    h.append("<h2>2. 전략 요약</h2><table class='kv'>")
    rows = [("목표", m["goal"]), ("종목 선정", m["select"]), ("비중", m["weight"]), ("리밸런스", m["reb"]),
            ("투자 규모", "NAV의 10%% — S&amp;P500 보유를 종목마다 10%%씩 줄이고 그 돈으로 바스켓을 담는다 · 나머지 90%%는 지수 그대로 (바스켓 단독이면 연 초과 %s · IR %s)" % (pct(A["basket_ann_ex"]), num(A["basket_ir"]))),
            ("위험 조건", "공매도 · 파생 · 차입 없음" + (" · 바스켓 안 한 회사 최대 20% (NAV의 2%)" if code == "E" else "")),
            ("비용 · 기준", "편도 10bp · 벤치는 가격수익 — 바스켓 종가는 배당조정이라 배당만큼(연 약 1~2%p × 10%) 유리하다"),
            ("랩 판정", m["lab"])]
    for k, v in rows:
        h.append("<tr><th>%s</th><td>%s</td></tr>" % (k, v))
    h.append("</table><h2>3. 방법론</h2>")
    if m["steps"]:
        h.append("<h3>3-1. 종목 선정</h3><table><tr><th>단계</th><th>내용</th><th>값</th></tr>")
        for a, b, c in m["steps"]:
            h.append("<tr><td>%s</td><td>%s</td><td class='n'>%s</td></tr>" % (a, b, c))
        h.append("<tr><td>시점 규칙</td><td>그때 공개되지 않은 재무·명단은 쓰지 않는다 · 편출 종목의 가격을 포함한다(생존 편향 차단)</td><td class='n'>—</td></tr></table>")
    if s.get("holdings"):
        H = s["holdings"]
        h.append("<h3>3-2. 비중과 보유 — 바스켓 상위 %d (%s 형성 · 유효 종목 수 %s개)</h3><table><tr><th>회사</th><th>티커</th><th>바스켓 비중</th><th>NAV 비중</th></tr>"
                 % (min(10, len(H["top"])), H["sig"], num(H["eff_n"], 1)))
        for x in H["top"][:10]:
            h.append("<tr><td>%s</td><td>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (html.escape(x["name"]), x["t"], pct(x["w"], 1, False), pct(x["w"] * 0.1, 2, False)))
        h.append("</table><h3>3-3. 매매와 비용</h3><table class='kv'>")
        h.append("<tr><th>명단 교체</th><td>리밸런스마다 새로 들어오는 종목 중앙 %s개</td></tr>" % num(s.get("name_turnover_median"), 0))
        h.append("<tr><th>회전율</th><td>연 편도 NAV 대비 %s (바스켓 자체 %s × 10%% + 10%% 되돌리기)</td></tr>" % (pct(s["nav_turn_oneway"] * 100, 1, False), pct(s["basket_turn_oneway"] * 100, 0, False)))
        h.append("<tr><th>거래비용</th><td>연 약 %s (NAV 1조 원이면 연 %.1f억 원)</td></tr></table>" % (pct(s["nav_turn_oneway"] * 2 * 0.1, 3, False), s["nav_turn_oneway"] * 2 * 0.001 * 1e4))
    else:
        cs = J["strategies"]
        h.append("<h3>3-1. 구성 바스켓</h3><table><tr><th>바스켓</th><th>몫</th><th>펀드 연 초과(단독)</th><th>IR</th></tr>")
        for c in ("B", "E", "M"):
            h.append("<tr><td>%s</td><td class='n'>1/3</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (META[c]["title"], pct(cs[c]["all"]["ann_ex"]), num(cs[c]["all"]["ir"])))
        cr = J["corr_ex"]
        h.append("</table><p class='note'>월 초과 상관 — B/M·Eg %s · B/M·모멘텀 %s · Eg·모멘텀 %s. 분산은 되지만 B/M 의 초과가 0 에 가까워 Eg 몫을 깎는다.</p>"
                 % (num(cr["BE"]), num(cr["BM"]), num(cr["EM"])))
    # 4쪽 — 최근 매매
    if s.get("trades"):
        h.append('<div class="pb"></div>' + page_head(m["title"], 4))
        h.append("<h2>부록 최근 매매 — %s 리밸런스 (펀드 NAV 대비 · %d종목)</h2>" % (s["holdings"]["sig"], len(s["trades"])))
        for kind in ("신규 매수", "전량 매도", "늘림", "줄임"):
            tt = [x for x in s["trades"] if x["kind"] == kind]
            if not tt:
                continue
            h.append("<h3>%s %d종목</h3><table><tr><th>티커</th><th>회사</th><th>매매 (%%)</th><th>금액 (억)</th></tr>" % (kind, len(tt)))
            for x in sorted(tt, key=lambda x: -abs(x["pct"]))[:20]:
                h.append("<tr><td>%s</td><td>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (x["t"], html.escape(x["name"]), pct(x["pct"], 4), "%+.2f" % x["eok"]))
            h.append("</table>")
    css = """<style>@page{size:A4;margin:14mm 13mm}body{font-family:'Malgun Gothic',sans-serif;font-size:9.6pt;color:#111}
    h1{font-size:15pt;margin:4px 0}h2{font-size:12pt;margin:14px 0 6px;border-bottom:1.5px solid #0A5697;padding-bottom:2px}h3{font-size:10.5pt;margin:10px 0 4px}
    table{border-collapse:collapse;width:100%;margin:2px 0 6px}th,td{border-bottom:1px solid #ddd;padding:3px 6px;text-align:left}th{background:#F2F0EB;font-weight:700}
    td.n{text-align:right;font-variant-numeric:tabular-nums}td.b{font-weight:700}td.dn{color:#A3352A}td.up{color:#0A7040}tr.avg td{background:#FAF8F3;font-weight:600}
    table.kv th{width:18%}.sub{color:#555;font-size:8.6pt}.note{color:#666;font-size:8pt;margin:2px 0 8px}.ph{display:flex;justify-content:space-between;color:#777;font-size:8pt;border-bottom:1px solid #ccc;margin-bottom:6px}
    .pb{page-break-after:always}</style>"""
    return "<!doctype html><html><head><meta charset='utf-8'>%s</head><body>%s</body></html>" % (css, "\n".join(h))


def main() -> int:
    J = json.load(io.open(SRC, encoding="utf-8"))
    os.makedirs(OUTDIR, exist_ok=True)
    for code in ORDER:
        m = META[code]
        hp = os.path.join(OUTDIR, "%s.html" % m["file"])
        pp = os.path.join(OUTDIR, "펀드전략_%s_%s.pdf" % (m["file"], DATE))
        io.open(hp, "w", encoding="utf-8").write(build(code, J))
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        "--print-to-pdf=" + pp, "file:///" + hp.replace("\\", "/")], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("→", pp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
