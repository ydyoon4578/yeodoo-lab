# -*- coding: utf-8 -*-
"""판정 원장(data/verdicts.json) 생성 — 홈이 숫자를 손으로 적지 않게 한다.

왜 필요한가
    홈에 '22개 전략(배포 3·제한적 유효 17·기각 2)' '기각 41개' 같은 숫자가 HTML에 박혀 있었다.
    전략을 하나 등재하는 순간 조용히 틀린다 — 실제로 README는 이미 어긋나 있었다.
    '정직성'을 내세운 페이지가 틀린 숫자를 자랑하는 게 최악이라, 원장은 원본(explorer.html·
    archive.html의 전략 배열)에서 **파싱해서** 만든다.

원본이 왜 HTML인가
    전략 목록은 explorer.html 안의 JS 배열이 정본이다(사람이 손으로 관리하는 리서치 산출물).
    별도 JSON으로 옮기면 이중 관리가 되므로, 옮기지 않고 여기서 읽어 집계만 굽는다.
    CI가 이 파일을 다시 만들어 커밋본과 비교하므로 배열을 고치고 원장을 안 굽는 실수는 막힌다.
"""
from __future__ import annotations
import io, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def _slug(n: str) -> str:
    """explorer.html의 _slug·archive.html의 slug와 **같은 규칙**(딥링크 #s-<슬러그>)."""
    s = re.sub(r"[^0-9a-z가-힣]+", "-", str(n).lower())
    return s.strip("-")


def _records(js: str):
    """`{n:"…" … }` 레코드를 순서대로 잘라낸다(따옴표 유무 무관)."""
    idx = [m.start() for m in re.finditer(r'\{\s*"?n"?\s*:\s*"', js)]
    for i, a in enumerate(idx):
        yield js[a: idx[i + 1] if i + 1 < len(idx) else len(js)]


def _field(rec: str, key: str):
    m = re.search(r'"?%s"?\s*:\s*"((?:[^"\\]|\\.)*)"' % key, rec)
    return m.group(1).replace('\\"', '"') if m else None


def _array(path: str, var: str = "D") -> str:
    """`var D=[ … ];` 블록만 떼어낸다. 대괄호 균형으로 끝을 찾는다(문자열 안 괄호 무시).

    2026-07-23 잠금 대응: 페이지가 AES 게이트(암호문)면 평문은 저장소 밖 _build/pages/에 있다.
    게이트를 파싱할 수는 없으므로 평문 사본으로 대체하고, 없으면 명확히 중단한다."""
    src = io.open(path, encoding="utf-8").read()
    # 잠금 게이트 감지 — validate_site.is_locked와 동일 규칙 유지(어긋나면 한쪽만 게이트를 평문 취급)
    if "crypto.subtle.decrypt" in src and re.search(r"var (?:P|PAYLOAD)=\{salt:", src):
        pp = os.path.join(os.path.dirname(os.path.abspath(path)), "_build", "pages", os.path.basename(path))
        if not os.path.exists(pp):
            raise SystemExit(f"{os.path.basename(path)}: 잠금 페이지인데 평문(_build/pages/)이 없음 — "
                             "평문 사본을 두거나 잠금 PC에서 실행할 것")
        plain_txt = io.open(pp, encoding="utf-8", newline="").read()   # 바이트 정확(지문 계약)
        # 지문(ph) 대조 — 낡은 사본으로 verdicts.json을 굽는 사고 방지
        m_ph = re.search(r'ph:"([0-9a-f]{64})"', src)
        if m_ph:
            import hashlib
            if hashlib.sha256(plain_txt.encode("utf-8")).hexdigest() != m_ph.group(1):
                raise SystemExit(f"{os.path.basename(path)}: 평문 사본이 배포 암호문과 불일치(지문 상이) — "
                                 "_build/pages 갱신 후 다시 실행할 것")
        src = plain_txt
    m = re.search(r"var\s+%s\s*=\s*\[" % var, src)
    if not m:
        raise SystemExit(f"{os.path.basename(path)}: var {var}=[ 를 찾지 못함")
    i = m.end() - 1
    depth, j, instr, esc = 0, i, False, False
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
            if depth == 0:
                return src[i: j + 1]
        j += 1
    raise SystemExit(f"{os.path.basename(path)}: var {var} 배열이 닫히지 않음")


def build(root: str = ROOT) -> dict:
    ex = list(_records(_array(os.path.join(root, "explorer.html"))))
    ar = list(_records(_array(os.path.join(root, "archive.html"))))

    def grp(v):
        # slug은 **이름이 아니라 불변 id(sid)** 에서 온다 — 이름을 고쳐도 딥링크가 살아 있어야 한다.
        return [{"n": _field(r, "n"), "slug": _field(r, "sid") or _slug(_field(r, "n")),
                 "alias": _field(r, "alias")}
                for r in ex if _field(r, "v") == v]

    deploy, marginal, rej_cmp = grp("deploy"), grp("marginal"), grp("reject")
    cats = []
    for r in ar:
        c = _field(r, "c")
        if c and c not in cats:
            cats.append(c)
    if not deploy or not ar:
        raise SystemExit("판정 원장 파싱 실패 — 배열 구조가 바뀌었는지 확인")
    return {
        "note": "explorer.html·archive.html의 전략 배열에서 파싱한 집계. 홈은 이 파일만 읽고 숫자를 적지 않는다.",
        "deploy": deploy, "marginal_n": len(marginal), "deploy_n": len(deploy),
        "reject_compare_n": len(rej_cmp), "explorer_n": len(ex),
        "archive_n": len(ar), "archive_cats": len(cats),
        "reject_total": len(ar) + len(rej_cmp),
    }


if __name__ == "__main__":
    import sys
    doc = build()
    p = os.path.join(ROOT, "data", "verdicts.json")
    if "--check" in sys.argv:
        cur = json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None
        same = cur == doc
        print("일치" if same else "불일치 — python build/verdicts_gen.py 로 다시 구울 것")
        raise SystemExit(0 if same else 1)
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"판정 원장: 배포 {doc['deploy_n']} · 제한적 유효 {doc['marginal_n']} · "
          f"기각 {doc['reject_total']}(아카이브 {doc['archive_n']} + 대조 {doc['reject_compare_n']}) "
          f"· 아카이브 카테고리 {doc['archive_cats']}")
