# -*- coding: utf-8 -*-
"""build/q_netper.py — 배치 Q · Q08 MATH-EG30-NETSTEP(EG30 + 상관망 주변부 단계 · 부류 B · 칸 B2 ½) ·
Q09 MATH-NETPERIPH20(상관망 주변부 20 · Pozzi·Di Matteo·Aste 2013 원문 규칙 · 측정만 · Q08 의 팔).

근본 이유: EG30 은 급등 구간에서 이기고 급락 구간에서 진다(급락 0/6 · 바스켓 베타 1.22). 손실의 원인은 Eg 신호가 아니라 바스켓이
  상관망의 중심 — 같은 요인으로 묶인 대형 성장주 군집 — 에 몰려 있다는 구조다. 공통 충격과 쏠림 매매는 상관망의 허브를 타고 퍼지고
  폭락 때 상관이 가장 크게 뛰는 곳도 거기다(Pozzi 2013). 주변부 종목은 자기만의 수익 동인에 묶여 충격 경로에서 떨어져 있다
  (Onnela 2003: 최소위험 포트폴리오는 MST 바깥쪽). 그래서 Eg 후보 60 가운데 망의 중심에서 먼 30 을 고른다 — 무엇을 믿느냐(Eg)는 그대로,
  어느 자리에 서느냐만 바꾼다. 판정은 베타 차이를 헤지한 하락월 차이(Δβ)로 하고 단순 저상관 30(C3)과 P 섞기 위약을 이겨야 한다
  — 효과가 «베타 낮추기» 나 «저상관 고르기» 가 아니라 망의 위치에서 나오는지만 남긴다.

규칙(카드 원문 scratchpad/qbatch_final.md # Q08 · # Q09 — 숫자는 모두 카드에 적힌 것):
  망(공통): 편입 월말 t(그달 마지막 거래일) · t−250..t 모든 날 가격(연속 4일 이하 빈칸은 앞값) · 일간 수익 250개 ·
    s = t−125..t 마다 끝이 s 인 125 수익의 지수가중 피어슨 상관(w_k = w0·exp((k−125)/125) · k = 1..125 · k = 125 가 s · Σw = 1)
    → 126 행렬 평균 R^a → R̄_ij = ½R^a_ij + ½ρ̄(i ≠ j · ρ̄ = 창마다 비대각 평균의 평균) · R̄_ii = 1.
    MST(scipy.sparse.csgraph.minimum_spanning_tree) · 거리 d = √(2(1 − R̄)).
    하이브리드 P = X + Y · X = (cD^w + cD^u + cBC^w + cBC^u − 4)/(4(N−1)) · Y = (cE^w + cE^u + cC^w + cC^u + cEC^w + cEC^u − 6)/(6(N−1))
    · 중간순위(1 = 가장 중심 · D · BC · EC 는 내림 · E · C(멀기) 는 오름) · 세기 · EC 가중 = 1 + R̄ · BC · E · C 거리 = d · 무가중 = 홉.
    P 가 크면 주변부.
  Q08: P60 = EG_BASE Eg 순위 상위 60 · 망 = World.universe(m, 'union', ex_fin=False) 중 251일 가격이 선 전부 · 망에 없는 후보 = 망 P 중앙값 ·
    P 큰 30(동률은 Eg 높은 쪽) · 시총 비례 20% 상한(EG_BASE 와 같은 재배분) · 분기(2016-08 + 분기말) · 흘러감 · 10bp · 펀드 90/10.
    G4: C3 = P60 중 행 평균 R̄ 낮은 30(같은 가중) — 하락월 평균 Δβ(V1 − C3) > 0 · 위약 = 60 후보 사이에서 P 무작위 순열 NPERM 번
    (씨앗 SEED + i · 30 · 같은 가중) — 참 하락월 Δβ(V1 − V0) ≥ 위약 95 백분위.
    측정만: 후보 45 · 후보 90 · C3b(P60 중 FP 베타 낮은 30) · Q09 · PMFG(networkx 없음 → «돌리지 않음»).
  Q09: World.universe(m, 'spx', ex_fin=False) − 부동산(pit_gics_sectors 의 max(m, 2016-12) 분류) · 251일 가격 ·
    S_i = 250 수익 평균/표준편차 상위 ceil(N/2)(동률은 큰 시총) → 그 안에서 망 · P 큰 20(동률은 행 평균 R̄ 낮은 쪽) · 각 5% · 흘러감 · 분기 · 10bp.
    대조(모두 측정만): K1 가장 중심 20 · K2 행 평균 R̄ 낮은 20 · K3 걸러진 전부 균등 · K4 무작위 20(NPERM) · K5 hedge_ctrl(evaluate).
  기록(구성만 · 선택에 안 쓴다): ec_method_check(EC 순위 방법이 목표를 움직였나) · delist_frozen(코어가 마지막 가격에 묶은 보유 이름) ·
    issuer_multi / v0_issuer_multi(CIK 없는 이중클래스 LBTYA/LBTYK 를 함께 든 편입 · 합친 비중) ·
    dup_tickers / dup_both / v0_dup_both(망 R^a ≥ 0.95 짝 — 대부분 다른 발행사의 쌍둥이 업종 짝 · 같은 발행사는 LBTYA/LBTYK 하나).
출처: Pozzi F., Di Matteo T., Aste T.(2013) «Spread of risk across financial markets: better to invest in the peripheries» Scientific Reports 3:1665
  (식 1 · 방법 절 — 카드가 Europe PMC 원문에서 옮긴 식) · Onnela J.-P. 외(2003) Physical Review E 68, 056110 ·
  Brandes U.(2001) «A faster algorithm for betweenness centrality» J. Mathematical Sociology 25(2).
  networkx 가 없어서 MST 는 scipy csgraph · 중심성(세기 · Brandes 사이 · 이심률 · 멀기 · 고유벡터)은 여기서 짠다 — 별 · 경로 · 작은 알려진
  그래프 단위 시험(selftest)이 유일한 방어선이다.

🚨 이 모듈은 selftest · dry 에서 규칙 · 대조 · 팔 · 위약의 수익을 계산하거나 찍지 않는다. run() 은 한 번 굽기에서만 부른다.

  python build/q_netper.py            # selftest(합성 자료만)
  python build/q_netper.py --dry      # 랩 자료로 구성만
  python build/q_netper.py --smoke    # 눈가린 연기 시험(NPERM 3 · 수익 숫자는 버린다)
"""
from __future__ import annotations
import hashlib, heapq, io, json, math, os, sys, time
from collections import deque

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import minimum_spanning_tree, shortest_path

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qbatch_core as Q              # noqa: E402

CARDS = {"Q08": {"cls": "B", "slot": "B2"},
         "Q09": {"cls": "M", "slot": None}}
NPERM = 1000                         # Q08 위약 · Q09 K4 뽑기 수(카드) — 연기 시험에서 작게 덮어쓴다

# ── 카드 상수 ─────────────────────────────────────────────────────────────
WIN = 250                            # Δt — 수익 250개(가격 251일)
TAU, THETA = 125, 125                # 지수가중 창 · 감쇠
NAVG = 126                           # s = t−125..t 평균 창 수
SHRINK = 0.5                         # ½ R^a + ½ ρ̄
GAP = 4                              # 앞값으로 채우는 연속 빈칸 최대
POOL, KEEP, CAP = 60, 30, 0.20       # Q08 후보 · 바스켓 · 발행사 상한(EG_BASE)
POOL_ARMS = (45, 90)                 # Q08 측정만 이웃
M20, W20 = 20, 0.05                  # Q09 보유 수 · 비중
REIT, REIT_FROM = "Real Estate", "2016-12"
COST20 = 0.0020                      # 20bp 판
# ── 구현 상수(카드가 정하지 않은 수치 잡음 한계 — 결과를 바꾸지 않는 크기) ──
TIE_REL = 1e-10                      # 중간순위 동률(부동소수 잡음)
EC_TOL, EC_MAXIT = 1e-14, 1_000_000  # 고유벡터 거듭제곱 수렴(최대 변화) · 최대 걸음
DIJ_TOL = 1e-12                      # 가중 Dijkstra 에서 같은 길이 판정(상대)
DUP_RA = 0.95                        # 기록만(선택에 안 쓴다) — R^a 이 이만큼 높은 망 안 짝(거의 복제 · 같은 발행사는 LBTYA/LBTYK 뿐)
ISSUER_NOCIK = {"LBTYA": "LBTY", "LBTYB": "LBTY", "LBTYK": "LBTY"}   # 기록만 — CIK 가 없어 World.universe 가 못 합치는 이중클래스(eg30plus.SEC_MANUAL)

