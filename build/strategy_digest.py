# -*- coding: utf-8 -*-
"""탐색 풀 118장의 «팀 공유용 정리» → data/strategy_digest.json

카드마다 넷을 낸다(사용자 요청 2026-09-07):
  ① 논문 내용·결과 요약        — 카드의 principle / performance / sources
  ② S&P 500 · NASDAQ 100 적용 결과 — 이 랩의 실측(PIT·소급·부풀림·회전…)
  ③ 잘 통한 국면 / 안 통한 국면   — 랩이 이미 재는 국면별 성적 · 연도별 초과
  ④ 활용 방안                 — **측정값에서 규칙으로** 뽑는다(§USE_RULES)

🚨 **문장을 카드마다 손으로 쓰지 않는다.** 118장을 손으로 쓰면 다음 갱신에 전부 거짓말이
  된다 — 이 저장소가 되풀이 밟는 결함 ②(손으로 적은 수가 낡음)가 정확히 그것이다.
  여기서 손으로 두는 것은 **카드 ↔ 규칙 이음표(LINK)** 하나뿐이고, 그것도 아래 검사가
  «없는 sid» 와 «이어졌는데 랩에 없는 규칙» 을 잡는다.

🚨 **못 잰 카드에 ②③④를 지어내지 않는다.** 118장 중 랩이 실제로 잰 것은 45장이고
  나머지는 원문이 수를 안 적었거나(underspec) 랩에 자료가 없다(no_input).
  그 카드의 답은 «왜 못 쟀나» 이고, 그 사유는 data/pool_triage.json 에 규칙별로 있다.
"""
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "strategy_digest.json")

# ── 카드 ↔ 랩 규칙 이음표 ───────────────────────────────────────────────────
# 🚨 저장소에 기계적인 이음이 없다(2026-09-07 확인) — 카드의 lab.t 는 사람이 쓴 아카이브
#   이름이고 archive_index 의 aka 는 대부분 한글 슬러그다. 그래서 여기 손으로 둔다.
#   ⚠ 손 표이므로 **검사가 붙는다**: ① 여기 적은 sid 가 실제로 랩에 있나
#     ② 그 sid 가 그 카드를 실제로 구현한 것인가(판정 문서·규칙문으로 사람이 확인)
#   ⚠ 사용자 요청대로 **카드를 하나씩 확인하며** 채운다. 빈 카드는 «아직 안 이었다» 로
#     화면에 그대로 나오고, 지어낸 문장으로 덮지 않는다.
LINK: dict = {
    # 2026-09-07 선언 규약(풀카드:/규칙:)이 붙은 문서에서 기계로 확인한 것들
    "A15": ["x-cgate", "x-cgate-mom"],
    "A16": ["x-demega10"],
    "A17": ["x-secew", "x-secew-gate"],
    "A22": ["x-residind-n52"],
    "E55": ["x-pdelay", "x-pdelay-cw", "x-illiqls"],
    "A7": ["a7-fidelity", "a7-conover"],
    "A2": ["a2-factor-rot"],
}

# ── ④ 활용 방안을 «측정값에서» 뽑는 규칙 ────────────────────────────────────
# 🚨 카드마다 문장을 지어내면 그것이 곧 근거 없는 소리다. 그래서 아래 규칙만 쓰고,
#   화면에 이 규칙표를 그대로 싣는다(읽는 사람이 판단 근거를 볼 수 있게).
USE_RULES = [
    {"if": "게시 중", "then": "이 랩이 매일 갱신하며 화면에 싣는 규칙이다."},
    {"if": "PIT 레그가 완전", "then": "생존편향을 걷고도 남은 성적이다 — 그렇지 않은 것과 같은 표에서 비교하지 말 것."},
    {"if": "부풀림 ≤ 랩 중앙값", "then": "백테스트가 «오늘 살아남은 종목» 에 덜 기댔다."},
    {"if": "부풀림 > 랩 중앙값의 1.5배", "then": "겉보기 우위의 상당 부분이 생존편향이다 — 실전에서 그만큼 깎인다고 볼 것."},
    {"if": "회전율 ≤ 2회/년", "then": "개인 계좌로도 굴릴 만하다."},
    {"if": "회전율 > 4회/년", "then": "비용·세금·손이 크게 든다 — 기관 실행을 전제로 읽을 것."},
    {"if": "바스켓 < 30종", "then": "단일 종목 위험이 크다. 한 종목이 반 토막 나면 포트폴리오가 그 비중만큼 빠진다."},
    {"if": "비용에 죽는다(cost_kill)", "then": "종이 위에서만 되는 규칙이다."},
    {"if": "t < 잡음 문턱", "then": "이 랩의 다중검정 진단이 말하는 잡음 분포 안쪽이다 — «이긴다» 로 읽지 말 것."},
]


def _load(fn, default=None):
    try:
        return json.load(io.open(os.path.join(DATA, fn), encoding="utf-8"))
    except FileNotFoundError:
        return default if default is not None else {}


def _num(x, nd=3):
    return None if x is None else round(x, nd)


