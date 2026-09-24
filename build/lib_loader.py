# -*- coding: utf-8 -*-
"""build/lib_loader.py — 랩 전략 라이브러리 → 결합(메타) 전략용 월 순수익 패널 · 유니버스 U_LIB

라이브러리 결합 배치 L(PREREG-2026-09-24-LIBMETA)의 공용 로더. 수익을 **읽어 정리**할 뿐 어떤 결합도 계산하지 않는다.

U_LIB(설계 워크플로 §0 · 구조만으로 정한다):
  · data/strategy_index.json 의 게시 항목 중 strategy_charts.json 에 월 계열이 있는 것
  · 뺀다: 지수 복제(^t-x-(n?cap)) · 등급 «판정 불가» · holds = 페어 · 이름·규칙에 «롱숏» · holds = 종목 이면서 basis ≠ pit(소급 종목 레그)
          · cost_drag 없음 · 다른 등록에 걸린 sid(PENDING)
  · 가족 하나로: 접미사(-band -n25 -n50 -n52 -n100 -n155 -sn -q -flat -disc -cont -base)를 되풀이해 떼어 같은 밑동끼리 묶고,
    가장 적게 뗀 것(같으면 sid 사전순)을 대표로.
월 수익: charts[sid].monthly 의 r(%) 을 달 키 'm' 으로(자리로 맞추지 않는다 · 'b' 는 쓰지 않는다) ·
  첫 달은 strategy_index.start 가 전달 마지막 거래일일 때만 남긴다 · 순수익 = r − cost_drag/12.
판정선: SPY 총수익(assets.json px.SPY 수정종가) 월말 수익(%) · 무위험 rf_monthly.json.
"""
from __future__ import annotations
import hashlib, io, json, os, re, subprocess, sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
SUF = ("-band", "-n25", "-n50", "-n52", "-n100", "-n155", "-sn", "-q", "-flat", "-disc", "-cont", "-base")
PENDING = {"t-x-cgate-mom", "t-x-guruacc", "p-lowcorr6"}


def _read(name, rev=None):
    """data/<name> — rev 가 있으면 그 커밋의 판(git show)을 읽는다. CI 가 매일 다시 굽는 파일을 얼린 판으로 읽기 위해서다."""
    if rev is None:
        return json.load(io.open(os.path.join(DATA, name), encoding="utf-8"))
    b = subprocess.run(["git", "-C", ROOT, "show", "%s:data/%s" % (rev, name)], capture_output=True, check=True).stdout
    return json.loads(b.decode("utf-8"))


def stem(sid):
    n, ch = 0, True
    while ch:
        ch = False
        for x in SUF:
            if sid.endswith(x):
                sid, ch, n = sid[:-len(x)], True, n + 1
    return sid, n


def _month_ends(dates, px):
    me = {}
    for d, p in zip(dates, px):
        if p is not None:
            me[d[:7]] = (d, p)
    return me


def spy_tr_monthly(rev=None):
    A = _read("assets.json", rev)
    out = {}
    for t in ("SPY", "RSP", "IVW", "IVE", "SPLV", "SPMO", "AGG", "QQQ"):
        me = _month_ends(A["dates"], A["px"][t])
        ms = sorted(me)
        out[t] = {ms[i]: (me[ms[i]][1] / me[ms[i - 1]][1] - 1) * 100 for i in range(1, len(ms))}
    return out, A["dates"]


def load(end="2026-08", rev=None):
    """→ {reps: [항목], panel: {sid: {m: 순수익 %}}, etf: {티커: {m: %}}, rf: {m: %}, excluded: {사유: n}, sha: {...}}
    rev — 자료 판 커밋(없으면 작업 트리)."""
    SI = _read("strategy_index.json", rev)
    CH = _read("strategy_charts.json", rev)["charts"]
    etf, adates = spy_tr_monthly(rev)
    trade_days = set(adates)
    why, keep = {}, []
    for it in SI["items"]:
        s = it["sid"]
        c = CH.get(s)
        reason = None
        if not c or not c.get("monthly"):
            reason = "월 계열 없음"
        elif re.match(r"^t-x-(n?cap)", s):
            reason = "지수 복제"
        elif it.get("grade") == "판정 불가":
            reason = "판정 불가"
        elif it.get("holds") == "페어":
            reason = "페어"
        elif "롱숏" in ((it.get("name") or "") + (it.get("rule") or "")):
            reason = "롱숏"
        elif it.get("holds") == "종목" and it.get("basis") != "pit":
            reason = "소급 종목 레그"
        elif it.get("cost_drag") is None:
            reason = "cost_drag 없음"
        elif s in PENDING:
            reason = "다른 등록 대기"
        if reason:
            why[reason] = why.get(reason, 0) + 1
            continue
        keep.append(it)
    fam = {}
    for it in keep:
        fam.setdefault(stem(it["sid"])[0], []).append(it)
    reps = sorted((sorted(v, key=lambda i: (stem(i["sid"])[1], i["sid"]))[0] for v in fam.values()), key=lambda i: i["sid"])
    panel = {}
    for it in reps:
        mo = [x for x in CH[it["sid"]]["monthly"] if x.get("r") is not None and x.get("m") and x["m"] <= end]
        if not mo:
            continue
        st = it.get("start") or ""
        # 첫 달: 시작일이 전달 마지막 거래일이면 온전한 달이다. 아니면 버린다.
        m0 = mo[0]["m"]
        y, mm = int(m0[:4]), int(m0[5:7])
        prev = "%04d-%02d" % (y - (mm == 1), 12 if mm == 1 else mm - 1)
        last_prev = max((d for d in trade_days if d[:7] == prev), default=None)
        if st != last_prev:
            mo = mo[1:]
        cd = float(it["cost_drag"]) / 12.0
        panel[it["sid"]] = {x["m"]: float(x["r"]) - cd for x in mo}
    rf = {m: float(v) * 100 for m, v in _read("rf_monthly.json", rev)["monthly"].items()}
    sid_list = "\n".join(sorted(panel))
    body = json.dumps({s: panel[s] for s in sorted(panel)}, sort_keys=True)
    return {"reps": [it for it in reps if it["sid"] in panel], "panel": panel, "etf": etf, "rf": rf, "excluded": why,
            "n_listed_series": len(keep), "sha": {"sids": hashlib.sha256(sid_list.encode()).hexdigest(),
                                                  "panel": hashlib.sha256(body.encode()).hexdigest()}}


if __name__ == "__main__":
    import collections
    L = load()
    print("U_LIB 계열 %d → 가족 %d · 제외 %s" % (L["n_listed_series"], len(L["reps"]), L["excluded"]))
    print("역할", dict(collections.Counter(i["role"] for i in L["reps"])), "· holds", dict(collections.Counter(i["holds"] for i in L["reps"])))
    ln = sorted(len(v) for v in L["panel"].values())
    print("월 수 중앙 %d · 최소 %d · 최대 %d" % (ln[len(ln) // 2], ln[0], ln[-1]))
    print("sid sha256 %s · panel sha256 %s" % (L["sha"]["sids"][:16], L["sha"]["panel"][:16]))
