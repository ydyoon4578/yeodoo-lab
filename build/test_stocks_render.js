// stocks.html 필터 패널·차트 마커 조립 검사. 브라우저 없이 실제 data/*.json 에 물린다.
//
// 🚨 2026-08-05 — 이 파일이 생긴 이유.
//   샹들리에 프리셋을 걷어내면서 `var ... ,pfch=el('presetsch')` 선언만 지우고 아래
//   디스패치 맵의 `ch:pfch` 참조를 남겼다. 결과는 **ReferenceError → PRESETS.forEach 전체
//   중단 → 칩이 하나도 안 그려짐 → 프리셋이 전부 사라지고 목록이 '전체'로 되돌아감.**
//   페이지 절반이 죽었는데 validate_site 도, 홈·explorer 렌더 검사도 통과했다 —
//   종목 페이지에는 조립 검사가 아예 없었기 때문이다. 브라우저로 눈으로 보고서야 알았다.
//
//   구문 검사로는 못 잡는다(문법은 멀쩡하다). 마크업 검사로도 못 잡는다(HTML 은 그대로다).
//   **돌려 봐야 잡힌다.** 그래서 홈과 같은 하네스로 본문을 통째로 평가한다.
//
// 종료코드 1 이면 실패다(build/validate_site.py 가 이 파일을 부른다).
"use strict";
const fs = require("fs");
const path = require("path");
const H = require(path.join(__dirname, "home_render_harness.js"));

const ROOT = path.join(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "stocks.html"), "utf8");

const fail = [];
// 🚨 프리셋 칩이 **실제로 붙었는지** 세려면 appendChild 를 기록해야 한다. 하네스의 기본
//   stub 은 appendChild 가 no-op 이라, 렌더러가 통째로 죽어도 '아무 일 없음'과 구별되지
//   않는다 — 오늘 낸 회귀(pfch ReferenceError)가 정확히 그 모양이었다.
function counted() { const o = H.stub(); o._n = 0; o.appendChild = function () { this._n++; }; return o; }
const named = { presets: counted(), presets2: counted(), presets2b: counted(),
                presets2c: counted(), presets3: counted(), presetall: counted(),
                // 🚨 2026-08-17 수익률 줄. 이 칸을 안 넣으면 counted() 가 아니라 일반 stub 이
                //   잡혀 칩이 붙어도 안 세어진다 — «칩 0개» 로 잘못 실패한다(실제로 그랬다).
                presetsr: counted() };
const spare = {};
const el = n => named[n] || (spare[n] || (spare[n] = H.stub()));

// 🚨 프리셋 렌더러는 fetch 의 .then 안에서 돈다. 거기서 던진 예외는 **동기 throw 가
//   아니라 unhandled rejection** 이라, run() 을 try 로 감싸도 안 잡힌다.
//   실제로 처음 이 검사를 이 상태로 두었더니 오늘의 회귀를 그대로 통과시켰다.
const rejected = [];
process.on("unhandledRejection", e => rejected.push(e && e.message ? e.message : String(e)));

// 페이지 본문을 통째로 평가한다. 여기서 죽으면 그것이 곧 이 검사의 결과다.
const G = H.browserGlobals(el, path.join(ROOT, "data"), []);
const body = H.body(path.join(ROOT, "stocks.html"));
if (body.length < 20000) fail.push("스크립트 본문이 " + body.length + "바이트뿐 — IIFE 를 못 벗겼다");
const scope = {};
const run = new Function(
  "document,window,fetch,matchMedia,localStorage,location,navigator,IntersectionObserver,getComputedStyle,el,__ctx",
  body + "\n;Object.assign(__ctx,{PRESETS:typeof PRESETS!=='undefined'?PRESETS:null," +
         "swKeys:typeof swKeys==='function'?swKeys:null});");
try {
  run(G.document, G.window, G.fetch, G.matchMedia, G.localStorage, G.location,
      G.navigator, G.IntersectionObserver, G.getComputedStyle, el, scope);
} catch (e) {
  console.log("종목 렌더 검사: 실패 ❌ — 페이지 스크립트가 평가 중 죽었다: " + e.message);
  process.exit(1);
}

