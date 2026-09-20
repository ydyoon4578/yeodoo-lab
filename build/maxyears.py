# -*- coding: utf-8 -*-
"""build/maxyears.py — 백테스트 길이 상한을 **펀드 비교 쪽에도** 건다.

🚨 2026-09-20 — 오늘 낸 사전등록 다섯이 이 규약을 어겼다.
   `MAX_YEARS = 10` 은 **2026-08-13 사용자 결정**이고 그 주석이 이렇게 적혀 있다 —

     «전략은 최근일자부터 최대 10년. 어떤건 14.4년, 16.6년 등 더 길게 비교한 것도 있더라.»
     «종목 랩만 자르고 여기를 두면 한 화면에서 10년짜리와 20년짜리가 나란히 서서
       비교가 성립하지 않는다.»

   그 상수는 `tech_backtest.py` · `asset_backtest.py` 등 **네 곳**에 같은 값으로 있고
   `validate_site.py` 가 일치를 검사한다. 그런데 **펀드 비교 스크립트들**
   (valsleeve · guruacc_fund · residmom_fund · runs_fund · runs2_fund · revcomp)은
   그 상수를 아예 안 읽고 **146개월(12.2년)** 로 쟀다. 게시 산출물이 아니라는 이유로
   새로 쓴 코드가 규약 밖에 있었던 것이다 — **규약은 코드가 아니라 랩에 거는 것이다.**

무엇을 하나
   창을 자르는 한 함수를 여기 두고, 위 스크립트들이 이것을 부르게 한다.
   ⚠ **이미 낸 판정을 이걸로 다시 읽지 않는다.** 등록은 그때의 창으로 이뤄졌고,
     창을 바꿔 판정을 고쳐 읽으면 그것이 바로 사후 조정이다.
     10년판은 **재진술(robustness restatement)** 로 따로 싣고, 판정이 갈리면 그 사실을 적는다.
"""
from __future__ import annotations
import os
import sys

import pandas as pd

MAX_YEARS = 10          # tech_backtest.py · asset_backtest.py 와 같은 값이어야 한다


def check_const():
    """네 곳의 상수와 같은 값인지 확인한다. 다르면 소리 내어 죽는다."""
    import io, re
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = []
    for f in ("tech_backtest.py", "asset_backtest.py"):
        p = os.path.join(root, "build", f)
        if not os.path.exists(p):
            continue
        m = re.search(r"^MAX_YEARS\s*=\s*(\d+)", io.open(p, encoding="utf-8").read(), re.M)
        if m and int(m.group(1)) != MAX_YEARS:
            bad.append("%s=%s" % (f, m.group(1)))
    if bad:
        raise SystemExit("🚨 MAX_YEARS 불일치: %s vs maxyears.py=%d" % (" · ".join(bad), MAX_YEARS))
    return True


def cap(idx, max_years=MAX_YEARS):
    """월 PeriodIndex 를 **끝에서부터** max_years 로 자른다.

    끝을 고정하고 앞을 자른다 — «최근일자부터 최대 10년» 이라는 결정의 문장 그대로다.
    """
    if len(idx) == 0:
        return idx
    n = int(round(max_years * 12))
    return idx[-n:] if len(idx) > n else idx


def cap_series(s, max_years=MAX_YEARS):
    return s.reindex(cap(s.index, max_years))


def note(idx_full, idx_capped):
    return ("창 %d개월(%s~%s) → 10년 상한 %d개월(%s~%s)"
            % (len(idx_full), idx_full[0], idx_full[-1],
               len(idx_capped), idx_capped[0], idx_capped[-1]))


if __name__ == "__main__":
    check_const()
    print("MAX_YEARS = %d — tech_backtest·asset_backtest 와 일치" % MAX_YEARS)
    i = pd.period_range("2014-07", "2026-08", freq="M")
    print(note(i, cap(i)))
