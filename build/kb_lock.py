# -*- coding: utf-8 -*-
"""build/kb_lock.py — kb.html 본문을 다시 잠그고 **ct 와 ph 를 함께** 기록한다.

왜 있나. kb.html 은 이 사이트에 하나 남은 잠금 페이지다. 배포본은 '평문 셸 + 암호화된
본문(PAYLOAD)' 이고, 본문 평문은 _build/pages/kb_content.html 조각으로만 관리된다.
그런데 잠그는 일을 저장소 밖 도구로 하다 보니 ph(평문 지문)를 같이 남기지 못했고,
validate_site.py 가 그걸 실패로 잡아 **refresh-assets 워크플로의 커밋 단계가 통째로
막혔다**(2026-07-27 이후). ct 와 ph 는 같은 순간에 같은 평문에서 나와야 의미가 있으므로,
둘을 따로 만들 수 있는 구조 자체가 사고였다. 한 도구가 같이 쓴다.

ph 는 무엇인가.
    ph = sha256(조각 평문의 UTF-8 바이트).hexdigest()
validate_site.py 가 로컬 조각과 대조해 '다른 PC에서 재잠금됐는데 낡은 사본으로 초록불'을
기계적으로 잡는 장치다. 그래서 **조각에서 ph 를 만들되 그 조각을 그 자리에서 암호화**한다 —
따로 계산하면 순환 논증이 되어 검사가 있으나 마나가 된다.

브라우저 게이트와 맞춰야 하는 규약(kb.html 의 unlock() 과 한 글자도 어긋나면 안 된다).
    키유도  PBKDF2-HMAC-SHA256 · iterations 310,000 · salt 16B
    암호화  AES-256-GCM · iv 12B · 인증태그 128bit 를 ct 뒤에 붙임(WebCrypto 기본)
    평문    UTF-8 바이트. TextDecoder().decode(pt) 가 그대로 innerHTML 로 들어간다

    python build/kb_lock.py            잠그고 ct·ph 기록
    python build/kb_lock.py --check    지금 기록된 ph 가 조각과 맞는지만 본다
"""
from __future__ import annotations
import argparse
import hashlib
import io
import os
import re
import secrets
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.hashes import SHA256
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except Exception:
    sys.exit("cryptography 가 필요하다 —  pip install cryptography")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 잠금 페이지 목록. 🚨 2026-08-11 에 sources.html 이 두 번째로 들어오면서 일반화했다 —
#   그 전에는 kb.html 이 상수로 박혀 있어서, 두 번째 페이지를 잠그려면 이 파일을 복사해야 했다.
#   복사본이 생기면 규약(iterations·salt 길이·ph 계산)이 두 벌이 되고, 한쪽만 고쳐지는 날이 온다.
#   이 파일 첫머리가 경계하는 바로 그 구조다.
# ⚠ 조각 경로는 _build/pages/ 아래이고 그 폴더는 gitignore 다 — 평문은 저장소에 안 들어간다.
PAGES = {
    "kb":      ("kb.html",      "kb_content.html"),
    "sources": ("sources.html", "sources_content.html"),
}
GATE = FRAG = None      # main() 이 --page 로 정한다

ITER = 310000          # 게이트에 박힌 값과 같아야 한다
SALT_LEN, IV_LEN = 16, 12
MIN_CT = 1024          # validate_site.py 의 절단 의심 문턱
BLOCK_RE = re.compile(r"var (P|PAYLOAD)=\{[^}]*\}")


def read_exact(p):
    """바이트 정확 읽기. newline='' 이 없으면 유니버설 개행 번역이 끼어 해시가 어긋난다."""
    return io.open(p, encoding="utf-8", newline="").read()


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def lock(plain: str, password: str, *, salt=None, iv=None, iters=ITER) -> dict:
    """조각 평문 → 게이트 파라미터. 브라우저 unlock() 이 그대로 복호할 수 있는 형태다."""
    import base64
    salt = salt or secrets.token_bytes(SALT_LEN)
    iv = iv or secrets.token_bytes(IV_LEN)
    key = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=iters).derive(
        password.encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, plain.encode("utf-8"), None)
    # 되돌려 풀어 본다 — 여기서 안 걸리면 페이지가 영구 복호불가로 배포된다.
    back = AESGCM(key).decrypt(iv, ct, None).decode("utf-8")
    if back != plain:
        raise SystemExit("자체검사 실패 — 복호 결과가 원문과 다르다. 기록하지 않았다.")
    b = lambda x: base64.b64encode(x).decode()
    return {"salt": b(salt), "iv": b(iv), "ct": b(ct), "iter": iters,
            "ph": fingerprint(plain)}