INTERP = [
    "일간 수익 = 단순수익 p_t/p_{t−1} − 1(카드 'returns' · Q09 원판 'daily simple returns') · 채운 날의 수익은 0.",
    "빈칸 채움은 창 앞 4일 가격까지 씨앗으로 쓴다 — 연속 5일 이상 빈칸이 창 t−250..t 에 걸리면 탈락(251일 미달).",
    "지수가중 w_k 는 평균 · 분산 · 공분산에 모두 같게 · k = 125 가 그 창의 끝 s(가장 최근) · 상관은 창마다 대칭화 · 대각 1.",
    "ρ̄ = 126 창 각각의 비대각 평균의 평균(= R^a 비대각 평균) · R̄ 은 대칭 · 대각 1.",
    "MST 입력 = d 의 위 삼각(0 = 간선 없음 · 비대각 d > 0 단언) · 마디 순서 = 가격 키 정렬(결정적).",
    "사이 중심성 = Brandes(2001) · 무방향 · 순서 없는 쌍(합 / 2) · 가중 = 길이 d(같은 길이는 상대 1e-12) · 무가중 = 홉 — 나무에서는 경로가 하나라 둘이 같다.",
    "이심률 · 멀기 = csgraph.shortest_path(가중 d · 무가중 홉) · 멀기 C = 다른 N−1 마디까지 평균 거리.",
    "고유벡터 중심성 = (A + I) 거듭제곱(나무는 이분 그래프라 A 만으로는 진동한다 · 같은 고유벡터) · 최대 변화 < 1e-14 · 조밀 eigh 로 검산 — 수렴 못 하면 eigh 벡터를 쓰고 표식.",
    "MST 는 지름이 27~49 홉이라 허브에서 먼 마디의 EC 는 1e-12 아래로 떨어진다 — 거듭제곱 · eigh 의 절대 오차(~1e-11)가 그 순위를 잡음으로 만든다. "
    "그래서 순위에는 같은 고유방정식을 나무 위에서 푼 tree_perron(비 x_v/x_부모 = w/(λ − Σ w ρ) · λ = 거듭제곱 벡터의 레일리 몫 · 뿌리 = 가장 큰 항목)을 쓴다 "
    "— 거듭제곱 벡터와 절대 차 < 1e-9 를 단언하고 항목마다 상대 정확하다(selftest: 소수 60자리 기준과 대조). "
    "카드 문자 그대로(거듭제곱 벡터 순위) 판과의 차이는 log['ec_method_check'] 에 적는다 — 목표 해시가 같은가(V1 · 후보 45/90 · Q09 rule · K1) · 움직인 P 키 · 위약 값 집합이 달라진 편입.",
    "중간순위 동률 = 상대 1e-10 안의 값(사슬) — 나무의 무가중 척도(차수 · 사이 · 홉 이심률 · 홉 멀기 · 잎의 EC)는 정확한 동률이 많다.",
    "P 는 정수 키 3·Σ(2c)_X + 2·Σ(2c)_Y − 48 = 24(N−1)·P 로 정확히 비교한다(부동소수로 동률이 갈리지 않게).",
    "Q08 망에 없는 후보(251일 미달)는 망 P 중앙값 · C3 의 행 평균 R̄ 도 같은 식(망 중앙값) — 카드는 P 의 대체만 적었다.",
    "행 평균 R̄ = 그 망(Q08 union 전체 · Q09 걸러진 풀)에서 자기를 뺀 N−1 평균 — Q08 C3 는 P60 안에서 고르되 행 평균은 union 망 전체 기준(P60 안 평균이 아니다 · P 와 같은 망).",
    "Q08 의 C3 · C3b · 후보 45/90 · 위약의 동률은 Eg 높은 쪽(카드 (5) 규칙을 옮김) · Eg 순위 = EG_BASE score 목록 순서(점수 → 티커).",
    "C3b 의 FP 베타가 없으면 eg30plus.betas_for 의 업종 중앙값(랩 B1 과 같은 대체).",
    "Q08 위약: 뽑기 i 마다 np.random.default_rng(SEED + i) 한 줄기로 편입 순서대로 60 후보의 P 를 순열 · 통계 = 하락월(39) 평균 Δβ(위약 − V0) · G4 = 참 Δβ(V1 − V0) ≥ numpy percentile(draws, 95)(선형 보간).",
    "Δβ 의 β̂ = qbatch_core.evaluate 의 sleeve_beta(120개월 OLS) · 하락월 = ctx.dmask(39).",
    "Q09 부동산 제외 = World.sector(t, k, max(m, 2016-12)) == 'Real Estate'(그달 표 → 가까운 달 → 오늘 · 랩 표준 조회) — 2016-08 · 2016-09 편입은 카드 선언대로 2016-12 분류.",
    "Q09 S_i 의 표준편차는 ddof 1(모두 250 수익이라 순위는 같다) · 동률 큰 시총 → 가격 키.",
    "Q09 K1 동률 = 행 평균 R̄ 높은 쪽(STEP 5 의 거울) · K2 동률 = 큰 시총 · K4 = 편입마다 걸러진 풀에서 비복원 균등 20(씨앗 SEED + i · 편입 순서대로 한 줄기) · 각 5%.",
    "Q09 K4 위약 통계 = 전 월 평균 X 와 하락월 평균 H(H = X − 0.1(β̂ − 1)(SPYTR − rf)) — 카드가 대조를 두 통계로 보고하라 했다.",
    "Q09 상장폐지 대금: 코어 stock_path(qg_lab.World.sleeve)는 마지막 가격에 묶어 두고 rf 이자를 붙이지 않는다 — 카드의 'cash at rf' 와 다르다(코어를 고치지 않는다 · 보고서에 적음). "
    "모든 종목 슬리브(Q08 포함 · V0 도)가 같은 동작 · 해당 사건(보유 이름 · 마지막 가격일 · 묶인 날 수)은 log['delist_frozen'] 에 적는다.",
    "Q09 가 20 종이 안 되면(예상 없음) 있는 이름 각 5% · 나머지 현금(rf).",
    "PMFG 팔(Q08 · Q09) — networkx 없음 → 돌리지 않음(사전등록 §2(i)).",
    "F0: 두 카드 모두 카드에 없다 — Q08 은 V1 이 V0 와 다른 편입이 하나라도 있는가 · Q09 는 모든 편입에서 걸러진 풀 ≥ 20 인가.",
    "한 발행사 두 마디: World.universe 는 CIK 로 이중클래스를 합치는데 Liberty Global(LBTYA/LBTYK)은 CIK 가 없어(SEC_MANUAL 로만 업종) 2016-08..2020-09 union 망에 "
    "두 마디로 들어간다(R^a 0.97~0.99 · 한쪽이 다른 쪽의 거의 복제 잎이 되어 그 둘레의 차수 · BC · P 순위가 조금 비틀린다). EG_BASE 적격을 카드가 물려받은 것이라 규칙은 바꾸지 않는다 "
    "— V0 도 같은 동작(두 클래스를 함께 든 편입이 있다). 두 클래스를 함께 든 편입과 합친 비중은 변형별 log['issuer_multi'] · V0 는 log['v0_issuer_multi'] 에 적는다. "
    "따로 망 안 R^a ≥ 0.95 짝(대부분 다른 발행사 — 은행 · 철도 · 카드 · 항공 쌍둥이)은 편입마다 dup_tickers · 변형별 dup_both(둘 다 든 편입 · 합친 비중) · V0 는 v0_dup_both 에 적는다(모두 기록만 · 선택에 안 쓴다).",
    "목표 이름은 모두 편입일 가격이 선다(단언 — 코어 sleeve 가 가격 없는 목표를 조용히 현금으로 돌리지 않게) · 후보 · 풀은 World.universe 의 시총(편입일 가격 > 0) 조건을 이미 통과한다.",
]


# ── 가격 창 · 상관 ────────────────────────────────────────────────────────
def ffill_limited(P, limit=GAP):
    """행마다 앞값 채움 — 연속 빈칸 limit 개까지만(더 긴 빈칸의 나머지는 NaN). 0 이하 가격은 빈칸."""
    P = np.array(P, float)
    with np.errstate(invalid="ignore"):
        P = np.where(np.isfinite(P) & (P > 0), P, np.nan)
    out = P.copy()
    n, T = P.shape
    last = np.full(n, np.nan)
    run = np.zeros(n, int)
    for j in range(T):
        col = P[:, j]
        good = np.isfinite(col)
        run = np.where(good, 0, run + 1)
        fill = ~good & (run <= limit) & np.isfinite(last)
        out[fill, j] = last[fill]
        last = np.where(good, col, last)
    return out


def window_px(Wd, keys, i):
    """t = i 로 끝나는 251일 가격(빈칸 채움 뒤) · 모든 날이 선 행. 🚨 i 뒤 자리는 읽지 않는다."""
    a = i - WIN - GAP
    assert a >= 0, "가격 창이 격자 앞으로 나간다"
    M = np.vstack([np.asarray(Wd.PX[k][a:i + 1], float) for k in keys]) if keys else np.zeros((0, WIN + GAP + 1))
    assert M.shape[1] == WIN + GAP + 1
    F = ffill_limited(M)[:, GAP:]
    assert F.shape[1] == WIN + 1
    ok = np.all(np.isfinite(F), axis=1)
    return F, ok


def ew_weights():
    k = np.arange(1, TAU + 1)
    w = np.exp((k - TAU) / THETA)
    return w / w.sum()


def rbar(Rt):
    """Rt: N × 250 일간 수익(시간 오름) → (R̄, R^a, ρ̄). 창 s(0..125) = 열 s..s+124 — 끝 열 s+124 가 날 t−125+s."""
    N, T = Rt.shape
    assert T == WIN and TAU + NAVG - 1 == WIN and N >= 3
    w = ew_weights()
    S = np.zeros((N, N))
    off = []
    for s in range(NAVG):
        Z = Rt[:, s:s + TAU]
        mu = Z @ w
        Zc = Z - mu[:, None]
        C = (Zc * w) @ Zc.T
        sd = np.sqrt(np.clip(np.diag(C), 0.0, None))
        assert np.all(sd > 0), "분산 0 인 이름이 창에 있다"
        Cr = C / np.outer(sd, sd)
        Cr = 0.5 * (Cr + Cr.T)
        np.fill_diagonal(Cr, 1.0)
        S += Cr
        off.append((Cr.sum() - N) / (N * (N - 1)))
    Ra = S / NAVG
    rho = float(np.mean(off))
    Rb = SHRINK * Ra + (1.0 - SHRINK) * rho
    np.fill_diagonal(Rb, 1.0)
    return Rb, Ra, rho


# ── 그래프 · 중심성(networkx 없이) ───────────────────────────────────────
def mst_edges(Rb):
    """d = √(2(1 − R̄)) 위 MST → (간선 [(a, b)] a < b 정렬, d)."""
    N = len(Rb)
    d = np.sqrt(np.clip(2.0 * (1.0 - Rb), 0.0, None))
    np.fill_diagonal(d, 0.0)
    iu = np.triu_indices(N, 1)
    assert np.all(d[iu] > 0), "거리 0 인 짝 — MST 입력에서 간선이 사라진다"
    T = minimum_spanning_tree(np.triu(d, 1)).tocoo()
    e = sorted((int(min(a, b)), int(max(a, b))) for a, b in zip(T.row.tolist(), T.col.tolist()))
    assert len(e) == N - 1 and len(set(e)) == N - 1, "MST 간선 수가 N − 1 이 아니다"
    return e, d


def sym_csr(n, edges, val):
    ea = np.asarray(edges, int).reshape(-1, 2)
    v = np.asarray(val, float)
    return csr_matrix((np.r_[v, v], (np.r_[ea[:, 0], ea[:, 1]], np.r_[ea[:, 1], ea[:, 0]])), shape=(n, n))


def brandes(n, edges, length=None):
    """Brandes(2001) 사이 중심성 — 무방향 · 순서 없는 쌍(합 / 2). length None = 홉(BFS) · 아니면 Dijkstra(같은 길이 = 상대 DIJ_TOL)."""
    adj = [[] for _ in range(n)]
    for j, (a, b) in enumerate(edges):
        l = 1.0 if length is None else float(length[j])
        assert l > 0
        adj[a].append((b, l))
        adj[b].append((a, l))
    bc = np.zeros(n)
    for s in range(n):
        S, P = [], [[] for _ in range(n)]
        sig = [0.0] * n
        sig[s] = 1.0
        if length is None:
            dist = [-1] * n
            dist[s] = 0
            q = deque([s])
            while q:
                v = q.popleft()
                S.append(v)
                for u, _ in adj[v]:
                    if dist[u] < 0:
                        dist[u] = dist[v] + 1
                        q.append(u)
                    if dist[u] == dist[v] + 1:
                        sig[u] += sig[v]
                        P[u].append(v)
        else:
            dist = [math.inf] * n
            dist[s] = 0.0
            done = [False] * n
            h = [(0.0, s)]
            while h:
                dv, v = heapq.heappop(h)
                if done[v]:
                    continue
                done[v] = True
                S.append(v)
                for u, l in adj[v]:
                    if done[u]:
                        continue
                    nd = dv + l
                    tol = DIJ_TOL * max(1.0, nd)
                    if nd < dist[u] - tol:
                        dist[u] = nd
                        sig[u] = sig[v]
                        P[u] = [v]
                        heapq.heappush(h, (nd, u))
                    elif abs(nd - dist[u]) <= tol:
                        sig[u] += sig[v]
                        P[u].append(v)
        dl = [0.0] * n
        while S:
            u = S.pop()
            for v in P[u]:
                dl[v] += sig[v] / sig[u] * (1.0 + dl[u])
            if u != s:
                bc[u] += dl[u]
    return bc / 2.0


def tree_bc(n, edges):
    """나무 검산 — v 를 빼면 갈라지는 조각 크기 c 로 BC(v) = ((n−1)² − Σc²)/2."""
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    par, order = [-1] * n, []
    seen = [False] * n
    st = [0]
    seen[0] = True
    while st:
        v = st.pop()
        order.append(v)
        for u in adj[v]:
            if not seen[u]:
                seen[u] = True
                par[u] = v
                st.append(u)
    assert len(order) == n, "나무가 이어져 있지 않다"
    size = [1] * n
    for v in reversed(order):
        if par[v] >= 0:
            size[par[v]] += size[v]
    out = np.zeros(n)
    for v in range(n):
        cs = [size[u] for u in adj[v] if par[u] == v]
        cs.append(n - size[v])
        out[v] = ((n - 1) ** 2 - sum(c * c for c in cs if c > 0)) / 2.0
    return out


