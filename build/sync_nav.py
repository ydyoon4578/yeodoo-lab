#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""내비게이션 정본 전파기.

빌드 스텝이 없는 사이트에서 22장의 HTML이 같은 메뉴를 갖게 하는 유일한 방법은
"한 곳에서 만들어 전부에 밀어넣고, 어긋나면 CI가 막는" 것이다. 이 스크립트가 그 한 곳이다.

  build/nav_items.json   ← 메뉴 정본(사람이 고치는 유일한 파일)
        │
        ├─ build/nav_head.html   생성: <head>에 들어갈 메뉴 CSS
        └─ build/nav_body.html   생성: <body> 최상단에 들어갈 메뉴 마크업 + JS
                │
                └─ 전 HTML의 NAVCSS:BEGIN~END / NAV:BEGIN~END 구간을 치환

설계상 지키는 것:
- **블록은 전 페이지에서 바이트 동일하다.** 현재 페이지 강조는 마크업이 아니라
  <body data-tool="…">를 JS가 읽어 aria-current를 다는 방식이라, 페이지마다 다른
  글자가 블록 안에 없다. 그래야 해시 한 개로 22장을 한꺼번에 검증할 수 있다.
- **없는 파일은 링크하지 않는다.** 슬롯은 40개지만 파일은 단계적으로 생긴다.
  디스크에 없으면 <a>가 아니라 <span>+'준비중'으로 렌더해 404를 만들지 않는다.
  파일이 생기면 이 스크립트를 다시 돌리는 것만으로 메뉴가 저절로 켜진다.
- **판정 배지는 손으로 적지 않는다.** verdict는 nav_items.json에 있지만
  validate_site.py가 data/verdicts.json과 대조하므로 원장과 어긋나면 CI가 실패한다.

사용:
    python3 build/sync_nav.py            # 생성 + 전파
    python3 build/sync_nav.py --check    # 전파하지 않고 어긋난 파일만 보고(CI용)
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS = os.path.join(ROOT, "build", "nav_items.json")
OUT_HEAD = os.path.join(ROOT, "build", "nav_head.html")
OUT_BODY = os.path.join(ROOT, "build", "nav_body.html")

# 잠금 페이지는 래퍼(게이트)와 평문 페이로드가 각각 셸을 갖는다 — 양쪽 다 대상이다.
PAGE_DIRS = [ROOT, os.path.join(ROOT, "_build", "pages")]

CSS_BEGIN, CSS_END = "<!-- NAVCSS:BEGIN -->", "<!-- NAVCSS:END -->"
NAV_BEGIN, NAV_END = "<!-- NAV:BEGIN -->", "<!-- NAV:END -->"
HOME_BEGIN, HOME_END = "<!-- HOMEDIR:BEGIN -->", "<!-- HOMEDIR:END -->"   # 홈에만 있는 선택 구간

VERDICT_LABEL = {
    "pass": ("통과", "vpass"),
    "marginal": ("제한적", "vmarg"),
    "unverified": ("미검증", "vunv"),
    "rejected": ("기각", "vrej"),
    "na": (None, None),        # 배지를 달지 않는다 — 판정 대상이 아닌 원문·메타 화면
}

BRAND_SVG = (
    '<svg viewBox="0 0 32 32" aria-hidden="true">'
    '<rect width="32" height="32" rx="7" fill="currentColor" opacity=".12"/>'
    '<path d="M6 22 L13 15 L18 19 L26 8" fill="none" stroke="var(--accent)" stroke-width="2.6" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '<circle cx="26" cy="8" r="2.4" fill="var(--accent)"/></svg>'
)


def esc(s: str) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def load_items() -> dict:
    with io.open(ITEMS, encoding="utf-8") as f:
        return json.load(f)


