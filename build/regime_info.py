# -*- coding: utf-8 -*-
"""A7 국면의 **정보성** 측정 → data/regime_info.json

규약: build/PREREG-2026-09-07-REGIME0.md — **계산 전 커밋 72e2c70d**.

🚨 **전략이 아니다.** 이 랩은 A7 에 탈것을 넷 세웠고 넷 다 죽었는데, 넷 다 «국면 라벨이
  섹터에 대해 정보를 갖는다» 는 전제를 안 재고 그 위에 세운 것이다. 이 파일은 그 전제만 잰다.

🚨 국면을 **개정 없는 계열로만** 만든다 — 지금까지 판이 공유한 결함이 «오늘의 개정 시계열로
  국면을 사후에 매긴다» 였다. 아래 셋은 시장가격·정책 공표값이라 사후에 안 바뀐다.
"""
import io
import json
import os
import random
import statistics as st
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
OUT = os.path.join(DATA, "regime_info.json")

SEC = ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
MKT = "SPY"
HYST = 2          # 히스테리시스 2개월 연속 확인(a7-fidelity 와 같은 규약 — 새 값이 아니다)
BLOCK_M = 3       # 블록 부트스트랩 블록 길이(랩 규약 = 한 분기)
REPS = 1000       # 등록 §3③
SEED = 20260907
MIN_M = 12        # F1 — 국면 관측이 이보다 적으면 그 국면 수치를 안 싣는다
MIN_STATES = 4    # F2 — 관측 12개월 이상인 국면이 이보다 적으면 측정 불가
MIN_FLIPS = 6     # F4 — 전환이 이보다 적으면 측정 불가


def load():
    A = json.load(io.open(os.path.join(DATA, "assets.json"), encoding="utf-8"))
    return A["dates"], A["px"], A["macro"]


def month_ends(dates):
    out, prev = [], None
    for i, d in enumerate(dates):
        if prev is not None and d[:7] != prev[:7]:
            out.append(i - 1)
        prev = d
    out.append(len(dates) - 1)
    return out


def asof(series, d):
    """그 날짜 **이하**의 마지막 값. 일간 계열이라 키가 곧 관측일이다(선견 없음)."""
    best = None
    for k in sorted(series):
        if k <= d:
            best = series[k]
        else:
            break
    return best


def policy_dir(mac, days):
    """통화 축 — 마지막 정책금리 **변경의 방향**(Conover). 문턱이 없다.

    🚨 DFEDTAR(단일 목표 · ~2008-12)와 DFEDTARU(상단 · 2008-12~)를 이어 붙인다.
      유효금리(FEDFUNDS)로 «변경» 을 잡으면 문턱이 필요하고 그것이 자유도다 —
      목표금리는 계단이라 변화가 이산이고, 그래서 문턱이 필요 없다.
    """
    a = mac.get("DFEDTAR") or {}
    b = mac.get("DFEDTARU") or {}
    merged = {}
    merged.update(a)
    merged.update(b)          # 겹치는 날은 새 계열이 이긴다
    ks = sorted(merged)
    state, last, out = None, None, {}
    for k in ks:
        v = merged[k]
        if last is not None and v != last:
            state = "긴축" if v > last else "완화"
        if last is None or v != last:
            last = v
        out[k] = state
    return out, merged


def build_regime(dates, me, mac):
    """세 축의 조합 8가지 → {월키: 국면}. 히스테리시스 2개월."""
    pol, _ = policy_dir(mac, dates)
    dgs10, dgs3 = mac.get("DGS10") or {}, mac.get("DGS3MO") or {}
    baa = mac.get("BAA10Y") or {}
    baa_hist, raw = [], {}
    for i in me:
        d = dates[i]
        p = asof(pol, d)
        a, b = asof(dgs10, d), asof(dgs3, d)
        c = asof(baa, d)
        if p is None or a is None or b is None or c is None:
            continue
        # 성장 — 기간스프레드 부호(문턱 0. 역전의 정의가 0 이다)
        g = "정상" if (a - b) > 0 else "역전"
        # 신용 — 그 시점까지의 **확장 윈도우** 중앙값 대비(고정 임계치 금지)
        #   ⚠ 오늘 값을 넣기 **전에** 견준다. 넣고 재면 자기 자신과 비교하게 된다.
        cr = ("긴장" if (baa_hist and c > st.median(baa_hist)) else "완만")
        baa_hist.append(c)
        raw[d[:7]] = "%s·%s·%s" % (g, p, cr)
    # 히스테리시스 — 2개월 연속 같은 값일 때만 전환
    out, cur, run, prev = {}, None, 0, None
    for k in sorted(raw):
        v = raw[k]
        run = run + 1 if v == prev else 1
        prev = v
        if cur is None or (v != cur and run >= HYST):
            cur = v
        out[k] = cur
    return out, raw


