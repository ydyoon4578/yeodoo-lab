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
           공용 의미색 4종(--hot/--marg/--deploy/--accent — 아래 SHARED),
           셸 타이포(제목·섹션 라벨·카드 머리글·표 머리·칩), 숫자 정렬(tabular-nums).
  안 바꾼다 — 국면(--rg-*)·심리(--sn-*)·등급(--gA~F)·--champ·--rp.
           대비를 맞춰 고른 값이라 손대면 국면·심리·등급 표시가 한꺼번에 흔들린다.
           색을 바꿀 때는 아래 check_contrast()로 **셸이 소유한 배경 3종 전부에서**
           AA(4.5:1)를 넘는지, 그리고 이전보다 나빠지지 않는지 검사한다.

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
# 🚨 2026-08-09 팔레트 교체 — 사용자 지적 "클로드 특유의 인터페이스 구성방식이 맘에 안 든다".
#   따뜻한 크림 + 골드 accent 는 그 인상의 큰 몫이었다. 중립 잉크 + 파랑 하나로 바꾸고
#   --shadow 를 none 으로 둔다(카드가 떠 보이는 것이 그 인상의 나머지 몫이다).
#   ⚠ 바꾸기 전에 대비를 먼저 계산했다 — check_contrast 가 최저 라이트 5.17:1 · 다크 6.35:1
#     로 이전보다 높다. 처음 고른 --muted 는 panel-2 위에서 4.14 로 AA 미달이라 되물렀다.
LIGHT = {
    "--ground": "#FBFAF7", "--panel": "#FBFAF7", "--panel-2": "#F2F0EB",
    "--line": "#D8D6D0", "--line-soft": "#EDEBE6",
    # --muted 는 2026-08-02 에 #6A737D → #646B74 로 내렸다. 이전 값은 --panel 위에서만 4.73:1 로
    # AA 를 넘었고 --ground 4.49 · --panel-2 4.18 이었다 — 게이트가 --panel 하나만 보고 있어서
    # 통과하던 조합만 검사하고 승인해 온 것이다(check_contrast 참조). 이 색이 붙은 자리가 하필
    # 표 각주(.stnote)·캘린더 지표명·칩 보조글자라 본문보다 각주가 흐린 상태였다.
    "--ink": "#111418", "--ink-2": "#3E444B", "--muted": "#5F656D",
    # 그림자를 없앤다 — 이 사이트의 화면은 대부분 표다. 표를 카드에 얹어 띄울 이유가 없다.
    "--shadow": "none",
}
DARK = {
    "--ground": "#0C0E11", "--panel": "#0C0E11", "--panel-2": "#161A1F",
    "--line": "#252A30", "--line-soft": "#1A1E23",
    "--ink": "#DEE3E8", "--ink-2": "#AEB6BE", "--muted": "#949DA6",
    "--shadow": "none",
}
# 셸이 소유하는 의미색. 색을 '바꾸는' 것이 아니라 **있게 보장하고 대비를 잠그는** 것이다.
# 처음엔 --hot·--marg 둘뿐이었다 — 내비(sync_nav.py 생성)의 .asofchip.stale이 var(--hot)을
# 쓰는데 explorer·signals에는 그 정의가 없어, 기준일이 낡았다는 표시가 아무 색도 없이 나왔다.
# 공용 블록이 쓰는 토큰은 페이지마다 챙길 것이 아니라 셸이 책임진다.
#
# 2026-08-02 에 --deploy·--accent 를 여기로 올렸다. 이유는 두 가지다.
#   ① 대비 게이트가 볼 수 없었다. 두 토큰은 25장의 각 :root 에만 있어 이 파일이 값을 모르고,
#      모르는 값은 잠글 수 없다. 실제로 --deploy 는 라이트 3배경에서 4.31/4.09/3.82 로 전부
#      AA 미달인 채 오래 배포돼 있었다 — 상승 숫자만 흐리고 하락(--hot 5.59)은 또렷한
#      비대칭이라, 같은 표가 실제보다 나빠 보였다.
#   ② 25장이 같은 값을 각자 들고 있었다(실측: --accent 25장 동일, --deploy 19장 동일).
#      한 곳에서 못 바꾸는 색은 언젠가 갈라진다.
# 라이트 4종은 이때 3배경 모두에서 AA(4.5) 를 넘도록 내렸다(색상은 유지, 명도만):
#   --muted #6A737D→#646B74 · --deploy #0E8A54→#0C7A4A · --marg #B25E12→#A35510 · --accent #8A6B00→#816400
# 다크는 전부 5.07:1 이상이라 손대지 않는다.
SHARED = {"light": {"--hot": "#A3352A", "--marg": "#7E5200",
                    "--deploy": "#0A7040", "--accent": "#0A5697"},
          "dark": {"--hot": "#E8887A", "--marg": "#DFAE55",
                   "--deploy": "#4BD08D", "--accent": "#6FB6EA"}}

