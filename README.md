# 여의도 전략 랩 — 사이트

퀀트 전략 리서치 결과를 공개하는 정적 사이트. **전략 코드·리서치는 비공개 repo(Yeouido)에 있고, 이 repo엔 배포 대시보드·탐색기 HTML과 데이터만** 있습니다.

**라이브:** https://globalkbam.github.io/yeouido-lab/

## 구성
| 파일 | 내용 |
|---|---|
| `index.html` | 랜딩 허브 |
| `dashboard.html` | 배포 대시보드 — 통합 포트폴리오 배분·리스크·강건성 |
| `explorer.html` | 전략 탐색기 — 62개 전략 인터랙티브 브라우저 |
| `data/*.json` | 배분·차트·라이브 데이터 |
| `build/refresh_live.py` | 클라우드 안전(yfinance) 갱신 스크립트 |

## 배포
GitHub Pages(branch source: `main` / root). `main`에 푸시하면 자동 재빌드.

## 데이터 갱신 (2단)
**① 라이브 자동 (매일·클라우드)** — `.github/workflows/refresh.yml` 크론이 `refresh_live.py`(yfinance, DB 불필요)로
`data/live.json`(RP 배분·벤치마크·as_of)을 갱신·커밋 → Pages 자동 재빌드. 사이트가 이를 fetch해 기준일·RP 바 반영.

**② 통합 스냅샷 (월별·수동)** — 챔피언 보유·통합 배분(Sharpe 1.42 등)은 사내 FactSet DB가 필요해 비공개 repo에서만 생성.
월말 리밸 후 비공개 repo(Yeouido)에서 산출한 JSON을 이 repo로 복사·푸시:
```bash
# (Yeouido에서) DB로 최신 배분 산출
python strategy/strategy_good/portfolio_ops.py cap50
python strategy/research_web_2026_07/dashboard_data.py cap50
# 이 repo로 복사·푸시
cp strategy/research_web_2026_07/out/combined_allocation.json  ../yeouido-lab/data/
cp strategy/research_web_2026_07/out/dashboard_chart.json      ../yeouido-lab/data/
cd ../yeouido-lab && git add data && git commit -m "chore(data): 월별 통합 배분 갱신" && git push
```

## 로컬 미리보기
```bash
python3 -m http.server 8080   # → http://localhost:8080
```
