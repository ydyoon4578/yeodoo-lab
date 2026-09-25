# -*- coding: utf-8 -*-
"""build/eg_q5_vintage.py — build/eg_q5.py(얼린 측정)의 복사본 + 재무 공급자 끼움 하나 (사전등록 PREREG-2026-09-25-EGFF §3)

🚨 EGFF 끼움 — 이 복사본이 eg_q5.py 와 다른 자리는 아래 «EGFF» 로 표시한 곳뿐이다.
  ① 재무 공급자(Supplier): state() 가 읽는 재무(Firm)와 주식수(sh)를 공급자에게서 받는다.
       latest = 지금의 경로(data/fx · fx_pit 의 최신 제출본 · tech_backtest.load_fund) — 얼린 판과 바이트 동일(재현 단언)
       v      = P-V 빈티지 패널: 날짜 d 에서 칸(발행사 그룹 · 태그 · 기간말 · 기간 길이)마다 가용일 ≤ d 인 제출 중 filed 가 가장 늦은 값
                · 1단계 결정의 기준(태그 규칙 = 형제 태그 메움 · 아래)
       ff     = P-FF 쌍둥이: 영원히 최초 제출값(가용일 규칙 · 태그 규칙은 v 와 같다) — 보고만
       vs     = P-VS 쌍둥이: v 와 같되 **최신판 태그만**(엄격 태그 · 형제 태그 메움 없음) — 보고만(2026-09-26 적대 검토 뒤 겹침 전 선언)
     칸 집합(키 · 버킷 · 기간말)은 최신판(data/fx · fx_pit)의 것과 같다 — 차이는 «그 칸의 어느 제출값을 언제부터 쓰나» 뿐이다.
     태그 규칙(v · ff): 최신판 태그 먼저 · 그 태그가 그 기간말을 아직 싣지 않은 날에는 같은 Eg 키의 다른 후보 태그(refresh_facts 순서)의
     가용 기록(vintage_pick — 태그 갈아타기 칸을 «그때 없던 값» 으로 잘못 세지 않게 · 사전등록 §1 «그때까지 제출된 숫자»).
     🚨 이 메움은 §2 의 «태그마다» 문구를 넘어서는 읽기이고 refresh_facts.extract 는 한 항목 안에서 태그를 섞지 않는다 — 그래서
       겹침을 보기 전에 선언하고(data/_s4_f0.json declared · stage1_plan) 엄격 태그 쌍둥이 vs 를 같이 굽는다.
     원장 = data/_fxv/(build/fxv_build.py). sh 는 제출 당시 기준이라: 기록 단위 사고를 날짜와 무관한 기준으로 정리(_unit_clean) →
     «분할 기준일»(같은 값을 실은 가장 늦은 filed · _basis) 뒤의 실제 분할만큼 되맞춘다(splits.json 효력일 ·
     tech_backtest.split_kinds 의 실제/분사형/섞임 판정 재사용 · 분사형 몫은 기간말 뒤 전부). 날짜마다의 _clean_units 와
     야후 빈 곳 메우기(merge_shares_yf)는 최신판과 같은 함수를 그대로 태운다.
  ② 수익 울타리: --pit-gics 에서 얼린 코드가 계산만 하고 버리던 다음 달 수익 · 다리 · 회전 · F4 는 계산하지 않는다
     (점수 · fin_lookups 는 한 바이트도 안 바뀐다 — 재현 단언이 그것을 보인다). --pit-gics 없이는 돌지 않는다.
  ③ 진단(--diag PATH): 달마다 회귀 표본 수와 그중 2026 전에 떠난 이름 수(기울기 생존 점검 · F0 보고) · 편입 후보 수.

  python build/eg_q5_vintage.py --pit-gics --supplier latest|v|ff|vs [--out PATH] [--diag PATH]

── 아래는 원본 eg_q5.py 의 머리 주석 그대로 ──
build/eg_q5.py — 기대투자성장(Eg · Hou·Mo·Xue·Zhang RoF 2021) 시점정확 검정 → data/_eg_q5.json

사전등록: build/PREREG-2026-09-23-EG.md (계산 전 커밋 cee33124)

원문 3.1절을 랩 자료로 옮긴다 —
  ① 매월 t: 랩이 재무를 가진 전 종목(금융·음(−)자본 제외)에서
       y = (t 에 알려진 I/A) − (t−12 에 알려져 있던 I/A)
     를 t−12 의 [log q, Cop, dRoe] 에 시총가중 WLS 로 회귀(좌우변 1–99% 윈저) → 기울기 b_t
  ② 평균 기울기 = 직전 120개월 b 의 평균(최소 30개월)
  ③ 형성월 t 의 예측 E_t = [1, X_t(윈저)] · 평균 기울기
  ④ 그때의 S&P 500 ∪ NASDAQ 100 멤버(금융 제외)를 E_t 3분위(30/70)로 갈라 시총가중, 다음 달 보유
🚨 원문과 다른 자리(사전등록 §1): Cop ≈ cfo(연간) ÷ 총자산 · dRoe 는 90일 지난 최신 분기 · 회귀 표본은 랩 전 종목.
🚨 한 번 굽는 얼린 측정이다. CI 에 붙이지 않는다.

  python build/eg_q5.py
"""
from __future__ import annotations
import bisect, io, json, math, os, sys, time
from datetime import date, timedelta

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import index_members as IM            # noqa: E402
import tech_backtest as TB            # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_eg_q5.json")

F0, F1_ = "2016-08", "2026-07"
POST = "2019-01"
REG0 = "2010-01"          # 회귀를 시작하는 달(재무가 2008 무렵부터라 t−12 설명변수가 서는 첫 해)
ROLL, ROLL_MIN = 120, 30
LAG_Q = 90                # dRoe 분기 공시 지연(랩 FUND_LAG_DAYS)
COST = 0.0010
F_T = 1.5
KEEP_DUAL = {"GOOGL", "FOXA", "NWSA"}
# 🚨 2026-09-24 — `--pit-gics`: 금융 판정을 **그때의 GICS** 로. 랩의 섹터는 오늘 것뿐이라 GICS 개편이 미래 정보가 됐다 —
#   2023-03 결제 처리(IT → 금융: V·MA·PYPL…)가 2016~2023 에도 빠졌고, 2016-09 부동산 분리 전의 리츠는 반대로 들어갔으며,
#   종목별 리츠 편입(AMT 2012 · CCI 2014 · WY 2011)과 끝내 금융이 아니었던 회사(EQIX IT · IRM 산업재)도 섞였다.
#   적대 검토(PREREG-2026-09-24-EGBEST 1·3차)가 잡았다. 손으로 적은 예외 대신 **월말 위키 표의 GICS 열**(data/pit_gics.json ·
#   build/pit_gics.py)로 가른다: 그달 표에 있으면 그 분류 · 없으면 가장 가까운 달의 분류 · 그것도 없으면 오늘 분류.
#   깃발이 없으면 계산·산출물이 한 바이트도 달라지지 않는다(얼린 측정 PREREG-2026-09-23-EG 그대로).
PIT_GICS = "--pit-gics" in sys.argv
# --from YYYY-MM(--pit-gics 와 함께만): 판정 창 앞 형성월(그달 ~ 2016-07)의 점수만 따로 쓴다 — EG30+ 창 이전 점검(PREREG-2026-09-24-EG30PLUS).
#   회귀·기울기·금융 판정은 --pit-gics 와 같고, 2016-08 이후 점수는 쓰지 않는다(얼린 두 산출물은 그대로).
PRE_FROM = sys.argv[sys.argv.index("--from") + 1] if (PIT_GICS and "--from" in sys.argv) else None
PRE_TO = "2016-07"

