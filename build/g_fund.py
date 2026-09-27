# -*- coding: utf-8 -*-
"""build/g_fund.py — 거장 슬리브 측정(GURUFUND) 계산 엔진 · 러너(build/g_fund_run.py)가 핀 판 임시 뿌리 안에서 자식 과정으로 부른다.

사전등록: build/PREREG-<등록 날짜>-GURUFUND.md 하나(글과 코드가 어긋나면 얼린 코드가 돌고 결과 문서에 «등록 오류» 로 적는다).

무엇을 재나(측정만 · 확증 가족 없음 m = 0)
  팔(arm)   VG  = 집중 밸류 16 + 성장 11 (사용자 선택 «c» · 2026-09-27) + 이력 전용 사이언(밸류 축 · HISTORY_ONLY 규칙)
            C   = 퀀트를 뺀 여섯 축 43 + 사이언(이력)            — 옛 겹침 명단(2026-09-27 전 백테스트 겹침 정의 = guru_overlap_backtest.counts_by_quarter @ 760df724b)
            C−BW = C − 브리지워터                              — 넓게 드는 한 곳만 뺀 판
  신호      S1 합의 점수 틸트 — GURUCMP 규칙 그대로(S = ½·[z(수준) + z(변화)] · 섹터 안 z · 중립 맞춤 · idxrev.solve «prop» · TE 2% · 섹터 ±3%p ·
               편도 10bp(= 왕복 20bp) · S&P 500 시총가중 벤치) — 슬리브 = 틸트한 S&P 500 포트폴리오
            S2 K≥2 겹침 바스켓 — 체결월(분기말 + 2개월 월말)의 실제 S&P 500 ∪ NASDAQ 100 멤버 ∩ 13F 매핑 안에서 그 팔의 두 곳 이상이 든 종목 ·
               동일가중 · 분기 사이 표류 · 편도 10bp · 최소 5종목 · K = 2 고정
  펀드 틀   F = 0.9 × SPY TR + 0.1 × 슬리브(매월 말 되돌림 · qbatch_core.fund_from_path · 되돌림 비용 2 × 10bp × 벗어난 몫) 대 SPY TR
  대조      B0 = 패널 시총가중 S&P 500(틸트 없음 · 비용 0) 슬리브 · U = 13F 매핑 유니버스 동일가중(K 없음 · S2 와 같은 생존 편향) 슬리브
  참고 줄   EG30 V0(얼린 data/_qbatch.json V0 · 10년) — 입력 · 대조 · 구성 요소가 아니다(상관과 얼린 지표만 옮긴다)
  창        보유월 2014-09 ~ 2026-08(144개월 · 최근 20년 한도 안 · 자료가 허락하는 최대) · 공개는 2016-09 ~ 2026-08(10년 · MAX_YEARS 10)
  자료      data/guru_history.json 은 등록 커밋 판(옛 CUSIP 지도 CUSIP_HIST 로 다시 푼 이력 · 2026-09-27 수선) — 러너가 핀 뿌리에 덧씌운다

🚨 랩 규율: 이 모듈의 수익 경로(main_child)는 등록 커밋이 origin 에 오른 뒤 러너의 한 번 굽기와 눈가린 연기에서만 돈다.
   f0_child · f0b_child 는 개수 · 날짜 · 커버리지 · 동일성(참/거짓)만 돌려준다. F0-b 는 얼린 GURUCMP 입력 · 산출을 재현하는지 본다
   (이미 공개된 값의 재현 — 새 팔 · 새 자료의 수익이 아니다 · 값은 돌려주지 않고 참/거짓 · 개수만).
🚨 머리에서는 표준 라이브러리만 부른다 — F0-b 는 3bbe5ca1d 판 뿌리(pit_alias · qbatch_core · eg30plus 가 아직 없던 판)에서 이 파일을 부른다.
"""
from __future__ import annotations

import collections
import copy
import io
import json
import math
import os
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

# ══════════════════════════════════════════════════════════════════════════
#  등록 상수(러너 REGISTERED 가 같은 값을 들고 판 점검에서 대조한다)
# ══════════════════════════════════════════════════════════════════════════
VALUE = (1067983, 1061768, 1709323, 1112520, 1358706, 1056831, 1720792, 1096343,
         1549575, 860643, 1036325, 813917, 807985, 1697868, 915191, 1569205)            # 집중 밸류 16(refresh_13f.AXES · 커밋 760df724b)
GROWTH = (1167483, 1061165, 1103804, 1135730, 1697748, 1747057, 1541617, 1798849, 934639, 1602189, 1088875)   # 성장 11
ACTIVIST = (2026053, 1040273, 1791786, 1345471, 1418814, 921669, 1517137, 1998597, 1489933)                   # 행동주의 9
MACRO = (1350694, 1029160, 1536411)                                                                           # 매크로 3
CREDIT = (1656456, 949509, 1035674)                                                                           # 부실채권 · 크레딧 3
ENDOW = (1166559,)                                                                                            # 재단 1
QUANT = (1037389, 1167557, 1510387)                                                                           # 퀀트 · 분산 3(겹침 제외 · NO_OVERLAP)
HIST_ONLY_VALUE = (1649339,)          # 사이언 — 2026-09-27 명단에서 뺐다 · 이력 전용(HISTORY_ONLY · axis value · last 2025-09-30)
BRIDGEWATER = 1350694
MAVERICK, BAILLIE = 934639, 1088875
ARM_NAMES = ("VG", "C", "C-BW")
PRIMARY = "VG"
SIGNALS = ("S1", "S2")
CONTROLS = ("B0", "U")

K = 2                                  # 겹침 문턱(고정)
MIN_HOLD = 5                           # S2 최소 종목(guru_overlap_backtest.MIN_HOLD 와 같다)
COST = 0.0010                          # 편도 10bp — S1 은 idxtilt.COST_RT(왕복 20bp) × 0.5 × Σ|Δw| 와 같은 뜻
SLEEVE = 0.10
TE = 0.02                              # idxtilt.TE_JUDGE
CAP_MODE = "prop"                      # GURUCMP 판정 칸(비중비례 |Δw| ≤ w_bench)
WIN = ("2014-09", "2026-08")           # 측정 창(보유월 144 · 20년 한도 안)
PUB = ("2016-09", "2026-08")           # 공개 창(10년 · MAX_YEARS 10) = F0-a 실패 때의 대체 창
SIG = ("2014-08", "2026-07")           # S1 신호월(보유월 − 1)
AS_OF = "2026-09"                      # 이력 월 격자에서 이 달부터 뺀다(미완결 달 · GURUCMP 실행 달과 같다)
LAG_Q = 2                              # 체결월 = 13F 분기말 + 2개월(guru17_backtest.LAG_MONTHS)
N_WIN = 144
F0A_CORR, F0A_GAP = 0.98, 0.30         # 패널 관문(GURUCMP · IDXEG 와 같다)
F0E_MIN_MGR, F0E_MIN_NAMES, F0E_FRAC = 5, 10, 0.90
NW_LAG = 3
ROLL_N = 36
FF_FACTORS = ("mkt_rf", "smb", "hml", "mom")
TOL_F0B = 1e-9
# F0-b(얼린 GURUCMP · 커밋 3bbe5ca1d)의 설정 — guru_cmp.py 그대로
F0B_TODAY = (2026, 9, 24)              # 3bbe5ca1d 커밋 날(guru_cmp.main 이 dt.date.today() 로 이력 끝 달을 뺀다)
F0B_SIG = ("2016-08", "2026-07")
F0B_END = "2026-08"
F0B_JUDGE0 = "2018-07"
# F0-f 옛 CUSIP 관문(수선 확인 · 구성 사실) — 체결월마다 시점정확 멤버(이중클래스 하나 · 가격 키가 오늘 유니버스 · 그날 가격 ·
#   13F 분기말에 있던 증권) 가운데 명단 전원(퀀트 포함 이력 CIK 전부) 아무도 안 든 종목 수의 상한. 수선 전 이력은 최대 38(S&P 500 35).
F0F_MAX_SPX, F0F_MAX_UNION = 3, 5
# F0-d 옛 CUSIP 수선 확인(C 팔 보유 곳 수 · 수선 전 이력은 셋 다 0)
F0D_OLD_CUSIP = (("GOOGL", "2014-08", 2), ("AVGO", "2017-08", 2), ("LRCX", "2018-08", 2))
# 후속 등록 후보 규칙(계산 전 고정 · 주 팔 VG 칸만 · 이 등록에서 채택 없음)
#   c6 · c8 은 대조(S1 − B0 · S2 − U)를 넘어야 한다 — 펀드 대 SPY TR 초과에는 패널 · 생존 편향이 섞여 있다(등록 §5-2 · §10)
CAND = {"nw_t_min": 2.0, "style_alpha_t_min": 1.5, "years_won_frac": 0.70, "min_full_years": 9, "roll36_hit_min": 60.0,
        "ctrl_nw_t_min": 1.5, "ctrl_alpha_t_min": 1.5}
