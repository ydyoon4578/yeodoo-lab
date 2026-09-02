# 사전등록 — S&P 스타일 점수를 랩에서 직접 계산한다 · 2026-09-02, 돌리기 전에 확정

사용자 지시 2026-09-02: 「Pure Value(RPV) / Pure Growth(RPG) 이걸로 현재 랩에 있는 모든
종목 성장주, 가치주로 분류해주는거 가능?」 → **ETF 보유명단으로는 안 된다**(§0) →
「1」(= 방법론을 직접 구현).

원천: **S&P U.S. Style Indices Methodology** (S&P Dow Jones Indices) — PDF 전문을 읽고 옮긴다.

---

## 0. ETF 명단으로는 왜 안 되나

- **Pure 지수는 가운데를 버린다.** RPV 약 125종 · RPG 약 75~80종 = 합 **200종**.
  랩 유니버스 518종 중 **300종 이상이 미분류**로 남는다. 설계가 그렇다.
- **오늘 명단만 얻는다.** Invesco 가 보유명단을 JS 페이지로 옮겨 CSV 경로가 죽었고,
  받아도 **과거 시점 명단이 없어** 백테스트에 못 쓴다.
- **방법론은 공개돼 있고 여섯 요인이 전부 이 랩에 있다.** 그래서 직접 계산한다.

## 0-1. 🚨 오늘 내가 틀리게 적은 것을 먼저 바로잡는다

`PREREG-2026-09-03-DURSTYLE4.md` §7 · 그 결과 문서 §3 · `PREREG-2026-09-03-DURATION.md` §2 에
**「S&P 는 500종을 쪼개고, 러셀은 한 종목이 양쪽에 부분 편입될 수 있다」** 고 적었다.
**틀렸다.** 방법론 원문 —

> The middle 34% of market capitalization consists of stocks that have similar growth and
> value ranks. Their market capitalization is **distributed among the Style indices**…

**S&P 도 가운데 34% 를 양쪽에 쪼개 넣는다.** IVE + IVW 를 합치면 S&P 500 이 되는 이유가 그것이고,
겹침이 없는 판을 따로 만든 것이 **Pure(RPV·RPG)** 다. 계산 전 등록은 안 고치는 것이 규약이므로
**여기와 각 결과 문서에 정정을 적는다.**
⚠ 그 오류가 두 결과의 판정을 바꾸지는 않는다(둘 다 실측 기반이다) — 다만
`DURATION` §2 의 «절반으로 나누는 근거» 로 든 문장이 사실이 아니었다.

---

## 1. 여섯 요인 — 원문 그대로

| 성장 3요인 | 가치 3요인 |
|---|---|
| 3년 주당순이익 변화 ÷ 주가 | 장부가/주가 (B/P) |
| 3년 주당매출 성장률 | 순이익/주가 (E/P) |
| 모멘텀 (12개월 가격변화율) | 매출/주가 (S/P) |

⚠ 성장 1번은 «3년 EPS 성장률» 이 아니라 **«3년간 EPS 변화액을 주가로 나눈 것»** 이다
(원문: *Three-Year Change in Earnings per Share **over Price per Share***). 흔한 오독이라 적어 둔다.

## 2. 점수 — 원문 그대로

> These raw values are then standardized by dividing the difference between each stock's
> raw score and the mean of the entire set by the standard deviation of the entire set.
> A Growth Score … is computed as the **average of the standardized values** of the three
> growth factors.

