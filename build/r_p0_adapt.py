# -*- coding: utf-8 -*-
"""build/r_p0_adapt.py — P0 계산기(build/r_p0.py)의 **자료 어댑터** 한 곳.

왜 따로 두나.
  P0 는 배치 R 의 새 자료(§A0 발행사 지도 · §A 내부자 PIT · §C 10-Q 위험요인)가 다 만들어지기 전에 짰다.
  그 파일들의 필드 이름·배치는 빌드가 끝나야 확정된다. 이름이 바뀔 때 고칠 곳을 **여기 FIELDS 한 곳**으로 모은다.
  r_p0.py 는 이 모듈이 돌려주는 세 가지만 안다.
    ① group_of(티커, 월) → 발행사 그룹 id · fpi 표지      (§A0 data/_issuer_map.json)
    ② flag_source(카드, 더미) → {"sets": {월: {그룹 id}}, "src", "defined": 원천이 정의한 달, "na": 표지 모름}
       (카운트 단계 전용 — 아래 방화벽 · flag_sets 는 (sets, src) 만 주는 얇은 판)
    ③ month_gate() → 달 관문(§F 가격 커버리지 ∩ §A0 지도 F0)을 넘은 신호월 목록 (없으면 None)

🚨 방화벽. P0 는 실제 플래그와 실제 수익의 관계를 어떤 식으로도 계산하지 않는다(그것은 등록 뒤 한 번 굽기다).
  그래서 플래그를 읽는 함수(flag_sets)는 «카운트 단계»(r_p0.py counts — 수익을 읽지 않는다)에서만 부른다.
  «P0 단계»(r_p0.py run — 수익을 읽는다)는 시작할 때 GUARD["run"] = True 를 세우고, 그 뒤 flag_sets 를 부르면
  예외로 멈춘다. P0 단계가 받는 것은 월 × 칸별 **개수 표**뿐이다(이름이 없다).

플래그 공급 순서(카드·더미마다 · 출처 이름이 개수 표에 남는다).
  1. override    덮어쓰기 파일 FIELDS["flags_override"] — {"cards": {카드: {더미: {월: [그룹 id, …]}}}}.
  2. canonical   정식 표지 빌더의 판 — R1: build/r_r1_flags.py 가 내는 cikmonth(그룹 → 가용월 → {"O","R","U","N",…} 개수 ·
                 OS = O > 0 · RS = R > 0 — r_r1_flags.Flags.dummy 와 같은 뜻) · R2: build/r_r2flags.r2_build(10-Q 짝 · 형태 전환 ·
                 전년도 하위 20% 경계 · t−2..t 창 · 결측 더미)를 그대로 부른다. 규칙은 그 파일들에 한 벌만 있다.
  3. provisional 정식 빌더를 import 할 수 없을 때만 — 카드 문구를 옮긴 이 파일의 간이판(시험·개발용). 개수 표 단계는
                 --allow-provisional 없이 이것을 받지 않는다(등록에 얼릴 판은 1·2 번이어야 한다).
  원천 파일이 아직 없으면 None — 부르는 쪽이 «자료 없음» 으로 기록한다(조용히 0 을 채우지 않는다).

정의된 달(defined). 원천이 다루지 않는 달의 «표지 없음» 은 0 이 아니라 모름이다.
  R1 cikmonth : 파일의 months_ok(r_r1_flags.cikmonth_doc — DERA 2011Q1..2026Q2 → 2026-06 에서 끝난다) · 달 우선 배치는 그 달 키 ·
                행 목록에 months_ok 가 없으면 None(부르는 쪽이 멈춘다).
  R2 10-Q     : 파일에 months_ok 가 있으면 그것 · 없으면 문서 공개월 범위 [첫 공개월 + 2, 끝 공개월](t−2..t 창이 자료 안).
  override    : 파일의 months_ok(목록 · {카드: 목록} · {카드: {더미: 목록}}) · 없으면 None.
"""
from __future__ import annotations
import datetime as dt
import io, json, os, sys

try: sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서 한글 print 가 죽지 않게(랩 규약)
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_R = os.environ.get("R_DATA") or os.path.join(ROOT, "data")   # 배치 R 새 자료가 있는 곳(가격 세계와 따로 둘 수 있다)

GUARD = {"run": False}          # r_p0.run() 이 True 로 세운다 — 그 뒤 flag_sets 호출은 멈춘다

