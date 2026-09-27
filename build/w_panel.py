# -*- coding: utf-8 -*-
"""build/w_panel.py — 배치 W Stage M-W 세계 · 패널(굽기 입력) · 시총 위생(선언) · 커버리지 F0 · 슬리브 단면 · V 단면(W06 · W12) · V06 VAL.

설계 원본(구속): wbatch_research.json final.slate.common_frame(universe · tier1_world · tier1_months · neutral_w_B · market_cap_rule ·
  fundamentals · price_features · sectors · stage_m_w_controls · gap_month_rule) · data_plan(coverage_gates_F0 · market_cap) ·
  build_plan.modules[w_panel](«Stage M-W 세계 · 패널(v_pit · v_fund · v_px_split 위) · KPS8 특성 · 통제 · 커버리지 F0»).
  w_geo.world_of · w_frag 가 이 파일의 stage_world 를 부른다(없으면 w_cards.smoke_world 근사) — 굽기와 F0 는 이 파일 하나로 세계를 짓는다.

세계(명세 tier1_world): PIT S&P 500 ∪ NASDAQ 100 합집합(v_pit.Universe.members · 회사당 한 줄 · 가격 키가 선 이름) 가운데
  비금융(GICS «Financials» 밖) · 비FPI · 발행사 그룹당 한 줄(시총 큰 줄) · 가격 · 위생 통과 시총 · PIT 섹터가 선 이름.
  금융주는 슬리브에서 w_B 그대로(능동 0 — w_cards B1) · W03 섹터 자산 · W02 동료 풀 · W11 보유 행렬은 금융 포함(각 카드 모듈).
중립 w_B: PIT S&P 500 구성 종목의 상한 없는 시총가중(NDX 전용 = 0) — 위생 통과 시총만(PN1).

🔎 명세가 정하지 않은 산수(선언 — 등록문에 옮긴다)
  PN1 시총 위생(자료 단계 발견 · 얼린 V 층을 고치지 않고 W 층에서 건다): 얼린 v_pit 시총(백만 달러)이 단위 사고를 품는다 — 예: 한 에너지 대형주의
      주식수가 2015-12 ~ 2024-06 에 1/1000 로 적혀 시총이 0.3~1.5억 달러로 나온다 · 2010~2013 에 몇 이름은 8조 달러를 넘는다(1e17 달러).
      규칙(PIT · 수익 없음 · 이름-달 하나씩): (a) 시총 < 3억 달러 또는 > 8조 달러(합집합 명단 이름으로 2010~2026 에 있을 수 없는 띠) ·
      (b) 랩 원장 주식수(pit_panel._shares · 결정일 기준) × 격자 가격과의 비가 [1/5, 5] 밖(두 주식수 원천이 5배 넘게 어긋남 = 한쪽 단위 사고) →
      그 이름-달의 시총을 결측으로 둔다(세계 · w_B · 슬리브 단면 · 요인 가중 모두에서 빠진다 · 값을 추측해 고치지 않는다).
      모든 W 카드 모듈에는 이 위생을 건 우주(SaneUniverse — 얼린 v_pit.Universe 를 감싸 me · me_row · w_B · me_of_ticker 만 바꾼다)를 넘긴다.
      F0 셈(2010-01 ~ 2026-07): 관측 92,259 이름-달 가운데 530 건(바닥 366 · 천장 18 · 원장 대조 146) · Tier-1 창 194 건(6 이름) [F0].
  PN2 커버리지(명세 tier1_months «시총 · 가격 커버리지 ≥ 0.95 인 결정 달»): 분모 = 그달 세계 후보(명단 이름 가운데 알려진 금융 · FPI 를 빼고
      발행사 그룹당 한 줄) + 가격 키가 없는 명단 이름(pit_panel.union_members 의 명단 수 − 가격 키 이름 수 · 보수) · 덮임 = 결정일 가격 ∧ 위생 통과 시총 ∧
      PIT 섹터 · 시총 몫 가중 = 덮인 이름은 제 시총 · 덮이지 않은 이름은 같은 가격 키의 12개월 안 마지막 위생 통과 시총 → 없으면 그달 같은 지수 쪽
      (S&P 500 · NDX 전용) 덮인 이름 시총 중앙값. 🔎 달 판정 = **시총 몫 ≥ 0.95**(명세 «시총 · 가격 커버리지 ≥ 0.95» 의 시총 가중 읽기) ·
      개수 몫은 보고 · 엔진 선언 H5 판(개수 ∧ 시총 ≥ 0.95 — w_hygiene.coverage_f0)과 배치 R 규칙(개수 ≥ 0.90 ∧ 시총 ≥ 0.95)은 민감도로 싣는다.
      이유(등록 전 · 수익 없이 개수만 보고 정했다): 랩 가격 격자에 2018-02 ~ 2021 약 20 ~ 45 이름(에너지 쏠림)의 결정일 가격이 비어 개수 몫이 0.88 ~ 0.95 에
      머문다 — 개수 ∧ 시총 판이면 Tier-1 달이 82 로 줄어 검정력이 무너지고(시총 몫은 0.94 ~ 0.98) 흘러가는 책이 3 년 넘게 재편성되지 않는다(공개 한계).
      Tier-1 결정 달 = 2016-08 ~ 2026-07 가운데 통과 달 · 못 넘은 달은 FM 에서 빠지고 책은 흘러간다(gap_month_rule · 러너).
      추정 되돌아보기 달(S-E 2010-01 ~)은 판정 없이 선 행을 쓴다(K3 — 신호의 입력).
  PN3 W01 특성 커버리지(명세 coverage_gates_F0 «8 특성 중 6 이상 있는 이름 ≥ 90%»): 달마다 세계 이름 가운데 KPS8 원값이 6 개 이상 선 몫 ·
      0.90 아래 결정 달은 W01 FM 에서 빠진다(커버리지 달 규칙과 같은 처리 · F0 허용 결정 «커버리지 못 넘은 달 → drift»).
  PN4 V06 VAL 통제(명세 «V06 VAL 점수(E/P · S/P 섹터 안 z · 결측 더미)»): frozen v_cards.signal_of(V06) 를 그대로 부른다 — V F0 결정 use_sp = False
      (data/_vb_f0.json · S/P 커버리지 부족)를 그대로 따라 E/P 섹터 안 백분위(E ≤ 0 최하위)가 점수 · 백분위는 V 단면(위생 통과 시총이 선 명단 전부)에서 ·
      그 점수를 세계 행으로 옮겨 섹터 안 z(w_ipca.sector_z) · 결측은 NaN(Stage M-W 결측 더미). 재무 원값은 ni · rev 의 TTM(최초 제출 · V AVAIL)만 —
      장부 자본(eq)은 읽지 않는다(w_guard 선언 · V 단면의 be 칸은 비어 있다).
  PN5 52주 고점(KPS8 ⑤): 명세는 «분할만 조정 종가» 다 — 랩 가격 격자(편출 이름 pit_px 포함)에 분할만 조정 종가 원천이 한 벌로 없어
      격자 가격(수정종가)의 252일 최대 대비로 한다(w_ipca.kps8_month · 배당 몫만 다르다 · 단면 순위 변환 뒤 영향 작음 · 이탈 공개).
  PN6 FP β̂(W04 통제 · β 띠 · V02): frozen v_pit.beta_fp 를 이름-달마다 한 번만 계산해 다시 쓴다(메모 · 값은 같다).
  PN7 V 단면(W06 V01 · W12 V02): frozen v_cards.Cross 에 위생 통과 시총 · w_B · 신호(섹터 · FP β̂ · 12-2 · 그달 수익)만 넣는다
      (재무 · 내부자 · 실적 칸은 비운다 — V01 · V02 선정은 그 칸을 쓰지 않는다).

🚨 랩 규율 — 이 모듈은 패널을 짓는다: y(다음 달 수익)는 v_pit.hold_ret 에서 온다. 패널 kind 는 "real" 이고 곧바로 러너가 등록 자물쇠
   (w_core.assert_kind_allowed) · 눈가림(w_hygiene.blind_panel)을 건다. 이 모듈은 수익 통계를 계산하지 않고 값을 찍지 않는다(개수 · 몫만).

  python build/w_panel.py --selftest
"""
from __future__ import annotations

