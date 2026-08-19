# -*- coding: utf-8 -*-
"""build/refresh_13f_history.py — 13F 보유 이력을 분기별로 모은다 → data/guru_history.json

왜 따로 만드나. 기존 build/refresh_13f.py는 SEC **분기 벌크 데이터셋**(ZIP 180MB)에서
최신 한 분기만 뽑는다. 과거를 복제하려면 수십 분기를 받아야 해서 '무거워서 못 한다'로
남겨뒀는데, 길이 하나 더 있었다 — **운용사별 EDGAR 제출**을 직접 읽으면 제출당 약 44KB다.
18개 운용사 × 약 40분기 = 40MB 안쪽. 벌크의 1/100이다.

CUSIP→티커는 refresh_13f.py의 FTD 방식을 그대로 재사용한다(13F는 티커를 안 적는다).
그 매핑은 **현재 시점** 기준이라, 과거에 티커가 바뀐 종목은 놓친다 — 한계에 적는다.

  python build/refresh_13f_history.py            # 전체
  python build/refresh_13f_history.py --q 20     # 최근 20분기만
"""
from __future__ import annotations
import io, json, os, re, statistics, sys, time, urllib.request
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from refresh_13f import GURUS, PREDECESSOR, cusip_map, fold_class  # noqa: E402  명단·매핑·클래스표를 복제하지 않는다

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "guru_history.json")
UA = {"User-Agent": os.environ.get("SEC_UA") or "yeodoo-lab globalkbam@gmail.com"}
SLEEP = 0.14          # SEC 권고 8 req/s 이내


def get(u, timeout=60):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception:
            if k == 3:
                raise
            time.sleep(1.5 * (k + 1))
    return b""


def filings(cik):
    """이 운용사의 13F-HR 전부 — (보고분기, 공시일, accession, 서식). 'recent' 밖의 오래된 것도 합친다.

    ⚠ 공시일(filingDate)을 반드시 들고 온다. 이게 없으면 '리밸런스 시점에 이 정보가 공개돼
      있었는가'를 판정할 방법이 저장소 안에 아예 없어진다 — 백테스트의 룩어헤드를 확인할 수단이
      사라진다는 뜻이다. 예전엔 form·reportDate·accession만 담고 filingDate를 버렸다.
    """
    j = json.loads(get("https://data.sec.gov/submissions/CIK%010d.json" % cik).decode())
    out = []

    def take(rec):
        fd = rec.get("filingDate") or []
        for i, f in enumerate(rec.get("form") or []):
            if f in ("13F-HR", "13F-HR/A"):
                out.append((rec["reportDate"][i], (fd[i] if i < len(fd) else ""),
                            rec["accessionNumber"][i], f))
    take(j["filings"]["recent"])
    for extra in (j["filings"].get("files") or []):
        try:
            take(json.loads(get("https://data.sec.gov/submissions/" + extra["name"]).decode()))
            time.sleep(SLEEP)
        except Exception:
            pass
    return out


TAG = re.compile(r"<(?:\w+:)?(nameOfIssuer|cusip|value|sshPrnamt|putCall)>([^<]*)</", re.I)