def main():
    pool = _load("rotation_pool.json")
    triage = _load("pool_triage.json")
    tech = _load("tech_strategies.json")
    pit = _load("pit_strategies.json")
    idx = _load("strategy_index.json")
    asset = _load("asset_strategies.json")
    rc = _load("reality_check.json")
    led = json.load(io.open(os.path.join(HERE, "tested_not_published.json"),
                            encoding="utf-8")).get("items") or []

    T = {s["sid"]: s for s in (tech.get("strategies") or [])}
    P = {s["sid"]: s for s in (pit.get("strategies") or [])}
    A = {s["sid"]: s for s in (asset.get("strategies") or [])}
    I = {}
    for x in (idx.get("items") or []):
        I[x["sid"]] = x
        if x["sid"].startswith("t-"):
            I[x["sid"][2:]] = x
        if x["sid"].startswith("a-"):
            I[x["sid"][2:]] = x
    L = {r.get("sid"): r for r in led if r.get("sid")}

    # 랩 부풀림 중앙값 — 손으로 안 적는다
    bs = sorted(s["bias_sharpe"] for s in (pit.get("strategies") or [])
                if s.get("bias_sharpe") is not None)
    bias_med = bs[len(bs) // 2] if bs else None
    noise = ((rc.get("primary") or {}).get("null_max_t") or {}).get("median")

    cards, unknown = [], []
    for c in (pool.get("strategies") or []):
        cid = c.get("id")
        tri = ((triage.get("cards") or {}).get(cid) or {})
        lab = c.get("lab") or {}
        sids = LINK.get(cid) or []
        rules = []
        for sid in sids:
            t, p, a = T.get(sid), P.get(sid), A.get(sid)
            if not (t or p or a):
                # 🚨 엔진에서 내린 규칙(기각·은퇴)은 tech/pit 에 없다. 그것을 «없는 sid» 로
                #   보면 이 랩이 판정한 사실 자체가 화면에서 사라진다 — 원장이 그 기록을
                #   갖고 있으므로 거기서 읽는다. 원장에도 없으면 그때가 진짜 오타다.
                if sid not in L:
                    unknown.append((cid, sid))
                    continue
                r0 = L[sid]
                rules.append({
                    "sid": sid, "name": r0.get("name") or sid,
                    "rule": None, "why": r0.get("why"),
                    "published": False, "retired": True,
                    "ledger_gate": r0.get("gate"), "ledger_t": r0.get("t"),
                    "ledger_when": r0.get("when"), "ledger_src": r0.get("src"),
                    "engine": False,
                    "use": ["엔진에서 내렸다(%s) — 정의와 수치는 원장과 판정 문서에 남는다."
                            % (r0.get("gate") or "판정 미상")],
                })
                continue
            src = t or a or {}
            row = {
                "sid": sid, "name": src.get("name"),
                "rule": src.get("rule"), "why": src.get("why"),
                "published": bool(I.get(sid) or I.get("t-" + sid) or I.get("a-" + sid)),
                "retired": (sid in L),
                "ledger_gate": (L.get(sid) or {}).get("gate"),
            }
            if p:
                row["pit"] = {"cagr": (p.get("metrics") or {}).get("cagr"),
                              "sharpe": (p.get("metrics") or {}).get("sharpe"),
                              "mdd": (p.get("metrics") or {}).get("mdd"),
                              "bench_sharpe": (p.get("bench") or {}).get("sharpe"),
                              "t": p.get("t"), "kind": p.get("pit_kind"),
                              "bias_sharpe": p.get("bias_sharpe"),
                              "n_months": len((p.get("chart") or {}).get("monthly") or [])}
                row["yearly"] = _yearly(p)
            if src:
                row["retro"] = {"cagr": (src.get("metrics") or {}).get("cagr"),
                                "sharpe": (src.get("metrics") or {}).get("sharpe"),
                                "mdd": (src.get("metrics") or {}).get("mdd")}
                row["turnover"] = src.get("turnover")
                row["cost_kill"] = src.get("cost_kill")
                row["basket"] = (src.get("bask") or {}).get("avg")
            ix = I.get(sid) or I.get("t-" + sid) or I.get("a-" + sid) or {}
            row["regime"] = ix.get("rg")
            row["winrate"] = (ix.get("winrate") or {}).get("win") if isinstance(
                ix.get("winrate"), dict) else ix.get("winrate")
            row["use"] = _use(row, bias_med, noise)
            rules.append(row)

        cards.append({
            "id": cid, "cat": c.get("cat"), "cat_label": c.get("cat_label"),
            "name": c.get("name"), "type": c.get("type"),
            # ① 논문 — 카드가 가진 것을 그대로 옮긴다(요약을 지어내지 않는다)
            "paper": {"purpose": c.get("purpose"), "principle": c.get("principle"),
                      "entry": c.get("entry"), "performance": c.get("performance"),
                      "recent": c.get("recent"), "recent_at": c.get("recent_at"),
                      "sources": c.get("sources") or []},
            # ② 랩 결과
            "lab": {"verdict": lab.get("v"), "title": lab.get("t"),
                    "why": lab.get("why"), "docs": lab.get("docs") or []},
            "rules": rules,
            "linked": bool(rules),
            "triage": {"bucket": tri.get("verdict"), "why": tri.get("why")},
        })

    doc = {
        "note": ("탐색 풀 카드의 팀 공유용 정리. 카드마다 ①논문 ②랩 적용 결과 ③통한 국면 "
                 "④활용 방안. 🚨 문장을 카드마다 손으로 쓰지 않는다 — 자료에서 생성한다."),
        "caveat": ("🚨 랩이 실제로 잰 카드는 일부다. 나머지는 원문이 수를 안 적었거나 랩에 "
                   "자료가 없다 — 그 카드의 답은 «왜 못 쟀나» 이고 ②③④를 지어내지 않는다."),
        "as_of": pool.get("generated") or tech.get("as_of"),
        "bias_median": bias_med, "noise_max_t_median": noise,
        "use_rules": USE_RULES,
        "n_cards": len(cards),
        "n_linked": sum(1 for c in cards if c["linked"]),
        "counts": triage.get("counts"),
        "link_note": ("카드 ↔ 규칙 이음은 build/strategy_digest.py 의 LINK 손 표다 — "
                      "저장소에 기계적인 이음이 없다(카드의 lab.t 는 사람이 쓴 이름이고 "
                      "archive_index 의 aka 는 대부분 한글 슬러그다). 한 장씩 확인하며 채운다."),
        "cards": cards,
    }
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("→ %s" % OUT)
    print("  카드 %d장 · 규칙을 이은 것 %d장 · 부풀림 중앙값 %s · 잡음 최고 t 중앙 %s"
          % (len(cards), doc["n_linked"], bias_med, noise))
    if unknown:
        raise SystemExit("🚨 LINK 에 랩에 없는 sid 가 있다: %s" % unknown)
    return 0


def _yearly(p):
    """연도별 전략·지수 수익(%) — ③이 쓴다."""
    out = {}
    for m in ((p.get("chart") or {}).get("monthly") or []):
        if m.get("r") is None:
            continue
        y = m["m"][:4]
        a, b = out.setdefault(y, [1.0, 1.0])
        out[y][0] = a * (1 + m["r"] / 100)
        ix = (m.get("i") or {}).get("S&P 500")
        if ix is not None:
            out[y][1] = b * (1 + ix / 100)
    return {y: {"strat": round((v[0] - 1) * 100, 1),
                "spx": round((v[1] - 1) * 100, 1),
                "diff": round(((v[0] - 1) - (v[1] - 1)) * 100, 1)}
            for y, v in sorted(out.items())}


def _use(row, bias_med, noise):
    """④ — 측정값에서 규칙으로 뽑는다. 문장을 지어내지 않는다."""
    out = []
    if row.get("published"):
        out.append("게시 중 — 이 랩이 매일 갱신하며 화면에 싣는다.")
    elif row.get("ledger_gate"):
        out.append("게시하지 않음(%s) — 정의와 수치는 원장에 남는다." % row["ledger_gate"])
    p = row.get("pit") or {}
    if p.get("kind") == "full":
        out.append("시점정확 레그가 완전하다 — 생존편향을 걷고도 남은 성적이다.")
    elif p.get("kind") == "partial":
        out.append("부분 시점정확이다 — 선견만 걷었고 편출 종목은 여전히 빠져 있다.")
    b = p.get("bias_sharpe")
    if b is not None and bias_med:
        if b > bias_med * 1.5:
            out.append("부풀림 %.3f — 랩 중앙값(%.3f)의 %.1f배다. 겉보기 우위의 상당 부분이 "
                       "생존편향이라 실전에서 그만큼 깎인다고 볼 것." % (b, bias_med, b / bias_med))
        elif b <= bias_med:
            out.append("부풀림 %.3f — 랩 중앙값(%.3f) 이하다. 백테스트가 «오늘 살아남은 "
                       "종목» 에 덜 기댔다." % (b, bias_med))
    tv = row.get("turnover")
    if tv is not None:
        if tv <= 2:
            out.append("회전 %.2f회/년 — 개인 계좌로도 굴릴 만하다." % tv)
        elif tv > 4:
            out.append("회전 %.2f회/년 — 비용·세금·손이 크게 든다. 기관 실행 전제로 읽을 것." % tv)
    bk = row.get("basket")
    if bk is not None and bk < 30:
        out.append("바스켓 %.0f종 — 단일 종목 위험이 크다." % bk)
    if row.get("cost_kill"):
        out.append("🚨 비용을 물리면 우위가 사라진다 — 종이 위에서만 되는 규칙이다.")
    t = p.get("t")
    if t is not None and noise:
        if abs(t) < noise:
            out.append("t %.2f — 이 랩의 다중검정 진단이 말하는 잡음 분포(최고 t 중앙 %.2f) "
                       "안쪽이다. «이긴다» 로 읽지 말 것." % (t, noise))
    return out


if __name__ == "__main__":
    sys.exit(main())
