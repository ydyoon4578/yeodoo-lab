#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공통 셸(글꼴·중립색·타이포) 정본 전파기.

빌드 스텝이 없는 사이트라 23장이 각자 <style>을 들고 있다. 공통 양식을 한 번에 바꾸려면
"한 곳에서 만들어 전부에 밀어넣고, 어긋나면 CI가 막는" 수밖에 없다 — sync_nav.py와 같은 방식이고,
이 스크립트는 메뉴가 아니라 **글꼴·중립색·타이포**를 담당한다.

  build/sync_shell.py (이 파일)   ← 정본
        └─ 각 HTML 첫 <style>의 끝에 /* SHELL:BEGIN */ ~ /* SHELL:END */ 를 넣거나 교체
        └─ <head>에 Pretendard <link> 를 넣거나 교체(SHELLFONT 마커)

왜 '첫 </style> 앞'인가.
  ① **마지막** </style>은 NAVCSS 구간이라 다음 sync_nav 실행이 통째로 갈아엎는다(실제로 겪었다).
  ② 페이지 고유 셸 규칙(.lbl·h1.title·.card .ch …)은 그 앞에 있다. 같은 특이도면 뒤가 이기므로
     여기 두면 페이지를 한 줄도 고치지 않고 셸만 덮어쓸 수 있다.

무엇을 바꾸고 무엇을 안 바꾸나.
  바꾼다 — 글꼴 스택, 중립색 8종(--ground/--panel/--panel-2/--line/--line-soft/--ink/--ink-2/--muted),
           셸 타이포(제목·섹션 라벨·카드 머리글·표 머리·칩), 숫자 정렬(tabular-nums).
  안 바꾼다 — 의미색 전부(--accent/--deploy/--marg/--champ/--rp/--hot/--gA~F/--rg-*/--sn-*).
           대비를 맞춰 고른 값이라 손대면 국면·심리·등급 표시가 한꺼번에 흔들린다.
           중립색을 바꿀 때도 아래 contrast()로 **패널 대비가 이전보다 나빠지지 않는지** 검사한다.

사용:
    python3 build/sync_shell.py            # 전파
    python3 build/sync_shell.py --check    # 전파하지 않고 어긋난 파일만 보고(CI용)
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE_DIRS = [ROOT, os.path.join(ROOT, "_build", "pages")]

# 리다이렉트 스텁 — <style> 한 개뿐이고 셸이 없다.
SKIP = {"archive.html"}

SHELL_BEGIN, SHELL_END = "/* SHELL:BEGIN */", "/* SHELL:END */"
FONT_BEGIN, FONT_END = "<!-- SHELLFONT:BEGIN -->", "<!-- SHELLFONT:END -->"

# ── Pretendard ────────────────────────────────────────────────────────────────
# 동적 서브셋 판(한글은 쓰인 글자만 내려받는다). 자체 호스팅하면 woff2 100여 개를 저장소에
# 넣어야 해서 CDN을 쓴다. CDN이 죽어도 --sans 뒷순위(시스템 한글 글꼴)로 떨어질 뿐이다.
FONT_LINK = (
    '<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>'
    '<link rel="stylesheet" as="style" crossorigin '
    'href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/'
    'pretendardvariable-dynamic-subset.min.css">'
)

# ── 중립색 정본 ───────────────────────────────────────────────────────────────
# 라이트는 valley.town 계열의 **중립 회색**으로 간다(기존은 파랑이 섞여 있었다 — #1B2733).
# 다크는 TradingView 계열(#131722 바탕 / #2A2E39 선)에 맞춘다. 둘 다 색상 편향을 줄여
# 초록·빨강·금색 의미색이 배경과 다투지 않게 하는 것이 목적이다.
# 라이트 바탕은 2026-07-28 요청으로 **연한 크림**으로 옮겼다 — 흰 바탕이 눈이 아프다는 것이
# 이유다. 순백(#FFFFFF)을 그대로 두면 화면 대부분을 덮는 패널이 여전히 눈부시므로 바탕만이
# 아니라 패널까지 함께 데운다. 노랑 쪽으로 기울지만 채도는 낮게 잡아, 의미색(초록·빨강·금색)이
# 배경과 다투지 않게 한다는 아래 원칙은 유지한다. 글자 대비는 check_contrast()가 잠근다
# (muted 4.82 → 4.73:1, AA 4.5 위·하락 0.09로 문턱 0.15 안).
LIGHT = {
    "--ground": "#FAF7EC", "--panel": "#FFFDF5", "--panel-2": "#F3EFE1",
    "--line": "#E4DFD0", "--line-soft": "#EDE9DC",
    "--ink": "#14181D", "--ink-2": "#3C444D", "--muted": "#6A737D",
    "--shadow": "0 1px 2px rgba(16,24,32,.04),0 10px 28px -18px rgba(16,24,32,.20)",
}
DARK = {
    "--ground": "#10141B", "--panel": "#171C24", "--panel-2": "#1F252F",
    "--line": "#2B323C", "--line-soft": "#232A33",
    "--ink": "#E6EAEF", "--ink-2": "#BAC3CC", "--muted": "#8B95A1",
    "--shadow": "0 1px 2px rgba(0,0,0,.45),0 14px 34px -18px rgba(0,0,0,.65)",
}
# 공용 부품이 기대는 의미색 2종. 색을 '바꾸는' 것이 아니라 **있게 보장하는** 것이다 —
# 값은 21장이 이미 쓰던 정본 그대로다. 내비(sync_nav.py 생성)의 .asofchip.stale이 var(--hot)을
# 쓰는데 explorer·signals에는 그 정의가 없어, 기준일이 낡았다는 표시가 아무 색도 없이 나왔다.
# 공용 블록이 쓰는 토큰은 페이지마다 챙길 것이 아니라 셸이 책임진다.
SHARED = {"light": {"--hot": "#A64B3B", "--marg": "#B25E12"},
          "dark": {"--hot": "#E5806A", "--marg": "#F0863C"}}

