# -*- coding: utf-8 -*-
"""build/v_ins.py — 배치 V04 INS 입력: 기회주의 내부자 순매수(OB) · 순매도(OS) 발행사 표지(최근 6개월 · RBATCH R1 등록 규칙 그대로).

설계 원본(구속): vbatch_research.json final.slate V04(base_signal · basket · density_F0) · data_plan.insider · D13.
  거래 규칙 = R1 1차(PREREG-2026-09-26-RBATCH.md:279 — Form 4 · 4/A NONDERIV · 매도 TRANS_CODE S · A/D = D · 10b5-1 로 빼지 않음 · 각주가 강제 매도(sell-to-cover)인 행
    제외 · 내부자 = Officer · Director · TenPercentOwner · 공동 제출은 제출당 한 번) · 매수 거울 = TRANS_CODE P · A/D = A · 같은 분류.
  분류 = CMP(1월 첫 거래일 D_Y · 직전 3개 달력연도 각각 ≥ 1건 · 세 해 모두 같은 달이 있으면 루틴 R · 없으면 기회주의 O · 한 해라도 비면 U(분류 불가 · 어느 쪽에도 넣지 않음) ·
    자료 첫해 뒤 3년 미만 N(자료 부족)) — data/_ins_pit/routine.json(PIT · sha 48cf3abb… · RBATCH.md:401).
  🔎 복사 방식: r_r1_flags 는 import 하지 않는다(D22). R1 등록 빌더가 규칙대로 센 등록 산출(data/_ins_pit/cikmonth.json · 그룹 × 가용월 · 칸 O = 기회주의 매도 행 ·
    bO = 기회주의 매수 행 · os_na = N 을 품고 O 가 없는 달 «모름» · months_ok)을 읽어 V 의 6개월 창 · 순(net) 규칙만 이 파일에서 더한다 — 거래 · 분류 규칙은 R1 한 벌 그대로
    (R1 과 같은 가설을 한 번만 센다). 허용 목록 감사(v_audit)가 r_r1_flags 의 OS 개수 · 해시와 짝맞춤을 한다.
  V 규칙(명세 V04 · 선언): 결정 달 m 의 창 = 가용월 m−5..m(6개월).
    순 = Σ O − Σ bO(행 수 · 금액 칸은 매도만 있어 쓰지 않는다). OS ⇔ 순 > 0 · OB ⇔ 순 < 0(Σ bO > Σ O).
    «모름»: 창 안에 months_ok 밖 달이 있거나(2011-02 앞 · 2026-07 뒤) os_na(N 을 품고 O 없음) 달이 있으면 매도가 과소 셈일 수 있다 → 순 ≤ 0 이면 «모름»(OB 아님) ·
      순 > 0 이면 OS(아는 매도만으로 이미 순매도). FPI(Section 16 비적용 · issuer_map fpi_q = 1)는 «모름». 그룹이 없으면 «모름».
  가용 = 제출 다음 NYSE 거래일(R1 · 가용월 = 그 날의 달) — 결정 달 m 에는 가용월 ≤ m 만. 전방 자료 경로 = data/_ins_daily(등록문 명시).

🚨 수익 · 신호-수익 통계를 계산하지 않는다. 표지 · 개수만.

  python build/v_ins.py --selftest
"""
from __future__ import annotations

import json
import os
import sys
import traceback

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import v_data as VD          # noqa: E402

LOOKBACK = 6
CIKMONTH = "data/_ins_pit/cikmonth.json"
ROUTINE = "data/_ins_pit/routine.json"
ROUTINE_SHA_PREFIX = "48cf3abb"