# ════════════════════════════════════════════════════════════════════════
# 🚨 EGFF ① 재무 공급자 끼움(PREREG-2026-09-25-EGFF §3)
# ════════════════════════════════════════════════════════════════════════
SUPPLIER = sys.argv[sys.argv.index("--supplier") + 1] if "--supplier" in sys.argv else "latest"
OUT_SCORES = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
DIAG = sys.argv[sys.argv.index("--diag") + 1] if "--diag" in sys.argv else None
LEFT_BEFORE = "2026-01-01"            # 기울기 생존 점검 — 마지막 가격이 이 날 전이면 «2026 전에 떠난 이름»
EGFF_PREREG = "build/PREREG-2026-09-25-EGFF.md"


def vintage_pick(subs, d, kind):
    """칸 하나의 d 시점 값 → (값, filed, 태그 순번) | None.

    subs = [(가용일들, 값들, filed 들, 태그 순번)] — 태그 순서 = 최신판 태그 먼저, 그다음 같은 Eg 키의 다른 후보(refresh_facts 순서).
    한 태그 안의 기록은 filed 오름차순이고 가용일은 filed 에 대해 줄지 않는다.
      v  — 앞선 태그부터 보아 d 에 가용한 기록이 있는 첫 태그의 «가용일 ≤ d 인 마지막 기록»(= filed 가 가장 늦은 가용 기록)
      ff — 앞선 태그부터 보아 첫 기록이 d 에 가용한 첫 태그의 첫 기록(영원히 최초 제출값)
    다른 후보 태그는 최신판 태그가 그 기간말을 아직 싣지 않았을 때만 쓰인다 — 회사가 태그를 갈아탄 칸(실측: AAPL 영업현금흐름
    FY2014~2016 은 …ContinuingOperations 로만 제출됐고 최신판 태그로는 2017-11 비교기간에서야 처음 실렸다)을 «그때 없던 값» 으로
    잘못 세지 않게 한다. 그때 랩의 경로(refresh_facts.extract)는 가장 최근까지 보고된 태그 — 곧 그 형제 태그 — 를 골랐을 것이다.
    엄격 태그 쌍둥이(vs)는 subs 를 최신판 태그(순번 0)만 남겨 넘긴다(Supplier.strict)."""
    for av, vs, fs, ti in subs:
        if kind == "ff":
            if av[0] <= d:
                return vs[0], fs[0], ti
        else:
            i = bisect.bisect_right(av, d) - 1
            if i >= 0:
                return vs[i], fs[i], ti
    return None


def ledger_subs(L, cands, k, tx, src, b, pe):
    """원장 한 그룹 → 칸(키 · 버킷 · 기간말)의 subs(vintage_pick 입력). 최신판 태그 src 먼저, 나머지 후보는 refresh_facts 순서."""
    order = [src] + [t for t in ((cands.get(k) or {}).get(tx) or []) if t != src]
    subs = []
    for ti, tag in enumerate(order):
        r = (((L.get("keys") or {}).get("%s:%s:%s" % (k, tx, tag)) or {}).get(b) or {}).get(pe) or []
        if r:
            subs.append(([x[0] for x in r], [x[1] for x in r], [x[4] for x in r], ti))
    return subs