def distances(n, edges, length):
    A = sym_csr(n, edges, length)
    Dw = shortest_path(A, method="D", directed=False)
    Du = shortest_path(A, method="D", directed=False, unweighted=True)
    assert np.all(np.isfinite(Dw)) and np.all(np.isfinite(Du)), "그래프가 이어져 있지 않다"
    return Dw, Du


def eig_centrality(n, edges, wt):
    """고유벡터 중심성 — (A + I) 거듭제곱(단위 L2 · 양수) · 조밀 eigh 검산. → (x, 기록)."""
    A = sym_csr(n, edges, wt)
    x = np.full(n, 1.0 / math.sqrt(n))
    conv, it = False, 0
    for it in range(1, EC_MAXIT + 1):
        y = A @ x + x
        y = y / np.linalg.norm(y)
        if float(np.max(np.abs(y - x))) < EC_TOL:
            x, conv = y, True
            break
        x = y
    ev, V = np.linalg.eigh(A.toarray())
    v = V[:, -1]
    v = v * (1.0 if v.sum() >= 0 else -1.0)
    v = v / np.linalg.norm(v)
    diff = float(np.max(np.abs(x - v)))
    rec = {"it": it, "conv": conv, "eigh_diff": diff, "lam1": float(ev[-1])}
    if not conv:
        x = np.abs(v)
        rec["fallback"] = "eigh"
    return x, rec


def tree_perron(n, edges, wt, lam, root):
    """나무의 페론 벡터를 항목마다 상대 정확하게 — 비 ρ_v = x_v/x_부모 = w_(v,부모)/(λ − Σ_자식 w ρ_자식) 를 잎에서 뿌리로,
    x 를 뿌리에서 잎으로(로그로 곱한다). 고유방정식 λx_v = Σ_이웃 w x 를 그대로 푼 것이라 벡터는 거듭제곱과 같고,
    뿌리에서 먼 작은 항목(조밀 풀이의 절대 오차 바닥 아래)까지 순위가 선다. → (x 단위 L2, 뿌리 잔차 λ − Σ w ρ)."""
    adj = [[] for _ in range(n)]
    for (a, b), w in zip(edges, wt):
        adj[a].append((b, float(w)))
        adj[b].append((a, float(w)))
    par, pw = [-1] * n, [0.0] * n
    seen = [False] * n
    seen[root] = True
    order, q = [root], deque([root])
    while q:
        v = q.popleft()
        for u, w in adj[v]:
            if not seen[u]:
                seen[u] = True
                par[u], pw[u] = v, w
                order.append(u)
                q.append(u)
    assert len(order) == n and len(edges) == n - 1, "나무가 아니다"
    rho = [0.0] * n
    for v in reversed(order):
        if v == root:
            continue
        den = lam - math.fsum(w * rho[u] for u, w in adj[v] if par[u] == v)
        assert den > 0, "페론 비의 분모가 0 이하 — λ 가 가장 큰 고유값이 아니다"
        rho[v] = pw[v] / den
    res = lam - math.fsum(w * rho[u] for u, w in adj[root] if par[u] == root)
    lx = [0.0] * n
    for v in order[1:]:
        lx[v] = lx[par[v]] + math.log(rho[v])
    lx = np.array(lx)
    x = np.exp(lx - lx.max())
    return x / np.linalg.norm(x), float(res)


def ec_tree(n, edges, wt):
    """나무 EC — 거듭제곱(A + I)으로 λ(레일리 몫)와 뿌리(가장 큰 항목)를 잡고 tree_perron 으로 항목별 상대 정확 벡터.
    두 벡터의 절대 차는 기록 · 단언(1e-9)."""
    x_pi, rec = eig_centrality(n, edges, wt)
    A = sym_csr(n, edges, wt)
    lam = float(x_pi @ (A @ x_pi) / (x_pi @ x_pi))
    x, res = tree_perron(n, edges, wt, lam, int(np.argmax(x_pi)))
    rec.update({"lam_rq": lam, "root_res": res, "tree_pi_diff": float(np.max(np.abs(x - x_pi))),
                "min_entry": float(x.min()), "method": "tree_perron",
                "rank_moves": int(np.sum(midrank2(x, True) != midrank2(x_pi, True)))})
    assert rec["tree_pi_diff"] < 1e-9, "나무 페론 벡터가 거듭제곱과 다르다(%.2e)" % rec["tree_pi_diff"]
    rec["x_pi"] = x_pi                                              # 카드 문자 그대로(거듭제곱) 판 — 방법 차이 기록용(순위에는 안 쓴다)
    return x, rec


def _tie(x, y):
    return abs(x - y) <= TIE_REL * max(abs(x), abs(y))


def midrank2(v, descending):
    """중간순위 × 2(정수) — 1 = 가장 중심(descending 이면 큰 값이 1). 같은 값(상대 TIE_REL · 사슬)은 평균 순위."""
    v = np.asarray(v, float)
    n = len(v)
    key = -v if descending else v
    o = np.argsort(key, kind="stable")
    r2 = np.empty(n, np.int64)
    a = 0
    while a < n:
        b = a
        while b + 1 < n and _tie(float(key[o[b + 1]]), float(key[o[b]])):
            b += 1
        r2[o[a:b + 1]] = (a + 1) + (b + 1)
        a = b + 1
    return r2


MEASURES = (("D_w", True), ("D_u", True), ("BC_w", True), ("BC_u", True),
            ("E_w", False), ("E_u", False), ("C_w", False), ("C_u", False), ("EC_w", True), ("EC_u", True))


def graph_measures(n, edges, length, wt):
    """10 척도(가중 · 무가중) — 세기 = Σ(1 + R̄) · BC · E · C 는 거리 · EC 는 1 + R̄."""
    ea = np.asarray(edges, int).reshape(-1, 2)
    wt = np.asarray(wt, float)
    deg_u = np.bincount(ea.ravel(), minlength=n).astype(float)
    deg_w = np.bincount(ea[:, 0], weights=wt, minlength=n) + np.bincount(ea[:, 1], weights=wt, minlength=n)
    bc_w, bc_u = brandes(n, edges, length), brandes(n, edges, None)
    Dw, Du = distances(n, edges, length)
    ecf = ec_tree if len(ea) == n - 1 else eig_centrality          # 나무면 항목별 상대 정확 벡터(같은 고유벡터)
    ec_w, rw = ecf(n, edges, wt)
    ec_u, ru = ecf(n, edges, np.ones(len(ea)))
    M = {"D_w": deg_w, "D_u": deg_u, "BC_w": bc_w, "BC_u": bc_u, "E_w": Dw.max(1), "E_u": Du.max(1),
         "C_w": Dw.sum(1) / (n - 1), "C_u": Du.sum(1) / (n - 1), "EC_w": ec_w, "EC_u": ec_u}
    # 카드 문자 그대로의 EC(거듭제곱 벡터)로 바꾼 척도 — 방법 차이가 순위 · 목표를 움직이는지 기록만 한다
    M_pi = dict(M, EC_w=rw.get("x_pi", ec_w), EC_u=ru.get("x_pi", ec_u))
    return M, {"ec_w": rw, "ec_u": ru, "diam_hops": int(Du.max()), "Du": Du, "M_pi": M_pi}


def hybrid_from(M, n):
    """척도 → 중간순위 → 정수 키 Pint = 24(N−1)·P · P."""
    r = {k: midrank2(M[k], desc) for k, desc in MEASURES}
    S4 = r["D_w"] + r["D_u"] + r["BC_w"] + r["BC_u"]
    S6 = r["E_w"] + r["E_u"] + r["C_w"] + r["C_u"] + r["EC_w"] + r["EC_u"]
    Pint = 3 * S4 + 2 * S6 - 48
    return Pint, Pint / (24.0 * (n - 1)), r


def hybrid(Rb):
    """R̄ → MST → 10 척도 → P. 나무 검산(쌍 공식 BC)도 한다."""
    N = len(Rb)
    edges, d = mst_edges(Rb)
    ea = np.asarray(edges, int)
    L = d[ea[:, 0], ea[:, 1]]
    Wt = 1.0 + Rb[ea[:, 0], ea[:, 1]]
    M, info = graph_measures(N, edges, L, Wt)
    Pint, P, r = hybrid_from(M, N)
    Pint_pi = hybrid_from(info["M_pi"], N)[0]
    tb = tree_bc(N, edges)
    ties = {k: int(N - len(set(r[k].tolist()))) for k, _ in MEASURES}
    rec = {"N": N, "tree_len": float(L.sum()), "max_deg": int(M["D_u"].max()), "n_leaf": int((M["D_u"] == 1).sum()),
           "diam_hops": info["diam_hops"], "bc_tree_diff": float(max(np.abs(M["BC_w"] - tb).max(), np.abs(M["BC_u"] - tb).max())),
           "ec_w_it": info["ec_w"]["it"], "ec_u_it": info["ec_u"]["it"], "ec_conv": bool(info["ec_w"]["conv"] and info["ec_u"]["conv"]),
           "ec_eigh_diff": max(info["ec_w"]["eigh_diff"], info["ec_u"]["eigh_diff"]),
           "ec_tree_pi_diff": max(info["ec_w"].get("tree_pi_diff", 0.0), info["ec_u"].get("tree_pi_diff", 0.0)),
           "ec_root_res": max(abs(info["ec_w"].get("root_res", 0.0)), abs(info["ec_u"].get("root_res", 0.0))),
           "ec_min_entry": min(info["ec_w"].get("min_entry", 1.0), info["ec_u"].get("min_entry", 1.0)),
           "ec_rank_moves": [info["ec_w"].get("rank_moves"), info["ec_u"].get("rank_moves")],
           "ec_fallback": [k for k in ("ec_w", "ec_u") if info[k].get("fallback")], "tie_lost": ties,
           "P_range": [float(P.min()), float(P.max())], "P_key_moves_pi": int(np.sum(Pint != Pint_pi))}
    rowmean = (Rb.sum(1) - 1.0) / (N - 1)
    return {"Pint": Pint, "Pint_pi": Pint_pi, "P": P, "rowmean": rowmean, "edges": edges, "rec": rec}


# ── 편입 준비 ─────────────────────────────────────────────────────────────
_NET = {}


def _assert_ltd(Wd, m):
    i = Wd.me[m]
    D = Wd.dates
    assert D[i][:7] == m and (i + 1 >= len(D) or D[i + 1][:7] > m), "편입일이 %s 의 마지막 거래일이 아니다" % m
    return i


def formations(ctx):
    import eg30plus as E
    fm = E.formations(ctx.Wd)
    assert fm == Q.quarterly_forms(), "World 편입월이 qbatch_core.quarterly_forms 와 다르다"
    return fm


def network(Wd, m, pairs):
    """pairs [(t, k)](가격 키 정렬) 중 251일이 선 이름으로 망 → (망 키, 수익, R̄ 정보, 하이브리드)."""
    i = _assert_ltd(Wd, m)
    keys = [k for _, k in pairs]
    F, ok = window_px(Wd, keys, i)
    idx = np.flatnonzero(ok)
    nk = [keys[j] for j in idx]
    Fn = F[idx]
    Rt = Fn[:, 1:] / Fn[:, :-1] - 1.0
    return nk, Rt