CUM_N_BEFORE = 968
N_ROWS_COUNTED = 8                     # 팔 3 × 신호 2 + 대조 2(B0 · U) — EG30 V0 는 이미 셌다

# 명명(표시용) — 계산에 쓰지 않는다
ARM_LABEL = {"VG": "밸류 + 성장(27 + 사이언 이력 · 주 팔)", "C": "옛 겹침 명단(2026-09-27 전 · 퀀트만 뺀 43 + 사이언 이력)",
             "C-BW": "옛 겹침 명단 − 브리지워터(42 + 사이언 이력)"}


class StopBake(RuntimeError):
    """등록된 멈춤 조건 · 결정적 자기 점검 실패 — 굽기 자식이 {"stopped": 사유} 로 돌려준다(다시 굽기로 풀리지 않는다 · 멈춤 기록이 결과다)."""


def arm_sets():
    """팔 → CIK 문자열 집합(이력 셈 · 사이언 이력 포함)."""
    s = lambda xs: frozenset(str(c) for c in xs)
    vg = s(VALUE + GROWTH + HIST_ONLY_VALUE)
    c = s(VALUE + ACTIVIST + GROWTH + MACRO + CREDIT + ENDOW + HIST_ONLY_VALUE)
    return {"VG": vg, "C": c, "C-BW": c - {str(BRIDGEWATER)}}


def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7]) + k
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return "%04d-%02d" % (y, m)


def months_between(a, b):
    out, m = [], a
    while m <= b:
        out.append(m)
        m = mshift(m, 1)
    return out