# 이전 값 — 대비가 나빠지지 않았는지 비교하는 기준선이다.
# 배경을 3종으로 넓히면서(2026-08-02) 이전 배경값도 함께 적는다. 의미색 4종은 이번에 게이트로
# 들어오므로 기준선은 '고치기 직전 값'이다 — 그 값들이 실제로 AA 미달이었고, 넓힌 목적이
# 바로 그것을 잡는 것이다. 미달분은 아래 규칙상 '나빠짐'이 아니라 'AA 미달'로 잡힌다.
OLD_LIGHT = {"--panel": "#FFFFFF", "--ground": "#F5F7FA", "--panel-2": "#EEF2F6",
             "--ink": "#1B2733", "--ink-2": "#42505E", "--muted": "#66757F",
             "--deploy": "#0E8A54", "--marg": "#B25E12", "--hot": "#A64B3B", "--accent": "#8A6B00"}
OLD_DARK = {"--panel": "#181E26", "--ground": "#0F141A", "--panel-2": "#20272F",
            "--ink": "#EAEEF2", "--ink-2": "#C4CDD6", "--muted": "#8A97A3",
            "--deploy": "#38D083", "--marg": "#F0863C", "--hot": "#E5806A", "--accent": "#FFBC00"}

# 게이트가 보는 조합. 배경 3종을 전부 보는 것이 핵심이다 — --panel 하나만 보던 때는
# 통과하는 조합만 검사하고 승인했다(--muted 는 panel 4.73 으로 통과하면서 panel-2 4.18).
GATE_FG = ("--ink", "--ink-2", "--muted", "--deploy", "--marg", "--hot", "--accent")
GATE_BG = ("--panel", "--ground", "--panel-2")


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


def palette(mode: str) -> dict:
    """셸이 소유한 색 전부 — 중립색 + 공용 의미색. 게이트와 CSS 생성이 같은 것을 본다."""
    return dict(LIGHT if mode == "light" else DARK, **SHARED[mode])


def check_contrast() -> list[str]:
    """셸이 소유한 글자색이 셸이 소유한 **모든 배경** 위에서 AA를 넘는지. 못 넘으면 배포를 막는다.

    화면에서 제일 자주 밟는 회귀가 '색을 예쁘게 바꿨더니 흐린 글씨가 안 보이는 것'이다.
    눈으로는 늦게 알아채므로 숫자로 잠근다(본문 4.5:1 기준은 WCAG AA).

    ⚠ 전에는 배경을 --panel 하나만 봤다. 그건 검사가 아니라 **통과하는 조합만 골라 보는
       것**이었다 — --muted 는 panel 4.73 으로 통과하면서 ground 4.49 · panel-2 4.18 이었고,
       하필 그 색이 표 각주와 캘린더 지표명에 붙어 있었다. 배경은 셸이 소유한 3종을 전부 본다.

    ⚠ '이전보다 조금이라도 낮으면 실패'로 두면 안 된다. 14.4:1이 14.2:1이 되는 건 눈에
       보이지 않는 변화이고, 그걸 막으면 색을 영원히 못 고친다. 그래서 **선 근처(AAA 7:1
       미만)에서만** 하락을 막고, 그 위에서는 AA만 지키면 통과시킨다.

    검사 대상이 아닌 것 — 국면(--rg-*)·심리(--sn-*)·등급(--gA~F) 계열. 앞의 둘은 20px bold
    대표값(큰 글자 3:1)이고 마지막은 흰 글자를 얹는 배지 배경이라, 본문 4.5:1 잣대를 그대로
    들이대면 잘못 막는다. 이 계열은 페이지가 소유하며 각자 주석에 근거를 적어 두었다."""
    bad = []
    for name, mode, old in (("라이트", "light", OLD_LIGHT), ("다크", "dark", OLD_DARK)):
        new = palette(mode)
        for fg in GATE_FG:
            for bg in GATE_BG:
                n = contrast(new[fg], new[bg])
                o = contrast(old[fg], old[bg])
                if n < 4.5:
                    bad.append("%s %s on %s 대비 %.2f:1 — AA(4.5) 미달" % (name, fg, bg, n))
                elif o < 7.0 and n < o - 0.15:
                    bad.append("%s %s on %s 대비 %.2f:1 — 이전 %.2f:1보다 나빠짐(선 근처)"
                               % (name, fg, bg, n, o))
    return bad