def holdings(cik, acc):
    """정보표 XML → [(cusip, 가치, 주식수, 발행사명)]. 파일명이 제출마다 달라 index.json으로 찾는다.

    발행사명을 같이 돌려주는 이유. 우리 유니버스(518종목) 밖 종목은 CUSIP→티커 매핑이
    없어 티커를 못 붙이는데, 13F 원문에는 nameOfIssuer가 들어 있다. 이름만 있어도
    '이 운용사가 무엇을 들고 있나'는 보여줄 수 있다 — 버리면 포트폴리오의 절반이 사라진다.
    """
    a = acc.replace("-", "")
    base = "https://www.sec.gov/Archives/edgar/data/%d/%s/" % (cik, a)
    try:
        idx = json.loads(get(base + "index.json").decode())
    except Exception:
        return []
    names = [x["name"] for x in idx["directory"]["item"] if x["name"].lower().endswith(".xml")]
    # primary_doc은 표지다 — 정보표는 그 외의 XML이다
    cand = [x for x in names if "primary_doc" not in x.lower()]
    rows = []
    for nm in cand:
        try:
            body = get(base + nm).decode("utf-8", "replace")
        except Exception:
            continue
        if "<nameOfIssuer" not in body and "nameOfIssuer" not in body:
            continue
        cur = {}
        # ⚠ 행을 끊는 지점은 **nameOfIssuer 하나뿐**이다. 예전엔 sshPrnamt 에서도 끊었는데,
        #   13F 정보표의 태그 순서가 … value → sshPrnamt → putCall … 이라서 그렇게 끊으면
        #   putCall 이 **다음 종목의 dict** 로 들어간다. 옵션 필터가 엉뚱한 행을 지우게 된다.
        for m in TAG.finditer(body):
            k, v = m.group(1).lower(), m.group(2).strip()
            if k == "nameofissuer":
                if cur.get("cusip"):
                    rows.append(cur)
                cur = {}
            cur[k] = v
        if cur.get("cusip"):
            rows.append(cur)          # 마지막 종목 — 뒤에 nameOfIssuer 가 없어 flush 가 안 된다
        if rows:
            break
    out = []
    for r in rows:
        # 콜/풋은 보통주 보유가 아니다 — 벌크 경로(refresh_13f.py)는 예전부터 버리는데
        # 이력 경로만 putCall 태그를 읽지도 않아 옵션 노셔널이 보통주 가치에 합산돼 있었다.
        # 실측(2026-03-31, 같은 분기 벌크 대비): 듀케인 AMZN 5.37배 · 소로스 CRWV 7.46배.
        # 풋이면 방향이 반대이므로, 이 값으로 복제를 만들면 숏을 롱으로 뒤집어 산다.
        if (r.get("putcall") or "").strip():
            continue
        try:
            out.append((r["cusip"].strip().upper()[:9],
                        float(r.get("value") or 0), float(r.get("sshprnamt") or 0),
                        (r.get("nameofissuer") or "").strip()))
        except (KeyError, ValueError):
            pass
    return out