def near_dups(Ra, keys):
    """R^a ≥ DUP_RA 인 망 안 짝(기록만 · 선택에 안 쓴다) → [[키 a, 키 b, R^a]](키 정렬 순)."""
    iu = np.triu_indices(len(keys), 1)
    v = Ra[iu]
    return [[keys[int(iu[0][j])], keys[int(iu[1][j])], round(float(v[j]), 4)] for j in np.flatnonzero(v >= DUP_RA)]


def dup_held(pairs, held, tick, w=None):
    """두 쪽을 다 든 짝 → [[티커 a, 티커 b]](w 가 있으면 두 비중 합을 덧붙인다)."""
    return [[tick.get(a, a), tick.get(b, b)] + ([round(float(w[a] + w[b]), 6)] if w is not None else [])
            for a, b, _ in pairs if a in held and b in held]


def prep_q08(ctx, m):
    """Q08 편입 m — m 월말 종가까지만(단언). 망 · P60 · 선택 재료."""
    ck = ("Q08", id(ctx.Wd), m)
    if ck in _NET:
        return _NET[ck]
    import eg30plus as E
    Wd = ctx.Wd
    i = _assert_ltd(Wd, m)
    U = sorted(Wd.universe(m, "union", False), key=lambda x: x[1])
    assert len({k for _, k in U}) == len(U), "union 가격 키가 겹친다(%s)" % m
    tick = {k: t for t, k in U}
    nk, Rt = network(Wd, m, U)
    Rb, Ra, rho = rbar(Rt)
    H = hybrid(Rb)
    pos = {k: j for j, k in enumerate(nk)}
    sc = Wd.score(dict(E.EG_BASE, index="union"), m)
    top = [(t, k) for (t, k), _ in sc]
    assert len(top) >= max(POOL_ARMS + (POOL,)), "Eg 후보가 %d 보다 적다(%s)" % (max(POOL_ARMS), m)
    t30 = {k for _, k in top[:KEEP]}
    assert set(ctx.V0_targets[m]["w"]) == t30, "V0 목표가 같은 순위의 상위 30 이 아니다(%s)" % m
    cand = [k for _, k in top[:max(POOL_ARMS + (POOL,))]]
    ctick = {k: t for t, k in top}
    egr = {k: r for r, (_, k) in enumerate(top)}
    def keys_of(Pint):
        key2 = 2 * Pint                                    # 짝수 정수 → 중앙값도 정수(짝수 두 개의 평균)
        mf = float(np.median(key2))
        med2 = int(round(mf))
        assert abs(mf - med2) < 1e-9
        return {k: (int(key2[pos[k]]) if k in pos else med2) for k in cand}, med2
    pk, med2 = keys_of(H["Pint"])
    pk_pi, _ = keys_of(H["Pint_pi"])                       # 기록만 — 카드 문자 그대로(거듭제곱 EC) 판
    medrm = float(np.median(H["rowmean"]))
    rm = {k: (float(H["rowmean"][pos[k]]) if k in pos else medrm) for k in cand}
    mc = {k: Wd.mcap(ctick[k], k, i) for k in cand}
    assert all(v and v > 0 for v in mc.values()), "후보 시총이 없다(%s)" % m
    p60 = cand[:POOL]
    secs = {k: Wd.sector(ctick[k], k, m) for k in p60}
    fpb, n_fb = E.betas_for(Wd, m, p60, secs, U)
    dups = near_dups(Ra, nk)
    out = {"m": m, "i": i, "cand": cand, "egr": egr, "tick": ctick, "pk": pk, "pk_pi": pk_pi, "rm": rm, "mc": mc, "fpb": fpb,
           "n_U": len(U), "N": len(nk), "rho_bar": rho, "Rb_off": [float(Rb[np.triu_indices(len(nk), 1)].min()), float(Rb[np.triu_indices(len(nk), 1)].max())],
           "miss": {n: sum(1 for k in cand[:n] if k not in pos) for n in (POOL,) + POOL_ARMS}, "fp_fallback": n_fb,
           "outnet": sorted(k for k in cand if k not in pos),
           "dups": dups, "dup_tickers": [[tick[a], tick[b], r] for a, b, r in dups],
           "nocik_net": sorted(str(tick[k]) for k in nk if str(tick[k]).split("@")[0] in ISSUER_NOCIK),
           "net": H["rec"], "last_px_date": Wd.dates[i], "win0": Wd.dates[i - WIN], "med2": med2}
    _NET[ck] = out
    return out


def _cap_target(P, keys):
    import eg30plus as E
    w = E.cap_weights({k: P["mc"][k] for k in keys}, CAP)
    return {"w": {k: float(v) for k, v in sorted(w.items())}, "names": {k: P["tick"][k] for k in sorted(w)}}


def pick_q08(P, var, pk=None):
    """변형 → 30 이름(순서 = 뽑힌 순)."""
    cand, egr = P["cand"], P["egr"]
    pk = P["pk"] if pk is None else pk
    if var in ("V1", "pool45", "pool90", "PLAC"):
        n = {"V1": POOL, "PLAC": POOL, "pool45": 45, "pool90": 90}[var]
        pool = cand[:n]
        return sorted(pool, key=lambda k: (-pk[k], egr[k]))[:KEEP]
    pool = cand[:POOL]
    if var == "C3":
        return sorted(pool, key=lambda k: (P["rm"][k], egr[k]))[:KEEP]
    if var == "C3b":
        return sorted(pool, key=lambda k: (P["fpb"][k], egr[k]))[:KEEP]
    raise ValueError(var)


Q08_VARS = ("V1", "C3", "C3b", "pool45", "pool90")


def build_q08(ctx, var):
    T, recs = {}, []
    for m in formations(ctx):
        P = prep_q08(ctx, m)
        ks = pick_q08(P, var)
        assert len(ks) == KEEP and len(set(ks)) == KEEP
        T[m] = _cap_target(P, ks)
        v0 = set(ctx.V0_targets[m]["w"])
        recs.append({"m": m, "n": len(ks), "overlap_V0": len(v0 & set(ks)), "max_w": max(T[m]["w"].values()),
                     "n_imputed_sel": sum(1 for k in ks if k in set(P["outnet"])),
                     "dup_both": dup_held(P["dups"], set(ks), P["tick"], T[m]["w"])})
    _assert_priced(ctx, T)
    return T, recs


def issuer_multi(T):
    """CIK 없는 이중클래스(ISSUER_NOCIK) 를 둘 이상 함께 든 편입 → [{m, tickers, w(합친 비중)}](기록만)."""
    out = []
    for m in sorted(T):
        g = {}
        for k in sorted(T[m]["w"]):
            t = T[m]["names"].get(k, k)
            b = ISSUER_NOCIK.get(str(t).split("@")[0])
            if b:
                g.setdefault(b, []).append((str(t), float(T[m]["w"][k])))
        for b in sorted(g):
            if len(g[b]) > 1:
                out.append({"m": m, "tickers": sorted(t for t, _ in g[b]), "w": round(math.fsum(x for _, x in g[b]), 6)})
    return out


def v0_dups(ctx):
    """V0 가 망 R^a ≥ DUP_RA 짝을 둘 다 든 편입(기록만)."""
    out = []
    for m in formations(ctx):
        P = prep_q08(ctx, m)
        tg = ctx.V0_targets[m]
        b = dup_held(P["dups"], set(tg["w"]), tg["names"], tg["w"])
        if b:
            out.append({"m": m, "both": b})
    return out


def plac_q08(ctx, i):
    """위약 뽑기 i — 편입 순서대로 한 줄기(SEED + i) · 60 후보의 P 를 순열."""
    rng = np.random.default_rng(Q.SEED + i)
    T = {}
    for m in formations(ctx):
        P = prep_q08(ctx, m)
        p60 = P["cand"][:POOL]
        vals = [P["pk"][k] for k in p60]
        perm = rng.permutation(POOL)
        pk = {k: vals[perm[j]] for j, k in enumerate(p60)}
        T[m] = _cap_target(P, pick_q08(P, "PLAC", pk))
    return T


def prep_q09(ctx, m):
    """Q09 편입 m — PIT S&P 500 − 부동산 · 251일 · 평균/표준편차 상위 절반 · 그 안 망."""
    ck = ("Q09", id(ctx.Wd), m)
    if ck in _NET:
        return _NET[ck]
    Wd = ctx.Wd
    i = _assert_ltd(Wd, m)
    U0 = sorted(Wd.universe(m, "spx", False), key=lambda x: x[1])
    assert len({k for _, k in U0}) == len(U0), "S&P 500 가격 키가 겹친다(%s)" % m
    mm = max(m, REIT_FROM)
    src = {"month": 0, "near": 0, "today": 0}
    U, n_reit = [], 0
    for t, k in U0:
        s = Wd.sector(t, k, mm)
        src[Wd.sector_src(t, k, mm)] += 1
        if s == REIT:
            n_reit += 1
            continue
        U.append((t, k))
    tick = {k: t for t, k in U}
    nk, Rt = network(Wd, m, U)
    mc = {k: Wd.mcap(tick[k], k, i) for k in nk}
    assert all(v and v > 0 for v in mc.values())
    S = Rt.mean(1) / Rt.std(1, ddof=1)
    n_keep = int(math.ceil(len(nk) / 2))
    o = sorted(range(len(nk)), key=lambda j: (-S[j], -mc[nk[j]], nk[j]))[:n_keep]
    pool = sorted(nk[j] for j in o)                      # 망 마디 순서 = 가격 키 정렬
    pj = {k: j for j, k in enumerate(nk)}
    Rp = Rt[[pj[k] for k in pool]]
    Rb, Ra, rho = rbar(Rp)
    H = hybrid(Rb)
    pk = {k: int(2 * H["Pint"][j]) for j, k in enumerate(pool)}
    pk_pi = {k: int(2 * H["Pint_pi"][j]) for j, k in enumerate(pool)}      # 기록만 — 거듭제곱 EC 판
    rm = {k: float(H["rowmean"][j]) for j, k in enumerate(pool)}
    dups = near_dups(Ra, pool)
    out = {"m": m, "i": i, "pool": pool, "tick": tick, "pk": pk, "pk_pi": pk_pi, "rm": rm, "mc": {k: mc[k] for k in pool},
           "n_spx": len(U0), "n_reit": n_reit, "n_elig": len(nk), "N": len(pool), "rho_bar": rho, "sec_src": src, "sec_month": mm,
           "dups": dups, "dup_tickers": [[tick[a], tick[b], r] for a, b, r in dups],
           "net": H["rec"], "last_px_date": Wd.dates[i], "win0": Wd.dates[i - WIN]}
    _NET[ck] = out
    return out


def pick_q09(P, var, pk=None):
    pool, rm, mc = P["pool"], P["rm"], P["mc"]
    pk = P["pk"] if pk is None else pk
    if var == "rule":
        return sorted(pool, key=lambda k: (-pk[k], rm[k], k))[:M20]
    if var == "K1":
        return sorted(pool, key=lambda k: (pk[k], -rm[k], k))[:M20]
    if var == "K2":
        return sorted(pool, key=lambda k: (rm[k], -mc[k], k))[:M20]
    if var == "K3":
        return list(pool)
    raise ValueError(var)


def _eq_target(P, ks, each):
    return {"w": {k: float(each) for k in sorted(ks)}, "names": {k: P["tick"][k] for k in sorted(ks)}}


Q09_VARS = ("rule", "K1", "K2", "K3")