# ════════════════════════════════════════════════════════════════════════
# FIELDS — 새 자료의 경로·필드 이름. 스키마가 확정되면 **여기만** 고친다.
# ════════════════════════════════════════════════════════════════════════
FIELDS = {
    # §A0 — tm[티커] = [[첫 달, 끝 달, 그룹, 주 CIK, [CIK 집합], fpi, 출처, fpi_q]] (issuer_map.py 머리말 · 2026-09-25 판)
    #   🔒 fpi 칸은 박지 않는다 — 지도의 fpi_registered.tm_index(2026-09-25 권고 fpi_q = 7 · r_stagem · r_r1_flags 와 같은 칸) · 없으면 5(사양 칸)
    #   viol = 지도 F0 위반 멤버-월 [[티커, 달, …]](표본 밖 — r_stagem.IssuerMap.violated 와 같다 · 2026-09-26)
    "issuer_map": {"file": "_issuer_map.json", "tm": "tm", "fpi_registered": "fpi_registered", "viol": ("f0", "violations"),
                   "pos": {"first": 0, "last": 1, "gid": 2, "primary": 3, "ciks": 4, "fpi_spec": 5, "src": 6}},
    # §A — 그룹 × 가용월 집계(data_build_plan §A 출력 (b)). 배치는 셋 중 하나를 알아본다:
    #   그룹 우선 {그룹: {월: {"O": n, "R": n, …}}}  (r_r1_flags.Flags.export · 최상위 또는 groups_root 아래)
    #   달 우선   {"months": {월: {그룹: {…}}}}
    #   행 목록   {"rows": [{"g": 그룹, "m": 월, …}]}
    # 개수 필드는 후보 목록 — 앞의 것부터 찾는다(빌더가 이름을 정하면 하나로 줄인다).
    "ins_cikmonth": {"file": os.path.join("_ins_pit", "cikmonth.json"), "months": "months", "rows": "rows",
                     "groups_root": ("groups", "gm", "data", "cikmonth"), "months_ok": "months_ok",
                     "g": "g", "m": "m", "os": ("O", "os_n", "n_os"), "rs": ("R", "rs_n", "n_rs"),
                     "os_na": ("os_na",), "rs_na": ("rs_na",)},
    # §C — 10-Q 한 건 = 한 행(data_build_plan §C data/_txt_sim.json 필드 목록 · 이 배치의 판 이름은 _tenq_rf.json)
    "tenq_rf": {"file": "_tenq_rf.json", "rows": "rows", "g": "g", "avail": "avail_date", "accepted": "accepted_et",
                "sim": "SimRF", "status": "parse_status", "ok": ("ok",),
                "missing": ("split_fail", "no_pair", "form_switch"), "months_ok": "months_ok"},
    # §F — 커버리지 F0 를 넘은 달(보유월이 아니라 신호월 t). 두 모양: {"months_ok": [...]} 또는
    #   r_stagem --construct 산출물 {"months": [첫, 끝], "coverage": {"fail": [...]}} (그쪽은 지도 F0 도 이미 걸었다)
    "coverage": {"file": "_r_coverage.json", "months_ok": "months_ok", "window": "months", "cov": "coverage", "fail": "fail"},
    # §A0 지도 F0 — 위반율 > 2% 인 달(측정 불가)
    "issuer_f0": {"f0": "f0", "bad_months": "bad_months"},
    # 정식 플래그 판(있으면 잠정 빌더보다 먼저)
    "flags_override": {"file": "_r_flags.json", "cards": "cards", "months_ok": "months_ok"},
}

# 카드 더미 → 잠정 빌더(더미 이름은 r_p0.CARDS 와 같다)
PROVIDER = {("R1-OPPSELL", "OS"): "ins_os", ("R1-OPPSELL", "RS"): "ins_rs",
            ("R2-LAZYRF", "CH"): "tenq_ch", ("R2-LAZYRF", "CH_MISS"): "tenq_miss"}


def _p(key):
    return os.path.join(DATA_R, FIELDS[key]["file"])