def main() -> int:
    nq = None
    if "--q" in sys.argv:
        nq = int(sys.argv[sys.argv.index("--q") + 1])

    st = json.load(io.open(os.path.join(DATA, "stocks.json"), encoding="utf-8"))
    uni = {s["t"] for s in st["stocks"]}
    print("CUSIP→티커 매핑(FTD) 수집…")
    cmap = cusip_map(uni)
    print("  CUSIP %d개" % len(cmap))

    hist = {}          # {분기: {cik: {티커: 가치}}}
    shs = {}           # {분기: {cik: {티커: 주식수}}} — 제출 단위 판정에만 쓰고 파일에는 안 넣는다
    vraw = {}          # {분기: {cik: {티커: 가치}}} — **클래스 접기 전** 값. 단위 판정 전용.
    fdates = {}        # {분기: {cik: 공시일}} — 리밸런스 시점에 공개돼 있었는지 판정용
    names = {}
    # 운용사별 커버리지를 남긴다 — 명단에 이름이 있는데 데이터가 0인 것을 조용히 넘기면,
    # '18명을 봤다'고 적고 실제로는 17명만 본 상태가 된다(현행 guru.json이 그랬다).
    cover = {}
    # 🚨 법인이 바뀐 곳은 **옛 법인도 같이 받아** 새 CIK 자리에 이어 붙인다.
    #   안 그러면 이력이 통째로 끊긴다 — 실측(2026-08-19): 퍼싱스퀘어가 새 법인으로
    #   갈아타면서 13년 성과가 사라지고 «성과 없음» 이 됐다.
    #   ⚠ 여기는 분기별로 담기만 하는 자리라 이어 붙여도 기준 분기 선택을 흔들지 않는다
    #     (refresh_13f 의 최신분기 선택에 넣었다가 27곳이 한 분기 밀린 사고와 다른 자리다).
    _roster = dict(GURUS)
    for _succ, _pred in PREDECESSOR.items():
        if _pred not in _roster:
            _roster[_pred] = GURUS.get(_succ, "승계 전 법인")
    for cik, label in _roster.items():
        try:
            fl = filings(cik)
        except Exception as e:
            print("  ❌ %-28s %s" % (label, e)); continue
        # 분기마다 **원본 13F-HR 하나**. 같은 분기에 원본이 여럿이면 공시일이 늦은 것.
        #
        # ⚠⚠ 수정보고(13F-HR/A)는 쓰지 않는다. 예전 코드는 `for rd, acc, form in sorted(fl): best[rd]=acc`
        #   로 **accession 문자열 사전순 마지막**을 골랐다(시간순 보장도 아니다). 그래서 기밀취급
        #   해제용 /A — 원본 전체가 아니라 '이제 공개하는 몇 종목만' 담은 제출 — 이 포트폴리오 전체를
        #   덮어썼다. 실측 오염 18셀, 버크셔는 2023Q3·Q4 **두 분기 연속 CB 100%**였다.
        #   복제 성과에 미친 크기: 버크셔 CAGR 15.19% → 11.15%(4.04%p).
        #   더 나쁜 것은 방향이다 — /A 로 늦게 공개된 포지션은 리밸런스 시점에 시장이 몰랐던 것이라
        #   그걸 100% 비중으로 잡으면 확정적 룩어헤드다(실측 리밸 후 3개월 +3.42%p, 18셀 중 13셀 양수).
        #   원본만 쓰면 '그때 공개돼 있던 것'이 되어 이 문제가 정의상 사라진다.
        #   ※ 벌크 경로(refresh_13f.py)는 RESTATEMENT 를 교체 적용하는데, 그쪽은 '지금 시점의 정확한
        #     잔고'를 만드는 화면용이라 규약이 다른 것이 맞다. 여기는 백테스트 입력이다.
        best, filed, n_amend = {}, {}, 0
        for rd, fdate, acc, form in sorted(fl):
            if form != "13F-HR":
                n_amend += 1
                continue
            if rd not in best or fdate >= filed.get(rd, ""):
                best[rd], filed[rd] = acc, fdate
        qs = sorted(best)[-nq:] if nq else sorted(best)
        got = 0
        for rd in qs:
            try:
                hs = holdings(cik, best[rd])
            except Exception:
                hs = []
            time.sleep(SLEEP)
            if not hs:
                continue
            # 🚨 복수 클래스를 여기서 접는다(2026-08-18). 화면 경로(refresh_13f.py)는
            #   2026-08-16 부터 접는데 **이력 경로만 안 접고 있었다** — 같은 «경로가 둘이라
            #   갈린다» 자리다. 그래서 13F 컨빅션 복제의 상위 10칸 중 2칸을 GOOG·GOOGL 이
            #   같은 회사로 썼다: 「10종목 동일가중」이 실제로는 9개 회사이고 알파벳이 20%였다.
            #   ⚠ 표는 refresh_13f.SHARE_CLASS 한 곳에만 있다. 여기 복사하지 않는다.
            # ⚠ 단위 판정(아래 rat)은 **접기 전** 값으로 한다. 접으면 (가치/주식수)/가격 이
            #   무너진다 — BRK.A 와 BRK.B 는 주당 가격이 1500배 다르다. 알파벳처럼 가격이
            #   거의 같은 짝은 무해하지만, 무해한 짝만 있다고 가정하지 않는다.
            m, msh, mraw = {}, {}, {}
            for cu, val, _sh, _nm in hs:
                t0 = cmap.get(cu)
                if t0:
                    t = fold_class(t0)
                    m[t] = m.get(t, 0.0) + val            # 출력 — 접은 것
                    mraw[t0] = mraw.get(t0, 0.0) + val    # 단위 판정 — 접기 전
                    msh[t0] = msh.get(t0, 0.0) + _sh
            if m:
                hist.setdefault(rd, {})[str(cik)] = m
                # 주식수는 저장하지 않는다 — 아래 단위 정규화에만 쓰고 버린다.
                shs.setdefault(rd, {})[str(cik)] = msh
                vraw.setdefault(rd, {})[str(cik)] = mraw
                fdates.setdefault(rd, {})[str(cik)] = filed.get(rd) or ""
                got += 1
        # 승계 전 법인의 분기는 **새 CIK 자리로 옮긴다**(같은 운용사이므로).
        _dst = None
        for _succ, _pred in PREDECESSOR.items():
            if cik == _pred:
                _dst = str(_succ)
                break
        if _dst:
            # ⚠ 정본은 hist 다(vraw 는 단위 판정용 사본). 한쪽만 옮기면 산출물이 안 바뀐다 —
            #   실측으로 vraw 만 옮겼더니 최종 파일에 옛 CIK 가 52분기 그대로 남았다.
            _moved = 0
            for _rd in list(hist):
                if str(cik) in hist[_rd] and _dst not in hist[_rd]:
                    hist[_rd][_dst] = hist[_rd].pop(str(cik))
                    if str(cik) in (vraw.get(_rd) or {}):
                        vraw[_rd][_dst] = vraw[_rd].pop(str(cik))
                    fdates.setdefault(_rd, {})[_dst] = fdates.get(_rd, {}).pop(str(cik), "")
                    _moved += 1
                else:
                    hist[_rd].pop(str(cik), None)
                    (vraw.get(_rd) or {}).pop(str(cik), None)
            print("  [승계] 옛 법인 CIK %d 의 %d분기를 %s 자리로 옮김" % (cik, _moved, _dst))
            continue
        names[str(cik)] = label
        cover[str(cik)] = {"name": label, "n_q": got, "n_filings": len(best),
                           "n_amend_skipped": n_amend,
                           "last": (sorted(best)[-1] if best else None)}
        print("  %-28s 분기 %d/%d%s"
              % (label, got, len(qs),
                 ("   ⚠ 마지막 제출 %s — 이 CIK는 더는 13F를 안 낸다" % sorted(best)[-1])
                 if (best and got == 0) else ""))

    qs = sorted(hist)
    # ── 복제용 월봉 ── 분기 리밸런스라 일봉은 과하다. 월말 종가만 있으면 성과를 낼 수 있고
    # 파일도 1/20로 줄어든다. 이 저장소의 종목 패널은 3년뿐이라 여기서 따로 받는다.
    need = sorted(set().union(*[set(h) for mm in hist.values() for h in mm.values()])) if hist else []
    mpx = {}
    if need:
        try:
            import yfinance as yf
            print("\n복제용 월봉 %d종목 내려받는 중…" % len(need))
            df = yf.download([t.replace(".", "-") for t in need], start="2012-01-01",
                             auto_adjust=True, progress=False, threads=True)["Close"]
            m = df.resample("ME").last()
            months = [d.strftime("%Y-%m") for d in m.index]
            for t in need:
                sym = t.replace(".", "-")
                if sym not in m.columns:
                    continue
                col = m[sym]
                if col.notna().sum() < 12:
                    continue
                mpx[t] = [None if v != v else round(float(v), 4) for v in col.tolist()]
            print("  월 %d개 · 종목 %d/%d" % (len(months), len(mpx), len(need)))
        except Exception as e:
            print("  ❌ 월봉 실패: %s" % e)
            months = []
    else:
        months = []

    # ── 제출 단위 정규화(천$ → 달러) ──────────────────────────────────────
    # 🚨 13F 정보표의 VALUE 는 2023년 규칙 변경 전까지 **천 달러** 단위였다. 이 파일은 52분기를
    #   담으므로 그 전환이 통째로 들어 있다 — 실측: 2022-09-30 까지 전 운용사가 천$, 2022-12-31
    #   부터 전원 달러. 게다가 전환이 늦은 운용사가 있어 **같은 분기 안에서도 눈금이 섞인다**
    #   (2026-03-31 기준 바우포스트·듀케인이 아직 천$, 히말라야는 2024-06-30 에 전환했다).
    #   지금 이 파일을 읽는 유일한 소비처(guru17_backtest)는 운용사·분기 안에서 비중으로
    #   정규화해 1000배가 상쇄되므로 결과가 맞다. 하지만 절대값을 쓰는 소비처가 하나만 생기면
    #   그때 조용히 틀린다 — 파일에 섞인 눈금을 남겨 두는 것 자체가 함정이다.
    #   판정 근거는 같은 잡이 이미 받아 둔 월봉이다(추가 호출 0). 내재주가(가치÷주식수)를
    #   그 분기 월말 종가로 나눈 중앙비가 달러면 ~1, 천$면 ~0.001 이라 세 자릿수가 벌어진다.
    _mi = {mo: i for i, mo in enumerate(months)}
    _scaled = _unknown = 0
    for rd, per_cik in hist.items():
        _px = {}
        _i = _mi.get(rd[:7])
        if _i is not None:
            for t, arr in mpx.items():
                if _i < len(arr) and arr[_i]:
                    _px[t] = float(arr[_i])
        for cik, m in per_cik.items():
            sh = (shs.get(rd) or {}).get(cik) or {}
            vr = (vraw.get(rd) or {}).get(cik) or {}
            rat = [(vr[t] / sh[t]) / _px[t] for t in vr
                   if sh.get(t) and vr.get(t) and _px.get(t)]
            if len(rat) >= 3:
                med = statistics.median(rat)
            elif sum(m.values()) < 1e8:      # 13F 는 13F증권 1억$ 이상일 때 내는 보고다
                med = 0.001
            else:
                _unknown += 1
                continue
            if med < 0.02:
                for t in m:
                    m[t] *= 1000.0
                _scaled += 1
    print("  제출 단위 정규화: %d건 ×1000 · 판정 불가 %d건 (분기×운용사 %d건 중)"
          % (_scaled, _unknown, sum(len(v) for v in hist.values())))

    doc = {
        "note": "운용사별 13F 보유 이력. SEC 분기 벌크 데이터셋(ZIP 180MB) 대신 운용사별 EDGAR "
                "제출을 직접 읽어 모았다 — 제출당 약 44KB라 100배 가볍다.",
        "source": "SEC EDGAR 13F-HR (운용사별 제출)",
        "as_of": qs[-1] if qs else None,
        "n_quarters": len(qs), "n_managers": len(names),
        "quarters": qs, "names": names, "holdings": hist, "coverage": cover,
        # 공시일 — {분기: {cik: "YYYY-MM-DD"}}. 백테스트는 이 날짜가 리밸런스일보다
        # 앞서는지 반드시 확인해야 한다. 없으면 룩어헤드 여부를 물을 수조차 없다.
        "filed": fdates,
        "months": months, "mpx": mpx,
        "empty_managers": [v["name"] for v in cover.values() if v["n_q"] == 0],
        "limits": [
            "CUSIP→티커 매핑은 SEC 공매도 미결제(FTD) 파일에서 만들며 **현재 시점** 기준이다. "
            "과거에 티커가 바뀌었거나 지금 상장폐지된 종목은 매핑되지 않아 빠진다.",
            "13F는 미국 상장 주식 롱 포지션만 담는다. 숏·현금·채권·해외 보유는 안 보이므로 "
            "이 데이터로 만든 '복제'는 운용사의 실제 포트폴리오가 아니다.",
            "분기말 잔고를 45일 뒤에 제출한다. 복제는 그 지연을 반드시 반영해야 한다 — "
            "안 하면 있지도 않은 정보를 쓰는 것이 된다.",
            "우리 유니버스(518종목) 안의 보유만 남긴다. 유니버스 밖 종목은 가격이 없어 못 돌린다. "
            "그래서 이 파일로는 '유니버스 밖에 얼마가 있었나'라는 분모를 알 수 없고, 겹침 비율의 "
            "시계열도 산출할 수 없다.",
            "**원본 13F-HR만 쓰고 수정보고(13F-HR/A)는 버린다.** 기밀취급 해제형 수정보고가 "
            "포트폴리오 전체를 덮어써 오염되던 것을 막기 위해서다. 대신 나중에 정정된 내용은 "
            "반영되지 않는다 — 백테스트에는 이쪽이 맞고(그때 공개된 것), 현재 잔고를 보려면 "
            "벌크 경로(refresh_13f.py)의 guru.json 을 볼 것.",
            "콜/풋은 제외한다(putCall 태그). 옵션 노셔널을 보통주 비중으로 섞으면 방향이 "
            "반대인 포지션을 롱으로 복제하게 된다.",
        ],
    }
    def _d(o_):
        return json.dumps(o_, ensure_ascii=False, separators=(",", ":"))
    parts = []
    for k, v in doc.items():
        if k in ("mpx", "holdings"):     # 줄을 나눠 git 델타가 먹게 한다(주 1회 갱신 대상)
            parts.append('%s:{\n%s\n}' % (_d(k), ",\n".join(' %s:%s' % (_d(a), _d(b))
                                                              for a, b in v.items())))
        else:
            parts.append('%s:%s' % (_d(k), _d(v)))
    io.open(OUT, "w", encoding="utf-8").write("{\n" + ",\n".join(parts) + "\n}\n")
    print("\n분기 %d개(%s ~ %s) · 운용사 %d · %.1fMB"
          % (len(qs), qs[0] if qs else "—", qs[-1] if qs else "—", len(names),
             os.path.getsize(OUT) / 1e6))
    return 0


if __name__ == "__main__":
    # 멈춤 사유를 체크런 주석으로 올린다 — 로그 본문은 사내 PC 에서 못 받는다(build/gate.py 참조)
    import gate
    gate.run(main, "13F 이력")