class Supplier:
    """state() 가 읽는 재무의 공급자. kind = latest | v | ff | vs.

    latest — FIRMS(data/fx · fx_pit 의 Firm)와 FUND(tech_backtest.load_fund 의 sh)를 그대로 준다(날짜를 보지 않는다).
    v · ff · vs — 원장 data/_fxv 의 제출 기록으로 날짜 d 에서 알 수 있던 값만 담은 Firm 과 sh 계열을 짓는다
      (vs = v 의 고르기에 최신판 태그만 · 형제 태그 기록은 칸에서 뺀다).
      칸 집합 = 최신판 파일의 (키 · 버킷 · 기간말) — Firm/load_fund 가 고르는 버킷(시점 i 가 있으면 i, 없으면 q · sh 는 i/q 가
      비면 a) · 최신판 태그(src) 먼저. 값은 vintage_pick(v = 가용일 ≤ d 중 filed 가 가장 늦은 기록 · ff = 첫 기록).
      원장에 기록이 하나도 없는 최신판 칸은 v · ff 에서 영영 가용하지 않다(F0 (i) 가 그 수를 센다 — 실측 0).
    sh(v · ff) — 칸 값은 제출 당시 기준이다. 기록마다 단위 사고를 날짜와 무관한 기준으로 먼저 정리하고(_unit_clean — 최신판과 같은 문턱)
      load_fund 과 같은 순서로 짓는다: sh 가 시작하기 전만 sho 로 잇기 → _clean_units → 분할 되맞춤(최신판이 가른 split_kinds 를
      그대로 · 분사형 몫 r/q 는 기간말 뒤 전부 · 실제 분할 q 는 **그 기록의 분할 기준일 뒤** 것만 — 기준일 = 같은 값을 실은 가장 늦은
      filed(_basis)) → 분할 이력을 모르는 편출 종목은
      최신판과 같은 이음매 앞을 뺀다 → merge_shares_yf(야후 빈 곳 메우기 · 최신판과 같은 함수).
    """

    FIELDS = (("asset", "inst"), ("debt", "inst"), ("eq", "inst"), ("ni", "q"), ("ni", "a"), ("cfo", "a"))

    KINDS = {"latest": (None, None), "v": ("v", False), "ff": ("ff", False), "vs": ("v", True)}   # 종류 → (고르기, 엄격 태그)

    def __init__(self, kind, FIRMS, FUND, data_dir=None):
        if kind not in self.KINDS:
            raise SystemExit("🚨 --supplier 는 latest · v · ff · vs 중 하나")
        self.kind, self.FIRMS, self.FUND = kind, FIRMS, FUND
        self.pick, self.strict = self.KINDS[kind]
        self.stat = {"cells": 0, "cells_no_record": 0, "cells_lf_tag_missing": 0, "cells_with_sibling": 0,
                     "cells_sibling_removed": 0, "firm_builds": 0, "sh_builds": 0, "tag_rule": "strict" if self.strict else "sibling_fill"}
        if kind == "latest":
            return
        import gzip, hashlib
        data_dir = data_dir or DATA
        vd = os.path.join(data_dir, "_fxv")
        IX = json.load(io.open(os.path.join(vd, "index.json"), encoding="utf-8"))
        self.index_sha = hashlib.sha256(open(os.path.join(vd, "index.json"), "rb").read()).hexdigest()
        self.cands = IX["candidates"]
        self.SPL = TB.load_splits()
        led = {}

        def ledger(gid):
            if gid not in led:
                g = IX["groups"][gid]
                b = open(os.path.join(vd, g["file"]), "rb").read()
                if hashlib.sha256(b).hexdigest() != g["sha256"]:
                    raise SystemExit("🚨 원장 파일 해시가 색인과 다르다 — %s" % g["file"])
                led[gid] = json.loads(gzip.decompress(b).decode("utf-8"))
            return led[gid]
        self.C, self.EPOCH, self.src, self.memo_f, self.memo_s = {}, {}, {}, {}, {}
        for sub in ("fx", "fx_pit"):
            dd = os.path.join(data_dir, sub)
            for fn in sorted(os.listdir(dd)):
                if not fn.endswith(".json"):
                    continue
                tk = fn[:-5]
                if tk in self.C:
                    continue
                j = json.load(io.open(os.path.join(dd, fn), encoding="utf-8"))
                tg = j.get("tags") or {}
                ti = IX["tickers"].get(tk)
                L = ledger(ti["gid"]) if ti else {"keys": {}}
                tx = "ifrs-full" if j.get("std") == "IFRS" else "us-gaap"
                cells = {}

                def build(field, k, b, tg=tg, L=L, tx=tx, cells=cells):
                    v = tg.get(k) or {}
                    ser = [x for x in (v.get(b) or []) if isinstance(x, list) and len(x) == 2 and isinstance(x[1], (int, float))]
                    rows = []
                    for pe, _val in ser:
                        subs = ledger_subs(L, self.cands, k, tx, v.get("src"), b, pe)
                        if self.strict:                  # vs — 최신판 태그(순번 0)의 기록만
                            self.stat["cells_sibling_removed"] += any(s_[3] != 0 for s_ in subs)
                            subs = [s_ for s_ in subs if s_[3] == 0]
                        self.stat["cells"] += 1
                        if not subs:
                            self.stat["cells_no_record"] += 1
                            continue
                        self.stat["cells_lf_tag_missing"] += subs[0][3] != 0
                        self.stat["cells_with_sibling"] += len(subs) > 1 or subs[0][3] != 0
                        rows.append((pe, subs))
                    cells[field] = (b, rows)
                for k, kind_ in self.FIELDS:
                    v = tg.get(k) or {}
                    if kind_ == "inst":
                        b = "i" if v.get("i") else ("q" if v.get("q") else None)   # Firm.inst: i 가 있으면 i, 없으면 q
                        if b:
                            build(k, k, b)
                    elif v.get(kind_):
                        build(k + "_" + kind_, k, kind_)
                # sh — load_fund 과 같은 버킷: series("sh")(i 가 있으면 i, 없으면 q)가 비면 annual("sh") · sho 는 i/q
                v = tg.get("sh") or {}
                b = "i" if v.get("i") else ("q" if v.get("q") else None)
                ok_ = [x for x in (v.get(b) or []) if isinstance(x, list) and len(x) == 2 and isinstance(x[1], (int, float))] if b else []
                if not ok_:
                    b = "a" if v.get("a") else None
                if b:
                    build("sh", "sh", b)
                v = tg.get("sho") or {}
                b = "i" if v.get("i") else ("q" if v.get("q") else None)
                if b:
                    build("sho", "sho", b)
                self.C[tk] = cells
                self.src[tk] = sub
        self._unit_clean()
        self._basis()
        for tk, cells in self.C.items():
            self.EPOCH[tk] = sorted({a for _b, rows in cells.values() for _pe, subs in rows for av, _v, _f, _t in subs for a in av})

    @staticmethod
    def fac(spl, pe, filed):
        """제출 당시 기준 → 오늘 기준 배수: 분사형 몫 r/q 는 기간말 뒤 전부 · 실제 분할 q 는 그 제출(filed) 뒤의 것만."""
        f = 1.0
        for x in spl:
            if x["s"] > pe:
                f *= x["r"] / x["q"]
            if x["s"] > filed and x["q"] != 1.0:
                f *= x["q"]
        return f

    def _unit_clean(self):
        """sh · sho 기록의 단위 사고(천주 ↔ 백만주)를 **날짜와 무관한 기준**으로 정리한다(최신판 _clean_units 와 같은 문턱).

        최신판은 계열 전체의 중앙값으로 가른다(tech_backtest._clean_units). 빈티지 계열을 날짜마다 그 함수에만 맡기면 이른 날짜의
        짧은 계열에서 사고 기록이 다수가 돼 중앙값이 사고 쪽으로 간다(실측: COP 2014~2021 · LNC 2011 · TSCO · AAP · HSIC —
        P-V 가 1000배 · 100만배 틀린 값을 정상으로 읽었다). 그래서 기록마다 오늘 기준으로 옮긴 값을 최신판 sh 계열(시총 기준 ·
        정리된 것)의 중앙값과 견준다: 500~2000배면 ÷1000 · 1/2000~1/500 이면 ×1000 · 0.01~100배 밖이면 그 기록을 뺀다
        (다른 기록이 있으면 그 칸은 남는다). 날짜마다의 _clean_units 는 그 뒤에 최신판과 같이 한 번 더 탄다."""
        self.stat.update({"sh_unit_rescaled": 0, "sh_unit_dropped": 0, "sh_cells_dropped": 0})
        for tk, cells in self.C.items():
            spl = TB.SPLIT_KIND.get(tk) or []
            ref = sorted(v for _d, v in ((self.FUND.get(tk) or {}).get("sh") or []) if v and v > 0)
            if not ref:
                ref = sorted(v * self.fac(spl, pe, f) for fld in ("sh", "sho") for pe, subs in cells.get(fld, (None, []))[1]
                             for _av, vs, fs, _t in subs for v, f in zip(vs, fs) if v and v > 0)
            if not ref:
                continue
            med = ref[len(ref) // 2]
            for fld in ("sh", "sho"):
                if fld not in cells:
                    continue
                b, rows = cells[fld]
                new = []
                for pe, subs in rows:
                    s2 = []
                    for av, vs, fs, t in subs:
                        a2, v2, f2 = [], [], []
                        for a, v, f in zip(av, vs, fs):
                            r = (v * self.fac(spl, pe, f) / med) if (v and v > 0) else 0.0
                            if 500 < r < 2000:
                                v = v / 1000
                                self.stat["sh_unit_rescaled"] += 1
                            elif 0 < r and 1 / 2000 < r < 1 / 500:
                                v = v * 1000
                                self.stat["sh_unit_rescaled"] += 1
                            elif not (0.01 < r < 100):
                                self.stat["sh_unit_dropped"] += 1
                                continue
                            a2.append(a)
                            v2.append(v)
                            f2.append(f)
                        if a2:
                            s2.append((a2, v2, f2, t))
                    if s2:
                        new.append((pe, s2))
                    else:
                        self.stat["sh_cells_dropped"] += 1
                cells[fld] = (b, new)

    def _basis(self):
        """sh · sho 기록마다 «분할 기준일» — 같은 칸(같은 태그)에서 값이 같은(±0.5%) 기록 가운데 가장 늦은 filed.

        분할은 보고 숫자를 분할비만큼 바꾼다 — 그러니 같은 기간을 같은 값으로 실은 두 제출은 같은 기준이다. 실제 분할 되맞춤(fac 의 q)은
        그 기준일 뒤의 분할만 곱한다. 효력일 전에 이미 분할을 반영해 낸 제출(SAB Topic 4C — 실측 AOS 2013-05-06 10-Q 는 05-16 의 2:1 을
        반영했다)을 두 번 곱하지 않게 한다. 값은 그대로(빈티지) — 기준만 뒤 제출이 확인해 준다."""
        n = 0
        for tk, cells in self.C.items():
            for fld in ("sh", "sho"):
                if fld not in cells:
                    continue
                b, rows = cells[fld]
                new = []
                for pe, subs in rows:
                    s2 = []
                    for av, vs, fs, t in subs:
                        bs = []
                        for v, f in zip(vs, fs):
                            m = max((f2 for v2, f2 in zip(vs, fs) if v and v2 and abs(math.log(v2 / v)) < 0.005), default=f)
                            bs.append(max(m, f))
                            n += bs[-1] != f
                        s2.append((av, vs, bs, t))
                    new.append((pe, s2))
                cells[fld] = (b, new)
        self.stat["sh_basis_later"] = n

    def series(self, tk, field, d):
        """(버킷, [(기간말, 값, filed, 태그 순번)]) — d 에 가용한 칸만(최신판 파일의 순서)."""
        b, rows = self.C.get(tk, {}).get(field, (None, []))
        out = []
        for pe, subs in rows:
            x = vintage_pick(subs, d, self.pick)
            if x is not None:
                out.append((pe, x[0], x[1], x[2]))
        return b, out

    def firm(self, fk, d):
        """d(YYYY-MM-DD) 에 알 수 있던 재무만 담은 Firm. latest 는 FIRMS 그대로."""
        if self.kind == "latest":
            return self.FIRMS[fk]
        ep = bisect.bisect_right(self.EPOCH.get(fk, []), d)
        mk = (fk, ep)
        F = self.memo_f.get(mk)
        if F is None:
            tg = {}
            for field in ("asset", "debt", "eq"):
                b, ser = self.series(fk, field, d)
                if b:
                    tg[field] = {b: [[pe, v] for pe, v, _f, _t in ser]}
            for k, b in (("ni", "q"), ("ni", "a"), ("cfo", "a")):
                bb, ser = self.series(fk, k + "_" + b, d)
                if bb:
                    tg.setdefault(k, {})[b] = [[pe, v] for pe, v, _f, _t in ser]
            F = self.memo_f[mk] = Firm(tg)
            self.stat["firm_builds"] += 1
        return F

    def sh(self, c, d):
        """shares() 가 읽는 주식수 계열(날짜 내림차순 · 시총 기준). latest 는 FUND[c]['sh'] 그대로."""
        if self.kind == "latest":
            return (self.FUND.get(c) or {}).get("sh")
        if c not in self.FUND:
            return None
        if c not in self.C:
            raise SystemExit("🚨 FUND 키 %s 가 fx · fx_pit 에 없다 — 공급자가 짓지 못한다" % c)
        ep = bisect.bisect_right(self.EPOCH.get(c, []), d)
        mk = (c, ep)
        if mk not in self.memo_s:
            self.memo_s[mk] = self.build_sh(c, d)
            self.stat["sh_builds"] += 1
        return self.memo_s[mk]

    def build_sh(self, c, d, parts=False):
        """parts=True 면 (계열, {기간말: (값, 분할 기준일, 배수, 필드, 태그 순번)}) — F0 (ii) 가 칸의 출처를 본다.
        (sh · sho 의 filed 자리에는 _basis 가 정한 분할 기준일이 들어 있다.)"""
        _b, prim = self.series(c, "sh", d)
        _b2, sho = self.series(c, "sho", d)
        if prim:                                   # load_fund 과 같다: sh 가 시작하기 전만 sho 로 잇는다
            first = min(x[0] for x in prim)
            raw = prim + [x for x in sho if x[0] < first]
        else:
            raw = list(sho)
        fld = {x[0]: "sh" for x in prim}
        raw.sort(key=lambda x: x[0], reverse=True)
        meta = {pe: (f, t) for pe, _v, f, t in raw}
        out, info = [], {}
        if raw:
            ok, _bad, _n = TB._clean_units([(pe, v) for pe, v, _f, _t in raw])
            spl = TB.SPLIT_KIND.get(c) or []
            for pe, v in ok:
                f, t = meta[pe]
                fac = self.fac(spl, pe, f)                # 분사형 몫 — 기간말 뒤 전부 · 실제 분할 — 그 제출보다 뒤의 것만
                out.append((pe, v * fac))
                info[pe] = (v, f, fac, fld.get(pe, "sho"), t)
            known = self.src.get(c) == "fx" or (c in self.SPL)
            seam = (self.FUND.get(c) or {}).get("sh_seam")
            if seam and not known:                     # 최신판이 분할 이력을 몰라 이음매 앞을 자른 종목 — 같은 이음매 앞을 뺀다
                out = [(pe, v) for pe, v in out if pe >= seam]
        if not out:
            res = TB.merge_shares_yf([], c, TB.split_kinds(c, self.SPL.get(c) or [], []))[0]
        else:
            res = TB.merge_shares_yf(out, c, TB.SPLIT_KIND.get(c) or [])[0]
        return (res, info) if parts else res


def d_(s):
    return date(int(s[:4]), int(s[5:7]), int(s[8:10]))


def add_months(dt, k):
    y, m = dt.year + (dt.month - 1 + k) // 12, (dt.month - 1 + k) % 12 + 1
    day = min(dt.day, [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return date(y, m, day)


def tstat(v):
    v = np.asarray(v, float)
    if len(v) < 2 or v.std(ddof=1) == 0:
        return None
    return float(v.mean() / (v.std(ddof=1) / math.sqrt(len(v))))


def ols_alpha_t(y, X):
    y = np.asarray(y, float)
    X = np.column_stack([np.ones(len(y)), np.asarray(X, float)])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    s2 = (e @ e) / (len(y) - X.shape[1])
    cov = s2 * np.linalg.inv(X.T @ X)
    return float(b[0]), float(b[0] / math.sqrt(cov[0, 0]))


def winsor(a, lo=1, hi=99):
    a = np.asarray(a, float)
    ok = ~np.isnan(a)
    if ok.sum() < 5:
        return a
    p1, p99 = np.percentile(a[ok], [lo, hi])
    return np.clip(a, p1, p99)


def spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ra = a.argsort().argsort().astype(float)
    rb = b.argsort().argsort().astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


class Firm:
    """한 회사의 재무 계열(날짜 오름차순). fx/fx_pit 의 태그를 그대로 읽는다."""

    def __init__(self, tg):
        def inst(k):
            v = tg.get(k) or {}
            a = v.get("i") or v.get("q") or []
            return sorted((d_(x[0]), float(x[1])) for x in a if isinstance(x, list) and len(x) == 2 and isinstance(x[1], (int, float)))

        def flow(k, b):
            v = tg.get(k) or {}
            a = v.get(b) or []
            return sorted((d_(x[0]), float(x[1])) for x in a if isinstance(x, list) and len(x) == 2 and isinstance(x[1], (int, float)))
        self.asset = inst("asset")
        self.debt = inst("debt")
        self.eq = inst("eq")
        self.ni_q = flow("ni", "q")
        self.ni_a = flow("ni", "a")
        self.cfo_a = flow("cfo", "a")
        self.fy = sorted({d for d, _ in self.ni_a} | {d for d, _ in self.cfo_a})

    @staticmethod
    def at(series, d, tol=12):
        """d 에서 ±tol 일 안의 관측값(가장 가까운 것)."""
        if not series:
            return None
        ds = [x[0] for x in series]
        i = bisect.bisect_left(ds, d)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(ds):
                gap = abs((ds[j] - d).days)
                if gap <= tol and (best is None or gap < best[0]):
                    best = (gap, series[j][1])
        return best[1] if best else None

    def fy_known(self, t):
        """t 에 «4개월 이상 지난» 가장 최근 회계연도말."""
        cut = add_months(t, -4)
        i = bisect.bisect_right(self.fy, cut)
        return self.fy[i - 1] if i else None

    def prev_fy(self, fy):
        i = bisect.bisect_left(self.fy, fy)
        if i >= 1:
            p = self.fy[i - 1]
            if 300 <= (fy - p).days <= 430:
                return p
        return fy - timedelta(days=365)

    def ia(self, fy):
        a1 = self.at(self.asset, fy)
        a0 = self.at(self.asset, self.prev_fy(fy), tol=20)
        if a1 and a0 and a0 > 0 and a1 > 0:
            return a1 / a0 - 1
        return None

    def droe(self, t):
        """90일 지난 최신 분기의 Roe − 4분기 전 Roe. Roe = 분기 순이익 ÷ 직전 분기말 자본."""
        cut = t - timedelta(days=LAG_Q)
        qs = [x for x in self.ni_q if x[0] <= cut]
        if len(qs) < 5:
            return None
        def roe(k):
            dq, ni = qs[k]
            e = self.at(self.eq, dq - timedelta(days=91), tol=20)
            return ni / e if e and e > 0 else None
        r0 = roe(-1)
        # 4분기 전 — 날짜로 찾는다(분기가 빠진 회사가 있다)
        target = qs[-1][0] - timedelta(days=364)
        k4 = min(range(len(qs)), key=lambda k: abs((qs[k][0] - target).days))
        if abs((qs[k4][0] - target).days) > 20:
            return None
        dq4, ni4 = qs[k4]
        e4 = self.at(self.eq, dq4 - timedelta(days=91), tol=20)
        r4 = ni4 / e4 if e4 and e4 > 0 else None
        return (r0 - r4) if (r0 is not None and r4 is not None) else None


def main() -> int:
    t0 = time.time()
    if not PIT_GICS:                              # 🚨 EGFF ② 수익 울타리 — 점수만 쓰는 경로만 연다
        raise SystemExit("🚨 eg_q5_vintage.py 는 --pit-gics(점수만) 로만 돈다 — 성과 경로는 이 복사본에서 열지 않는다")
    S = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    dates = S["pxd_dates"]
    D = len(dates)
    didx = {d: i for i, d in enumerate(dates)}
    ddates = [d_(x) for x in dates]
    sector_now = {s["t"]: s.get("sector") for s in S["stocks"]}

    PX = {}
    for t in sector_now:
        d = json.load(io.open(os.path.join(DATA, "sd", t + ".json"), encoding="utf-8"))
        PX[t] = np.array([np.nan if v is None else float(v) for v in d["pxd"]])
    # 🚨 2026-09-23 정정 — 편출 가격은 **정리본 data/pit_px.json** 을 쓴다(격리·합병 보정 반영).
    #   처음에는 원시 캐시 _pit_px_cache.json 을 읽었는데, 그 안의 PARA 는 랩이 2026-09-14 에 격리한
    #   «다른 증권» 계열이다(주당 57~113,900달러). 그 한 종목이 시총가중을 지배해 Eg 첫 판을 오염시켰다.
    #   정리본은 157종으로 원시 캐시(122종)보다 넓다 — 인수된 36종이 더 들어 있다.
    pxc = json.load(io.open(os.path.join(DATA, "pit_px.json"), encoding="utf-8"))["px"]
    for t, obj in pxc.items():
        if t not in PX:
            # pit_px.json 의 한 종목 = {i0: 격자 시작 인덱스, p: 가격 배열} (날짜 사전이 아니다)
            a = np.full(D, np.nan)
            i0, arr = int(obj.get("i0") or 0), obj.get("p") or []
            for j, v in enumerate(arr):
                if v is not None and 0 <= i0 + j < D:
                    a[i0 + j] = float(v)
            PX[t] = a
    PU = json.load(io.open(os.path.join(DATA, "pit_universe.json"), encoding="utf-8"))
    splice = PU.get("cik_spliced") or {}
    reassigned = (json.load(io.open(os.path.join(DATA, "pit_reuse.json"), encoding="utf-8")).get("reassigned") or {})
    meta = json.load(io.open(os.path.join(DATA, "index_ledger.json"), encoding="utf-8")).get("meta") or {}
    cikmap = json.load(io.open(os.path.join(DATA, "index_history.json"), encoding="utf-8")).get("cik") or {}
    FUND = TB.load_fund(extra_dirs=[os.path.join(DATA, "fx_pit")])

    # 재무 원장 — fx(오늘) + fx_pit(편출)
    _FXPIT = {fn[:-5] for fn in os.listdir(os.path.join(DATA, "fx_pit")) if fn.endswith(".json")}   # 🚨 EGFF ③ 진단용
    FIRMS = {}
    for sub in ("fx", "fx_pit"):
        dd = os.path.join(DATA, sub)
        for fn in sorted(os.listdir(dd)):
            if not fn.endswith(".json"):
                continue
            tk = fn[:-5]
            if tk in FIRMS:
                continue
            j = json.load(io.open(os.path.join(dd, fn), encoding="utf-8"))
            FIRMS[tk] = Firm(j.get("tags") or {})
    SUP = Supplier(SUPPLIER, FIRMS, FUND)          # 🚨 EGFF ① 공급자

    def key(t):
        if t in PX:
            return t
        n = splice.get(t)
        return n if (n and n in PX) else None

    def fkey(t, k):
        return k if k in FIRMS else (t if t in FIRMS else (splice.get(t) if splice.get(t) in FIRMS else None))

    def sector(t, k):
        s = sector_now.get(k) or sector_now.get(t)
        if s:
            return s
        m = meta.get(t) or meta.get(k)
        return m[1] if (m and len(m) > 1) else None

    def shares(t, k, d, lag=None, td=None):
        for c in (k, t):
            sh = SUP.sh(c, td)                     # 🚨 EGFF ① 공급자(latest = FUND[c]['sh'] 그대로)
            if sh:
                obs = TB.asof_all(sh, d) if lag is None else TB.asof_all(sh, d, lag=lag)
                if obs and obs[0][1]:
                    return obs[0][1]
        return None

    def px_on(k, d):
        """d 이전 가장 가까운 거래일 종가(10거래일 안)."""
        i = bisect.bisect_right(ddates, d) - 1
        p = PX[k]
        for j in range(i, max(-1, i - 10), -1):
            if p[j] == p[j]:
                return p[j]
        return None

    # 월말 거래일
    me = {}
    for i, d in enumerate(dates):
        me[d[:7]] = i
    allm = sorted(me)

    def mshift(ym, k):
        y, m = int(ym[:4]), int(ym[5:7])
        n = y * 12 + (m - 1) + k
        return "%04d-%02d" % (n // 12, n % 12 + 1)

    # ── 회사·월별 예측변수 X 와 현재 I/A ─────────────────────────────────────
    #   회귀용 표본은 가격 계열이 있는 모든 회사(금융·음(−)자본 제외) — 사전등록 §1
    # 이중클래스의 남기지 않는 쪽(GOOG·FOX·NWS)은 회귀에서도 뺀다 — 같은 회사를 두 번 세지 않게
    universe_all = sorted({t for t in FIRMS if key(t)} - {"GOOG", "FOX", "NWS"})
    if PIT_GICS:
        # 같은 회사의 옛 티커가 따로 들어오면 회귀에서 두 번 센다(FI → FISV: 오늘 금융이라 얼린 판에선 빠져 있던 쌍).
        #   오늘 금융인 별칭 쌍만 하나로 줄인다 — 비금융 쌍(ECHO/SATS)은 얼린 판과 같게 둔다.
        _u = set(universe_all)
        universe_all = [t for t in universe_all
                        if not (key(t) != t and key(t) in _u and (sector(t, key(t)) or "").strip() == "Financials")]
    fin = {t for t in universe_all if (sector(t, key(t)) or "").strip() == "Financials"}
    PGI, PGT, pg_stat = {}, {}, {"month": 0, "near": 0, "today": 0}
    if PIT_GICS:
        PG = json.load(io.open(os.path.join(DATA, "pit_gics.json"), encoding="utf-8"))["months"]
        for ym_, v in PG.items():
            fin_t = set(v["fin"])
            all_t = fin_t | set(v["other"])
            cikf = {c: (t in fin_t) for t, c in v["cik"].items() if t in all_t}
            PGI[ym_] = (fin_t, all_t, cikf)
            for t in all_t:                                   # 회사별 연표(가까운 달 찾기용)
                PGT.setdefault("t:" + t, []).append((ym_, t in fin_t))
            for c, f in cikf.items():
                PGT.setdefault("c:" + c, []).append((ym_, f))
        pg_lo, pg_hi = min(PG), max(PG)

    def _mdist(a, b):
        return abs((int(a[:4]) * 12 + int(a[5:7])) - (int(b[:4]) * 12 + int(b[5:7])))

    def fin_at(t, ym, k=None):
        """ym 월말의 금융 여부. 깃발이 없으면 오늘 GICS(얼린 판) 그대로."""
        f = (t in fin) if k is None else ((sector(t, k) or "").strip() == "Financials")
        if not PIT_GICS or ym > pg_hi:
            return f
        kk = k or key(t)
        cks = [c for c in (cikmap.get(t), cikmap.get(kk), cikmap.get((t or "").replace(".", "-"))) if c]
        tks = [x.replace("-", ".") for x in (t, kk) if x]
        row = PGI.get(ym)
        if row:
            fin_t, all_t, cikf = row
            for c in cks:
                if c in cikf:
                    pg_stat["month"] += 1
                    return cikf[c]
            for x in tks:
                if x in all_t:
                    pg_stat["month"] += 1
                    return x in fin_t
        best = None
        for key_ in ["c:" + c for c in cks] + ["t:" + x for x in tks]:
            for ym_, fl in PGT.get(key_, ()):
                d = _mdist(ym_, ym)
                if best is None or d < best[0]:
                    best = (d, fl)
        if best is not None:
            pg_stat["near"] += 1
            return best[1]
        pg_stat["today"] += 1
        return f
    cache = {}

    def state(t, ym):
        """(logq, cop, droe, ia, fy, me_t) — ym 월말에 알 수 있던 값. 없으면 None."""
        ck = (t, ym)
        if ck in cache:
            return cache[ck]
        out = None
        k = key(t)
        fk = fkey(t, k)
        if k and fk and ym in me:
            F = SUP.firm(fk, dates[me[ym]])       # 🚨 EGFF ① 공급자(latest = FIRMS[fk] 그대로)
            td = ddates[me[ym]]
            fy = F.fy_known(td)
            if fy:
                at = F.at(F.asset, fy)
                eq = F.at(F.eq, fy)
                cfo = F.at(F.cfo_a, fy, tol=5)
                ia = F.ia(fy)
                p_fy = px_on(k, fy)
                sh_fy = shares(t, k, fy.isoformat(), lag=0, td=dates[me[ym]])
                p_t = PX[k][me[ym]]
                sh_t = shares(t, k, dates[me[ym]], td=dates[me[ym]])
                if (at and at > 0 and eq is not None and eq > 0 and cfo is not None and ia is not None
                        and p_fy and sh_fy and p_t == p_t and sh_t):
                    debt = F.at(F.debt, fy) or 0.0
                    q = (p_fy * sh_fy + debt) / at
                    dr = F.droe(td)
                    if q > 0:
                        out = (math.log(q), cfo / at, dr if dr is not None else 0.0, ia, fy, p_t * sh_t)
        cache[ck] = out
        return out

    # ── ① 월별 회귀 ─────────────────────────────────────────────────────────
    reg_months = [m for m in allm if REG0 <= m <= F1_]
    B = {}
    nreg = {}
    REGN = {}                                     # 🚨 EGFF ③ 진단 — 달마다 회귀 표본 이름(계산에는 안 쓴다)
    for ym in reg_months:
        y, X, w = [], [], []
        REGN[ym] = []
        for t in universe_all:
            if fin_at(t, ym):
                continue
            s1 = state(t, ym)
            s0 = state(t, mshift(ym, -12))
            if not s1 or not s0 or s1[4] == s0[4]:
                continue                    # 새 회계연도가 안 들어왔으면 실현된 변화가 없다
            y.append(s1[3] - s0[3])
            X.append([s0[0], s0[1], s0[2]])
            w.append(s0[5])
            REGN[ym].append(t)
        if len(y) < 60:
            continue
        y = winsor(y)
        X = np.column_stack([winsor(np.asarray(X)[:, j]) for j in range(3)])
        W = np.asarray(w, float)
        Xc = np.column_stack([np.ones(len(y)), X])
        sw = np.sqrt(W / W.mean())
        b, *_ = np.linalg.lstsq(Xc * sw[:, None], y * sw, rcond=None)
        B[ym] = b
        nreg[ym] = len(y)

    def bbar(ym):
        ks = [m for m in B if mshift(ym, -ROLL + 1) <= m <= ym]
        if len(ks) < ROLL_MIN:
            return None
        return np.mean([B[m] for m in ks], axis=0)

    # ── ③④ 형성·보유 ─────────────────────────────────────────────────────────
    mem, _c = IM.load(PRE_FROM or F0)
    months = [m for m in sorted(mem) if (PRE_FROM <= m <= PRE_TO if PRE_FROM else F0 <= m <= F1_)]
    rows, prev_w, prev_rn, f4_rho, drops = [], {}, {}, [], {"no_state": 0, "fin": 0, "dual": 0, "no_px": 0, "reuse": 0}
    SCORES = {}               # 형성월 → {멤버 티커: E_t} — PREREG-2026-09-23-IDXEG 가 읽는다
    for m in months:
        bb = bbar(m)
        if bb is None:
            raise SystemExit("🚨 %s: 평균 기울기를 낼 회귀가 %d개월뿐이다(최소 %d)" % (m, len([x for x in B if x <= m]), ROLL_MIN))
        e1, e2 = me[m], me[mshift(m, 1)]
        # 예측변수 윈저 기준 = 그 달 회귀 표본 전체의 분포(원문 «most recent winsorized predictors»)
        Xall = [state(t, m) for t in universe_all if not fin_at(t, m)]
        Xall = np.array([[s[0], s[1], s[2]] for s in Xall if s])
        lo = np.percentile(Xall, 1, axis=0)
        hi = np.percentile(Xall, 99, axis=0)
        by_cik = {}
        for t in mem[m]:
            c = cikmap.get(t) or cikmap.get(t.replace("-", "."))
            by_cik.setdefault(c or ("_" + t), []).append(t)
        keep = set()
        for c, ts in by_cik.items():
            if len(ts) == 1 or c.startswith("_"):
                keep.update(ts)
                continue
            k_ = [t for t in ts if t in KEEP_DUAL]
            keep.add(k_[0] if k_ else sorted(ts)[0])
            drops["dual"] += len(ts) - 1
        cand = []
        for t in sorted(keep):
            k = key(t)
            if k is None or not (PX[k][e1] == PX[k][e1]):
                drops["no_px"] += 1
                continue
            if fin_at(t, m, k):
                drops["fin"] += 1
                continue
            if t in reassigned and m >= reassigned[t].get("last", "9999"):
                drops["reuse"] += 1
                continue
            s = state(t, m)
            if not s:
                drops["no_state"] += 1
                continue
            x = np.clip(np.array([s[0], s[1], s[2]]), lo, hi)
            eg = float(bb[0] + x @ bb[1:])
            if PIT_GICS:                              # 🚨 EGFF ② 수익 울타리 — 점수에 쓰지 않는 수익 · F4 는 계산하지 않는다
                cand.append({"t": t, "eg": eg, "mc": s[5]})
                continue
            p = PX[k]
            seg2 = p[e1 + 1:e2 + 1]
            ok = np.where(seg2 == seg2)[0]
            rn = (seg2[ok[-1]] / p[e1] - 1) if len(ok) else 0.0
            # F4 — 12개월 뒤에 알려진 I/A − 지금 I/A (실현 d1 I/A)
            s12 = state(t, mshift(m, 12)) if mshift(m, 12) <= allm[-1] else None
            real = (s12[3] - s[3]) if (s12 and s12[4] != s[4]) else None
            cand.append({"t": t, "eg": eg, "mc": s[5], "rn": rn, "real": real})
        SCORES[m] = {c["t"]: round(c["eg"], 6) for c in cand}   # --scores 가 내보낸다(계산에는 안 쓴다)
        if len(cand) < 60:
            raise SystemExit("🚨 %s 자격 종목 %d — 너무 얇다" % (m, len(cand)))
        if PIT_GICS:                                  # 🚨 EGFF ② 수익 울타리 — 다리 · 회전 · 순위상관은 짓지 않는다
            rows.append({"form": m, "n_cand": len(cand)})
            continue
        egs = np.array([c["eg"] for c in cand])
        q30, q70 = np.percentile(egs, [30, 70])
        legs = {"H": [c for c in cand if c["eg"] >= q70], "L": [c for c in cand if c["eg"] <= q30]}
        res = {}
        for nm, g in legs.items():
            ws = sum(c["mc"] for c in g)
            res[nm] = {"ret": sum(c["mc"] * c["rn"] for c in g) / ws, "w": {c["t"]: c["mc"] / ws for c in g}, "n": len(g)}
        wu = sum(c["mc"] for c in cand)
        univ = sum(c["mc"] * c["rn"] for c in cand) / wu
        turns = {}
        for nm in ("H", "L"):
            pw = prev_w.get(nm) or {}
            if pw:
                drift = {t: w * (1 + prev_rn.get(t, 0.0)) for t, w in pw.items()}
                s_ = sum(drift.values()) or 1.0
                drift = {t: w / s_ for t, w in drift.items()}
                nw = res[nm]["w"]
                turns[nm] = 0.5 * sum(abs(nw.get(t, 0.0) - drift.get(t, 0.0)) for t in set(drift) | set(nw))
            else:
                turns[nm] = None
            prev_w[nm] = res[nm]["w"]
        prev_rn = {c["t"]: c["rn"] for c in cand}
        rr = [(c["eg"], c["real"]) for c in cand if c["real"] is not None]
        if len(rr) >= 30:
            f4_rho.append(spearman([a for a, b in rr], [b for a, b in rr]))
        rows.append({"m": mshift(m, 1), "form": m, "spread": (res["H"]["ret"] - res["L"]["ret"]) * 100,
                     "lo": (res["H"]["ret"] - univ) * 100, "univ": univ * 100,
                     "n": {"H": res["H"]["n"], "L": res["L"]["n"], "all": len(cand)}, "turn": turns,
                     "slopes": [round(float(v), 5) for v in bb]})
    dt = time.time() - t0
    if PIT_GICS:
        # 점수만 내보내고 끝낸다 — 이 판의 성과(Eg 3분위 스프레드 등)는 **계산은 되지만 적지도 찍지도 않는다**.
        #   EGBEST 가 이 점수를 기저로 쓰기 전에 성과를 보면 안 되기 때문이다(사전등록 PREREG-2026-09-24-EGBEST).
        # 🚨 EGFF ① 공급자별 산출 — latest 는 얼린 판과 같은 문서(재현 단언) · v · ff 는 같은 스키마(열쇠 같음 · 설명과 등록만 다르다)
        sfx = {"latest": "_latest", "v": "_v", "ff": "_ff", "vs": "_vs"}[SUPPLIER]
        sp_ = OUT_SCORES or os.path.join(DATA, ("_eg_q5_scores_pitgics_pre%s.json" if PRE_FROM else "_eg_q5_scores_pitgics%s.json") % sfx)
        doc_ = {"note": "eg_q5.py --pit-gics 형성월별 Eg 예측치 E_t. 금융 판정만 시점정확(월말 위키 표의 GICS · data/pit_gics.json) — "
                        "나머지는 얼린 판(_eg_q5_scores.json)과 같은 식. 점수만 — 성과는 내보내지 않는다.",
                "prereg": "build/PREREG-2026-09-24-EGBEST.md", "pit_gics": "data/pit_gics.json", "pit_gics_range": [pg_lo, pg_hi],
                "fin_lookups": pg_stat,
                "months": SCORES}
        if SUPPLIER != "latest":
            doc_["note"] = ("eg_q5_vintage.py --pit-gics --supplier %s 형성월별 Eg 예측치 E_t — 재무 입력만 %s(원장 data/_fxv · "
                            "가용일 = max(기간말 + 90일, filed 다음 NYSE 거래일)). 그 밖은 _eg_q5_scores_pitgics.json 과 같은 식 · 같은 스키마. "
                            "점수만 — 성과는 내보내지 않는다." % (SUPPLIER, {"v": "P-V 빈티지(그날까지 가용한 제출 중 filed 가 가장 늦은 값)",
                                                                   "ff": "P-FF 최초 제출값",
                                                                   "vs": "P-VS 엄격 태그 쌍둥이(P-V 와 같되 최신판 태그만 · 보고만)"}[SUPPLIER]))
            doc_["prereg"] = EGFF_PREREG
        io.open(sp_, "w", encoding="utf-8", newline="\n").write(json.dumps(doc_, ensure_ascii=False, separators=(",", ":")) + "\n")
        if DIAG:
            import hashlib
            lastpx = {}
            for t_ in universe_all:
                p_ = PX[key(t_)]
                okx = np.where(p_ == p_)[0]
                lastpx[t_] = dates[okx[-1]] if len(okx) else None
            io.open(DIAG, "w", encoding="utf-8", newline="\n").write(json.dumps({
                "supplier": SUPPLIER, "scores_sha256": hashlib.sha256(open(sp_, "rb").read()).hexdigest(),
                "ledger_index_sha256": getattr(SUP, "index_sha", None), "supplier_stat": SUP.stat,
                "left_before": LEFT_BEFORE,
                "reg": {ym: {"n": len(v), "n_left": sum(1 for t_ in v if (lastpx.get(t_) or "") < LEFT_BEFORE),
                             "n_fxpit": sum(1 for t_ in v if t_ in _FXPIT)} for ym, v in sorted(REGN.items())},
                "n_regressions": len(B),
                "formations": {r["form"]: r["n_cand"] for r in rows}}, ensure_ascii=False, indent=1) + "\n")
        print("→ %s (%d개월 · 월 평균 %.1f종 · 금융 판정 그달 표 %d · 가까운 달 %d · 오늘 %d · %.0f초)" % (
            sp_, len(SCORES), np.mean([len(v) for v in SCORES.values()]), pg_stat["month"], pg_stat["near"], pg_stat["today"], dt))
        return 0

    sp = np.array([r["spread"] for r in rows])
    lo_ = np.array([r["lo"] for r in rows])
    post = np.array([r["spread"] for r in rows if r["m"] >= POST])
    pre = np.array([r["spread"] for r in rows if r["m"] < POST])
    cost = np.array([0.0] + [COST * (r["turn"]["H"] + r["turn"]["L"]) * 100 for r in rows[1:]])
    net = sp - cost

    CH = json.load(io.open(os.path.join(DATA, "strategy_charts.json"), encoding="utf-8"))
    IX = {s["sid"]: s for s in json.load(io.open(os.path.join(DATA, "strategy_index.json"), encoding="utf-8"))["items"]}
    spx = CH["idx_monthly"]["S&P 500"]
    uu = [(r["univ"], spx[r["m"]]) for r in rows if r["m"] in spx]
    corr_spx = float(np.corrcoef([a for a, b in uu], [b for a, b in uu])[0, 1])
    mset = [r["m"] for r in rows]
    pool = []
    for sid, c in CH["charts"].items():
        s = IX.get(sid)
        mo = c.get("monthly") or []
        if not s or s.get("src") != "종목 전략" or s.get("role") != "수익엔진" or len(mo) < 100:
            continue
        ex = {x["m"]: x["r"] - x["b"] for x in mo if x.get("r") is not None and x.get("b") is not None}
        if all(m_ in ex for m_ in mset):
            pool.append((sid, s.get("name"), np.array([ex[m_] for m_ in mset])))
    cors = sorted(((abs(np.corrcoef(sp, v)[0, 1]), float(np.corrcoef(sp, v)[0, 1]), sid, nm, v) for sid, nm, v in pool),
                  key=lambda x: -x[0])
    # 상관 상위 5 — 서로 사실상 같은 계열(상관 0.999 초과, 예: 밴드판 = 원판)은 하나만 남긴다.
    #   같은 계열 둘을 넣으면 회귀 행렬이 특이해진다(첫 실행에서 실제로 죽었다).
    top5 = []
    for x in cors:
        if all(abs(np.corrcoef(x[4], y[4])[0, 1]) < 0.999 for y in top5):
            top5.append(x)
        if len(top5) == 5:
            break
    a5, t5 = ols_alpha_t(sp, np.column_stack([x[4] for x in top5]))

    f1m, f1t = float(sp.mean()), tstat(sp)
    rho = float(np.mean(f4_rho)) if f4_rho else None
    R = {
        "f1": {"hit": not (f1m > 0), "mean_pm": f1m},
        "f2": {"hit": not (f1t is not None and f1t >= F_T), "t": f1t, "문턱": F_T},
        "f3": {"hit": not (post.mean() > 0), "post_mean_pm": float(post.mean()), "post_t": tstat(post), "n_post": len(post),
               "pre_mean_pm": float(pre.mean()), "pre_t": tstat(pre), "n_pre": len(pre)},
        "f4": {"hit": not (rho is not None and rho > 0), "rank_corr_mean": rho, "n_months": len(f4_rho),
               "rank_corr_t": tstat(f4_rho)},
        "f5": {"hit": not (t5 >= F_T), "alpha_pm": a5, "t": t5, "n_pool": len(pool),
               "top5": [{"sid": x[2], "name": x[3], "corr": x[1]} for x in top5]},
        "f6": {"hit": not (net.mean() > 0), "net_mean_pm": float(net.mean()), "net_t": tstat(net), "cost_mean_pm": float(cost.mean())},
    }
    verdict = ("기각" if any(R[k]["hit"] for k in ("f1", "f2", "f3", "f4", "f6")) else
               "보류" if R["f5"]["hit"] else "게시 후보")
    slopes = np.array([r["slopes"] for r in rows])
    doc = {"note": "기대투자성장(Eg) PIT 검정. 사전등록 PREREG-2026-09-23-EG(계산 전 커밋 cee33124) 값 그대로.",
           "prereg": "build/PREREG-2026-09-23-EG.md", "commit": "cee33124",
           "window": "보유 %s ~ %s (%d개월)" % (rows[0]["m"], rows[-1]["m"], len(rows)),
           "summary": {"spread_mean_pm": f1m, "spread_t": f1t, "longonly_pm": float(lo_.mean()), "longonly_t": tstat(lo_),
                       "avg_turnover": {nm: float(np.mean([r["turn"][nm] for r in rows[1:]])) for nm in ("H", "L")},
                       "avg_n": {k: float(np.mean([r["n"][k] for r in rows])) for k in ("H", "L", "all")},
                       "slopes_mean": {"const": float(slopes[:, 0].mean()), "logq": float(slopes[:, 1].mean()),
                                       "cop": float(slopes[:, 2].mean()), "droe": float(slopes[:, 3].mean())},
                       "n_regressions": len(B), "reg_n_median": float(np.median(list(nreg.values())))},
           "sanity": {"univ_vs_spx_corr": corr_spx}, "drops": drops, **R, "verdict": verdict,
           "monthly": [{"m": r["m"], "spread": round(r["spread"], 4), "lo": round(r["lo"], 4)} for r in rows]}
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    # 🚨 --scores — 월별 예측치 E_t 를 따로 내보낸다(PREREG-2026-09-23-IDXEG 의 신호). 판정 산출물(OUT)은
    #   이 깃발과 무관하게 한 바이트도 달라지지 않아야 한다 — 같은 계산의 부산물을 적을 뿐이다.
    if "--scores" in sys.argv:
        sp_ = os.path.join(DATA, "_eg_q5_scores.json")
        io.open(sp_, "w", encoding="utf-8", newline="\n").write(json.dumps(
            {"note": "eg_q5.py 형성월별 Eg 예측치 E_t(금융 제외 · 그때의 멤버 중 재무 상태가 있는 종목). 얼린 측정의 부산물.",
             "prereg": "build/PREREG-2026-09-23-EG.md", "months": SCORES},
            ensure_ascii=False, separators=(",", ":")) + "\n")
        print("→ %s (%d개월)" % (sp_, len(SCORES)))

    print("보유 %s ~ %s · %d개월 · 회귀 %d개월(표본 중앙 %d) · %.0f초"
          % (rows[0]["m"], rows[-1]["m"], len(rows), len(B), np.median(list(nreg.values())), dt))
    print("평균 기울기: 상수 %.4f · log q %.4f · Cop %.4f · dRoe %.4f  (원문 1년: log q 음 · Cop 양 · dRoe 양)"
          % tuple(slopes.mean(axis=0)))
    print("위생: 모집단 시총가중 vs S&P 500 상관 %.3f · 제외 %s" % (corr_spx, drops))
    print("평균 종목 수 %s · 편도 회전 %s" % (doc["summary"]["avg_n"], {k: round(v, 3) for k, v in doc["summary"]["avg_turnover"].items()}))
    print("\n  고Eg − 저Eg  월 %+.3f%% · t %.2f" % (f1m, f1t))
    print("  롱온리 고Eg − 모집단  월 %+.3f%% · t %.2f   (서술)" % (lo_.mean(), tstat(lo_)))
    print("\n🚨 실패 조건")
    print("  F1 평균 %+.3f%% → %s" % (f1m, "걸림 ✗" if R["f1"]["hit"] else "통과"))
    print("  F2 t %.2f → %s" % (f1t, "구별 불가 ✗" if R["f2"]["hit"] else "통과"))
    print("  F3 발표 후 %d개월 %+.3f%% · t %.2f (앞 %d개월 %+.3f%% · t %.2f) → %s"
          % (len(post), post.mean(), tstat(post), len(pre), pre.mean(), tstat(pre), "걸림 ✗" if R["f3"]["hit"] else "통과"))
    print("  F4 예측 순위상관 평균 %.3f (t %.2f · %d개월) → %s"
          % (rho, tstat(f4_rho), len(f4_rho), "걸림 ✗ 예측기가 안 선다" if R["f4"]["hit"] else "통과"))
    print("  F5 증분 알파 %+.3f%% · t %.2f → %s" % (a5, t5, "보류 ✗" if R["f5"]["hit"] else "통과"))
    for x in top5:
        print("       %+.3f  %s  %s" % (x[1], x[2], x[3]))
    print("  F6 편도 10bp 뒤 %+.3f%% · t %.2f (비용 월 %.3f%%) → %s"
          % (net.mean(), tstat(net), cost.mean(), "걸림 ✗" if R["f6"]["hit"] else "통과"))
    print("\n판정: **%s**" % verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
