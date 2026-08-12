#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B11 기술 링크 모멘텀 — **커버리지 프로브**. 사전등록 build/PREREG-2026-08-12-TECHLINK.md §8.

무엇을 재나. 단 하나다 —
  "매 월말 기준 직전 5년 창에 특허 3건 이상인 우리 유니버스 종목이 몇 개인가"
이 숫자(G1)의 중앙값이 90 미만이면 CPC 행렬을 만들 필요가 없다. B7 이 '실명 링크 4종 vs
문턱 30' 에서 멈춘 것과 같은 자리다.

⚠ 그래서 이 프로브는 **CPC 를 받지 않는다.** G1 을 못 넘으면 321MB 를 받을 이유가 없다.
  받는 것은 두 개뿐이다: g_patent(특허번호·등록일) · g_assignee_disambiguated(특허번호·출원인명).

원천: Zenodo record 15783125 — "Final release of PatentsView metadata, granted (12/31/2024)",
      United States Patent and Trademark Office, CC-BY-4.0. 무인증.
      🚨 이 자료는 2024-12-31 에서 얼어붙는다(사전등록 §3). 라이브 신호용이 아니다.

산출: data/_probe_patent_orgs.json — 출원인 조직명 × 등록연도 특허수(2004~2024).
      원자료는 받은 자리에서 지운다(수백 MB 를 저장소에 남기지 않는다).
      ⚠ 이름 매칭은 여기서 하지 않는다. 손검산(G2)이 필요해서 로컬에서 따로 한다.

사용: python build/probe_patents.py
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
import urllib.request
import zipfile
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949) 대비
except Exception: pass

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "_probe_patent_orgs.json")

ZEN = "https://zenodo.org/records/15783125/files/%s?download=1"
F_PATENT = "g_patent.tsv.zip"
F_ASSIGNEE = "g_assignee_disambiguated.tsv.zip"

YEAR_MIN = 2004          # 5년 창이 2009-01 부터 서려면 2004 부터 필요하다
YEAR_MAX = 2024          # 자료가 여기서 끝난다
MIN_TOTAL = 15           # 이보다 적게 낸 조직은 산출물에서 뺀다(파일 크기 — 5년 3건 문턱의 5배)
MAX_ORGS = 40000         # 안전 상한
UA = {"User-Agent": os.environ.get("SEC_UA") or "yeodoo-lab globalkbam@gmail.com"}


def fetch(url, dest):
    """스트리밍 다운로드. 메모리에 통째로 올리지 않는다(수백 MB)."""
    t0 = time.time()
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r, io.open(dest, "wb") as w:
        n = 0
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            w.write(b); n += len(b)
    print("  받음 %-34s %8.1f MB · %.0f초" % (os.path.basename(dest), n / 1e6, time.time() - t0))
    return n


def open_tsv(path):
    """ZIP 안의 유일한 .tsv 를 텍스트로 연다. 헤더는 호출부가 읽는다."""
    z = zipfile.ZipFile(path)
    names = [n for n in z.namelist() if n.lower().endswith((".tsv", ".csv"))]
    if len(names) != 1:
        raise SystemExit("ZIP 안 표 파일이 %d개다(1개를 기대했다): %s" % (len(names), names))
    return z, io.TextIOWrapper(z.open(names[0]), encoding="utf-8", errors="replace")


def col_index(header, *cands):
    """헤더에서 컬럼 위치를 찾는다. 못 찾으면 **실제 헤더를 그대로 보여주고** 멈춘다.

    자료 딕셔너리 PDF 를 원문으로 확인하지 못해 컬럼명이 2차 출처 근거다(사전등록 §3).
    그러니 이름이 다를 가능성을 열어 두되, 조용히 다른 컬럼을 집는 일은 없어야 한다.
    """
    low = [h.strip().strip('"').lower() for h in header]
    for c in cands:
        if c in low:
            return low.index(c)
    raise SystemExit("컬럼 %s 를 못 찾았다. 실제 헤더: %s" % (list(cands), header[:20]))