def page_exists(href: str, anchor_kind: str | None = None) -> bool:
    """슬롯이 실제로 열리는가.

    파일만 보고 판정하면 '파일은 있는데 그 섹션은 아직 없는' 앵커 슬롯이
    '동작 중'으로 잡힌다(regime.html#axes가 그랬다). 앵커는 종류를 나눠서 본다:
      static  — HTML에 id가 실제로 있어야 한다(기본값. 증명 못 하면 준비중)
      route   — JS 해시 라우터가 해석한다(stocks.html#p=up). 파일만 있으면 된다
      runtime — JS가 렌더하며 만드는 id. 파일만 있으면 된다
    """
    path, _, anc = href.partition("#")
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return False
    if not anc or (anchor_kind or "static") != "static":
        return True
    try:
        with io.open(full, encoding="utf-8") as f:
            return ('id="%s"' % anc) in f.read()
    except Exception:
        return False


def tool_live(t: dict) -> bool:
    """열리는 도구인가.

    placeholder=true 는 탭·앵커는 있지만 내용이 '어떤 데이터가 없어서 비었는지'뿐인 칸이다.
    앵커가 존재한다는 이유로 동작에 넣으면 홈의 계수 줄('동작 N')이 거짓이 된다 —
    빈 탭 6칸(co #fs/#ir/#ins · valuation #ddm/#rim/#index)이 실제로 그렇게 잡혔었다.
    """
    if t.get("placeholder"):
        return False
    return page_exists(t["file"], t.get("anchor"))