def monthly_excess(dates, me, px):
    """섹터별 월 초과수익(vs SPY). {월키: {섹터: 초과}}"""
    out = {}
    for a, b in zip(me, me[1:]):
        k = dates[b][:7]
        m = px.get(MKT)
        if not m or not m[a] or not m[b]:
            continue
        rm = m[b] / m[a] - 1
        row = {}
        for t in SEC:
            s = px.get(t)
            if s and s[a] and s[b] and s[a] > 0:
                row[t] = (s[b] / s[a] - 1) - rm
        if len(row) >= 8:
            out[k] = row
    return out


def rank_of(vals):
    """평균 초과수익 → 섹터 순위(1 이 최상). 값이 없는 섹터는 빠진다."""
    xs = sorted(vals.items(), key=lambda kv: -kv[1])
    return {t: i + 1 for i, (t, _v) in enumerate(xs)}


def spearman(a, b):
    ks = sorted(set(a) & set(b))
    n = len(ks)
    if n < 4:
        return None
    x = [a[k] for k in ks]
    y = [b[k] for k in ks]
    mx, my = sum(x) / n, sum(y) / n
    num = sum((p - mx) * (q - my) for p, q in zip(x, y))
    dx = sum((p - mx) ** 2 for p in x) ** 0.5
    dy = sum((q - my) ** 2 for q in y) ** 0.5
    return (num / (dx * dy)) if dx and dy else None


def dispersion(labels, exc, months):
    """정보성 통계량 — 국면 간 섹터 **순위가 얼마나 다른가**.

    국면쌍 스피어만 상관의 평균을 낸 뒤 1 에서 뺀다(클수록 국면마다 리더가 다르다).
    ⚠ 관측 12개월 미만 국면은 뺀다(F1).
    """
    by = {}
    for m in months:
        g = labels.get(m)
        if g is None:
            continue
        by.setdefault(g, []).append(m)
    ok = {g: v for g, v in by.items() if len(v) >= MIN_M}
    if len(ok) < 2:
        return None, ok
    ranks = {}
    for g, ms in ok.items():
        acc = {}
        for m in ms:
            for t, v in exc[m].items():
                acc.setdefault(t, []).append(v)
        ranks[g] = rank_of({t: sum(v) / len(v) for t, v in acc.items() if len(v) >= 3})
    gs = sorted(ranks)
    cs = []
    for i in range(len(gs)):
        for j in range(i + 1, len(gs)):
            c = spearman(ranks[gs[i]], ranks[gs[j]])
            if c is not None:
                cs.append(c)
    if not cs:
        return None, ok
    return 1.0 - sum(cs) / len(cs), ok