import math
import os
import sys
import time
import traceback

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import w_core as WC          # noqa: E402
import w_guard as WG         # noqa: E402

FIN_SECTOR = "Financials"
PANEL_FROM = "2010-01"                               # S-E(추정 전용 · D27)
TIER1 = ("2016-08", "2026-07")                       # Tier-1 결정 달(보유 2016-09 ~ 2026-08)
V_ARM_FROM = "2014-05"                               # V S_ARM_FROM — W06 · W12 V 단면 첫 결정 달
ME_FLOOR, ME_CEIL = 300.0, 8.0e6                     # PN1 (a) 백만 달러
LEDGER_BAND = (0.2, 5.0)                             # PN1 (b)
COV_THR = 0.95                                       # PN2
CAP_CARRY = 12                                       # PN2 덮이지 않은 이름 가중의 이월 달 수
KPS_MIN_FEATURES, KPS_COVER_MIN = 6, 0.90            # PN3
V06_USE_SP = False                                   # PN4 — V F0 결정(data/_vb_f0.json decisions.use_sp)
TAIL_WIN = 63

PANEL_UNITS = [WG.unit("me_sane", source="v_pit.me + pit_panel._shares", concept="market cap unit-accident screen (split-only ME)", use="me_denominator"),
               WG.unit("val", source="v_fund(first-filed ledger) ni rev", concept="value_ep_sp (V06 VAL within-sector)", use="control"),
               WG.unit("beta_fp", source="data/pit_px.json", concept="Frazzini-Pedersen daily beta (Dimson 5)", use="control"),
               WG.unit("tail", source="data/pit_px.json", concept="10% quantile of 63-day daily returns over sigma", use="signal"),
               WG.unit("y", source="v_pit.hold_ret", concept="next-month return (pit_panel.y_stop rule)", use="target")]
WG.assert_units(PANEL_UNITS, "w_panel 입력(모듈 적재)")


def _log(msg):
    print(msg, flush=True)


# ══════════════════════════════════════════════════════════════════════════
#  PN1 시총 위생 — 얼린 v_pit.Universe 를 감싼다(고치지 않는다)
# ══════════════════════════════════════════════════════════════════════════
def me_check(v, lab):
    """이름-달 하나의 시총 위생 — 사유(floor · ceil · ledger) | None. v = v_pit 시총 · lab = 랩 원장 주식수 × 격자 가격(없으면 None) · 둘 다 백만 달러."""
    if v is None or not (v == v) or v <= 0:
        return None
    if v < ME_FLOOR:
        return "floor"
    if v > ME_CEIL:
        return "ceil"
    if lab is not None and lab == lab and lab > 0:
        r = v / lab
        if r < LEDGER_BAND[0] or r > LEDGER_BAND[1]:
            return "ledger"
    return None


class SaneUniverse:
    """위생 우주 — 얼린 v_pit.Universe 의 모든 속성 · 메서드를 그대로 넘기고 me · w_B · me_of_ticker · beta_fp(메모)만 바꾼다(PN1 · PN6)."""

    def __init__(self, U, lab_check=True):
        self._U = U
        self._me, self._flag, self._bfp = {}, {}, {}
        self._lab_check = lab_check
        self._PP = WC.frozen("pit_panel") if lab_check else None

    def __getattr__(self, name):                       # 없는 속성만 여기로 온다 — 얼린 우주에 넘긴다
        if name.startswith("_") and name in ("_U", "_me", "_flag", "_bfp", "_lab_check", "_PP"):
            raise AttributeError(name)
        return getattr(self._U, name)

    @property
    def inner(self):
        return self._U

    def _lab_me(self, r, i, d):
        if not self._lab_check:
            return None
        s2 = self._PP._shares(self._U.W, r["t"], r["k"], d)
        p = np.asarray(self._U.PX[r["k"]], float)[i]
        if not s2 or not (p == p and p > 0):
            return None
        return float(p) * float(s2)

    def me(self, m):
        if m in self._me:
            return self._me[m]
        U = self._U
        raw = U.me(m)
        i = U.me_idx[m]
        d = U.dates[i]
        out, fl = {}, {}
        for r in U.members(m):
            v, how = raw[r["t"]]
            if not v:
                out[r["t"]] = (v, how)
                continue
            why = me_check(float(v), self._lab_me(r, i, d))
            if why:
                out[r["t"]] = (None, "w_sane:" + why)
                fl[r["t"]] = why
            else:
                out[r["t"]] = (v, how)
        self._me[m], self._flag[m] = out, fl
        return out

    def me_row(self, row, m):
        """이름 한 줄 · 달 하나의 시총(w_geo 동료 가중이 부른다) — 얼린 me_row 에 같은 위생(PN1)을 건다(명단 밖 달의 줄도)."""
        v, how = self._U.me_row(row, m)
        if not v:
            return v, how
        i = self._U.me_idx[m]
        why = me_check(float(v), self._lab_me(row, i, self._U.dates[i]))
        return (None, "w_sane:" + why) if why else (v, how)

    def raw_me(self, m):
        return self._U.me(m)

    def flags(self, m):
        self.me(m)
        return dict(self._flag[m])

    def w_B(self, m):
        me = self.me(m)
        mc = {r["t"]: me[r["t"]][0] for r in self._U.members(m) if r["spx"] and me[r["t"]][0]}
        tot = sum(mc.values())
        return {t: v / tot for t, v in mc.items()} if tot > 0 else {}

    def me_of_ticker(self, t, m):
        for r in self._U.members(m):
            if r["t"] == t or r["k"] == t:
                return self.me(m)[r["t"]]
        return None, "not_member"

    def beta_fp(self, k, m):
        key = (k, m)
        if key not in self._bfp:
            self._bfp[key] = self._U.beta_fp(k, m)
        return self._bfp[key]

    def poison_after(self, m, rng):
        """선견 점검용 — 얼린 v_pit.poison_after 뒤 같은 위생(랩 원장 대조 포함)을 건다."""
        return SaneUniverse(self._U.poison_after(m, rng), lab_check=self._lab_check)