# ── 메뉴 CSS ────────────────────────────────────────────────────────────────
# 기존 SA 셸의 토큰(--panel/--line/--accent/--mono …)만 쓴다. 새 색을 만들지 않는다.
NAV_CSS = """<style>
  /* ── 메가메뉴(build/sync_nav.py 생성 — 직접 고치지 말 것) ────────────────
     카테고리 × 슬롯 구조(개수는 nav_items.json 이 정한다). 데스크톱은 카테고리 버튼 → 패널, 모바일은 드로어 + 아코디언.
     현재 위치 강조는 <body data-tool>을 JS가 읽는다(블록을 전 페이지 바이트 동일하게 유지). */

  /* 배지 색은 자체 토큰으로 들고 간다 — 페이지마다 --deploy/--marg/--champ 보유가 달라
     (잠금 래퍼 4장엔 없다) 페이지 팔레트에 기대면 22장에서 다르게 보인다. */
  :root{--nv-pass:#0E8A54;--nv-marg:#B25E12;--nv-unv:#66757F;--nv-rej:#A64B3B;--nv-soon:#2C6E8F}
  @media(prefers-color-scheme:dark){:root{--nv-pass:#38D083;--nv-marg:#F0863C;--nv-unv:#8A97A3;--nv-rej:#E5806A;--nv-soon:#6BB0D6}}
  :root[data-theme="light"]{--nv-pass:#0E8A54;--nv-marg:#B25E12;--nv-unv:#66757F;--nv-rej:#A64B3B;--nv-soon:#2C6E8F}
  :root[data-theme="dark"]{--nv-pass:#38D083;--nv-marg:#F0863C;--nv-unv:#8A97A3;--nv-rej:#E5806A;--nv-soon:#6BB0D6}
  .skiplink{position:absolute;left:-9999px;top:0;z-index:100;background:var(--panel);color:var(--ink);
            padding:10px 16px;border:1px solid var(--accent);border-radius:0 0 2px 0;font-family:var(--mono);font-size:13px}
  .skiplink:focus{left:0}
  .topnav{position:sticky;top:0;z-index:60;background:color-mix(in srgb,var(--panel) 92%,transparent);
          backdrop-filter:saturate(1.4) blur(10px);-webkit-backdrop-filter:saturate(1.4) blur(10px);
          border-bottom:1px solid var(--line)}
  .topnav .nvin{max-width:var(--w-wide,1440px);margin:0 auto;padding:0 20px;height:52px;
                display:flex;align-items:center;gap:10px}
  .topnav .brand{display:inline-flex;align-items:center;gap:9px;font-family:var(--sans);font-weight:800;
                 font-size:15px;color:var(--ink);text-decoration:none;letter-spacing:-.01em;flex:none}
  .topnav .brand svg{width:22px;height:22px;flex:none}
  .navsp{flex:1}

  .navcats{display:flex;align-items:center;gap:1px;margin:0 0 0 6px;padding:0;list-style:none}
  .navcat{position:relative}
  .navcat>button{font-family:var(--sans);font-size:13px;font-weight:600;color:var(--ink-2);
                 background:none;border:0;cursor:pointer;padding:7px 9px;border-radius:2px;white-space:nowrap;
                 display:inline-flex;align-items:center;gap:3px}
  .navcat>button:hover{background:var(--panel-2);color:var(--accent)}
  .navcat>button[aria-expanded="true"]{background:var(--panel-2);color:var(--accent)}
  .navcat.on>button{color:var(--accent)}
  .navcat.on>button::after{content:"";position:absolute;left:9px;right:9px;bottom:-1px;height:2px;background:var(--accent);border-radius:2px}
  .navcat .cv{font-size:11px;opacity:.55;transition:transform .12s}
  .navcat>button[aria-expanded="true"] .cv{transform:rotate(180deg)}

  .mmpanel{position:absolute;top:calc(100% + 5px);left:0;min-width:320px;max-width:min(560px,92vw);
           background:var(--panel);border:1px solid var(--line);border-radius:2px;box-shadow:var(--shadow);
           padding:7px;z-index:70}
  .mmpanel[hidden]{display:none}
  .navcat:last-child .mmpanel,.navcat:nth-last-child(2) .mmpanel{left:auto;right:0}
  .mmi{display:grid;grid-template-columns:1fr auto;gap:1px 8px;align-items:baseline;
       padding:8px 10px;border-radius:2px;text-decoration:none;color:inherit}
  a.mmi:hover{background:var(--panel-2)}
  a.mmi:hover .mmn{color:var(--accent)}
  .mmi .mmn{font-family:var(--sans);font-size:13px;font-weight:600;color:var(--ink);line-height:1.35;letter-spacing:-.012em}
  .mmi .mmd{grid-column:1/-1;font-size:11px;color:var(--muted);line-height:1.45}
  .mmi[aria-current="page"]{background:color-mix(in srgb,var(--accent) 10%,transparent)}
  .mmi[aria-current="page"] .mmn{color:var(--accent)}
  span.mmi{cursor:default}
  span.mmi .mmn{color:var(--muted);font-weight:600}
  .mmb{font-family:var(--sans);font-size:11px;font-weight:700;border-radius:2px;padding:2px 6px;white-space:nowrap;
       border:1px solid color-mix(in srgb,var(--mmc,var(--muted)) 40%,transparent);
       background:color-mix(in srgb,var(--mmc,var(--muted)) 12%,transparent);color:var(--mmc,var(--muted))}
  .mmb.vpass{--mmc:var(--nv-pass)} .mmb.vmarg{--mmc:var(--nv-marg)}
  .mmb.vunv{--mmc:var(--nv-unv)}   .mmb.vrej{--mmc:var(--nv-rej)}
  .mmb.soon{--mmc:var(--nv-soon)}  .mmb.wont{--mmc:var(--nv-unv)}
  .mmlk{font-size:11px;opacity:.6;margin-left:3px;vertical-align:1px}

  .asofchip{display:none;align-items:center;gap:6px;font-family:var(--mono);font-size:11px;
            color:var(--ink-2);text-decoration:none;border:1px solid var(--line);border-radius:2px;
            padding:4px 9px;white-space:nowrap;flex:none}
  .asofchip:hover{border-color:var(--accent);color:var(--accent)}
  .asofchip .ac1{color:var(--muted);font-size:11px;letter-spacing:.06em;text-transform:uppercase}
  .asofchip.stale{border-color:var(--hot);color:var(--hot)}
  .asofchip.ready{display:inline-flex}
  .themebtn{width:32px;height:32px;border-radius:2px;border:1px solid var(--line);background:var(--panel);
            color:var(--ink-2);cursor:pointer;font-size:14px;display:inline-flex;align-items:center;
            justify-content:center;flex:none}
  .themebtn:hover{border-color:var(--accent)}
  .navtoggle{display:none;width:34px;height:32px;border-radius:2px;border:1px solid var(--line);
             background:var(--panel);color:var(--ink-2);cursor:pointer;font-size:15px;align-items:center;
             justify-content:center;flex:none}

  /* ── 모바일: 카테고리 줄을 드로어로 접는다 ───────────────────────────── */
  @media(max-width:1100px){
    /* ⚠ backdrop-filter를 반드시 끈다 — 장식이 아니라 **레이아웃 버그의 원인**이다.
       filter·backdrop-filter·transform이 걸린 요소는 자손 position:fixed의 컨테이닝 블록이
       된다(뷰포트가 아니라). 아래 .navcats는 fixed 드로어인데 .topnav(높이 52px)가 기준이 되면
       top:52px·bottom:0이 52px짜리 상자 안에서 계산돼 **드로어 높이가 0이 된다**.
       실측(2026-07-25): 필터 있음 0px · 제거 859px. 화면에는 첫 카테고리만 삐져나와
       "모바일에서 시장밖에 안 보인다"로 나타났다.
       블러를 끄는 대신 배경을 불투명하게 만들어 스티키 바 가독성을 지킨다. */
    .topnav{backdrop-filter:none;-webkit-backdrop-filter:none;background:var(--panel)}
    .topnav .nvin{gap:8px;padding:0 14px}
    .navtoggle{display:inline-flex}
    .navcats{position:fixed;top:52px;left:0;right:0;bottom:0;display:block;margin:0;padding:8px 14px 40px;
             background:var(--ground);border-top:1px solid var(--line);overflow-y:auto;-webkit-overflow-scrolling:touch}
    .navcats[hidden]{display:none}
    .navcat{position:static;border-bottom:1px solid var(--line-soft)}
    .navcat>button{width:100%;justify-content:space-between;padding:13px 4px;font-size:13.5px}
    .navcat.on>button::after{display:none}
    .mmpanel{position:static;min-width:0;max-width:none;border:0;box-shadow:none;background:none;
             padding:0 0 8px 4px;border-radius:0}
    .mmi{padding:9px 8px}
  }
  @media(min-width:1101px){ .navcats[hidden]{display:flex} }
  @media(prefers-reduced-motion:reduce){.navcat .cv{transition:none}}
</style>"""


