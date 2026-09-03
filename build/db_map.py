# -*- coding: utf-8 -*-
"""build/db_map.py — 사내 DB 지도(db.html)의 **본문 조각**을 굽는다.

왜 잠금 페이지인가. 이 랩은 공개 저장소(ydyoon4578/yeodoo-lab)이고 GitHub Pages 로
그대로 서빙된다. 그런데 이 문서가 담는 것은 사내 게이트웨이 IP·내부 호스트명·DB 스키마와
테이블명·사내 펀드코드다. 평문으로 올리면 되돌릴 수 없다(인덱싱·캐시). 그래서
portfolio/sources/ok 와 같은 AES 게이트 뒤에 둔다.

입력은 build/db_catalog.json — 7곳의 list_tables 응답을 그대로 담은 파일이다.
사내망에서만 채울 수 있으므로 이 스크립트는 **로컬 전용**이고, 러너는 돌리지 않는다.
카탈로그가 없으면 아무것도 하지 않고 종료한다(러너에서 조용히 깨지지 않게).

    python build/db_map.py        조각을 _build/pages/db_content.html 로 굽는다

굽고 나면 잠금은 build/kb_lock.py --page db 가 한다(ct 와 ph 를 함께 기록).
"""
from __future__ import annotations
import io, json, os, re, sys, html, datetime

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "build", "db_catalog.json")
OUT  = os.path.join(ROOT, "_build", "pages", "db_content.html")
# 🚨 DB 이름표·함정 문안·조인키는 **여기 두지 않는다.** 이 파일은 공개 저장소에 추적되고,
#   그 문안에는 사내 테이블명과 게이트웨이 규약이 들어간다 — 본문을 암호화해 놓고 생성기에
#   같은 내용을 평문으로 두면 잠금이 무의미해진다. 문안은 gitignore 되는 build/db_notes.json 에 있다.
NOTES = os.path.join(ROOT, "build", "db_notes.json")

# 작업 테이블·복제 잔재는 카탈로그에서 뺀다 — xfeed 의 tmptable_* 112개가 목록을 덮는다.
JUNK = re.compile(r"^(tmptable_|awsdms_|_)", re.I)



SEV = {"bad": ("치명", "hot"), "warn": ("주의", "marg"), "good": ("발견", "good")}



def nrows(v):
    try: return int(v) if v is not None else -1
    except Exception: return -1


def fmt(r):
    if r < 0: return "—"
    if r >= 1e9: return "%.1fB" % (r / 1e9)
    if r >= 1e6: return "%.1fM" % (r / 1e6)
    if r >= 1e3: return "%.0fK" % (r / 1e3)
    return str(r)


def keep_of(ts):
    return [t for t in ts if not JUNK.match(t["table_name"]) and t["schema_name"] != "cron"]


