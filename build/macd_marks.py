# -*- coding: utf-8 -*-
"""MACD(12,26,9) 신호선 교차 타점 — 종목 신호 화면의 스윙 타점 옆에 두는 표시용 계열.

만드는 것 — 종목마다 최근 3년의 교차일 인덱스(data/stocks.json 의 pxd_dates 좌표계).
    b: MACD선이 신호선을 **상향** 돌파한 날   s: **하향** 돌파한 날

🚨 이 랩은 이것을 이미 재 놨고, 결과를 화면이 함께 말해야 한다. build/signal_lab 산출
  (data/signal_lab.json · 518종 · 2010-01~2026-08 · 대조군 동일가중 β조정)에서
  MACD 계열 넷이 전부 **구별 불가**이고, 그중 매수 둘은 **부호가 원하는 방향의 반대**다:

      MACD 골든크로스(0선 아래)  매수   h5 t −2.79 · h10 −1.06 · h20 +0.23
      MACD 0선 상향             매수   h5 t −1.48 · h10 −2.10 · h20 −0.26
      MACD 데드크로스(0선 위)    매도   h5 t −0.32 · h10 −1.10 · h20 −1.66
      MACD 0선 하향             매도   h5 t −0.48 · h10 −0.26 · h20 +0.26

  즉 '골든크로스에 사면 5일 뒤 대조군보다 못했다'가 이 표본의 실측이다(임계 3.18 미달이라
  판정은 구별 불가지만 부호가 반대다). **그러므로 이 계열은 매매 신호가 아니라 표시다.**
  화면이 그 사실을 적지 않으면 이 파일을 만드는 것 자체가 거짓말이 된다.

⚠ 왜 별도 파일인가 — 교차는 스윙 타점보다 3~4배 잦다(종목당 185개 대 700개 남짓).
  stocks.json(948KB)에 넣으면 본체가 배로 커지고, 그 파일은 화면이 첫 화면에서 통째로 받는다.
  최근 3년만 담아 따로 두고, 필요한 화면이 따로 받는다.
⚠ 왜 refresh_stocks 안이 아닌가 — 거기가 제자리이긴 하나 그 스크립트는 네트워크 수집을
  같이 한다. 이 계산은 이미 저장된 종가만 있으면 되므로 분리해 두면 수집 실패와 무관하게 돈다.
  대신 워크플로에서 refresh_stocks **뒤에** 돌려야 한다(pxd_dates 좌표계를 공유한다).
"""
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "macd_marks.json")
WIN = 756          # 최근 3년(거래일). 차트 기본 구간과 목록 판정에 충분하다.


def ema(a, n):
    """단순 EMA. pandas 없이 — 이 스크립트는 종가 배열 하나만 쓴다."""
    k = 2.0 / (n + 1)
    out, prev = [], None
    for x in a:
        if x is None:
            out.append(prev)
            continue
        prev = x if prev is None else prev + k * (x - prev)
        out.append(prev)
    return out


def marks(px):
    """(상향 교차 인덱스, 하향 교차 인덱스). refresh_stocks.macd 와 같은 (12,26,9)."""
    e12, e26 = ema(px, 12), ema(px, 26)
    line = [None if (a is None or b is None) else a - b for a, b in zip(e12, e26)]
    sig = ema(line, 9)
    b, s, prev = [], [], None
    for i in range(len(px)):
        if line[i] is None or sig[i] is None:
            continue
        d = line[i] - sig[i]
        if prev is not None:
            if prev <= 0 < d:
                b.append(i)
            elif prev >= 0 > d:
                s.append(i)
        prev = d
    return b, s


def main():
    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    D = st["pxd_dates"]
    n = len(D)
    lo = max(0, n - WIN)
    out, miss, nb, ns = {}, [], 0, 0
    for s in st["stocks"]:
        t = s["t"]
        p = os.path.join(DATA, "sd", "%s.json" % t)
        if not os.path.exists(p):
            miss.append(t)
            continue
        try:
            px = json.load(io.open(p, encoding="utf-8")).get("pxd")
        except Exception:
            miss.append(t)
            continue
        if not px or len(px) != n:
            # 좌표계가 다르면 마커 인덱스가 엉뚱한 날을 가리킨다 — 조용히 넣지 않는다.
            miss.append(t)
            continue
        b, sl = marks(px)
        b = [i for i in b if i >= lo]
        sl = [i for i in sl if i >= lo]
        if not b and not sl:
            continue
        out[t] = {"b": b, "s": sl}
        nb += len(b); ns += len(sl)
    doc = {
        "note": "MACD(12,26,9) 신호선 교차일 — data/stocks.json 의 pxd_dates 인덱스. 최근 %d거래일." % WIN,
        "warn": ("표시용이다. 매매 신호가 아니다. 이 랩이 같은 표본(518종 · 2010-01~)에서 잰 "
                 "MACD 계열 넷은 전부 판정 '구별 불가'이고, 매수 둘은 부호가 반대다 — "
                 "골든크로스 매수의 5일 t 가 −2.79 로, 산 뒤 대조군보다 못했다."),
        "src": "data/signal_lab.json (macd-gold · macd-zup · macd-dead · macd-zdn)",
        "as_of": st.get("as_of"), "win": WIN, "d0": D[lo], "d1": D[-1],
        "n_stocks": len(out), "n_buy": nb, "n_sell": ns,
        "marks": out,
    }
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("MACD 교차 타점 — %d종목 · 매수 %d · 매도 %d (%s ~ %s)"
          % (len(out), nb, ns, D[lo], D[-1]))
    if miss:
        print("  ⚠ 건너뜀 %d종(상세 파일 없음·길이 불일치): %s"
              % (len(miss), " ".join(miss[:10]) + (" …" if len(miss) > 10 else "")))
    print("→ %s (%.0fKB)" % (OUT, os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