def _json(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def _wjson(p, obj):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with io.open(p + ".part", "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False, allow_nan=False) + "\n")
    os.replace(p + ".part", p)


# ══════════════════════════════════════════════════════════════════════════
#  13F 셈 — counts_by_quarter 와 같은 논리 + 팔 필터(허용 CIK 집합)
# ══════════════════════════════════════════════════════════════════════════
def load_history(as_of=AS_OF, G=None):
    """guru_history.json → (G, months, P, mi) — guru_cmp.main 과 같은 자르기(as_of 달부터 뺀다)."""
    if G is None:
        from guru17_backtest import load as g_load
        G = g_load("guru_history.json")
    months, P = list(G["months"]), G["mpx"]
    while months and months[-1] >= as_of:
        months = months[:-1]
    P = {t: v[:len(months)] for t, v in P.items()}
    mi = {m: i for i, m in enumerate(months)}
    return G, months, P, mi


def arm_holders(G, mi, P, months, allow):
    """체결월 → {티커: 보유 CIK 집합} · diag. guru_overlap_backtest.counts_by_quarter 와 같은 차례 · 같은 거르기
    (공시일이 체결월 말보다 뒤면 제외 · 보유 값 ≤ 0 제외 · 체결월 가격 없는 종목 제외) — 다른 것은 «NO_OVERLAP 이 아니면» 대신 «allow 안이면» 뿐."""
    from guru17_backtest import add_months, month_end, LAG_MONTHS
    H, FILED = G["holdings"], G.get("filed") or {}
    out, diag = {}, []
    for q in sorted(H):
        qm = q[:7]
        rm = add_months(qm, LAG_MONTHS)
        if rm not in mi or qm not in mi:
            continue
        i_r = mi[rm]
        hold, used, skipped = {}, 0, 0
        for cik, raw in H[q].items():
            if cik not in allow:
                continue
            fd = (FILED.get(q) or {}).get(cik)
            if fd and fd > month_end(rm):
                skipped += 1
                continue
            used += 1
            for t, v in raw.items():
                if not v or v <= 0:
                    continue
                if P.get(t, [None] * len(months))[i_r] is None:
                    continue
                hold.setdefault(t, set()).add(cik)
        out[rm] = hold
        diag.append({"q": q, "rebal": rm, "managers": used, "lookahead_skipped": skipped,
                     "n_ge2": sum(1 for c in hold.values() if len(c) >= 2)})
    return out, diag


def arm_counts(G, mi, P, months, allow):
    H, diag = arm_holders(G, mi, P, months, allow)
    return {rm: {t: len(c) for t, c in h.items()} for rm, h in H.items()}, diag


def signal_at(counts, reb, mm):
    """신호월 mm 에 알 수 있는 최신 체결월의 (수준, 직전 체결월 수준) — guru_cmp.signal_at 과 같다."""
    past = [r for r in reb if r <= mm]
    if len(past) < 2:
        return None, None
    return counts[past[-1]], counts[past[-2]]


# ══════════════════════════════════════════════════════════════════════════
#  S1 — 합의 점수 행(guru_cmp.main 의 행 만들기 그대로)
# ══════════════════════════════════════════════════════════════════════════
def s1_base_rows(Wd, ix, sig, end):
    import pit_panel as PP
    sig_months = [m for m in sorted(set(k[:7] for k in Wd["me"])) if sig[0] <= m <= sig[1]]
    return PP.month_rows(Wd, ix, sig_months, end)


def attach_z(rows_base, counts, today):
    """행마다 Z['rev'] · cov['guru'] 를 붙인 새 행 목록(얕은 복사 — names · wb · r · sec · key 는 공유 · 바꾸지 않는다)."""
    import idxrev as IR
    from guru_cmp import zs
    reb = sorted(counts)
    out = []
    for x0 in rows_base:
        x = dict(x0)
        cur, prev = signal_at(counts, reb, x["sig"])
        names = x["names"]
        mp = [t for t in names if x["key"][t] in today]
        if cur is None:
            x["Z"] = {"rev": {}}
            x["cov"] = {"guru": 0.0}
            out.append(x)
            continue
        lev = {t: float(cur.get(x["key"][t], 0)) for t in mp}
        chg = {t: float(cur.get(x["key"][t], 0) - prev.get(x["key"][t], 0)) for t in mp}
        zl, zc = zs(lev), zs(chg)
        raw = {t: 0.5 * (zl[t] + zc[t]) for t in mp}
        z = IR.zsec(raw, x["sec"], names)
        wmp = sum(x["wb"][t] for t in z)
        c = (sum(x["wb"][t] * z[t] for t in z) / wmp) if wmp > 0 else 0.0
        x["Z"] = {"rev": {t: z[t] - c for t in z}}
        x["cov"] = {"guru": wmp}
        out.append(x)
    return out


def tilt_weights(rows, j0, te_target, lam_mult, flip=False):
    """idxrev.run(signal 'rev' · cap 'prop' · band False)의 비중 셈을 그대로 옮겨 달마다 비중을 돌려준다(run 은 마지막 비중만 준다).
    굽기는 달마다 p · b · cost 가 run 과 1e-12 안에서 같은지 단언한다(selftest 도 합성으로)."""
    import idxtilt as IT
    out, prevw = [], None
    for j in range(j0, len(rows)):
        x = rows[j]
        names, wb = x["names"], x["wb"]
        sc = {}
        for t in names:
            v = x["Z"]["rev"].get(t)
            sc[t] = (0.0 if v is None else (-v if flip else v))
        mu = sum(wb[t] * sc[t] for t in names)
        tl = {t: sc[t] - mu for t in names}
        ss = math.sqrt(sum(wb[t] * tl[t] ** 2 for t in names)) or 1e-9
        lam = te_target / (ss * 0.18)
        if lam_mult is not None:
            lam *= lam_mult
        w = {}
        for t in names:
            cap = wb[t]
            a_ = max(-cap, min(cap, lam * tl[t]))
            w[t] = max(0.0, wb[t] + a_)
        bysec = collections.defaultdict(list)
        for t in names:
            bysec[x["sec"].get(t, "?")].append(t)
        for s, ts in bysec.items():
            da = sum(w[t] - wb[t] for t in ts)
            if abs(da) > IT.CAP_SEC:
                k_ = IT.CAP_SEC / abs(da)
                for t in ts:
                    w[t] = max(0.0, wb[t] + (w[t] - wb[t]) * k_)
        z = sum(w.values())
        w = {t: w[t] / z for t in w}
        rp = sum(w[t] * x["r"][t] for t in names)
        rb = sum(wb[t] * x["r"][t] for t in names)
        c = 0.0
        if prevw is not None:
            c = IT.COST_RT * 0.5 * sum(abs(w.get(t, 0.0) - prevw.get(t, 0.0)) for t in sorted(set(w) | set(prevw)))
        prevw = w
        out.append({"m": x["m"], "sig": x["sig"], "w": w, "p": rp, "b": rb, "cost": c})
    return out


def weights_path(Wd, rows, j0, books):
    """달마다 비중(books[j]['w'] · 키 = 명단 티커)으로 일간 경로 — 신호월 말 i 종가에 사서 보유월 말 i1 까지 흘러간다(값 없는 날은 마지막 값).
    체결 날 경로 값 = 비용 뒤 값(qg_lab.World.sleeve · qbatch_core.etf_path 와 같은 규약 · 첫 체결 비용은 경로 밖).
    달 말 값 = 체결 값 × Σ w (1 + r) — pit_panel 의 보유월 수익(seg 마지막 값 / 신호월 값 − 1)과 같은 가격을 쓴다."""
    PX, me = Wd["PX"], Wd["me"]
    path, V = {}, 1.0
    for j, bk in enumerate(books):
        x = rows[j0 + j]
        i, i1 = me[x["sig"]], me[x["m"]]
        if j > 0 and i not in path:
            raise StopBake("S1 행이 이어지지 않는다: %s" % x["m"])
        V = path.get(i, V)
        V2 = V * (1.0 - bk.get("cost", 0.0))
        units, last = {}, {}
        for t, wt in bk["w"].items():
            if wt <= 0:
                continue
            k = x["key"][t]
            p0 = PX[k][i]
            if not (p0 == p0 and p0 > 0):
                raise StopBake("체결 가격 없음 %s %s" % (k, x["sig"]))
            units[k] = units.get(k, 0.0) + V2 * wt / p0
            last[k] = i
        path[i] = V2
        for d in range(i + 1, i1 + 1):
            tot = 0.0
            for k, u in units.items():
                p = PX[k][d]
                if p == p and p > 0:
                    last[k] = d
                tot += u * PX[k][last[k]]
            path[d] = tot
        V = path[i1]
    return path


# ══════════════════════════════════════════════════════════════════════════
#  S2 · U — 분기 체결 동일가중 바스켓(일간 경로)
# ══════════════════════════════════════════════════════════════════════════
def union_mapped(Wd, rm):
    """체결월 rm 말의 S&P 500 ∪ NASDAQ 100 멤버 중 13F 매핑(오늘 유니버스 키)이 있고 그날 가격이 선 가격 키 목록(정렬)."""
    import pit_panel as PP
    i = Wd["me"][rm]
    mem, _n = PP.union_members(Wd, rm, i)
    PX, today = Wd["PX"], Wd["today"]
    out = set()
    for t, k in mem:
        if k in today:
            p = PX[k][i]
            if p == p and p > 0:
                out.add(k)
    return sorted(out)


def basket_targets(Wd, reb_months, counts=None, k=K):
    """체결월 → 담을 가격 키 목록. counts 가 None 이면 U(매핑 유니버스 전부)."""
    tg = {}
    for rm in reb_months:
        uni = union_mapped(Wd, rm)
        if counts is None:
            tg[rm] = uni
        else:
            c = counts.get(rm) or {}
            tg[rm] = [x for x in uni if c.get(x, 0) >= k]
    return tg


def basket_path(Wd, reb_months, targets, end_month, cost=COST, min_hold=MIN_HOLD):
    """분기 체결 동일가중 경로 — 체결월 말 종가에 사고 다음 체결까지 흘러간다 · 편도 cost × 거래액 · 최소 min_hold 종목(못 미치면 그 체결은 건너뛰고 들던 것을 든다).
    돌려주는 것 {path, turn, n_names(체결마다 · 건너뛰면 None), skipped}."""
    PX, me = Wd["PX"], Wd["me"]
    reb = sorted(reb_months)
    i0, iE = me[reb[0]], me[end_month]
    path, units, last = {}, {}, {}
    V = 1.0
    turns, n_names, skipped = [], [], []
    bounds = [me[m] for m in reb] + [iE]
    for j, rm in enumerate(reb):
        i, i_next = me[rm], bounds[j + 1]
        if i >= iE:
            break
        val = {k: units[k] * PX[k][last[k]] for k in units}
        V = sum(val.values()) if units else V
        tgt = list(targets.get(rm) or [])
        if len(tgt) < min_hold:
            if j == 0:
                raise StopBake("첫 체결 %s 의 종목이 %d 개(최소 %d)" % (rm, len(tgt), min_hold))
            skipped.append(rm)
            n_names.append(None)
            turns.append(0.0)
            path[i] = V
        else:
            wv = V / len(tgt)
            tv = {k: wv for k in tgt}
            traded = sum(abs(tv.get(k, 0.0) - val.get(k, 0.0)) for k in sorted(set(tv) | set(val)))
            V2 = V - cost * traded
            units = {k: (V2 / len(tgt)) / PX[k][i] for k in tgt}
            last = {k: i for k in units}
            turns.append(traded / V)
            n_names.append(len(tgt))
            path[i] = V2
        for d in range(i + 1, min(i_next, iE) + 1):
            tot = 0.0
            for k, u in units.items():
                p = PX[k][d]
                if p == p and p > 0:
                    last[k] = d
                tot += u * PX[k][last[k]]
            path[d] = tot
    yrs = (iE - i0) / 252.0 if iE > i0 else 1.0
    return {"path": path, "turn": float(sum(turns) / 2.0 / max(yrs, 1e-9)), "n_names": n_names, "skipped": skipped}


# ══════════════════════════════════════════════════════════════════════════
#  펀드 틀 · 지표(qbatch_core 그대로 + 36개월 굴림 · 스타일 · MDD · 차이)
# ══════════════════════════════════════════════════════════════════════════
def make_grid(Wd):
    """qbatch_core.Grid — 날짜 격자 = 패널(stocks.json) · SPY 총수익 = assets.json px.SPY · S&P 500 PR = bench_px spx(날짜로 맞추고 앞값 채움)."""
    import numpy as np
    import qbatch_core as QC
    A = QC.load("assets.json")
    B = QC.load("bench_px.json")
    pa = {d: i for i, d in enumerate(A["dates"])}
    pb = {d: i for i, d in enumerate(B["dates"])}
    spy = [A["px"]["SPY"][pa[d]] if d in pa and A["px"]["SPY"][pa[d]] is not None else np.nan for d in Wd["dates"]]
    spx = [B["series"]["spx"]["px"][pb[d]] if d in pb and B["series"]["spx"]["px"][pb[d]] is not None else np.nan for d in Wd["dates"]]
    return QC.Grid(Wd["dates"], spy, spx)


def fund(G, path, forms, turn=None):
    import qbatch_core as QC
    return QC.fund_from_path(G, {"path": path, "turn": turn}, forms, cost=COST, basis="TR")


def sub_fr(G, fr, h0):
    """펀드 결과를 보유월 h0 부터로 자른다(같은 굽기의 부분 창 — 다시 풀지 않는다)."""
    import numpy as np
    j = fr["hold"].index(h0)
    i0 = G.me[mshift(h0, -1)]
    out = dict(fr)
    out["hold"] = fr["hold"][j:]
    for k in ("ex", "basket", "index", "fund"):
        out[k] = np.asarray(fr[k])[j:]
    out["days"] = [d for d in fr["days"] if d >= i0]
    return out


def roll36(ex, ix, n=ROLL_N):
    """36개월 굴린 초과 — 펀드 36개월 연율 복리 − 지수 36개월 연율 복리(%p) · 펀드 월 = 지수 월 + 월 초과."""
    import numpy as np
    ex, ix = np.asarray(ex, float) / 100, np.asarray(ix, float) / 100
    f = ix + ex
    r = [((np.prod(1 + f[k - n:k])) ** (12.0 / n) - (np.prod(1 + ix[k - n:k])) ** (12.0 / n)) * 100 for k in range(n, len(ex) + 1)]
    if not r:
        return {"n": 0}
    r = np.array(r)
    return {"n": int(len(r)), "hit": float(np.mean(r > 0) * 100), "worst": float(r.min()), "median": float(np.median(r)),
            "best": float(r.max()), "last": float(r[-1])}


def ff_monthly(Wd, ff):
    """French 일간(%) → 달 복리(%) — 그달 패널 마지막 거래일이 French 날짜에 있을 때만(미완결 달 제외)."""
    ds = ff["dates"]
    pos = {d: i for i, d in enumerate(ds)}
    by = collections.OrderedDict()
    for i, d in enumerate(ds):
        by.setdefault(d[:7], []).append(i)
    out = {}
    for m, idx in by.items():
        me = Wd["me"].get(m)
        if me is None or Wd["dates"][me] not in pos:
            continue
        row = {}
        for f in FF_FACTORS:
            s = ff["series"][f]
            p = 1.0
            for i in idx:
                v = s[i]
                if v is None:
                    p = None
                    break
                p *= 1 + float(v) / 100.0
            row[f] = None if p is None else (p - 1.0) * 100.0
        if all(v is not None for v in row.values()):
            out[m] = row
    return out


def style(fr, ffm):
    """스타일 통제 — 펀드 월 초과(%) = α + β·[Mkt−RF · SMB · HML · Mom](%) · Newey–West(3) t(eg30plus.nw_ols)."""
    import numpy as np
    import eg30plus as E
    js = [j for j, h in enumerate(fr["hold"]) if h in ffm]
    if len(js) < 24:
        return {"n": len(js)}
    y = np.asarray(fr["ex"], float)[js]
    X = np.column_stack([np.ones(len(js))] + [np.array([ffm[fr["hold"][j]][f] for j in js]) for f in FF_FACTORS])
    b, t = E.nw_ols(y, X, lag=NW_LAG)
    out = {"n": len(js), "alpha_ann": float(b[0] * 12), "alpha_t": float(t[0])}
    for q, f in enumerate(FF_FACTORS):
        out["b_" + f], out["t_" + f] = float(b[q + 1]), float(t[q + 1])
    return out


def mdd(r):
    import numpy as np
    nav = np.cumprod(1 + np.asarray(r, float) / 100)
    return float((nav / np.maximum.accumulate(nav) - 1).min() * 100)


def full_years(hold):
    c = collections.Counter(h[:4] for h in hold)
    return sorted(y for y, n in c.items() if n == 12)


def metrics(G, fr, ffm):
    """qbatch_core.evaluate + CAGR 차 · 36개월 굴림 · 스타일 통제 · MDD · 온전한 해 승수."""
    import numpy as np
    import qbatch_core as QC
    ev = QC.evaluate(G, fr)
    n = len(fr["ex"])
    fu, ix = np.asarray(fr["fund"], float), np.asarray(fr["index"], float)
    cg = lambda r: (np.prod(1 + r / 100) ** (12.0 / n) - 1) * 100
    ev["cagr_fund"], ev["cagr_index"] = float(cg(fu)), float(cg(ix))
    ev["cagr_ex"] = ev["cagr_fund"] - ev["cagr_index"]
    ev["roll36"] = roll36(fr["ex"], fr["index"])
    ev["style"] = style(fr, ffm)
    ev["mdd_fund"], ev["mdd_index"] = mdd(fu), mdd(ix)
    fy = full_years(fr["hold"])
    ev["full_years"] = fy
    ev["years_won_full"] = int(sum(1 for y in fy if ev["years"].get(y, 0) > 0))
    ev["n_full_years"] = len(fy)
    ev["window"] = [fr["hold"][0], fr["hold"][-1]]
    return ev


def diff_stats(G, fa, fb, ffm=None):
    """두 펀드의 월 초과 차 d = ex_a − ex_b — 연 평균 · NW t · iid t · 월 승률 · 하락월 평균 · 해마다 승수 · ΔIR ·
    (ffm 을 주면) d 의 4요인 통제 α(style — 대조 차의 스타일 몫을 걷어 낸 «거장이 골랐다» 몫 · 후보 규칙 c8)."""
    import numpy as np
    import eg30plus as E
    a, b = np.asarray(fa["ex"], float), np.asarray(fb["ex"], float)
    if list(fa["hold"]) != list(fb["hold"]):
        raise StopBake("차이의 두 판 보유월이 다르다")
    d = a - b
    dset = set(G.down_months(fa["hold"]))
    dm = np.array([h in dset for h in fa["hold"]])
    yrs = {}
    for h, x, y in zip(fa["hold"], fa["fund"], fb["fund"]):
        v = yrs.setdefault(h[:4], [1.0, 1.0])
        v[0] *= 1 + x / 100
        v[1] *= 1 + y / 100
    fy = full_years(fa["hold"])
    te = lambda v: float(v.std(ddof=1) * math.sqrt(12))
    ir = lambda v: float(v.mean() * 12 / te(v)) if te(v) > 0 else None
    out = {"n": int(len(d)), "mean_ann": float(d.mean() * 12), "nw_t": E.nw_t(d, lag=NW_LAG),
            "t_iid": float(d.mean() / (d.std(ddof=1) / math.sqrt(len(d)))) if d.std(ddof=1) > 0 else None,
            "win": float(np.mean(d > 0) * 100), "down_mean": float(d[dm].mean()) if dm.any() else None,
            "up_mean": float(d[~dm].mean()) if (~dm).any() else None,
            "years_won_full": int(sum(1 for y in fy if yrs[y][0] > yrs[y][1])), "n_full_years": len(fy),
            "d_ir": (ir(a) - ir(b)) if (ir(a) is not None and ir(b) is not None) else None,
            "window": [fa["hold"][0], fa["hold"][-1]]}
    if ffm is not None:
        out["style"] = style({"hold": list(fa["hold"]), "ex": d}, ffm)
    return out


def native_s1(o, h0=None):
    """S1 고유 틀(idxrev.ev — GURUCMP 의 IR · t · 비용 뒤 IR · 월승률) — h0 를 주면 같은 굽기의 부분 창."""
    import idxrev as IR
    oo = [z for z in o if h0 is None or z["m"] >= h0]
    s = IR.ev(oo)
    s["window"] = [oo[0]["m"], oo[-1]["m"]]
    return s


def candidate(full, pub, native_full, ctrl_diff_full, sig):
    """후속 등록 후보 규칙(계산 전 고정) — 모두 참이어야 «후속 등록 후보». 이 등록에서 채택하는 것은 없다.
    c1 ~ c5 · c7 · c9 는 펀드 대 SPY TR(패널 · 생존 편향이 섞인다) · c6 · c8 은 대조를 넘는가(S1 − B0 · S2 − U · 같은 편향을 공유)."""
    st = full.get("style") or {}
    mech = (pub.get("mech") or {}).get("crash_legs") or {}
    reb = (pub.get("mech") or {}).get("rebounds") or {}
    cst = ctrl_diff_full.get("style") or {}
    c = {
        "c1_excess_pos_both": bool(full["ann_ex"] > 0 and pub["ann_ex"] > 0),
        "c2_nw_t": bool((full.get("nw_t") or -9) >= CAND["nw_t_min"]),
        "c3_style_alpha": bool(st.get("alpha_ann") is not None and st["alpha_ann"] > 0 and (st.get("alpha_t") or -9) >= CAND["style_alpha_t_min"]),
        "c4_years": bool(full["n_full_years"] >= CAND["min_full_years"]
                         and full["years_won_full"] >= math.ceil(CAND["years_won_frac"] * full["n_full_years"] - 1e-9)),
        "c5_defense": bool(full["down_mean"] >= 0 and (mech.get("mean") is not None and mech["mean"] >= 0)),
        "c6_control": bool(ctrl_diff_full["mean_ann"] > 0 and (ctrl_diff_full.get("nw_t") or -9) >= CAND["ctrl_nw_t_min"]
                           and (sig == "S2" or (native_full.get("placebo_ir") is not None and native_full["placebo_ir"] < 0))),
        "c7_roll36": bool((full.get("roll36") or {}).get("hit", 0) >= CAND["roll36_hit_min"]),
        "c8_control_style": bool(cst.get("alpha_ann") is not None and cst["alpha_ann"] > 0 and (cst.get("alpha_t") or -9) >= CAND["ctrl_alpha_t_min"]),
        "c9_surge": bool(full.get("up_mean") is not None and full["up_mean"] >= 0 and reb.get("mean") is not None and reb["mean"] >= 0),
    }
    c["all"] = bool(all(c.values()))
    return c


def predictions(R):
    """미리 적은 예측(계산 전 고정 · 결과 문서가 채점) — 참/거짓만."""
    cells, dif = R["cells"], R["diffs"]
    g = lambda a, s: cells[a][s]["full"]
    P = {}
    P["P1_vg_minus_c_indistinct"] = bool(all(abs(dif["VG-C"][s]["full"]["nw_t"] or 0) < 1.5 for s in SIGNALS))
    a = abs(dif["C-BW-C"]["S2"]["full"]["mean_ann"])
    b = abs(dif["VG-C"]["S2"]["full"]["mean_ann"])
    P["P2_bw_half_of_vg_gap_s2"] = bool(b == 0 or a >= 0.5 * b)
    P["P3_style_alpha_small"] = bool(all(abs((g(x, s).get("style") or {}).get("alpha_t") or 0) < 1.5 for x in ARM_NAMES for s in SIGNALS))
    P["P4_fund_excess_small"] = bool(all(abs(g(x, s)["ann_ex"]) < 0.5 for x in ARM_NAMES for s in SIGNALS))
    P["P5_s2_not_beyond_u"] = bool(all((R["ctrl_diffs"][x]["S2"]["full"]["nw_t"] or 0) < 1.5 for x in ARM_NAMES))
    P["P6_no_candidate"] = bool(not any(R["candidates"][s]["all"] for s in SIGNALS))
    return P


# ══════════════════════════════════════════════════════════════════════════
#  잎 비교(F0-b) — 숫자 잎은 tol 안 · 글자 · 참/거짓 · None 은 같아야
# ══════════════════════════════════════════════════════════════════════════
def leaf_compare(a, b, tol=TOL_F0B, path=""):
    bad, n = [], 0
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return [path + ":키"], 1
        for k in sorted(a):
            bb, nn = leaf_compare(a[k], b[k], tol, path + "/" + str(k))
            bad += bb
            n += nn
        return bad, n
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return [path + ":길이"], 1
        for q, (x, y) in enumerate(zip(a, b)):
            bb, nn = leaf_compare(x, y, tol, path + "[%d]" % q)
            bad += bb
            n += nn
        return bad, n
    if isinstance(a, bool) or isinstance(b, bool):
        return ([] if (type(a) is type(b) and a == b) else [path]), 1
    if a is None or b is None or isinstance(a, str) or isinstance(b, str):
        return ([] if a == b else [path]), 1
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        ok = (a == b) or (math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a) - float(b)) <= tol)
        return ([] if ok else [path]), 1
    return ([] if a == b else [path]), 1


