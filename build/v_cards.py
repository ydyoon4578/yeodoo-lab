# -*- coding: utf-8 -*-
"""build/v_cards.py — 배치 V 카드 V01~V08 · 쌍둥이 · 대조 · 정적판: 책 규칙(선정 · 버퍼 · 시총가중 · 능동 상한 · θ 혼합 · β 띠) ·
S 층 PIT 책 경로(체결 · 흘러감 · T+1 · 비용) · L 층 French 대리 거미줄 팔(기울기 · 군 R2 · θ 경로 · COST_ERAS × 내부 τ).

설계 원본(구속): vbatch_research.json final.slate(common_frame · strategies V01~V07 · twins_report_only · removed_from_design) ·
  final.conditions · final.estimator · final.tests.S_layer.arms · 오케스트레이터 결정 8(V08 «NI — 순자사주(주주환원)» 전방 전용).
  명세 build_plan 은 책 규칙 모듈을 «v_books.py» 로 불렀다 — 과제 지시(엔진 단계)에 따라 build/v_cards.py 로 짓는다(내용은 명세 v_books 그대로).

카드(명세 slate · 설계를 다시 짓지 않는다)
  V01 MOM  합집합 12-2 상위 30% · 버퍼 45% · 섹터 ±10%p · β 띠 · 거미줄(SLOW + · G2own S) · θ0 0.75 · Δθ 0.25
  V02 LBS  섹터마다 FP β̂ 하위 20%(섹터 이름 수 ∝ 섹터 시총 몫 · 최대 나머지법) · 버퍼 · 섹터 ±5%p · β 띠 면제 · 거미줄(BSPRD + · G2own +)
  V03 LIQ  s = −IRRX 상위 30% · 버퍼 없음 · 전량 체결 · 섹터 ±10%p · β 띠 · 상태 의존 비용 · θ0 0.5 · Δθ 0.3(비상 규칙 [0.2, 0.6] · θ0 0.4)
  V04 INS  φ = ½: OB 시총가중 + ½: OS 뺀 w_B(재정규화) · OB < 5 이면 OB 몫 → w_B-ex-OS · β 띠 · 정적 · 측정만
  V05 EAR  CAR[−2,+1] 상위 20% · 버퍼 30% · CH 제외(옛 LAZY 흡수 단계) · ATTN 책 안 기울기(실시간 축소 평균 · λ = ½·band(u^A)) · 섹터 ±10%p · β 띠 · θ 정적 · 측정만
  V06 VAL  섹터 안 백분위 평균(E/P · S/P — S/P 는 F0 커버리지일 때만) 상위 30% · E < 0 이면 E/P 최하위 · 버퍼 · 섹터 ±10%p · β 띠 · 거미줄(VSPRD +)
  V07 QLT  (섹터 × β̂ 3분위) 칸 안 z 평균(PROF[OP|ROA_ttm] · −LEV · −σROA · 성분 ≥ 2) 상위 30% · 버퍼 · 섹터 ±10%p · β 띠 · 거미줄(PQ +)
  V08 NI   🔎 오케스트레이터 결정 8 — T18 규칙(PREREG-2026-09-26-TBATCH.md §1.12: NI = FY t−2 말 → FY t−1 말 분할 조정 주식수 로그 변화 ·
           6월 말 재구성 · 순발행 «< 0» = 순매입)을 PIT S&P 500 ∪ NDX 주식 바스켓으로: 6월 말에 NI < 0 이름을 뽑아 다음 6월까지 든다(우주 탈락은 판다 ·
           새 편입은 다음 6월에) · 🔧 섹터 중립(검토 고침 · 오케스트레이터 «sector-neutral»): 섹터마다 NI < 0 이름의 시총가중 × 그 섹터의 w_B 몫 ·
           NI < 0 이름이 없는 섹터는 그 섹터 w_B 그대로(능동 섹터 0) · 능동 상한(발행사 ±5%p · NDX 전용 ≤ 10%) · 섹터 띠 ±3%p(β 띠 뒤 재투영 · T-MOM-SN 과 같은 띠) ·
           같은 중립 w_B · β 띠 · θ 정적 0.75 · 거미줄 없음(정적).
           표본 안 확정 가설 없음(긴 층은 배치 T 가 이미 쟀다 — 공개) · VFWD 전방 원장에만 측정/전방 채택 카드로 든다.
           입력은 순발행 자체(v_fund.net_issuance)뿐 — EG30 · Eg · 투자 · cfo 입력 없음. 🔎 이론 인접(공개): 순발행은 투자 CAPM(HXZ 투자 범주)의 이웃이다.

팔(명세 tests.S_layer.arms) — 카드마다 W(거미줄/기울기 · θ_t) · S0(θ0 정적) · F(θ = 1) + 쌍둥이(TWINS). 배분기 팔은 build/v_alloc.py.
  EAR 의 W = CH 제외 + ATTN 기울기(θ0) · S0 = CH 제외만(= T-EAR-NOATTN 과 같은 책 — 공개) · INS · V08 은 W 없음(정적).

명세가 정하지 않은 산수(최소 선택 · 여기서 선언 — 등록문에 옮긴다)
  K1 분위 선정: 선 이름 N(신호 · 시총이 선 이름) 안 내림차순(동점은 티커 차례) · 새 이름은 순위 ≤ round(qN)(≥ 1) · 기존 이름은 ≤ round(1.5qN).
      섹터 안 · 칸 안 선정은 그 묶음의 N 으로. LBS 는 섹터 이름 수 n_s(최대 나머지법 · 총 round(0.2N))로 같은 규칙(버퍼 round(1.5 n_s)).
  K2 β̂ 가 없는 이름(관측 < 200)은 LBS · QLT 선정에서 뺀다(β 띠 계산에서는 1.0 · v_core V2).
  K3 QLT 칸 z = (x − 칸 평균)/칸 sd(ddof 1 · 칸 선 이름 ≥ 3 · 아니면 0) · 성분 결측은 빼고 평균(선 성분 ≥ 2) · β̂ 3분위는 섹터 안.
  K4 VAL: E/P = TTM NI/ME · S/P = TTM 매출/ME(둘 다 백만 달러) · E ≤ 0 이면 E/P 는 섹터 안 최하위(동점 평균 순위) · 백분위 = v_core.pct01.
  K5 T+1 행: 체결 비중 · 거래량은 D0 와 같다(같은 결정) · 보유월 수익만 «옛 책(우주 안 · 비례 맞춤)의 첫날 × 새 책의 나머지 날» 로 잰다(첫날 가격 없으면 0).
  K6 S 층 거미줄: 시장 가닥 z = cond_S(2006-03 앞은 cond_L 로 이음 · R̂ 역사) · 기울기 = L 에서 추정한 같은 가닥 기울기(U E0) · 책 G2own z = θ = 1 목표 책의
      log BE/ME − w_B log BE/ME(v_cond.g2own_book · 결정일 PIT · 늦춤 0) 의 z_rolling240(최소 60) · 그 기울기 = L 짝(G2own:V02 · V07)이 있으면 L,
      없으면(V01 · V03 · 쌍둥이) S-E(2010-01~) 쌍 · 목표 y_S = θ = 1 목표 책 − w_B 의 보유월 수익(체결 마찰 없음).
  K7 군(🔧 검토 고침 · 등록 전): 웹마다 그 웹의 가닥끼리만 (가족 같음) ∪ (|ρ| ≥ 0.5) 전이적 폐포(v_cond.clusters_for) · ρ = F0 에서 잰 L 조건 z 쌍 상관 ·
      책 G2own(S) 는 L 짝이 있으면 그 L 조건 이름 · 없으면(V01 · V03 · 쌍둥이) F0 에서 잰 S 층 ρ(책 G2own z 대 시장 가닥 z · s_g2own_rho)로 잇는다 ·
      등록물(l_clusters) 은 F0 에서 한 번 · 등록문에 고정.
  K8 EAR ATTN 목표 y^A_s = VW r(θ = 1 목표 책 가운데 pct_책(a) > ½) − VW r(≤ ½)(기울기 전 책 · 순환 없음).
  K9 V08: 6월 달에만 새 선정 · 그 사이 달은 6월 선정 ∩ 그달 명단(시총이 선 이름) · 첫 6월(2010-06) 앞은 책 없음.
  K10 T-MOM-IND(S): GICS 섹터 12-2 = 섹터 안 이름 12-2 의 시총가중 평균 · 상위 round(0.3 × 섹터 수) 섹터의 모든 이름 시총가중 · 섹터 띠 끔(신호가 섹터라서 · 공개).
      (L): French 49 산업 · 결정 t 에 t−12..t−2 누적 수익 상위 30%(기업 수 ≥ 20) · 가중 = 기업 수 × 평균 시총(t−2) · y = P − Mkt.
  K11 T-CAP80: 중립 · 책 모두 시총을 그달 합집합 시총 80 백분위에서 자른 값으로 가중(옛 설계).

🚨 수익 · 신호-수익 통계를 계산하지 않는다 — 경로 계열(보유월 수익 · 거래량)을 굽기 · 검정(v_tests)에 넘길 뿐이다. --blind-smoke 는 산출을 열지 않고 지운다.

  python build/v_cards.py --selftest
  python build/v_cards.py --blind-smoke          실자료 눈가린 연기(S 층 카드 전부 · L 층 거미줄 · 참/거짓 · 모양만)
"""
from __future__ import annotations

import bisect
import copy
import io
import json
import math
import os
import sys
import time
import traceback

import numpy as np
import pandas as pd

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import v_core as C          # noqa: E402
import v_data as VD         # noqa: E402
import v_cond as VC         # noqa: E402

LAST_DECISION = "2026-07"           # 보유 2026-08 까지(S 창 끝)
S_ARM_FROM = "2014-05"              # 워밍업 첫 보유달 2014-06 의 결정 달
S_EST_FROM = VD.SE_FROM             # S-E 추정 전용 연장 2010-01~
L_AXIS = ("1926-07", "2026-08")
S_SPLICE = VC.S_FROM                # 2006-03 — S 조건 이음 시작

# ══════════════════════════════════════════════════════════════════════════
#  카드(명세 slate) · 쌍둥이
# ══════════════════════════════════════════════════════════════════════════
BASE = {"select": "union", "signal": None, "q": 0.30, "buffer": True, "sband": C.SECTOR_BAND, "sector_on": True, "fill": C.FILL,
        "theta0": C.THETA0, "dtheta": C.DTHETA, "beta_band": True, "cost": "flat", "excl_ch": False, "attn": False, "phi": None,
        "ob_min": 5, "web": False, "hv": False, "adopt": "measure", "forward_only": False, "cap80": False, "qlt_cells": "sector_beta3",
        "use_sp": True, "prof": "op", "val_bm": False, "web_add": (), "web_lit": False, "web_g2": False, "v_demean": False,
        "sector_neutral": False, "layers": ("L", "S"), "status": "built"}