class Insider:
    """그룹 × 가용월 표(R1 등록 산출). doc = cikmonth.json 꼴(합성 시험은 같은 꼴)."""

    def __init__(self, doc=None):
        doc = doc if doc is not None else VD.read_json(VD.lab_path(CIKMONTH))
        if doc.get("joint_rule") not in (None, "O>R>N>U"):
            raise SystemExit("🚨 cikmonth 공동 규칙이 R1 등록(O>R>N>U)과 다르다")
        if doc.get("variants") and not (doc["variants"].get("primary") or {}).get("stc_excl", True):
            raise SystemExit("🚨 cikmonth 1차 판이 강제 매도를 빼지 않는다 — R1 규칙과 다르다")
        self.G = doc.get("groups") or {}
        self.ok = set(doc.get("months_ok") or [])

    def window(self, gid, m, look=LOOKBACK):
        """(Σ O, Σ bO, 모름 여부, 창 달 수) — 가용월 m−look+1..m."""
        cells = self.G.get(gid) or {}
        so = sb = 0
        unk = False
        for k in range(look):
            ym = VD.mshift(m, -k)
            if ym not in self.ok:
                unk = True
                continue
            c = cells.get(ym) or {}
            o = int(c.get("O") or 0)
            so += o
            sb += int(c.get("bO") or 0)
            if c.get("os_na") and o == 0:
                unk = True
        return so, sb, unk, look

    def flag(self, gid, m, fpi=None):
        """'OS' · 'OB' · 'none' · 'unk'(모름) — 머리말 규칙."""
        if not gid or fpi == 1:
            return "unk"
        so, sb, unk, _ = self.window(gid, m)
        net = so - sb
        if net > 0:
            return "OS"
        if unk:
            return "unk"
        return "OB" if net < 0 else "none"

    def flags(self, U, m):
        """우주 U(v_pit.Universe)의 그달 명단 → {명단 티커: 표지}."""
        return {r["t"]: self.flag(r["gid"], m, r.get("fpi")) for r in U.members(m)}

    def density(self, U, m):
        f = self.flags(U, m)
        out = {}
        for v in f.values():
            out[v] = out.get(v, 0) + 1
        return out

    def poison_after(self, m, rng):
        """가용월 > m 칸을 난수로 바꾼 표(선견 점검용)."""
        G2 = {}
        for g, cells in self.G.items():
            G2[g] = {ym: (c if ym <= m else {"O": int(rng.integers(0, 9)), "bO": int(rng.integers(0, 9))}) for ym, c in cells.items()}
        doc = {"groups": G2, "months_ok": sorted(self.ok)}
        return Insider(doc)


def routine_pin_ok():
    p = VD.lab_path(ROUTINE)
    return os.path.exists(p) and VD.sha256_file(p).startswith(ROUTINE_SHA_PREFIX)


def _st_rule():
    ok = ["2016-%02d" % k for k in range(1, 13)]
    doc = {"joint_rule": "O>R>N>U", "variants": {"primary": {"stc_excl": True}}, "months_ok": ok,
           "groups": {"gA": {"2016-03": {"O": 2}, "2016-05": {"bO": 1}},                 # 순 +1 → OS
                      "gB": {"2016-04": {"bO": 2}, "2016-06": {"O": 1}},                 # 순 −1 → OB
                      "gC": {"2016-06": {"os_na": 1}, "2016-05": {"bO": 3}},             # 모름 달 + 순 < 0 → 모름
                      "gD": {"2016-06": {"os_na": 1, "O": 1}},                            # 모름 표지지만 O 가 있다 → OS
                      "gE": {"2015-12": {"bO": 5}},                                       # 창 밖 매수 — 6월 창에 없다
                      "gF": {}}}
    I = Insider(doc)
    m = "2016-06"
    assert I.flag("gA", m) == "OS" and I.flag("gB", m) == "OB" and I.flag("gC", m) == "unk" and I.flag("gD", m) == "OS"
    assert I.flag("gE", m) == "none" and I.flag("gF", m) == "none" and I.flag(None, m) == "unk" and I.flag("gB", m, fpi=1) == "unk"
    assert I.flag("gB", "2016-03") == "unk"                                            # 창이 months_ok 앞(2015-10..12)에 걸친다 · 순 ≤ 0
    try:
        Insider(dict(doc, joint_rule="R>O"))
        raise AssertionError("다른 공동 규칙이 통과했다")
    except SystemExit:
        pass
    import numpy as np
    I2 = I.poison_after(m, np.random.default_rng(3))
    assert all(I2.flag(g, m) == I.flag(g, m) for g in doc["groups"])
    return "6개월 창 · 순 = ΣO − ΣbO · OS/OB · 모름(months_ok 밖 · os_na · FPI · 그룹 없음) · R1 규칙 대조 · 가용월 뒤 독 불변"


def selftest():
    res, ok = [], True
    for fn in (_st_rule,):
        try:
            res.append(("통과", fn.__name__, fn()))
        except Exception:
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-1500:]))
    for st, nm, msg in res:
        print("  %s %-10s %s" % ("✓" if st == "통과" else "✗", nm, msg))
    print("v_ins selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