_SANE = {}


def sane(U):
    """얼린 우주 → 위생 우주(같은 U 는 같은 감싸개 · 메모 공유) · 이미 감싼 것이면 그대로."""
    if isinstance(U, SaneUniverse):
        return U
    k = id(U)
    if k not in _SANE or _SANE[k][0] is not U:
        _SANE[k] = (U, SaneUniverse(U))
    return _SANE[k][1]


# ══════════════════════════════════════════════════════════════════════════
#  PN8 내부 가격 오버레이 — 편출 이름의 결정일 가격 구멍(등록 전 · 수익 없이 이름 · 날짜 셈만 보고 정했다)
# ══════════════════════════════════════════════════════════════════════════
#  왜: 랩 가격 격자(stocks.json sd + data/pit_px.json)에는 2018-02 ~ 2025-04 에 지수를 떠난 이름(인수 · 파산 · 편출)의 결정일 가격이 비어 있다.
#    빈 이름이 거의 모두 «나중에 명단을 떠나는 이름» 이라 세계 소속이 미래 사건에 기댄다(사후 선택 선견 · 비평 1 H2). 사용자 상시 규칙
#    (가격 결측은 아무 공개 원천 + 사내 DB 로 메운다 · 2026-09-25)대로, 배치 R Stage M 이 이미 쓴 **검증된 내부 오버레이 파일 하나**
#    (format pit_px_stage/1 · 사내 DB 종가 + CC0 공개 데이터셋 + 야후 후계 티커 · 검증 게이트 V1 ~ V9 통과 · 저장소 밖 · 커밋하지 않는다)를 얹는다.
#  규칙(배치 R r_stagem.apply_px_overlay 와 같은 빈 칸 규칙 · 이 파일에 옮겨 적었다 — r_stagem 은 부르지 않는다):
#    ① 그 키의 그날 값이 비었고 ② 그 키의 명단 티커(keys[키].tickers · 없으면 키) 가운데 그날이 멤버 창(월말 명단의 멤버 달 + 다음 달) 안인 것이 있고
#    ③ 그 티커가 pit_panel._key 로 그날 다른 키의 값을 읽지 않을 때만 채운다 · 있는 값은 한 칸도 바꾸지 않는다 · 오늘 유니버스 키 · 격리 이름은 채우지 않는다 ·
#    판정은 모두 파일을 읽은 세계(오버레이 전) 위에서 하고 채우기는 그 뒤 한 번에 · 채운 키의 보유월 멈춤 판정(stops)은 같은 날 판정이 없을 때만 더한다.
#    격자: 오버레이 날짜가 세계 격자의 앞부분과 같아야 한다(뒤에 날이 더 붙은 격자는 받는다 · 평가 창은 2026-08 에서 끝난다) — 아니면 멈춘다.
#  🔒 파일 경로는 저장소 밖만 · 환경변수 WBATCH_PX_OVERLAY 로만 가리킨다(공개 코드 · 문서에 경로 · 파일 이름을 적지 않는다) · 공개 쪽에는 sha256 과 셈만 싣는다
#    (경로 · 원천 이름 · 값 없음) · 굽기 · F0 는 명세(data/_wb_manifest.json)의 sha256 과 같은 파일만 받는다(w_run 판 점검 6).
#  남는 구멍(오버레이로도 못 메운 이름-달)은 F0 가 해마다 세고(편출 여부 셈 포함) 등록 문서가 «사후 선택 선견 한계» 로 공개한다.
PX_OVERLAY_ENV = "WBATCH_PX_OVERLAY"
PX_OVERLAY_FORMAT = "pit_px_stage/1"
_OV_DOC = {}


def px_overlay_path():
    """PN8 오버레이 파일의 절대 경로(환경변수 WBATCH_PX_OVERLAY) — 없으면 멈춘다(fail-closed · 등록 판은 오버레이를 얹은 세계다) · 저장소 안이면 멈춘다."""
    v = (os.environ.get(PX_OVERLAY_ENV) or "").strip()
    if not v:
        raise SystemExit("🚨 %s 가 없다 — PN8 내부 가격 오버레이 없이는 등록 판 세계를 지을 수 없다" % PX_OVERLAY_ENV)
    p = os.path.abspath(v)
    if not os.path.isfile(p):
        raise SystemExit("🚨 %s 가 가리키는 파일이 없다" % PX_OVERLAY_ENV)
    if WC._inside(p, WC.ROOT):
        raise SystemExit("🚨 PN8 오버레이는 저장소 밖 파일만 받는다")
    return p


def _overlay_doc(path):
    import hashlib
    import io
    import json
    st = os.stat(path)
    ck = (path, st.st_size, st.st_mtime_ns)
    if ck not in _OV_DOC:
        _OV_DOC.clear()
        with open(path, "rb") as f:
            b = f.read()
        J = json.load(io.TextIOWrapper(io.BytesIO(b), encoding="utf-8"))
        if J.get("format") != PX_OVERLAY_FORMAT:
            raise SystemExit("🚨 PN8 오버레이 형식 %r — %s 만 받는다" % (J.get("format"), PX_OVERLAY_FORMAT))
        _OV_DOC[ck] = (J, hashlib.sha256(b).hexdigest(), len(b))
    return _OV_DOC[ck]


