# -*- coding: utf-8 -*-
"""build/fund_card_pdf.py — 우량성장선별 30 · 전략 카드 → data/fund_card.pdf (A4 5쪽)

자료는 build/fund_card.py 가 낸 data/_fund_card.json 하나뿐이다(build/qg_report.py 가
같은 파일을 마크다운으로 뽑는 것과 같은 규약 — **여기서 아무것도 새로 계산하지 않는다.**
카드가 바뀌면 이 PDF 도 같이 바뀐다).

⚠ style8.pdf 와 같은 화판·색·표 도우미(style_top_pdf)를 쓰지만 **월별 히트맵·자산곡선·
  위험수익 산점도는 못 그린다** — 그걸 낼 월별 수익 계열(qg_monthly.pkl)이 사내 파일이라
  이 클론에 없다(build/fund_fit.py 가 읽는 D18 경로가 이 PC 에 없다). 대신 카드가 이미
  재 둔 **연 단위 진단**(가중 분해 · 십분위 · 크기구간 · 상한 메뉴 · 다중검정)으로 짠다.

  1쪽  표지 · 핵심 주장 · 성과 · 깔때기
  2쪽  분해 — 가중이 전부다 · 십분위 · 크기구간
  3쪽  상한 메뉴 · 건전성(다중검정 · OOS 순위 · 구조)
  4쪽  한계 9가지
  5쪽  비용 · 국면 · 읽는 법

  python build/fund_card_pdf.py [--png]
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["axes.unicode_minus"] = False
from matplotlib.backends.backend_pdf import PdfPages   # noqa: E402

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "fund_card.pdf")
sys.path.insert(0, HERE)
import style_top_pdf as ST                                        # noqa: E402

X0, X1 = ST.X0, ST.X1
INK, INK2, MUTED, LINE, RULE = ST.INK, ST.INK2, ST.MUTED, ST.LINE, ST.RULE
POS, NEG, ACC, PAPER, PANEL2 = ST.POS, ST.NEG, ST.ACC, ST.PAPER, ST.PANEL2

TOT = 5
YMIN = .050               # 이보다 내려가면 꼬리말을 뚫는다


# ══ 글자 정리 · 줄바꿈 ══════════════════════════════════════════════════════
# 🚨 카드 문장은 사람이 쓴 진단 메모라 ⚠·🚨·U+2212(진짜 마이너스)가 섞여 있다.
#   맑은 고딕에 이 셋이 없다(이 랩에서 여러 번 두부로 나온 자리다 — memory
#   naver-blog 류가 아니라 이 저장소 자체의 실측이다). 🚨 는 지우고(뒤에 오는
#   **굵게**가 이미 강조를 한다) ⚠ 는 ta_signals_pdf 의 관례를 따라 «!!» 로,
#   U+2212 는 ASCII 하이픈으로 바꾼다.
def clean(s):
    if not s:
        return s
    return (s.replace("🚨 ", "").replace("🚨", "")
             .replace("⚠ ", "!! ").replace("⚠", "!!")
             .replace("−", "-"))


def _mw(fig, r, s, fs, weight="normal"):
    """렌더 실측 폭(그림 비율) — PDF 5% 여유(ST._PDF_PAD) 포함."""
    t = fig.text(0, 0, s.replace("**", ""), fontsize=fs, weight=weight)
    w = t.get_window_extent(renderer=r).width / fig.bbox.width * ST._PDF_PAD
    t.remove()
    return w


def wrap(fig, r, s, fs, max_w, weight="normal"):
    """낱말 단위 줄바꿈 — 실측 폭 기준. ** 는 굵게 표기(tx 가 조각별로 처리)."""
    words = clean(s).split(" ")
    lines, cur = [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if cur and _mw(fig, r, trial, fs, weight) > max_w * .97:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def bullets(fig, r, x, y, items, fs=6.8, lh=.0112, gap=.0058, num=False,
           color=INK2, max_w=None):
    """번호(한계) 또는 가운뎃점(증거) 목록 — 줄마다 실측 줄바꿈."""
    max_w = max_w if max_w is not None else (X1 - x - .026)
    for i, s in enumerate(items, 1):
        mark, mark_w = ("%d." % i, .020) if num else ("·", .012)
        for j, ln in enumerate(wrap(fig, r, s, fs, max_w)):
            if j == 0:
                ST.tx(fig, x, y, mark, fontsize=fs, color=ACC if num else MUTED,
                     weight="bold" if num else "normal")
            ST.tx(fig, x + mark_w, y, ln, fontsize=fs, color=color)
            y -= lh
        y -= gap
    return y


# ══ 쪽 뼈대 ══════════════════════════════════════════════════════════════
def foot(fig, page, asof, y_end=None):
    if y_end is not None and y_end < YMIN:
        print("  !! %d쪽 바닥 y=%.4f — %.3f 아래로 내려갔다" % (page, y_end, YMIN))
    ST.hline(fig, X0, X1, .034, LINE, .6)
    ST.tx(fig, X0, .024,
          "여두 전략 랩 · 우량성장선별 30 · 전략 카드 · 기준 %s" % asof,
          fontsize=6.4, color=MUTED)
    ST.tx(fig, X1, .024, "%d / %d · %s" % (page, TOT, dt.datetime.now().strftime("%Y-%m-%d")),
          fontsize=6.4, color=MUTED, ha="right")


def head(fig, title, sub, asof, meta):
    y = .958
    ST.tx(fig, X0, y, title, fontsize=16, weight="bold")
    ST.tx(fig, X1, y + .002, meta, fontsize=7.0, color=MUTED, ha="right")
    y -= .0215
    ST.tx(fig, X0, y, sub, fontsize=8.2, color=MUTED)
    y -= .020
    ST.hline(fig, X0, X1, y, RULE, .9)
    return y - .015


def section(fig, y, title, note=""):
    ST.tx(fig, X0, y, title, fontsize=10.5, weight="bold")
    if note:
        ST.tx(fig, X1, y, note, fontsize=6.3, color=MUTED, ha="right")
    return y - .0155


def _ax(fig, x, y, w, h):
    ax = fig.add_axes([x, y, w, h])
    ax.set_facecolor(PAPER)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(LINE)
        ax.spines[s].set_linewidth(.6)
    ax.tick_params(colors=MUTED, labelsize=6.0, length=2, width=.5, pad=1.5)
    return ax


def stat_strip(fig, y, items, h=.052):
    """큰 수 카드를 한 줄에 늘어놓는다 — items=[(value, label, color)]."""
    n = len(items)
    gw = (X1 - X0) / n
    for i, (v, lab, col) in enumerate(items):
        cx = X0 + gw * i + gw / 2
        ST.tx(fig, cx, y, v, fontsize=15, weight="bold", color=col, ha="center")
        ST.tx(fig, cx, y - .020, lab, fontsize=6.6, color=MUTED, ha="center")
        if i:
            ST.vline(fig, X0 + gw * i, y - h + .010, y + .010, LINE, .6)
    return y - h


def pf(v, d=1, pp=False, pct=False):
    if v is None:
        return "—"
    s = "%+.*f" % (d, v)
    return s + ("%p" if pp else ("%" if pct else ""))


# ══ 1쪽 — 표지 · 핵심 주장 · 성과 · 깔때기 ═══════════════════════════════
def page1(fig, C, asof):
    P = C["perf"]
    y = head(fig, C["name"], "%s · %s" % (C["family"], C["role"]), asof,
            "창 %s~%s(%d개월) · 잣대 %s · 상한 %.0f%%"
            % (C["window"]["start"], C["window"]["end"], C["window"]["n_months"],
               C["bench"], C["cap_pct"]))

    y = section(fig, y, "무엇을 담나")
    for ln in wrap(fig, fig.canvas.get_renderer(), C["rule"], 7.4, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=7.4, color=INK2)
        y -= .0122
    y -= .010

    # ── 핵심 주장 callout ──
    r = fig.canvas.get_renderer()
    cl = C["claim"]
    lines = (wrap(fig, r, "이것이다 — " + cl["is"], 8.2, X1 - X0 - .020)
            + wrap(fig, r, "이것은 아니다 — " + cl["is_not"], 8.2, X1 - X0 - .020))
    bh = .026 + len(lines) * .0142
    ST.box(fig, X0, y - bh, X1 - X0, bh, PANEL2, z=0)
    ST.box(fig, X0, y - bh, .006, bh, ACC, z=1)
    yy = y - .013
    for ln in lines:
        ST.tx(fig, X0 + .018, yy, ln, fontsize=8.2, color=INK)
        yy -= .0142
    y -= bh + .018

    # ── 성과 스탯 ──
    y = section(fig, y, "성과", "10bp 편도 거래비용 반영 · 분기 리밸런스")
    y -= .004
    y = stat_strip(fig, y, [
        (pf(P["excess_y_pp"], 2, pp=True), "연 초과", POS),
        ("%.2f%%" % P["te_y_pct"], "추적오차(TE)", MUTED),
        ("%.2f" % P["ir"], "정보비율(IR)", POS),
        ("%.2f" % P["t"], "t값", POS if P["t"] >= 2 else ACC),
        ("%.1f%%" % P["win_rate_pct"], "월 승률", INK),
        ("%.1f%%" % C["concentration"]["top3_pct"], "상위 3사 비중", ACC),
    ])
    y -= .006
    ST.tx(fig, X0, y,
          "**초과 = 바스켓 총수익(TR) - S&P 500 총수익(TR).** 유효 종목 수(1/HHI) 중앙 %.1f개 "
          "· 최근 %.1f개(이름은 30개) · 연 회전율 %.0f%%."
          % (C["diag"]["structure"]["eff_names_median"], C["diag"]["structure"]["eff_names_last"],
             C["concentration"]["turn_y_pct"]), fontsize=6.8, color=INK2)
    y -= .026

    # ── 깔때기 ──
    y = section(fig, y, "어디서 늘었나 — 설계를 한 단계씩 쌓으면",
               "diag.funnel 실측(qg_diag.json)")
    fr = C["diag"]["funnel"]
    tr = [[f["step"], "%.2f%%" % f["ann"],
           ("%+.2f%%p" % f["delta"]) if f["delta"] is not None else "—",
           "%.0f%%" % f["turn"], "%.2f" % f["ir"], "%.2f" % f["t"]] for f in fr]

    def cc(rr, c):
        if c == 0:
            return INK
        if c == 2:
            v = tr[rr][2]
            return MUTED if v == "—" else (POS if v.startswith("+") else NEG)
        return MUTED
    y = ST.table(fig, X0, y, [.360, .120, .120, .100, .092, .092],
                 ["단계", "연 수익", "증분", "회전율", "IR", "t"], tr,
                 row_h=.0170, fs=7.4, hfs=6.6, zebra=True,
                 aligns=["l", "r", "r", "r", "r", "r"], cell_color=cc)
    y -= .010
    gap = fr[-1]["ann"] - P["excess_y_pp"]
    r = fig.canvas.get_renderer()
    note1 = ("마지막 단계 %.2f%%p 와 위 성과표 %.2f%%p 사이 %.2f%%p 차는 diag(qg_diag.json)와 "
            "perf 를 **따로 낸 값이라 생기는 재현 차**다 — cap_menu 의 재현오차(anchor_recon_gap_pp "
            "%.4f%%p)와는 다른 자리다. 감추지 않고 여기 적는다."
            % (fr[-1]["ann"], P["excess_y_pp"], gap, C["cap_menu"]["anchor_recon_gap_pp"]))
    for ln in wrap(fig, r, note1, 6.3, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=6.3, color=MUTED)
        y -= .0104
    y -= .0006
    # 하드코딩하지 않고 깔때기(fr) 값을 그대로 쓴다 — 손으로 적은 수는 낡는다(qg_report.py 의 교훈).
    note2 = ("읽는 법 — **100종에서 30종으로 좁힌 것**이 %+.2f%%p 로 가장 크게 벌었고, "
            "상한 %.0f%% 는 %+.2f%%p 를 더 얹었다. 이 30종을 **어떻게 담는지**가 얼마나 "
            "더 큰지는 다음 쪽에서 잰다."
            % (fr[2]["delta"], C["cap_pct"], fr[3]["delta"]))
    for ln in wrap(fig, r, note2, 6.8, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=6.8, color=INK2)
        y -= .0122
    foot(fig, 1, asof, y - .012)


# ══ 2쪽 — 분해 ═══════════════════════════════════════════════════════════
def page2(fig, C, asof):
    y = head(fig, C["name"], "분해 — 초과는 어디서 오나", asof, "")

    y = section(fig, y, "가중이 전부다", "같은 30종 · 같은 시점규칙 · 가중만 다르게")
    W = C["diag2"]["weight"]
    order = [("동일가중", "equal", MUTED), ("상한없음(지수비중)", "uncapped", ACC),
             ("상한 20%(현행)", "cap20", POS)]
    tr = [[lab, "%+.2f%%p" % W[k]["excess_y_pp"], "%.2f%%" % W[k]["te_y_pct"],
           "%.2f" % W[k]["ir"], "%.2f" % W[k]["t"], "%.1f%%" % W[k]["mdd_ex_pct"],
           "%.1f%%" % W[k]["win_rate_pct"], "%.0f%%" % W[k]["turn"], "%.1f" % W[k]["eff"]]
          for lab, k, _c in order]

    def cc(r, c):
        if c == 0:
            return INK
        if c == 1:
            return POS if not tr[r][1].startswith("-") else NEG
        return MUTED
    y = ST.table(fig, X0, y, [.190, .100, .088, .078, .066, .092, .092, .088, .090],
                 ["방식", "연 초과", "TE", "IR", "t", "MDD(초과)", "승률", "회전", "유효종목"],
                 tr, row_h=.0158, fs=7.2, hfs=6.5, zebra=True,
                 aligns=["l", "r", "r", "r", "r", "r", "r", "r", "r"], cell_color=cc)
    y -= .010

    r = fig.canvas.get_renderer()
    ax = _ax(fig, X0, y - .085, .250, .080)
    vals = [W[k]["excess_y_pp"] for _l, k, _c in order]
    cols = [c for _l, _k, c in order]
    ax.bar(range(3), vals, color=cols, width=.55, zorder=3)
    ax.axhline(0, color=RULE, lw=.6, zorder=2)
    ax.set_ylim(0, max(vals) * 1.22)
    ax.set_xticks(range(3)); ax.set_xticklabels(["동일가중", "상한없음", "상한20%"], fontsize=6.4)
    ax.set_ylabel("연 초과(%p)", fontsize=6.2, color=MUTED)
    for i, v in enumerate(vals):
        ax.text(i, v + .28, "%+.2f" % v, ha="center", va="bottom",
                fontsize=6.6, weight="bold", color=cols[i])
    # ⚠ 옆 문단을 재지 않고 그냥 찍었더니 오른쪽 여백을 뚫었다(렌더 실측) — 실측 줄바꿈으로 바꾼다.
    nx, nw = X0 + .275, X1 - X0 - .275
    ny = y - .012
    note = ("동일가중은 초과 **%+.2f%%p(t %.2f)** 로 잡음과 구분이 안 된다. 상한없음(지수비중)은 "
           "**%+.2f%%p** 까지 올라오고, 20%% 상한이 %+.2f%%p 를 마저 보탠다."
           % (W["equal"]["excess_y_pp"], W["equal"]["t"], W["uncapped"]["excess_y_pp"],
              W["cap20"]["excess_y_pp"] - W["uncapped"]["excess_y_pp"]))
    for ln in wrap(fig, r, note, 6.9, nw):
        ST.tx(fig, nx, ny, ln, fontsize=6.9, color=INK2)
        ny -= .0122
    ny -= .006
    note2 = ("즉 초과의 **%.0f%%**(%.2f%%p 중 %.2f%%p)가 «어느 30종을 고르나» 가 아니라 "
            "«누구에게 몰아주나» 에서 온다." % (W["wgt_share_pct"], W["cap20"]["excess_y_pp"],
                                       W["wgt_share_pp"]))
    for ln in wrap(fig, r, note2, 6.9, nw):
        ST.tx(fig, nx, ny, ln, fontsize=6.9, color=INK2, weight="bold")
        ny -= .0122
    y -= .105

    # ── 십분위 ──
    D = C["diag2"]["decile"]
    y = section(fig, y, "점수 십분위 — 단조로운가", "동일가중 · 전체 %d종 · 분기수익률(%%)" % D["n_q"])
    ax = _ax(fig, X0, y - .092, X1 - X0, .082)
    xs = list(range(1, 11))
    rets = [d["ret"] for d in D["deciles"]]
    ax.bar(xs, rets, color=[POS if v >= D["uni"] else NEG for v in rets], width=.62, zorder=3)
    ax.axhline(D["uni"], color=ACC, lw=.9, ls=(0, (3, 2)), zorder=4)
    ax.set_xlim(.3, 10.7)
    ax.set_ylim(0, max(rets) * 1.18)
    # ⚠ 데이터 좌표(10.55, uni)에 라벨을 두었더니 10분위 막대·눈금과 겹쳤다(렌더 실측) —
    #   막대 높이에 안 흔들리게 **축 비율 좌표**(transAxes)로 왼쪽 위 구석에 둔다.
    ax.text(.010, .95, "전체 평균 %.2f%%" % D["uni"], transform=ax.transAxes,
           fontsize=6.4, color=ACC, weight="bold", va="top")
    ax.set_xticks(xs)
    ax.set_xticklabels(["1(상)"] + [str(i) for i in range(2, 10)] + ["10(하)"], fontsize=6.4)
    # !! 축 눈금 라벨은 그림틀(.082) 아래로 넘쳐 그려진다 — 다음 글까지 간격을 .006 만
    #   두었더니 라벨과 글이 격쳤다(렌더 실측). 가중 분해 차트와 같은 .020 로 맞추다.
    y -= .116
    note = ("1분위 **%+.2f%%p**(t %.2f) · 10분위 %+.2f%%p — **단조롭지 않다.** 1-10 스프레드는 "
           "%+.2f%%p(t %.2f)로 잡음과 구분이 안 된다(중간 폭 %.2f%%p)."
           % (D["deciles"][0]["vs_uni"], D["deciles"][0]["t"], D["deciles"][9]["vs_uni"],
              D["spread_1_10"], D["spread_t"], D["mid_range"]))
    for ln in wrap(fig, r, note, 6.9, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=6.9, color=INK2)
        y -= .0122
    y -= .010

    # ── 크기 구간별 ──
    SB = C["diag2"]["sizeband"]
    y = section(fig, y, "크기 구간별 — 어디서만 듣나", "동일가중 · 점수 상위 대 하위(분기수익률%)")
    ax = _ax(fig, X0, y - .092, X1 - X0, .080)
    n = len(SB)
    w_ = .32
    his = [b["hi"] for b in SB]
    los = [b["lo"] for b in SB]
    ax.bar([i - w_ / 2 for i in range(n)], his, width=w_, color=POS, zorder=3, label="점수 상위")
    ax.bar([i + w_ / 2 for i in range(n)], los, width=w_, color=NEG, zorder=3, label="점수 하위")
    ax.set_ylim(0, max(his + los) * 1.20)
    ax.set_xticks(range(n)); ax.set_xticklabels([b["label"] for b in SB], fontsize=6.2)
    # ⚠ 범례를 그림 안(upper right)에 두었더니 막대와 겹쳤다(렌더 실측) — 그림 위로 뺀다.
    ax.legend(fontsize=6.2, frameon=False, loc="lower center",
             bbox_to_anchor=(.5, 1.02), ncol=2)
    # ⚠ 여기도 축 눈금 라벨과 다음 글 사이가 .008 뿐이었다 — .020 로 맞춘다.
    y -= .112
    big = SB[0]
    note = ("**%s** 만 상 하위가 갈린다 — 스프레드 %+.2f%%p(t %.2f). 그 밖 구간은 스프레드가 "
           "0 근처다(101~250위 t %.2f · 251위~ t %.2f). **점수는 대형주에서만 듣는다.**"
           % (big["label"], big["spread_pp"], big["t"], SB[1]["t"], SB[2]["t"]))
    for ln in wrap(fig, r, note, 6.9, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=6.9, color=INK2)
        y -= .0122
    y -= .010

    y = section(fig, y, "증거")
    y = bullets(fig, r, X0, y, C["claim"]["evidence"], fs=6.8)
    foot(fig, 2, asof, y)


# ══ 3쪽 — 상한 메뉴 · 건전성 ═════════════════════════════════════════════
def page3(fig, C, asof):
    y = head(fig, C["name"], "상한 메뉴 · 얼마나 믿을 만한가", asof, "")
    r = fig.canvas.get_renderer()

    y = section(fig, y, "상한 메뉴", clean(C["cap_menu"]["note"]))
    rows = C["cap_menu"]["rows"]
    cur = C["cap_pct"]
    tr = [["%.0f%%" % rr["cap_pct"] + ("  ← 현행" if rr["cap_pct"] == cur else ""),
           "%+.2f%%p" % rr["excess_y_pp"], "%.2f%%" % rr["te_y_pct"], "%.2f" % rr["ir"],
           "%.2f" % rr["t"], "%.1f%%" % rr["mdd_ex_pct"], "%.1f%%" % rr["win_rate_pct"],
           "%.0f%%" % rr["turn_y_pct"], "%.1f%%" % rr["top3_pct"],
           ("%+.2f%%p" % rr["vs20_pp"]) if rr["cap_pct"] != 20 else "기준"]
          for rr in rows]

    def cc(r, c):
        if c == 0:
            return ACC if rows[r]["cap_pct"] == cur else INK
        if c == 1:
            return POS
        return MUTED
    y = ST.table(fig, X0, y,
                 [.108, .098, .078, .066, .060, .092, .080, .076, .080, .096],
                 ["상한", "연 초과", "TE", "IR", "t", "MDD(초과)", "승률", "회전", "상위3사", "20%대비"],
                 tr, row_h=.0156, fs=7.1, hfs=6.3, zebra=True,
                 aligns=["l", "r", "r", "r", "r", "r", "r", "r", "r", "r"], cell_color=cc)
    y -= .012

    CS = C["diag"]["structure"]["cap_stability"]
    ST.tx(fig, X0, y, "창을 바꾸면 최적 상한도 바뀐다", fontsize=8.6, weight="bold")
    y -= .0148
    wins = list(CS["by_window"].items())
    tr2 = [[wl] + ["%.2f%%p" % v for v in wd["row"]] +
           ["%.0f%%  ← 최적" % wd["best"]] for wl, wd in wins]
    y = ST.table(fig, X0, y, [.130] + [.098] * 5 + [.126],
                 ["창"] + ["%.0f%%" % c for c in CS["caps"]] + ["이 창의 최적"], tr2,
                 row_h=.0150, fs=7.0, hfs=6.3, zebra=True,
                 aligns=["l"] + ["r"] * 6, cell_color=lambda r, c: ACC if c == 6 else MUTED)
    y -= .011
    agree = [wl for wl, wd in wins if wd["best"] == 20.0]
    note = ("셋 중 **%d개**(%s)는 20%%를 고르고, 나머지(%s)만 %.0f%%를 고른다 — 지금 20%% 인 "
           "것은 «최근 창에서 최적이라서» 가 아니라 **20~30%% 대가 평평해서**다(등록서 §3). "
           "창을 바꿔 최적을 다시 고르지 않는다."
           % (len(agree), "·".join(agree),
              "·".join(wl for wl, wd in wins if wd["best"] != 20.0),
              next(wd["best"] for wl, wd in wins if wd["best"] != 20.0)))
    for ln in wrap(fig, r, note, 6.7, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=6.7, color=INK2)
        y -= .0114
    y -= .014

    y = section(fig, y, "얼마나 믿을 만한가", "다중검정 진단(qg_diag.json)")
    MT = C["diag"]["multiple_testing"]
    y = stat_strip(fig, y, [
        ("%.0f%%ile" % MT["percentile"], "%d회 뒤섞기 중 위치" % MT["shuffle_n"], POS),
        ("%.3f" % MT["monthly_sr"], "월 샤프", INK),
        ("%.2f" % MT["dsr"]["N100"], "DSR(설계 100종 가정)", ACC if MT["dsr"]["N100"] < .95 else POS),
        ("%.2f" % MT["dsr"]["N200"], "DSR(설계 200종 가정)", ACC if MT["dsr"]["N200"] < .95 else POS),
    ], h=.046)
    y -= .002
    # ⚠ 여기 나오는 N=54~200 은 이 **펀드 하나의 설계 탐색**에 대한 DSR 민감도 가정이다
    #   (한계 6번 — 「원 문서가 백 가지 넘는 조합에서 고른 설계라고 적었다」). 랩 전체 다중검정
    #   분모(strategy_index.json 의 trials.n · 지금 499)와는 **다른 수다** — 혼동하지 않게 밝혀 둔다.
    #   !! 「시행 N회」꼴로 적으면 validate_site.py 가 랩 전체 분모로 오인해 대조하니(그 검사의
    #   뜻은 맞다 — 과거 이 랩에서 실제로 여러 스크립트가 저마다 다른 수를 하드코딩해 어긋난
    #   적이 있다) 그 표기를 피한다.
    note = ("**뒤섞기 검정**(수익 순서를 500번 무작위로 섞어 같은 규칙을 태움)에서는 실제 설계가 "
           "섞은 것 전부보다 높다(귀무 평균 %+.2f · 표준편차 %.2f). 그런데 **DSR**(이 펀드의 설계를 "
           "몇 종 탐색했다고 가정하고 깎는 샤프 — 랩 전체 다중검정 분모와는 다른, 이 펀드만의 "
           "가정이다)은 설계 100~200종 가정 모두 **0.95 문턱을 못 넘는다**"
           "(%.2f~%.2f). 둘이 다른 것을 잰다 — 뒤섞기는 «신호가 무작위는 아니다», DSR 은 "
           "«그런데 몇 번이나 골라 봤는지를 셈하면 자신 있게 말하기엔 이르다» 쪽이다."
           % (MT["shuffle_mean"], MT["shuffle_sd"], MT["dsr"]["N100"], MT["dsr"]["N200"]))
    for ln in wrap(fig, r, note, 6.7, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=6.7, color=INK2)
        y -= .0114
    y -= .020

    RO = C["diag2"]["rank_oos"]; ST_ = C["diag"]["structure"]
    ST.tx(fig, X0, y, "다음 분기를 맞히나 · 구조", fontsize=8.6, weight="bold")
    y -= .0148
    tr3 = [
        ["IS-OOS 순위상관(중앙)", "%+.3f" % RO["rank_corr"]["all_median"],
         "t %.2f · 양(+)이 %d%%" % (RO["rank_corr"]["all_t"], round(RO["rank_corr"]["all_pos_pct"]))],
        ["다음분기 백분위(중앙)", "%.1f%%ile" % RO["oos_percentile"]["median"],
         "하위25%% 진입 %.0f%% · 상위25%% 진입 %.1f%% — 무작위(25%%)와 비슷" %
         (RO["oos_percentile"]["below25_pct"], RO["oos_percentile"]["above75_pct"])],
        ["유효 종목 수(1/HHI)", "중앙 %.1f · 최근 %.1f" % (ST_["eff_names_median"], ST_["eff_names_last"]),
         "이름은 %d개" % ST_["topn"]],
        ["이월률(Jaccard)", "분기 %.0f%% · 1년 %.0f%%" % (ST_["jaccard_q_median"] * 100, ST_["jaccard_y_median"] * 100),
         "1년 지나면 명단의 4분의 1만 남는다"],
    ]
    y = ST.table(fig, X0, y, [.230, .220, .434], ["무엇을", "값", "비고"], tr3,
                 row_h=.0168, fs=7.0, hfs=6.4, zebra=True,
                 aligns=["l", "r", "l"], cell_color=lambda r, c: INK if c == 0 else MUTED)
    foot(fig, 3, asof, y - .010)


# ══ 4쪽 — 한계 9가지 ═════════════════════════════════════════════════════
def page4(fig, C, asof):
    y = head(fig, C["name"], "한계 9가지", asof, "")
    r = fig.canvas.get_renderer()
    # ⚠ 안 재고 한 줄로 찍었더니 .943(본문 폭 .884)로 오른쪽 여백을 먹고 종이 끝까지
    #   닿았다(렌더 실측) — 줄바꿈으로 바꾼다.
    for ln in wrap(fig, r, "성적표 위쪽 두 쪽이 «무엇이 벌었나» 라면, 이 쪽은 **«그래서 어디까지 "
                  "믿을 것인가»** 다. 카드(data/_fund_card.json)에 실린 것을 그대로 옮긴다 — "
                  "순서도 그대로다.", 7.4, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=7.4, color=MUTED)
        y -= .0128
    y -= .014
    y = bullets(fig, r, X0, y, C["limits"], fs=7.0, lh=.0118, gap=.0090, num=True, color=INK2)
    foot(fig, 4, asof, y)


# ══ 5쪽 — 비용 · 국면 · 읽는 법 ═══════════════════════════════════════════
def page5(fig, C, asof):
    y = head(fig, C["name"], "비용에 물어보면 · 국면별 · 읽는 법", asof, "")

    y = section(fig, y, "설계를 바꾸면 얼마나 드나", "비용 10bp(편도) · pp/년")
    r = fig.canvas.get_renderer()
    for c in C["costs"]:
        frz = "" if c["remeasured"] else "(얼린 값 — 이 클론에 입력이 없어 다시 재지 못했다)"
        head_s = "%s — %+.2f%%p/년  ·  %s" % (clean(c["what"]), c["pp_per_year"], clean(c["verdict"]))
        for j, ln in enumerate(wrap(fig, r, head_s, 7.6, X1 - X0 - .180, weight="bold")):
            ST.tx(fig, X0, y, ln, fontsize=7.6, color=INK, weight="bold")
            if j == 0:
                ST.tx(fig, X1, y, clean(c["basis"]), fontsize=6.2, color=MUTED, ha="right")
            y -= .0130
        if frz:
            ST.tx(fig, X0, y, frz, fontsize=6.2, color=MUTED)
            y -= .0108
        for ln in wrap(fig, r, c["note"], 6.6, X1 - X0 - .020):
            ST.tx(fig, X0 + .014, y, ln, fontsize=6.6, color=INK2)
            y -= .0108
        y -= .0068
    y -= .012

    rbc = C.get("regime_basis_cap_pct")
    y = section(fig, y, "국면별", "상한 %.0f%% 계열(카드 실측) · 분기수익률(%%) 삼분위" % rbc)
    y -= .0002
    # 🚨 카드 안에서 서로 어긋난다 — 감추지 않고 적는다. regime_basis_cap_pct 필드값은
    #   10(= prev_design.cap_pct, 구설계)인데, 바로 아래 regime_note 문장은 «20% 상한
    #   계열» 이라고 적혀 있다. 어느 쪽이 맞는지 여기서 새로 가리지 않는다 — 카드가
    #   가리키는 두 값을 그대로 나란히 보인다.
    if rbc is not None and rbc != C["cap_pct"] and rbc == C.get("prev_design", {}).get("cap_pct"):
        ST.tx(fig, X0, y,
              "!! 필드값(%.0f%%)과 아래 카드 문장이 어긋난다 — 문장은 «20%% 상한 계열»이라고 "
              "적혀 있는데 필드는 구설계(%.0f%%) 상한을 가리킨다. 카드 원본의 불일치라 "
              "여기서 고르지 않는다." % (rbc, rbc), fontsize=6.2, color=ACC)
        y -= .0104
    y -= .0018
    tr = []
    for k, v in C["regime"].items():
        tr.append([k, "%.2f" % v["low"], "%.2f" % v["mid"], "%.2f" % v["high"],
                   "%+.2f%%p" % v["diff"], "%d" % v["n"]])

    def cc(rr, c):
        if c == 0:
            return INK
        if c == 4:
            return POS if not tr[rr][4].startswith("-") else NEG
        return MUTED
    y = ST.table(fig, X0, y, [.260, .118, .118, .118, .130, .140],
                 ["국면 축(삼분위)", "낮음", "중간", "높음", "높음-낮음", "n"], tr,
                 row_h=.0158, fs=7.2, hfs=6.5, zebra=True,
                 aligns=["l", "r", "r", "r", "r", "r"], cell_color=cc)
    y -= .010
    for ln in wrap(fig, r, clean(C.get("regime_note", "")), 6.4, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=6.4, color=MUTED)
        y -= .0104
    y -= .020

    y = section(fig, y, "읽는 법")
    cl = C["claim"]
    for ln in wrap(fig, r, cl["but"], 7.2, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=7.2, color=INK2)
        y -= .0122
    y -= .006
    # ⚠ 앞에 "**" 를 덧붙였더니 원문 안의 짝과 합쳐 홀수가 되어 굵기가 뒤집혔다
    #   (강조하려던 인용구가 안 굵고, 안 굵어야 할 앞뒤가 굵어졌다) — 원문 그대로 쓴다.
    #   weight= 를 넘기면(비어 있지 않은 문자열이면 "normal" 이어도) tx() 가 ** 파싱을
    #   건너뛰므로 아예 안 넘긴다.
    for ln in wrap(fig, r, cl["so"], 7.4, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=7.4, color=INK)
        y -= .0128
    y -= .010
    for ln in wrap(fig, r, "판정 — " + cl["verdict"], 7.0, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=7.0, color=ACC)
        y -= .0118
    y -= .002
    for ln in wrap(fig, r, cl["unchanged"], 6.6, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=6.6, color=MUTED)
        y -= .0108
    y -= .002
    for ln in wrap(fig, r, C["basis_note"], 6.6, X1 - X0):
        ST.tx(fig, X0, y, ln, fontsize=6.6, color=MUTED)
        y -= .0108
    y -= .012
    foot(fig, 5, asof, y)


def main() -> int:
    C = json.load(io.open(os.path.join(DATA, "_fund_card.json"), encoding="utf-8"))
    asof = C["window"]["end"]
    figs = []
    with PdfPages(OUT) as pdf:
        for i, fn in enumerate((page1, page2, page3, page4, page5), 1):
            fig = ST.new_page()
            figs.append(fig)
            fn(fig, C, asof)
        for i, f in enumerate(figs, 1):
            pdf.savefig(f)
            if "--png" in sys.argv[1:]:
                f.savefig(os.path.join(DATA, "_fc_%d.png" % i), dpi=110, facecolor=PAPER)
            ST.plt.close(f)
        pdf.infodict()["Title"] = "%s · 전략 카드 · 기준 %s" % (C["name"], asof)

    print("→ %s · %d쪽 · 기준 %s" % (OUT, TOT, asof))
    return 0


if __name__ == "__main__":
    sys.exit(main())