CARDS = {
    "V01": dict(BASE, key="MOM", name="MOM — 가격 모멘텀 12-2", family="모멘텀(과소반응)", signal="mom", q=0.30, web=True, hv=True,
                adopt="web+alloc"),
    "V02": dict(BASE, key="LBS", name="LBS — 섹터 안 저베타(레버리지 제약)", family="저위험", select="lbs", signal="lowbeta", q=0.20,
                sband=C.SECTOR_BAND_LBS, beta_band=False, web=True, hv=True, adopt="alloc_only"),
    "V03": dict(BASE, key="LIQ", name="LIQ — 유동성 공급 반전(IRRX)", family="유동성 공급", signal="irrx", q=0.30, buffer=False, fill=C.FILL_LIQ,
                theta0=C.THETA0_LIQ, dtheta=C.DTHETA_LIQ, cost="liq", web=True, hv=True, adopt="web+alloc(FID)"),
    "V04": dict(BASE, key="INS", name="INS — 기회주의 내부자 매수(사적 정보)", family="사적 정보", select="ins", phi=0.5, layers=("S",)),
    "V05": dict(BASE, key="EAR", name="EAR — 실적발표 반응 드리프트 + 공시 부주의 제외", family="제한된 주의", signal="car", q=0.20, excl_ch=True,
                attn=True, layers=("S",)),
    "V06": dict(BASE, key="VAL", name="VAL — 섹터 안 가치(E/P · S/P)", family="가치", select="within_sector", signal="val", q=0.30, web=True,
                hv=True, adopt="web+alloc"),
    "V07": dict(BASE, key="QLT", name="QLT — 수익성 · 안전성(베타 3분위 안)", family="퀄리티", select="qlt", signal="qlt", q=0.30, web=True,
                hv=True, adopt="web+alloc"),
    "V08": dict(BASE, key="NI", name="NI — 순자사주(주주환원)", family="주주환원(순발행)", select="ni_june", signal="ni", forward_only=True,
                adopt="forward_only", layers=("S",), sector_neutral=True, sband=C.SECTOR_BAND_SN),
}
CARD_IDS = tuple(CARDS)
WEB_CARDS = ("V01", "V02", "V03", "V06", "V07")
ALLOC5 = ("V01", "V02", "V03", "V06", "V07")
ALLOC7 = ALLOC5 + ("V04", "V05")
# 쌍둥이 — 보고만(어떤 가족에도 들지 않는다). status: built | input_absent(자료 층에 입력 없음 · 짓지 않고 공개) | gated_f0(F0 커버리지 뒤)
TWINS = {
    "T-MOM-PANIC": dict(card="V01", mods={"web_add": (("PANICX", -1, "L"),)}, layers=("L",), label="재현(T05) · L 전용"),
    "T-MOM-SN": dict(card="V01", mods={"select": "within_sector", "sband": C.SECTOR_BAND_SN}, layers=("S",)),
    "T-MOM-IND": dict(card="V01", mods={"select": "sector_mom", "sector_on": False}, layers=("L", "S"), label="옛 V09 IND — MOM 분해 쌍둥이"),
    "T-MOM-10": dict(card="V01", mods={}, layers=("L",), proxy="T-MOM-10", label="L 충실도 — 10_Portfolios Hi PRIOR"),
    "T-LBS-SENT": dict(card="V02", mods={}, layers=("L",), status="input_absent", label="재현(T15) · Wurgler SENT 는 V 자료 층에 없다"),
    "T-LBS-LO20": dict(card="V02", mods={}, layers=("L",), proxy="T-LBS-LO20", label="L 충실도 — Portfolios_Formed_on_BETA Lo 20"),
    "T-LIQ-HL": dict(card="V03", mods={}, layers=("S",), status="gated_f0", label="이름별 고가·저가 스프레드 비용 — _pit_hl_cache 커버리지 F0 뒤"),
    "T-LIQ-DEMEAN": dict(card="V03", mods={"v_demean": True}, layers=("L", "S")),
    "T-LIQ-REV": dict(card="V03", mods={"signal": "rev"}, layers=("S",), label="원시 REV — L 충실도용"),
    "T-INS-G2": dict(card="V04", mods={"web_g2": True}, layers=("S",)),
    "T-INS-PHI25": dict(card="V04", mods={"phi": 0.25}, layers=("S",)),
    "T-INS-PHI75": dict(card="V04", mods={"phi": 0.75}, layers=("S",)),
    "T-EAR-G2": dict(card="V05", mods={"web_g2": True}, layers=("S",)),
    "T-EAR-NOCH": dict(card="V05", mods={"excl_ch": False}, layers=("S",)),
    "T-EAR-NOATTN": dict(card="V05", mods={"attn": False}, layers=("S",), label="= V05 S0 책(공개)"),
    "T-VAL-BM": dict(card="V06", mods={"val_bm": True}, layers=("S",)),
    "T-QLT-SLOW": dict(card="V07", mods={"web_add": (("SLOW", +1, "L·S"),)}, layers=("L", "S")),
    "T-QLT-CRED6": dict(card="V07", mods={}, layers=("L",), status="input_absent", label="U13 신용 조건은 V 자료 층에 없다(추론 부호)"),
    "T-QLT-NOBETA": dict(card="V07", mods={"qlt_cells": "sector"}, layers=("S",)),
}
for _sid in ("V01", "V02", "V03", "V06", "V07"):
    TWINS["T-%s-CAP80" % CARDS[_sid]["key"]] = dict(card=_sid, mods={"cap80": True}, layers=("S",), label="옛 80 백분위 상한 중립")
for _sid in ("V01", "V03", "V06", "V07"):
    TWINS["T-%s-NOBAND" % CARDS[_sid]["key"]] = dict(card=_sid, mods={"beta_band": False}, layers=("S",))
for _sid in ("V01", "V03", "V06"):
    TWINS["T-%s-LIT" % CARDS[_sid]["key"]] = dict(card=_sid, mods={"web_lit": True}, layers=("L", "S"),
                                                  label="〔초록〕 강등 가닥을 되살린 판(data/_vb_lit_open.json · 보고만)")


def spec_of(sid, twin=None, **over):
    """카드 spec(dict) — twin 이 있으면 그 수정 · over 는 굽기 선택(F0 결정: use_sp · prof · liq_emergency · gcommon)."""
    s = dict(CARDS[sid])
    s["sid"] = sid
    s["twin"] = twin
    if twin:
        tw = TWINS[twin]
        assert tw["card"] == sid
        s.update(tw["mods"])
        s["layers"] = tw.get("layers", s["layers"])
        s["status"] = tw.get("status", "built")
    for k, v in over.items():
        if k == "liq_emergency":
            if v and sid == "V03":
                s["theta0"], s["dtheta"] = C.THETA0_LIQ_EMERG, C.DTHETA_LIQ_EMERG
            continue
        s[k] = v
    return s


def strands_of(spec, status=None):
    """전략의 거미줄 가닥 [(조건, 부호, 층)] — v_cond.web(주 가닥) + 쌍둥이 수정(강등 가닥 되살림 · 더한 가닥 · 책 G2own)."""
    sid = spec["sid"]
    if not (spec.get("web") or spec.get("web_g2") or spec.get("web_add")):
        return []
    prim, twin = VC.web(sid, status) if spec.get("web") else ([], [])
    out = list(prim)
    if spec.get("web_lit"):
        out += [(c, sg, layer) for c, sg, layer, _why in twin]
    for c, sg, layer in spec.get("web_add") or ():
        out.append((c, sg, layer))
    if spec.get("web_g2"):
        out.append(("G2own:S", +1, "S"))
    seen, uniq = set(), []
    for x in out:
        if x[0] not in seen:
            uniq.append(x)
            seen.add(x[0])
    return uniq


def family_of(cond):
    if cond == "G2own:S":
        return "자기 값(HKS)"
    return VC.CONDS[cond][5]


# ══════════════════════════════════════════════════════════════════════════
#  결정 달 단면(자료 층 입력 → 이름 차례 배열)
# ══════════════════════════════════════════════════════════════════════════
class Cross:
    """결정 달 m 의 단면 — 시총이 선 명단 이름만(가중 · 선정 모두). inp = v_data.Layer.inputs(m)."""

    def __init__(self, m, inp):
        self.m = m
        mev = inp["me"]
        rows = [r for r in inp["members"] if (mev.get(r["t"]) or (None,))[0]]
        sig, ir, ea, ch, ins = inp["signals"], inp["irrx"], inp["ear"], inp["ch"], inp["ins"]
        self.t = [r["t"] for r in rows]
        self.pos = {t: j for j, t in enumerate(self.t)}
        self.k = [r["k"] for r in rows]
        self.gid = [r.get("gid") for r in rows]
        n = self.n = len(rows)
        self.me = np.array([float(mev[t][0]) for t in self.t])
        self.me_how = [mev[t][1] for t in self.t]
        wb = inp["w_B"]
        self.wB = np.array([float(wb.get(t, 0.0)) for t in self.t])
        if self.wB.sum() > 0:
            self.wB = self.wB / self.wB.sum()
        self.spx = np.array([bool(r["spx"]) for r in rows])
        self.ndx = np.array([bool(r["ndx_only"]) for r in rows])
        g = lambda t, key: (sig.get(t) or {}).get(key)
        nf = lambda v: np.nan if v is None else float(v)
        self.sec = [g(t, "sector") for t in self.t]
        self.beta = np.array([nf(g(t, "beta_fp")) for t in self.t])
        self.mom = np.array([nf(g(t, "mom12_2")) for t in self.t])
        self.mret = np.array([nf(g(t, "month_ret")) for t in self.t])
        F = [(g(t, "fund") or {}) for t in self.t]
        fget = lambda key: np.array([nf(f.get(key)) for f in F])
        self.ni, self.rev, self.be, self.asset = fget("ni_ttm"), fget("rev_ttm"), fget("be"), fget("asset")
        self.op, self.roa, self.lev, self.sroa = fget("op"), fget("roa_ttm"), fget("lev"), fget("sig_roa")
        self.irrx_s = np.array([nf((ir.get(t) or {}).get("s")) for t in self.t])
        self.ear_ok = np.array([bool((ea.get(t) or {}).get("eligible")) for t in self.t])
        self.car = np.array([nf((ea.get(t) or {}).get("car")) if (ea.get(t) or {}).get("eligible") else np.nan for t in self.t])
        self.attn = np.array([nf((ea.get(t) or {}).get("attn_primary")) for t in self.t])
        self.attn_twin = np.array([nf((ea.get(t) or {}).get("attn_twin")) for t in self.t])
        self.ch = np.array([int((ch.get(t) or {}).get("ch") or 0) for t in self.t])
        self.ins = [ins.get(t, "unk") for t in self.t]
        self.niv = np.array([nf((g(t, "ni_v08") or {}).get("ni")) for t in self.t])
        with np.errstate(divide="ignore", invalid="ignore"):
            self.logme = np.log(self.me)
        # T-CAP80 — 합집합 시총 80 백분위 자르기
        q80 = float(np.quantile(self.me, 0.8)) if n else 0.0
        self.me80 = np.minimum(self.me, q80)
        self.wB80 = self.me80 / self.me80.sum() if n else self.me80

    def book(self, w):
        return {self.t[j]: float(w[j]) for j in np.flatnonzero(w > 0)}

    def arr(self, book):
        return np.array([float(book.get(t, 0.0)) for t in self.t])

    def with_ni(self, niv):
        c = copy.copy(self)
        c.niv = niv
        return c


# ══════════════════════════════════════════════════════════════════════════
#  선정(K1 ~ K4 · K9 · K10)
# ══════════════════════════════════════════════════════════════════════════
def _rank_select(score, elig, names, q, prev, buffer, n_in=None):
    """한 묶음 안 선정 — 내림차순(동점 티커) · 새 이름 ≤ n_in · 기존 이름 ≤ n_keep. 돌려주는 것 선정 위치 목록."""
    idx = [i for i in np.flatnonzero(elig) if np.isfinite(score[i])]
    N = len(idx)
    if N == 0:
        return []
    order = sorted(idx, key=lambda i: (-score[i], names[i]))
    if n_in is None:
        n_in = max(1, int(round(q * N)))
        n_keep = max(n_in, int(round(C.BUFFER * q * N))) if buffer else n_in
    else:
        n_keep = max(n_in, int(round(C.BUFFER * n_in))) if buffer else n_in
    out = []
    for p, i in enumerate(order):
        if p < n_in or (buffer and prev and names[i] in prev and p < n_keep):
            out.append(i)
    return out


def _largest_remainder(total, shares):
    """총 total 을 몫 shares(합 1) 비례로 정수 배분 — 최대 나머지법(동점은 차례)."""
    raw = np.asarray(shares, float) * total
    base = np.floor(raw).astype(int)
    rem = int(total - base.sum())
    order = np.argsort(-(raw - base), kind="mergesort")
    for j in order[:max(rem, 0)]:
        base[j] += 1
    return base


def _groups(X, spec):
    if spec["select"] == "qlt" and spec.get("qlt_cells", "sector_beta3") == "sector_beta3":
        out = [None] * X.n
        for s in set(x for x in X.sec if x):
            idx = [i for i in range(X.n) if X.sec[i] == s and np.isfinite(X.beta[i])]
            if not idx:
                continue
            b = X.beta[idx]
            order = sorted(range(len(idx)), key=lambda j: (b[j], X.t[idx[j]]))
            for r, j in enumerate(order):
                out[idx[j]] = (s, min(2, int(3 * r / len(idx))))
        return out
    return list(X.sec)


def _cell_z(x, groups, elig):
    """칸 안 z(K3) — 칸 선 이름 ≥ 3 · sd > 0 이면 (x − 평균)/sd · 아니면 0 · 결측은 NaN."""
    z = np.full(len(x), np.nan)
    for gname in set(g for g in groups if g is not None):
        idx = [i for i in range(len(x)) if groups[i] == gname and elig[i] and np.isfinite(x[i])]
        if not idx:
            continue
        v = x[idx]
        if len(idx) >= 3 and np.std(v, ddof=1) > 0:
            z[idx] = (v - v.mean()) / np.std(v, ddof=1)
        else:
            z[idx] = 0.0
    return z