def apply_px_overlay(W, path):
    """PN8 — 오버레이를 pit_panel 세계 W 에 얹는다(제자리) → 적용 요약(sha256 · 셈 — 경로 · 이름 · 값 없음)."""
    PP, PQ = WC.frozen("pit_panel"), WC.frozen("pit_quarantine")
    J, sha, nbytes = _overlay_doc(path)
    dates = W["dates"]
    D = len(dates)
    od = list(J.get("dates") or [])
    if not od or od != list(dates[:len(od)]):
        raise SystemExit("🚨 PN8 오버레이 격자가 세계 격자의 앞부분과 다르다 — 같은 판에서 다시 만들 것")
    Q, today = set(PQ.names()), set(W["today"])
    mon, days_of, wcache = {}, {}, {}
    for ix in ("spx", "ndx"):
        for m, ts in W["lists"][ix].items():
            for t in ts:
                mon.setdefault(t, set()).add(m)
    for i, d in enumerate(dates):
        days_of.setdefault(d[:7], []).append(i)

    def win(t):
        if t not in wcache:
            s = set()
            for m in mon.get(t, ()):
                for mm in (m, PP.mshift(m, 1)):
                    s.update(days_of.get(mm, ()))
            wcache[t] = s
        return wcache[t]

    cnt, fills, meta = {}, {}, (J.get("keys") or {})
    bump = lambda n, v=1: cnt.__setitem__(n, cnt.get(n, 0) + v)
    for k in sorted(J.get("px") or {}):
        o = J["px"][k]
        i0 = int(o.get("i0") or 0)
        vals = [(i0 + j, float(v)) for j, v in enumerate(o.get("p") or []) if v is not None and 0 <= i0 + j < min(D, len(od))]
        if k in today:
            bump("today_key", len(vals))
            continue
        if k in Q:
            bump("quarantined_key", len(vals))
            continue
        tks = list((meta.get(k) or {}).get("tickers") or [k])
        b = W["PX"].get(k)
        for i, v in vals:
            if not (v > 0):
                bump("nonpositive")
                continue
            if b is not None and b[i] == b[i]:
                bump("kept_existing")
                if abs(v / b[i] - 1) > 1e-9:
                    bump("kept_existing_value_differs")
                continue
            inw = [t for t in tks if i in win(t)]
            if not inw:
                bump("outside_member_window")
                continue
            other = False
            for t in inw:
                c = PP._key(W, t, i)
                if c is not None and c != k:
                    x = W["PX"][c][i]
                    if x == x and x > 0:
                        other = True
                        break
            if other:
                bump("priced_under_other_key")
                continue
            fills.setdefault(k, []).append((i, v))
    new_keys = 0
    for k, lst in fills.items():
        if k not in W["PX"]:
            W["PX"][k] = np.full(D, np.nan)
            new_keys += 1
        a = W["PX"][k]
        for i, v in lst:
            a[i] = v
    stops = W.setdefault("stops", {})
    st_add = st_keep = 0
    for k in sorted(fills):
        for s in ((J.get("stops") or {}).get(k) or []):
            if s.get("y") not in ("missing", "last_price", "short_cut"):
                continue
            have = stops.setdefault(k, {})
            if s["d"] in have:
                st_keep += 1
                continue
            have[s["d"]] = {"d": s["d"], "y": s["y"], "why": s.get("why") or "", "uncertain": bool(s.get("uncertain")), "by": "overlay"}
            st_add += 1
    return {"env": PX_OVERLAY_ENV, "sha256": sha, "bytes": nbytes, "format": J.get("format"), "visibility": J.get("visibility"),
            "keys_in_file": len(J.get("px") or {}), "keys_filled": len(fills), "keys_new": new_keys,
            "values_filled": sum(len(v) for v in fills.values()), "skipped": dict(sorted(cnt.items())),
            "stops_added": st_add, "stops_kept_existing": st_keep,
            "rule": "PN8 — price-missing member-days only · never overwrites · no today/quarantined keys · no other-key reads"}


def real_universe(overlay=True):
    """굽기 · F0 · 연기의 실자료 우주 — 얼린 v_pit.Universe.real(with_vd1=True) 를 **PN8 오버레이를 얹은 세계**로 짓는다
    (pit_panel.load_world 를 그 부름 동안만 감싼다 · 얼린 파일은 한 바이트도 바꾸지 않는다). overlay=False 는 공개 판(민감도 · 탐침)."""
    VP, PP = WC.frozen("v_pit"), WC.frozen("pit_panel")
    if not overlay:
        U = VP.Universe.real(with_vd1=True)
        U.px_overlay = None
        return U
    path = px_overlay_path() if overlay is True else os.path.abspath(str(overlay))
    orig = PP.load_world
    rec = {}

    def lw():
        W = orig()
        rec.update(apply_px_overlay(W, path))
        return W
    PP.load_world = lw
    try:
        U = VP.Universe.real(with_vd1=True)
    finally:
        PP.load_world = orig
    U.px_overlay = rec
    return U


def price_hole_summary(SU, months, last_month=None):
    """PN8 — 남은 구멍 셈(값 없음): 해마다 결정일 가격이 없는 세계 후보 수의 달 평균 · 그 가운데 나중에 명단을 떠나는 이름 몫."""
    last_member = {}
    for m in SU.months:
        for r in SU.members(m):
            last_member[r["t"]] = m
    end = last_month or max(months)
    by = {}
    for m in months:
        cands, _ = world_candidates(SU, m)
        miss = [r["t"] for r in cands if not _price_ok(SU, r["k"], m)]
        ex = sum(1 for t in miss if last_member.get(t, "9999") < end)
        by.setdefault(m[:4], []).append((len(miss), ex, len(cands)))
    out = {}
    for y, v in sorted(by.items()):
        a = np.array(v, float)
        out[y] = {"months": len(v), "missing_mean": round(float(a[:, 0].mean()), 2), "later_exit_mean": round(float(a[:, 1].mean()), 2),
                  "cands_mean": round(float(a[:, 2].mean()), 1)}
    return {"rule": "결정일 가격이 없는 세계 후보(이름 수의 달 평균) · 그 가운데 창 끝 전에 명단을 떠나는 이름", "by_year": out}