def build_q09(ctx, var):
    T, recs = {}, []
    for m in formations(ctx):
        P = prep_q09(ctx, m)
        ks = pick_q09(P, var)
        each = (1.0 / len(ks)) if var == "K3" else W20
        T[m] = _eq_target(P, ks, each)
        recs.append({"m": m, "n": len(ks), "sum_w": sum(T[m]["w"].values()), "dup_both": dup_held(P["dups"], set(ks), P["tick"], T[m]["w"])})
    _assert_priced(ctx, T)
    return T, recs


def plac_q09(ctx, i):
    """K4 뽑기 i — 편입 순서대로 한 줄기(SEED + i) · 걸러진 풀에서 비복원 균등 20 · 각 5%."""
    rng = np.random.default_rng(Q.SEED + i)
    T = {}
    for m in formations(ctx):
        P = prep_q09(ctx, m)
        pool = P["pool"]
        j = rng.choice(len(pool), min(M20, len(pool)), replace=False)
        T[m] = _eq_target(P, [pool[x] for x in sorted(j.tolist())], W20)
    return T


def thash(T):
    return hashlib.sha256(json.dumps(T, sort_keys=True).encode("utf-8")).hexdigest()


def _proxy_turn(T):
    """목표 사이 편도 회전 대용(흘러감 무시 · 구성만) — 연율(분기 4번)."""
    ms = sorted(T)
    tv = [0.5 * sum(abs(T[b]["w"].get(k, 0.0) - T[a]["w"].get(k, 0.0)) for k in sorted(set(T[a]["w"]) | set(T[b]["w"]))) for a, b in zip(ms, ms[1:])]
    return float(np.mean(tv) * 4) if tv else None


def ec_method_check(ctx, T8, T9):
    """EC 순위 방법(tree_perron) 대 카드 문자 그대로(거듭제곱 벡터) — P 키 · 목표가 움직였는가(구성만 · 기록).
    C3 · C3b · K2 · K3 는 P 를 쓰지 않아 비교하지 않는다."""
    fm = formations(ctx)
    P8 = [prep_q08(ctx, m) for m in fm]
    P9 = [prep_q09(ctx, m) for m in fm]
    alt8 = {v: {P["m"]: _cap_target(P, pick_q08(P, v, P["pk_pi"])) for P in P8} for v in ("V1", "pool45", "pool90")}
    alt9 = {v: {P["m"]: _eq_target(P, pick_q09(P, v, P["pk_pi"]), W20) for P in P9} for v in ("rule", "K1")}
    moved = lambda P, ks: [P["tick"][k] for k in ks if P["pk"][k] != P["pk_pi"][k]]
    ms8 = lambda P, d: sorted(d[k] for k in P["cand"][:POOL])
    return {"q08_same_hash": {v: thash(alt8[v]) == thash(T8[v]) for v in alt8},
            "q09_same_hash": {v: thash(alt9[v]) == thash(T9[v]) for v in alt9},
            "q08_net_key_moves": sum(P["net"]["P_key_moves_pi"] for P in P8),
            "q08_cand90_key_moves": [[P["m"], moved(P, P["cand"])] for P in P8 if moved(P, P["cand"])],
            "q08_p60_key_moves": [[P["m"], moved(P, P["cand"][:POOL])] for P in P8 if moved(P, P["cand"][:POOL])],
            "q08_placebo_values_differ": [P["m"] for P in P8 if ms8(P, P["pk"]) != ms8(P, P["pk_pi"])],
            "q09_pool_key_moves": [[P["m"], moved(P, P["pool"])] for P in P9 if moved(P, P["pool"])]}


def delist_frozen(ctx, T):
    """가격이 다음 편입(마지막 편입은 보유 끝 HOLD1) 전에 끊긴 보유 이름 — 코어 stock_path 가 마지막 가격에 묶어 두는 날 수.
    카드 Q09 STEP 5 'cash at rf' 와 코어의 차이 크기를 적는 기록만(구성 · 선택에 안 쓴다 · 수익 없음)."""
    Wd = ctx.Wd
    fm = sorted(T)
    ev = []
    for m, m1 in zip(fm, fm[1:] + [Q.HOLD1]):
        i, i1 = Wd.me[m], Wd.me[m1]
        for k in sorted(T[m]["w"]):
            p = np.asarray(Wd.PX[k][i:i1 + 1], float)
            good = np.flatnonzero(np.isfinite(p) & (p > 0))
            last = int(good[-1]) if len(good) else 0
            if last < i1 - i:
                ev.append({"m": m, "t": T[m]["names"][k], "w": round(float(T[m]["w"][k]), 6),
                           "last_px": Wd.dates[i + last], "frozen_days": int(i1 - i - last)})
    return {"n": len(ev), "max_days": max((e["frozen_days"] for e in ev), default=0), "events": ev}


def _assert_priced(ctx, T):
    """목표 이름마다 편입일 가격이 선다(코어 sleeve 가 가격 없는 목표를 조용히 현금으로 돌리지 않게)."""
    Wd = ctx.Wd
    for m, tg in T.items():
        i = Wd.me[m]
        for k in tg["w"]:
            p = Wd.PX[k][i]
            assert p == p and p > 0, "편입일 가격 없음 %s %s" % (m, k)


def sector_weights(ctx, T):
    """편입마다 업종 비중(시점정확 · 구성만)."""
    Wd = ctx.Wd
    out = {}
    for m, tg in T.items():
        s = {}
        for k, x in tg["w"].items():
            sec = Wd.sector(tg["names"][k], k, m) or "?"
            s[sec] = s.get(sec, 0.0) + x
        out[m] = dict(sorted(s.items()))
    return out


def exante_beta(ctx, T):
    """편입마다 FP 사전 베타(구성만 · eg30plus.betas_for 대체)."""
    import eg30plus as E
    Wd = ctx.Wd
    out = {}
    for m, tg in T.items():
        ks = sorted(tg["w"])
        secs = {k: Wd.sector(tg["names"][k], k, m) for k in ks}
        b, _ = E.betas_for(Wd, m, ks, secs, Wd.universe(m, "union", False))
        out[m] = float(sum(tg["w"][k] * b[k] for k in ks))
    return out


# ── 판정 보조(카드 G4 · 위약 통계만) ─────────────────────────────────────
def sleeve_beta(ctx, fr):
    """β̂_s = qbatch_core.evaluate 의 sleeve_beta(120개월 OLS · 복제하지 않는다)."""
    return Q.evaluate(ctx.G, fr)["sleeve_beta"]


def _rf(ctx, hold):
    return np.array([float(ctx.G.RF.get(h, 0.0)) * 100 for h in hold])


def dbeta_down(ctx, fa, fb, ba=None, bb=None):
    """하락월(39) 평균 Δβ = (X_a − X_b) − 0.1(β̂_a − β̂_b)(SPYTR − rf)."""
    ha, hb = fa["hold"], fb["hold"]
    assert ha == hb and fa["basis"] == fb["basis"] == "TR"
    ba = sleeve_beta(ctx, fa) if ba is None else ba
    bb = sleeve_beta(ctx, fb) if bb is None else bb
    dm = ctx.dmask(ha)
    ix = np.asarray(fa["index"], float)
    assert np.allclose(ix, fb["index"])
    db = (np.asarray(fa["ex"]) - np.asarray(fb["ex"])) - Q.SLEEVE * (ba - bb) * (ix - _rf(ctx, ha))
    return float(db[dm].mean())


def x_all_h_down(ctx, fr):
    """(전 월 평균 X, 하락월 평균 H) — H = X − 0.1(β̂ − 1)(SPYTR − rf)."""
    b = sleeve_beta(ctx, fr)
    ex = np.asarray(fr["ex"], float)
    h = ex - Q.SLEEVE * (b - 1.0) * (np.asarray(fr["index"], float) - _rf(ctx, fr["hold"]))
    dm = ctx.dmask(fr["hold"])
    return float(ex.mean()), float(h[dm].mean())


# ── 계약 ──────────────────────────────────────────────────────────────────
def _star(nl):
    return nl + 1, [(0, j) for j in range(1, nl + 1)]


def _path(n):
    return n, [(j, j + 1) for j in range(n - 1)]


def _brute_bc(n, edges, length):
    """무차별 검산 — 전 쌍 거리(Floyd) · σ(최단경로 수) DP · σ_st(v) = σ_sv σ_vt(d_sv + d_vt = d_st) · 순서 없는 쌍."""
    INF = math.inf
    Dm = [[INF] * n for _ in range(n)]
    for v in range(n):
        Dm[v][v] = 0.0
    for (a, b), l in zip(edges, length):
        Dm[a][b] = Dm[b][a] = min(Dm[a][b], float(l))
    for k in range(n):
        for a in range(n):
            for b in range(n):
                if Dm[a][k] + Dm[k][b] < Dm[a][b] - 1e-12:
                    Dm[a][b] = Dm[a][k] + Dm[k][b]
    L = {}
    for (a, b), l in zip(edges, length):
        L[(a, b)] = L[(b, a)] = float(l)
    sig = [[0.0] * n for _ in range(n)]
    for s in range(n):
        order = sorted(range(n), key=lambda v: Dm[s][v])
        sig[s][s] = 1.0
        for v in order:
            if v == s:
                continue
            sig[s][v] = sum(sig[s][u] for u in range(n) if (u, v) in L and abs(Dm[s][u] + L[(u, v)] - Dm[s][v]) <= 1e-12)
    bc = np.zeros(n)
    for s in range(n):
        for t in range(s + 1, n):
            for v in range(n):
                if v in (s, t):
                    continue
                if abs(Dm[s][v] + Dm[v][t] - Dm[s][t]) <= 1e-12:
                    bc[v] += sig[s][v] * sig[v][t] / sig[s][t]
    return bc


def _decimal_perron(n, edges, wt, digits=60):
    """검산 기준 — 소수 60자리 (A + I) 거듭제곱(최대 항목 정규화 · 변화 < 10^−(digits−8)) → 단위 L2 float."""
    import decimal
    with decimal.localcontext() as c:
        c.prec = digits
        Dd = lambda v: decimal.Decimal(repr(float(v)))
        adj = [[] for _ in range(n)]
        for (a, b), w in zip(edges, wt):
            adj[a].append((b, Dd(w)))
            adj[b].append((a, Dd(w)))
        x = [decimal.Decimal(1)] * n
        tol = decimal.Decimal("1e-%d" % (digits - 8))
        conv = False
        for _ in range(20000):
            y = [x[v] + sum((w * x[u] for u, w in adj[v]), decimal.Decimal(0)) for v in range(n)]
            mx = max(y)
            y = [v / mx for v in y]
            if max(abs(a - b) for a, b in zip(y, x)) < tol:
                x, conv = y, True
                break
            x = y
        assert conv, "소수 기준 거듭제곱이 수렴하지 않았다"
        nrm = sum((v * v for v in x), decimal.Decimal(0)).sqrt()
        return np.array([float(v / nrm) for v in x])


def _prim(d):
    """검산용 Prim(조밀) — MST 전체 길이."""
    n = len(d)
    inT = np.zeros(n, bool)
    inT[0] = True
    best = d[0].copy()
    tot = 0.0
    for _ in range(n - 1):
        cand = np.where(inT, np.inf, best)
        j = int(np.argmin(cand))
        tot += float(cand[j])
        inT[j] = True
        best = np.minimum(best, d[j])
    return tot


