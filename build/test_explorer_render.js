// explorer '같은 구간 지수' 비교표 조립 검사. 브라우저 없이 실제 data/*.json 에 물린다.
//
// 여기서만 잡히는 것들 — 전부 실제로 있던 사고다.
//   · 이름 조인이 끊겨 배포 원장 4종이 지수 눈금·구성·비교가능 표시를 통째로 못 받음
//     (목록 쪽 이름은 ixL 로 'SPX'→'S&P 500' 을 편 뒤인데 키는 원문으로 만들었다)
//   · 지수를 전략과 **다른 주기**로 재 같은 SPX 가 한 화면에서 두 값으로 나옴
//     (일간 샤프 0.351 vs 월말 0.535 · MDD -56.78 vs -52.56)
// 종료코드 1 이면 실패다(build/validate_site.py 가 이 파일을 부른다).
"use strict";
const fs = require("fs");
const path = require("path");
const H = require(path.join(__dirname, "home_render_harness.js"));

const ROOT = path.join(__dirname, "..");
const IX = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "strategy_index.json"), "utf8"));

const spare = {};
const el = n => spare[n] || (spare[n] = H.stub());
const G = H.browserGlobals(el, path.join(ROOT, "data"), []);
const body = H.body(path.join(ROOT, "explorer.html"));

const fail = [];
if (body.length < 40000) fail.push("스크립트 본문이 " + body.length + "바이트뿐 — IIFE 를 못 벗겼다");
const ctx = {};
try {
  new Function(
    "document,window,fetch,matchMedia,localStorage,location,navigator,IntersectionObserver,getComputedStyle,__ctx",
    body + "\n;Object.assign(__ctx,{drawDetail:typeof drawDetail==='function'?drawDetail:null," +
           "detailEl:typeof detailEl!=='undefined'?detailEl:null,D:typeof D!=='undefined'?D:null});"
  )(G.document, G.window, G.fetch, G.matchMedia, G.localStorage, G.location,
    G.navigator, G.IntersectionObserver, G.getComputedStyle, ctx);
} catch (e) { fail.push("스크립트 평가 실패: " + e.message); }
if (!ctx.drawDetail || !ctx.D) fail.push("렌더러를 못 얻었다(drawDetail/D)");
if (fail.length) { console.log("❌ " + fail.join(" / ")); process.exit(1); }

setTimeout(() => {
  const D = ctx.D || [];
  // ① 이름 조인 — 인덱스에 있는 전략은 화면에서도 눈금을 받아야 한다.
  //    '목록 제외'로 뺀 전략은 인덱스에 없으므로 이름으로 맞춰 걸러 낸다.
  const inIx = new Set();
  IX.items.forEach(x => { inIx.add(x.name); inIx.add(x.name.replace(/NDX 100/g, "NASDAQ 100")
    .replace(/\bNDX\b/g, "NASDAQ 100").replace(/\bSPX\b/g, "S&P 500")); });
  const orphan = D.filter(d => inIx.has(d.n) && !d._pr).map(d => d.n);
  console.log("전략 %d · 지수 눈금 %d · 인덱스 수록 %d", D.length, D.filter(d => d._pr).length, IX.items.length);
  if (orphan.length) fail.push("지수 눈금이 안 붙은 전략 " + orphan.length + "건: " + orphan.slice(0, 3).join(" / "));

  // ② 주기 — 대조군이 지수인 전략은 대조군 값과 지수 열이 같아야 한다.
  //    다른 주기로 재면 같은 SPX 가 한 화면에서 두 값이 된다.
  let checked = 0, off = [];
  IX.items.forEach(x => {
    const lab = x.bench_label || "", b = x.bench || {}, p = (x.pr || {}).spx;
    if (!/S&P 500/.test(lab) || !/매수후보유/.test(lab)) return;
    if (!p || b.vol == null || b.mdd == null) return;
    checked++;
    if (Math.abs(b.vol - p.vol) + Math.abs(b.mdd - p.mdd) > 1.5)
      off.push(x.name + " (vol " + b.vol + "/" + p.vol + " · mdd " + b.mdd + "/" + p.mdd + ")");
  });
  console.log("대조군=S&P 500 매수후보유 %d건 중 지수 열 불일치 %d건", checked, off.length);
  if (!checked) fail.push("주기 검사를 한 건도 못 했다 — bench_label 표기가 바뀌었나");
  if (off.length) fail.push("같은 SPX 인데 대조군과 지수 열이 다르다: " + off.slice(0, 2).join(" / "));

  // ③ 표가 실제로 그려지나 — 지표 4행이 나와야 한다.
  const d = D.find(x => x._pr && x._mx);
  try { ctx.drawDetail(d); } catch (e) { fail.push("drawDetail 예외: " + e.message); }
  const h = ctx.detailEl ? ctx.detailEl.innerHTML : "";
  const tb = (h.match(/<table class="prtbl">[\s\S]*?<\/table>/) || [""])[0];
  const rows = (tb.match(/<tr><th scope="row">/g) || []).length;
  const cols = (tb.match(/<th scope="col">/g) || []).length;
  console.log("비교표: %d행 × %d열 (%s)", rows, cols, (d || {}).n);
  if (rows !== 4) fail.push("비교표가 " + rows + "행 — CAGR·변동성·MDD·샤프 넷이어야 한다");
  if (cols !== 6) fail.push("비교표가 " + cols + "열 — 지표·전략·SPX·차이·NDX·차이 여섯이어야 한다");
  if (!/mv (pw|pl)/.test(tb)) fail.push("전략이 지수보다 나은/못한 칸 표식이 하나도 없다");

  if (fail.length) { console.log("\n❌ " + fail.length + "건"); fail.forEach(f => console.log("  · " + f)); process.exit(1); }
  console.log("\nexplorer 렌더 검사: 통과 ✅");
}, 400);
