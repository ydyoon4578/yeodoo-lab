// 홈 '기간별 수익률' 조립 검사. 브라우저 없이 렌더러를 실제 data/*.json 에 물린다.
//
// ⚠ '지금 시장' 카드 검사는 2026-08-03 에 함께 빠졌다(그 구획을 홈에서 뺐다).
//   국면·심리·폭·위험선호는 market.html 이 그린다 — 검사가 필요하면 그쪽에 붙인다.
//
// 여기서만 잡히는 것들 — 전부 실제로 배포됐던 사고다.
//   · 자료 **도착 순서** 때문에 섹터 묶음이 0줄로 나감(두 파일이 한 표를 채운다)
//   · 같은 종목을 두 경로에서 그려 '그 밖'이 두 줄씩 나옴
//   · 트리 자식합이 부모와 안 맞음 · 시총 정렬이 깨짐 · 하위 단에서 up/dn 색이 덮임
// 종료코드 1 이면 실패다(build/validate_site.py 가 이 파일을 부른다).
"use strict";
const fs = require("fs");
const path = require("path");
const H = require(path.join(__dirname, "home_render_harness.js"));

const ROOT = path.join(__dirname, "..");
const J = p => JSON.parse(fs.readFileSync(path.join(ROOT, "data", p), "utf8"));
const opt = p => { try { return J(p); } catch (e) { return null; } };

const TBL = H.stub(), SUB = H.stub();
// 이름 붙인 것만 검사에서 들여다보고, **나머지 id 도 그림자를 준다** — 페이지 본문을
// 통째로 돌리므로 모르는 id 에 null 을 주면 관계없는 곳에서 죽어 렌더러에 닿지도 못한다.
const CALG = H.stub(), CALS = H.stub();
const named = { sttbl: TBL, "st-sub": SUB, "wk-cal-grid": CALG, "wk-sub": CALS };
const spare = {};
const el = n => named[n] || (spare[n] || (spare[n] = H.stub()));

const mb = J("market_board.json"), hr = J("home_reco.json"), rgj = J("regime.json");
const top = J("style_top.json"), trj = J("style_trails.json");
const stk = opt("home_stocks.json");
const snj = (opt("home_market.json") || {}).sentiment || false;

const fail = [];
// IIFE 본문을 통째로 평가한다 — var·function 이 전부 이 스코프에 생긴다(하네스 주석 참조).
// home_reco 를 **늦게** 도착시킨다 — 홈의 표는 스타일 묶음과 이 파일 둘이 채우는데,
// 늦게 오는 쪽이 자리를 못 찾은 채 배포된 적이 있다. 그 순서를 검사에 못 박는다.
const G = H.browserGlobals(el, path.join(ROOT, "data"), ["home_reco.json"]);
const body = H.body(path.join(ROOT, "index.html"));
if (body.length < 20000) fail.push("스크립트 본문이 " + body.length + "바이트뿐 — IIFE 를 못 벗겼다");
const run = new Function(
  "document,window,fetch,matchMedia,localStorage,location,navigator,IntersectionObserver,getComputedStyle,el,__ctx",
  body + "\n;Object.assign(__ctx,{drawStyle:typeof drawStyle==='function'?drawStyle:null," +
         "setSTOP:function(v){STOP=v},setSLAB:function(v){SLAB=v},MK:MK});");
const ctx = {};
try {
  run(G.document, G.window, G.fetch, G.matchMedia, G.localStorage, G.location,
      G.navigator, G.IntersectionObserver, G.getComputedStyle, el, ctx);
} catch (e) { fail.push("스크립트 평가 실패: " + e.message); }
const { drawStyle, setSTOP, setSLAB, MK } = ctx;
if (!drawStyle) fail.push("렌더러를 못 얻었다(drawStyle)");
if (fail.length) { console.log("❌ " + fail.join(" / ")); process.exit(1); }
console.log("스크립트 본문 %d바이트 평가 · 렌더러 확보 ✅", body.length);

// ① 페이지 자신의 도착 경로. **검사가 대신 그려 주지 않는다** — fetch 가 실제 파일로
//    응답하므로 index.html 의 .then 사슬이 그대로 돌고, 그 배선이 검사 대상이 된다.
//    (전에는 검사가 renderMarket·drawStyle 을 손수 불러, 배선을 지워도 통과했다.)
let err = null;
async function settle(n) { for (let i = 0; i < n; i++) await new Promise(r => setImmediate(r)); }