# 이전 값 — 대비가 나빠지지 않았는지 비교하는 기준선이다.
OLD_LIGHT = {"--panel": "#FFFFFF", "--ink": "#1B2733", "--ink-2": "#42505E", "--muted": "#66757F"}
OLD_DARK = {"--panel": "#181E26", "--ink": "#EAEEF2", "--ink-2": "#C4CDD6", "--muted": "#8A97A3"}


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hexcol: str) -> float:
    h = hexcol.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def check_contrast() -> list[str]:
    """글자색 3종이 패널 위에서 이전보다 나빠지지 않는지. 나빠지면 배포를 막는다.

    화면에서 제일 자주 밟는 회귀가 '색을 예쁘게 바꿨더니 흐린 글씨가 안 보이는 것'이다.
    눈으로는 늦게 알아채므로 숫자로 잠근다(본문 4.5:1 기준은 WCAG AA).

    ⚠ '이전보다 조금이라도 낮으면 실패'로 두면 안 된다. 14.4:1이 14.2:1이 되는 건 눈에
       보이지 않는 변화이고, 그걸 막으면 색을 영원히 못 고친다. 그래서 **선 근처(AAA 7:1
       미만)에서만** 하락을 막고, 그 위에서는 AA만 지키면 통과시킨다."""
    bad = []
    for name, new, old in (("라이트", LIGHT, OLD_LIGHT), ("다크", DARK, OLD_DARK)):
        for tok in ("--ink", "--ink-2", "--muted"):
            n = contrast(new[tok], new["--panel"])
            o = contrast(old[tok], old["--panel"])
            if n < 4.5:
                bad.append("%s %s 대비 %.2f:1 — AA(4.5) 미달" % (name, tok, n))
            elif o < 7.0 and n < o - 0.15:
                bad.append("%s %s 대비 %.2f:1 — 이전 %.2f:1보다 나빠짐(선 근처)" % (name, tok, n, o))
    return bad


def _decl(d: dict) -> str:
    return "".join("%s:%s;" % (k, v) for k, v in d.items())


def build_shell() -> str:
    # % 서식 대신 치환을 쓴다 — CSS에 color-mix(… 7%) 처럼 %가 그대로 들어간다.
    css = (SHELL_BEGIN + _CSS.replace("@LIGHT@", _decl(LIGHT) + _decl(SHARED["light"]))
           .replace("@DARK@", _decl(DARK) + _decl(SHARED["dark"]))
           + SHELL_END)
    # ⚠ style 종료 태그가 한 글자라도 섞이면 HTML 파서가 **주석 안이든 아니든** 거기서
    #   style 요소를 끝낸다. 그러면 뒤의 CSS 전체가 본문 글자로 쏟아진다. 실제로 밟았고
    #   (설명 주석에 태그를 그대로 적었다), 검증기보다 여기서 막는 게 빠르다.
    if "</" + "style" in css:
        raise SystemExit("셸 CSS에 style 종료 태그가 들어 있다 — 파서가 거기서 스타일을 끊는다")
    # 주석 짝도 본다. 설명에 --rg-*/--sn-* 처럼 별표+빗금이 붙은 토큰명을 쓰면 그 자리에서
    # 주석이 닫히고, 뒤의 설명 문장이 CSS로 해석되면서 이어지는 규칙까지 함께 죽는다.
    if css.count("/*") != css.count("*/"):
        raise SystemExit("셸 CSS의 주석 짝이 안 맞는다(%d 열기 / %d 닫기) — 주석 안에 */가 섞였다"
                         % (css.count("/*"), css.count("*/")))
    return css