// ── ⓪ .then 사슬이 다 돌 때까지 기다린 뒤에 센다 ─────────────────────────
async function main() {
for (let i = 0; i < 20; i++) await new Promise(r => setTimeout(r, 5));
if (rejected.length) {
  fail.push("페이지 스크립트가 비동기 경로에서 죽었다: " + rejected[0]);
}
const nChip = Object.values(named).reduce((a, o) => a + o._n, 0);
if (nChip < 10) {
  fail.push("프리셋 칩이 " + nChip + "개만 붙었다 — 필터 패널이 사실상 비었다"
            + (rejected.length ? "" : " (예외 없이 조용히 비었다)"));
}

// ── ① 프리셋 레지스트리가 살아 있는가 ─────────────────────────────────────
const P = scope.PRESETS;
if (!Array.isArray(P) || P.length < 10) {
  fail.push("PRESETS 가 없거나 너무 적다(" + (P ? P.length : "없음") + ") — 필터 정의가 깨졌다");
} else {
  // 그룹 코드가 디스패치 맵과 맞는가. 맵에 없는 그룹은 `||pf` 로 흘러 **스윙 줄에 섞인다** —
  // 조용히 잘못된 줄에 붙으므로 눈으로 보기 전에는 안 드러난다.
  const KNOWN = new Set(["a", "r", "p", "f", "s1", "s2", "s3", "s2b"]);   // p = 수익률(2026-08-17)
  const bad = [...new Set(P.map(p => p[6]).filter(g => !KNOWN.has(g)))];
  if (bad.length) {
    fail.push("PRESETS 에 디스패치 맵이 모르는 그룹 코드 " + JSON.stringify(bad) +
              " — 이 프리셋들은 기본 줄(스윙 타점)에 섞여 붙는다");
  }
  // 지운 프리셋이 정말 지워졌는가(레지스트리에 남으면 #p=… URL 로 계속 닿는다)
  const keys = new Set(P.map(p => p[0]));
  for (const k of ["swingbuy", "swingsell", "all"]) {
    if (!keys.has(k)) fail.push("핵심 프리셋 '" + k + "' 가 사라졌다");
  }
}

// ── ② 프리셋 헬퍼가 실제로 동작하는가 ─────────────────────────────────────
if (typeof scope.swKeys === "function") {
  const a = scope.swKeys("swingbuy"), b = scope.swKeys("swingsell"), c = scope.swKeys("all");
  if (!Array.isArray(a) || !Array.isArray(b) || c !== null) {
    fail.push("swKeys 가 스윙 두 개에 마커 키를 못 돌려준다 — 스윙 탭이 빈 목록이 된다");
  }
} else {
  fail.push("swKeys 가 없다 — 스윙 타점 필터의 뼈대가 사라졌다");
}

// ── ③ 차트 마커 배선 ─────────────────────────────────────────────────────
// 🚨 2026-08-05 — 샹들리에 마름모는 화면에서 뺐다(사용자 요청). 이 검사는 **반쪽만
//   되살아나는 것**을 막는 용도로 남긴다: 데이터에 chb 가 다시 생겼는데 아무도 안 읽거나,
//   그리면서 '구별 불가' 판정을 안 적는 상태. 지금은 nChb=0 이라 조용히 지나간다.
const stocks = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "stocks.json"), "utf8"));
const nChb = (stocks.stocks || []).filter(s => (s.chb || []).length).length;
if (nChb > 0) {
  if (!/s\.chb/.test(html) || !/mk\.chb/.test(html)) {
    fail.push("stocks.json 의 " + nChb + "종이 chb(샹들리에 교차)를 들고 있는데 차트가 안 읽는다");
  }
  if (!/구별 불가/.test(html)) {
    fail.push("샹들리에 교차를 그리면서 '구별 불가' 판정을 어디에도 안 적는다");
  }
}

if (fail.length) {
  console.log("종목 렌더 검사: 실패 ❌ " + fail.length + "건");
  fail.forEach(f => console.log("  - " + f));
  process.exit(1);
}
console.log("종목 렌더 검사: 통과 ✅ (프리셋 " + (scope.PRESETS || []).length +
            "종 · 칩 " + nChip + "개 부착 · 샹들리에 교차 보유 " + nChb + "종)");
}
main();