def me_flag_summary(SU, months):
    """F0 — 위생 규칙이 결측으로 둔 이름-달 셈(해마다 · 사유별 · Tier-1 창 이름 목록) · 값 없음."""
    by_year, by_why, names_t1, n_obs = {}, {}, {}, 0
    for m in months:
        me = SU.raw_me(m)
        n_obs += sum(1 for v in me.values() if v[0])
        for t, why in SU.flags(m).items():
            by_year[m[:4]] = by_year.get(m[:4], 0) + 1
            by_why[why] = by_why.get(why, 0) + 1
            if TIER1[0] <= m <= TIER1[1]:
                names_t1[t] = names_t1.get(t, 0) + 1
    return {"rule": "PN1 — 시총 < %.0f 백만 달러 · > %.0e 백만 달러 · 랩 원장 대조 비 [%.1f, %.1f] 밖 → 결측" % (ME_FLOOR, ME_CEIL, *LEDGER_BAND),
            "n_obs": n_obs, "n_flag": sum(by_year.values()), "by_year": dict(sorted(by_year.items())), "by_reason": dict(sorted(by_why.items())),
            "tier1_names": dict(sorted(names_t1.items())), "tier1_n_flag": sum(names_t1.values())}


# ══════════════════════════════════════════════════════════════════════════
#  세계 · 커버리지(PN2)
# ══════════════════════════════════════════════════════════════════════════
def _price_ok(SU, k, m):
    p = np.asarray(SU.PX[k], float)[SU.me_idx[m]]
    return bool(p == p and p > 0)


def world_candidates(SU, m):
    """그달 세계 후보 — 명단(가격 키가 선 이름) 가운데 알려진 금융 · FPI 를 빼고 발행사 그룹당 한 줄(위생 시총 → 원 시총 큰 줄 · 동점 티커).
    돌려주는 것 (후보 행 목록, 셈{fin, fpi, dup})."""
    SU = sane(SU)
    me, raw = SU.me(m), SU.raw_me(m)
    rows, cnt = [], {"fin": 0, "fpi": 0, "dup": 0}
    for r in SU.members(m):
        sec, how = SU.sector(r["t"], m, r["ndx_only"])
        if sec == FIN_SECTOR:
            cnt["fin"] += 1
            continue
        if r.get("fpi"):
            cnt["fpi"] += 1
            continue
        rows.append(dict(r, sec=sec, sec_src=how, me=(me[r["t"]][0] or None), me_raw=(raw[r["t"]][0] or None), me_how=me[r["t"]][1]))
    best = {}
    for r in sorted(rows, key=lambda z: (-(z["me"] or 0.0), -(z["me_raw"] or 0.0), z["t"])):
        g = r.get("gid") or ("_" + r["t"])
        if g in best:
            cnt["dup"] += 1
            continue
        best[g] = r
    return sorted(best.values(), key=lambda z: z["t"]), cnt


def covered(SU, m, r):
    return bool(r["me"] and r["sec"] is not None and _price_ok(SU, r["k"], m))


def stage_world(U, m):
    """Stage M-W 세계(덮인 후보 · PN2) — 행 목록 [{t, k, gid, spx, ndx, ndx_only, fpi, sec, me, …}](티커 차례). w_geo · w_frag 가 부른다."""
    SU = sane(U)
    cands, _ = world_candidates(SU, m)
    return [r for r in cands if covered(SU, m, r)]


def coverage_rows(U, months):
    """PN2 — {결정 달: {n, n_px, cap, cap_px, n_nokey, fin, fpi, dup, n_flag, n_nosec, n_noprice, n_nome}}(개수 · 몫만 · 수익 없음)."""
    SU = sane(U)
    PP = WC.frozen("pit_panel")
    last = {}
    out = {}
    for m in sorted(months):
        cands, cnt = world_candidates(SU, m)
        i = SU.me_idx[m]
        _pairs, n_list = PP.union_members(SU.W, SU._eff(m), i)
        n_nokey = max(0, int(n_list) - len(SU.members(m)))
        cov = [r for r in cands if covered(SU, m, r)]
        med = {}
        for side in ("spx", "ndx"):
            v = [r["me"] for r in cov if (r["spx"] if side == "spx" else not r["spx"])]
            med[side] = float(np.median(v)) if v else None
        cap_px = float(sum(r["me"] for r in cov))
        cap = cap_px
        mn = WC.mno(m)
        for r in cands:
            if covered(SU, m, r):
                continue
            w = None
            lc = last.get(r["k"])
            if r["me"]:
                w = r["me"]
            elif lc and mn - lc[0] <= CAP_CARRY:
                w = lc[1]
            else:
                w = med["spx" if r["spx"] else "ndx"]
            cap += float(w or 0.0)
        cap += n_nokey * float(med["spx"] or 0.0)
        for r in cands:
            if r["me"]:
                last[r["k"]] = (mn, r["me"])
        flags = SU.flags(m)
        out[m] = {"n": len(cands) + n_nokey, "n_px": len(cov), "cap": cap, "cap_px": cap_px, "n_nokey": n_nokey, "fin": cnt["fin"],
                  "fpi": cnt["fpi"], "dup": cnt["dup"], "n_flag": len(flags),
                  "n_nosec": sum(1 for r in cands if r["sec"] is None), "n_noprice": sum(1 for r in cands if not _price_ok(SU, r["k"], m)),
                  "n_nome": sum(1 for r in cands if not r["me"])}
    return out


R_RULE = (0.90, 0.95)                               # 배치 R 커버리지 규칙(개수 ≥ 0.90 ∧ 시총 ≥ 0.95 · 보고 비교)


def tier1_months(cov_rows, window=TIER1):
    """PN2 — 달 판정 = 시총 몫(가격 · 위생 시총 · 섹터가 선 세계 후보의 시총 몫) ≥ 0.95(명세 «시총 · 가격 커버리지 ≥ 0.95» 의 시총 가중 읽기).
    보고: 개수 몫 · w_hygiene.coverage_f0(개수 ∧ 시총 ≥ 0.95 · 엔진 선언 H5 판) · 배치 R 규칙(개수 ≥ 0.90 ∧ 시총 ≥ 0.95) · 배치 R 목록과의 일치."""
    import w_hygiene as H
    use, fail, by = [], [], {}
    for m in sorted(cov_rows):
        if window and not (window[0] <= m <= window[1]):
            continue
        r = cov_rows[m]
        cn = (r["n_px"] / r["n"]) if r.get("n") else None
        cc = (r["cap_px"] / r["cap"]) if r.get("cap") else None
        ok = cc is not None and cc >= COV_THR
        by[m] = {"cov_n": cn, "cov_cap": cc, "use": ok}
        (use if ok else fail).append(m)
    h5 = H.coverage_f0(cov_rows, thr=COV_THR, window=window)
    rr = [m for m, b in by.items() if not (b["cov_n"] is not None and b["cov_cap"] is not None and b["cov_n"] >= R_RULE[0] and b["cov_cap"] >= R_RULE[1])]
    rf = sorted(set(H.R_TIER1_FAIL) & set(by))
    return {"months": use, "fail": fail, "T": len(use), "by_month": by, "thr": COV_THR,
            "rule": "PN2 — 시총 몫 ≥ %.2f(가격 · 위생 시총 · PIT 섹터가 선 세계 후보)" % COV_THR,
            "vs_R": {"R_fail": list(H.R_TIER1_FAIL), "same_fail": sorted(fail) == rf, "only_W": sorted(set(fail) - set(rf)), "only_R": sorted(set(rf) - set(fail))},
            "sensitivity": {"count_and_cap_095": {"T": h5["T"], "n_fail": len(h5["fail"]), "months": h5["months"]},
                            "R_rule_count090_cap095": {"T": len(by) - len(rr), "fail": sorted(rr)}},
            "count_share_min": (min(b["cov_n"] for b in by.values() if b["cov_n"] is not None) if by else None)}