_CSS = """
/* ── 공통 셸 v1 — build/sync_shell.py 생성. 이 블록은 직접 고치지 말 것 ──────────────
   23장이 각자 스타일 블록을 들고 있어 공통 양식을 넣을 자리가 첫 블록 맨 끝밖에 없다.
   같은 특이도면 뒤가 이기므로 페이지 셸 규칙만 덮어쓰고 고유 컴포넌트는 건드리지 않는다.
   ⚠ 이 블록 안에 스타일 종료 태그를 글자 그대로 쓰면 안 된다 — HTML 파서는 주석 안이든
      아니든 그 지점에서 style 요소를 끝내버린다(실제로 한 번 밟았다). */

/* ① 글꼴 — Pretendard.
   기존 스택 첫 후보는 "Malgun Gothic"이었다. 윈도 기본 한글 글꼴이라 굵기가 사실상 400/700
   두 단계뿐이고 맥에서는 Apple SD Gothic Neo로 떨어져, 같은 화면이 OS마다 다른 글꼴로 보였다.
   Pretendard는 100~900 가변에 라틴·숫자가 Inter 계열이라 한글과 숫자가 한 글꼴로 붙는다.
   --mono의 한글 후보도 Pretendard로 바꾼다 — 고정폭이 필요한 건 숫자뿐인데, 한글까지 고정폭
   스택으로 떨어뜨리면 본문과 다른 글꼴이 한 줄 안에서 섞인다. */
:root{
  --sans:"Pretendard Variable",Pretendard,-apple-system,BlinkMacSystemFont,system-ui,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif;
  --mono:ui-monospace,"SF Mono","JetBrains Mono","Roboto Mono",Menlo,Consolas,"Pretendard Variable",Pretendard,"Apple SD Gothic Neo",monospace;
  /* 폭 토큰 — 페이지를 옮겨 다닐 때 본문 폭이 튀지 않게 하는 값이다. 21장은 각자 갖고 있었지만
     stocks.html은 max-width:var(--w-wide)를 쓰면서 정의를 안 갖고 있어 폭 제한 없이 퍼져 있었다.
     이런 건 페이지마다 챙길 것이 아니라 셸이 보장할 것이다. */
  --w-wide:1440px;--w-base:1200px;--w-read:980px;
}

/* ② 중립색 — 라이트는 중립 회색, 다크는 터미널 계열. 의미색(accent·deploy·국면·심리 계열)은
   손대지 않는다. 대비는 sync_shell.py의 check_contrast()가 배포 전에 검사한다.
   ⚠ 주석에 별표와 빗금이 붙은 토큰명을 그대로 쓰면 거기서 주석이 닫힌다(밟았다). */
:root{@LIGHT@}
@media(prefers-color-scheme:dark){:root{@DARK@}}
:root[data-theme="light"]{@LIGHT@}
:root[data-theme="dark"]{@DARK@}

/* ③ 타이포 — 한글에 고정폭·대문자변환·자간을 걸던 것을 되돌린다.
   한글은 대소문자가 없어 text-transform:uppercase가 무의미하고(라틴만 바뀐다), 자간 .1~.2em은
   음절을 벌려 읽기를 방해한다. 실제로 이 규칙 때문에 통계량 |t|가 화면에서 |T|로 찍힌 적이 있다. */
body{font-family:var(--sans);letter-spacing:-.003em}
h1,h2,h3,h4{letter-spacing:-.02em}
h1.title{font-family:var(--sans);font-weight:800;letter-spacing:-.032em;line-height:1.14}
/* 큰 제목은 본문 글꼴로. 고정폭 스택에서 한글은 Pretendard로, 라틴·숫자는 SF Mono로 떨어져
   한 제목 안에 두 글꼴이 섞인다("… RP 통합 (Multi-Sleeve Core)"가 그렇게 보였다).
   작은 머리글(h4 등)은 라틴 약어가 대부분이라 그대로 둔다.
   :not(._)은 특이도를 페이지 규칙(.dtop h2 같은 것)과 맞추려고 붙였다 — 요소 선택자만으로는
   페이지 쪽이 이긴다. !important를 쓰지 않으려는 최소 장치다. */
:is(h1,h2):not(._){font-family:var(--sans);letter-spacing:-.025em}
.eyebrow{font-family:var(--sans);font-weight:700;font-size:11px;letter-spacing:.06em}
.lbl{font-family:var(--sans);font-size:15px;font-weight:700;letter-spacing:-.012em;text-transform:none;color:var(--ink)}
.lbl::before{height:16px}
.lbl .sub{font-size:12.5px;font-weight:500}
.card .ch{font-family:var(--sans);font-size:11.5px;font-weight:600;letter-spacing:0;text-transform:none}
.chip{font-family:var(--sans);font-size:12px;font-weight:600;letter-spacing:-.006em;border-radius:999px}

/* ④ 숫자 — 자릿수가 흔들리면 세로로 비교할 수 없다. 표·지표값은 전부 고정폭 숫자로. */
.tnum,.num,.cv,.stat,table,code,kbd{font-variant-numeric:tabular-nums}

/* ⑤ 표 — 머리글은 한글이라 고정폭을 벗기고, 행에 hover를 준다(어느 줄을 읽는지 잃지 않게). */
.tbl{font-variant-numeric:tabular-nums}
.tbl thead th{font-family:var(--sans);font-size:11px;font-weight:600;letter-spacing:0;text-transform:none;color:var(--muted)}
.tbl tbody th{font-family:var(--sans);font-weight:700;letter-spacing:-.01em}
.tbl tbody tr:hover>*{background:color-mix(in srgb,var(--accent) 7%,transparent)}

/* ⑥ 잔손질 — 키보드 초점 링(전엔 브라우저 기본에 맡겨 다크에서 안 보였다), 선택색, 얇은 스크롤바 */
:where(a,button,summary,input,select,textarea,[tabindex]):focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:5px}
::selection{background:color-mix(in srgb,var(--accent) 30%,transparent)}
html{scrollbar-width:thin;scrollbar-color:var(--line) transparent}
"""