def rows_compare(ra, rb, tol=TOL_F0B):
    """S1 행 두 벌이 같은가 — 달 · 명단 · 키 · 섹터는 같아야 · wb · r 은 1e-12 · Z · cov 는 tol."""
    if len(ra) != len(rb):
        return ["행 수"]
    bad = []
    for x, y in zip(ra, rb):
        for k in ("m", "sig", "names"):
            if x[k] != y[k]:
                bad.append("%s:%s" % (x.get("m"), k))
        if x["key"] != y["key"] or x["sec"] != y["sec"]:
            bad.append("%s:key/sec" % x["m"])
        for k in ("wb", "r"):
            if set(x[k]) != set(y[k]) or any(abs(x[k][t] - y[k][t]) > 1e-12 for t in x[k]):
                bad.append("%s:%s" % (x["m"], k))
        zx, zy = x["Z"]["rev"], y["Z"]["rev"]
        if set(zx) != set(zy) or any(abs(zx[t] - zy[t]) > tol for t in zx):
            bad.append("%s:Z" % x["m"])
        if abs(x["cov"]["guru"] - y["cov"]["guru"]) > tol:
            bad.append("%s:cov" % x["m"])
    return bad


def _snap_rows(rows):
    return [{"m": x["m"], "sig": x["sig"], "names": list(x["names"]), "key": dict(x["key"]), "sec": dict(x["sec"]),
             "wb": dict(x["wb"]), "r": dict(x["r"]), "Z": {"rev": dict((x.get("Z") or {}).get("rev") or {})},
             "cov": {"guru": float((x.get("cov") or {}).get("guru") or 0.0)}} for x in rows]