# ══════════════════════════════════════════════════════════════════════════
#  V06 VAL(PN4) · V 단면(PN7) · 슬리브 단면
# ══════════════════════════════════════════════════════════════════════════
def _v_inputs(SU, m, fund=False, beta=False):
    """frozen v_cards.Cross 입력 — 위생 시총 · w_B · 신호(섹터 · (FP β̂ · 12-2 · 그달 수익) · (재무 ni · rev TTM)) · 나머지 칸은 비운다."""
    VF = WC.frozen("v_fund")
    d = SU.d_of(m)
    sig = {}
    for r in SU.members(m):
        rec = {"sector": SU.sector(r["t"], m, r["ndx_only"])[0]}
        if beta:
            rec["beta_fp"] = SU.beta_fp(r["k"], m)["beta"]
            rec["mom12_2"] = SU.mom12_2(r["k"], m)
            rec["month_ret"] = SU.month_ret(r["k"], m)
        if fund and r.get("gid"):
            ni = VF.ttm_key(SU.L, r["gid"], "ni", d)
            rv = VF.ttm_key(SU.L, r["gid"], "rev", d)
            rec["fund"] = {"ni_ttm": ni[0] if ni else None, "rev_ttm": rv[0] if rv else None}
        sig[r["t"]] = rec
    return {"members": SU.members(m), "w_B": SU.w_B(m), "me": SU.me(m), "signals": sig, "irrx": {}, "ear": {}, "ch": {}, "ins": {}}


def v_cross(U, m):
    """PN7 — W06(V01) · W12(V02) 용 frozen v_cards.Cross(위생 시총 · FP β̂ · 12-2 · 그달 수익 · 섹터)."""
    SU = sane(U)
    return WC.frozen("v_cards").Cross(m, _v_inputs(SU, m, beta=True))


def val_scores(U, m, world):
    """PN4 — V06 VAL 점수(frozen v_cards.signal_of · use_sp = V F0 결정) → 세계 행 차례 · 섹터 안 z(결측 NaN)."""
    import w_ipca as IP
    SU = sane(U)
    VK = WC.frozen("v_cards")
    Xv = VK.Cross(m, _v_inputs(SU, m, fund=True))
    sc, el, _g = VK.signal_of(Xv, VK.spec_of("V06", use_sp=V06_USE_SP))
    s = {Xv.t[i]: float(sc[i]) for i in np.flatnonzero(el) if np.isfinite(sc[i])}
    v0 = np.array([s.get(r["t"], np.nan) for r in world], float)
    sec = np.array([r["sec"] for r in world], object)
    z = IP.sector_z(v0, sec)
    out = np.full(len(world), np.nan)
    ok = np.isfinite(v0)
    out[ok] = z[ok]
    return out


def sleeve_cross(U, m):
    """슬리브 단면(w_cards.Cross) — 명단 전체(위생 시총이 선 이름 · 금융 포함 · 섹터 없음 칸 허용) · w_B · FP β̂(β 띠)."""
    import w_cards as WCD
    SU = sane(U)
    me = SU.me(m)
    rows = []
    for r in SU.members(m):
        v = me[r["t"]][0]
        if not v:
            continue
        sec, _ = SU.sector(r["t"], m, r["ndx_only"])
        rows.append(dict(r, me=float(v), sec=sec))
    rows.sort(key=lambda z: z["t"])
    wb = SU.w_B(m)
    beta = [SU.beta_fp(r["k"], m)["beta"] for r in rows]
    return WCD.Cross(m, [r["t"] for r in rows], [r["me"] for r in rows], [wb.get(r["t"], 0.0) for r in rows], [r["sec"] for r in rows],
                     [r["ndx_only"] for r in rows], [np.nan if b is None else b for b in beta], k=[r["k"] for r in rows])


# ══════════════════════════════════════════════════════════════════════════
#  패널(굽기 입력)
# ══════════════════════════════════════════════════════════════════════════
def daily_matrix(U):
    """일간 수익 행렬(격자 × 가격 키) · 열 색인 — 신호의 입력(과거 수익)."""
    keys = sorted(U.PX)
    kcol = {k: j for j, k in enumerate(keys)}
    DR = np.column_stack([U.daily_ret(k) for k in keys])
    return DR, kcol


def panel_months(U, a=PANEL_FROM, b=TIER1[1]):
    return [m for m in U.months if a <= m <= b and WC.mshift(m, 1) in U.me_idx]


def month_panel(U, m, DR, kcol, mkt_d, with_beta=True, with_y=True):
    """결정 달 m 의 패널 행렬(세계 차례) — t · k · gid · me · sec · y · val · tail · beta_fp · KPS8 원값 · fin. 🚨 y 를 찍지 않는다."""
    import w_cards as WCD
    import w_ipca as IP
    SU = sane(U)
    VF = WC.frozen("v_fund")
    world = stage_world(SU, m)
    if not world:
        return None
    d = SU.d_of(m)

    def asset_of(r, dd):
        if not r.get("gid"):
            return None
        at = VF.latest(SU.L.series(r["gid"], "asset", "i"), dd)
        return at[0] if at else None
    K8 = IP.kps8_month(SU, m, world, mkt_d, asset_of=asset_of, DR=DR, kcol=kcol)
    if with_y:
        hr = SU.hold_ret(m)
        y = np.array([np.nan if hr.get(r["t"]) is None else float(hr[r["t"]]) for r in world])
    else:                                                                  # F0 — 다음 달 수익을 읽지 않는다
        y = np.full(len(world), np.nan)
    i1 = SU.me_idx[m]
    cols = [kcol[r["k"]] for r in world]
    Rw = DR[max(0, i1 - TAIL_WIN + 1):i1 + 1][:, cols]
    D = {"t": [r["t"] for r in world], "k": [r["k"] for r in world], "gid": [r.get("gid") for r in world],
         "me": np.array([r["me"] for r in world], float), "sec": np.array([r["sec"] for r in world], object), "y": y,
         "val": val_scores(SU, m, world), "tail": WCD.tail_shape(Rw), "fin": np.zeros(len(world), bool),
         "ndx_only": np.array([bool(r["ndx_only"]) for r in world]), "spx": np.array([bool(r["spx"]) for r in world])}
    D.update(K8)
    if with_beta:
        D["beta_fp"] = np.array([np.nan if SU.beta_fp(r["k"], m)["beta"] is None else SU.beta_fp(r["k"], m)["beta"] for r in world], float)
    else:
        D["beta_fp"] = np.full(len(world), np.nan)
    D["n_kps"] = np.sum([np.isfinite(D[c]) for c in IP.KPS8], axis=0)
    return D