def _pct_within(x, groups, elig):
    out = np.full(len(x), np.nan)
    for gname in set(g for g in groups if g is not None):
        idx = [i for i in range(len(x)) if groups[i] == gname and elig[i] and np.isfinite(x[i])]
        p = C.pct01({i: float(x[i]) for i in idx})
        for i, v in p.items():
            out[i] = v
    return out


def signal_of(X, spec):
    """(점수 · 선 이름 마스크 · 묶음) — 점수가 클수록 먼저 뽑힌다."""
    sg = spec["signal"]
    n = X.n
    true = np.ones(n, bool)
    if sg == "mom":
        return X.mom, np.isfinite(X.mom), None
    if sg == "irrx":
        return X.irrx_s, np.isfinite(X.irrx_s), None
    if sg == "rev":
        return -X.mret, np.isfinite(X.mret), None
    if sg == "car":
        el = X.ear_ok & np.isfinite(X.car)
        if spec.get("excl_ch"):
            el &= X.ch == 0
        return X.car, el, None
    if sg == "lowbeta":
        return -X.beta, np.isfinite(X.beta) & np.array([s is not None for s in X.sec]), list(X.sec)
    if sg == "val":
        with np.errstate(divide="ignore", invalid="ignore"):
            ep = np.where(np.isfinite(X.ni), X.ni / X.me, np.nan)
            sp = np.where(np.isfinite(X.rev) & (X.rev > 0), X.rev / X.me, np.nan)
            bm = np.where(np.isfinite(X.be) & (X.be > 0), X.be / X.me, np.nan)
        ep = np.where(np.isfinite(ep) & (X.ni <= 0), -1e9, ep)                         # K4 — E ≤ 0 이면 최하위
        groups = list(X.sec)
        has_sec = np.array([s is not None for s in groups])
        el = np.isfinite(ep) & has_sec
        p_ep = _pct_within(ep, groups, el)
        parts = [p_ep]
        if spec.get("use_sp", True):
            parts.append(_pct_within(sp, groups, el & np.isfinite(sp)))
        if spec.get("val_bm"):
            parts.append(_pct_within(bm, groups, el & np.isfinite(bm)))
        P = np.vstack(parts)
        cnt = np.isfinite(P).sum(0)
        sc = np.where(cnt > 0, np.nansum(np.where(np.isfinite(P), P, 0.0), axis=0) / np.maximum(cnt, 1), np.nan)
        return sc, el & np.isfinite(sc), groups
    if sg == "qlt":
        groups = _groups(X, spec)
        el0 = np.array([g is not None for g in groups])
        prof = X.op if spec.get("prof", "op") == "op" else X.roa
        comps = [_cell_z(prof, groups, el0), _cell_z(-X.lev, groups, el0), _cell_z(-X.sroa, groups, el0)]
        Zc = np.vstack(comps)
        nc = np.isfinite(Zc).sum(0)
        sc = np.where(nc >= 2, np.nansum(np.where(np.isfinite(Zc), Zc, 0.0), axis=0) / np.maximum(nc, 1), np.nan)
        return sc, el0 & (nc >= 2), groups
    if sg == "ni":
        return -X.niv, np.isfinite(X.niv) & (X.niv < 0), None
    raise KeyError(sg)


def select(X, spec, prev=None, ni_hold=None):
    """선정 마스크(bool 배열) — prev = 앞 달 선정 티커 집합(버퍼) · ni_hold = V08 6월 선정 티커 집합(6월이 아닌 달)."""
    n = X.n
    mask = np.zeros(n, bool)
    sel = spec["select"]
    if sel == "ins":
        return np.array([f == "OB" for f in X.ins])
    if sel == "ni_june":
        if X.m[5:7] == "06":
            sc, el, _ = signal_of(X, spec)
            return el.copy()
        if ni_hold is None:
            return None
        return np.array([t in ni_hold for t in X.t])
    if sel == "sector_mom":
        secs = sorted(set(s for s in X.sec if s))
        smom = {}
        for s in secs:
            idx = [i for i in range(n) if X.sec[i] == s and np.isfinite(X.mom[i])]
            if idx:
                w = X.me[idx]
                smom[s] = float((w * X.mom[idx]).sum() / w.sum())
        k = max(1, int(round(spec["q"] * len(smom))))
        top = set(sorted(smom, key=lambda s: (-smom[s], s))[:k])
        return np.array([X.sec[i] in top for i in range(n)])
    score, elig, groups = signal_of(X, spec)
    if sel == "union":
        for i in _rank_select(score, elig, X.t, spec["q"], prev, spec["buffer"]):
            mask[i] = True
        return mask
    if sel == "lbs":
        secs = sorted(set(groups[i] for i in range(n) if elig[i] and groups[i]))
        capsh = np.array([X.me[[i for i in range(n) if elig[i] and groups[i] == s]].sum() for s in secs])
        N = int(elig.sum())
        tot = int(round(spec["q"] * N))
        ns = _largest_remainder(tot, capsh / capsh.sum()) if len(secs) else []
        for s, n_s in zip(secs, ns):
            ns_ = min(int(n_s), sum(1 for i in range(n) if elig[i] and groups[i] == s))
            if ns_ <= 0:
                continue
            e2 = elig & np.array([g == s for g in groups])
            for i in _rank_select(score, e2, X.t, None, prev, spec["buffer"], n_in=ns_):
                mask[i] = True
        return mask
    if sel in ("within_sector", "qlt"):
        if spec["signal"] == "mom":
            groups = list(X.sec)
            elig = elig & np.array([s is not None for s in groups])
        for gname in sorted(set(g for g in groups if g is not None), key=str):
            e2 = elig & np.array([g == gname for g in groups])
            for i in _rank_select(score, e2, X.t, spec["q"], prev, spec["buffer"]):
                mask[i] = True
        return mask
    raise KeyError(sel)


# ══════════════════════════════════════════════════════════════════════════
#  책(명세 common_frame.book · theta_blend · beta_band)
# ══════════════════════════════════════════════════════════════════════════
def projector(X, spec, cap=C.ISSUER_ACTIVE_CAP):
    wB = X.wB80 if spec.get("cap80") else X.wB
    return lambda x: C.project_active(x, wB, X.sec, X.ndx, cap=cap, sband=spec["sband"], sector_on=spec["sector_on"])[0]


def strategy_weights(X, spec, mask, lam=None):
    """전략 선정 책 w_f(투영 전) — 선정 이름의 상한 없는 시총가중(INS 는 φ 섞기) · EAR ATTN 기울기. 돌려주는 것 (w_f | None, info)."""
    me = X.me80 if spec.get("cap80") else X.me
    wB = X.wB80 if spec.get("cap80") else X.wB
    info = {"n_sel": int(mask.sum()) if mask is not None else 0}
    if spec["select"] == "ins":
        os_ = np.array([f == "OS" for f in X.ins])
        wbx = np.where(os_, 0.0, wB)
        wbx = wbx / wbx.sum() if wbx.sum() > 0 else wB.copy()
        n_ob = int(mask.sum())
        info.update(n_ob=n_ob, n_os=int(os_.sum()))
        if n_ob < spec["ob_min"]:
            return wbx, dict(info, ob_to_bench=True)
        wob = np.where(mask, me, 0.0)
        wob = wob / wob.sum()
        phi = float(spec["phi"])
        return phi * wob + (1.0 - phi) * wbx, dict(info, ob_to_bench=False)
    if mask is None or not mask.any():
        return None, info
    if spec.get("sector_neutral"):
        # V08(검토 고침) — 섹터 중립 LBS 식: 섹터마다 선정 이름의 시총가중 × 그 섹터 w_B 몫 · 선정 이름이 없는 섹터는 w_B 그대로 · w_B 몫 0 인 섹터(NDX 전용뿐)는 비운다
        secs = ["_none" if x is None else str(x) for x in X.sec]
        w = np.zeros(X.n)
        n_fill = 0
        for g in sorted(set(secs)):
            idx = np.array([i for i in range(X.n) if secs[i] == g], int)
            wb_g = float(wB[idx].sum())
            if wb_g <= 0:
                continue
            sel = idx[mask[idx]]
            if len(sel) and float(me[sel].sum()) > 0:
                w[sel] = wb_g * me[sel] / float(me[sel].sum())
            else:
                w[idx] = wB[idx]
                n_fill += 1
        info["sector_fill"] = n_fill
        return w / w.sum(), info
    w = np.where(mask, me, 0.0)
    w = w / w.sum()
    if spec.get("attn") and lam is not None:
        a = X.attn
        w, ow = C.attn_tilt(w, a, lam)
        info["attn_oneway"] = ow
    return w, info


def target_book(X, spec, mask, theta, lam=None, gcommon=False):
    """최종 목표 책(이름 차례 배열) — w_f → 능동 상한 투영 → w_B + θ(w_p − w_B) → (G-COMMON 크기 중립) → β 띠(LBS 면제). (w | None, info)."""
    wf, info = strategy_weights(X, spec, mask, lam)
    if wf is None:
        return None, info
    wB = X.wB80 if spec.get("cap80") else X.wB
    proj = projector(X, spec)
    wp, pinfo = C.project_active(wf, wB, X.sec, X.ndx, sband=spec["sband"], sector_on=spec["sector_on"])
    info["proj"] = {k: pinfo[k] for k in ("iters", "shrink", "feasible")}
    w = wB + float(theta) * (wp - wB)
    if gcommon:
        w, sinfo = C.size_neutral(w, wB, X.logme, proj)
        info["size_gap"] = sinfo["gap"]
    if spec["beta_band"]:
        w, binfo = C.beta_band(w, wB, X.beta, proj)
        info["beta"] = binfo
    w = np.where(w > 1e-15, w, 0.0)
    w = w / w.sum()
    return w, info


