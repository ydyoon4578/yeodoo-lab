/* js/portfolio_app.js — 운용 포트폴리오 웹 앱: 원장 편집 · GitHub 동기화 · 라이브 성과 · 백테스트
 *
 * ⚠ 이 파일은 공개 저장소에 평문으로 있다 — 그래서 여기엔 **코드만** 있다.
 *   자료는 전부 암호문 안에 있다: 펀드 자료는 portfolio.html 의 PAYLOAD(잠금 해제 후
 *   window.PF 로 등장), 웹 원장은 data/portfolio_user.json(AES-256-GCM 봉투)이다.
 *   이 구조 덕에 앱 로직은 재잠금 없이 고칠 수 있다 — 자료가 바뀔 때만 재잠금한다.
 *
 * 게이트(portfolio.html)와의 계약:
 *   잠금 해제 성공 시 window.__pfKM 에 PBKDF2 키 재료(CryptoKey)를 두고 PFAPP.init() 을
 *   부른다. 로드 순서 경쟁(defer vs 해제 시점)은 양쪽에서 init 을 시도해 흡수한다.
 *
 * 웹 원장 봉투 규약(data/portfolio_user.json):
 *   {v:1, fmt:"aesgcm", iter:310000, salt:b64(16B), iv:b64(12B), ct:b64, updated:ISO}
 *   평문 = {v:1, strategies:{이름:{memo,status}}, trades:[{id,fund,dt,s,t,q,p,note}], saved:ISO}
 *   초기 상태는 {v:1, empty:true} — 첫 저장이 봉투로 대체한다.
 *   ⚠ 암호는 페이지 열람 암호와 같다(같은 키 재료로 봉투를 만든다). 페이지를 다른 암호로
 *     재잠금하면 옛 봉투가 안 풀린다 — 그때는 화면이 옛 암호를 따로 물어 연다.
 */
