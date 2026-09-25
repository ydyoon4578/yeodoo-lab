# -*- coding: utf-8 -*-
"""build/t_guard.py — 배치 T B8 사이트 경계(D1 · D3): L 층 산출물 · 라이선스 원자료가 저장소 · 사이트 자료에 없다.

표준 라이브러리만 쓴다 — build/validate_site.py(CI · 표준 라이브러리만)가 매 푸시 · 매일 부르고, 굽기 전
build/t_run.py 의 판 점검(frozen_check)도 같은 함수를 부른다(두 벌이면 갈린다). 파일 이름 · 문자열 표식 · 명세 구조만 본다(수익 없음).

  ① 저장소(추적 + 추적 안 된 비무시 파일)에 `_tbatch*` 산출 이름이 없다
  ② 라이선스 원자료로 보이는 파일 이름(Cboe `*_History` · AQR 파일 · `SENTIMENT.xlsx` · Shiller `ie_data`)이 없다
  ③ `data/_tb*` 에는 명세와 명세가 저장소에 고정한 연방 통계 파일만
  ④ 사이트 파일(뿌리 `*.html` · `js/*.js` · `data/*.json` · `data/_qfwd/`)에 배치 T 산출 표식이 없다
  ⑤ 명세가 값 계열처럼 보이는 목록을 담지 않고 등록 밖 키가 없으며, 저장소에 고정된 것은 연방 통계뿐이다

  python build/t_guard.py          # 결과 JSON · 위반이 있으면 1
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

LICENSED_NAME_MARKS = ("BXMD_History", "BXM_History", "PUT_History", "VIX_History", "SPX_History",       # Cboe
                       "Time-Series-Momentum-Factors", "Betting-Against-Beta",                            # AQR
                       "SENTIMENT.xlsx", "ie_data")                                                       # Wurgler · Shiller
OUTPUT_CONTENT_MARKS = (b'"H_T0"', b'"H_T0_sens_exT02"', b'"n_arms_L"', b"_tbatch.json", b"_tbatch.run.json", b"_tbatch.public.json")
MANIFEST_DS_KEYS = {"cards", "design_sha256", "design_state", "license", "live", "pinned", "pinned_in", "source", "summary", "url",
                    "vs_design_expect"}
MANIFEST_TOP_KEYS = {"note", "generated_at", "cache_root", "design", "decisions", "availability", "forbidden_signals", "cache_identity",
                     "pylib", "datasets"}


def _git(root, *a):
    return subprocess.run(["git", "-C", root] + list(a), capture_output=True, text=True, encoding="utf-8")


def _numeric_list(x, depth=0):
    """값 계열처럼 보이는 것(숫자 넷 이상 목록)이 있는가 — 명세는 구조만 담아야 한다."""
    if depth > 8:
        return False
    if isinstance(x, dict):
        return any(_numeric_list(v, depth + 1) for v in x.values())
    if isinstance(x, (list, tuple)):
        nums = [v for v in x if isinstance(v, (int, float)) and not isinstance(v, bool)]
        return len(nums) > 3 or any(_numeric_list(v, depth + 1) for v in x)
    return False


def site_guard(root=ROOT):
    """돌려주는 것 {ok, bad[], n_bad, n_files, n_scanned}. git 이 없으면(ls-files 실패) ok=False."""
    bad = []
    ls = _git(root, "ls-files", "-co", "--exclude-standard")
    if ls.returncode != 0:
        return {"ok": False, "bad": ["git ls-files 실패: %s" % ls.stderr.strip()[:200]], "n_bad": 1, "n_files": 0, "n_scanned": 0}
    files = [f for f in ls.stdout.splitlines() if f]
    man_p = os.path.join(root, "data", "_tb_manifest.json")
    allowed_tb = {"data/_tb_manifest.json"}
    if os.path.exists(man_p):
        man = json.load(io.open(man_p, encoding="utf-8"))
        top = set(man) - MANIFEST_TOP_KEYS
        if top:
            bad.append("명세에 등록 밖 머리 키 %s" % sorted(top))
        for k, v in (man.get("datasets") or {}).items():
            pin = str(v.get("pinned_in") or "")
            if pin.startswith("repo:"):
                allowed_tb.add(pin[5:])
            extra = set(v) - MANIFEST_DS_KEYS
            if extra:
                bad.append("명세 %s 에 등록 밖 키 %s" % (k, sorted(extra)))
            if _numeric_list(v.get("summary")) or _numeric_list(v.get("live")):
                bad.append("명세 %s 가 값 계열처럼 보이는 목록을 담는다" % k)
            if pin.startswith("repo:") and v.get("source") not in ("fred", "alfred"):
                bad.append("명세 %s 가 연방 통계가 아닌데 저장소에 고정돼 있다(%s)" % (k, pin))
    for f in files:
        b = os.path.basename(f)
        if b.startswith("_tbatch"):
            bad.append("L 층 산출물 이름이 저장소에 있다: %s" % f)
        if any(m in b for m in LICENSED_NAME_MARKS):
            bad.append("라이선스 원자료로 보이는 파일이 저장소에 있다: %s" % f)
        if f.startswith("data/_tb") and f not in allowed_tb:
            bad.append("data/_tb* 에 명세가 허용하지 않은 파일: %s" % f)
    scan = [f for f in files if (("/" not in f and f.endswith(".html")) or (f.startswith("js/") and f.endswith(".js"))
                                 or (f.startswith("data/") and f.count("/") == 1 and f.endswith(".json") and f != "data/_tb_manifest.json")
                                 or (f.startswith("data/_qfwd/")))]
    n_scanned = 0
    for f in scan:
        p = os.path.join(root, f)
        if not os.path.isfile(p):
            continue
        with open(p, "rb") as fh:
            blob = fh.read()
        n_scanned += 1
        hit = [m.decode() for m in OUTPUT_CONTENT_MARKS if m in blob]
        if hit:
            bad.append("사이트 자료 %s 에 배치 T 산출 표식 %s" % (f, hit))
    return {"ok": not bad, "bad": bad[:40], "n_bad": len(bad), "n_files": len(files), "n_scanned": n_scanned}


if __name__ == "__main__":
    g = site_guard()
    print(json.dumps(g, ensure_ascii=False, indent=1))
    raise SystemExit(0 if g["ok"] else 1)