def selftest() -> dict:
    """합성 자료만 — 랩 수익 없음. 중심성 · MST · 상관 · 빈칸 · 순위 · 선택 규칙."""
    t = {}
    rng = np.random.default_rng(Q.SEED)
    # 1) 중간순위
    r = midrank2([3.0, 1.0, 2.0, 2.0], True)
    r2 = midrank2([3.0, 1.0, 2.0, 2.0 * (1 + 1e-13)], False)
    t["midrank_ok"] = bool(r.tolist() == [2, 8, 5, 5] and r2.tolist() == [8, 2, 5, 5] and midrank2([0.0, 0.0, 0.0], True).tolist() == [4, 4, 4])
    # 2) 별(잎 6) — 무가중 · 가중(잎마다 다른 길이 · 세기)
    n, E_ = _star(6)
    ln = np.array([1.0, 2.0, 3.0, 1.5, 2.5, 0.5])
    wt = np.array([1.2, 1.4, 1.1, 1.9, 1.3, 1.6])
    M, info = graph_measures(n, E_, ln, wt)
    nl = 6
    bc_c = nl * (nl - 1) / 2
    far_leaf_u = (1 + 2 * (nl - 1)) / nl
    dw = np.r_[0.0, ln]
    far_w = [ln.sum() / nl] + [(ln[j] + (ln.sum() - ln[j]) + ln[j] * (nl - 1)) / nl for j in range(nl)]
    ecc_w = [ln.max()] + [ln[j] + max(np.delete(ln, j)) for j in range(nl)]
    t["star_degree_ok"] = bool(M["D_u"].tolist() == [6.0] + [1.0] * 6 and np.allclose(M["D_w"], np.r_[wt.sum(), wt]))
    t["star_bc_ok"] = bool(np.allclose(M["BC_u"], [bc_c] + [0.0] * 6) and np.allclose(M["BC_w"], [bc_c] + [0.0] * 6))
    t["star_ecc_far_ok"] = bool(np.allclose(M["E_u"], [1] + [2] * 6) and np.allclose(M["C_u"], [1.0] + [far_leaf_u] * 6)
                                and np.allclose(M["E_w"], ecc_w) and np.allclose(M["C_w"], far_w))
    t["star_ec_ok"] = bool(abs(M["EC_u"][0] / M["EC_u"][1] - math.sqrt(nl)) < 1e-9 and np.allclose(M["EC_u"][1:], M["EC_u"][1])
                           and info["ec_u"]["conv"] and info["ec_w"]["conv"] and info["ec_w"]["eigh_diff"] < 1e-9)
    Pint, P, rk = hybrid_from(M, n)
    t["star_P_ok"] = bool(Pint[0] == 0 and P[0] == 0 and np.all(Pint[1:] > 0) and all(int(rk[k][0]) == 2 for k, _ in MEASURES))
    # 무가중 별만으로 P(잎) = N/(N−1)
    Mu = {k: (M[k.replace("_w", "_u")] if k.endswith("_w") else M[k]) for k, _ in MEASURES}
    Pu_int, Pu, _ = hybrid_from(Mu, n)
    t["star_P_leaf_ok"] = bool(Pu_int[0] == 0 and np.allclose(Pu[1:], n / (n - 1)))
    # 3) 경로(7) — BC = i(n−1−i) · E = max(i, n−1−i) · C = Σ|i − j|/(n−1) · EC ∝ sin((i+1)π/(n+1))
    n, E_ = _path(7)
    ln = rng.uniform(0.5, 2.0, n - 1)
    M, info = graph_measures(n, E_, ln, np.ones(n - 1))
    ii = np.arange(n)
    pos = np.r_[0.0, np.cumsum(ln)]
    ec = np.sin((ii + 1) * math.pi / (n + 1))
    ec = ec / np.linalg.norm(ec)
    t["path_bc_ok"] = bool(np.allclose(M["BC_u"], ii * (n - 1 - ii)) and np.allclose(M["BC_w"], ii * (n - 1 - ii)))
    t["path_ecc_far_ok"] = bool(np.allclose(M["E_u"], np.maximum(ii, n - 1 - ii)) and np.allclose(M["C_u"], [np.abs(ii - j).sum() / (n - 1) for j in ii])
                                and np.allclose(M["E_w"], [max(pos[j], pos[-1] - pos[j]) for j in ii])
                                and np.allclose(M["C_w"], [np.abs(pos - pos[j]).sum() / (n - 1) for j in ii]))
    t["path_ec_ok"] = bool(np.allclose(M["EC_u"], ec, atol=1e-10) and np.allclose(M["EC_w"], ec, atol=1e-10))
    Mu, _ = graph_measures(n, E_, np.ones(n - 1), np.ones(n - 1))
    Pint, P, rk = hybrid_from(Mu, n)
    t["path_center_P_min_ok"] = bool(int(np.argmin(Pint)) == 3 and Pint[0] == Pint.max() and Pint[0] == Pint[6]
                                     and np.array_equal(Pint, Pint[::-1]) and np.all(np.diff(Pint[:4]) < 0))
    # 4) 알려진 작은 그래프 — C4 는 각 0.5 · 가중 삼각형(0-1 1 · 1-2 1 · 0-2 3)은 가중 BC(1) = 1 · 무가중 0
    c4 = [(0, 1), (1, 2), (2, 3), (0, 3)]
    t["c4_bc_ok"] = bool(np.allclose(brandes(4, c4, None), 0.5) and np.allclose(brandes(4, c4, [2.0] * 4), 0.5))
    tri = [(0, 1), (1, 2), (0, 2)]
    t["tri_weighted_bc_ok"] = bool(np.allclose(brandes(3, tri, [1.0, 1.0, 3.0]), [0, 1, 0]) and np.allclose(brandes(3, tri, None), 0.0))
    # 5) 무작위 그래프(정수 길이 → 같은 길이 경로가 많다) — Brandes = 무차별 검산
    ok5 = True
    for g in range(12):
        nn = int(rng.integers(5, 10))
        ed = set((j, int(rng.integers(0, j))) for j in range(1, nn))           # 이어진 뼈대
        for _ in range(int(rng.integers(0, nn))):
            a, b = sorted(rng.choice(nn, 2, replace=False).tolist())
            ed.add((b, a))
        ed = sorted((min(a, b), max(a, b)) for a, b in ed)
        ed = sorted(set(ed))
        lg = rng.integers(1, 4, len(ed)).astype(float)
        ok5 &= bool(np.allclose(brandes(nn, ed, lg), _brute_bc(nn, ed, lg)) and np.allclose(brandes(nn, ed, None), _brute_bc(nn, ed, [1.0] * len(ed))))
    t["random_graph_bc_ok"] = bool(ok5)
    # 6) 무작위 나무(300) — Brandes = 쌍 공식 · 거듭제곱 EC = eigh
    nn = 300
    ed = sorted((int(rng.integers(0, j)), j) for j in range(1, nn))
    lg = rng.uniform(0.3, 1.5, nn - 1)
    t0 = time.time()
    b_w = brandes(nn, ed, lg)
    t["brandes_300_sec"] = round(time.time() - t0, 3)
    tb = tree_bc(nn, ed)
    x, rec = eig_centrality(nn, ed, rng.uniform(1.0, 1.9, nn - 1))
    t["tree_bc_ok"] = bool(np.allclose(b_w, tb) and np.allclose(brandes(nn, ed, None), tb))
    t["tree_ec_ok"] = bool(rec["conv"] and rec["eigh_diff"] < 1e-9 and np.all(x > 0))
    t["tree_ec_it"] = rec["it"]
    # 7) MST — scipy(위 삼각) 길이 = Prim · 간선 N − 1
    Z = rng.standard_normal((40, 250)) + 0.5 * rng.standard_normal((1, 250))
    Rb, Ra, rho = rbar(Z)
    e, d = mst_edges(Rb)
    ea = np.asarray(e)
    t["mst_ok"] = bool(len(e) == 39 and abs(float(d[ea[:, 0], ea[:, 1]].sum()) - _prim(d)) < 1e-10)
    # 8) 상관 — 지수가중 식 · 126 창 평균 · 축소(비대각 평균 보존 · 대각 1 · 대칭)
    w = ew_weights()
    ok8 = abs(w.sum() - 1) < 1e-15 and abs(w[-1] / w[0] - math.exp(124 / 125)) < 1e-12
    a_, b_ = 3, 17
    acc = 0.0
    for s in range(NAVG):
        x1, x2 = Z[a_, s:s + TAU], Z[b_, s:s + TAU]
        m1, m2 = (w * x1).sum(), (w * x2).sum()
        c = (w * (x1 - m1) * (x2 - m2)).sum() / math.sqrt((w * (x1 - m1) ** 2).sum() * (w * (x2 - m2) ** 2).sum())
        acc += c
    ra_ab = acc / NAVG
    iu = np.triu_indices(40, 1)
    ok8 = ok8 and abs(Ra[a_, b_] - ra_ab) < 1e-12 and abs(Rb[a_, b_] - (0.5 * ra_ab + 0.5 * rho)) < 1e-12
    ok8 = ok8 and np.allclose(np.diag(Rb), 1) and np.allclose(Rb, Rb.T) and abs(Rb[iu].mean() - Ra[iu].mean()) < 1e-12 and abs(Ra[iu].mean() - rho) < 1e-12
    # 균등 가중이면 np.corrcoef 와 같다(식 모양 점검)
    wu = np.full(TAU, 1.0 / TAU)
    x1, x2 = Z[a_, :TAU], Z[b_, :TAU]
    cu = (wu * (x1 - x1.mean()) * (x2 - x2.mean())).sum() / math.sqrt((wu * (x1 - x1.mean()) ** 2).sum() * (wu * (x2 - x2.mean()) ** 2).sum())
    ok8 = ok8 and abs(cu - np.corrcoef(x1, x2)[0, 1]) < 1e-12
    t["corr_ok"] = bool(ok8)
    # 9) 빈칸 채움 — 4일은 채우고 5일은 탈락 · 첫 값 전은 NaN
    Pm = np.ones((3, 12))
    Pm[0, 3:7] = np.nan
    Pm[1, 3:8] = np.nan
    Pm[2, :2] = np.nan
    F = ffill_limited(Pm)
    t["ffill_ok"] = bool(np.all(np.isfinite(F[0])) and np.isnan(F[1, 7]) and np.all(np.isfinite(F[1, 3:7])) and np.all(np.isnan(F[2, :2])))
    # 10) 선택 규칙 — P 동률은 Eg 높은 쪽 · 중앙값 대체 · 위약 순열은 값의 다중집합을 지킨다
    Pd = {"cand": ["a", "b", "c", "d"] + ["x%02d" % j for j in range(86)], "egr": {}, "pk": {}, "rm": {}, "fpb": {}, "mc": {}, "tick": {}}
    for r_, k in enumerate(Pd["cand"]):
        Pd["egr"][k] = r_
        Pd["pk"][k] = 10 if k in ("c", "d") else (100 if k == "a" else 0)
        Pd["rm"][k] = 0.1 * r_
        Pd["fpb"][k] = 1.0
        Pd["mc"][k] = 1.0 + r_
        Pd["tick"][k] = k
    sel = pick_q08(Pd, "V1")
    t["tie_rule_ok"] = bool(sel[:3] == ["a", "c", "d"] and sel[3] == "b" and len(sel) == KEEP)
    rr = np.random.default_rng(Q.SEED + 5).permutation(POOL)
    rr2 = np.random.default_rng(Q.SEED + 5).permutation(POOL)
    t["seed_ok"] = bool(np.array_equal(rr, rr2) and sorted(rr.tolist()) == list(range(POOL)))
    import eg30plus as E
    cw = E.cap_weights({"p": 50.0, "q": 30.0, "r": 10.0, "s": 5.0, "t": 5.0, "u": 1.0}, CAP)
    t["cap_ok"] = bool(abs(sum(cw.values()) - 1) < 1e-12 and max(cw.values()) <= CAP + 1e-12)
    # 11) 동률 허용이 다른 값을 합치지 않는다
    t["midrank_distinct_ok"] = bool(midrank2([1.0, 1.0 + 1e-8, 1.0 + 2e-8], True).tolist() == [6, 4, 2])
    # 12) 합성 요인 구조 — 공통 요인에 크게 실린 20 이 작게 실린 40 보다 중심(P 작다) · 전 과정(상관 → MST → P)
    nf = 60
    lo_ = np.r_[np.full(20, 1.0), np.full(40, 0.15)]
    Zf = lo_[:, None] * rng.standard_normal((1, WIN)) + rng.standard_normal((nf, WIN))
    Hs = hybrid(rbar(Zf * 0.01)[0])
    t["factor_hubs_central_ok"] = bool(Hs["P"][:20].mean() < Hs["P"][20:].mean() and Hs["rowmean"][:20].mean() > Hs["rowmean"][20:].mean()
                                       and Hs["rec"]["bc_tree_diff"] < 1e-9 and Hs["rec"]["ec_conv"])
    t["factor_P_means"] = [round(float(Hs["P"][:20].mean()), 3), round(float(Hs["P"][20:].mean()), 3)]
    # 13) 깊은 나무의 EC — 빗자루(허브 + 잎 10 · 35 홉 꼬리) · 소수 60자리 거듭제곱 기준과 항목별 상대 오차 · 순위
    nb = 1 + 10 + 35
    ed = [(0, j) for j in range(1, 11)] + [(0 if j == 11 else j - 1, j) for j in range(11, nb)]
    wb = np.r_[rng.uniform(1.8, 1.9, 10), rng.uniform(1.0, 1.3, 35)]
    ref = _decimal_perron(nb, ed, wb)
    x_t, rec_t = ec_tree(nb, ed, wb)
    x_p, _ = eig_centrality(nb, ed, wb)
    rel_t = float(np.max(np.abs(x_t - ref) / ref))
    rel_p = float(np.max(np.abs(x_p - ref) / ref))
    t["deep_ec_min_entry"] = float(ref.min())
    t["deep_ec_rel_err_tree"] = rel_t
    t["deep_ec_rel_err_power"] = rel_p
    t["deep_ec_ok"] = bool(ref.min() < 1e-20 and rel_t < 1e-10 and rel_p > 1e3 * rel_t
                           and midrank2(x_t, True).tolist() == midrank2(ref, True).tolist() and abs(rec_t["root_res"]) < 1e-12)
    # 경로 · 별에서도 tree_perron = 닫힌 해
    n7, E7 = _path(7)
    xp7, _ = ec_tree(n7, E7, np.ones(6))
    ec7 = np.sin((np.arange(7) + 1) * math.pi / 8)
    t["tree_perron_closed_ok"] = bool(np.allclose(xp7, ec7 / np.linalg.norm(ec7), rtol=1e-12, atol=0))
    # 14) 기록 도구 — 거의 복제 짝 찾기 · 회전 대용은 사전 순서와 무관 · 얕은 나무에서는 거듭제곱 EC 판 P 키가 같다
    Rn = np.eye(4)
    Rn[1, 3] = Rn[3, 1] = 0.97
    Rn[0, 2] = Rn[2, 0] = 0.949
    nd = near_dups(Rn, ["a", "b", "c", "d"])
    t["near_dups_ok"] = bool(nd == [["b", "d", 0.97]] and dup_held(nd, {"b", "d", "a"}, {"b": "B", "d": "D"}) == [["B", "D"]]
                             and dup_held(nd, {"b", "a"}, {}) == [])
    Ta = {"2016-08": {"w": {"x": 0.5, "y": 0.3, "z": 0.2}}, "2016-09": {"w": {"z": 0.1, "w": 0.6, "x": 0.3}}}
    Tb = {"2016-08": {"w": {"z": 0.2, "x": 0.5, "y": 0.3}}, "2016-09": {"w": {"x": 0.3, "w": 0.6, "z": 0.1}}}
    Ti = {"2018-09": {"w": {"k1": 0.2, "k2": 0.05, "k3": 0.75}, "names": {"k1": "LBTYA", "k2": "LBTYK", "k3": "AAPL"}},
          "2018-12": {"w": {"k1": 0.5, "k3": 0.5}, "names": {"k1": "LBTYA", "k3": "AAPL"}}}
    t["issuer_multi_ok"] = bool(issuer_multi(Ti) == [{"m": "2018-09", "tickers": ["LBTYA", "LBTYK"], "w": 0.25}])
    t["proxy_turn_ok"] = bool(_proxy_turn(Ta) == _proxy_turn(Tb) and abs(_proxy_turn(Ta) - 0.5 * (0.2 + 0.3 + 0.1 + 0.6) * 4) < 1e-12)
    Hs2 = hybrid(rbar(Zf[:30] * 0.01)[0])
    t["pint_pi_shallow_ok"] = bool(np.array_equal(Hs2["Pint"], Hs2["Pint_pi"]) and Hs2["rec"]["P_key_moves_pi"] == 0)
    keys = [k for k in t if k.endswith("_ok")]
    return {"ok": all(t[k] for k in keys), "tests": t}