# ══════════════════════════════════════════════════════════════════════════
#  자식 과정 — F0-b(3bbe5ca1d 뿌리) · F0(760df724b 뿌리 · 수익 없음) · 굽기(760df724b 뿌리)
# ══════════════════════════════════════════════════════════════════════════
def f0b_child(tmp_out):
    """🚨 3bbe5ca1d 판 뿌리에서만. (b1) 얼린 guru_cmp.main 을 그 판 입력으로 다시 돌려 data/_guru_cmp.json(동결)의 모든 잎이 1e-9 안에서 같은가
    (b2) 이 엔진의 C 팔 셈 · S1 행(S&P 500 · NASDAQ 100)이 guru_cmp 가 idxrev.solve 에 넘긴 입력과 같은가. 값은 돌려주지 않는다(참/거짓 · 개수 · 어긋난 잎 경로)."""
    import contextlib
    import datetime
    import types
    import guru_cmp as GC
    import guru_overlap_backtest as GO
    import idxrev as IR
    import pit_panel as PP
    rec = {"counts": None, "diag": None, "rows": {}, "j0": {}}
    real_cbq, real_solve = GO.counts_by_quarter, IR.solve

    def cbq(*a, **k):
        out = real_cbq(*a, **k)
        if rec["counts"] is None:
            rec["counts"], rec["diag"] = copy.deepcopy(out[0]), copy.deepcopy(out[1])
        return out

    order, alive = [], []                                    # alive — 행 목록을 붙잡아 id 가 다시 쓰이지 않게(S&P 500 행이 풀린 뒤 NASDAQ 100 행이 같은 id 를 받는 것을 막는다)

    def solve(rows, j0, signal, cap_mode, te_target, flip=False, band=False):
        if cap_mode == "prop" and not flip and id(rows) not in rec["rows"]:
            alive.append(rows)
            rec["rows"][id(rows)] = _snap_rows(rows)
            rec["j0"][id(rows)] = j0
            order.append(id(rows))
        return real_solve(rows, j0, signal, cap_mode, te_target, flip, band)

    real_lw, wc = PP.load_world, {}

    def lw():                                                # 같은 세계를 엔진 쪽 대조에도 쓴다(두 번 읽지 않는다 · 읽기만 한다)
        if "W" not in wc:
            wc["W"] = real_lw()
        return wc["W"]

    frozen_p = os.path.join(DATA, "_guru_cmp.json")
    frozen = _json(frozen_p)
    GO.counts_by_quarter, IR.solve, PP.load_world = cbq, solve, lw
    GC.dt = types.SimpleNamespace(date=types.SimpleNamespace(today=lambda: datetime.date(*F0B_TODAY)))
    GC.OUT = tmp_out
    try:
        with open(os.devnull, "w", encoding="utf-8") as dn, contextlib.redirect_stdout(dn):
            GC.main()
    finally:
        GO.counts_by_quarter, IR.solve, PP.load_world = real_cbq, real_solve, real_lw
    new = _json(tmp_out)
    os.remove(tmp_out)
    bad1, n1 = leaf_compare(new, frozen)
    del new, frozen
    # (b2) 엔진 — C 팔(이 판 이력의 CIK − 퀀트)
    G, months, P, mi = load_history(as_of="%04d-%02d" % F0B_TODAY[:2])
    hist = set()
    for q, h in G["holdings"].items():
        hist |= set(h)
    allow = frozenset(hist - {str(c) for c in QUANT})
    counts_e, diag_e = arm_counts(G, mi, P, months, allow)
    same_counts = bool(counts_e == rec["counts"] and diag_e == rec["diag"])
    Wd = lw()
    bad2, nrows = [], {}
    for n_ix, ix in enumerate(("spx", "ndx")):
        rows_b, _cov = s1_base_rows(Wd, ix, F0B_SIG, F0B_END)
        rows_e = attach_z(rows_b, counts_e, Wd["today"])
        j0 = next(k for k, x in enumerate(rows_e) if x["m"] >= F0B_JUDGE0)
        if n_ix >= len(order):
            bad2.append("%s:잡힌 행 없음" % ix)
            continue
        ref = rec["rows"][order[n_ix]]
        bad2 += ["%s:%s" % (ix, b) for b in rows_compare(_snap_rows(rows_e), ref)]
        if j0 != rec["j0"][order[n_ix]]:
            bad2.append("%s:j0" % ix)
        nrows[ix] = len(rows_e)
    return {"kind": "gfund_f0b", "record_reproduced": not bad1, "n_leaves": n1, "n_bad_leaves": len(bad1), "bad_leaves": bad1[:8],
            "engine_counts_same": same_counts, "engine_rows_same": not bad2, "rows_bad": bad2[:8], "n_rows": nrows,
            "n_reb": len(counts_e), "n_allow": len(allow), "ok": bool(not bad1 and same_counts and not bad2)}


