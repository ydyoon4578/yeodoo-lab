-- =====================================================================
-- yeouido-lab · Postgres 누적 스토어 (schema: yeodoo)
-- =====================================================================
-- 역할 분담 (중요)
--   · 원본(source of truth) = git 저장소의 data/*.json
--     GitHub Actions 러너는 Tailscale tailnet 밖이라 이 DB에 도달할 수 없다.
--     따라서 사이트 생성기는 절대 DB에 의존하지 않는다(의존시 매일 크론이 깨짐).
--   · 이 DB = 누적 미러(queryable mirror)
--     매 영업일 커밋이 git에 남으므로, 로더는 git 이력을 되짚어 백필할 수 있다.
--     → 적재 머신이 며칠 꺼져 있어도 데이터 유실 0. 언제든 전량 재구축 가능.
--
-- 스키마 드리프트 대응
--   지표는 계속 추가된다(펀더멘털 확장 등). 컬럼을 매번 늘리면 로더가 깨지므로
--   "안정적 핵심만 타입 컬럼으로 승격 + 전체 레코드는 raw jsonb" 하이브리드.
--   신규 지표는 DDL 변경 없이 raw->>'키' 로 즉시 조회된다.
-- =====================================================================

create schema if not exists yeodoo;
comment on schema yeodoo is 'yeouido-lab 공개 사이트 일별 스냅샷 누적 (원본은 git data/*.json, 여기는 미러)';

-- ---------------------------------------------------------------------
-- 1) 종목 일별 스냅샷
-- ---------------------------------------------------------------------
create table if not exists yeodoo.stock_daily (
  asof          date              not null,
  ticker        text              not null,
  name          text,
  sector        text,
  idx           text[],                      -- SPX / NDX 소속
  timing        text,                        -- 매수우세 / 매도우세 / 중립
  overheat      double precision,            -- comp.*  0~100 백분위 (인과적 계산)
  trend         double precision,
  momentum      double precision,
  volatility    double precision,
  positioning   double precision,
  bscore        double precision,
  sscore        double precision,
  flags         text[],
  raw           jsonb             not null,  -- 종목 레코드 원본 전체
  loaded_at     timestamptz       not null default now(),
  primary key (asof, ticker)
);
create index if not exists ix_stock_daily_ticker on yeodoo.stock_daily (ticker, asof desc);
create index if not exists ix_stock_daily_sector on yeodoo.stock_daily (sector, asof desc);
create index if not exists ix_stock_daily_raw    on yeodoo.stock_daily using gin (raw jsonb_path_ops);

-- ---------------------------------------------------------------------
-- 2) 펀더멘털 일별 (raw 중심 — 지표 추가시 DDL 무변경)
-- ---------------------------------------------------------------------
create table if not exists yeodoo.fundamental_daily (
  asof          date              not null,
  ticker        text              not null,
  teps          double precision,            -- 주당순이익 TTM
  feps          double precision,            -- 선행 EPS
  tpe           double precision,            -- P/E (TTM)
  fpe           double precision,            -- 선행 P/E
  gr            double precision,            -- 선행 EPS 성장률 %
  raw           jsonb             not null,
  loaded_at     timestamptz       not null default now(),
  primary key (asof, ticker)
);
create index if not exists ix_fund_daily_ticker on yeodoo.fundamental_daily (ticker, asof desc);
create index if not exists ix_fund_daily_raw    on yeodoo.fundamental_daily using gin (raw jsonb_path_ops);

-- ---------------------------------------------------------------------
-- 3) 애널리스트 목표주가 일별
--    ⚠ 표기·검증 전용. 상승여력(up)은 매수 근거 아님(기각 아카이브 참조).
--    git의 target_history.json 은 무한 증가하므로 장기 이력은 여기가 정본.
-- ---------------------------------------------------------------------
create table if not exists yeodoo.target_daily (
  asof          date              not null,
  ticker        text              not null,
  tp_mean       double precision,
  tp_high       double precision,
  tp_low        double precision,
  n_analyst     integer,
  rec_key       text,                        -- buy / hold / underperform ...
  upside_pct    double precision,
  primary key (asof, ticker)
);
create index if not exists ix_target_daily_ticker on yeodoo.target_daily (ticker, asof desc);

-- ---------------------------------------------------------------------
-- 4) 스윙 마커 생명주기  ★ JSON이 줄 수 없는 유일한 자산
--    잠정(bmw/smw) 마커가 며칠 뒤 확정(bms/sms)으로 승격되는지, 아니면
--    리페인팅으로 사라지는지를 추적한다. 화면에 쓰는 "확정 확률 ~%"를
--    과거 추정치가 아니라 우리 실측으로 대체하기 위한 근거 테이블.
-- ---------------------------------------------------------------------
create table if not exists yeodoo.swing_marker (
  ticker          text            not null,
  bar_date        date            not null,  -- 마커가 찍힌 봉의 날짜
  side            text            not null,  -- 'buy' | 'sell'
  first_seen      date            not null,  -- 이 마커를 처음 관측한 as_of
  last_seen       date            not null,  -- 마지막으로 관측된 as_of
  ever_provisional boolean        not null default false,
  first_confirmed date,                      -- 확정으로 처음 올라온 as_of (null=아직 잠정)
  price           double precision,
  primary key (ticker, bar_date, side)
);
create index if not exists ix_swing_marker_seen on yeodoo.swing_marker (last_seen desc);

-- ---------------------------------------------------------------------
-- 5) 시장 국면 / 6) 시장 심리
-- ---------------------------------------------------------------------
create table if not exists yeodoo.regime_daily (
  asof        date        primary key,
  regime      text,
  raw         jsonb       not null,
  loaded_at   timestamptz not null default now()
);

create table if not exists yeodoo.sentiment_daily (
  asof        date        primary key,
  score       double precision,
  score_pctl  double precision,
  label       text,
  raw         jsonb       not null,
  loaded_at   timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 7) 적재 감사 로그 — 어느 커밋에서 무엇을 넣었는지
-- ---------------------------------------------------------------------
create table if not exists yeodoo.load_log (
  id          bigserial   primary key,
  source      text        not null,          -- stocks / fundamental / target / regime / sentiment / swing
  asof        date,
  git_sha     text,
  n_rows      integer,
  status      text        not null,          -- ok / skip / error
  message     text,
  ran_at      timestamptz not null default now()
);
create index if not exists ix_load_log_src on yeodoo.load_log (source, asof desc);

-- ---------------------------------------------------------------------
-- 뷰: 잠정 마커 확정 전환율 (화면의 "확정 확률" 실측 대체용)
--
-- ⚠ 우측 절단(right-censoring) 처리가 이 뷰의 존재 이유다.
--    마지막 관측일에 처음 등장한 잠정 마커는 승격할 시간이 0일이므로, 분모에
--    넣으면 승격률이 기계적으로 낮게 나온다. 실제로 초기 적재에서 sell 7.4%가
--    나왔는데 이는 전환율이 아니라 절단 산물이었다.
--    → 자기 뒤에 관측일이 하나 이상 있는(=승격할 기회가 있었던) 마커만 센다.
--
--    n_evaluable 이 작으면 어떤 결론도 내지 말 것. 관측일이 며칠 누적된 뒤에야
--    화면의 "과거 통계상 확정 확률"을 이 실측으로 대체할 수 있다.
-- ---------------------------------------------------------------------
-- CREATE OR REPLACE VIEW는 컬럼 추가/개명이 불가 → 뷰는 항상 drop 후 재생성.
-- (뷰는 파생물이라 drop해도 데이터 손실 없음. 테이블은 절대 drop하지 않는다.)
drop view if exists yeodoo.v_swing_promotion;
create view yeodoo.v_swing_promotion as
with obs as (select distinct first_seen as d from yeodoo.swing_marker),
     ev as (
       select m.*
       from yeodoo.swing_marker m
       where m.ever_provisional
         and exists (select 1 from obs where obs.d > m.first_seen)   -- 승격 기회 있었음
     )
select side,
       (select count(*) from yeodoo.swing_marker s
         where s.side = ev.side and s.ever_provisional)   as n_total,
       count(*)                                           as n_evaluable,
       count(*) filter (where first_confirmed is not null) as n_promoted,
       round(100.0 * count(*) filter (where first_confirmed is not null)
             / nullif(count(*), 0), 1)                    as promote_pct,
       round(avg(first_confirmed - first_seen) filter (where first_confirmed is not null), 2)
                                                          as avg_days_to_confirm,
       (select count(*) from obs)                         as n_obs_days
from ev
group by side;

-- 뷰: 최신 영업일 스냅샷 (조회 편의)
drop view if exists yeodoo.v_stock_latest;
create view yeodoo.v_stock_latest as
select * from yeodoo.stock_daily
where asof = (select max(asof) from yeodoo.stock_daily);