def _ec_tree_summary(rows):
    n = [r["net"] for r in rows]
    return {"tree_pi_diff_max": max(x["ec_tree_pi_diff"] for x in n), "root_res_max": max(x["ec_root_res"] for x in n),
            "min_entry": min(x["ec_min_entry"] for x in n),
            "rank_moves_w": [min(x["ec_rank_moves"][0] for x in n), max(x["ec_rank_moves"][0] for x in n)],
            "rank_moves_u": [min(x["ec_rank_moves"][1] for x in n), max(x["ec_rank_moves"][1] for x in n)]}


def dry(ctx) -> dict:
    """랩 자료로 구성만 — 망 크기 · 커버리지 · 대체 수 · 나무 검산 · EC 수렴 · 비중 합 · 한도 · 개수 · 날짜 단언 · 시간. 수익 없음."""
    t0 = time.time()
    fm = formations(ctx)
    out = {"forms": len(fm), "q08": {}, "q09": {}}
    bad = 0
    # Q08
    rows = []
    for m in fm:
        P = prep_q08(ctx, m)
        rows.append(P)
    out["q08"]["prep_sec"] = round(time.time() - t0, 1)
    out["q08"]["N_union"] = [min(r["n_U"] for r in rows), max(r["n_U"] for r in rows)]
    out["q08"]["N_net"] = [min(r["N"] for r in rows), max(r["N"] for r in rows)]
    out["q08"]["net_cover"] = [round(min(r["N"] / r["n_U"] for r in rows), 3), round(max(r["N"] / r["n_U"] for r in rows), 3)]
    out["q08"]["p60_imputed"] = [min(r["miss"][POOL] for r in rows), max(r["miss"][POOL] for r in rows), sum(r["miss"][POOL] for r in rows)]
    out["q08"]["p90_imputed_total"] = sum(r["miss"][90] for r in rows)
    out["q08"]["fp_fallback_total"] = sum(r["fp_fallback"] for r in rows)
    out["q08"]["rho_bar"] = [round(min(r["rho_bar"] for r in rows), 3), round(max(r["rho_bar"] for r in rows), 3)]
    out["q08"]["Rb_off"] = [round(min(r["Rb_off"][0] for r in rows), 3), round(max(r["Rb_off"][1] for r in rows), 3)]
    out["q08"]["max_deg"] = [min(r["net"]["max_deg"] for r in rows), max(r["net"]["max_deg"] for r in rows)]
    out["q08"]["diam_hops"] = [min(r["net"]["diam_hops"] for r in rows), max(r["net"]["diam_hops"] for r in rows)]
    out["q08"]["n_leaf_share"] = [round(min(r["net"]["n_leaf"] / r["N"] for r in rows), 3), round(max(r["net"]["n_leaf"] / r["N"] for r in rows), 3)]
    out["q08"]["bc_tree_diff_max"] = max(r["net"]["bc_tree_diff"] for r in rows)
    out["q08"]["ec_conv_all"] = all(r["net"]["ec_conv"] for r in rows)
    out["q08"]["ec_it_max"] = max(max(r["net"]["ec_w_it"], r["net"]["ec_u_it"]) for r in rows)
    out["q08"]["ec_eigh_diff_max"] = max(r["net"]["ec_eigh_diff"] for r in rows)
    out["q08"]["P_range"] = [round(min(r["net"]["P_range"][0] for r in rows), 3), round(max(r["net"]["P_range"][1] for r in rows), 3)]
    out["q08"]["ec_tree"] = _ec_tree_summary(rows)
    out["q08"]["windows"] = [[rows[0]["win0"], rows[0]["last_px_date"]], [rows[-1]["win0"], rows[-1]["last_px_date"]]]
    out["q08"]["var"] = {}
    T8 = {}
    for v in Q08_VARS:
        T, recs = build_q08(ctx, v)
        T8[v] = T
        for m, tg in T.items():
            s = sum(tg["w"].values())
            if abs(s - 1) > 1e-9 or min(tg["w"].values()) < 0 or max(tg["w"].values()) > CAP + 1e-9 or len(tg["w"]) != KEEP:
                bad += 1
        out["q08"]["var"][v] = {"hash": thash(T)[:12], "turn_proxy": round(_proxy_turn(T), 3),
                                "overlap_V0": [min(r["overlap_V0"] for r in recs), max(r["overlap_V0"] for r in recs)],
                                "same_as_V0": sum(1 for r in recs if r["overlap_V0"] == KEEP),
                                "max_w": round(max(r["max_w"] for r in recs), 4),
                                "dup_both_forms": sum(1 for r in recs if r["dup_both"]),
                                "delist_frozen": {k_: x_ for k_, x_ in delist_frozen(ctx, T).items() if k_ != "events"}}
    out["q08"]["dup_forms"] = sum(1 for r in rows if r["dups"])
    out["q08"]["dup_tickers_seen"] = sorted({"/".join(sorted(x[:2])) for r in rows for x in r["dup_tickers"]})
    out["q08"]["dup_Ra_range"] = ([min(x[2] for r in rows for x in r["dup_tickers"]), max(x[2] for r in rows for x in r["dup_tickers"])]
                                  if out["q08"]["dup_forms"] else None)
    out["q08"]["v0_dup_both_forms"] = [x["m"] for x in v0_dups(ctx)]
    out["q08"]["issuer_multi_forms"] = {v: [x["m"] for x in issuer_multi(T8[v])] for v in Q08_VARS}
    out["q08"]["v0_issuer_multi"] = issuer_multi(ctx.V0_targets)
    out["q08"]["nocik_both_in_net_forms"] = [r["m"] for r in rows if len(r["nocik_net"]) > 1]
    tp = time.time()
    Tp = plac_q08(ctx, 0)
    out["q08"]["placebo_build_sec"] = round(time.time() - tp, 2)
    out["q08"]["placebo_ok"] = all(abs(sum(tg["w"].values()) - 1) < 1e-9 and len(tg["w"]) == KEEP for tg in Tp.values())
    # Q09
    t1 = time.time()
    rows9 = [prep_q09(ctx, m) for m in fm]
    out["q09"]["prep_sec"] = round(time.time() - t1, 1)
    out["q09"]["n_spx"] = [min(r["n_spx"] for r in rows9), max(r["n_spx"] for r in rows9)]
    out["q09"]["n_reit"] = [min(r["n_reit"] for r in rows9), max(r["n_reit"] for r in rows9)]
    out["q09"]["n_reit_first3"] = [(r["m"], r["n_reit"], r["sec_month"]) for r in rows9[:3]]
    out["q09"]["n_elig"] = [min(r["n_elig"] for r in rows9), max(r["n_elig"] for r in rows9)]
    out["q09"]["N_pool"] = [min(r["N"] for r in rows9), max(r["N"] for r in rows9)]
    out["q09"]["sec_src"] = {s: sum(r["sec_src"][s] for r in rows9) for s in ("month", "near", "today")}
    out["q09"]["rho_bar"] = [round(min(r["rho_bar"] for r in rows9), 3), round(max(r["rho_bar"] for r in rows9), 3)]
    out["q09"]["bc_tree_diff_max"] = max(r["net"]["bc_tree_diff"] for r in rows9)
    out["q09"]["ec_conv_all"] = all(r["net"]["ec_conv"] for r in rows9)
    out["q09"]["ec_eigh_diff_max"] = max(r["net"]["ec_eigh_diff"] for r in rows9)
    out["q09"]["max_deg"] = [min(r["net"]["max_deg"] for r in rows9), max(r["net"]["max_deg"] for r in rows9)]
    out["q09"]["ec_tree"] = _ec_tree_summary(rows9)
    out["q09"]["tie_lost_max"] = {k: max(r["net"]["tie_lost"][k] for r in rows9) for k, _ in MEASURES}
    out["q09"]["var"] = {}
    T9 = {}
    for v in Q09_VARS:
        T, recs = build_q09(ctx, v)
        T9[v] = T
        for m, tg in T.items():
            s = sum(tg["w"].values())
            if abs(s - 1) > 1e-9 or min(tg["w"].values()) < 0:
                bad += 1
        out["q09"]["var"][v] = {"hash": thash(T)[:12], "n": [min(r["n"] for r in recs), max(r["n"] for r in recs)],
                                "turn_proxy": round(_proxy_turn(T), 3), "dup_both_forms": sum(1 for r in recs if r["dup_both"]),
                                "delist_frozen": {k_: x_ for k_, x_ in delist_frozen(ctx, T).items() if k_ != "events"}}
    out["q09"]["dup_forms"] = sum(1 for r in rows9 if r["dups"])
    out["q09"]["dup_tickers_seen"] = sorted({"/".join(sorted(x[:2])) for r in rows9 for x in r["dup_tickers"]})
    out["ec_method_check"] = ec_method_check(ctx, T8, T9)
    out["delist_events_rule"] = delist_frozen(ctx, T9["rule"])["events"]
    out["q09"]["rule_K1_overlap_max"] = max(len(set(T9["rule"][m]["w"]) & set(T9["K1"][m]["w"])) for m in fm)
    Tk = plac_q09(ctx, 0)
    out["q09"]["K4_ok"] = all(abs(sum(tg["w"].values()) - 1) < 1e-9 and len(tg["w"]) == M20 for tg in Tk.values())
    # 한 번 굽기 시간 추정 재료 — V0 경로 한 벌 시간(공개 판 · 수익은 버린다)
    t2 = time.time()
    sl = Q.stock_path(ctx.Wd, ctx.V0_targets, reb=3)
    frv = Q.fund_from_path(ctx.G, sl, ctx.Wd.months)
    _ = Q.evaluate(ctx.G, frv)["sleeve_beta"]
    del sl, frv, _
    out["one_path_eval_sec"] = round(time.time() - t2, 2)
    out["bad_weights"] = bad
    out["sec"] = round(time.time() - t0, 1)
    out["ok"] = bool(bad == 0 and out["q08"]["bc_tree_diff_max"] < 1e-9 and out["q09"]["bc_tree_diff_max"] < 1e-9
                     and out["q08"]["ec_conv_all"] and out["q09"]["ec_conv_all"] and out["q08"]["placebo_ok"] and out["q09"]["K4_ok"]
                     and out["q09"]["N_pool"][0] >= M20)
    return out


