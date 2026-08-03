// index.html 인라인 스크립트를 브라우저 없이 평가해, 홈 렌더러를 손에 쥐여 주는 얇은 층.
//
// 왜 있나 — 홈의 표·카드는 자료가 여러 파일에서 따로 도착하고, 그 조립이 어긋나면
// 화면이 조용히 비어서 나간다(실제로 두 번 그렇게 배포됐다: 섹터 묶음 0줄 · 종목 두 줄씩).
// 브라우저를 띄우지 않고 그 조립만 재현해 보는 것이 이 파일의 일이다.
//
// 🚨 **선언을 골라 뽑지 않는다.** 처음엔 필요한 함수·변수를 손으로 적어 정규식으로
//    떼어 냈다. 두 가지가 계속 어긋났다:
//      ① 새 최상위 선언을 만들 때마다 하네스가 그것을 모르고 'X is not defined' 로 죽었다
//         (한 세션에 IXNOTE·gauge·drawMkSum 세 번). 페이지 버그가 아니라 검사 도구의
//         구멍이라, 매번 하네스를 고치다 보면 검사 자체를 안 믿게 된다.
//      ② 정규식 리터럴이 스캐너를 깬다. /[&<>"]/ 의 " 를 문자열 시작으로 읽어 그 뒤 코드를
//         통째로 삼켰다(61개 중 40개가 잘려 'Unexpected end of input').
//         JS 를 정규식으로 파싱하려던 것이 애초에 틀린 접근이었다.
//    → **IIFE 껍데기만 벗기고 본문을 통째로 평가한다.** var·function 이 전부 이 모듈의
//      스코프에 그대로 생긴다. 스크립트가 자라도 하네스는 손댈 것이 없다.
//
// ⚠ 본문을 통째로 돌리므로 로드 시점 부수효과(fetch·리스너 부착·초기 렌더)도 함께 돈다.
//   그것이 목적이다 — fetch 는 **data/ 의 진짜 파일로 응답**하므로 페이지 자신의 .then
//   사슬이 돌고, '자료가 늦게 오면 다시 그린다' 같은 배선이 검사 대상이 된다.
//   (검사가 렌더러를 손수 부르던 시절엔 그 배선을 지워도 통과했다.)
"use strict";
const fs = require("fs");

function mainScript(html) {
  const blocks = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  return blocks.reduce((a, b) => (b.length > a.length ? b : a), "");
}

// 감싼 IIFE 를 벗긴다. 못 벗기면 그대로 돌려준다(그 경우 선언이 안 새어 나오므로
// 부르는 쪽이 '선언이 너무 적다'로 잡는다).
function unwrap(src) {
  const t = src.trim();
  const head = t.match(/^\(function\s*\(\s*\)\s*\{/);
  if (!head) return src;
  const tail = t.match(/\}\s*\)\s*\(\s*\)\s*;?\s*$/);
  if (!tail) return src;
  return t.slice(head[0].length, t.length - tail[0].length);
}

// 최소 DOM 그림자. 렌더러가 실제로 부르는 것만 흉내 낸다 —
// 브라우저를 흉내 내는 것이 목적이 아니라 조립을 재현하는 것이다.
function stub(html) {
  const o = {
    _a: {}, hidden: false, _h: html || "", dataset: {},
    style: { setProperty() {}, removeProperty() {}, getPropertyValue() { return ""; } },
    classList: { add() {}, remove() {}, contains() { return false; } },
    getAttribute(k) { return k in this._a ? this._a[k] : null; },
    setAttribute(k, v) { this._a[k] = v; },
    removeAttribute(k) { delete this._a[k]; },
    hasAttribute(k) { return k in this._a; },
    addEventListener() {}, removeEventListener() {}, appendChild() {}, remove() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    closest() { return null; }, focus() {}, click() {}, scrollIntoView() {},
    getBoundingClientRect() { return { width: 0, height: 0, top: 0, left: 0 }; },
    set innerHTML(v) { this._h = v; }, get innerHTML() { return this._h; },
    set textContent(v) { this._t = v; }, get textContent() { return this._t || ""; },
    get children() { return []; }, get cells() { return []; },
  };
  return o;
}

// 브라우저 전역의 최소 대역. 없는 것을 부르면 조용히 통과시킨다 —
// 여기서 죽으면 정작 재려던 렌더러에 닿지도 못한다.
function browserGlobals(getEl, dataDir, slow) {
  const doc = {
    getElementById: getEl,
    querySelector: () => null, querySelectorAll: () => [],
    createElement: () => stub(), createDocumentFragment: () => stub(),
    addEventListener() {}, documentElement: stub(), body: stub(),
    head: stub(), cookie: "", title: "",
  };
  return {
    document: doc,
    window: { addEventListener() {}, matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
              location: { hash: "", href: "", search: "" }, scrollTo() {}, scrollBy() {},
              requestAnimationFrame(f) { return 0; }, localStorage: { getItem: () => null, setItem() {} } },
    // 🚨 **진짜 파일로 응답한다.** 처음엔 영원히 대기시키고 검사가 자료를 직접 먹여
    //    렌더러를 불렀는데, 그러면 검사가 **페이지의 배선을 대신 해주는** 꼴이 된다 —
    //    '자료가 늦게 오면 다시 그린다' 같은 배선을 지워도 검사가 통과했다(실측).
    //    fetch 가 실제로 응답하면 페이지 자신의 .then 사슬이 돌고, 그 배선이 검사 대상이 된다.
    // ⚠ slow 에 적은 파일은 **일부러 늦게** 준다. 전부 즉시 응답하면 도착 순서가 늘
    //    유리하게 나와, '늦게 오면 다시 그린다' 배선을 지워도 검사가 통과한다(실측).
    //    홈의 표는 두 파일이 채우므로 그 순서가 곧 검사 대상이다.
    fetch: (url) => {
      const name = String(url).split("?")[0].replace(/^.*\//, "");
      const p = require("path").join(dataDir, name);
      const late = (slow || []).indexOf(name) >= 0;
      const give = () => {
        if (!require("fs").existsSync(p)) return { ok: false, json: () => Promise.reject(new Error("404")) };
        const j = JSON.parse(require("fs").readFileSync(p, "utf8"));
        return { ok: true, json: () => Promise.resolve(j) };
      };
      return late ? new Promise(r => setTimeout(() => r(give()), 12)) : Promise.resolve(give());
    },
    matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
    localStorage: { getItem: () => null, setItem() {} },
    location: { hash: "", href: "", search: "" },
    navigator: { userAgent: "node" },
    IntersectionObserver: function () { return { observe() {}, disconnect() {} }; },
    getComputedStyle: () => ({ getPropertyValue: () => "" }),
  };
}

module.exports = {
  mainScript, unwrap, stub, browserGlobals,
  body(path) { return unwrap(mainScript(fs.readFileSync(path, "utf8"))); },
};