def build_body(items: dict) -> str:
    """<body> 최상단에 들어갈 메뉴 마크업 + 동작 스크립트."""
    out = []
    out.append('<a class="skiplink" href="#main">본문 바로가기</a>')
    out.append('<nav class="topnav" aria-label="주 메뉴">')
    out.append('  <div class="nvin">')
    out.append('    <a class="brand" href="index.html">%s 여두 전략 랩</a>' % BRAND_SVG)
    out.append('    <button class="navtoggle" id="navtoggle" aria-expanded="false" '
               'aria-controls="navcats" aria-label="메뉴 열기">☰</button>')
    out.append('    <ul class="navcats" id="navcats">')

    for c in items["categories"]:
        pid = "mm-" + c["slug"]
        out.append('      <li class="navcat" data-cat="%s">' % esc(c["slug"]))
        out.append('        <button aria-expanded="false" aria-controls="%s">%s<span class="cv" aria-hidden="true">▼</span></button>'
                   % (pid, esc(c["short"])))
        out.append('        <div class="mmpanel" id="%s" hidden role="group" aria-label="%s">'
                   % (pid, esc(c["name"])))
        for t in c["tools"]:
            href, name, desc = t["file"], t["name"], t["desc"]
            live = tool_live(t)
            lab, cls = VERDICT_LABEL.get(t.get("verdict") or "na", (None, None))

            if t["status"] == "wont-build":
                badge = '<span class="mmb wont">미제작</span>'
            elif not live:
                badge = '<span class="mmb soon">준비중</span>'
            elif lab:
                badge = '<span class="mmb %s">%s</span>' % (cls, lab)
            else:
                badge = ""

            lk = '<span class="mmlk">🔒</span>' if t.get("locked") else ""
            inner = ('<span class="mmn">%s%s</span>%s<span class="mmd">%s</span>'
                     % (esc(name), lk, badge, esc(desc)))
            if live:
                out.append('          <a class="mmi" href="%s" data-nav="%s">%s</a>'
                           % (esc(href), esc(href), inner))
            else:
                # 없는 파일로 링크하지 않는다 — 404 대신 '준비중'을 보여준다
                out.append('          <span class="mmi">%s</span>' % inner)
        out.append('        </div>')
        out.append('      </li>')

    out.append('    </ul>')
    out.append('    <span class="navsp"></span>')
    # sources.html은 공개 페이지다(2026-07-25 잠금 해제) — nofollow를 걸지 않는다
    out.append('    <a class="asofchip" id="navasof" href="sources.html">'
               '<span class="ac1">기준일</span><b id="navasofv">—</b></a>')
    out.append('    <button class="themebtn" id="themebtn" aria-label="테마 전환" title="라이트/다크 전환">◐</button>')
    out.append('  </div>')
    out.append('</nav>')
    out.append(NAV_JS)
    return "\n".join(out)