def run(ctx) -> dict:
    """한 번 굽기 — Q08 · Q09 CardResult. 🚨 결과 값을 찍지 않는다."""
    t0 = time.time()
    fm = formations(ctx)
    T8, R8, T9, R9 = {}, {}, {}, {}
    for v in Q08_VARS:
        T8[v], R8[v] = build_q08(ctx, v)
    for v in Q09_VARS:
        T9[v], R9[v] = build_q09(ctx, v)
    fr8 = {v: ctx.stock_fr(T8[v], reb=3, basis="TR") for v in Q08_VARS}
    fr9 = {v: ctx.stock_fr(T9[v], reb=3, basis="TR") for v in Q09_VARS}
    v0 = ctx.V0()
    b0 = sleeve_beta(ctx, v0)
    # Q08 G4
    true8 = dbeta_down(ctx, fr8["V1"], v0, bb=b0)
    c3_pos = dbeta_down(ctx, fr8["V1"], fr8["C3"]) > 0
    tp = time.time()
    draws8 = []
    for i in range(NPERM):
        fri = ctx.stock_fr(plac_q08(ctx, i), reb=3, basis="TR")
        draws8.append(dbeta_down(ctx, fri, v0, bb=b0))
        del fri
    sec8 = round(time.time() - tp, 1)
    p95 = float(np.percentile(draws8, 95)) if draws8 else None
    n_diff = sum(1 for m in fm if set(T8["V1"][m]["w"]) != set(ctx.V0_targets[m]["w"]))
    prep8 = [prep_q08(ctx, m) for m in fm]
    ecm = ec_method_check(ctx, T8, T9)
    q08 = {"code": "Q08", "cls": "B", "slot": "B2",
           "fr": fr8["V1"], "fr_pr": ctx.stock_fr(T8["V1"], reb=3, basis="PR"), "fr20": ctx.stock_fr(T8["V1"], reb=3, basis="TR", cost=COST20),
           "controls": {"C3": fr8["C3"]},
           "arms": {"pool45": fr8["pool45"], "pool90": fr8["pool90"], "C3b": fr8["C3b"], "Q09": fr9["rule"]},
           "placebo": {"P_shuffle": {"stat": "하락월(39) 평균 Δβ(위약 − V0) · 60 후보 사이에서 P 무작위 순열 · 30 · 20% 상한 시총 가중 · 씨앗 SEED + i",
                                     "draws": draws8, "true": true8, "p95": p95}},
           "perm": None,
           "g4": {"C3_dbeta_down_pos": bool(c3_pos), "placebo_ge95": bool(p95 is not None and true8 >= p95)},
           "label_caps": {},
           "f0": {"ok": n_diff > 0, "why": "카드에 F0 없음 — V1 이 V0 와 다른 편입 %d/%d" % (n_diff, len(fm))},
           "targets_hash": thash(T8["V1"]),
           "log": {"interpretation": INTERP, "not_run": {"PMFG": "networkx 없음 — 사전등록 §2(i) · 돌리지 않음"},
                   "formations": [{k: P[k] for k in ("m", "n_U", "N", "rho_bar", "Rb_off", "miss", "fp_fallback", "dup_tickers", "nocik_net", "net", "last_px_date", "win0")} for P in prep8],
                   "selection": {v: R8[v] for v in Q08_VARS}, "hashes": {v: thash(T8[v]) for v in Q08_VARS},
                   "turn": {v: fr8[v].get("turn") for v in Q08_VARS}, "turn_proxy": {v: _proxy_turn(T8[v]) for v in Q08_VARS},
                   "exante_fp_beta": {v: exante_beta(ctx, T8[v]) for v in ("V1", "C3", "C3b")},
                   "ec_method_check": ecm, "delist_frozen": {v: delist_frozen(ctx, T8[v]) for v in Q08_VARS},
                   "v0_dup_both": v0_dups(ctx), "issuer_multi": {v: issuer_multi(T8[v]) for v in Q08_VARS},
                   "v0_issuer_multi": issuer_multi(ctx.V0_targets),
                   "placebo": {"n": len(draws8), "sec": sec8}, "sec": round(time.time() - t0, 1)}}
    # Q09 K4
    tk = time.time()
    xa, hd = [], []
    for i in range(NPERM):
        fri = ctx.stock_fr(plac_q09(ctx, i), reb=3, basis="TR")
        a, b = x_all_h_down(ctx, fri)
        xa.append(a)
        hd.append(b)
        del fri
    ta, th = x_all_h_down(ctx, fr9["rule"])
    prep9 = [prep_q09(ctx, m) for m in fm]
    q09 = {"code": "Q09", "cls": "M", "slot": None,
           "fr": fr9["rule"], "fr_pr": ctx.stock_fr(T9["rule"], reb=3, basis="PR"), "fr20": ctx.stock_fr(T9["rule"], reb=3, basis="TR", cost=COST20),
           "controls": {"K1": fr9["K1"], "K2": fr9["K2"], "K3": fr9["K3"]},
           "arms": {},
           "placebo": {"K4_allX": {"stat": "전 월 평균 X · 걸러진 풀 무작위 20(각 5%) · 씨앗 SEED + i", "draws": xa, "true": ta},
                       "K4_downH": {"stat": "하락월(39) 평균 H = X − 0.1(β̂ − 1)(SPYTR − rf) · 같은 뽑기", "draws": hd, "true": th}},
           "perm": None, "g4": {}, "label_caps": {},
           "f0": {"ok": all(P["N"] >= M20 for P in prep9), "why": "카드에 F0 없음 — 걸러진 풀 최소 %d" % min(P["N"] for P in prep9)},
           "targets_hash": thash(T9["rule"]),
           "log": {"interpretation": INTERP, "arm_of": "Q08", "not_run": {"PMFG": "networkx 없음 — 사전등록 §2(i) · 돌리지 않음"},
                   "K5": "hedge_ctrl = qbatch_core.evaluate(fr)['hedge_ctrl'](러너 lite 가 싣는다)",
                   "formations": [{k: P[k] for k in ("m", "n_spx", "n_reit", "n_elig", "N", "rho_bar", "sec_src", "sec_month", "dup_tickers", "net", "last_px_date", "win0")} for P in prep9],
                   "selection": {v: R9[v] for v in Q09_VARS}, "hashes": {v: thash(T9[v]) for v in Q09_VARS},
                   "sector_weights": {v: sector_weights(ctx, T9[v]) for v in ("rule", "K1", "K2")},
                   "exante_fp_beta": {v: exante_beta(ctx, T9[v]) for v in Q09_VARS},
                   "turn": {v: fr9[v].get("turn") for v in Q09_VARS}, "turn_proxy": {v: _proxy_turn(T9[v]) for v in Q09_VARS},
                   "ec_method_check": ecm, "delist_frozen": {v: delist_frozen(ctx, T9[v]) for v in Q09_VARS},
                   "issuer_multi": {v: issuer_multi(T9[v]) for v in Q09_VARS},
                   "placebo": {"n": len(xa), "sec": round(time.time() - tk, 1)}, "sec": round(time.time() - t0, 1)}}
    return {"Q08": q08, "Q09": q09}


def main() -> int:
    a = sys.argv[1:]
    if not a:
        r = selftest()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["ok"] else 1
    ctx = Q.Ctx()
    if "--dry" in a:
        print(json.dumps(dry(ctx), ensure_ascii=False, indent=1, default=str))
        return 0
    if "--smoke" in a:
        global NPERM
        NPERM = 3
        print(json.dumps(Q.blind_smoke(run, ctx), ensure_ascii=False, indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