def _decl(d: dict) -> str:
    return "".join("%s:%s;" % (k, v) for k, v in d.items())


def build_shell() -> str:
    # % 서식 대신 치환을 쓴다 — CSS에 color-mix(… 7%) 처럼 %가 그대로 들어간다.
    css = (SHELL_BEGIN + _CSS.replace("@LIGHT@", _decl(palette("light")))
           .replace("@DARK@", _decl(palette("dark")))
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
     이런 건 페이지마다 챙길 것이 아니라 셸이 보장할 것이다.
     🚨 2026-08-10 — --w-wide 를 1440 → 1680 으로 올렸다(사용자 요청 '화면을 최대한 넓게').
       홈은 자료 화면이다. 종목 히트맵이 518칸을 그리는데 폭이 곧 읽히는 종목 수다 —
       1200px 에서는 가장 작은 칸이 7×10px 라 글자가 안 들어갔다.
       ⚠ 내비(.topnav .nvin)도 이 토큰을 쓴다. 본문만 넓히면 내비보다 본문이 넓어져
         화면이 어긋나 보인다 — 그래서 페이지가 아니라 여기서 바꾼다.
       ⚠ --w-read 는 글이 주인 화면이다. 한 줄이 길어지면 읽기 나빠지므로 가장 덜 늘린다 —
         넓게 쓰는 것과 아무 데나 늘리는 것은 다르다.
     🚨 2026-08-19 — **고정 px 를 걷고 화면에 맞춘다**(사용자 지적 "사이트 전체에서 빈공간이
       절반이야, 내 화면 기준"). 종전에는 상한이 1680/1200/980 고정이라 2560px 화면에서
       본문이 각각 66%/47%/38% 만 썼다. 남는 절반은 배경이었다.
       → min(뷰포트 비율, 상한) 으로 바꾼다. 좁은 화면에서는 vw 가 이겨 종전과 같고,
         넓은 화면에서만 상한까지 늘어난다. 세 층 구조는 그대로 둔다 —
         층을 없애면 «글 화면» 이 표 화면만큼 넓어져 읽기가 나빠진다.
       ⚠ 상한을 무한히 두지 않는 이유: 표·차트는 넓을수록 낫지만 글줄은 아니고,
         내비(.topnav .nvin)도 같은 토큰을 쓰기 때문에 통째로 늘어난다. */
  --w-wide:min(96vw,2240px);--w-base:min(94vw,1600px);--w-read:min(92vw,1120px);
}
/* 넓은 층 한 벌 — 종전에는 intraday·rates 가 **각자** 이 한 줄을 갖고 있었다.
   그래서 다른 페이지를 넓은 층으로 올리려면 CSS 를 또 복사해야 했고, 실제로 guru 를
   올렸더니 class 만 붙고 아무 일도 안 일어났다(2026-08-19 실측). 셸이 보장한다.
   ⚠ 대체값(fallback)을 두지 않는다 — 토큰은 바로 위에서 셸이 반드시 정의한다. */
.wrap.wide{max-width:var(--w-wide)}

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
.chip{font-family:var(--sans);font-size:12px;font-weight:600;letter-spacing:-.006em;border-radius:2px}

/* ④ 숫자 — 자릿수가 흔들리면 세로로 비교할 수 없다. 표·지표값은 전부 고정폭 숫자로. */
.tnum,.num,.cv,.stat,table,code,kbd{font-variant-numeric:tabular-nums}

/* ⑤ 표 — 머리글은 한글이라 고정폭을 벗기고, 행에 hover를 준다(어느 줄을 읽는지 잃지 않게). */
.tbl{font-variant-numeric:tabular-nums}
.tbl thead th{font-family:var(--sans);font-size:11px;font-weight:600;letter-spacing:0;text-transform:none;color:var(--muted)}
.tbl tbody th{font-family:var(--sans);font-weight:700;letter-spacing:-.01em}
.tbl tbody tr:hover>*{background:color-mix(in srgb,var(--accent) 7%,transparent)}

/* ⑥ 잔손질 — 키보드 초점 링(전엔 브라우저 기본에 맡겨 다크에서 안 보였다), 선택색, 얇은 스크롤바 */
:where(a,button,summary,input,select,textarea,[tabindex]):focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:2px}
::selection{background:color-mix(in srgb,var(--accent) 30%,transparent)}
html{scrollbar-width:thin;scrollbar-color:var(--line) transparent}

