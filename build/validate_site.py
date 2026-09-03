# -*- coding: utf-8 -*-
"""사이트 정적 검증 — 브라우저 없이 '깨진 배포'를 막는 최소 안전망. CI(.github/workflows/validate.yml)에서 실행.

검사 항목
 1) 인라인 JS 괄호 균형(문자열·정규식·주석 제거 후)
 2) 정의되지 않은 함수 호출(오타) — 파일 단위 휴리스틱
 3) data/*.json 파싱 + rotation_pool 필수 필드
 4) rotation lab.href 앵커가 archive/explorer에 실제 존재하는지
 5) rotation.html의 선별 상수(CATORD·QUOTA)와 build/rotation_select.py의 상수 일치
    — 어긋나면 화면의 9선과 일일잡 갱신 대상이 달라진다(이 저장소의 핵심 불변식)
실패 시 exit 1.
"""
import re, io, os, sys, json

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ⚠ 예전엔 이 목록이 손으로 적힌 10장이었다. 그 사이 페이지가 23장으로 늘었는데 목록은
# 그대로여서, **새로 만든 페이지는 JS 검사를 한 번도 안 받고 있었다**.
# 실사고(2026-07-25): co.html에 이 페이지에 없는 포매터 nf()를 쓴 코드가 그대로 배포됐다.
# 값이 도착해 재렌더할 때 예외가 나고 화면이 옛 렌더에 멈춰 있었는데, 검사 대상이 아니라
# CI가 통과시켰다. 목록을 손으로 적지 않고 디스크에서 읽는다 — 페이지가 늘면 저절로 포함된다.
# 리다이렉트 전용 페이지 — 내비·폭 토큰·본문이 없는 게 정상이다(통합으로 남은 껍데기).
# 목록에 두면 '내비 없음'으로 매번 실패한다. 대신 리다이렉트가 살아 있는지는 아래에서 따로 본다.
REDIRECTS = {"archive.html"}
PAGES = sorted(f for f in os.listdir(ROOT)
               if f.endswith(".html") and not f.startswith("_") and f not in REDIRECTS)
errors = []


def rd(p): return io.open(os.path.join(ROOT, p), encoding="utf-8").read()


# ── 잠금 페이지 평문 해석(2026-07-23 cd2373b AES 잠금 대응) ────────────────
# explorer/rotation/archive/sources는 배포본이 '게이트+암호문'이고 평문 원본은 저장소 밖
# _build/pages/ 에서만 관리된다(.gitignore). 평문 의존 검사는 그 사본으로 수행하고,
# 사본이 없으면(CI 러너 등) 해당 검사를 맨 끝에 **SKIP으로 크게 표시**한다 — 조용한 통과 금지.
# 잠금 여부는 내용으로 판정하므로, 페이지를 평문으로 되돌리면 자동으로 원래 검사로 복귀한다.
# ⚠ 한계: 평문 사본과 배포 암호문의 일치는 여기서 확인할 수 없다(복호 키 없음) —
#   평문을 고치면 반드시 재암호화·재배포까지 한 세트로 할 것.
PLAINDIR = os.path.join(ROOT, "_build", "pages")
skips, _skipseen = [], set()
# 건너뜀은 사유가 두 갈래다. 섞어 세면 안 된다 —
#   skips      : 평문 사본(_build/pages) 부재. 이 PC에서 사본을 채우면 사라진다 → 평문 필수 모드의 대상.
#   tool_skips : 검사 도구(node 등) 부재. 사본과 무관하고 사본을 채워도 사라지지 않는다.
# 예전엔 한 통에 담아 평문 필수 모드가 'node 없음' 23건까지 평문 부재로 승격시켰다.
# 그 결과 이 PC(node 미설치)에서는 일일잡이 매일 exit 7 로 죽었다(2026-07-22~27 실측).
tool_skips = []


def is_locked(txt):
    """게이트 감지 — 표기 변형에 흔들리지 않게 2마커. kb.html식(PAYLOAD·innerHTML 주입)도 포함.
    verdicts_gen.py의 감지 규칙과 반드시 동일하게 유지할 것(어긋나면 한쪽만 게이트를 평문 취급)."""
    return "crypto.subtle.decrypt" in txt and re.search(r"var (?:P|PAYLOAD)=\{salt:", txt) is not None


def src(p):
    """검증에 쓸 평문 소스. 잠금 페이지는 _build/pages/ 사본, 없으면 None."""
    served = rd(p)
    if not is_locked(served): return served
    pp = os.path.join(PLAINDIR, p)
    if os.path.exists(pp): return io.open(pp, encoding="utf-8").read()
    return None


def plain(p, what):   # ⚠ 이름 주의: 아래 rotation_pool 검사에 `need`(필수 필드 set)가 이미 있다
    s = src(p)
    if s is None and (p, what) not in _skipseen:
        _skipseen.add((p, what)); skips.append(f"{p}: {what}")
    return s


# ── JS 리터럴 제거 ─────────────────────────────────────────────
def strip_js(js):
    out, i, n, prev = [], 0, len(js), ""
    while i < n:
        c, nx = js[i], (js[i + 1] if i + 1 < n else "")
        if c == "/" and nx == "/":
            i = js.find("\n", i); i = n if i < 0 else i; continue
        if c == "/" and nx == "*":
            j = js.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        if c in "\"'`":
            q = c; i += 1
            while i < n:
                if js[i] == "\\": i += 2; continue
                if js[i] == q: i += 1; break
                i += 1
            prev = "x"; continue
        if c == "/" and prev not in ("x", ")", "]"):
            i += 1; incls = False
            while i < n:
                ch = js[i]
                if ch == "\\": i += 2; continue
                if ch == "[": incls = True
                elif ch == "]": incls = False
                elif ch == "/" and not incls: i += 1; break
                elif ch == "\n": break
                i += 1
            while i < n and js[i].isalpha(): i += 1
            prev = "x"; continue
        out.append(c)
        if not c.isspace(): prev = "x" if (c.isalnum() or c in "_$") else c
        i += 1
    return "".join(out)


BUILTIN = set("""if for while switch catch function return typeof new else do try delete void in of instanceof
fetch parseInt parseFloat isNaN isFinite Number String Boolean Math JSON Date Array Object Symbol Error
setTimeout clearTimeout setInterval clearInterval requestAnimationFrame cancelAnimationFrame
decodeURIComponent encodeURIComponent decodeURI encodeURI escape unescape matchMedia alert confirm prompt
console document window localStorage sessionStorage location history navigator
RegExp Set Map WeakMap WeakSet Promise Proxy Reflect Intl Blob URL URLSearchParams
MutationObserver IntersectionObserver ResizeObserver Image Event CustomEvent DOMParser AbortController
getComputedStyle structuredClone queueMicrotask requestIdleCallback cancelIdleCallback
atob btoa crypto TextEncoder TextDecoder Uint8Array Uint16Array Uint32Array ArrayBuffer DataView async await""".split())
DEFPAT = [r"function\s+([A-Za-z_$][\w$]*)\s*\(", r"(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=",
          r"([A-Za-z_$][\w$]*)\s*=\s*function", r"([A-Za-z_$][\w$]*)\s*:\s*function",
          r"function\s*\(([^)]*)\)", r"catch\s*\(\s*([A-Za-z_$][\w$]*)\s*\)",
          # 이름 있는 함수의 **매개변수**도 정의로 친다. 이게 빠져 있어서
          # slider(id,outId,key,fmt)의 fmt·wireChart(...,extra)의 extra가 '미정의 호출'로 잡혔다.
          r"function\s+[A-Za-z_$][\w$]*\s*\(([^)]*)\)"]

import subprocess as _sp0
import shutil as _sh0
# node가 있으면 인라인 스크립트를 진짜 파서로 검사한다. 없으면 그 검사만 건너뛴다.
NODE = _sh0.which("node")