- 각 요인을 **z-점수**로 표준화(전체 집합의 평균·표준편차).
- 성장점수 `SG` = 성장 3요인 z 의 **단순평균** · 가치점수 `SV` = 가치 3요인 z 의 단순평균.
- **가중치는 동일**하다(원문: *"the equal weighting approach is chosen to meet the design
  goal of simplicity"*).

⚠ **원문은 S&P Total Market Index(TMI · 약 3,000종) 를 표준화 모집단으로 쓴다.**
이 랩에는 그 유니버스가 없다. **랩의 518종을 모집단으로 쓴다** — 그러면 z 의 원점과 척도가
원문과 달라지고, 그것이 이 구현과 실제 지수의 **가장 큰 차이**다. 결과 문서에 그렇게 적는다.
🚨 **모집단을 결과 보고 바꾸지 않는다.**

## 3. 바스켓 — 원문 그대로

1. 성장순위 `RG`(점수 높을수록 1위) · 가치순위 `RV` 를 매긴다.
2. **`RG/RV` 오름차순**으로 정렬한다.
3. 위에서부터 **시가총액 33%** 까지 = **성장 바스켓**.
4. 아래에서부터 **시가총액 33%** 까지 = **가치 바스켓**.
5. 가운데 **34%** = **블렌드**.

### 3-1. 블렌드의 시총 배분 — 원문 부록 I 그대로

바스켓 중점 넷을 먼저 구한다(원문은 연 1회 리밸런스에서 계산):
`AVG`= 가치바스켓의 성장점수 평균 · `AVV`= 가치바스켓의 가치점수 평균 ·
`AGG`= 성장바스켓의 성장점수 평균 · `AGV`= 성장바스켓의 가치점수 평균.

블렌드 종목 X 에 대해
```
DG,X = |SV_X − AGV|              (SG_X ≥ AGG)
     = |AGG − SG_X|              (SV_X ≤ AGV)
     = √((SV_X−AGV)² + (AGG−SG_X)²)   그 밖
DV,X = |SG_X − AVG|              (SV_X ≥ AVV)
     = |AVV − SV_X|              (SG_X ≤ AVG)
     = √((SV_X−AVV)² + (AVG−SG_X)²)   그 밖
```
```
WV,X = DG,X / (DG,X + DV,X)      WG,X = DV,X / (DG,X + DV,X)
```
**반올림 규칙**(원문): `WV ≥ 0.8 → WV=1, WG=0` · `WG ≥ 0.8 → WG=1, WV=0`.

### 3-2. Pure — 원문 그대로

> The constituents of the Pure Value index are all stocks for which **WV = 1 and
> SV > (the mean of all parent index value scores + 0.2)**.

- Pure Value = `WV=1` 이면서 `SV > mean(SV) + 0.2`. Pure Growth 는 대칭.
- **가중은 시총이 아니라 스타일 점수**다(원문: *"index constituents are weighted by their
  Style Scores"*), 그리고 **점수는 2.0 에서 자른다**(`SV>2 → 2`).

---

## 4. 무엇을 만드나 — **분류이지 전략이 아니다**

`build/style_score.py` → `data/_style_score.json`(얼린 측정 · 커밋 금지).

월말마다 랩 518종 전부에 대해 —
`SG` · `SV` · `RG/RV` · 바스켓(성장/블렌드/가치) · `WV`·`WG` · Pure 편입 여부.

🚨 **이 등록은 전략을 만들지 않는다.** 실패 조건도 성적이 아니라 **재현 검증**이다(§5).
이 분류를 쓰는 전략은 **다음 등록의 일**이다.

## 4-1. 자료

| 요인 | 랩 계열 |
|---|---|
| 3년 EPS 변화 ÷ 주가 | `eps`(3년 전 대비) ÷ 종가 |
| 3년 주당매출 성장률 | `rev` ÷ `sh`, 3년 CAGR |
| 모멘텀 12개월 | 종가 |
| B/P · E/P · S/P | `eq`·`ni`·`rev` ÷ 시총 |

- 전부 90일 공시지연(`FUND_LAG_DAYS`). 3년 창이 없으면 원문대로 **2년 → 1년으로 낮춘다**
  (원문: *"Two-Year … used when three-year data is not available, and One-Year … when
  two-year data is not available"*).
- 여섯 요인 중 **하나라도 못 내는 종목은 그 달 후보에서 뺀다.** 그 수를 결과에 적는다.

---

## 5. 실패 조건 — 성적이 아니라 **재현**을 잰다

- **F1** 시총 배분의 합이 성립해야 한다 — 전 종목에서 `WV + WG = 1`, 그리고
  가치 지수 시총 + 성장 지수 시총 = 모지수 시총(오차 0.5% 이내). 아니면 구현이 틀린 것이다.
- **F2** 성장·가치 바스켓이 각각 **시총 33% ± 3%p** 여야 한다.
- **F3** Pure 편입 종목 수가 **실제 RPV(약 125) · RPG(약 75~80)의 ±50% 안**이어야 한다.
  ⚠ 넓게 잡은 이유 — 모집단이 TMI 가 아니라 랩 518종이라 z 척도가 달라 정확히 못 맞춘다.
  **못 맞추면 그 사실이 결과이지 실패가 아니다.** 벗어나면 «다르다» 고 적는다.
- **F4** 이 분류로 만든 «가치 절반 vs 성장 절반» 이 **IVE·IVW 수익과 상관 0.9 이상**이어야
  실제 지수를 근사한다고 말할 수 있다. 미만이면 «다른 물건» 이라고 적는다.
- **F5** 여섯 요인을 다 내는 종목이 **월 300종 미만**인 달이 20% 를 넘으면 그 사실을 첫 줄에 적는다.

### 5-1. 미리 적는 예측

- **P1** 가치점수는 `x-btp`·`x-ep`·`x-sp` 의 합성이므로 **B/M 과 순위상관 0.85 이상**일 것이다
  (오늘 듀레이션이 −0.83 이었다).
- **P2** 그럼에도 성장점수가 **모멘텀을 담고 있어** 전체 분류는 B/M 단독과 다를 것이다 —
  `RG/RV` 순위와 B/M 순위의 상관은 **0.85 미만**일 것이다.
- **P3** F4 는 통과할 것이다(IVE·IVW 와 상관 0.9 이상).

## 6. 미리 적어 두는 반론

- **표준화 모집단이 다르다**(§2) — 가장 큰 차이이고 못 고친다. 랩에 TMI 가 없다.
- **원문은 연 1회 리밸런스**(12월)인데 이 구현은 **월말마다 다시 계산**한다.
  ⚠ 그래서 이것은 «S&P 지수의 복제» 가 아니라 **«S&P 산식을 매월 적용한 분류»** 다. 그렇게 부른다.
- **IWF·주식수 조정 없음** — 원문은 유동주식 가중(IWF)을 쓰는데 랩에 그 계열이 없다. 총주식수를 쓴다.
- **가치 3요인이 서로 겹친다**(B/P·E/P·S/P 가 다 «÷주가»다) — 원문의 설계가 그렇다. 안 고친다.

## 7. 안 하는 것

- 요인·가중치·문턱(33/34/33 · 0.8 · 0.2 · 2.0)을 결과 보고 바꾸는 것. 전부 원문의 수다.
- 표준화 모집단을 바꿔 가며 RPV·RPG 종목 수를 맞추는 것 — 그것이 결과를 만드는 짓이다.
- 이 분류로 전략을 만들어 같은 등록에서 판정하는 것. **분류가 먼저다.**

---

**계산 전 커밋**: 이 문서를 먼저 커밋하고 그 해시를 결과 문서에 적는다.