def render(varname: str, p: dict) -> str:
    # ⚠ validate_site.py 는 var (P|PAYLOAD)=\{([^}]*)\} 로 읽는다 — 블록 안에 '}' 가 있으면
    #   파싱이 거기서 끊긴다. base64 와 10진수뿐이라 안전하지만 순서를 바꿔도 무방하다.
    return ('var %s={salt:"%s",iv:"%s",ct:"%s",iter:%d,ph:"%s"}'
            % (varname, p["salt"], p["iv"], p["ct"], p["iter"], p["ph"]))


def sanity(gate_text: str) -> list:
    """validate_site.py 의 게이트 검사를 그대로 재현한다 — 배포 전에 여기서 걸러 낸다."""
    import base64
    out = []
    # 🚨 2026-08-05 — 게이트만 보고 **셸 속성은 안 봤다.** 그래서 재잠금이 <body> 를 새로 쓸
    #   때마다 data-tool 이 사라졌고, 같은 실패가 두 번 났다(2026-08-02 커밋 524e691a 가
    #   한 번 고쳤는데 2026-08-04 재잠금이 다시 지웠다). 화면에서는 내비가 현재 위치를
    #   표시 못 하고, CI 는 그 상태로 커밋 단계까지 막는다.
    #   여기서 막는다 — 아래 main() 이 복원까지 하지만, 복원이 실패하면 기록을 멈춘다.
    if not re.search(r'<body[^>]*\bdata-tool\s*=', gate_text):
        out.append("<body data-tool> 이 없다 — 내비가 현재 위치를 표시할 수 없다")
    m = BLOCK_RE.search(gate_text)
    if not m:
        return ["게이트 파라미터 블록 파싱 실패"]
    blk = m.group(0)
    d = dict(re.findall(r'(\w+):"([^"]*)"', blk))
    it = re.search(r"iter:(\d+)", blk)
    try:
        if len(base64.b64decode(d.get("salt", ""), validate=True)) != SALT_LEN:
            out.append("salt 길이가 16B 가 아니다")
        if len(base64.b64decode(d.get("iv", ""), validate=True)) != IV_LEN:
            out.append("iv 길이가 12B 가 아니다")
        if len(base64.b64decode(d.get("ct", ""), validate=True)) < MIN_CT:
            out.append("ct 가 너무 짧다 — 절단 의심")
    except Exception as e:
        out.append("base64 손상 — %s" % e)
    if not it or int(it.group(1)) < 100000:
        out.append("PBKDF2 iterations 비정상/누락")
    if not re.fullmatch(r"[0-9a-f]{64}", d.get("ph", "")):
        out.append("ph 가 64자리 소문자 hex 가 아니다")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="잠금 페이지 본문 재잠금 + ph 기록")
    ap.add_argument("--page", default="kb", choices=sorted(PAGES),
                    help="잠글 페이지(기본 kb — 종전 동작 그대로)")
    ap.add_argument("--check", action="store_true",
                    help="기록된 ph 와 조각 평문이 맞는지만 확인하고 끝낸다")
    a = ap.parse_args()

    global GATE, FRAG
    _g, _f = PAGES[a.page]
    GATE = os.path.join(ROOT, _g)
    FRAG = os.path.join(ROOT, "_build", "pages", _f)
    print("페이지 %s ← 조각 %s" % (_g, _f))

    if not os.path.exists(GATE):
        print("없음:", GATE); return 1
    gate = read_exact(GATE)
    m = BLOCK_RE.search(gate)
    if not m:
        print("게이트 파라미터 블록을 못 찾았다 — %s 구조가 바뀌었다." % _g); return 1
    if len(BLOCK_RE.findall(gate)) != 1:
        print("파라미터 블록이 둘 이상이다 — 어느 것을 고칠지 알 수 없다."); return 1
    varname = m.group(1)

    if not os.path.exists(FRAG):
        print("없음:", FRAG)
        print("  본문 조각이 있는 PC에서 돌려야 한다. 조각이 곧 잠글 평문이다.")
        return 1
    frag = read_exact(FRAG)
    ph_now = fingerprint(frag)

    if a.check:
        cur = dict(re.findall(r'(\w+):"([^"]*)"', m.group(0))).get("ph")
        print("조각 sha256 :", ph_now)
        print("게이트 ph   :", cur or "(없음)")
        if not cur:
            print("→ ph 가 없다. python build/kb_lock.py --page %s 로 다시 잠그며 기록할 것." % a.page); return 2
        if cur != ph_now:
            print("→ 불일치. 조각이 낡았거나 다른 PC에서 재잠금됐다."); return 3
        print("→ 일치."); return 0

    print("조각 %s (%d bytes)" % (os.path.relpath(FRAG, ROOT), len(frag.encode("utf-8"))))
    print("지문 %s" % ph_now)
    import getpass
    pw = getpass.getpass("열람 암호: ")
    if len(pw) < 4:
        print("암호가 너무 짧다."); return 1
    if pw != getpass.getpass("한 번 더    : "):
        print("두 입력이 다르다 — 아무것도 바꾸지 않았다."); return 1

    p = lock(frag, pw)
    new = gate[:m.start()] + render(varname, p) + gate[m.end():]
    # 🚨 재잠금이 <body> 를 새로 쓰면서 셸 속성을 잃는 일이 반복됐다. 잃었으면 되돌린다 —
    #   사람이 매번 기억해야 하는 것은 언젠가 잊는다(두 번 잊었다).
    if not re.search(r'<body[^>]*\bdata-tool\s*=', new):
        _bm = re.search(r'<body([^>]*)>', new)
        if _bm:
            new = new[:_bm.start()] + '<body data-tool="%s"%s>' % (_g, _bm.group(1)) + new[_bm.end():]
            print("  ↻ <body data-tool=\"%s\"> 를 되돌렸다(재잠금이 지웠다)" % _g)

    bad = sanity(new)
    if bad:
        print("자체검사 실패 — 기록하지 않았다:")
        for b in bad:
            print("  -", b)
        return 1
    io.open(GATE, "w", encoding="utf-8", newline="").write(new)
    # 🚨 2026-08-12 — 여기가 "kb.html" 로 **하드코딩**돼 있었다. --page sources 로 돌리면
    #   sources.html 에 제대로 기록해 놓고 화면에는 "기록: kb.html" 이라 찍혀서,
    #   실제로 사용자가 "kb 를 덮어썼나" 하고 놀랐다(실측 2026-08-12). 기록한 곳을 적는다.
    print("기록: %s  ct %d chars · ph %s…"
          % (os.path.basename(GATE), len(p["ct"]), p["ph"][:12]))

    # 평문 한 장을 다시 만들어 둔다 — validate 의 평문 의존 검사 6종이 그것을 본다.
    #
    # ⚠ 예전엔 subprocess 로 돌렸다가 메시지를 통째로 잃었다(실측 2026-07-29).
    #   kb_plain.py 는 stdout 을 UTF-8 로 재설정하는데 부모의 text=True 는 **로케일**
    #   (한국어 윈도면 cp949)로 디코딩한다. 한글 UTF-8 바이트가 cp949 로 안 풀려
    #   subprocess 리더 스레드가 UnicodeDecodeError 로 죽고 r.stdout 이 None 이 됐다.
    #   그 결과 진짜 사유 대신 '무응답'만 찍혔다. 파이프를 없애면 그 층 자체가 사라진다.
    # 🚨 2026-08-12 — 자식 모듈을 부를 때 **argv 를 비운다.** 이것들도 argparse 를 쓰는데
    #   부모의 sys.argv(`--page sources`)를 그대로 읽어 "unrecognized arguments" 로 죽었다.
    #   그리고 argparse 는 SystemExit 을 던지므로 아래 `except Exception` 에 **안 잡힌다** —
    #   프로세스가 거기서 끝나 셸·내비 전파와 마지막 안내가 통째로 건너뛰어졌다(실측).
    _argv0 = sys.argv
    sys.argv = [_argv0[0]]
    try:
        import importlib.util as _ilu
        _sp = _ilu.spec_from_file_location("_kbplain", os.path.join(ROOT, "build", "kb_plain.py"))
        _kp = _ilu.module_from_spec(_sp)
        _sp.loader.exec_module(_kp)
        rc = _kp.main()
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    except Exception as e:
        print("  ⚠ kb_plain.py 를 부르지 못했다 — %s: %s" % (type(e).__name__, e))
        rc = 1
    if rc != 0:
        print("  ⚠ 평문 한 장을 못 만들었다 — 평문 의존 검사 6종은 계속 SKIP 된다.")
    # 🚨 잠근 뒤에 셸·내비 정본을 함께 민다. 종전에는 사람이 따로 돌려야 했고, 안 돌리면
    #   '공통 셸 드리프트'·'내비 드리프트'가 CI 에서 터졌다(2026-08-05 실측: kb.html 1장 ·
    #   내비 3장). 잠금과 전파는 늘 같이 일어나야 하는 일이므로 여기서 같이 한다.
    for _mod, _lab in (("sync_shell", "공통 셸"), ("sync_nav", "내비 정본")):
        try:
            import importlib.util as _ilu2
            _s2 = _ilu2.spec_from_file_location("_" + _mod, os.path.join(ROOT, "build", _mod + ".py"))
            _m2 = _ilu2.module_from_spec(_s2)
            _s2.loader.exec_module(_m2)
            if hasattr(_m2, "main"):
                _m2.main()
        except SystemExit as _e3:
            if _e3.code not in (0, None):
                print("  ⚠ %s 전파가 종료코드 %s 로 끝났다 (직접 python build/%s.py 를 돌릴 것)"
                      % (_lab, _e3.code, _mod))
        except Exception as _e2:
            print("  ⚠ %s 전파 실패 — %s: %s (직접 python build/%s.py 를 돌릴 것)"
                  % (_lab, type(_e2).__name__, _e2, _mod))
    sys.argv = _argv0
    print("다음: python build/validate_site.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
