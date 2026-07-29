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
import subprocess
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
GATE = os.path.join(ROOT, "kb.html")
FRAG = os.path.join(ROOT, "_build", "pages", "kb_content.html")

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
    ap = argparse.ArgumentParser(description="kb.html 본문 재잠금 + ph 기록")
    ap.add_argument("--check", action="store_true",
                    help="기록된 ph 와 조각 평문이 맞는지만 확인하고 끝낸다")
    a = ap.parse_args()

    if not os.path.exists(GATE):
        print("없음:", GATE); return 1
    gate = read_exact(GATE)
    m = BLOCK_RE.search(gate)
    if not m:
        print("게이트 파라미터 블록을 못 찾았다 — kb.html 구조가 바뀌었다."); return 1
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
            print("→ ph 가 없다. python build/kb_lock.py 로 다시 잠그며 기록할 것."); return 2
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
    bad = sanity(new)
    if bad:
        print("자체검사 실패 — 기록하지 않았다:")
        for b in bad:
            print("  -", b)
        return 1
    io.open(GATE, "w", encoding="utf-8", newline="").write(new)
    print("기록: kb.html  ct %d chars · ph %s…" % (len(p["ct"]), p["ph"][:12]))

    # 평문 한 장을 다시 만들어 둔다 — validate 의 평문 의존 검사 6종이 그것을 본다.
    r = subprocess.run([sys.executable, os.path.join(ROOT, "build", "kb_plain.py")],
                       capture_output=True, text=True)
    print((r.stdout or r.stderr).strip() or "kb_plain.py 무응답")
    if r.returncode != 0:
        print("  ⚠ kb_plain.py 가 실패했다 — 평문 의존 검사 6종은 계속 SKIP 된다.")
    print("다음: python build/validate_site.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
