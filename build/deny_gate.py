# -*- coding: utf-8 -*-
"""build/deny_gate.py — 사내 식별자 차단 관문(해시 대조). 표준 라이브러리만 쓴다.

왜 있나 (2026-09-27 · 사용자 규칙).
  이 저장소는 공개다(GitHub Pages). 사내 정보 — 내부 펀드코드 · 사내 시스템 이름 ·
  사내 DB 스키마/테이블명과 접속 정보 · 게이트웨이 주소/호스트명 · 회사 네트워크 경로 —
  는 어떤 추적 파일에도 들어가면 안 된다. 사내 자료가 필요한 곳은 이미 두 길이 있다:
  잠금 페이지(build/kb_lock.py) 와 git-ignore 된 로컬 입력(build/_private/ 등).
  🚨 그런데 **무엇이 사내 식별자인지 적어 둔 목록 자체**를 평문으로 두면 그 목록이 유출이다.
    그래서 목록은 해시로만 적고, 그 파일도 공개 저장소에 두지 않는다(git-ignore 된
    build/_private/deny_hashes.json · 이 PC 전용). 짧은 값(펀드코드 · IP)의 해시는 무차별 대입으로
    되찾을 수 있어서, 해시 목록을 공개하면 그 자체가 유출이다.

무엇을 하나.
  추적 중인 텍스트 파일 전부(git ls-files)를 토큰으로 잘라 해시를 차단 목록과 대조한다. 파일 이름(경로)도
  같은 규약으로 본다(이진 파일 포함 · 걸리면 줄 번호 0). 걸리면 «파일:줄» 만 말한다 — **토큰은 찍지
  않는다**(CI 로그도 공개다).

토큰 규약(정규화 = 소문자).
  ① 영숫자 낱말 [A-Za-z0-9_]+  — 글자나 밑줄이 하나라도 있는 것.
  ② 복합어 — 점 · 하이픈 · 밑줄로 이어진 조각(schema.table · host-name · name_suffix · a.b.c)의
     이어진 조각 1~8개의 모든 창(구분자는 원문 그대로). 그래서 snake_case 안에 박힌 이름도 잡힌다.
     한 창 안에 글자 조각이 있거나, 숫자 넷이 점으로 이어진 IPv4 모양이면 후보다.
  ③ 한글이 든 낱말 — 한글을 포함하는 길이 2~24 의 모든 부분 문자열(조사가 붙어도 잡힌다).
  🚨 뺀 것과 그 이유 — «통과» 가 «없다» 를 뜻하지 않는 자리다.
     · 순수 숫자(가격 · 날짜 · 소수)는 후보가 아니다. 가격 자료가 수천만 개라 넣으면 이 검사가
       수십 초가 된다. 목록에 순수 숫자 식별자는 없다(IPv4 는 ② 로 잡는다).
     · 길이 80 이상 base64 덩어리(+ 또는 / 가 있고 . - _ 가 없는 것)는 건너뛴다 — 잠금
       페이지의 AES 암호문이라 우연히 짧은 토큰이 생기면 거짓 경보가 된다.
     · .json 은 문자열 리터럴 안만 본다(JSON 에서 글자는 문자열 밖에 올 수 없다). \\uXXXX 는 푼다.
     · 이진 파일(.gz · .pdf · NUL 바이트)은 안 본다.
     · 공백이 낀 표기(«A B» 처럼 둘로 쓴 이름)는 토큰 하나가 아니라 못 잡는다.

해시.
  sha256(DOMAIN + NUL + 정규화 토큰). DOMAIN 은 비밀이 아니다 — 흔한 sha256 역표(짧은 낱말)로
  바로 뒤집히지 않게 하는 구분자일 뿐이다.
  ⚠ 해시는 무차별 대입을 막지 못한다 — 짧거나 추측할 수 있는 값은 되찾을 수 있다. 이 목록은
    «검색·색인·눈으로 읽기» 를 막는 장치이고, 꼭 숨겨야 하는 값은 저장소 밖에 둔다.
  목록이 없는 곳(CI · 다른 PC)에서는 관문이 «건너뜀» 을 알린다 — 그곳의 통과는 검사한 것이 아니다.
  공개 저장소로 가는 길은 이 PC 에서 푸시 전에 도는 validate_site 가 막는다.

얼린 기록(사전등록·감사 문서 · data/_* 굽기 산출).
  이미 박제된 기록은 고치지 않는다. 대신 FROZEN 에 경로와 **허용 줄 수**를 적는다 — 그보다
  늘면 실패, 줄면 «허용을 낮출 것» 안내(래칫 · 배선 감사와 같은 방식).

  python build/deny_gate.py             저장소 검사(걸리면 exit 1)
  python build/deny_gate.py --selftest  합성 토큰으로 자체 시험
  python build/deny_gate.py --add       표준입력의 토큰(한 줄에 하나)을 목록에 더한다 — 화면에 안 찍는다
  python build/deny_gate.py --test      표준입력의 토큰이 목록에 있는지 답한다 — 화면에 안 찍는다
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HASHES = os.path.join(ROOT, "build", "_private", "deny_hashes.json")   # 로컬 전용(git-ignore)
DOMAIN = b"yeodoo-lab/deny/v1"
REPL = "[내부]"

# 얼린 기록 — 경로와 허용 줄 수(해시가 걸린 줄의 수). 새 기록을 여기에 더하지 말 것:
#   새 문서는 처음부터 일반 명칭으로 쓴다. data/_* 넷은 CI 가 매일 다시 굽는다 —
#   생성기 문구를 고쳤으니 다음 굽기에서 0 이 되고, 그때 «허용을 낮출 것» 안내가 뜬다.
FROZEN = {
    "build/PREREG-2026-08-20-TILT.md": 1,
    "build/PREREG-2026-09-21-REGIMEGRID.md": 1,
    "build/PREREG-2026-09-21-REGIMEGRID-RESULT.md": 1,
    "build/PREREG-2026-09-26-RBATCH-CARDS.md": 1,
    "data/_flags.json": 1,
    "data/_monitor.json": 1,
    "data/_regime_grid.json": 1,
    "data/_riskonoff.json": 1,
}

BINARY_EXT = (".gz", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".zip",
              ".xlsx", ".xls", ".parquet", ".pkl", ".woff", ".woff2", ".ttf")

# ── 토큰 ──────────────────────────────────────────────────────────────────
_KEEP = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-+/=") | set(range(0x80, 0x100))
_T = bytes((c if c in _KEEP else 0x20) for c in range(256))    # 토큰 문자 밖은 전부 공백
_NUMCH = b"0123456789.-"
_SUBRUN = re.compile(r"[^+/=]+")
_ASCII_COMP = re.compile(r"[A-Za-z0-9_]+(?:[.\-][A-Za-z0-9_]+)*")
_PART_SEP = re.compile(r"[.\-]")
_PART = re.compile(r"[A-Za-z0-9]+")                  # 창의 조각 — 점 · 하이픈 · 밑줄 사이
_HAS_LETTER = re.compile(r"[A-Za-z_]")
_KWORD = re.compile(r"[A-Za-z0-9_\uac00-\ud7a3]+")
_HANGUL = re.compile(r"[\uac00-\ud7a3]")
_UESC = re.compile(rb"\\u([0-9a-fA-F]{4})")
# 문자열 쪽 덩어리 — 바이트 쪽 _T(비ASCII 바이트는 토큰 문자)와 같은 경계다.
_RUN_STR = re.compile(r"[A-Za-z0-9_.\-+/=%s-%s]+" % (chr(0x80), chr(0x10FFFF)))
MAXW, KMAX = 8, 24


_PREFIX = DOMAIN + b"\0"
_WORDB = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_"
_DIGB = b"0123456789"
_SEP_ONLY = re.compile(r"[.\-]")


def digest(tok: str) -> str:
    return hashlib.sha256(_PREFIX + tok.lower().encode("utf-8")).hexdigest()


def _dg(low: bytes) -> bytes:
    """이미 소문자로 만든 바이트의 원시 digest — 검사 안쪽 고리용(hexdigest 보다 싸다)."""
    return hashlib.sha256(_PREFIX + low).digest()


def _is_b64(run: str) -> bool:
    return len(run) >= 80 and ("+" in run or "/" in run) and not any(c in run for c in ".-_")


def _win_spans(comp: str):
    """복합어 하나 → 창의 (시작, 끝) — 조각은 영숫자 덩어리, 사이 구분자(. - _)는 원문 그대로 둔다."""
    sp = [(m.start(), m.end()) for m in _PART.finditer(comp)]
    n = len(sp)
    let = [bool(_HAS_LETTER.search(comp[a:b])) for a, b in sp]
    for i in range(n):
        anyl = False
        for j in range(i, min(n, i + MAXW)):
            anyl = anyl or let[j]
            a, b = sp[i][0], sp[j][1]
            if anyl or (j - i == 3 and all(comp[sp[k][1]:sp[k + 1][0]] == "." for k in range(i, j))):
                yield a, b
    if "_" in comp[:1] + comp[-1:] and any(let):
        yield 0, len(comp)                               # 앞뒤 밑줄까지 붙은 낱말 전체(_name 같은 것)


def _ascii_windows(s: str, base: int):
    """ASCII 복합어의 창 — (시작, 끝, 글자). 순수 숫자 창은 IPv4 모양만 남긴다."""
    for m in _ASCII_COMP.finditer(s):
        comp = m.group(0)
        for a, b in _win_spans(comp):
            yield base + m.start() + a, base + m.start() + b, comp[a:b]


def candidates(run: str):
    """토큰 문자 덩어리 하나 → 후보 (시작, 끝, 글자). 규약은 머리말 참조."""
    if _is_b64(run):
        return
    for sm in _SUBRUN.finditer(run):              # + / = 는 경계(경로 · 대입 · 짧은 base64)
        sub, pos = sm.group(0), sm.start()
        # ① ② — 비ASCII 한 글자를 '?' 한 글자로(위치 보존) 보고 ASCII 복합어를 잡는다
        yield from _ascii_windows(sub.encode("ascii", "replace").decode("ascii"), pos)
        # ③ — 한글이 든 낱말의 부분 문자열(한글을 포함하는 것만 — ASCII 만은 위에서 봤다)
        if _HANGUL.search(sub):
            for w in _KWORD.finditer(sub):
                t = w.group(0)
                if not _HANGUL.search(t):
                    continue
                L = len(t)
                for a in range(L):
                    for b in range(a + 2, min(L, a + KMAX) + 1):
                        piece = t[a:b]
                        if _HANGUL.search(piece):
                            yield pos + w.start() + a, pos + w.start() + b, piece


def _comp_windows(comp: str) -> set:
    """ASCII 복합어 하나의 창 글자들(candidates 의 ② 와 같은 규약 — _win_spans 를 같이 쓴다)."""
    if "." not in comp and "-" not in comp and "_" not in comp:
        return {comp} if _HAS_LETTER.search(comp) else set()
    return {comp[a:b] for a, b in _win_spans(comp)}


def _kword_pieces(t: str) -> set:
    """한글이 든 낱말 하나의 부분 문자열(한글을 포함하는 길이 2~KMAX) — candidates 의 ③."""
    out, L = set(), len(t)
    for a in range(L):
        for b in range(a + 2, min(L, a + KMAX) + 1):
            piece = t[a:b]
            if _HANGUL.search(piece):
                out.add(piece)
    return out


def _parts_of(s: str):
    """덩어리 → (ASCII 복합어 목록, 한글 낱말 목록). base64 덩어리는 빈 것."""
    comps, kws = [], []
    if _is_b64(s):
        return comps, kws
    for sub in _SUBRUN.findall(s):
        comps += _ASCII_COMP.findall(sub.encode("ascii", "replace").decode("ascii"))
        if _HANGUL.search(sub):
            kws += [t for t in _KWORD.findall(sub) if _HANGUL.search(t)]
    return comps, kws


def load_hashes(path: str = HASHES):
    """차단 목록(로컬 전용). 파일이 없으면 None — 부르는 쪽이 «건너뜀» 으로 다룬다."""
    if not os.path.exists(path):
        return None
    d = json.load(io.open(path, encoding="utf-8"))
    hs = d.get("hashes") or []
    bad = [h for h in hs if not re.fullmatch(r"[0-9a-f]{64}", h or "")]
    if bad:
        raise ValueError("차단 목록에 64자리 hex 가 아닌 값 %d개" % len(bad))
    return set(hs)


class _Matcher:
    """덩어리(run) 단위 캐시 — 같은 덩어리를 두 번 해시하지 않는다."""

    def __init__(self, hashes: set):
        self.hb = {bytes.fromhex(h) for h in hashes}
        self.clean = set()
        self.hit = {}          # run(bytes) → [걸린 글자(str) …]  (메모리에만 산다)
        self.part_ok = set()   # 깨끗하다고 확인한 복합어 · 한글 낱말(덩어리끼리 공유한다)

    def _hits_in(self, piece: str, gen) -> list:
        if piece in self.part_ok:
            return []
        got = [c for c in gen(piece) if _dg(c.lower().encode("utf-8")) in self.hb]
        if not got:
            self.part_ok.add(piece)
        return got

    def classify(self, run: bytes):
        if not run.translate(None, _WORDB) and b"_" not in run:   # 단순 영숫자 낱말 — 덩어리의 대부분
            if run.translate(None, _DIGB) and _dg(run.lower()) in self.hb:
                self.hit[run] = [run.decode("ascii")]
            else:
                self.clean.add(run)                      # 순수 숫자이거나 목록에 없다
            return
        if not run.translate(None, _NUMCH) and run.count(b".") < 3:
            self.clean.add(run)             # 순수 숫자 — 점이 셋 미만이면 IPv4 창도 없다
            return
        comps, kws = _parts_of(run.decode("utf-8", "replace"))
        got = set()
        for c in comps:
            got.update(self._hits_in(c, _comp_windows))
        for t in kws:
            got.update(self._hits_in(t, _kword_pieces))
        if got:
            self.hit[run] = sorted(got, key=len, reverse=True)
        else:
            self.clean.add(run)

    def file_hits(self, runs: set) -> set:
        new = runs - self.clean
        new.difference_update(self.hit.keys())
        for r in new:
            self.classify(r)
        return runs.intersection(self.hit)


def _prep(path: str, raw: bytes) -> bytes:
    """JSON 은 문자열 리터럴만 남긴다(따옴표 짝이 안 맞으면 전문을 본다)."""
    if path.endswith(".json"):
        c = raw.replace(b"\\\\", b"  ").replace(b'\\"', b"  ") if b"\\" in raw else raw
        parts = c.split(b'"')
        if len(parts) % 2 == 1:
            raw = b" ".join(parts[1::2])
    return _unesc(raw)


def _unesc(raw: bytes) -> bytes:
    """\\uXXXX 를 푼다(ensure_ascii 로 쓴 JSON 의 한글 등). 짝 없는 서로게이트는 버린다."""
    if b"\\u" not in raw:
        return raw
    return _UESC.sub(lambda m: chr(int(m.group(1), 16)).encode("utf-8", "ignore"), raw)


def _runs(path: str, raw: bytes) -> set:
    return set(_prep(path, raw).translate(_T).split())


def _lines_with(text: str, needles) -> list:
    """걸린 글자가 든 줄 번호(1부터). 같은 규약으로 다시 잘라 경계까지 확인한다."""
    low = [n.lower() for n in needles]
    out = []
    for i, ln in enumerate(text.split("\n"), 1):
        l2 = ln.lower()
        if not any(n in l2 for n in low):
            continue
        rs = set(ln.encode("utf-8").translate(_T).split())
        for r in rs:
            s = r.decode("utf-8", "replace")
            if any(c.lower() in low for _a, _b, c in candidates(s)):
                out.append(i)
                break
    return out


def scan_text(text: str, hashes=None) -> list:
    """문자열 하나를 같은 규약으로 훑어 걸린 줄 번호(1부터)를 돌려준다 — 생성기가 굽기 전에 쓴다."""
    hs = load_hashes() if hashes is None else hashes
    if hs is None:
        return []                         # 목록 없음(로컬 전용) — 부르는 쪽이 따로 알린다
    M = _Matcher(hs)
    raw = _unesc(text.encode("utf-8"))
    fh_ = M.file_hits(set(raw.translate(_T).split()))
    if not fh_:
        return []
    needles = sorted({c for r in fh_ for c in M.hit[r]}, key=len, reverse=True)
    return _lines_with(raw.decode("utf-8", "replace"), needles) or [0]


def tracked_files(root: str = ROOT) -> list:
    r = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("git ls-files 실패 — 추적 파일 목록 없이 통과시키지 않는다")
    return [f for f in r.stdout.decode("utf-8", "replace").split("\0") if f]


def scan_repo(root: str = ROOT, hashes=None, files=None) -> dict:
    t0 = time.time()
    hs = load_hashes() if hashes is None else hashes
    if hs is None:                        # 목록 없음(로컬 전용 · CI · 다른 PC) — 검사하지 않았다
        return {"skipped": True, "files": 0, "binary": 0, "hashes": 0, "hits": [],
                "frozen_over": [], "frozen_stale": [], "seconds": 0.0}
    M = _Matcher(hs)
    files = tracked_files(root) if files is None else files
    hits, frozen_n, n_text, n_bin = [], {}, 0, 0
    for p in files:
        if M.file_hits(set(p.encode("utf-8").translate(_T).split())):
            hits.append((p, 0))                  # 파일 이름 자체(줄 번호 0)
        if p.lower().endswith(BINARY_EXT):
            n_bin += 1
            continue
        try:
            with open(os.path.join(root, p), "rb") as fh:
                raw = fh.read()
        except OSError:
            continue                          # 체크아웃에 없는 파일(희소 체크아웃 등)
        if b"\0" in raw[:8192]:
            n_bin += 1
            continue
        n_text += 1
        fh_ = M.file_hits(_runs(p, raw))
        if not fh_:
            if p in FROZEN:
                frozen_n[p] = 0
            continue
        needles = sorted({c for r in fh_ for c in M.hit[r]}, key=len, reverse=True)
        # 줄 번호는 원문 기준(\\u 만 풀어서). JSON 문자열 밖에는 글자가 올 수 없어 전문을 봐도 같다.
        lines = _lines_with(_unesc(raw).decode("utf-8", "replace"), needles) or [0]
        if p in FROZEN:
            frozen_n[p] = len(lines)
            continue
        hits += [(p, ln) for ln in lines]
    over = [(p, n, FROZEN[p]) for p, n in sorted(frozen_n.items()) if n > FROZEN[p]]
    stale = [(p, frozen_n.get(p, None), FROZEN[p]) for p in sorted(FROZEN)
             if frozen_n.get(p, 0) < FROZEN[p]]
    return {"skipped": False, "files": n_text, "binary": n_bin, "hashes": len(hs), "hits": hits,
            "frozen_over": over, "frozen_stale": stale, "seconds": time.time() - t0}


def redact(text: str, hashes=None, repl: str = REPL):
    """문장 안의 차단 토큰을 repl 로 바꾼다 → (새 문장, 바꾼 수). 갱신 피드(log_from_git)용.

    ASCII 복합어는 창 하나라도 걸리면 **복합어 전체**를 바꾼다(schema.table.col 을 통째로).
    한글 낱말은 걸린 부분만 바꾼다(조사는 남긴다)."""
    hs = load_hashes() if hashes is None else hashes
    if hs is None:
        return text, 0                    # 목록 없음(로컬 전용) — 가리지 못한다(부르는 쪽이 알린다)
    spans = []
    for m in _RUN_STR.finditer(text):
        run = m.group(0)
        asc = run.encode("ascii", "replace").decode("ascii")
        for a, b, c in candidates(run):
            if digest(c) in hs:
                if not _HANGUL.search(c):              # ASCII → 복합어 전체
                    for cm in _ASCII_COMP.finditer(asc):
                        if cm.start() <= a < cm.end():
                            a, b = cm.start(), cm.end()
                            break
                spans.append((m.start() + a, m.start() + b))
    if not spans:
        return text, 0
    spans.sort()
    merged = [list(spans[0])]
    for a, b in spans[1:]:
        if a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out, last = [], 0
    for a, b in merged:
        out.append(text[last:a]); out.append(repl); last = b
    out.append(text[last:])
    return "".join(out), len(merged)


def redacted_pattern(red: str, repl: str = REPL):
    """redact() 결과를 옛 제목과 대조하는 정규식 — repl 자리는 아무 글자(1자 이상)."""
    return re.compile("^" + ".+?".join(re.escape(x) for x in red.split(repl)) + "$", re.S)


# ── 자체 시험(합성 토큰만 — 실제 식별자를 여기에 적지 않는다) ───────────────
def selftest() -> list:
    fails = []
    syn = ["zq9x", "203.0.113.77", "qa-node7", "zz_schema.qq_tbl", "시험용팀", "wqv_dept"]
    H = {digest(t) for t in syn}

    def hit(txt, path="t.txt"):
        return bool(_Matcher(H).file_hits(_runs(path, txt.encode("utf-8"))))

    yes = [("대소문자", "펀드 ZQ9X 기준가"), ("조사 붙음", "ZQ9X은 펀드"), ("IP·포트", "host=203.0.113.77:5432"),
           ("앞 하이픈", "--qa-node7 로"), ("SQL", "FROM zz_schema.qq_tbl WHERE"), ("긴 복합어", "zz_schema.qq_tbl.col"),
           ("한글 조사", "시험용팀이 만든"), ("한글 앞 구분자", "사내·시험용팀"), ("한글 뒤 영문", "WQV_DEPT의 표"),
           ("괄호 안", "(zq9x, Δ=0)"), ("경로", "C:/x/zq9x/y.txt"), ("밑줄 뒤", "zq9x_nav_2026"),
           ("밑줄 앞", "fund_zq9x"), ("앞 밑줄", "_ZQ9X"), ("밑줄 테이블", "zz_schema.qq_tbl_bak"),
           ("밑줄 IP 옆", "ip_203.0.113.77")]
    no = [("다른 토큰", "zq9xa azq9x zq9x1 x9zq"), ("IP 경계", "203.0.113.770 1203.0.113.77 203.0.113.7"),
          ("부분 host", "qa-node node7"), ("테이블만", "qq_tbl"), ("숫자", "123.45 2026-09-27 1e-05"),
          ("base64", "ct:\"" + "Ab3+" * 10 + "zq9x/" + "Cd4/" * 20 + "\""), ("치환 결과", REPL + " " + REPL + "이")]
    for lab, t in yes:
        if not hit(t):
            fails.append("못 잡음: " + lab)
    for lab, t in no:
        if hit(t):
            fails.append("거짓 경보: " + lab)
    if not hit('{"a": "x zq9x y", "b": 1.5}', "d.json"):
        fails.append("못 잡음: JSON 문자열")
    if not hit('{"ZQ9X": [1, 2.5]}', "d.json"):
        fails.append("못 잡음: JSON 키")
    if hit('{"k": [203.0, 113.77, 1e-05]}', "d.json"):
        fails.append("거짓 경보: JSON 숫자")
    if not hit('{"a": "\\uc2dc\\ud5d8\\uc6a9\\ud300"}', "d.json"):
        fails.append("못 잡음: JSON \\u 이스케이프")
    if not hit('{"a": "say \\"zq9x\\" ok"}', "d.json"):
        fails.append("못 잡음: JSON 이스케이프 따옴표")
    src = "포트폴리오 — 전 펀드(ZQ9X + zq9x) · 시험용팀이 zz_schema.qq_tbl.col 을 · 203.0.113.77:5432"
    red, n = redact(src, H)
    want = "포트폴리오 — 전 펀드([내부] + [내부]) · [내부]이 [내부] 을 · [내부]:5432"
    if red != want or n != 5:
        fails.append("치환 결과가 다르다(%d곳)" % n)
    if redact(red, H) != (red, 0):
        fails.append("치환이 멱등이 아니다")
    if not redacted_pattern(red).match("포트폴리오 — 전 펀드(가 + 나) · 다이 라 을 · 마:5432"):
        fails.append("치환 대조식이 옛 제목을 못 알아본다")
    if redacted_pattern(red).match("다른 제목"):
        fails.append("치환 대조식이 너무 넓다")
    if _lines_with("a\nb\nx ZQ9X y\n", ["zq9x"]) != [3]:
        fails.append("줄 번호가 틀렸다")
    if scan_text("첫 줄\n둘째 줄 zz_schema.qq_tbl\n셋째", H) != [2] or scan_text("깨끗한 문장", H):
        fails.append("scan_text 가 틀렸다")
    _r = scan_repo(ROOT, H, files=["docs/zq9x_notes.txt"])
    if ("docs/zq9x_notes.txt", 0) not in _r["hits"]:
        fails.append("파일 이름을 못 본다")
    try:
        real = load_hashes()
        if real is not None:              # 목록은 로컬 전용 — 없는 곳(CI)에서는 합성 시험만 한다
            if not real:
                fails.append("차단 목록이 비었다")
            if real & H:
                fails.append("차단 목록에 자체 시험 토큰이 섞였다")
    except Exception as e:
        fails.append("차단 목록을 못 읽었다(%s)" % type(e).__name__)
    return fails


def _stdin_tokens():
    return [ln.strip() for ln in sys.stdin.read().splitlines() if ln.strip()]


def main(argv) -> int:
    if "--selftest" in argv:
        f = selftest()
        print("자체 시험 %s" % ("통과" if not f else "실패 — " + "; ".join(f)))
        return 1 if f else 0
    if "--add" in argv:
        d = json.load(io.open(HASHES, encoding="utf-8")) if os.path.exists(HASHES) else {"hashes": []}
        os.makedirs(os.path.dirname(HASHES), exist_ok=True)
        hs = set(d.get("hashes") or [])
        toks = _stdin_tokens()
        new = {digest(t) for t in toks} - hs
        d["hashes"] = sorted(hs | new)
        io.open(HASHES, "w", encoding="utf-8", newline="\n").write(
            json.dumps(d, ensure_ascii=False, indent=1) + "\n")
        print("읽은 토큰 %d · 새로 더한 해시 %d · 목록 %d" % (len(toks), len(new), len(d["hashes"])))
        return 0
    if "--test" in argv:
        hs = load_hashes()
        if hs is None:
            print("차단 목록 없음(로컬 전용 build/_private/deny_hashes.json)")
            return 1
        for i, t in enumerate(_stdin_tokens(), 1):
            print("%d번째 줄: %s" % (i, "목록에 있다" if digest(t) in hs else "없다"))
        return 0
    r = scan_repo()
    if r.get("skipped"):
        print("~ 차단 목록(로컬 전용 build/_private/deny_hashes.json)이 없어 건너뜀 — 검사한 것이 아니다")
        return 0
    for p, ln in r["hits"]:
        print("✗ %s:%d — 사내 식별자(차단 목록 해시 일치)" % (p, ln))
    for p, n, a in r["frozen_over"]:
        print("✗ %s — 얼린 기록인데 걸린 줄이 %d 로 허용 %d 을 넘었다" % (p, n, a))
    for p, n, a in r["frozen_stale"]:
        print("~ %s — 허용 %d 인데 지금 %s — FROZEN 을 낮출 것" % (p, a, "없음" if n is None else n))
    print("파일 %d · 이진 %d · 목록 %d · %.1f초 · %s"
          % (r["files"], r["binary"], r["hashes"], r["seconds"],
             "통과" if not r["hits"] and not r["frozen_over"] else "실패"))
    return 1 if r["hits"] or r["frozen_over"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