# ══════════════════════════════════════════════════════════════════════════
#  S 층 — 월 단면 · 선정 경로 · 책 · 체결 경로 · 거미줄
# ══════════════════════════════════════════════════════════════════════════
class SLayer:
    """S 층(PIT) 한 벌 — Lr = v_data.Layer. months = 결정 달(2010-01 ~ LAST_DECISION). 🚨 경로 계열만 만든다(통계 없음)."""

    def __init__(self, Lr, months=None, clusters=None, lit_status=None):
        self.Lr = Lr
        self.U = Lr.pit
        ms = [m for m in self.U.months if S_EST_FROM <= m <= LAST_DECISION and VD.mshift(m, 1) in self.U.me_idx]
        self.months = months or ms
        self.X, self._r, self._r1, self._sel = {}, {}, {}, {}
        self.clusters = clusters
        self.lit_status = lit_status
        self._spy_m = None
        self._liq = None

    # ── 입력 ──────────────────────────────────────────────────────────────
    def cross(self, m):
        if m not in self.X:
            self.X[m] = Cross(m, self.Lr.inputs(m))
        return self.X[m]

    def hold(self, m):
        """결정 달 m → 보유월 m+1 이름별 수익(D0 · pit_panel.y_stop) — 🚨 수익 입력(굽기 · 연기에서만)."""
        if m not in self._r:
            self._r[m] = self.U.hold_ret(m)
        return self._r[m]

    def hold_split(self, m):
        """T+1(K5) — {명단 티커: (첫날 수익, 나머지 날 수익)} · 결측 규칙은 hold 와 같다."""
        if m in self._r1:
            return self._r1[m]
        import pit_panel as PP
        U = self.U
        i, i1 = U.me_idx[m], U.me_idx[VD.mshift(m, 1)]
        out = {}
        for r in U.members(m):
            k = r["k"]
            p = np.asarray(U.PX[k], float)
            if not (p[i] == p[i] and p[i] > 0):
                out[r["t"]] = (None, None)
                continue
            if PP.y_stop(U.W, k, i, i1) == "missing":
                out[r["t"]] = (None, None)
                continue
            seg = p[i + 1:i1 + 1]
            ok = np.where(seg == seg)[0]
            if not len(ok):
                out[r["t"]] = (0.0, 0.0)
                continue
            last = float(seg[ok[-1]])
            if i + 1 <= i1 and p[i + 1] == p[i + 1] and p[i + 1] > 0:
                out[r["t"]] = (float(p[i + 1] / p[i] - 1.0), float(last / p[i + 1] - 1.0))
            else:
                out[r["t"]] = (0.0, float(last / p[i] - 1.0))
        self._r1[m] = out
        return out

    def spy_hold(self, m):
        """보유월 m+1 의 SPY 총수익(격자 월말 대 월말) — 🚨 수익."""
        U = self.U
        i, i1 = U.me_idx[m], U.me_idx[VD.mshift(m, 1)]
        return float(U.spy[i1] / U.spy[i] - 1.0)

    def liq_rate(self):
        if self._liq is None:
            self._liq = C.liq_cost_rate(self.U.spy, self.U.dates)
        return self._liq

    # ── 선정 경로(θ 와 무관 · 버퍼 · V08 6월) ────────────────────────────────
    def selections(self, spec):
        key = (spec["sid"], spec.get("twin"), spec["select"], spec["signal"], spec.get("excl_ch"), spec.get("use_sp"), spec.get("prof"),
               spec.get("val_bm"), spec.get("qlt_cells"), spec["q"], spec["buffer"])
        if key in self._sel:
            return self._sel[key]
        out, prev, hold = {}, None, None
        for m in self.months:
            X = self.cross(m)
            mask = select(X, spec, prev=prev, ni_hold=hold)
            if spec["select"] == "ni_june" and mask is not None and m[5:7] == "06":
                hold = {X.t[i] for i in np.flatnonzero(mask)}
            out[m] = mask
            prev = None if mask is None else {X.t[i] for i in np.flatnonzero(mask)}
        self._sel[key] = out
        return out

    # ── 책 ────────────────────────────────────────────────────────────────
    def books(self, spec, theta=None, lam=None, gcommon=False, months=None):
        """{결정 달: {티커: 비중}} — theta = 상수(정적 · F) 또는 {달: θ_t}(W) · lam = {달: λ_t}(EAR ATTN)."""
        sels = self.selections(spec)
        out, info = {}, {}
        for m in (months or self.months):
            mask = sels.get(m)
            if mask is None and spec["select"] not in ("ins",):
                continue
            th = theta.get(m) if isinstance(theta, dict) else (spec["theta0"] if theta is None else theta)
            if th is None:
                continue
            X = self.cross(m)
            w, inf = target_book(X, spec, mask, th, lam=(lam or {}).get(m) if lam else None, gcommon=gcommon)
            if w is None:
                continue
            b = X.book(w)
            C.assert_stock_book(b)
            out[m] = b
            info[m] = inf
        return out, info

    def wB(self, m, cap80=False):
        X = self.cross(m)
        return X.book(X.wB80 if cap80 else X.wB)

    # ── 수익 쪽 입력(🚨 굽기 · 연기에서만) ─────────────────────────────────
    def active_y(self, books, cap80=False):
        """θ = 1 목표 책의 능동수익 y_S(보유 달 색인) = R(책) − R(w_B)(K6 · 체결 마찰 없음)."""
        out = {}
        for m, b in books.items():
            r = self.hold(m)
            rb, rw = C.book_ret(b, r), C.book_ret(self.wB(m, cap80), r)
            if rb is not None and rw is not None:
                out[VD.mshift(m, 1)] = rb - rw
        return pd.Series(out, dtype=float).sort_index().rename("y_S") if out else pd.Series(dtype=float)

    def attn_y(self, books):
        """EAR ATTN 목표 y^A(K8) — VW r(pct_책(a) > ½) − VW r(≤ ½)."""
        out = {}
        for m, b in books.items():
            X = self.cross(m)
            r = self.hold(m)
            names = list(b)
            pc = C.pct01({t: (None if not np.isfinite(X.attn[X.pos[t]]) else float(X.attn[X.pos[t]])) for t in names})
            hi = {t: b[t] for t in names if pc.get(t, 0.5) > 0.5}
            lo = {t: b[t] for t in names if pc.get(t, 0.5) <= 0.5}
            if hi and lo:
                a, c = C.book_ret(hi, r), C.book_ret(lo, r)
                if a is not None and c is not None:
                    out[VD.mshift(m, 1)] = a - c
        return pd.Series(out, dtype=float).sort_index() if out else pd.Series(dtype=float)

    def g2own_x(self, books, cap80=False):
        """책 G2own x(결정 달) — log VW BE/ME(책) − log VW BE/ME(w_B)(v_cond.g2own_book · 결정일 PIT)."""
        out = {}
        for m, b in books.items():
            X = self.cross(m)
            be = {t: (None if not np.isfinite(X.be[j]) else float(X.be[j])) for j, t in enumerate(X.t)}
            me = {t: float(X.me[j]) for j, t in enumerate(X.t)}
            v = VC.g2own_book(b, self.wB(m, cap80), be, me)
            if v is not None:
                out[m] = v
        return pd.Series(out, dtype=float).sort_index() if out else pd.Series(dtype=float)

    # ── 체결 경로(🚨 수익 입력) ──────────────────────────────────────────────
    def path(self, targets, fill=C.FILL, rate="flat", start=S_ARM_FROM, end=LAST_DECISION):
        """목표 책 경로 → 보유 달 계열 DataFrame(S · S_t1 · traded · rate · B(SPY TR) · beta(체결 책 FP β̂) · n · n_miss).
        첫 결정 달은 목표에서 시작(첫 매수 미과금 · t_core 와 같다) · 목표가 빈 달이 끼면 경로가 끊기고 다시 시작한다."""
        ms = [m for m in self.months if start <= m <= end]
        rates = self.liq_rate() if rate == "liq" else None
        Ed = None
        rows = {}
        for m in ms:
            T = targets.get(m)
            if T is None:
                Ed = None
                continue
            X = self.cross(m)
            if Ed is None:
                E, tr = dict(T), 0.0
                old = None
            else:
                E, tr = C.execute_book(Ed, T, fill=fill)
                old = {t: v for t, v in Ed.items() if t in X.pos}
            r = self.hold(m)
            Ed_new, R, nmiss = C.drift_book(E, r)
            sp = self.hold_split(m)
            r1 = {t: v[0] for t, v in sp.items()}
            rr = {t: v[1] for t, v in sp.items()}
            R1 = C.book_ret(old if old else E, r1)
            Rr = C.book_ret(E, rr)
            beta = float(sum(E[t] * (X.beta[X.pos[t]] if np.isfinite(X.beta[X.pos[t]]) else 1.0) for t in E if t in X.pos))
            h = VD.mshift(m, 1)
            ew = [v for t, v in r.items() if v is not None and t in X.pos and np.isfinite(v)]
            rows[h] = {"S": R, "S_t1": ((1 + R1) * (1 + Rr) - 1.0) if (R1 is not None and Rr is not None) else R, "traded": tr,
                       "rate": (rates.get(m, C.S_COST) if rates else C.S_COST), "B": self.spy_hold(m), "B_EW": (float(np.mean(ew)) if ew else None),
                       "beta": beta, "n": len(E), "n_miss": nmiss}
            Ed = Ed_new
        df = pd.DataFrame.from_dict(rows, orient="index")
        if len(df):
            df.index = pd.PeriodIndex(df.index, freq="M")
        return df

    def path_split(self, targets, shares, fill_a=C.FILL_LIQ, rate_a="liq", fill_b=C.FILL, rate_b="flat", start=S_ARM_FROM, end=LAST_DECISION):
        """두 소매 체결 경로(배분기 순액 책 · 검토 고침 A5) — targets = {달: 순액 목표 책} · shares = {달: {티커: 소매 a(LIQ) 몫 ∈ [0, 1]}}.
        소매 a = 순액 목표 × 몫(LIQ 규칙: 전량 체결 · 상태 의존 비용) · 소매 b = 나머지(½ 체결 · 10bp). 두 소매는 따로 흘러가고(같은 이름 수익) 체결 뒤 함께 합 1 로 맞춘다.
        거래량 = 이름마다 두 소매 순 거래 |Δa + Δb| 의 합(안에서 상쇄 · 이중 과금 없음) · 비율 = 이름마다 |Δa| · |Δb| 가중 혼합 비율의 거래량 가중 평균
        (거래 없는 달은 소매 크기 가중 비율 — 펀드 되돌림 비용 c_f 에 쓰인다).
        돌려주는 것은 path 와 같은 모양(S · S_t1 · traded · rate · B · B_EW · beta · n · n_miss). 🚨 수익 입력."""
        ms = [m for m in self.months if start <= m <= end]
        ra = self.liq_rate() if rate_a == "liq" else None
        rb = self.liq_rate() if rate_b == "liq" else None
        Ea_d = Eb_d = None
        rows = {}
        for m in ms:
            T = targets.get(m)
            if T is None:
                Ea_d = Eb_d = None
                continue
            X = self.cross(m)
            sh = shares.get(m) or {}
            Ta = {t: v * float(sh.get(t, 0.0)) for t, v in T.items()}
            Tb = {t: v * (1.0 - float(sh.get(t, 0.0))) for t, v in T.items()}
            rate_am = ra.get(m, C.S_COST) if ra else C.S_COST
            rate_bm = rb.get(m, C.S_COST) if rb else C.S_COST
            if Ea_d is None:
                Ea, Eb, tr, rate = dict(Ta), dict(Tb), 0.0, None
                old = None
            else:
                Ea = C.execute_abs(Ea_d, Ta, fill=fill_a)
                Eb = C.execute_abs(Eb_d, Tb, fill=fill_b)
                tot = sum(Ea.values()) + sum(Eb.values())
                if tot > 0:
                    Ea = {k: v / tot for k, v in Ea.items()}
                    Eb = {k: v / tot for k, v in Eb.items()}
                names = set(Ea) | set(Eb) | set(Ea_d) | set(Eb_d)
                tr, cost = 0.0, 0.0
                for k in names:
                    da = Ea.get(k, 0.0) - Ea_d.get(k, 0.0)
                    db = Eb.get(k, 0.0) - Eb_d.get(k, 0.0)
                    net = abs(da + db)
                    if net <= 0:
                        continue
                    wa, wb = abs(da), abs(db)
                    tr += net
                    cost += net * ((rate_am * wa + rate_bm * wb) / (wa + wb) if (wa + wb) > 0 else rate_bm)
                rate = (cost / tr) if tr > 0 else None
                comb_d = {k: Ea_d.get(k, 0.0) + Eb_d.get(k, 0.0) for k in set(Ea_d) | set(Eb_d)}
                old = {t: v for t, v in comb_d.items() if t in X.pos and v > 0}
            E = {k: Ea.get(k, 0.0) + Eb.get(k, 0.0) for k in set(Ea) | set(Eb)}
            E = {k: v for k, v in E.items() if v > 0}
            if rate is None:                                                    # 거래 없는 달 — 소매 크기 가중 비율(되돌림 비용 c_f 에 쓰인다)
                sa = float(sum(Ea.values())) / max(float(sum(E.values())), 1e-300)
                rate = rate_am * sa + rate_bm * (1.0 - sa)
            r = self.hold(m)
            Ed_new, R, nmiss = C.drift_book(E, r)
            g = {k: (1.0 + (r[k] if (r.get(k) is not None and np.isfinite(r.get(k))) else (R if R is not None else 0.0))) for k in E}
            tot_g = sum(E[k] * g[k] for k in E)
            Ea_d = {k: v * g[k] / tot_g for k, v in Ea.items() if k in g and v > 0} if tot_g > 0 else dict(Ea)
            Eb_d = {k: v * g[k] / tot_g for k, v in Eb.items() if k in g and v > 0} if tot_g > 0 else dict(Eb)
            spl = self.hold_split(m)
            r1 = {t: v[0] for t, v in spl.items()}
            rr = {t: v[1] for t, v in spl.items()}
            R1 = C.book_ret(old if old else E, r1)
            Rr = C.book_ret(E, rr)
            beta = float(sum(E[t] * (X.beta[X.pos[t]] if np.isfinite(X.beta[X.pos[t]]) else 1.0) for t in E if t in X.pos))
            h = VD.mshift(m, 1)
            ew = [v for t, v in r.items() if v is not None and t in X.pos and np.isfinite(v)]
            rows[h] = {"S": R, "S_t1": ((1 + R1) * (1 + Rr) - 1.0) if (R1 is not None and Rr is not None) else R, "traded": tr, "rate": rate,
                       "B": self.spy_hold(m), "B_EW": (float(np.mean(ew)) if ew else None), "beta": beta, "n": len(E), "n_miss": nmiss,
                       "share_a": float(sum(Ea.values()))}
        df = pd.DataFrame.from_dict(rows, orient="index")
        if len(df):
            df.index = pd.PeriodIndex(df.index, freq="M")
        return df

    # ── 거미줄(S · K6 · K7) ────────────────────────────────────────────────
    def web(self, spec, Lweb, F_books=None, y_S=None, opt=None):
        """S 층 결정 달 v_t — Lweb = LLayer.web_slopes(spec) 결과(시장 가닥 L 기울기) · F_books = θ = 1 목표 책(책 G2own z) · y_S(보유 달 능동).
        돌려주는 것 dict(v (Series · S 달) · u · n_act · strands · …)."""
        opt = dict({"r2": "cluster", "shrink": True}, **(opt or {}))
        strands = [s for s in strands_of(spec, self.lit_status) if s[2] in ("L·S", "S")]
        axis = pd.period_range(L_AXIS[0], LAST_DECISION, freq="M")
        if not strands:
            v = pd.Series(0.0, index=pd.PeriodIndex(self.months, freq="M"))
            return {"v": v, "u": v, "n_act": v.astype(int), "strands": []}
        Zs = s_conditions(self.Lr)
        cols, B, fams, cls, signs = [], [], [], [], []
        g2x = None
        for c, sg, layer in strands:
            if c.startswith("G2own"):
                if g2x is None:
                    g2x = self.g2own_x(F_books, spec.get("cap80")) if F_books is not None else pd.Series(dtype=float)
                z = VC.z_rolling(g2x).reindex(axis) if len(g2x) else pd.Series(np.nan, index=axis)
                lk = "G2own:%s" % spec["sid"]
                if lk in VC.CONDS and Lweb is not None and lk in Lweb["b_c"]:
                    bc = Lweb["b_c"][lk].reindex(axis)
                    cl = lk                                                     # L 짝 가닥 — 그 L 조건의 이름으로 군을 잇는다
                else:
                    y = pd.Series(y_S, dtype=float) if y_S is not None else pd.Series(dtype=float)
                    zz = z.to_numpy(float)
                    yy = y.reindex(axis).to_numpy(float)
                    sl = C.slope_path(zz, yy, sg, shrink=opt["shrink"])
                    bc = pd.Series(sl["b_c"], index=axis)
                    cl = "G2own:S"                                              # S 전용 — F0 에서 잰 S 층 ρ 로 잇는다(K7 검토 고침)
                cols.append(z)
                B.append(bc)
                fams.append(family_of("G2own:S"))
                cls.append(cl)
                signs.append(sg)
                continue
            z = Zs[c].reindex(axis)
            bc = Lweb["b_c"][c].reindex(axis) if (Lweb is not None and c in Lweb["b_c"]) else pd.Series(np.nan, index=axis)
            cols.append(z)
            B.append(bc)
            fams.append(family_of(c))
            cls.append(c)
            signs.append(sg)
        cls = web_cluster_labels(self.clusters, cls, spec["sid"])
        Zf = np.column_stack([x.to_numpy(float) for x in cols])
        Bc = np.column_stack([x.to_numpy(float) for x in B])
        act = np.isfinite(Zf) & np.isfinite(Bc)
        res = C.direction_eval(Zf, Bc, act, signs, fams, cls, r2=opt["r2"])
        v = pd.Series(res["v"], index=axis)
        if spec.get("v_demean"):
            v = (v - v.expanding(1).mean().shift(1).fillna(0.0)).clip(-1.0, 1.0)      # T-LIQ-DEMEAN(실시간 확장 평균 · 띠 범위)
        sm = pd.PeriodIndex(self.months, freq="M")
        return {"v": v.reindex(sm).fillna(0.0), "u": pd.Series(res["u"], index=axis).reindex(sm), "n_act": pd.Series(res["n_act"], index=axis).reindex(sm),
                "n_clusters_act": pd.Series(res["n_clusters_act"], index=axis).reindex(sm), "strands": [s[0] for s in strands], "clusters": cls}

    def theta_map(self, spec, v):
        th = C.theta_path(pd.Series(v).reindex(pd.PeriodIndex(self.months, freq="M")).fillna(0.0).to_numpy(), spec["theta0"], spec["dtheta"])
        return {m: float(x) for m, x in zip(self.months, th)}

    def attn_lambda(self, y_A):
        """λ_t = ½·band(u^A_t)(u^A = 축소 NW(6) t · 부호 잘림 · S-E 쌍) — {결정 달: λ}."""
        axis = pd.PeriodIndex(self.months, freq="M")
        y = pd.Series(y_A, dtype=float).reindex(axis).to_numpy(float)
        mp = C.mean_path(y, +1)
        lam = 0.5 * C.band(np.nan_to_num(mp["u"], nan=0.0))
        return {m: float(max(0.0, x)) for m, x in zip(self.months, lam)}, mp


