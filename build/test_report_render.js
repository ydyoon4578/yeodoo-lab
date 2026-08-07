// report.html 조립 검사. 브라우저 없이 실제 data/strategy_report.json 에 물린다.
//
// 🚨 이 페이지는 **fetch 한 번에 화면 전체가 달려 있다.** 목차·리포트 117편·랩 한계·
//   통계줄이 전부 같은 .then 안에서 그려진다. 거기서 예외가 나면 unhandled rejection 이
//   되어 조용히 빈 화면이 나간다 — stocks.html 이 정확히 그렇게 죽었고(pfch ReferenceError)
//   validate_site 도 다른 렌더 검사도 전부 통과했다. 그래서 **돌려 본다.**
//
// 이 검사가 특별히 지키는 것 하나 더 — **esc() 필드에 들어간 마크다운.**
//   이 저장소는 별표가 화면에 그대로 찍히는 사고를 하루에 네 번 냈다(DATA-FACTS 24).
//   report.html 은 mb() 로 굵게 바꾸지만, 그 변환기를 안 태운 경로가 하나라도 있으면
//   별표가 다시 새어 나온다. 렌더 결과에서 직접 센다.
//
// 종료코드 1 이면 실패다(build/validate_site.py 가 이 파일을 부른다).
"use strict";
const fs = require("fs");
const path = require("path");
const H = require(path.join(__dirname, "home_render_harness.js"));

const ROOT = path.join(__dirname, "..");
const fail = [];

// 붙은 것을 세려면 innerHTML 을 붙잡아야 한다. 하네스 stub 은 그걸 해 준다.
const named = {};
const el = n => named[n] || (named[n] = H.stub());

const rejected = [];
process.on("unhandledRejection", e => rejected.push(e && e.message ? e.message : String(e)));

const G = H.browserGlobals(el, path.join(ROOT, "data"), []);
const body = H.body(path.join(ROOT, "report.html"));
if (body.length < 6000) fail.push("스크립트 본문이 " + body.length + "바이트뿐 — IIFE 를 못 벗겼다");

try {
  new Function(
    "document,window,fetch,matchMedia,localStorage,location,navigator,IntersectionObserver,getComputedStyle,el",
    body)(G.document, G.window, G.fetch, G.matchMedia, G.localStorage, G.location,
          G.navigator, G.IntersectionObserver, G.getComputedStyle, el);
} catch (e) {
  console.log("리포트 렌더 검사: 실패 ❌ — 페이지 스크립트가 평가 중 죽었다: " + e.message);
  process.exit(1);
}