def _rj(path):
    if not os.path.exists(path):
        return None
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def mshift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    n = y * 12 + (m - 1) + k
    return "%04d-%02d" % (n // 12, n % 12 + 1)


# ── ① 발행사 지도 ─────────────────────────────────────────────────────────
class IssuerMap:
    """(티커, 월) → {"gid", "fpi", "fpi_spec", "src"}. 파일이 없으면 ok=False — 부르는 쪽이 티커를 키로 쓴다(합성·임시).
    fpi = 등록 표지(fpi_registered.tm_index 칸) · violated(티커, 월) = 지도 F0 위반 멤버-월."""

    def __init__(self, path=None, doc=None):
        path = path or _p("issuer_map")
        d = doc if doc is not None else _rj(path)
        self.path, self.ok, self.idx, self.viol = path, d is not None, {}, set()
        self.fpi_index = FIELDS["issuer_map"]["pos"]["fpi_spec"]
        if not self.ok:
            return
        F = FIELDS["issuer_map"]
        P = F["pos"]
        self.fpi_index = int((d.get(F["fpi_registered"]) or {}).get("tm_index", P["fpi_spec"]))
        fx = self.fpi_index
        for t, runs in (d.get(F["tm"]) or {}).items():
            for run in runs:
                ym, b = run[P["first"]], run[P["last"]]
                rec = {"gid": run[P["gid"]], "fpi": run[fx] if len(run) > fx else run[P["fpi_spec"]], "fpi_spec": run[P["fpi_spec"]],
                       "src": run[P["src"]]}
                while ym <= b:
                    self.idx[(t, ym)] = rec
                    ym = mshift(ym, 1)
        v = d
        for k in F["viol"]:
            v = v.get(k) if isinstance(v, dict) else None
        self.viol = {(str(x[0]).replace("-", "."), x[1]) for x in (v or [])}

    def violated(self, t, ym):
        """지도 F0 위반 멤버-월인가(명단 '-' · 지도 '.' 표기 둘 다 · r_stagem.IssuerMap.violated 와 같은 뜻)."""
        return ((t or "").replace("-", "."), ym) in self.viol

    def get(self, t, ym, k=None):
        """명단 티커(점 → 대시 표기)·가격 키 둘 다 본다. 없으면 None."""
        for c in (t, (t or "").replace("-", "."), k, (k or "").replace("-", ".")):
            if c and (c, ym) in self.idx:
                return self.idx[(c, ym)]
        return None


# ── ③ 커버리지 F0 ────────────────────────────────────────────────────────
def coverage_months(path=None):
    """§F 커버리지 F0 를 넘은 신호월 목록 — 파일이 없으면 None."""
    F = FIELDS["coverage"]
    d = _rj(path or _p("coverage"))
    if d is None:
        return None
    if isinstance(d.get(F["months_ok"]), list):
        return sorted(d[F["months_ok"]])
    w, fail = d.get(F["window"]), set(((d.get(F["cov"]) or {}).get(F["fail"])) or [])
    if isinstance(w, list) and len(w) >= 2:
        out, m = [], w[0]
        while m <= w[1]:
            if m not in fail:
                out.append(m)
            m = mshift(m, 1)
        return out
    raise SystemExit("🚨 커버리지 파일 모양을 모른다 — r_p0_adapt.FIELDS['coverage'] 를 고쳐라 (키 %s)" % sorted(d)[:20])


def month_gate(path=None):
    """달 관문 = 커버리지 F0 달 − 지도 F0 측정 불가 달. 커버리지가 없으면 (None, 이유) — T 가 잠정이 된다."""
    cov = coverage_months(path)
    im = _rj(_p("issuer_map")) or {}
    bad = set(((im.get(FIELDS["issuer_f0"]["f0"]) or {}).get(FIELDS["issuer_f0"]["bad_months"])) or [])
    src = {"coverage": path or _p("coverage"), "coverage_exists": cov is not None, "issuer_bad_months": sorted(bad)}
    if cov is None:
        return None, src
    return [m for m in cov if m not in bad], src


# ── ② 플래그 집합(카운트 단계 전용) ──────────────────────────────────────
_CACHE = {}


def flag_sets(card, dummy, world=None, allow_provisional=True):
    """({월: set(그룹 id)} | None, 출처) — flag_source 의 얇은 판. 🚨 P0 단계(GUARD["run"])에서는 부를 수 없다."""
    r = flag_source(card, dummy, world=world, allow_provisional=allow_provisional)
    return r["sets"], r["src"]


def _res(sets, src, defined=None, na=None):
    return {"sets": sets, "src": src, "defined": None if defined is None else sorted(defined), "na": na or {}}


def window_defined(pub_months, lead=2):
    """공개월 목록 → t−lead..t 창이 모두 자료 안에 드는 달 t 목록([첫 + lead, 끝])."""
    pm = sorted(m for m in pub_months if _is_ym(m))
    if not pm:
        return []
    out, m = [], mshift(pm[0], lead)
    while m <= pm[-1]:
        out.append(m)
        m = mshift(m, 1)
    return out


def _override_defined(ov, card, dummy):
    mo = ov.get(FIELDS["flags_override"]["months_ok"])
    if isinstance(mo, list):
        return mo
    if isinstance(mo, dict):
        c = mo.get(card)
        if isinstance(c, list):
            return c
        if isinstance(c, dict) and isinstance(c.get(dummy), list):
            return c[dummy]
    return None


def flag_source(card, dummy, world=None, allow_provisional=True):
    """{"sets": {월: set(그룹 id)} | None, "src": 출처, "defined": 원천이 정의한 달 | None, "na": {월: set(그룹)}(표지 모름)}.
    world = {(그룹, 월)} — R2 경계 분포의 세계(r_r2flags.boundaries 의 inw · BW0 부터).
    🚨 P0 단계(GUARD["run"])에서는 부를 수 없다."""
    if GUARD["run"]:
        raise RuntimeError("🚨 방화벽 — P0 단계에서 실제 플래그를 읽으려 했다(개수 표만 쓴다)")
    ov = _rj(_p("flags_override"))
    if ov is not None:
        c = (ov.get(FIELDS["flags_override"]["cards"]) or {}).get(card) or {}
        if dummy in c:
            return _res({m: set(v) for m, v in c[dummy].items()}, "override:" + FIELDS["flags_override"]["file"],
                        _override_defined(ov, card, dummy))
    kind = PROVIDER.get((card, dummy))
    if kind is None:
        return _res(None, "no_builder")
    if kind in ("ins_os", "ins_rs"):
        k = "os" if kind == "ins_os" else "rs"
        got = _ins(FIELDS["ins_cikmonth"][k], FIELDS["ins_cikmonth"][k + "_na"])
        if got is None:
            return _res(None, "absent")
        return _res(got[0], "canonical:cikmonth(r_r1_flags.export)", got[1], got[2])
    got = _tenq_canonical(world)
    src = "canonical:r_r2flags.r2_build"
    if got is None:
        if not allow_provisional:
            return _res(None, "canonical_unavailable")
        got, src = _tenq(), "provisional:tenq"
    out = got[0] if kind == "tenq_ch" else got[1]
    return _res(out, src, got[2]) if out is not None else _res(None, "absent")


def _pick(rec, names):
    for n in names:
        if n in rec:
            return rec[n]
    return None


def _is_ym(x):
    return isinstance(x, str) and len(x) == 7 and x[4] == "-" and x[:4].isdigit()


def _ins(fields, na_fields=()):
    """R1 — 그룹 × 가용월 의 매도자 수(fields 후보) ≥ 1 이면 그 달 플래그(카드 (6) OS_i,t · RS_i,t).
    반환 (sets, 정의된 달 | None, na {월: set(그룹)}) · 파일이 없으면 None. 표지가 1 이 아니고 na 칸이 1 이면 «모름»(선언 f)."""
    F = FIELDS["ins_cikmonth"]
    d = _rj(_p("ins_cikmonth"))
    if d is None:
        return None
    out, na = {}, {}
    mo = d.get(F["months_ok"]) if isinstance(d.get(F["months_ok"]), list) else None

    def add(m, g, rec):
        rec = rec or {}
        if (_pick(rec, fields) or 0) >= 1:
            out.setdefault(m, set()).add(str(g))
        elif (_pick(rec, na_fields) or 0) >= 1:
            na.setdefault(m, set()).add(str(g))
    if isinstance(d.get(F["months"]), dict):                                   # 달 우선
        for m, byg in d[F["months"]].items():
            for g, rec in (byg or {}).items():
                add(m, g, rec)
        return out, (mo if mo is not None else sorted(m for m in d[F["months"]] if _is_ym(m))), na
    if isinstance(d.get(F["rows"]), list):                                     # 행 목록
        for r in d[F["rows"]]:
            add(r[F["m"]], r[F["g"]], r)
        return out, mo, na
    root = next((d[k] for k in F["groups_root"] if isinstance(d.get(k), dict)), d)
    for g, bym in root.items():                                                # 그룹 우선(r_r1_flags.export · cikmonth_doc)
        if not isinstance(bym, dict) or not any(_is_ym(m) for m in bym):
            continue
        for m, rec in bym.items():
            if _is_ym(m) and isinstance(rec, dict):
                add(m, g, rec)
    return out, mo, na


def _tenq_canonical(world=None):
    """R2 정식 — r_r2flags 의 판(load_tenq → r2_build) 그대로. 반환 (CH, CH_MISS, 정의된 달).
    import 가 안 되면 None, 원천이 없으면 (None, None, None)."""
    try:
        import r_r2flags as R2
    except Exception:
        return None
    path = next((x for x in (_p("tenq_rf"), _p("tenq_rf") + ".gz") if os.path.exists(x)), None)
    if path is None:
        return (None, None, None)
    key = (path, os.path.getmtime(path), None if world is None else hash(frozenset(world)))
    if key in _CACHE:
        return _CACHE[key]
    im = R2.IssuerMap.load(_p("issuer_map")) if os.path.exists(_p("issuer_map")) else None
    raw = R2.read_json(path)
    R = R2.r2_build(R2.load_tenq(path), R2.Cal(), gof=(im.group_of if im else None), world=world)
    ch, miss = {}, {}
    for (g, t), row in R["gm"].items():
        if row.get("ch"):
            ch.setdefault(t, set()).add(str(g))
        if row.get("miss"):
            miss.setdefault(t, set()).add(str(g))
    mo = raw.get(FIELDS["tenq_rf"]["months_ok"]) if isinstance(raw, dict) else None
    defined = mo if isinstance(mo, list) else window_defined({d.get("pub_m") for d in R["docs"].values()})
    _CACHE[key] = (ch, miss, defined)
    return _CACHE[key]


def _avail_month(r, F):
    """공개월 — avail_date(가용 거래일, 이미 16:00 규칙 적용) 우선 · 없으면 accepted_et 의 날짜(16:00 이후면 다음 날).
    잠정 빌더의 근사: 다음 날이 휴장일이어도 달이 바뀌는 경우만 틀린다(월말 16:00 이후 접수)."""
    if r.get(F["avail"]):
        return r[F["avail"]][:7]
    a = r.get(F["accepted"])
    if not a:
        return None
    t = dt.datetime.fromisoformat(a[:19])
    if t.hour >= 16:
        t = t + dt.timedelta(days=1)
    return t.strftime("%Y-%m")


def _tenq():
    """R2 간이판(provisional · 정식 r_r2flags 를 import 못 할 때만) — 카드 (7)(8): 직전 달력연도에 공개된 유효 짝 SimRF 의 하위 20% 경계보다 낮으면 Q1.
    CH_active_t = 공개월 t−2..t 에 Q1 10-Q 가 있으면 1 · CH_MISS_t = 그 창에 결측 사유(분리 실패·짝 없음·형태 전환) 10-Q 가
    있고 CH_active 가 아니면 1. 반환 (CH, CH_MISS, 정의된 달) — 원천이 없으면 (None, None, None)."""
    import numpy as np
    F = FIELDS["tenq_rf"]
    d = _rj(_p("tenq_rf"))
    if d is None:
        return None, None, None
    rows = d.get(F["rows"]) or []
    by_year, ev_q1, ev_miss, pubs = {}, {}, {}, set()
    for r in rows:
        pm = _avail_month(r, F)
        if pm is None:
            continue
        r["_pm"] = pm
        pubs.add(pm)
        if r.get(F["status"]) in F["ok"] and r.get(F["sim"]) is not None:
            by_year.setdefault(pm[:4], []).append(float(r[F["sim"]]))
    mo = d.get(F["months_ok"])
    defined = mo if isinstance(mo, list) else window_defined(pubs)
    cut = {y: float(np.quantile(v, 0.20)) for y, v in by_year.items() if v}
    for r in rows:
        pm = r.get("_pm")
        if pm is None:
            continue
        if r.get(F["status"]) in F["ok"] and r.get(F["sim"]) is not None:
            c = cut.get(str(int(pm[:4]) - 1))
            if c is not None and float(r[F["sim"]]) < c:
                ev_q1.setdefault(pm, set()).add(r[F["g"]])
        elif r.get(F["status"]) in F["missing"]:
            ev_miss.setdefault(pm, set()).add(r[F["g"]])
    months = sorted(set(ev_q1) | set(ev_miss))
    if not months:
        return {}, {}, defined
    ch, miss = {}, {}
    m, end = months[0], mshift(months[-1], 2)
    while m <= end:
        w = [mshift(m, -j) for j in range(3)]
        a = set().union(*[ev_q1.get(x, set()) for x in w])
        b = set().union(*[ev_miss.get(x, set()) for x in w]) - a
        if a:
            ch[m] = a
        if b:
            miss[m] = b
        m = mshift(m, 1)
    return ch, miss, defined


def status():
    """어느 원천이 지금 있는가(구성 점검용 — 내용은 읽지 않는다). 파일이 따로 없는 칸(issuer_f0 = 지도 안의 칸)은 뺀다."""
    return {k: {"path": os.path.relpath(_p(k), ROOT) if _p(k).startswith(ROOT) else _p(k), "exists": os.path.exists(_p(k))}
            for k in FIELDS if "file" in FIELDS[k]}


if __name__ == "__main__":
    print(json.dumps(status(), ensure_ascii=False, indent=1))