_SZ = {}


def s_conditions(Lr):
    """S 층 시장 조건 z(K6) — cond_S(2006-03~) 앞을 cond_L 로 이은 표(결정 달 × 조건)."""
    key = id(Lr)
    if key not in _SZ:
        zl, zs = Lr.cond_L(), Lr.cond_S()
        a = zl.loc[zl.index < pd.Period(S_SPLICE, "M")]
        _SZ[key] = pd.concat([a, zs]).sort_index()
    return _SZ[key]


# ══════════════════════════════════════════════════════════════════════════
#  L 층 — French 대리 · 거미줄 기울기 · θ · 다리 팔(🚨 L 층 값은 저장소에 쓰지 않는다 · D1)
# ══════════════════════════════════════════════════════════════════════════
class LLayer:
    """L 층 한 벌 — zL = cond_L(결정 달 × 조건) · proxies = {sid | 쌍둥이: y = P − Mkt(보유 달)} · mkt = French Mkt TR · rf."""

    def __init__(self, zL, proxies, mkt, rf, clusters=None, lit_status=None, taus=None):
        self.axis = pd.period_range(L_AXIS[0], L_AXIS[1], freq="M")
        self.Z = pd.DataFrame(zL).reindex(self.axis)
        self.P = {k: pd.Series(v, dtype=float).reindex(self.axis) for k, v in proxies.items()}
        self.mkt = pd.Series(mkt, dtype=float).reindex(self.axis)
        self.rf = pd.Series(rf, dtype=float).reindex(self.axis)
        self.clusters = clusters
        self.lit_status = lit_status
        self.taus = taus or {}
        self._sl = {}

    @classmethod
    def vintage(cls, vintage, clusters=None, lit_status=None, taus=None):
        """French 판 민감도(보고만 · 명세 tests.L_layer.windows «French 빈티지(2024-12 고정 사본)») — 같은 규칙 · 같은 군 등록물로 조건 · 대리 · Mkt · RF 를
        그 판 사본에서 다시 짓는다(쌍둥이 대리는 없다). 🚨 L 층 — 저장소에 쓰지 않는다."""
        zl = VC.conditions_L(VC.inputs_L(vintage))
        prox = {s: VD.l_proxy(s, vintage=vintage) for s in VD.L_PROXIES}
        f3 = VD.ff3("m", vintage=vintage)
        return cls(zl, prox, f3["Mkt"], f3["RF"], clusters=clusters, lit_status=lit_status, taus=taus)

    @classmethod
    def real(cls, Lr, clusters=None, lit_status=None, taus=None):
        prox = dict(Lr.l_proxy())
        prox["T-MOM-10"] = VD.l_proxy("V01", "T-MOM-10")
        prox["T-LBS-LO20"] = VD.l_proxy("V02", "T-LBS-LO20")
        prox["T-MOM-IND"] = ind_mom_proxy()
        f3 = VD.ff3("m")
        return cls(Lr.cond_L(), prox, f3["Mkt"], f3["RF"], clusters=clusters, lit_status=lit_status, taus=taus)

    def slope(self, cond, proxy, sign, shrink=True):
        k = (cond, proxy, sign, shrink)
        if k not in self._sl:
            bs = cond == "BSPRD"
            z = self.Z[cond].to_numpy(float) if cond in self.Z else np.full(len(self.axis), np.nan)
            y = self.P[proxy].to_numpy(float)
            self._sl[k] = C.slope_path(z, y, sign, C.PAIRS_MIN_BSPRD if bs else C.PAIRS_MIN, C.NW_SLOPE_BSPRD if bs else C.NW_SLOPE,
                                       shrink=shrink)
        return self._sl[k]

    def web_slopes(self, spec, shrink=True, proxy=None):
        """전략의 L 가닥 기울기 {조건: b^c Series} — S 층이 같은 기울기를 읽는다(U E0)."""
        proxy = proxy or (spec.get("proxy") or spec["sid"])
        out = {}
        for c, sg, layer in strands_of(spec, self.lit_status):
            if c in VC.CONDS and "L" in layer:
                out[c] = pd.Series(self.slope(c, proxy, sg, shrink)["b_c"], index=self.axis)
        return {"b_c": out}

    def web(self, spec, opt=None, Zover=None, proxy=None):
        """L 층 결정 달 거미줄 — dict(v, u, n_act, n_clusters_act, strands, first_active) · Zover = 위약 z 판(DataFrame · 같은 열)."""
        opt = dict({"r2": "cluster", "shrink": True}, **(opt or {}))
        proxy = proxy or spec["sid"]
        strands = [s for s in strands_of(spec, self.lit_status) if s[0] in VC.CONDS and "L" in s[2]]
        T = len(self.axis)
        if not strands:
            z0 = pd.Series(0.0, index=self.axis)
            return {"v": z0, "u": z0, "n_act": z0.astype(int), "strands": [], "first_active": None}
        Zsrc = self.Z if Zover is None else Zover
        Zf, Bc = [], []
        for c, sg, _ in strands:
            z = Zsrc[c].to_numpy(float)
            if Zover is None:
                sl = self.slope(c, proxy, sg, opt["shrink"])
            else:
                bs = c == "BSPRD"
                sl = C.slope_path(z, self.P[proxy].to_numpy(float), sg, C.PAIRS_MIN_BSPRD if bs else C.PAIRS_MIN,
                                  C.NW_SLOPE_BSPRD if bs else C.NW_SLOPE, shrink=opt["shrink"])
            Zf.append(z)
            Bc.append(sl["b_c"])
        Zf, Bc = np.column_stack(Zf), np.column_stack(Bc)
        act = np.isfinite(Zf) & np.isfinite(Bc)
        cls = web_cluster_labels(self.clusters, [s[0] for s in strands], spec["sid"])
        res = C.direction_eval(Zf, Bc, act, [s[1] for s in strands], [family_of(s[0]) for s in strands], cls, r2=opt["r2"])
        v = pd.Series(res["v"], index=self.axis)
        if spec.get("v_demean"):
            v = (v - v.expanding(1).mean().shift(1).fillna(0.0)).clip(-1.0, 1.0)      # T-LIQ-DEMEAN(실시간 확장 평균 · 띠 범위)
        na = pd.Series(res["n_act"], index=self.axis)
        fa = na.index[na.to_numpy() > 0]
        return {"v": v, "u": pd.Series(res["u"], index=self.axis), "n_act": na,
                "n_clusters_act": pd.Series(res["n_clusters_act"], index=self.axis), "strands": [s[0] for s in strands],
                "first_active": (str(fa[0]) if len(fa) else None), "clusters": cls}

    def theta(self, spec, v):
        return pd.Series(C.theta_path(pd.Series(v).reindex(self.axis).fillna(0.0).to_numpy(), spec["theta0"], spec["dtheta"]), index=self.axis)

    def arm(self, sid_proxy, theta, tau=None):
        """L 슬리브 = Mkt + θ_{t−1}·(P_f − Mkt)(보유 달) — 다리 [Mkt, P_f] · COST_ERAS × (흘러감 대비 Σ|Δw| + 내부 τ).
        🚨 수익 계열 — 굽기 · 눈가린 연기에서만. 돌려주는 것 dict(arm_legs 결과 + X · B · theta_hold)."""
        ok_der, bad = C.no_derivative_positions([("market_slot", "French Mkt"), ("french_leg", str(sid_proxy))])
        if not ok_der:
            raise SystemExit("🚨 L 다리에 파생 표식: %s" % bad)
        y = self.P[sid_proxy]
        th = pd.Series(theta, dtype=float).reindex(self.axis)
        th_hold = th.shift(1)
        W = pd.DataFrame({"Mkt": 1.0 - th_hold, "P": th_hold}, index=self.axis)
        R = pd.DataFrame({"Mkt": self.mkt, "P": self.mkt + y}, index=self.axis)
        ok = W.notna().all(axis=1) & R.notna().all(axis=1)
        W, R = W[ok], R[ok]
        rate = C.cost_rate_L(W.index)
        tau = self.taus.get(sid_proxy) if tau is None else tau
        a = C.arm_legs(W, R, rate, tau={"P": tau} if tau is not None else None)
        a["B"] = self.mkt.reindex(W.index)
        a["theta_hold"] = th_hold.reindex(W.index)
        return a