NAV_JS = r"""<script>
(function(){
  var root=document.documentElement;
  // ── 테마 ── (초기 적용은 <head> 인라인 스크립트가 이미 했다 — 여기서 다시 하면 이중 실행)
  var tb=document.getElementById('themebtn');
  if(tb)tb.addEventListener('click',function(){
    var cur=root.getAttribute('data-theme')||(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');
    var next=cur==='dark'?'light':'dark'; root.setAttribute('data-theme',next);
    try{localStorage.setItem('yeouido-theme',next);}catch(e){}
  });

  // ── 현재 위치: 마크업이 아니라 <body data-tool>에서 읽는다(메뉴 블록을 전 페이지 동일하게 유지) ──
  var cur=(document.body.getAttribute('data-tool')||'').trim();
  if(cur){
    var a=document.querySelector('.mmi[data-nav="'+cur.replace(/"/g,'')+'"]');
    if(a){a.setAttribute('aria-current','page');
      var li=a.closest('.navcat'); if(li)li.classList.add('on');}
  }

  // ── 카테고리 패널 ──
  var cats=[].slice.call(document.querySelectorAll('.navcat'));
  var drawer=document.getElementById('navcats'), toggle=document.getElementById('navtoggle');
  function mobile(){return matchMedia('(max-width:1100px)').matches;}
  function closeAll(except){
    cats.forEach(function(li){
      var b=li.querySelector('button'), p=li.querySelector('.mmpanel');
      if(li===except||!b||!p)return;
      b.setAttribute('aria-expanded','false'); p.hidden=true;
    });
  }
  cats.forEach(function(li){
    var b=li.querySelector('button'), p=li.querySelector('.mmpanel');
    if(!b||!p)return;
    b.addEventListener('click',function(e){
      e.stopPropagation();
      var open=b.getAttribute('aria-expanded')==='true';
      if(!mobile())closeAll(li);          // 데스크톱은 한 번에 하나만, 모바일 아코디언은 여러 개 허용
      b.setAttribute('aria-expanded',open?'false':'true'); p.hidden=open;
    });
  });
  // 드로어(모바일)
  if(toggle&&drawer){
    drawer.hidden=mobile();
    toggle.addEventListener('click',function(e){
      e.stopPropagation();
      var open=toggle.getAttribute('aria-expanded')==='true';
      toggle.setAttribute('aria-expanded',open?'false':'true');
      drawer.hidden=open; toggle.textContent=open?'☰':'✕';
      toggle.setAttribute('aria-label',open?'메뉴 열기':'메뉴 닫기');
    });
    // 폭이 바뀌면 드로어 상태를 그 폭의 기본값으로 되돌린다(데스크톱에서 hidden이 남으면 메뉴가 사라진다)
    var mq=matchMedia('(max-width:1100px)');
    (mq.addEventListener?mq.addEventListener.bind(mq,'change'):mq.addListener.bind(mq))(function(){
      drawer.hidden=mobile();
      if(toggle){toggle.setAttribute('aria-expanded','false');toggle.textContent='☰';}
      closeAll(null);
    });
  }
  document.addEventListener('click',function(){ if(!mobile())closeAll(null); });
  document.addEventListener('keydown',function(e){
    if(e.key!=='Escape')return;
    closeAll(null);
    if(toggle&&toggle.getAttribute('aria-expanded')==='true'){
      toggle.setAttribute('aria-expanded','false');toggle.textContent='☰';
      if(drawer)drawer.hidden=true; toggle.focus();
    }
  });

  // ── 기준일 칩: data/asof.json 정본 하나만 읽는다(페이지마다 다른 날짜를 적지 않는다) ──
  function bdGap(d){
    var p=String(d||'').split('-'); if(p.length!==3)return 0;
    var x=new Date(Date.UTC(+p[0],+p[1]-1,+p[2])), t=new Date(), n=0;
    var end=Date.UTC(t.getFullYear(),t.getMonth(),t.getDate());
    while(x.getTime()<end&&n<40){x.setUTCDate(x.getUTCDate()+1);var w=x.getUTCDay();if(w!==0&&w!==6)n++;}
    return n;
  }
  fetch('data/asof.json',{cache:'no-cache'}).then(function(r){return r.ok?r.json():null;}).then(function(j){
    if(!j||!j.primary)return;
    var el=document.getElementById('navasof'), v=document.getElementById('navasofv');
    if(!el||!v)return;
    v.textContent=j.primary; el.classList.add('ready');
    var n=bdGap(j.primary);
    if(n>=3){el.classList.add('stale');el.title='데이터가 '+n+'영업일 지연 — 자동갱신 확인 필요';}
    else{el.title='데이터 기준일 '+j.primary+' · 축별 기준일은 출처 페이지 참조';}
  }).catch(function(){});
})();
</script>"""