def build_panel(U, months, DR, kcol, mkt_d, beta_from=TIER1[0], sleeve_from=TIER1[0], log=_log, with_y=True):
    """패널 {"kind": "real", "months", "m"} · 슬리브 단면 {달: w_cards.Cross}(sleeve_from ~) — kind real(러너가 곧바로 자물쇠 · 눈가림을 건다)."""
    SU = sane(U)
    P = {"kind": ("real" if with_y else "f0"), "months": [], "m": {}}
    X, t0 = {}, time.time()
    for j, m in enumerate(months):
        D = month_panel(SU, m, DR, kcol, mkt_d, with_beta=(m >= beta_from), with_y=with_y)
        if D is None:
            continue
        P["months"].append(m)
        P["m"][m] = D
        if m >= sleeve_from:
            X[m] = sleeve_cross(SU, m)
        if log and j % 24 == 0:
            log("  패널 %s · 세계 %d · %.0fs" % (m, len(D["t"]), time.time() - t0))
    return P, X


def kps_coverage(P, months=None):
    """PN3 — {달: KPS8 원값 ≥ 6 개인 세계 이름 몫} · 통과 달 · 못 넘은 달."""
    by, bad = {}, []
    for m in (months or P["months"]):
        D = P["m"].get(m)
        if D is None:
            continue
        v = np.asarray(D["n_kps"], float)
        s = float(np.mean(v >= KPS_MIN_FEATURES)) if len(v) else 0.0
        by[m] = s
        if s < KPS_COVER_MIN:
            bad.append(m)
    return {"by_month": by, "fail": bad, "min": (min(by.values()) if by else None), "rule": "KPS8 원값 ≥ %d 인 이름 몫 ≥ %.2f" % (KPS_MIN_FEATURES, KPS_COVER_MIN)}