async function main() {
  for (let i = 0; i < 30; i++) await new Promise(r => setTimeout(r, 5));
  if (rejected.length) fail.push("페이지 스크립트가 비동기 경로에서 죽었다: " + rejected[0]);

  const D = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "strategy_report.json"), "utf8"));
  const N = D.items.length;
  const content = el("content").innerHTML || "";
  const toc = el("tocgrid").innerHTML || "";
  const filt = el("filt").innerHTML || "";
  const stat = el("statline").innerHTML || "";
  const tail = el("tail").innerHTML || "";

  // ── ① 리포트가 전부 그려졌나 ──────────────────────────────────────────
  const nArt = (content.match(/<article class="rep"/g) || []).length;
  if (nArt !== N) fail.push("리포트가 " + nArt + "편만 그려졌다 — 자료엔 " + N + "편 있다");
  const nToc = (toc.match(/<a href="#/g) || []).length;
  if (nToc !== N) fail.push("목차가 " + nToc + "줄뿐 — 리포트 " + N + "편과 안 맞는다");
  if ((filt.match(/class="fchip"/g) || []).length < 8) fail.push("필터 칩이 8개 미만 — 조작부가 비었다");
  if (!/규칙 <b>/.test(stat)) fail.push("통계줄이 비었다");
  if (!/랩 전체의 한계/.test(tail)) fail.push("랩 전체의 한계 블록이 안 그려졌다");

  // ── ② 각 절이 실제로 붙었나 ───────────────────────────────────────────
  // 절 제목은 sec() 이 내용이 있을 때만 낸다 — 자료에 있는 만큼 나와야 한다.
  const want = [
    ["규칙", N, x => !!x.rule],
    ["비용 후", D.items.filter(x => x.cost).length, x => !!x.cost],
    ["위험 — 낙폭·꼬리", D.items.filter(x => x.risk).length, x => !!x.risk],
    ["매매대상 대비", D.items.filter(x => x.vs_traded).length, x => !!x.vs_traded],
    ["생존편향 보정 (PIT)", D.items.filter(x => x.pit).length, x => !!x.pit],
    ["후보 풀 추이", D.items.filter(x => x.pool).length, x => !!x.pool],
    ["지금 들고 있는 것", D.items.filter(x => x.holdings).length, x => !!x.holdings],
    ["원문 대비", D.items.filter(x => x.repro).length, x => !!x.repro],
  ];
  for (const [title, n] of want) {
    const got = (content.match(new RegExp("<h3>" + title.replace(/[.*+?^${}()|[\]\\—·()]/g, "\\$&"), "g")) || []).length;
    if (got !== n) fail.push("'" + title + "' 절이 " + got + "편에만 붙었다 — 자료엔 " + n + "편 있다");
  }

  // ── ③ 못 잰 것을 지우지 않았나 ────────────────────────────────────────
  // 🚨 빈칸을 지우면 그 규칙이 그 항목을 통과한 것처럼 읽힌다. 이 페이지의 존재 이유 중
  //   하나가 그것이라, 사라지면 검사가 막는다.
  const nMiss = D.items.filter(x => x.missing && x.missing.length).length;
  const gotMiss = (content.match(/class="miss"/g) || []).length;
  if (gotMiss !== nMiss) fail.push("'못 잰 것' 상자가 " + gotMiss + "편에만 붙었다 — 자료엔 " + nMiss + "편 있다");

  // ── ④ esc() 필드로 새어 나온 마크다운 ─────────────────────────────────
  const stars = (content + tail).match(/\*\*[^*]{1,40}\*\*/g);
  if (stars) fail.push("렌더 결과에 마크다운 별표가 " + stars.length + "곳 남았다(" +
                       stars[0] + ") — mb() 를 안 태운 경로가 있다");

  // ── ⑤ 값이 없을 때 0 으로 채우지 않았나 ───────────────────────────────
  // t 가 없는 규칙이 있으면 '0.00' 이 아니라 '—' 여야 한다. 0 은 '쟀는데 0' 이라는 뜻이다.
  const noT = D.items.filter(x => x.t === null || x.t === undefined).length;
  if (noT > 0 && !/—/.test(content)) fail.push("t 가 없는 규칙 " + noT + "종이 있는데 화면에 '—' 가 없다");

  // ── ⑥ 랩이 실은 값과 화면 값이 같은가(표본 대조) ──────────────────────
  // 채점기를 두 벌 두지 않는다는 약속을 실제로 지키는지, 원본 세 파일과 직접 맞춘다.
  const tech = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "tech_strategies.json"), "utf8"));
  const asset = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "asset_strategies.json"), "utf8"));
  const src = {};
  for (const r of tech.strategies) src[r.sid] = r;
  for (const r of asset.strategies) src[r.sid] = r;
  let drift = 0;
  for (const x of D.items) {
    const s = src[x.sid];
    if (!s) { fail.push("리포트에 원본에 없는 규칙 " + x.sid + " 가 있다"); continue; }
    if (x.t !== (s.t === undefined ? null : s.t)) drift++;
    const c = (x.perf || []).find(p => p.k === "연복리수익률");
    if (c && s.metrics && Math.abs(c.s - s.metrics.cagr) > 0.005) drift++;
  }
  if (drift) fail.push("리포트 수치가 원본과 어긋난 곳 " + drift + "건 — 채점기가 두 벌이 됐다");

  if (fail.length) {
    console.log("리포트 렌더 검사: 실패 ❌ " + fail.length + "건");
    fail.forEach(f => console.log("  - " + f));
    process.exit(1);
  }
  console.log("리포트 렌더 검사: 통과 ✅ (리포트 " + nArt + "편 · 목차 " + nToc +
              "줄 · '못 잰 것' " + gotMiss + "편 · 원본 대조 무편차)");
}
main();