(function () {
  'use strict';

  var GH = { owner: 'ydyoon4578', repo: 'yeodoo-lab', path: 'data/portfolio_user.json' };
  var API = 'https://api.github.com/repos/' + GH.owner + '/' + GH.repo;
  var ITER = 310000;
  var TOKEN_KEY = 'pf_gh_token';

  var PF = null;          // 암호문에서 나온 데이터 블롭
  var TKI = {};           // ticker → 패널 행 번호
  var U16 = null;         // 종가 패널(Uint16Array)
  var ND = 0;             // 패널 날짜 수
  var S = {
    km: null,             // PBKDF2 키 재료 — 게이트가 준다. 메모리에만 있다.
    base: null,           // 마지막으로 불러온 원격 {sha, updated}
    doc: { v: 1, strategies: {}, trades: [], migrated: false },
    // 🚨 2026-08-21 사용자 지시 — «반영이 된 건지 안 된 건지 명확히».
    //   S.dirty 만으로는 «무엇이» 안 저장됐는지 알 수 없다. 편집마다 한 줄씩 쌓아
    //   상태바가 그 목록을 그대로 보여준다. 저장·취소하면 비운다.
    pending: [],
    dirty: false,
    ready: false,
    loadErr: null,
    env: null             // 복호 실패한 봉투를 들고 있는다 — 옛 암호 시도를 로컬에서 한다
  };

  // ── 유틸 ────────────────────────────────────────────────────────────────
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function num(v, nd) {
    if (v == null || !isFinite(v)) return '—';
    nd = nd == null ? 2 : nd;
    return Number(v).toLocaleString('en-US', { minimumFractionDigits: nd, maximumFractionDigits: nd });
  }
  function pct(v, nd, signed) {
    if (v == null || !isFinite(v)) return '—';
    nd = nd == null ? 2 : nd;
    var s = (v * 100).toFixed(nd) + '%';
    return (signed && v > 0 ? '+' : '') + s;
  }
  function sgn(v) { return (v || 0) > 0 ? 'pos' : ((v || 0) < 0 ? 'neg' : ''); }
  function el(id) { return document.getElementById(id); }
  function b64e(u8) {
    var s = '';
    for (var i = 0; i < u8.length; i += 0x8000)
      s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
    return btoa(s);
  }
  function b64d(b) {
    // GitHub contents API 는 b64 에 개행을 끼워 준다 — atob 전에 걷는다.
    var s = atob(String(b).replace(/\s+/g, '')), u = new Uint8Array(s.length);
    for (var i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);
    return u;
  }
  function today() {
    // 원장 날짜의 기본값. 미국 종가 기준일(PF.asof_us)이 아니라 입력 시점의 로컬 날짜다 —
    // 사용자가 "오늘 산 것"을 적는 게 자연스럽고, 가격은 어차피 그 날짜의 종가로 찾는다.
    var d = new Date(); // 표시용 기본값일 뿐 계산엔 안 쓴다
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function uid() { return 'w' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }
  // 편집 하나를 «미저장» 으로 등록한다. 화면 갱신까지 여기서 한 번에 — 호출부가
  // S.dirty 를 손으로 세우고 renderSync 를 빼먹는 사고를 없앤다.
  /* 원장 봉투 → 메모리 문서. **두 경로(첫 로드 · 옛 암호 복구)가 같은 함수를 쓴다** —
     사본을 두면 한쪽만 고쳐진다(이 저장소가 되풀이 밟은 자리다).
     ⚠ 2026-08-26 — 옛 이전 메모('DB 원장에서 이전')를 여기서 걷는다. 전 건에 같은 글이
       붙어 아무것도 안 가르는데 원장 표에서 줄마다 한 줄씩 더 차지했다(사용자 지시).
       ⚠ dirty 로 표시하지 않는다. 화면에서는 곧바로 사라지고, 저장된 값은 다음에 무언가를
         저장할 때 같이 정리된다 — 화면 정리 때문에 사용자가 안 누른 저장이 일어나면 안 된다. */
  var LEGACY_NOTE = 'DB 원장에서 이전';
  function adoptDoc(doc) {
    var trades = (doc.trades || []).map(function (t) {
      return (t.note === LEGACY_NOTE) ? Object.assign({}, t, { note: '' }) : t;
    });
    return { v: 1, strategies: doc.strategies || {}, trades: trades, migrated: !!doc.migrated };
  }

  function mark(desc, slug) {
    S.pending.push(desc);
    S.dirty = true;
    if (slug) renderFund(slug);
    renderSync();
    flash(desc);
  }
  // 방금 무엇이 반영됐는지 잠깐 띄운다 — 목록이 길어져도 «지금 누른 것»이 보인다.
  var _flashT = null;
  function flash(msg) {
    var b = el('pfflash');
    if (!b) {
      b = document.createElement('div');
      b.id = 'pfflash'; b.className = 'pfflash';
      document.body.appendChild(b);
    }
    b.textContent = '반영됨 — ' + msg + ' (저장 필요)';
    b.classList.add('on');
    clearTimeout(_flashT);
    _flashT = setTimeout(function () { b.classList.remove('on'); }, 2600);
  }

  // ── 패널 접근 ───────────────────────────────────────────────────────────
  function boot() {
    PF = window.PF;
    ND = PF.panel.nd;
    U16 = new Uint16Array(b64d(PF.panel.u16).buffer);
    TKI = {};
    PF.panel.tickers.forEach(function (t, k) { TKI[t] = k; });
  }
  function dLe(d) {
    // dates 는 오름차순 — d 이하 마지막 인덱스(이분탐색). 없으면 -1.
    var lo = 0, hi = PF.dates.length - 1, ans = -1;
    while (lo <= hi) {
      var m = (lo + hi) >> 1;
      if (PF.dates[m] <= d) { ans = m; lo = m + 1; } else hi = m - 1;
    }
    return ans;
  }
  function pxAt(t, i) {
    var k = TKI[t];
    if (k == null || i < 0) return null;
    var v = U16[k * ND + i];
    return v ? v / PF.panel.scale[k] * PF.panel.p0[k] : null;
  }
  /* ── 그날의 NAV·환율 (2026-08-26) ─────────────────────────────────────────
     비중 = 수량×체결가(USD)×**그날** 환율 ÷ **그날** NAV(원). 둘 중 하나만 시점을 맞추면
     나머지가 어긋난다.
     ⚠ 조각이 옛 판이면 시계열(navs·fxs)이 없다 — 그때는 최신 한 값으로 버티되 **버텼다는
       사실을 돌려준다**(exact:false). 화면이 그걸 각주로 적는다. 조용히 최신값을 쓰면
       과거 매매의 비중이 틀린 채로 «맞는 수» 처럼 실린다. */
  function lastLeq(map, d) {
    if (!map) return null;
    var best = null, bk = null;
    Object.keys(map).forEach(function (k) {
      if (k <= d && (bk === null || k > bk)) { bk = k; best = map[k]; }
    });
    return best;
  }
  function navFxAt(F, d) {
    var n = lastLeq(F.navs, d), x = lastLeq(PF.fxs, d);
    return { nav: (n != null ? n : F.nav), fx: (x != null ? x : F.fx),
             exact: (n != null && x != null) };
  }
  // 비중(%) — 그 매매가 그날 NAV 의 몇 %였나. 못 내면 null.
  function wOfNav(F, d, qty, px) {
    var A = navFxAt(F, d);
    if (!(A.nav > 0) || !(A.fx > 0) || px == null) return null;
    return qty * px * A.fx / A.nav * 100;
  }

  function pxLeI(t, i) {
    for (; i >= 0; i--) { var v = pxAt(t, i); if (v != null) return v; }
    return null;
  }
  function lvlLeI(arr, i) {
    for (; i >= 0; i--) { if (arr[i] != null) return arr[i]; }
    return null;
  }

  // ── 원장 병합 ───────────────────────────────────────────────────────────
  function mergedTrades(slug) {
    var idx = PF.funds[slug].idx;
    var out = [];
    // 🚨 이전이 끝났으면 DB 씨앗(PF.mp)을 **완전히 무시한다.** 안 그러면 같은 매매가
    //   웹 원장과 씨앗 양쪽에 있어 수량·손익이 두 배로 센다. migrated 플래그가 그 스위치다.
    if (!S.doc.migrated) PF.mp.forEach(function (t) {
      if (t.idx === idx) out.push({ src: 'db', dt: t.dt, s: t.s, t: t.t, q: t.q, p: t.p, note: '' });
    });
    S.doc.trades.forEach(function (t) {
      if (t.fund === slug) out.push({ src: 'web', id: t.id, dt: t.dt, s: t.s, t: t.t, q: t.q, p: t.p, note: t.note || '' });
    });
    out.sort(function (a, b) { return a.dt < b.dt ? -1 : a.dt > b.dt ? 1 : (a.s < b.s ? -1 : 1); });
    return out;
  }

  // ── 성과 엔진 — build/portfolio_fund.py 의 strat_perf 와 같은 정의 ────────
  //   pnl = Σ qty×(px_t − 체결가) · BM = 같은 날 같은 금액을 지수에(매매 시점 일치)
  //   inv = 매수(qty>0)의 원금 합. 파이썬 쪽 수치(PF.funds[*].check)와 기계 대조한다.
  function calcPerf(slug, trades, asofI) {
    var lvl = PF.lvl[slug];
    // 창 경계 — 조용히 새는 세 갈래를 «제외 + 집계»로 바꾼다(적대감사 13·14·15):
    //   ① 패널 시작 전 매매: BM 앵커가 없어 pnl 만 남으면 초과가 손익 전액으로 부풀려진다.
    //   ② 기준일(asof_us) 이후 매매(오늘 KST 입력): 곡선·분해가 서로 다른 답을 내게 된다.
    //   ③ 패널에 가격이 없는 종목: 파이썬 엔진과 같게 통째로 제외(양쪽 다 inv 미집계 = 정의 일치).
    var lo = PF.dates[0], hi = PF.dates[asofI];
    var skipped = { old: 0, future: 0, nopx: 0 };
    var use = [];
    trades.forEach(function (tr) {
      if (tr.dt < lo) { skipped.old++; return; }
      if (tr.dt > hi) { skipped.future++; return; }
      if (pxLeI(tr.t, asofI) == null) { skipped.nopx++; return; }
      use.push(tr);
    });
    trades = use;
    var byS = {};
    trades.forEach(function (tr) {
      (byS[tr.s] = byS[tr.s] || []).push(tr);
    });
    var out = {};
    Object.keys(byS).sort().forEach(function (sname) {
      var trs = byS[sname];
      var t0 = trs.reduce(function (m, t) { return t.dt < m ? t.dt : m; }, trs[0].dt);
      var i0 = dLe(t0);
      if (i0 < 0) i0 = 0;
      if (PF.dates[i0] < t0) i0++;                    // 첫 매매일 이후 축부터
      var curve = [];
      for (var i = i0; i <= asofI; i++) {
        var pnl = 0, bm = 0, inv = 0, d = PF.dates[i];
        for (var j = 0; j < trs.length; j++) {
          var tr = trs[j];
          if (tr.dt > d) continue;
          var p = pxLeI(tr.t, i);
          if (p == null) continue;
          pnl += tr.q * (p - tr.p);
          var it = lvlLeI(lvl, i), iv0 = lvlLeI(lvl, dLe(tr.dt));
          if (it && iv0) bm += tr.q * tr.p * (it / iv0 - 1);
          if (tr.q > 0) inv += tr.q * tr.p;
        }
        curve.push([i, pnl, bm, inv]);
      }
      // 분할 가드 — 보유 구간에 하루 |40%| 초과 변동
      var warn = {};
      var byT = {};
      trs.forEach(function (t) { (byT[t.t] = byT[t.t] || []).push(t); });
      Object.keys(byT).forEach(function (tk) {
        var tf = byT[tk].reduce(function (m, t) { return t.dt < m ? t.dt : m; }, byT[tk][0].dt);
        var prev = null;
        for (var i2 = Math.max(0, dLe(tf)); i2 <= asofI; i2++) {
          var v = pxAt(tk, i2);
          if (v != null) {
            if (prev != null && Math.abs(v / prev - 1) > PF.guard) warn[tk] = 1;
            prev = v;
          }
        }
      });
      // 종목별 분해
      var rows = [];
      Object.keys(byT).sort().forEach(function (tk) {
        var p = pxLeI(tk, asofI);
        if (p == null) return;
        var trsT = byT[tk];
        var invT = 0, pnlT = 0, bmT = 0, qT = 0;
        var it = lvlLeI(lvl, asofI);
        trsT.forEach(function (t) {
          qT += t.q;
          pnlT += t.q * (p - t.p);
          if (t.q > 0) invT += t.q * t.p;
          var iv0 = lvlLeI(lvl, dLe(t.dt));
          if (it && iv0) bmT += t.q * t.p * (it / iv0 - 1);
        });
        rows.push({ t: tk, q: qT, px: p, inv: invT, pnl: pnlT, ret: invT ? pnlT / invT : null,
                    exc: pnlT - bmT, warn: !!warn[tk] });
      });
      rows.sort(function (a, b) { return b.exc - a.exc; });
      var last = curve.length ? curve[curve.length - 1] : null;
      out[sname] = {
        trades: trs, curve: curve, rows: rows, warn: Object.keys(warn).sort(),
        last: last ? { pnl: last[1], bm: last[2], inv: last[3],
                       ret: last[3] ? last[1] / last[3] : null,
                       bmRet: last[3] ? last[2] / last[3] : null } : null
      };
    });
    return { byS: out, skipped: skipped };
  }

  // 교차검증 — DB 원장만으로 돌린 JS 결과가 파이썬 스냅샷(PF.funds[*].check)과 같은가.
  // 두 엔진이 같은 정의를 서로 다른 언어로 구현했으므로, 어긋나면 한쪽이 틀린 것이다.
  function crossCheck(slug) {
    var chk = PF.funds[slug].check || {};
    var names = Object.keys(chk);
    if (!names.length) return { n: 0, bad: [] };
    var idx = PF.funds[slug].idx;
    var dbOnly = [];
    var preWindow = false;
    PF.mp.forEach(function (t) {
      if (t.idx !== idx) return;
      if (t.dt < PF.dates[0]) preWindow = true;      // JS 는 창 밖 매매를 제외, 파이썬은 포함 — 대조 불능
      dbOnly.push({ src: 'db', dt: t.dt, s: t.s, t: t.t, q: t.q, p: t.p });
    });
    if (preWindow) return { n: names.length, bad: [], skip: '패널 창 이전 DB 매매가 있어 대조 생략' };
    var asofI = dLe(PF.funds[slug].asof_us);
    var perf = calcPerf(slug, dbOnly, asofI).byS;
    var bad = [];
    names.forEach(function (n) {
      var a = chk[n], b = (perf[n] || {}).last;
      if (!b) { bad.push(n + '(JS 미계산)'); return; }
      ['inv', 'pnl', 'bm'].forEach(function (k) {
        // 허용오차 바닥 $100 — uint16 양자화의 최악 오차(주당 반스텝 × 수량)가 $2 바닥을
        // 넘을 수 있어 가짜 ⚠ 가 났다(적대감사 17). 진짜 엔진 어긋남은 구조적이라 1% 를 넘는다.
        var tol = Math.max(100, Math.abs(a[k]) * 0.005);
        if (Math.abs(a[k] - b[k]) > tol) bad.push(n + '.' + k + ' py=' + num(a[k], 0) + ' js=' + num(b[k], 0));
      });
    });
    return { n: names.length, bad: bad };
  }

  // ── SVG 라인차트(파이썬 svg_lines 의 JS 판) ────────────────────────────────
  /* ── 가로 막대 (2026-08-26) ────────────────────────────────────────────────
     🚨 사용자 «구성종목별 등락률이나 기여도도 차트로 딱 볼 수 있게». 종전에는 그 수가
       전략마다 접힌 <details> 안 표에만 있었다 — 펴야 보이고, 펴도 어느 종목이 큰지는
       숫자를 눈으로 훑어야 했다.
     ⚠ 선 그래프(svgLines)를 쓰지 않는다. 저건 «시간에 따라» 를 말하는 그림이고 여기는
       «종목끼리 크기 비교» 다. 축이 다른 것을 같은 그림에 담으면 둘 다 안 읽힌다.
     ⚠ 툴팁 배선(PFCHARTS)을 안 태운다 — 그 배선은 시계열 좌표(data-ch)를 전제한다.
       막대는 값이 바로 옆에 찍히므로 툴팁이 필요 없다. */
  function svgBars(items, unit, nd) {
    if (!items.length) return '';
    var rowH = 21, padT = 8, padB = 8, labW = 66, valW = 74, w = 760;
    var h = padT + padB + rowH * items.length;
    var mx = 0;
    items.forEach(function (it) { mx = Math.max(mx, Math.abs(it.v)); });
    if (!(mx > 0)) mx = 1;
    var barL = labW + 6, barR = w - valW - 6, mid = (barL + barR) / 2;
    var half = (barR - barL) / 2;
    var o = ['<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" class="ichart bars" ' +
             'preserveAspectRatio="none" style="width:100%;height:' + h + 'px">'];
    o.push('<line x1="' + mid + '" y1="' + padT + '" x2="' + mid + '" y2="' + (h - padB) +
           '" stroke="var(--line)" stroke-width="1"/>');
    items.forEach(function (it, i) {
      var y = padT + rowH * i, cy = y + rowH / 2;
      var len = Math.abs(it.v) / mx * half;
      var pos = it.v >= 0;
      var col = pos ? 'var(--deploy)' : 'var(--hot)';
      o.push('<text x="' + labW + '" y="' + (cy + 3.6) + '" text-anchor="end" ' +
             'font-size="11" font-family="var(--mono)" fill="var(--ink-2)">' + esc(it.k) + '</text>');
      o.push('<rect x="' + (pos ? mid : mid - len) + '" y="' + (y + 3.5) + '" width="' +
             Math.max(len, 0.6) + '" height="' + (rowH - 7) + '" fill="' + col + '" opacity=".78"/>');
      o.push('<text x="' + (w - 4) + '" y="' + (cy + 3.6) + '" text-anchor="end" ' +
             'font-size="11" font-family="var(--mono)" fill="' + col + '">' +
             (it.v > 0 ? '+' : '') + num(it.v, nd) + esc(unit) + '</text>');
    });
    o.push('</svg>');
    return '<div class="barwrap">' + o.join('') + '</div>';
  }

  // 🚨 파이썬 svg_lines 와 **같은 마크업**을 낸다 — .chwrap[data-ch] + .ichart. 호버 배선은
  //   조각 스크립트(window.PFCHARTS)가 한 벌로 하므로, 여기서 툴팁을 또 만들면 두 벌이 된다.
  //   눈금·여백 규약도 그쪽과 맞춘다(안 맞으면 같은 화면에서 두 그림의 눈이 달라진다).
  function svgLines(series, labels, w, h, zero) {
    w = w || 760; h = h || 232;
    var pad = 46;
    var ys = [];
    series.forEach(function (t) { t[1].forEach(function (p) { ys.push(p[1]); }); });
    if (!ys.length) return '';
    var lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys);
    if (hi - lo < 1e-9) hi = lo + 1;
    var span = hi - lo; lo -= span * 0.06; hi += span * 0.06;
    var xi = {}, labs = [];
    series.forEach(function (t) {
      t[1].forEach(function (p) { if (!(p[0] in xi)) { xi[p[0]] = labs.length; labs.push(p[0]); } });
    });
    var n = labs.length;
    var colors = ['var(--accent)', 'var(--champ)', 'var(--rp)', 'var(--hot)', 'var(--deploy)'];
    function X(i) { return pad + (w - pad - 12) * (i / Math.max(1, n - 1)); }
    function Y(v) { return (h - 26) - (h - 46) * ((v - lo) / (hi - lo)); }
    var o = ['<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" class="ichart" preserveAspectRatio="none" style="width:100%;height:auto">'];
    for (var k = 0; k <= 4; k++) {
      var v = lo + (hi - lo) * k / 4, yy = Y(v);
      o.push('<line x1="' + pad + '" y1="' + yy.toFixed(1) + '" x2="' + (w - 12) + '" y2="' + yy.toFixed(1) + '" stroke="var(--line-soft)" stroke-width="1"/>');
      o.push('<text x="' + (pad - 5) + '" y="' + (yy + 3.5).toFixed(1) + '" font-size="10" text-anchor="end" fill="var(--muted)" font-family="var(--mono)">' + v.toFixed(1) + '</text>');
    }
    if (lo < 0 && 0 < hi)
      // 초과수익 그림에서는 0선이 곧 벤치마크다 — zero 를 받으면 벤치 색으로 긋는다.
      o.push('<line x1="' + pad + '" y1="' + Y(0).toFixed(1) + '" x2="' + (w - 12) + '" y2="' + Y(0).toFixed(1) +
             '" stroke="' + (zero || 'var(--line)') + '" stroke-width="' + (zero ? 1.4 : 1) + '" stroke-dasharray="' + (zero ? '5 3' : '3 3') + '"/>');
    var pm = '';
    labs.forEach(function (lb, i) {
      var mm = String(lb).slice(0, 7);
      if (mm !== pm && i) {
        pm = mm;
        o.push('<line x1="' + X(i).toFixed(1) + '" y1="12" x2="' + X(i).toFixed(1) + '" y2="' + (h - 26) + '" stroke="var(--line-soft)" stroke-width="1"/>');
        o.push('<text x="' + X(i).toFixed(1) + '" y="' + (h - 12) + '" font-size="9.5" text-anchor="middle" fill="var(--muted)" font-family="var(--mono)">' + esc(mm.slice(5) + '월') + '</text>');
      } else if (!i) pm = mm;
    });
    series.forEach(function (t, k) {
      var color = t[2] || colors[k % colors.length];
      var d = t[1].map(function (p, i) { return (i ? 'L' : 'M') + X(xi[p[0]]).toFixed(1) + ',' + Y(p[1]).toFixed(1); }).join(' ');
      o.push('<path d="' + d + '" fill="none" stroke="' + color + '" stroke-width="1.8" stroke-linejoin="round"' + (t[3] ? ' stroke-dasharray="4 3"' : '') + '/>');
    });
    o.push('<line class="chguide" x1="0" y1="12" x2="0" y2="' + (h - 26) + '" stroke="var(--muted)" stroke-width="1" opacity="0"/>');
    series.forEach(function (t, k) { o.push('<circle class="chdot" r="3.2" fill="' + (t[2] || colors[k % colors.length]) + '" opacity="0"/>'); });
    o.push('</svg>');
    // 🚨 2026-09-17 — 범례가 **기본 팔레트**를 쓰고 있었다. 선 색을 직접 넘긴 그림에서는
    //   (renderPerf 의 «전략 vs 지수» 가 그렇다) 범례 색과 선 색이 서로 달랐다 —
    //   지수 선은 --hot 인데 범례 점은 --champ 였다. 선과 같은 색을 쓴다.
    if (labels) o.push('<div class="chlgd">' + labels.map(function (lb, k) {
      var c2 = (series[k] && series[k][2]) || colors[k % colors.length];
      return '<span><i style="background:' + c2 + '"></i>' + esc(lb) + '</span>';
    }).join('') + '</div>');
    var meta = {
      pad: pad, w: w, h: h, lo: lo, hi: hi, labs: labs,
      s: series.map(function (t, k) {
        return { n: t[0], c: t[2] || colors[k % colors.length],
                 v: t[1].map(function (p) { return [p[0], Math.round(p[1] * 1e4) / 1e4]; }) };
      })
    };
    return '<div class="chwrap" data-ch="' + esc(JSON.stringify(meta)) + '">' + o.join('') +
           '<div class="chtip" hidden></div></div>';
  }

  // ── 암복호 ──────────────────────────────────────────────────────────────
  function deriveKey(km, salt, usages, iters) {
    return crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt: salt, iterations: iters || ITER, hash: 'SHA-256' },
      km, { name: 'AES-GCM', length: 256 }, false, usages);
  }
  async function encDoc(doc) {
    var salt = crypto.getRandomValues(new Uint8Array(16));
    var iv = crypto.getRandomValues(new Uint8Array(12));
    var key = await deriveKey(S.km, salt, ['encrypt']);
    var ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, key,
      new TextEncoder().encode(JSON.stringify(doc)));
    return { v: 1, fmt: 'aesgcm', iter: ITER, salt: b64e(salt), iv: b64e(iv),
             ct: b64e(new Uint8Array(ct)), updated: new Date().toISOString() };
  }
  async function decDoc(env, km) {
    // ⚠ iter 는 봉투에 적힌 값을 따른다 — 상수만 쓰면 반복수를 바꾼 미래 봉투를 «암호 불일치»로 오진한다.
    var key = await deriveKey(km || S.km, b64d(env.salt), ['decrypt'], env.iter || ITER);
    var pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: b64d(env.iv) }, key, b64d(env.ct));
    return JSON.parse(new TextDecoder().decode(pt));
  }

  // ── GitHub API ──────────────────────────────────────────────────────────
  function token() { try { return localStorage.getItem(TOKEN_KEY) || ''; } catch (e) { return ''; } }
  function ghHeaders(json) {
    var h = { 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' };
    if (json) h['Content-Type'] = 'application/json';
    var t = token();
    if (t) h['Authorization'] = 'Bearer ' + t;
    return h;
  }
  async function ghGetFile(ref) {
    var u = API + '/contents/' + GH.path + (ref ? '?ref=' + encodeURIComponent(ref) : '');
    // cache:no-store — api.github.com 은 max-age=60 을 달고 온다. 캐시를 타면 «다른 기기 저장
    // 직후의 sha 재취득»이 60초간 옛 sha 를 돌려줘 409 가 반복된다(적대감사 확정).
    var r = await fetch(u, { headers: ghHeaders(), cache: 'no-store' });
    if (r.status === 404) return null;
    if (!r.ok) throw new Error('GitHub 읽기 실패 HTTP ' + r.status);
    var j = await r.json();
    // Contents API 는 1MB 초과 파일에 200 + content:"" (encoding:"none") 을 준다 — 그대로
    // 파싱하면 «손상» 오진 후 복원 유도로 파일을 실제로 비우게 된다(적대감사 실측).
    if (j && j.content === '' && j.size > 1000000)
      throw new Error('원장이 1MB 를 넘어 Contents API 로 못 읽습니다(' + j.size + 'B) — 원장을 나누거나 정리할 것.');
    return j;
  }
  async function ghPut(contentB64, sha, message) {
    var body = { message: message, content: contentB64 };
    if (sha) body.sha = sha;
    var r = await fetch(API + '/contents/' + GH.path, {
      method: 'PUT', headers: ghHeaders(true), body: JSON.stringify(body)
    });
    if (r.status === 401) throw new Error('토큰 인증 실패(401) — 설정에서 토큰을 확인하세요.');
    if (r.status === 403) throw new Error('권한 없음(403) — 토큰에 이 저장소 Contents 쓰기 권한이 필요합니다.');
    if (r.status === 404) throw new Error('쓰기 불가(404) — fine-grained 토큰의 저장소 범위에 yeodoo-lab 이 있는지 확인하세요.');
    if (r.status === 409 || r.status === 422) throw Object.assign(new Error('CONFLICT'), { conflict: true });
    if (!r.ok) throw new Error('GitHub 쓰기 실패 HTTP ' + r.status);
    return r.json();
  }
  async function ghHistory() {
    var r = await fetch(API + '/commits?path=' + encodeURIComponent(GH.path) + '&per_page=15',
      { headers: ghHeaders(), cache: 'no-store' });
    if (!r.ok) throw new Error('이력 조회 실패 HTTP ' + r.status);
    return r.json();
  }

  // ── 원장 불러오기/저장 ──────────────────────────────────────────────────
  async function loadLedger() {
    S.loadErr = null;
    var f;
    try { f = await ghGetFile(); }
    catch (e) { S.loadErr = e.message; renderSync(); return; }
    // ⚠ 404/empty 경로에서 S.doc 을 «반드시» 초기화한다 — 안 하면 복원·리로드가 직전
    //   메모리 상태를 들고 «동기화됨»을 사칭한다(적대감사 확정: restoreRev→loadLedger 경로).
    if (!f) { S.base = { sha: null, updated: null }; S.doc = { v: 1, strategies: {}, trades: [], migrated: false }; return; }
    S.base = { sha: f.sha, updated: null };
    var env;
    try { env = JSON.parse(new TextDecoder().decode(b64d(f.content))); }
    catch (e) { S.loadErr = '원장 JSON 파싱 실패 — 파일이 손상됐다. 이력에서 복원하세요.'; renderSync(); return; }
    if (env.empty) { S.doc = { v: 1, strategies: {}, trades: [], migrated: false }; return; }   // 초기 상태 — 빈 원장
    S.base.updated = env.updated || null;
    try {
      var doc = await decDoc(env);
      S.doc = adoptDoc(doc);
      S.env = null;
    } catch (e) {
      // 페이지 재잠금 암호가 바뀐 경우 — 봉투는 옛 암호다. 화면에서 옛 암호를 따로 받는다.
      // 🚨 봉투를 들고 있는다 — 옛 암호 시도가 매번 GitHub 을 다시 부르면 (ㄱ) 느리고
      //   (ㄴ) 비인증 GET 시간당 60회 제한에 걸려 «암호가 틀렸다» 로 위장된다. 실제로
      //   그 구별을 못 해서 사용자가 «맞는 암호를 넣어도 안 열린다» 를 겪었다(2026-09-03).
      S.env = env;
      S.loadErr = 'PWMISMATCH';
    }
  }
  async function saveLedger(force) {
    var doc = { v: 1, strategies: S.doc.strategies, trades: S.doc.trades, migrated: !!S.doc.migrated, saved: new Date().toISOString() };
    var env = await encDoc(doc);
    var b64 = b64e(new TextEncoder().encode(JSON.stringify(env)));
    var msg = 'portfolio: 웹 원장 (전략 ' + Object.keys(S.doc.strategies).length +
              ' · 매매 ' + S.doc.trades.length + '건)';
    var sha = S.base && S.base.sha;
    if (force) {
      var cur = await ghGetFile();                  // 강제 덮어쓰기도 최신 sha 로 PUT 해야 한다
      sha = cur && cur.sha;
    }
    var res = await ghPut(b64, sha, msg);
    S.base = { sha: res.content.sha, updated: env.updated };
    S.dirty = false;
    return res.commit.sha;
  }
  async function restoreRev(sha) {
    var f = await ghGetFile(sha);
    if (!f) throw new Error('그 버전을 읽지 못했다.');
    var cur = await ghGetFile();
    var res = await ghPut(f.content.replace(/\s+/g, ''), cur && cur.sha,
      'portfolio: 원장을 ' + sha.slice(0, 7) + ' 버전으로 복원');
    S.base = { sha: res.content.sha, updated: null };
    await loadLedger();
    S.dirty = false;
  }

  // 변경 취소 — 저장 안 된 편집을 버리고 **원격 원장을 다시 읽는다**. 메모리만 되돌리면
  // 직전 저장 시점과 어긋난 상태가 남는다(그게 «반영됐나?» 의 원인이다).
  async function onUndo() {
    if (!S.dirty) return;
    if (!confirm('저장 안 된 변경 ' + S.pending.length + '건을 버리고 마지막 저장 상태로 되돌립니다.\n계속할까요?')) return;
    try {
      await loadLedger();
      S.pending = []; S.dirty = false;
      renderAll();
      flashOk('마지막 저장 상태로 되돌렸습니다.');
    } catch (e) {
      panel('<b class="perr">되돌리기 실패</b><p class="pnote">' + esc(e.message) + '</p>');
    }
  }
  function flashOk(msg) {
    var b = el('pfflash');
    if (!b) { b = document.createElement('div'); b.id = 'pfflash'; b.className = 'pfflash'; document.body.appendChild(b); }
    b.textContent = msg;
    b.classList.add('on', 'ok');
    clearTimeout(_flashT);
    _flashT = setTimeout(function () { b.classList.remove('on', 'ok'); }, 2600);
  }

  // ── 렌더: 동기화 바 ─────────────────────────────────────────────────────
  // 🚨 골격(상태줄 #pfrow / 패널 #pfpanel)은 한 번만 만들고, 갱신은 #pfrow 만 다시 쓴다.
  //    처음엔 renderSync 가 통째로 innerHTML 을 갈았는데, 그러면 panel() 이 그린 다이얼로그의
  //    버튼 리스너가 재렌더마다 파괴돼 «충돌 다이얼로그가 통째로 죽는» 결함이 됐다
  //    (2026-08-20 적대감사 확정 — innerHTML 재삽입은 리스너를 복제하지 않는다).
  function renderSync() {
    var box = el('pfsync');
    if (!box) return;
    // 🚨 2026-08-20 사용자 지시 — «이력·되돌리기·토큰등록 이런거 다 안보이게. 필요하면 말할게».
    //   평소에는 바를 통째로 숨긴다. 단 **숨겨서 잃으면 안 되는 상태**에서는 나온다:
    //   저장 안 된 편집(S.dirty — 안 보이면 저장할 길이 없다) · 원장 로드 실패 ·
    //   충돌/이력 패널이 열려 있을 때. 조용한 초록불만 숨기는 것이다.
    var _panelOpen = el('pfpanel') && !el('pfpanel').hidden;
    box.style.display = (S.dirty || S.loadErr || _panelOpen) ? '' : 'none';
    if (!el('pfrow')) {
      box.innerHTML = '<div id="pfrow"></div><div class="syncpanel" id="pfpanel" hidden></div>';
      el('pfrow').addEventListener('click', function (e) {
        var b = e.target.closest('button');
        if (!b) return;
        if (b.id === 'pfsave') onSave();
        else if (b.id === 'pfundo') onUndo();
        else if (b.id === 'pfhist') onHist();
        else if (b.id === 'pfcfg') onCfg();
      });
    }
    var h = [];
    var nW = S.doc.trades.length, nS = Object.keys(S.doc.strategies).length;
    var st;
    if (S.loadErr === 'PWMISMATCH') st = '<span class="dot warn"></span>원장 암호가 페이지와 다름';
    else if (S.loadErr) st = '<span class="dot warn"></span>' + esc(S.loadErr);
    else if (!S.base) st = '<span class="dot"></span>불러오는 중…';
    else if (S.dirty) st = '<span class="dot warn"></span><b>저장 안 됨</b> — 변경 ' + S.pending.length + '건';
    else st = '<span class="dot ok"></span>저장됨';
    h.push('<div class="syncrow">');
    h.push('<span class="syncst">' + st + '</span>');
    h.push('<span class="syncmeta">웹 원장 전략 ' + nS + ' · 매매 ' + nW + '건' +
      (S.base && S.base.updated ? ' · 마지막 저장 ' + esc(String(S.base.updated).slice(0, 16).replace('T', ' ')) + 'Z' : '') + '</span>');
    h.push('<span class="syncbtns">');
    // 🚨 저장·취소를 **한 쌍으로** 둔다. 취소가 없으면 잘못 누른 편집을 되돌릴 길이
    //   새로고침(경고창)뿐이고, 그건 «반영됐나?» 를 더 헷갈리게 한다.
    h.push('<button class="sb primary" id="pfsave"' + (S.dirty ? '' : ' disabled') + '>저장</button>');
    h.push('<button class="sb warn" id="pfundo"' + (S.dirty ? '' : ' disabled') + '>변경 취소</button>');
    h.push('<button class="sb" id="pfhist">이력·되돌리기</button>');
    h.push('<button class="sb" id="pfcfg">' + (token() ? '⚙ 토큰' : '⚙ 토큰 등록 필요') + '</button>');
    h.push('</span></div>');
    if (S.dirty && S.pending.length) {
      h.push('<div class="pendlist"><b>저장하면 반영될 변경</b><ol>' +
        S.pending.slice(-12).map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') +
        '</ol>' + (S.pending.length > 12 ? '<span class="pnote">외 ' + (S.pending.length - 12) + '건</span>' : '') +
        '</div>');
    }
    el('pfrow').innerHTML = h.join('');
    if (S.loadErr === 'PWMISMATCH' && el('pfpanel').hidden) showPwPrompt();
  }

  function panel(html) {
    var p = el('pfpanel');
    p.hidden = false;
    p.innerHTML = html;
    return p;
  }

  function showPwPrompt() {
    var env = S.env;
    var when = env && env.updated ? String(env.updated).slice(0, 10) : '?';
    var p = panel(
      '<b>웹 원장이 옛 암호로 잠겨 있습니다</b>' +
      '<p class="pnote">저장소에 있는 웹 원장(' + esc(when) + ' 저장분)이 <b>지금 페이지 암호로는 안 열립니다</b>. ' +
      '웹 원장은 저장할 때의 페이지 암호로 잠기는데, 그 뒤 페이지를 <b>다른 암호로 재잠금</b>하면 이렇게 됩니다. ' +
      '아래 두 갈래 중 하나를 고르세요 — 어느 쪽이든 <b>지금 화면의 매매 내역은 그대로입니다</b>' +
      '(화면은 사내 원장에서 직접 읽어 그립니다).</p>' +
      '<p class="pnote"><b>① 그때 암호를 안다면</b> 여기에 넣으세요. 열면 지금 암호로 다시 잠급니다.</p>' +
      '<input type="password" id="pfoldpw" placeholder="원장을 저장하던 시기의 암호">' +
      '<button class="sb primary" id="pfoldgo">열기</button> <span id="pfolderr" class="perr"></span>' +
      '<p class="pnote" style="margin-top:10px"><b>② 기억나지 않으면</b> 원장을 비우고 지금 암호로 새로 시작하면 됩니다. ' +
      '옛 원장은 <b>git 이력에 그대로 남아</b> 나중에 암호가 기억나면 언제든 되살릴 수 있습니다(지워지지 않습니다).</p>' +
      '<button class="sb warn" id="pfreset">원장 비우고 지금 암호로 새로 시작</button> ' +
      '<span id="pfreseterr" class="perr"></span>');

    el('pfoldgo').addEventListener('click', async function () {
      var msg = el('pfolderr');
      msg.textContent = '';
      if (!env) { msg.textContent = '봉투를 못 들고 있습니다 — 새로고침 후 다시 시도하세요.'; return; }
      var pw = el('pfoldpw').value;
      if (!pw) { msg.textContent = '암호를 입력하세요.'; return; }
      var doc;
      try {
        // 🚨 이미 받아 둔 봉투로 «로컬에서만» 시도한다 — 네트워크를 안 타므로 실패하면
        //   원인은 오직 암호다. 종전에는 여기서 GitHub 을 다시 불러, 통신 실패까지
        //   «암호가 틀렸다» 로 뭉뚱그렸다(오진의 근원).
        var km = await crypto.subtle.importKey('raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveKey']);
        doc = await decDoc(env, km);
      } catch (e) {
        msg.textContent = '이 암호로는 안 열립니다 — 다른 암호를 시도해 보세요.';
        return;
      }
      try {
        S.doc = adoptDoc(doc);
        S.loadErr = null; S.env = null;
        S.dirty = true;                             // 현재 암호로 재저장 유도
        renderAll();
        panel('원장을 열었습니다 — 매매 ' + S.doc.trades.length + '건. ' +
              '<b>[GitHub에 저장]</b> 을 누르면 지금 페이지 암호로 다시 잠급니다.');
      } catch (e2) {
        msg.textContent = '열긴 했지만 내용이 예상 형식이 아닙니다: ' + esc(e2.message);
      }
    });

    el('pfreset').addEventListener('click', async function () {
      var msg = el('pfreseterr');
      msg.textContent = '';
      if (!token()) { onCfg(); return; }
      if (!confirm('웹 원장을 빈 상태로 되돌립니다.\n\n' +
                   '· 화면의 매매 내역은 사내 원장에서 오므로 그대로 남습니다.\n' +
                   '· 옛 원장은 git 이력에 보존되어 나중에 되살릴 수 있습니다.\n\n' +
                   '진행할까요?')) return;
      try {
        var body = JSON.stringify({ v: 1, empty: true,
          note: '웹 원장 초기 상태 — 다음 저장이 AES-256-GCM 봉투로 대체한다' }) + '\n';
        var cur = await ghGetFile();
        await ghPut(b64e(new TextEncoder().encode(body)), cur && cur.sha,
                    'portfolio: 웹 원장 초기화(옛 암호 봉투는 이력에 보존)');
        S.env = null; S.loadErr = null;
        await loadLedger();
        renderAll();
        panel('원장을 비웠습니다 — 이제 지금 암호로 저장됩니다. 옛 봉투는 git 이력에 남아 있습니다.');
      } catch (e) {
        msg.textContent = '초기화 실패: ' + esc(e.message);
      }
    });
  }

  async function onSave() {
    if (!token()) { onCfg(); return; }
    // 🚨 불러오기가 실패한 상태의 저장은 «빈 문서로 원격을 덮는» 길이다 — 막는다.
    //   (GET 실패 → base=null → sha 없는 PUT → 422 를 충돌로 오진 → 덮어쓰기 = 원장 소실.
    //    2026-08-20 적대감사 확정 시나리오.)
    if (S.loadErr) {
      panel('<span class="perr">원장을 불러오지 못한 상태라 저장이 위험합니다 — ' +
        (S.loadErr === 'PWMISMATCH' ? '먼저 아래에서 옛 암호로 원장을 여세요.' : '새로고침 후 다시 시도하세요.') + '</span>');
      if (S.loadErr === 'PWMISMATCH') showPwPrompt();
      return;
    }
    var b = el('pfsave');
    b.disabled = true; b.textContent = '저장 중…';
    try {
      var sha = await saveLedger(false);
      S.pending = [];                    // 저장됐으니 «미저장» 목록을 비운다
      renderAll();
      flashOk('저장 완료 — 커밋 ' + sha.slice(0, 7));
      panel('저장됨 — 커밋 <span class="tk">' + esc(sha.slice(0, 7)) + '</span>. git 이력에 남아 언제든 되돌릴 수 있습니다.');
    } catch (e) {
      renderAll();
      if (e.conflict) {
        // renderAll 뒤에 그린다 — 골격 분리로 패널은 재렌더에도 살아남지만, 순서까지 지켜 확실히.
        panel('<b>충돌</b> — 다른 기기에서 먼저 저장했습니다.<br>' +
          '<button class="sb" id="pfreload">원격을 불러오기(내 미저장 변경 폐기)</button> ' +
          '<button class="sb warn" id="pfforce">내 것으로 덮어쓰기(이전 버전은 이력에 남음)</button>');
        el('pfreload').addEventListener('click', async function () { await loadLedger(); S.dirty = false; S.pending = []; renderAll(); panel('원격 상태를 불러왔습니다.'); });
        el('pfforce').addEventListener('click', async function () {
          try { var s2 = await saveLedger(true); S.pending = []; renderAll(); panel('덮어씀 — 커밋 ' + esc(s2.slice(0, 7))); }
          catch (e2) { panel('<span class="perr">' + esc(e2.message) + '</span>'); }
        });
      } else panel('<span class="perr">' + esc(e.message) + '</span>');
    }
  }

  async function onHist() {
    panel('이력 조회 중…');
    try {
      var cs = await ghHistory();
      if (!cs.length) { panel('저장 이력이 아직 없습니다.'); return; }
      var h = ['<b>원장 이력</b> — 복원하면 «그 시점의 원장»이 새 커밋으로 얹힙니다(이력은 안 지워짐).<table class="mini"><tbody>'];
      cs.forEach(function (c) {
        h.push('<tr><td class="tk">' + esc(c.sha.slice(0, 7)) + '</td>' +
          '<td>' + esc((c.commit.committer.date || '').slice(0, 16).replace('T', ' ')) + 'Z</td>' +
          '<td>' + esc(c.commit.message.split('\n')[0].slice(0, 60)) + '</td>' +
          '<td><button class="sb" data-rev="' + esc(c.sha) + '">이 버전으로 복원</button></td></tr>');
      });
      h.push('</tbody></table>');
      var p = panel(h.join(''));
      p.querySelectorAll('button[data-rev]').forEach(function (b) {
        b.addEventListener('click', async function () {
          if (!token()) { onCfg(); return; }
          b.disabled = true; b.textContent = '복원 중…';
          try { await restoreRev(b.dataset.rev); renderAll(); panel('복원 완료.'); }
          catch (e) { panel('<span class="perr">' + esc(e.message) + '</span>'); }
        });
      });
    } catch (e) { panel('<span class="perr">' + esc(e.message) + '</span>'); }
  }

  function onCfg() {
    var t = token();
    panel(
      '<b>GitHub 쓰기 토큰</b> <span class="pnote">(이 기기 브라우저에만 저장 — 저장소·서버로 안 나감)</span>' +
      '<p class="pnote">발급: github.com → Settings → Developer settings → ' +
      '<b>Fine-grained tokens</b> → Generate: Repository access 를 <b>yeodoo-lab 하나만</b>, ' +
      'Permissions 는 <b>Contents: Read and write</b> 만. 만료는 90일 권장(만료되면 다시 등록).</p>' +
      '<input type="password" id="pftok" placeholder="github_pat_…" value="' + esc(t) + '">' +
      '<button class="sb primary" id="pftoksave">이 기기에 저장</button> ' +
      (t ? '<button class="sb warn" id="pftokdel">삭제</button> ' : '') +
      '<span id="pftokmsg" class="pnote"></span>');
    el('pftoksave').addEventListener('click', async function () {
      var v = el('pftok').value.trim();
      if (!v) { el('pftokmsg').textContent = '값이 비었습니다.'; return; }
      try { localStorage.setItem(TOKEN_KEY, v); } catch (e) {}
      el('pftokmsg').textContent = '확인 중…';
      try {
        var r = await fetch(API, { headers: ghHeaders(), cache: 'no-store' });
        var j = await r.json();
        el('pftokmsg').textContent = r.ok && j.permissions && j.permissions.push
          ? '✓ 쓰기 권한 확인됨' : '⚠ 토큰은 저장했지만 쓰기 권한이 안 보입니다 — 권한 설정 확인.';
      } catch (e) { el('pftokmsg').textContent = '⚠ 확인 실패: ' + e.message; }
      renderSync();          // 골격 분리 덕에 이 패널(리스너 포함)은 살아남는다
    });
    if (t) el('pftokdel') && el('pftokdel').addEventListener('click', function () {
      try { localStorage.removeItem(TOKEN_KEY); } catch (e) {}
      renderSync();
    });
  }

  // ── 렌더: 원장(③) ───────────────────────────────────────────────────────
  function strategyNames(slug) {
    var s = {};
    mergedTrades(slug).forEach(function (t) { s[t.s] = 1; });
    Object.keys(S.doc.strategies).forEach(function (n) { s[n] = 1; });
    return Object.keys(s).sort();
  }

  function renderLedger(slug) {
    var box = el('ledger-' + slug);
    if (!box) return;
    var F = PF.funds[slug];
    var trs = mergedTrades(slug);
    var asofI = dLe(F.asof_us);
    var h = [];

    // ── DB 원장 → 웹 원장 이전 (2026-08-21 사용자 결정) ──────────────────
    // «mp.strategy_trade 도 안 쓰고 웹 입력으로만. 지금 있는 데이터 웹에 올리고 통일하자.»
    // 씨앗(PF.mp)은 조각을 구울 때 DB 에서 한 번 읽어 온 것이다. 여기서 웹 원장으로
    // 옮기고 저장하면 그 뒤로는 씨앗을 안 본다(migrated).
    // ⚠ 체결가는 빌더가 **분할 소급 기준으로 되맞춘 값**이다(split_factor) — 랩 종가가
    //   조정본이라 원장도 같은 눈금이어야 한다. 옮길 때 다시 손대지 않는다.
    if (!S.doc.migrated && PF.mp && PF.mp.length) {
      var _n = PF.mp.filter(function (t) { return t.idx === F.idx; }).length;
      h.push('<div class="migbox"><b>DB 원장 ' + _n + '건</b>이 아직 웹 원장 밖에 있습니다 — ' +
        '옮기면 이 화면이 웹 원장 하나로 굴러갑니다(사내 DB 의존이 사라집니다). ' +
        '<button class="sb primary" id="mig-' + slug + '">웹 원장으로 가져오기</button>' +
        '<span class="pnote">두 펀드 전체가 한 번에 옮겨집니다. 옮긴 뒤 «GitHub에 저장»을 눌러야 확정됩니다.</span></div>');
    }

    /* ── 일괄 입력 폼 (2026-08-26) ────────────────────────────────────────
       🚨 사용자 «하나의 전략을 추가하면서 다수 종목을 넣기 편하게. 빼는 것도 마찬가지.
         날짜 하나 전략 하나 종목 다수 하고 편입 편출 하면 딱딱 반영되게».
       종전에는 한 줄에 한 종목이었다 — 10종목 바스켓이면 같은 날짜·전략을 열 번 다시 쳤다.
       ⚠ «편입/편출» 을 고르게 하고 부호는 기계가 붙인다. 종전에는 매도를 «수량에 −» 로
         쳐야 했는데, 그건 사람이 틀리는 자리다(한 번 빠뜨리면 매도가 매수로 들어간다).
       ⚠ 편출은 수량을 비우면 **그 전략이 들고 있는 전량**이다 — «빼는 것도 마찬가지로
         편하게» 의 핵심이다. 순보유가 0 이면 미리보기가 막는다.
       ⚠ 티커에 공백이 들어간다(«NVDA US»). 그래서 «티커 수량» 을 **뒤에서** 가른다 —
         마지막 토막이 숫자면 그것이 수량이고 앞이 통째로 티커다. 앞에서 자르면
         «NVDA US 100» 이 티커 «NVDA» 로 잘린다. */
    var _held = {};                       // 전략|티커 → 순보유 수량(편출 전량 계산용)
    trs.forEach(function (t) { var k = t.s + '\u0000' + t.t; _held[k] = (_held[k] || 0) + t.q; });

    h.push('<form class="tradeform batch" id="tf-' + slug + '" autocomplete="off">');
    h.push('<div class="tfrow">' +
      '<label>날짜<input type="date" name="dt" value="' + esc(today()) + '" required></label>' +
      '<label>전략<input name="s" list="dl-s-' + slug + '" placeholder="전략 이름" required></label>' +
      '<label>구분<select name="dir"><option value="in">편입(매수)</option>' +
      '<option value="out">편출(매도)</option></select></label>' +
      '<label>가격<input name="p" type="number" step="any" placeholder="비우면 그날 종가"></label>' +
      '</div>');
    h.push('<datalist id="dl-s-' + slug + '">' + strategyNames(slug).map(function (n) {
      return '<option value="' + esc(n) + '">'; }).join('') + '</datalist>');
    h.push('<div class="tfrow tfmain">' +
      '<label class="tfgrow">종목<textarea name="tks" rows="4" required ' +
      'placeholder="한 줄에 하나 (쉼표도 됩니다)&#10;NVDA US 100&#10;AAPL US 50&#10;— 수량을 안 적으면 오른쪽 값을 씁니다"></textarea></label>' +
      '<div class="tfside">' +
      // ⚠ 티커 자동완성을 여기서 살린다. textarea 에는 datalist 를 못 붙이는데, 종목을
      //   여러 개 칠수록 오히려 더 필요한 자리다 — 골라서 위 칸에 **덧붙이는** 입구를 둔다.
      '<label>구성종목에서 찾기<input name="pick" list="dl-t-' + slug + '" ' +
      'placeholder="치고 Enter — 위에 줄로 붙습니다"></label>' +
      // 🚨 2026-08-26 사용자 «종목마다 같은 수량을 쓸 경우는 없으니까 빼고, 종목당 금액
      //   또는 종목당 비중(해당일자 NAV 대비)». 칸 둘을 나란히 두면 «둘 다 채우면?» 이
      //   생긴다 — **방식 하나 + 값 하나**로 묶어 그 물음 자체를 없앤다.
      '<label>배분<span class="tfalloc">' +
      '<select name="mode"><option value="amt">종목당 금액(USD)</option>' +
      '<option value="w">종목당 비중(NAV %)</option></select>' +
      '<input name="val" type="number" step="any" placeholder="값"></span></label>' +
      '<p class="pnote">줄에 <b>티커 수량 가격</b> 순으로 적으면 그것이 가장 셉니다 ' +
      '(예: <code>INTC US 1400 106.24</code> — 가격은 생략 가능).<br>' +
      '편출은 <b>비우면 전량</b>입니다. 정수 주식으로 <b>내림</b>합니다. ' +
      '쉼표는 종목 구분자라 <b>천단위 쉼표를 쓰지 마세요</b>.</p>' +
      '</div></div>');
    h.push('<datalist id="dl-t-' + slug + '">' + Object.keys(F.cons).sort().map(function (t) {
      return '<option value="' + esc(t) + '">' + esc(F.cons[t][1]) + '</option>';
    }).join('') + '</datalist>');
    h.push('<div class="tfprev" id="tfprev-' + slug + '"></div>');
    h.push('<input type="hidden" name="editid">');
    h.push('<div class="tfrow">' +
      '<button class="sb primary" type="submit" id="tfgo-' + slug + '">반영</button>' +
      '<button class="sb" type="button" id="tfcancel-' + slug + '" hidden>수정 취소</button>' +
      '<span class="perr" id="tferr-' + slug + '"></span></div>');
    h.push('</form>');

    if (trs.length) {
      // 진입 시점별 묶음(2026-08-20 사용자 지시 «DB 형태 말고 진입 시점별로 딱 보기 좋게»).
      // 같은 날 매매를 한 묶음으로 — 머리에 날짜·건수·투입금액·현재 평가손익 합.
      // 최신이 위로 온다(원장은 과거를 뒤지는 표가 아니라 «지금» 을 보는 표다).
      annotateRealized(trs);            // 매도 줄에 실현손익·실현수익률을 달아 둔다
      var byD = {};
      trs.forEach(function (t) { (byD[t.dt] = byD[t.dt] || []).push(t); });
      Object.keys(byD).sort().reverse().forEach(function (d0) {
        // 🚨 2026-09-16 — «평가» 합을 **매수/매도로 가른다.** 둘은 이름만 같지 다른 것을 잰다.
        //   매수 줄의 q×(현재가−체결가) 는 «아직 안 판 돈»(평가)이지만, 매도 줄에서 그 값은
        //   q<0 이라 부호가 뒤집혀 «팔고 나서 안 맞은 하락분»(회피)이 된다. 한 칸에 «평가»
        //   라고만 적어 두면 매도 묶음에서 뜻이 통째로 어긋난다 — 사용자가 「매도하고 가격
        //   떨어졌는데 수익률이 −」로 걸린 자리가 여기다(행의 «실현»은 원가 대비라 음수인데
        //   머리의 «평가»는 회피라 양수였고, 라벨이 그 차이를 하나도 말해 주지 않았다).
        //   ⚠ 실현과 회피를 더하지 않는다 — 실현은 «산 값 대비», 회피는 «판 값 대비»다.
        var g = byD[d0], inv = 0, pnlB = 0, pnlS = 0, npB = 0, npS = 0,
            nB = 0, nS = 0;
        g.forEach(function (t) {
          var p = pxLeI(t.t, asofI);
          inv += t.q * t.p;
          if (t.q < 0) {
            nS++;
            if (p != null) pnlS += t.q * (p - t.p); else npS++;
          } else {
            nB++;
            if (p != null) pnlB += t.q * (p - t.p); else npB++;
          }
        });
        // 그날 이 매매들이 펀드의 몇 %였나 — 묶음 머리에 합을 적는다(개별 열의 합계).
        var gw = 0, gwOK = false;
        g.forEach(function (t) {
          var w = wOfNav(F, t.dt, t.q, t.p);
          if (w != null) { gw += w; gwOK = true; }
        });
        h.push('<div class="ledgrp"><div class="ledhd"><b>' + esc(d0) + '</b>' +
          '<span>' + g.length + '건 · 투입 ' + num(inv, 0) + ' USD' +
          (gwOK ? ' · NAV 대비 ' + pct(gw / 100, 2, true) : '') + '</span>' +
          // 매수가 있는 묶음에만 «평가» 를 적는다(매도만인 날에 평가 0 을 적으면 안 판 것이 있다고 읽힌다).
          (nB ? '<span class="' + sgn(pnlB) + '">평가 ' + (pnlB > 0 ? '+' : '') + num(pnlB, 0) + ' USD' +
                (nS ? ' (매수 ' + nB + '건)' : '') +
                (npB ? ' (가격 없는 ' + npB + '건 제외)' : '') + '</span>' : '') +
          // 매도 묶음의 «회피» — 판 값 대비 지금 얼마나 빠졌나. 팔아서 번 돈이 아니라
          // «안 팔았으면 더 잃었을 돈»이다. 그래서 이름을 «평가» 와 다르게 준다.
          (nS ? '<span class="' + sgn(pnlS) + '" title="매도 후 회피 — 체결가 대비 현재가가 빠진 몫입니다. ' +
                  '판 값 대비라, 산 값 대비인 «실현» 과 더하면 안 됩니다.">매도 후 회피 ' +
                (pnlS > 0 ? '+' : '') + num(pnlS, 0) + ' USD' +
                (npS ? ' (가격 없는 ' + npS + '건 제외)' : '') + '</span>' : '') +
          // 🚨 2026-09-17 사용자 «매매내역에는 헷갈리니까 실현 빼고 기존 매매처럼 적어줘».
          //   «실현»(원가 대비)을 머리에서도 뺀다. 같은 줄에 기준이 다른 두 수가 나란히
          //   있으면 부호가 갈릴 때 어느 쪽을 봐야 할지 알 수 없다 — 실제로 그렇게 걸렸다
          //   (9/10 매도: 실현 −158,909 vs 회피 +129,214).
          //   ⚠ 원가·실현은 버리지 않는다. 줄의 title 로 남긴다(마우스를 올려야 보인다).
          '</div>');
        // 🚨 2026-08-26 사용자 «해당 일자 기준 종목별 비중(해당일자 NAV 대비) 열 추가».
        //   그 매매가 그날 펀드의 몇 %였나 — 손익만으로는 «얼마나 크게 걸었나» 가 안 보인다.
        h.push('<div class="tblwrap"><table class="big"><thead><tr><th>전략</th><th>티커</th>' +
          '<th class="tnum">수량</th><th class="tnum">체결가</th><th class="tnum">금액(USD)</th>' +
          '<th class="tnum">비중(NAV)</th>' +
          '<th class="tnum">현재가</th><th class="tnum">평가손익</th><th class="tnum">수익률</th><th></th></tr></thead><tbody>');
        g.forEach(function (t) {
          var p = pxLeI(t.t, asofI);
          /* 🚨 2026-09-17 사용자 «기존 매매처럼 적어줘. 나스닥 9/10 LITE 는 988.98 에
             팔았고 838.88 됐으니 111×(988.98−838.88) 이 평가손익이고 수익률도 그만큼 +».
             매수·매도를 **한 식**으로 되돌린다:
               평가손익 = 수량 × (현재가 − 체결가)      ← 매도는 수량이 음수라 부호가 뒤집힌다
               수익률   = 평가손익 ÷ |수량 × 체결가|
             매수에서는 종전과 똑같다(= 현재가/체결가 − 1). 매도에서는 «판 뒤 얼마나
             빠졌나» 가 + 로 나온다 — LITE: +16,661 · +15.2%.
             ⚠ 종전에는 수익률을 q>0 일 때만 채워 매도 줄이 통째로 «—» 였다. 그래서
               «실현» 을 넣었던 것인데, 기준이 다른 수가 한 표에 섞여 더 헷갈렸다.
               칸을 비우지도, 다른 기준을 섞지도 않는 길은 이 한 식뿐이다. */
          var pnl1 = p != null ? t.q * (p - t.p) : null;
          var r1 = (pnl1 != null && t.p > 0 && t.q) ? pnl1 / Math.abs(t.q * t.p) : null;
          var sell = t.q < 0, tip = '';
          if (sell) {
            tip = '체결 ' + num(t.p) + ' → 현재 ' + num(p) + ' · 판 값 대비';
            // ⚠ 원가·실현은 화면에서 뺐을 뿐 버리지 않는다 — 여기 남긴다.
            if (t.ravg != null)
              tip += ' / 이동평균 원가 ' + num(t.ravg) + ' 대비 실현 ' +
                     (t.rp > 0 ? '+' : '') + num(t.rp, 0) + ' USD (' + num(t.rn, 0) + '주' +
                     (t.rn < -t.q ? ' · 순보유 초과 ' + num(-t.q - t.rn, 0) + '주 제외' : '') + ')';
          }
          h.push('<tr' + (sell ? ' class="sellrow"' : '') + '><td>' +
            esc(t.s) + (t.src === 'web' ? ' <span class="badge web">웹</span>' : '') + '</td>' +
            '<td class="tk">' + esc(t.t) + '</td>' +
            '<td class="tnum">' + num(t.q, 0) + '</td><td class="tnum">' + num(t.p) + '</td>' +
            '<td class="tnum">' + num(t.q * t.p, 0) + '</td>' +
            '<td class="tnum">' + (function () {
              var w = wOfNav(F, t.dt, t.q, t.p);
              return w != null ? pct(w / 100, 2, true) : '—';
            })() + '</td>' +
            '<td class="tnum">' + (p != null ? num(p) : '—') + '</td>' +
            '<td class="tnum ' + sgn(pnl1) + '"' + (tip ? ' title="' + esc(tip) + '"' : '') + '>' +
              (pnl1 != null ? num(pnl1, 0) : '—') + '</td>' +
            '<td class="tnum ' + sgn(r1) + '"' + (tip ? ' title="' + esc(tip) + '"' : '') + '>' +
              (r1 != null ? pct(r1, 1, true) : '—') + '</td>' +
            '<td class="rowops">' + (t.src === 'web'
              ? '<button class="sb" data-edit="' + esc(t.id) + '">✎</button><button class="sb warn" data-del="' + esc(t.id) + '">✕</button>'
              : '') + '</td></tr>');
          if (t.note) h.push('<tr class="noterow"><td></td><td colspan="9">↳ ' + esc(t.note) + '</td></tr>');
        });
        h.push('</tbody></table></div></div>');
      });
    } else h.push('<p>매매가 없다 — 아래에서 첫 매매를 입력하세요.</p>');

    /* 🚨 2026-08-26 사용자 «전략 메모 상태 이런 불필요한 부분은 줄이고» —
         이 자리에 있던 «전략 메모·상태» 접이를 걷었다.
       · **메모**: 넣는 칸만 있고 **어디에도 안 나온다**(적어 보고 확인함 — 화면·표·성과
         어디서도 안 읽는다). 쓰는 곳 없는 입력은 칸만 먹고 «어딘가 쓰이겠지» 로 읽힌다.
         ⚠ 저장된 값은 **안 지운다.** S.doc.strategies[*].memo 는 그대로 두고 입구만 없앤다
           — 기록을 지우지 않는 것이 이 랩의 규약이고, 되살리려면 이 칸만 다시 그리면 된다.
       · **상태**: 쓰인다(성과 표의 «종료» 배지·흐린 줄). 그래서 없애지 않고 **쓰이는
         자리로 옮겼다** — 성과 표의 전략 이름 옆 작은 단추. 상태를 보는 곳과 바꾸는 곳이
         같아야 «지금 무엇이 종료인지» 를 두 군데서 안 찾는다. */
    box.innerHTML = h.join('');

    // 배선
    var _mig = el('mig-' + slug);
    if (_mig) _mig.addEventListener('click', function () {
      // 두 펀드를 한 번에 — 펀드마다 따로 누르면 절반만 옮겨진 상태가 생긴다.
      var byIdx = {};
      Object.keys(PF.funds).forEach(function (sg) { byIdx[PF.funds[sg].idx] = sg; });
      var add = 0;
      PF.mp.forEach(function (t) {
        var sg = byIdx[t.idx];
        if (!sg) return;
        // ⚠ 2026-08-26 사용자 «DB 원장에서 이전 글 써있는거 다 없애줘» — 옮겼다는 표시를
        //   매매마다 메모로 달지 않는다. 어차피 전 건에 같은 글이 붙어 아무것도 안 가르고,
        //   원장 표에서 줄마다 한 줄씩 더 차지했다. «옮겼나» 는 S.doc.migrated 가 갖는다.
        S.doc.trades.push({ id: uid(), fund: sg, dt: t.dt, s: t.s, t: t.t, q: t.q, p: t.p,
                            note: '' });
        add++;
      });
      S.doc.migrated = true;
      mark('DB 원장 ' + add + '건을 웹 원장으로 이전');
      renderAll();
    });
    var form = el('tf-' + slug);
    var _cx = el('tfcancel-' + slug);
    if (_cx) _cx.addEventListener('click', function () {
      form.reset(); form.dt.value = today(); form.editid.value = '';
      el('tferr-' + slug).textContent = '';
      _cx.hidden = true;
      refresh();                       // 단추 글자·미리보기를 한 곳에서 되돌린다
    });
    /* ── 미리보기 · 반영 (2026-08-26) ─────────────────────────────────────
       ⚠ 미리보기와 반영이 **같은 buildBatch 를 부른다.** 두 벌로 두면 «본 것과 다른 것이
         들어가는» 사고가 난다 — 이 저장소가 되풀이 밟은 종류다. */
    var prev = el('tfprev-' + slug), goBtn = el('tfgo-' + slug);
    function refresh() {
      var B = buildBatch(form, slug, _held);
      var editing = !!form.editid.value;
      if (!B.rows.length) {
        prev.innerHTML = '';
        goBtn.textContent = editing ? '수정 반영' : '반영';
        goBtn.disabled = true;
        return B;
      }
      var warnP = (!B.pFix && false);
      var ph = ['<div class="tblwrap"><table class="mini prevtbl"><thead><tr><th>티커</th>' +
        '<th class="tnum">수량</th><th class="tnum">가격</th><th class="tnum">금액(USD)</th>' +
        '<th class="tnum">비중(NAV)</th><th>비고</th></tr></thead><tbody>'];
      var tot = 0, totW = 0;
      B.rows.forEach(function (r) {
        var w = r.ok ? wOfNav(F, B.dt, r.q, r.p) : null;
        if (r.ok) { tot += r.q * r.p; if (w != null) totW += w; }
        ph.push('<tr class="' + (r.ok ? '' : 'badrow') + '"><td class="tk">' + esc(r.t) + '</td>' +
          '<td class="tnum ' + (r.q < 0 ? 'neg' : '') + '">' + (r.q != null ? num(r.q, 0) : '—') + '</td>' +
          '<td class="tnum">' + (r.p != null ? num(r.p) : '—') + '</td>' +
          '<td class="tnum">' + (r.ok ? num(r.q * r.p, 0) : '—') + '</td>' +
          '<td class="tnum">' + (w != null ? pct(w / 100, 2, true) : '—') + '</td>' +
          '<td class="prevwhy">' + esc(r.why) + '</td></tr>');
      });
      ph.push('</tbody><tfoot><tr><td><b>' + B.rows.length + '종</b></td><td class="tnum"></td>' +
        '<td class="tnum"></td><td class="tnum"><b>' + num(tot, 0) + '</b></td>' +
        '<td class="tnum"><b>' + pct(totW / 100, 2, true) + '</b></td>' +
        '<td>' + (B.n === B.rows.length ? '' : '<span class="perr">' +
          (B.rows.length - B.n) + '종은 반영되지 않습니다</span>') + '</td></tr></tfoot></table></div>');
      // ⚠ 어느 NAV 로 나눴는지 말한다. 옛 조각은 시계열이 없어 최신 NAV 로 버티는데,
      //   그 사실을 안 적으면 과거 일자의 비중이 «맞는 수» 처럼 읽힌다.
      if (!B.navfx.exact)
        ph.push('<p class="pnote">비중은 <b>최신 NAV·환율</b> 기준입니다 — 조각에 일자별 ' +
                'NAV 가 아직 없습니다(사내 PC 에서 <span class="tk">pf</span> 를 한 번 돌리면 ' +
                '그 날짜의 NAV 로 바뀝니다).</p>');
      if (B.pFix != null && B.rows.length > 1)
        ph.push('<p class="warn">⚠ 가격을 직접 넣으면 <b>모든 종목에 같은 값</b>이 들어갑니다 — ' +
                '여러 종목이면 비워 두고 그날 종가를 쓰세요.</p>');
      prev.innerHTML = ph.join('');
      goBtn.textContent = editing ? '수정 반영' : (B.n ? B.n + '건 반영' : '반영');
      goBtn.disabled = !B.n;
      return B;
    }
    ['input', 'change'].forEach(function (ev) { form.addEventListener(ev, refresh); });
    // 「구성종목에서 찾기」 — 고른 것을 종목 칸에 줄로 덧붙인다.
    // ⚠ Enter 를 가로챈다. 폼 안의 input 에서 Enter 는 제출이라, 안 막으면 종목 하나를
    //   고를 때마다 원장에 들어간다.
    var pick = form.pick;
    function addPick() {
      var v = String(pick.value || '').trim().toUpperCase();
      if (!v) return;
      var cur = form.tks.value.replace(/\s+$/, '');
      form.tks.value = (cur ? cur + '\n' : '') + v;
      pick.value = '';
      refresh();
    }
    if (pick) {
      pick.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter') { ev.preventDefault(); addPick(); }
      });
      // 목록에서 마우스로 고르면 keydown 이 안 온다 — change 로도 받는다.
      pick.addEventListener('change', function () { if (pick.value) addPick(); });
    }
    refresh();

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var errEl = el('tferr-' + slug);
      errEl.textContent = '';
      var B = buildBatch(form, slug, _held);
      if (!B.s) { errEl.textContent = '전략 이름이 비었습니다.'; return; }
      var ok = B.rows.filter(function (r) { return r.ok; });
      if (!ok.length) { errEl.textContent = '반영할 종목이 없습니다 — 위 비고를 확인하세요.'; return; }
      var editId = String(form.editid.value || '');
      if (editId) {
        // ⚠ 수정은 한 줄짜리다. 여러 줄을 친 채 «수정 반영» 을 누르면 첫 줄만 반영되고
        //   나머지가 조용히 사라진다 — 그래서 막고 말한다.
        if (ok.length > 1) { errEl.textContent = '수정은 한 종목만 됩니다 — 종목 칸을 한 줄로 줄이세요.'; return; }
        var tr = S.doc.trades.find(function (x) { return x.id === editId; });
        if (tr) { tr.dt = B.dt; tr.s = B.s; tr.t = ok[0].t; tr.q = ok[0].q; tr.p = ok[0].p; }
        mark('매매 수정 — ' + B.dt + ' ' + ok[0].t + ' ' + num(ok[0].q, 0) + '주 @' + num(ok[0].p), slug);
        return;
      }
      ok.forEach(function (r) {
        S.doc.trades.push({ id: uid(), fund: slug, dt: B.dt, s: B.s,
                            t: r.t, q: r.q, p: r.p, note: '' });
      });
      mark((B.out ? '편출' : '편입') + ' ' + ok.length + '종 — ' + B.dt + ' 「' + B.s + '」 ' +
           ok.slice(0, 4).map(function (r) { return r.t; }).join(' · ') +
           (ok.length > 4 ? ' 외 ' + (ok.length - 4) + '종' : ''), slug);
    });
    box.querySelectorAll('button[data-del]').forEach(function (b) {
      b.addEventListener('click', function () {
        var _t = S.doc.trades.find(function (x) { return x.id === b.dataset.del; }) || {};
        if (!confirm('이 매매를 지울까요?\n\n' + (_t.dt || '') + ' ' + (_t.t || '') + ' ' + (_t.q || '') + '주\n' +
                     '(«저장»을 누르기 전에는 «변경 취소»로 되돌릴 수 있습니다)')) return;
        S.doc.trades = S.doc.trades.filter(function (x) { return x.id !== b.dataset.del; });
        mark('매매 삭제 — ' + (_t.dt || '') + ' ' + (_t.t || '') + ' ' + (_t.q || '') + '주', slug);
      });
    });
    box.querySelectorAll('button[data-edit]').forEach(function (b) {
      b.addEventListener('click', function () {
        var tr = S.doc.trades.find(function (x) { return x.id === b.dataset.edit; });
        if (!tr) return;
        // 일괄 폼으로 되돌린다 — 부호는 «구분» 이 갖고 수량은 절대값으로 넣는다.
        //   그래야 화면이 말하는 것(편입/편출)과 저장되는 부호가 한 벌이다.
        form.dt.value = tr.dt; form.s.value = tr.s;
        // 수량은 종목 줄에 «티커 수량» 으로 되돌린다 — 배분 칸은 비운다(그 칸은 «나눠 담기»
        //   용이고, 수정은 이미 정해진 한 건을 고치는 일이라 배분이 끼면 값이 덮인다).
        form.tks.value = tr.t + ' ' + Math.abs(tr.q);
        form.dir.value = tr.q < 0 ? 'out' : 'in';
        form.val.value = ''; form.p.value = tr.p;
        form.editid.value = tr.id;
        var _c1 = el('tfcancel-' + slug); if (_c1) _c1.hidden = false;
        refresh();
        form.scrollIntoView({ block: 'center' });
      });
    });
  }

  /* ── 일괄 입력 해석 (2026-08-26 · 가격 토막 2026-09-16) ────────────────────
     한 줄(또는 쉼표 한 토막) = 한 종목.
       «티커»                 수량·가격은 폼에서 정한다
       «티커 수량»            가격은 폼에서 정한다
       «티커 수량 가격»       ← 2026-09-16 추가
     🚨 가격 토막을 왜 넣나. 사내 매매내역 CSV 는 종목마다 **실제 체결가**가 다른데 폼의
       «가격» 칸은 전 종목에 하나뿐이라, 그대로 넣으면 10건이 전부 그날 종가로 기록된다.
       랩 원장이 여태 «체결가 = 당시 종가»였던 것이 정확히 그 제약이었다 — 실체결가가
       손에 있는데 버릴 이유가 없다.
     ⚠ 뒤에서 가른다 — 티커에 공백이 있다(«NVDA US»). 뒤쪽 숫자 토막을 최대 둘까지 떼고
       남은 앞부분이 티커다. 앞에서 자르면 «NVDA US 100» 의 티커가 «NVDA» 가 된다.
     ⚠ 천단위 쉼표를 쓰지 말 것 — 쉼표는 **종목 구분자**라 «1,400» 은 두 종목이 된다. */
  /* ── 매도의 «실현» (2026-09-16) ────────────────────────────────────────────
     사용자 지시 — «9월 10일 매도 부분 수익률도 나오게 해줘. sell 이니까 빠진만큼 + 해주면 될듯».

     왜 필요한가. 행의 «평가손익» 은 q×(현재가−체결가) 다. 매도(q<0)에서 그 값은
     «팔고 나서 얼마나 덜 손해봤나» 이지 **팔아서 번 돈이 아니다**. 그리고 수익률 칸은
     `t.q > 0` 일 때만 채우고 있어 **매도 줄이 통째로 «—»** 였다(09-10 매도 10건 실측).
     → 매도 줄에는 «실현» 을 적는다: 이동평균 원가 대비 얼마에 팔았나.

     ⚠ 전략×종목으로 따로 센다 — 같은 종목을 두 전략이 들면 원가가 섞이면 안 된다.
     ⚠ **이동평균 원가**다(FIFO 아님). 원장이 로트를 안 들고 있어 FIFO 를 만들 수 없다.
     ⚠ 순보유를 넘겨 판 몫은 원가가 없다 — 그 몫은 실현에서 뺀다(rn 에 실제로 센 수량을
       적어 두고 화면이 «순보유 초과분 제외» 를 말할 수 있게 한다). */
  function annotateRealized(trs) {
    var pos = {};
    trs.slice().sort(function (a, b) { return a.dt < b.dt ? -1 : a.dt > b.dt ? 1 : 0; })
      .forEach(function (t) {
        t.rp = t.rr = t.ravg = null; t.rn = 0;
        var k = t.s + '\u0000' + t.t, P = pos[k] || (pos[k] = { q: 0, cost: 0 });
        if (t.q > 0) { P.q += t.q; P.cost += t.q * t.p; return; }
        if (!(t.q < 0)) return;
        var avg = P.q > 0 ? P.cost / P.q : null;
        var n = Math.min(-t.q, P.q);
        if (avg != null && n > 0) {
          t.rp = n * (t.p - avg);
          t.rr = avg > 0 ? (t.p / avg - 1) : null;
          t.ravg = avg; t.rn = n;
          P.cost -= n * avg; P.q -= n;
        }
      });
    return trs;
  }

  function parseTickerLines(text) {
    return String(text || '').split(/[\n;,]+/).map(function (x) { return x.trim(); })
      .filter(Boolean).map(function (line) {
        var m = line.match(/^(.*\S)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)$/);
        if (m) return { t: m[1].trim().toUpperCase(), q: parseFloat(m[2]), p: parseFloat(m[3]) };
        m = line.match(/^(.*\S)\s+(-?\d+(?:\.\d+)?)$/);
        return m ? { t: m[1].trim().toUpperCase(), q: parseFloat(m[2]), p: null }
                 : { t: line.toUpperCase(), q: null, p: null };
      });
  }

  /* 미리보기 줄을 만든다 — 반영과 **같은 함수**를 쓴다. 두 벌이면 «미리보기와 다른 것이
     들어가는» 사고가 난다(이 저장소가 다른 자리에서 되풀이 밟은 종류다). */
  function buildBatch(form, slug, held) {
    var fd = new FormData(form);
    var dt0 = String(fd.get('dt') || '');
    var sname = String(fd.get('s') || '').trim();
    var out = String(fd.get('dir') || 'in') === 'out';
    var mode = String(fd.get('mode') || 'amt');
    var val = (fd.get('val') !== '' && fd.get('val') != null) ? Math.abs(parseFloat(fd.get('val'))) : null;
    var pFix = (fd.get('p') !== '' && fd.get('p') != null) ? parseFloat(fd.get('p')) : null;
    var di = dLe(dt0);
    // 비중 배분에 쓸 그날 NAV·환율. 시계열이 없는 옛 조각이면 최신 값으로 버틴다(exact=false).
    var A = navFxAt(PF.funds[slug], dt0);
    var perStock = null;                            // 종목당 배분 금액(USD)
    if (val != null)
      perStock = (mode === 'w') ? ((A.nav > 0 && A.fx > 0) ? A.nav * val / 100 / A.fx : null) : val;
    var rows = parseTickerLines(fd.get('tks')).map(function (e) {
      var r = { t: e.t, why: '' };
      if (e.p != null) {
        // 줄에 적은 **실체결가**가 가장 세다. 🚨 반올림하지 않는다 — 521.095 를 521.1 로
        // 접으면 실체결가를 쓰려고 넣은 칸이 도로 근사값이 된다.
        r.p = e.p;
      } else {
        r.p = pFix != null ? pFix : (di >= 0 ? pxAt(e.t, di) : null);
        if (r.p != null) r.p = Math.round(r.p * 100) / 100;
      }
      var q = e.q != null ? Math.abs(e.q) : null;    // 줄에 적은 수량이 가장 세다
      if (q == null && out && perStock == null) {
        var hq = held[sname + '\u0000' + e.t] || 0;      // 편출 기본 = 전량
        q = hq > 0 ? hq : null;
        r.why = (q == null) ? '이 전략에 순보유가 없습니다' : '전량';
      }
      if (q == null && perStock != null && r.p > 0) {
        q = Math.floor(perStock / r.p);                  // 금액·비중 → 정수 주식(내림)
        if (!q) r.why = (mode === 'w' ? '비중이 1주 값보다 작습니다' : '금액이 1주 값보다 작습니다');
      }
      if (q == null && val != null && mode === 'w' && !(A.nav > 0 && A.fx > 0))
        r.why = '그날 NAV·환율이 없어 비중을 못 바꿉니다';
      r.q = (q && q > 0) ? (out ? -q : q) : null;
      if (r.q == null && !r.why) r.why = '수량을 정할 수 없습니다';
      if (r.p == null && !r.why) r.why = '그날 종가가 패널에 없습니다 — 가격을 직접 넣으세요';
      else if (r.q != null && TKI[r.t] == null && !r.why) r.why = '패널에 없는 티커 — 성과에 가격이 안 잡힙니다';
      if (out && r.q != null) {
        var hq2 = held[sname + '\u0000' + r.t] || 0;
        if (-r.q > hq2 + 1e-9) r.why = (r.why ? r.why + ' · ' : '') + '순보유(' + num(hq2, 0) + ')보다 많이 뺍니다';
      }
      r.ok = (r.q != null && r.p != null && r.p > 0);
      return r;
    });
    return { dt: dt0, s: sname, out: out, rows: rows, mode: mode, navfx: A,
             n: rows.filter(function (r) { return r.ok; }).length, pFix: pFix };
  }

  // ── 렌더: 성과(④) ───────────────────────────────────────────────────────
  function renderPerf(slug) {
    var box = el('perf-' + slug);
    if (!box) return;
    var F = PF.funds[slug];
    var trs = mergedTrades(slug);
    var h = [];
    // ⚠ 지난 렌더의 막대 자료를 지운다. 이 속성은 DOM 요소에 남으므로, 안 지우면 이번에
    //   그릴 것이 없을 때 **옛 막대를 다시 그린다**(원장을 비운 직후가 그 자리다).
    box._pfBars = null;
    if (!trs.length) { box.innerHTML = '<p>매매가 없어 성과를 계산할 것이 없다.</p>'; return; }
    var asofI = dLe(F.asof_us);
    var cp = calcPerf(slug, trs, asofI);
    var perf = cp.byS, sk = cp.skipped;

    h.push('<div class="prbar"><button class="sb" id="pdf-' + slug + '">전략 성과 PDF</button>' +
      '<span class="pnote">브라우저 인쇄 대화상자에서 «대상 → PDF로 저장» 을 고르면 됩니다.</span></div>');
    var cc = crossCheck(slug);
    if (cc.n) {
      h.push(cc.skip ? '<p class="pnote">교차검증 생략 — ' + esc(cc.skip) + '</p>'
        : cc.bad.length
        ? '<p class="warn">⚠ 교차검증 불일치 — 파이썬 스냅샷과 JS 계산이 다릅니다: ' + esc(cc.bad.join(' / ')) + '</p>'
        : '<p class="ccok">✓ 교차검증 — DB 원장 ' + cc.n + '개 전략에서 파이썬 계산과 일치</p>');
    }
    if (sk.old + sk.future + sk.nopx) {
      var parts = [];
      if (sk.old) parts.push('가격 패널(' + esc(PF.dates[0]) + '~) 이전 ' + sk.old + '건');
      if (sk.future) parts.push('기준일(' + esc(F.asof_us) + ') 이후 ' + sk.future + '건 — 다음 종가부터 반영');
      if (sk.nopx) parts.push('가격 없는 종목 ' + sk.nopx + '건');
      h.push('<p class="warn">⚠ 성과 계산에서 제외된 매매: ' + parts.join(' · ') + '</p>');
    }

    h.push('<div class="tblwrap"><table class="big"><thead><tr><th>전략</th><th class="tnum">매수원금(USD)</th>' +
      '<th class="tnum">손익</th><th class="tnum">수익률</th><th class="tnum">BM</th>' +
      '<th class="tnum">초과</th><th class="tnum">NAV 기여(bp)</th></tr></thead><tbody>');
    var totExc = 0;
    Object.keys(perf).sort().forEach(function (sname) {
      var L = perf[sname].last;
      if (!L) return;
      var exc = L.pnl - L.bm;
      totExc += exc;
      var bp = exc * F.fx / F.nav * 1e4;
      var closed = (S.doc.strategies[sname] || {}).status === 'closed';
      // 상태 단추 — 보는 자리에서 바로 바꾼다(종전에는 원장 아래 별도 접이에 있었다).
      h.push('<tr' + (closed ? ' class="closedrow"' : '') + '><td>' + esc(sname) +
        (perf[sname].warn.length ? ' ⚠' + esc(perf[sname].warn.join(',')) : '') +
        ' <button type="button" class="sstat' + (closed ? ' off' : '') + '" data-s="' + esc(sname) +
        '" title="누르면 운용중/종료를 바꿉니다">' + (closed ? '종료' : '운용중') + '</button></td>' +
        '<td class="tnum">' + num(L.inv, 0) + '</td>' +
        '<td class="tnum ' + sgn(L.pnl) + '">' + num(L.pnl, 0) + '</td>' +
        '<td class="tnum">' + pct(L.ret, 2, true) + '</td>' +
        '<td class="tnum">' + pct(L.bmRet, 2, true) + '</td>' +
        '<td class="tnum ' + sgn(exc) + '">' + num(exc, 0) + '</td>' +
        '<td class="tnum ' + sgn(bp) + '">' + (bp > 0 ? '+' : '') + bp.toFixed(1) + '</td></tr>');
    });
    var totBp = totExc * F.fx / F.nav * 1e4;
    h.push('<tr class="totrow"><td><b>합계</b></td><td></td><td></td><td></td><td></td>' +
      '<td class="tnum ' + sgn(totExc) + '"><b>' + num(totExc, 0) + '</b></td>' +
      '<td class="tnum ' + sgn(totBp) + '"><b>' + (totBp > 0 ? '+' : '') + totBp.toFixed(1) + '</b></td></tr>');
    h.push('</tbody></table></div>');

    var series = [];
    Object.keys(perf).sort().forEach(function (sname) {
      var pts = perf[sname].curve
        .filter(function (c) { return c[3]; })
        .map(function (c) { return [PF.dates[c[0]], (c[1] - c[2]) / c[3] * 100]; });
      if (pts.length) series.push([sname, pts]);
    });
    if (series.length)
      h.push('<div class="chart"><div class="chtitle">전략별 누적 초과수익(%, 매수원금 대비)' +
        '<span class="hnote">빨간 0선 = 지수와 같은 성과</span></div>' +
        svgLines(series, series.map(function (s) { return s[0].slice(0, 16); }), null, null, 'var(--hot)') + '</div>');

    /* ── 종목별 등락률·기여도 (2026-08-26) ────────────────────────────────
       🚨 사용자 «구성종목별 등락률이나 기여도도 차트로 딱 볼 수 있게». 접이 밖에 둔다 —
         펴야 보이면 «딱 볼 수 있게» 가 아니다.
       ⚠ **종목 기준으로 합친다.** 한 종목이 여러 전략에 들어 있으면 rows 에 따로 뜨는데,
         그대로 그리면 같은 티커 막대가 둘 나와 어느 쪽이 그 종목의 성적인지 안 보인다.
         손익·초과·원금은 더하고, 등락률은 원금 가중으로 다시 낸다(단순 평균은 큰 자리와
         작은 자리를 같게 세어 거짓이 된다).
       ⚠ 세 눈금은 서로 다른 질문에 답한다 — 한 그림에 겹치지 않고 단추로 가른다:
         등락률 = «얼마나 올랐나» · 기여 = «펀드에 얼마를 보탰나»(크기까지 담는다) ·
         초과 = «지수 대비». 등락률만 보면 작은 자리가 크게 보인다. */
    var agg = {};
    Object.keys(perf).forEach(function (sname) {
      (perf[sname].rows || []).forEach(function (r) {
        var a2 = agg[r.t] || (agg[r.t] = { t: r.t, inv: 0, pnl: 0, exc: 0, n: 0 });
        a2.inv += (r.inv != null ? r.inv : 0);
        a2.pnl += (r.pnl || 0); a2.exc += (r.exc || 0); a2.n++;
      });
    });
    var aggL = Object.keys(agg).map(function (t) { return agg[t]; });
    if (aggL.length) {
      var VIEWS = {
        bp:  { lab: 'NAV 기여(bp)', unit: 'bp', nd: 1,
               f: function (a2) { return a2.exc * F.fx / F.nav * 1e4; },
               note: '초과손익을 펀드 순자산으로 나눈 것 — 종목 크기까지 담는다' },
        ret: { lab: '등락률(%)', unit: '%', nd: 2,
               f: function (a2) { return a2.inv > 0 ? a2.pnl / a2.inv * 100 : null; },
               note: '매수원금 대비 손익 — 자리 크기와 무관한 순수 등락' },
        exc: { lab: '초과손익(USD)', unit: '', nd: 0,
               f: function (a2) { return a2.exc; },
               note: '같은 날 같은 금액을 지수에 넣었을 때 대비' }
      };
      h.push('<div class="chart barchart" id="bars-' + slug + '">');
      h.push('<div class="chtitle">종목별 <span class="barbtns">' +
        Object.keys(VIEWS).map(function (k) {
          return '<button type="button" class="bbt" data-v="' + k + '"' +
                 (k === 'bp' ? ' aria-pressed="true"' : '') + '>' + esc(VIEWS[k].lab) + '</button>';
        }).join('') + '</span><span class="hnote barnote">' + esc(VIEWS.bp.note) + '</span></div>');
      h.push('<div class="barbody"></div></div>');
      // 그리기는 DOM 이 붙은 뒤에 한다 — 아래 box.innerHTML 다음에서 배선한다
      var _mk = function (k) {
        var V = VIEWS[k];
        var items = aggL.map(function (a2) { return { k: a2.t, v: V.f(a2) }; })
                        .filter(function (x) { return x.v != null && isFinite(x.v); })
                        .sort(function (x, y) { return y.v - x.v; });
        return { html: svgBars(items, V.unit, V.nd), note: V.note, n: items.length };
      };
      box._pfBars = { mk: _mk, def: 'bp' };
    }

    Object.keys(perf).sort().forEach(function (sname) {
      var rows = perf[sname].rows;
      if (!rows.length) return;
      h.push('<details><summary>' + esc(sname) + ' — 종목별 분해</summary><div class="tblwrap"><table class="mini"><thead><tr>' +
        '<th>티커</th><th class="tnum">순수량</th><th class="tnum">현재가</th><th class="tnum">손익(USD)</th>' +
        '<th class="tnum">수익률</th><th class="tnum">초과(USD)</th></tr></thead><tbody>');
      rows.forEach(function (r) {
        h.push('<tr><td class="tk">' + esc(r.t) + (r.warn ? ' ⚠' : '') + '</td>' +
          '<td class="tnum">' + num(r.q, 0) + '</td><td class="tnum">' + num(r.px) + '</td>' +
          '<td class="tnum ' + sgn(r.pnl) + '">' + num(r.pnl, 0) + '</td>' +
          '<td class="tnum">' + pct(r.ret, 2, true) + '</td>' +
          '<td class="tnum ' + sgn(r.exc) + '">' + num(r.exc, 0) + '</td></tr>');
      });
      h.push('</tbody></table></div></details>');
    });
    var _bars = box._pfBars;
    box.innerHTML = h.join('');
    var _pdf = el('pdf-' + slug);
    if (_pdf) _pdf.addEventListener('click', function () { printReport(slug); });
    box.querySelectorAll('.sstat').forEach(function (b2) {
      b2.addEventListener('click', function () {
        var m = S.doc.strategies[b2.dataset.s] = S.doc.strategies[b2.dataset.s] || {};
        m.status = (m.status === 'closed') ? 'active' : 'closed';
        mark('전략 상태 — ' + b2.dataset.s + ' → ' + (m.status === 'closed' ? '종료' : '운용중'), slug);
      });
    });
    // ⚠ 배선은 innerHTML **뒤에** 한다. 앞에서 하면 방금 그린 노드가 통째로 갈아치워져
    //   단추가 조용히 죽는다(이 저장소가 다른 화면에서 밟은 자리다).
    if (_bars) {
      var wrap = el('bars-' + slug);
      var body = wrap && wrap.querySelector('.barbody');
      var note = wrap && wrap.querySelector('.barnote');
      var draw = function (k) {
        var r = _bars.mk(k);
        body.innerHTML = r.n ? r.html : '<p class="pnote">이 눈금으로 그릴 종목이 없습니다.</p>';
        if (note) note.textContent = r.note;
        [].slice.call(wrap.querySelectorAll('.bbt')).forEach(function (b2) {
          b2.setAttribute('aria-pressed', b2.dataset.v === k ? 'true' : 'false');
        });
        try { sessionStorage.setItem('pf.barview', k); } catch (e) {}
      };
      [].slice.call(wrap.querySelectorAll('.bbt')).forEach(function (b2) {
        b2.addEventListener('click', function () { draw(b2.dataset.v); });
      });
      var want = null;
      try { want = sessionStorage.getItem('pf.barview'); } catch (e) {}
      // ⚠ 저장값을 그대로 믿지 않는다 — 눈금 이름이 바뀌면 없는 키로 그리다 죽는다.
      //   실제로 단추가 있는 값일 때만 쓴다.
      draw(want && wrap.querySelector('.bbt[data-v="' + want + '"]') ? want : _bars.def);
    }
  }

  // ── 렌더: 백테스트(⑤) ───────────────────────────────────────────────────
  function renderBT() {
    var box = el('btbox');
    if (!box) return;
    var h = [];
    h.push('<form class="btform" id="btform">');
    h.push('<select name="uni"><option value="ndx">나스닥100</option><option value="spx">S&amp;P500</option></select>');
    h.push('<select name="rule"><option value="mom">모멘텀 상위 N (L개월−1개월)</option>' +
      '<option value="wtop">지수비중 상위 N</option>' +
      '<option value="eqw">구성 전체 동일가중</option>' +
      '<option value="basket">직접 바스켓(동일가중)</option></select>');
    h.push('<label>N <input name="n" type="number" value="10" min="1" max="100" style="width:56px"></label>');
    h.push('<label>L <select name="lb"><option value="3">3개월</option><option value="6" selected>6개월</option><option value="12">12개월</option></select></label>');
    h.push('<input name="basket" placeholder="바스켓 티커(쉼표 구분, 예: NVDA US, MSFT US)" style="min-width:240px">');
    h.push('<button class="sb primary" type="submit">돌리기</button>');
    h.push('</form>');
    h.push('<div id="btout"><p class="pnote">규칙을 고르고 돌리세요 — 월간 리밸런스 · 거래비용 0 가정.</p></div>');
    box.innerHTML = h.join('');
    el('btform').addEventListener('submit', function (e) {
      e.preventDefault();
      var fd = new FormData(e.target);
      try {
        runBT(String(fd.get('uni')), String(fd.get('rule')), parseInt(fd.get('n'), 10) || 10,
              parseInt(fd.get('lb'), 10) || 6, String(fd.get('basket') || ''));
      } catch (err) {
        el('btout').innerHTML = '<p class="perr">' + esc(err.message) + '</p>';
      }
    });
  }

  function runBT(slug, rule, N, lbM, basketRaw) {
    var F = PF.funds[slug];
    var lvl = PF.lvl[slug];
    var out = el('btout');
    var uni = rule === 'basket'
      ? basketRaw.split(',').map(function (s) { return s.trim().toUpperCase(); }).filter(Boolean)
      : Object.keys(F.cons);
    if (rule === 'basket' && !uni.length) throw new Error('바스켓 티커를 넣으세요.');

    var lbD = lbM * 21, skipD = 21;
    // mom 은 첫 리밸런스일에 i−skipD−lbD 종가가 필요하다 — lbD+2 로 잡으면 첫 달 신호가
    // 전부 null 이라 조용히 현금으로 시작한다(적대감사 12). skipD 까지 확보하고 시작한다.
    var startI = rule === 'mom' ? lbD + skipD + 2 : 1;
    if (startI >= ND - 21) throw new Error('패널이 짧아 이 설정으로 못 돌립니다.');

    // 적격성 — 창 전체 커버 + 분할의심(하루 |40%| 초과) 제외. 제외는 반드시 공시한다.
    var elig = [], exSplit = [], exCover = [];
    uni.forEach(function (t) {
      var k = TKI[t];
      if (k == null) { exCover.push(t); return; }
      var miss = 0, prev = null, split = false;
      for (var i = 0; i < ND; i++) {
        var v = U16[k * ND + i];
        if (!v) { miss++; continue; }
        var p = v / PF.panel.scale[k] * PF.panel.p0[k];
        if (prev != null && Math.abs(p / prev - 1) > PF.guard) split = true;
        prev = p;
      }
      if (split) exSplit.push(t);
      else if (miss > ND * 0.1) exCover.push(t);
      else elig.push(t);
    });
    if (!elig.length) throw new Error('적격 종목이 없습니다(제외: 분할의심 ' + exSplit.length + ' · 데이터부족 ' + exCover.length + ').');

    // 월초 리밸런스 지점
    var rebs = [];
    for (var i = startI; i < ND; i++)
      if (PF.dates[i].slice(0, 7) !== PF.dates[i - 1].slice(0, 7)) rebs.push(i);
    if (!rebs.length || rebs[0] > ND - 5) throw new Error('리밸런스 지점이 없습니다.');

    function pick(i) {
      if (rule === 'eqw' || rule === 'basket') return elig;
      if (rule === 'wtop')
        return elig.slice().sort(function (a, b) { return F.cons[b][0] - F.cons[a][0]; }).slice(0, N);
      // mom: (t-21 종가)/(t-21-lbD 종가) − 1 — 신호는 리밸런스일 «이전» 종가만 쓴다(선견 차단).
      var scored = [];
      elig.forEach(function (t) {
        var p1 = pxLeI(t, i - skipD), p0 = pxLeI(t, i - skipD - lbD);
        if (p1 != null && p0 != null && p0 > 0) scored.push([t, p1 / p0 - 1]);
      });
      scored.sort(function (a, b) { return b[1] - a[1]; });
      return scored.slice(0, N).map(function (x) { return x[0]; });
    }

    var i0 = rebs[0];
    var V = 100, shares = {};
    var curve = [[PF.dates[i0], 100]], rets = [];
    var nextReb = 0;
    for (var d = i0; d < ND; d++) {
      // 🚨 순서가 정확성이다: ① 어제 보유분을 오늘 종가로 «먼저» 평가해 하루 수익을 확정하고
      //    ② 그다음 리밸런스한다. 리밸런스를 먼저 하면 그날 하루치 수익이 통째로 0 이 된다
      //    (적대감사 10 — 시뮬레이션으로 확정: 리밸런스일 2배 상승이 완전 소실).
      if (d > i0) {
        var v2 = 0;
        Object.keys(shares).forEach(function (t) { var p = pxLeI(t, d); if (p) v2 += shares[t] * p; });
        if (v2 > 0) { rets.push(v2 / V - 1); V = v2; }
      }
      if (nextReb < rebs.length && d === rebs[nextReb]) {
        // 가격 없는 선정 종목은 여기서 걸러 1/n 을 «남은 종목에» 재배분한다 — 안 거르면
        // 그 비중이 현금도 아닌 채로 증발해 가짜 −1/n 손실이 된다(적대감사 11).
        var names = pick(d).filter(function (t) { return pxLeI(t, d) != null; });
        if (names.length) {
          shares = {};
          var w = 1 / names.length;
          names.forEach(function (t) { shares[t] = V * w / pxLeI(t, d); });
        }
        nextReb++;
      }
      if (d > i0) curve.push([PF.dates[d], V]);
    }
    var bmCurve = [], bm0 = lvlLeI(lvl, i0);
    for (var d2 = i0; d2 < ND; d2++) {
      var lv = lvlLeI(lvl, d2);
      bmCurve.push([PF.dates[d2], lv && bm0 ? lv / bm0 * 100 : null]);
    }
    bmCurve = bmCurve.filter(function (p) { return p[1] != null; });

    var totR = V / 100 - 1;
    var bmR = bmCurve.length ? bmCurve[bmCurve.length - 1][1] / 100 - 1 : null;
    var mean = rets.reduce(function (a, b) { return a + b; }, 0) / (rets.length || 1);
    var vol = Math.sqrt(rets.reduce(function (a, b) { return a + (b - mean) * (b - mean); }, 0) / Math.max(1, rets.length - 1)) * Math.sqrt(252);
    var peak = -1, mdd = 0;
    curve.forEach(function (p) { peak = Math.max(peak, p[1]); mdd = Math.min(mdd, p[1] / peak - 1); });

    var h = [];
    h.push('<div class="chart"><div class="chtitle">전략 vs ' + esc(F.idx.split(' ')[0]) + ' (시작=100 · ' +
      esc(PF.dates[i0]) + '~' + esc(PF.dates[ND - 1]) + ')</div>' +
      // 벤치마크는 빨강 — 화면 전체 규약(연초 후 차트와 같다).
      svgLines([['전략', curve, 'var(--accent)'], ['지수', bmCurve, 'var(--hot)']], ['전략', '지수(PR)']) + '</div>');
    h.push('<table class="mini"><tbody>' +
      '<tr><td>기간수익 전략 / 지수 / 초과</td><td class="tnum">' + pct(totR, 1, true) + ' / ' + pct(bmR, 1, true) +
      ' / <b class="' + sgn(totR - bmR) + '">' + pct(totR - bmR, 1, true) + '</b></td></tr>' +
      '<tr><td>연변동성 / MDD</td><td class="tnum">' + pct(vol, 1) + ' / ' + pct(mdd, 1) + '</td></tr>' +
      '<tr><td>보유 종목 수 / 리밸런스</td><td class="tnum">' + (rule === 'eqw' ? elig.length : Math.min(N, elig.length)) + '종 / 월간 ' + rebs.length + '회</td></tr>' +
      '<tr><td>제외 종목</td><td class="tnum">분할의심 ' + exSplit.length + ' · 데이터부족 ' + exCover.length +
      (exSplit.length ? ' <span class="pnote">(' + esc(exSplit.slice(0, 8).join(', ')) + (exSplit.length > 8 ? ' …' : '') + ')</span>' : '') + '</td></tr>' +
      '</tbody></table>');
    h.push('<p class="warn">⚠ 진단용 — 유니버스가 «현재» 구성종목이라 생존편향이 있고, 무배당(PR) 눈금에 단일 창입니다. 배포 판단 금지.</p>');
    out.innerHTML = h.join('');
  }

  /* ── ② 포트폴리오 표의 «전략» 열을 원장과 맞춘다 (2026-09-17) ──────────────
     사용자 지적 — «매매내역 넣어도 왼쪽 포트폴리오에서 전략 수량이 안 바뀌어.
     나스닥 MU 6/24 +489 · 9/10 −180 인데 전략 수량 624 로 찍힘».

     맞다. 왼쪽 표는 **파이썬이 구워 둔 정적 HTML** 이고, 그 생성기(build/portfolio_fund.py)는
     전략 수량을 **DB 씨앗(mp.strategy_trade)만** 보고 만든다 — 웹 원장은 암호문이라
     생성기가 못 읽는다. 그래서 웹에 넣은 매매는 ③④ 에만 반영되고 ② 는 게시 시점의 DB
     값에 얼어붙어 있었다. MU 624 = DB 의 6/24 +489 와 8/3 +135 이고, 웹의 9/10 매도는
     그 합에 닿지 못했다. 고치는 자리는 여기다 — 잠금이 풀린 이 앱만이 두 원장을 다 안다.

     【왜 «다시 계산» 이 아니라 «차이만 더하기» 인가】
     처음에 전략(%)·패시브 수량 따위를 **다시 계산**해 덮어썼더니 합계에서 파이썬과
     0.01%p 가 갈렸다 — 화면에 있는 값은 이미 반올림된 것이라 그것을 더하면 파이썬이
     반올림 전에 더한 합과 다르다(실측: 패시브차이 합계 +0.00 → +0.01).
     그래서 산식을 옮겨오지 않는다. **원장이 바뀐 만큼만 움직인다.**
       Δ수량 = 통합원장 순수량 − 씨앗 순수량(=구워진 칸)
       Δ비중 = Δ수량 ÷ spp            (spp = NAV 1%p 를 만드는 주식수, 생성기가 구움)
       전략(%) += Δ비중 · 전략수량 += Δ수량 · 패시브수량 −= Δ수량
       펀드패시브 −= Δ비중 · 패시브차이 −= Δ비중       (지수패시브는 안 움직인다)
     이러면 Δ=0 일 때 **칸을 건드리지 않는 것이 보장된다** — 우연이 아니라 구조로.
     ⚠ 지수비중·펀드비중·보유 수량은 안 건드린다. 사내 보유 원장에서 온 사실이고
       전략 원장과 무관하다.
     ⚠ mergedTrades 가 이미 권위다(migrated 플래그로 씨앗을 버릴지 그쪽이 정한다).
       같은 판단을 여기서 다시 하지 않는다.
     🚨 열은 **이름으로 찾는다.** 이 표의 nth-child 규칙이 열 순서가 바뀔 때마다 어긋난
       적이 세 번 있다(가장 최근 2026-09-16). 번호를 또 손으로 세지 않는다.
     🔑 전제 검사 — «구워진 전략수량 칸 = 씨앗 순수량» 이어야 Δ 의 기준이 성립한다.
       어긋나면 조각이 다른 씨앗으로 구워진 것이므로 **아무것도 고치지 않고** 경고만 띄운다. */
  var COLS = { ipas: '지수패시브', fpas: '펀드패시브', dpas: '패시브차이',
               st: '전략', hq: '보유 수량', pq: '패시브 수량', sq: '전략 수량' };
  function colMap(tb) {
    var ths = tb.querySelectorAll('thead tr:first-child th'), m = {};
    Array.prototype.forEach.call(ths, function (th, i) {
      var t = (th.textContent || '').replace(/\(.*$/, '').trim();
      Object.keys(COLS).forEach(function (k) { if (t === COLS[k]) m[k] = i; });
    });
    return m;
  }
  function cellNum(td) {
    if (!td) return null;
    var v = parseFloat((td.textContent || '').replace(/[,+\s]/g, ''));
    return isFinite(v) ? v : null;
  }
  function tickerOf(tr) {
    var td = tr.querySelector('td.tk');
    if (!td) return null;
    var n0 = td.firstChild;                       // 배지(밖) 앞의 순수 텍스트 노드
    return ((n0 && n0.nodeValue) || td.textContent || '').trim();
  }
  function netByTicker(list, key) {
    var n = {};
    list.forEach(function (t) { n[t.t] = (n[t.t] || 0) + t[key || 'q']; });
    return n;
  }
  /* 구워진 값을 한 번만 떠 둔다. 두 번째 호출부터 이미 고친 칸을 «구워진 값» 으로
     읽으면 Δ 가 누적돼 원장을 고칠 때마다 수가 밀린다. */
  function bake(tr, m) {
    if (tr._pfBake) return tr._pfBake;
    var td = tr.children;
    tr._pfBake = { st: cellNum(td[m.st]) || 0, sq: cellNum(td[m.sq]) || 0,
                   pq: cellNum(td[m.pq]), fpas: cellNum(td[m.fpas]),
                   dpas: cellNum(td[m.dpas]) };
    return tr._pfBake;
  }
  function syncStrategyCols(slug) {
    var tb = document.getElementById('tb-' + slug);
    if (!tb) return;
    var m = colMap(tb);
    if (m.st == null || m.sq == null || m.pq == null || m.fpas == null ||
        m.dpas == null || m.ipas == null) return;      // 표가 바뀌었다 — 손대지 않는다
    var rows = Array.prototype.filter.call(tb.querySelectorAll('tbody tr[data-spp]'),
                                           function (tr) { return tickerOf(tr); });
    var idx = PF.funds[slug].idx, seed = [];
    PF.mp.forEach(function (t) { if (t.idx === idx) seed.push(t); });
    var sn = netByTicker(seed), net = netByTicker(mergedTrades(slug));

    // 🔑 전제 검사 — 구워진 «전략 수량» 이 씨앗 순수량과 같은가.
    var bad = null;
    rows.forEach(function (tr) {
      if (bad) return;
      var b = bake(tr, m), want = sn[tickerOf(tr)] || 0;
      if (Math.abs(b.sq - want) > 0.5) bad = tickerOf(tr) + ' 화면 ' + num(b.sq, 0) + ' ≠ 씨앗 ' + num(want, 0);
    });
    var box = tb.parentNode, warn = box.querySelector('.stsyncwarn');
    if (bad) {
      if (!warn) {
        warn = document.createElement('p');
        warn.className = 'warn stsyncwarn';
        box.insertBefore(warn, box.firstChild);
      }
      warn.textContent = '⚠ 전략 수량의 기준이 안 맞습니다(' + bad +
        ') — 원장을 반영하지 않고 게시 시점 값을 그대로 둡니다.';
      return;
    }
    if (warn) warn.remove();

    /* 🚨 겹침 경보 — 씨앗을 아직 안 버렸는데(migrated=false) 웹 원장에 **같은 매매**가
       또 있으면 수량이 두 배로 센다. 전략 이름이 다르면(«…웹» 처럼 손으로 다시 적은
       경우) 이름으로는 안 갈리므로 «같은 날 · 같은 종목 · 같은 수량» 으로 본다.
       ⚠ 막지는 않는다. ③④ 도 같은 mergedTrades 를 쓰므로 ② 만 다르게 굴리면 화면
         안에서 수가 갈린다 — 한 벌로 두고 **겹쳤다는 사실을 말한다**. 고치는 자리는
         원장이지 이 표가 아니다(«웹 원장으로 가져오기» 를 누르면 씨앗을 버린다).
       ⚠ 열쇠 구분자는 '~' 다. 티커·날짜에 안 나오고, 소스에 제어문자를 박지 않는다
         (2026-09-16 에 편집이 NUL 바이트를 써 넣어 게이트에 걸린 적이 있다). */
    if (!S.doc.migrated) {
      var key = {}, dup = [];
      seed.forEach(function (t) { key[t.dt + '~' + t.t + '~' + t.q] = 1; });
      S.doc.trades.forEach(function (t) {
        if (t.fund === slug && key[t.dt + '~' + t.t + '~' + t.q] && dup.indexOf(t.t) < 0)
          dup.push(t.t);
      });
      var dwarn = box.querySelector('.stdupwarn');
      if (dup.length) {
        if (!dwarn) {
          dwarn = document.createElement('p');
          dwarn.className = 'warn stdupwarn';
          box.insertBefore(dwarn, box.firstChild);
        }
        dwarn.textContent = '⚠ DB 씨앗과 웹 원장에 같은 매매가 겹쳐 있습니다(' +
          dup.slice(0, 6).join(', ') + (dup.length > 6 ? ' 외 ' + (dup.length - 6) + '종' : '') +
          ') — 전략 수량이 두 번 세어집니다. ③ 매매 원장의 «웹 원장으로 가져오기» 를 누르면 ' +
          '씨앗을 버리고 웹 원장 하나로 굴러갑니다.';
      } else if (dwarn) dwarn.remove();
    }

    // 원장이 바뀐 만큼만 각 칸을 민다.
    var dwTot = 0, touched = 0;
    rows.forEach(function (tr) {
      var b = bake(tr, m), td = tr.children,
          spp = parseFloat(tr.getAttribute('data-spp')),
          q = net[tickerOf(tr)] || 0, dq = q - b.sq;
      if (!isFinite(spp) || !spp) return;
      var dw = dq / spp;
      dwTot += dw;
      if (!dq) return;
      touched++;
      var st = b.st + dw;
      td[m.st].textContent = q ? num(st, 2) : '—';
      td[m.st].className = 'tnum' + (q ? ' tk' : '');
      td[m.sq].textContent = q ? num(q, 0) : '—';
      td[m.sq].className = 'tnum' + (q ? ' tk' : '');
      if (b.pq != null) td[m.pq].textContent = num(b.pq - dq, 0);
      if (b.fpas != null) td[m.fpas].textContent = num(b.fpas - dw, 2);
      if (b.dpas != null) {
        var dp = b.dpas - dw;
        td[m.dpas].textContent = (dp > 0 ? '+' : '') + num(dp, 2);
        td[m.dpas].className = 'tnum ' + (dp > 0 ? 'pos' : (dp < 0 ? 'neg' : ''));
      }
    });

    // 합계 줄도 같은 Δ 로 민다(전략 +Δ · 펀드패시브 −Δ · 패시브차이 −Δ).
    var tot = tb.querySelector('thead tr.totrow');
    if (!tot) return;
    if (!tot._pfBake) tot._pfBake = { st: cellNum(tot.children[m.st]),
                                      fpas: cellNum(tot.children[m.fpas]),
                                      dpas: cellNum(tot.children[m.dpas]) };
    var tb0 = tot._pfBake;
    function setTot(i, v, signed) {
      var th = tot.children[i];
      if (!th || v == null) return;
      var b = th.querySelector('b');
      var txt = (signed && v > 0 ? '+' : '') + num(v, 2);
      if (b) b.textContent = txt; else th.textContent = txt;
    }
    if (touched || dwTot) {
      setTot(m.st, tb0.st + dwTot);
      setTot(m.fpas, tb0.fpas - dwTot);
      setTot(m.dpas, tb0.dpas - dwTot, true);
    }
    /* 🚨 2026-09-17 사용자 «2A81 도 그 10종 지수 대비 이런 거 없애줘. 2Z30 이랑 통일해».
       ⚠ 조건 없이 지운다. 종전에는 «원장이 바뀐 경우» 에만 지워서, 원장과 씨앗이 같은
         펀드(2A81, Δ=0)에는 그대로 남았다 — 같은 표인데 두 펀드가 다른 것을 말했다.
         생성기에서도 뺐지만(다음 게시부터) 이미 게시된 조각에도 걸려야 한다. */
    var stc = tot.children[m.st];
    if (stc) {
      var d1 = stc.querySelector('.totd'), d2 = stc.querySelector('.totb');
      if (d1) d1.remove();
      if (d2) d2.remove();
    }
  }

  /* ── 전략 성과 리포트(인쇄 → PDF) (2026-09-17) ────────────────────────────
     사용자 «둘 다 전략 성과 PDF로 내용 깔끔하게 뽑는 버튼도 만들어줘. 내용에 전략 비중도
     포함되어야 함(현재 S&P 0.43%, 나스닥 0.54%)».

     🚨 PDF 라이브러리를 끌어오지 않는다. 이 페이지는 사내 PC 에서 열리고, 외부 CDN 을
       새로 부르는 것은 이 저장소가 지켜 온 «로컬에서 임의 외부 호출 최소화» 와 어긋난다.
       브라우저의 인쇄 → «PDF 로 저장» 이면 의존 없이 같은 결과가 나온다.
     🔑 전략 비중은 **② 표의 합계 칸에서 읽는다.** 다시 계산하지 않는다 — 그 칸은 이미
       웹 원장을 반영해 밀어 둔 값이고, 리포트가 화면과 한 글자라도 다르면 둘 중 어느
       것을 믿어야 할지 알 수 없게 된다. 종목별 비중도 같은 표의 spp 로 만든다.
     ⚠ 성과 수치는 renderPerf 와 **같은 calcPerf** 를 부른다(엔진 두 벌 금지).
     ⚠ 인쇄가 끝나면 리포트 DOM 을 지운다. 남겨 두면 다음 렌더에서 두 벌이 된다. */
  function sppMap(slug) {
    var tb = document.getElementById('tb-' + slug), out = {};
    if (!tb) return out;
    Array.prototype.forEach.call(tb.querySelectorAll('tbody tr[data-spp]'), function (tr) {
      var t = tickerOf(tr), v = parseFloat(tr.getAttribute('data-spp'));
      if (t && isFinite(v) && v) out[t] = v;
    });
    return out;
  }
  function stratTotalW(slug) {
    var tb = document.getElementById('tb-' + slug);
    if (!tb) return null;
    var m = colMap(tb), tot = tb.querySelector('thead tr.totrow');
    if (!tot || m.st == null) return null;
    return cellNum(tot.children[m.st]);
  }
  function fmtLocal(d) {
    function z(n) { return (n < 10 ? '0' : '') + n; }
    return d.getFullYear() + '-' + z(d.getMonth() + 1) + '-' + z(d.getDate()) +
           ' ' + z(d.getHours()) + ':' + z(d.getMinutes());
  }
  function printReport(slug) {
    var F = PF.funds[slug], trs = mergedTrades(slug);
    if (!trs.length) { alert('매매가 없어 낼 리포트가 없습니다.'); return; }
    var asofI = dLe(F.asof_us), cp = calcPerf(slug, trs, asofI), perf = cp.byS;
    var spp = sppMap(slug), wTot = stratTotalW(slug);
    var h = [];
    h.push('<div class="prh"><div class="prt">전략 성과</div>' +
      '<div class="prs">' + esc(F.label) + ' <span class="tk">' + esc(F.fund) + '</span></div></div>');
    h.push('<table class="prmeta"><tbody><tr>' +
      '<td>기준일(미국 종가)</td><td class="tnum">' + esc(F.asof_us) + '</td>' +
      '<td>NAV</td><td class="tnum">' + num(F.nav / 1e8, 1) + '억원</td>' +
      '<td>환율</td><td class="tnum">' + num(F.fx, 2) + '</td>' +
      // ⚠ toISOString 은 UTC 라 한국에서 날짜가 하루 어긋난다(실측: KST 09-17 08:09 을
      //   «2026-09-16 23:09» 로 찍었다). 리포트에 박히는 시각이라 현지시로 쓴다.
      '<td>출력</td><td class="tnum">' + esc(fmtLocal(new Date())) + '</td>' +
      '</tr></tbody></table>');
    // 요약 — 전략 비중이 첫 줄이다(사용자 요구).
    var totExc = 0, totPnl = 0, totInv = 0, nS = 0;
    Object.keys(perf).forEach(function (k) {
      var L = perf[k].last;
      if (!L) return;
      nS++; totExc += L.pnl - L.bm; totPnl += L.pnl; totInv += L.inv;
    });
    h.push('<div class="prcards">' +
      // ⚠ 라벨을 짧게 — 세로 A4(인쇄 폭 188mm)에서 여섯 칸이 한 줄에 들어와야 한다.
      //   길면 줄바꿈이 생겨 카드 높이가 배가 되고, 그만큼 한 장에서 밀려난다.
      '<div class="prc"><div class="prk">전략 비중(NAV)</div><div class="prv">' +
        (wTot == null ? '—' : num(wTot, 2) + '%') + '</div></div>' +
      '<div class="prc"><div class="prk">전략 수</div><div class="prv">' + nS + '</div></div>' +
      '<div class="prc"><div class="prk">매수원금</div><div class="prv">' + num(totInv, 0) + '</div></div>' +
      '<div class="prc"><div class="prk">평가손익</div><div class="prv ' + sgn(totPnl) + '">' +
        num(totPnl, 0) + '</div></div>' +
      '<div class="prc"><div class="prk">초과(vs BM)</div><div class="prv ' + sgn(totExc) + '">' +
        num(totExc, 0) + '</div></div>' +
      '<div class="prc"><div class="prk">NAV 기여</div><div class="prv ' + sgn(totExc) + '">' +
        num(totExc * F.fx / F.nav * 1e4, 1) + ' bp</div></div></div>');
    /* 차트 (2026-09-17 사용자 «전략 차트 나오게 해주고») — 화면과 **같은 svgLines** 를
       쓴다. 그림을 따로 그리면 눈금 규약이 갈려 같은 자료가 다르게 보인다.
       ⚠ 매수원금이 0 인 구간(c[3]=0)은 뺀다 — 나누면 발산한다(화면 쪽과 같은 필터).
       ⚠ 전략이 여럿이면 ① 은 전략별로 겹쳐 그리고, ② 는 전부 합친 한 쌍으로 그린다.
         ② 를 전략별로 또 겹치면 선이 네 개가 되어 인쇄에서 못 읽는다. */
    /* 🚨 색을 테마 변수(var(--accent) 등)에 맡기지 않는다. 인쇄는 흰 종이 위이고,
       변수는 화면 테마를 따라 연할 수 있다(다크에서 고른 색이 흰 바탕에서 안 보인다).
       리포트에서만 쓰는 고정 팔레트를 준다 — 명도를 낮춰 흑백 출력에서도 갈린다. */
    var PRC = ['#1a4e8a', '#b5651d', '#2e7d32', '#6a1b9a', '#00707a'];
    var exSeries = [];
    Object.keys(perf).sort().forEach(function (sname) {
      var pts = perf[sname].curve
        .filter(function (c) { return c[3]; })
        .map(function (c) { return [PF.dates[c[0]], (c[1] - c[2]) / c[3] * 100]; });
      if (pts.length) exSeries.push([sname, pts, PRC[exSeries.length % PRC.length]]);
    });
    // ⚠ «전략 합산 vs 지수» 차트는 뺐다(2026-09-17 사용자 «이 차트는 필요 없어»).
    //   초과수익 그림의 0선이 이미 지수라, 같은 이야기를 두 번 하고 있었다.
    if (exSeries.length)
      h.push('<h4>전략별 누적 초과수익 (%, 매수원금 대비 · 0선 = 지수와 같은 성과)</h4>' +
        '<div class="prch">' +
        svgLines(exSeries, exSeries.map(function (x) { return x[0].slice(0, 16); }),
                 760, 168, '#b02a37') + '</div>');

    // 전략별
    h.push('<h4>전략별</h4><table class="prtbl"><thead><tr><th>전략</th>' +
      '<th class="tnum">비중(NAV)</th><th class="tnum">종목</th><th class="tnum">매수원금</th>' +
      '<th class="tnum">평가손익</th><th class="tnum">수익률</th><th class="tnum">BM</th>' +
      '<th class="tnum">초과</th><th class="tnum">기여(bp)</th></tr></thead><tbody>');
    Object.keys(perf).sort().forEach(function (sname) {
      var P = perf[sname], L = P.last;
      if (!L) return;
      var wS = 0, known = false;
      P.rows.forEach(function (r) { if (spp[r.t]) { wS += r.q / spp[r.t]; known = true; } });
      h.push('<tr><td>' + esc(sname) + '</td>' +
        '<td class="tnum">' + (known ? num(wS, 2) : '—') + '</td>' +
        '<td class="tnum">' + P.rows.length + '</td>' +
        '<td class="tnum">' + num(L.inv, 0) + '</td>' +
        '<td class="tnum ' + sgn(L.pnl) + '">' + num(L.pnl, 0) + '</td>' +
        '<td class="tnum ' + sgn(L.ret) + '">' + (L.ret == null ? '—' : pct(L.ret, 2, true)) + '</td>' +
        '<td class="tnum">' + (L.bmRet == null ? '—' : pct(L.bmRet, 2, true)) + '</td>' +
        '<td class="tnum ' + sgn(L.pnl - L.bm) + '">' + num(L.pnl - L.bm, 0) + '</td>' +
        '<td class="tnum ' + sgn(L.pnl - L.bm) + '">' + num((L.pnl - L.bm) * F.fx / F.nav * 1e4, 1) + '</td></tr>');
    });
    h.push('<tr class="prtot"><td>합계</td><td class="tnum">' + (wTot == null ? '—' : num(wTot, 2)) +
      '</td><td class="tnum"></td><td class="tnum">' + num(totInv, 0) + '</td>' +
      '<td class="tnum ' + sgn(totPnl) + '">' + num(totPnl, 0) + '</td><td class="tnum"></td>' +
      '<td class="tnum"></td><td class="tnum ' + sgn(totExc) + '">' + num(totExc, 0) + '</td>' +
      '<td class="tnum ' + sgn(totExc) + '">' + num(totExc * F.fx / F.nav * 1e4, 1) + '</td></tr>');
    h.push('</tbody></table>');
    /* 종목별 — 전략마다 표를 따로 내지 않는다(2026-09-17 «가급적 한 페이지에»).
       전략이 둘이면 머리글 줄과 열 이름 줄이 두 벌씩 붙어 그것만으로 20mm 가까이
       먹었다. 한 장으로 합치고 «전략» 열을 둔다 — 전략이 하나인 펀드에서는 열이
       하나 늘 뿐이고, 둘 이상이면 자리를 아끼면서 비교도 쉬워진다.
       ⚠ 전략 이름은 첫 줄에만 적는다. 같은 값을 세로로 반복하면 눈이 그 열을 읽게 된다. */
    var anyRow = Object.keys(perf).some(function (k) { return perf[k].rows.length; });
    if (anyRow) {
      h.push('<h4>종목별</h4><table class="prtbl"><thead><tr><th>전략</th>' +
        '<th>티커</th><th class="tnum">순수량</th><th class="tnum">비중(NAV)</th>' +
        '<th class="tnum">현재가</th><th class="tnum">매수원금</th><th class="tnum">평가손익</th>' +
        '<th class="tnum">수익률</th><th class="tnum">초과</th></tr></thead><tbody>');
      Object.keys(perf).sort().forEach(function (sname) {
        perf[sname].rows.forEach(function (r, i) {
          h.push('<tr' + (i ? '' : ' class="prgrp"') + '><td>' +
            (i ? '' : esc(sname)) + '</td>' +
            '<td class="tk">' + esc(r.t) + (r.warn ? ' ⚠' : '') + '</td>' +
            '<td class="tnum">' + num(r.q, 0) + '</td>' +
            '<td class="tnum">' + (spp[r.t] ? num(r.q / spp[r.t], 2) : '—') + '</td>' +
            '<td class="tnum">' + num(r.px, 2) + '</td>' +
            '<td class="tnum">' + num(r.inv, 0) + '</td>' +
            '<td class="tnum ' + sgn(r.pnl) + '">' + num(r.pnl, 0) + '</td>' +
            '<td class="tnum ' + sgn(r.ret) + '">' + (r.ret == null ? '—' : pct(r.ret, 2, true)) + '</td>' +
            '<td class="tnum ' + sgn(r.exc) + '">' + num(r.exc, 0) + '</td></tr>');
        });
      });
      h.push('</tbody></table>');
    }
    /* 🚨 2026-09-17 사용자 «정의·한계 이 부분은 빼줘» — 통째로 뺀다.
       ⚠ 다만 **그 리포트에서 실제로 일어난 일**은 남긴다. 둘 다 평소에는 안 나오고,
         나올 때는 숫자 자체의 뜻이 달라지는 것들이다:
           · 성과에서 뺀 매매가 있으면 표의 합이 원장 전체가 아니다.
           · ⚠ 표시가 있는데 범례가 없으면 «이 기호가 뭐지» 로 남는다.
         «늘 같은 문구» 만 없애고 «이번에만 참인 사실» 은 남기는 것이 지운 취지에 맞다. */
    var sk = cp.skipped, ex = [];
    if (sk.old) ex.push('가격 패널 이전 ' + sk.old + '건');
    if (sk.future) ex.push('기준일 이후 ' + sk.future + '건');
    if (sk.nopx) ex.push('가격 없는 종목 ' + sk.nopx + '건');
    var anyWarn = Object.keys(perf).some(function (k) {
      return perf[k].rows.some(function (r) { return r.warn; });
    });
    if (ex.length || anyWarn)
      h.push('<div class="prnote">' +
        (ex.length ? '· 성과 계산에서 뺀 매매: ' + esc(ex.join(' · ')) + '<br>' : '') +
        (anyWarn ? '· ⚠ = 보유 중 하루 ±' + num(PF.guard * 100, 0) +
                   '% 초과 변동(분할 의심)' : '') + '</div>');

    var box = document.getElementById('pfprint');
    if (!box) {
      box = document.createElement('div');
      box.id = 'pfprint';
      document.body.appendChild(box);
    }
    box.innerHTML = h.join('');
    document.body.classList.add('pf-printing');
    var done = function () {
      document.body.classList.remove('pf-printing');
      if (box && box.parentNode) box.parentNode.removeChild(box);
      window.removeEventListener('afterprint', done);
    };
    window.addEventListener('afterprint', done);
    // 인쇄 대화상자를 안 띄우고 닫는 브라우저 대비 — afterprint 가 안 오면 손으로 치운다.
    setTimeout(function () { if (document.body.classList.contains('pf-printing')) done(); }, 60000);
    window.print();
  }

  // ── 조립 ────────────────────────────────────────────────────────────────
  function renderFund(slug) { renderLedger(slug); renderPerf(slug); syncStrategyCols(slug); }
  function renderAll() {
    renderSync();
    Object.keys(PF.funds).forEach(renderFund);
    renderBT();
    // 앱이 그린 차트에도 조각 스크립트의 호버 배선을 건다 — 배선이 한 벌이어야
    // 두 곳의 툴팁이 같은 규약으로 움직인다(이미 걸린 것은 dataset.wired 로 건너뛴다).
    try { if (window.PFCHARTS) window.PFCHARTS(document); } catch (e) {}
  }

  /* ── 목표 비중 → 필요 수량 (2026-09-16) ──────────────────────────────────
     사용자 지시 — «내가 타겟 비중 넣으면 몇 주 팔아야 하는지도 바로 볼 수 있게».

     행에 실린 두 수만 쓴다(생성기가 구워 둔다):
       data-spp  NAV 1%p 를 만드는 주식수 = NAV ÷ (종가 × 보유일환율) ÷ 100
       data-wf   지금 펀드비중(%)
     필요 수량 = (목표 − 현재) × spp. 음수면 매도다.

     ⚠ 여기서 NAV·환율을 다시 나누지 않는다. 그러면 같은 계산이 파이썬과 js 두 벌이
       되고, 언젠가 한쪽만 고쳐진다 — 이 저장소가 되풀이 밟는 종류다. 곱하기만 한다.
     ⚠ 환율은 **보유일** 것이다(생성기 fx_hold). 최신 환율을 섞으면 «목표 = 현재» 를
       넣어도 0 이 안 나온다 — 화면의 비중이 그 눈금으로 만들어졌기 때문이다.
     ⚠ 위임으로 건다. 이 표는 암호문 안에 있어 잠금이 풀린 뒤에야 DOM 에 들어온다 —
       로드 시점에 칸을 찾아 거는 배선은 아무것도 못 잡는다.
     ⚠ 값은 어디에도 저장하지 않는다. 계산기이지 원장이 아니다 — 새로고침하면 빈다. */
  function fmtQty(n) {
    return (n > 0 ? '+' : '') + n.toLocaleString('en-US');
  }
  function targetRow(tr) {
    var inp = tr.querySelector('input.tgtw'), out = tr.querySelector('td.tgtq');
    if (!inp || !out) return 0;
    var spp = parseFloat(tr.getAttribute('data-spp')),
        wf = parseFloat(tr.getAttribute('data-wf')),
        v = inp.value.trim();
    out.className = 'tnum tgtq';
    if (v === '' || !isFinite(spp) || !isFinite(wf)) { out.textContent = ''; return 0; }
    var tgt = parseFloat(v);
    if (!isFinite(tgt)) { out.textContent = ''; return 0; }
    var dq = Math.round((tgt - wf) * spp);
    out.textContent = fmtQty(dq);
    out.className = 'tnum tgtq ' + (dq > 0 ? 'pos' : (dq < 0 ? 'neg' : ''));
    out.title = '목표 ' + tgt.toFixed(2) + '% − 현재 ' + wf.toFixed(2) + '% = '
              + (tgt - wf).toFixed(2) + '%p → ' + fmtQty(dq) + '주'
              + (dq < 0 ? ' (매도)' : (dq > 0 ? ' (매수)' : ''));
    return 1;
  }
  function targetSum(tbody) {
    // 합계 칸은 «몇 건을 건드렸나» 를 센다. 수량을 더하지는 않는다 — 단위가 섞인
    // 숫자라 더해도 뜻이 없다(이 표의 다른 수량 열에 합계가 없는 것과 같은 이유다).
    var tb = tbody.closest ? tbody.closest('table') : null;
    if (!tb) return;
    var cell = tb.querySelector('th.tgtsum');
    if (!cell) return;
    var n = 0, buy = 0, sell = 0;
    Array.prototype.forEach.call(tb.querySelectorAll('tbody tr[data-spp]'), function (tr) {
      var out = tr.querySelector('td.tgtq');
      if (!out || !out.textContent) return;
      n++;
      var q = parseFloat(out.textContent.replace(/[+,]/g, ''));
      if (q > 0) buy++; else if (q < 0) sell++;
    });
    cell.textContent = n ? (n + '건') : '';
    cell.title = n ? ('목표를 넣은 ' + n + '종 — 매수 ' + buy + ' · 매도 ' + sell
                      + '. 수량은 종목마다 단가가 달라 더하지 않는다.') : '';
  }
  document.addEventListener('input', function (e) {
    var inp = e.target;
    if (!inp || !inp.classList || !inp.classList.contains('tgtw')) return;
    var tr = inp.closest('tr');
    if (!tr) return;
    targetRow(tr);
    targetSum(tr.parentNode);
  });

  window.addEventListener('beforeunload', function (e) {
    if (S.dirty) { e.preventDefault(); e.returnValue = ''; }
  });

  async function init() {
    if (S.ready) return;
    if (!window.PF || !window.__pfKM) return;      // 아직 잠금 해제 전 — 게이트가 다시 부른다
    S.ready = true;
    S.km = window.__pfKM;
    try { boot(); } catch (e) {
      var b = el('pfsync');
      if (b) b.innerHTML = '<span class="perr">데이터 블롭 해석 실패: ' + esc(e.message) + '</span>';
      return;
    }
    renderAll();                                    // 웹 원장 도착 전에도 DB 원장으로 먼저 그린다
    await loadLedger();
    renderAll();
  }

  // refresh — 원장을 바꾸지 않고 화면만 다시 그린다(콘솔 점검·회귀 검증용).
  window.PFAPP = { init: init, refresh: function () { if (S.ready) renderAll(); } };
  init();                                           // 앱이 게이트보다 늦게 로드된 경우
})();