def pages() -> list[str]:
    out = []
    for d in PAGE_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".html") or fn in SKIP:
                continue
            p = os.path.join(d, fn)
            # 조각 파일(_build/pages/kb_content.html)은 <head>가 없다 — 셸을 갖는 쪽은
            # 이걸 끼워 넣는 kb.html이므로 여기서 다루지 않는다.
            # 여는 <head>만 본다 — 닫는 </head>는 <style>이 커서 파일 한참 뒤에 있다.
            if "<head" not in io.open(p, encoding="utf-8").read(2000):
                continue
            out.append(p)
    return out


def apply(html: str, shell: str) -> tuple[str, list[str]]:
    """셸 블록과 글꼴 링크를 넣거나 교체한다. 바꾸지 못하면 이유를 돌려준다."""
    why = []

    # ── 글꼴 링크 ──
    if FONT_BEGIN in html:
        html = re.sub(re.escape(FONT_BEGIN) + r".*?" + re.escape(FONT_END),
                      FONT_BEGIN + FONT_LINK + FONT_END, html, flags=re.S)
    else:
        m = re.search(r"<style>", html)
        if not m:
            return html, ["<style>가 없다"]
        html = html[:m.start()] + FONT_BEGIN + FONT_LINK + FONT_END + "\n" + html[m.start():]

    # ── 셸 블록 ──
    if SHELL_BEGIN in html:
        i = html.index(SHELL_BEGIN)
        j = html.index(SHELL_END, i) + len(SHELL_END)
        html = html[:i] + shell + html[j:]
    else:
        k = html.find("</style>")
        if k < 0:
            return html, ["</style>가 없다"]
        # 첫 </style>이 NAVCSS 구간이면 넣지 않는다 — sync_nav가 다음 실행에서 지운다.
        nav = html.find("<!-- NAVCSS:BEGIN -->")
        if 0 <= nav < k:
            return html, ["첫 </style>이 NAVCSS 구간 안이다 — 넣으면 sync_nav가 지운다"]
        html = html[:k] + "\n" + shell + "\n" + html[k:]
    return html, why


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="쓰지 않고 어긋난 파일만 보고")
    a = ap.parse_args()

    bad = check_contrast()
    if bad:
        for b in bad:
            print("  ✗ 대비 회귀:", b)
        print("중단 — 중립색을 고쳤으면 대비부터 맞춘다.")
        return 2

    shell = build_shell()
    changed, errs = [], []
    for p in pages():
        src = io.open(p, encoding="utf-8").read()
        new, why = apply(src, shell)
        if why:
            errs.append((p, why))
            continue
        if new != src:
            changed.append(os.path.relpath(p, ROOT))
            if not a.check:
                io.open(p, "w", encoding="utf-8").write(new)

    for p, why in errs:
        print("  ✗ %s — %s" % (os.path.relpath(p, ROOT), "; ".join(why)))
    lo = min(contrast(LIGHT[t], LIGHT["--panel"]) for t in ("--ink", "--ink-2", "--muted"))
    do = min(contrast(DARK[t], DARK["--panel"]) for t in ("--ink", "--ink-2", "--muted"))
    print("셸 %d바이트 · 최저 대비 라이트 %.2f:1 · 다크 %.2f:1" % (len(shell), lo, do))
    if a.check:
        if changed:
            print("어긋난 페이지 %d장: %s" % (len(changed), ", ".join(changed)))
        else:
            print("전 페이지 셸 일치")
        return 1 if (changed or errs) else 0
    print("셸 전파 — 바뀐 페이지 %d장" % len(changed))
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
