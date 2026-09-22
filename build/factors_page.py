# -*- coding: utf-8 -*-
"""팩터 사전(factors.html) 생성기.

입력  build/factors_src.json — 사내 팩터 정의 표를 그대로 뽑은 것.
      🚨 공개 저장소라 반입 금지(.gitignore). 게시물은 factors.html 하나다.
      {"extracted": "YYYY-MM-DD", "columns": [...],
       "rows": [{factor, spg, group, subgroup, description, rank_order, notes, formula, citations}, ...]}
출력  factors.html 의 <!-- FACTORS:BEGIN --> ~ <!-- FACTORS:END --> 구간(요약 수치·필터 선택지·목록).
      머리·스타일·스크립트·메뉴는 손대지 않는다(메뉴는 sync_nav, 셸은 sync_shell 몫).

원칙  값은 **원표 그대로** 싣는다 — 문구를 고치거나 줄이지 않는다. 순서도 원표 순서다.
      빈 값(NULL)은 '—' 로 보이게 둔다(없는 것을 없다고 표시한다).
실행  python build/factors_page.py            굽기
      python build/factors_page.py --check    페이지가 입력과 같은지만 본다(다르면 종료코드 1)
      ⚠ 입력이 반입 금지라 CI 러너에는 없다 — --check 를 CI 에 걸지 말 것.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import html, json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "build", "factors_src.json")
PAGE = os.path.join(ROOT, "factors.html")
BEGIN, END = "<!-- FACTORS:BEGIN -->", "<!-- FACTORS:END -->"
LF, CRLF = chr(10), chr(13) + chr(10)
KEYS = ("factor", "spg", "group", "subgroup", "description", "rank_order",
        "notes", "formula", "citations")
# rank_order 원문 → (필터 키, 화면 표기). 원문 낱말은 그대로 두고 화살표만 덧붙인다.
DIR = {"오름차순": ("asc", "오름차순 ↑"), "내림차순": ("desc", "내림차순 ↓")}
KNOWN_GROUPS = {"S&P Global": "sp", "Style Factor": "st"}


def esc(v):
    return html.escape(v, quote=True)


def load():
    with open(SRC, encoding="utf-8") as f:
        d = json.load(f)
    seen = set()
    for r in d["rows"]:
        miss = [k for k in KEYS if k not in r]
        if miss:
            raise SystemExit("입력에 없는 열: %s" % miss)
        if not r["factor"]:
            raise SystemExit("factor 가 빈 행이 있다")
        if r["factor"] in seen:
            raise SystemExit("factor 중복: %s" % r["factor"])
        seen.add(r["factor"])
        for k in KEYS:
            v = r[k]
            if v is not None and any(ord(c) < 32 and ord(c) not in (9, 10, 13) for c in v):
                raise SystemExit("제어문자: %s / %s" % (r["factor"], k))
        if r["rank_order"] is not None and r["rank_order"] not in DIR:
            raise SystemExit("알 수 없는 rank_order %r — DIR 에 먼저 넣을 것 (%s)"
                             % (r["rank_order"], r["factor"]))
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

    L = ['<p class="stats"><span>팩터 <b class="tnum">%d</b>개</span>%s'
         '<span>소분류 <b class="tnum">%d</b>개</span><span>원표 추출 <b class="tnum">%s</b></span></p>'
         % (len(rows), "".join('<span>%s <b class="tnum">%d</b></span>' % (esc(g or "—"), gc[g]) for g in groups),
            len(subs), esc(d["extracted"]))]
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
    for i, r in enumerate(rows, 1):
        dk, dl = DIR.get(r["rank_order"], ("", "—"))
        body = []
        if r["spg"] and r["spg"] != r["factor"]:
            body.append(field("원 명칭", r["spg"]))
        body.append(field("설명", r["notes"]))
        body.append(field("산식", r["formula"], code=True))
        body.append(field("참고문헌", r["citations"]))
        L.append('<details class="fx" id="f%d" data-g="%s" data-sg="%s" data-dir="%s"><summary>'
                 '<span class="fxn">%s</span><span class="fxd">%s</span>'
                 '<span class="fxm"><span class="chip">%s</span><span class="chip g-%s">%s</span>'
                 '<span class="dir">%s</span></span></summary><div class="fxb">%s</div></details>'
                 % (i, gk[r["group"]], esc(r["subgroup"] or ""), dk,
                    esc(r["factor"]), esc(r["description"] or "—"),
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
    print("팩터 사전: %d개 → factors.html (원표 추출 %s)" % (len(d["rows"]), d["extracted"]))


if __name__ == "__main__":
    main()