def main():
    if not os.path.exists(SRC):
        print("db_catalog.json 없음 — 사내망에서 채우는 파일이다. 아무것도 하지 않는다."); return 0
    if not os.path.exists(NOTES):
        print("db_notes.json 없음 — 문안 파일이다(gitignore). 아무것도 하지 않는다."); return 0
    cat = json.load(io.open(SRC, encoding="utf-8"))
    nt = json.load(io.open(NOTES, encoding="utf-8"))
    DBS = [tuple(x) for x in nt["dbs"]]; FINDINGS = [tuple(x) for x in nt["findings"]]
    HILITE = set(nt["hilite"]); FOOTER = nt["footer"]; CAPS = nt.get("caps", {})
    DESCS = nt.get("descs", {})   # DB 주석이 빈 테이블의 설명 — 컬럼 스키마를 읽고 쓴 것
    P = []; A = P.append

    A('<style>')
    A('.dbwrap{max-width:1120px;margin:0 auto}')
    A('.dbnote{margin:18px 0 26px;color:var(--muted);font-size:14px;max-width:74ch;line-height:1.7}')
    A('.dbstrip{display:grid;grid-template-columns:repeat(auto-fit,minmax(126px,1fr));gap:1px;'
      'background:var(--line);border:1px solid var(--line);margin:0 0 40px}')
    A('.dbstrip a{background:var(--panel);padding:13px 13px 12px;text-decoration:none;color:inherit;display:block}')
    A('.dbstrip a:hover{background:var(--panel-2)}')
    A('.dbstrip b{font-family:var(--mono);font-size:20px;font-weight:600;font-variant-numeric:tabular-nums;display:block;line-height:1.15}')
    A('.dbstrip i{font-style:normal;font-size:12.5px;font-weight:600;display:block;margin-top:3px}')
    A('.dbstrip s{text-decoration:none;font-family:var(--mono);font-size:10px;color:var(--muted);display:block;margin-top:1px}')
    A('.dbh2{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);'
      'font-weight:600;margin:0 0 16px;padding-bottom:7px;border-bottom:1px solid var(--line)}')
    A('.finds{display:flex;flex-direction:column;gap:12px;margin-bottom:46px}')
    A('.fnd{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--line);padding:14px 16px}')
    A('.fnd.hot{border-left-color:var(--hot)} .fnd.marg{border-left-color:var(--marg)} .fnd.good{border-left-color:var(--good)}')
    A('.fnd h4{margin:0 0 6px;font-size:15.5px;font-weight:700;display:flex;gap:9px;align-items:baseline;flex-wrap:wrap}')
    A('.fnd .tag{font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;padding:2px 6px;font-weight:700;flex:none;'
      'border:1px solid currentColor;border-radius:2px}')
    A('.fnd.hot .tag{color:var(--hot)} .fnd.marg .tag{color:var(--marg)} .fnd.good .tag{color:var(--good)}')
    A('.fnd p{margin:0;font-size:14px;color:var(--muted);line-height:1.72}')
    A('.fnd p.act{margin-top:7px;padding-top:7px;border-top:1px dotted var(--line);color:var(--ink-2);font-size:13.5px}')
    A('.fnd b{color:var(--ink)} .fnd i{font-style:italic;color:var(--ink-2)}')
    A('.fnd code,.dbfoot code{font-family:var(--mono);font-size:12.5px;background:var(--panel-2);padding:1px 4px;border-radius:2px;color:var(--ink)}')
    A('.dbsec{margin-bottom:40px}')
    A('.dbhead{display:flex;align-items:baseline;gap:11px;flex-wrap:wrap;border-bottom:2px solid var(--ink);padding-bottom:8px;margin-bottom:5px}')
    A('.dbhead h3{margin:0;font-size:20px;font-weight:700}')
    A('.dbhead .ep{font-family:var(--mono);font-size:11.5px;color:var(--accent);font-weight:600}')
    A('.dbhead .ct{margin-left:auto;font-family:var(--mono);font-size:11.5px;color:var(--muted);font-variant-numeric:tabular-nums}')
    A('.dbsec>p{margin:0 0 12px;font-size:13.5px;color:var(--muted);max-width:74ch}')
    A('.dbscroll{overflow-x:auto;border:1px solid var(--line);background:var(--panel)}')
    A('.dbtbl{border-collapse:collapse;width:100%;min-width:600px}')
    A('.dbtbl th{font-family:var(--mono);font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);'
      'font-weight:600;text-align:left;padding:8px 11px;border-bottom:1px solid var(--line);background:var(--panel-2);white-space:nowrap}')
    A('.dbtbl td{padding:7px 11px;border-bottom:1px solid var(--line-soft);font-size:13px;vertical-align:top}')
    A('.dbtbl tr:last-child td{border-bottom:none}')
    A('.dbtbl td.sc{font-family:var(--mono);font-size:11px;color:var(--muted);white-space:nowrap}')
    A('.dbtbl td.nm{font-family:var(--mono);font-size:12.5px;font-weight:600;white-space:nowrap;color:var(--ink)}')
    A('.dbtbl td.rw{font-family:var(--mono);font-size:12px;text-align:right;font-variant-numeric:tabular-nums;color:var(--muted);white-space:nowrap}')
    A('.dbtbl td.ds{color:var(--muted);font-size:12.5px;line-height:1.55}')
    A('.dbtbl tr.hi td.nm{color:var(--accent)} .dbtbl tr.hi td.rw{color:var(--ink)}')
    A('.dbtbl td.ds b{color:var(--ink);font-weight:600}')
    A('.dbtbl td.drv{border-left:2px solid var(--line)}')
    A('.dblegend{margin:0 0 11px;font-size:12px;color:var(--muted);display:flex;gap:16px;flex-wrap:wrap}')
    A('.dblegend span{display:flex;align-items:center;gap:6px}')
    A('.dblegend em{font-style:normal;width:14px;height:0;border-top:2px solid var(--line);display:inline-block}')
    A('.dbmore{padding:9px 11px;font-size:12px;color:var(--muted);font-family:var(--mono);border-top:1px solid var(--line);background:var(--panel-2)}')
    A('.dbfoot{margin-top:44px;padding-top:20px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}')
    A('.dbfoot h4{font-family:var(--mono);font-size:11.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:0 0 9px;font-weight:600}')
    A('.dbfoot p{margin:0 0 8px;max-width:78ch;line-height:1.7}')
    A('</style>')

    A('<div class="dbwrap">')

    total = sum(len(v) for v in cat.values() if isinstance(v, list))
    kept  = sum(len(keep_of(v)) for v in cat.values() if isinstance(v, list))
    asof  = datetime.date.today().isoformat()

    A('<p class="dbnote">AI추진팀이 MCP 로 연 사내 데이터베이스 7곳의 테이블을 <code>list_tables</code> 로 전수 조회하고, '
      '핵심 테이블은 실제로 질의해 행수·기간·커버리지를 확인한 결과다. '
      f'테이블 <b>{total}개</b>(작업·시스템 잔재 {total-kept} 제외 {kept}) · 실측 {asof} · '
      '전부 읽기 전용 · 60초 타임아웃 · 1000행 리밋. '
      '<b>배포된 안내문과 어긋나는 지점을 먼저 적었다</b> — 이 문서의 값어치는 목록이 아니라 그쪽이다.</p>')

    A('<nav class="dbstrip">')
    for key, label, _ in DBS:
        ts = cat.get(key, [])
        k = keep_of(ts) if isinstance(ts, list) else []
        A(f'<a href="#db-{key}"><b>{len(k)}</b><i>{html.escape(label)}</i><s>{html.escape(key)}</s></a>')
    A('</nav>')

    A('<h3 class="dbh2">실측으로 확인한 것</h3><div class="finds">')
    for sev, title, body, act in FINDINGS:
        lab, cls = SEV[sev]
        A(f'<article class="fnd {cls}"><h4><span class="tag">{lab}</span>{html.escape(title)}</h4>'
          f'<p>{body}</p><p class="act">{act}</p></article>')
    A('</div>')

    A('<h3 class="dbh2">데이터베이스별 테이블</h3>')
    _drv = sum(1 for db in cat.values() if isinstance(db, list) for t in keep_of(db)
               if not (t.get("comment") or "").strip()
               and "%s.%s" % (t["schema_name"], t["table_name"]) in DESCS)
    A('<div class="dblegend"><span>설명 %d개 — DB 주석 %d, '
      '<em></em> 왼쪽 선은 주석이 없어 컬럼 스키마를 읽고 쓴 것 %d</span></div>'
      % (kept, kept - _drv, _drv))
    for key, label, note in DBS:
        ts = cat.get(key, [])
        if not isinstance(ts, list): continue
        k = keep_of(ts); k.sort(key=lambda t: -nrows(t.get("approx_rows")))
        cap = CAPS.get(key, len(k))
        A(f'<section class="dbsec" id="db-{key}">')
        A(f'<div class="dbhead"><h3>{html.escape(label)}</h3><span class="ep">{html.escape(key)}</span>'
          f'<span class="ct">{len(k)}개 · 잔재 {len(ts)-len(k)}</span></div>')
        A(f'<p>{html.escape(note)}</p>')
        A('<div class="dbscroll"><table class="dbtbl"><thead><tr><th>스키마</th><th>테이블</th>'
          '<th style="text-align:right">행</th><th>설명</th></tr></thead><tbody>')
        for t in k[:cap]:
            full = "%s.%s" % (t["schema_name"], t["table_name"])
            c = re.sub(r"\s+", " ", (t.get("comment") or "")).strip()
            c = re.sub(r"\s*·\s*원천\s.*$", "", c)
            # DB 주석이 비었으면 유도 설명으로 채우고, 그 사실을 표식으로 남긴다 —
            # 원천이 다르니 화면에서도 구분되어야 한다(DB 가 말한 것 vs 우리가 읽고 쓴 것).
            derived = False
            if not c:
                c = DESCS.get(full, ""); derived = bool(c)
            if len(c) > 165: c = c[:163] + "…"
            cell = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(c))
            A('<tr%s><td class="sc">%s</td><td class="nm">%s</td><td class="rw">%s</td>'
              '<td class="ds%s">%s</td></tr>'
              % (' class="hi"' if full in HILITE else "", html.escape(t["schema_name"]),
                 html.escape(t["table_name"]), fmt(nrows(t.get("approx_rows"))),
                 " drv" if derived else "", cell))
        A('</tbody></table>')
        if len(k) > cap:
            A(f'<div class="dbmore">행수 하위 {len(k)-cap}개 생략 — 대부분 ciq* 코드 마스터와 Compustat 레거시(co_*·sec_*·idx_*)다</div>')
        A('</div></section>')

    A('<div class="dbfoot"><h4>접속과 규약</h4>')
    for _para in FOOTER:
        A('<p>%s</p>' % _para)
    A('</div></div>')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="").write("\n".join(P))
    print("조각 생성:", OUT, len("\n".join(P)), "bytes ·", kept, "테이블")
    return 0


if __name__ == "__main__":
    sys.exit(main())
