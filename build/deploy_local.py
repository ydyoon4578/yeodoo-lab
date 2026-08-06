# -*- coding: utf-8 -*-
"""사내망 배포본을 굽는다 — 공개 사이트는 그대로 두고 사본을 따로 낸다.

🚨 왜 '복사해서 고치기'인가. 저장소를 사내용으로 **고치면 안 된다.** 고치는 순간
  공개 저장소와 사내가 갈라지고, 다음 git pull 마다 충돌하거나 사내 수정이 공개로
  새어 나간다. 단일 출처는 공개 저장소 하나여야 한다.

    공개 저장소(github)  ──git pull──▶  사내 체크아웃  ──이 스크립트──▶  배포 디렉터리
                                              │
                                              └─ 사내 전용 자료를 여기에 얹는다
                                                 (gitignore 대상이라 pull 과 안 부딪친다)

  배포 디렉터리는 **매번 새로 만든다.** 지난번 파일이 남아 있으면 지워진 페이지가
  사내에서만 계속 살아 있는다.

## 무엇이 공개본과 다른가 (실측으로 세어 둔 것)

  · canonical · og:url · twitter:url — HTML 25장. 안 고치면 사내 팀원이 검색·공유로
    **공개 사이트로 튕긴다.** 사내 배포본이 공개 URL 을 자기 정본이라 말하는 꼴이다.
  · robots.txt · sitemap.xml — 공개 도메인이 박혀 있다. 사내에서는 색인 자체를 막는다.
  · data/_pit_*_cache.json (20.5MB) — 빌드 전용. 화면이 **한 번도 안 받는다**(실측:
    HTML 참조 0곳). 배포에서 뺀다.
  · data/pit_members.json — 사내 DB(public.index_constituents) 산출물이라 공개 저장소에
    못 올린다. **사내 배포에는 넣을 수 있다** — 있으면 그대로 싣는다.

## 서버에 반드시 걸어야 하는 것 둘

  ① gzip — JSON 이라 3~5배 줄어든다. 안 켜면 96MB 를 그대로 내려보낸다.
  ② data/*.json 캐시 짧게 — 자료가 매일 바뀐다. 브라우저가 물고 있으면 **반쪽만 맞는
     화면**이 나온다(옛 파일에 있던 필드는 보이고 새 필드만 빠진다 — 전부 틀린 화면보다
     알아채기 어렵다. 2026-08-06 에 실제로 겪었다).
  이 스크립트가 nginx conf 와 IIS web.config 를 함께 낸다.
"""
import io
import os
import re
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

PUBLIC = "https://ydyoon4578.github.io/yeodoo-lab"
# 배포에서 뺀다 — 화면이 안 받는 빌드 산출물. 여기 없는 큰 파일이 생기면 늘려야 한다.
DROP_DATA = ("_pit_px_cache.json", "_pit_hl_cache.json", "_pit_sh_cache.json",
             "_custconc_raw.json", "_chand_marks.json")
DROP_DIR = (".git", ".github", "build", "_build", "__pycache__", ".claude")