def _arms_check():
    """팔 상수 = 이 뿌리 refresh_13f 의 AXES · HISTORY_ONLY · NO_OVERLAP 규칙(명단을 코드 밖에서 다시 적지 않았는지)."""
    import refresh_13f as R
    ax = {a[0]: {str(c) for c in a[4]} for a in R.AXES}
    ho = {str(c): h["axis"] for c, h in R.HISTORY_ONLY.items()}
    want_vg = ax["value"] | ax["growth"] | {c for c, a in ho.items() if a in ("value", "growth")}
    nov = {str(c) for c in R.NO_OVERLAP}
    want_c = ({str(c) for c in R.GURUS} - nov) | {c for c, a in ho.items() if str(c) not in nov and a != "quant"}
    A = arm_sets()
    bad = []
    if A["VG"] != want_vg:
        bad.append("VG")
    if A["C"] != want_c:
        bad.append("C")
    if A["C-BW"] != want_c - {str(BRIDGEWATER)}:
        bad.append("C-BW")
    if nov != {str(c) for c in QUANT}:
        bad.append("QUANT")
    if len(ax["value"]) != 16 or len(ax["growth"]) != 11:
        bad.append("축 곳 수")
    return {"ok": not bad, "bad": bad, "n_current": {"VG": len(ax["value"] | ax["growth"]), "C": len({str(c) for c in R.GURUS} - nov),
                                                     "C-BW": len({str(c) for c in R.GURUS} - nov - {str(BRIDGEWATER)})},
            "n_history": {k: len(v) for k, v in A.items()}}


def f0_child():
    """F0 — 수익 없음(개수 · 날짜 · 커버리지 · 동일성). 굽기 전 판 점검이 부른다."""
    import numpy as np
    import guru_overlap_backtest as GO
    import pit_panel as PP
    out = {"kind": "gfund_f0", "arms": _arms_check()}
    G, months, P, mi = load_history()
    A = arm_sets()
    hold = {a: arm_holders(G, mi, P, months, A[a]) for a in ARM_NAMES}
    counts = {a: {rm: {t: len(c) for t, c in h.items()} for rm, h in hold[a][0].items()} for a in ARM_NAMES}
    go_counts, go_diag = GO.counts_by_quarter(G, mi, P, months)
    out["f0c"] = {"ok": bool(counts["C"] == go_counts and hold["C"][1] == go_diag), "n_reb": len(go_counts)}
    # F0-d 수선 확인(구성 사실)
    H = G["holdings"]
    rbk = counts["C"].get("2026-08", {}).get("BRK.B", 0)
    harris = [len([t for t, v in ((H.get(q) or {}).get("813917") or {}).items() if v and v > 0]) for q in sorted(H) if "2022-03-31" <= q <= "2026-06-30"]
    last = (H.get("2026-06-30") or {})
    d = {"brkb_holders_2026_08": int(rbk), "brkb_ok": bool(rbk >= 8),
         "harris_min_names_2022_2026": int(min(harris)) if harris else 0, "harris_ok": bool(harris and min(harris) >= 50),
         "eqix_coatue": bool(((last.get("1135730") or {}).get("EQIX") or 0) > 0),
         "kkr_akre": bool(((last.get("1112520") or {}).get("KKR") or 0) > 0)}
    # 옛 CUSIP 수선 확인(C 팔 보유 곳 수 · 수선 전 이력은 셋 다 0)
    oc = {}
    for t, m, need in F0D_OLD_CUSIP:
        n_ = int(counts["C"].get(m, {}).get(t, 0))
        oc["%s_%s" % (t, m)] = {"holders": n_, "min": need, "ok": bool(n_ >= need)}
    d["old_cusip"] = oc
    d["old_cusip_ok"] = bool(all(v["ok"] for v in oc.values()))
    d["ok"] = bool(d["brkb_ok"] and d["harris_ok"] and d["eqix_coatue"] and d["kkr_akre"] and d["old_cusip_ok"])
    out["f0d"] = d
    # 창 · 체결월
    reb_all = sorted(go_counts)
    reb_w = [m for m in reb_all if mshift(WIN[0], -1) <= m <= mshift(WIN[1], -1)]
    Wd = PP.load_world()
    rows, cover = s1_base_rows(Wd, "spx", SIG, WIN[1])
    rw = [x for x in rows if WIN[0] <= x["m"] <= WIN[1]]
    contiguous = all(rw[q]["m"] == mshift(rw[q - 1]["m"], 1) for q in range(1, len(rw)))
    out["window"] = {"win": list(WIN), "pub": list(PUB), "first_13f_quarter": sorted(H)[0], "first_reb": reb_all[0],
                     "first_reb_with_prev": reb_all[1] if len(reb_all) > 1 else None, "index_history_first": min(Wd["lists"]["spx"]),
                     "first_s2_form": reb_w[0] if reb_w else None, "last_s2_form": reb_w[-1] if reb_w else None, "n_s2_forms": len(reb_w),
                     "s1_first_hold": rw[0]["m"] if rw else None, "s1_last_hold": rw[-1]["m"] if rw else None, "s1_n": len(rw),
                     "s1_contiguous": bool(contiguous), "ok": bool(rw and rw[0]["m"] == WIN[0] and rw[-1]["m"] == WIN[1] and len(rw) == N_WIN
                                                                   and contiguous and reb_w and reb_w[0] == mshift(WIN[0], -1))}
    covw = [c for x, c in zip(rows, cover) if WIN[0] <= x["m"] <= WIN[1]] if len(cover) == len(rows) else list(cover)
    out["panel"] = {"coverage_min": float(min(covw)) if covw else None, "coverage_med": float(np.median(covw)) if covw else None}
    # F0-e 팔 두께 · 구성 서술
    e = {}
    for a in ARM_NAMES:
        dg = {x["rebal"]: x for x in hold[a][1]}
        mgr = [dg[m]["managers"] for m in reb_w if m in dg]
        k2 = [len([k for k in union_mapped(Wd, m) if counts[a].get(m, {}).get(k, 0) >= K]) for m in reb_w]
        e[a] = {"managers_min": int(min(mgr)) if mgr else 0, "managers_max": int(max(mgr)) if mgr else 0,
                "basket_min": int(min(k2)) if k2 else 0, "basket_med": int(np.median(k2)) if k2 else 0, "basket_max": int(max(k2)) if k2 else 0,
                "n_forms_ge10_frac": float(np.mean([x >= F0E_MIN_NAMES for x in k2])) if k2 else 0.0,
                "ok": bool(mgr and min(mgr) >= F0E_MIN_MGR and k2 and np.mean([x >= F0E_MIN_NAMES for x in k2]) >= F0E_FRAC)}
    out["f0e"] = e
    # F0-f 옛 CUSIP 관문 — 명단 전원(퀀트 포함) 아무도 안 든 시점정확 멤버(13F 분기말에 있던 증권만)
    out["f0f"] = nobody_gate(Wd, G, months, P, mi, reb_w)
    # 멈춤 조건 앞당김(굽기 자식의 등록된 멈춤이 표식 뒤에 터지지 않게) — 측정 창 · 대체 창 둘 다
    out["stops"] = stop_prechecks(Wd, rows, reb_all, counts)
    # 구성 서술(수익 없음) — C 의 K≥2 가운데 브리지워터가 든 몫 · «브리지워터 + 한 곳» 몫 · VG 의 K≥2 가운데 «매버릭 또는 베일리 기포드 + 한 곳» 몫
    nb = nbw = nbw1 = nv = nvmb = 0
    bw, mav, bg = str(BRIDGEWATER), str(MAVERICK), str(BAILLIE)
    for m in reb_w:
        uni = set(union_mapped(Wd, m))
        for t, cs in (hold["C"][0].get(m) or {}).items():
            if t in uni and len(cs) >= K:
                nb += 1
                nbw += bw in cs
                nbw1 += (bw in cs and len(cs) == 2)
        for t, cs in (hold["VG"][0].get(m) or {}).items():
            if t in uni and len(cs) >= K:
                nv += 1
                nvmb += (len(cs) == 2 and (mav in cs or bg in cs))
    out["composition"] = {"c_k2_bw_frac": nbw / nb if nb else None, "c_k2_bw_plus_one_frac": nbw1 / nb if nb else None,
                          "vg_k2_mav_bg_plus_one_frac": nvmb / nv if nv else None, "n_c_k2_pooled": nb, "n_vg_k2_pooled": nv}
    out["ok"] = bool(out["arms"]["ok"] and out["f0c"]["ok"] and d["ok"] and out["window"]["ok"] and out["f0f"]["ok"] and out["stops"]["ok"])
    return out