def twin_proxy(twin, sid=None):
    """L 층 쌍둥이의 대리 열쇠 — 충실도 쌍둥이(T-MOM-10 · T-LBS-LO20) · T-MOM-IND 는 제 대리 · 나머지는 카드 대리(기울기도 그 대리에서)."""
    if not twin:
        return sid
    d = TWINS[twin]
    return d.get("proxy") or ("T-MOM-IND" if twin == "T-MOM-IND" else d["card"])


def ind_mom_proxy():
    """T-MOM-IND L(K10) — French 49 산업 · t−12..t−2 누적 상위 30%(기업 수 ≥ 20) · 가중 = 기업 수 × 평균 시총 · y = P − Mkt(보유 달)."""
    R = VD.french("ind49", "vw_m")
    N = VD.french("ind49", "nfirms", pct=False).reindex(index=R.index, columns=R.columns)
    S = VD.french("ind49", "avgsize", pct=False).reindex(index=R.index, columns=R.columns)
    R = R.where(N >= VD.MIN_FIRMS)
    lg = np.log1p(R)
    cum = lg.shift(2).rolling(11, min_periods=11).sum()                     # 결정 t: t−12..t−2(t 의 행이 t 의 결정)
    cap = (N * S).shift(2)
    out = {}
    idx = R.index
    for j in range(len(idx) - 1):
        t, h = idx[j], idx[j + 1]
        c = cum.iloc[j]
        ok = c.notna() & cap.iloc[j].notna() & R.iloc[j + 1].notna()
        if ok.sum() < 10:
            continue
        k = max(1, int(round(0.3 * ok.sum())))
        top = c[ok].sort_values(ascending=False).index[:k]
        w = cap.iloc[j][top]
        out[h] = float((w * R.iloc[j + 1][top]).sum() / w.sum())
    P = pd.Series(out, dtype=float).sort_index()
    P.index = pd.PeriodIndex(P.index, freq="M")
    mkt = VD.ff3("m")["Mkt"]
    return (P - mkt.reindex(P.index)).rename("T-MOM-IND")


CLUSTER_RULE = ("군 = 그 웹 가닥끼리의 (기전 가족 같음) ∪ (|ρ| ≥ 0.5 인 쌍 = edges) 전이적 폐포 · ρ = F0 에서 잰 L 층 조건 z 역사 상관(pair_rho) · "
                "S 전용 책 G2own 은 F0 에서 잰 S 층 ρ(책 G2own z 대 시장 가닥 z · S_edges) — 검토 고침(웹 하나의 폐포 · K7 S 전용 G2own 상관) · "
                "등록물에는 합칠 쌍(불리언)만 싣고 ρ 값은 저장소 밖 F0 캐시에만(D1)")


def l_cluster_rho(zL):
    """L 조건 z 역사 쌍 ρ(F0 · 저장소 밖 캐시에만 — L 층 수치 · D1)."""
    return VC.pair_rho(pd.DataFrame(zL)[list(VC.CONDS)])


def l_clusters(zL):
    """K7 — 군 등록물(F0 에서 한 번 · 등록문에 고정): {"rule", "edges"(|ρ| ≥ 0.5 인 L 조건 쌍 «A|B» — 불리언만), "families",
    "global"(아홉 조건 전체 폐포 — 보고만), "S_edges"({카드: [시장 가닥]} — S 전용 책 G2own 과 |ρ| ≥ 0.5 · s_g2own_edges 가 채운다)}.
    웹마다 군은 web_cluster_labels 가 이 등록물에서 짓는다. ρ 값 자체는 싣지 않는다(L 층 수치 · D1)."""
    Z = pd.DataFrame(zL)[list(VC.CONDS)]
    fam = {c: VC.CONDS[c][5] for c in VC.CONDS}
    glob = VC.assign_clusters(Z, fam, rho=C.CLUSTER_RHO)
    rho = VC.pair_rho(Z)
    return {"rule": CLUSTER_RULE, "edges": sorted(k for k, r in rho.items() if abs(r) >= C.CLUSTER_RHO), "families": fam,
            "global": {k: int(v) for k, v in glob.items()}, "S_edges": {}}


def web_cluster_labels(creg, conds, sid):
    """웹 하나의 군 이름(가닥 차례) — creg = l_clusters 등록물(없으면 가닥마다 제 군) · conds 에 «G2own:S»(S 전용 책 G2own)가 있으면
    creg["S_edges"][sid] 로 잇는다(F0 에서 재지 않았으면 제 군 · 옛 K7)."""
    conds = list(conds)
    if not creg:
        return conds
    fam = dict(creg.get("families") or {})
    fam["G2own:S"] = family_of("G2own:S") + ":" + str(sid)                      # 카드마다 다른 책 — 다른 카드의 G2own 과 가족으로 묶지 않는다
    rp = {e: 1.0 for e in (creg.get("edges") or [])}
    extra = {VC.pkey("G2own:S", c): 1.0 for c in ((creg.get("S_edges") or {}).get(sid) or [])}
    return VC.clusters_for(conds, fam, rp, rho=C.CLUSTER_RHO, extra=extra)


def s_g2own_rho(SL, F_books, sid, min_n=24):
    """F0(K7 검토 고침) — S 전용 책 G2own z(θ = 1 목표 책 · z_rolling240) 와 S 층 시장 가닥 z(s_conditions) 의 겹친 결정 달 상관 {가닥: ρ}.
    비중 · 장부가 · 시총 · 시장 수준 계열만 — 수익 없음. 등록 F0 는 s_g2own_edges(합칠 가닥 이름)만 creg["S_edges"][sid] 로 싣는다(ρ 값은 캐시에만)."""
    g2x = SL.g2own_x(F_books)
    if not len(g2x):
        return {}
    axis = pd.period_range(L_AXIS[0], LAST_DECISION, freq="M")
    z = VC.z_rolling(g2x).reindex(axis)
    Zs = s_conditions(SL.Lr).reindex(axis)
    out = {}
    for c in VC.CONDS:
        if c.startswith("G2own") or c not in Zs:
            continue
        pair = pd.concat([z.rename("g"), Zs[c].rename("c")], axis=1).dropna()
        if len(pair) >= min_n and pair["g"].std() > 0 and pair["c"].std() > 0:
            r = float(np.corrcoef(pair["g"], pair["c"])[0, 1])
            if np.isfinite(r):
                out[c] = round(r, 4)
    return out


# ══════════════════════════════════════════════════════════════════════════
#  카드 한 장의 S 층 팔 묶음 — F → (y_S · G2own · ATTN) → W · S0 (🚨 수익 입력 · 굽기 · 연기에서만)
# ══════════════════════════════════════════════════════════════════════════
def s_g2own_edges(rho):
    """S 전용 책 G2own 과 합칠 시장 가닥(|ρ| ≥ 0.5) — 이름 목록(불리언만 · 등록물)."""
    return sorted(c for c, r in (rho or {}).items() if r is not None and abs(r) >= C.CLUSTER_RHO)


def book_diag(infos):
    """책 진단(F0 · 비중만) — 달 수 · β 띠 못 맞춘 달 · 투영 줄임 달 · 투영 불가능 달 · 선정 이름 수 중앙값."""
    n = len(infos)
    beta_fail = sum(1 for v in infos.values() if v.get("beta") is not None and not v["beta"]["ok"])
    shrink = sum(1 for v in infos.values() if (v.get("proj") or {}).get("shrink", 1.0) < 1.0)
    infeas = sum(1 for v in infos.values() if not (v.get("proj") or {}).get("feasible", True))
    nsel = [v.get("n_sel") for v in infos.values() if v.get("n_sel") is not None]
    return {"n": n, "beta_fail": beta_fail, "shrink": shrink, "infeasible": infeas, "n_sel_median": (float(np.median(nsel)) if nsel else None)}


def s_card_arms(SL, spec, Lw=None, web_opt=None, gcommon=False, arms=("F", "S0", "W"), paths=True, keep_books=False):
    """카드(또는 쌍둥이) 한 장의 S 층 팔 — 돌려주는 것 dict(books{arm: {달: 책}}, paths{arm: DataFrame}, v, theta, y_S, lam, diag).
    🚨 y_S · λ · 경로는 수익 입력 — 굽기 · 눈가린 연기에서만 실자료로 부른다."""
    out = {"spec": {k: v for k, v in spec.items() if not callable(v)}, "books": {}, "paths": {}, "diag": {}}
    F, fi = SL.books(spec, theta=1.0, lam=None, gcommon=gcommon)
    lam = None
    if spec.get("attn"):
        yA = SL.attn_y(F)
        lam, mp = SL.attn_lambda(yA)
        out["attn"] = {"n_active": int(np.nansum(mp["ok"])), "first_active": next((m for m, ok in zip(SL.months, mp["ok"]) if ok), None)}
        F, fi = SL.books(spec, theta=1.0, lam=lam, gcommon=gcommon)
    out["books"]["F"] = F
    out["diag"]["F"] = book_diag(fi)
    yS = SL.active_y(out["books"]["F"], spec.get("cap80"))
    out["y_S"] = yS
    has_web = bool(strands_of(spec, SL.lit_status))
    if "S0" in arms:
        s0 = dict(spec, attn=False) if spec.get("attn") else spec           # EAR S0 = CH 제외만(ATTN 기울기 없음 · = T-EAR-NOATTN 책)
        out["books"]["S0"], i0 = SL.books(s0, theta=spec["theta0"], lam=None, gcommon=gcommon)
        out["diag"]["S0"] = book_diag(i0)
    if "W" in arms and (has_web or spec.get("attn")):
        if has_web:
            wv = SL.web(spec, Lw, F_books=F, y_S=yS, opt=web_opt)
            th = SL.theta_map(spec, wv["v"])
            out["v"] = wv
        else:
            th = {m: spec["theta0"] for m in SL.months}
        out["theta"] = th
        out["books"]["W"], iw = SL.books(spec, theta=th, lam=lam, gcommon=gcommon)
        out["diag"]["W"] = book_diag(iw)
    if paths:
        fill = spec["fill"]
        for a, bk in out["books"].items():
            out["paths"][a] = SL.path(bk, fill=fill, rate=spec["cost"])
    out["tau_w"] = {a: C.tau_weights_only([bk.get(m) for m in SL.months if S_ARM_FROM <= m]) for a, bk in out["books"].items()}
    if not keep_books:
        out["books"] = {a: None for a in out["books"]}
    return out


# ══════════════════════════════════════════════════════════════════════════
#  F0 신호 커버리지(개수 · 몫만 — 수익 없음) · 사전 고정 결정(VAL S/P · QLT PROF)
# ══════════════════════════════════════════════════════════════════════════
F0_COVER_MIN, F0_MONTH_SHARE = 0.85, 0.95


def f0_signal_coverage(SL, months=None):
    """명세 slate V06 · V07 · coverage_gates_F0 — 달마다 합집합(시총이 선) 이름 가운데 E/P · S/P · OP · QLT 성분 ≥ 2 · β̂ 가 선 몫.
    결정(사전 고정): VAL S/P 포함 ⇔ S/P 몫 ≥ 0.85 인 달이 S 창(보유 2016-09 ~ 2026-08 의 결정 달) 달의 95% 이상 · QLT PROF = OP ⇔ OP 몫이 같은 규칙 · 아니면 ROA_ttm.
    🔎 OP 의 «같은 달 95%» 는 S/P 규칙을 그대로 옮긴 선언이다(명세는 «OP 최초 제출 커버리지 ≥ 0.85» 만 적었다). 🚨 개수 · 몫만."""
    ms = months or [m for m in SL.months if "2016-08" <= m <= LAST_DECISION]
    rows = {}
    for m in ms:
        X = SL.cross(m)
        n = max(X.n, 1)
        comps = np.vstack([np.isfinite(X.op) | np.isfinite(X.roa), np.isfinite(X.lev), np.isfinite(X.sroa)]).sum(0)
        rows[m] = {"n": X.n, "ep": float(np.isfinite(X.ni).sum() / n), "sp": float((np.isfinite(X.rev) & (X.rev > 0)).sum() / n),
                   "op": float(np.isfinite(X.op).sum() / n), "roa": float(np.isfinite(X.roa).sum() / n), "qlt2": float((comps >= 2).sum() / n),
                   "beta": float(np.isfinite(X.beta).sum() / n)}
    share = lambda k: (sum(1 for r in rows.values() if r[k] >= F0_COVER_MIN) / len(rows)) if rows else 0.0
    dec = {"use_sp": share("sp") >= F0_MONTH_SHARE, "prof": ("op" if share("op") >= F0_MONTH_SHARE else "roa"),
           "month_share": {k: share(k) for k in ("ep", "sp", "op", "roa", "qlt2", "beta")}}
    return rows, dec