def digest_of(*blocks: str) -> str:
    return hashlib.sha256("\n".join(blocks).encode("utf-8")).hexdigest()[:16]


def badge_of(t: dict):
    """메뉴에 실제로 찍히는 배지 — 홈 분포 막대도 같은 규칙을 써야 한다.
    (메뉴는 '준비중'인데 홈 막대는 '미검증'으로 세면 같은 화면이 두 말을 한다.)"""
    if t["status"] == "wont-build":
        return ("미제작", "wont")
    if not tool_live(t):
        return ("준비중", "soon")
    lab, cls = VERDICT_LABEL.get(t.get("verdict") or "na", (None, None))
    return (lab, cls) if lab else (None, None)


BAR_ORDER = [("vpass", "통과"), ("vmarg", "제한적"), ("vunv", "미검증"),
             ("vrej", "기각"), ("soon", "준비중"), ("wont", "미제작")]

CAT_EDGE = {"market": "var(--deploy)", "newsroom": "var(--muted)", "macro": "var(--champ)",
            "quant": "var(--rp)", "gurus": "var(--muted)", "financials": "var(--deploy)",
            "valuation": "var(--marg)", "portfolio": "var(--rp)", "industry": "var(--champ)",
            "ledger": "var(--hot)"}


def region(src: str, begin: str, end: str):
    i = src.find(begin)
    j = src.find(end)
    if i < 0 or j < 0 or j < i:
        return None
    return i, j + len(end)


