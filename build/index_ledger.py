# -*- coding: utf-8 -*-
"""월별 지수 편입 원장 — data/index_ledger.json

무엇을 만드나.
  S&P 500 · 나스닥 100 의 **매월말 실제 편입 종목**을 눈으로 넘겨 볼 수 있는 표와,
  "그 시점 종목 자료를 몇 % 갖고 있나" 를 달마다 잰 값.

왜 만드나(사용자 요청 2026-08-13).
  이 랩의 시점정확(PIT) 레그가 쓰는 멤버십이 어떤 것인지 화면에서 볼 수가 없었다.
  pit_backtest.py 는 커버리지를 전체 한 숫자(96.7%)로만 냈고, 그 숫자가 어느 달에
  어느 종목에서 빠진 것인지는 산출물에 없었다. 편향을 재는 레그의 입력이 안 보이면
  그 레그의 수치도 못 믿는다.

원천.
  · 멤버십 — data/index_history.json (위키백과 지수 목록 문서의 **과거 리비전**, CC BY-SA).
    2014-06 부터다. 그 아래는 위키 표에 CIK 컬럼이 없어 개명과 티커 재사용을 구별할 수 없다.
  · 가격  — data/sd/*.json (오늘의 유니버스 518종) + data/_pit_px_cache.json (편출 종목).
    🚨 뒤쪽 캐시는 **gitignore** 라 저장소에 없다. 그래서 커버리지는 **여기서 미리 세어**
      산출물에 숫자로 박는다 — 화면이 11MB 캐시를 읽게 두지 않는다.

⚠ 사내 DB(public.index_constituents)는 쓰지 않는다. 이 저장소는 공개이고,
  사내 DB 산출물은 커밋 금지다(data/pit_members.json 이 그 사유로 걷혔다).
  위키 리비전은 출처·리비전 번호까지 같이 실을 수 있어 오히려 검증이 된다.
"""
import io
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서 ⚠·— 출력 시 UnicodeEncodeError 방지
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "index_ledger.json")

IDX = [("spx", "S&P 500", "List_of_S%26P_500_companies"),
       ("ndx", "나스닥 100", "Nasdaq-100")]


def _pitpx():
    """편출 종목 가격 — 커밋된 기록(pit_px.json) + 로컬 캐시(_pit_px_cache.json) 합집합.

    🚨 2026-08-19 — 종전에는 로컬 캐시만 읽었다. 그 파일은 gitignore 라 러너에는 없고,
      그래서 러너가 이 원장을 구우면 편출 종목이 통째로 «자료 없음» 이 된다.
      이제 커밋되는 data/pit_px.json 이 있으므로 그것을 먼저 읽는다.
    ⚠ 둘 다 있으면 합친다 — 로컬 캐시가 더 신선할 수 있고, 기록이 더 넓을 수 있다
      (사내 DB 로 메운 76종은 기록에만 있다).
    """
    out = {}
    try:
        sl = _load("pit_px.json") or {}
        ds = sl.get("dates") or []
        for t, v in (sl.get("px") or {}).items():
            i0 = v.get("i0") or 0
            out[t] = {ds[i0 + k]: p for k, p in enumerate(v.get("p") or [])
                      if p is not None and i0 + k < len(ds)}
    except Exception as e:
        print("  [주의] pit_px.json 을 못 읽었다(%s)" % str(e)[:50])
    for t, ser in (_load("_pit_px_cache.json") or {}).items():
        if isinstance(ser, dict):
            out.setdefault(t, {}).update(ser)
    return out


def _load(name, default=None):
    try:
        return json.load(io.open(os.path.join(DATA, name), encoding="utf-8"))
    except Exception:
        return default


def month_end_index(dates):
    """거래일 격자에서 각 달의 **마지막 거래일** 위치. 커버리지를 그날 기준으로 잰다.

    왜 월말인가. PIT 레그가 월말에 리밸런스하고 그 시점 점수로 종목을 고른다.
    달 중간의 아무 날이 아니라 **실제로 후보를 세는 날**의 커버리지를 재야 뜻이 있다.
    """
    last = {}
    for i, d in enumerate(dates):
        last[d[:7]] = i
    return last