# ══════════════════════════════════════════════════════════════════════════
#  selftest(합성 자료만 — v_pit.fake_universe)
# ══════════════════════════════════════════════════════════════════════════
def _raises(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


def _st_rule():
    assert me_check(None, None) is None and me_check(0.0, None) is None
    assert me_check(299.9, None) == "floor" and me_check(300.0, None) is None and me_check(8.0e6 + 1, None) == "ceil"
    assert me_check(1000.0, 1000.0) is None and me_check(1000.0, 4999.0) is None and me_check(1000.0, 5001.0) == "ledger"
    assert me_check(5000.0, 999.0) == "ledger" and me_check(5000.0, 1001.0) is None and me_check(5000.0, None) is None
    assert me_check(80.0, 80000.0) == "floor"                                    # 1/1000 단위 사고 — 바닥이 먼저
    return "PN1 규칙(바닥 · 천장 · 원장 대조 띠 경계 · 원장 없음)"


def _fake():
    VP = WC.frozen("v_pit")
    U, _ = VP.fake_universe(n=30, seed=11)
    return U


def _st_sane_proxy():
    U = _fake()
    SU = SaneUniverse(U, lab_check=False)
    m = "2015-06"
    raw = U.me(m)
    t0 = sorted(t for t, v in raw.items() if v[0])[0]
    want = {}
    for t, v in raw.items():
        why = me_check(float(v[0]), None) if v[0] else None
        want[t] = (None, "w_sane:" + why) if why else v
    assert SU.me(m) == want                                                    # 규칙이 이름-달마다 그대로 걸린다
    fl = SU.flags(m)
    assert fl == {t: want[t][1][len("w_sane:"):] for t in want if want[t][0] is None and raw[t][0]}
    wb = SU.w_B(m)
    assert all(want[t][0] for t in wb) and (abs(sum(wb.values()) - 1.0) < 1e-12 if wb else True)
    assert SU.dates is U.dates and SU.PX is U.PX and SU.members(m) == U.members(m)            # 나머지는 그대로 넘긴다
    # 위생이 한 이름을 걸면 그 이름은 w_B · 시총에서 빠진다(바닥을 올려 한 이름을 건다)
    global ME_FLOOR
    old = ME_FLOOR
    try:
        vals = sorted(float(v[0]) for v in raw.values() if v[0])
        ME_FLOOR = (vals[0] + vals[1]) / 2.0
        SU3 = SaneUniverse(U, lab_check=False)
        f3 = SU3.flags(m)
        assert len(f3) == 1 and list(f3.values()) == ["floor"] and list(f3)[0] not in SU3.w_B(m)
    finally:
        ME_FLOOR = old
    assert sane(U) is sane(U) and sane(sane(U)) is sane(U)
    # 바닥을 0 으로 내리면(단위 규약을 합성에 맞춘다) 위생 = 원 시총 · w_B = 얼린 w_B
    old = ME_FLOOR
    try:
        ME_FLOOR = 0.0
        SU2 = SaneUniverse(U, lab_check=False)
        assert SU2.me(m) == raw and SU2.flags(m) == {}
        wb, wb0 = SU2.w_B(m), U.w_B(m)
        assert set(wb) == set(wb0) and max(abs(wb[t] - wb0[t]) for t in wb) < 1e-15
        assert SU2.me_of_ticker(t0, m) == U.me_of_ticker(t0, m)
        b1 = SU2.beta_fp(U.members(m)[0]["k"], m)
        assert b1 == U.beta_fp(U.members(m)[0]["k"], m) and SU2.beta_fp(U.members(m)[0]["k"], m) is b1        # 메모
    finally:
        ME_FLOOR = old
    return "위생 우주(이름-달 규칙 · 나머지 속성 그대로 · 바닥 0 이면 얼린 me · w_B 와 같다 · β̂ 메모)"


def _st_world_cov():
    global ME_FLOOR
    old = ME_FLOOR
    try:
        ME_FLOOR = 0.0
        U = _fake()
        SU = SaneUniverse(U, lab_check=False)
        _SANE[id(U)] = (U, SU)
        m = "2015-06"
        cands, cnt = world_candidates(SU, m)
        w = stage_world(U, m)
        assert all(r["sec"] != FIN_SECTOR and not r.get("fpi") for r in w) and len({r.get("gid") or r["t"] for r in w}) == len(w)
        assert [r["t"] for r in w] == sorted(r["t"] for r in w) and len(w) <= len(cands)
        rows = coverage_rows(U, ["2015-05", "2015-06", "2015-07"])
        r = rows[m]
        assert r["n"] >= r["n_px"] and r["cap"] >= r["cap_px"] > 0 and r["n_px"] == len(w)
        c = tier1_months(rows, window=("2015-05", "2015-07"))
        assert c["T"] + len(c["fail"]) == 3
        # 편출 이름(N03 · 가격 끝) — 가격 없는 달은 덮이지 않는다
        m2 = [x for x in sorted(U.me_idx) if x > U.dates[1800][:7]][1]
        w2 = stage_world(U, m2)
        assert "N03" not in [x["t"] for x in w2]
    finally:
        ME_FLOOR = old
    return "세계(비금융 · 비FPI · 그룹당 한 줄 · 차례) · 커버리지 행(분모 ≥ 덮임 · 시총 몫) · 달 판정 · 편출 뒤 제외"


def _st_static():
    WG.assert_units(PANEL_UNITS, "selftest")
    assert _raises(lambda: WG.assert_units([WG.unit("be", source="v_fund", use="control")], "st"))
    r = WG.noeg_static(targets=["w_panel"])
    assert r["ok"], r
    return "입력 단위 · 장부 자본 거부 · G-NoEG 정적(w_panel 폐포 %d)" % r["n_reached"]


def _st_overlay():
    """PN8 — 빈 칸만(멤버 창 안) · 있는 값 그대로 · 오늘 키 · 다른 키 값 있는 날 건너뜀 · 멈춤 판정 더하기 · 격자 앞부분 규칙 · 형식 · 저장소 밖(합성 파일만)."""
    import json
    import tempfile
    dates = ["2020-01-%02d" % d for d in range(1, 29)] + ["2020-02-%02d" % d for d in range(1, 29)] + ["2020-03-%02d" % d for d in range(1, 29)]
    D = len(dates)
    nan = np.full(D, np.nan)
    W = {"dates": dates, "D": D, "today": {"TOD"}, "splice": {}, "stops": {},
         "PX": {"TOD": np.ones(D), "OLD": nan.copy(), "HAS": np.where(np.arange(D) < 30, 5.0, np.nan), "ALT": np.full(D, 7.0)},
         "lists": {"spx": {"2020-01": ["OLD", "HAS", "NEW", "TOD"], "2020-02": ["HAS", "NEW", "TOD"]}, "ndx": {}}}
    W["PX"]["OLD"][:10] = 3.0
    ov = {"format": PX_OVERLAY_FORMAT, "visibility": "INTERNAL", "dates": dates[:70],
          "px": {"OLD": {"i0": 0, "p": [9.0] * 70}, "HAS": {"i0": 0, "p": [6.0] * 70}, "NEW": {"i0": 5, "p": [2.0] * 60},
                 "TOD": {"i0": 0, "p": [4.0] * 70}, "ALTK": {"i0": 0, "p": [8.0] * 70}},
          "keys": {"NEW": {"tickers": ["NEW"]}, "ALTK": {"tickers": ["ALT"]}},
          "stops": {"NEW": [{"d": dates[64], "y": "last_price", "why": "합성"}]}}
    W["lists"]["spx"]["2020-01"].append("ALT")
    with tempfile.TemporaryDirectory() as td:
        fp = os.path.join(td, "ov.json")
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(ov, f)
        r = apply_px_overlay(W, fp)
        assert np.all(W["PX"]["OLD"][:10] == 3.0) and np.all(W["PX"]["OLD"][10:56] == 9.0) and np.isnan(W["PX"]["OLD"][56:]).all()   # 1 · 2월 멤버 창만
        assert np.all(W["PX"]["HAS"][:30] == 5.0) and np.all(W["PX"]["HAS"][30:70] == 6.0) and np.isnan(W["PX"]["HAS"][70:]).all()   # 3월 = 2월 멤버 + 다음 달
        assert np.all(W["PX"]["TOD"] == 1.0) and "NEW" in W["PX"] and np.all(W["PX"]["NEW"][5:65] == 2.0) and "ALTK" not in W["PX"]
        assert W["stops"]["NEW"][dates[64]]["by"] == "overlay" and r["keys_new"] == 1 and r["skipped"]["today_key"] == 70
        assert r["skipped"]["priced_under_other_key"] > 0 and r["skipped"]["kept_existing"] > 0 and "path" not in json.dumps(r)
        bad = dict(ov, dates=["1999-01-01"] + dates[1:70])
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(bad, f)
        _OV_DOC.clear()
        assert _raises(lambda: apply_px_overlay(dict(W, PX=dict(W["PX"])), fp))                                  # 격자 앞부분이 다르면 멈춤
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(dict(ov, format="x"), f)
        _OV_DOC.clear()
        assert _raises(lambda: apply_px_overlay(W, fp))
    _OV_DOC.clear()
    old = os.environ.get(PX_OVERLAY_ENV)
    try:
        os.environ[PX_OVERLAY_ENV] = os.path.join(WC.ROOT, "data", "stocks.json")
        assert _raises(px_overlay_path)                                                                            # 저장소 안 파일 거부
        os.environ[PX_OVERLAY_ENV] = os.path.join(tempfile.gettempdir(), "wb_no_such_overlay.json")
        assert _raises(px_overlay_path)                                                                            # 없으면 멈춤(fail-closed)
        os.environ.pop(PX_OVERLAY_ENV, None)
        assert _raises(px_overlay_path)                                                                            # 환경변수 없음 = 멈춤
    finally:
        if old is None:
            os.environ.pop(PX_OVERLAY_ENV, None)
        else:
            os.environ[PX_OVERLAY_ENV] = old
    return "빈 칸만(멤버 창 + 다음 달) · 있는 값 · 오늘 키 · 다른 키 날 그대로 · 새 키 · 멈춤 판정 · 격자 앞부분 · 형식 · 저장소 안 · 없는 파일 = 멈춤"


def selftest():
    res, ok = [], True
    for fn in (_st_rule, _st_sane_proxy, _st_world_cov, _st_overlay, _st_static):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:                                                    # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-16s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("w_panel selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
