# -*- coding: utf-8 -*-
"""팩터 사전(factors.html) 생성기.

입력  build/factors_src.json — 사내 팩터 정의 표를 그대로 뽑은 것.
      🚨 공개 저장소라 반입 금지(.gitignore). 게시물은 factors.html 하나다.
      {"extracted": "YYYY-MM-DD", "columns": [...],
       "rows": [{factor, spg, group, subgroup, description, rank_order, notes, formula, citations}, ...]}
      build/factors_lab.json — 여두 전략 랩 규칙에서 옮긴 팩터(공개 · 저장소에 있다).
      원표 열에 lab_sid(explorer 카드) · similar(비슷한 원표 팩터 이름 목록)를 더한 모양이다.
      🚨 2026-09-22 사용자 «Style Factor에 추가할만한거 … Low Volatility, Momentum, Size, Value,
        Quality 로 분류» · «S&P Global은 건들면 안돼. 비슷한 팩터는 스타일 팩터 오른쪽에 따로 분류».
        → 원표 행 **뒤에** 이어 붙인다. 원표 행은 순서·문구·번호(#f1…)가 그대로다.
          비슷한 원표 팩터가 있는 것은 group «유사 팩터»(분류 단추가 Style Factor 오른쪽에 온다),
          없는 것은 group «Style Factor». 둘 다 소분류는 다섯 스타일 중 하나다.
출력  factors.html 의 <!-- FACTORS:BEGIN --> ~ <!-- FACTORS:END --> 구간(요약 수치·필터 선택지·목록).
      머리·스타일·스크립트·메뉴는 손대지 않는다(메뉴는 sync_nav, 셸은 sync_shell 몫).

원칙  값은 **원표 그대로** 싣는다 — 문구를 고치거나 줄이지 않는다. 순서도 원표 순서다.
      빈 값(NULL)은 '—' 로 보이게 둔다(없는 것을 없다고 표시한다).
      랩 행은 줄마다 «랩» 표시와 출처(카드 링크)를 달아 원표 행과 섞여 읽히지 않게 한다.
실행  python build/factors_page.py            굽기
      python build/factors_page.py --check    페이지가 입력과 같은지만 본다(다르면 종료코드 1)
      ⚠ 입력이 반입 금지라 CI 러너에는 없다 — --check 를 CI 에 걸지 말 것.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import html, json, os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "build", "factors_src.json")
LAB = os.path.join(ROOT, "build", "factors_lab.json")
PAGE = os.path.join(ROOT, "factors.html")
BEGIN, END = "<!-- FACTORS:BEGIN -->", "<!-- FACTORS:END -->"
LF, CRLF = chr(10), chr(13) + chr(10)
KEYS = ("factor", "spg", "group", "subgroup", "description", "rank_order",
        "notes", "formula", "citations")
# rank_order 원문 → (필터 키, 화면 표기). 원문 낱말은 그대로 두고 화살표만 덧붙인다.
DIR = {"오름차순": ("asc", "오름차순 ↑"), "내림차순": ("desc", "내림차순 ↓")}
KNOWN_GROUPS = {"S&P Global": "sp", "Style Factor": "st", "유사 팩터": "sim"}
# 랩 행이 들어갈 수 있는 그룹과 소분류 — 사용자가 정한 다섯 스타일 밖으로 나가지 않게 막는다.
LAB_GROUPS = ("Style Factor", "유사 팩터")
STYLE_SUBS = ("Low Volatility", "Momentum", "Size", "Value", "Quality")


def esc(v):
    return html.escape(v, quote=True)


def _check_row(r, where):
    miss = [k for k in KEYS if k not in r]
    if miss:
        raise SystemExit("%s 에 없는 열: %s" % (where, miss))
    if not r["factor"]:
        raise SystemExit("%s: factor 가 빈 행이 있다" % where)
    for k in KEYS:
        v = r[k]
        if v is not None and any(ord(c) < 32 and ord(c) not in (9, 10, 13) for c in v):
            raise SystemExit("제어문자: %s / %s" % (r["factor"], k))
    if r["rank_order"] is not None and r["rank_order"] not in DIR:
        raise SystemExit("알 수 없는 rank_order %r — DIR 에 먼저 넣을 것 (%s)"
                         % (r["rank_order"], r["factor"]))


def load():
    with open(SRC, encoding="utf-8") as f:
        d = json.load(f)
    seen = set()
    for r in d["rows"]:
        _check_row(r, "원표")
        if r["factor"] in seen:
            raise SystemExit("factor 중복: %s" % r["factor"])
        seen.add(r["factor"])
    base = {r["factor"]: r for r in d["rows"]}
    # ── 랩 행 ── 없으면 멈춘다(조용히 빠지면 «랩 팩터가 원래 없는 사전» 으로 읽힌다).
    if not os.path.exists(LAB):
        raise SystemExit("build/factors_lab.json 이 없다 — 랩 팩터를 빼려면 파일이 아니라 행을 지울 것")
    with open(LAB, encoding="utf-8") as f:
        lab = json.load(f)
    rows = []
    for r in lab["rows"]:
        _check_row(r, "랩")
        nm = r["factor"]
        if nm in seen:
            raise SystemExit("랩 factor 가 원표·랩과 겹친다: %s" % nm)
        seen.add(nm)
        if r["group"] not in LAB_GROUPS:
            raise SystemExit("랩 행 group 은 %s 중 하나: %s (%s)" % (LAB_GROUPS, r["group"], nm))
        if r["subgroup"] not in STYLE_SUBS:
            raise SystemExit("랩 행 subgroup 은 다섯 스타일 %s 중 하나: %s (%s)" % (STYLE_SUBS, r["subgroup"], nm))
        if not re.fullmatch(r"t-[a-z0-9-]+", r.get("lab_sid") or ""):
            raise SystemExit("랩 행 lab_sid 가 explorer 카드 id(t-…) 가 아니다: %s" % nm)
        sim = r.get("similar") or []
        # 유사 팩터는 짝이 있어야 하고, Style Factor 로 넣은 것은 짝이 없어야 한다 — 두 판정이 갈리면 분류가 틀린 것이다.
        if r["group"] == "유사 팩터" and not sim:
            raise SystemExit("«유사 팩터» 인데 similar 가 비었다: %s" % nm)
        if r["group"] == "Style Factor" and sim:
            raise SystemExit("similar 가 있는데 «Style Factor» 로 넣었다 — «유사 팩터» 로 옮길 것: %s" % nm)
        for s in sim:
            if s not in base:
                raise SystemExit("similar 가 가리키는 원표 팩터가 없다: %r (%s) — 원표가 바뀌었나" % (s, nm))
        rows.append(dict(r, _lab=True))
    d["rows"] = d["rows"] + rows
    d["n_lab"] = len(rows)
    return d


def field(label, v, code=False):
    if v is None or v == "":
        return '<div class="fxk">%s</div><div class="fxv nil">—</div>' % label
    if code:
        return '<div class="fxk">%s</div><pre class="fxv code">%s</pre>' % (label, esc(v))
    return '<div class="fxk">%s</div><div class="fxv">%s</div>' % (label, esc(v))


def render(d):
    rows = d["rows"]
    groups = []
    for r in rows:
        if r["group"] not in groups:
            groups.append(r["group"])
    gk, extra = {}, 0
    for g in groups:
        if g in KNOWN_GROUPS:
            gk[g] = KNOWN_GROUPS[g]
        else:
            extra += 1
            gk[g] = "g%d" % extra
    gc = {g: sum(1 for r in rows if r["group"] == g) for g in groups}
    subs, dirs = {}, {}
    for r in rows:
        subs[r["subgroup"]] = subs.get(r["subgroup"], 0) + 1
        dirs[r["rank_order"]] = dirs.get(r["rank_order"], 0) + 1
    # 원표 행의 번호(#f<n>) — 랩 행의 «비슷한 기존 팩터» 가 이 번호로 건다(원표 행은 앞에 있어 번호가 안 바뀐다).
    num = {r["factor"]: i for i, r in enumerate(rows, 1) if not r.get("_lab")}
    n_lab = d.get("n_lab", 0)

    L = ['<p class="stats"><span>팩터 <b class="tnum">%d</b>개</span>%s'
         '<span>소분류 <b class="tnum">%d</b>개</span><span>원표 추출 <b class="tnum">%s</b></span>%s</p>'
         % (len(rows), "".join('<span>%s <b class="tnum">%d</b></span>' % (esc(g or "—"), gc[g]) for g in groups),
            len(subs), esc(d["extracted"]),
            ('<span>랩 추가 <b class="tnum">%d</b> (여두 전략 랩 규칙 · 원표 아님)</span>' % n_lab) if n_lab else "")]
    L.append('<div class="fxbar">')
    L.append('<input type="search" id="fxq" placeholder="팩터명·설명·산식·참고문헌 검색" aria-label="팩터 검색" autocomplete="off">')
    L.append('<div class="fxg" role="group" aria-label="그룹">'
             '<button type="button" data-g="all" aria-pressed="true">전체 <span class="tnum">%d</span></button>%s</div>'
             % (len(rows), "".join('<button type="button" data-g="%s" aria-pressed="false">%s <span class="tnum">%d</span></button>'
                                   % (gk[g], esc(g or "—"), gc[g]) for g in groups)))
    L.append('<select id="fxsg" aria-label="소분류"><option value="">소분류 전체</option>%s</select>'
             % "".join('<option value="%s">%s (%d)</option>' % (esc(s or ""), esc(s or "—"), n)
                       for s, n in sorted(subs.items(), key=lambda x: (-x[1], x[0] or ""))))
    L.append('<select id="fxdir" aria-label="순위 방향"><option value="">순위 방향 전체</option>%s</select>'
             % "".join('<option value="%s">%s (%d)</option>' % (DIR[k][0], esc(k), dirs[k]) for k in DIR if k in dirs))
    L.append('</div>')
    L.append('<div class="fxtool"><span>표시 <b class="tnum" id="fxcnt">%d / %d</b></span>'
             '<button type="button" id="fxopen" data-open="0">모두 펼치기</button></div>' % (len(rows), len(rows)))
    L.append('<div class="fxlist" id="fxlist">')
    by_name = {r["factor"]: r for r in rows}
    for i, r in enumerate(rows, 1):
        dk, dl = DIR.get(r["rank_order"], ("", "—"))
        body = []
        if r["spg"] and r["spg"] != r["factor"]:
            body.append(field("원 명칭", r["spg"]))
        body.append(field("설명", r["notes"]))
        body.append(field("산식", r["formula"], code=True))
        body.append(field("참고문헌", r["citations"]))
        lab = r.get("_lab")
        if lab:
            if r.get("similar"):
                body.append('<div class="fxk">비슷한 기존 팩터</div><div class="fxv">%s</div>' % " · ".join(
                    '<a href="#f%d">%s</a> <span class="fxs">(%s · %s)</span>'
                    % (num[s], esc(s), esc(by_name[s]["group"] or "—"), esc(by_name[s]["subgroup"] or "—"))
                    for s in r["similar"]))
            body.append('<div class="fxk">출처</div><div class="fxv">여두 전략 랩 규칙 '
                        '<a href="explorer.html#s-%s">%s</a> — 백테스트·판정은 그 카드에서 본다</div>'
                        % (esc(r["lab_sid"]), esc(r["lab_sid"])))
        L.append('<details class="fx" id="f%d" data-g="%s" data-sg="%s" data-dir="%s"><summary>'
                 '<span class="fxn">%s</span><span class="fxd">%s</span>'
                 '<span class="fxm">%s<span class="chip">%s</span><span class="chip g-%s">%s</span>'
                 '<span class="dir">%s</span></span></summary><div class="fxb">%s</div></details>'
                 % (i, gk[r["group"]], esc(r["subgroup"] or ""), dk,
                    esc(r["factor"]), esc(r["description"] or "—"),
                    '<span class="chip lab" title="여두 전략 랩 규칙에서 옮긴 팩터(사내 원표 아님)">랩</span>' if lab else "",
                    esc(r["subgroup"] or "—"), gk[r["group"]], esc(r["group"] or "—"), esc(dl),
                    "".join(body)))
    L.append('<p class="fxempty" id="fxempty" hidden>조건에 맞는 팩터가 없습니다.</p>')
    L.append('</div>')
    return LF.join(L)


def main():
    check = "--check" in sys.argv[1:]
    d = load()
    with open(PAGE, encoding="utf-8", newline="") as f:
        page = f.read()
    nl = CRLF if CRLF in page else LF
    a, b = page.find(BEGIN), page.find(END)
    if a < 0 or b < a:
        raise SystemExit("factors.html 에 FACTORS:BEGIN/END 표지가 없다")
    new = page[:a + len(BEGIN)] + nl + render(d).replace(LF, nl) + nl + page[b:]
    if check:
        same = new == page
        print("팩터 사전:", "입력과 같음" if same else "입력과 다름 — python build/factors_page.py 로 다시 구울 것")
        sys.exit(0 if same else 1)
    with open(PAGE, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    print("팩터 사전: %d개(원표 %d · 랩 %d) → factors.html (원표 추출 %s)"
          % (len(d["rows"]), len(d["rows"]) - d["n_lab"], d["n_lab"], d["extracted"]))


if __name__ == "__main__":
    main()