def mcap_tools():
    """시가총액을 재는 도구 셋 — (주식수 집기, 종가 집기). 못 만들면 (None, None).

    주식수·종가는 랩 본편과 **같은 함수**로 집는다(TB.load_fund + TB.asof_fund).
    사본을 두면 시총 정의가 두 벌이 되고, 이 저장소는 그 유형의 사고를 되풀이해 밟았다.
    편출 종목은 로컬 캐시(_pit_sh_cache · _pit_px_cache)로 메운다 — 없으면 그 종목은
    비중이 안 잡히고, 화면은 그것을 '자료 없음' 으로 이미 표시하고 있다.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import tech_backtest as TB
    except Exception as e:
        print("  [주의] tech_backtest 를 못 읽었다(%s) - 비중 없이 만든다." % str(e)[:50])
        return None, None
    FU = TB.load_fund()
    SHC = _load("_pit_sh_cache.json") or {}
    PXC = _pitpx()
    PXD = {}
    sd = os.path.join(DATA, "sd")
    if os.path.isdir(sd):
        for fn in os.listdir(sd):
            if not fn.endswith(".json"):
                continue
            try:
                j = json.load(io.open(os.path.join(sd, fn), encoding="utf-8"))
            except Exception:
                continue
            PXD[j.get("t") or fn[:-5]] = j.get("pxd") or []

    def _last_at(ser, d):
        """{날짜: 값} 에서 d 이하의 마지막 관측. 잔고·가격 둘 다 시점을 집으면 된다."""
        if not isinstance(ser, dict):
            return None
        best = None
        for k, v in ser.items():
            if k <= d and v is not None and (best is None or k > best[0]):
                best = (k, v)
        return best[1] if best else None

    def shares_at(t, d):
        return TB.asof_fund((FU.get(t) or {}).get("sh"), d) or _last_at(SHC.get(t), d)

    def close_at(t, d, i):
        p = PXD.get(t)
        if p and i < len(p) and p[i] is not None:
            return p[i]
        return _last_at(PXC.get(t), d)

    return shares_at, close_at


def px_months():
    """티커 → 가격이 실제로 있는 달의 집합.

    🚨 '파일이 있다' 와 '그달 값이 있다' 는 다르다. 오늘의 유니버스에 있어도 2014년에
      상장 전이면 pxd 가 None 이다 — 파일 유무로 세면 그 시절 커버리지가 100% 로 나온다.
      값이 None 이 아닌 달만 센다.
    """
    st = _load("stocks.json") or {}
    dates = st.get("pxd_dates") or []
    mend = month_end_index(dates)
    have = {}
    nulls = [0]          # 리스트로 두는 것은 아래 루프에서 더하기 위함이다
    sd = os.path.join(DATA, "sd")
    if os.path.isdir(sd):
        for fn in os.listdir(sd):
            if not fn.endswith(".json"):
                continue
            t = fn[:-5]
            try:
                pxd = (json.load(io.open(os.path.join(sd, fn), encoding="utf-8")) or {}).get("pxd")
            except Exception:
                continue
            if not pxd:
                continue
            ms = set()
            for m, i in mend.items():
                if i < len(pxd) and pxd[i] is not None:
                    ms.add(m)
            if ms:
                have[t] = ms
            # 🚨 입력 지문용 — **상장 후** 생긴 결측만 센다(상장 전 None 은 결측이 아니다).
            #   이 수가 산출물에 박히고, 검증기가 다시 세어 대조한다. 가격을 고쳐 놓고
            #   원장을 안 구우면 두 수가 갈려 바로 잡힌다(2026-08-14 에 실제로 그랬다).
            _seen = False
            for _v in pxd:
                if _v is not None:
                    _seen = True
                elif _seen:
                    nulls[0] += 1
    # 편출 종목 가격 — 커밋된 기록 + 로컬 캐시(합집합). 러너도 읽을 수 있다.
    cache = _pitpx()
    for t, ser in cache.items():
        if not isinstance(ser, dict):
            continue
        ms = have.setdefault(t, set())
        # 월말 거래일이 캐시에 그대로 있진 않을 수 있다(편출 후 잘린 계열). 그달에 값이
        # 하나라도 있으면 '자료를 갖고 있다' 로 센다 — 후보로 세울 수 있다는 뜻이다.
        for d in ser:
            ms.add(d[:7])
    return have, dates, nulls[0]


def main():
    hist = _load("index_history.json")
    if not hist:
        raise SystemExit("data/index_history.json 이 없다 — build/refresh_index_history.py 를 먼저 돌릴 것.")
    months = sorted(hist["months"])
    have, dates, px_nulls = px_months()
    if not have:
        raise SystemExit("가격 자료를 하나도 못 읽었다 — data/sd 와 data/stocks.json 을 확인할 것.")
    grid = set(d[:7] for d in dates)

    # ── 종목 메타(이름·섹터) ────────────────────────────────────────────
    # 오늘의 518종은 members.json, 편출 종목은 pit_sector.json 이 섹터만 준다.
    # ⚠ 이름이 없는 편출 종목은 **티커만** 적는다. 없는 것을 지어내지 않는다.
    meta = {}
    for t, r in ((_load("members.json") or {}).get("members") or {}).items():
        meta[t] = [r.get("name") or "", r.get("sector") or ""]
    for t, s in ((_load("pit_sector.json") or {}).get("sector") or {}).items():
        if t not in meta:
            meta[t] = ["", s or ""]
    # 🚨 편출 종목 이름 — **이미 받아 둔 것을 안 읽고 있었다.** index_history.json 은
    #   위키 표의 CIK 열에서 티커→CIK(795종)와 CIK→{티커: 그때 이름}(692종)을 같이 모아
    #   두는데, 원장은 members.json(오늘의 518종)과 pit_sector.json(PIT 창 편출 87종)만
    #   봤다. 그래서 그 앞 구간 편출 종목이 통째로 '이름 없음' 이었다(실측 262종).
    # ⚠ 여기서 붙는 이름은 **그때의 이름**이다 — AA 는 'Alcoa Inc'(지금 그 CIK 는
    #   Howmet Aerospace 다), ABC 는 'AmerisourceBergen Corp'(지금은 Cencora).
    #   오늘 이름으로 덮으면 그 달의 명단을 오늘 회사로 바꿔 읽게 된다. 티커 키로 집는다.
    # ⚠ 이름을 _ihcik 로 둔다. 아래 이중클래스 블록이 cik_map.json 을 _cik 에 다시 담는데,
    #   같은 이름을 쓰면 순서가 바뀌는 날 조용히 엉뚱한 표를 읽는다(이 저장소가 되풀이 밟은 유형).
    _ih = _load("index_history.json") or {}
    _ihcik, _cnm = _ih.get("cik") or {}, _ih.get("cik_names") or {}
    # 섹터도 같은 파일에서 온다(위키 표의 GICS Sector 열, 2026-08-14 에 파서가 잡기 시작).
    # 🚨 편출 종목 섹터의 **유일한 공개 출처**다 — yfinance 는 사라진 심볼에 아무것도 안 주고
    #   GICS 자체는 라이선스 자료다. pit_sector.json 은 PIT 창(2021-07~) 편출 87종뿐이고
    #   그것도 '오늘 기준' 분류라, 그 앞 구간은 이쪽이 아니면 채울 길이 없었다.
    # ⚠ 여기 값은 **그때의 표기**다. 'Telecommunication Services' 는 2018-09 GICS 개편 전
    #   이름이고 그대로 둔다 — 오늘 이름으로 덮으면 그 시점 분류가 아니게 된다.
    _isec = _ih.get("sector") or {}
    _sected = 0
    for t, sc in _isec.items():
        if t not in meta:
            meta[t] = ["", sc]
            _sected += 1
        elif not meta[t][1]:
            meta[t][1] = sc
            _sected += 1
    # 위키 CIK 열로도 안 채워지는 이름 — 나스닥 전용 종목(Liberty 계열·Qurate·Trip.com 등)은
    # NDX 표에 CIK 열이 없어 끝까지 남는다. EODHD 편출 명단이 그 자리를 메운다.
    # ⚠ 이름만이다. 그 명단에는 섹터가 없다(Code·Name·Country·Exchange·Currency·Type·Isin).
    #   섹터 미상 23종은 이걸로 안 줄어든다 — 줄어든 척하지 않는다.
    # ⚠ **이미 아는 이름을 이 출처로 덮지 않는다.** 위키가 준 '그때 이름' 이 더 정확하다
    #   (AA=Alcoa Inc). EODHD 는 오늘 기준 표기라 개명 후 이름이 올 수 있다.
    _dn = (_load("delisted_names.json") or {}).get("names") or {}
    _dnamed = 0
    for t, r in _dn.items():
        nm = (r or {}).get("name")
        if not nm:
            continue
        if t not in meta:
            meta[t] = [nm, ""]
            _dnamed += 1
        elif not meta[t][0]:
            meta[t][0] = nm
            _dnamed += 1
    _named = 0

    def _put_name(t, nm):
        """이름을 채운다 — **이미 있으면 안 덮는다.** 먼저 온 출처가 더 정확하다."""
        if not nm:
            return 0
        if t not in meta:
            meta[t] = [nm, ""]
            return 1
        if not meta[t][0]:
            meta[t][0] = nm
            return 1
        return 0

    # ① CIK 키 이름(SPX 표) — 그 CIK 가 그때 쓰던 티커의 이름이다.
    for t, k in _ihcik.items():
        _named += _put_name(t, (_cnm.get(k) or {}).get(t))
    # ② 티커 키 이름 — NDX 표는 CIK 열이 없어 ①로는 못 담긴다.
    #    🚨 그래서 지금도 상장 중인 BIDU·JD·NTES·SIRI 가 '이름 없음' 이었다.
    #      파싱은 되고 저장만 안 되던 것이다 — 오늘 같은 유형 세 번째다
    #      (섹터 · 편출 이름 · 이것). 받아 놓고 안 담는 자리를 계속 찾게 된다.
    for t, nm in (_ih.get("name") or {}).items():
        _named += _put_name(t, nm)

    # ── 추정 비중 ────────────────────────────────────────────────────────
    # 🚨 공식 비중이 아니다. S&P·나스닥은 **유동주식 조정**(float-adjusted) 시총으로
    #   비중을 매기는데 여기 시총은 발행주식수 × 종가다. 내부자·정부·모회사 지분이 큰
    #   종목은 실제보다 무겁게 잡히고, 다중 클래스(GOOG/GOOGL 등)는 공식 지수가 합산하는
    #   것을 여기서는 따로 센다. 화면이 그 사실을 반드시 같이 적는다.
    # ⚠ 그래도 싣는 이유: 알파벳순 500줄은 눈으로 읽을 수 없고, **상위 종목의 순서**는
    #   유동주식 조정과 무관하게 대체로 맞는다. 못 하는 것을 하는 척하지 않되,
    #   할 수 있는 근사는 이름을 붙여서 낸다.
    mend = month_end_index(dates)
    sh_at, px_at = mcap_tools()

    # 🚨 이중 클래스 — 같은 CIK 를 쓰는 티커 묶음(FOX/FOXA · GOOG/GOOGL · NWS/NWSA).
    #   SEC 의 주식수(sh)는 **회사 전체**라 클래스마다 그 값을 쓰면 시총을 두 번 센다.
    #   실측으로 알파벳이 GOOGL 5.60% + GOOG 5.58% = 11.18% 로 잡혔다(실제 지수는 합산 ~4%).
    #   → 묶음의 시총을 **한 번만** 세고, 대표 클래스에 몰아 준 뒤 나머지는 0 으로 둔다.
    #     화면은 묶음을 한 줄로 합쳐 적는다. 클래스별로 쪼개는 것은 클래스별 주식수가
    #     있어야 하는데 SEC 원자료가 그걸 안 준다 — 못 하는 것을 지어내지 않는다.
    _cik = (_load("cik_map.json") or {}).get("co") or {}
    _bycik = {}
    for _t, _k in _cik.items():
        _bycik.setdefault(_k, []).append(_t)
    DUAL = {}                      # 티커 → 대표 티커(묶음의 첫 티커)
    for _k, _ts in _bycik.items():
        if len(_ts) > 1:
            _ts = sorted(_ts)
            for _t in _ts:
                DUAL[_t] = _ts[0]

    def wbp(tickers, m):
        """그달 멤버의 비중(bp, 만분율). 시총을 모르는 종목은 0 이고 분모에서도 빠진다.

        🚨 분모를 '전체 멤버' 로 두면 자료가 없는 종목만큼 비중 합이 100% 에 못 미쳐
          상위 종목이 실제보다 가볍게 보인다. **잰 것들 안에서의 비중**으로 두고,
          몇 %를 못 쟀는지는 커버리지가 따로 말한다.
        """
        i = mend.get(m)
        if i is None or sh_at is None:
            return None
        mc = {}
        d = dates[i]
        _done = set()
        for t in tickers:
            rep = DUAL.get(t)
            if rep is not None:
                if rep in _done:
                    continue           # 같은 회사를 이미 셌다
                _done.add(rep)
            s = sh_at(t, d)
            p = px_at(t, d, i)
            if s and p and s > 0 and p > 0:
                mc[rep if rep is not None else t] = s * p
        tot = sum(mc.values())
        if not tot:
            return None
        # 산출물 크기를 위해 만분율 정수로 둔다(0.01% 단위). 147개월 × 600종이라
        # 소수 문자열로 실으면 파일이 세 배가 된다.
        return [int(round(10000.0 * mc.get(t, 0) / tot)) for t in tickers]

    out = {}
    seen = set()
    for key, label, wiki in IDX:
        prev, mm, base = None, {}, None
        for m in months:
            cur = hist["months"][m].get(key)
            if not cur:
                continue                      # 그달 리비전을 못 읽은 것(hist.gaps 에 사유가 있다)
            cur = sorted(cur)
            seen.update(cur)
            rec = {"n": len(cur), "rev": hist["months"][m].get(key + "_rev")}
            # ⚠ w 는 **sorted(cur) 와 같은 순서**다. 화면이 명단을 base+증감으로 되짚어
            #   만들고 같은 정렬을 쓰므로 짝이 맞는다. 길이가 어긋나면 화면이 비중을
            #   버리게 해 둔다 — 어긋난 채 그리면 종목마다 남의 비중을 달게 된다.
            _w = wbp(cur, m)
            if _w:
                rec["w"] = _w
            if prev is None:
                base = {"month": m, "t": cur}
            else:
                rec["add"] = sorted(set(cur) - set(prev))
                rec["drop"] = sorted(set(prev) - set(cur))
            # 커버리지 — 그달 월말에 가격이 있는 멤버 수.
            # ⚠ 격자에 없는 달(오늘 이후·거래일 없음)은 '0%' 가 아니라 **못 잼**이다.
            if m in grid:
                miss = [t for t in cur if m not in have.get(t, ())]
                rec["px"] = len(cur) - len(miss)
                rec["pct"] = round(100.0 * rec["px"] / len(cur), 1)
                rec["miss"] = miss
            mm[m] = rec
            prev = cur
        out[key] = {"label": label, "wiki": wiki, "base": base, "m": mm}

    # 한 번이라도 멤버였던 티커 중 메타가 없는 것 — 지어내지 않고 개수만 적는다.
    n_nometa = len([t for t in seen if t not in meta])
    n_noname = len([t for t in seen if not (meta.get(t) or ["", ""])[0]])
    n_nosec = len([t for t in seen if not (meta.get(t) or ["", ""])[1]])
    print("   위키 이름 %d · 섹터 %d · EODHD 이름 %d → 남은 이름 없음 %d · 섹터 미상 %d"
          % (_named, _sected, _dnamed, n_noname, n_nosec))

    doc = {
        "as_of": hist.get("as_of"),
        "source": hist.get("source"),
        "months": [m for m in months if any(m in out[k]["m"] for k, _l, _w in IDX)],
        "idx": out,
        "meta": {t: meta[t] for t in sorted(seen) if t in meta},
        # 🚨 입력 지문 — 이 표를 만든 **입력이 그 뒤로 바뀌었는지** 검증기가 알아채는 자리다.
        #   커버리지는 빌드 때 세어 여기 박는 값이라(화면이 11MB 가격 캐시를 읽지 않게 하려고
        #   그렇게 뒀다) 원본이 바뀌어도 표는 옛 수를 그대로 들고 있다. 2026-08-14 에
        #   가격 구멍 497칸을 메우고 이 파일을 안 구워서 7월이 77.7% 인 채로 남았다.
        #   validate_site 가 세 값을 다시 세어 대조한다.
        "src_fp": {"grid_days": len(dates), "px_nulls": px_nulls,
                   "hist_months": len(hist.get("months") or {}),
                   "hist_as_of": hist.get("as_of")},
        "n_seen": len(seen),
        "n_nometa": n_nometa,
        # 이름과 섹터를 따로 센다 — 화면이 "무엇이 없는지" 를 구별해 적을 수 있게.
        # 이름은 위키 CIK 열로 대부분 메웠고, 섹터는 아직 출처가 없다(아래 limits 참조).
        "n_noname": n_noname, "n_nosec": n_nosec,
        # 이중 클래스 묶음 — 화면이 한 줄로 합쳐 적는다(비중은 대표 티커에 몰려 있다).
        "dual": {t: r for t, r in DUAL.items() if t in seen},
        "note": "매월말 지수 편입 종목과, 그 시점 가격 자료를 몇 %나 갖고 있는지. "
                "멤버십은 위키백과 지수 목록 문서의 과거 리비전(data/index_history.json)이고 "
                "달마다 리비전 번호를 같이 실어 원문을 확인할 수 있게 했다.",
        "limits": [
            "이름·섹터는 위키백과 지수 목록 문서의 그 시점 표에서 가져왔다 — 오늘 이름이 "
            "아니라 **그때 이름**이다(AA=Alcoa Inc, 오늘 그 CIK 는 Howmet Aerospace다). "
            "섹터도 그때 표기라 2018-09 GICS 개편 전 'Telecommunication Services' 가 그대로 "
            "남아 있다. 오늘 분류로 덮으면 그 달의 명단을 오늘 기준으로 바꿔 읽게 된다.",
            "🚨 섹터가 아직 없는 23종은 **나스닥 100 전용 종목**이다(Liberty Media 계열 · "
            "Ctrip · BioMarin · Shire · 21세기폭스 · Vodafone 등). 나스닥 목록 문서는 GICS 가 "
            "아니라 **ICB(Industry Classification Benchmark)** 로 분류한다 — 다른 분류 체계다. "
            "한 열에 두 체계를 섞으면 'Technology'(ICB)와 'Information Technology'(GICS)가 "
            "서로 다른 묶음으로 앉는다. **빈칸보다 나쁜 오류**라 채우지 않고 비워 둔다.",
            "🚨 커버리지 100%가 '자료가 완전하다'는 뜻은 아니다. 여기서 세는 것은 **그달 "
            "월말에 종가가 있는 멤버의 비율**이고, 종가는 (ㄱ) 오늘의 유니버스 518종과 "
            "(ㄴ) 편출 종목 캐시에서 온다. (ㄴ)은 yfinance 가 주는 것뿐이라 M&A·상장폐지로 "
            "심볼 자체가 사라진 회사는 애초에 안 잡힌다 — 그 종목들은 분모에는 있고 분자에는 "
            "없으니 %로 드러나지만, 재무·거래량 같은 다른 축의 결손은 이 표가 재지 않는다.",
            "구간이 2014-06 부터인 것은 자료의 한계다 — 위키 표에 CIK 컬럼이 생긴 첫 달이고, "
            "그 아래는 티커로만 조인하게 되어 개명(BBWI←LB)과 티커 재사용을 구별할 수 없다. "
            "명단 자체는 더 깊다(SPX 2007-04 · NDX 2008-03).",
            "편입·편출은 **월말 스냅샷의 차이**다. 한 달 안에 들어왔다 나간 종목은 안 잡히고, "
            "위키 문서가 늦게 갱신된 달은 실제 변경일보다 한 달 뒤로 잡힐 수 있다.",
            "🚨 랩 전략의 PIT 레그가 쓰는 창은 이 표 전체가 아니라 **2021-07 부터**다 "
            "(세 커버리지가 모두 90%를 넘고 다시 안 내려가는 첫 달). 이 표에서 그 이전 달의 "
            "커버리지가 낮은 것이 그 문턱의 근거다.",
        ],
    }
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"))
    kb = os.path.getsize(OUT) / 1024.0
    print("→ %s · %d개월 · %.0fKB" % (os.path.relpath(OUT, ROOT), len(doc["months"]), kb))
    for key, label, _w in IDX:
        mm = out[key]["m"]
        cov = [(r["pct"], m) for m, r in mm.items() if "pct" in r]
        cov.sort()
        if cov:
            print("   %-10s %d개월 · 커버리지 최저 %.1f%%(%s) → 최근 %.1f%%"
                  % (label, len(mm), cov[0][0], cov[0][1],
                     mm[max(m for m in mm if "pct" in mm[m])]["pct"]))
    if n_nometa:
        print("   ⚠ 이름·섹터가 없는 티커 %d종 — 티커만 표시한다." % n_nometa)


if __name__ == "__main__":
    main()