# ══════════════════════════════════════════════════════════════════════════
#  G-EGD 넘김 — V 프로세스가 θ = 1 책 · 신호 · w_B · 가격 키를 캐시 파일로 쓴다(v_cmp 는 이 파일만 읽는다 · 서로 import 하지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def card_signal(X, spec):
    """G-EGD (3) 의 «전략 신호» — 선정 점수(클수록 먼저) · INS = OB +1 / OS −1 / 나머지 0 · 선 이름만."""
    if spec["select"] == "ins":
        return {t: (1.0 if f == "OB" else (-1.0 if f == "OS" else 0.0)) for t, f in zip(X.t, X.ins)}
    if spec["select"] == "sector_mom":
        return {t: float(v) for t, v in zip(X.t, X.mom) if np.isfinite(v)}
    sc, el, _ = signal_of(X, spec)
    return {X.t[i]: float(sc[i]) for i in np.flatnonzero(el) if np.isfinite(sc[i])}


def export_for_cmp(SL, comps, path, months=None):
    """cmp 넘김 파일(gz JSON · 저장소 밖) — {"cards", "months": {m: {wB, keys, books{sid: θ = 1 책}, signals{sid: 점수}}}}. 수익 없음(비중 · 신호만)."""
    if VD._inside(path, VD.ROOT):
        raise SystemExit("🚨 cmp 넘김 파일이 저장소 안이다(D1)")
    import gzip
    ms = months or [m for m in SL.months if "2016-08" <= m <= LAST_DECISION]
    doc = {"cards": sorted(comps), "months": {}, "note": "v_cards.export_for_cmp — θ = 1 목표 책 · 선정 신호 · w_B · 가격 키(수익 없음)"}
    for m in ms:
        X = SL.cross(m)
        d = {"wB": X.book(X.wB), "keys": {t: k for t, k in zip(X.t, X.k)}, "books": {}, "signals": {}}
        for sid, r in comps.items():
            F = (r.get("books") or {}).get("F") or {}
            if m in F:
                d["books"][sid] = F[m]
                d["signals"][sid] = card_signal(X, VK_spec(r))
        doc["months"][m] = d
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)
    return path


def VK_spec(r):
    s = r["spec"]
    return spec_of(s["sid"], s.get("twin"), **{k: s[k] for k in ("use_sp", "prof") if k in s})


# ══════════════════════════════════════════════════════════════════════════
#  합성 시험
# ══════════════════════════════════════════════════════════════════════════
class _FakeLayer:
    """v_data.Layer 꼴의 가짜 — v_pit.fake_universe 위에 가짜 발표 · 10-Q · 내부자 표지를 얹는다(합성 자료만)."""

    def __init__(self, seed=7, n=40):
        import v_pit as VP
        import v_ear as VE
        U, mkt = VP.fake_universe(n=n, seed=seed)
        self.pit = U
        rng = np.random.default_rng(seed)
        ed = {t: sorted({(pd.Timestamp("2010-01-15") + pd.Timedelta(days=int(d))).strftime("%Y-%m-%d")
                         for d in np.cumsum(rng.integers(80, 100, 40))}) for t in U.PX}
        self.ear = VE.Earnings(U, ed)
        self._rng = rng
        self._cL = self._cS = None

    def inputs(self, m):
        U = self.pit
        mem = U.members(m)
        sig = U.signals(m)
        ins = {}
        for r in mem:
            h = hash((r["t"], m)) % 10
            ins[r["t"]] = "OB" if h < 3 else ("OS" if h < 5 else "none")
        ch = {r["t"]: {"ch": int(hash((r["t"], m, "c")) % 7 == 0), "miss": 0, "n": 1} for r in mem}
        return {"members": mem, "w_B": U.w_B(m), "me": U.me(m), "signals": sig, "irrx": self.ear.irrx_inputs(m),
                "ear": self.ear.ear_inputs(m), "ch": ch, "ins": ins}

    def cond_L(self):
        if self._cL is None:
            self._cL = VC.conditions_L(VC._fake_french())
        return self._cL

    def cond_S(self):
        if self._cS is None:
            self._cS = VC.conditions_S(VC._fake_french(), VC._fake_S())
        return self._cS

    def l_proxy(self):
        rng = np.random.default_rng(3)
        idx = pd.period_range("1926-07", "2026-08", freq="M")
        return {s: pd.Series(rng.normal(0.001, 0.02, len(idx)), index=idx) for s in VD.L_PROXIES}


def _st_select():
    import v_pit as VP
    FL = _FakeLayer()
    SL = SLayer(FL)
    m = "2016-03"
    X = SL.cross(m)
    # K1 손 확인 — 합집합 모멘텀 상위 30% · 버퍼
    sp = spec_of("V01")
    msk = select(X, sp)
    idx = [i for i in range(X.n) if np.isfinite(X.mom[i])]
    order = sorted(idx, key=lambda i: (-X.mom[i], X.t[i]))
    n_in = int(round(0.3 * len(idx)))
    assert set(np.flatnonzero(msk)) == set(order[:n_in])
    prev = {X.t[order[n_in + 2]]}
    msk2 = select(X, sp, prev=prev)
    assert msk2[order[n_in + 2]] and msk2.sum() == n_in + 1                                  # 버퍼 1.5q 안 기존 이름은 남는다
    far = {X.t[order[-1]]}
    assert not select(X, sp, prev=far)[order[-1]]
    # LBS — 섹터 이름 수 ∝ 섹터 시총 몫(최대 나머지법)
    assert list(_largest_remainder(10, [0.55, 0.3, 0.15])) == [6, 3, 1] and list(_largest_remainder(7, [0.5, 0.25, 0.25])) == [3, 2, 2]
    ml = select(X, spec_of("V02"))
    N = sum(1 for i in range(X.n) if np.isfinite(X.beta[i]) and X.sec[i])
    assert abs(int(ml.sum()) - int(round(0.2 * N))) <= 0
    for s in set(X.sec):
        ids = [i for i in range(X.n) if X.sec[i] == s and np.isfinite(X.beta[i])]
        chosen = [i for i in ids if ml[i]]
        if chosen:
            assert max(X.beta[chosen]) <= min(X.beta[[i for i in ids if not ml[i]]] if len(ids) > len(chosen) else [9])
    # VAL — 섹터 안 · E ≤ 0 은 최하위
    X2 = copy.copy(X)
    X2.ni = X.ni.copy()
    X2.ni[0] = -5.0
    sc, el, g = signal_of(X2, spec_of("V06", use_sp=False))                           # E/P 성분만 — E ≤ 0 은 최하위
    same = [i for i in range(X2.n) if X2.sec[i] == X2.sec[0] and el[i]]
    assert sc[0] <= min(sc[same]) + 1e-12
    mv = select(X2, spec_of("V06"))
    for s in set(X2.sec):
        ids = [i for i in range(X2.n) if X2.sec[i] == s and el[i]]
        assert sum(mv[i] for i in ids) == max(1, int(round(0.3 * len(ids))))
    # QLT 칸(섹터 × β̂ 3분위) · 성분 ≥ 2
    gq = _groups(X, spec_of("V07"))
    assert all(g is None or (isinstance(g, tuple) and g[1] in (0, 1, 2)) for g in gq)
    sq, eq, _ = signal_of(X, spec_of("V07"))
    assert eq.sum() > 0 and np.isfinite(sq[eq]).all()
    # INS · V08 · IND · EAR(CH 제외)
    mi = select(X, spec_of("V04"))
    assert mi.sum() == sum(1 for f in X.ins if f == "OB")
    wf, inf = strategy_weights(X, spec_of("V04"), mi)
    os_ = np.array([f == "OS" for f in X.ins])
    assert abs(wf.sum() - 1) < 1e-12 and (wf[os_ & ~mi] == 0).all()
    ms = select(X, spec_of("V01", "T-MOM-IND"))
    assert len(set(X.sec[i] for i in np.flatnonzero(ms))) == max(1, int(round(0.3 * len(set(X.sec)))))
    se, ee, _ = signal_of(X, spec_of("V05"))
    assert not ee[X.ch == 1].any()
    Xj = SL.cross("2016-06").with_ni(np.linspace(-0.1, 0.1, SL.cross("2016-06").n))
    mj = select(Xj, spec_of("V08"))
    assert mj.sum() == int((Xj.niv < 0).sum())
    Xn = SL.cross("2016-07")
    hold = {Xj.t[i] for i in np.flatnonzero(mj)}
    mn = select(Xn, spec_of("V08"), ni_hold=hold)
    assert set(Xn.t[i] for i in np.flatnonzero(mn)) == hold & set(Xn.t)
    assert select(SL.cross("2016-05"), spec_of("V08"), ni_hold=None) is None
    # V08 섹터 중립(검토 고침) — θ = 1 전략 책의 섹터 몫 = w_B 섹터 몫 · 선정 없는 섹터는 w_B 그대로
    w8, i8 = strategy_weights(Xj, spec_of("V08"), mj)
    for s_ in set(Xj.sec):
        idx = [i for i in range(Xj.n) if Xj.sec[i] == s_]
        assert abs(w8[idx].sum() - Xj.wB[idx].sum()) < 1e-12
        if not mj[idx].any():
            assert np.allclose(w8[idx], Xj.wB[idx])
        else:
            assert (w8[[i for i in idx if not mj[i]]] == 0).all()
    return "선정: 합집합 30% 손 확인 · 버퍼 1.5q · LBS 최대 나머지법 · 섹터 β̂ 하위 · VAL 섹터 안(E ≤ 0 최하위) · QLT 칸 · INS OB · φ 섞기(OS 뺀 w_B) · IND 섹터 · EAR CH 제외 · V08 6월 선정 · 사이 달 유지 · 첫 6월 앞 없음"


def _st_books_identity():
    FL = _FakeLayer()
    SL = SLayer(FL, months=[m for m in FL.pit.months if "2014-01" <= m <= "2017-10"])
    for sid in ("V01", "V03", "V06", "V07"):
        sp = spec_of(sid)
        th0 = {m: sp["theta0"] for m in SL.months}
        th_v0 = SL.theta_map(sp, pd.Series(0.0, index=pd.PeriodIndex(SL.months, freq="M")))
        W, _ = SL.books(sp, theta=th_v0)
        S0, _ = SL.books(sp, theta=sp["theta0"])
        assert set(W) == set(S0)
        for m in W:
            ks = set(W[m]) | set(S0[m])
            assert max(abs(W[m].get(k, 0) - S0[m].get(k, 0)) for k in ks) <= 1e-12                 # 항등성: v ≡ 0 → W = S0
    # 책 제약 — 능동 상한 · 섹터 띠 · NDX · β 띠(LBS 면제) · θ 혼합
    m = "2016-03"
    X = SL.cross(m)
    for sid in CARD_IDS:
        sp = spec_of(sid)
        mask = SL.selections(sp).get(m)
        if mask is None and sp["select"] != "ins":
            continue
        for th in (1.0, sp["theta0"]):
            w, inf = target_book(X, sp, mask, th)
            if w is None:
                continue
            a = w - X.wB
            assert abs(w.sum() - 1) < 1e-9 and (w >= 0).all() and (np.abs(a) <= 0.05 + 1e-9).all(), sid
            for s in set(X.sec):
                idx = [i for i in range(X.n) if X.sec[i] == s]
                assert abs(a[idx].sum()) <= sp["sband"] + 1e-9, (sid, s)
            assert w[X.ndx].sum() <= 0.10 + 1e-9
            bb = np.where(np.isfinite(X.beta), X.beta, 1.0)
            if sp["beta_band"]:
                assert abs(w @ bb - X.wB @ bb) <= 0.03 + 1e-9 or not inf["beta"]["ok"], (sid, inf.get("beta"))
    # θ = 0 → w_B
    sp = spec_of("V01")
    w0, _ = target_book(X, dict(sp, beta_band=False), SL.selections(sp)[m], 0.0)
    assert np.allclose(w0, X.wB, atol=1e-12)
    return "항등성(v ≡ 0 → W = S0 · 1e−12 · 네 거미줄 카드) · 카드 여덟 책 제약(발행사 ±5%p · 섹터 띠 · NDX ≤ 10% · β 띠 · 합 1 · long-only) · θ = 0 → w_B"


