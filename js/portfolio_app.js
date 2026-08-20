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
    doc: { v: 1, strategies: {}, trades: [] },
    dirty: false,
    ready: false,
    loadErr: null
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
    PF.mp.forEach(function (t) {
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
  function svgLines(series, labels, w, h) {
    w = w || 760; h = h || 210;
    var pad = 40;
    var ys = [];
    series.forEach(function (s) { s[1].forEach(function (p) { ys.push(p[1]); }); });
    if (!ys.length) return '';
    var lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys);
    if (hi - lo < 1e-9) hi = lo + 1;
    var n = Math.max.apply(null, series.map(function (s) { return s[1].length; }));
    var colors = ['var(--accent)', 'var(--champ)', 'var(--rp)', 'var(--hot)', 'var(--deploy)'];
    function X(i) { return pad + (w - pad - 10) * (i / Math.max(1, n - 1)); }
    function Y(v) { return (h - 24) - (h - 44) * ((v - lo) / (hi - lo)); }
    var out = ['<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" style="width:100%;height:auto">'];
    if (lo < 0 && 0 < hi)
      out.push('<line x1="' + pad + '" y1="' + Y(0).toFixed(1) + '" x2="' + (w - 10) + '" y2="' + Y(0).toFixed(1) + '" stroke="var(--line)" stroke-dasharray="3 3"/>');
    series.forEach(function (s, k) {
      var d = s[1].map(function (p, i) { return (i ? 'L' : 'M') + X(i).toFixed(1) + ',' + Y(p[1]).toFixed(1); }).join(' ');
      out.push('<path d="' + d + '" fill="none" stroke="' + colors[k % colors.length] + '" stroke-width="1.8"/>');
    });
    out.push('<text x="2" y="14" font-size="10" fill="var(--muted)" font-family="var(--mono)">' + hi.toFixed(1) + '</text>');
    out.push('<text x="2" y="' + (h - 24) + '" font-size="10" fill="var(--muted)" font-family="var(--mono)">' + lo.toFixed(1) + '</text>');
    var x0 = series[0][1].length ? series[0][1][0][0] : '', x1 = series[0][1].length ? series[0][1][series[0][1].length - 1][0] : '';
    out.push('<text x="' + pad + '" y="' + (h - 10) + '" font-size="10" fill="var(--muted)" font-family="var(--mono)">' + esc(x0) + ' → ' + esc(x1) + '</text>');
    if (labels) {
      var lx = pad + 170;
      labels.forEach(function (lb, k) {
        out.push('<text x="' + lx + '" y="' + (h - 10) + '" font-size="11" fill="' + colors[k % colors.length] + '" font-family="var(--mono)">━ ' + esc(lb) + '</text>');
        lx += 11 * lb.length + 44;
      });
    }
    out.push('</svg>');
    return out.join('');
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
    if (!f) { S.base = { sha: null, updated: null }; S.doc = { v: 1, strategies: {}, trades: [], navs: {} }; return; }
    S.base = { sha: f.sha, updated: null };
    var env;
    try { env = JSON.parse(new TextDecoder().decode(b64d(f.content))); }
    catch (e) { S.loadErr = '원장 JSON 파싱 실패 — 파일이 손상됐다. 이력에서 복원하세요.'; renderSync(); return; }
    if (env.empty) { S.doc = { v: 1, strategies: {}, trades: [], navs: {} }; return; }   // 초기 상태 — 빈 원장
    S.base.updated = env.updated || null;
    try {
      var doc = await decDoc(env);
      S.doc = { v: 1, strategies: doc.strategies || {}, trades: doc.trades || [], navs: doc.navs || {} };
    } catch (e) {
      // 페이지 재잠금 암호가 바뀐 경우 — 봉투는 옛 암호다. 화면에서 옛 암호를 따로 받는다.
      S.loadErr = 'PWMISMATCH';
    }
  }
  async function saveLedger(force) {
    var doc = { v: 1, strategies: S.doc.strategies, trades: S.doc.trades, navs: S.doc.navs || {}, saved: new Date().toISOString() };
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

  // ── 렌더: 동기화 바 ─────────────────────────────────────────────────────
  // 🚨 골격(상태줄 #pfrow / 패널 #pfpanel)은 한 번만 만들고, 갱신은 #pfrow 만 다시 쓴다.
  //    처음엔 renderSync 가 통째로 innerHTML 을 갈았는데, 그러면 panel() 이 그린 다이얼로그의
  //    버튼 리스너가 재렌더마다 파괴돼 «충돌 다이얼로그가 통째로 죽는» 결함이 됐다
  //    (2026-08-20 적대감사 확정 — innerHTML 재삽입은 리스너를 복제하지 않는다).
  function renderSync() {
    var box = el('pfsync');
    if (!box) return;
    if (!el('pfrow')) {
      box.innerHTML = '<div id="pfrow"></div><div class="syncpanel" id="pfpanel" hidden></div>';
      el('pfrow').addEventListener('click', function (e) {
        var b = e.target.closest('button');
        if (!b) return;
        if (b.id === 'pfsave') onSave();
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
    else if (S.dirty) st = '<span class="dot warn"></span>변경 미저장';
    else st = '<span class="dot ok"></span>동기화됨';
    h.push('<div class="syncrow">');
    h.push('<span class="syncst">' + st + '</span>');
    h.push('<span class="syncmeta">웹 원장 전략 ' + nS + ' · 매매 ' + nW + '건' +
      (S.base && S.base.updated ? ' · 저장 ' + esc(String(S.base.updated).slice(0, 16).replace('T', ' ')) + 'Z' : '') + '</span>');
    h.push('<span class="syncbtns">');
    h.push('<button class="sb primary" id="pfsave"' + (S.dirty ? '' : ' disabled') + '>GitHub에 저장</button>');
    h.push('<button class="sb" id="pfhist">이력·되돌리기</button>');
    h.push('<button class="sb" id="pfcfg">' + (token() ? '⚙ 토큰' : '⚙ 토큰 등록 필요') + '</button>');
    h.push('</span></div>');
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
    var p = panel(
      '<b>원장 암호 확인</b><p class="pnote">저장된 웹 원장이 현재 페이지 암호로 안 풀립니다 — ' +
      '페이지를 다른 암호로 재잠금한 경우입니다. 원장을 저장할 때 쓴 암호를 입력하면 열고, ' +
      '다음 저장부터는 현재 페이지 암호로 다시 잠급니다.</p>' +
      '<input type="password" id="pfoldpw" placeholder="원장 저장 당시 암호">' +
      '<button class="sb primary" id="pfoldgo">열기</button> <span id="pfolderr" class="perr"></span>');
    el('pfoldgo').addEventListener('click', async function () {
      try {
        var pw = el('pfoldpw').value;
        var km = await crypto.subtle.importKey('raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveKey']);
        var f = await ghGetFile();
        var env = JSON.parse(new TextDecoder().decode(b64d(f.content)));
        var doc = await decDoc(env, km);
        S.doc = { v: 1, strategies: doc.strategies || {}, trades: doc.trades || [], navs: doc.navs || {} };
        S.base = { sha: f.sha, updated: env.updated || null };
        S.loadErr = null;
        S.dirty = true;                             // 현재 암호로 재저장 유도
        renderAll();
      } catch (e) { el('pfolderr').textContent = '그 암호로도 안 풀립니다.'; }
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
      renderAll();
      panel('저장됨 — 커밋 <span class="tk">' + esc(sha.slice(0, 7)) + '</span>. git 이력에 남아 언제든 되돌릴 수 있습니다.');
    } catch (e) {
      renderAll();
      if (e.conflict) {
        // renderAll 뒤에 그린다 — 골격 분리로 패널은 재렌더에도 살아남지만, 순서까지 지켜 확실히.
        panel('<b>충돌</b> — 다른 기기에서 먼저 저장했습니다.<br>' +
          '<button class="sb" id="pfreload">원격을 불러오기(내 미저장 변경 폐기)</button> ' +
          '<button class="sb warn" id="pfforce">내 것으로 덮어쓰기(이전 버전은 이력에 남음)</button>');
        el('pfreload').addEventListener('click', async function () { await loadLedger(); S.dirty = false; renderAll(); panel('원격 상태를 불러왔습니다.'); });
        el('pfforce').addEventListener('click', async function () {
          try { var s2 = await saveLedger(true); renderAll(); panel('덮어씀 — 커밋 ' + esc(s2.slice(0, 7))); }
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

    if (trs.length) {
      h.push('<div class="tblwrap"><table class="big"><thead><tr><th>일자</th><th>전략</th><th>티커</th>' +
        '<th class="tnum">수량</th><th class="tnum">체결가</th><th class="tnum">금액(USD)</th>' +
        '<th class="tnum">현재가</th><th class="tnum">평가손익</th><th>출처</th><th></th></tr></thead><tbody>');
      trs.forEach(function (t) {
        var p = pxLeI(t.t, asofI);
        var pnl = p != null ? t.q * (p - t.p) : null;
        h.push('<tr><td>' + esc(t.dt) + '</td><td>' + esc(t.s) + '</td><td class="tk">' + esc(t.t) + '</td>' +
          '<td class="tnum">' + num(t.q, 0) + '</td><td class="tnum">' + num(t.p) + '</td>' +
          '<td class="tnum">' + num(t.q * t.p, 0) + '</td>' +
          '<td class="tnum">' + (p != null ? num(p) : '—') + '</td>' +
          '<td class="tnum ' + sgn(pnl) + '">' + (pnl != null ? num(pnl, 0) : '—') + '</td>' +
          '<td>' + (t.src === 'db' ? '<span class="badge db">DB</span>' : '<span class="badge web">웹</span>') + '</td>' +
          '<td class="rowops">' + (t.src === 'web'
            ? '<button class="sb" data-edit="' + esc(t.id) + '">✎</button><button class="sb warn" data-del="' + esc(t.id) + '">✕</button>'
            : '') + '</td></tr>');
        if (t.note) h.push('<tr class="noterow"><td></td><td colspan="9">↳ ' + esc(t.note) + '</td></tr>');
      });
      h.push('</tbody></table></div>');
    } else h.push('<p>매매가 없다 — 아래에서 첫 매매를 입력하세요.</p>');

    // 입력 폼
    h.push('<form class="tradeform" id="tf-' + slug + '" autocomplete="off">');
    h.push('<b>+ 매매 입력</b> ');
    h.push('<input type="date" name="dt" value="' + esc(today()) + '" required>');
    h.push('<input name="s" list="dl-s-' + slug + '" placeholder="전략" required>');
    h.push('<datalist id="dl-s-' + slug + '">' + strategyNames(slug).map(function (n) { return '<option value="' + esc(n) + '">'; }).join('') + '</datalist>');
    h.push('<input name="t" list="dl-t-' + slug + '" placeholder="티커 (예: NVDA US)" required>');
    h.push('<datalist id="dl-t-' + slug + '">' + Object.keys(F.cons).sort().map(function (t) {
      return '<option value="' + esc(t) + '">' + esc(F.cons[t][1]) + '</option>';
    }).join('') + '</datalist>');
    h.push('<input name="q" type="number" step="any" placeholder="수량(매도는 −)" required>');
    h.push('<input name="p" type="number" step="any" placeholder="가격(비우면 그날 종가)">');
    h.push('<input name="note" placeholder="메모(선택)">');
    h.push('<input type="hidden" name="editid">');
    h.push('<button class="sb primary" type="submit">추가</button>');
    h.push('<span class="perr" id="tferr-' + slug + '"></span>');
    h.push('</form>');

    // 전략 메모/상태
    var names = strategyNames(slug);
    if (names.length) {
      h.push('<details class="smeta"><summary>전략 메모·상태 (' + names.length + ')</summary><table class="mini"><tbody>');
      names.forEach(function (n) {
        var m = S.doc.strategies[n] || {};
        h.push('<tr><td class="tk">' + esc(n) + '</td>' +
          '<td><input class="smemo" data-s="' + esc(n) + '" value="' + esc(m.memo || '') + '" placeholder="메모"></td>' +
          '<td><select class="sstat" data-s="' + esc(n) + '">' +
          '<option value="active"' + (m.status !== 'closed' ? ' selected' : '') + '>운용중</option>' +
          '<option value="closed"' + (m.status === 'closed' ? ' selected' : '') + '>종료</option>' +
          '</select></td></tr>');
      });
      h.push('</tbody></table></details>');
    }
    box.innerHTML = h.join('');

    // 배선
    var form = el('tf-' + slug);
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var fd = new FormData(form);
      var errEl = el('tferr-' + slug);
      errEl.textContent = '';
      var t = String(fd.get('t')).trim().toUpperCase();
      var dt0 = String(fd.get('dt'));
      var q = parseFloat(fd.get('q'));
      var p = fd.get('p') ? parseFloat(fd.get('p')) : null;
      if (!q) { errEl.textContent = '수량이 0 입니다.'; return; }
      if (p == null) {
        var i = dLe(dt0);
        p = i >= 0 ? pxAt(t, i) : null;
        if (p == null) { errEl.textContent = '그 날짜의 종가가 패널에 없습니다 — 가격을 직접 넣으세요.'; return; }
        p = Math.round(p * 100) / 100;
      }
      if (!(p > 0)) { errEl.textContent = '가격이 유효하지 않습니다.'; return; }
      if (TKI[t] == null) errEl.textContent = '⚠ 패널에 없는 티커 — 등록은 되지만 평가·성과에 가격이 없습니다.';
      var editId = String(fd.get('editid') || '');
      if (editId) {
        var tr = S.doc.trades.find(function (x) { return x.id === editId; });
        if (tr) { tr.dt = dt0; tr.s = String(fd.get('s')).trim(); tr.t = t; tr.q = q; tr.p = p; tr.note = String(fd.get('note') || '').trim(); }
      } else {
        S.doc.trades.push({ id: uid(), fund: slug, dt: dt0, s: String(fd.get('s')).trim(),
                            t: t, q: q, p: p, note: String(fd.get('note') || '').trim() });
      }
      S.dirty = true;
      renderFund(slug); renderSync();
    });
    box.querySelectorAll('button[data-del]').forEach(function (b) {
      b.addEventListener('click', function () {
        if (!confirm('이 매매를 지울까요? (저장 전이면 흔적 없음, 저장 후엔 이력에 남음)')) return;
        S.doc.trades = S.doc.trades.filter(function (x) { return x.id !== b.dataset.del; });
        S.dirty = true;
        renderFund(slug); renderSync();
      });
    });
    box.querySelectorAll('button[data-edit]').forEach(function (b) {
      b.addEventListener('click', function () {
        var tr = S.doc.trades.find(function (x) { return x.id === b.dataset.edit; });
        if (!tr) return;
        form.dt.value = tr.dt; form.s.value = tr.s; form.t.value = tr.t;
        form.q.value = tr.q; form.p.value = tr.p; form.note.value = tr.note || '';
        form.editid.value = tr.id;
        form.querySelector('button[type=submit]').textContent = '수정 저장';
        form.scrollIntoView({ block: 'center' });
      });
    });
    box.querySelectorAll('.smemo').forEach(function (inp) {
      inp.addEventListener('change', function () {
        var m = S.doc.strategies[inp.dataset.s] = S.doc.strategies[inp.dataset.s] || {};
        m.memo = inp.value.trim();
        S.dirty = true; renderSync();
      });
    });
    box.querySelectorAll('.sstat').forEach(function (sel) {
      sel.addEventListener('change', function () {
        var m = S.doc.strategies[sel.dataset.s] = S.doc.strategies[sel.dataset.s] || {};
        m.status = sel.value;
        S.dirty = true; renderSync();
      });
    });
  }

  // ── 렌더: 성과(④) ───────────────────────────────────────────────────────
  function renderPerf(slug) {
    var box = el('perf-' + slug);
    if (!box) return;
    var F = PF.funds[slug];
    var trs = mergedTrades(slug);
    var h = [];
    if (!trs.length) { box.innerHTML = '<p>매매가 없어 성과를 계산할 것이 없다.</p>'; return; }
    var asofI = dLe(F.asof_us);
    var cp = calcPerf(slug, trs, asofI);
    var perf = cp.byS, sk = cp.skipped;

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
      h.push('<tr' + (closed ? ' class="closedrow"' : '') + '><td>' + esc(sname) +
        (perf[sname].warn.length ? ' ⚠' + esc(perf[sname].warn.join(',')) : '') +
        (closed ? ' <span class="badge">종료</span>' : '') + '</td>' +
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
      h.push('<div class="chart"><div class="chtitle">전략별 누적 초과수익(%, 매수원금 대비)</div>' +
        svgLines(series, series.map(function (s) { return s[0].slice(0, 16); })) + '</div>');

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
    box.innerHTML = h.join('');
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
      svgLines([['전략', curve], ['지수', bmCurve]], ['전략', '지수(PR)']) + '</div>');
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

  // ── 최신 기준가 반영 (2026-08-20 사용자 지시) ────────────────────────────
  // «내가 최신 NAV랑 환율을 넣고 업데이트 버튼을 클릭하면 그때 D-1 성과까지 보여주면 돼.»
  // 계산은 빌더(portfolio_fund.render_fund)와 같은 규약이다:
  //   펀드 점  = 기준가 ÷ bp0 × 100
  //   지수 점  = (지수 last_lt(D) × 입력 환율) ÷ ib0 × 100   ← T-1 짝맞춤 그대로
  // 지수 레벨은 동봉 PF.lvl(최신 미국 종가까지)에서 찾으므로 새 자료가 필요 없다.
  // 입력은 S.doc.navs[slug] 에 실려 «GitHub에 저장»으로 봉투에 같이 들어간다.
  function lvlLtDate(slug, d) {
    // PF.dates(미국 거래일 축)에서 d **미만**의 마지막 날 — 빌더의 last_lt 와 같은 뜻.
    var i = -1;
    for (var k = 0; k < PF.dates.length; k++) { if (PF.dates[k] < d) i = k; else break; }
    if (i < 0) return null;
    var v = lvlLeI(PF.lvl[slug], i);
    return v == null ? null : { d: PF.dates[i], v: v };
  }
  function navRows(slug) {
    var meta = PF.funds[slug], y = meta && meta.ytd;
    if (!y) return [];
    return ((S.doc.navs || {})[slug] || [])
      .filter(function (r) { return r && r.d && r.d > y.nav_d && r.bp > 0 && r.fx > 0; })
      .sort(function (a, b) { return a.d < b.d ? -1 : 1; });
  }
  function redrawYtd(slug) {
    var meta = PF.funds[slug], y = meta && meta.ytd;
    var box = el('ytd-' + slug);
    if (!y || !box) return;
    var rows = navRows(slug);
    var f = y.f.slice(), b = y.b.slice(), bad = null;
    rows.forEach(function (r) {
      var lv = lvlLtDate(slug, r.d);
      if (!lv) { bad = r.d + ' 이전 지수 종가가 동봉 자료에 없습니다'; return; }
      f.push([r.d, r.bp / y.bp0 * 100]);
      b.push([r.d, (lv.v * r.fx) / y.ib0 * 100]);
    });
    box.innerHTML = svgLines([['펀드', f], ['지수', b]], y.chart_labels);
    // 카드 0(NAV)·1(연초후)·2(초과) — 빌더가 심은 id 자리만 갈아 끼운다
    var ytdF = f.length ? f[f.length - 1][1] / 100 - 1 : null;
    var ytdB = b.length ? b[b.length - 1][1] / 100 - 1 : null;
    var last = rows.length ? rows[rows.length - 1] : null;
    function setCard(ci, v, sub, sign) {
      var cv = el('cv-' + slug + '-' + ci), cs = el('cs-' + slug + '-' + ci);
      if (cv) { cv.textContent = v; cv.className = 'cv ' + sgn(sign); }
      if (cs && sub != null) cs.textContent = sub;
    }
    if (last && last.nav > 0) setCard(0, num(last.nav, 0) + '억원', '기준가 ' + num(last.bp), 0);
    else if (!last) setCard(0, num(meta.nav / 1e8, 0) + '억원', '기준가 ' + num(meta.base), 0);
    setCard(1, pct(ytdF, 2, true), '지수(원화환산) ' + pct(ytdB, 2, true), ytdF || 0);
    var ex = (ytdF == null || ytdB == null) ? null : ytdF - ytdB;
    setCard(2, pct(ex, 2, true), null, ex || 0);
    return bad;
  }
  function renderNavUpd(slug) {
    var wrap = el('navupd-' + slug);
    if (!wrap) return;                              // 조각이 아직 옛 판이면 폼 자체가 없다
    redrawYtd(slug);                                // 저장돼 있던 입력분을 곡선에 반영
    if (wrap.dataset.wired) return;                 // 리스너는 한 번만 — 조각은 재렌더되지 않는다
    wrap.dataset.wired = '1';
    var st = el('nu-st-' + slug);
    function say(m, ok) { if (st) { st.textContent = m || ''; st.className = 'nust' + (ok ? ' ok' : ''); } }
    el('nu-go-' + slug).addEventListener('click', function () {
      var y = (PF.funds[slug] || {}).ytd;
      if (!y) { say('이 조각에는 곡선 원자료가 없습니다 — 조각을 다시 생성할 것'); return; }
      var d = (el('nu-d-' + slug).value || '').trim();
      var bp = parseFloat(el('nu-bp-' + slug).value);
      var nav = parseFloat(el('nu-nav-' + slug).value);   // 억원 — 비워도 된다(카드만 못 바꾼다)
      var fx = parseFloat(el('nu-fx-' + slug).value);
      if (!d) { say('기준일을 넣으세요'); return; }
      if (d <= y.nav_d) { say('시트가 이미 ' + y.nav_d + ' 기준입니다 — 그 뒤 날짜만 받습니다'); return; }
      if (!(bp > 0)) { say('기준가를 넣으세요'); return; }
      if (!(fx > 0)) { say('환율을 넣으세요'); return; }
      if (!lvlLtDate(slug, d)) { say('그 기준일과 짝지을 지수 종가가 동봉 자료에 없습니다'); return; }
      S.doc.navs = S.doc.navs || {};
      var arr = (S.doc.navs[slug] || []).filter(function (r) { return r.d !== d; });
      arr.push({ d: d, bp: bp, nav: (nav > 0 ? nav : null), fx: fx });
      S.doc.navs[slug] = arr;
      S.dirty = true; renderSync();
      var bad = redrawYtd(slug);
      say(bad || (d + ' 반영 — 미국 ' + lvlLtDate(slug, d).d + ' 종가와 짝지었습니다. 저장하려면 «GitHub에 저장»'), !bad);
    });
    el('nu-clr-' + slug).addEventListener('click', function () {
      if (!((S.doc.navs || {})[slug] || []).length) { say('지울 입력분이 없습니다'); return; }
      delete S.doc.navs[slug];
      S.dirty = true; renderSync();
      redrawYtd(slug);
      say('입력분을 지웠습니다 — 시트 값으로 되돌림. 저장하려면 «GitHub에 저장»', true);
    });
  }

  // ── 조립 ────────────────────────────────────────────────────────────────
  function renderFund(slug) { renderLedger(slug); renderPerf(slug); renderNavUpd(slug); }
  function renderAll() {
    renderSync();
    Object.keys(PF.funds).forEach(renderFund);
    renderBT();
  }

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

  window.PFAPP = { init: init };
  init();                                           // 앱이 게이트보다 늦게 로드된 경우
})();