def main() -> int:
    os.makedirs(DATA, exist_ok=True)
    tmp = os.path.join(DATA, "_probe_tmp")
    os.makedirs(tmp, exist_ok=True)

    # ── 1) 특허번호 → 등록연도 ────────────────────────────────────────────
    p1 = os.path.join(tmp, F_PATENT)
    fetch(ZEN % F_PATENT, p1)
    z, fh = open_tsv(p1)
    header = fh.readline().rstrip("\n").split("\t")
    i_id = col_index(header, "patent_id", "id")
    i_dt = col_index(header, "patent_date", "date")
    ids, yrs = [], []
    n_row = n_skip = 0
    for line in fh:
        p = line.rstrip("\n").split("\t")
        if len(p) <= max(i_id, i_dt):
            n_skip += 1; continue
        pid = p[i_id].strip().strip('"')
        # 실용특허만 — 디자인(D)·재발행(RE)·식물(PP)·특허권부여전공개는 CPC 성격이 다르다
        if not pid.isdigit():
            n_skip += 1; continue
        d = p[i_dt].strip().strip('"')
        if len(d) < 4 or not d[:4].isdigit():
            n_skip += 1; continue
        y = int(d[:4])
        if y < YEAR_MIN or y > YEAR_MAX:
            n_skip += 1; continue
        ids.append(int(pid)); yrs.append(y); n_row += 1
    fh.close(); z.close(); os.remove(p1)
    ids = np.asarray(ids, dtype=np.int64)
    yrs = np.asarray(yrs, dtype=np.int16)
    order = np.argsort(ids, kind="stable")
    ids, yrs = ids[order], yrs[order]
    print("  실용특허 %d건 (%d~%d) · 제외 %d행" % (n_row, YEAR_MIN, YEAR_MAX, n_skip))
    if n_row < 1_000_000:
        raise SystemExit("실용특허가 %d건뿐이다 — 자료가 잘렸거나 컬럼을 잘못 집었다" % n_row)

    # ── 2) 특허번호 → 출원인 조직명 ───────────────────────────────────────
    p2 = os.path.join(tmp, F_ASSIGNEE)
    fetch(ZEN % F_ASSIGNEE, p2)
    z, fh = open_tsv(p2)
    header = fh.readline().rstrip("\n").split("\t")
    i_id = col_index(header, "patent_id", "id")
    i_org = col_index(header, "disambig_assignee_organization", "assignee_organization", "organization")
    NY = YEAR_MAX - YEAR_MIN + 1
    agg, n_hit, n_miss, n_noorg = {}, 0, 0, 0
    for line in fh:
        p = line.rstrip("\n").split("\t")
        if len(p) <= max(i_id, i_org):
            continue
        pid = p[i_id].strip().strip('"')
        if not pid.isdigit():
            continue
        org = p[i_org].strip().strip('"')
        if not org:
            n_noorg += 1; continue
        k = np.searchsorted(ids, int(pid))
        if k >= len(ids) or ids[k] != int(pid):
            n_miss += 1; continue       # 창 밖 연도이거나 실용특허가 아님
        v = agg.get(org)
        if v is None:
            v = agg[org] = [0] * NY
        v[int(yrs[k]) - YEAR_MIN] += 1
        n_hit += 1
    fh.close(); z.close(); os.remove(p2)
    try: os.rmdir(tmp)
    except OSError: pass
    print("  출원인 행 %d건 매칭 · 창밖/비실용 %d · 조직명 없음 %d · 고유 조직 %d"
          % (n_hit, n_miss, n_noorg, len(agg)))
    if n_hit < 1_000_000:
        raise SystemExit("매칭된 출원인 행이 %d건뿐이다 — 조인이 깨졌다" % n_hit)

    # ── 3) 산출 ──────────────────────────────────────────────────────────
    rows = [(o, v, sum(v)) for o, v in agg.items() if sum(v) >= MIN_TOTAL]
    rows.sort(key=lambda x: -x[2])
    rows = rows[:MAX_ORGS]
    doc = {
        "note": "B11 커버리지 프로브 산출물. 출원인 조직명 × 등록연도 실용특허 수. "
                "사이트가 읽지 않는 내부 산출물이다(사전등록 build/PREREG-2026-08-12-TECHLINK.md §8).",
        "source": "PatentsView final release (12/31/2024), United States Patent and Trademark Office. "
                  "Zenodo record 15783125, CC-BY-4.0. https://doi.org/10.5281/zenodo.15783125",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "year_min": YEAR_MIN, "year_max": YEAR_MAX,
        "min_total": MIN_TOTAL,
        "n_orgs_all": len(agg), "n_orgs_kept": len(rows),
        "n_patents": int(n_row), "n_assignee_rows": int(n_hit),
        "orgs": {o: v for o, v, _ in rows},
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    sz = os.path.getsize(OUT) / 1024
    print("→ %s (%.0fKB · 조직 %d/%d)" % (OUT, sz, len(rows), len(agg)))
    for o, v, t in rows[:10]:
        print("   %-46s %6d건" % (o[:46], t))
    # 로그 본문은 사내 PC 에서 못 받는다 — 머릿수치는 체크런 주석으로도 남긴다(build/gate.py 참조)
    print("::notice title=B11 프로브::실용특허 %d건 · 고유 조직 %d · 보관 %d · 산출 %.0fKB"
          % (n_row, len(agg), len(rows), sz), flush=True)
    return 0


if __name__ == "__main__":
    import gate
    gate.run(main, "B11 특허 프로브")