def first_price_dates(Wd, keys):
    import numpy as np
    out = {}
    for k in keys:
        a = Wd["PX"].get(k)
        ok = np.where(a == a)[0] if a is not None else []
        out[k] = Wd["dates"][int(ok[0])] if len(ok) else "9999-99-99"
    return out


def nobody_gate(Wd, G, months, P, mi, reb_w, max_spx=None, max_union=None):
    """F0-f — 체결월마다 시점정확 S&P 500 ∪ NASDAQ 100 멤버(이중클래스 하나 · 가격 키 ∈ 오늘 유니버스 · 그날 가격 · 키의 첫 가격 ≤ 13F 분기말)
    가운데 이력의 CIK 전부(퀀트 포함)가 아무도 안 든 종목 수. 옛 CUSIP 지도가 빠지면 이 수가 커진다(수선 전 최대 38 · S&P 500 35)."""
    import pit_panel as PP
    from guru17_backtest import add_months, month_end
    max_spx = F0F_MAX_SPX if max_spx is None else max_spx
    max_union = F0F_MAX_UNION if max_union is None else max_union
    allc = set()
    for q, h in G["holdings"].items():
        allc |= set(h)
    H, _d = arm_holders(G, mi, P, months, frozenset(allc))
    fp = first_price_dates(Wd, Wd["today"])
    per, worst = [], {"union": (0, None, []), "spx": (0, None, [])}
    for rm in reb_w:
        i = Wd["me"][rm]
        qend = month_end(add_months(rm, -LAG_Q))
        mem, _n = PP.union_members(Wd, rm, i)
        spx = set(Wd["lists"]["spx"].get(rm) or [])
        hold = H.get(rm) or {}
        nob = []
        for t, k in mem:
            if k not in Wd["today"]:
                continue
            p = Wd["PX"][k][i]
            if not (p == p and p > 0) or fp.get(k, "9999") > qend:
                continue
            if not hold.get(k):
                nob.append((t, k, t in spx))
        ns, nu = sum(1 for x in nob if x[2]), len(nob)
        per.append((rm, ns, nu))
        if nu > worst["union"][0]:
            worst["union"] = (nu, rm, sorted(x[1] for x in nob))
        if ns > worst["spx"][0]:
            worst["spx"] = (ns, rm, sorted(x[1] for x in nob if x[2]))
    mx_s = max((x[1] for x in per), default=0)
    mx_u = max((x[2] for x in per), default=0)
    return {"n_forms": len(per), "max_spx": int(mx_s), "max_union": int(mx_u), "total_union": int(sum(x[2] for x in per)),
            "total_spx": int(sum(x[1] for x in per)), "limit_spx": int(max_spx), "limit_union": int(max_union),
            "worst_union": {"n": worst["union"][0], "form": worst["union"][1], "keys": worst["union"][2]},
            "worst_spx": {"n": worst["spx"][0], "form": worst["spx"][1], "keys": worst["spx"][2]},
            "ok": bool(per and mx_s <= max_spx and mx_u <= max_union)}


def stop_prechecks(Wd, rows, reb_all, counts):
    """등록된 멈춤 조건을 표식 전에 — 측정 창 · 대체 창(F0-a 실패 때) 둘 다: S1 행이 창 시작 · 끝과 맞고 이어진다 ·
    S2 첫 체결월 = 창 시작 전달 · 첫 체결의 종목 수 ≥ MIN_HOLD(팔 셋 · 대조 U). 개수 · 참/거짓만."""
    out, ok = {}, True
    for nm, w in (("win", WIN), ("pub", PUB)):
        j0 = next((k for k, x in enumerate(rows) if x["m"] >= w[0]), None)
        rw = rows[j0:] if j0 is not None else []
        s1 = bool(rw and rw[0]["m"] == w[0] and rw[-1]["m"] == w[1] and all(rw[q]["m"] == mshift(rw[q - 1]["m"], 1) for q in range(1, len(rw))))
        rb = [m for m in reb_all if mshift(w[0], -1) <= m <= mshift(w[1], -1)]
        first = rb[0] if rb else None
        s2_first = bool(first == mshift(w[0], -1))
        n_first = {}
        if first:
            uni = union_mapped(Wd, first)
            n_first = {a: len([k for k in uni if counts[a].get(first, {}).get(k, 0) >= K]) for a in ARM_NAMES}
            n_first["U"] = len(uni)
        names_ok = bool(n_first and all(v >= MIN_HOLD for v in n_first.values()))
        out[nm] = {"window": list(w), "s1_rows_ok": s1, "s2_first_form": first, "s2_first_ok": s2_first, "first_form_names": n_first,
                   "first_form_names_ok": names_ok}
        ok &= bool(s1 and s2_first and names_ok)
    out["ok"] = bool(ok)
    return out


def main_child():
    """🚨 굽기 본체(수익) — 러너의 한 번 굽기 · 눈가린 연기에서만. 돌려주는 것 dict(전부 · 캐시 전용).
    등록된 멈춤 조건 · 결정적 자기 점검(StopBake)은 {"stopped": 사유} 로 돌려준다 — 러너가 멈춤 기록 · 결과 문서를 쓴다(다시 굽기 없음)."""
    try:
        return _main_body()
    except StopBake as e:
        return {"kind": "gfund_out", "stopped": str(e)[:300]}