def js_checks(label, html):
    raw = re.findall(r"<script>([\s\S]*?)</script>", html)
    scripts = [strip_js(s) for s in raw]
    js = "\n".join(scripts)
    for k, s in enumerate(scripts):
        for a, b in [("(", ")"), ("{", "}"), ("[", "]")]:
            d = s.count(a) - s.count(b)
            if d: errors.append(f"{label} script#{k}: 괄호 불균형 {a}{b}={d:+d}")
    # 진짜 문법 검사 — node가 있으면 파서에게 맡긴다.
    # 손으로 만든 검사는 정규식 리터럴 안의 따옴표(/[&<>"\']/g)를 문자열 시작으로 오해한다.
    # 실제로 그렇게 오탐이 났다. JS 문법은 JS 파서가 판정하게 두는 편이 짧고 정확하다.
    # node가 없는 환경에서는 검사를 건너뛴다 — 못 잡는 것보다 거짓 통과를 만드는 게 나쁘다.
    if NODE:
        for k, s in enumerate(raw):
            # encoding 은 생략하면 안 된다. text=True 만 주면 로케일 인코딩(한국어 Windows는
            # cp949)으로 stdin을 쓰다가 주석의 '—'에서 UnicodeEncodeError 가 난다. 그 예외는
            # stdin 을 쓰는 **워커 스레드**에서만 터져 파이썬은 죽지 않고, stdin 이 닫히지 않은
            # node 가 입력을 영원히 기다린다 — 검증이 실패가 아니라 '멈춤'으로 끝난다(실측).
            r = _sp0.run([NODE, "--check", "-"], input=s, capture_output=True,
                         text=True, encoding="utf-8")
            if r.returncode != 0:
                first = next((l.strip() for l in (r.stderr or "").split("\n")
                              if l.strip() and "SyntaxError" in l), (r.stderr or "")[:120])
                errors.append(f"{label} script#{k}: JS 문법 오류 — 이 스크립트 전체가 실행되지 않는다. "
                              f"{first}")
    elif os.getenv("CI"):
        # CI에서 조용히 건너뛰면 '검사가 있다'는 착각만 남는다 — 그건 검사가 없는 것보다 나쁘다.
        _e = "인라인 JS 문법 검사를 돌릴 node가 없다 — CI에서는 건너뛰지 않는다"
        if _e not in errors:
            errors.append(_e)
    else:
        _noskip = f"{label}: 인라인 JS 문법 검사(node 없음)"
        if _noskip not in tool_skips:
            tool_skips.append(_noskip)

    known = set(BUILTIN)
    for pat in DEFPAT:
        for m in re.finditer(pat, js):
            for part in m.group(1).split(","):
                q = part.strip()
                if re.fullmatch(r"[A-Za-z_$][\w$]*", q or ""): known.add(q)
    unknown = sorted({m.group(1) for m in re.finditer(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(", js)} - known)
    if unknown: errors.append(f"{label}: 정의되지 않은 호출 {', '.join(unknown)}")


for p in PAGES:
    js_checks(p, rd(p))                        # 배포본(잠금 페이지면 게이트 자체를 검사)
    if is_locked(rd(p)):
        _pt = plain(p, "인라인 JS 괄호·미정의 호출(평문)")  # 잠금 해제 후 실제 렌더되는 본문
        if _pt is not None: js_checks(p + "(평문)", _pt)

# ── 독립 JS 파일 문법 검사 — 인라인 <script> 만 보면 js/ 의 앱 본체(45KB)가 통째로
#    사각지대다(2026-08-20 적대감사 확정: portfolio_app.js 를 아무 검사도 안 받고 있었다).
#    괄호 세기는 생략 — 문자열·정규식 리터럴 오탐 전력이 있어, 파일 단위는 node 파서가 정답.
_jsdir = os.path.join(ROOT, "js")
for _jf in (sorted(os.listdir(_jsdir)) if os.path.isdir(_jsdir) else []):
    if not _jf.endswith(".js"):
        continue
    _jlab = "js/" + _jf
    if NODE:
        _jr = _sp0.run([NODE, "--check", os.path.join(_jsdir, _jf)],
                       capture_output=True, text=True, encoding="utf-8")
        if _jr.returncode != 0:
            _jfirst = next((l.strip() for l in (_jr.stderr or "").split("\n")
                            if l.strip() and "SyntaxError" in l), (_jr.stderr or "")[:120])
            errors.append(f"{_jlab}: JS 문법 오류 — 이 파일 전체가 실행되지 않는다. {_jfirst}")
    elif os.getenv("CI"):
        errors.append(f"{_jlab}: JS 문법 검사를 돌릴 node가 없다 — CI에서는 건너뛰지 않는다")
    else:
        tool_skips.append(f"{_jlab}: JS 문법 검사(node 없음)")

# ── 자격증명 평문 게이트 — 2026-08-20 build/portfolio_fund.py 의 DB 암호가 평문으로
#    origin/main 까지 나간 사고의 재발 방지. 리터럴만 잡는다(환경변수·모듈 참조는 통과).
#    이 저장소는 공개다 — 사내망 IP·암호는 어떤 추적 파일에도 못 들어간다.
for _cf in sorted(os.listdir(os.path.join(ROOT, "build"))):
    if not _cf.endswith(".py"):
        continue
    try:
        _cs = io.open(os.path.join(ROOT, "build", _cf), encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    if re.search(r'password\s*=\s*["\'][^"\']{2,}["\']', _cs):
        errors.append(f"build/{_cf}: 암호 리터럴 의심 — 자격증명은 저장소 밖(util/variables.py·환경변수)에 둘 것")
    if re.search(r"\b10\.2\d\d\.\d{1,3}\.\d{1,3}\b", _cs):
        errors.append(f"build/{_cf}: 사내망 IP 리터럴 — 공개 저장소에 내부 주소를 적지 않는다")

# ── 잠금 게이트 무결성: 암호문 sanity + 평문 지문(ph) 대조 ──────────────────
#   ct 손상은 괄호 균형 검사로는 안 잡히고(실증: ct 400자 치환 → 통과), 페이지가 영구 복호불가가 된다.
#   ph = sha256(평문 utf-8 바이트). 잠금(재암호화) 도구가 반드시 함께 기록해야 하는 계약 —
#   validate가 로컬 평문 사본과 대조해 '낡은 사본으로 초록불'(타 PC 재잠금 후 드리프트)을 기계적으로 잡는다.
GATE_PLAIN = {"kb.html": "kb_content.html",
              # 2026-08-11 — 두 번째 잠금 페이지. 본문(렌더러 포함)만 조각으로 뽑아 암호화한다.
              "sources.html": "sources_content.html",
              # 🚨 2026-08-14 — 세 번째. 여기 안 적으면 get(_gp, _gp) 의 기본값이 페이지 이름
              #   자체가 되어 **조각이 아니라 평문 페이지 한 장**을 해시한다. 그러면 ph 는
              #   영원히 안 맞고 "다른 PC에서 재잠금됐다"는 엉뚱한 사유가 뜬다(실제로 떴다).
              #   기본값이 조용히 틀리는 자리라, 잠금 페이지를 늘릴 때 같이 늘려야 한다.
              "ok.html": "ok_content.html",
              # 2026-08-20 — 운용 포트폴리오(실펀드). 조각 생성은 build/portfolio_fund.py(로컬 전용).
              "portfolio.html": "portfolio_content.html",
              # 2026-09-03 — 사내 DB 지도. 조각 생성은 build/db_map.py(로컬 전용).
              "db.html": "db_content.html"}
import base64 as _b64
import hashlib as _hl
# kb.html 은 이미 PAGES 안에 있다(루트의 '_' 로 시작하지 않는 모든 .html). 그냥 이어 붙이면
# 같은 페이지를 두 번 돌아 같은 오류가 두 번 찍힌다 — 실패 1건이 2건으로 보였다. 순서는 두고 중복만 지운다.
for _gp in dict.fromkeys(PAGES + ["kb.html"]):
    _sv = rd(_gp)
    if not is_locked(_sv): continue
    if _gp not in PAGES: js_checks(_gp + "(셸)", _sv)   # kb.html은 PAGES 밖 — 게이트 셸 JS 검사 여기서
    _pm = re.search(r"var (?:P|PAYLOAD)=\{([^}]*)\}", _sv)
    if not _pm:
        errors.append(f"{_gp}: 게이트 파라미터 블록 파싱 실패"); continue
    _pd = dict(re.findall(r'(\w+):"([^"]*)"', _pm.group(1)))
    _pi = re.search(r"iter:(\d+)", _pm.group(1))
    try:
        _salt = _b64.b64decode(_pd.get("salt", ""), validate=True)
        _iv = _b64.b64decode(_pd.get("iv", ""), validate=True)
        _ct = _b64.b64decode(_pd.get("ct", ""), validate=True)
        if len(_salt) != 16: errors.append(f"{_gp}: salt {len(_salt)}B ≠ 16B — 게이트 손상")
        if len(_iv) != 12: errors.append(f"{_gp}: iv {len(_iv)}B ≠ 12B — 게이트 손상")
        if len(_ct) < 1024: errors.append(f"{_gp}: ct {len(_ct)}B — 절단 의심(정상 수만B)")
    except Exception as _ge:
        errors.append(f"{_gp}: 게이트 base64 손상 — {_ge}")
    if not _pi or int(_pi.group(1)) < 100000:
        errors.append(f"{_gp}: PBKDF2 iterations 비정상/누락")
    _ph = _pd.get("ph")
    _pp2 = os.path.join(PLAINDIR, GATE_PLAIN.get(_gp, _gp))
    if not _ph:
        errors.append(f"{_gp}: 게이트에 평문 지문(ph=sha256)이 없음 — 잠금 시 ph를 함께 기록할 것(스테일 사본 검출용)")
    elif os.path.exists(_pp2):
        # newline="" = 바이트 정확 읽기 — 유니버설 개행 번역이 끼면 같은 파일도 해시가 어긋난다
        _lh = _hl.sha256(io.open(_pp2, encoding="utf-8", newline="").read().encode("utf-8")).hexdigest()
        if _lh != _ph:
            errors.append(f"{_gp}: 평문 사본이 배포 암호문과 불일치(지문 상이) — 다른 PC에서 재잠금됐거나 사본 손상. _build/pages 갱신 필요")
    elif (_gp, "지문 대조") not in _skipseen:
        _skipseen.add((_gp, "지문 대조")); skips.append(f"{_gp}: 평문 지문(ph) 대조 — 사본 없음")

# ── 데이터 JSON ────────────────────────────────────────────────
pool = None
for f in os.listdir(os.path.join(ROOT, "data")):
    if not f.endswith(".json"): continue
    try:
        j = json.load(io.open(os.path.join(ROOT, "data", f), encoding="utf-8"))
    except Exception as e:
        errors.append(f"data/{f}: JSON 파싱 실패 {e}"); continue
    if f == "rotation_pool.json": pool = j

if pool:
    need = {"id", "cat", "cat_label", "name", "type", "target", "purpose", "principle", "entry", "performance", "recent", "sources"}
    ids = set()
    for s in pool.get("strategies", []):
        miss = need - set(s)
        if miss: errors.append(f"rotation_pool {s.get('id')}: 필드 결측 {sorted(miss)}")
        if not s.get("sources"): errors.append(f"rotation_pool {s.get('id')}: 출처 없음")
        if s["id"] in ids: errors.append(f"rotation_pool: id 중복 {s['id']}")
        ids.add(s["id"])
    # lab 앵커가 실제 항목을 가리키는지 — 앵커 키는 표시명이 아니라 **불변 id(sid)** 다.
    # 전에는 슬러그를 이름에서 즉석 생성해, 전략을 개명하는 순간 여기 19개 딥링크가 조용히 깨졌다.
    def _slug(n):   # archive.html / explorer.html의 slug()와 동일 규칙(구 슬러그 호환용)
        return re.sub(r"^-+|-+$", "", re.sub(r"[^0-9a-z가-힣]+", "-", str(n).lower()))

    def _recs(page, var="D"):
        """`var D=[ … ];` 를 대괄호 균형으로 잘라 JSON으로 읽는다(주석 허용). 잠금 평문 없으면 None."""
        src_txt = plain(page, f"전략 배열(var {var}) 스키마·sid·앵커 검사")
        if src_txt is None: return None
        src = src_txt
        m = re.search(r"var\s+%s\s*=\s*\[" % var, src)
        if not m: raise SystemExit(f"{page}: var {var}=[ 를 찾지 못함")
        i, depth, j, instr, esc = m.end() - 1, 0, m.end() - 1, False, False
        while j < len(src):
            c = src[j]
            if instr:
                if esc: esc = False
                elif c == "\\": esc = True
                elif c == '"': instr = False
            elif c == '"': instr = True
            elif c == "[": depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0: break
            j += 1
        body = re.sub(r"(?m)^\s*//.*$", "", src[i:j + 1])
        return json.loads(body)

    # 2026-07-25: archive.html이 '기각 사유 목록'에서 '규칙+성과'로 바뀌며 D 배열을
    # data/archive_index.json으로 뺐다. 그래서 아카이브는 페이지가 아니라 정본에서 읽는다.
    # ⚠ 예전엔 둘을 한 try에 묶어, 아카이브 파싱이 깨지면 explorer까지 빈 배열이 되어
    #   무관한 오류가 4건 쏟아졌다(실제로 그렇게 났다). 이제 따로 잡는다.
    try:
        AREC = (json.load(io.open(os.path.join(ROOT, "data", "archive_index.json"),
                                  encoding="utf-8")).get("items") or [])
    except Exception as e:
        errors.append(f"archive_index.json 파싱 실패: {e}"); AREC = []
    try:
        EREC = _recs("explorer.html")
    except (Exception, SystemExit) as e:   # SystemExit도 흡수 — 리포트 절단 방지(fail-closed 유지)
        errors.append(f"explorer 전략 배열 파싱 실패: {e}"); EREC = []
    anames = {d["n"] for d in AREC} if AREC is not None else None
    enames = {d["n"] for d in EREC} if EREC is not None else None

    # sid 불변식: 전 항목에 있어야 하고, 페이지 안에서 유일해야 하며, 앵커로 쓸 수 있어야 한다
    for page, recs in (("archive.html", AREC), ("explorer.html", EREC)):
        if recs is None: continue   # 잠금 평문 없음 — plain()이 SKIP 기록
        seen = {}
        for d in recs:
            sid = d.get("sid")
            if not sid:
                errors.append(f"{page} \"{d['n']}\": sid 없음 — 개명하면 딥링크가 깨진다"); continue
            if not re.fullmatch(r"[0-9a-z][0-9a-z-]*", sid):
                errors.append(f"{page} \"{d['n']}\": sid '{sid}'는 소문자 영숫자·하이픈만 허용")
            if sid in seen:
                errors.append(f"{page}: sid 중복 '{sid}' ({seen[sid]} / {d['n']})")
            seen[sid] = d["n"]

    # 구 슬러그(aka) → sid 해석표. 기존 북마크·외부 링크가 계속 도달해야 한다.
    def _resolve(recs):
        m = {}
        for d in recs:
            sid = d.get("sid") or _slug(d["n"])
            for k in [sid, _slug(d["n"])] + list(d.get("aka") or []):
                m[k] = d
        return m
    ARES = _resolve(AREC) if AREC is not None else None
    ERES = _resolve(EREC) if EREC is not None else None

    for s in pool.get("strategies", []):
        L = s.get("lab")
        if not L: continue
        # 링크 없는 lab — 아카이브 레코드를 지웠지만 '이미 검증하고 기각했다'는 지식은 남긴 경우다.
        # 이걸 허용하지 않으면 레코드를 지울 때마다 풀에서 판정까지 사라져, 같은 걸 다시 제안하게 된다.
        # 대신 판정(v)과 사유(why)는 반드시 있어야 한다 — 둘 다 없으면 그냥 빈 껍데기다.
        if not L.get("href"):
            if not (L.get("v") and L.get("why")):
                errors.append(f"rotation_pool {s['id']}: lab에 링크가 없으면 판정(v)과 사유(why)는 있어야 한다")
            continue
        href = L.get("href", "")
        page, _, frag = href.partition("#")
        if page not in ("archive.html", "explorer.html"):
            errors.append(f"rotation_pool {s['id']}: lab.href 대상 페이지가 이상함 ({href})"); continue
        if not os.path.exists(os.path.join(ROOT, page)):
            errors.append(f"rotation_pool {s['id']}: lab.href 대상 파일 없음 ({page})"); continue
        if (anames if page == "archive.html" else enames) is None: continue   # 잠금 평문 없음(SKIP 기록됨)
        # 🚨 2026-08-19 — explorer 는 이제 **전략 이름을 소스에 안 갖고 있다.** 수동 배포
        #   원장(D 배열)을 비웠고, 랩 전략은 data/strategy_index.json 에서 실행시에 붙는다.
        #   종전 검사는 «이름이 explorer.html 안에 있나» 만 봐서, D 를 비운 순간 모든 랩
        #   전략 링크가 깨진 것으로 나왔다(실측). 정본을 하나 더 본다.
        _pool = set(anames if page == "archive.html" else (enames or set()))
        if page == "explorer.html":
            try:
                _pool |= {r.get("name") for r in json.load(io.open(
                    os.path.join(ROOT, "data", "strategy_index.json"), encoding="utf-8"))["items"]}
            except Exception:
                pass
        if L["t"] not in _pool:
            errors.append(f"rotation_pool {s['id']}: lab.t \"{L['t']}\"가 {page}·strategy_index 어디에도 없음(링크 깨짐)"); continue
        if page == "explorer.html" and L["t"] not in (enames or set()):
            continue      # 랩 전략은 실행시에 붙으므로 아래 앵커 대조(소스 기준)를 건너뛴다
        pre, res = ("a-", ARES) if page == "archive.html" else ("s-", ERES)
        if not frag:
            errors.append(f"rotation_pool {s['id']}: lab.href에 앵커(#)가 없음 ({href})"); continue
        if not frag.startswith(pre):
            errors.append(f"rotation_pool {s['id']}: 앵커 접두어가 '{pre}'가 아님 (#{frag})"); continue
        tgt = res.get(frag[len(pre):])
        if tgt is None:
            errors.append(f"rotation_pool {s['id']}: 앵커 #{frag}가 {page}의 어떤 항목에도 도달하지 못함")
        elif tgt["n"] != L["t"]:
            errors.append(f"rotation_pool {s['id']}: 앵커 #{frag}는 \"{tgt['n']}\"인데 lab.t는 \"{L['t']}\"")
        elif frag[len(pre):] != (tgt.get("sid") or ""):
            errors.append(f"rotation_pool {s['id']}: 앵커가 구 슬러그(#{frag}) — sid 기준 #{pre}{tgt.get('sid')}로 갱신할 것")

    # 구 슬러그 하위호환: 각 페이지의 해시 해석 코드가 aka를 실제로 참조하는지(문안만 남고 로직이 빠지는 사고 방지)
    # 2026-07-26 통합: 랩 콘텐츠(돌린 규칙·재점검·재검)가 explorer.html로 들어갔다.
    # archive.html은 기존 딥링크를 넘기는 리다이렉트만 남았으므로 아래 검사들은 explorer를 본다.
    # NAVCSS 블록은 sync_nav.py가 매번 통째로 다시 쓴다. 거기에 페이지 고유 규칙을 넣으면
    # 다음 sync에서 소리 없이 사라진다(실측: 랩 CSS 14KB를 그렇게 한 번 날렸다).
    # 블록 안에 정본이 만들지 않는 셀렉터가 있으면 잡는다.
    try:
        import sync_nav as _sn
        _navcss = _sn.NAV_CSS if hasattr(_sn, "NAV_CSS") else None
    except Exception:
        _navcss = None
    if _navcss:
        for _f in PAGES:
            _t = plain(_f, "NAVCSS 블록 오염 검사")
            if _t is None:
                continue
            _m = re.search(r"<!-- NAVCSS:BEGIN -->(.*?)<!-- NAVCSS:END -->", _t, re.S)
            if _m and _m.group(1).strip() != _navcss.strip():
                errors.append(f"{_f}: NAVCSS 블록이 정본과 다름 — 페이지 고유 CSS를 여기 넣으면 "
                              f"다음 sync_nav 실행에서 통째로 지워진다")

    # 기준일이 대표(마지막 거래일)를 앞서는 축은 없어야 한다. '받은 날'을 기준일로 찍는 축을
    # 새로 붙일 때마다 이 실수가 되풀이된다(실제로 members 자동화에서 한 번 더 냈다).
    # 수집일이 다르면 asof_index가 collected로 분리해 두므로, 여기서 걸리면 그 처리를 빠뜨린 것이다.
    try:
        _aj = json.load(io.open(os.path.join(ROOT, "data", "asof.json"), encoding="utf-8"))
        _pri = _aj.get("primary")
        for _ax in (_aj.get("axes") or []):
            # ahead=True 는 asof_index 가 '이건 실제 거래일이고 그 축이 먼저 돈 것'이라고 판정한
            # 경우다(시장일 축). 그건 오기입이 아니므로 막지 않는다 — 막으면 자산 패널을 평일에
            # 수동 실행할 때마다 잡이 죽고, 같은 잡의 다른 산출물까지 폐기된다(실측 2026-07-27).
            if _pri and _ax.get("as_of", "") > _pri and not _ax.get("ahead"):
                errors.append(f"asof '{_ax.get('label')}': 기준일 {_ax['as_of']}이 대표 {_pri}보다 "
                              f"앞선다 — 수집일을 기준일로 찍고 있다(asof_index.py의 COLLECTED에 넣을 것)")
    except FileNotFoundError:
        pass

    # 홈 슬림 묶음(home_flow.json)이 원본보다 낡았는지 — 워크플로에서 재생성을 빠뜨리면
    # 홈만 옛 공시·수급을 말하고 다른 화면은 최신이라 아무도 알아채지 못한다.
    try:
        _hf = json.load(io.open(os.path.join(ROOT, "data", "home_flow.json"), encoding="utf-8"))
        for _src, _key in (("filings.json", "filings"), ("insider.json", "insider"),
                           ("guru.json", "guru"), ("earnings.json", "earnings")):
            _p = os.path.join(ROOT, "data", _src)
            if not os.path.exists(_p):
                continue
            _o = json.load(io.open(_p, encoding="utf-8")).get("as_of")
            _n = (_hf.get(_key) or {}).get("as_of")
            if _o and _n and _n < _o:
                errors.append(f"home_flow.{_key}: 기준일 {_n}이 원본({_src}) {_o}보다 낡음 "
                              f"— 워크플로에 build/home_flow.py 재생성이 빠졌다")
    except FileNotFoundError:
        pass

    # 통합 전략 목록이 원본보다 낡았는지 — 워크플로에서 재생성을 빠뜨리면 랩만 옛 목록을 보여준다.
    try:
        _si = json.load(io.open(os.path.join(ROOT, "data", "strategy_index.json"), encoding="utf-8"))
        _want = 0
        # ⚠ 새 엔진을 붙일 때 **여기에도 더해야 한다.** 안 더하면 목록이 원본보다 많아져
        #   "재생성을 빠뜨렸다"는 정반대의 오진이 난다(페어 트레이딩 4종, 2026-08-12).
        for _f, _k in (("tech_strategies.json", "strategies"), ("asset_strategies.json", "strategies"),
                       ("deploy_index.json", "items"), ("archive_backtests.json", "strategies"),
                       ("pairs_strategies.json", "strategies")):
            _p = os.path.join(ROOT, "data", _f)
            if os.path.exists(_p):
                _v = json.load(io.open(_p, encoding="utf-8")).get(_k) or []
                _want += len(_v)
        # 거장 겹침(guru_overlap.json)은 변형이 variants·tops 두 목록에 나뉘어 있고, 성과가
        # 안 나온 변형(표본 부족)은 원장에 싣지 않는다 — 원장이 세는 것과 같은 기준으로 센다.
        _gp = os.path.join(ROOT, "data", "guru_overlap.json")
        if os.path.exists(_gp):
            _gv = json.load(io.open(_gp, encoding="utf-8"))
            # 🚨 2026-08-16 — 종전에는 `pool`(풀 동일가중) 키가 있는 것만 셌다. 그날 대조군을
            #   S&P 500·나스닥 100 으로 바꾸면서 pool 이 없어졌고, 그러자 이 조건이 **항상
            #   거짓**이 되어 겹침 판이 하나도 안 세어졌다(원본 합계가 10 모자랐다).
            #   대조군 키에 기대지 말고 '성과가 나온 판' 으로 센다 — 원장이 세는 기준과 같다.
            _want += sum(1 for _x in ((_gv.get("variants") or []) + (_gv.get("tops") or []))
                         if _x.get("metrics"))
        # 의도적으로 목록에서 뺀 것(n_hidden)은 더해서 센다 — 그래야 '낡은 목록' 검출이
        # 살아 있으면서 의도적 제외를 오탐하지 않는다. 제외를 숨은 채로 두면 이 가드가 죽는다.
        _got = (_si.get("n") or 0) + (_si.get("n_hidden") or 0)
        if _want and _got != _want:
            errors.append(f"strategy_index: {_si.get('n')}개(+제외 {_si.get('n_hidden') or 0})인데 "
                          f"원본 합계는 {_want}개 — python build/strategy_index.py 를 다시 돌릴 것")

        # 🚨 2026-08-05 — 위 검사는 **합계만** 본다. 그래서 측정된 규칙을 목록에서 빼고 다른
        #   것을 하나 복제해 넣어도 통과한다. 신원(sid)까지 본다.
        #   ⚠ 통합 목록은 종목 규칙에 "t-" 접두를 붙인다(strategy_index 규약).
        _idx_sid = set()
        for _it in ((_si.get("items") or []) + (_si.get("hidden") or [])):
            _s = _it.get("sid") if isinstance(_it, dict) else None
            if _s:
                _idx_sid.add(_s)
                if _s.startswith("t-"):
                    _idx_sid.add(_s[2:])
        _idx_name = {(_it.get("name") or "") for _it in (_si.get("items") or [])}
        _idx_name |= {(_h.get("name") or "") for _h in (_si.get("hidden") or []) if isinstance(_h, dict)}
        _lost = []
        for _f, _k in (("tech_strategies.json", "strategies"), ("asset_strategies.json", "strategies"),
                       ("pairs_strategies.json", "strategies")):
            _p = os.path.join(ROOT, "data", _f)
            if not os.path.exists(_p):
                continue
            for _r in (json.load(io.open(_p, encoding="utf-8")).get(_k) or []):
                _s = _r.get("sid")
                if _s and _s not in _idx_sid and (_r.get("name") or "") not in _idx_name:
                    _lost.append("%s(%s)" % (_s, _f.split("_")[0]))
        if _lost:
            errors.append("측정했는데 통합 목록에 없는 규칙 %d개: %s — 합계만 맞으면 통과하던 "
                          "구멍이다(다른 것이 복제돼 자리를 채워도 안 걸린다)"
                          % (len(_lost), ", ".join(sorted(_lost)[:12])))

        # 🚨 2026-09-03 — **레그 선언(legs)이 실제와 맞는지 대조한다.**
        #   strategy_index.json 은 basis='pit' 항목의 머리 숫자만 시점정확이고 곡선·구간수익·
        #   승률·회전율은 **소급**이다. 실측: nav 역산 CAGR 이 metrics_retro 와 중앙 0.12%p 로
        #   붙고 머리의 metrics 와는 중앙 4.50%p·최대 25.38%p 벌어진다(PIT 43종 중 42종).
        #   그 넷에는 *_retro 짝조차 없어 **자료만 보고는 어느 레그인지 알 수 없었다.**
        #   → strategy_index.py 가 legs 로 적게 했고, 여기서 그 선언을 실제와 댄다.
        #   ⚠ 선언만 싣고 대조를 안 하면 선언이 낡아도 모른다(오늘 「표시용 계열」에서 얻은 교훈).
        #   ⚠ 소수는 정상이다 — 두 레그가 거의 같은 규칙이 있다. 절반을 넘으면 선언이 뒤집힌 것이다.
        # ⚠ 지역 임포트다. 이 파일의 `import datetime as _dt` 는 **1518행**이라 여기서는
        #   아직 없다. 처음에 그것을 모르고 _dt 를 썼더니 NameError 가 아래 `except` 에
        #   삼켜져 **모든 행이 건너뛰어지고 검사가 공허하게 통과**했다(선언을 뒤집어도
        #   조용했다). 이 저장소가 경계하는 vacuous pass 를 검사기 안에서 만든 것이다.
        import datetime as _dtg
        _lgrows = [_r for _r in (_si.get("items") or []) if _r.get("basis") == "pit"]
        if _lgrows and not (_si.get("legs") or {}):
            errors.append("strategy_index.json 에 legs 선언이 없다 — basis='pit' 항목의 머리 "
                          "숫자와 곡선·승률·회전율이 서로 다른 레그인데, 자료가 그 사실을 "
                          "말하지 않으면 읽는 사람이 한 카드의 수를 같은 잣대로 읽는다")
        _lgbad = 0
        for _r in _lgrows:
            _nv = _r.get("nav")
            _m, _mr = (_r.get("metrics") or {}), (_r.get("metrics_retro") or {})
            if not (_nv and _m.get("cagr") is not None and _mr.get("cagr") is not None):
                continue
            try:
                _yr = ((_dtg.date.fromisoformat(_r["end"])
                        - _dtg.date.fromisoformat(_r["start"])).days / 365.25)
            except Exception:
                continue
            if _yr <= 0:
                continue
            _c = ((_nv[-1] / _nv[0]) ** (1 / _yr) - 1) * 100
            if abs(_c - _m["cagr"]) < abs(_c - _mr["cagr"]):
                _lgbad += 1              # 곡선이 선언(소급)이 아니라 PIT 쪽에 붙었다
        if _lgrows and _lgbad > len(_lgrows) // 2:
            errors.append(
                "strategy_index.json 의 legs 선언이 실제와 뒤집혔다 — nav 를 «retro» 라 적어 "
                "뒀는데 %d/%d 종이 metrics(PIT) 쪽을 재현한다. 레그를 바꿨다면 legs 선언과 "
                "화면 설명을 같이 고칠 것" % (_lgbad, len(_lgrows)))

        # 🚨 2026-09-03 — **「기각이라 적어 놓고 게시 목록에 그대로 둔다」를 잡는다.**
        #   실측 사고: PREREG-2026-09-03-A1FIX-RESULT 가 「게시하지 않는다 … 판정은 철회한다」
        #   「기각. x-a1payout 은 게시 목록에서 빠진다」라고 **두 번** 못박았는데, 그 규칙이
        #   09-03 까지 게시 48종에 그대로 서 있었다. 같은 날 같이 기각된 형제 둘은 배선됐고
        #   이것만 빠졌다 — 판정문·원장·HIDE_SIDS 셋을 **사람이 손으로** 맞춰야 하기 때문이다.
        #   → 새 유형 「판정만 하고 안 배선」(«수집만 하고 안 배선» 의 판정 판).
        #   ⚠ 판정문 본문을 파싱하지 않는다. 표현이 문서마다 다르고(81편) 제목 줄 규약도
        #     최근 것에만 있어 거짓 양성이 난다. 대신 **기계가 읽는 원장**을 정본으로 삼는다 —
        #     build/tested_not_published.json 에 실린 sid 는 게시 목록에 있으면 안 된다.
        #     그 파일이 만들어진 이유가 정확히 이 사고다(2026-08-08: 이미 기각한 셋을
        #     «한 번도 검정한 적 없는 칸» 이라 적고 재등록했다).
        #   ⚠ 접두사 — 종목 규칙은 목록에서 `t-` 가 붙고(x-a1payout → t-x-a1payout),
        #     자산 규칙은 원장이 이미 `a-` 를 달고 있다(a-dur-style-r). 둘 다 본다.
        try:
            _led = json.load(io.open(os.path.join(ROOT, "build", "tested_not_published.json"),
                                     encoding="utf-8"))
            # ⚠ `readmitted` 가 붙은 항목은 **다시 게시하기로 한 것**이라 목록에 있는 것이
            #   맞다(실측 4종: x-fscore · x-amihud · x-turn · x-reta — 2026-08-12 게시 정책
            #   변경으로 관문이 해제됐다). 원장이 그 사실을 이미 적고 있으므로 그것을 읽는다.
            #   ⚠ 재편입을 이 검사에서 예외로 «하드코딩» 하지 않는다 — 자료가 말하게 둔다.
            _led_sid = {_r.get("sid") for _r in (_led.get("items") or [])
                        if _r.get("sid") and not _r.get("readmitted")}
            _pub = {_it.get("sid") for _it in (_si.get("items") or []) if isinstance(_it, dict)}
            _leak = sorted(_s for _s in _led_sid if _s in _pub or ("t-" + _s) in _pub)
            if _leak:
                errors.append(
                    "기각 원장에 실린 규칙이 게시 목록에 그대로 있다 %d개: %s — "
                    "build/tested_not_published.json 은 «검정했고 게시하지 않는다» 는 기록이다. "
                    "strategy_index.py 의 HIDE_SIDS 에 넣거나, 게시가 맞다면 원장에서 뺄 것"
                    % (len(_leak), ", ".join(_leak[:8])))
        except FileNotFoundError:
            pass

        # 🚨 2026-08-05 — 상세차트(strategy_charts.json)는 목록과 분리된 지연 로딩 파일이라
        #   랩을 다시 돌리고 차트를 안 구우면 **카드와 곡선이 다른 실행의 것**이 된다.
        #   실측으로 그 상태였다(차트 07:01 · 랩 15:56). x-52wh 처럼 그날 버그를 고친 규칙은
        #   화면이 고치기 전 곡선을 계속 그린다. 어떤 검사도 이것을 안 봤다.
        _cp = os.path.join(ROOT, "data", "strategy_charts.json")
        if os.path.exists(_cp):
            _cj = json.load(io.open(_cp, encoding="utf-8"))
            _ch = _cj.get("charts") or {}
            _miss = [_s for _s in _idx_sid if _s.startswith("t-x-") or _s.startswith("t-t-")]
            _miss = [_s for _s in _miss if _s not in _ch]
            if _miss:
                errors.append("상세차트가 없는 규칙 %d개: %s — python build/strategy_charts.py 를 "
                              "다시 돌릴 것(목록만 굽고 차트를 빠뜨리면 화면이 '차트 없는 전략'을 낸다)"
                              % (len(_miss), ", ".join(sorted(_miss)[:8])))
            # 끝점 대조 — 같은 실행의 산출물인지 본다(개수가 맞아도 내용이 낡을 수 있다).
            # 🚨 2026-09-03 — **원인을 둘로 가른다.** 종전에는 하나로 묶어 오류를 냈는데,
            #   그 안에 성질이 다른 둘이 섞여 있었다.
            #     ⓐ strategy_charts.py 를 안 돌렸다 → 다시 돌리면 낫는다. **오류가 맞다.**
            #     ⓑ 돌렸는데 원천 pit_strategies.json 이 낡았다 → 다시 돌려도 **안 낫는다.**
            #        그 파일을 굽는 잡이 저장소에 없다(가격 캐시 넷이 커밋 금지라 러너가 못 굽는다).
            #        랩 차트 끝점은 패널 끝(매일 움직인다)이고 pit 은 사람이 돌릴 때만 움직이므로
            #        **stocks 가 하루라도 앞서면 반드시 갈린다.** 구조적 상태지 회귀가 아니다.
            #   가르지 않았을 때 무슨 일이 났나 — refresh-tech 이 08-29·09-02 연속으로 죽었다.
            #   회귀 관문이 「이 잡이 1건을 늘렸다」로 읽어 잡 전체를 막았고, 안내문은 헛돌게 하는
            #   「strategy_charts.py 를 다시 돌릴 것」이었다. 랩 본체가 그 뒤로 CI 에서 한 번도
            #   안 구워졌다(마지막 성공 2026-08-21).
            # ⚠ ⓑ 를 **조용히 넘기지 않는다.** 아래에서 pit 의 나이를 실제로 재서 경고로 낸다.
            #   경고로 내는 것은 style_pit 과 같은 규약이다(«로컬 전용 산출물은 errors 아님»,
            #   이 파일 1918행). 오류로 내면 사람이 손으로 돌릴 때까지 저장소가 영원히 붉고,
            #   그러면 이 잡뿐 아니라 **모든 잡**이 이것 때문에 막힌다.
            _tsj = json.load(io.open(os.path.join(ROOT, "data", "tech_strategies.json"), encoding="utf-8"))
            _csrc = _cj.get("src") or {}
            try:
                _pit_as_of = json.load(io.open(os.path.join(ROOT, "data", "pit_strategies.json"),
                                               encoding="utf-8")).get("as_of") or ""
            except Exception:
                _pit_as_of = ""
            _lab_as_of = _tsj.get("as_of") or ""
            _pit_behind = bool(_pit_as_of and _lab_as_of and _pit_as_of < _lab_as_of)
            _stale, _struct = [], []
            for _r in (_tsj.get("strategies") or []):
                _c = _ch.get("t-" + _r["sid"])
                if not _c:
                    continue
                _cd = (_c.get("chart") or {}).get("dates") or _c.get("dates") or []
                _rd = _r.get("dates") or []
                if not (_cd and _rd) or _cd[-1] == _rd[-1]:
                    continue
                _one = "%s(차트 %s ≠ 랩 %s)" % (_r["sid"], _cd[-1], _rd[-1])
                # 출처가 pit 이고 pit 자체가 랩보다 뒤면 ⓑ 다. src 가 없는 옛 파일은
                # 판단 근거가 없으므로 종전대로 ⓐ 로 둔다(안전한 쪽).
                if _pit_behind and _csrc.get("t-" + _r["sid"]) == "pit_strategies.json":
                    _struct.append(_one)
                else:
                    _stale.append(_one)
            if _stale:
                errors.append("상세차트가 랩과 다른 실행의 것 %d개: %s — strategy_charts.py 를 "
                              "다시 돌릴 것" % (len(_stale), " · ".join(_stale[:5])))
            if _struct:
                _gap = ""
                try:
                    _gap = " · %d일 뒤짐" % (_dt.date.fromisoformat(_lab_as_of)
                                            - _dt.date.fromisoformat(_pit_as_of)).days
                except Exception:
                    pass
                print("  ~ 시점정확 곡선 %d개가 랩보다 낡았다 — pit_strategies.json %s vs 랩 %s%s. "
                      "strategy_charts.py 를 다시 돌려도 안 낫는다(원천이 낡은 것이다). "
                      "가격 캐시가 있는 PC 에서 build/pit_backtest.py 를 돌릴 것"
                      % (len(_struct), _pit_as_of or "?", _lab_as_of or "?", _gap))
    except FileNotFoundError:
        pass

    for _rp in sorted(REDIRECTS):
        _rt = io.open(os.path.join(ROOT, _rp), encoding="utf-8").read()
        if "location.replace" not in _rt or "explorer.html" not in _rt:
            errors.append(f"{_rp}: 리다이렉트가 없다 — 기존 딥링크가 빈 페이지에 떨어진다")
        if "location.hash" not in _rt:
            errors.append(f"{_rp}: 해시를 넘기지 않는다 — #s-… 딥링크가 목적지를 잃는다")

    _ak = plain("explorer.html", "구 슬러그(aka) 해석 로직 검사(랩)")
    # ⚠ 이 검사는 원래 "'aka'와 'ALIAS'라는 글자가 페이지 어딘가에 있는가"만 봤다. 그러면
    #   ① 표를 만들기만 하고 해석에 안 써도 ② 다른 블록(전략 목록)의 aka 로직이 대신 걸려도
    #   통과한다 — 실제로 기각 원장의 aka 해석을 통째로 없애도 안 잡혔다(음성 테스트로 확인).
    #   그래서 **기각 원장 블록만 떼어내** 그 안에서 표를 만드는 곳과 읽는 곳을 둘 다 요구한다.
    #   (옛 archive.html 딥링크 #s-<옛슬러그>가 도착할 곳은 목록이 아니라 이 원장이다)
    _led = ""
    if _ak is not None:
        _lm = re.search(r"(?s)<script>((?:(?!</script>).)*?al-body(?:(?!</script>).)*?)</script>", _ak)
        _led = _lm.group(1) if _lm else ""
        if not _led:
            errors.append("explorer.html(랩): 기각 원장 블록(al-body)을 찾지 못함 — 목록이 사라졌는지 확인")
    #   ALIAS는 **만들기(ALIAS[k]=…)와 읽기(ALIAS[slug])를 구분**해서 본다. 표만 만들고
    #   해석에 안 쓰면 딥링크는 그대로 깨지는데 'ALIAS'라는 글자는 남아 통과해 버린다.
    _alias_reads = [g for g in re.findall(r"ALIAS\s*\[[^\]]*\]\s*(=?)", _led) if g != "="]
    if _led and not (re.search(r"\.aka\s*\|\|", _led) and _alias_reads):
        errors.append("explorer.html(랩): 기각 원장에 구 슬러그(aka) 해석 로직이 없음 — 기존 딥링크가 깨진다")
    # 딥링크 도착지 유일성 — 같은 sid가 두 곳에 앵커를 만들면 #s-<sid>가 문서 순서상 앞
    # 카드로 끌려가 "링크는 열리는데 다른 규칙이 보인다"는 조용한 오작동이 된다.
    #   2026-07-27: 랩 탭이 폐지되며(2554b44) 재검 카드 섹션이 사라져 rc- 앵커도 없어졌다.
    #   지금 sid로 앵커를 만드는 곳은 목록('s-')과 기각 원장('a-') 둘이므로, 검사도 그
    #   **네임스페이스 분리**를 본다(요구는 그대로다 — 대상만 현재 구현으로 옮겼다).
    #   앵커를 **만드는 자리**(id="a-…)를 본다 — 조회 코드에 'a-'가 남아 있는 것만으로는
    #   통과하면 안 된다(음성 테스트로 확인).
    if _ak is not None and 'id="a-' not in _ak:
        errors.append("explorer.html(랩): 기각 원장이 'a-' 앵커 네임스페이스를 쓰지 않음 "
                      "— 목록의 's-'와 겹치면 딥링크 도착지가 어긋난다")
    # aka는 sid 공간과 섞이면 안 된다(구 슬러그가 남의 sid와 같으면 해석이 갈린다)
    _sids = {x.get("sid") for x in AREC}
    _seen_aka = {}
    for _x in AREC:
        for _k in (_x.get("aka") or []):
            if _k in _sids and _k != _x.get("sid"):
                errors.append(f"archive_index {_x.get('sid')}: 구 슬러그 '{_k}'가 다른 항목의 sid와 충돌")
            if _k in _seen_aka:
                errors.append(f"archive_index: 구 슬러그 '{_k}'를 {_seen_aka[_k]}·{_x.get('sid')}가 함께 씀")
            _seen_aka[_k] = _x.get("sid")

    # archive_index의 본문은 페이지에서 esc()로 감싸 넣는다. 그래서 데이터에 태그나 마크다운을
    # 섞으면 **굵게 보이는 대신 <b>가 글자 그대로 찍힌다**(실측으로 21개 필드가 그랬다).
    # 강조가 필요하면 데이터가 아니라 렌더 쪽에서 할 일이다.
    for _x in AREC:
        for _k, _v in _x.items():
            if isinstance(_v, str) and re.search(r"</?[a-zA-Z][^>]*>", _v):
                errors.append(f"archive_index {_x.get('sid')}.{_k}: HTML 태그가 들어 있음 "
                              f"— esc() 대상이라 화면에 태그가 그대로 찍힌다")
            if isinstance(_v, str) and re.search(r"\*\*[^*]+\*\*", _v):
                errors.append(f"archive_index {_x.get('sid')}.{_k}: 마크다운 굵게(**) 표기 "
                              f"— esc() 대상이라 별표가 그대로 보인다")

    # tech_strategies의 rule/why/limits도 같은 esc() 경로를 탄다. 백테스트 스크립트의
    # 주석 습관(**강조**)이 그대로 새어나온 적이 있어 같이 막는다.
    try:
        _ts0 = json.load(io.open(os.path.join(ROOT, "data", "tech_strategies.json"), encoding="utf-8"))
        _txts = [(r.get("name", "?"), k, r.get(k, "")) for r in (_ts0.get("strategies") or [])
                 for k in ("rule", "why", "name")]
        _txts += [("limits", "limits", t) for t in (_ts0.get("limits") or [])]
        _txts += [("t_crit_note", "note", _ts0.get("t_crit_note") or "")]
        # 🚨 검사의 범위가 사고의 범위보다 좁으면 안 된다 — 페어 엔진(2026-08-12)도 같은
        #   esc() 경로를 타고, 실제로 첫 산출에서 note 에 ** 가 들어갔다. holdings.note 는
        #   중첩이라 위 루프가 안 훑으므로 따로 넣는다.
        _pz0 = os.path.join(ROOT, "data", "pairs_strategies.json")
        if os.path.exists(_pz0):
            _pz0 = json.load(io.open(_pz0, encoding="utf-8"))
            for _r0 in (_pz0.get("strategies") or []):
                for _k1 in ("name", "rule", "why", "note", "bench_label"):
                    _txts.append((_r0.get("name", "?"), "pairs." + _k1, _r0.get(_k1) or ""))
                _txts.append((_r0.get("name", "?"), "pairs.holdings.note",
                              (_r0.get("holdings") or {}).get("note") or ""))
        for _nm0, _k0, _v0 in _txts:
            if re.search(r"</?[a-zA-Z][^>]*>", _v0) or re.search(r"\*\*[^*]+\*\*", _v0):
                errors.append(f"tech_strategies '{_nm0}'.{_k0}: 태그/마크다운 표기 "
                              f"— esc() 대상이라 화면에 기호가 그대로 찍힌다")
    except FileNotFoundError:
        pass

    # sd/ 의 고가·저가 — 지표별 타이밍 신호(build/signal_lab.py)의 절반 이상이 여기에 의존한다.
    # 리팩터링 중에 조용히 빠지면 그 신호들이 통째로 '표본 부족'이 되고, 화면은 아무 말도 안 한다.
    try:
        _sdd = os.path.join(ROOT, "data", "sd")
        _fs = sorted(f for f in os.listdir(_sdd) if f.endswith(".json"))[:40]
        _nohl = [f for f in _fs
                 if not (json.load(io.open(os.path.join(_sdd, f), encoding="utf-8")).get("hd"))]
        if len(_nohl) > len(_fs) * 0.2:
            errors.append(f"data/sd: 고가·저가(hd/ld)가 없는 파일이 표본 {len(_fs)}개 중 {len(_nohl)}개 "
                          f"— build/refresh_stocks.py가 hd/ld를 안 쓰고 있다(지표 신호 검증이 죽는다)")
    except FileNotFoundError:
        pass

    # signal_lab의 화면 문구도 esc() 경로를 탄다 — 태그·마크다운 금지(archive와 같은 사고 방지)
    try:
        _sl = json.load(io.open(os.path.join(ROOT, "data", "signal_lab.json"), encoding="utf-8"))
        _tx = [(r.get("name", "?"), k, r.get(k, "")) for r in (_sl.get("signals") or [])
               for k in ("name", "rule", "why", "use")]
        _tx += [("protocol", "p", t) for t in (_sl.get("protocol") or [])]
        _tx += [("limits", "l", t) for t in (_sl.get("limits") or [])]
        for _n1, _k1, _v1 in _tx:
            if isinstance(_v1, str) and (re.search(r"</?[a-zA-Z][^>]*>", _v1)
                                         or re.search(r"\*\*[^*]+\*\*", _v1)):
                errors.append(f"signal_lab '{_n1}'.{_k1}: 태그/마크다운 표기 — 화면에 기호가 그대로 찍힌다")
            # 🚨 `%%` 도 같은 계열이다 — 파이썬 % 서식의 이스케이프인데, 그 문자열에
            #   % 연산자가 안 붙으면 **`5%%` 가 화면에 그대로 찍힌다.** 실측으로
            #   protocol 에 '상위 5%%' 가 그 상태로 나가 있었고, 위 두 정규식은 이걸
            #   못 잡는다(2026-08-14 CI 가 ** 를 잡은 김에 옆에서 발견했다).
            if isinstance(_v1, str) and "%%" in _v1:
                errors.append(f"signal_lab '{_n1}'.{_k1}: '%%' 가 그대로 남았다 — % 서식의 "
                              f"이스케이프인데 이 문자열에는 % 연산자가 안 붙는다. "
                              f"화면에 '%%' 로 찍힌다")
    except FileNotFoundError:
        pass

    # asset_strategies의 화면 문구 + arch 참조 무결성(아카이브에 없는 sid를 가리키면 카드가 빈다)
    try:
        _as = json.load(io.open(os.path.join(ROOT, "data", "asset_strategies.json"), encoding="utf-8"))
        for _r in (_as.get("strategies") or []):
            if _r.get("arch") and _r["arch"] not in _sids:
                errors.append(f"asset_strategies '{_r['name']}': arch='{_r['arch']}'가 archive_index에 없음")
            for _k2 in ("name", "rule", "why", "note"):
                _v2 = _r.get(_k2) or ""
                if isinstance(_v2, str) and (re.search(r"</?[a-zA-Z][^>]*>", _v2)
                                             or re.search(r"\*\*[^*]+\*\*", _v2)):
                    errors.append(f"asset_strategies '{_r['name']}'.{_k2}: 태그/마크다운 표기 "
                                  f"— 화면에 기호가 그대로 찍힌다")
        _au = _as.get("audit") or {}
        # 재점검표는 아카이브 38건을 빠짐없이 덮어야 한다 — 빠지면 그 항목이 화면에서 사라진다
        _covered = {a["sid"] for a in (_au.get("items") or [])}
        _tj = json.load(io.open(os.path.join(ROOT, "data", "tech_strategies.json"), encoding="utf-8"))
        _tsids = {r["arch"] for r in (_tj.get("strategies") or []) if r.get("arch")}
        # 목록에서 뺀 규칙도 아카이브를 '재현했다'는 사실은 그대로다 — 그 arch 도 커버로 센다.
        # (안 세면 규칙을 뺄 때마다 아카이브 항목이 덩달아 화면에서 사라진다.)
        _tsids |= {r["arch"] for r in (_tj.get("retired") or []) if r.get("arch")}
        _missing = _sids - _covered - _tsids
        if _missing:
            errors.append(f"asset_strategies.audit: 아카이브 {len(_missing)}건이 재점검표에서 누락 "
                          f"({sorted(_missing)[:3]}…) — 화면에서 조용히 사라진다")
    except FileNotFoundError:
        pass

    # arch 참조 무결성 — 규칙 카드의 '이전 판정' 줄은 A[r.arch]로 붙는다. 없는 sid를 가리키면
    # 그 줄이 조용히 사라진다(오류도 안 난다). 링크가 끊긴 걸 화면에서 알아챌 방법이 없으므로 여기서 막는다.
    try:
        _ts = json.load(io.open(os.path.join(ROOT, "data", "tech_strategies.json"), encoding="utf-8"))
        for _r in _ts.get("strategies") or []:
            if _r.get("arch") and _r["arch"] not in _sids:
                errors.append(f"tech_strategies '{_r['name']}': arch='{_r['arch']}'가 archive_index에 없음 "
                              f"— '이전 판정' 줄이 조용히 사라진다")
    except FileNotFoundError:
        pass

    _ek = plain("explorer.html", "구 슬러그(aka) 해석 로직 검사")
    if _ek is not None and ("aka" not in _ek or "_keys" not in _ek):
        errors.append("explorer.html: 구 슬러그(aka) 해석 로직이 없음 — 기존 딥링크가 깨진다")

    # 구 슬러그가 한글이면 location.hash에 퍼센트 인코딩돼 들어온다(실측: '#s-vix-기간구조' →
    # '#s-vix-%EA%B8%B0...'). 디코드를 빠뜨리면 조회가 조용히 빗나가 "링크는 열리는데 아무 데도
    # 안 간다"가 된다 — 2026-07-25 아카이브 재작성 때 실제로 이렇게 회귀했다.
    for _pg, _txt in (("explorer.html(랩)", _ak), ("explorer.html", _ek)):
        if _txt is not None and "decodeURIComponent" not in _txt:
            errors.append(f"{_pg}: 해시 해석에 decodeURIComponent가 없음 — 한글 구 슬러그 딥링크가 빗나간다")

# ── 선별 알고리즘 상수 일치(프론트 ↔ 일일잡) ──────────────────
rot = plain("rotation.html", "선별 상수(QUOTA/CATORD)·Math.imul·KST 검사")
sel = rd(os.path.join("build", "rotation_select.py"))
def consts(txt):   # JS는 {A:2,…}·["A",…], 파이썬은 {"A": 2,…}·["A",…] → 따옴표 무시하고 정규화
    q = re.search(r"QUOTA\s*=\s*\{([^}]*)\}", txt); c = re.search(r"CATORD\s*=\s*\[([^\]]*)\]", txt)
    return (dict(re.findall(r'["\']?([A-Z])["\']?\s*:\s*(\d+)', q.group(1))) if q else None,
            re.findall(r"[A-Z]", c.group(1)) if c else None)
qj, cj = consts(rot) if rot is not None else (None, None)
qp, cp = consts(sel)
# 상수가 같아도 **산술**이 다르면 9선이 갈린다(실제 사고): JS의 seed*16777619는 2^53을 넘겨 float64 정밀도를
# 잃으므로 파이썬의 정확한 32비트 연산과 다른 시드가 됐다. Math.imul 사용을 강제한다.
if rot is not None:
    if not re.search(r"Math\.imul\s*\(\s*seed\s*,\s*16777619\s*\)", rot):
        errors.append("rotation.html FNV 해시가 Math.imul을 쓰지 않음 — float64 정밀도 손실로 rotation_select.py와 9선이 달라진다")
    if re.search(r"seed\s*\*\s*16777619", rot):
        errors.append("rotation.html에 `seed*16777619` 잔존 — Math.imul로 교체할 것")
    # 날짜 기준(KST)도 양쪽이 같아야 한다 — UTC였을 때 갱신 대상과 표시 대상이 오전 9시에 어긋났다
    if "9*3600e3" not in rot:
        errors.append("rotation.html today()가 KST 보정(9*3600e3)을 하지 않음 — 일일잡과 날짜가 어긋난다")
if "hours=9" not in sel:
    errors.append("rotation_select.py가 KST(hours=9)를 쓰지 않음 — rotation.html과 날짜가 어긋난다")

# 홈은 home_reco.json만 fetch하므로 stocks.json과 기준일이 어긋나면 홈이 낡은 채 고착된다(워크플로가 한쪽만 커밋한 사고)
try:
    _sj = json.load(io.open(os.path.join(ROOT, "data", "stocks.json"), encoding="utf-8"))
    _s = _sj.get("as_of")
    _h = json.load(io.open(os.path.join(ROOT, "data", "home_reco.json"), encoding="utf-8")).get("as_of")
    if _s and _h and _s != _h:
        errors.append(f"기준일 불일치: stocks.json {_s} vs home_reco.json {_h} — 워크플로가 두 파일을 함께 커밋하는지 확인")
    # 홈 상단 기준일 바는 '가격·테크니컬·EPS·시장국면 통일'을 정적 문구로 주장한다. 국면·심리가 고착되면
    # 그 주장이 거짓이 되므로 여기서도 막는다. 다만 FRED 릴리스가 하루 늦는 건 정상이라 2영업일부터 실패시킨다
    # (실사고: FRED 시크릿 미설정으로 전 시리즈가 조용히 멈춘 적이 있다 — 그건 곧 2영업일을 넘긴다).
    import datetime as _d0
    def _bdgap(a, b):
        try:
            _x, _y = _d0.date.fromisoformat(str(a)[:10]), _d0.date.fromisoformat(str(b)[:10])
        except Exception:
            return 0
        if _y >= _x: return 0
        n = 0
        while _y < _x:
            _y += _d0.timedelta(days=1)
            if _y.weekday() < 5: n += 1
        return n
    for _fn in ("regime.json", "sentiment.json"):
        try:
            _v = json.load(io.open(os.path.join(ROOT, "data", _fn), encoding="utf-8")).get("as_of")
        except Exception:
            continue
        if _s and _v:
            _g = _bdgap(_s, _v)
            if _g >= 2:
                errors.append(f"기준일 고착: {_fn} {_v} 가 stocks.json {_s} 보다 {_g}영업일 뒤처짐 — 자동갱신 중단 의심")
    # PBR 단위 붕괴 재발 방지(2026-07-27 BRK.B): yfinance가 클래스주 PBR을 'B주 주가 ÷ A주 주당순자산'으로
    #   준다(BRK.A:B=1500:1 → 1.55가 0.00098로). 반올림 뒤엔 `0`이 되어 값이 비는 게 아니라 **전 지수에서
    #   가장 싼 주식으로 둔갑**한다(저PBR 스크린·밸류 퍼센타일·배지가 전부 오염). refresh_stocks._fix_pb 가
    #   막지만, 가드가 무력화되거나 다른 클래스주가 편입되면 조용히 재발하므로 산출물에서 직접 확인한다.
    #   음수(자본잠식)는 실재하는 값이라 대상이 아니다 — 양수만 본다.
    _pbz = [(s["t"], (s.get("fund") or {}).get("pb")) for s in _sj.get("stocks", [])
            if isinstance((s.get("fund") or {}).get("pb"), (int, float)) and 0 <= (s["fund"]["pb"]) < 0.05]
    if _pbz:
        errors.append(f"PBR 이상치 게시: {len(_pbz)}종목이 0≤PBR<0.05 (예: {_pbz[:3]}) — "
                      "클래스주 단위 붕괴 의심. build/refresh_stocks.py의 _fix_pb 가드 확인")
    # 상세 분리 불변식: ①슬림 본체에 상세 필드가 재유입되면 페이로드가 도로 1.9MB로 부푼다
    #                 ②종목별 상세 파일이 없거나 기준일이 어긋나면 상세 패널이 낡거나 빈다
    _sd = os.path.join(ROOT, "data", "sd")
    _fat = [s["t"] for s in _sj.get("stocks", []) if any(k in s for k in ("sig", "pxd", "vd"))]
    if _fat:
        errors.append(f"stocks.json 슬림 위반: {len(_fat)}종목에 상세 필드(sig/pxd/vd) 잔존 (예: {_fat[:3]}) — 생성기 분리 로직 확인")
    _miss, _stale = [], []
    for s in _sj.get("stocks", []):
        p = os.path.join(_sd, s["t"] + ".json")
        if not os.path.exists(p):
            _miss.append(s["t"]); continue
        try:
            _d = json.load(io.open(p, encoding="utf-8"))
            if _d.get("as_of") != _s: _stale.append(s["t"])
            if not _d.get("sig"): _miss.append(s["t"])
        except Exception:
            _miss.append(s["t"])
    if _miss: errors.append(f"data/sd 상세 결측/손상 {len(_miss)}종목 (예: {_miss[:5]}) — 워크플로가 data/sd를 커밋하는지 확인")
    if _stale: errors.append(f"data/sd 기준일 불일치 {len(_stale)}종목 (예: {_stale[:5]}) — 슬림과 상세가 다른 날짜")
except Exception as e:
    errors.append(f"기준일 교차검증 실패: {e}")

# 보유 구성(무료 + DB요약): 키가 explorer D 배열 이름과 다르면 화면에 조용히 안 뜬다 + 비중합·비공개 정책 검사
try:
    if enames is None:
        plain("explorer.html", "strategy_holdings 이름 조인 검사")   # SKIP 명시 기록(무기록 증발 방지)
    for _fn in ("strategy_holdings.json", "strategy_holdings_db.json"):
        _hp = os.path.join(ROOT, "data", _fn)
        if not os.path.exists(_hp): continue
        _hd = json.load(io.open(_hp, encoding="utf-8"))
        for nm, st in (_hd.get("strategies") or {}).items():
            if enames is not None and nm not in enames:
                errors.append(f"{_fn} \"{nm}\": explorer.html D 배열에 없는 이름(화면 미표시)")
            if st.get("private"):
                # 종목 비공개 항목 — positions가 비어 있어야 정상(티커 유출 방지)
                if st.get("positions"):
                    errors.append(f"{_fn} \"{nm}\": private인데 positions 존재 — 티커 유출 의심")
            else:
                _ws = sum(p.get("w", 0) for p in st.get("positions", []))
                if abs(_ws - 1.0) > 0.01:
                    errors.append(f"{_fn} \"{nm}\": 비중합 {_ws:.4f} ≠ 1")
            if not st.get("as_of") or not st.get("note"):
                errors.append(f"{_fn} \"{nm}\": as_of/note 누락")
except Exception as e:
    errors.append(f"strategy_holdings 검증 실패: {e}")

# ── 스크리닝 정의(screens.json): 화면과 DB 로더가 **같은 파일**을 읽어야 한다 ──
#    정의를 코드에 복제하면 조용히 어긋난다(로테이션 9선 FNV 사고와 같은 유형).
try:
    _sp = os.path.join(ROOT, "data", "screens.json")
    if os.path.exists(_sp):
        _sj = json.load(io.open(_sp, encoding="utf-8"))
        _dir, _scr = _sj.get("dir") or {}, _sj.get("screens") or {}
        if not _scr:
            errors.append("screens.json: screens 비어 있음")
        for _k, _v in _scr.items():
            for _f in ("name", "keys", "qualify", "note"):
                if not _v.get(_f): errors.append(f"screens.json[{_k}]: {_f} 누락")
            for _m in list(_v.get("keys") or []) + list((_v.get("qualify") or {}).keys()) + list((_v.get("qualify_max") or {}).keys()):
                if _m not in _dir:
                    errors.append(f"screens.json[{_k}]: 지표 '{_m}'의 방향(dir) 정의 없음")
            for _m, _th in list((_v.get("qualify") or {}).items()) + list((_v.get("qualify_max") or {}).items()):
                if not isinstance(_th, (int, float)) or not (0 <= _th <= 100):
                    errors.append(f"screens.json[{_k}]: 임계 {_m}={_th} 는 0~100 백분위여야 함")
        _sh = rd("stocks.html")
        # 주석에 파일명을 적어둔 것만으로 통과하지 않도록, 실제 fetch 호출을 확인한다
        if not re.search(r"""fetch\(\s*['"]data/screens\.json""", _sh):
            errors.append("stocks.html이 screens.json을 읽지 않음 — 정의가 코드에 복제되면 로더와 어긋난다")
        if "var SCREENS={qval" in _sh or "qualify:function(s){return good(s,'fpe')" in _sh:
            errors.append("stocks.html에 스크린 정의가 인라인으로 남아 있음 — screens.json 단일 소스 위반")
        # 판정 계산은 build/screens_apply.py 한 곳뿐이어야 한다. 화면이 다시 계산하면 동점 처리 같은
        # 미세한 차이로 목록이 갈린다(실측: CMCSA가 화면 69종 / 로더 70종으로 어긋났다).
        if re.search(r"function\s+(fpct|scoreOf)\s*\(", _sh):
            errors.append("stocks.html이 스크린 판정을 자체 계산함 — 구현이 둘이면 DB·화면이 어긋난다")
        sys.path.insert(0, os.path.join(ROOT, "build"))
        import screens_apply
        _st = json.load(io.open(os.path.join(ROOT, "data", "stocks.json"), encoding="utf-8"))
        _res = _st.get("screens")
        if not _res:
            errors.append("stocks.json에 스크린 판정 결과(screens) 없음 — build/screens_apply.py 실행 필요")
        else:
            if set(_res) != set(_scr):
                errors.append(f"스크린 목록 불일치 — 정의 {sorted(_scr)} vs 결과 {sorted(_res)}")
            _fp = screens_apply.fingerprint(_sj)
            if _st.get("screens_fp") != _fp:
                errors.append(f"스크린 정의 지문 불일치({_st.get('screens_fp')}≠{_fp}) — 정의를 고친 뒤 stocks.json을 다시 굽지 않았다")
            _tk = {x["t"] for x in _st.get("stocks") or []}
            for _k, _lst in _res.items():
                _bad = [r["t"] for r in _lst if r["t"] not in _tk]
                if _bad:
                    errors.append(f"스크린 결과[{_k}]에 커버 밖 종목: {_bad[:3]}")
                _sc = [r.get("s") for r in _lst]
                if _sc != sorted(_sc, reverse=True):
                    errors.append(f"스크린 결과[{_k}]가 적합도 내림차순이 아님 — 화면은 이 순서를 그대로 그린다")
except Exception as e:
    errors.append(f"screens.json 검증 실패: {e}")

# ── 판정 원장(verdicts.json): 홈이 숫자를 손으로 적지 않는지 ──
#    '기각 41'처럼 HTML에 박아두면 전략 등재일에 조용히 틀린다 — 정직성 페이지가 틀린 숫자를 자랑하는 게 최악이다.
try:
    sys.path.insert(0, os.path.join(ROOT, "build"))
    import verdicts_gen
    _vp = os.path.join(ROOT, "data", "verdicts.json")
    if not os.path.exists(_vp):
        errors.append("data/verdicts.json 없음 — python build/verdicts_gen.py 실행 필요")
    else:
        _cur = json.load(io.open(_vp, encoding="utf-8"))
        # (1) 잠금과 무관한 검사 — 커밋본(_cur) 기준으로 항상 수행(CI에서도 죽지 않게 평문 게이트 밖에 둔다)
        _ih = rd("index.html")
        if "data/verdicts.json" not in _ih:
            errors.append("index.html이 verdicts.json을 읽지 않음 — 판정 수치를 손으로 적고 있다")
        # 홈 본문(스크립트 제외)에 판정 수치가 하드코딩돼 있으면 드리프트한다
        _body = re.sub(r"(?s)<script.*?</script>", "", _ih)
        for _n, _lab in ((_cur.get("archive_n"), "기각 아카이브 건수"), (_cur.get("explorer_n"), "전략 총수"),
                         (_cur.get("marginal_n"), "제한적 유효 건수")):
            if _n and re.search(r"(?<![0-9])%d\s*(개|종|건)" % _n, _body):
                errors.append(f"index.html에 {_lab}({_n})가 하드코딩됨 — verdicts.json에서 읽을 것")
        # 배포 전략에 백테스트가 있는지 — 이름을 고치면 explorer와 backtests가 조용히 어긋난다
        _bt = json.load(io.open(os.path.join(ROOT, "data", "strategy_backtests.json"), encoding="utf-8"))
        _bs = (_bt or {}).get("strategies") or {}
        for _d in _cur.get("deploy") or []:
            if _d["n"] not in _bs:
                errors.append(f"배포 전략에 백테스트가 없음: {_d['n']} — 이름 불일치 의심")
        # (2) 평문 의존 검사 — 원장 재계산 비교(위조 불가능한 데이터 계약)
        #     ⚠ or 단락평가로 한쪽 SKIP이 묻히지 않게 둘 다 먼저 평가한다
        _pe = plain("explorer.html", "판정 원장(verdicts) 재계산 비교")
        _pa = plain("explorer.html", "판정 원장(verdicts) 재계산 비교")
        if _pe is not None and _pa is not None:
            _fresh = verdicts_gen.build(ROOT)
            if _cur != _fresh:
                errors.append("판정 원장이 전략 배열과 어긋남 — python build/verdicts_gen.py 로 다시 구울 것")
            # 아카이브 statline도 전에 '제한적 유효 20개'를 손으로 적어두고 이관 때 틀렸다 — 스크립트까지 검사
            if re.search(r"제한적 유효 \d+개", _pa) and not re.search(r"제한적 유효 <b>", _pa):
                errors.append("explorer.html이 배포·제한적 유효 개수를 하드코딩함 — verdicts.json에서 읽을 것")
            # 배포 딥링크 슬러그가 explorer에서 실제로 선택되는지(규칙 동일성)
            for _d in _fresh["deploy"]:
                if _d["n"] not in _pe:
                    errors.append(f"배포 전략명이 explorer.html에 없음: {_d['n']}")
except (Exception, SystemExit) as e:   # verdicts_gen.build의 SystemExit도 흡수 — 리포트 절단 방지
    errors.append(f"판정 원장 검증 실패: {e}")

# ── 성과지표 v2 스키마(build/strategy_metrics.py 산출) ─────────
# explorer의 지표표는 metrics.s/.b/.basis 를 읽는다. 시계열만 다시 굽고 지표를 안 구우면
# 화면이 조용히 폴백 문구로 바뀐다 — 그 상태를 배포하지 않도록 여기서 잡는다.
try:
    if enames is None:
        plain("explorer.html", "strategy_backtests 이름 조인 검사")   # SKIP 명시 기록
    _bt = json.load(io.open(os.path.join(ROOT, "data", "strategy_backtests.json"), encoding="utf-8"))
    if _bt.get("metrics_schema") != "v2":
        errors.append("strategy_backtests.json: metrics_schema가 v2가 아님 — python build/strategy_metrics.py 실행 필요")
    for _nm, _b in (_bt.get("strategies") or {}).items():
        # 키는 explorer D 배열의 표시명과 **글자 단위로** 같아야 조인된다(개명 사고 방지)
        if enames is not None and _nm not in enames:
            errors.append(f"strategy_backtests.json \"{_nm}\": explorer.html D 배열에 없는 이름 — 차트·지표가 통째로 사라진다")
        _m = _b.get("metrics") or {}
        if not (_m.get("s") and _m.get("b") and _m.get("basis")):
            errors.append(f"{_nm}: 지표 v2 블록(s/b/basis) 없음 — build/strategy_metrics.py 로 다시 구울 것"); continue
        _ba = _m["basis"]
        if not _ba.get("excess") or not _ba.get("rf_source"):
            errors.append(f"{_nm}: 초과수익 기준(rf) 표기가 없음 — rf=0 Sharpe 게시 금지")
        if _ba.get("mdd_basis") != "monthly_nav":
            errors.append(f"{_nm}: MDD 기준이 월말 NAV가 아님 — 차트 낙폭 곡선과 어긋난다")
        for _k in ("dd", "dd_b"):
            if len(_b.get(_k) or []) != len(_b.get("dates") or []):
                errors.append(f"{_nm}: {_k} 길이가 dates와 다름")
        if _b.get("mdd_b") is not None and _m["b"].get("mdd") is not None and abs(_b["mdd_b"] - _m["b"]["mdd"]) > 0.011:
            errors.append(f"{_nm}: mdd_b({_b['mdd_b']})와 metrics.b.mdd({_m['b']['mdd']})가 어긋남")
        # N은 화면에 반드시 노출돼야 한다(전략별 3배 차이) — 값이 비면 표가 거짓말을 한다
        if not _ba.get("n_months") or _ba["n_months"] != _m["s"].get("n_months"):
            errors.append(f"{_nm}: basis.n_months 결측/불일치")
        # 🚨 2026-08-14 사용자 지적 — **곡선의 출발점이 같아야 한다.**
        #   "차트 수익률 시작점이 달라서 전략 성과가 과대계상되어 보인다."
        #   10년 상한으로 계열 앞을 자를 때 값을 다시 세우지 않아, 창 첫날의 전략 NAV 와
        #   대조군 NAV 가 서로 달랐다(실측 9종 중 8종). 차트는 그 두 수를 그대로 그리므로
        #   한쪽 선이 처음부터 위에서 출발한다 — Multi-Sleeve Core 는 **대조군이 이겼는데**
        #   그림에서는 전략 선이 위에 있었다(전략 135.0 vs 대조군 110.5 출발).
        #   ⚠ 이 결함은 **지표를 하나도 안 건드린다**(전부 비율로 재기 때문이다). 그래서
        #     기존 검사 어디에도 안 걸렸다. 틀린 것이 그림뿐이면 눈으로만 잡히는데,
        #     눈은 8종을 놓쳤다. 자리를 만들어 둔다.
        for _k, _lab in (("bench", "대조군"), ("bench2", "보조 대조군")):
            _v0 = (_b.get(_k) or [None])[0]
            _n0 = (_b.get("nav") or [None])[0]
            if _v0 is None or _n0 is None:
                continue
            if abs(_v0 - _n0) > 0.01:
                errors.append(
                    f"{_nm}: 곡선 출발점이 어긋남 — 전략 {_n0} vs {_lab} {_v0}. "
                    "차트가 두 선을 그대로 그리므로 한쪽이 처음부터 위에서 출발한다"
                    "(지표는 비율이라 멀쩡해서 눈에만 보인다). "
                    "build/strategy_metrics.py 의 100 재기준 블록을 확인할 것")
    _rf = os.path.join(ROOT, "data", "rf_monthly.json")
    if not os.path.exists(_rf):
        errors.append("data/rf_monthly.json 없음 — 무위험금리 캐시가 커밋되지 않았다(FRED 장애 시 폴백 불가)")
    else:
        _rfj = json.load(io.open(_rf, encoding="utf-8"))
        if len(_rfj.get("monthly") or {}) < 100:
            errors.append("data/rf_monthly.json: 월간 관측이 100개 미만 — 비정상")
    _e2h = plain("explorer.html", "지표 v2(metrics.s) 참조 검사")
    if _e2h is not None and "metrics.s" not in _e2h and "m.s" not in _e2h:
        errors.append("explorer.html이 지표 v2(metrics.s)를 읽지 않음")
except Exception as e:
    errors.append(f"성과지표 v2 검증 실패: {e}")

# ── 성격(kind) 축 · 대조군 역할 · 프록시 고지 · 기준월 통일 ─────
# 전략마다 '무엇으로 판단하는가'가 다르다는 것이 explorer의 발표 축이다. 그 축이 비면
# 화면은 도로 CAGR 한 줄로 모든 전략을 재단한다 — 그 상태를 배포하지 않도록 여기서 잡는다.
try:
    _kp = os.path.join(ROOT, "data", "strategy_kinds.json")
    if not os.path.exists(_kp):
        errors.append("data/strategy_kinds.json 없음 — 성격 축 정의가 커밋되지 않았다")
    else:
        _kj = json.load(io.open(_kp, encoding="utf-8"))
        _kinds = set((_kj.get("kinds") or {}).keys())
        _roles = set((_kj.get("bench_roles") or {}).keys())
        _mlab = _kj.get("metric_labels") or {}
        if not _kinds: errors.append("strategy_kinds.json: kinds가 비어 있음")
        for _k, _v in (_kj.get("kinds") or {}).items():
            for _need in ("one_liner", "primary", "list_metric", "list_label", "read_note"):
                if not _v.get(_need):
                    errors.append(f"strategy_kinds.json {_k}: {_need} 결측 — 화면이 빈칸으로 렌더된다")
            for _pk in (_v.get("primary") or []):
                if _pk not in _mlab:
                    errors.append(f"strategy_kinds.json {_k}: primary '{_pk}'의 metric_labels 라벨이 없음")
        # 목록에 뜨는 전략의 성격은 전부 kinds 에 정의가 있어야 한다.
        #   없으면 headM 이 조용히 CAGR 로 넘어간다(예외도 빈칸도 아니고 **틀린 지표**가 뜬다).
        #   2026-07-27 방어보험 정의를 걷어내면서 넣는다 — 그 계열을 다시 목록에 올리면
        #   정의가 없다는 사실이 여기서 잡혀야 한다. 제외된(hidden) 것은 화면에 안 뜨므로 대상이 아니다.
        try:
            _sidx = json.load(io.open(os.path.join(ROOT, "data", "strategy_index.json"), encoding="utf-8"))
            _orphan = sorted({(_r.get("role") or "") for _r in (_sidx.get("items") or [])} - _kinds - {""})
            if _orphan:
                errors.append(f"strategy_index: 성격 {_orphan} 이 strategy_kinds.json 에 없다 — "
                              "목록 헤드라인이 조용히 CAGR로 대체된다. 정의를 넣거나 성격을 바꿀 것")
        except FileNotFoundError:
            pass
        _det = json.load(io.open(os.path.join(ROOT, "data", "strategy_detail.json"), encoding="utf-8"))
        _bt2 = json.load(io.open(os.path.join(ROOT, "data", "strategy_backtests.json"), encoding="utf-8"))
        _bs2 = (_bt2 or {}).get("strategies") or {}
        # (f) 기준월 통일 = 사용자 1순위 원칙 — end_month는 strategy_backtests.json에서 나오므로
        #     잠금 평문 없이도 검사해야 한다(EREC에 묶으면 CI에서 이 핵심 검사가 통째로 죽는다)
        _endmonths = set()
        for _b2 in _bs2.values():
            _em = ((_b2.get("metrics") or {}).get("basis") or {}).get("end_month")
            if _em: _endmonths.add(_em)
        if len(_endmonths) > 1:
            errors.append(f"지표 기준월이 전략마다 다름: {sorted(_endmonths)} — 기준일 통일이 이 랩의 1순위 원칙이다")
        if EREC is None:
            plain("explorer.html", "strategy_detail/backtests 조인(kind·archetype·sid·bench_role·crisis) 검사")
        for _d in (EREC or []):   # EREC=None(잠금 평문 없음)이면 건너뜀 — 위에서 SKIP 기록
            _nm = _d["n"]
            _dd = _det.get(_nm) or {}
            # (a)(b) 성격 축
            if not _dd.get("kind"):
                errors.append(f"strategy_detail.json \"{_nm}\": kind 없음 — 목록·카드가 '미분류'로 떨어진다")
            elif _dd["kind"] not in _kinds:
                errors.append(f"strategy_detail.json \"{_nm}\": kind '{_dd['kind']}'가 strategy_kinds.json에 없음")
            # (e) 용도 축 미분류 0건
            if not _dd.get("archetype"):
                errors.append(f"strategy_detail.json \"{_nm}\": archetype 없음 — 용도 필터에 '미분류' 칩이 생긴다")
            _b = _bs2.get(_nm)
            if not _b: continue
            # 조인 키 이중화 — 표시명 하나로만 묶여 있으면 개명하는 순간 차트가 통째로 사라진다
            if not _b.get("sid"):
                errors.append(f"strategy_backtests.json \"{_nm}\": sid 병기 없음 — 개명 시 조인이 끊긴다")
            elif _b["sid"] != _d.get("sid"):
                errors.append(f"strategy_backtests.json \"{_nm}\": sid '{_b['sid']}'가 explorer의 '{_d.get('sid')}'와 다름")
            # (c) 대조군 역할
            for _rk, _lk in (("bench_role", "bench_label"), ("bench2_role", "bench2_label")):
                if _b.get(_lk) and not _b.get(_rk):
                    errors.append(f"strategy_backtests.json \"{_nm}\": {_rk} 없음 — 화면이 대조군 성격을 설명하지 못한다")
                elif _b.get(_rk) and _b[_rk] not in _roles:
                    errors.append(f"strategy_backtests.json \"{_nm}\": {_rk}='{_b[_rk]}'가 허용값 {sorted(_roles)}에 없음")
            # (d) 프록시 고지 — 원본인 척하면 안 된다
            if _b.get("is_proxy") and not _b.get("proxy_note"):
                errors.append(f"strategy_backtests.json \"{_nm}\": is_proxy=true인데 proxy_note가 없음 — 프록시를 원본인 척 게시할 수 없다")
            # 위기 구간·성격 보조 수치는 엔진 산출물이다(손으로 적은 값이 섞이면 조용히 틀린다)
            _m = _b.get("metrics") or {}
            if not _m.get("crisis"):
                errors.append(f"{_nm}: metrics.crisis 없음 — build/strategy_metrics.py 로 다시 구울 것")
            if _m.get("profile") is None:
                errors.append(f"{_nm}: metrics.profile 없음 — build/strategy_metrics.py 로 다시 구울 것")
            if _b.get("effective_from") and not _b.get("effective_note"):
                errors.append(f"{_nm}: effective_from만 있고 effective_note가 없음 — 겹친 구간이 차트 버그로 읽힌다")
        # explorer가 성격 축을 실제로 읽는지(문안만 남고 로직이 빠지는 사고 방지)
        _ex = plain("explorer.html", "성격 축·위기표 참조 검사")
        if _ex is not None:
            for _needs, _msg in ((("strategy_kinds.json",), "성격 축 정의를 읽지 않음"),
                                 (("metrics.crisis", "m.crisis"), "위기 구간을 화면에 쓰지 않음"),
                                 (("crisisTable",), "위기 구간 표 컴포넌트가 없음"),
                                 (("min_detectable_d_sharpe_95",), "'구별 불가'의 판정 범위를 설명하지 않음"),
                                 (("kindOf", "kmeta"), "성격별 1차 지표 분기가 없음")):
                if not any(_n in _ex for _n in _needs):
                    errors.append(f"explorer.html이 {' / '.join(_needs)} 를 참조하지 않음 — {_msg}")
except Exception as e:
    errors.append(f"성격 축·대조군 역할 검증 실패: {e}")

# ── 기각 재검 부기 — 전건 '기각 유지'다. 이게 전략처럼 보이면 랩의 신뢰가 무너진다 ──
try:
    _ap = os.path.join(ROOT, "data", "archive_backtests.json")
    if os.path.exists(_ap):
        _ab = json.load(io.open(_ap, encoding="utf-8"))
        # 2026-07-25: archive.html의 D 배열을 data/archive_index.json으로 뺐다(페이지가 '규칙+성과'로 바뀜).
        # sid 조인 검사는 그 데이터 파일을 본다 — 페이지가 아니라 정본을 보는 게 맞다.
        _asrc = plain("explorer.html", "기각 재검 부기('기각 유지' 문구) 검사")
        try:
            _aidx = json.load(io.open(os.path.join(ROOT, "data", "archive_index.json"), encoding="utf-8"))
            _idx_sids = {x.get("sid") for x in (_aidx.get("items") or [])}
        except Exception:
            _idx_sids = None
        if _ab.get("metrics_schema") != "v2":
            errors.append("archive_backtests.json: metrics_schema가 v2가 아님 — strategy_metrics.py 실행 필요")
        # 분모를 게시 건수로 잡으면 보정이 실제보다 관대해진다(고른 뒤에 세는 것 = selection 무시)
        _nt = _ab.get("n_tests_total")
        if not _nt or _nt < len(_ab.get("strategies") or {}):
            errors.append("archive_backtests.json: n_tests_total 결측/과소 — 다중검정 분모는 게시 건수가 아니라 재검 총 건수")
        # archive.html의 sid와 조인되지 않으면 부기가 통째로 사라진다(개명 사고 유형)
        _asids = _idx_sids
        for _sid, _b in (_ab.get("strategies") or {}).items():
            if _asids is not None and _sid not in _asids:
                errors.append(f"archive_backtests.json \"{_sid}\": data/archive_index.json에 없는 sid — 부기가 렌더되지 않는다")
            _m = _b.get("metrics") or {}
            if not (_m.get("s") and _m.get("b") and _m.get("basis")):
                errors.append(f"{_sid}: 부기 지표 v2 블록 없음"); continue
            if not _m["basis"].get("excess"):
                errors.append(f"{_sid}: 부기가 초과수익 기준이 아님 — rf=0 게시 금지")
            _mu = _m.get("multiplicity") or {}
            if _mu.get("n_tests") != _nt:
                errors.append(f"{_sid}: 다중검정 n_tests({_mu.get('n_tests')})가 n_tests_total({_nt})과 다름")
            if _mu.get("passed"):
                errors.append(f"{_sid}: 부기가 다중검정을 통과한 것으로 표시됨 — 재검 판정은 전건 '기각 유지'다. "
                              "실제로 통과했다면 아카이브가 아니라 탐색기로 승격 검토가 먼저다")
        if _asrc is not None and "기각 유지" not in _asrc:
            errors.append("explorer.html 부기에 '기각 유지' 문구가 없음 — 표만 보면 부활한 것으로 읽힌다")
except Exception as e:
    errors.append(f"기각 재검 부기 검증 실패: {e}")

# ── 폭 토큰: 페이지 이동 시 콘텐츠 폭이 튀지 않게 세 가지로만 ──
try:
    # 🚨 2026-08-10 — index.html 을 --w-base(1200) 에서 --w-wide(1680) 로 옮겼다(사용자 요청).
    #   홈은 읽는 화면이 아니라 자료 화면이라 폭이 곧 정보량이다(히트맵 518칸).
    #   이 표를 같이 안 고치면 이 검사가 '되돌려라'라고 말한다 — 기대값도 결정의 일부다.
    # 🚨 2026-08-12 — explorer.html 도 --w-wide 로 옮겼다(사용자 요청 '홈처럼 좌우 넓게').
    #   같은 사유다 — 왼쪽 130종 목록 · 오른쪽 6열 비교표와 12열 월별 히트맵이라 폭이 정보량이다.
    _want = {"stocks.html": "--w-wide", "index.html": "--w-wide", "explorer.html": "--w-wide",
             "regime.html": "--w-base", "rotation.html": "--w-base", "archive.html": "--w-base",
             "sources.html": "--w-read"}
    _want = {k: v for k, v in _want.items() if k not in REDIRECTS}   # 리다이렉트는 본문이 없다
    for _f, _tok in _want.items():
        _s = plain(_f, "폭 토큰 검사")   # 잠금 페이지는 평문 기준(게이트는 자체 폭을 가짐)
        if _s is None: continue
        _m = re.search(r"\.wrap\{[^}]*?max-width:\s*([^;]+);", _s)
        if not _m:
            errors.append(f"{_f}: .wrap max-width 없음")
        elif _m.group(1).strip() != f"var({_tok})":
            errors.append(f"{_f}: 폭이 var({_tok})가 아님({_m.group(1).strip()}) — 폭 토큰 밖으로 나갔다")
except Exception as e:
    errors.append(f"폭 토큰 검증 실패: {e}")

# ── 모바일 가로스크롤 방지 ──
#    body에 word-break:keep-all(한글 단어 보전)만 걸면 끊을 곳 없는 라틴 문자열이 통째로 붙들려
#    페이지를 가로로 밀어낸다(실측: regime.html의 "(Goldilocks·…·Recession)" 527px → 문서폭 547).
#    overflow-wrap:break-word는 넘칠 때만 끊으므로 한글 보전과 양립한다.
try:
    for _p in PAGES:
        _srv = rd(_p)
        _cands = [(_p, _srv)]                 # 배포본(잠금이면 게이트 화면도 모바일에서 렌더된다)
        if is_locked(_srv):
            _pt2 = plain(_p, "모바일 word-break 안전망 검사(평문)")
            if _pt2 is not None: _cands.append((_p + "(평문)", _pt2))
        # ⚠ 주석에 문자열이 있는 것만으로 통과하면 안 된다(스크린 검사에서 이미 겪은 함정) —
        #    두 속성이 **한 선언 안에 붙어 있는지**를 본다.
        for _lab2, _s in _cands:
            if "word-break:keep-all" in _s and not re.search(r"word-break:\s*keep-all\s*;\s*overflow-wrap:\s*break-word", _s):
                errors.append(f"{_lab2}: word-break:keep-all에 overflow-wrap:break-word 안전망이 없음 — 모바일 가로스크롤 위험")
except Exception as _e3:
    errors.append(f"줄바꿈 안전망 검증 실패: {_e3}")

# ── 갱신 피드(updates.json): 홈 '최근 업데이트'·각 페이지 배지의 소스 ──
#    시각(hm)은 선택 필드지만, 있으면 HH:MM이어야 한다 — 형식이 깨지면 화면에 그대로 노출된다.
try:
    _up = json.load(io.open(os.path.join(ROOT, "data", "updates.json"), encoding="utf-8"))
    for _e in _up.get("events") or []:
        _hm = _e.get("hm")
        if _hm is not None and not re.fullmatch(r"[0-2]\d:[0-5]\d", str(_hm)):
            errors.append(f"updates.json: 시각 형식 이상 {_e.get('dt')} {_hm}")
except Exception as _e2:
    errors.append(f"updates.json 시각 검증 실패: {_e2}")
try:
    _up = os.path.join(ROOT, "data", "updates.json")
    if os.path.exists(_up):
        _u = json.load(io.open(_up, encoding="utf-8"))
        # 목록을 여기 또 적지 않는다 — log_update.py의 TARGETS가 정본이다.
        # (구현이 둘이면 어긋난다: 실제로 이 줄이 옛 7개로 굳어 새 화면 기록을 전부 오류로 잡았다.)
        _m0 = re.search(r"TARGETS\s*=\s*\{(.*?)\}", rd("build/log_update.py"), re.S)
        _ok_t = set(re.findall(r'"([a-z]+)"', _m0.group(1))) if _m0 else set()
        if not _ok_t:
            errors.append("log_update.py의 TARGETS를 파싱하지 못함 — updates.json target 검사를 할 수 없다")
        _evs = _u.get("events")
        if not isinstance(_evs, list) or not _evs:
            errors.append("updates.json: events 비어 있음")
        else:
            _prev = None
            for i, e in enumerate(_evs):
                for k in ("dt", "target", "title"):
                    if not e.get(k): errors.append(f"updates.json[{i}]: {k} 누락")
                if e.get("target") and e["target"] not in _ok_t:
                    errors.append(f"updates.json[{i}]: 알 수 없는 target '{e['target']}' (허용: {sorted(_ok_t)})")
                if _prev and e.get("dt") and e["dt"] > _prev:
                    errors.append(f"updates.json[{i}]: 정렬 오류 — 최신순이어야 함({e['dt']} > {_prev})")
                _prev = e.get("dt") or _prev
            # 🚨 오래 비어 있는 것도 결함이다 — 2026-08-10 에 사용자가 '마지막 기록이 3일
            #   전'이라고 짚어서 알았다. 그날 방문자가 보는 변경이 다섯 건 있었는데 하나도
            #   안 적혀 있었다. 이 피드는 **손으로 적는다**(log_update.py 를 부르는 워크플로가
            #   하나도 없다). 사람이 기억해야 하는 것은 언젠가 잊힌다 —
            #   코드 주석이 이미 "2026-07-23~25 사흘이 그렇게 비었다"고 적고 있었다.
            #   ⚠ 실패가 아니라 경고다. 조용한 주가 정상일 수 있고(주말·휴장), 이 검사 때문에
            #     일일 잡이 죽으면 그게 더 나쁘다. 문턱 10일은 '한산함'이 아니라 '멈춤'을 잡는다.
            #   ⚠ datetime 은 여기서 따로 들인다 — 모듈 상단의 _dt 별칭은 이 블록보다
            #     **아래**에서 만들어진다. 그대로 쓰면 NameError 가 나고, 그 예외를 바깥
            #     except 가 삼켜 '검증 실패'로 둔갑한다(원인이 안 보이는 종류의 실패다).
            import datetime as _dtl
            _newest = next((e.get("dt") for e in _evs if e.get("dt")), None)
            if _newest:
                _gap = (_dtl.date.today() - _dtl.date.fromisoformat(_newest)).days
                if _gap >= 10:
                    print(f"⚠ 갱신 피드가 {_gap}일째 조용하다(마지막 {_newest}). "
                          f"그동안 방문자가 보는 변경이 있었다면 build/log_update.py 로 남길 것 "
                          f"— 이 피드를 채우는 자동 잡은 없다.")
except Exception as e:
    errors.append(f"updates.json 검증 실패: {e}")

# ── strategy_index 의 필드 중 화면이 한 번도 안 읽는 것 ──────────────────
# 🚨 이 저장소가 반복해 온 실패는 두 종류다.
#     ① 재 놓고 안 실었다 — 아래쪽 '_IDX_SKIP' 검사가 잡는다(tech → index).
#     ② 실어 놓고 안 그렸다 — **이건 아무도 안 잡고 있었다.**
#   2026-08-11 에 내가 ②를 만들었다. 바스켓 크기 계측(bask)을 index 까지 보내 놓고
#   explorer 에 그리는 코드를 안 썼다. ①의 검사를 통과했기 때문에 초록불이었다.
#   같은 자리에 has_detail 도 있었다 — 8행에 True 만 싣고 읽는 코드가 저장소에 0곳이다.
# ⚠ 문자열 포함으로 보는 헐거운 검사다. 화면이 x.foo·"foo"·'foo' 중 어떤 형태로든
#   한 번이라도 언급하면 통과한다. 그래도 '아예 아무 데도 없는' 필드는 확실히 잡힌다.
try:
    _si = json.load(io.open(os.path.join(ROOT, "data", "strategy_index.json"), encoding="utf-8"))
    # 🚨 2026-08-13 — 읽는 화면이 explorer 하나가 아니다. 홈이 strategy_index.json 을
    #   직접 받아 '최근 성과 상위'를 그리면서 trails·trails_base 를 쓰는데, 여기서
    #   explorer 만 보고 있어 **그리고 있는 필드를 고아로 잡았다.**
    #   ⚠ 면제 목록(_IDX_ORPHAN_OK)에 넣지 않는다. 그건 "안 그린다"는 뜻인데 실제로는
    #     그리고 있다 — 검사 범위를 넓히는 것이 맞고, 면제로 덮으면 진짜 고아가 생겨도
    #     같은 자리에 숨는다.
    _ex = "".join(io.open(os.path.join(ROOT, _f), encoding="utf-8").read()
                  for _f in ("explorer.html", "index.html"))
    _IDX_ORPHAN_OK = set()      # 일부러 안 그리는 필드가 생기면 여기 사유와 함께 적을 것
    _seen = set()
    for _row in (_si.get("items") or []):
        _seen |= set(_row.keys())
    _orph = sorted(_k for _k in _seen - _IDX_ORPHAN_OK
                   if ("." + _k) not in _ex and ('"' + _k + '"') not in _ex and ("'" + _k + "'") not in _ex)
    if _orph:
        errors.append("strategy_index 에 실었는데 explorer 가 한 번도 안 읽는 필드: "
                      + ", ".join(_orph) + " — 그리든지, 안 보낼 것(재 놓고 안 그리면 잰 적 없는 것과 같다). "
                      "일부러 남기는 것이면 validate_site 의 _IDX_ORPHAN_OK 에 사유와 함께 적을 것")
except Exception as _e:
    errors.append("strategy_index 고아 필드 검사 실패: %s" % _e)

# ── PowerShell 스크립트는 UTF-8 BOM 이어야 한다 ──────────────────────────
# 🚨 2026-08-11 에 실제로 당했다. build/rotation_daily.ps1 을 BOM 없이 저장했더니
#   Windows PowerShell 5.1 이 그 파일을 **시스템 ANSI(CP949)로 읽어** 한글 주석이 깨졌고,
#   깨진 바이트가 파서에 걸려 스크립트가 통째로 안 돌았다
#   ("Missing expression after unary operator '!'" — 주석 안에서 난 오류다).
#   5.1 은 BOM 이 없으면 UTF-8 인지 알 방법이 없다. pwsh(7+)는 UTF-8 이 기본이라 안 걸린다 —
#   즉 개발자가 pwsh 로 시험하면 통과하고 작업 스케줄러(powershell.exe)에서만 죽는다.
#   같은 자리에 build/deploy_local.ps1 도 BOM 없이 있었다(아직 안 터졌을 뿐이다).
# ⚠ ASCII 만 있는 스크립트는 문제가 없으므로 비ASCII 가 든 것만 본다.
try:
    import glob as _glb
    import codecs as _cdc
    _nobom = []
    for _p in sorted(_glb.glob(os.path.join(ROOT, "build", "*.ps1"))):
        _raw = io.open(_p, "rb").read()
        if _raw.startswith(_cdc.BOM_UTF8):
            continue
        try:
            _txt = _raw.decode("utf-8")
        except Exception:
            _nobom.append(os.path.basename(_p) + "(UTF-8 도 아님)")
            continue
        if any(ord(_c) > 127 for _c in _txt):
            _nobom.append(os.path.basename(_p))
    if _nobom:
        errors.append("PowerShell 스크립트에 UTF-8 BOM 이 없다 — Windows PowerShell 5.1 이 "
                      "ANSI 로 읽어 한글 주석에서 파서가 죽는다: " + ", ".join(_nobom))
except Exception as _e:
    errors.append("ps1 BOM 검사 실패: %s" % _e)

# ── 홈 표 위 시계열의 끝값이 표의 그 칸과 같은가 ─────────────────────────
# 🚨 이 그림이 있는 이유는 아래 표를 그림으로 보자는 것이다. 끝값이 표와 다르면
#   같은 화면이 한 섹터에 두 숫자를 말한다 — 이 저장소가 가장 싫어하는 상태다.
#   build/home_perf.py 가 표와 **같은 정의**로 굽지만(섹터 = 기준일 대비 비율의 평균),
#   한쪽 빌더만 고치는 날이 온다. 그때 여기서 잡는다.
try:
    _hp = os.path.join(ROOT, "data", "home_perf.json")
    if os.path.exists(_hp):
        _P = json.load(io.open(_hp, encoding="utf-8"))
        _MB = json.load(io.open(os.path.join(ROOT, "data", "market_board.json"), encoding="utf-8"))
        _HR = json.load(io.open(os.path.join(ROOT, "data", "home_reco.json"), encoding="utf-8"))
        _secs = ((_HR.get("industry") or {}).get("sectors") or [])
        _ixn = {"SPY": "S&P 500", "QQQ": "나스닥 100", "DIA": "다우존스 30", "IWM": "러셀 2000"}
        _bad = []
        for _hz, _blk in (_P.get("series") or {}).items():
            # 🚨 자료 건강 — 못 박기로 사라지지 않는 진짜 관측이다. home_perf 가 못 박기
            #   **전** 의 분봉·종가 차이를 gap_max 로 적는다. 그 수가 없으면 대조를 아예
            #   안 한 것이고, 그러면 아래 «끝값이 같다» 가 자료가 맞다는 증거가 못 된다.
            #   ⚠ 문턱은 여기 두지 않는다 — home_perf 의 가드(0.15)가 정본이다.
            #   ⚠ 반드시 **루프 안**이어야 한다. 밖에 두면 _hz 가 마지막 지평선이라
            #     조건이 영영 거짓이 된다 — 2026-08-28 에 실제로 그렇게 넣었고 일부러
            #     gap_max 를 지워 보고서야 안 걸린다는 것을 알았다.
            if _hz == "1D" and _blk.get("ix") and _blk.get("gap_max") is None:
                errors.append("홈 1D 시계열에 gap_max 가 없다 — 분봉과 표를 대조하지 "
                              "않았다는 뜻이다. 끝점은 표와 같게 못 박혀 있으므로 «끝값이 "
                              "같다» 는 것이 자료가 맞다는 증거가 되지 못한다"
                              "(build/home_perf.py 를 확인할 것)")
            for _x in (_MB.get("index") or []):
                _nm = _ixn.get(_x.get("t"))
                _w = (_x.get("r") or {}).get(_hz)
                _v = (_blk.get("ix") or {}).get(_nm) or []
                if _nm and _w is not None and _v and _v[-1] is not None and round(_v[-1], 2) != round(_w, 2):
                    _bad.append("%s %s 표 %.2f vs 그림 %.2f" % (_hz, _nm, _w, _v[-1]))
            for _s in _secs:
                _w = (_s.get("r") or {}).get(_hz)
                _v = (_blk.get("sec") or {}).get(_s.get("nm")) or []
                if _w is not None and _v and _v[-1] is not None and round(_v[-1], 2) != round(_w, 2):
                    _bad.append("%s %s 표 %.2f vs 그림 %.2f" % (_hz, _s.get("nm"), _w, _v[-1]))
        # 🚨 아래 검사의 뜻이 2026-08-28 에 바뀌었다. 전에는 «분봉으로 그린 끝점이 표와
        #   맞나» 를 물었는데, home_perf 가 끝점을 표와 같은 식으로 못 박으면서(분봉
        #   마지막 체결가는 마감 동시호가를 못 담아 구조적으로 표와 다르다) 이제는
        #   «그 못 박기가 살아 있나» 를 묻는 회귀 가드다. 문턱을 반올림 오차 수준까지
        #   표시 자릿수(둘째 자리)에서 같은지로 본다 — 문턱을 고르지 않는다.
        if _bad:
            errors.append("홈 시계열의 끝값이 기간별 수익률 표와 다르다(%d건): %s — "
                          "python build/home_perf.py 를 market_board 뒤에 다시 돌릴 것"
                          % (len(_bad), " / ".join(_bad[:4])))
except Exception as _e:
    errors.append("홈 시계열 대조 실패: %s" % _e)

# ── JS 문자열 안에서 쓰는 CSS 변수도 정의돼 있는가 ──────────────────────
# 🚨 2026-08-11 에 당했다. 사이클 차트가 SVG 를 JS 문자열로 조립하면서 fill="var(--champ)"
#   를 썼는데 regime.html 에는 그 토큰이 **없다**(kb.html 은 자기 팔레트를 따로 둬서 있다).
#   색이 통째로 빠져 경기 곡선이 회색으로 그려졌고, 아무 검사도 안 걸렸다 —
#   기존 '정의 없는 CSS 변수' 검사는 CSS 선언과 인라인 style= 만 보기 때문이다.
#   그림이 잘못 그려져도 파서는 아무 말을 안 한다. 그래서 여기서 따로 본다.
# ⚠ 문자열 안이라 오탐이 있을 수 있다(주석·설명문에 쓴 var(--x)). 실제 정의를 못 찾은 것만 낸다.
try:
    import glob as _g2
    for _hp in sorted(_g2.glob(os.path.join(ROOT, "*.html"))):
        _fn = os.path.basename(_hp)
        _tx = io.open(_hp, encoding="utf-8").read()
        _def = set(re.findall(r"(--[\w-]+)\s*:", _tx))
        # 런타임에 심는 것도 정의로 친다 — explorer 의 --vc 가 그 경우다
        # (b.style.setProperty('--vc', …)). 허용목록을 손으로 두면 낡는다.
        _def |= set(re.findall(r"setProperty\(\s*['\"](--[\w-]+)", _tx))
        # var(--x, 대체값) 형태는 대체값이 있으니 빠져도 화면이 안 깨진다 — 뺀다.
        _use = set(re.findall(r"var\((--[\w-]+)\s*\)", _tx))
        _bad = sorted(_use - _def)
        if _bad:
            errors.append("%s: 정의 없는 CSS 변수를 var() 로 쓴다 %s — 그 자리는 색·크기가 "
                          "통째로 빠진 채 그려진다(파서는 아무 말도 안 한다)"
                          % (_fn, ", ".join(_bad)))
except Exception as _e:
    errors.append("var(--x) 정의 검사 실패: %s" % _e)

# ── 경기 사이클 곡선이 국면과 같은 날을 가리키는가 ────────────────────────
# 🚨 regime_cycle.json 은 regime.json 에서 파생된다. 둘이 따로 커밋되면 곡선 위 점만
#   어제 자리에 남고 화면은 아무 말도 안 한다 — 이 저장소가 반복해 온 '한 화면 두 날짜'다.
#   refresh-regime 워크플로가 둘을 같이 굽고 같이 밀지만, 사람이 손으로 regime.json 만
#   고치는 날이 온다. 그때 여기서 잡는다.
try:
    _rg = json.load(io.open(os.path.join(ROOT, "data", "regime.json"), encoding="utf-8"))
    _cyp = os.path.join(ROOT, "data", "regime_cycle.json")
    if os.path.exists(_cyp):
        _cy = json.load(io.open(_cyp, encoding="utf-8"))
        if _cy.get("as_of") != _rg.get("as_of"):
            errors.append("경기 사이클 곡선 기준일 불일치 — regime_cycle.json %s vs regime.json %s. "
                          "python build/regime_cycle.py 를 다시 돌릴 것"
                          % (_cy.get("as_of"), _rg.get("as_of")))
        _now = (_cy.get("now") or {}).get("r")
        _lab = (_rg.get("regime") or {}).get("label")
        if _now != _lab:
            errors.append("경기 사이클 곡선이 다른 국면을 가리킨다 — 곡선 %s vs 국면 %s" % (_now, _lab))
        # 곡선 위 자리는 빌드가 굽는다 — 화면이 숫자를 새로 적으면 채점기가 두 벌이 된다.
        _rh = io.open(os.path.join(ROOT, "regime.html"), encoding="utf-8").read()
        if "renderCycle" in _rh and "regime_cycle.json" not in _rh:
            errors.append("regime.html 이 renderCycle 을 갖고 있는데 regime_cycle.json 을 안 받는다")
        # 🚨 레퍼런스 원문이 없으면 곡선이 통째로 안 그려진다 — 조용한 빈칸을 만들지 않는다.
        if "renderCycle" in _rh and not (_cy.get("ref") or {}).get("boxes"):
            errors.append("regime_cycle.json 에 ref.boxes 가 없다 — 화면이 통째로 빈다. "
                          "build/regime_cycle.py 를 다시 돌릴 것")
        # 비교표가 쓰는 두 자.
        _sc = _cy.get("sectors") or {}
        if "cmptbl" in _rh:      # 교과서 vs 실측 비교표가 두 자를 다 쓴다
            for _b in ("price", "earn"):
                if not (_sc.get(_b) or {}):
                    errors.append("regime.html 에 선호 업종 탭이 있는데 regime_cycle.json 의 "
                                  "sectors.%s 가 비었다 — build/regime_cycle.py 를 다시 돌릴 것" % _b)
            # 🚨 순위를 화면이 다시 매기면 채점기가 두 벌이 된다. 정렬 코드가 없어야 한다.
            _seg = _rh[_rh.find("function renderCycle"):]
            _seg = _seg[:_seg.find("\n  }")]
            if ".sort(" in _seg:
                errors.append("renderCycle 안에 정렬이 있다 — 순위는 빌드가 정한다(채점기 두 벌 금지)")
except Exception as _e:
    errors.append("경기 사이클 곡선 검사 실패: %s" % _e)

# ── 전략 탐색 풀(rotation_pool.json)이 멈췄는지 ──────────────────────────
# 🚨 2026-08-11 에 사용자가 '최근 갱신이 8월 7일'이라고 짚어서 알았다. 이 풀을 채우는
#   자동 잡은 **없다**(생산자는 로컬 작업 스케줄러 + 헤드리스 Claude 다 — asof_index.py 주석
#   참조). 생산자가 죽으면 화면은 아무 말 없이 옛 동향을 계속 보여 준다.
#   rotation.html 자신도 3영업일부터 경고를 띄우지만 그건 **누가 그 페이지를 열어야** 보인다.
#   여기서 같이 잡아 검증 로그에 남긴다.
#   ⚠ 실패가 아니라 경고다. 갱신 피드와 같은 방침 — 손으로 도는 일 때문에 자동 잡을
#     죽이지 않는다. 문턱은 화면의 경고와 같은 3영업일로 맞춘다(두 화면이 다른 말을 하면 안 된다).
try:
    import datetime as _dtr
    _pool = json.load(io.open(os.path.join(ROOT, "data", "rotation_pool.json"), encoding="utf-8"))
    _gen = _pool.get("generated")
    if _gen:
        _dd, _bd = _dtr.date.fromisoformat(_gen), 0
        while _dd < _dtr.date.today() and _bd < 60:
            _dd += _dtr.timedelta(days=1)
            if _dd.weekday() < 5:
                _bd += 1
        if _bd >= 3:
            print("⚠ 전략 탐색 풀이 %d영업일째 안 돌았다(generated %s). "
                  "이 풀은 자동 잡이 아니라 로컬 스케줄러 + 헤드리스 Claude 가 채운다 — "
                  "생산자가 살아 있는지 확인할 것"
                  "(build/rotation_select.py 독스트링에 절차가 있다)." % (_bd, _gen))
except Exception as _e:
    errors.append("rotation_pool 신선도 검사 실패: %s" % _e)

# ── 일자 정합(데이터 정책 3): 알려진 날짜 필드가 전부 파싱되고 미래가 아니어야 한다 ──
# (실사고: members.json에 미래 날짜 07-23이 들어가 있었음. TZ 여유로 +1일 허용.)
import datetime as _dt
_tomorrow = (_dt.date.today() + _dt.timedelta(days=1)).isoformat()
def _dates_of(fn, j):
    if fn == "stocks.json": return [("as_of", j.get("as_of"))]
    if fn == "home_reco.json": return [("as_of", j.get("as_of"))]
    if fn == "regime.json": return [("as_of", j.get("as_of"))]
    if fn == "sentiment.json": return [("as_of", j.get("as_of")), ("generated_at", (j.get("generated_at") or "")[:10])]
    if fn == "members.json": return [("as_of_members", j.get("as_of_members"))]
    if fn == "updates.json":
        return [("updated", j.get("updated"))] + [(f"events[{i}].dt", e.get("dt")) for i, e in enumerate(j.get("events") or [])]
    if fn == "rotation_pool.json": return [("generated", j.get("generated"))]
    if fn in ("strategy_holdings.json", "strategy_holdings_db.json"):
        return [("generated", j.get("generated"))] + [(f"{nm}.as_of", st.get("as_of")) for nm, st in (j.get("strategies") or {}).items()]
    if fn == "rf_monthly.json": return [("fetched", j.get("fetched")), ("last_obs", j.get("last_obs"))]
    if fn == "strategy_backtests.json":
        out = [("generated", j.get("generated"))]
        for nm, b in (j.get("strategies") or {}).items():
            out += [(f"{nm}.start", b.get("start")), (f"{nm}.end", b.get("end"))]
        return out
    return []
for _fn in ("stocks.json", "home_reco.json", "regime.json", "sentiment.json", "members.json", "rotation_pool.json", "updates.json",
            "strategy_holdings.json", "strategy_holdings_db.json", "strategy_backtests.json", "rf_monthly.json"):
    _p = os.path.join(ROOT, "data", _fn)
    if not os.path.exists(_p): continue
    try:
        _j = json.load(io.open(_p, encoding="utf-8"))
    except Exception:
        continue   # 파싱 오류는 위의 JSON 검사가 이미 보고
    for k, v in _dates_of(_fn, _j):
        if not v:
            errors.append(f"{_fn}: 날짜 필드 {k} 비어 있음"); continue
        try:
            _dt.date.fromisoformat(str(v)[:10])
        except Exception:
            errors.append(f"{_fn}: {k}={v} 날짜 파싱 불가"); continue
        if str(v)[:10] > _tomorrow:
            errors.append(f"{_fn}: {k}={v} 미래 날짜 — 일자 꼬임")
# rotation_select.py 쪽 계약은 잠금과 무관 — 평문 유무와 무관하게 항상 검증(CI 포함)
# 2026-08-06 카테고리 쿼터를 없앴다(사용자 결정). 그래서 대조 대상이 바뀐다:
#   (구) QUOTA·CATORD 가 양쪽에서 같은가   → 선정이 카테고리별 쿼터로 이뤄지던 시절의 계약
#   (신) ① 어느 쪽에도 QUOTA 가 없는가     — 한쪽에만 되살아나면 화면과 갱신 대상이 갈린다
#        ② 뽑는 개수 n 이 양쪽에서 같은가  — 이게 이제 유일한 선정 파라미터다
# CATORD 는 rotation.html 의 분류·색상 표시에만 남아 있어 더는 대조 대상이 아니다.
if qp is not None:
    errors.append("rotation_select.py에 QUOTA가 되살아남 — 카테고리 쿼터는 2026-08-06에 폐지했다. "
                  "선정에 카테고리를 다시 넣으려면 rotation.html과 함께 바꾸고 이 검사도 고칠 것")
if rot is not None and qj is not None:
    errors.append("rotation.html에 QUOTA가 되살아남 — 카테고리 쿼터는 2026-08-06에 폐지했다(위와 같음)")


def _pickn(txt):
    m = re.search(r"pick\(\s*S\s*,\s*(\d+)\s*,", txt)
    return int(m.group(1)) if m else None


_nj = _pickn(rot) if rot is not None else None
_np = _pickn(sel)
if _np is None:
    errors.append("rotation_select.py에서 pick(S, n, …)의 n을 찾지 못함")
if rot is not None:
    if _nj is None:
        errors.append("rotation.html에서 pick(S,n,…)의 n을 찾지 못함")
    elif _np is not None and _nj != _np:
        errors.append(f"선정 개수 불일치: rotation.html {_nj}선 vs rotation_select.py {_np}선 "
                      f"— 화면에 뜨는 전략과 일일잡이 갱신하는 전략이 달라진다")

# ── 시장 국면: 종합 요약(summary)·블록 슬롯 ──────────────────────────────
#   요약 문장은 build/regime_summary.py 한 곳에서만 만든다(verdicts_gen과 같은 재계산 비교).
#   화면이 문장을 직접 쓰면 지표가 바뀌어도 요약만 옛말을 하는 '조용히 틀린' 사고가 난다.
try:
    sys.path.insert(0, os.path.join(ROOT, "build"))
    import regime_summary
    _rj = json.load(io.open(os.path.join(ROOT, "data", "regime.json"), encoding="utf-8"))
    _cur = _rj.get("summary")
    if not _cur:
        errors.append("regime.json에 summary 없음 — build/refresh_regime.py 재실행 필요")
    else:
        # 자기 축을 prev로 넘겨 재계산 → 히스테리시스가 no-op이 되어 결정적. 지표만 갱신되고
        #   요약이 안 구워졌으면 재계산이 달라져 잡힌다.
        _fresh = regime_summary.build(_rj.get("indicators") or [], _rj.get("regime") or {},
                                      prev_axes=_cur.get("axes"))
        if _fresh != _cur:
            errors.append("종합 요약이 지표와 어긋남 — regime_summary.build() 결과와 불일치(지표만 갱신되고 요약이 안 구워졌다)")
        _txt = (_cur.get("text") or "")
        if _txt and regime_summary.guard(_txt):
            errors.append(f"종합 요약 금칙어/규칙 위반: {regime_summary.guard(_txt)}")
        # 요약 문장이 HTML에 하드코딩되면 드리프트한다(주석 제거 후 검사)
        _rh = strip_js(rd("regime.html"))
        if _txt and len(_txt) > 12 and _txt in _rh:
            errors.append(f'regime.html에 요약 문장이 하드코딩됨: "{_txt[:20]}…" — regime.json에서 읽을 것')
except SystemExit as e:
    errors.append(f"종합 요약 빌드 규칙 위반(금칙어 등): {e}")
except Exception as e:
    errors.append(f"종합 요약 검증 실패: {e}")

# ── 시장 국면: #main을 세 슬롯으로 쪼갠 뒤 렌더/실패 경로가 모두 슬롯을 채우는가 ──────
try:
    _rh = rd("regime.html")
    for _slot in ("summary", "regimeperf", "macro"):
        if not re.search(r'id="%s"' % _slot, _rh):
            errors.append(f"regime.html: 슬롯 #{_slot}가 없음 — 블록 재배치가 반쯤 적용됐다")
        elif not re.search(r"el\('%s'\)\.innerHTML" % _slot, _rh):
            errors.append(f"regime.html: #{_slot}에 렌더하는 코드가 없음 — 영구 '불러오는 중…' 슬롯")
    # 실패 경로가 세 슬롯을 한 번에 채우는 fail() 헬퍼를 쓰는지(개별 el('main')= 잔재 금지)
    if "el('main')" in _rh:
        errors.append("regime.html: el('main') 잔재 — #main은 슬롯 3개로 분리됐다")
    if not re.search(r"function fail\(", _rh):
        errors.append("regime.html: 실패 경로 헬퍼 fail()가 없음 — 로드 실패 시 일부 슬롯이 조용히 빈다")
except Exception as e:
    errors.append(f"슬롯 렌더 검증 실패: {e}")

# ── 내비 정본: 22장이 같은 메뉴를 갖는가 ──────────────────────────────────────
# 빌드 스텝이 없으니 "한 곳에서 만들어 전부에 밀어넣고 어긋나면 막는다"가 유일한 보증이다.
try:
    import subprocess as _sp
    # sync_nav.py 는 stdout 을 utf-8 로 고정해 찍는다(그쪽 38번 줄). 여기서 로케일로 읽으면
    # 드리프트 메시지가 깨지거나 디코드 예외로 바뀌어, 진짜 사유가 '실행 실패'로 덮인다.
    _r = _sp.run([sys.executable, os.path.join(ROOT, "build", "sync_nav.py"), "--check"],
                 capture_output=True, text=True, encoding="utf-8")
    if _r.returncode != 0:
        for _l in (_r.stdout or "").strip().split("\n"):
            if "어긋남" in _l:
                errors.append("내비 드리프트: " + _l.strip())
        if not any("내비 드리프트" in e for e in errors):
            errors.append("내비 정본 검사 실패: " + ((_r.stdout or "") + (_r.stderr or ""))[:300])
except Exception as e:
    errors.append(f"내비 정본 검사 실행 실패: {e}")

# ── 정의 없이 쓰이는 CSS 변수 ────────────────────────────────────────────────
# 24장이 각자 CSS를 들고 있어, 공용 부품이 쓰는 토큰을 어떤 페이지가 안 갖고 있어도
# 아무도 알려주지 않는다. 값이 없으면 그 선언은 무효가 되고 색/폭이 조용히 사라진다 —
# stocks.html이 max-width:var(--w-wide)를 정의 없이 써서 폭 제한이 풀려 있었고,
# 내비의 .asofchip.stale이 쓰는 var(--hot)이 두 장에 없어 '낡음' 표시가 무색이었다.
# 대체값이 있는 var(--x, y)는 없어도 동작하므로 세지 않는다.
for _f in PAGES:
    _t = plain(_f, "미정의 CSS 변수 검사")
    if _t is None:
        continue
    _css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", _t, re.S))
    _used = {m.group(1) for m in re.finditer(r"var\(\s*(--[\w-]+)\s*\)", _css)}
    _def = set(re.findall(r"(--[\w-]+)\s*:", _css))
    # 인라인 style·JS setProperty로 요소에 직접 꽂는 것도 정의로 친다
    _inl = set(re.findall(r'style="[^"]*?(--[\w-]+)\s*:', _t)) | \
        set(re.findall(r"setProperty\(\s*['\"](--[\w-]+)", _t))
    _miss = sorted(_used - _def - _inl)
    if _miss:
        errors.append(f"{_f}: 정의 없는 CSS 변수 {', '.join(_miss)} — 그 선언이 통째로 무효가 된다"
                      f"(색·폭이 조용히 사라진다). 셸에 넣거나 페이지에 정의할 것")

# ── 공통 셸 정본: 23장이 같은 글꼴·중립색·타이포를 갖는가 ─────────────────────
# 내비와 같은 이유다. 다만 셸은 **페이지 CSS 뒤에 붙어야만** 이기므로, 마커가 첫 </style>
# 안에 있는지까지 본다 — 마지막 </style>(NAVCSS)에 들어가면 다음 sync_nav가 지운다.
try:
    import subprocess as _sp
    _r = _sp.run([sys.executable, os.path.join(ROOT, "build", "sync_shell.py"), "--check"],
                 capture_output=True, text=True, encoding="utf-8")   # 위 sync_nav 와 같은 이유
    if _r.returncode != 0:
        _msg = ((_r.stdout or "") + (_r.stderr or "")).strip()
        errors.append("공통 셸 드리프트 — build/sync_shell.py를 다시 돌릴 것: "
                      + " / ".join(l.strip() for l in _msg.split("\n") if "셸 " not in l)[:300])
    # 스타일 요소가 엉뚱한 데서 끊기지 않았는가.
    # HTML 파서는 style 안에서 종료 태그를 만나면 **주석 안이든 아니든** 거기서 끊는다.
    # 그러면 뒤의 CSS가 통째로 본문 글자로 쏟아지는데, 화면은 '스타일이 조금 안 먹네' 정도로만
    # 보여서 늦게 발견된다(실제로 셸 도입 때 밟았다). 중괄호·주석 균형으로 잡는다.
    for _f in PAGES:
        _t = plain(_f, "스타일 블록 균형 검사")
        if _t is None:
            continue
        for _n, _m in enumerate(re.finditer(r"<style[^>]*>(.*?)</style>", _t, re.S), 1):
            _css = _m.group(1)
            if _css.count("{") != _css.count("}"):
                errors.append(f"{_f}: {_n}번째 스타일 블록의 중괄호가 안 맞는다({_css.count('{')}/"
                              f"{_css.count('}')}) — 블록 안에 스타일 종료 태그가 섞였을 가능성이 크다")
            if _css.count("/*") != _css.count("*/"):
                errors.append(f"{_f}: {_n}번째 스타일 블록의 주석이 안 닫혔다 — 뒤 CSS가 통째로 죽는다")

    for _f in PAGES:
        _t = plain(_f, "공통 셸 위치 검사")
        if _t is None:
            continue
        _i, _c = _t.find("/* SHELL:BEGIN */"), _t.find("</style>")
        if _i < 0:
            errors.append(f"{_f}: 공통 셸 블록이 없다 — build/sync_shell.py를 돌릴 것")
        elif _i > _c:
            errors.append(f"{_f}: 공통 셸이 첫 </style> 뒤에 있다 — 페이지 CSS를 못 덮거나 "
                          f"NAVCSS 구간에 들어가 다음 sync_nav 실행에서 지워진다")
except Exception as e:
    errors.append(f"공통 셸 검사 실행 실패: {e}")

try:
    _ni = json.load(io.open(os.path.join(ROOT, "build", "nav_items.json"), encoding="utf-8"))
    _tools = [t for c in _ni.get("categories") or [] for t in c.get("tools") or []]

    # ① 실제로 열리는 슬롯이 메뉴에서 '준비중'으로 죽어 있으면 안 된다.
    #    liveness 판정은 sync_nav와 반드시 같은 함수를 써야 한다 — 규칙이 둘이면 한쪽만 맞는다
    #    (앵커 종류 static/route/runtime을 여기서 다시 구현하면 regime.html#axes류가 어긋난다).
    sys.path.insert(0, os.path.join(ROOT, "build"))
    import sync_nav as _sn
    _ix = rd("index.html")
    for _t in _tools:
        if _sn.tool_live(_t) and ('data-nav="%s"' % _t["file"]) not in _ix:
            errors.append(f"내비: {_t['file']}는 열리는데 메뉴가 '준비중'이다 — build/sync_nav.py를 다시 돌릴 것")

    # ② nav_items.json 의 verdict 는 원장(verdicts.json)과 모순되면 안 된다.
    #    ⚠ 2026-08-16 부터 이 값을 **화면에 안 그린다**(사용자 지시로 판정 배지를 걷었다).
    #      그래도 검사는 남긴다 — 값이 자료로 남아 있고, 낡으면 나중에 되살릴 때 조용히
    #      거짓을 말하게 된다. 지금은 '화면의 거짓' 이 아니라 '자료의 낡음' 을 잡는다.
    _vd = json.load(io.open(os.path.join(ROOT, "data", "verdicts.json"), encoding="utf-8"))
    if any(t.get("verdict") == "pass" for t in _tools) and not _vd.get("deploy_n"):
        errors.append("내비: nav_items 에 verdict=pass 인 슬롯이 있는데 verdicts.json deploy_n=0 "
                      "— 원장과 정본이 어긋남(화면에는 안 그리지만 값이 낡았다)")
    if any(t.get("verdict") == "rejected" for t in _tools) and not _vd.get("reject_total"):
        errors.append("내비: nav_items 에 verdict=rejected 인 슬롯이 있는데 verdicts.json "
                      "reject_total=0 — 원장과 정본이 어긋남")

    # ③ 모든 배포 HTML은 자기가 어느 슬롯인지 밝혀야 한다(현재위치 강조의 유일한 입력).
    # 홈은 도구가 아니라 도구들의 관문이라 슬롯 목록에 없다 — 유효한 data-tool로 인정한다
    # 🚨 2026-08-12 — **메뉴에서 뺐지만 남아 있는 페이지**도 유효한 슬롯으로 인정한다.
    #   nav_items.json 의 retired[].was_file 이 그 목록이다(BK/kb.html 이 첫 사례).
    #   전에는 이 검사가 '메뉴에 없으면 고아'로 봤는데, 이 저장소의 규약은
    #   "칸은 지우되 사유는 지우지 않는다" 라 **뺀 페이지가 사유와 함께 남는 것이 정상**이다.
    #   그 사유가 retired 에 적혀 있으면 통과시키고, 안 적혀 있으면 그대로 막는다 —
    #   즉 '조용히 사라진 슬롯'과 '기록하고 뺀 슬롯'을 가른다.
    _retired_files = {(r.get("was_file") or "").split("#")[0]
                      for r in (_ni.get("retired") or [])} - {""}
    _known = ({t["file"].split("#")[0] for t in _tools} | {"index.html"}) | _retired_files
    for _fn in sorted(f for f in os.listdir(ROOT)
                      if f.endswith(".html") and f not in REDIRECTS):
        _s = rd(_fn)
        _m = re.search(r'<body[^>]*\sdata-tool="([^"]*)"', _s)
        if not _m:
            errors.append(f"{_fn}: <body data-tool> 없음 — 내비가 현재 위치를 표시할 수 없다")
        elif _m.group(1) not in _known:
            errors.append(f"{_fn}: data-tool='{_m.group(1)}'가 nav_items.json에 없는 슬롯")
except Exception as e:
    errors.append(f"내비 정합 검증 실패: {e}")

# ── 텍스트 open()에 encoding 명시 강제 ────────────────────────────────────────
# encoding 을 빼면 파이썬이 **OS 기본 코덱**을 쓴다. CI 러너는 Linux(UTF-8)라 항상 통과하지만
# 한국어 Windows 는 cp949 → 한글이 든 JSON 을 읽는 순간 UnicodeDecodeError 로 죽는다.
# 즉 **CI가 구조적으로 못 잡는 부류**다(2026-07-27 refresh_stocks.py:630 실측 — 사내 PC에서 생성기를
# 직접 돌릴 때만 터졌다). 그래서 실행이 아니라 정적 검사로 잡는다.
# 정밀도: 내장 open() 만 본다. ZipFile.open 등 `x.open(...)` 은 애초에 encoding 인자가 없고
#   바이너리를 주므로 대상이 아니다(전수 확인: 4곳 모두 io.TextIOWrapper(..., "utf-8") 로 감싸고 있다).
#   바이너리 모드('b')도 제외 — encoding 을 주면 오히려 예외가 난다.
try:
    import ast as _ast, glob as _glob
    _enc_bad = []
    for _p in sorted(_glob.glob(os.path.join(ROOT, "build", "*.py"))):
        _s = io.open(_p, encoding="utf-8").read()
        try:
            _tree = _ast.parse(_s)
        except SyntaxError:
            continue          # 문법 오류는 별도 검사의 몫이다
        for _nd in _ast.walk(_tree):
            if not (isinstance(_nd, _ast.Call) and isinstance(_nd.func, _ast.Name) and _nd.func.id == "open"):
                continue
            if any(_k.arg == "encoding" for _k in _nd.keywords):
                continue
            _mode = ""
            if len(_nd.args) > 1 and isinstance(_nd.args[1], _ast.Constant):
                _mode = str(_nd.args[1].value)
            for _k in _nd.keywords:
                if _k.arg == "mode" and isinstance(_k.value, _ast.Constant):
                    _mode = str(_k.value.value)
            if "b" in _mode:
                continue
            _enc_bad.append(f"{os.path.basename(_p)}:{_nd.lineno}")
    if _enc_bad:
        errors.append(f"open() encoding 미지정 {len(_enc_bad)}곳 ({', '.join(_enc_bad[:5])}) — "
                      "한국어 Windows(cp949)에서 UnicodeDecodeError로 죽는다. encoding='utf-8'을 명시할 것")
    # 짝이 되는 출력 쪽 문제: 읽기를 고쳐도 stdout 이 cp949 면 ⚠·— 를 print 하는 순간 죽는다.
    #   (실측: ⚠ U+26A0 · — U+2014 · ❌ · 🔴 모두 cp949 에 없다. 40개 파일 전부 해당됐다.)
    #   집안 관례: 임포트 직후 `try: sys.stdout.reconfigure(encoding="utf-8") / except Exception: pass`.
    def _cp949_ok(ch):
        try:
            ch.encode("cp949")
            return True
        except UnicodeEncodeError:
            return False

    # ⚠ '프렐류드가 있다'로 끝내면 안 된다. sys 가 **모듈 최상위**에 임포트돼 있지 않으면
    #   sys.stdout.reconfigure 가 NameError 를 내고 `except Exception: pass` 가 그걸 삼켜
    #   프렐류드가 조용히 무력해진다(실측: 함수 안에만 import sys 가 있던 4개 파일).
    #   그래서 프렐류드 유무가 아니라 **실제로 동작하는가**를 본다.
    _rc_bad = []
    for _p in sorted(_glob.glob(os.path.join(ROOT, "build", "*.py"))):
        _s = io.open(_p, encoding="utf-8").read()
        if not any(not _cp949_ok(_c) for _c in set(_s)):
            continue                      # cp949 로 다 쓸 수 있으면 프렐류드가 필요 없다
        if "reconfigure" not in _s:
            _rc_bad.append(os.path.basename(_p) + " (프렐류드 없음)"); continue
        try:
            _t = _ast.parse(_s)
        except SyntaxError:
            continue
        if not any(isinstance(_n, _ast.Import) and any(_a.name == "sys" for _a in _n.names)
                   for _n in _t.body):
            _rc_bad.append(os.path.basename(_p) + " (import sys 가 최상위에 없어 프렐류드가 무력)")
    if _rc_bad:
        errors.append(f"stdout UTF-8 재설정 누락 {len(_rc_bad)}개 ({', '.join(_rc_bad[:5])}) — "
                      "cp949 콘솔에서 print 시 UnicodeEncodeError로 죽는다. "
                      'try: sys.stdout.reconfigure(encoding="utf-8") 프렐류드를 추가할 것')
except Exception as _e:
    errors.append(f"open() encoding 검사 실패: {_e}")


# ── 기준일 정본: data/asof.json이 stocks.json과 어긋나면 전 페이지 칩이 거짓이 된다 ──
try:
    _ao = json.load(io.open(os.path.join(ROOT, "data", "asof.json"), encoding="utf-8"))
    _stk2 = json.load(io.open(os.path.join(ROOT, "data", "stocks.json"), encoding="utf-8"))
    if _ao.get("primary") != _stk2.get("as_of"):
        errors.append(f"기준일 정본 불일치: asof.json primary {_ao.get('primary')} vs "
                      f"stocks.json as_of {_stk2.get('as_of')} — build/asof_index.py를 다시 돌릴 것")
    if not (_ao.get("axes") or []):
        errors.append("asof.json에 축이 비어 있음")
except Exception as e:
    errors.append(f"기준일 정본 검증 실패: {e}")

# ── 평문 필드에 마크다운이 섞이는 걸 막는다 ─────────────────────────────────
# rotation.html은 카드 본문을 esc()로 감싸 넣는다 — HTML도 마크다운도 렌더되지 않는다.
# 그런데 갱신은 사람(혹은 헤드리스 작업)이 텍스트로 쓰므로 **볼드**가 섞이기 쉽고,
# 그러면 화면에 별표가 그대로 찍힌다(2026-07-25에 12장이 그렇게 나갔다).
try:
    _rp = json.load(io.open(os.path.join(ROOT, "data", "rotation_pool.json"), encoding="utf-8"))
    _plain = ("purpose", "principle", "entry", "performance", "recent")
    _md = []
    for _s in (_rp.get("strategies") or []):
        for _f in _plain:
            _v = _s.get(_f)
            if isinstance(_v, str) and ("**" in _v or "<b>" in _v):
                _md.append("%s.%s" % (_s.get("id", "?"), _f))
    if _md:
        errors.append("rotation_pool: 평문 필드에 마크다운/HTML이 있습니다 — esc()로 감싸 렌더되므로 "
                      "화면에 기호가 그대로 찍힙니다: " + ", ".join(_md[:8]))
except Exception as e:
    errors.append(f"rotation_pool 평문 검사 실패: {e}")

# ── 자격증명이 소스로 새어 들어가는 걸 막는다 ────────────────────────────────
# 실사고: FRED API 키가 "시크릿 미설정 시 크래시 방지" 폴백으로 build/refresh_regime.py에
# 박힌 채 공개 저장소에 올라가 있었다(2026-07-25 발견·정리). 조용한 폴백은 편해 보이지만,
# 그 편함의 대가가 '키가 공개돼도 아무도 모른다'였다. 다시 들어오면 여기서 막는다.
#
# 검사 대상은 build/*.py의 32자리 hex 리터럴(FRED 키 형식)과 흔한 API 키 접두사다.
# 해시·지문은 이 사이트에서 12~16자리를 쓰므로 32자리와 겹치지 않는다(도입 시점 실측 0건).
try:
    _SECRET_PATS = [
        (re.compile(r"""["'`]([0-9a-f]{32})["'`]"""), "32자리 hex(FRED API 키 형식)"),
        (re.compile(r"""["'`](sk-[A-Za-z0-9_\-]{20,})["'`]"""), "sk- 접두 키"),
        (re.compile(r"""["'`](gh[pousr]_[A-Za-z0-9]{20,})["'`]"""), "GitHub 토큰"),
        (re.compile(r"""["'`](AKIA[0-9A-Z]{16})["'`]"""), "AWS 액세스 키"),
    ]
    _bdir = os.path.join(ROOT, "build")
    for _fn in sorted(os.listdir(_bdir)):
        if not _fn.endswith((".py", ".sh")):
            continue
        _src = io.open(os.path.join(_bdir, _fn), encoding="utf-8").read()
        for _pat, _what in _SECRET_PATS:
            _m = _pat.search(_src)
            if _m:
                errors.append(
                    f"자격증명 유출 의심: build/{_fn}에 {_what} 리터럴이 있습니다 "
                    f"({_m.group(1)[:6]}…) — 시크릿(os.getenv)으로 옮기고 키를 폐기·재발급하세요")
except Exception as e:
    errors.append(f"자격증명 검사 실패: {e}")

# ── 갱신 피드: 기록할 수단이 없어서 조용히 비는 일을 막는다 ──────────────────
# 실사고: 도구를 여럿 새로 만든 사흘(2026-07-23~25) 동안 updates.json이 한 줄도 늘지 않았다.
# 원인은 log_update.py의 TARGETS가 옛 7개로 고정돼 새 화면은 기록 자체가 거부됐기 때문이다.
# 두 집합(기록 가능한 target · 홈이 이름을 아는 target)이 어긋나면 여기서 막는다.
try:
    _lu = rd("build/log_update.py")
    _m = re.search(r"TARGETS\s*=\s*\{(.*?)\}", _lu, re.S)
    # 🚨 2026-08-06 — 주석을 걷어내고 본다. 종전에는 블록 전문에 정규식을 물려서,
    #   주석 안에 따옴표로 적힌 이름까지 target 으로 셌다. 실제로 물렸다 — industry 를
    #   빼면서 "왜 뺐는지"를 주석에 적었더니 그 주석 때문에 '아직 남아 있다'로 잡혔다.
    #   validate_site 안에서만 오늘 세 번째다(ci_push 검사·도움말 태그 검사·여기).
    #   검사가 코드를 볼 때는 **살아 있는 줄만** 봐야 한다.
    _live_t = chr(10).join(_ln.split("#", 1)[0] for _ln in (_m.group(1) if _m else "").split(chr(10)))
    _lt = set(re.findall(r'"([a-z]+)"', _live_t)) if _m else set()
    # UPD 정본은 2026-07-25부터 updates.html에 있다(홈에서 갱신 피드를 뺐다).
    _ix2 = rd("updates.html")
    _m2 = re.search(r"var UPD=\{(.*?)\};", _ix2, re.S)
    _ut = set(re.findall(r"(?:^|[,{\s])([a-z]+):\[", _m2.group(1))) if _m2 else set()
    if not _lt or not _ut:
        errors.append("갱신 피드 대상 집합을 파싱하지 못함(log_update.py TARGETS / updates.html UPD)")
    else:
        _only_lu, _only_ix = sorted(_lt - _ut), sorted(_ut - _lt)
        if _only_lu:
            errors.append(f"갱신 피드: log_update.py에만 있는 target {_only_lu} — 갱신 기록에서 '기타'로 떨어진다")
        if _only_ix:
            errors.append(f"갱신 피드: updates.html UPD에만 있는 target {_only_ix} — 기록할 수단이 없다")
    # 실제로 쓰인 target이 둘 중 어디에도 없으면 그 이벤트는 영영 '기타'다
    _uj = json.load(io.open(os.path.join(ROOT, "data", "updates.json"), encoding="utf-8"))
    _used = {e.get("target") for e in (_uj.get("events") or [])}
    _unknown = sorted(_used - _lt - {None})
    if _unknown:
        errors.append(f"updates.json에 정의되지 않은 target {_unknown} — TARGETS/UPD에 추가할 것")
except Exception as e:
    errors.append(f"갱신 피드 검증 실패: {e}")

# ── 홈 하드코딩 문구가 데이터와 따로 썩지 않게 ────────────────────────────────
# (실사고: meta description은 512종목, 본문 히어로는 518종목 — 검색 스니펫·공유 카드에만 옛 유니버스가 나갔다)
# ⚠ 2026-08-03: index.html 만 보던 것을 **전 페이지**로 넓혔다. 그날 sources.html 이 '512종목'을
#   띄우고 있었는데(실제 518) 이 검사가 못 잡았다 — 같은 화면의 메가메뉴는 셸이 뿌린 518 을 띄워
#   한 화면에 512 와 518 이 같이 보였다. 위 주석이 기록한 사고와 **같은 사고**가 다른 파일에서
#   반복된 것이다.
#   범위를 n±30 으로 좁힌 이유 — 'NASDAQ 100 종목'·'상위 200종목'·'488사' 처럼 유니버스가
#   아닌 수가 걸린다(실측 오탐 3건). 유니버스 크기로 읽힐 만한 수만 본다.
try:
    # _sj는 383행에서 screens.json으로 재사용된다 — 여기서 stocks.json을 다시 읽는다
    _stk = json.load(io.open(os.path.join(ROOT, "data", "stocks.json"), encoding="utf-8"))
    _n = int(_stk.get("n_stocks") or len(_stk.get("stocks") or []))
    # 지수 이름이 앞에 오면 유니버스 수가 아니다('S&P 500 종목 중 …'). 실측으로 걸린 오탐이다.
    _IXNAME = ("S&P", "S&amp;P", "NASDAQ", "Nasdaq", "나스닥", "러셀", "Russell", "다우")
    for _pg in sorted(f for f in os.listdir(ROOT) if f.endswith(".html")):
        try:
            _src = rd(_pg)
        except Exception:
            continue
        # 주석은 뺀다 — 과거 사고를 기록해 둔 주석까지 잡으면 그 기록을 못 남긴다.
        # HTML 주석과 <script> 안의 JS 주석 둘 다(실측: stocks.html 의 '// … 512종목 …' 이 걸렸다).
        _body = re.sub(r"(?s)<!--.*?-->", "", _src)
        _body = re.sub(r"(?s)/\*.*?\*/", "", _body)
        _body = re.sub(r"(?m)^\s*//.*$", "", _body)
        for _m in re.finditer(r"(?<![0-9])(\d{3})\s*종목(?![0-9])", _body):
            _v = int(_m.group(1))
            if _v == _n or abs(_v - _n) > 30:          # 유니버스 크기로 읽힐 수만 본다
                continue
            # ⚠ 지수명이 **바로 앞**일 때만 면제한다('S&P 500 종목'). 앞쪽 아무 데나 있으면
            #   면제하던 판이 'S&P 500 · NASDAQ 100 512종목'의 512 까지 놓쳤다(실측).
            _pre = _body[max(0, _m.start() - 12):_m.start()]
            if any(_pre.endswith(_x + " ") or _pre.endswith(_x) for _x in _IXNAME):
                continue
            errors.append(f"{_pg} '{_m.group(0)}' ≠ stocks.json n_stocks {_n} — 유니버스 표기 갱신 누락")
except Exception as e:
    errors.append(f"유니버스 표기 검증 실패: {e}")

# ── 자물쇠 역방향: 잠기지 않은 페이지에 🔒를 달지 않는다 ─────────────────────
# 아래 정방향 검사(잠긴 페이지에 🔒가 없다)만 있어서 반대 방향이 오래 살아 있었다 —
# 2026-08-03 실측으로 공개 페이지 sources.html 에 '열람 암호 필요' 자물쇠가 10개 파일 푸터에,
# explorer.html 에도 하나 붙어 있었다(총 11곳). 데이터 계보를 공개한다는 페이지가 잠긴 것처럼
# 보이는 것은 잠금을 예고 안 하는 것만큼 나쁘다.
try:
    _locked = set()
    for _f in os.listdir(ROOT):
        if not _f.endswith(".html"):
            continue
        try:
            if "crypto.subtle" in rd(_f):
                _locked.add(_f)
        except Exception:
            continue
    for _pg in sorted(f for f in os.listdir(ROOT) if f.endswith(".html")):
        try:
            _src = rd(_pg)
        except Exception:
            continue
        for _m in re.finditer(r'<a[^>]+href="([^"#?]+)[^"]*"[^>]*>(?:(?!</a>).)*</a>\s*<span[^>]*>\s*\U0001F512', _src, re.S):
            _t = _m.group(1)
            if _t.endswith(".html") and _t not in _locked:
                errors.append(f"{_pg}: 잠기지 않은 {_t} 에 🔒가 붙었다 — 공개 페이지를 잠긴 것처럼 보이게 한다")
except Exception as e:
    errors.append(f"자물쇠 역방향 검증 실패: {e}")

# ── 자물쇠 표기 규약: 암호 게이트가 있는 페이지는 홈 내비에서 🔒로 예고돼야 한다 ──
# 히어로가 '판정을 전부 공개합니다'라고 적어둔 터라, 예고 없는 암호창은 잠금 자체보다 신뢰를 깎는다.
try:
    _ix = rd("index.html")
    _tools = _tools if "_tools" in dir() else []
    for _pg in sorted(f for f in os.listdir(ROOT) if f.endswith(".html") and f != "index.html"):
        try:
            _src = rd(_pg)
        except Exception:
            continue
        if "crypto.subtle" not in _src:
            continue
        _a = re.search(r'<a[^>]*href="%s(?:#[^"]*)?"[^>]*>(.*?)</a>' % re.escape(_pg), _ix, re.S)
        if not _a:
            continue          # 홈이 링크하지 않는 잠금 페이지는 이 규약의 대상이 아니다
        if "🔒" not in _a.group(1):
            errors.append(f"index.html 내비: {_pg}는 암호 잠금인데 링크에 🔒 표기가 없음 — 예고 없는 암호창")
        # 메뉴 정본에도 같은 사실이 적혀 있어야 한다(정본이 틀리면 다음 sync에서 🔒가 사라진다)
        if not any(t.get("locked") for t in _tools if t["file"].split("#")[0] == _pg):
            errors.append(f"nav_items.json: {_pg}는 암호 잠금인데 locked 표시가 없음")
except Exception as e:
    errors.append(f"자물쇠 표기 검증 실패: {e}")

# 평문 필수 모드: 일일잡이 도는 운영 PC에서는 SKIP=실패로 승격(사본 소실이 무경보 강등으로 이어지지 않게).
# 단, 승격 대상은 **평문 부재(skips)만**이다. 도구 부재(tool_skips)는 사본을 채워도 안 사라지므로
# 여기서 죽이면 잡이 영구히 실패한다 — 대신 아래에서 계속 눈에 띄게 경고한다.
if skips and os.environ.get("VALIDATE_REQUIRE_PLAINTEXT") == "1":
    errors.append(f"평문 필수 모드인데 평문 부재로 {len(skips)}개 검사가 SKIP됨 — 이 머신에서는 _build/pages 전체 검증이 계약이다")
if skips:
    print(f"⚠ 잠금 페이지 평문 부재(_build/pages/) — {len(skips)}개 검사 건너뜀(통과가 아니라 미검증이다. 평문 있는 곳에서 검증할 것):")
    for s in sorted(skips): print("  ~", s)
# ⚠ 여기서 찍는 것은 **이 시점까지** 쌓인 것뿐이다. 아래에서 더 쌓이므로 파일 끝에서 한 번 더 찍는다.
_skips_shown = set()
if tool_skips:
    print(f"⚠ 검사 도구 부재 — {len(tool_skips)}개 검사 건너뜀(미검증이다. node 를 설치하면 되살아난다. CI 에서는 이미 오류로 잡는다):")
    for s in sorted(tool_skips): print("  ~", s)
    _skips_shown = set(tool_skips)

# ── 편향 캐비엇의 기준일이 표와 갈렸는가 ─────────────────────────────────
# style.html 의 캐비엇은 style_perf.json 의 caveat 을 그대로 찍고, 그 문자열은 build/style_top_pdf.py
# 가 **style_pit.json** 의 base/pit 에서 만든다. 두 파일의 as_of 가 다르면 캐비엇이 인용하는
# '보정 전' 수치가 같은 화면의 표와 안 맞는다 — 2026-08-03 실측: pit 07-29 vs perf 07-31 이라
# 성장의 '보정 전'(+44%)이 표(+23.21%)보다 오히려 높아, 독자가 보정 배율을 대응시킬 수 없었다.
#
# 🚨 **경고로만 낸다(errors 아님).** style_pit.py 는 가격 캐시(data/_pit_px_cache.json, gitignore)
#    이 있어야 돌아 러너에서 재생성할 수 없다. errors 로 올리면 그 파일을 못 만드는 CI 가
#    영구히 빨간불이 되어 일일 데이터 잡 전부가 멈춘다.
#    → build/style_pit.py 를 style_top_pdf 와 같은 as_of 로 한 번 돌린 뒤,
#      이 블록을 errors.append 로 승격할 것.
try:
    _pp = os.path.join(ROOT, "data", "style_pit.json")
    _qq = os.path.join(ROOT, "data", "style_perf.json")
    if os.path.exists(_pp) and os.path.exists(_qq):
        _pa = (json.load(io.open(_pp, encoding="utf-8")) or {}).get("as_of")
        _qa = (json.load(io.open(_qq, encoding="utf-8")) or {}).get("as_of")
        if _pa and _qa and _pa != _qa:
            print(f"⚠ 편향 캐비엇 기준일 불일치 — style_pit.json {_pa} vs style_perf.json {_qa}. "
                  f"style.html 캐비엇의 '보정 전' 수치가 같은 화면의 표와 다른 날을 가리킨다. "
                  f"build/style_pit.py 재실행 필요(가격 캐시가 있는 PC 에서).")
        # 🚨 2026-09-03 — **두 파일의 as_of 만 보는 것으로는 부족했다.**
        #   캐비엇 «문자열 안»에 기준일이 따로 박혀 나간다("… (2026-08-31 기준)").
        #   그 문장은 style_top_pdf.pit_caveat() 이 **디스크의 style_pit.json** 을 읽어
        #   만드는데, style_pit.py 는 style_perf.json 을 앵커로 쓰므로 그 뒤에 돈다 —
        #   두 빌더가 서로의 산출물을 읽는 **순환**이라 캐비엇이 한 판 뒤진다.
        #   실측 2026-09-02: 두 파일 as_of 가 둘 다 09-01 이라 위 검사는 **통과했는데**
        #   캐비엇 본문은 「2026-08-31 기준」이었고 인용한 수 여섯 개가 전부 어긋났다.
        #   방어가 정확히 그 한 칸을 안 본 것이다. 그래서 **문자열 안의 날짜**를 직접 판다.
        #   ⚠ 순환 자체는 build/style_pit.py 가 산출 뒤 그 칸을 다시 찍어 끊었다.
        #     이 검사는 그 보정이 빠졌을 때 잡는 그물이다(고침과 그물을 같이 둔다).
        _cv = (json.load(io.open(_qq, encoding="utf-8")) or {}).get("caveat") or ""
        _cm = re.search(r"\((\d{4}-\d{2}-\d{2}) 기준\)", _cv)
        if _cm and _pa and _cm.group(1) != _pa:
            errors.append(
                f"편향 캐비엇 본문이 옛 기준일을 말한다 — 문장 안 '{_cm.group(1)} 기준' vs "
                f"style_pit.json {_pa}. 화면에 나가는 «보정 전 → 보정 후» 수치가 그날 것이 "
                f"아니다(실측 2026-09-02 에 여섯 개가 전부 어긋났다). "
                f"build/style_pit.py 를 다시 돌릴 것 — 그 끝에서 캐비엇을 다시 찍는다")
except Exception as _e:
    print(f"⚠ 편향 캐비엇 기준일 검사 실패: {_e}")

# ── 다중검정 분모를 **손으로 적은 자리**가 또 생겼는가 ─────────────────────────
# 🚨 2026-09-03 — 시행 수 N 이 산문에만 있어 낡아 있었다. 실측: 전 원천 sid 합집합이 440 인데
#   build/report_durstyle_pdf.py 는 상수로 「시행 304회」, PREREG-2026-09-03-BMROT-RESULT 는
#   「311」이라 적었다. 세 수가 다 다르다.
#   → strategy_index.json 이 trials.n 을 **세어 싣게** 했고, 살아 있는 소비자는 그것을 읽는다.
#   이 검사는 **build/*.py 에 다시 손으로 박히는 것**을 잡는다(RESULT.md 는 그때의 기록이므로
#   대상이 아니다 — 기록을 나중에 손대는 것이 더 나쁘다).
try:
    _tn = ((json.load(io.open(os.path.join(ROOT, "data", "strategy_index.json"), encoding="utf-8"))
            .get("trials") or {}).get("n"))
    if _tn:
        _hard = []
        for _f in sorted(os.listdir(os.path.join(ROOT, "build"))):
            if not _f.endswith(".py"):
                continue
            _s = io.open(os.path.join(ROOT, "build", _f), encoding="utf-8").read()
            # 주석은 걷어낸다 — 사고 기록에 옛 수가 적혀 있는 것은 정상이다.
            _live = "\n".join(_l.split("#", 1)[0] for _l in _s.split("\n"))
            for _m in re.finditer(r"시행\s*(\d{2,4})\s*회", _live):
                if int(_m.group(1)) != _tn:
                    _hard.append("%s(%s회)" % (_f, _m.group(1)))
        if _hard:
            errors.append(
                "다중검정 분모를 손으로 적은 자리 %d곳: %s — 지금 실측은 %d회다. "
                "strategy_index.json 의 trials.n 을 읽을 것(손으로 적은 수는 낡는다)"
                % (len(_hard), ", ".join(_hard[:4]), _tn))
        else:
            print("  ~ 다중검정 분모 대조 통과(실측 %d회 · 손으로 박힌 자리 0곳)" % _tn)
except Exception as _e:
    print("⚠ 다중검정 분모 대조 실패: %s" % _e)

# ── 사전등록 규율: 「계산 전 커밋」이 **검증 가능한가** ─────────────────────────
# 🚨 2026-09-03 — 이 랩의 신뢰는 「등록을 먼저 커밋하고 그 다음에 계산했다」에 걸려 있다.
#   RESULT 문서마다 그 해시를 적어 두는데, **그 해시가 실제로 증명이 되는지는 아무도 안 봤다.**
#   전수 실측(RESULT 61편):
#       31편  등록 커밋이 결과 커밋의 조상 — 정상, 기계로 증명된다
#       20편  계산 전 커밋 해시가 아예 없다
#        9편  해시는 진짜 등록 커밋인데 **main 의 조상이 아니다**(리베이스로 떨어진 고아)
#        1편  해시가 저장소에 없는 개체다 — PREREG-2026-08-04-RESULT.md 의 14b1aa5
#   ⚠ 고아 9편은 **내용상으로는 결백하다** — 커밋 개체가 실재하고 날짜·메시지가 등록 그대로다.
#     문제는 증명이 삭아 간다는 것이다: 고아는 언젠가 gc 되고, 그때 14b1aa5 처럼 사라진다.
#     즉 1편은 사고가 아니라 **9편의 미래**다.
#   → 옛 문서를 고쳐 쓰지 않는다(기록을 나중에 손대는 것이 더 나쁘다). 대신 **앞으로**를
#     강제한다 — 오늘 이후 날짜의 등록은 «main 의 조상인» 해시를 적어야 한다.
#     그리고 현재 분포를 매 실행 찍어 조용히 삭지 않게 한다.
try:
    import subprocess as _sp2
    _CUT = "2026-09-03"          # 이 날짜 이후 등록부터 강제한다(옛 문서는 소급 적용 안 한다)
    _pr = {"ok": 0, "nohash": [], "bad": [], "orphan": []}
    for _fn in sorted(os.listdir(os.path.join(ROOT, "build"))):
        if not (_fn.startswith("PREREG-") and _fn.endswith("-RESULT.md")):
            continue
        _dm = re.match(r"PREREG-(\d{4}-\d{2}-\d{2})-", _fn)
        _new = bool(_dm and _dm.group(1) >= _CUT)
        _txt = io.open(os.path.join(ROOT, "build", _fn), encoding="utf-8").read()
        _hm = re.search(r"커밋\s*[`'\"]?([0-9a-f]{7,40})", _txt)
        if not _hm:
            _pr["nohash"].append((_fn, _new)); continue
        _h = _hm.group(1)
        if _sp2.run(["git", "cat-file", "-e", _h + "^{commit}"], cwd=ROOT,
                    stdout=_sp2.DEVNULL, stderr=_sp2.DEVNULL).returncode != 0:
            _pr["bad"].append((_fn, _h, _new)); continue
        if _sp2.run(["git", "merge-base", "--is-ancestor", _h, "HEAD"], cwd=ROOT,
                    stdout=_sp2.DEVNULL, stderr=_sp2.DEVNULL).returncode != 0:
            _pr["orphan"].append((_fn, _h, _new)); continue
        _pr["ok"] += 1
    _newbad = ([f for f, n in _pr["nohash"] if n]
               + [f for f, _h, n in _pr["bad"] if n]
               + [f for f, _h, n in _pr["orphan"] if n])
    if _newbad:
        errors.append(
            "사전등록 %d편이 «계산 전 커밋» 을 증명하지 못한다: %s — %s 이후 등록은 "
            "해시가 있어야 하고 그것이 **main 의 조상**이어야 한다(고아 커밋은 gc 되면 "
            "증명이 사라진다. 실측으로 이미 한 편이 그렇게 사라졌다)"
            % (len(_newbad), ", ".join(sorted(_newbad)[:4]), _CUT))
    print("  ~ 사전등록 해시 대조 — 증명됨 %d편 · 해시 없음 %d · 고아 %d · 개체 없음 %d "
          "(%s 이전은 소급 적용하지 않는다)"
          % (_pr["ok"], len(_pr["nohash"]), len(_pr["orphan"]), len(_pr["bad"]), _CUT))
except Exception as _e:
    print("⚠ 사전등록 해시 대조 실패: %s" % _e)

# ── 가격 패널 길이: 본체와 상세가 같은 좌표계인가 ──────────────────────────
#   stocks.json 의 bms/sms 는 pxd_dates 에 대한 **위치 인덱스**다. 본체와 data/sd 가
#   다른 커밋에서 오면 타점이 엉뚱한 날짜를 가리키는데, 길이만 재면 기계적으로 잡힌다.
#   (2026-07-27 패널 753→2514 전환 때 이 검사가 없어 부분 배포 위험을 눈으로 확인해야 했다)
try:
    _sj = json.load(io.open(os.path.join(ROOT, "data", "stocks.json"), encoding="utf-8"))
    _pn = len(_sj.get("pxd_dates") or [])
    _bad = []
    for _s in (_sj.get("stocks") or [])[:40]:      # 40종 표본이면 부분 배포는 반드시 걸린다
        _f = os.path.join(ROOT, "data", "sd", _s["t"] + ".json")
        if not os.path.exists(_f):
            continue
        _n = len(json.load(io.open(_f, encoding="utf-8")).get("pxd") or [])
        if _pn and _n != _pn:
            _bad.append("%s(%d)" % (_s["t"], _n))
    if _bad:
        errors.append("가격 패널 길이 불일치 — pxd_dates %d vs %s. stocks.json 과 data/sd 가 "
                      "다른 커밋에서 왔다(bms/sms 는 위치 인덱스라 타점이 어긋난다)"
                      % (_pn, ", ".join(_bad[:6])))
except Exception as e:
    errors.append(f"가격 패널 길이 검사 실패: {e}")

# ── 게시 문구의 기간 표기가 실제 표본과 맞는가 ─────────────────────────────
#   "표본이 3년(2254거래일)뿐이다"(tech), "표본이 3년뿐이고 그중 대부분이 강세장"(signals) —
#   둘 다 실제로 게시됐던 문장이다. 거래일 수는 데이터에서 파생하면서 연수만 손으로 적어 둔 탓.
#
#   ⚠ 연수 리터럴을 전부 잡으면 안 된다. 정당한 용법이 섞여 있다:
#     · assets.limits "공개 CSV가 최근 3년만 준다"  → 정보원 라이선스 한계
#     · ml.protocol   "검정 구간이 2년(504거래일) 미만이면"  → 판정 문턱
#   그래서 두 갈래로 나눠 본다.
#     ① 자기정합 — 한 문장 안에 '연'과 '거래일'이 같이 나오면 서로 맞아야 한다.
#        문서의 n_days 가 없어도 성립하고, 문턱 서술("2년(504거래일)")은 자연히 통과한다.
#     ② 표본 주장 — "표본이/표본은/과거 N년"처럼 표본 길이를 단언하는 꼴만 골라
#        그 문서의 n_days 와 대조한다.
_PER_FILES = ("tech_strategies.json", "signal_lab.json", "guru_clone.json",
              "assets.json", "strategy_backtests.json", "archive_backtests.json")
_PER_KEYS = ("limits", "protocol", "note", "notes", "caveats")
#   '최근 N년'은 넣지 않는다 — assets.limits 의 "공개 CSV가 최근 3년만 준다"(정보원 라이선스
#   한계)를 표본 주장으로 오탐했다. 표본을 단언하는 꼴만 남긴다.
_CLAIM = re.compile(r"(?:표본(?:이|은|을)?|구간(?:이|은)?|과거)\s*(\d+(?:\.\d+)?)\s*년")
_PAIR = re.compile(r"(\d+(?:\.\d+)?)\s*년\s*\(?\s*([\d,]+)\s*거래일")
for _fn in _PER_FILES:
    _p = os.path.join(ROOT, "data", _fn)
    if not os.path.exists(_p):
        continue
    try:
        _d = json.load(io.open(_p, encoding="utf-8"))
    except Exception as e:
        errors.append(f"{_fn}: 기간 표기 검사용 로드 실패 — {e}")
        continue
    if not isinstance(_d, dict):
        continue
    _nd = _d.get("n_days")
    _sents = []
    for _k in _PER_KEYS:
        _v = _d.get(_k)
        if not _v:
            continue
        for _s in (_v if isinstance(_v, list) else [_v]):
            _sents.append((_k, str(_s)))
    for _k, _s in _sents:
        # ① 같은 문장 안의 연 ↔ 거래일 자기정합
        for _m in _PAIR.finditer(_s):
            _y, _td = float(_m.group(1)), int(_m.group(2).replace(",", ""))
            if abs(_y - _td / 252.0) > 1.0:
                errors.append("%s.%s: '%s년(%s거래일)' 이 서로 안 맞는다(%.1f년) — "
                              "연수를 손으로 적지 말고 거래일에서 파생할 것"
                              % (_fn, _k, _m.group(1), _m.group(2), _td / 252.0))
        # ② 표본 길이를 단언하는 문장은 그 문서의 n_days 와 대조
        if not _nd:
            continue
        _yrs = _nd / 252.0
        for _m in _CLAIM.finditer(_s):
            if abs(float(_m.group(1)) - _yrs) > 1.0:
                errors.append("%s.%s: 표본 기간을 %s년이라 적었는데 실제는 %.1f년(n_days %d)이다 "
                              "— 문구에 연수를 박지 말고 n_days 에서 파생할 것"
                              % (_fn, _k, _m.group(1), _yrs, _nd))
                break

# ── 갱신 주기 라벨: 워크플로 cron이 단일 출처인가 ──────────────────────────
#   손으로 적던 시절 cron을 바꿔도 라벨이 안 따라와 전면적으로 어긋나 있었다(2026-07-25 실측:
#   SEC 공시 10:15↔실제 08:45, 13F 12:15↔09:25, 없어진 백업 크론 '08:35 + 09:10' 표기 등).
#   ① schedule.json이 현재 cron과 일치하는가 ② sources.html이 시각을 하드코딩하지 않는가.
try:
    sys.path.insert(0, os.path.join(ROOT, "build"))
    import schedule_index
    _fresh = schedule_index.build()
    _cur = json.load(io.open(os.path.join(ROOT, "data", "schedule.json"), encoding="utf-8"))
    if _cur != _fresh:
        errors.append("갱신 주기 라벨이 워크플로 cron과 어긋남 — python build/schedule_index.py 로 다시 구울 것")
    # 표·상세 카드에 시각을 다시 적어 넣으면 드리프트가 재발한다.
    #   ⚠ strip_js()에 HTML 전체를 넘기면 안 된다 — 속성 따옴표를 JS 문자열로 오인해 본문을
    #     통째로 지워, 검사가 아무것도 못 잡는다(음성 테스트로 확인). 주석만 걷어내고 본문은 남긴다.
    #     JS 문자열도 남겨야 화면에서 하드코딩하는 우회까지 잡힌다.
    _sh = re.sub(r"(?s)<!--.*?-->", "", rd("sources.html"))     # HTML 주석
    _sh = re.sub(r"(?m)^\s*//.*$", "", _sh)                      # 줄머리 JS 주석(URL의 // 는 보존)
    _sh = re.sub(r"(?s)/\*.*?\*/", "", _sh)                      # JS 블록 주석
    _hard = re.findall(r"(?:매일|매주|매월)[^<>\n]{0,14}\d{2}:\d{2}\s*KST", _sh)
    if _hard:
        errors.append(f"sources.html에 갱신 시각 하드코딩 {_hard[:3]} — data/schedule.json에서 읽을 것")
except SystemExit as e:
    errors.append(f"갱신 주기 라벨 생성 실패(워크플로 매핑 누락 등): {e}")
except Exception as e:
    errors.append(f"갱신 주기 라벨 검증 실패: {e}")

# ── 13F 평가액 눈금: 제출사마다 단위가 다르면 화면이 1000배 틀린다 ─────────
#   13F 정보표의 VALUE 는 2023년 규칙 변경 전까지 천 달러 단위였고, 지금도 그 눈금으로 내는
#   운용사가 있다. 정규화 없이 합산하면 운용사마다 단위가 1000배 다른 필드가 된다.
#   2026-07-31 실측: 17곳 중 2곳이 천$라 guru.html 에 "$5M"(실제 $5.1B) · 아마존 주당 $0.21 이
#   아무 배지 없이 나가고 있었다. 겹침 비율(%)은 스케일 불변이라 정상으로 보여 오래 안 들켰다.
#   생성기(build/refresh_13f.py)가 정규화하지만, 그 판정이 실패해도 화면은 조용하다 —
#   그래서 **결과물을 직접** 검사한다. 내재주가(평가액÷주식수)를 우리 가격 패널의 분기말 종가와
#   대조하면 맞는 눈금은 ~1, 틀린 눈금은 ~0.001 이라 오판 여지가 없다.
try:
    import statistics as _stat
    _g = json.load(io.open(os.path.join(ROOT, "data", "guru.json"), encoding="utf-8"))
    _s = json.load(io.open(os.path.join(ROOT, "data", "stocks.json"), encoding="utf-8"))
    _ds = _s.get("pxd_dates") or []
    _i = max((i for i, d in enumerate(_ds) if d <= (_g.get("as_of") or "")), default=None)
    if _i is None:
        errors.append("guru.json 기준일(%s)이 가격 패널 범위 밖 — 13F 눈금을 검사할 수 없다" % _g.get("as_of"))
    else:
        _cl = {}
        for _t in {h["t"] for m in _g.get("managers", []) for h in m.get("holds", []) if not h.get("off")}:
            try:
                _px = json.load(io.open(os.path.join(ROOT, "data", "sd", _t + ".json"), encoding="utf-8")).get("pxd") or []
                if _i < len(_px) and _px[_i]: _cl[_t] = float(_px[_i])
            except Exception:
                pass
        _off_scale, _nojudge = [], 0
        for _m in _g.get("managers", []):
            _r = [(h["v"] / h["sh"]) / _cl[h["t"]] for h in _m.get("holds", [])
                  if not h.get("off") and h.get("sh") and h.get("v") and _cl.get(h["t"])]
            if len(_r) < 3:
                _nojudge += 1
                continue
            _md = _stat.median(_r)
            if not (0.5 <= _md <= 2.0):
                _off_scale.append("%s(내재주가가 종가의 %.4f배 · %d종목)" % (_m.get("label"), _md, len(_r)))
        if _off_scale:
            errors.append("13F 평가액 눈금이 종가와 어긋남 — " + " · ".join(_off_scale[:4]) +
                          " (0.001배면 천$ 제출을 정규화하지 못한 것)")
        # 판정 가능한 운용사가 절반도 안 되면 검사가 무력화된 것이다 — 통과로 읽히면 안 된다.
        if _nojudge * 2 > len(_g.get("managers", []) or [1]):
            errors.append("13F 눈금 판정 가능한 운용사가 %d/%d뿐 — 가격 패널 대조가 무력하다"
                          % (len(_g.get("managers", [])) - _nojudge, len(_g.get("managers", []))))
except FileNotFoundError:
    pass
except Exception as e:
    errors.append(f"13F 평가액 눈금 검증 실패: {e}")

# ── 여러 잡이 공유하는 산출물은 재생성 표에 있어야 한다 ────────────────────
#   build/ci_push.sh는 리베이스 충돌을 만나면 REBAKE_TABLE에 있는 파일만 자동 해소하고,
#   없으면 abort 한다 — 그 잡의 그날치 산출물이 통째로 버려진다.
#   그래서 **둘 이상의 잡이 커밋하는 파일**은 표에 있거나, 여기 예외 목록에 사유와 함께 있어야 한다.
#   2026-07-31 실측으로 잡음: data/home_flow.json을 5개 잡(stocks·earnings·filings·insider·13f)이
#   커밋하는데 표에 없었다. 이 파일은 매 실행 generated 타임스탬프가 바뀌는 한 줄 JSON이라
#   두 잡의 실행 창이 겹치면 충돌이 **확정**이고, 늦게 민 쪽은 소급 불가 누적물
#   (target_history·fund_history)까지 함께 잃는다.
try:
    _wf_dir = os.path.join(ROOT, ".github", "workflows")

    # ①-w 🚨 2026-08-26 — **run 도 uses 도 없는 빈 step.** YAML 로는 멀쩡해서 파이썬
    #   파서도 통과하는데 GitHub 의 워크플로 스키마는 그것을 못 읽는다. 그러면 파일
    #   전체가 무효가 되어 **그 잡의 schedule 이 아예 발화하지 않는다.**
    #   실측: refresh-rates.yml 에 «- name: Validate» 만 있고 run 이 없어 08-22~08-26
    #   나흘간 금리·FedWatch 가 08-20 에 고착했다. 푸시마다 빨간불이 떴지만 문구가
    #   «workflow file issue» 뿐이라 자료 고착과 연결되지 않았고, 잡 로그도 비어 있었다.
    #   ⚠ 사람이 눈으로 못 잡는다 — 정상 step 과 한 글자 차이(다음 줄이 run 이냐 주석이냐)다.
    #   ⚠ PyYAML 을 쓰지 않는다. 이 잡은 «표준 라이브러리만 · 설치 단계 없음» 이 설계이고
    #     (validate.yml 의 step 이름에 그렇게 적혀 있다), 여기 한 줄 때문에 설치를 붙이면
    #     그 설계가 이 검사 하나에 끌려 무너진다. 필요한 것은 «steps: 아래 각 항목에
    #     run 이나 uses 가 있나» 뿐이라 줄 단위로 충분하다.
    for _fn in sorted(os.listdir(_wf_dir)):
        if not _fn.endswith((".yml", ".yaml")): continue
        _lines = io.open(os.path.join(_wf_dir, _fn), encoding="utf-8").read().splitlines()
        _steps_ind = None          # steps: 의 들여쓰기(None 이면 지금 steps 블록 밖)
        _item_ind = None           # 그 아래 «- » 항목의 들여쓰기
        _cur = None                # (이름, 줄번호, run/uses 봤나)
        def _close(_c, _f=_fn):
            if _c and not _c[2]:
                errors.append(
                    ".github/workflows/%s: %d번째 줄 step «%s» 에 run 도 uses 도 없다 — "
                    "GitHub 이 파일을 못 읽어 이 잡의 schedule 이 통째로 안 돈다"
                    "(자료가 조용히 고착한다)" % (_f, _c[1], _c[0]))
        for _ln, _raw in enumerate(_lines, 1):
            if not _raw.strip() or _raw.lstrip().startswith("#"):
                continue
            _ind = len(_raw) - len(_raw.lstrip())
            if _steps_ind is None:
                if re.match(r"^\s*steps:\s*(#.*)?$", _raw):
                    _steps_ind, _item_ind, _cur = _ind, None, None
                continue
            # steps 블록을 벗어났나 — 같거나 얕은 들여쓰기의 키가 나오면 끝이다.
            if _ind <= _steps_ind:
                _close(_cur); _cur = None
                _steps_ind = _item_ind = None
                if re.match(r"^\s*steps:\s*(#.*)?$", _raw):
                    _steps_ind, _item_ind = _ind, None
                continue
            _body = _raw.lstrip()
            if _body.startswith("- "):
                if _item_ind is None:
                    _item_ind = _ind
                if _ind == _item_ind:
                    _close(_cur)
                    _in = _body[2:]
                    _nm = re.match(r"name:\s*(.+?)\s*$", _in)
                    _cur = [(_nm.group(1) if _nm else _in[:40]), _ln,
                            bool(re.match(r"(run|uses):", _in))]
                    continue
            if _cur and re.match(r"^(run|uses):", _body):
                _cur[2] = True
        _close(_cur)

    _staged = {}
    for _fn in sorted(os.listdir(_wf_dir)):
        if not _fn.endswith(".yml"): continue
        _s = io.open(os.path.join(_wf_dir, _fn), encoding="utf-8").read()
        # ci_push.sh 호출부만 본다(주석의 경로가 섞이지 않게 호출 줄부터 빈 줄 전까지).
        for _m in re.finditer(r"ci_push\.sh[^\n]*\n(?:\s+[^\n]*\n)*", _s):
            _blk = _m.group(0)
            _blk = re.sub(r"(?m)^\s*#.*$", "", _blk)
            for _p in set(re.findall(r"data/[A-Za-z0-9_/.]+", _blk)):
                _staged.setdefault(_p, set()).add(_fn)
    _tbl = io.open(os.path.join(ROOT, "build", "ci_push.sh"), encoding="utf-8").read()
    # 수집물이라 다시 못 굽는 것들. 충돌하면 사람이 봐야 하므로 표에 넣으면 안 된다.
    #   (한 잡만 커밋하므로 애초에 잡끼리 충돌하지 않는다 — 사람과 겹칠 때만 abort 한다.)
    _rebake_exempt = set()
    for _p, _jobs in sorted(_staged.items()):
        if len(_jobs) < 2 or _p in _rebake_exempt: continue
        if (_p + "|") not in _tbl:
            errors.append(
                f"{_p}을(를) {len(_jobs)}개 잡이 커밋하는데 ci_push.sh의 REBAKE_TABLE에 없음"
                f"({', '.join(sorted(_jobs))}) — 충돌 시 그날치 산출물이 통째로 버려진다")
    # 반대 방향: 표에 있는데 아무 잡도 안 넘기는 줄은 사문이다(조용히 썩는다).
    for _line in _tbl.splitlines():
        if _line.startswith("data/") and "|" in _line:
            _p = _line.split("|", 1)[0]
            if _p not in _staged:
                errors.append(f"REBAKE_TABLE의 {_p}을(를) 커밋하는 잡이 없음 — 사문이거나 워크플로에서 빠졌다")
    # ── 데이터를 커밋하는 잡은 커밋 전에 스스로 검증해야 한다 ────────────────
    # 🚨 GitHub Actions 는 GITHUB_TOKEN 으로 민 푸시에 워크플로를 **재귀 실행하지 않는다**.
    #   그래서 봇의 데이터 커밋에는 이 CI(validate.yml)가 아예 안 돈다 — paths 에 data/** 가
    #   있어도 마찬가지다(2026-07-31 실측: 봇 커밋 뒤 validate 런이 하나도 안 생긴다).
    #   즉 데이터의 실제 관문은 CI 가 아니라 **각 잡 안의 Validate 단계**다. 그게 빠진 잡이
    #   생기면 그 축은 아무 검증 없이 배포된다 — 그리고 그 사실이 어디에도 안 드러난다.
    for _fn in sorted(os.listdir(_wf_dir)):
        if not _fn.endswith(".yml"): continue
        _s = io.open(os.path.join(_wf_dir, _fn), encoding="utf-8").read()
        # 🚨 2026-08-05 — 종전에는 파일 전문에 substring 검사를 했다. 그래서 주석 한 줄에
        #   'validate_site.py' 가 있으면 실제 단계가 없어도 통과했다 — refresh-stocks.yml 이
        #   정확히 그 상태였다. 검사가 막으려던 것을 검사가 통과시켰다. 주석을 걷어낸 뒤 본다.
        _live = chr(10).join(_ln.split("#", 1)[0] for _ln in _s.split(chr(10)))
        # 🚨 2026-08-05 — 잡들이 validate_site.py 를 직접 부르지 않고 validate_gate.py 를
        #   거치게 바뀌었다(절대 기준 → 회귀 기준). 관문은 안에서 validate_site.py 를
        #   그대로 돌린다. 둘 다 인정하지 않으면 이 검사가 정상 전환을 고장으로 읽는다.
        _has_val = ("validate_site.py" in _live) or ("validate_gate.py" in _live)
        # 관문의 check 만 있고 baseline 이 없으면 기준선 파일이 없어 절대 기준으로
        # 퇴화한다 — 이름만 관문이고 하는 일은 전과 같아진다. 짝을 강제한다.
        if "validate_gate.py check" in _live and "validate_gate.py baseline" not in _live:
            errors.append(f".github/workflows/{_fn}: validate_gate check 만 있고 baseline 단계가 없음 "
                          "— 기준선이 없으면 관문이 절대 기준으로 퇴화해서, 이 잡과 무관한 "
                          "결함에 방금 받은 자료를 버린다(그걸 막으려고 만든 관문이다)")
        if "ci_push.sh" in _live and not _has_val:
            errors.append(f".github/workflows/{_fn}: 데이터를 커밋하는데 validate_site.py 단계가 없음 "
                          f"— 봇 커밋에는 CI 가 안 도므로 이 잡의 산출물은 아무도 검증하지 않는다")
except Exception as e:
    errors.append(f"재생성 표 검증 실패: {e}")

# ── 성장률 눈금 규약: 같은 키 이름이 파일마다 100배 다르면 화면이 뒤집힌다 ──
#   data/stocks.json 의 fund.rg 는 _x100 을 거쳐 **백분율**(중앙 9.1)인데, data/estimates.json 의
#   rg 는 정보원 원값 그대로 **분수**(중앙 0.056)였다. screener.html 이 그 분수를 '배' 단위로 그려
#   AVGO 0.629 를 "0.629배"(= −37% 축소)로 찍고 있었다 — 실제로는 +62.9% 성장이고,
#   rg 상위 10 중 8행이 그렇게 방향이 뒤집혀 있었다. '성장률 상위' 표 아래에서.
#   두 파일의 값 크기를 직접 대조한다. 눈금이 같으면 O(1), 다르면 100배가 벌어진다.
try:
    import statistics as _st2
    _sj = json.load(io.open(os.path.join(ROOT, "data", "stocks.json"), encoding="utf-8"))
    _ej = json.load(io.open(os.path.join(ROOT, "data", "estimates.json"), encoding="utf-8"))
    _sv = [abs(s["fund"]["rg"]) for s in _sj.get("stocks", [])
           if isinstance((s.get("fund") or {}).get("rg"), (int, float))]
    _ev = [abs(r["rg"]) for r in (_ej.get("rows") or {}).values()
           if isinstance(r.get("rg"), (int, float))]
    if len(_sv) > 50 and len(_ev) > 50:
        _ms, _me = _st2.median(_sv), _st2.median(_ev)
        if _ms > 0 and _me / _ms < 0.1:
            errors.append("성장률 눈금 불일치 — stocks.json fund.rg 중앙 %.3f(백분율) vs "
                          "estimates.json rg 중앙 %.3f(분수). 같은 키 이름이 100배 다른 눈금이다"
                          % (_ms, _me))
except FileNotFoundError:
    pass
except Exception as e:
    errors.append(f"성장률 눈금 검증 실패: {e}")

# ── 기각 아카이브 분류(k) 무결성 ─────────────────────────────────────────
#   45종을 한 칸에 세면 '좋은 전략 45개가 기각됐다'로 읽힌다. k로 갈라 세되,
#   ① 모든 항목에 유효한 k가 있고 ② kinds에 뜻이 적혀 있고 ③ 합이 총계와 맞아야 한다.
#   (분류를 붙이다 만 상태로 배포되면 건수가 조용히 틀린다)
try:
    _aj = json.load(io.open(os.path.join(ROOT, "data", "archive_index.json"), encoding="utf-8"))
    _ai2, _kinds = _aj.get("items") or [], _aj.get("kinds") or {}
    _OK = {"reject", "undetermined", "variant", "undecidable"}
    if set(_kinds) != _OK:
        errors.append(f"archive_index.kinds 누락/과잉: {sorted(set(_kinds) ^ _OK)}")
    _bad = [x.get("sid") for x in _ai2 if (x.get("k") or "reject") not in _OK]
    if _bad:
        errors.append(f"archive_index: 알 수 없는 k 값 {_bad[:5]}")
    # variant/undecidable 은 왜 그렇게 분류했는지(kw)를 반드시 남긴다 — 근거 없는 재분류 방지
    _nokw = [x.get("sid") for x in _ai2 if x.get("k") in ("undetermined", "variant", "undecidable") and not x.get("kw")]
    if _nokw:
        errors.append(f"archive_index: k가 reject가 아닌데 사유(kw) 없음 {_nokw[:5]}")
    # 분류 기준은 '스탠드얼론 렌즈가 정의되는가'다. 스탠드얼론 재검 백테스트를 가진 항목을
    #   '전략이 아니다'로 분류하면 자기모순 — 실제로 low-beta-weight-tilt에서 한 번 틀렸다.
    _abk = set((json.load(io.open(os.path.join(ROOT, "data", "archive_backtests.json"),
                                  encoding="utf-8")).get("strategies") or {}))
    _contra = sorted(_abk & {x.get("sid") for x in _ai2 if x.get("k") in ("variant", "undecidable")})
    if _contra:
        errors.append(f"archive_index: 스탠드얼론 재검이 있는데 전략이 아니라고 분류함 {_contra}")
    _v = json.load(io.open(os.path.join(ROOT, "data", "verdicts.json"), encoding="utf-8"))
    _sum = (_v.get("archive_reject_n", 0) + _v.get("archive_undetermined_n", 0)
            + _v.get("archive_variant_n", 0) + _v.get("archive_undecidable_n", 0))
    if _sum != _v.get("archive_n"):
        errors.append(f"verdicts: 아카이브 분류 합 {_sum} ≠ 총계 {_v.get('archive_n')} — verdicts_gen 재실행 필요")
except Exception as e:
    errors.append(f"아카이브 분류 검증 실패: {e}")

# ── 캘린더 이벤트 정본(data/events.json) ───────────────────────────────────
#   FOMC 일정은 손으로 적는 유일한 캘린더 재료다(FRED가 주지 않는다). 연준이 다음 해를
#   공표하면 build/refresh_events.py에 덧붙여야 하는데, 안 하면 어느 날 조용히 바닥난다 —
#   화면엔 '이벤트 없음'으로만 보여서 눈치채기 어렵다. 그래서 기계가 대신 세어 준다.
try:
    _ev = json.load(io.open(os.path.join(ROOT, "data", "events.json"), encoding="utf-8"))
    _fo = [x.get("d") for x in (_ev.get("fomc") or []) if x.get("d")]
    _st = (_ev.get("stars") or {})
    if not _fo:
        errors.append("events.json: fomc 비어 있음 — build/refresh_events.py 실행 필요")
    if not _st.get("by_rid") or not _st.get("by_name"):
        errors.append("events.json: stars.by_rid/by_name 누락 — 세 화면의 ★가 사라진다")
    if _fo:
        _today = _dt.date.today().isoformat()
        _fut = [d for d in _fo if d >= _today]
        if not _fut:
            errors.append(f"events.json: 남은 FOMC 일정 0건(마지막 {max(_fo)}) — "
                          f"연준 공표 일정을 build/refresh_events.py에 추가할 것")
        elif max(_fo) < (_dt.date.today() + _dt.timedelta(days=182)).isoformat():
            print(f"  ~ events.json: FOMC 일정이 {max(_fo)}까지밖에 없다(6개월 미만) — "
                  f"다음 해 공표분을 refresh_events.py에 미리 추가할 것")
except FileNotFoundError:
    errors.append("data/events.json 없음 — build/refresh_events.py 를 실행해 생성할 것")
except Exception as e:
    errors.append(f"events.json 검증 실패: {e}")

# ── 홈 스타일 표: 랩 행 ↔ ETF 행 짝짓기(2026-07-29) ────────────────────────
#   홈은 ETF 수익률(market_board.json) 옆에 이 랩의 스타일 백테스트(style_trails.json)를
#   나란히 그린다. 두 정본이 세 군데서 조용히 어긋날 수 있어 기계가 대신 본다.
#     ① 구간 라벨 — 홈은 1W/1M/… 로 묻고 랩은 '1주'/'1개월'/… 로 답한다. 어느 한쪽 이름이
#        바뀌면 그 칸만 —(빈칸)이 되고 표는 멀쩡해 보인다. ST_TR 매핑을 실제 데이터에 대본다.
#     ② 짝 — index.html 의 ST_KEY(티커→홈키)∘ST_PERF(홈키→백테스트키) 합성이 실제 키에
#        닿는지. 닿지 않으면 그 스타일의 랩 행이 통째로 사라진다(에러 없음).
#     ③ 기준일 — style_trails 와 market_board 는 서로 다른 입력에서 날짜를 얻는다
#        (stocks.json 매일 · assets.json 주 1회). 크게 벌어지면 한 표가 두 날짜를 말한다.
try:
    _ih = rd("index.html")

    def _obj(name):
        """index.html 의 `var NAME={a:'b',…};` 를 dict 로. 값이 전부 문자열인 매핑 전용."""
        m = re.search(r"var %s\s*=\s*\{(.*?)\}\s*;" % name, _ih, re.S)
        if not m:
            raise ValueError("index.html 에서 %s 를 찾지 못했다" % name)
        return dict(re.findall(r"""['"]?([\w]+)['"]?\s*:\s*['"]([^'"]*)['"]""", m.group(1)))
    _tr_map, _k_map, _p_map = _obj("ST_TR"), _obj("ST_KEY"), _obj("ST_PERF")
    _sl = json.load(io.open(os.path.join(ROOT, "data", "style_trails.json"), encoding="utf-8"))
    _mb = json.load(io.open(os.path.join(ROOT, "data", "market_board.json"), encoding="utf-8"))
    _by = {s["key"]: s for s in (_sl.get("styles") or [])}
    if not _by:
        errors.append("style_trails.json: styles 비어 있음 — build/style_top_pdf.py --json 실행 필요")
    # ① 구간 라벨
    for _s in _by.values():
        # 3년·5년은 1년 창 산출물에 있을 수 없어 **별 키(trails5)** 로 온다(2026-08-12).
        # 두 지도를 합쳐서 본다 — 합치지 않으면 정상 배선을 '어긋났다'고 오진한다.
        _tv = dict(_s.get("trails") or {})
        _tv.update(_s.get("trails5") or {})
        _miss = [v for v in _tr_map.values() if v not in _tv]
        if _miss:
            errors.append(f"style_trails: {_s['key']} 에 구간 {_miss} 없음 — index.html ST_TR 와 "
                          f"build/style_top_pdf.py TRAIL 이 어긋났다(그 칸이 조용히 빈다)")
            break
    # ② 짝 — **양방향 도달성**으로 본다. '짝이 N종이어야 한다'고 손으로 적으면 그 숫자가
    #    다음번에 낡는다. 대신 두 방향을 각각 묻는다: 홈이 가리키는 키가 자료에 있는가,
    #    자료에 있는 스타일이 홈에 닿는가. 어느 쪽이 끊겨도 그 랩 행은 에러 없이 사라진다.
    # 짝 ETF 가 없어 표에 못 들어가는 지수들(index.html 의 ST_IDX)도 화면에 나오는 것이므로
    # 도달 가능으로 친다 — 없으면 그 넷이 통째로 '고아'로 잡힌다(2026-08-02).
    _m_idx = re.search(r"var ST_IDX\s*=\s*\[(.*?)\]\s*;", _ih, re.S)
    _idx_extra = set(re.findall(r"['\"]([\w]+)['\"]", _m_idx.group(1))) if _m_idx else set()
    _want = {_p_map[_k_map[t]] for t in _k_map if _k_map[t] in _p_map}
    _want |= {_p_map[k] for k in _idx_extra if k in _p_map}
    # 🚨 2026-08-05 — '못 쟀다'고 명시한 스타일은 매달린 것이 아니다. style_trails 의
    #   skipped 에 사유와 함께 실려 있으면 화면이 '자료 없음'을 말할 수 있다. 그것까지
    #   오류로 올리면 "입력이 없으니 정직하게 비웠다"를 고칠 수 없는 실패로 만든다.
    #   ⚠ 다만 **조용히 사라지는 것**은 그대로 잡는다 — 둘의 차이가 이 검사의 전부다.
    _skipped = set((_sl.get("skipped") or {}).keys())
    _dangle = sorted(_want - set(_by) - _skipped)
    _orphan = sorted(set(_by) - _want)
    if _dangle:
        errors.append(f"홈 스타일 표: index.html 이 가리키는 랩 키 {_dangle} 가 style_trails 에 없다 "
                      f"— 그 스타일의 랩 행이 조용히 사라진다")
    if _orphan:
        errors.append(f"홈 스타일 표: 랩 스타일 {_orphan} 를 가리키는 ETF 가 없다 — 잰 것이 "
                      f"화면에 안 나온다(index.html ST_KEY·ST_PERF 확인)")
    # ③ 기준일
    _d1, _d2 = _sl.get("as_of") or "", _mb.get("as_of") or ""
    if _d1 and _d2 and _d1 != _d2:
        _gap = abs((_dt.date.fromisoformat(_d1) - _dt.date.fromisoformat(_d2)).days)
        if _gap > 14:
            errors.append(f"홈 스타일 표: 랩 기준일 {_d1} 과 ETF 기준일 {_d2} 이 {_gap}일 벌어졌다 — "
                          f"style_top_pdf.py --json 이 갱신 잡에서 밀렸다")
        else:
            print(f"  ~ 홈 스타일 표: 랩 {_d1} · ETF {_d2}({_gap}일 차) — 부제에 함께 표시된다")
    # ④ 유니버스 편향 실측치의 신선도 — style_pit.json 은 사내망 PC 에서만 만들 수 있고
    #    (입력이 gitignore) 화면 각주가 그 수치를 인용한다. 배포 수치는 매주 갱신되므로
    #    오래 두면 각주가 옛 창의 편향을 현재 수치인 척 말한다. 자동화가 불가능한 파일이라
    #    실패가 아니라 경고로 낸다 — 대신 조용히는 두지 않는다.
    _sp = os.path.join(ROOT, "data", "style_pit.json")
    if not os.path.exists(_sp):
        print("  ~ data/style_pit.json 없음 — 화면 각주가 수치 없는 정성 문구로 나간다"
              "(사내망 PC 에서 build/style_pit.py 실행)")
    else:
        _pj = json.load(io.open(_sp, encoding="utf-8"))
        _pd = _pj.get("as_of") or ""
        if _pd and _d1 and _pd != _d1:
            _g2 = abs((_dt.date.fromisoformat(_pd) - _dt.date.fromisoformat(_d1)).days)
            if _g2 > 45:
                print(f"  ~ 유니버스 편향 실측이 {_pd} 로 랩 기준일 {_d1} 보다 {_g2}일 낡았다 — "
                      f"build/style_pit.py 를 다시 돌릴 것(각주가 옛 창의 수치를 인용한다)")
except FileNotFoundError as e:
    errors.append(f"홈 스타일 표 검증: 파일 없음 {e} — build/style_top_pdf.py --json 실행 필요")
except Exception as e:
    errors.append(f"홈 스타일 표 검증 실패: {e}")

# ── head 메타: 공유 링크가 남의 페이지를 말하지 않게 ────────────────────────
# 실사고(2026-08-02 발견): style.html 의 og:title·og:description·twitter:* 4줄이 통째로
# sources.html 것이었다. <title>·canonical 은 옳아서 화면·검색에서는 멀쩡했고, 카톡·슬랙에
# 링크를 붙였을 때만 '데이터 출처·기준일'로 떴다 — 아무 검사도 이 파일의 head 를 보지 않았다.
# 새 페이지는 기존 페이지를 복사해 만들므로 이 사고는 구조적으로 반복된다.
#
# 규칙은 '<title> 과 닮았는가'가 아니라 '**다른 페이지 것과 똑같은가**'로 잡는다.
#   · 닮음 검사는 오탐이 난다 — explorer(「여두 · 전략 랩」/「여두 전략 리스트」)와
#     stocks(「여두 · 종목 신호」/「여두 종목 시그널」)는 일부러 다르게 적은 것이고,
#     index 는 브랜드 낱말만으로 이뤄져 있어 낱말 비교 자체가 성립하지 않는다.
#   · 복붙 사고의 지문은 '완전 일치'다. 사람이 일부러 두 페이지에 같은 제목·설명을 다는 일은
#     없으므로 오탐이 0이고, style.html 사고는 이 규칙 하나에 정확히 걸린다.
# twitter:* 는 og:* 의 사본이어야 한다 — 한쪽만 고치고 다른 쪽을 잊는 것이 이 사고의 후속판이다.
_own, _seen_t, _seen_d, _seen_td = {}, {}, {}, {}
_heads = []
for _p in PAGES:
    _s = rd(_p)
    _h = _s[:_s.find("</head>")] if "</head>" in _s else _s[:4000]
    # 색인에서 뺀 페이지(kb 같은 잠금 게이트)는 공유 카드가 필요 없다 — 면제 근거를 페이지가 스스로 밝힌다.
    if re.search(r'name="robots"[^>]*content="[^"]*noindex', _h): continue
    _heads.append((_p, _h))

def _hm(h, pat):
    mm = re.search(pat, h)
    return mm.group(1).strip() if mm else None

for _p, _h in _heads:                       # 1차 — 각 페이지의 <title> 을 먼저 모은다
    _own[_p] = _hm(_h, r"<title>([^<]*)</title>")
for _p, _h in _heads:
    _ti, _ot = _own[_p], _hm(_h, r'og:title"\s+content="([^"]*)"')
    _od = _hm(_h, r'og:description"\s+content="([^"]*)"')
    _tt = _hm(_h, r'twitter:title"\s+content="([^"]*)"')
    _td = _hm(_h, r'twitter:description"\s+content="([^"]*)"')
    _ou, _cn = _hm(_h, r'og:url"\s+content="([^"]*)"'), _hm(_h, r'rel="canonical"\s+href="([^"]*)"')
    if not _ti: errors.append(f"{_p}: <title> 없음"); continue
    if not _ot or not _od:
        errors.append(f"{_p}: og:title/og:description 없음 — 공유하면 제목·설명이 빈다"); continue
    # ① og:title 이 **남의 <title>** 과 같다 = 그 페이지에서 복사해 왔다는 뜻
    _steal = next((q for q, t in _own.items() if q != _p and t and t == _ot), None)
    if _steal:
        errors.append(f"{_p}: og:title「{_ot}」이 {_steal} 의 <title> 과 같다 — 복붙 사고")
    for _lbl, _v, _bag in (("og:title", _ot, _seen_t), ("og:description", _od, _seen_d)):
        if _v in _bag:
            errors.append(f"{_p}: {_lbl} 이 {_bag[_v]} 것과 완전히 같다 — 복붙 사고")
        else:
            _bag[_v] = _p
    # ② twitter:title 은 og:title 의 사본 — 한쪽만 고치면 공유 경로마다 다른 제목이 뜬다.
    #    ⚠ description 은 같은 규칙을 걸면 안 된다. 7장이 트위터용으로 **일부러 짧게** 적어
    #      두었다(예: roadmap「…칸과 그 사유 — 칸은 지우되 사유는 지우지 않습니다」→「…칸과 그 사유.」).
    #      그건 사고가 아니라 편집이다. 그래서 설명은 동일성이 아니라 중복만 본다.
    if _tt and _tt != _ot:
        errors.append(f"{_p}: twitter:title 이 og:title 과 다르다 —「{_tt}」/「{_ot}」")
    if _td:
        if _td in _seen_td:
            errors.append(f"{_p}: twitter:description 이 {_seen_td[_td]} 것과 완전히 같다 — 복붙 사고")
        else:
            _seen_td[_td] = _p
    # ③ 자기 자신을 가리키는가
    for _k, _v in (("og:url", _ou), ("canonical", _cn)):
        if _v and not _v.endswith("/" + _p):
            errors.append(f"{_p}: {_k} 가 자기 파일({_p})을 가리키지 않는다 — {_v}")

# ── 홈 렌더 조립 검사 ─────────────────────────────────────────────────
#   홈의 표·카드는 자료가 여러 파일에서 **따로 도착**하고, 그 조립이 어긋나면 화면이
#   조용히 비어서 나간다. 문법 검사로는 안 잡힌다 — 실제로 두 번 그렇게 배포됐다
#   (섹터 묶음 0줄 · 종목 두 줄씩). build/test_home_render.js 가 브라우저 없이
#   렌더러를 실제 data/*.json 에 물려 그 조립만 재현한다.
#   ⚠ node 가 없으면 건너뛴다(이 저장소의 다른 node 검사와 같은 규칙) — 못 잡는 것보다
#     거짓 통과를 만드는 것이 나쁘지만, 도구 부재로 일일 잡을 죽이는 것은 더 나쁘다.
_hr = os.path.join(ROOT, "build", "test_home_render.js")
if not NODE:
    tool_skips.append("홈 렌더 조립 검사(node 없음)")
elif not os.path.exists(_hr):
    tool_skips.append("홈 렌더 조립 검사(스크립트 없음)")
else:
    try:
        # ⚠ encoding 을 고정한다 — 이 검사는 한글로 찍는다. 윈도우 로케일(cp949)로 읽으면
        #   읽기 스레드가 UnicodeDecodeError 로 죽고, 그 예외가 아래 except 로 떨어져
        #   **검사가 조용히 tool_skips 로 간다.** 화면에는 '통과 ✅' 만 남아 안 돈 것을
        #   알 길이 없다(2026-08-03 실측 — 위 sync_nav·node --check 와 같은 사유다).
        _r = _sp0.run([NODE, _hr], cwd=ROOT, capture_output=True, text=True,
                      encoding="utf-8", timeout=180)
        if _r.returncode != 0:
            _tail = [x for x in (_r.stdout + _r.stderr).strip().split("\n") if x.strip()][-6:]
            errors.append("홈 렌더 조립 검사 실패 — " + " / ".join(_tail))
        else:
            print("  ~ 홈 렌더 조립 검사 통과(" +
                  next((x for x in _r.stdout.split("\n") if "표:" in x), "").strip() + ")")
    except Exception as _e:
        tool_skips.append(f"홈 렌더 조립 검사({_e})")

# ── explorer 지수 비교표 검사 ──────────────────────────────────────────
#   같은 이유다. 여기서 조용히 깨진 것 둘 — 이름 조인이 끊겨 배포 원장 4종이 지수 눈금을
#   통째로 못 받았고(목록 쪽 이름은 'SPX'→'S&P 500' 을 편 뒤인데 키는 원문이었다),
#   지수를 전략과 다른 주기로 재 같은 SPX 가 한 화면에서 두 값으로 나왔다.
_xr = os.path.join(ROOT, "build", "test_explorer_render.js")
if not NODE:
    tool_skips.append("explorer 렌더 검사(node 없음)")
elif not os.path.exists(_xr):
    tool_skips.append("explorer 렌더 검사(스크립트 없음)")
else:
    try:
        _r = _sp0.run([NODE, _xr], cwd=ROOT, capture_output=True, text=True,
                      encoding="utf-8", timeout=180)   # 바로 위 홈 렌더 검사와 같은 사유
        if _r.returncode != 0:
            _tail = [x for x in (_r.stdout + _r.stderr).strip().split("\n") if x.strip()][-6:]
            errors.append("explorer 렌더 검사 실패 — " + " / ".join(_tail))
        else:
            print("  ~ explorer 렌더 검사 통과(" +
                  next((x for x in _r.stdout.split("\n") if "비교표:" in x), "").strip() + ")")
    except Exception as _e:
        tool_skips.append(f"explorer 렌더 검사({_e})")

# ── 종목 페이지 조립 검사 ──────────────────────────────────────────────
# 🚨 2026-08-05 — 종목 페이지에는 조립 검사가 **아예 없었다.** 그래서 프리셋을 걷어내며
#   선언(pfch)만 지우고 참조를 남긴 것이 ReferenceError → 칩 렌더 전체 중단 → 필터 패널이
#   통째로 사라지는 사고가 됐는데, validate_site 도 홈·explorer 검사도 전부 통과했다.
#   문법도 마크업도 멀쩡했기 때문이다 — **돌려 봐야 잡히는 종류**다.
_sr = os.path.join(ROOT, "build", "test_stocks_render.js")
if not NODE:
    tool_skips.append("종목 렌더 검사(node 없음)")
elif not os.path.exists(_sr):
    tool_skips.append("종목 렌더 검사(스크립트 없음)")
else:
    try:
        _r = _sp0.run([NODE, _sr], cwd=ROOT, capture_output=True, text=True,
                      encoding="utf-8", timeout=180)
        if _r.returncode != 0:
            _tail = [x for x in (_r.stdout + _r.stderr).strip().split(chr(10)) if x.strip()][-6:]
            errors.append("종목 렌더 검사 실패 — " + " / ".join(_tail))
        else:
            print("  ~ " + next((x for x in _r.stdout.split(chr(10)) if "종목 렌더" in x), "").strip())
    except Exception as _e:
        tool_skips.append(f"종목 렌더 검사({_e})")


# ── 복제 리포트 조립 검사 ──────────────────────────────────────────────
# 🚨 report.html 은 **fetch 한 번에 화면 전체가 달려 있다** — 통계줄·필터·목차·리포트
#   117편·랩 한계가 전부 같은 .then 안에서 그려진다. 거기서 예외가 나면 unhandled
#   rejection 이 되어 조용히 빈 화면이 나간다(종목 페이지가 정확히 그렇게 죽었다).
#   문법도 마크업도 멀쩡하므로 **돌려 봐야 잡힌다.**
#   이 검사는 두 가지를 더 지킨다: ① '못 잰 것' 상자가 사라지지 않았는가(빈칸을 지우면
#   그 항목을 통과한 것처럼 읽힌다) ② esc() 필드로 마크다운 별표가 새지 않았는가.
_rr = os.path.join(ROOT, "build", "test_report_render.js")
if not NODE:
    tool_skips.append("리포트 렌더 검사(node 없음)")
elif not os.path.exists(_rr):
    tool_skips.append("리포트 렌더 검사(스크립트 없음)")
else:
    try:
        _r = _sp0.run([NODE, _rr], cwd=ROOT, capture_output=True, text=True,
                      encoding="utf-8", timeout=180)
        if _r.returncode != 0:
            _tail = [x for x in (_r.stdout + _r.stderr).strip().split(chr(10)) if x.strip()][-6:]
            errors.append("리포트 렌더 검사 실패 — " + " / ".join(_tail))
        else:
            print("  ~ " + next((x for x in _r.stdout.split(chr(10)) if "리포트 렌더" in x), "").strip())
    except Exception as _e:
        tool_skips.append(f"리포트 렌더 검사({_e})")


# ── 복제 리포트가 랩과 같은 날을 말하는가 ──────────────────────────────
# 🚨 report.html 은 랩 세 파일에서 값을 **옮긴** 것이다. 랩만 갱신되고 리포트가 안 굽히면
#   같은 사이트의 두 화면이 다른 날짜·다른 t 를 말하게 된다 — 이 저장소가 여러 번 당한
#   '채점기가 두 벌' 이다. 기준일이 어긋나면 여기서 막는다(build/strategy_report.py 재실행).
# ── 세 번째 목록 대조: '이미 판 자리'를 빈 칸으로 세지 않게 한다 ────────────
# 🚨 2026-08-08 — 이 가드가 생긴 사고. 이 랩의 '이미 해 봤다' 기록이 세 곳에 흩어져 있고
#   **둘만 기계가 읽었다**: 살아 있는 것·퇴출한 것은 JSON 인데, 돌렸지만 게시 안 한 13종은
#   build/PREREG-*.md 산문에만 있었다. 그래서 JKP 빈 칸을 세면서 이미 돌려 기각한 셋
#   (x-illiq t 5.31 · x-noa t 3.02 · x-fscore 측정 불가)을 '한 번도 검정한 적 없는 칸'이라
#   적고 신규로 등록했다. 코드에 우연히 남아 있던 x-illiq 주석을 보고서야 알았다.
#   사람이 조심해서 될 일이 아니라 목록이 한 곳에 없어서 나는 일이다.
#
# 규칙: 세 번째 목록의 sid 를 다시 살려 등록하려면 **readmitted 를 채워야 한다.**
#   무엇을 바꿨는지(changed)와 그것이 결과가 아니라 자료·정의 때문임(why_ok)을 적고
#   새 사전등록 문서를 가리켜야 한다. 안 적으면 여기서 막는다 — 같은 규칙을 문턱만
#   바뀐 채 다시 돌리는 것과, 자료가 달라져 재현이 가능해진 것을 구별하기 위해서다.
_n_err0 = len(errors)          # 🚨 이 블록이 낸 오류만 센다 — 아래 '통과' 줄의 조건이다
try:
    _tn = json.load(io.open(os.path.join(ROOT, "build", "tested_not_published.json"),
                            encoding="utf-8"))
    _tech3 = json.load(io.open(os.path.join(ROOT, "data", "tech_strategies.json"),
                               encoding="utf-8"))
    _tested = {x["sid"]: x for x in (_tn.get("items") or [])}
    _live3 = {r["sid"]: r for r in (_tech3.get("strategies") or [])}
    _retd3 = {r["sid"] for r in (_tech3.get("retired") or [])}

    # ①-b 🚨 2026-08-12 — **sid 만 대조하면 이름을 바꾼 재등록을 못 잡는다.**
    #   실제로 그날 `x-illiq`(Amihud ILLIQ · 2026-08-04 자료 타당성 기각)을 `x-amihud` 라는
    #   새 이름으로 다시 등록했고, 이 검사는 sid 가 다르다는 이유로 통과시켰다. 소급 t 6.84 로
    #   게시 직전까지 갔다가 보유 종목(BF.B·FOX·NWS)이 기각 사유가 지목한 13종과 겹치는 것을
    #   손으로 보고서야 알았다 — 사람이 조심해서 될 일이 아니라는 이 파일의 전제 그대로다.
    #   → **arch(규칙의 계보)로도 대조한다.** 같은 arch 면 이름이 달라도 같은 규칙 계열이다.
    _arch_shelf = {}
    for _x in (_tn.get("items") or []):
        if _x.get("arch"):
            _arch_shelf.setdefault(_x["arch"], []).append(_x["sid"])
    for _r in (_tech3.get("strategies") or []):
        _a = _r.get("arch")
        if not _a or _a not in _arch_shelf or _r["sid"] in _tested:
            continue
        errors.append(
            "'%s'(%s)는 선반의 %s 와 **같은 계보(arch=%s)** 인데 새 sid 로 살아 있다 — "
            "이름을 바꾼 재등록은 재등록이 아니다. tested_not_published.json 의 그 항목에 "
            "readmitted{prereg,changed,why_ok} 를 적거나, 이 규칙을 선반으로 옮길 것"
            % (_r.get("name"), _r["sid"], "·".join(_arch_shelf[_a]), _a))

    # ① 살아 있는 규칙이 세 번째 목록에 있으면 readmitted 가 있어야 한다
    for _sid in sorted(set(_tested) & set(_live3)):
        _rm = _tested[_sid].get("readmitted") or {}
        if not (_rm.get("prereg") and _rm.get("changed") and _rm.get("why_ok")):
            errors.append(
                "'%s'(%s)는 %s 에 이미 돌려 게시하지 않은 규칙인데 다시 살아 있다 — "
                "build/tested_not_published.json 의 readmitted 에 prereg·changed·why_ok 를 "
                "적을 것(같은 규칙을 문턱만 바뀐 채 다시 돌리는 것과 구별해야 한다)"
                % (_live3[_sid].get("name"), _sid, _tested[_sid].get("when")))

    # ② 세 목록에 같은 sid 가 둘 이상 나오면 어느 것이 정본인지 알 수 없다
    for _sid in sorted(set(_tested) & _retd3):
        errors.append("'%s'가 퇴출 목록과 세 번째 목록에 **둘 다** 있다 — 한쪽으로 정할 것" % _sid)

    # ③ arch 충돌 — 같은 아키타입을 다른 sid 로 다시 등록하면 '이전 판정' 줄이 갈린다
    _arch_t = {x.get("arch"): x["sid"] for x in _tested.values() if x.get("arch")}
    for _r in (_tech3.get("strategies") or []):
        _a = _r.get("arch")
        if _a and _a in _arch_t and _arch_t[_a] != _r["sid"]:
            errors.append("'%s'(%s)의 arch '%s'가 세 번째 목록의 %s 와 같다 — "
                          "같은 아키타입을 다른 sid 로 다시 등록했다"
                          % (_r.get("name"), _r["sid"], _a, _arch_t[_a]))

    # ④ 목록이 화면에 나가는지 — 모아 놓고 안 내면 모은 적 없는 것과 같다
    if not (_tech3.get("tested") or []):
        errors.append("data/tech_strategies.json 에 tested(세 번째 목록)가 비었다 — "
                      "build/tech_backtest.py 가 안 싣고 있다(수집 ≠ 배선)")
    elif len(_tech3["tested"]) != len(_tested):
        errors.append("세 번째 목록 개수 불일치 — 정본 %d종 vs 산출 %d종. "
                      "build/tech_backtest.py 재실행 필요"
                      % (len(_tested), len(_tech3["tested"])))
    # ⑤ 🚨 풀 카드의 **산문 안에 글자로 박힌 sid** 를 훑는다. ①~④ 는 전부 sid *필드* 로
    #   대조하는데 data/rotation_pool.json 에는 sid 필드가 없다 — 카드 본문이 규칙 이름을
    #   문장으로 인용할 뿐이다. 그래서 규칙을 삭제하거나 선반으로 옮겨도 그 카드는
    #   '지금은 없는 규칙' 을 있는 것처럼 계속 말한다(이 검사 없이는 아무도 못 잡는다).
    try:
        _pool5 = json.load(io.open(os.path.join(ROOT, "data", "rotation_pool.json"),
                                   encoding="utf-8"))
        _arch5 = {x.get("sid") for x in AREC if x.get("sid")}
        _known5 = set(_live3) | _retd3 | set(_tested) | _arch5
        # ⚠ 오탐 방지: 영문 하이픈 단어가 sid 처럼 보이는 것을 거른다. 알려진 sid 합집합에
        #   없는 토큰만 걸되, 아래 허용목록은 사람이 판단해 늘린다.
        _ok5 = {"e-mail", "t-test", "x-axis", "t-stat"}
        for _s5 in (_pool5.get("strategies") or []):
            _lab5 = _s5.get("lab") or {}
            _txt5 = " ".join(str(_lab5.get(k) or "") for k in ("v", "why", "t"))
            for _tok in sorted(set(re.findall(r"(?<![A-Za-z0-9_-])[xte]-[a-z0-9]+(?![A-Za-z0-9_-])", _txt5))):
                if _tok in _ok5:
                    continue
                if _tok in _tested and _tok not in _live3:
                    if "tested_not_published" not in _txt5:
                        errors.append(
                            "rotation_pool %s: lab 산문이 '%s' 를 인용하는데 그 규칙은 세 번째 "
                            "목록(돌렸지만 게시 안 함)에 있다 — build/tested_not_published.json "
                            "을 함께 가리키거나 문장을 고칠 것" % (_s5.get("id"), _tok))
                elif _tok not in _known5:
                    errors.append(
                        "rotation_pool %s: lab 산문이 '%s' 를 인용하는데 살아 있는 규칙·퇴출·"
                        "선반·아카이브 어디에도 없다 — 낡은 참조다" % (_s5.get("id"), _tok))
    except Exception as _e5:
        errors.append("rotation_pool 산문 sid 검사가 예외로 죽었다 — %s" % _e5)

    # 🚨 '통과' 는 이 블록이 오류를 **하나도** 안 냈을 때만 찍는다. 종전에는 ④만 보고
    #   찍어서, ①이 실패한 판에서도 "대조 통과" 가 함께 나왔다 — 실패하면서 통과라고
    #   말하는 출력이다(자체 시험에서 잡았다).
    # ①-e 🚨 2026-08-21 사용자 신고 «1개월 차트에 ETF 3개밖에 안 보임» — home_perf 의 구간
    #   판은 기준일에 값이 없는 계열을 통째로 뺀다(0 으로 채우지 않는 것은 옳다). 그래서
    #   상류 assets 의 **하루 구멍**이 그 날을 기준일로 쓰는 판 하나만 조용히 반토막 낸다.
    #   실측: 7-21 수집 실패 → 1M 판이 스타일 3/8·섹터 7/11. 판마다 계열 수가 같은지 본다.
    try:
        _hp = json.load(io.open(os.path.join(ROOT, "data", "home_perf.json"), encoding="utf-8"))
        _ser = _hp.get("series") or {}
        _cnt = {h: {k: len((b or {}).get(k) or {}) for k in ("ix", "sec", "sty")}
                for h, b in _ser.items()}
        for _k in ("ix", "sec", "sty"):
            _vals = {h: c[_k] for h, c in _cnt.items() if c.get(_k)}
            if not _vals:
                continue
            _mx = max(_vals.values())
            _short = {h: v for h, v in _vals.items() if v < _mx}
            if _short:
                errors.append("home_perf 구간판 계열 수 불균일(%s) — 최대 %d인데 %s. "
                              "대개 상류 assets 의 그 기준일 결측이다(기준일: %s)"
                              % (_k, _mx, ", ".join("%s %d" % kv for kv in sorted(_short.items())),
                                 ", ".join("%s=%s" % (h, (_hp.get("base_dates") or {}).get(h))
                                           for h in sorted(_short))))
    except Exception as _e8:
        errors.append("home_perf 구간판 대조 실패 — %s" % _e8)

    # ①-d 🚨 2026-08-21 — 가족(family) 지도 완전성. explorer 큰 칸이 «팩터·테크니컬·타이밍·
    #   자산배분» 축으로 바뀌면서(사용자 요청) 종목 수익엔진은 strategy_kinds.family_of 손
    #   지도로 갈린다. 지도에 없는 sid 가 생기면 화면이 '미분류' 칸을 만든다 — 손 지도의
    #   낡음을 사람이 아니라 여기서 잡는다(화면 famOf 규칙과 동일 규칙).
    try:
        _kd = json.load(io.open(os.path.join(ROOT, "data", "strategy_kinds.json"),
                                encoding="utf-8"))
        _fo = _kd.get("family_of") or {}
        _six = json.load(io.open(os.path.join(ROOT, "data", "strategy_index.json"),
                                 encoding="utf-8"))
        _unk = [x.get("sid") for x in (_six.get("items") or [])
                if x.get("src") == "종목 전략" and x.get("role") == "수익엔진"
                and x.get("sid") not in _fo]
        if _unk:
            errors.append("가족 지도에 없는 종목 수익엔진 %d종 — strategy_kinds.family_of 에 "
                          "팩터/테크니컬로 등재할 것: %s" % (len(_unk), ", ".join(_unk[:8])))
    except Exception as _e7:
        errors.append("가족 지도 대조 실패 — %s" % _e7)

    # ①-e 🚨 2026-09-02 — **«표시용 계열» 검사.** 이 저장소가 하루에 네 번 밟은 결함이다:
    #   strategies[].dates/nav 는 약 7일 간격 504점짜리 **표시용 표본**인데 이름이 그렇게
    #   안 읽혀, 분석에서 «일간 정본» 으로 알고 접었다(chart.nav 도 같다). chart.monthly 도
    #   월간 표본이고 **둘 중 어느 것도 metrics 를 정확히 재현하지 않는다.**
    #   그래서 ① 자료가 스스로 그 사실을 적게 하고(series_note·sampling) ② 그 선언이
    #   실제와 맞는지를 여기서 기계로 대조한다. 선언만 있고 안 맞으면 선언이 낡은 것이다.
    import datetime as _dtm          # 이 파일은 위쪽에서 _dt 로 쓰는 자리가 따로 있다
    # 🚨 2026-09-03 — **자료가 스스로 못박은 불변식을 검사로 만든다.**
    #   data/asof.json 의 signals 축 주석이 「종목 스냅샷과 같은 잡에서 같은 기준일로
    #   굽는다 — **어긋나면 그건 사고다**」라고 적어 뒀는데, 그 사고를 재는 곳이 없었다.
    #   실제로 refresh-stocks.yml 이 signal_lab.py 를 돌리고 커밋까지 하면서 신선도 검사도
    #   안 걸고 있었다(같은 날 배선했다). 여기서는 «둘이 같은 날인가» 를 본다 —
    #   신선도 검사는 «낡았나» 만 보므로 둘이 나란히 낡으면 통과한다. 짝을 이룬다.
    try:
        _sl = json.load(io.open(os.path.join(ROOT, "data", "signal_lab.json"), encoding="utf-8"))
        _st = json.load(io.open(os.path.join(ROOT, "data", "stocks.json"), encoding="utf-8"))
        _sa, _ta = _sl.get("as_of"), _st.get("as_of")
        if _sa and _ta and _sa != _ta:
            errors.append(
                "지표별 타이밍 신호와 종목 스냅샷의 기준일이 다르다 — signal_lab %s vs "
                "stocks %s. 둘은 refresh-stocks.yml 의 **같은 실행**에서 같은 격자로 구워야 "
                "한다(data/asof.json 의 signals 축이 「어긋나면 그건 사고다」라고 적어 뒀다). "
                "한쪽만 커밋됐거나 잡이 중간에 죽은 것이다" % (_sa, _ta))
    except FileNotFoundError:
        pass

    # ⚠ 2026-09-03 — style_perf.json 을 목록에 더한다. 같은 함정을 가진 파일이 규약 밖에
    #   있었다: styles[].nav 는 252점 → 140점으로 솎은 표시용 표본이고 **dates 조차 없다**
    #   (좌표계가 없어 어느 날 값인지 못 되짚는다). 되계산하면 MDD 가 최대 1.76%p 어긋난다.
    #   이 함정으로 이미 한 번 틀렸다(A1PAYOUT-RESULT §8-1).
    #   ⚠ 이 파일은 항목이 styles 이고 dates 가 없으므로 아래 «간격·복리» 대조는 건너뛴다 —
    #     선언이 있는지만 본다. 선언조차 없으면 읽는 사람이 정본으로 안다.
    _BUILDER = {"tech_strategies.json": "tech_backtest.py",
                "asset_strategies.json": "asset_backtest.py",
                "style_perf.json": "style_top_pdf.py"}
    for _fn, _lbl in (("tech_strategies.json", "종목 랩"), ("asset_strategies.json", "자산 랩"),
                      ("style_perf.json", "랩 스타일")):
        try:
            _d = json.load(io.open(os.path.join(ROOT, "data", _fn), encoding="utf-8"))
        except Exception as _e:
            errors.append("%s 를 못 읽었다 — %s" % (_fn, _e)); continue
        if not _d.get("series_note") or not _d.get("sampling"):
            errors.append("%s 에 series_note/sampling 이 없다 — nav 가 표시용 표본이라는 "
                          "사실을 자료가 스스로 적어야 한다(2026-09-02 규약). "
                          "build/%s 의 산출 묶음에 넣을 것" % (_fn, _BUILDER.get(_fn, "?")))
            continue
        _sm = _d["sampling"]
        _rows = _d.get("strategies") or _d.get("items") or []
        _gaps, _dn, _dm = [], [], []
        for _r in _rows:
            _dd, _nv = _r.get("dates"), _r.get("nav")
            _mo = (_r.get("chart") or {}).get("monthly")
            _cg = (_r.get("metrics") or {}).get("cagr")
            if not (_dd and _nv and _mo and _cg):
                continue
            try:
                _g = [(_dtm.date.fromisoformat(_dd[i + 1]) - _dtm.date.fromisoformat(_dd[i])).days
                      for i in range(min(80, len(_dd) - 1))]
                _yr = ((_dtm.date.fromisoformat(_dd[-1]) - _dtm.date.fromisoformat(_dd[0])).days
                       / 365.25)
            except ValueError:
                continue                     # 월 키('YYYY-MM')를 쓰는 몇 종은 건너뛴다
            if not _g or _yr <= 0:
                continue
            _gaps.append(sorted(_g)[len(_g) // 2])
            _dn.append(abs(((_nv[-1] / _nv[0]) ** (1 / _yr) - 1) * 100 - _cg))
            _p = 1.0
            for _x in _mo:
                _p *= 1 + _x["r"] / 100.0
            _dm.append(abs((_p ** (12.0 / len(_mo)) - 1) * 100 - _cg))
        if not _gaps:
            continue
        _med = sorted(_gaps)[len(_gaps) // 2]
        _decl = (_sm.get("nav") or {}).get("median_gap_days")
        if _decl and abs(_med - _decl) > 1:
            errors.append("%s: nav 간격 선언 %d일인데 실측 %d일 — sampling 선언이 낡았다"
                          % (_lbl, _decl, _med))
        _cap = _sm.get("max_cagr_gap_pp") or {}
        for _k, _v in (("nav", _dn), ("monthly", _dm)):
            _lim = _cap.get(_k)
            if _lim and max(_v) > _lim * 1.5:
                errors.append("%s: %s 복리와 metrics.cagr 의 차이가 선언(%.2f%%p)의 1.5배를 "
                              "넘었다 — 실측 최대 %.2f%%p. 표본이 더 성겨졌거나 산식이 "
                              "바뀐 것이다(선언을 고치기 전에 왜 벌어졌는지 볼 것)"
                              % (_lbl, _k, _lim, max(_v)))

    # ①-c 🚨 2026-08-20 — 세 번째 목록의 **셋째 사본**(data/strategy_report.json tested.tech)
    #   도 대조한다. 당일 측정 세션이 정본·tech 사본만 늘리면 report.html 이 옛 수(98종)를
    #   하루 창 동안 보여 줬는데, 이 검사가 없어 «전항 통과»로 보였다(점검 패널 실측).
    try:
        _sr = json.load(io.open(os.path.join(ROOT, "data", "strategy_report.json"),
                                encoding="utf-8"))
        _srt = ((_sr.get("tested") or {}).get("tech")) or []
        if len(_srt) != len(_tested):
            errors.append("세 번째 목록 사본 어긋남 — 정본 %d종 vs strategy_report %d종. "
                          "python build/strategy_report.py 재실행 필요" % (len(_tested), len(_srt)))
    except Exception as _e6:
        errors.append("strategy_report 세 번째 목록 대조 실패 — %s" % _e6)
    if len(errors) == _n_err0:
        print("  ~ 세 번째 목록 대조 통과(돌렸지만 게시 안 함 %d종 · 재등록 %d종)"
              % (len(_tested), sum(1 for x in _tested.values() if x.get("readmitted"))))
except FileNotFoundError as _e:
    errors.append("build/tested_not_published.json 이 없다 — 세 번째 목록 대조를 못 한다")
except Exception as _e:
    errors.append("세 번째 목록 대조 실패 — %s" % _e)


_dd = os.path.join(ROOT, "data")
try:
    _rep = json.load(io.open(os.path.join(_dd, "strategy_report.json"), encoding="utf-8"))
    _tech = json.load(io.open(os.path.join(_dd, "tech_strategies.json"), encoding="utf-8"))
    _ass = json.load(io.open(os.path.join(_dd, "asset_strategies.json"), encoding="utf-8"))
    for _k, _src, _lab in (("tech", _tech, "종목 랩"), ("asset", _ass, "자산 랩")):
        _a, _b = (_rep.get("as_of") or {}).get(_k), _src.get("as_of")
        if _a != _b:
            errors.append("복제 리포트 기준일 불일치 — %s %s vs strategy_report %s. "
                          "build/strategy_report.py 재실행 필요" % (_lab, _b, _a))
        _n = len(_src.get("strategies") or [])
        _m = len([x for x in _rep.get("items") or []
                  if x.get("family") == ("종목·타이밍" if _k == "tech" else "자산배분")])
        if _n != _m:
            errors.append("복제 리포트 규칙 수 불일치 — %s %d종 vs 리포트 %d편" % (_lab, _n, _m))
except FileNotFoundError:
    errors.append("data/strategy_report.json 이 없다 — build/strategy_report.py 를 돌릴 것")
except Exception as _e:
    errors.append("복제 리포트 대조 실패 — %s" % _e)


# ── 배선 검사: 모아 놓고 안 잇는 것을 잡는다 ────────────────────────────
#   🚨 2026-08-04 하루에 **네 번** 같은 사고가 났다. 전부 "수집은 됐는데 다음 단계가
#   그 값을 안 받아" 조용히 없는 것과 같아진 경우다. 넷 다 실행은 **성공**했다 —
#   그래서 아무도 몰랐다.
#     ① refresh_facts 가 태그 5종(ca·cl·debt·re·dep)을 새로 모았는데 load_fund 가 안 실었다
#        → 그것을 쓰는 규칙이 198개월 전부 후보 0. 규칙이 아니라 배선이 원인이었다.
#     ② tech_backtest 가 pool·n_thin 을 냈는데 strategy_index 가 안 넘겨 화면이 계속 비었다
#     ③ pit_backtest 는 FUND_SIDS 에 넣어도 score() 갈래가 없으면 무보유 → 표엔 '열위'
#     ④ pit 실측이 판정 강등에만 쓰이고 화면에는 안 나갔다
#   ③은 score() 가 이제 죽고, ④는 이미 이었다. ①②를 여기서 막는다.
#   ⚠ 안 잇는 것이 늘 잘못은 아니다 — 그래서 '일부러 안 잇는 것' 목록을 명시로 둔다.
#     목록에 적는 순간 그것은 결정이 되고, 아무도 모르게 빠지는 일은 없어진다.
try:
    sys.path.insert(0, os.path.join(ROOT, "build"))
    import refresh_facts as _RF
    import tech_backtest as _TB

    # ① 수집 태그 → load_fund 계열
    _tag_keys = {t[0] for t in _RF.TAGS} | {t[0] for t in _RF.TAGS_IFRS}
    _WIRE_SKIP = {
        "sho": "sh 가 없을 때만 쓰는 대타 — load_fund 안에서 sh 로 합쳐진다",
        "iss": "주식 발행(현금흐름) — 쓰는 규칙이 아직 없다",
    }
    _fu = _TB.load_fund()
    _sample = set()
    for _v in _fu.values():
        _sample |= set(_v)
    _missing = sorted(_tag_keys - _sample - set(_WIRE_SKIP))
    if _missing:
        errors.append("수집만 되고 백테스트에 안 실린 재무 태그 %d개: %s — "
                      "refresh_facts.TAGS 에 넣었으면 tech_backtest.load_fund 도 실어야 한다"
                      "(안 쓸 것이면 validate_site 의 _WIRE_SKIP 에 사유와 함께 적을 것)"
                      % (len(_missing), ", ".join(_missing)))

    # ①-b 일봉 계열 → tech_backtest.load()
    #   🚨 ① 은 **재무 태그만** 봤다. 그래서 같은 사고가 일봉 쪽에서 조용히 나 있었다 —
    #   refresh_stocks.py 가 종목당 고가(hd)·저가(ld)를 4,422일치 써 두고 있었는데
    #   tech_backtest.load() 는 pxd·vd 만 집어 갔다(2026-08-04 실측). 결과는 '규칙이
    #   나쁘다'가 아니라 **일중 범위를 쓰는 규칙을 만들 수 없었다** 였고, 아무 검사도
    #   그걸 말해 주지 않았다. 검사의 범위가 사고의 범위보다 좁으면 그 검사는 다음 사고를
    #   못 막는다 — 그래서 여기를 넓힌다.
    #   판정 방식: data/sd/*.json 의 **일봉 길이 배열** 키를 모으고, load() 원문이 그 키를
    #   실제로 집어 가는지(`d.get("키")`) 본다. 원문 검사라 투박하지만, '읽는 코드가
    #   존재하는가'를 묻는 데는 이것이 가장 직접적이다.
    import inspect as _inspect
    import re as _re
    _SD_SKIP = {
        "sig": "화면용 기술적 지표 스냅샷(오늘 값 하나) — 시계열이 아니라 백테스트에 못 쓴다",
        "why": "화면용 설명 문자열",
        "fundx": "화면용 밸류에이션 스냅샷 — 시점정합이 없어 백테스트에 쓰면 선견이다",
        "fundx_flags": "화면용 태그", "fundx_na": "화면용 태그",
        "prof": "회사 소개 텍스트", "as_of": "기준일", "t": "티커",
    }
    _sd_dir = os.path.join(ROOT, "data", "sd")
    _sd_keys = set()
    if os.path.isdir(_sd_dir):
        # ⚠ 40종 표본이었다. 배선(키 존재)만 보는 검사라 표본으로 충분하다고 봤는데,
        #   그러면 나머지 478종에서 계열이 통째로 사라져도 통과한다 — 이 검사가 막으려는
        #   사고가 정확히 "조용히 없어지는 것"이므로 전수로 본다(파일 열기 518회, 수 초).
        _fs = [f for f in sorted(os.listdir(_sd_dir)) if f.endswith(".json")]
        for _f in _fs:
            try:
                _j = json.load(io.open(os.path.join(_sd_dir, _f), encoding="utf-8"))
            except Exception:
                continue
            _sd_keys |= {k for k, v in _j.items() if isinstance(v, list) and len(v) > 500}
    _src = _inspect.getsource(_TB.load)
    _read = set(_re.findall(r'd\.get\(\s*["\'](\w+)["\']', _src))
    _sd_missing = sorted(_sd_keys - _read - set(_SD_SKIP))
    if _sd_missing:
        errors.append("data/sd 에 모아 놓고 tech_backtest.load() 가 안 읽는 일봉 계열 %d개: %s — "
                      "refresh_stocks 가 쓰면 load() 도 읽어야 한다"
                      "(안 쓸 것이면 validate_site 의 _SD_SKIP 에 사유와 함께 적을 것)"
                      % (len(_sd_missing), ", ".join(_sd_missing)))

    # ② tech_strategies 규칙 필드 → strategy_index 항목
    _ts = json.load(io.open(os.path.join(ROOT, "data", "tech_strategies.json"), encoding="utf-8"))
    _si = json.load(io.open(os.path.join(ROOT, "data", "strategy_index.json"), encoding="utf-8"))
    _IDX_SKIP = {
        "sid", "kind", "why", "rule", "name", "verdict",   # 인덱스가 이름을 바꿔 싣는다
        "dates", "chart", "exposure", "incr", "n_days", "role", "n_stocks",
        # 🚨 perf_end 는 인덱스에서 **이름을 바꿔 실린다** — rec(end=...) 가 이 값을 받아
        #   "end" 로 넣는다(strategy_index 의 rec 호출부). 같은 수가 두 이름으로 가면
        #   화면이 어느 쪽을 믿을지 고르게 되고, 그 선택이 파일마다 갈린다.
        #   ⚠ 짝인 px_end 는 이름 그대로 넘어간다(구간수익의 지수 대조가 그걸 쓴다).
        "perf_end",
        "excess_cagr", "bench",                            # metrics/bench 로 접혀 들어간다
        # 🚨 입력 커버리지 플래그 — **효과가 이미 화면에 가 있다.** 이 둘이 켜지면
        #   tech_backtest 가 verdict 를 '판정 불가' 로 내리고 why 뒤에 사유를 붙인다:
        #   "입력(투자의견 이력)이 0.0%만 존재해 나머지 기간이 자동으로 현금 처리됐다.
        #    여기 성과는 규칙의 실력이 아니다." — 커버리지 수치까지 그 문장에 들어간다.
        #   verdict·why 는 인덱스로 넘어가므로 원시 플래그를 또 보내면 같은 말이 두 벌이 된다.
        # ⚠ 이 둘은 **정상 빌드에서는 아예 안 생긴다.** gitignore 된 로컬 캐시
        #   (_ratings_cache.json 등)가 없는 환경에서 돌릴 때만 켜진다. 실제로 워크트리에서
        #   캐시 없이 돌렸다가 7규칙이 이 상태로 나왔고(2026-08-14), 그때 이 검사가 잡았다 —
        #   결과적으로 '캐시 없이 빌드했다' 를 알려 준 셈이라 검사 자체는 값을 했다.
        "cov_short", "input_cov",
    }
    _by = {}
    for _it in (_si.get("items") or []):
        _s = _it.get("sid") or ""
        _by[_s] = _it
        if _s.startswith("t-"):
            _by[_s[2:]] = _it
    _lost = {}
    for _r in _ts.get("strategies", []):
        _it = _by.get(_r.get("sid"))
        if not _it:
            continue
        for _k, _v in _r.items():
            if _k in _IDX_SKIP or _v in (None, "", [], {}):
                continue
            if _k not in _it:
                _lost.setdefault(_k, 0)
                _lost[_k] += 1
    if _lost:
        errors.append("tech_strategies 에 있는데 strategy_index 로 안 넘어가는 필드 %d개: %s — "
                      "화면(explorer)은 인덱스만 읽으므로 여기서 빠지면 잰 적 없는 것과 같다"
                      "(안 보낼 것이면 validate_site 의 _IDX_SKIP 에 적을 것)"
                      % (len(_lost), ", ".join("%s(%d규칙)" % (_k, _n) for _k, _n in sorted(_lost.items()))))
    if not _missing and not _lost:
        print("  ~ 배선 검사 통과(재무 태그 %d종 · 전략 필드 %d종)"
              % (len(_tag_keys), len(_ts.get("strategies", []))))
except Exception as _e:
    tool_skips.append("배선 검사(%s)" % _e)


# ── el('x') 가 가리키는 요소가 그 페이지에 있나 ────────────────────────────
#   🚨 2026-08-10 에 이 검사가 없어서 난 사고. sector.html 의 el('nmax') 가 가리키던
#     안내문이 설명 정리 때 지워졌는데 **채우는 줄만 남았다**. el 은 getElementById 라
#     null 을 주고 .textContent= 가 던져, 그 함수의 나머지가 통째로 죽었다 —
#     rtally·sampfirst·partn·covA·covB·linknote·cursub·curbars·mx·maptbl 열 자리가
#     라이브에서 비어 있었다.
#     가장 나쁜 부분은 바깥 .catch() 가 그 TypeError 를 받아 "데이터를 불러오지
#     못했습니다"를 그렸다는 것이다. **배선 결함이 자료 결함으로 위장했다** — 화면은
#     자료 탓을 하고 있었고 자료는 멀쩡했다. 그래서 몇 주간 아무도 못 봤다.
#   ⚠ 문자열 리터럴만 본다(el('up-'+rid) 같은 조립형은 대상이 아니다 — 그쪽은 id 가
#     자료에서 오므로 정적으로 알 수 없다). 그래서 거짓양성이 없다: 실측 24페이지에서
#     위 두 건 말고는 전부 짝이 맞았다.
try:
    import glob as _glob
    _wire_bad = []
    def _strip_comments(_t):
        """JS 주석을 걷어낸다 — 주석에 적은 el('x') 예시를 배선으로 세지 않으려고.

        🚨 이 검사를 처음 걸었을 때 **자기가 쓴 주석 네 줄에 스스로 걸렸다**. 사고를
          설명하려고 주석에 el('nmax') 라고 적었더니 그것을 배선으로 읽었다. 주석은
          코드가 아니다.
        ⚠ '//' 는 줄 전체가 주석일 때만 자른다. 코드 중간의 '//' 는 URL(https://)일 수
          있어서, 문자열 안인지 아닌지를 정규식으로는 못 가린다 — 덜 자르는 쪽으로 둔다.
        """
        _t = re.sub(r"/\*.*?\*/", " ", _t, flags=re.S)
        return "\n".join(_ln for _ln in _t.split("\n") if not _ln.lstrip().startswith("//"))

    for _p in sorted(_glob.glob(os.path.join(ROOT, "*.html"))):
        _s = io.open(_p, encoding="utf-8").read()
        _ids = set(re.findall(r'\bid="([A-Za-z0-9_\-]+)"', _s))
        _used = set(re.findall(r"\bel\(\s*'([A-Za-z0-9_\-]+)'\s*\)", _strip_comments(_s)))
        for _k in sorted(_used - _ids):
            _wire_bad.append("%s: el('%s')" % (os.path.basename(_p), _k))
    if _wire_bad:
        errors.append("가리키는 요소가 없는 el() %d건: %s — 널 가드가 없으면 그 줄에서 "
                      "예외가 나고 뒤가 통째로 죽는다(그리고 .catch 가 '자료를 못 받았다'로 "
                      "위장한다). 요소를 되살리든 죽은 줄을 지우든 짝을 맞출 것"
                      % (len(_wire_bad), " · ".join(_wire_bad[:8])))
    else:
        print("  ~ el() 배선 검사 통과(%d페이지)" % len(_glob.glob(os.path.join(ROOT, "*.html"))))
except Exception as _e:
    tool_skips.append("el() 배선 검사(%s)" % _e)


# ── DATA-FACTS.md 가 스스로 검사받는다 ────────────────────────────────────
#   🚨 문서에 박은 숫자는 아무도 안 볼 때 조용히 거짓이 된다. 2026-08-04 실측 두 건 —
#   style_pit.py 머리말의 편향 요약이 두 달 만에 성장 26.2 → 2.4%p 로 어긋나 있었고,
#   DATA-FACTS 의 gp 커버리지도 쓰는 사이에 37.7 → 38.3% 로 움직였다.
#   그래서 그 문서의 <!-- DATA-FACTS-CHECK --> 블록을 읽어 **다시 재고** 어긋나면 실패시킨다.
#   ⚠ 목적은 숫자를 얼리는 것이 아니라 **낡은 것을 알아채는 것**이다. 어긋나면 할 일은 둘 중
#     하나 — 정상적으로 움직인 것이면 문서를 고치고, 뜻밖이면 왜 움직였는지 먼저 본다.
try:
    _dfp = os.path.join(ROOT, "build", "DATA-FACTS.md")
    _dft = io.open(_dfp, encoding="utf-8").read()
    _m = re.search(r"<!--\s*DATA-FACTS-CHECK\s*(\{.*?\})\s*-->", _dft, re.S)
    if not _m:
        errors.append("build/DATA-FACTS.md 에 DATA-FACTS-CHECK 블록이 없다 — "
                      "문서의 수치를 기계가 다시 잴 수 없으면 낡아도 아무도 모른다")
    else:
        _exp = json.loads(_m.group(1))
        _fxd = os.path.join(ROOT, "data", "fx")
        _n_gp = _n_all = 0
        _rev_old = []
        for _f in os.listdir(_fxd):
            if not _f.endswith(".json"):
                continue
            try:
                _tg = json.load(io.open(os.path.join(_fxd, _f), encoding="utf-8")).get("tags") or {}
            except Exception:
                continue
            _n_all += 1
            if _tg.get("gp"):
                _n_gp += 1
            _q = (_tg.get("rev") or {}).get("q")
            if _q:
                _rev_old.append(_q[-1][0])
        _rev_old.sort()
        _cm = json.load(io.open(os.path.join(ROOT, "data", "cik_map.json"), encoding="utf-8")).get("co") or {}
        _cnt = {}
        for _t, _c in _cm.items():
            if _c:
                _cnt[_c] = _cnt.get(_c, 0) + 1
        _ts = json.load(io.open(os.path.join(ROOT, "data", "tech_strategies.json"), encoding="utf-8"))
        _xs = [_r for _r in _ts.get("strategies", []) if _r.get("pool")]
        _got = {
            "gp_cov_pct": round(_n_gp / max(1, _n_all) * 100, 1),
            "rev_q_oldest_med": (_rev_old[len(_rev_old) // 2][:7] if _rev_old else ""),
            "dual_pairs": sum(1 for _v in _cnt.values() if _v > 1),
            "xsec_rules": len(_xs),
            "narrow_rules": sum(1 for _r in _xs if _r["pool"]["narrow"]),
            "incr5_rules": sum(1 for _r in _ts.get("strategies", []) if _r.get("incr5")),
        }
        # 허용오차 — 자연스러운 움직임은 넘기고, 문서가 낡은 수준이면 잡는다.
        _TOL = {"gp_cov_pct": 3.0, "dual_pairs": 0, "xsec_rules": 3, "narrow_rules": 3,
                "incr5_rules": 3}
        _drift = []
        for _k, _v in _got.items():
            if _k not in _exp:
                continue
            _e = _exp[_k]
            if isinstance(_v, str):
                if _v != _e:
                    _drift.append("%s: 문서 %s → 실측 %s" % (_k, _e, _v))
            else:
                if abs(_v - _e) > _TOL.get(_k, 0):
                    _drift.append("%s: 문서 %s → 실측 %s (허용 ±%s)" % (_k, _e, _v, _TOL.get(_k, 0)))
        if _drift:
            errors.append("build/DATA-FACTS.md 의 수치가 낡았다 %d건 — %s. "
                          "정상적인 이동이면 문서를 고치고(그 블록도 함께), 뜻밖이면 왜 움직였는지 먼저 볼 것"
                          % (len(_drift), " · ".join(_drift)))
        else:
            print("  ~ DATA-FACTS 수치 검사 통과(%d항목 재측정)" % len(_got))
except Exception as _e:
    tool_skips.append("DATA-FACTS 수치 검사(%s)" % _e)

# 🚨 2026-08-05 — tool_skips 인쇄가 적재 지점보다 **600행 앞**에 있었다. 그래서 배선 검사와
#   DATA-FACTS 수치 검사가 예외로 죽으면 그 사실이 어디에도 안 찍히고 exit 0 으로 끝났다
#   (두 검사 다 try/except 로 tool_skips 에 넣기만 한다). 검사가 안 돈 것과 통과한 것이
#   화면에서 구별되지 않았다 — 이 파일이 막으려는 사고를 이 파일이 저지르고 있었다.
_late = [x for x in tool_skips if x not in _skips_shown]
if _late:
    print("⚠ 검사 건너뜀 %d건(위 목록 뒤에 발생 — 통과가 아니라 **미검증**이다):" % len(_late))
    for _s in sorted(_late):
        print("  ~", _s)
    # 핵심 가드가 죽은 것은 통과로 넘기지 않는다. 도구 부재(node)와 달리 이쪽은 코드 오류다.
    for _s in _late:
        if _s.startswith("배선 검사") or _s.startswith("DATA-FACTS"):
            errors.append("핵심 검사가 예외로 죽었다 — %s. 이 검사는 건너뛰면 안 된다" % _s)

# ── 제어문자 검사: 정규식이 조용히 다른 규칙이 된다 ──────────────────────
# 🚨 2026-08-05 하루에 **세 번** 났다. 편집 도구가 `\b`(단어경계)를 한 겹 덜 이스케이프하면
#   0x08(백스페이스) 한 글자로 들어간다. 파이썬은 정상 컴파일하고 정규식도 정상 동작하는데
#   **매치하는 대상만 달라진다** — refresh_custconc 의 MANY 가 그래서 복수고객을 못 잡았고,
#   kb_lock 의 data-tool 검사가 그래서 있는데도 없다고 했다. 눈으로는 안 보인다.
#   소스·문서에 인쇄 불가 제어문자가 있을 이유가 없으므로 통째로 막는다.
_CTRL_OK = {chr(9), chr(10), chr(13)}          # 탭·개행·복귀만 허용
_ctrl = []
for _root, _dirs, _files in os.walk(ROOT):
    _dirs[:] = [_d for _d in _dirs if _d not in (".git", "_build", "node_modules", "__pycache__")]
    for _fn in _files:
        if not _fn.endswith((".py", ".md", ".html", ".js", ".yml")):
            continue
        _fp = os.path.join(_root, _fn)
        try:
            _tx = io.open(_fp, encoding="utf-8").read()
        except Exception:
            continue
        _bad = {c for c in _tx if ord(c) < 32 and c not in _CTRL_OK}
        if _bad:
            _ctrl.append("%s(%s)" % (os.path.relpath(_fp, ROOT),
                                     " ".join("0x%02x" % ord(c) for c in sorted(_bad))))
if _ctrl:
    errors.append("인쇄 불가 제어문자가 들어간 파일 %d개: %s — 정규식이 조용히 다른 규칙이 "
                  "된다(예: `\b` 를 덜 이스케이프하면 0x08 한 글자가 된다)"
                  % (len(_ctrl), ", ".join(_ctrl[:6])))

# ── 라이선스 자료가 공개 저장소에 들어왔는가 ──────────────────────────────
# 🚨 2026-08-05 — data/pit_members.json(사내 DB public.index_constituents 산출)이
#   `git add -A` 에 쓸려 커밋됐다. 2026-08-03 에 파이프라인에서 걷어내면서 **무시 규칙도
#   같이 지웠기** 때문이다. 이 저장소는 공개(GitHub Pages)라 올라가면 되돌리기 어렵다.
#   푸시가 거부돼 공개되진 않았지만, 그건 운이었다. 규칙으로 막는다.
_LICENSED = ("data/pit_members.json",)
# ⚠ 여기를 try/except: pass 로 감싸면 안 된다. 검사가 죽어도 조용히 통과하는데,
#   그건 이 검사가 막으려는 것보다 나쁘다(오늘만 같은 유형을 여러 번 고쳤다).
#   _sp0 은 모듈 최상단에서 import 한 것이다 — 아래쪽 try 안의 _sp 는 그 블록이
#   안 돌면 정의되지 않는다.
_leak = []
for _lf in _LICENSED:
    _r = _sp0.run(["git", "ls-files", "--error-unmatch", _lf], cwd=ROOT,
                  capture_output=True, text=True)
    if _r.returncode == 0:
        _leak.append(_lf)
if _leak:
    errors.append("라이선스 자료가 저장소에 추적되고 있다: %s — 사내 DB 산출물이라 공개 "
                  "저장소에 두면 안 된다(`git rm --cached` 로 빼고 .gitignore 에 넣을 것)"
                  % ", ".join(_leak))

# ── 손으로 적은 갱신 주기가 크론과 어긋나는가 ────────────────────────────
# 🚨 2026-08-05 — asof_index 의 cadence 는 손으로 적고 sched 는 크론에서 파생한다.
#   둘이 한 문자열로 붙어 화면에 나가는데, 어긋나면 "매일 · 매주 토 07:30 KST" 같은
#   자기모순이 그대로 찍힌다. 실제로 둘이 반대 방향으로 틀려 있었다 —
#   선행 컨센서스(매일↔주간) · 자산 패널(주 1회↔매일). 정상 지연이 고장처럼 보였다.
#   ⚠ '분기 데이터셋'처럼 **자료의 주기**를 적는 축은 잡 주기와 달라도 맞다. 그래서
#     매일↔주간이 정면으로 뒤집힌 경우만 잡는다.
try:
    _aj = json.load(io.open(os.path.join(ROOT, "data", "asof.json"), encoding="utf-8"))
    _bad_cad = []
    for _a in (_aj.get("axes") or []):
        _cad, _sch = (_a.get("cadence") or ""), (_a.get("sched") or "")
        if not _sch:
            continue
        _daily_txt = ("매 거래일" in _cad) or ("매일" in _cad)
        _weekly_txt = "주 1회" in _cad
        _daily_cron = ("월~토" in _sch) or (_sch.count("매주") > 1)
        _weekly_cron = ("매주" in _sch) and not _daily_cron
        if (_daily_txt and _weekly_cron) or (_weekly_txt and _daily_cron):
            _bad_cad.append("%s(적힘 '%s' ↔ 크론 '%s')" % (_a.get("label"), _cad, _sch))
    if _bad_cad:
        errors.append("갱신 주기 라벨이 크론과 어긋난다 %d개: %s — build/asof_index.py 의 "
                      "cadence 는 손으로 적는 값이라 크론을 바꿀 때 같이 안 고쳐진다"
                      % (len(_bad_cad), " · ".join(_bad_cad)))
except FileNotFoundError:
    pass

# ── 소스 장애 대장이 화면까지 이어지는가 ────────────────────────────────
# 🚨 2026-08-05 — 대장(data/source_outages.json)에 적힌 결측은 완전성 게이트를 통과한다.
#   즉 '줄어든 지수'가 게시된다는 뜻이다. 그 사실이 화면에 안 나가면 이 저장소가 여러 번
#   당한 그것이다 — 재 놓고 안 내면 모은 적 없는 것과 같다. 배선을 강제한다.
# 🚨 2026-08-13 — **이 게이트가 통째로 죽어 있었다.** 대상이 market.html 이었는데 그 파일은
#   삭제됐고, 아래 `except FileNotFoundError: pass` 가 그 예외를 삼켰다. 그래서 여기 있는
#   검사 셋(배선·미기재 결측·대장 썩음)이 08-10 이후 아무것도 검사하지 않았다.
#   게이트는 초록인데 화면은 침묵했다 — MOVE 결측이 그 상태로 게시되고 있었다.
# ⚠ 없는 파일을 조용히 넘기지 않는다. 화면이 사라졌으면 그 사실이 곧 결함이다.
#   FileNotFoundError 를 통째로 삼키는 대신 대상 존재를 **먼저 확인하고 실패시킨다.**
_OUTAGE_PAGE = "regime.html"      # 결측 사유를 적는 화면. 옮기면 여기도 같이 옮길 것.
try:
    _og = json.load(io.open(os.path.join(ROOT, "data", "source_outages.json"), encoding="utf-8"))
    _oge = _og.get("outages") or {}
    _mkp = os.path.join(ROOT, _OUTAGE_PAGE)
    if not os.path.exists(_mkp):
        errors.append("소스 장애를 적기로 한 화면 %s 이 없다 — 페이지를 옮겼으면 "
                      "validate_site 의 _OUTAGE_PAGE 도 같이 옮길 것(안 옮기면 이 검사가 "
                      "조용히 죽는다. 실제로 market.html 삭제 뒤 그렇게 됐다)" % _OUTAGE_PAGE)
        _mk = ""
    else:
        _mk = io.open(_mkp, encoding="utf-8").read()
    # ⚠ 실제 **자료 접근**만 인정한다. 종전 시험에서 내가 넣은 주석의 'outages' 라는 낱말만으로
    #   통과해 버렸다 — 배선을 강제하려는 게이트가 낱말 세기로 만족하면 아무것도 안 잡는다.
    if _oge and "d.outages" not in _mk:
        errors.append("%s 이 sentiment.json 의 outages 를 안 읽는다 — 대장에 적힌 결측이 "
                      "게이트를 통과해 게시되는데 화면은 그 사유를 말하지 않는다" % _OUTAGE_PAGE)
    _sj = json.load(io.open(os.path.join(ROOT, "data", "sentiment.json"), encoding="utf-8"))
    _miss = [c.get("key") for c in (_sj.get("components") or []) if c.get("score") is None]
    _undoc = [k for k in _miss if k not in _oge]
    if _undoc:
        errors.append("시장 심리 컴포넌트 %s 가 결측인데 대장에 없다 — data/source_outages.json 에 "
                      "사유를 적거나, 일시 장애면 갱신이 막힌 상태 그대로 두어야 한다" % ", ".join(_undoc))
    # 🚨 종전에는 «checked 가 있기만 하면» 통과했다. 그래서 2026-08-05 에 적힌 날짜가
    #   08-17 까지 12일째 그대로였는데 게이트는 초록이었다 — 대장이 썩는 것을 막겠다던
    #   검사가 정작 썩음을 못 봤다. **날짜가 있느냐가 아니라 최근이냐**를 본다.
    # ⚠ 문턱 10일: refresh_sentiment 가 매 실행 대장을 자동 갱신하므로(그 파일의
    #   _touch_outage) 정상 상태면 0~1일이다. 10일이면 그 잡이 며칠째 안 돈 것이고,
    #   그러면 «장애가 아직 있는지» 자체를 아무도 확인하지 않고 있다는 뜻이다.
    _stale = [k for k, v in _oge.items() if (v.get("checked") or "") < "2000-01-01"]
    if _stale:
        errors.append("소스 장애 대장에 checked 날짜가 없는 항목 %s — 대장은 썩는다. 확인한 날을 적을 것"
                      % ", ".join(_stale))
    try:
        import datetime as _dtm
        _cut = (_dtm.date.today() - _dtm.timedelta(days=10)).isoformat()
        _old = [(k, v.get("checked")) for k, v in _oge.items()
                if (v.get("checked") or "9999") >= "2000-01-01" and v.get("checked") < _cut]
        if _old:
            errors.append("소스 장애 대장이 %d일 넘게 확인되지 않았다: %s — 장애가 아직 있는지 "
                          "아무도 안 보고 있다는 뜻이다. build/refresh_sentiment.py 가 매 실행 "
                          "자동 갱신하므로, 이 오류는 그 잡이 며칠째 안 돌았다는 신호다"
                          % (10, " · ".join("%s(checked %s)" % x for x in _old)))
    except Exception:
        pass
except FileNotFoundError:
    pass

# ── 샹들리에 흔적이 남아 있나 ─────────────────────────────────────────────
# 🚨 2026-08-05 — 화면에서 샹들리에를 전부 뺐다(칩·프리셋·차트 마름모·배지, 사용자 요청).
#   여기 있던 '화면 정의 ↔ 랩 정의 대조' 가드는 대상이 사라져 무의미해졌으므로 걷는다.
#   대신 반쪽만 되살아나는 것을 막는다 — 차트가 다시 chb 를 그리는데 판정을 안 적거나,
#   데이터에 chb 가 남았는데 아무도 안 읽는 상태(수집만 하고 안 내는 것)를 잡는다.
try:
    _sh3 = io.open(os.path.join(ROOT, "stocks.html"), encoding="utf-8").read()
    _sj3 = json.load(io.open(os.path.join(ROOT, "data", "stocks.json"), encoding="utf-8"))
    _has_data = any(x.get("chb") or x.get("chs") for x in (_sj3.get("stocks") or []))
    _has_draw = "mk.chb" in _sh3
    if _has_draw and "구별 불가" not in _sh3:
        errors.append("stocks.html 이 샹들리에 교차를 그리는데 '구별 불가' 판정을 어디에도 안 적는다 "
                      "— signal_lab 실측 t 0.95/0.44 로 귀무와 구별되지 않는 신호다")
    if _has_data and not _has_draw:
        errors.append("stocks.json 에 chb/chs 가 남아 있는데 화면이 안 읽는다 — "
                      "수집만 하고 안 내면 모은 적 없는 것과 같고, 파일만 무거워진다")
except FileNotFoundError:
    pass

# ── esc() 로 나가는 도움말 필드에 태그가 들었나 ──────────────────────────
# 🚨 2026-08-05 — stocks.html 의 도움말(HELP)은 2·3번째 필드를 esc() 로 내보낸다.
#   거기 <b> 를 쓰면 굵어지는 게 아니라 **글자 그대로 화면에 뜬다.** 실제로 swingbuy 가
#   그 상태였고(오래됨), 내가 샹들리에 항목을 같은 형식으로 베껴 쓰면서 두 개를 더 만들었다.
#   포맷이 허용하지 않는 마크업을 조용히 통과시키면 화면에서만 드러난다.
try:
    _sh2 = io.open(os.path.join(ROOT, "stocks.html"), encoding="utf-8").read()
    if "# [이름, 평문 뜻, 판정 기준]" in _sh2 or "[이름, 평문 뜻, 판정 기준]" in _sh2:
        _blk = _sh2.split("[이름, 평문 뜻, 판정 기준]", 1)[1].split("function mcOf", 1)[0]
        _tags = re.findall(r"</?(?:b|i|em|strong|span)[^>]*>", _blk)
        if _tags:
            errors.append("stocks.html 도움말(HELP) 항목에 HTML 태그 %d개 — 이 필드는 esc() 로 "
                          "나가므로 태그가 글자 그대로 노출된다: %s"
                          % (len(_tags), ", ".join(sorted(set(_tags))[:4])))
except FileNotFoundError:
    pass

# ── 랩에서 돌린 풀 후보가 풀 카드에 비치는가 ─────────────────────────────
# 🚨 2026-08-05 — A2(국면 연동 팩터 로테이션)를 사전등록하고 돌려 기각했는데, 정작
#   사용자가 보는 풀 카드(rotation.html)에는 아무 표시가 없었다. 카드는 여전히 '검정한 적
#   없는 아이디어'처럼 읽혔고, 그래서 "이건 어떻게 됐어"라는 질문이 되돌아왔다.
#   재 놓고 안 내면 모은 적 없는 것과 같다 — 랩에 있는데 풀에 없으면 여기서 막는다.
#   ⚠ 반대 방향(풀에 있는데 랩에 없음)은 정상이다. 풀은 아이디어 목록이라 대부분 미검정이다.
try:
    _pool = json.load(io.open(os.path.join(ROOT, "data", "rotation_pool.json"), encoding="utf-8"))
    _ai2 = json.load(io.open(os.path.join(ROOT, "data", "archive_index.json"), encoding="utf-8"))
    _arch_by_name = {x.get("n"): x for x in (_ai2.get("items") or [])}
    # 풀 카드가 이미 가리키고 있는 아카이브 이름들
    _linked = {(x.get("lab") or {}).get("t") for x in (_pool.get("strategies") or [])}
    # 아카이브 항목의 aka 에 풀 id(A2 등)가 적혀 있으면 그 카드는 반드시 연결돼야 한다
    _ids = {x.get("id") for x in (_pool.get("strategies") or [])}
    _orphan = []
    for _n, _rec in _arch_by_name.items():
        _tags = [str(a) for a in (_rec.get("aka") or [])] + [str(_rec.get("sid") or "")]
        _hit = [i for i in _ids if i and any(i.lower() in t.lower() for t in _tags)]
        if _hit and _n not in _linked:
            _orphan.append("%s → 풀 %s" % (_rec.get("sid"), ",".join(sorted(_hit))))
    if _orphan:
        errors.append("랩에서 판정한 전략이 풀 카드에 안 비친다 %d건: %s — rotation_pool 의 "
                      "해당 항목에 lab{v,t,why,href} 를 달 것(안 달면 카드가 '검정한 적 없는 "
                      "아이디어'로 읽힌다)" % (len(_orphan), " · ".join(_orphan)))
except FileNotFoundError:
    pass

# ── 사이클 곡선의 바닥 위치를 화면이 손으로 적고 있지 않은가 ────────────────
# 🚨 2026-08-12. 증시 곡선은 cos(2π(p − mkt_trough)) 이고 그 값(ECO_SHIFT)이 7국면 자리를
#   **같이** 정한다. 화면에 숫자를 박으면 빌더에서 바꿨을 때 자리는 움직이는데 곡선은
#   그대로여서 점이 곡선 밖에 뜬다 — 같은 종류의 사고를 이미 한 번 겪었다(Ym vs Ye · 163px).
#   이제 그리는 화면이 둘이라(regime.html + index.html 압축판) 박아 넣을 자리도 둘이다.
try:
    _shift = json.load(io.open(os.path.join(ROOT, "data", "regime_cycle.json"),
                               encoding="utf-8"))["ref"]["mkt_trough"]
    for _pg in ("regime.html", "index.html"):
        _src = io.open(os.path.join(ROOT, _pg), encoding="utf-8").read()
        # cos 인자 안에서 p 에 상수를 직접 빼는 꼴: (p-0.02) · (p - 0.02 - LEAD)
        _bad = re.findall(r"\(\s*p\s*-\s*(\d*\.\d+)", _src)
        if _bad:
            errors.append("%s 가 사이클 곡선의 바닥 위치를 손으로 적었다(%s) — "
                          "regime_cycle.json 의 ref.mkt_trough(%s)를 읽을 것. 빌더에서 "
                          "ECO_SHIFT 를 바꾸면 7국면 자리만 움직이고 곡선은 안 움직인다"
                          % (_pg, ", ".join(sorted(set(_bad))), _shift))
except FileNotFoundError:
    pass
except Exception as _e:
    errors.append("사이클 바닥 위치 검사가 예외로 죽었다 — %s" % _e)

# ── 백업 크론 표가 워크플로와 맞는가 ─────────────────────────────────────
# 🚨 2026-08-12. build/should_refresh.py 의 BACKUP_CRONS 는 **워크플로에 적힌 cron 문자열과
#   글자 단위로 같아야** 한다. 어긋나면 조용히 정반대가 된다:
#     · 표에 없는 cron → '본 슬롯'으로 판정 → 백업이 **매일 두 번** 돈다(야후 쓰로틀·저장소 팽창)
#     · 표에만 있고 워크플로에 없는 cron → 죽은 항목이 남아 다음 사람이 그걸 믿는다
#   두 파일에 같은 값을 적어 두고 "같이 바꿀 것"이라고 주석만 달아 둔 상태였다 — 그 주석은
#   지켜지지 않는다. 여기서 대조한다.
try:
    _sr = io.open(os.path.join(ROOT, "build", "should_refresh.py"), encoding="utf-8").read()
    _blk = re.search(r"BACKUP_CRONS\s*=\s*\{(.*?)\}", _sr, re.S)
    _tbl = dict(re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', _blk.group(1))) if _blk else {}
    if not _tbl:
        errors.append("build/should_refresh.py 의 BACKUP_CRONS 를 못 읽었다 — 백업 슬롯 판정이 "
                      "무엇을 보고 있는지 확인할 것")
    _wfd = os.path.join(ROOT, ".github", "workflows")
    for _cron, _wf in sorted(_tbl.items()):
        _p = os.path.join(_wfd, _wf)
        if not os.path.exists(_p):
            errors.append("BACKUP_CRONS 가 없는 워크플로를 가리킨다: %s (cron %r)" % (_wf, _cron))
            continue
        _txt = io.open(_p, encoding="utf-8").read()
        if ("'%s'" % _cron) not in _txt and ('"%s"' % _cron) not in _txt:
            errors.append("백업 크론 %r 이 %s 에 없다 — 표와 워크플로가 어긋나면 그 백업은 "
                          "'본 슬롯'으로 판정돼 매일 두 번 돈다" % (_cron, _wf))
    # 반대 방향 — gate 잡을 둔 워크플로는 백업 cron 이 반드시 표에 있어야 한다.
    for _fn in sorted(os.listdir(_wfd)):
        if not _fn.endswith(".yml"):
            continue
        _txt = io.open(os.path.join(_wfd, _fn), encoding="utf-8").read()
        if not re.search(r"^\s{2}gate:\s*$", _txt, re.M):
            continue
        _crons = re.findall(r"-\s*cron:\s*['\"]([^'\"]+)['\"]", _txt)
        if not any(c in _tbl for c in _crons):
            errors.append("%s 에 gate 잡이 있는데 그 크론(%s) 중 어느 것도 BACKUP_CRONS 에 "
                          "없다 — 관문이 늘 통과시켜 백업이 헛돈다" % (_fn, ", ".join(_crons)))
except Exception as _e:
    errors.append("백업 크론 대조가 예외로 죽었다 — %s" % _e)

# ── PIT 산출물의 커버리지 경고를 **기계가 읽는다** ────────────────────────────
# 🚨 2026-08-12 적대감사. build/pit_backtest.py 는 커버리지 미달·입력 채널 부재를 콘솔과
#   pit_strategies.json 의 coverage.warn 에 적는데, **그것을 읽는 코드가 저장소에 없었다**
#   (tech_backtest 는 t_crit·t_max 만 읽고, 화면은 접힌 <details> 한 줄뿐이다). 경고가
#   아무 데도 도달하지 않으면 없는 것과 같다 — 사람이 로그를 안 보면 그대로 배포된다.
#   여기서 커밋된 산출물을 본다. 값 자체는 건드리지 않는다: 통과/실패만 말한다.
try:
    _pj = os.path.join(ROOT, "data", "pit_strategies.json")
    if os.path.exists(_pj):
        _pd = json.load(io.open(_pj, encoding="utf-8"))
        _cv = _pd.get("coverage") or {}
        if "ok" not in _cv:
            # 옛 산출물(coverage 에 min/median 만 있던 시절)이면 검사할 것이 없다 —
            # 조용히 통과시키되 다음 재생성에서 채워진다는 사실만 남긴다.
            print("  ~ data/pit_strategies.json 에 coverage.ok 가 없다(옛 산출물) — "
                  "다음 재생성부터 이 검사가 실제로 작동한다")
        elif not _cv.get("ok"):
            # 🚨 2026-08-14 정책 변경 — PIT 창을 랩 10년 창(2016-08)에 맞춰 내렸다(사용자 결정).
            #   그 아래 구간은 커버리지가 90% 문턱을 못 넘는다(2016 84% → 2026 100%).
            #   **경고를 끄지 않는다** — 대신 (ㄱ) 연도별 커버리지가 실려 있고 (ㄴ) 최저치가
            #   여기 적은 바닥 위이면 '알고 택한 대가' 로 보고 통과시킨다. 그 아래로 더
            #   나빠지면 그때는 진짜 사고이므로 막는다.
            # ⚠ 문턱을 낮춘 것이 아니라 **두 단으로 나눈** 것이다. 90%는 그대로 '이상적' 이고,
            #   80%는 '이 창에서 감수하기로 한 바닥' 이다. 둘을 한 수로 합치면 나중에
            #   어느 쪽 근거로 통과했는지 못 읽는다.
            _COV_FLOOR = 0.80
            _by = _cv.get("by_year") or {}
            _lo = min(_by.values()) / 100.0 if _by else 0.0
            if _by and _lo >= _COV_FLOOR:
                print("  ~ PIT 커버리지 %.0f%%~%.0f%% (문턱 90%% 미만이나 바닥 %.0f%% 이상 — "
                      "10년 창을 택한 대가로 기록)"
                      % (min(_by.values()), max(_by.values()), _COV_FLOOR * 100))
            else:
                errors.append("data/pit_strategies.json 의 coverage — %s. 연도별 최저가 %.0f%% 로 "
                              "감수 바닥(%.0f%%)마저 밑돈다. 이 창에서는 PIT 이 편향을 못 걷어낸다 — "
                              "편출 종목 가격을 더 받거나 창을 올릴 것"
                              % (" · ".join(_cv.get("warn") or ["사유 미기재"]),
                                 _lo * 100, _COV_FLOOR * 100))
        # 전 구간 무보유가 **수치로** 실려 있으면(옛 코드의 결과) 그것부터 잡는다.
        _z = [s["sid"] for s in _pd.get("strategies", [])
              if abs((s.get("metrics") or {}).get("cagr") or 0) < 1e-9 and (s.get("n_days") or 0) > 0]
        if _z:
            errors.append("data/pit_strategies.json 에 CAGR 0 인 규칙 %d종(%s) — 전 구간 무보유가 "
                          "'측정값 0' 으로 실린 것이다(고저가 캐시 부재 등). 안 돈 것은 수치가 "
                          "아니라 사유로 나가야 한다" % (len(_z), ", ".join(_z)))
except Exception as _e:
    errors.append("PIT 커버리지 검사가 예외로 죽었다 — %s" % _e)

# ── 종목 랩에도 'CAGR 이 정확히 0' 검사 ────────────────────────────────────
# 🚨 같은 검사가 PIT 쪽에만 있었다. 전 구간 무보유가 '측정값 0' 으로 실리면 안 되는 것은
#   두 랩이 같다 — 대칭으로 건다. cov_short(판정 보류)인 규칙은 이미 '안 잰 것' 이라고
#   말하고 있으므로 예외로 둔다.
try:
    _td = json.load(io.open(os.path.join(ROOT, "data", "tech_strategies.json"),
                            encoding="utf-8"))
    _z2 = [s["sid"] for s in _td.get("strategies", [])
           if abs((s.get("metrics") or {}).get("cagr") or 0) < 1e-9
           and (s.get("n_days") or 0) > 0 and not s.get("cov_short")]
    if _z2:
        errors.append("data/tech_strategies.json 에 CAGR 0 인 규칙 %d종(%s) — 전 구간 무보유가 "
                      "'측정값 0' 으로 실린 것이다(입력 캐시 부재 등). 안 돈 것은 수치가 아니라 "
                      "사유로 나가야 한다(cov_short)" % (len(_z2), ", ".join(_z2)))
except Exception as _e:
    errors.append("종목 랩 CAGR 0 검사가 예외로 죽었다 — %s" % _e)

# ── `_shift(…, 음수)` 정적 금지 ────────────────────────────────────────────
# 🚨 이 저장소의 `_shift(d, days)` 는 `d - days` 다. 음수를 넘기면 **미래** 기준일이 되고,
#   asof_fund/ttm2 가 `d <= cut` 으로 고르므로 미래 재무를 집는다 — 순수 선견이다.
#   2026-08-11 에 x-debtiss 한 줄을 고치면서 "이 한 줄만 부호가 반대였다" 고 단언했는데
#   그 단언이 틀렸고, 그 문장이 재발 점검을 막아 tech_backtest 의 `_fscore` 일곱 줄과
#   probe_newrules 의 네 줄이 2026-08-18 까지 살아남았다. 사람이 조심해서 될 일이 아니다.
#   → 기계가 센다. 정말 미래를 봐야 하는 자리면 같은 줄에 `# shift-future-ok` 를 붙일 것.
# ⚠ 대상 파일을 손으로 적지 않는다 — 손으로 적은 목록은 이 저장소에서 반복해 낡았다.
try:
    import glob as _glob3
    _sf_pat = re.compile(r"_shift\s*\([^,()]*,\s*-")
    _sf_hits = []
    for _fp in sorted(_glob3.glob(os.path.join(ROOT, "build", "*.py"))):
        if os.path.basename(_fp) == "validate_site.py":
            continue
        for _ln, _line in enumerate(io.open(_fp, encoding="utf-8"), 1):
            # 주석 줄은 건너뛴다 — 이 오류를 **설명하는** 주석이 스스로 걸린다.
            if _line.lstrip().startswith("#"):
                continue
            if _sf_pat.search(_line) and "shift-future-ok" not in _line:
                _sf_hits.append("%s:%d" % (os.path.basename(_fp), _ln))
    if _sf_hits:
        errors.append("`_shift(…, 음수)` %d곳 — _shift 는 빼는 함수라 음수 인자는 1년 '뒤'를 "
                      "준다(미래 재무 = 선견). %s. 부호를 뒤집거나, 정말 미래를 봐야 하면 "
                      "그 줄에 `# shift-future-ok` 를 붙일 것"
                      % (len(_sf_hits), " · ".join(_sf_hits[:12])))
    else:
        print("  ~ _shift 음수 인자 없음(선견 정적 검사 통과)")
except Exception as _e:
    errors.append("_shift 부호 정적 검사가 예외로 죽었다 — %s" % _e)

# ── PIT 코드 판 표식이 두 파일에서 갈리지 않는가 ───────────────────────────
# 🚨 2026-08-18 신설. data/pit_strategies.json 을 굽는 워크플로가 **하나도 없어서**(전수
#   확인) 그 파일은 손으로 돌릴 때만 갱신된다. 그래서 채점 함수를 고치면 랩 열만 새 코드가
#   되고 PIT 열은 옛 코드 값인 채 남는데, 화면에서 그 차이가 '생존편향'으로 읽힌다.
#   tech_backtest 가 pit_strategies 의 code_rev 를 제 상수와 대조해 캐비엇을 띄우게 해
#   뒀는데, **두 리터럴이 갈리면 그 장치 자체가 조용히 죽는다** — 한쪽만 올리면 캐비엇이
#   영영 뜨거나 영영 안 뜬다. 그래서 여기서 두 상수를 대조한다.
try:
    _pcr = {}
    for _f, _k in ((os.path.join(ROOT, "build", "tech_backtest.py"), "PIT_CODE_REV"),
                   (os.path.join(ROOT, "build", "pit_backtest.py"), "CODE_REV")):
        _m = re.search(r"^%s\s*=\s*[\"']([^\"']+)[\"']" % _k,
                       io.open(_f, encoding="utf-8").read(), re.M)
        _pcr[_k] = _m.group(1) if _m else None
    if None in _pcr.values():
        errors.append("PIT 코드 판 상수를 못 찾았다 — %s. tech_backtest.PIT_CODE_REV 와 "
                      "pit_backtest.CODE_REV 는 둘 다 모듈 최상단 리터럴이어야 한다"
                      % _pcr)
    elif _pcr["PIT_CODE_REV"] != _pcr["CODE_REV"]:
        errors.append("PIT 코드 판이 갈렸다 — tech_backtest.PIT_CODE_REV=%s vs "
                      "pit_backtest.CODE_REV=%s. 한쪽만 올리면 'PIT 열이 옛 코드' 캐비엇이 "
                      "영영 뜨거나 영영 안 뜬다 — 둘을 같이 올릴 것"
                      % (_pcr["PIT_CODE_REV"], _pcr["CODE_REV"]))
    else:
        _pj_rev = None
        try:
            _pj_rev = json.load(io.open(os.path.join(ROOT, "data", "pit_strategies.json"),
                                        encoding="utf-8")).get("code_rev")
        except Exception:
            pass
        print("  ~ PIT 코드 판 %s (산출물 %s%s)"
              % (_pcr["CODE_REV"], _pj_rev or "표시 없음",
                 "" if _pj_rev == _pcr["CODE_REV"] else " — 캐비엇 표시 중"))
except Exception as _e:
    errors.append("PIT 코드 판 대조가 예외로 죽었다 — %s" % _e)

# ── 백테스트 길이 상한이 네 파일에서 갈리지 않는가 ─────────────────────────
# 🚨 사용자 결정(2026-08-13)으로 전 전략 백테스트를 최대 10년으로 자르는데, 격자가
#   거래일/월말로 갈려 **상수를 한 곳에 못 모았다**. 네 곳이 같은 값을 따로 들고 있고,
#   한쪽만 고치면 한 화면에 10년짜리와 12년짜리가 나란히 놓인다 — 눈으로는 안 보인다.
#   그래서 ① 상수가 서로 같은지 ② 산출물이 실제로 그 상한을 지켰는지 둘 다 본다.
#   ②가 본체다. 상수를 우회해도 잡힌다.
try:
    import re as _re
    _CAPS = [("build/tech_backtest.py",   r"^MAX_YEARS\s*=\s*(\d+)",        1),
             ("build/asset_backtest.py",  r"^MAX_YEARS\s*=\s*(\d+)",        1),
             ("build/guru_clone.py",      r"^\s+MAX_YEARS\s*=\s*(\d+)",    1),
             ("build/strategy_metrics.py", r"^MAX_MONTHS\s*=\s*(\d+)\s*\*\s*12", 1)]
    _got = {}
    for _f, _pat, _mul in _CAPS:
        _m = _re.search(_pat, rd(_f), _re.M)
        if not _m:
            errors.append("%s 에서 백테스트 길이 상한 상수를 못 찾았다 — 이름이 바뀌었으면 "
                          "이 검사도 같이 고칠 것(안 그러면 상한이 조용히 풀린다)" % _f)
        else:
            _got[_f] = int(_m.group(1)) * _mul
    _cap_ok = True
    if len(set(_got.values())) > 1:
        _cap_ok = False
        errors.append("백테스트 길이 상한이 파일마다 다르다 — %s. 네 곳이 같은 값을 따로 들고 "
                      "있으므로 바꿀 때는 넷 다 바꿔야 한다(격자가 거래일/월말로 갈려 한 곳에 "
                      "못 모았다)" % " · ".join("%s=%d년" % (k.split("/")[-1], v)
                                                for k, v in sorted(_got.items())))
    _cap = max(_got.values()) if _got else 10
    # ② 산출물 실측 — 게시 목록에서 상한을 넘는 전략이 있으면 상수와 무관하게 잡는다.
    #    한 달치 여유를 둔다(월말 격자·거래일 반올림으로 10.0 을 살짝 넘길 수 있다).
    _si = json.loads(rd("data/strategy_index.json"))
    _over = []
    for _x in _si.get("items") or []:
        _s, _e = _x.get("start"), _x.get("end")
        if not (_s and _e and len(_s) >= 7 and len(_e) >= 7):
            continue
        _y = (int(_e[:4]) * 12 + int(_e[5:7]) - int(_s[:4]) * 12 - int(_s[5:7])) / 12.0
        if _y > _cap + 0.25:
            _over.append("%s %.1f년" % ((_x.get("name") or _x.get("sid") or "?")[:28], _y))
    if _over:
        _cap_ok = False
        errors.append("백테스트 구간이 상한(%d년)을 넘는 전략 %d종 — %s. 창이 갈리면 카드끼리 "
                      "세로로 비교할 수 없다. 해당 엔진에 상한이 안 걸린 경로가 있다는 뜻이다"
                      % (_cap, len(_over), " · ".join(_over[:6])))
    if _cap_ok and len(_got) == len(_CAPS):
        print("  ~ 백테스트 길이 상한 검사 통과(%d년 · 상수 %d곳 일치 · 게시 %d종 전부 이내)"
              % (_cap, len(_got), len(_si.get("items") or [])))
except Exception as _e:
    errors.append("백테스트 길이 상한 검사가 예외로 죽었다 — %s" % _e)

# ── 화면의 시점정확 수치가 **원천과 같은가** ──────────────────────────────
# 🚨 2026-08-14 실측 3종(x-sur 13.90 vs 11.85 · x-volratio 10.41 vs 9.03 · x-agrow).
#   경로가 둘이라 생긴다: pit_strategies.json → tech_backtest 가 병합 → tech_strategies.json
#   → strategy_index.json(화면). 중간의 tech 를 다시 안 구우면 화면은 **옛 PIT** 을 들고
#   있는데, 곡선(strategy_charts)은 pit_strategies 에서 곧장 오므로 최신이다.
#   그러면 한 카드 안에서 **머리 숫자와 그 밑 곡선이 다른 값**을 말한다.
# ⚠ 이 어긋남은 둘 다 '그럴듯한 수' 라 눈으로 안 잡힌다. 두 파일을 직접 맞대야 보인다.
try:
    _pj = json.loads(rd("data/pit_strategies.json"))
    _psrc = {r["sid"]: r for r in (_pj.get("strategies") or [])}
    _ix3 = json.loads(rd("data/strategy_index.json"))
    _drift = []
    for _x in _ix3.get("items") or []:
        _p = _x.get("pit")
        if not _p or not str(_x.get("sid", "")).startswith("t-"):
            continue
        _q = _psrc.get(_x["sid"][2:])
        if not _q:
            continue
        _a, _b = _p.get("cagr"), (_q.get("metrics") or {}).get("cagr")
        if _a is not None and _b is not None and abs(_a - _b) > 0.01:
            _drift.append("%s 화면 %.2f vs 원천 %.2f" % (_x["sid"], _a, _b))
    if _drift:
        errors.append(
            "시점정확 수치가 원천과 어긋난 전략 %d종 — %s. tech_strategies.json 이 옛 "
            "pit_strategies.json 을 병합한 채로 남아 있다는 뜻이다(곡선은 원천에서 곧장 오므로 "
            "한 카드 안에서 머리 숫자와 곡선이 갈린다). python build/tech_backtest.py 를 다시 "
            "돌린 뒤 strategy_index·strategy_charts 를 같이 구울 것"
            % (len(_drift), " · ".join(_drift[:5])))
    else:
        print("  ~ 시점정확 원천 대조 통과(%d종 · 화면 = pit_strategies.json)"
              % sum(1 for _x in (_ix3.get("items") or []) if _x.get("pit")))
except FileNotFoundError:
    pass
except Exception as _e:
    errors.append("시점정확 원천 대조가 예외로 죽었다 — %s" % _e)

# ── 성과 기준일이 **전월말**인가 ────────────────────────────────────────
# 🚨 2026-08-14 사용자 지시 — "성과는 전월말까지로 하고 월 1회 자동 업데이트".
#   백테스트가 격자를 전월말에서 끊는다(tech_backtest.asof_cut). 그런데 그 절단은 빌더
#   **다섯 곳**(tech·pit·asset·guru·pairs)에 각각 배선돼 있어서, 한 곳만 안 자르면 그
#   랩의 전략만 며칠 더 긴 창을 갖고 같은 표에 놓인다. 그건 숫자로만 보이고 아무도 안 막는다.
# ⚠ 자료가 아직 그 달을 다 못 채운 경우(수집 지연)는 **넘긴다** — 그건 기준이 틀린 것이
#   아니라 격자가 밀린 것이고, 그쪽은 asof/신선도 검사가 말한다. 여기서 잡는 것은 반대
#   방향, 즉 **현재 달까지 재 버린** 경우 하나다.
try:
    import datetime as _dt2
    _now_m = _dt2.date.today().strftime("%Y-%m")
    _si2 = json.loads(rd("data/strategy_index.json"))
    _late = []
    for _x in _si2.get("items") or []:
        _e = _x.get("end")
        if _e and len(_e) >= 7 and _e[:7] >= _now_m:
            _late.append("%s %s" % ((_x.get("name") or _x.get("sid") or "?")[:26], _e))
    if _late:
        errors.append(
            "성과 구간이 **이번 달(%s)까지** 걸친 전략 %d종 — %s. 기준일은 전월말이어야 "
            "한다(사용자 지시 2026-08-14). 절단이 빌더 다섯 곳에 각각 배선돼 있으므로 "
            "어느 하나가 asof_cut 을 안 부르고 있다는 뜻이다"
            % (_now_m, len(_late), " · ".join(_late[:6])))
    else:
        _ends = sorted({(_x.get("end") or "")[:7] for _x in (_si2.get("items") or [])
                        if _x.get("end")})
        print("  ~ 성과 기준일 검사 통과(전월말 · 게시 %d종의 종료월 %s)"
              % (len(_si2.get("items") or []),
                 (_ends[-1] if len(_ends) == 1 else "%s~%s" % (_ends[0], _ends[-1]))))
except Exception as _e:
    errors.append("성과 기준일 검사가 예외로 죽었다 — %s" % _e)

# ── 「샤프 0.5 미만은 남기지 않는다」 — **사용자 결정** 대조 ──────────────────
# 🚨 이것은 랩의 문턱이 **아니다.** 이 랩은 2026-08-13·16 에 t 문턱과 다중검정 임계를
#   폐지했고 게시 기준을 두지 않는다. 여기서 하는 일은 «사용자가 두 번 내린 결정»
#   (2026-08-19 일괄 17종 · 2026-08-23 테일 헤지 Long-Vol)에 걸리는 종이 목록에
#   들어왔는지 알리는 것뿐이다. 규칙을 판정하지 않고, 자동으로 자르지도 않는다.
# ⚠ 이 검사가 왜 필요했나 — 2026-08-23 에 숨겨 뒀던 테일 헤지 둘을 되살리면서 그 잣대를
#   다시 대지 않았다. 한 종(샤프 0.111)이 그대로 화면에 올라갔고 **사용자가 잡았다.**
#   숨김을 푸는 것은 새로 싣는 것과 같은데, 그때 통과해야 할 결정을 안 본 것이다.
#   사람이 기억해야만 지켜지는 규약은 언젠가 깨진다 — 그래서 여기 못 박는다.
# ⚠ 잣대를 바꾸려면 이 상수만 고치는 것이 아니라 build/tested_not_published.json 의
#   삭제 기록도 같이 손봐야 한다(무엇을 왜 뺐는지가 그 목록에 있다).
_SH_CUT = 0.5
try:
    _si4 = json.loads(rd("data/strategy_index.json"))
    _bad4 = []
    for _x in _si4.get("items") or []:
        _sh = (_x.get("metrics") or {}).get("sharpe")
        if isinstance(_sh, (int, float)) and _sh < _SH_CUT:
            _bad4.append("%s %s(샤프 %.3f)"
                         % (_x.get("sid"), (_x.get("name") or "")[:24], _sh))
    if _bad4:
        errors.append(
            "샤프 %.1f 미만인데 목록에 남아 있는 전략 %d종 — %s. 이것은 랩의 문턱이 "
            "아니라 **사용자 결정**(2026-08-19 · 08-23)이다. 빼려면 "
            "build/strategy_index.py 의 HIDE_SIDS 에 sid 를 넣고 "
            "build/tested_not_published.json 에 사유를 함께 적을 것 — 기록을 지우지 "
            "않는 것이 이 랩의 규약이다"
            % (_SH_CUT, len(_bad4), " · ".join(_bad4[:6])))
    else:
        _shs = sorted((_x.get("metrics") or {}).get("sharpe") for _x in (_si4.get("items") or [])
                      if isinstance((_x.get("metrics") or {}).get("sharpe"), (int, float)))
        print("  ~ 샤프 하한 대조 통과(사용자 결정 %.1f · 게시 %d종 최저 %.3f)"
              % (_SH_CUT, len(_si4.get("items") or []), _shs[0] if _shs else float("nan")))
except Exception as _e:
    errors.append("샤프 하한 대조가 예외로 죽었다 — %s" % _e)

# ── 「연 회전율 10배 초과는 남기지 않는다」 — **사용자 결정** 대조 ─────────────
# 🚨 랩의 문턱이 아니다. 2026-08-24 사용자 결정이고, 바깥 잣대가 근거다 — 국내 공모펀드
#   평균 매매회전율 약 2.4배(금융투자협회 2023-06 · 47개 운용사 243.80%), 국내 최고
#   운용사 약 20배, 국제적으로는 2배만 넘어도 투기적으로 본다.
# 🚨 이 잣대는 성적이 아니라 **행동**을 자른다. 실제로 걸린 21종 중 여럿은 비용 후에도
#   샤프 0.9 대였고(이동평균 합의 0.984 · 주간 반전 0.932), 그래서 이 삭제는 남은 목록을
#   **더 나쁘게** 만들었다(중앙 0.839 → 0.811). 보통의 생존 선택과 반대다.
# ⚠ 회전율이 없는 규칙(자산 랩 일부)은 대조 대상이 아니다 — «없음» 을 «작음» 으로 읽지 않는다.
_TURN_CAP = 10.0
try:
    _si5 = json.loads(rd("data/strategy_index.json"))
    _bad5 = []
    for _x in _si5.get("items") or []:
        _tv = _x.get("turnover")
        if isinstance(_tv, (int, float)) and _tv > _TURN_CAP:
            _bad5.append("%s %s(연 %.1f회)"
                         % (_x.get("sid"), (_x.get("name") or "")[:22], _tv))
    if _bad5:
        errors.append(
            "연 회전율 %.0f배 초과인데 목록에 남아 있는 전략 %d종 — %s. 이것은 랩의 문턱이 "
            "아니라 **사용자 결정**(2026-08-24)이다. 빼려면 build/strategy_index.py 의 "
            "HIDE_SIDS 에 sid 를 넣고 build/tested_not_published.json 에 사유를 함께 적을 것"
            % (_TURN_CAP, len(_bad5), " · ".join(_bad5[:6])))
    else:
        _tv2 = sorted((_x.get("turnover") for _x in (_si5.get("items") or [])
                       if isinstance(_x.get("turnover"), (int, float))), reverse=True)
        print("  ~ 회전율 상한 대조 통과(사용자 결정 %.0f배 · 게시 %d종 최고 %.1f회)"
              % (_TURN_CAP, len(_si5.get("items") or []), _tv2[0] if _tv2 else 0.0))
except Exception as _e:
    errors.append("회전율 상한 대조가 예외로 죽었다 — %s" % _e)

# ── 1일 분봉 판에 **평평한 꼬리**가 있는가 ──────────────────────────────────
# 🚨 2026-08-23 사용자 지적 «1일 스타일 수익률 차트 제대로 안 나오는 게 있네».
#   원인은 봉을 시각이 아니라 **위치**로 읽은 것이었다. 거래가 뜸한 ETF 는 거래 없는
#   분의 봉이 아예 없어서(실측 SDY 207봉/390분), 207개가 앞쪽에 몰려 그려지고 뒤
#   183분이 마지막 값 되풀이로 **평평한 직선**이 됐다. 화면은 「11시부터 마감까지 한
#   번도 안 움직였다」고 말하는데 사실이 아니다.
# ⚠ 이 검사가 없으면 다음에 종목이 늘거나 유동성이 낮은 ETF 가 들어올 때 조용히 재발한다.
#   자료를 보고 «말이 되나» 를 묻는 검사라, 배선 검사로는 못 잡는다.
# ⚠ 진짜로 안 움직인 구간도 있을 수 있으므로 문턱을 넉넉히 둔다 — 격자의 15% 를 넘는
#   연속 동일값만 잡는다(SDY 사고는 47% 였다).
try:
    _hp = json.loads(rd("data/home_perf.json"))
    _d1 = (_hp.get("series") or {}).get("1D") or {}
    _npt = len(_d1.get("dates") or [])
    _flat = []
    if _npt >= 20:
        for _pane in ("ix", "sec", "sty", "ind"):
            for _nm, _v in (_d1.get(_pane) or {}).items():
                if not _v or len(_v) != _npt:
                    continue
                _run = 0
                for _i in range(len(_v) - 1, 0, -1):
                    if _v[_i] is not None and _v[_i] == _v[_i - 1]:
                        _run += 1
                    else:
                        break
                if _run > _npt * 0.15:
                    _flat.append("%s/%s(끝 %d칸 = %.0f%%)"
                                 % (_pane, _nm, _run, 100.0 * _run / _npt))
    if _flat:
        errors.append(
            "1일 분봉 판에 **평평한 꼬리**가 있는 줄 %d개: %s — 봉을 시각(tm)이 아니라 "
            "위치로 읽으면 거래가 뜸한 종목이 이렇게 된다. build/home_perf._at_minutes "
            "가 tm 으로 맞추고 있는지 확인할 것" % (len(_flat), " · ".join(_flat[:6])))
    elif _npt:
        print("  ~ 1일 분봉 평평꼬리 검사 통과(격자 %d칸 · 네 판 전부)" % _npt)
except Exception as _e:
    errors.append("1일 분봉 평평꼬리 검사가 예외로 죽었다 — %s" % _e)

# ── `%%` 가 산출물에 남았는가 — 전 파일 훑기 ────────────────────────────
# 🚨 2026-08-14. CI 가 signal_lab 의 마크다운 `**` 를 잡았고, 그 옆에서 `상위 5%%` 를
#   발견했다. `%%` 는 파이썬 % 서식의 이스케이프인데 그 문자열에 % 연산자가 안 붙으면
#   **화면에 `5%%` 로 그대로 찍힌다.** 기존 누출 검사는 파일 넷(signal_lab·tech·pairs·
#   asset)의 지정 필드만 봐서, 같은 병이 다른 파일·다른 필드에 6곳 더 살아 있었다
#   (x-updown·x-currat·x-custconc·x-ratebeta·x-aci 의 why 와 자산 랩 규약).
#   → 파일을 고르지 않고 **data/ 전부**를 훑는다. `%%` 는 어떤 렌더러도 되돌리지 않으므로
#     의도된 표기일 수가 없다(마크다운 `**` 와 달리 예외가 없다).
# ⚠ _ 로 시작하는 로컬 캐시는 화면에 안 나가므로 제외한다.
try:
    _pcthits = []

    def _pctwalk(o, path, fn):
        if isinstance(o, str):
            if "%%" in o:
                _pcthits.append((fn, path, o[:60]))
        elif isinstance(o, dict):
            for _k, _v in o.items():
                _pctwalk(_v, path + "." + str(_k), fn)
        elif isinstance(o, list):
            for _i, _v in enumerate(o):
                _pctwalk(_v, path + "[%d]" % _i, fn)

    for _fn in sorted(os.listdir(os.path.join(ROOT, "data"))):
        if not _fn.endswith(".json") or _fn.startswith("_"):
            continue
        try:
            _pctwalk(json.load(io.open(os.path.join(ROOT, "data", _fn), encoding="utf-8")), "", _fn)
        except Exception:
            continue
    if _pcthits:
        _u = sorted({h[2] for h in _pcthits})
        errors.append("산출물에 '%%%%' 가 남았다 %d곳(고유 문구 %d개) — %s. 파이썬 %% 서식의 "
                      "이스케이프인데 그 문자열에 %% 연산자가 안 붙어 화면에 그대로 찍힌다. "
                      "빌더 소스에서 고칠 것"
                      % (len(_pcthits), len(_u),
                         " / ".join("%s %s" % (h[0], h[1][:26]) for h in _pcthits[:4])))
    else:
        print("  ~ '%%' 누출 검사 통과(data/ 전 파일)")
except Exception as _e:
    errors.append("'%%' 누출 검사가 예외로 죽었다 — %s" % _e)

# ── 가격 격자에 구멍이 있는가 ─────────────────────────────────────────
# 🚨 2026-08-14 실측. data/sd/*.json 의 pxd 에서 세 날이 통째로 비어 있었다 —
#   2026-07-21·22 각 192종 / 2026-07-31 113종 (전체 518종 중). 17.6년 격자에서 그 셋뿐이고
#   전후 거래일은 멀쩡했다. yfinance 를 개별로 받으면 그 봉이 **있다** — 원천 공백이
#   아니라 120종 배치 다운로드가 조용히 행을 빠뜨린 것이다.
#   그냥 두면 안 되는 이유: **2026-07-31 은 월말이자 주간 리밸런스 날**이라 그날 전
#   횡단면 전략이 518종이 아니라 405종에서 골랐다. 후보 게이트(30종)는 한참 위라
#   아무 경고도 안 났다 — 성과가 조용히 78% 유니버스에서 나왔다.
#   → 날짜별로 '상장 후 결측' 을 세어 임계를 넘으면 막는다. 고치는 법은
#     build/patch_px_holes.py (None 인 칸만 채운다).
# ⚠ 상장 전 None 은 결측이 아니다(아직 없는 것이다). 첫 유효값 뒤의 None 만 센다.
try:
    _st = json.loads(rd("data/stocks.json"))
    _dts = _st.get("pxd_dates") or []
    _sdd = os.path.join(ROOT, "data", "sd")
    if _dts and os.path.isdir(_sdd):
        _n = len(_dts)
        _hole = [0] * _n
        for _f in os.listdir(_sdd):
            if not _f.endswith(".json"):
                continue
            try:
                _px = (json.load(io.open(os.path.join(_sdd, _f), encoding="utf-8"))
                       or {}).get("pxd") or []
            except Exception:
                continue
            _seen = False
            for _i in range(min(_n, len(_px))):
                if _px[_i] is not None:
                    _seen = True
                elif _seen:
                    _hole[_i] += 1
        # 임계 20종 — 정상일의 상장 후 결측은 실측으로 0~1종이다(거래정지·상폐 개별 건).
        _bad = [(_dts[_i], _hole[_i]) for _i in range(_n) if _hole[_i] >= 20]
        if _bad:
            errors.append("가격 격자에 구멍 %d일 — %s. 한 날짜에 20종 넘게 비는 것은 개별 "
                          "거래정지가 아니라 **수집 실패**다(정상일은 0~1종). 그 날이 리밸런스 "
                          "날이면 전 전략이 좁아진 유니버스에서 고르는데 후보 게이트는 그 정도로 "
                          "안 걸린다. build/patch_px_holes.py 로 None 인 칸만 채울 것"
                          % (len(_bad), " · ".join("%s %d종" % b for b in _bad[:5])))
        else:
            print("  ~ 가격 격자 구멍 검사 통과(%d거래일 · 한 날 최대 결측 %d종)"
                  % (_n, max(_hole) if _hole else 0))
        # 🚨 2026-09-03 — **위 검사는 격자 «안»의 None 만 센다. 격자에서 통째로 빠진 날은 못 본다.**
        #   실측: 랩 격자에 2026-08-28(금)이 없다. 518종 전부 길이가 정상이라 위 검사는 통과한다.
        #   원인은 refresh_stocks.py 의 `daily = daily[_cov >= 0.5]` — 그날 커버리지가 50% 아래라
        #   「유령 거래일」로 떨어졌다. **그 관문은 옳다**(날짜 축이 어긋난 날을 막는다).
        #   문제는 **재실행으로 안 낫는다**는 것이다. 실측(2026-09-03):
        #     · 개별 조회는 그 날이 있다 — yf.Ticker("AAPL").history() 에 2026-08-28 존재
        #     · **배치 조회는 15종 중 6종(40%)만 준다** → 매 실행 다시 50% 관문에 걸린다
        #     즉 원천의 배치 종단점이 그 날을 지속적으로 덜 준다. period="max" 로 매번
        #     전체를 받아도 같은 자리에서 같은 이유로 다시 떨어진다.
        #   ⚠ 누적수익은 안 틀린다(08-27→08-31 이 이틀치 수익을 한 칸에 담는다). 틀어지는 것은
        #     **거래일 수와 리밸 정렬**이고, 그것을 아무도 안 보고 있었다.
        #   ⚠ **오류가 아니라 경고로 낸다.** 러너가 고칠 수 없는 것을 오류로 내면 예정 검증이
        #     매일 빨갛고, 그러면 사람이 경보 자체를 안 믿게 된다(이 저장소가 style_pit 에서
        #     이미 택한 규약). 고치려면 그 날짜만 **종목별로** 받아 격자에 끼워 넣어야 하는데
        #     build/patch_px_holes.py 는 «격자 안의 None 칸» 전용이라 날짜 추가는 못 한다.
        #   대조 상대는 벤치 격자다 — data/bench_px.json 은 같은 시장의 지수라 거래일이 같아야 한다.
        #   ⚠ 이 파일을 validate_site 가 그동안 한 번도 안 읽었다(grep 0건).
        try:
            _bpx = json.load(io.open(os.path.join(ROOT, "data", "bench_px.json"), encoding="utf-8"))
            _bdt = _bpx.get("dates") or []
            _lset = set(_dts)
            _miss = [_d for _d in _bdt if _dts and _dts[0] <= _d <= _dts[-1] and _d not in _lset]
            if _miss:
                print("  ~ 🚨 랩 가격 격자에서 거래일 %d일이 통째로 빠졌다: %s — 벤치 격자에는 "
                      "있는 날이다. refresh_stocks 의 «유령 거래일» 관문(_cov >= 0.5)이 떨궜고, "
                      "원천 배치 조회가 그 날을 지속적으로 덜 줘서 **재실행으로 안 낫는다**. "
                      "누적수익은 맞고 거래일 수·리밸 정렬이 어긋난다. 고치려면 그 날짜를 "
                      "종목별로 받아 격자에 끼워 넣어야 한다(전용 도구 없음)"
                      % (len(_miss), " · ".join(_miss[:5])))
            else:
                print("  ~ 격자 거래일 대조 통과(랩 %d일 = 벤치 격자와 같은 날짜 집합)" % len(_dts))
        except FileNotFoundError:
            pass
        # 🚨 산출물이 **지금 입력으로 구워진 것인가.** index_ledger 의 커버리지는 빌드 때
        #   세어 파일에 박는 값이라(화면이 11MB 가격 캐시를 읽지 않게 하려고 그렇게 뒀다)
        #   원본이 바뀌어도 표는 옛 수를 그대로 들고 있다 — 조용히 틀린다.
        #   2026-08-14 에 실제로 그랬다: 가격 구멍 497칸을 메우고 이 파일을 안 구워
        #   7월이 77.7% 인 채로 남았고, 사용자가 화면을 보고 물어서야 알았다.
        #   → 원장이 실어 둔 입력 지문을 여기서 **다시 세어** 대조한다.
        # ⚠ 같은 유형이 오늘만 두 번이다(소스 고치고 signal_lab.json 안 구움 · 가격 고치고
        #   여기). 산출물에 미리 박는 수치는 전부 이 검사가 필요한 자리다.
        _lg = json.loads(rd("data/index_ledger.json"))
        _fp = _lg.get("src_fp")
        if not _fp:
            print("  ~ index_ledger 에 src_fp 가 없다(옛 산출물) — 다음 재생성부터 대조한다")
        else:
            _now = {"grid_days": _n, "px_nulls": sum(_hole),
                    "hist_months": len(json.loads(rd("data/index_history.json")).get("months") or {}),
                    "hist_as_of": json.loads(rd("data/index_history.json")).get("as_of")}
            _dif = [k for k in _now if _fp.get(k) != _now[k]]
            if _dif:
                errors.append("data/index_ledger.json 이 **지금 입력으로 구워진 것이 아니다** — "
                              "%s. 원장의 커버리지는 빌드 때 세어 박는 값이라 원본이 바뀌면 "
                              "표가 조용히 옛 수를 들고 있다. python build/index_ledger.py 를 "
                              "다시 돌릴 것"
                              % " · ".join("%s 산출물 %s ≠ 실측 %s" % (k, _fp.get(k), _now[k])
                                           for k in _dif))
            else:
                print("  ~ index_ledger 입력 지문 일치(격자 %d일 · 결측 %d · 이력 %d개월)"
                      % (_now["grid_days"], _now["px_nulls"], _now["hist_months"]))
except Exception as _e:
    errors.append("가격 격자 구멍 검사가 예외로 죽었다 — %s" % _e)

# ── 갱신 피드가 사람 작업을 담고 있나 ────────────────────────────────
# 🚨 2026-08-16 점검에서 찾았다. 2026-08-12~08-16 닷새에 비-chore 커밋이 122건인데
#   data/updates.json 의 사람 작업 기록은 **0건**이었다(자동 잡만 자기 기록을 남겼다).
#   그래서 갱신 기록 화면이 «마지막 변경 2026-08-11» 로 보였다 — 그 화면이 막겠다고
#   적어 둔 상태(«데이터는 매일 도는데 사이트는 몇 달째 그대로»)의 정확한 거울상이다.
# 원인은 build/log_update.py 가 **사람이 기억해서 불러야** 하는 도구라는 것이다. 같은 일이
#   2026-07-23~25 에도 있었다(log_update.py 머리말). 기억에 기대는 고리는 또 끊어진다.
#   → 여기서 세어 막고, build/log_from_git.py 로 채운다.
# ⚠ CI 체크아웃이 얕으면(fetch-depth=1) git log 가 비어 이 검사가 **조용히 통과**한다.
#   그건 통과가 아니라 미검증이므로 그렇게 찍는다.
try:
    import subprocess as _sp
    _gl = _sp.run(["git", "log", "--since", "14 days ago", "--pretty=%ad|%s",
                   "--date=format-local:%Y-%m-%d"],
                  cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    _lines = [l for l in (_gl.stdout or "").splitlines() if "|" in l]
    _human = [l.split("|", 1) for l in _lines
              if not l.split("|", 1)[1].startswith(("chore(", "Merge ", "merge:"))]
    if _gl.returncode != 0 or len(_lines) < 2:
        print("  ~ 갱신 피드 대조 건너뜀 — git 이력을 못 읽었다(얕은 체크아웃?). "
              "통과가 아니라 미검증이다")
    elif not _human:
        print("  ~ 갱신 피드 대조: 최근 14일 사람 커밋이 없다 — 셀 것이 없다")
    else:
        # 🚨 커밋 1:1 을 요구하지 않는다. 이 피드는 원래 **추린 기록**이다(2026-08-11 은
        #   커밋 40여 건에 항목 21건). 1:1 로 세면 늘 실패해서 아무도 안 보게 된다.
        #   잡는 것은 «일한 날인데 한 줄도 없는 날» 이다 — 실제로 난 사고가 그 모양이었다.
        _cnt = {}
        for d, t in _human:
            _cnt[d] = _cnt.get(d, 0) + 1
        _ev = json.loads(rd("data/updates.json")).get("events") or []
        _days = {e.get("dt") for e in _ev}
        _blank = sorted(d for d, n in _cnt.items() if n >= 3 and d not in _days)
        if _blank:
            errors.append("갱신 피드에 **통째로 빠진 날 %d일**(%s) — 그날 사람 커밋이 각각 "
                          "3건 이상인데 기록이 한 줄도 없다. 자동 잡만 남으면 화면이 "
                          "«사이트가 멈췄다»고 말한다. python build/log_from_git.py --since %s "
                          "로 채우거나 build/log_update.py 로 그날치를 적을 것"
                          % (len(_blank), " · ".join(_blank[:6]), _blank[0]))
        else:
            print("  ~ 갱신 피드 대조 통과(최근 14일 사람 커밋 %d건 · 기록 없는 날 0일)"
                  % len(_human))
except Exception as _e:
    print("  ~ 갱신 피드 대조가 예외로 죽었다 — %s (미검증)" % str(_e)[:80])

# ── 벤더가 소급 안 한 분할이 남아 있나 ──────────────────────────────────
# 🚨 2026-08-19 — MNST 가 2026-08-11 에 2:1 분할했는데 야후가 **가격 이력을 소급
#   조정하지 않았다**(분할 이력에는 있다). 랩은 받은 대로 실었고, 화면과 모든 전략이
#   가짜 −50% 하루를 보았다. 사용자가 차트를 보고 찾았다.
# ⚠ 일간 변동 검사로는 절대 못 잡는다 — 분할일이 결측이라 «어제 대비 오늘» 이 끊긴다.
#   그래서 **결측을 건너뛴 인접 관측**으로 본다. build/split_fix.py 와 같은 규칙이다.
try:
    _sp = (json.loads(rd("data/splits.json")) or {}).get("co") or {}
    _stk2 = json.loads(rd("data/stocks.json"))
    _dts2 = _stk2.get("pxd_dates") or []
    _di2 = {d: k for k, d in enumerate(_dts2)}
    _n2 = len(_dts2)
    _sdd2 = os.path.join(ROOT, "data", "sd")
    _raw = []
    for _t2, _evs in _sp.items():
        _p2 = os.path.join(_sdd2, "%s.json" % _t2)
        if not os.path.exists(_p2):
            continue
        _px2 = (json.load(io.open(_p2, encoding="utf-8")) or {}).get("pxd") or []
        _px2 = _px2 + [None] * (_n2 - len(_px2))
        for _d0, _r0 in _evs:
            _i2 = _di2.get(_d0)
            if _i2 is None or not _r0 or _r0 <= 1:
                continue
            _lo = next((_px2[k] for k in range(_i2 - 1, max(-1, _i2 - 7), -1)
                        if k >= 0 and _px2[k] is not None), None)
            _hi = next((_px2[k] for k in range(_i2, min(_n2, _i2 + 6))
                        if _px2[k] is not None), None)
            if not _lo or not _hi:
                continue
            if abs(_hi / _lo - 1.0 / _r0) <= 0.12 / _r0:
                _raw.append("%s %s %.0f:1" % (_t2, _d0, _r0))
    if _raw:
        errors.append(
            "벤더가 **소급 적용하지 않은 분할**이 가격 계열에 남아 있다 — %s. 그대로 두면 "
            "그 날 하루가 가짜 −%d%% 로 잡히고 화면·전략이 전부 그것을 본다. "
            "python build/split_fix.py 로 고칠 것" % (" · ".join(_raw[:5]), 50))
    else:
        print("  ~ 분할 소급 검사 통과(분할 이력 %d종 · 소급 안 된 것 0건)" % len(_sp))
except Exception as _e:
    print("  ~ 분할 소급 검사가 예외로 죽었다 — %s (미검증)" % str(_e)[:80])

# ── 한 종목이 며칠째 비었나 ──────────────────────────────────────────────
# 🚨 2026-08-19 — EQR(현역 S&P 500 편입 종목)이 data/sd/EQR.json 에서 **22거래일째**
#   비어 있었는데 아무 검사도 안 걸렸다. 격자 구멍 검사는 «하루에 몇 종이 비었나» 만 보고
#   (문턱 20종) «한 종목이 며칠째 비었나» 는 안 본다. 그 사이 이 랩의 전 횡단면 전략이
#   그 종목 없이 돌았고, 화면도 조용했다.
#   ⚠ 두 검사는 서로를 대신하지 못한다 — 하나는 «넓고 얕은» 결손, 하나는 «좁고 깊은» 결손이다.
try:
    _sdd = os.path.join(ROOT, "data", "sd")
    _stk = json.loads(rd("data/stocks.json"))
    _n = len(_stk.get("pxd_dates") or [])
    _uni = {x.get("t") for x in (_stk.get("stocks") or []) if x.get("t")}
    _dark = []
    for _t in sorted(_uni):
        _p = os.path.join(_sdd, "%s.json" % _t)
        if not os.path.exists(_p):
            continue
        _o = json.load(io.open(_p, encoding="utf-8"))
        _px = _o.get("pxd") or []
        _rep = _o.get("px_repair") or {}
        _k = 0
        for _i in range(min(_n, len(_px)) - 1, -1, -1):
            if _px[_i] is None:
                _k += 1
            else:
                break
        if _k >= 5:
            _dark.append((_k, _t, len(_rep)))
    _dark.sort(reverse=True)
    if _dark:
        errors.append(
            "종목 계열이 **끊긴 채** 있다 — %s. 하루 단위 구멍 검사(문턱 20종)는 이것을 "
            "못 잡는다: 한 종목이 며칠째 비는 것은 «좁고 깊은» 결손이라 매일 1종씩만 세이기 "
            "때문이다. 벤더가 그 종목을 안 주는 것이면 build/px_repair_db.py 로 메울 것"
            % " · ".join("%s %d거래일" % (t, k) for k, t, _r in _dark[:6]))
    else:
        print("  ~ 종목 계열 연속 결손 검사 통과(유니버스 %d종 · 5거래일 이상 끊긴 종목 0)"
              % len(_uni))
except Exception as _e:
    print("  ~ 종목 계열 연속 결손 검사가 예외로 죽었다 — %s (미검증)" % str(_e)[:80])

# ── 배선 감사 둘을 여기서 돌린다 ────────────────────────────────────────────
# 🚨 2026-08-18 — build/audit_commit_lists.py 도 build/audit_unbuilt.py 도
#   **어디서도 안 불리고 있었다.** 안 배선된 것을 찾는 감사기가 자기도 안 배선돼 있었다.
#   손으로 부를 때만 도는 검사는, 부를 생각을 한 사람이 이미 문제를 아는 날에만 돈다.
# ⚠ 두 감사는 정적 분석이라 «이상 없음» 을 증명하지 못한다(각 머리말 참조). 그래서
#   여기서도 **수가 늘 때만** 막는다. 지금 남은 것을 0 으로 만들 수 없으니 기준선을
#   코드에 박고, 그보다 늘면 «이 변경이 늘렸다» 고 말한다 — 랩이 이미 쓰는 관문 방식이다.
# ⚠ 기준선을 줄이는 것은 좋은 일이다. 줄었으면 이 수를 낮춰 적을 것(안 낮추면 다음
#   퇴행을 못 잡는다). 그 안내를 화면에 같이 찍는다.
# 2026-08-19 — 1→0. data/home_perf.json 을 refresh-intraday 도 굽게 되면서 «굽는 잡이
#   없는 산출물» 이 사라졌다. 래칫이므로 줄면 바로 낮춘다 — 안 낮추면 다시 늘어도 안 걸린다.
BASE_UNBUILT, BASE_UNREAD = 0, 2
try:
    import importlib, contextlib
    _au = importlib.import_module("audit_unbuilt")
    _buf = io.StringIO()
    with contextlib.redirect_stdout(_buf):
        _au.main()
    _txt = _buf.getvalue()
    def _n(pat):
        m = re.search(pat, _txt)
        return int(m.group(1)) if m else 0
    _ub = _n(r"굽는 잡이 없는\*\* 산출물 (\d+)개")
    _ur = _n(r"읽는 곳이 없는\*\* 산출물 (\d+)개")
    if _ub > BASE_UNBUILT or _ur > BASE_UNREAD:
        errors.append(
            "배선 감사 퇴행 — 굽는 잡 없는 산출물 %d개(기준 %d) · 읽는 곳 없는 산출물 "
            "%d개(기준 %d). 새로 만든 산출물을 잡에 안 붙였거나 화면에 안 실었다는 뜻이다. "
            "python build/audit_unbuilt.py 로 어느 것인지 볼 것"
            % (_ub, BASE_UNBUILT, _ur, BASE_UNREAD))
    elif _ub < BASE_UNBUILT or _ur < BASE_UNREAD:
        print("  ~ 배선 감사: 줄었다(굽는 잡 없음 %d≤%d · 읽는 곳 없음 %d≤%d) — "
              "build/validate_site.py 의 BASE_UNBUILT/BASE_UNREAD 를 이 수로 낮출 것"
              % (_ub, BASE_UNBUILT, _ur, BASE_UNREAD))
    else:
        print("  ~ 배선 감사 통과(굽는 잡 없음 %d · 읽는 곳 없음 %d — 기준선과 같음)"
              % (_ub, _ur))
except Exception as _e:
    print("  ~ 배선 감사가 예외로 죽었다 — %s (미검증)" % str(_e)[:80])

print("사이트 검증:", "통과 ✅" if not errors else f"실패 ❌ {len(errors)}건")
for e in errors: print("  -", e)
sys.exit(1 if errors else 0)