def main():
    dates, px, mac = load()
    me = month_ends(dates)
    labels, raw = build_regime(dates, me, mac)
    exc = monthly_excess(dates, me, px)
    months = sorted(set(labels) & set(exc))
    if not months:
        raise SystemExit("겹치는 달이 없다.")

    flips, prev = 0, None
    for m in months:
        if labels[m] != prev:
            flips += 1 if prev is not None else 0
            prev = labels[m]
    cnt = {}
    for m in months:
        cnt[labels[m]] = cnt.get(labels[m], 0) + 1
    thick = {g: n for g, n in cnt.items() if n >= MIN_M}

    out = {
        "note": ("A7 국면의 **정보성** 측정 — 전략이 아니다. 국면 라벨이 섹터 수익에 대해 "
                 "정보를 갖는지만 묻는다(등록 §3)."),
        "prereg": "build/PREREG-2026-09-07-REGIME0.md (계산 전 커밋 72e2c70d)",
        "regime_note": ("🚨 국면을 **개정 없는 계열로만** 만들었다 — 기간스프레드(DGS10−DGS3MO) · "
                        "정책금리 방향(DFEDTAR+DFEDTARU) · 신용 스프레드(BAA10Y). 셋 다 시장가격· "
                        "정책 공표값이라 사후에 안 바뀐다. 종전 판(산업생산·실업률)은 오늘의 "
                        "개정본으로 국면을 사후에 매겼다."),
        "window": {"from": months[0], "to": months[-1], "n_months": len(months)},
        "states": dict(sorted(cnt.items(), key=lambda kv: -kv[1])),
        "states_thick": dict(sorted(thick.items(), key=lambda kv: -kv[1])),
        "flips": flips, "hysteresis_months": HYST,
        "block_months": BLOCK_M, "reps": REPS, "seed": SEED,
    }

    # ── F2 · F4 ─────────────────────────────────────────────────────────────
    fail = []
    if len(thick) < MIN_STATES:
        fail.append("관측 %d개월 이상인 국면이 %d개뿐이다(문턱 %d) — 8국면이 이름만 있다"
                    % (MIN_M, len(thick), MIN_STATES))
    if flips < MIN_FLIPS:
        fail.append("국면 전환이 %d회뿐이다(문턱 %d) — 조건이 안 바뀌면 조건을 잰 것이 아니다"
                    % (flips, MIN_FLIPS))
    if fail:
        out["verdict"] = "측정 불가"
        out["why"] = " · ".join(fail)
        _save(out, months, labels)
        return 0

    # ── 정보성 + 무작위 대조 ────────────────────────────────────────────────
    actual, ok = dispersion(labels, exc, months)
    if actual is None:
        out["verdict"] = "측정 불가"
        out["why"] = "국면쌍 순위 상관을 낼 수 없다(두꺼운 국면이 2개 미만)"
        _save(out, months, labels)
        return 0

    # 🚨 국면 라벨을 **블록 단위로** 섞는다 — 한 달씩 섞으면 국면의 지속성이 깨져
    #   «국면이 붙어 있다» 는 성질까지 같이 지워 버린다. 그러면 잡음이 실제보다 약해진다.
    rnd = random.Random(SEED)
    n = len(months)
    nb = (n + BLOCK_M - 1) // BLOCK_M
    null = []
    for _ in range(REPS):
        idx = []
        for _b in range(nb):
            s0 = rnd.randrange(n)
            idx.extend((s0 + k) % n for k in range(BLOCK_M))
        idx = idx[:n]
        shuf = {months[i]: labels[months[j]] for i, j in enumerate(idx)}
        v, _ = dispersion(shuf, exc, months)
        if v is not None:
            null.append(v)
    null.sort()
    pct = sum(1 for x in null if x < actual) / len(null) if null else None
    out["information"] = {
        "stat": round(actual, 4),
        "note": ("국면 간 섹터 **순위 차이** — 국면쌍 스피어만 상관의 평균을 1 에서 뺀 값. "
                 "클수록 국면마다 리더가 다르다. 0 에 가까우면 어느 국면이든 이긴 섹터가 같다."),
        "null_median": round(null[len(null) // 2], 4) if null else None,
        "null_p95": round(null[int(0.95 * len(null))], 4) if null else None,
        "pct_rank": round(pct, 4) if pct is not None else None,
        "n_null": len(null),
    }
    passed = (pct is not None and pct >= 0.95)
    out["verdict"] = "정보 있음" if passed else "기각 — 무작위와 구별되지 않는다"
    out["why"] = ("국면 라벨을 블록으로 섞은 %d회 분포에서 실측이 %.1f%% 지점에 선다. "
                  "등록 §4 F3 은 상위 5%% 를 요구했다 — %s."
                  % (len(null), (pct or 0) * 100,
                     "통과" if passed else "못 넘었으므로 로테이션을 만들지 않는다"))
    _save(out, months, labels)
    return 0


def _save(out, months, labels):
    out["labels"] = {m: labels[m] for m in months}
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("→ %s" % OUT)
    w = out["window"]
    print("  창 %s~%s · %d개월 · 전환 %d회" % (w["from"], w["to"], w["n_months"], out["flips"]))
    print("  국면 분포: %s" % json.dumps(out["states"], ensure_ascii=False))
    print("  관측 %d개월 이상: %d개" % (MIN_M, len(out.get("states_thick") or {})))
    inf = out.get("information")
    if inf:
        print("  정보성 %.4f · 무작위 중앙 %.4f · 95%% %.4f · 백분위 %.1f%%"
              % (inf["stat"], inf["null_median"], inf["null_p95"], (inf["pct_rank"] or 0) * 100))
    print("  🚨 %s — %s" % (out["verdict"], out["why"]))


if __name__ == "__main__":
    sys.exit(main())