def _main_body():
    import numpy as np
    import idxrev as IR
    import pit_panel as PP
    t0 = __import__("time").time()
    G_, months, P, mi = load_history()
    A = arm_sets()
    counts = {a: arm_counts(G_, mi, P, months, A[a])[0] for a in ARM_NAMES}
    Wd = PP.load_world()
    today = Wd["today"]
    Gd = make_grid(Wd)
    ffm = ff_monthly(Wd, _json(os.path.join(DATA, "ff_daily.json")))
    rows_b, _cover = s1_base_rows(Wd, "spx", SIG, WIN[1])
    # F0-a 패널 관문(벤치 대 S&P 500 PR · 측정 창) — 실패하면 대체 창(공개 창)으로(자료 품질로만)
    pr = {}
    for m in months_between(WIN[0], WIN[1]):
        a, b = Gd.me.get(mshift(m, -1)), Gd.me.get(m)
        if a is not None and b is not None:
            pr[m] = (Gd.IX_PR[b] / Gd.IX_PR[a] - 1) * 100
    f0a_ok, f0a_corr, f0a_gap = PP.f0_gate(rows_b, {"S&P 500": pr}, "S&P 500", WIN)
    win = WIN if f0a_ok else PUB
    j0 = next(k for k, x in enumerate(rows_b) if x["m"] >= win[0])
    if rows_b[j0]["m"] != win[0] or rows_b[-1]["m"] != win[1]:
        raise StopBake("S1 행이 창과 맞지 않는다")
    forms_m = [x["sig"] for x in rows_b[j0:]]
    R = {"kind": "gfund_out", "window_used": list(win), "fallback": bool(not f0a_ok),
         "f0a": {"ok": bool(f0a_ok), "corr": f0a_corr, "gap_pm": f0a_gap, "window": list(WIN)},
         "cells": {a: {} for a in ARM_NAMES}, "controls": {}, "series": {}, "native": {}}
    frs = {a: {} for a in ARM_NAMES}
    # ── S1 ────────────────────────────────────────────────────────────────
    for a in ARM_NAMES:
        rows = attach_z(rows_b, counts[a], today)
        o, b, _a, _lw, mult, sat = IR.solve(rows, j0, "rev", CAP_MODE, TE, False)
        op, _b2, _a2, _lw2, _m2, _s2 = IR.solve(rows, j0, "rev", CAP_MODE, TE, True)
        books = tilt_weights(rows, j0, TE, mult)
        dev = max(max(abs(x["p"] - y["p"]), abs(x["b"] - y["b"]), abs(x["cost"] - y["cost"])) for x, y in zip(books, o))
        if len(books) != len(o) or dev > 1e-12:
            raise StopBake("tilt_weights 가 idxrev.run 과 다르다")
        path = weights_path(Wd, rows, j0, books)
        fr = fund(Gd, path, forms_m)
        frs[a]["S1"] = fr
        nat_full, nat_pub = native_s1(o), native_s1(o, PUB[0])
        pl_full, pl_pub = native_s1(op), native_s1(op, PUB[0])
        nat_full.update({"placebo_ir": pl_full["ir"], "lam_mult": mult, "saturated": bool(sat), "bind": 100 * b[0] / max(1, b[1])})
        nat_pub.update({"placebo_ir": pl_pub["ir"]})
        R["native"][a] = {"full": nat_full, "pub": nat_pub}
        cov_g = [x["cov"]["guru"] for x in rows[j0:]]
        R["native"][a]["mapped_w_min"], R["native"][a]["mapped_w_med"] = float(min(cov_g)), float(np.median(cov_g))
        del rows
    # B0 — 패널 시총가중 S&P 500(틸트 없음 · 비용 0)
    b0_books = [{"w": dict(x["wb"]), "cost": 0.0} for x in rows_b[j0:]]
    frs_b0 = fund(Gd, weights_path(Wd, rows_b, j0, b0_books), forms_m)
    # ── S2 · U ───────────────────────────────────────────────────────────
    reb_all = sorted(counts["C"])
    reb_w = [m for m in reb_all if mshift(win[0], -1) <= m <= mshift(win[1], -1)]
    if reb_w[0] != mshift(win[0], -1):
        raise StopBake("S2 첫 체결월이 창 시작 전달이 아니다")
    s2_meta = {}
    for a in ARM_NAMES:
        tg = basket_targets(Wd, reb_w, counts[a])
        bp = basket_path(Wd, reb_w, tg, win[1])
        frs[a]["S2"] = fund(Gd, bp["path"], forms_m, bp["turn"])
        nn = [x for x in bp["n_names"] if x is not None]
        s2_meta[a] = {"n_forms": len(reb_w), "n_skipped": len(bp["skipped"]), "names_min": int(min(nn)), "names_med": int(np.median(nn)),
                      "names_max": int(max(nn)), "turn": bp["turn"]}
    bu = basket_path(Wd, reb_w, basket_targets(Wd, reb_w, None), win[1])
    frs_u = fund(Gd, bu["path"], forms_m, bu["turn"])
    R["s2_meta"] = s2_meta
    # ── 지표 ─────────────────────────────────────────────────────────────
    def both(fr):
        return {"full": metrics(Gd, fr, ffm), "pub": metrics(Gd, sub_fr(Gd, fr, PUB[0]), ffm)}
    for a in ARM_NAMES:
        for s in SIGNALS:
            R["cells"][a][s] = both(frs[a][s])
            R["series"]["%s|%s" % (a, s)] = {"hold": frs[a][s]["hold"], "ex": [float(v) for v in frs[a][s]["ex"]],
                                             "basket": [float(v) for v in frs[a][s]["basket"]], "index": [float(v) for v in frs[a][s]["index"]]}
    R["controls"]["B0"] = both(frs_b0)
    R["controls"]["U"] = both(frs_u)
    R["controls"]["U"]["meta"] = {"names_min": int(min(x for x in bu["n_names"] if x)), "names_med": int(np.median([x for x in bu["n_names"] if x])),
                                  "names_max": int(max(x for x in bu["n_names"] if x)), "turn": bu["turn"]}
    for c, fr in (("B0", frs_b0), ("U", frs_u)):
        R["series"]["%s" % c] = {"hold": fr["hold"], "ex": [float(v) for v in fr["ex"]]}
    # 차이
    R["diffs"] = {"VG-C": {}, "C-BW-C": {}}
    R["ctrl_diffs"] = {a: {} for a in ARM_NAMES}
    for s in SIGNALS:
        for nm, x in (("VG-C", "VG"), ("C-BW-C", "C-BW")):
            R["diffs"][nm][s] = {"full": diff_stats(Gd, frs[x][s], frs["C"][s], ffm),
                                 "pub": diff_stats(Gd, sub_fr(Gd, frs[x][s], PUB[0]), sub_fr(Gd, frs["C"][s], PUB[0]), ffm)}
        for a in ARM_NAMES:
            ctrl = frs_u if s == "S2" else frs_b0
            R["ctrl_diffs"][a][s] = {"full": diff_stats(Gd, frs[a][s], ctrl, ffm),
                                     "pub": diff_stats(Gd, sub_fr(Gd, frs[a][s], PUB[0]), sub_fr(Gd, ctrl, PUB[0]), ffm)}
    # 후속 등록 후보(주 팔 VG 칸만 — 비교 팔은 같은 규칙으로 서술만)
    R["candidates"] = {}
    R["candidates_compare"] = {a: {} for a in ARM_NAMES if a != PRIMARY}
    for s in SIGNALS:
        for a in ARM_NAMES:
            c = candidate(R["cells"][a][s]["full"], R["cells"][a][s]["pub"], R["native"][a]["full"], R["ctrl_diffs"][a][s]["full"], s)
            if a == PRIMARY:
                R["candidates"][s] = c
            else:
                R["candidates_compare"][a][s] = c
    # EG30 V0 참고 줄(얼린 _qbatch.json V0 · 10년 — 입력이 아니다)
    Q = _json(os.path.join(DATA, "_qbatch.json"))["V0"]
    v0ex = np.asarray(Q["ex"], float)
    ref = {"hold": [Q["hold"][0], Q["hold"][-1]], "window": [Q["hold"][0], Q["hold"][-1]],
           "frozen_eval": {k: Q["eval"].get(k) for k in ("ann_ex", "te", "ir", "nw_t", "win", "years_won", "n_years", "down_mean", "down_win",
                                                          "crash_won", "surge_won", "sleeve_beta")}, "corr_fund_ex": {}}
    for a in ARM_NAMES:
        for s in SIGNALS:
            fp_ = sub_fr(Gd, frs[a][s], PUB[0])
            if list(fp_["hold"]) == list(Q["hold"]):
                ref["corr_fund_ex"]["%s|%s" % (a, s)] = float(np.corrcoef(np.asarray(fp_["ex"], float), v0ex)[0, 1])
            else:
                ref["corr_fund_ex"]["%s|%s" % (a, s)] = None
    R["eg30_ref"] = ref
    R["predictions"] = predictions(R)
    R["multiplicity"] = {"m_confirmatory": 0, "cum_n_before": CUM_N_BEFORE, "rows_counted": N_ROWS_COUNTED, "cum_n_after": CUM_N_BEFORE + N_ROWS_COUNTED}
    R["sec"] = round(__import__("time").time() - t0, 1)
    return R


def child_main(argv):
    """러너가 부른다: python -X utf8 <뿌리>/build/g_fund.py --child f0b|f0|main --out <경로>."""
    mode = argv[argv.index("--child") + 1]
    outp = argv[argv.index("--out") + 1]
    import warnings
    warnings.simplefilter("ignore")
    if mode == "f0b":
        res = f0b_child(outp + ".guru_cmp.tmp.json")
    elif mode == "f0":
        res = f0_child()
    elif mode == "main":
        import numpy as np
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            res = main_child()
    else:
        raise SystemExit("모르는 자식 방식: %s" % mode)
    _wjson(outp, _clean(res))
    return 0


def _clean(o, depth=0):
    """JSON 으로(NaN · inf → None · numpy → 파이썬 · 튜플 → 목록 · 집합 → 정렬 목록)."""
    if depth > 60:
        return str(o)
    if o is None or isinstance(o, (str, bool)):
        return o
    if isinstance(o, int):
        return int(o)
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    try:
        import numpy as np
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            f = float(o)
            return f if math.isfinite(f) else None
        if isinstance(o, np.ndarray):
            return _clean(o.tolist(), depth + 1)
    except Exception:                                        # noqa: BLE001
        pass
    if isinstance(o, dict):
        return {str(k): _clean(v, depth + 1) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v, depth + 1) for v in o]
    if isinstance(o, (set, frozenset)):
        return sorted(_clean(v, depth + 1) for v in o)
    return str(o)


if __name__ == "__main__":
    if "--child" in sys.argv:
        sys.exit(child_main(sys.argv))
    print(__doc__)