def _st_paths():
    FL = _FakeLayer()
    SL = SLayer(FL, months=[m for m in FL.pit.months if "2014-01" <= m <= "2017-10"])
    sp = spec_of("V01")
    bk, _ = SL.books(sp, theta=1.0)
    P = SL.path(bk, fill=sp["fill"])
    assert len(P) and P["traded"].iloc[0] == 0.0 and (P["traded"].iloc[1:] >= 0).all()
    # 손 확인 — 둘째 달: 흘러간 첫 책 → 체결 → 수익
    ms = [m for m in SL.months if S_ARM_FROM <= m]
    m0, m1 = ms[0], ms[1]
    E0 = dict(bk[m0])
    Ed, R0, _ = C.drift_book(E0, SL.hold(m0))
    assert abs(P["S"].iloc[0] - R0) < 1e-15
    E1, tr1 = C.execute_book(Ed, bk[m1], fill=0.5)
    R1 = C.book_ret(E1, SL.hold(m1))
    assert abs(P["traded"].iloc[1] - tr1) < 1e-15 and abs(P["S"].iloc[1] - R1) < 1e-15
    # T+1 쪼개기 = 월 수익(첫날 × 나머지)
    sp1 = SL.hold_split(m1)
    hr = SL.hold(m1)
    for t, (a, b) in sp1.items():
        if hr.get(t) is not None and a is not None:
            assert abs((1 + a) * (1 + b) - 1 - hr[t]) < 1e-12
    # 수익 쪽 입력 모양(합성 — 값은 보지 않는다)
    y = SL.active_y(bk)
    g = SL.g2own_x(bk)
    assert len(y) == len(bk) and len(g) > 0
    liq = SL.path(bk, fill=1.0, rate="liq")
    assert (liq["rate"] >= C.S_COST - 1e-15).all()
    return "S 경로: 첫 달 목표에서(미과금) · 흘러감 → 체결 → 보유월 수익 손 확인 · T+1 쪼개기 = 월 수익 · 능동 y · 책 G2own · LIQ 상태 의존 비율"


def _st_web_L():
    rng = np.random.default_rng(5)
    axis = pd.period_range(L_AXIS[0], L_AXIS[1], freq="M")
    zL = pd.DataFrame({c: np.clip(rng.normal(0, 1, len(axis)), -2, 2) for c in VC.CONDS}, index=axis)
    zL.iloc[:100] = np.nan
    prox = {s: pd.Series(rng.normal(0, 0.02, len(axis)), index=axis) for s in VD.L_PROXIES}
    y = prox["V01"].to_numpy().copy()
    y[1:] += 0.006 * np.nan_to_num(zL["SLOW"].to_numpy()[:-1])                                # SLOW 가 V01 을 + 로 예측(합성)
    prox["V01"] = pd.Series(y, index=axis)
    mkt = pd.Series(rng.normal(0.008, 0.045, len(axis)), index=axis)
    st = {"SLOW": {"status": "primary"}, "DISP": {"status": "twin", "why": "x"}, "G2own": {"status": "primary"}}
    LL = LLayer(zL, prox, mkt, pd.Series(0.003, index=axis), clusters=l_clusters(zL), lit_status=st)
    sp = spec_of("V01")
    w = LL.web(sp)
    assert w["strands"] == ["SLOW"] and w["first_active"] is not None
    na = w["n_clusters_act"].to_numpy()
    vv = w["v"].to_numpy()
    assert np.all(np.abs(vv[na == 1]) <= 0.5 + 1e-15) and np.abs(vv).max() > 0                   # 한 군 → 절반 강도(|v| ≤ ½)
    th = LL.theta(sp, w["v"])
    assert (np.abs(np.diff(th.to_numpy())) <= 0.1 + 1e-12).all() and th.min() >= 0.5 - 1e-12 and th.max() <= 1.0 + 1e-12
    a = LL.arm("V01", th, tau=3.0)
    a0 = LL.arm("V01", pd.Series(sp["theta0"], index=axis), tau=3.0)
    assert len(a["S"]) > 1000 and a["turn_1w"] is not None and a0["turn_1w"] < a["turn_1w"] + 1e-9
    lit = LL.web(spec_of("V01", "T-MOM-LIT"))
    assert lit["strands"] == ["SLOW", "DISP"]
    pan = LL.web(spec_of("V01", "T-MOM-PANIC"))
    assert "PANICX" in pan["strands"]
    zero = LL.web(sp, Zover=zL * 0.0)
    assert np.abs(zero["v"].to_numpy()).max() == 0.0
    return "L 거미줄: 주 가닥만(강등 DISP 는 LIT 쌍둥이) · 한 군 → |v| ≤ ½ · θ 경로 [0.5, 1] · |Δθ| ≤ 0.10 · L 다리 팔 · PANIC 쌍둥이 · z ≡ 0 → v = 0"


def _st_registry():
    assert set(CARDS) == {"V01", "V02", "V03", "V04", "V05", "V06", "V07", "V08"}
    assert [s for s in CARD_IDS if CARDS[s]["hv"]] == ["V01", "V02", "V03", "V06", "V07"]
    assert CARDS["V08"]["forward_only"] and not CARDS["V08"]["web"] and not CARDS["V08"]["hv"] and CARDS["V08"]["adopt"] == "forward_only"
    assert not CARDS["V02"]["beta_band"] and CARDS["V02"]["sband"] == 0.05 and CARDS["V03"]["fill"] == 1.0 and not CARDS["V03"]["buffer"]
    e = spec_of("V03", liq_emergency=True)
    assert e["theta0"] == 0.4 and e["dtheta"] == 0.2
    for tw, d in TWINS.items():
        s = spec_of(d["card"], tw)
        assert s["status"] in ("built", "input_absent", "gated_f0")
    assert "T-MOM-IND" in TWINS and TWINS["T-EAR-NOCH"]["mods"] == {"excl_ch": False}                  # IND = MOM 쌍둥이 · LAZY = EAR 제외 단계
    forb = ("eg", "eg30", "qg30", "cfo", "invest", "asset_growth", "accrual")
    for sid, c in CARDS.items():
        assert not any(f == str(c.get("signal")) for f in forb)
    return "카드 여덟(H_V 다섯 · V08 전방 전용 · 정적) · LBS β 띠 면제 · LIQ 전량 체결 · 비상 규칙 · 쌍둥이 상태(built · input_absent · gated_f0) · IND = MOM 쌍둥이 · LAZY = EAR 단계 · 금지 신호 없음"


def selftest():
    res, ok = [], True
    for fn in (_st_registry, _st_select, _st_books_identity, _st_paths, _st_web_L):
        t0 = time.time()
        try:
            with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
                res.append(("통과", fn.__name__, fn(), round(time.time() - t0, 1)))
        except Exception:
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-2500:], round(time.time() - t0, 1)))
    for st, nm, msg, sec in res:
        print("  %s %-18s %5ss  %s" % ("✓" if st == "통과" else "✗", nm, sec, msg))
    print("v_cards selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


# ══════════════════════════════════════════════════════════════════════════
#  눈가린 연기 — 실자료 S 층 카드 전부 · L 층 거미줄 · 산출을 열지 않고 지운다
# ══════════════════════════════════════════════════════════════════════════
def blind_smoke(twins=True, months_from=None):
    import v_guard as VG
    VG.install_open_audit()
    out = {}
    box = {}

    def build():
        box["Lr"] = VD.Layer.real()
        return box["Lr"].pit.months
    out["layer"] = VD.blind_smoke(build)
    if "Lr" not in box:
        return out
    Lr = box["Lr"]

    def mkL():
        zl = Lr.cond_L()
        box["cl"] = l_clusters(zl)
        box["LL"] = LLayer.real(Lr, clusters=box["cl"])
        return box["LL"].axis
    out["LLayer"] = VD.blind_smoke(mkL)
    sl_months = None
    if months_from:
        sl_months = [m for m in Lr.pit.months if months_from <= m <= LAST_DECISION]
    box["SL"] = SLayer(Lr, months=sl_months, clusters=box.get("cl"))
    SL, LL = box["SL"], box.get("LL")
    td = os.path.join(VD.cache_guard(), "_vb_smoke_cards")
    os.makedirs(td, exist_ok=True)
    for sid in CARD_IDS:
        sp = spec_of(sid)

        def run(_sp=sp):
            Lw = LL.web_slopes(_sp) if (LL and _sp["web"]) else None
            r = s_card_arms(SL, _sp, Lw)
            fn = os.path.join(td, "%s.pkl" % _sp["sid"])
            pd.to_pickle(r, fn)                                   # 산출 — 열지 않고 지운다
            return {a: len(p) for a, p in r["paths"].items()}
        out["S " + sid] = VD.blind_smoke(run)
    if twins:
        for tw, d in TWINS.items():
            sp = spec_of(d["card"], tw)
            if sp["status"] != "built" or "S" not in sp["layers"]:
                continue

            def run_t(_sp=sp):
                Lw = LL.web_slopes(_sp) if (LL and (_sp["web"] or _sp.get("web_add"))) else None
                r = s_card_arms(SL, _sp, Lw, arms=("F", "S0", "W"))
                pd.to_pickle(r, os.path.join(td, "%s.pkl" % _sp["twin"]))
                return {a: len(p) for a, p in r["paths"].items()}
            out["S " + tw] = VD.blind_smoke(run_t)
    if LL is not None:
        def run_L():
            res = {}
            for sid in WEB_CARDS:
                sp = spec_of(sid)
                w = LL.web(sp)
                th = LL.theta(sp, w["v"])
                a, a0 = LL.arm(sid, th, tau=1.0), LL.arm(sid, pd.Series(sp["theta0"], index=LL.axis), tau=1.0)
                pd.to_pickle({"w": w, "a": a, "a0": a0}, os.path.join(td, "L_%s.pkl" % sid))
                res[sid] = len(a["S"])
            for tw in ("T-MOM-PANIC", "T-MOM-LIT", "T-LIQ-LIT", "T-VAL-LIT", "T-QLT-SLOW", "T-LIQ-DEMEAN", "T-MOM-IND", "T-MOM-10", "T-LBS-LO20"):
                d = TWINS[tw]
                sp = spec_of(d["card"], tw)
                prox = twin_proxy(tw)
                w = LL.web(sp, proxy=prox)
                a = LL.arm(prox, LL.theta(sp, w["v"]), tau=1.0)
                pd.to_pickle({"w": w, "a": a}, os.path.join(td, "L_%s.pkl" % tw))
                res[tw] = len(a["S"])
            return res
        out["L webs + twins"] = VD.blind_smoke(run_L)
    import shutil
    shutil.rmtree(td, ignore_errors=True)                            # 열지 않고 지운다
    out["G-NoEG runtime"] = {"ok": VG.runtime_check()["ok"], "sec": 0, "shape": VG.runtime_check(), "err": None}
    out["G-NoEG open audit"] = {"ok": VG.open_audit_check()["ok"], "sec": 0, "shape": {"n_opened": VG.open_audit_check()["n_opened"],
                                                                                       "eg": VG.open_audit_check()["eg_files_opened"]}, "err": None}
    return out


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--blind-smoke" in sys.argv:
        mf = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else None
        res = blind_smoke(twins="--no-twins" not in sys.argv, months_from=mf)
        for k, v in res.items():
            sh = json.dumps(v.get("shape"), ensure_ascii=False, default=str)
            print("  %s %-26s %7ss %s" % ("✓" if v["ok"] else "✗", k, v["sec"], (sh[:160] if v["ok"] else v["err"])))
        print("연기 %d/%d 참" % (sum(1 for v in res.values() if v["ok"]), len(res)))
        raise SystemExit(0 if all(v["ok"] for v in res.values()) else 1)
    print(__doc__)