def apply_to(path: str, head_block: str, body_block: str, home_block: str, check: bool):
    with io.open(path, encoding="utf-8") as f:
        src = f.read()
    new = src
    touched = False
    # 앞의 둘은 필수(없으면 대상 아님), HOMEDIR은 홈에만 있는 선택 구간이다
    for begin, end, block, required in ((CSS_BEGIN, CSS_END, head_block, True),
                                        (NAV_BEGIN, NAV_END, body_block, True),
                                        (HOME_BEGIN, HOME_END, home_block, False)):
        r = region(new, begin, end)
        if r is None:
            if required:
                return None        # 마커가 없는 파일은 대상이 아니다(예: kb_content.html 조각)
            continue
        want = begin + "\n" + block + "\n" + end
        if new[r[0]:r[1]] != want:
            touched = True
            new = new[:r[0]] + want + new[r[1]:]
    if touched and not check:
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(new)
    return touched


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="쓰지 않고 어긋난 파일만 보고(CI용)")
    args = ap.parse_args()

    items = load_items()
    head_block = NAV_CSS
    body_block = build_body(items)
    # 홈의 도구 디렉터리는 2026-07-25에 뺐다 — 메가메뉴와 같은 목록을 두 번 그리고 있었고,
    # 홈이 '동료에게 보여주는 화면'이 아니라 '이 사이트를 어떻게 만들고 있나'로 읽혔다.
    # HOMEDIR은 선택 구간이라 마커가 없는 index.html은 그냥 건너뛴다.
    home_block = ""

    if not args.check:
        io.open(OUT_HEAD, "w", encoding="utf-8").write(head_block + "\n")
        io.open(OUT_BODY, "w", encoding="utf-8").write(body_block + "\n")
        # 공개용 슬림 사본 — roadmap.html·홈 도구 디렉터리가 읽는다.
        # build/는 배포되지만 데이터 fetch는 data/에서 하는 게 이 사이트 관례라 여기로 뺀다.
        pub = {"note": "메뉴 정본(build/nav_items.json)에서 생성. 직접 고치지 말 것.",
               "generated_from": digest_of(head_block, body_block, home_block),
               "categories": [
                   {"name": c["name"], "slug": c["slug"], "short": c["short"],
                    "tools": [{k: t.get(k) for k in
                               ("name", "file", "status", "desc", "verdict", "src", "effort",
                                "locked", "anchor", "blocked_by", "blocked_why", "pipeline")
                               if t.get(k) is not None} | {"live": tool_live(t)}
                              for t in c["tools"]]}
                   for c in items["categories"]],
               # 메뉴에서 뺀 칸 — 슬롯 수에는 안 들어가지만 로드맵이 사유를 그대로 게시한다.
               # 지운 기록을 지우면 '무엇을 못 하는지'가 같이 사라진다.
               "retired_note": items.get("retired_note", ""),
               "retired": items.get("retired", []),
               }
        io.open(os.path.join(ROOT, "data", "nav.json"), "w", encoding="utf-8").write(
            json.dumps(pub, ensure_ascii=False, indent=1) + "\n")

    digest = digest_of(head_block, body_block, home_block)

    drifted, synced, skipped = [], [], []
    for d in PAGE_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".html"):
                continue
            p = os.path.join(d, fn)
            r = apply_to(p, head_block, body_block, home_block, args.check)
            rel = os.path.relpath(p, ROOT)
            if r is None:
                skipped.append(rel)
            elif r:
                (drifted if args.check else synced).append(rel)

    n_slots = sum(len(c["tools"]) for c in items["categories"])
    n_live = sum(1 for c in items["categories"] for t in c["tools"] if tool_live(t))
    print("내비 정본 %s · 카테고리 %d · 슬롯 %d(연결 %d · 준비중 %d)"
          % (digest, len(items["categories"]), n_slots, n_live, n_slots - n_live))
    if skipped:
        print("  마커 없음(대상 아님): " + ", ".join(skipped))
    if args.check:
        if drifted:
            print("  ❌ 정본과 어긋남 %d장: %s" % (len(drifted), ", ".join(drifted)))
            return 1
        print("  ✅ 전 페이지 정본과 일치")
        return 0
    print("  갱신 %d장%s" % (len(synced), (": " + ", ".join(synced)) if synced else " (변경 없음)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