def _size(p):
    n = 0
    for r, _d, fs in os.walk(p):
        for f in fs:
            try:
                n += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass
    return n


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "_deploy"),
                    help="배포 디렉터리(매번 새로 만든다)")
    ap.add_argument("--base", default="",
                    help="사내 URL 뿌리. 예: http://lab.corp.local  또는 "
                         "http://10.0.0.5/yeodoo-lab . 비우면 canonical/og 를 **지운다**")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    base = a.base.rstrip("/")

    if os.path.abspath(ROOT) == out:
        raise SystemExit("배포 디렉터리가 저장소 자신이다 — 그러면 사내용 수정이 공개로 샌다")

    # 🚨 매번 새로. 남겨 두면 저장소에서 지운 페이지가 사내에서만 계속 산다.
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)

    n_file = 0
    for r, dirs, fs in os.walk(ROOT):
        # 🚨 배포 디렉터리를 걷어낸다. 저장소 안에 두면 os.walk 가 **자기 자신을 다시 복사**한다
        #   (실측: 파일 4,470개 · 185.6MB — 기대치의 두 배. _deploy/_deploy 가 생겼다).
        dirs[:] = [d for d in dirs
                   if d not in DROP_DIR and not d.startswith(".")
                   and os.path.abspath(os.path.join(r, d)) != out]
        rel = os.path.relpath(r, ROOT)
        if rel == ".":
            rel = ""
        for f in fs:
            if f.startswith(".") or f.endswith((".py", ".md", ".pyc")):
                continue
            if rel == "data" and f in DROP_DATA:
                continue
            src = os.path.join(r, f)
            dst = os.path.join(out, rel, f)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            n_file += 1

    # ── HTML — 공개 URL 을 사내 것으로 바꾸거나 지운다 ──────────────────────
    n_html = n_meta = 0
    for f in sorted(os.listdir(out)):
        if not f.endswith(".html"):
            continue
        p = os.path.join(out, f)
        s = io.open(p, encoding="utf-8").read()
        before = s
        if base:
            s = s.replace(PUBLIC, base)
        else:
            # 뿌리를 안 주면 **지운다.** 공개 URL 을 남겨 두는 것이 최악이다 —
            # 사내 배포본이 "내 정본은 공개 사이트"라고 말하게 된다.
            s = re.sub(r'\s*<link[^>]+rel="canonical"[^>]*>', "", s)
            s = re.sub(r'\s*<meta[^>]+(?:property="og:url"|name="twitter:url")[^>]*>', "", s)
        # 사내 배포본은 색인 대상이 아니다.
        if "<head>" in s and "noindex" not in s:
            s = s.replace("<head>", '<head>\n  <meta name="robots" content="noindex,nofollow">', 1)
        if s != before:
            io.open(p, "w", encoding="utf-8").write(s)
            n_meta += 1
        n_html += 1

    # robots.txt · sitemap.xml — 사내에서는 색인을 막는다
    io.open(os.path.join(out, "robots.txt"), "w", encoding="utf-8").write(
        "# 사내 배포본 — 색인하지 않는다(공개본은 github.io 에 따로 있다)\n"
        "User-agent: *\nDisallow: /\n")
    sm = os.path.join(out, "sitemap.xml")
    if os.path.exists(sm):
        os.remove(sm)

    # ── 서버 설정 두 벌 ────────────────────────────────────────────────────
    io.open(os.path.join(out, "_nginx.conf"), "w", encoding="utf-8").write(NGINX % {"root": out})
    io.open(os.path.join(out, "web.config"), "w", encoding="utf-8").write(IIS)

    mb = _size(out) / 1e6
    pit = os.path.exists(os.path.join(out, "data", "pit_members.json"))
    print("사내 배포본 — %s" % out)
    print("  파일 %d개 · %.1fMB (공개 저장소 대비 _pit_*_cache 등 제외)" % (n_file, mb))
    print("  HTML %d장 중 %d장에서 공개 URL 을 %s" % (n_html, n_meta, ("%s 로 바꿈" % base) if base else "지움"))
    print("  robots.txt 색인 차단 · sitemap.xml 제거 · 전 페이지 noindex")
    print("  사내 전용 PIT 멤버십: %s" % ("실림 ✅" if pit else "없음(사내 DB 에서 받아 data/ 에 두면 다음 배포에 실린다)"))
    print("  서버 설정: _nginx.conf · web.config (gzip + data/*.json 캐시 60초)")
    if not base:
        print("  ⚠ --base 를 안 줘서 canonical/og 를 지웠다. 사내 URL 이 정해지면 그걸로 다시 구울 것.")
    return 0


NGINX = """# 사내 배포본 nginx 설정 — build/deploy_local.py 가 만든다.
# 🚨 둘 다 반드시 켤 것.
#   ① gzip — JSON 이라 3~5배 줄어든다. 안 켜면 96MB 를 그대로 내려보낸다.
#   ② data/*.json 캐시 짧게 — 자료가 매일 바뀐다. 브라우저가 옛 파일을 물고 있으면
#      **반쪽만 맞는 화면**이 나온다(옛 파일에 있던 필드는 보이고 새 필드만 빠진다).
#      전부 틀린 화면보다 알아채기 어렵다.
server {
    listen 80;
    server_name _;
    root %(root)s;
    index index.html;
    charset utf-8;

    gzip on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_types text/html text/css application/javascript application/json image/svg+xml;
    gzip_vary on;

    # 자료 — 매일 바뀐다. 짧게.
    location ~* ^/data/.*\\.json$ {
        add_header Cache-Control "public, max-age=60, must-revalidate";
    }
    # 화면 — 배포할 때만 바뀐다. 다만 자료와 짝이 맞아야 하므로 길게 잡지 않는다.
    location ~* \\.html$ {
        add_header Cache-Control "public, max-age=300";
    }
    location / { try_files $uri $uri/ =404; }

    # 사내 배포본은 색인 대상이 아니다(robots.txt 와 이중으로 건다).
    add_header X-Robots-Tag "noindex, nofollow" always;
}
"""

IIS = """<?xml version="1.0" encoding="UTF-8"?>
<!-- 사내 배포본 IIS 설정 — build/deploy_local.py 가 만든다.
     nginx 쪽 주석과 같은 이유로 gzip 과 data/*.json 짧은 캐시를 반드시 켠다. -->
<configuration>
  <system.webServer>
    <staticContent>
      <mimeMap fileExtension=".json" mimeType="application/json; charset=utf-8" />
      <mimeMap fileExtension=".webmanifest" mimeType="application/manifest+json" />
      <!-- 기본 캐시는 짧게. 자료가 매일 바뀐다. -->
      <clientCache cacheControlMode="UseMaxAge" cacheControlMaxAge="00:01:00" />
    </staticContent>
    <urlCompression doStaticCompression="true" doDynamicCompression="true" />
    <httpCompression>
      <staticTypes>
        <add mimeType="application/json*" enabled="true" />
        <add mimeType="text/*" enabled="true" />
        <add mimeType="application/javascript" enabled="true" />
        <add mimeType="*/*" enabled="false" />
      </staticTypes>
    </httpCompression>
    <httpProtocol>
      <customHeaders>
        <add name="X-Robots-Tag" value="noindex, nofollow" />
      </customHeaders>
    </httpProtocol>
    <defaultDocument><files><add value="index.html" /></files></defaultDocument>
  </system.webServer>
</configuration>
"""

if __name__ == "__main__":
    sys.exit(main())