/* ⑦ 장식 걷기 (2026-08-09) — 사용자 지적 "클로드 특유의 인터페이스 구성방식".
   그 인상의 정체는 색만이 아니다. **떠 있는 둥근 카드**와 **알약 배지**가 나머지 몫이다.
   팔레트는 위에서 바꿨고 여기서 형태를 걷는다.

   🚨 범위를 좁게 잡는다. 페이지마다 컴포넌트가 다르고, 전부에 border-radius:0 을 걸면
     입력창·버튼까지 각져 오히려 쓰기 나빠진다. **떠 보이게 하는 것**만 끈다:
       · box-shadow — 토큰(--shadow:none)으로 이미 죽지만, 값을 손으로 박은 자리가 남아 있다
       · 큰 모서리(2px 이상) — 카드가 카드처럼 보이는 반경. 작은 반경(칩·입력)은 둔다
   ⚠ :where() 로 감싸 특이도 0 으로 둔다 — 페이지가 의도적으로 다르게 준 곳은 그대로 이긴다.
     셸이 페이지를 이겨서는 안 된다(이 블록의 원칙이다). */
:where(.card,.scard,.rep,.panel,.box,.tile,.sec,details,.toc,table,.tbl,.search,.controls,
       .asoftbl,.asofrow,.calgrid,.calcell,.chiprow,.statline){box-shadow:none}
:where(.card,.scard,.rep,.panel,.box,.tile,.asoftbl,.calgrid,details.toc){border-radius:3px}
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
            # 조각 파일(_build/pages/*_content.html)은 <head>가 없다 — 셸을 갖는 쪽은
            # 이걸 끼워 넣는 게이트 페이지이므로 여기서 다루지 않는다.
            # 여는 <head>만 본다 — 닫는 </head>는 <style>이 커서 파일 한참 뒤에 있다.
            # 🚨 접두 문자열 "<head" 로 보면 안 된다. **"<header" 가 걸린다.**
            #   2026-08-11 에 sources_content.html 조각이 <header class="mast"> 로 시작해서
            #   실제로 걸렸고, 조각을 셸 대상으로 오인해 "<style>가 없다"로 실패시켰다.
            #   kb_content.html 은 우연히 앞머리에 <header 가 없어 그동안 안 드러났을 뿐이다.
            if not re.search(r"<head[\s>]", io.open(p, encoding="utf-8").read(2000)):
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
    # 보고하는 최저값은 게이트가 보는 조합과 같아야 한다 — 전에는 --panel 위 3색만 재서
    # 화면에 5.29 를 찍으면서 실제 최저(panel-2 위 4.18)는 말하지 않았다. 검사와 보고가
    # 다른 것을 보면, 통과 메시지가 통과를 뜻하지 않게 된다.
    def _lo(mode):
        pal = palette(mode)
        return min(contrast(pal[f], pal[b]) for f in GATE_FG for b in GATE_BG)
    print("셸 %d바이트 · 최저 대비(전경 %d × 배경 %d) 라이트 %.2f:1 · 다크 %.2f:1"
          % (len(shell), len(GATE_FG), len(GATE_BG), _lo("light"), _lo("dark")))
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
