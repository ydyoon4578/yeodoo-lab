# 여두 전략 랩

미국 대형주(S&P 500 · NASDAQ 100)를 대상으로 한 **퀀트 전략 연구실**입니다.
전략을 만들기 전에 판정 기준을 먼저 적고(사전등록), 공개 자료로 다시 돌려 보고, 통과하지 못한 전략도 기록으로 남깁니다.

사이트: <https://ydyoon4578.github.io/yeodoo-lab/>

## 무엇이 있나

| 화면 | 내용 |
|---|---|
| [전략 랩](https://ydyoon4578.github.io/yeodoo-lab/explorer.html) | 전 전략 통합 목록 — 성격(무엇을 살까 · 언제 살까 · 위험 줄이기)별 성과, 시점정합(PIT) 재측정, 생존편향 크기 |
| [스타일](https://ydyoon4578.github.io/yeodoo-lab/style.html) | 가치 · 모멘텀 · 퀄리티 · 저변동 등 스타일 포트폴리오와 대응 ETF |
| [로테이션](https://ydyoon4578.github.io/yeodoo-lab/rotation.html) | 섹터 · 스타일 · 자산 로테이션 규칙과 오늘의 신호 |
| [지표별 타이밍](https://ydyoon4578.github.io/yeodoo-lab/signals.html) | 테크니컬 신호 32개의 과거 성적과 오늘 발동 종목 |
| [거장 포트폴리오](https://ydyoon4578.github.io/yeodoo-lab/guru.html) | SEC 13F 원문 기반 보유·매매 (45일 지연 · 분기말 · 롱온리) |
| [시장 국면](https://ydyoon4578.github.io/yeodoo-lab/regime.html) · [금리](https://ydyoon4578.github.io/yeodoo-lab/rates.html) · [경제지표](https://ydyoon4578.github.io/yeodoo-lab/macro.html) | 국면 판정과 거시 지표 (서술 통계, 예측 아님) |
| [방법론](https://ydyoon4578.github.io/yeodoo-lab/method.html) | 백테스트 규약 — 체결 시점 · 비용 · 다중검정 · 판정 기준 |

## 연구 방식

- **사전등록**: `build/PREREG-*.md` — 계산 전에 가설 · 규칙 · 판정 기준을 적고 커밋한다. 결과는 같은 이름의 `-RESULT.md`.
- **감사**: `build/AUDIT-*.md` — 통과한 전략도 선견 · 생존편향 · 자료 결함을 다시 잰다.
- **자료 사실**: `build/DATA-FACTS.md` — 규칙을 만들기 전에 알아야 하는 자료의 함정.
- 기각된 전략도 지우지 않는다(다중검정 분모).

## 자료

공개 자료만 씁니다 — yfinance(가격) · SEC EDGAR(재무 · 13F) · FRED(거시) · 위키백과 과거 리비전(지수 편입 이력) · CFTC(COT) · 공개 데이터셋(상장폐지 종목 가격).
대부분의 자료는 GitHub Actions 가 매일 · 매주 다시 굽습니다(`.github/workflows/`).

## 알림

교육 · 연구 목적의 기록이며 투자 권유가 아닙니다. 과거 성과는 미래 수익을 보장하지 않습니다.
