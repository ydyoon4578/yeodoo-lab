# -*- coding: utf-8 -*-
"""build/x_adapter.py — 배치 X S 층 어댑터: D(얼린 V02 LBS 선정 · 이름당 20% 상한) 목표 → 얼린 q_switch 책 · 얼린 V0 경로와 혼합 · 짝맞춤 시험.

설계 원본(구속): xbatch_research.json action(D_basket · execution · proposition_1) · evaluation.S_layer · data_plan.stock_layer · combiner.applicability_APP ·
  decisions D-2 · UF-6 · UF-7 — 저장소 밖 스크래치. 이 파일은 설계를 다시 짓지 않는다.

두 자식 과정(메모리 ≤ 3 GB · 한 번에 하나 · 작업자 ≤ 2)
  D 자식(배치 V 핀 판 임시 뿌리 vroot = 자료 핀 커밋 DATA_PIN 의 build/ + data/ · 배치 V 얼린 코드 blob 단언 · v_data --check 파일 핀 + 폴더 요약 통과 · K7)
    V02 선정 = v_cards.SLayer.selections(spec_of("V02")) — 결정 달 2010-01 ~ 2026-07(버퍼 경로는 VBATCH 와 같은 첫 달부터) ·
    입력은 가벼운 층(members · w_B · me · signals(beta_fp · sector)) — V02 가 읽는 칸은 v_data.Layer.inputs 와 같다(ear · ch · ins 는 V02 가 읽지 않는다).
    D 목표 w_D(m) = eg30plus.cap_weights(선정 이름 시총, 0.20)(얼린 · EG30 과 같은 반복) · β̂_D(m) = Σ w_D·β̂_FP(없으면 1.0 · v_core K2).
    🔗 짝맞춤 A: 같은 선정으로 얼린 v_cards.target_book(θ = 1) 을 다시 짓고 배치 V F0 넘김 파일(vb_books.json.gz · sha256 = data/_vb_f0.json
       gegd_pins.in_sha)의 V02 책과 120개월 모두 같아야 한다(키 집합 같음 · |차| ≤ 1e−12) — 하나라도 다르면 D 목표를 쓰지 않는다.
    선정 해시 = sha256(정규 JSON {달: 정렬 티커}) — 등록 문서에 싣는다(«D 해시»).
  S 자식(임시 뿌리 = 코드 핀 1d81f083 의 build/ + 자료 판 bef4eea8:data/ + 940f0bda 의 가격 판 + P3 덮어쓰기 — qfwd_adapter.build_root 와 같은 뿌리 ·
    이 파일은 그 함수를 부르지 않고 같은 규칙을 따로 짓는다(QFWD 파일은 건드리지 않는다) · 얼린 blob 단언)
    V0 = qbatch_core.Ctx().V0_targets → q_switch.offense_v0(분기 · 흘러감) · D = 얼린 q_switch.Book(D 책 자식의 경로 · 아래 K6) ·
    SPY = q_switch.spy_book · T-bill = q_switch.tbill_book · 두 장부 사이의 몫(공격 몫 = 1 − a)은 T+1 에 바꾼다(mix_t1 · 아래 K2).
    팔(주 행 T+1): V0(몫 1) · X(1 − a) · X_half(1 − ½a · a_op) · STATIC(1 − ā) · IDX(D 대신 SPY) · CASH(같은 Δβ: f = a·(β̂_C − β̂_D)/β̂_C → T-bill) ·
        DIL(c·V0 + (1 − c)·SPY · c = 1 + e/x_V0 · [0, 1]) · 20bp 판(X20 · V0_20) · D0 행(X · V0 — 얼린 q_switch.mix_fr · d_m 종가 되맞춤 · 보고만).
    APP_S(m) = 1[β̂_C(m) − β̂_D(m) ≥ 0.10] · β̂_C = V0 보유가중(마지막 편입 목표를 m 까지 가격으로 흘린 비중) × β̂_FP(D 자식 표 · 없으면 1.0).
    🔗 V0 재현(수익 없이): Ctx.V0_targets 의 해시 두 판 = QFWD 명세 §6 짝맞춤 표(V0_LT · V0_BL) — 다르면 멈춘다.
    🔗 짝맞춤 B: 몫 ≡ 1 의 펀드 월 초과 = Ctx.V0() 의 월 초과(T+1 행 · D0 행 모두 |차| ≤ 1e−10 · 명제 1 의 실자료판) · 되맞춤 거래 0.
    🔗 짝맞춤 C: 몫 {0, 1} 인 X 의 T+1 행 = 얼린 q_switch.switch_fr(pos_from_daily(delay 1))(|차| ≤ 1e−10) — T+1 행을 얼린 교체 틀이 받친다.
  선언(명세가 비워 둔 것): K1 «D 목표가 선다» = 그달 World(1d81f083 판)에 값이 선 이름이 ≥ 1 이고 VBATCH 목표 비중의 ≥ 0.90 이 옮겨졌다(나머지는 비례 재정규화) ·
    K2 S 층 주 행 = T+1(명세 action.execution «결정 d_m 종가 · 체결 T+1 종가» · S_layer.reports_only «D0 행» — 주 행은 T+1 이다):
    두 장부(V0 · D)의 자기 되맞춤은 얼린 틀 그대로(d_m 종가) · 둘 사이 몫 교체만 보유월 첫 거래일(T+1) 종가 · 창 첫 달의 앞 몫은 V0(1) ·
    펀드 월 초과는 달력 달(d_m → d_m · 얼린 fund_from_path). 명세 «혼합은 얼린 q_switch.mix_fr» 는 D0 행으로 그대로 싣는다 ·
    K3 β̂ 가 없는 이름은 1.0(v_core K2) · 티커 «.»/«-» 는 «-» 로 맞춘다 · K4 CASH 의 β̂_C ≤ 0 이면 f = 0 ·
    K5 보고 요약은 얼린 qbatch_core.evaluate(이름 붙은 급락 6 · 급등 6 · 기계적 다리 8 · 반등 8 · 해마다 · 이동 12개월 · 헤지 대조) ·
    K6 D 책 가격 판(F0 커버리지 · 수익을 보지 않고 정함): 얼린 V0 뿌리 World(940f0bda 가격 판)에는 뒤에 편출된 D 이름(AGN · RTN · ATVI · RHT · COL …)의
    가격 키가 없어 옮긴 몫이 0.89 까지 떨어졌다(2017-11). 명세 data_plan.stock_layer «PIT 편출 가격은 pit_px.json 만» 에 따라 D 책은 배치 V 핀 판 World
    (임시 뿌리 vroot data/ · v_data --check 통과 · pit_panel e2073703)에서 얼린 qbatch_core.stock_path(reb 1 · 0 · 10 · 20bp)로 짓고(D 책 자식), S 자식이
    날짜 문자열로 뿌리 격자에 맞춰 얼린 q_switch.Book 으로 읽는다(S 창 거래일 집합이 같아야 한다 — 단언). 키 옮기기는 배치 V 선정이 쓴 가격 키 그대로
    (같은 pit_panel · 같은 자료) → 없을 때만 그달 명단 · 결과 120개월 모두 옮긴 몫 1.0(K1 문턱 0.90 은 그대로). V0 책은 얼린 뿌리 World 그대로(V0 재현).
    K7 배치 V 핀 판 임시 뿌리(검토 반영 2026-09-27): D 자식 · D 책 자식 · S 커버리지(dbook)는 작업 트리가 아니라 자료 핀 커밋 DATA_PIN(c6a35ff0 ·
    origin/main 조상 · 그 data/ 가 data/_vb_manifest.json 의 파일 핀 20 · 폴더 요약 4 와 모두 같다)의 build/ + data/ 를 git archive 로 꺼낸 캐시 s/vroot 에서 돈다 —
    CI 가 작업 트리 data/(stocks · pit_px · shares_yf …)를 매일 갈아도 굽기 날짜와 무관하게 같은 판이다. 러너 판 점검(frozen_check)이 태그 전에 vroot_check 로 본다.
🚨 이 파일은 수익을 찍지 않는다. S 자식의 산출(월 계열)은 캐시(%TEMP%/xbatch_cache/s)에만 · 눈가린 연기는 열지 않고 지운다.
🚨 20년 규칙: S 층 보유월 2016-09 ~ 2026-08(120) · PIT 워밍업 2014-06~(D 자식 결정 달 2010-01~ 은 VBATCH 선정 경로 재현 — 20년 안).

  python build/x_adapter.py --selftest            합성만(명제 1 · mix_t1 짝 · switch_fr 짝 · 20% 상한 · 키 옮기기 · APP · 해시)
  python build/x_adapter.py --blind-smoke          D 자식 · D 책 자식 · 뿌리 · S 자식을 실자료로 끝까지(모양 · 개수 · 참/거짓 · 시간만 · S 산출은 열지 않고 지운다)
  python build/x_adapter.py --s-coverage [--root]  F0 — D 목표 → World 키 옮김(몫 · 개수 · 못 옮긴 티커 · 수익 없음)
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback

import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# ══════════════════════════════════════════════════════════════════════════
#  핀
# ══════════════════════════════════════════════════════════════════════════
CODE_PIN = "1d81f083a404c68e23d15a649ef6f0a340d4d95c"               # 배치 Q 등록 커밋(V0 얼린 코드)
BUILD_TREE = "e221c9817b8baa4e225e0382ff4cf2c15fbcb8c8"             # git rev-parse 1d81f083:build
P1_PRICE, P1_BASE = "940f0bda99ae1cc99299a43a06b30b9fa267d734", "bef4eea8c98572bd05815d44bd0744d9ce7ed370"
SNAP_FILES = ("data/stocks.json", "data/pit_px.json", "data/sd")
P3 = {                                                             # 코드 핀 blob 으로 덮는 고정 입력(qfwd_adapter.P3 와 같다 — selftest 가 대조)
    "data/_q07_ltd_fits.json": "1c670bc0a7d76b23fd1e916f842cfb8a20c3295d",
    "data/_eg_q5_scores_pitgics.json": "21f43d226463f3978982acc077fbca1576780f33",
    "data/_eg_q5_scores_pitgics_pre.json": "cb96d4bf7cd35786c0b69d369df0a317db137373",
    "data/_eg_q5_scores.json": "2868509a502b5104e49d378457451f80eb694d17",
    "data/pit_gics_sectors.json": "4b20f0e6a02595ec81db4ceaa877afe5628201e8",
    "data/pit_gics.json": "f4163293cc92f1386ef5c5f31521d6d302a5c228",
    "data/mech_episodes.json": "d67a2a74b486aff7f3a46d0f2a9bebe104df669f",
    "data/_eg_best.json": "cc58f30c84886554c76fecf6df5dc85974eb09f1",
    "data/_eg30plus.json": "c205f1365e924ebf097b200042133369d7de3f3d"}
ROOT_FROZEN = {                                                    # 뿌리 build/ 에서 단언(1d81f083 판)
    "qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d", "q_switch": "c0e52a85d24dfd6a3cd5db2c82aa514b3358dec5",
    "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628", "qg_lab": "ca95e32b627c1dc9b0136c886eb42b5fb3b0daea",
    "pit_panel": "ae044a5d3b8af4b6b8aee12d3879f5c97d4885fb", "pit_quarantine": "329e5d9ff15be4c07052921dfff9a41afbcc2513",
    "stoploss": "e2408e98d03216146cf809d6643c68947130c727", "tech_backtest": "4bf3424b71986ef1ee0eec19c05fda3efcdbda79",
    "rally_pattern": "25bbe121aec76be3a54c62a5bb5567c63666cbfa", "index_members": "7850ef55f5b89583b24e190b250a14c897c93395",
    "mech_episodes": "161080fd9244c060a7a94c559044de3e3ddcc27c"}
V_FROZEN = {                                                       # 작업 사본 · vroot build/ 에서 단언(배치 V 등록 핀 · PREREG-2026-09-27-VBATCH §6)
    "v_cards": "aadaf24f173579d3f3146014aa150a4ca07eb0a5", "v_core": "bdba648f1d790748cd5008ceeea3c5eee9d733c8",
    "v_data": "f08782e4f2d5e5d3ee4e9c491e1cd550f2c8847a", "v_pit": "5983b9902b106a2b234db05a397e9ce0b73fb689",
    "v_fund": "2d8093f0009c09b05f597e07eea10f53c8d18b8e", "v_px_split": "c747ae4030c4f2f5bc97b8e634f3a80a36d04028",
    "v_cond": "d25914deb89490410ea2dca56b5999356628821e", "pit_panel": "e207370369aaa2d71d92dcac4ecbcd79d0df9b38",
    "pit_alias": "ead714d97c87c3588a8fdc2ca4b1c57c5a497c0b", "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628"}
VB_BOOKS_SHA = "c1aeff7df4d02c03742f224623f109e89bb6873ea8e18eaf6ff6f53862784c1b"   # = data/_vb_f0.json gegd_pins.in_sha
DATA_PIN = "c6a35ff0168e5ea21c2ab2d18680550452511a3a"             # K7 배치 V 핀 판 자료 커밋(origin/main · 2026-09-27 · data/ = _vb_manifest 파일 핀 20 · 폴더 요약 4)
VROOT_PATHS = ("build/", "data/")                                   # 임시 뿌리 vroot 가 꺼내는 경로(git archive DATA_PIN)
V0_HASH_PIN = {"V0_LT": "ec0a2aa43f1efffa3d59b5d5b78268153a2bf7f36947ab2ed6345c61c0370202",     # = qfwd_adapter.PARITY(명세 §6) — 읽기만 · 대조는 selftest
               "V0_BL": "132008e66ddf2ef85ea3acf408ae213641f92a0a0a4f7ea3118b6963d2a3c077"}
A_OP = 0.5                                                         # 사용자 U1(½ 판 보고 · 관문은 a 1)
DBOOK_FROZEN = {                                                   # D 책 자식(vroot · 배치 V 핀 판 World) 이 단언하는 얼린 blob
    "qbatch_core": "38ecb2b3f38ac7996cbd10957f7fe665a3758a8d", "eg30plus": "5688b266adece152d2dc72f911bb7a6ac977d628",
    "qg_lab": "ca95e32b627c1dc9b0136c886eb42b5fb3b0daea", "pit_panel": "e207370369aaa2d71d92dcac4ecbcd79d0df9b38",
    "pit_alias": "ead714d97c87c3588a8fdc2ca4b1c57c5a497c0b", "pit_quarantine": "329e5d9ff15be4c07052921dfff9a41afbcc2513",
    "stoploss": "e2408e98d03216146cf809d6643c68947130c727", "tech_backtest": "4bf3424b71986ef1ee0eec19c05fda3efcdbda79",
    "v_data": "f08782e4f2d5e5d3ee4e9c491e1cd550f2c8847a"}
DBOOK_COSTS = (0.0, 0.0010, 0.0020)
D_CAP = 0.20
D_MAP_MIN = 0.90
APP_MIN = 0.10
D_FIRST_DECISION = "2014-05"                                       # S 층 PIT 워밍업 첫 보유월 2014-06 의 결정 달(v_cards.S_ARM_FROM)
S_FORM = ("2016-08", "2026-07")
ENV = {"PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1", "PYTHONIOENCODING": "utf-8", "MKL_NUM_THREADS": "1"}
TIMEOUT = {"d": 3600, "s": 5400, "archive": 900}


def blob_sha1(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def _rbytes(p):
    with open(p, "rb") as f:
        return f.read()


def _wjson(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p + ".part", "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, allow_nan=True)
    os.replace(p + ".part", p)


def _rjson(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def canon_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")).hexdigest()


def assert_dir_blobs(build_dir, want):
    bad = {}
    for m, b in want.items():
        p = os.path.join(build_dir, m + ".py")
        got = blob_sha1(_rbytes(p).replace(b"\r\n", b"\n")) if os.path.exists(p) else None
        if got != b:
            bad[m] = (got or "없음")[:12]
    if bad:
        raise SystemExit("🚨 얼린 blob 불일치 %s — 부르지 않는다" % bad)
    return True


# ══════════════════════════════════════════════════════════════════════════
#  순수 도우미(부모 · 자식 · 합성 시험이 함께 쓴다)
# ══════════════════════════════════════════════════════════════════════════
def map_targets(tgt_w, universe_pairs, priced):
    """VBATCH 목표 {티커: 비중} → World 키 {키: 비중}(값이 선 이름만 · 재정규화) — 돌려주는 것 (w_k, names{키: 티커}, 옮긴 몫, 이름 수)."""
    tk2k = {}
    for t, k in universe_pairs:
        tk2k.setdefault(t, k)
        tk2k.setdefault(t.replace(".", "-"), k)
    w, names, moved = {}, {}, 0.0
    for t, x in tgt_w.items():
        k = tk2k.get(t) or tk2k.get(t.replace("-", "."))
        if k is None or not priced(k):
            continue
        w[k] = w.get(k, 0.0) + float(x)
        names[k] = t
        moved += float(x)
    tot = sum(w.values())
    if tot > 0:
        w = {k: v / tot for k, v in w.items()}
    return w, names, moved, len(w)


def app_flags(beta_c, beta_d, thr=APP_MIN):
    """APP = 1[β̂_C − β̂_D ≥ 0.10] · 어느 쪽이 없으면 0."""
    out = {}
    for m in beta_c:
        bc, bd = beta_c.get(m), beta_d.get(m)
        out[m] = 1.0 if (bc is not None and bd is not None and (bc - bd) >= thr - 1e-12) else 0.0
    return out


def book_beta(w, beta):
    """보유가중 β̂(없으면 1.0 · v_core K2)."""
    return float(sum(x * (beta.get(t) if beta.get(t) is not None else 1.0) for t, x in w.items()))


def drifted_weights(tgt, px_ratio):
    """편입 목표 {키: 비중} 을 가격 비(편입 → m)로 흘린 비중(합 1) — 비가 없으면 1."""
    v = {k: x * (px_ratio.get(k) if px_ratio.get(k) is not None else 1.0) for k, x in tgt.items()}
    s = sum(v.values())
    return {k: x / s for k, x in v.items()} if s > 0 else dict(tgt)


def beta_c_rows(Wd, T0, D, months):
    """β̂_C(V0 보유가중 · 마지막 편입 목표를 m 까지 가격으로 흘린 비중) · β̂ 가 선 이름 수 · β̂ 가 선 비중 몫(K3 커버리지) — 달마다.
    β̂ = D 자식 beta_union(VBATCH FP β̂) · 없으면 1.0(K3). S 자식(APP_S)과 F0 커버리지 자식이 같은 식을 쓴다(수익 없음 · 비중만)."""
    forms = sorted(T0)
    out = {}
    for m in months:
        f = max(x for x in forms if x <= m)
        i, i0 = Wd.me[m], Wd.me[f]
        tg = T0[f]["w"]
        pr = {}
        for k in tg:
            p = np.asarray(Wd.PX[k], float)
            pr[k] = (float(p[i] / p[i0]) if (p[i0] == p[i0] and p[i0] > 0 and p[i] == p[i] and p[i] > 0) else None)
        wk = drifted_weights(tg, pr)
        bu = {_tk(t): v for t, v in ((D.get("beta_union") or {}).get(m) or {}).items()}
        wt = {}
        for k, x in wk.items():
            t = _tk(T0[f]["names"].get(k, k.split("@")[0]))
            wt[t] = wt.get(t, 0.0) + x
        out[m] = {"beta_c": book_beta(wt, bu), "n_beta": int(sum(1 for t in wt if bu.get(t) is not None)),
                  "cov": float(sum(x for t, x in wt.items() if bu.get(t) is not None)), "n_names": len(wt)}
    return out


def mix_t1(F, shares, bO, bD, c, fund_from_path, s_pre=1.0):
    """S 층 주 행(T+1 체결 · 명세 action.execution «결정 d_m 종가 · 체결 T+1 종가») — mix_fr 와 같은 얼린 장부(bO · bD 의 비용 포함 일간 성장)를 쓰되
    보유월 k 의 첫 수익일(= 결정일 d_m 다음 거래일 T+1)은 앞 몫(흘러간 구성)으로 들고 그날 종가에 몫 s_k 로 되맞춘다(편도 c · 현금 쪽 무비용).
    창 첫 달의 앞 몫은 s_pre(기본 1 = V0 — 창 앞 결정은 채점 밖 · M 층 «첫 결정의 앞 노출 0» 과 같은 뜻).
    짝맞춤: 몫 ≡ 1 이면 V0 경로(Ctx.V0) · 몫 ∈ {0, 1} 이면 얼린 q_switch.switch_fr(pos_from_daily(delay 1)) 와 같은 경로(교체일 T+1 은 두 장부의 자기
    되맞춤 날(d_m)이 아니라서 비용 규칙도 같다 — pairing_C 가 실자료로 확인한다). 펀드 월 초과는 달력 달(d_m → d_m · fund_from_path)."""
    lO = bO.lg0 + bO.lf.get(c, 0.0)
    lD = bD.lg0 + bD.lf.get(c, 0.0)
    gO, gD = np.exp(lO), np.exp(lD)
    shares = np.asarray(shares, float)
    nM = len(F.months)
    assert len(shares) == nM and shares.min() >= 0 and shares.max() <= 1 and 0.0 <= s_pre <= 1.0
    VO, VDv = float(s_pre), float(1.0 - s_pre)
    path = {F.i0: 1.0}
    trs = 0.0
    for k in range(nM):
        a = F.mstart[k]
        b = F.mstart[k + 1] if k + 1 < nM else F.T
        for j in range(a, b):
            VO *= gO[j]
            VDv *= gD[j]
            if j == a:
                V = VO + VDv
                s1 = shares[k]
                tO, tD = abs(s1 * V - VO), abs((1 - s1) * V - VDv)
                cost = c * ((0.0 if bO.cash else tO) + (0.0 if bD.cash else tD))
                trs += (tO + tD) / V
                V -= cost
                VO, VDv = s1 * V, (1 - s1) * V
            path[int(F.day[j])] = VO + VDv
    own = sum(float((1.0 - np.exp(bk.lf[c])).sum()) / c * float(np.mean(w)) for bk, w in ((bO, shares), (bD, 1 - shares)) if c in bk.lf)
    fr = fund_from_path(F.G, {"path": path, "turn": (trs + own) / 2.0 / F.years}, F.months, cost=c, basis="TR")
    fr["cost_drag"] = float(c * (trs + own) / F.years * 100)
    return fr


def t1_pos(F, shares_binary):
    """몫 {0, 1}(보유월 k) → 얼린 q_switch.pos_from_daily(delay 1) 에 넘길 날짜 상태 {날짜: 1 공격 · 0 수비} — 결정일 d_{m_k} 부터 다음 결정일 전날까지 몫 k ·
    창 첫 결정일 앞은 상태 없음(= 공격 · mix_t1 의 s_pre 1 과 같다)."""
    G = F.G
    sh = np.asarray(shares_binary, float)
    assert set(np.unique(sh)).issubset({0.0, 1.0})
    ends = [G.me[m] for m in F.months] + [F.iE + 1]
    st = {}
    for k in range(len(F.months)):
        for i in range(ends[k], min(ends[k + 1], len(G.dates))):
            st[G.dates[i]] = int(sh[k])
    return st


# ══════════════════════════════════════════════════════════════════════════
#  D 자식(vroot · 배치 V 코드 · K7)
# ══════════════════════════════════════════════════════════════════════════
class _LightLayer:
    """v_data.Layer 꼴 — V02 가 읽는 입력만(members · w_B · me · signals(beta_fp · sector)) · ear · ch · ins 는 빈 표."""

    def __init__(self, U):
        self.pit = U

    def inputs(self, m):
        U = self.pit
        return {"members": U.members(m), "w_B": U.w_B(m), "me": U.me(m), "signals": U.signals(m, which=("beta_fp",)),
                "irrx": {}, "ear": {}, "ch": {}, "ins": {}}


def _nrm(p):
    return os.path.normcase(os.path.abspath(p))


def _v_pins_full(VD, want_root=None):
    """배치 V 자료 핀 — v_data.check_pins(파일 20 · French) + 폴더 요약 4(_vb_manifest lab_dirs) · 뿌리가 vroot 인가. (ok, 문제 목록)."""
    ok, bad = VD.check_pins()
    bad = list(bad)
    man = VD.read_json(VD.MANIFEST)
    for rel, rec in (man.get("lab_dirs") or {}).items():
        dg, _n = VD._lab_dir_sha(rel)
        if rec.get("digest") and dg != rec["digest"]:
            bad.append("lab dir %s: 요약 다름" % rel)
    if want_root is not None and _nrm(VD.ROOT) != _nrm(want_root):
        bad.append("v_data 뿌리가 vroot 가 아니다")
    return not bad, bad


def _vcheck_child(job):
    """판 점검용(굽기 전) — vroot build/ blob · 배치 V 자료 핀(파일 · 폴더) · 뿌리. 값 없음."""
    assert_dir_blobs(HERE, V_FROZEN)
    assert_dir_blobs(HERE, DBOOK_FROZEN)
    import v_data as VD
    ok, bad = _v_pins_full(VD, job.get("root"))
    _wjson(job["out"], {"ok": bool(ok), "bad": bad[:10], "data_pin": DATA_PIN})
    return 0


def _d_child(job):
    t0 = time.time()
    assert_dir_blobs(HERE, V_FROZEN)
    import v_data as VD
    import v_pit as VP
    import v_cards as VK
    import eg30plus as E
    rep = {"started": time.strftime("%Y-%m-%d %H:%M:%S")}
    ok_pins, bad_pins = _v_pins_full(VD, job.get("root"))          # 배치 V 자료 핀(명세 SHA · 폴더 요약 · vroot) — 틀리면 D 목표를 짓지 않는다
    rep["v_data_check_ok"] = bool(ok_pins)
    if not ok_pins:
        raise SystemExit("🚨 배치 V 자료 핀 불일치 — %s" % bad_pins[:3])
    f0 = VD.read_json(VD.lab_path("data/_vb_f0.json"))
    dec = f0.get("decisions") or {}
    over = {k: dec[k] for k in ("use_sp", "prof") if k in dec}
    spec = VK.spec_of("V02", **over)
    U = VP.Universe.real(with_vd1=True)
    SL = VK.SLayer(_LightLayer(U))
    sels = SL.selections(spec)
    rep["n_sel_months"] = len(sels)
    out_m, beta_union, sel_map = {}, {}, {}
    for m in SL.months:
        if m < D_FIRST_DECISION:
            continue
        X = SL.cross(m)
        mask = sels.get(m)
        if mask is None or not mask.any():
            out_m[m] = None
            continue
        idx = np.flatnonzero(mask)
        me = {X.t[i]: float(X.me[i]) for i in idx}
        w = E.cap_weights(me, D_CAP)
        beta = {X.t[i]: (float(X.beta[i]) if np.isfinite(X.beta[i]) else None) for i in range(X.n)}
        out_m[m] = {"w": w, "keys": {X.t[i]: X.k[i] for i in idx}, "beta_D": book_beta(w, beta), "n": int(len(idx)),
                    "max_w": float(max(w.values()))}
        sel_map[m] = sorted(X.t[i] for i in idx)
        if S_FORM[0] <= m <= S_FORM[1]:
            beta_union[m] = beta
    # 짝맞춤 A — θ = 1 책 = VBATCH F0 넘김
    pA = {"vb_books_sha_ok": False, "n_months": 0, "n_match": 0, "first_mismatch": None}
    vbp = job.get("vb_books")
    if vbp and os.path.exists(vbp):
        sha = hashlib.sha256(_rbytes(vbp)).hexdigest()
        pA["vb_books_sha_ok"] = (sha == VB_BOOKS_SHA and sha == (f0.get("gegd_pins") or {}).get("in_sha"))
        with gzip.open(vbp, "rt", encoding="utf-8") as f:
            VB = json.load(f)["months"]
        for m in sorted(VB):
            if not (S_FORM[0] <= m <= S_FORM[1]):
                continue
            ref = (VB[m].get("books") or {}).get("V02")
            X = SL.cross(m)
            w, _ = VK.target_book(X, spec, sels.get(m), 1.0)
            got = X.book(w) if w is not None else {}
            pA["n_months"] += 1
            same = ref is not None and set(ref) == set(got) and max((abs(ref[t] - got[t]) for t in ref), default=0.0) <= 1e-12
            if same:
                pA["n_match"] += 1
            elif pA["first_mismatch"] is None:
                pA["first_mismatch"] = m
    pA["pass"] = bool(pA["vb_books_sha_ok"] and pA["n_months"] == 120 and pA["n_match"] == 120)
    doc = {"kind": "xbatch_d_targets", "note": "D = 얼린 V02 LBS 선정 · 이름당 20% 상한(eg30plus.cap_weights) — 비중 · β̂ 만(수익 없음)",
           "spec": {k: v for k, v in spec.items() if isinstance(v, (str, int, float, bool, type(None)))}, "months": out_m, "beta_union": beta_union,
           "sel_hash": canon_hash(sel_map), "pairing_A": pA, "v_blobs": V_FROZEN, "rep": rep}
    if job.get("fidelity"):
        # D_S 달 수익(2014-06 ~ 2026-08 · 얼린 SLayer.path · 전량 체결) — 🚨 수익 · F0 충실도 corr 전용 파일(캐시) · 연기에서는 지운다
        T = {m: v["w"] for m, v in out_m.items() if v}
        import v_core as C
        P = SL.path(T, fill=1.0, start=D_FIRST_DECISION)
        _wjson(job["fidelity"], {"kind": "xbatch_d_path", "S": {str(k): (None if v != v else float(v)) for k, v in P["S"].items()},
                                 "beta": {str(k): float(v) for k, v in P["beta"].items()}})
    doc["sec"] = round(time.time() - t0, 1)
    _wjson(job["out"], doc)
    return 0


# ══════════════════════════════════════════════════════════════════════════
#  뿌리(1d81f083 build/ + bef4eea8 data/ + 940f0bda 가격 판 + P3)
# ══════════════════════════════════════════════════════════════════════════
def _git(args, repo, text=True, timeout=None):
    return subprocess.run(["git", "-C", repo, "-c", "core.autocrlf=false"] + args, capture_output=True, text=text, timeout=timeout)


def _archive(repo, commit, paths, dest, timeout=TIMEOUT["archive"]):
    p = subprocess.run(["git", "-C", repo, "-c", "core.autocrlf=false", "archive", "--format=tar", commit] + list(paths),
                       capture_output=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError("git archive %s 실패: %s" % (commit[:12], p.stderr[:200]))
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as tf:
        n = 0
        for mem in tf.getmembers():
            if mem.isfile():
                tgt = os.path.join(dest, *mem.name.split("/"))
                os.makedirs(os.path.dirname(tgt), exist_ok=True)
                with open(tgt, "wb") as f:
                    f.write(tf.extractfile(mem).read())
                n += 1
    return n


def build_root(dest, repo, force=False):
    """임시 뿌리 — 표지 파일(root.json)이 핀과 같으면 다시 짓지 않는다. 돌려주는 것 (root, 보고)."""
    root = os.path.join(dest, "root")
    mark = os.path.join(dest, "root.json")
    want = {"code_pin": CODE_PIN, "base": P1_BASE, "price": P1_PRICE, "p3": P3, "frozen": ROOT_FROZEN, "adapter": blob_sha1(_rbytes(os.path.abspath(__file__)))}
    if not force and os.path.exists(mark) and os.path.isdir(root):
        try:
            if _rjson(mark).get("want") == want:
                assert_dir_blobs(os.path.join(root, "build"), ROOT_FROZEN)
                return root, {"reused": True}
        except Exception:                                                  # noqa: BLE001
            pass
    t0 = time.time()
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(root)
    if _git(["rev-parse", "%s:build" % CODE_PIN], repo).stdout.strip() != BUILD_TREE:
        raise SystemExit("🚨 코드 핀의 build 트리가 %s 가 아니다" % BUILD_TREE[:12])
    n = _archive(repo, P1_BASE, ["data/"], root)
    qd = os.path.join(root, "data", "_qfwd")
    if os.path.isdir(qd):
        shutil.rmtree(qd)
    shutil.rmtree(os.path.join(root, "data", "sd"), ignore_errors=True)
    n += _archive(repo, P1_PRICE, list(SNAP_FILES), root)
    for rel, b in P3.items():
        blob = _git(["cat-file", "blob", "%s:%s" % (CODE_PIN, rel)], repo, text=False).stdout
        if blob_sha1(blob) != b:
            raise SystemExit("🚨 P3 %s blob 불일치" % rel)
        tgt = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(tgt), exist_ok=True)
        with open(tgt, "wb") as f:
            f.write(blob)
    _archive(repo, CODE_PIN, ["build/"], root)
    shutil.copyfile(os.path.abspath(__file__), os.path.join(root, "build", "x_adapter.py"))
    assert_dir_blobs(os.path.join(root, "build"), ROOT_FROZEN)
    _wjson(mark, {"want": want, "built": time.strftime("%Y-%m-%d %H:%M:%S"), "n_files": n, "sec": round(time.time() - t0, 1)})
    return root, {"reused": False, "n_files": n, "sec": round(time.time() - t0, 1)}


# ══════════════════════════════════════════════════════════════════════════
#  S 자식(뿌리 build/ 에서 · 얼린 V0 · q_switch)
# ══════════════════════════════════════════════════════════════════════════
def _tk(t):
    return (t or "").replace(".", "-")


def v0_target_hashes(T):
    """V0 목표 해시 두 판 — QFWD 명세 §6 짝맞춤 표의 V0_LT(q_ltd.thash · json sort_keys) · V0_BL(q_bmrot_leg.thash · 비중 12자리 반올림)와 같은 식.
    값(수익)이 아니라 목표 비중의 해시다 — 얼린 V0 가 재현됐는지를 수익을 보지 않고 확인한다."""
    lt = hashlib.sha256(json.dumps(T, sort_keys=True).encode("utf-8")).hexdigest()
    bl = hashlib.sha256(json.dumps({m: {"w": {k: round(v, 12) for k, v in sorted(x["w"].items())}} for m, x in sorted(T.items())},
                                   sort_keys=True).encode()).hexdigest()
    return {"V0_LT": lt, "V0_BL": bl}


def _eval_summary(ev):
    keep = ("n", "ann_ex", "te", "ir", "nw_t", "down_n", "down_mean", "down_win", "up_mean", "sleeve_beta", "turn", "years", "years_won", "n_years",
            "episodes", "crash_won", "surge_won", "mech", "hedge_ctrl", "halves", "roll12")
    return {k: ev.get(k) for k in keep}


def _map_month(Wd, m, rec):
    """D 목표(티커 비중) → 그달 World 키(값이 선 이름 · 재정규화) — (목표 | None, 옮긴 몫, 이름 수, K1 참/거짓)."""
    if not rec:
        return None, None, 0, False
    i = Wd.me[m]
    pairs = _d_pairs(Wd, m, rec)
    w, names, mv, n = map_targets(rec["w"], pairs, lambda k: (k in Wd.PX and Wd.PX[k][i] == Wd.PX[k][i] and Wd.PX[k][i] > 0))
    return ({"w": w, "names": names} if n >= 1 else None), mv, n, bool(n >= 1 and mv >= D_MAP_MIN - 1e-12)


def _d_pairs(Wd, m, rec):
    """K6 키 옮기기 — 먼저 배치 V 선정이 쓴 가격 키 그대로(같은 pit_panel · 같은 자료 판이라 같은 키 공간 · 날짜 인식 키 포함) ·
    그 키가 World 가격에 없을 때만 그달 World 명단(티커 → 키)으로."""
    keys = rec.get("keys") or {}
    direct = [(t, keys[t]) for t in rec["w"] if keys.get(t) in Wd.PX]
    return direct + list(Wd.universe(m, "union", False))


def _dbook_child(job):
    """D 책 경로(K6 · K7) — 배치 V 핀 판 World(vroot data/ · pit_panel e2073703 · pit_px.json — 명세 «PIT 편출 가격은 pit_px.json 만»)에서
    얼린 qbatch_core.stock_path(reb 1 · 비용 0 · 10bp · 20bp)로 짓는다. 🚨 경로 = 수익 계열 → 캐시에만 · 부모는 열지 않고 S 자식에 넘긴다."""
    t0 = time.time()
    assert_dir_blobs(HERE, DBOOK_FROZEN)
    import v_data as VD
    ok_pins, bad_pins = _v_pins_full(VD, job.get("root"))          # 배치 V 자료 핀(명세 SHA · 폴더 요약 · vroot) — 틀리면 짓지 않는다
    if not ok_pins:
        raise SystemExit("🚨 배치 V 자료 핀 불일치 — %s" % bad_pins[:3])
    import qbatch_core as Q
    import eg30plus as E
    Wd = E.World()
    D = _rjson(job["d_targets"])
    months = [m for m in Wd.months if S_FORM[0] <= m <= S_FORM[1]]
    assert len(months) == 120 and months[0] == S_FORM[0] and months[-1] == S_FORM[1], (months[:1], months[-1:], len(months))
    T_D, d_ok, moved, n_names = {}, [], {}, {}
    for m in months:
        tg, mv, n, ok = _map_month(Wd, m, (D["months"] or {}).get(m))
        T_D[m], moved[m], n_names[m] = tg, mv, n
        d_ok.append(ok)
    last = None
    for m in months:                                               # 빈 달은 앞 달 목표를 든다(d_ok 거짓으로 센다)
        if T_D[m] is None:
            T_D[m] = last
        last = T_D[m]
    if T_D[months[0]] is None:
        raise SystemExit("🚨 첫 달 D 목표가 없다")
    i0, iE = Wd.me[months[0]], Wd.me[Q.mshift(months[-1], 1)]
    dates = [Wd.dates[i] for i in range(i0, iE + 1)]
    paths, turn = {}, {}
    for c in DBOOK_COSTS:
        sl = Q.stock_path(Wd, T_D, reb=1, cost=c)
        paths["%.4f" % c] = [float(sl["path"][i]) for i in range(i0, iE + 1)]
        turn["%.4f" % c] = float(sl["turn"])
    doc = {"kind": "xbatch_d_book", "note": "🚨 D 책 일간 경로(수익) — 캐시 전용 · S 자식만 읽는다", "dates": dates, "paths": paths, "turn": turn,
           "d_ok": d_ok, "d_moved": [moved[m] for m in months], "d_names": [n_names[m] for m in months], "months": months,
           "blobs": DBOOK_FROZEN, "sec": round(time.time() - t0, 1)}
    _wjson(job["out"], doc)
    return 0


def d_book(force=False):
    """D 책 자식(vroot · K7) — 캐시 s/d_book.json(🚨 수익 경로 · 열지 않는다). 돌려주는 것 (경로, 보고)."""
    out = os.path.join(s_dir(), "d_book.json")
    dpath, _ = d_targets()
    mark = out + ".want.json"
    want = {"d_targets_sha256": hashlib.sha256(_rbytes(dpath)).hexdigest(), "blobs": DBOOK_FROZEN, "adapter": blob_sha1(_rbytes(os.path.abspath(__file__))),
            "data_pin": DATA_PIN}
    if os.path.exists(out) and not force and os.path.exists(mark):
        try:
            if _rjson(mark) == want:
                return out, {"reused": True}
        except Exception:                                                  # noqa: BLE001
            pass
    vr, _ = build_vroot(s_dir(), _XD().ROOT)
    job = {"_path": os.path.join(s_dir(), "job_dbook.json"), "out": out, "d_targets": dpath, "root": vr}
    r = _child(os.path.join(vr, "build", "x_adapter.py"), "--dbook-child", job, TIMEOUT["d"], cwd=vr)
    if r["rc"] != 0:
        raise SystemExit("🚨 D 책 자식 실패: %s" % r["stderr_tail"])
    _wjson(mark, want)
    return out, r


def _book_from_dates(SW, F, name, dbk):
    """D 책 자식의 날짜 경로 → 얼린 q_switch.Book(뿌리 격자 자리 · 날짜 문자열로 맞춘다 · S 창 거래일 집합이 같아야 한다)."""
    G = F.G
    win = [G.dates[i] for i in range(F.i0, F.iE + 1)]
    if list(dbk["dates"]) != win:
        a, b = set(dbk["dates"]), set(win)
        raise SystemExit("🚨 D 책 날짜가 뿌리 격자와 다르다(뿌리에만 %d · D 에만 %d)" % (len(b - a), len(a - b)))
    paths = {}
    for ck, vals in dbk["paths"].items():
        paths[float(ck)] = {F.i0 + j: float(v) for j, v in enumerate(vals)}
    return SW.Book(name, F, paths, {float(k): v for k, v in dbk["turn"].items() if float(k) > 0})


def _s_cov_child(job):
    """F0 커버리지(수익 없음) — D 목표를 그달 World 키로 옮긴 몫 · 이름 수 · 못 옮긴 티커(비중 · 이유)를 달마다. 장부 · 경로를 만들지 않는다.
    job["world"] = "dbook"(vroot · 배치 V 핀 판 World · K6 · K7 — D 책이 쓰는 World) | "root"(얼린 V0 뿌리 World · 비교 보고)."""
    t0 = time.time()
    assert_dir_blobs(HERE, DBOOK_FROZEN if job.get("world", "dbook") == "dbook" else ROOT_FROZEN)
    if job.get("world", "dbook") == "dbook":
        import v_data as VD
        okp, badp = _v_pins_full(VD, job.get("root"))
        if not okp:
            raise SystemExit("🚨 배치 V 자료 핀 불일치 — %s" % badp[:3])
    import eg30plus as E
    Wd = E.World()
    months = [m for m in Wd.months if S_FORM[0] <= m <= S_FORM[1]]
    D = _rjson(job["d_targets"])
    rows = {}
    for m in months:
        rec = (D["months"] or {}).get(m)
        if not rec:
            rows[m] = {"target": False}
            continue
        i = Wd.me[m]
        pairs = _d_pairs(Wd, m, rec)
        tk2k = {}
        for t, k in pairs:
            tk2k.setdefault(t, k)
            tk2k.setdefault(t.replace(".", "-"), k)
        priced = lambda k: (k in Wd.PX and Wd.PX[k][i] == Wd.PX[k][i] and Wd.PX[k][i] > 0)
        w, names, mv, n = map_targets(rec["w"], pairs, priced)
        miss = []
        for t, x in sorted(rec["w"].items(), key=lambda kv: -kv[1]):
            k = tk2k.get(t) or tk2k.get(t.replace("-", "."))
            if k is None:
                kk = [key for key in Wd.PX if key.split("@")[0] in (t, t.replace("-", "."))]
                miss.append({"t": t, "w": round(float(x), 6), "why": "우주 밖(World 명단에 없음)", "px_keys": kk[:3],
                             "vb_key": (rec.get("keys") or {}).get(t)})
            elif not priced(k):
                miss.append({"t": t, "w": round(float(x), 6), "why": "그달 가격 없음", "k": k})
        rows[m] = {"target": True, "moved": round(float(mv), 6), "n_mapped": int(n), "n_target": len(rec["w"]), "ok": bool(n >= 1 and mv >= D_MAP_MIN - 1e-12),
                   "missing": miss[:12]}
    doc = {"kind": "xbatch_s_coverage", "note": "F0 — D 목표 → World 키 옮김(비중 · 개수 · 이유만 · 수익 없음)", "months": rows,
           "n_ok": int(sum(1 for r in rows.values() if r.get("ok"))), "n_months": len(rows), "sec": round(time.time() - t0, 1)}
    _wjson(job["out"], doc)
    return 0


def s_coverage(out_path=None, world="dbook"):
    """F0 — D 목표 커버리지(수익 없음). world = "dbook"(vroot World · D 책 · K6 · K7) | "root"(얼린 V0 뿌리 World · 비교)."""
    XD = _XD()
    dpath, rd = d_targets()
    out_path = out_path or os.path.join(s_dir(), "s_coverage_%s.json" % world)
    job = {"_path": os.path.join(s_dir(), "job_scov.json"), "out": out_path, "d_targets": dpath, "world": world}
    if world == "root":
        root, rr = build_root(s_dir(), XD.ROOT)
        r = _child(os.path.join(root, "build", "x_adapter.py"), "--s-cov-child", job, TIMEOUT["s"], cwd=root)
    else:
        vr, _ = build_vroot(s_dir(), XD.ROOT)
        job["root"] = vr
        r = _child(os.path.join(vr, "build", "x_adapter.py"), "--s-cov-child", job, TIMEOUT["s"], cwd=vr)
    if r["rc"] != 0:
        raise SystemExit("🚨 S 커버리지 자식 실패: %s" % r["stderr_tail"])
    return _rjson(out_path)


def _s_child(job):
    t0 = time.time()
    assert_dir_blobs(HERE, ROOT_FROZEN)
    import qbatch_core as Q
    import q_switch as SW
    ctx = Q.Ctx()
    Wd = ctx.Wd
    F = SW.frame(ctx)
    months = list(F.months)
    assert months[0] == S_FORM[0] and months[-1] == S_FORM[1] and len(months) == 120, (months[0], months[-1], len(months))
    D = _rjson(job["d_targets"])
    a_unit = {m: float(job["a"][m]) for m in months}
    assert set(a_unit.values()).issubset({0.0, 1.0}), "a 단위는 {0, 1}(X-BEAR)"
    # V0 재현(수익 없이) — 목표 해시 = QFWD 명세 §6 짝맞춤 표
    T0 = ctx.V0_targets
    v0h = v0_target_hashes(T0)
    v0_ok = {k: bool(v0h[k] == V0_HASH_PIN[k]) for k in V0_HASH_PIN}
    if not all(v0_ok.values()):
        raise SystemExit("🚨 V0 목표 해시가 QFWD 짝맞춤 표와 다르다 %s — 얼린 V0 가 아니다" % v0_ok)
    # D 책(K6) — 배치 V 핀 판 World 에서 지은 경로(d_book 자식) → 얼린 Book · 날짜를 뿌리 격자에 맞춘다
    dbk = _rjson(job["d_book"])
    assert list(dbk["months"]) == months
    d_ok, moved, n_names = list(dbk["d_ok"]), dict(zip(months, dbk["d_moved"])), dict(zip(months, dbk["d_names"]))
    bO = SW.offense_v0(ctx)
    bD = _book_from_dates(SW, F, "XBATCH-D", dbk)
    del dbk
    bS = SW.spy_book(ctx)
    bT = SW.tbill_book(ctx)
    # β̂_C(V0 보유가중 · 흘린 비중) · β̂_D · APP — β̂ = VBATCH FP β̂(일간 1년 · Dimson 5 · 축소 0.5 · D 자식 beta_union) · 없으면 1.0(K3)
    rows = beta_c_rows(Wd, T0, D, months)
    beta_c, beta_d, n_beta_c = {}, {}, {}
    for m in months:
        beta_c[m] = rows[m]["beta_c"]
        n_beta_c[m] = rows[m]["n_beta"]
        beta_d[m] = (D["months"].get(m) or {}).get("beta_D")
    app = app_flags(beta_c, beta_d)
    a = np.array([a_unit[m] * app[m] for m in months])
    abar = float(a.mean())
    c10, c20 = Q.COST, SW.COST20
    arms, turn, frs = {}, {}, {}

    def run(nm, shares, bk, c=c10):                                        # 주 행 T+1(mix_t1)
        fr = mix_t1(F, np.clip(shares, 0.0, 1.0), bO, bk, c, Q.fund_from_path)
        arms[nm] = [float(x) for x in fr["ex"]]
        turn[nm] = float(fr["turn"]) if fr.get("turn") is not None else None
        frs[nm] = fr
        return fr
    frV0 = run("V0", np.ones(120), bD)
    frX = run("X", 1 - a, bD)
    run("X_half", 1 - A_OP * a, bD)
    run("STATIC", np.full(120, 1 - abar), bD)
    run("IDX", 1 - a, bS)
    fcash = np.array([(a[j] * (beta_c[m] - beta_d[m]) / beta_c[m]) if (beta_c[m] and beta_c[m] > 0 and beta_d[m] is not None) else 0.0
                      for j, m in enumerate(months)])
    run("CASH", 1 - np.clip(fcash, 0.0, 1.0), bT)
    run("X20", 1 - a, bD, c=c20)
    run("V0_20", np.ones(120), bD, c=c20)
    e = np.array(arms["X"]) - np.array(arms["V0"])
    x_v0 = float(np.mean(arms["V0"]) * 12)
    e_ann = float(e.mean() * 12)
    cdil = 1.0 if (x_v0 <= 0 or e_ann >= 0) else float(np.clip(1 + e_ann / x_v0, 0.0, 1.0))
    run("DIL", np.full(120, cdil), bS)
    # D0 행(보고) — 얼린 q_switch.mix_fr(d_m 종가 되맞춤)
    d0X = SW.mix_fr(ctx, np.clip(1 - a, 0.0, 1.0), bO, bD, c=c10)
    d0V = SW.mix_fr(ctx, np.ones(120), bO, bD, c=c10)
    frD = SW.mix_fr(ctx, np.zeros(120), bO, bD, c=c10)                     # D 슬리브 홀로(β(D) 보고 · S-C2)
    # 짝맞춤 B — 몫 ≡ 1 = Ctx.V0()(T+1 행 · D0 행 모두) · 교체 되맞춤 거래 0
    v0 = ctx.V0(basis="TR", cost=c10)
    diffB = float(np.max(np.abs(np.asarray(frV0["ex"]) - np.asarray(v0["ex"]))))
    diffB_d0 = float(np.max(np.abs(np.asarray(d0V["ex"]) - np.asarray(v0["ex"]))))
    # 짝맞춤 C — 몫 {0, 1} 인 X 의 T+1 경로 = 얼린 q_switch.switch_fr(pos_from_daily(delay 1))
    pos = SW.pos_from_daily(F, t1_pos(F, 1 - a), delay=1)
    swX = SW.switch_fr(ctx, pos, bO, bD, c=c10)
    diffC = float(np.max(np.abs(np.asarray(swX["ex"]) - np.asarray(frX["ex"]))))
    pairing_B = {"max_abs_diff_t1": diffB, "max_abs_diff_d0": diffB_d0, "pass": bool(diffB <= 1e-10 and diffB_d0 <= 1e-10)}
    pairing_C = {"max_abs_diff": diffC, "pass": bool(diffC <= 1e-10), "n_switch_switch_fr": int(swX.get("n_switch", -1))}
    hold = list(F.hold)
    dset = set(ctx.A.down_months(hold))
    dmask = np.array([h in dset for h in hold])
    ME = json.load(io.open(os.path.join(Q.DATA, "mech_episodes.json"), encoding="utf-8"))
    crash = set(ME["months"]["crash_m"])
    rfm = np.array([float(F.G.RF.get(h, 0.0)) * 100 for h in hold])
    ix = np.asarray(frX["index"], float)
    evals = {nm: _eval_summary(Q.evaluate(F.G, frs[nm], dmask)) for nm in ("V0", "X", "X_half", "STATIC", "IDX")}
    doc = {"kind": "xbatch_s_series", "hold": hold, "a": [float(x) for x in a], "a_unit": [a_unit[m] for m in months], "app": [app[m] for m in months],
           "beta_C": [beta_c[m] for m in months], "beta_D": [beta_d[m] for m in months], "n_beta_C_names": [n_beta_c[m] for m in months],
           "Re_m": [float(x) for x in (ix - rfm)], "index": [float(x) for x in ix], "down": [bool(x) for x in dmask], "crash": [h in crash for h in hold],
           "d_ok": d_ok, "d_moved": [moved.get(m) for m in months], "d_names": [n_names.get(m) for m in months], "turn": turn.get("X"), "turns": turn,
           "arms": arms, "arms_d0": {"X": [float(x) for x in d0X["ex"]], "V0": [float(x) for x in d0V["ex"]]},
           "sleeve": {"V0": [float(x) for x in frV0["basket"]], "D": [float(x) for x in frD["basket"]]}, "dil_c": cdil,
           "pairing_B": pairing_B, "pairing_C": pairing_C, "v0_hash_ok": v0_ok, "evals": evals, "abar": abar,
           "execution": "주 행 T+1(mix_t1 · 결정 d_m · 체결 T+1 종가) · D0 행 = 얼린 mix_fr(보고)", "sec": round(time.time() - t0, 1)}
    _wjson(job["out"], doc)
    return 0


def _v0beta_cov_child(job):
    """F0 커버리지(수익 없음 · 검토 반영) — V0 흘린 비중 가운데 VBATCH FP β̂ 가 선 비중 몫(K3 — 없으면 β 1.0)의 달별 최소 · 중앙 · 이름 수.
    S 뿌리(얼린 V0) · D 목표 beta_union · 창 2016-08 ~ 2026-07. 장부 · 경로 · 수익을 만들지 않는다."""
    t0 = time.time()
    assert_dir_blobs(HERE, ROOT_FROZEN)
    import qbatch_core as Q
    import q_switch as SW
    ctx = Q.Ctx()
    F = SW.frame(ctx)
    months = list(F.months)
    assert months[0] == S_FORM[0] and months[-1] == S_FORM[1] and len(months) == 120
    T0 = ctx.V0_targets
    v0h = v0_target_hashes(T0)
    if not all(v0h[k] == V0_HASH_PIN[k] for k in V0_HASH_PIN):
        raise SystemExit("🚨 V0 목표 해시가 QFWD 짝맞춤 표와 다르다")
    D = _rjson(job["d_targets"])
    rows = beta_c_rows(ctx.Wd, T0, D, months)
    cov = sorted(rows[m]["cov"] for m in months)
    nb = [rows[m]["n_beta"] for m in months]
    nn = [rows[m]["n_names"] for m in months]
    _wjson(job["out"], {"kind": "xbatch_v0_beta_cov", "window": list(S_FORM), "n_months": len(months),
                        "coverage_beta_min": float(cov[0]), "coverage_beta_median": float(cov[len(cov) // 2]),
                        "n_beta_names_min": int(min(nb)), "n_names_min": int(min(nn)), "n_names_max": int(max(nn)),
                        "rule": "V0 흘린 비중 가운데 VBATCH FP β̂ 가 선 이름의 비중 몫(K3 — 없는 이름은 β 1.0 으로 APP_S 의 β̂_C 에 든다)",
                        "sec": round(time.time() - t0, 1)})
    return 0


# ══════════════════════════════════════════════════════════════════════════
#  부모(작업 사본) — 자식 부르기 · S 계열 · vroot(K7)
# ══════════════════════════════════════════════════════════════════════════
def _XD():
    import x_data as XD
    return XD


def s_dir():
    d = os.path.join(_XD().cache_guard(), "s")
    os.makedirs(d, exist_ok=True)
    return d


def _child(script, flag, job, timeout, cwd=None):
    env = dict(os.environ, **ENV)
    jp = job["_path"]
    _wjson(jp, {k: v for k, v in job.items() if k != "_path"})
    t0 = time.time()
    p = subprocess.run([sys.executable, "-X", "utf8", script, flag, jp], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, env=env, cwd=cwd)
    return {"rc": p.returncode, "sec": round(time.time() - t0, 1), "stderr_tail": (p.stderr or "")[-2500:] if p.returncode else None,
            "stdout_chars_discarded": len(p.stdout or "")}


def build_vroot(dest, repo, force=False):
    """K7 — 배치 V 핀 판 임시 뿌리: 자료 핀 커밋 DATA_PIN 의 build/ + data/ 를 git archive 로 캐시 <dest>/vroot 에(작업 트리 랩 자료와 무관).
    표지(vroot.json)가 핀과 같으면 다시 짓지 않는다 · x_adapter.py 는 부를 때마다 새로 복사한다 · 얼린 blob(V_FROZEN · DBOOK_FROZEN)을 단언한다.
    돌려주는 것 (뿌리, 보고)."""
    root = os.path.join(dest, "vroot")
    mark = os.path.join(dest, "vroot.json")
    want = {"data_pin": DATA_PIN, "paths": list(VROOT_PATHS), "v_frozen": V_FROZEN, "dbook_frozen": DBOOK_FROZEN}
    reuse = False
    if not force and os.path.exists(mark) and os.path.isdir(os.path.join(root, "build")):
        try:
            reuse = _rjson(mark).get("want") == want
        except Exception:                                                  # noqa: BLE001
            reuse = False
    rep = {"reused": reuse}
    if not reuse:
        t0 = time.time()
        if _git(["cat-file", "-e", DATA_PIN + "^{commit}"], repo).returncode != 0:
            raise SystemExit("🚨 자료 핀 커밋 %s 이 저장소에 없다(git fetch origin)" % DATA_PIN[:12])
        if os.path.exists(root):
            shutil.rmtree(root)
        os.makedirs(root)
        n = _archive(repo, DATA_PIN, list(VROOT_PATHS), root)
        _wjson(mark, {"want": want, "built": time.strftime("%Y-%m-%d %H:%M:%S"), "n_files": n, "sec": round(time.time() - t0, 1)})
        rep.update({"n_files": n, "sec": round(time.time() - t0, 1)})
    shutil.copyfile(os.path.abspath(__file__), os.path.join(root, "build", "x_adapter.py"))
    assert_dir_blobs(os.path.join(root, "build"), V_FROZEN)
    assert_dir_blobs(os.path.join(root, "build"), DBOOK_FROZEN)
    return root, rep


def vroot_check(repo=None):
    """판 점검(굽기 전 · 시작 태그 전 · 러너 frozen_check · precommit) — 핀 커밋 넷(DATA_PIN · CODE_PIN · P1_BASE · P1_PRICE)이 있고 origin/main 의 조상 ·
    vroot build/ blob · 배치 V 자료 핀(파일 20 · 폴더 요약 4 · 뿌리) 통과. 값 없음. 돌려주는 것 {ok, bad, …}."""
    XD = _XD()
    repo = repo or XD.ROOT
    bad = []
    for nm, c in (("DATA_PIN", DATA_PIN), ("CODE_PIN", CODE_PIN), ("P1_BASE", P1_BASE), ("P1_PRICE", P1_PRICE)):
        if _git(["cat-file", "-e", c + "^{commit}"], repo).returncode != 0:
            bad.append("%s 커밋(%s)이 저장소에 없다" % (nm, c[:12]))
        elif _git(["merge-base", "--is-ancestor", c, "origin/main"], repo).returncode != 0:
            bad.append("%s 커밋(%s)이 origin/main 의 조상이 아니다" % (nm, c[:12]))
    if bad:
        return {"ok": False, "bad": bad, "data_pin": DATA_PIN}
    root, rr = build_vroot(s_dir(), repo)
    out = os.path.join(s_dir(), "vcheck.json")
    if os.path.exists(out):
        os.remove(out)
    job = {"_path": os.path.join(s_dir(), "job_vcheck.json"), "out": out, "root": root}
    r = _child(os.path.join(root, "build", "x_adapter.py"), "--vcheck-child", job, TIMEOUT["d"], cwd=root)
    if r["rc"] != 0 or not os.path.exists(out):
        return {"ok": False, "bad": ["vroot 점검 자식 실패: %s" % (r.get("stderr_tail") or "")[-300:]], "data_pin": DATA_PIN}
    doc = _rjson(out)
    return {"ok": bool(doc.get("ok")), "bad": list(doc.get("bad") or []), "data_pin": DATA_PIN, "vroot": rr, "sec": r["sec"]}


def v0_beta_coverage():
    """F0 — V0 흘린 비중의 β̂ 커버리지(K3 · 수익 없음 · S 뿌리 자식). D 목표(s/d_targets.json)가 있어야 한다."""
    XD = _XD()
    dpath, _ = d_targets()
    root, _rr = build_root(s_dir(), XD.ROOT)
    out = os.path.join(s_dir(), "v0_beta_cov.json")
    job = {"_path": os.path.join(s_dir(), "job_v0bcov.json"), "out": out, "d_targets": dpath}
    r = _child(os.path.join(root, "build", "x_adapter.py"), "--v0beta-cov-child", job, TIMEOUT["s"], cwd=root)
    if r["rc"] != 0:
        raise SystemExit("🚨 V0 β̂ 커버리지 자식 실패: %s" % r["stderr_tail"])
    return _rjson(out)


def d_targets(force=False, fidelity_out=None):
    """D 자식 — 캐시 s/d_targets.json(비중 · β̂ · 짝맞춤 A · 선정 해시). 있으면 그대로(force 면 다시)."""
    out = os.path.join(s_dir(), "d_targets.json")
    if os.path.exists(out) and not force and not fidelity_out:
        return out, {"reused": True}
    vb = os.path.join(tempfile.gettempdir(), "vbatch_cache", "f0", "vb_books.json.gz")
    vr, _ = build_vroot(s_dir(), _XD().ROOT)
    job = {"_path": os.path.join(s_dir(), "job_d.json"), "out": out, "vb_books": vb, "fidelity": fidelity_out, "root": vr}
    r = _child(os.path.join(vr, "build", "x_adapter.py"), "--d-child", job, TIMEOUT["d"], cwd=vr)
    if r["rc"] != 0:
        raise SystemExit("🚨 D 자식 실패: %s" % r["stderr_tail"])
    return out, r


def d_check(dpath):
    """D 목표 파일의 짝맞춤 A · 20% 상한 · 달 수(값 없음) — 하나라도 어긋나면 D 목표를 쓰지 않는다(멈춘다)."""
    D = _rjson(dpath)
    pA = D.get("pairing_A") or {}
    ms = [m for m, v in (D.get("months") or {}).items() if v]
    chk = {"pairing_A_pass": bool(pA.get("pass")), "vb_books_sha_ok": bool(pA.get("vb_books_sha_ok")), "n_months_A": pA.get("n_months"),
           "n_match_A": pA.get("n_match"), "n_with_target": len(ms), "first": min(ms) if ms else None, "last": max(ms) if ms else None,
           "max_w_le_cap": all(v["max_w"] <= D_CAP + 1e-12 for v in D["months"].values() if v), "sel_hash": D.get("sel_hash"),
           "v_blobs_ok": D.get("v_blobs") == V_FROZEN}
    return chk


def s_series(a_dec, out_path, force_root=False, force_d=False):
    """S 자식 — a_dec = {결정 달: a 단위(0/1)} · 산출 out_path(🚨 수익 · 캐시) · 돌려주는 것 보고(값 없음 · 짝맞춤 참/거짓).
    D 짝맞춤 A · V0 목표 해시 · 짝맞춤 B · C 가 하나라도 어긋나면 멈춘다(그 S 계열은 쓰지 않는다)."""
    XD = _XD()
    dpath, rd = d_targets(force=force_d)
    dc = d_check(dpath)
    if not (dc["pairing_A_pass"] and dc["max_w_le_cap"] and dc["v_blobs_ok"]):
        raise SystemExit("🚨 D 목표 짝맞춤 A · 상한 · blob 실패 — D 목표를 쓰지 않는다: %s" % {k: dc[k] for k in ("pairing_A_pass", "max_w_le_cap", "v_blobs_ok")})
    bpath, rb = d_book(force=force_d)
    root, rr = build_root(s_dir(), XD.ROOT, force=force_root)
    months = ["%04d-%02d" % (y, m) for y in range(2016, 2027) for m in range(1, 13)]
    months = [m for m in months if S_FORM[0] <= m <= S_FORM[1]]
    job = {"_path": os.path.join(s_dir(), "job_s.json"), "out": out_path, "d_targets": dpath, "d_book": bpath, "a": {m: float(a_dec[m]) for m in months}}
    r = _child(os.path.join(root, "build", "x_adapter.py"), "--s-child", job, TIMEOUT["s"], cwd=root)
    if r["rc"] != 0:
        raise SystemExit("🚨 S 자식 실패: %s" % r["stderr_tail"])
    S = _rjson(out_path)
    pairs = {"pairing_B": bool(S["pairing_B"]["pass"]), "pairing_C": bool(S["pairing_C"]["pass"]), "v0_hash_ok": all(S["v0_hash_ok"].values()),
             "n_hold": len(S["hold"]), "n_d_ok": int(sum(bool(x) for x in S["d_ok"]))}
    del S
    if not (pairs["pairing_B"] and pairs["pairing_C"] and pairs["v0_hash_ok"]):
        raise SystemExit("🚨 S 층 짝맞춤 실패 %s — 이 S 계열은 쓰지 않는다" % pairs)
    return {"d": rd, "d_check": dc, "d_book": {k: rb.get(k) for k in ("reused", "rc", "sec")}, "root": rr, "s": r, "pairing": pairs}


def bear_a_s_window():
    """X-BEAR 결정(2016-08 ~ 2026-07 · a 단위 0/1) — 신호 층(T1 · EG30 입력 없음 · JM 없이)."""
    import x_signals as XS
    XD = _XD()
    F = XS.signal_frame(XD.signal_inputs("T1"), with_jm=False)
    a = F["X-BEAR"]
    out = {str(k): float(v) for k, v in a.items() if S_FORM[0] <= str(k) <= S_FORM[1]}
    assert len(out) == 120 and all(v in (0.0, 1.0) for v in out.values())
    return out


def s_series_cached(force_d=False):
    """x_eval.blind_smoke · 굽기 용 — S 계열을 캐시 임시 파일로 만들고 메모리로 읽은 뒤 파일은 지운다(값은 x_eval 이 관문에만 쓰고 찍지 않는다)."""
    p = os.path.join(s_dir(), "_s_series.tmp.json")
    s_series(bear_a_s_window(), p, force_d=force_d)
    S = _rjson(p)
    os.remove(p)
    return S


SMOKE_INTERMEDIATES = ("d_book.json", "d_book.json.want.json", "job_s.json", "_s_series.tmp.json")   # 수익 경로 · 신호 상태가 든 중간 파일


def cleanup_smoke():
    """눈가린 연기 뒤 중간 파일(D 책 수익 경로 · S 작업 파일의 a 상태)을 열지 않고 지운다 — 굽기는 다시 짓는다(D 책 약 6초)."""
    for f in SMOKE_INTERMEDIATES:
        p = os.path.join(s_dir(), f)
        if os.path.exists(p):
            os.remove(p)


def blind_smoke():
    """D 자식 · 뿌리 · S 자식을 실자료로 끝까지 — 보고는 키 이름 · 개수 · 참/거짓(짝맞춤) · 시간만(S 산출 · D 경로 파일은 열지 않고 지운다).
    싣지 않는 것: 수익 · 초과 · 관문 값 · 켜짐 몫 · APP 켜진 달 수(신호가 정하는 개수)."""
    XD = _XD()
    XD.install_write_guard(XD.ROOT)
    rep = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "ok": False}
    t0 = time.time()
    try:
        fid = os.path.join(s_dir(), "_d_path.smoke.tmp.json")
        dpath, rd = d_targets(force=True, fidelity_out=fid)
        rep["d_child"] = {k: rd.get(k) for k in ("rc", "sec", "stdout_chars_discarded")}
        rep["d_path_written"] = os.path.exists(fid)
        if os.path.exists(fid):
            os.remove(fid)                                                  # 수익 파일 — 열지 않고 지운다
        rep["d_path_deleted_unread"] = not os.path.exists(fid)
        rep["d_check"] = d_check(dpath)
        rep["d_check"]["sel_hash16"] = (rep["d_check"].pop("sel_hash") or "")[:16]
        out = os.path.join(s_dir(), "_s_series.smoke.tmp.json")
        r = s_series(bear_a_s_window(), out)
        rep["root"], rep["s_child"], rep["pairing"] = r["root"], {k: r["s"].get(k) for k in ("rc", "sec", "stdout_chars_discarded")}, r["pairing"]
        rep["d_book"] = r["d_book"]
        S = _rjson(out)
        rep["s"] = {"n_hold": len(S["hold"]), "first": S["hold"][0], "last": S["hold"][-1], "arms": sorted(S["arms"]), "arms_d0": sorted(S["arms_d0"]),
                    "arm_lengths": sorted({len(v) for v in S["arms"].values()}), "evals": sorted(S["evals"]), "keys": sorted(S),
                    "n_beta_C_nonnull": int(sum(1 for x in S["beta_C"] if x is not None)), "n_beta_D_nonnull": int(sum(1 for x in S["beta_D"] if x is not None)),
                    "sec": S.get("sec")}
        import x_eval as XE
        with open(os.devnull, "w", encoding="utf-8") as dn:
            old = sys.stdout
            sys.stdout = dn
            try:
                sres = XE.s_layer(S)
                keys = sorted(sres["gates"])
            finally:
                sys.stdout = old
        rep["s_layer_gate_ids"] = keys
        del S, sres
        os.remove(out)
        rep["s_deleted_unread"] = not os.path.exists(out)
        cleanup_smoke()
        rep["intermediates_deleted_unread"] = not any(os.path.exists(os.path.join(s_dir(), f)) for f in SMOKE_INTERMEDIATES)
        rep["ok"] = True
    except BaseException:                                                    # noqa: BLE001
        import re as _re
        tb = traceback.format_exc()[-3000:]
        rep["err"] = "\n".join(l if l.strip().startswith("File ") else _re.sub(r"(?<![A-Za-z_])[-+]?\d+\.\d+(e[-+]?\d+)?", "<num>", l)
                               for l in tb.splitlines())
    finally:
        XD.guard_off()
    rep["sec"] = round(time.time() - t0, 1)
    p = os.path.join(XD.cache_guard(), "meta", "_smoke_x_adapter.json")
    _wjson(p, rep)
    return rep


# ══════════════════════════════════════════════════════════════════════════
#  합성 시험(망 · 캐시 · 실자료 없음)
# ══════════════════════════════════════════════════════════════════════════
def _syn_ctx(n_months=24, seed=1):
    """q_switch 틀이 읽는 최소 ctx — Wd.months · G(dates · me · IX_TR · IX_PR · RF · di). 합성 가격만."""
    import qbatch_core as Q
    rng = np.random.default_rng(seed)
    months = [Q.mshift("2016-08", k) for k in range(n_months)]
    dates, me = [], {}
    import datetime as dt
    d = dt.date(2016, 8, 1)
    endm = Q.mshift(months[-1], 1)
    while d.strftime("%Y-%m") <= endm:
        if d.weekday() < 5:
            dates.append(d.strftime("%Y-%m-%d"))
            me[d.strftime("%Y-%m")] = len(dates) - 1
        d += dt.timedelta(days=1)
    ix = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(dates))))
    G = Q.Grid.__new__(Q.Grid)
    G.dates, G.di, G.IX_TR, G.IX_PR, G.me = dates, {x: i for i, x in enumerate(dates)}, ix, ix * 0.99, me
    G.RF = {m: 0.001 for m in me}

    class _W:
        pass
    Wd = _W()
    Wd.months = months
    Wd.me = me

    class _C:
        pass
    ctx = _C()
    ctx.Wd, ctx.G = Wd, G
    return ctx


def _syn_book(SW, F, name, drift, vol, seed, cost_days=(), cash=False):
    rng = np.random.default_rng(seed)
    g0 = np.exp(rng.normal(drift, vol, F.T))
    bk = SW.Book.__new__(SW.Book)
    bk.name, bk.g0, bk.lg0 = name, g0, np.log(g0)
    lf = {}
    for c in (SW.COST, SW.COST20):
        f = np.zeros(F.T)
        for j in cost_days:
            f[j] = math.log(1 - c * 0.3)
        lf[c] = f
    bk.lf, bk.turn, bk.reb_days, bk.cash = lf, {SW.COST: 0.0, SW.COST20: 0.0}, np.array(list(cost_days), int), cash
    return bk


def _st_prop1():
    """명제 1 — 합성 자료 a ≡ 0 이면 X 경로 = V0 경로(1e−12) · 교체 되맞춤 비용 행 0 · T+1 행(mix_t1)도 같다 · a 가 켜지기 전 달은 같다."""
    assert_dir_blobs(HERE, {k: ROOT_FROZEN[k] for k in ("qbatch_core", "q_switch")})    # 합성 시험도 얼린 판으로
    import qbatch_core as Q
    import q_switch as SW
    ctx = _syn_ctx()
    SW._CACHE.clear()
    F = SW.frame(ctx)
    me_days = [int(F.mstart[k] - 1) for k in range(1, len(F.months))]              # 장부 자기 되맞춤 = 월말 d_m 종가(실장부와 같은 자리)
    bO = _syn_book(SW, F, "O", 0.0005, 0.012, 3, cost_days=(me_days[2], me_days[5]))
    bD = _syn_book(SW, F, "D", 0.0002, 0.007, 4, cost_days=tuple(me_days))
    nM = len(F.months)
    frX = SW.mix_fr(ctx, np.ones(nM), bO, bD, c=SW.COST)
    lO = bO.lg0 + bO.lf[SW.COST]
    v = np.exp(np.cumsum(lO))
    path = {F.i0: 1.0}
    for j, d in enumerate(F.day):
        path[int(d)] = float(v[j])
    frV = Q.fund_from_path(F.G, {"path": path}, F.months, cost=SW.COST)
    assert float(np.max(np.abs(frX["ex"] - frV["ex"]))) < 1e-12
    own_only = float((1.0 - np.exp(bO.lf[SW.COST])).sum()) / SW.COST
    assert abs(frX["cost_drag"] - SW.COST * own_only / F.years * 100) < 1e-12          # 교체 되맞춤 거래 0 — 자기 회전만
    t1 = mix_t1(F, np.ones(nM), bO, bD, SW.COST, Q.fund_from_path)
    assert float(np.max(np.abs(t1["ex"] - frV["ex"]))) < 1e-12 and abs(t1["cost_drag"] - frX["cost_drag"]) < 1e-12
    # a ≠ 0 이면 달라진다(시험이 이빨이 있다)
    a = np.zeros(nM)
    a[5:8] = 1.0
    frA = SW.mix_fr(ctx, 1 - a, bO, bD, c=SW.COST)
    assert float(np.max(np.abs(frA["ex"] - frV["ex"]))) > 1e-6
    # D0 행(mix_fr): 보유월 5 로 옮기는 매매는 달 4 의 마지막 날 종가 → 달 0 ~ 3 은 V0 와 같다(달 4 는 교체 비용만 다르다)
    assert float(np.max(np.abs(frA["ex"][:4] - frV["ex"][:4]))) < 1e-12 and float(abs(frA["ex"][4] - frV["ex"][4])) > 1e-9
    # T+1 행(mix_t1): 교체는 보유월 5 의 첫 거래일 종가 → 달 0 ~ 4 모두 V0 와 같다(하루 늦게 바꾼다)
    tA = mix_t1(F, 1 - a, bO, bD, SW.COST, Q.fund_from_path)
    assert float(np.max(np.abs(tA["ex"][:5] - frV["ex"][:5]))) < 1e-12 and float(np.max(np.abs(tA["ex"] - frA["ex"]))) > 1e-9
    SW._CACHE.clear()
    return "명제 1: a ≡ 0 → X 경로 = V0 경로(|차| < 1e−12 · T+1 · D0 행 모두) · 교체 되맞춤 거래 0 · 켜지기 전 달 같음(D0 는 교체 앞 달까지 · T+1 은 교체 달 앞까지) · a ≠ 0 이면 달라짐"


def _st_pairing_c():
    """짝맞춤 C(합성) — 몫 {0, 1} 이면 mix_t1(T+1) = 얼린 q_switch.switch_fr(pos_from_daily(delay 1)) · 창 첫 달 켜짐 · 여러 번 교체 · 현금 장부도."""
    assert_dir_blobs(HERE, {k: ROOT_FROZEN[k] for k in ("qbatch_core", "q_switch")})
    import qbatch_core as Q
    import q_switch as SW
    ctx = _syn_ctx(n_months=30, seed=5)
    SW._CACHE.clear()
    F = SW.frame(ctx)
    me_days = [int(F.mstart[k] - 1) for k in range(1, len(F.months))]
    bO = _syn_book(SW, F, "O", 0.0005, 0.012, 3, cost_days=tuple(me_days[2::3]))
    bD = _syn_book(SW, F, "D", 0.0002, 0.007, 4, cost_days=tuple(me_days))
    bT = _syn_book(SW, F, "T", 0.0001, 0.0, 6, cash=True)
    nM = len(F.months)
    rng = np.random.default_rng(11)
    for trial in range(4):
        a = (rng.random(nM) < 0.35).astype(float)
        if trial == 0:
            a[0] = 1.0                                                       # 창 첫 결정이 켜짐 — 첫 달 첫날은 V0(앞 몫) · 그날 종가 교체
        for bk in (bD, bT):
            t1 = mix_t1(F, 1 - a, bO, bk, SW.COST, Q.fund_from_path)
            sw = SW.switch_fr(ctx, SW.pos_from_daily(F, t1_pos(F, 1 - a), delay=1), bO, bk, c=SW.COST)
            d = float(np.max(np.abs(np.asarray(t1["ex"]) - np.asarray(sw["ex"]))))
            assert d < 1e-12, (trial, bk.name, d)
    try:
        t1_pos(F, np.full(nM, 0.5))
        raise AssertionError("분수 몫 통과")
    except AssertionError as e:
        if "통과" in str(e):
            raise
    SW._CACHE.clear()
    return "짝맞춤 C: 몫 {0, 1} 이면 T+1 행 mix_t1 = 얼린 switch_fr(pos_from_daily delay 1)(|차| < 1e−12 · 4 경로 × D · 현금 장부 · 첫 달 켜짐) · 분수 몫 거부"


def _st_dbook():
    """K6 — D 책 날짜 경로 → 얼린 Book(뿌리 격자 자리 · 날짜가 다르면 멈춤) · 키 옮기기(배치 V 가격 키 먼저 · 없으면 명단)."""
    assert_dir_blobs(HERE, {k: ROOT_FROZEN[k] for k in ("qbatch_core", "q_switch")})
    import q_switch as SW
    ctx = _syn_ctx(n_months=12, seed=9)
    SW._CACHE.clear()
    F = SW.frame(ctx)
    G = F.G
    rng = np.random.default_rng(3)
    dates = [G.dates[i] for i in range(F.i0, F.iE + 1)]
    v0 = np.cumprod(np.r_[1.0, np.exp(rng.normal(0, 0.01, len(dates) - 1))])
    cost = np.ones(len(dates))
    for k in range(1, len(F.months)):
        cost[F.mstart[k] - 1 + 1:] *= (1 - 0.0010 * 0.3)                 # 월말 되맞춤 비용(모양만)
    dbk = {"dates": dates, "paths": {"0.0000": list(v0), "0.0010": list(v0 * cost), "0.0020": list(v0 * cost ** 2)},
           "turn": {"0.0000": 0.0, "0.0010": 1.0, "0.0020": 1.0}}
    bk = _book_from_dates(SW, F, "D", dbk)
    assert np.allclose(bk.g0, v0[1:] / v0[:-1], rtol=0, atol=1e-15) and set(bk.lf) == {0.001, 0.002}
    assert len(bk.reb_days) == len(F.months) - 1
    bad = dict(dbk, dates=dates[:-1] + ["2099-01-01"])
    try:
        _book_from_dates(SW, F, "D", bad)
        raise AssertionError("날짜 어긋남 통과")
    except SystemExit:
        pass

    class _W:
        PX = {"COL@1137411": [1.0], "AAA": [1.0], "SIRI": [1.0]}

        def universe(self, m, idx, ex):
            return [("AAA", "AAA"), ("COL", "COL@999")]
    pr = _d_pairs(_W(), "2017-11", {"w": {"COL": 0.3, "SIRI": 0.2, "AAA": 0.5, "ZZZ": 0.0}, "keys": {"COL": "COL@1137411", "SIRI": "SIRI", "ZZZ": "ZZZ@1"}})
    wk, names, mv, n = map_targets({"COL": 0.3, "SIRI": 0.2, "AAA": 0.5}, pr, lambda k: True)
    assert names.get("COL@1137411") == "COL" and "COL@999" not in wk and names.get("SIRI") == "SIRI" and abs(mv - 1.0) < 1e-12
    SW._CACHE.clear()
    return "K6 D 책: 날짜 경로 → 얼린 Book(g0 · 비용 배수 · 되맞춤 날) · 날짜 어긋나면 멈춤 · 키 옮기기(배치 V 가격 키 먼저 · 날짜 인식 키 · 명단 대체)"


def _st_cap_map_app():
    import eg30plus as E
    rng = np.random.default_rng(7)
    me = {("T%02d" % i): float(x) for i, x in enumerate(rng.lognormal(3, 1.5, 25))}
    me["BIG"] = 1e6
    w = E.cap_weights(me, D_CAP)
    assert abs(sum(w.values()) - 1) < 1e-12 and max(w.values()) <= D_CAP + 1e-12 and abs(w["BIG"] - D_CAP) < 1e-12
    pairs = [("AAA", "AAA"), ("BRK-B", "BRK.B"), ("CCC", "CCC@2")]
    wk, names, mv, n = map_targets({"AAA": 0.5, "BRK-B": 0.3, "ZZZ": 0.2}, pairs, lambda k: True)
    assert n == 2 and abs(mv - 0.8) < 1e-12 and abs(sum(wk.values()) - 1) < 1e-12 and names["BRK.B"] == "BRK-B" and abs(wk["AAA"] - 0.625) < 1e-12
    wk2, _, mv2, n2 = map_targets({"AAA": 0.5, "CCC": 0.5}, pairs, lambda k: k != "CCC@2")
    assert n2 == 1 and abs(mv2 - 0.5) < 1e-12
    ap = app_flags({"2020-01": 1.20, "2020-02": 1.05, "2020-03": None}, {"2020-01": 0.70, "2020-02": 0.99, "2020-03": 0.7})
    assert ap == {"2020-01": 1.0, "2020-02": 0.0, "2020-03": 0.0}
    assert abs(book_beta({"a": 0.5, "b": 0.5}, {"a": 0.6, "b": None}) - 0.8) < 1e-12
    dw = drifted_weights({"a": 0.5, "b": 0.5}, {"a": 2.0, "b": None})
    assert abs(dw["a"] - 2 / 3) < 1e-12
    assert canon_hash({"2020-01": ["A", "B"], "2020-02": ["C"]}) == canon_hash({"2020-02": ["C"], "2020-01": ["A", "B"]})
    return "D 20% 상한(얼린 eg30plus.cap_weights · 합 1) · 키 옮기기(점/줄표 · 값 없는 키 빼고 재정규화 · 옮긴 몫) · APP 0.10 · β̂ 없음 1.0 · 흘린 비중 · 선정 해시 정규화"


def _st_pins():
    """핀 대조 — P3 · 코드 핀 · 가격 판이 qfwd_adapter 의 것과 같다(읽기만) · 작업 사본 배치 V blob · VB 넘김 sha = data/_vb_f0.json."""
    src = io.open(os.path.join(HERE, "qfwd_adapter.py"), encoding="utf-8").read()
    for k, v in P3.items():
        assert ('"%s":' % k) in src and v in src, k
    assert CODE_PIN in src and BUILD_TREE in src and P1_PRICE in src and P1_BASE in src
    for m, b in ROOT_FROZEN.items():
        assert b in src, m
    assert_dir_blobs(HERE, V_FROZEN)
    f0 = _rjson(os.path.join(os.path.dirname(HERE), "data", "_vb_f0.json"))
    assert (f0.get("gegd_pins") or {}).get("in_sha") == VB_BOOKS_SHA
    for k, v in V0_HASH_PIN.items():                                    # V0 목표 해시 = QFWD 명세 §6 짝맞춤 표(PARITY)
        assert ('"%s": "%s"' % (k, v)) in src, k
    import re as _re
    assert _re.fullmatch(r"[0-9a-f]{40}", DATA_PIN) and VROOT_PATHS == ("build/", "data/")
    repo = os.path.dirname(HERE)
    mv = _git(["rev-parse", "%s:data/_vb_manifest.json" % DATA_PIN], repo).stdout.strip()   # K7 — 자료 핀 커밋의 배치 V 명세 = 작업 사본의 얼린 명세
    assert mv and mv == blob_sha1(_rbytes(os.path.join(repo, "data", "_vb_manifest.json")).replace(b"\r\n", b"\n")), "DATA_PIN 의 _vb_manifest 가 다르다"
    for m, b in V_FROZEN.items():                                       # 자료 핀 커밋의 build/ 도 배치 V 얼린 blob
        assert _git(["rev-parse", "%s:build/%s.py" % (DATA_PIN, m)], repo).stdout.strip() == b, m
    T = {"2016-08": {"w": {"A": 0.5, "B@2": 0.5}, "names": {"A": "A", "B@2": "B"}}}
    h = v0_target_hashes(T)
    assert h["V0_LT"] == hashlib.sha256(json.dumps(T, sort_keys=True).encode("utf-8")).hexdigest() and len(h["V0_BL"]) == 64
    return ("P3 · 코드 핀 · 가격 판 · 뿌리 얼린 blob = qfwd_adapter(읽기만) · 배치 V blob 10 · VB 넘김 sha = data/_vb_f0.json · V0 목표 해시 = QFWD PARITY · "
            "K7 자료 핀 커밋의 _vb_manifest · build/ 배치 V blob = 얼린 판")


def _st_blob_guard():
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "m.py"), "wb") as f:
            f.write(b"x = 1\n")
        good = blob_sha1(b"x = 1\n")
        assert assert_dir_blobs(td, {"m": good})
        try:
            assert_dir_blobs(td, {"m": "0" * 40})
            raise AssertionError("blob 불일치 통과")
        except SystemExit:
            pass
        with open(os.path.join(td, "m.py"), "wb") as f:
            f.write(b"x = 1\r\n")                                      # CRLF 사본도 같은 blob(LF 로 맞춘다)
        assert assert_dir_blobs(td, {"m": good})
    return "얼린 blob 단언(불일치면 멈춤 · CRLF 사본은 LF 로 맞춰 같다)"


SELFTESTS = (_st_prop1, _st_pairing_c, _st_dbook, _st_cap_map_app, _st_pins, _st_blob_guard)


def selftest():
    res, ok = [], True
    for fn in SELFTESTS:
        t = time.time()
        try:
            res.append(("통과", fn.__name__, fn(), time.time() - t))
        except BaseException:                                              # noqa: BLE001
            ok = False
            res.append(("실패", fn.__name__, traceback.format_exc()[-2000:], time.time() - t))
    for st, nm, msg, dt in res:
        print("  %s %-18s %5.2fs  %s" % ("✓" if st == "통과" else "✗", nm, dt, msg))
    print("x_adapter selftest %d/%d 통과" % (sum(1 for r in res if r[0] == "통과"), len(res)))
    return 0 if ok else 1


def main(argv):
    if "--d-child" in argv:
        return _d_child(_rjson(argv[argv.index("--d-child") + 1]))
    if "--s-child" in argv:
        return _s_child(_rjson(argv[argv.index("--s-child") + 1]))
    if "--dbook-child" in argv:
        return _dbook_child(_rjson(argv[argv.index("--dbook-child") + 1]))
    if "--s-cov-child" in argv:
        return _s_cov_child(_rjson(argv[argv.index("--s-cov-child") + 1]))
    if "--vcheck-child" in argv:
        return _vcheck_child(_rjson(argv[argv.index("--vcheck-child") + 1]))
    if "--v0beta-cov-child" in argv:
        return _v0beta_cov_child(_rjson(argv[argv.index("--v0beta-cov-child") + 1]))
    if "--vroot-check" in argv:
        r = vroot_check()
        print(json.dumps({k: r.get(k) for k in ("ok", "bad", "data_pin", "vroot", "sec")}, ensure_ascii=False, indent=1))
        return 0 if r["ok"] else 1
    if "--s-coverage" in argv:
        doc = s_coverage(world="root" if "--root" in argv else "dbook")
        bad = {m: r for m, r in doc["months"].items() if not r.get("ok")}
        print(json.dumps({"n_ok": doc["n_ok"], "n_months": doc["n_months"], "not_ok": bad, "sec": doc["sec"]}, ensure_ascii=False, indent=1))
        return 0
    if "--selftest" in argv:
        return selftest()
    if "--blind-smoke" in argv:
        rep = blind_smoke()
        print(json.dumps(rep, ensure_ascii=False, indent=1, default=str))
        return 0 if rep.get("ok") else 1
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