(async () => {
  await settle(10); await new Promise(r => setTimeout(r, 60)); await settle(20);
  const late = (TBL.innerHTML.match(/tr class="lv1"/g) || []).length;
  console.log("페이지 자체 로드 후: 섹터 %d줄", late);
  if (!late) fail.push("섹터 줄이 0 — 자료 도착 순서 배선이 끊겼다");

  // ⑦ 일정 캘린더 — 격자가 그려지고 **기준일이 머리글에 붙는가.**
  //    🚨 2026-08-10 에 시차를 설명하던 격자 아래 세 줄(.calfresh)을 걷어내고 그 날짜만
  //      머리글 .sub 로 옮겼다(사용자 결정). 옮긴 자리가 조용히 비면 화면은 "오늘 칸이
  //      왜 비었나"에 아무 답도 못 한다 — 그 질문은 실제로 두 번 신고됐다.
  //      설명을 지우는 것과 근거를 지우는 것은 다르다. 근거가 살아 있는지 여기서 못 박는다.
  const nDay = (CALG.innerHTML.match(/class="caldate"/g) || []).length;
  const asof = CALS.textContent || "";
  console.log("캘린더: 날짜칸 %d개 · 머리글 기준일 %j", nDay, asof);
  //    ⚠ 문턱은 10 이다. 지금 20칸(4주 × 평일 5)이지만 그 수를 강제하지 않는다 —
  //      이 검사가 잡으려는 것은 '격자가 통째로 안 그려졌다'이지 주 수가 아니다.
  if (nDay < 10) fail.push("캘린더 날짜칸이 " + nDay + "개뿐 — 격자 배선이 끊겼다");
  // ⚠ 2026-08-11 — 문구를 '지수 등락률 …기준' 에서 '기준일 …' 로 바꿨다(사용자 결정).
  //   기대값도 같이 고친다. 안 고치면 이 검사가 '되돌려라'라고 말한다.
  if (!/^· 기준일 \d{4}-\d{2}-\d{2}$/.test(asof))
    fail.push("캘린더 머리글 기준일이 안 붙었다: " + JSON.stringify(asof));
  if (/calfresh/.test(CALG.innerHTML))
    fail.push("걷어낸 .calfresh 가 격자 아래에 다시 나타났다");

  // ⑧ 정밀도 — **없는 자리를 그리고 있지 않은가.**
  //    🚨 2026-08-10 사고. home_summary 가 종목 수익률을 round(v,1) 로 저장하는데 화면은
  //      toFixed(2) 로 그려서 +0.026% 가 '0.00%' 로 나갔다. 518종 전부 둘째 자리가 0
  //      이었는데 아무도 못 봤다 — 없는 자리는 빈칸이 아니라 0 으로 보이기 때문이다.
  //      증상을 직접 잰다: 소수 2자리로 찍힌 숫자 중 마지막 자리가 0 인 비율.
  //      값이 고르면 10% 근처다. 저장이 1자리면 100% 가 된다.
  //    ⚠ 문턱 35% 는 넉넉히 잡았다. 이 검사가 잡으려는 것은 '자리가 통째로 없음'이지
  //      분포의 미세한 치우침이 아니다(목표주가처럼 원래 반올림된 값이 섞이면 올라간다).
  const nums = (TBL.innerHTML.replace(/<[^>]*>/g, " ").match(/-?\d+\.\d\d(?!\d)/g) || []);
  const zero = nums.filter(s => s.slice(-1) === "0").length;
  const pct = nums.length ? Math.round((100 * zero) / nums.length) : 0;
  console.log("정밀도: 2자리 숫자 %d개 중 끝자리 0 이 %d개 (%d%%)", nums.length, zero, pct);
  if (nums.length >= 200 && pct >= 35)
    fail.push("2자리로 그린 숫자의 " + pct + "%가 끝자리 0 — 저장 정밀도가 표시보다 낮다(round 자릿수를 볼 것)");

  // ⚠ 2026-08-04 홈이 **섹터 → 산업그룹(2차) → 종목** 두 단으로 돌아왔다(사용자 결정).
  //    2026-08-03 에 '11섹터만' 으로 줄이면서 걷었던 검사 중 이 구조에 맞는 것을 되살린다.
  //    서브산업(4차)은 여전히 안 낸다 — 그쪽은 industry.html 전담이라 lv4 가 나오면 실패다.
  const Hh = TBL.innerHTML;
const cnt = n => (Hh.match(new RegExp('tr class="lv' + n + '"', "g")) || []).length;
console.log("표: 묶음 %d · 섹터 %d · 하위단 %d · 열 %d",
  (Hh.match(/tr class="grp"/g) || []).length, cnt(1), cnt(2) + cnt(3) + cnt(4),
  ((Hh.match(/<thead>[\s\S]*?<\/thead>/) || [""])[0].split("<th").length - 1));

// ③ 섹터는 GICS 기준 그대로여야 하고, 하위 단이 다시 새어 나오면 안 된다
const D = hr.industry;
if (cnt(1) !== D.sectors.length)
  fail.push("섹터 줄 " + cnt(1) + " ≠ home_reco.industry.sectors " + D.sectors.length);
// 산업그룹 줄 — solo(이름이 섹터와 같고 그 섹터의 유일한 2차)는 **빼는 것이 정본이다**.
//   화면이 스스로 판정하지 않고 home_reco 의 solo 표를 읽으므로, 여기서도 그 표로 기대값을 만든다.
const g2 = D.rows.filter(r => r.lv === 2);
const bySec2 = {};
g2.forEach(r => (bySec2[r.p] = bySec2[r.p] || []).push(r));
const wantG = g2.filter(r => !(bySec2[r.p].length === 1 && r.solo)).length;
if (cnt(2) !== wantG)
  fail.push("산업그룹 줄 " + cnt(2) + " ≠ solo 뺀 기대값 " + wantG);
if (cnt(4))
  fail.push("서브산업(lv4)이 " + cnt(4) + "줄 새어 나왔다 — 홈은 2차까지만 낸다");
// solo 섹터는 그 이름의 2차 줄이 화면에 있으면 안 된다(같은 이름이 두 번 나온다)
g2.filter(r => bySec2[r.p].length === 1 && r.solo).forEach(r => {
  if (Hh.indexOf('data-open="g-' + r.p + '-') >= 0)
    fail.push("solo 산업그룹이 그려졌다: " + r.p + " / " + r.nm);
});
// 펼침 버튼은 섹터 11 + 산업그룹 wantG 개여야 한다(종목 줄에는 버튼이 없다)
const nOpen = (Hh.match(/class="htg" data-open/g) || []).length;
if (nOpen !== cnt(1) + wantG)
  fail.push("펼침 버튼 " + nOpen + " ≠ 섹터 " + cnt(1) + " + 산업그룹 " + wantG);
// 자식 줄은 부모 id 를 가리켜야 한다 — 끊기면 눌러도 아무 일도 안 일어난다
const ids = new Set([...Hh.matchAll(/data-id="([^"]+)"/g)].map(m => m[1]));
[...new Set([...Hh.matchAll(/data-p="([^"]+)"/g)].map(m => m[1]))].forEach(p => {
  if (!ids.has(p)) fail.push("고아 줄 — data-p=" + p + " 를 가리키는 부모 줄이 없다");
});

// ④ 정렬(시총 내림차순)
const dom = [...Hh.matchAll(/<tr class="lv1"[^>]*>(?:<th[^>]*>)(?:<(?:button|span)[^>]*>[^<]*<\/(?:button|span)>)?<span class="snm">([^<]*)</g)].map(m => m[1]);
const mcOf = {}; D.sectors.forEach(x => (mcOf[x.nm] = x.mc || 0));
if (dom.length !== cnt(1)) fail.push("섹터 이름을 " + dom.length + "개만 읽었다(줄은 " + cnt(1) + ")");
for (let i = 1; i < dom.length; i++) if (mcOf[dom[i - 1]] < mcOf[dom[i]]) fail.push("섹터 정렬이 시총순이 아니다: " + dom[i - 1] + " < " + dom[i]);

// ⑥ 구성종목 ▸ — **누르면 열리는가.**
//    🚨 이 검사가 없어서 놓친 사고: 지수 방법론의 ▸ 핸들러가 wireTree 와 중복방지 플래그
//       이름(__htg)이 겹쳐 **한 번도 안 붙었다.** 버튼 17개는 마크업에 그대로 있었으므로
//       위 ①~⑤ 는 전부 통과했고, 배포 하루 뒤 사용자가 신고했다(2026-08-03).
//       → 세는 것으로는 부족하다. 리스너를 실제로 눌러 본다.
const holdIds = [...Hh.matchAll(/<tr class="hold" id="([^"]+)"/g)].map(m => m[1]);
const btnIds = [...Hh.matchAll(/<button[^>]*class="htg" data-hold="([^"]+)"/g)].map(m => m[1]);
if (!btnIds.length) fail.push("지수 방법론 ▸ 버튼이 0개 — 묶음이 안 그려졌다");
btnIds.forEach(id => { if (holdIds.indexOf(id) < 0) fail.push("▸ " + id + " 가 가리키는 구성종목 행이 없다"); });

// sttbl 의 위임 리스너는 지금 **하나**다(구성종목 펼침). 섹터 트리가 나가면서
// wireTree 도 함께 나갔다(2026-08-03).
// ⚠ 둘을 다시 걸 때는 중복방지 플래그 이름을 겹치지 말 것 — 전에 둘 다 __htg 를 써
//   구성종목 핸들러가 **한 번도 안 붙은** 사고가 있었다.
const nls = TBL.listeners("click");
if (nls < 1) fail.push("sttbl 클릭 리스너가 0개 — 구성종목 펼침 핸들러가 안 붙었다");

// 열고 → 닫고. 마크업대로 접힌 상태에서 시작한다.
if (btnIds.length && nls) {
  const n0 = fail.length;                                 // 이 구획에서 새로 난 실패만 센다
  const id = btnIds[0];
  const row = el(id);
  row.setAttribute("hidden", "");
  const b = H.fakeBtn({ "data-hold": id, "aria-expanded": "false" });
  b.textContent = "▸";
  const e1 = H.clickOn(b);
  TBL.dispatch("click", e1);
  (e1.__err || []).forEach(x => fail.push("▸ 클릭 핸들러 예외: " + x.message));
  if (row.hasAttribute("hidden")) fail.push("▸ " + id + " 를 눌러도 구성종목이 안 열린다");
  if (b.getAttribute("aria-expanded") !== "true") fail.push("▸ " + id + " aria-expanded 가 안 바뀐다");
  if (b.textContent !== "▾") fail.push("▸ " + id + " 화살표가 ▾ 로 안 바뀐다");
  const e2 = H.clickOn(b);
  TBL.dispatch("click", e2);
  (e2.__err || []).forEach(x => fail.push("▸ 재클릭 핸들러 예외: " + x.message));
  if (!row.hasAttribute("hidden")) fail.push("▸ " + id + " 를 다시 눌러도 안 접힌다");
  if (b.textContent !== "▸") fail.push("▸ " + id + " 화살표가 ▸ 로 안 돌아온다");
  // ⚠ ✅ 는 **이 구획이 실제로 통과했을 때만** 찍는다. 처음엔 무조건 찍었더니 버그를 다시
  //   넣어 본 실행에서 '열고 닫기 ✅' 밑에 실패 4건이 나왔다 — 로그가 거짓말을 한다.
  console.log("구성종목 ▸ %d개 · sttbl 클릭 리스너 %d개 · %s 열고 닫기 %s",
    btnIds.length, nls, id, fail.length === n0 ? "✅" : "❌");
}
// ⚠ 여기서 재지 **않는** 것 — 섹터 트리(data-open)의 펼침. 그쪽 핸들러는 box.querySelectorAll
//   로 자식 행을 찾는데 이 그림자 DOM 은 선택자를 풀지 않는다(빈 배열을 준다). 트리를 통째로
//   짓지 않는 한 여기서는 못 잰다 — 필요해지면 그때 진짜 DOM 을 들이는 것이 맞다.

  if (fail.length) { console.log("\n❌ " + fail.length + "건"); fail.forEach(f => console.log("  · " + f)); process.exit(1); }
  console.log("\n홈 렌더 검사: 통과 ✅");
})();
