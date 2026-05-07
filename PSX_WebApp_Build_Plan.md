# PSX Prediction & Portfolio Web App — Phase-by-Phase Build Plan

**Document version:** 1.0
**Target platform:** Web application (responsive, mobile-friendly)
**Total estimated timeline:** 9–12 months to full v1
**Approach:** Incremental — every phase ships a usable product

---

## Table of Contents

1. [Phase 0 — Foundations & Legal Setup (2 weeks)](#phase-0)
2. [Phase 1 — MVP: The Tracker (8–10 weeks)](#phase-1)
3. [Phase 2 — The Analyst: Predictions, Goals, Backtests (10–12 weeks)](#phase-2)
4. [Phase 3 — The Guardian: Sentiment, Anomaly Detection, Macro (8–10 weeks)](#phase-3)
5. [Phase 4 — The Community: Benchmarking & Advanced Features (6–8 weeks)](#phase-4)
6. [Phase 5 — Scale, Polish, Launch (4–6 weeks)](#phase-5)
7. [Cross-Cutting Concerns](#cross-cutting)
8. [Cost & Infrastructure Estimates](#costs)

---

## Tech Stack — Final Decision

Locked in once at the start so every phase builds on the same foundation.

**Frontend**
- **Framework:** Next.js 14+ (App Router) with TypeScript
- **Styling:** TailwindCSS + shadcn/ui component library
- **Charts:** TradingView Lightweight Charts (free, fast, professional) for price charts; Apache ECharts for everything else (heatmaps, comparisons, dashboards)
- **State:** TanStack Query (React Query) for server state, Zustand for client state
- **Forms:** React Hook Form + Zod for validation
- **Auth client:** Auth.js (NextAuth) v5

**Backend**
- **API framework:** FastAPI (Python 3.11+)
- **ORM:** SQLAlchemy 2.0 + Alembic for migrations
- **Background jobs:** Celery + Redis (or RQ if Celery is overkill early on)
- **WebSocket:** FastAPI native WebSockets for live prices

**Data Stores**
- **Primary database:** PostgreSQL 15+ with **TimescaleDB extension** (critical — this turns Postgres into a time-series powerhouse for OHLCV data)
- **Cache:** Redis 7+
- **Object storage:** Cloudflare R2 or AWS S3 (cheap, for storing reports, exports)

**ML / Inference**
- **Training stack:** Python, scikit-learn, XGBoost, PyTorch (LSTM)
- **Serving:** Separate FastAPI inference microservice + ONNX Runtime
- **Backtesting:** vectorbt (faster than backtrader for indicator-based strategies)
- **Indicators:** TA-Lib or pandas-ta

**Infrastructure**
- **Frontend hosting:** Vercel (zero-config Next.js)
- **Backend hosting:** Hetzner Cloud (best price/perf for Pakistan/EU latency) or DigitalOcean droplets, behind Caddy or Nginx
- **Database hosting:** Self-managed on the same VPS for cost, OR Neon / Supabase managed Postgres if you want zero ops (but you'll need TimescaleDB which Neon doesn't support — so probably self-managed)
- **CI/CD:** GitHub Actions
- **Monitoring:** Grafana + Prometheus, Sentry for error tracking, BetterStack for uptime
- **Domain & DNS:** Cloudflare (free tier covers most needs)

**Why these choices:** Every component is open-source, has a free tier, runs well on a single VPS for the first 10K users, and scales horizontally when you need it.

---

<a name="phase-0"></a>
## Phase 0 — Foundations & Legal Setup (2 weeks)

**Objective:** Lay every foundation that every later phase will depend on. Skip nothing here — going back to fix Phase 0 mistakes later costs 5×.

### Week 1: Legal, Domain, Repo, Cloud

#### Step 1: Resolve PSX data licensing — DO THIS FIRST

PSX explicitly prohibits commercial use of its market data without a license. The PSX Market Data team email is `marketdatarequest@psx.com.pk`. You have three realistic paths:

1. **Educational / non-commercial mode at start:** Build the product as a free educational tool until you have funding. Document this clearly in the ToS. PSX's public DPS portal (`dps.psx.com.pk`) provides EOD data that's acceptable for this use.
2. **Become a Capital Stake API customer:** Capital Stake is an authorized PSX data vendor with REST and WebSocket feeds. This is the fastest legitimate route to commercial-grade data. Pricing is via direct contact.
3. **Apply for a direct PSX license:** Contact `marketdatarequest@psx.com.pk` and apply for a market data redistribution license. This is the long-term right answer once you have revenue.

**Action:** Write the email today. Even if you start in educational mode, you want the relationship started.

#### Step 2: Register the legal entity and trademarks

Decide if you're forming a Sole Proprietorship, AOP, or a Pvt Ltd company under SECP. For anything that handles money or could grow, register as a **Single Member Pvt Ltd** through SECP's eServices — costs roughly PKR 5,000–15,000 in fees. This protects you personally and is required if you'll later seek investment.

#### Step 3: Domain and brand basics

Register your `.com` and `.pk` domain together. Set up Cloudflare for DNS. Buy a professional email on the domain (Google Workspace or Zoho Mail).

#### Step 4: Source control and project structure

Create a GitHub organization (not a personal repo). Set up these repositories from day one:

```
psx-app/
├── psx-web/              # Next.js frontend
├── psx-api/              # FastAPI main backend
├── psx-ingest/           # Data ingestion workers (separate so they can scale independently)
├── psx-inference/        # ML model serving (separate so model deploys don't restart the main API)
├── psx-shared/           # Shared TypeScript types and Python pydantic models
├── psx-infra/            # Terraform / Ansible / docker-compose for deployment
└── psx-docs/             # Internal documentation, runbooks, ADRs
```

Set up branch protection on `main`, require PR reviews, require passing CI.

### Week 2: Cloud, CI/CD, Observability

#### Step 5: Provision infrastructure

Spin up a single Hetzner CCX23 (4 vCPU, 16 GB RAM, ~€26/month) as your dev/staging server. Install Docker + Docker Compose. Configure SSH key-only access, fail2ban, ufw firewall. Add a separate user for the application with no sudo.

#### Step 6: Set up databases

Use docker-compose to run Postgres 15 with the TimescaleDB extension and Redis. Create three databases: `psx_dev`, `psx_test`, `psx_staging`. Schedule daily pg_dump backups to R2 / S3.

#### Step 7: CI/CD baseline

GitHub Actions workflows:
- Backend: lint (ruff), type-check (mypy), test (pytest), build Docker image, push to GitHub Container Registry on merge to main
- Frontend: lint (eslint), type-check (tsc), test (vitest), build, deploy preview on every PR via Vercel

#### Step 8: Observability from day one

Wire up Sentry SDKs in both frontend and backend before writing any business logic. Set up a basic Grafana dashboard hooked to Prometheus exporters for Postgres, Redis, and the API. BetterStack uptime monitor on the staging URL.

#### Step 9: Architectural Decision Records (ADRs)

Create `psx-docs/adr/` and write your first three ADRs:
- ADR-001: Why Next.js + FastAPI split
- ADR-002: Why TimescaleDB for time series
- ADR-003: Why we separated the inference service

This habit pays huge dividends in 6 months when you can't remember why you chose something.

### Phase 0 Acceptance Criteria

- [ ] PSX data licensing strategy decided and email sent
- [ ] Legal entity registered (or formal plan to register)
- [ ] Domain owned, email working, Cloudflare DNS active
- [ ] All five repos created with branch protection
- [ ] Hetzner server provisioned, Docker running, SSH locked down
- [ ] Postgres + TimescaleDB + Redis running and backed up
- [ ] CI/CD pipeline works: a "Hello World" PR to each repo passes lint, test, build, deploy
- [ ] Sentry receiving test errors, Grafana showing basic metrics, BetterStack uptime green

---

<a name="phase-1"></a>
## Phase 1 — MVP: The Tracker (8–10 weeks)

**Objective:** Ship a usable product. A real user can sign up, browse PSX stocks, build a watchlist, log trades into a portfolio, see correct after-tax returns, view technical indicators with plain-English explanations, compare stocks within a sector, and toggle Shariah-only mode.

This is the table-stakes feature set every PSX app has — but you'll do it better and free, which is the wedge.

### Sub-phase 1A: Data Ingestion (Weeks 1–2)

#### Step 10: Build the stock universe table

Create a `securities` table seeded with all currently-listed PSX symbols. Source: scrape `dps.psx.com.pk/eligible-scrips` or use the `psx-data-reader` Python library's symbol list as a starting point.

```sql
CREATE TABLE securities (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(20) UNIQUE NOT NULL,
  company_name VARCHAR(255) NOT NULL,
  sector VARCHAR(100) NOT NULL,
  is_kmi_compliant BOOLEAN DEFAULT FALSE,
  is_kse100 BOOLEAN DEFAULT FALSE,
  is_kse30 BOOLEAN DEFAULT FALSE,
  market_cap_pkr BIGINT,
  shares_outstanding BIGINT,
  listed_at DATE,
  delisted_at DATE,
  is_active BOOLEAN DEFAULT TRUE,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Step 11: Build the OHLCV ingestion worker

In `psx-ingest`, write a daily worker that:
1. After 4:30 PM PKT (market close + buffer), pulls EOD OHLCV for every active symbol
2. Inserts into a TimescaleDB hypertable
3. Validates: no negative volumes, no zero opens, no >50% single-day moves without a corresponding announcement (flag for review)

```sql
CREATE TABLE ohlcv_daily (
  symbol VARCHAR(20) NOT NULL,
  date DATE NOT NULL,
  open NUMERIC(12, 4),
  high NUMERIC(12, 4),
  low NUMERIC(12, 4),
  close NUMERIC(12, 4),
  volume BIGINT,
  value_pkr NUMERIC(20, 2),
  PRIMARY KEY (symbol, date)
);
SELECT create_hypertable('ohlcv_daily', 'date');
CREATE INDEX ON ohlcv_daily (symbol, date DESC);
```

#### Step 12: Backfill 5 years of history

Run a one-time backfill job that pulls 5 years of historical EOD data for every active symbol. Expect this to take 2–6 hours. Store raw responses in S3/R2 in case you ever need to re-parse.

#### Step 13: Corporate actions ingestion

Write a parallel worker that scrapes PUCARS (`dps.psx.com.pk/announcements`) daily for dividend declarations, bonus issues, rights issues, AGMs, and book-closure dates.

```sql
CREATE TABLE corporate_actions (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(20) NOT NULL REFERENCES securities(symbol),
  action_type VARCHAR(30) NOT NULL,  -- 'dividend_cash', 'dividend_stock', 'bonus', 'rights', 'agm', 'split'
  announcement_date DATE NOT NULL,
  ex_date DATE,
  record_date DATE,
  payment_date DATE,
  amount_per_share NUMERIC(12, 4),
  ratio_numerator INT,
  ratio_denominator INT,
  raw_announcement TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Step 14: Adjusted-price computation

Crucial for accurate backtests later. Write a function that, given raw OHLCV + corporate actions, produces split-and-dividend-adjusted close prices. Store both raw and adjusted in your tables. This is where most amateur stock apps go wrong — never compute returns on raw close prices when there have been splits or rights issues.

### Sub-phase 1B: Auth & User Management (Week 3)

#### Step 15: Database schema for users

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  email_verified_at TIMESTAMPTZ,
  password_hash VARCHAR(255),
  full_name VARCHAR(255),
  phone VARCHAR(20),
  cnic_last4 VARCHAR(4),  -- optional, for filer status verification later
  is_filer BOOLEAN DEFAULT FALSE,
  shariah_mode BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash VARCHAR(255) NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  user_agent TEXT,
  ip_address INET
);
```

#### Step 16: Auth flows

Implement: email/password signup with email verification, login with rate-limiting (max 5 failed attempts per IP per hour), password reset via email, optional 2FA via TOTP (Google Authenticator). Store password hashes with Argon2id, never bcrypt-only. Use HTTP-only secure cookies for session tokens, never localStorage.

#### Step 17: Frontend auth pages

Build `/signup`, `/login`, `/forgot-password`, `/verify-email`, `/settings/security`. Use Auth.js for client-side session handling. Add a middleware that protects all `/app/*` routes.

### Sub-phase 1C: Stock Browser & Watchlist (Weeks 4–5)

#### Step 18: API endpoints

```
GET  /api/v1/securities                    # list with filters: sector, kmi, search
GET  /api/v1/securities/{symbol}            # detail
GET  /api/v1/securities/{symbol}/ohlcv      # query: ?from=&to=&interval=daily
GET  /api/v1/securities/{symbol}/fundamentals
GET  /api/v1/securities/{symbol}/announcements
GET  /api/v1/sectors                        # list with current performance
GET  /api/v1/indices                        # KSE-100, KSE-30, KMI-30, etc.
GET  /api/v1/watchlist
POST /api/v1/watchlist                      # body: {symbol}
DELETE /api/v1/watchlist/{symbol}
```

Every list endpoint must support pagination, filtering, and sorting. Every response must be cached in Redis with a TTL appropriate to the data (1 minute for live prices during market hours, 1 hour for fundamentals, 24 hours for sector classifications).

#### Step 19: Stock detail page

The single most important page in the entire app. Layout (top to bottom):
- Header: symbol, company name, sector, KMI badge, current price, day change, day change %
- Price chart: TradingView Lightweight Charts, default 1-year daily, with timeframe toggles (1D / 1W / 1M / 3M / 1Y / 5Y / All)
- Quick stats grid: market cap, P/E, P/B, dividend yield, EPS, ROE, 52-week range, average volume
- Tabs: Overview / Financials / Announcements / Compare
- Add-to-watchlist button (toggles)
- Add-to-portfolio button (opens trade entry modal)

Critical UX: every metric label has a small (i) icon — clicking it opens a tooltip with a plain-English definition. "P/E Ratio: how much investors are paying per rupee of company earnings. A P/E of 10 means investors pay PKR 10 today for every PKR 1 the company earns per year."

#### Step 20: Watchlist page

Simple table view with symbol, current price, day change %, your custom note. Drag-to-reorder. Mobile-friendly card layout below 768px.

### Sub-phase 1D: Portfolio with Tax-Aware Ledger (Weeks 6–7)

This is your differentiator vs every other PSX app. Get it right.

#### Step 21: Database schema

```sql
CREATE TABLE portfolios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  base_currency VARCHAR(3) DEFAULT 'PKR',
  is_default BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
  symbol VARCHAR(20) NOT NULL REFERENCES securities(symbol),
  transaction_type VARCHAR(20) NOT NULL,  -- 'buy', 'sell', 'dividend', 'bonus', 'rights'
  transaction_date DATE NOT NULL,
  quantity NUMERIC(20, 4) NOT NULL,
  price_per_share NUMERIC(12, 4) NOT NULL,
  brokerage_pkr NUMERIC(12, 4) DEFAULT 0,
  fed_pkr NUMERIC(12, 4) DEFAULT 0,
  cvt_pkr NUMERIC(12, 4) DEFAULT 0,
  cgt_pkr NUMERIC(12, 4) DEFAULT 0,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE holdings_snapshot (
  -- denormalized rollup, refreshed nightly + on every transaction
  portfolio_id UUID NOT NULL,
  symbol VARCHAR(20) NOT NULL,
  quantity NUMERIC(20, 4) NOT NULL,
  avg_cost_pkr NUMERIC(12, 4) NOT NULL,
  total_invested_pkr NUMERIC(20, 2) NOT NULL,
  realized_pnl_pkr NUMERIC(20, 2) NOT NULL,
  total_dividends_received_pkr NUMERIC(20, 2) NOT NULL,
  PRIMARY KEY (portfolio_id, symbol)
);
```

#### Step 22: Tax engine

Build a pure Python module `psx_api/tax/cgt.py` that, given a sell transaction and the user's filer status, returns the exact CGT owed using current SECP rules. Make it configurable via a `tax_rules` table, not hardcoded — tax rates change.

```python
def calculate_cgt(
    buy_price: Decimal,
    sell_price: Decimal,
    quantity: Decimal,
    holding_period_days: int,
    is_filer: bool,
    sell_date: date,
) -> Decimal:
    """Returns CGT in PKR. Looks up rate from tax_rules table by sell_date."""
    ...
```

Key behaviors: FIFO accounting by default (per SECP convention), with optional LIFO and specific-lot identification for advanced users. NCCPL deducts CGT at source — your job is to compute and display the user's net.

#### Step 23: Trade entry UI

Modal form with: transaction type, symbol (autocomplete from securities table), date (defaults to today), quantity, price (defaults to current market price, editable), brokerage commission (defaults to user's saved broker rate, editable). On submit, run the tax engine, show a confirmation step that displays gross value, all charges, and net cash impact. Then save.

#### Step 24: Portfolio dashboard

Top-level page showing: total invested, current value, unrealized P&L (gross and after-tax), realized P&L YTD, dividends received YTD, total fees paid YTD, allocation pie by sector, holdings table with per-position day change and total return.

The "after-tax" framing is your unique sauce. Every other app shows gross numbers. You show: "Your portfolio is up PKR 47,500 — but if you sold today, you'd net PKR 39,800 after CGT and brokerage."

### Sub-phase 1E: Technical Indicators with Plain-English (Week 8)

#### Step 25: Indicator computation service

Use `pandas-ta` library — it computes 130+ indicators, fast, well-tested. Wrap it in a clean service:

```python
class IndicatorService:
    def compute(self, symbol: str, indicator: str, period: int = 14) -> pd.Series:
        df = self._fetch_ohlcv(symbol, lookback=period * 5)
        if indicator == "rsi":
            return ta.rsi(df["close"], length=period)
        elif indicator == "macd":
            return ta.macd(df["close"])
        # ... etc
```

Cache results aggressively — indicator values for closed days never change.

#### Step 26: Indicator panel UI

On the stock detail page, add an "Indicators" tab. User picks an indicator from a dropdown. Below the chart, show:
1. The indicator's current value
2. A traffic-light interpretation: green (bullish signal) / yellow (neutral) / red (bearish)
3. A 2–3 sentence plain-English explanation: "RSI is at 78. Values above 70 typically suggest a stock is overbought and may pull back. This is a cautionary signal, not a sell order."
4. A "What is RSI?" expandable section with the full educational explainer

Ship with these 8 indicators in v1: RSI, MACD, SMA (50/200), EMA (20), Bollinger Bands, Stochastic, OBV, ATR. Add more in later phases.

### Sub-phase 1F: Sector Comparison + Shariah Toggle (Week 9)

#### Step 27: Sector comparison view

URL: `/sectors/{sector_slug}/compare`. User selects 2–4 stocks. Display:
- Overlaid normalized price chart (each stock starts at 100 on a chosen base date)
- Side-by-side fundamentals table (P/E, P/B, ROE, ROA, dividend yield, debt-to-equity, payout ratio, market cap)
- Each metric cell shows the value plus a sector percentile rank ("P/E 8.4 — better than 75% of cement sector")

#### Step 28: Sector heatmap

URL: `/sectors`. Treemap-style view, each rectangle a stock, sized by market cap, colored by day change %. Click any rectangle to drill into the stock detail. Use ECharts treemap.

#### Step 29: Shariah Mode

Settings toggle in user profile. When enabled:
- Every search/screen filters to KMI-compliant stocks only
- A persistent green "Shariah Mode On" badge in the header
- Trade entry warns if a non-compliant stock is being added (you can still add it, but with a warning)
- Watchlist and portfolio show non-compliant items grayed out with a warning icon

### Sub-phase 1G: Polish & Deploy v1 (Week 10)

#### Step 30: Empty-state and loading-state design

Every page has a thoughtful empty state. "You don't have a portfolio yet. Want to start with a virtual one to learn first, or log a real trade?" Every loading state uses skeletons, not spinners.

#### Step 31: Mobile responsive review

Walk through every page on a 375px viewport. Fix everything that breaks. The PSX user base is heavily mobile-first.

#### Step 32: Error tracking & quality

Trigger a deliberate error in every major code path and verify Sentry catches it. Run Lighthouse on the key pages — aim for Performance > 90, Accessibility > 95.

#### Step 33: Deploy to production

Provision a production Hetzner server (separate from staging). Set up blue-green deploys via Docker. DNS pointing to production. Soft launch to 20–50 friends and family, gather feedback for a week, fix critical issues.

### Phase 1 Acceptance Criteria

- [ ] User can sign up, verify email, log in, enable 2FA
- [ ] User can search any of the ~500 PSX stocks and view a stock detail page with chart, fundamentals, announcements
- [ ] User can build a watchlist
- [ ] User can create one or more portfolios and log buy/sell/dividend transactions
- [ ] Portfolio dashboard correctly shows after-tax returns matching manual calculation on 10 test cases
- [ ] User can view 8 technical indicators with plain-English interpretation on any stock
- [ ] User can compare 2–4 stocks within a sector side by side
- [ ] User can toggle Shariah Mode and see the entire app filter accordingly
- [ ] All pages mobile-responsive
- [ ] Lighthouse Performance > 90, Accessibility > 95 on top 5 pages
- [ ] Sentry, Grafana, BetterStack all healthy on production

---

<a name="phase-2"></a>
## Phase 2 — The Analyst: Predictions, Goals, Backtests (10–12 weeks)

**Objective:** Move from tracker to analyst. The user now gets predictions (with honest confidence labels), can plan toward goals like a Hajj fund or retirement, and can backtest simple strategies on real history.

### Sub-phase 2A: Risk Profiling & Goal Engine (Weeks 1–2)

#### Step 34: Risk-profiling questionnaire

12 questions, three axes:
- **Risk tolerance** (5 questions): "If your portfolio dropped 30% in a month, would you (a) sell everything, (b) sell some, (c) hold, (d) buy more?"
- **Time horizon** (3 questions): when do you need this money?
- **Knowledge level** (4 questions): basic terminology checks

Score each axis 1–5, map combinations to one of five archetypes: Conservative Saver, Cautious Beginner, Balanced Builder, Growth Seeker, Aggressive Trader. Store on user profile and let users retake every 6 months.

#### Step 35: Goal database & engine

```sql
CREATE TABLE goals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  goal_type VARCHAR(30) NOT NULL,  -- 'retirement', 'hajj', 'education', 'home', 'marriage', 'custom'
  target_amount_pkr NUMERIC(20, 2) NOT NULL,
  target_date DATE NOT NULL,
  current_amount_pkr NUMERIC(20, 2) DEFAULT 0,
  monthly_contribution_pkr NUMERIC(20, 2) DEFAULT 0,
  linked_portfolio_id UUID REFERENCES portfolios(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Implement the time-value-of-money math: given target, date, current, and monthly contribution, solve for required CAGR. Show the user the result and rate it: "You need 24% CAGR — this is unrealistically high for the long term. Increase your monthly contribution to PKR 45,000 or extend the deadline by 2 years."

#### Step 36: Recommended allocation per goal

For each goal-archetype combo, generate a target asset allocation. Use a simple lookup table for v1, not a real optimizer:

| Archetype | <2 yrs | 2–5 yrs | 5–10 yrs | >10 yrs |
|---|---|---|---|---|
| Conservative | 100% T-Bills | 30% equity / 70% TB | 50/50 | 60/40 |
| Balanced | 30/70 | 50/50 | 70/30 | 80/20 |
| Aggressive | 50/50 | 70/30 | 90/10 | 100% equity |

Phase 3 will replace this with real Markowitz mean-variance optimization.

### Sub-phase 2B: Backtesting Engine (Weeks 3–5)

#### Step 37: Backtest infrastructure

Use **vectorbt** as the backtesting library. Set up a Celery task queue for backtest jobs — even a simple 5-year SMA crossover backtest takes 100–500ms, which is too slow for a synchronous request when 100 users hit it at once.

```python
# Backtest contract
class BacktestRequest(BaseModel):
    symbol: str
    strategy: str  # 'sma_cross', 'rsi_oversold', 'macd_signal', 'bollinger_mean_revert', 'buy_hold'
    start_date: date
    end_date: date
    initial_capital_pkr: Decimal
    parameters: dict  # strategy-specific

class BacktestResult(BaseModel):
    final_value: Decimal
    total_return_pct: float
    cagr: float
    sharpe_ratio: float
    max_drawdown_pct: float
    num_trades: int
    win_rate: float
    benchmark_return_pct: float  # buy-and-hold same period
    trades: list[Trade]  # for narration
    equity_curve: list[tuple[date, Decimal]]
```

#### Step 38: Five preset strategies

Ship with: SMA crossover (50/200), RSI oversold/overbought (30/70), MACD signal-line cross, Bollinger Band mean reversion, dividend-reinvestment buy-and-hold. Each strategy is implemented as a vectorbt signal generator — well-tested, with unit tests checking known-correct outcomes on synthetic price series.

**Critical:** Use adjusted prices for backtests, not raw close. Account for brokerage commission in every simulated trade. Without these, your backtest results are fiction.

#### Step 39: Trade narration

After every backtest, the system generates a plain-English narration of every trade made:

> "On March 12, 2022, the 50-day moving average crossed above the 200-day moving average — a 'golden cross' signal. The strategy bought 100 shares of LUCK at PKR 142.50, paying PKR 142,500 plus PKR 285 in commission. The position was held for 187 days. On September 15, the moving averages crossed back, and the strategy sold at PKR 178.20 for a gross profit of PKR 3,570 (25% return), reduced to PKR 3,000 net of all fees and CGT."

This is what turns a backtest from a chart into a teaching tool.

#### Step 40: Backtest UI

Wizard-style flow: pick stock → pick strategy → pick date range → review → run. Result page shows: equity curve overlaid with buy-and-hold benchmark, summary stats card, the trade-by-trade narration, "Lessons" panel highlighting things like "this strategy lost money during the 2022 sideways market — strategies based on momentum need trending markets."

### Sub-phase 2C: Prediction Engine (Weeks 6–9)

#### Step 41: Feature engineering pipeline

For each stock, compute a 60-day rolling feature matrix daily:

```
- OHLCV log returns (1, 5, 10, 20-day)
- RSI(14), Stochastic(14)
- MACD (12, 26, 9), MACD signal, MACD histogram
- Bollinger %B (20, 2)
- Williams %R(14)
- Momentum(10)
- Disparity 5, Disparity 10
- ATR(14) normalized by price
- OBV change
- Volume Z-score (vs 20-day mean)
- Price Z-score (vs 50-day mean)
- KSE-100 same-day return (market context)
- Sector index same-day return
- KIBOR 6M (interest rate context)
- PKR/USD daily change (FX context)
```

This is your feature universe. Store computed features in a TimescaleDB table for fast retrieval.

#### Step 42: Train ensemble models

For each of the top 50 most-liquid PSX stocks (avg daily volume > some threshold), train three models:

1. **LSTM** (1D-CNN + LSTM hybrid): input = 60-day window of features, output = probability that next-day close > today's close. Train on 2015–2022, validate 2023, test 2024.
2. **XGBoost classifier**: input = today's full feature vector, output = same probability.
3. **Random Forest**: same as above.

Train and evaluate **per stock**. Save R² for regression task, accuracy/F1 for classification, and the test-set ROC curve. Be ruthless: any stock where the best model fails to beat a 53% accuracy baseline gets marked "model unreliable — predictions disabled for this stock."

Research baseline: ANN and SVM hit roughly 85% binary classification accuracy on Pakistani stocks using 27 technical indicators, Random Forest 84%, and LSTM 78%, with Williams %R, Momentum, and Disparity 5 the strongest features. Aim to match this on liquid stocks; accept lower on illiquid ones.

#### Step 43: Stacking layer

Train a logistic regression meta-model that takes the three model outputs as inputs and produces a final probability. Add a confidence score = 1 - variance(model outputs). High agreement → high confidence; large disagreement → low confidence.

#### Step 44: Inference service

Deploy as separate FastAPI microservice (`psx-inference`). Models stored as ONNX files for fast loading. Endpoint:

```
POST /predict
Body: {"symbol": "ENGRO", "horizon_days": 1}
Response: {
  "symbol": "ENGRO",
  "probability_up": 0.68,
  "confidence": "high",
  "as_of_date": "2026-05-07",
  "horizon_days": 1,
  "model_version": "v1.2.3",
  "key_features": [
    {"name": "RSI(14)", "value": 42.1, "contribution": "neutral"},
    {"name": "MACD signal", "value": "bullish_cross", "contribution": "positive"},
    {"name": "Volume Z-score", "value": 2.3, "contribution": "positive"}
  ]
}
```

#### Step 45: Prediction UI on stock detail page

Add a "Signal" panel:
- Big probability gauge: "68% chance of upward close tomorrow"
- Confidence badge: "High confidence" / "Medium" / "Low" / "Predictions disabled for this stock"
- Top 3 contributing features listed
- A clear disclaimer: "This is a probabilistic signal, not a guarantee. Past model accuracy on this stock: 71%."
- A link to "How does this work?" explainer page

#### Step 46: Model retraining schedule

Monthly retraining job. Track every model version's live performance vs predicted in a `model_predictions` table. If any model's rolling 30-day live accuracy drops below threshold, automatically disable predictions for affected stocks and alert you.

### Sub-phase 2D: Macro Overlays (Weeks 10–11)

#### Step 47: Macro data ingestion

Daily worker pulls: KIBOR (1M, 3M, 6M, 12M) from SBP website, SBP policy rate, PKR/USD spot, Brent crude oil, gold per tola. Store in `macro_indicators` table, hypertable in TimescaleDB.

#### Step 48: Chart overlay UI

On every price chart, add an "Overlay" dropdown. User picks a macro variable; the chart adds a second Y-axis with the macro line overlaid on the stock price. Educational: a beginner immediately sees that OGDC tracks oil, that banks rally on rate decisions, that exporters benefit from PKR depreciation.

### Sub-phase 2E: Polish & Deploy v2 (Week 12)

Same pattern as Phase 1: error testing, performance review, mobile review, gradual rollout.

### Phase 2 Acceptance Criteria

- [ ] User completes risk profile, sees their archetype, can retake it
- [ ] User can create goals (retirement, Hajj, etc.) and gets a realistic CAGR analysis
- [ ] Each goal shows recommended allocation per the lookup table
- [ ] User can run backtests on any stock with 5 strategies and see clear narration
- [ ] Predictions live on top 50 liquid stocks with proper confidence labeling
- [ ] Stocks where the model failed validation explicitly say "predictions disabled"
- [ ] User can overlay any of 5 macro variables on any price chart
- [ ] Model performance dashboard exists internally — you can see if any model is degrading
- [ ] Monthly retraining job runs unattended

---

<a name="phase-3"></a>
## Phase 3 — The Guardian: Sentiment, Anomaly Detection, Macro (8–10 weeks)

**Objective:** This is where the app becomes uniquely valuable. Pump-and-dump alerts, news sentiment, and the filer/non-filer simulator address the top fears and pain points of Pakistani retail investors that no other app addresses.

### Sub-phase 3A: News & Sentiment Pipeline (Weeks 1–4)

#### Step 49: News scrapers

Build modular scrapers in `psx-ingest/scrapers/`:
- `dawn_business.py` (Dawn business section RSS + page scraping)
- `business_recorder.py`
- `profit_pakistantoday.py`
- `the_news_business.py`
- `tribune_business.py`
- `pucars.py` (PSX official announcements — already done in Phase 1)

Each scraper runs every 30 minutes during market hours, every 6 hours otherwise. Stores raw articles in:

```sql
CREATE TABLE news_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source VARCHAR(50) NOT NULL,
  url VARCHAR(1000) UNIQUE NOT NULL,
  headline TEXT NOT NULL,
  body TEXT NOT NULL,
  published_at TIMESTAMPTZ NOT NULL,
  scraped_at TIMESTAMPTZ DEFAULT NOW(),
  language VARCHAR(10) DEFAULT 'en'
);
```

Respect robots.txt. Rate-limit aggressively. Have a clear "we link back to source" policy on your site.

#### Step 50: Entity extraction

For each article, extract which PSX-listed companies are mentioned. Build a regex + alias matcher first (fast, cheap, ~95% recall): map "Engro Corporation", "ENGRO", "Engro Corp" → ENGRO. Maintain a `company_aliases` table. Phase 4 can upgrade to a small NER model.

```sql
CREATE TABLE article_mentions (
  article_id UUID NOT NULL REFERENCES news_articles(id),
  symbol VARCHAR(20) NOT NULL REFERENCES securities(symbol),
  PRIMARY KEY (article_id, symbol)
);
```

#### Step 51: Sentiment scoring

Two-tier approach:
1. **Tier 1 (fast, free):** Use a pre-trained FinBERT model (e.g. `ProsusAI/finbert`). Run inference on each article headline + first 200 words. Output: positive / neutral / negative with confidence. ~50ms per article on CPU.
2. **Tier 2 (accurate, costs):** For articles flagged as high-impact (mentioning earnings, M&A, regulatory action), additionally run an LLM (Llama 3.1 8B locally on a GPU instance, OR cheap API like Groq or Together) with a structured-output prompt extracting (a) tickers, (b) event type, (c) sentiment polarity, (d) reasoning.

```sql
CREATE TABLE article_sentiment (
  article_id UUID NOT NULL REFERENCES news_articles(id),
  symbol VARCHAR(20) NOT NULL,
  polarity NUMERIC(4, 3) NOT NULL,  -- -1 to +1
  event_type VARCHAR(30),  -- 'earnings', 'guidance', 'regulatory', 'macro', 'mna', 'leadership', 'scandal'
  model_version VARCHAR(20),
  scored_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (article_id, symbol)
);
```

#### Step 52: News Pulse aggregation

For each symbol, compute a rolling 5-day sentiment score with exponential time decay:

```
pulse(symbol, today) = Σ[ polarity_i * exp(-(today - pub_date_i) / 5) ]
```

Normalize to -100 to +100. Display on stock detail page as a colored bar with the top 3 driving headlines visible.

#### Step 53: Plug sentiment into the prediction engine

Add `sentiment_pulse_5d`, `sentiment_pulse_1d`, and `news_volume_z` (anomalous surge in coverage) as features to the Phase 2 prediction models. Retrain. Re-evaluate. Document the lift.

### Sub-phase 3B: Pump-and-Dump Detection (Weeks 5–7)

#### Step 54: Layer 1 — Rule-based detector

Daily after-close worker that flags suspicious days:

```python
def flag_suspicious_day(symbol: str, date: date) -> dict | None:
    df = get_recent_ohlcv(symbol, lookback=30)
    today = df.iloc[-1]
    vol_ma_20 = df["volume"].iloc[-21:-1].mean()
    vol_spike = today["volume"] / vol_ma_20
    price_change = (today["close"] - today["open"]) / today["open"]

    if vol_spike > 4 and price_change > 0.03:
        return {
            "type": "pump_alert",
            "vol_spike": vol_spike,
            "price_change": price_change,
            "explanation": f"Volume today is {vol_spike:.1f}x the 20-day average with a {price_change*100:.1f}% price increase."
        }
    if vol_spike > 4 and price_change < -0.03:
        return {"type": "dump_alert", ...}
    return None
```

This rule pattern is a well-established baseline — the literature confirms that sharp coordinated changes in price and volume are the two strongest single-variable indicators of a pump-and-dump.

#### Step 55: Layer 2 — Isolation Forest anomaly detector

Per-stock Isolation Forest trained on 2-year history of features (close, volume, vol_spike, price_change, intraday_range_pct, gap_pct). Contamination set to 2%.

```python
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

features = ["close", "volume", "vol_spike", "price_change", "intraday_range_pct", "gap_pct"]
scaler = StandardScaler()
X = scaler.fit_transform(df[features].fillna(0))
model = IsolationForest(contamination=0.02, random_state=42)
df["anomaly_score"] = -model.score_samples(X)  # higher = more anomalous
```

This unsupervised approach is well-supported by the research as a practical baseline for manipulation detection given the absence of labelled data.

#### Step 56: Layer 3 — News-correlation filter

A pure spike with no news context is more suspicious than a spike on earnings day. Combine: if pump_alert AND no announcement in PUCARS in the last 3 days AND no high-impact news mentioning the symbol → escalate to "high suspicion." If accompanied by an earnings beat or major announcement → suppress alert.

#### Step 57: User-facing UI

Two surfaces:
- **Stock detail page:** small flag icon with tooltip — "Trading volume today is 7× the 30-day average with no announced corporate news. Be cautious."
- **Watchlist & portfolio:** an alerts inbox — every suspicious-day flag for any stock the user holds or watches gets pushed as an in-app notification and (opt-in) email/SMS.

### Sub-phase 3C: Tax Filer Simulator (Week 8)

#### Step 58: Filer-vs-non-filer simulator

A page where the user inputs their last 12 months of trades (or pulls from their portfolio history) and sees side-by-side: total CGT paid as filer vs non-filer, total fees, net retained. Explicit call-to-action: "By becoming a tax filer, you would have kept an additional PKR 87,400 last year. Here's how to file."

Link to FBR's e-filing portal and a step-by-step guide. This is genuine social good and a viral feature — people share it.

### Sub-phase 3D: Polish & Deploy v3 (Weeks 9–10)

Same playbook. By now your release process is well-oiled.

### Phase 3 Acceptance Criteria

- [ ] News scrapers running for 5 sources, articles flowing into the database
- [ ] Sentiment scoring live, News Pulse visible on every stock detail page
- [ ] Sentiment features added to prediction models, performance lift documented
- [ ] Pump-and-dump rule-based alerts trigger correctly on historical known cases
- [ ] Isolation Forest anomaly scores computed daily for every active stock
- [ ] Suspicious-day alerts surface in user inbox for held/watched stocks
- [ ] Filer simulator working with real historical FBR rates
- [ ] All systems running unattended for 14 consecutive days without manual intervention

---

<a name="phase-4"></a>
## Phase 4 — The Community: Benchmarking & Advanced Features (6–8 weeks)

**Objective:** Network effects. Once you have data on thousands of portfolios, anonymized benchmarking and community signals become possible — and create lock-in no competitor can replicate without first matching your user base.

### Sub-phase 4A: Anonymized Portfolio Benchmarking (Weeks 1–2)

#### Step 59: Opt-in data sharing

Setting: "Help others by sharing my portfolio anonymously for community benchmarking. Only aggregated patterns are shown — never your name, identity, or specific trades."

#### Step 60: Aggregation pipeline

Nightly batch: compute anonymized aggregates by user archetype, age bucket, portfolio size bucket. Examples:
- "Aggressive Trader, 25–34, PKR 100K–500K portfolios": top 10 most-held stocks, median sector allocation, median YTD return
- "Balanced Builder, 35–44, > PKR 1M portfolios": same metrics

#### Step 61: Benchmark UI

On the user's portfolio dashboard, add a "How I compare" panel:
- "Your YTD return: 18.4%. Median for your archetype/age/size: 22.1%. You're in the 38th percentile."
- "Your top sector: Banks (42%). Your peer group's top sector: Cement (28%)."
- Aspirational: "Top 10% performers in your peer group hold these 5 stocks more often than you do: ..." (only if the user opts into "show peer holdings.")

### Sub-phase 4B: Custom Strategy Builder (Weeks 3–4)

#### Step 62: No-code rule builder

UI for power users: build custom backtest strategies with a visual rule chain:
- Entry: when [RSI(14)] [<] [30] AND [Volume] [>] [SMA(20) × 1.5]
- Exit: when [RSI(14)] [>] [70] OR [Position held > 30 days]
- Position sizing: 10% of capital per position, max 5 concurrent

Parse the rules into vectorbt-compatible signal generators. Save user-created strategies, allow sharing them publicly.

#### Step 63: Strategy marketplace

Users can publish their tested strategies. Other users can fork, run on different stocks, modify. Each strategy shows verified backtest performance computed by the platform (not user-claimed).

### Sub-phase 4C: Shariah Compliance Monitor & Dividend Purification (Week 5)

#### Step 64: KMI delisting watch

Worker subscribes to Meezan Bank's KMI updates. Whenever a stock is added or removed from KMI, every Shariah-Mode user holding that stock gets a notification: "FFC has been removed from the KMI All-Share Index based on the latest review. You may want to review your position."

#### Step 65: Dividend purification calculator

For each Shariah-Mode user, annually estimate the purification amount: typically 5% of cash dividends from KMI-compliant stocks (a conservative figure used by major Islamic mutual funds; the user can adjust). Generate a year-end report listing the recommended purification amount per holding, with checkboxes for "marked as donated."

### Sub-phase 4D: Educational Micro-Learning (Weeks 6–7)

#### Step 66: Skill tree

Gamified progression: 30+ short lessons, each 3–5 minutes, each ending in a 3-question quiz. Topics cover: what is a stock, how IPOs work, reading a balance sheet, understanding P/E, what RSI actually measures, why diversification matters, how taxes work in PSX, what to never do. Track user completion. Award badges. Display badges on portfolio dashboard.

The killer move: **link lessons to user actions**. If the user is about to make a 50% concentrated bet on a single stock, suggest: "You haven't completed the Diversification lesson yet — want to learn before clicking trade?"

#### Step 67: Polish & Deploy v4

### Phase 4 Acceptance Criteria

- [ ] Opt-in benchmarking working with > 100 users contributing anonymized data
- [ ] Custom strategy builder lets a non-coder create and backtest a non-trivial strategy
- [ ] At least 10 community-published strategies available
- [ ] KMI delisting alerts fire correctly on test cases
- [ ] Dividend purification calculator generates accurate year-end reports
- [ ] Skill tree has 30+ lessons covering core curriculum

---

<a name="phase-5"></a>
## Phase 5 — Scale, Polish, Launch (4–6 weeks)

**Objective:** Take what's working with hundreds of beta users and prepare for thousands. Performance, security, compliance, and a marketing engine.

### Step 68: Performance audit

Profile the slowest 20 endpoints. Add database indexes where queries do sequential scans. Move the heaviest aggregations into materialized views refreshed nightly. Add CDN caching headers to every static asset.

### Step 69: Security audit

Run automated scans (OWASP ZAP, npm audit, pip-audit, Snyk). Hire a freelance pentester for a one-week engagement (~$1,500–$3,000). Fix everything they find. Get SOC 2 readiness checklist done even if you don't certify yet — investors will ask.

### Step 70: Legal & Compliance review

Get a Pakistani lawyer to review:
- Terms of Service (especially the disclaimer that you are not a SECP-registered investment advisor and predictions are not advice)
- Privacy Policy (PII handling, data retention, user rights)
- Data licensing arrangement with PSX or Capital Stake
- SECP regulations on what constitutes "investment advice" in Pakistan — there's a real line between providing analytical tools (legal) and giving personalized recommendations (regulated). Stay clearly on the right side of it.

### Step 71: Marketing site

Separate marketing site at the root domain (Next.js, Vercel). Pages: home, features, pricing, blog, about. The blog matters more than you think — write 20 SEO-targeted articles on PSX topics ("How to start investing in PSX with PKR 25,000," "Understanding PSX taxes," "What is the KSE-100"). This drives organic acquisition for years.

### Step 72: Pricing & monetization

Three tiers:
- **Free:** core tracker, watchlist, portfolio with tax engine, basic indicators, 1 portfolio, sector comparison, Shariah toggle. Forever free.
- **Pro (~PKR 800–1,200/month):** predictions on all stocks (free tier sees top 20 only), sentiment, anomaly alerts, unlimited portfolios, custom backtests, goal planning.
- **Pro+ (~PKR 2,500/month):** API access, advanced rebalancing, priority support, early access to new features.

Why this works: the free tier alone is better than what 90% of users have today, which drives signups. The Pro tier targets the engaged minority who'll happily pay for the analyst layer.

### Step 73: Launch sequencing

1. **Soft launch:** invite-only, first 500 users from your network and beta program
2. **Public beta:** open signup, no paid tiers active, gather feedback
3. **Pricing launch:** turn on Pro tier, grandfather beta users with 6 months free
4. **Press push:** reach out to ProPakistani, TechJuice, Dawn Business, Profit Pakistan Today with a story angle ("the first PSX app with honest AI predictions," "Pakistani founder builds Bloomberg Terminal for retail")

### Phase 5 Acceptance Criteria

- [ ] Top 20 endpoints respond < 200ms p95
- [ ] No critical or high-severity security findings open
- [ ] Lawyer-approved ToS, Privacy Policy, and disclaimers live
- [ ] Marketing site live with 20+ blog posts
- [ ] Stripe / local payment gateway integrated for Pro tier
- [ ] First 1,000 users onboarded
- [ ] First paying customer

---

<a name="cross-cutting"></a>
## Cross-Cutting Concerns (Apply to Every Phase)

### Testing strategy

- **Unit tests:** every pure function (tax engine, indicator math, signal generators) > 90% coverage
- **Integration tests:** every API endpoint hit through the real test database
- **E2E tests:** Playwright suite covering signup, login, add portfolio, log trade, view prediction. Run on every PR.
- **Backtest validation:** for every strategy, a fixed test case with known correct outcome (computed manually) that fails CI if the math drifts

### Documentation

- API docs auto-generated from FastAPI's OpenAPI schema, hosted at `/api/docs`
- Internal runbooks: "what to do when prediction service is down," "how to retrain a model from scratch," "how to handle a PSX symbol getting delisted"
- ADRs for every non-obvious decision

### Observability

- Every request logged with structured JSON (timestamp, user_id_hash, endpoint, status, latency)
- Custom metrics: predictions served per minute, model confidence distribution, anomaly alerts fired per day
- Dashboards reviewed weekly even when nothing is broken

### Data integrity

- Daily reconciliation job: total quantities held in `holdings_snapshot` must equal sum of all transactions. If not, alert.
- Idempotency keys on every mutating endpoint
- Soft-delete (never hard-delete) user data; comply with deletion requests via an explicit purge job

### Disaster recovery

- Postgres backups every 6 hours, retained 30 days
- Backup restore tested quarterly (an untested backup is no backup)
- Runbook for full-region outage
- One-click "read-only mode" toggle for the API in case of partial failures

---

<a name="costs"></a>
## Cost & Infrastructure Estimates (Monthly, USD)

### Phase 1 (1–500 users)

| Item | Cost |
|---|---|
| Hetzner CCX23 (staging+prod combined) | ~$30 |
| Vercel Pro (frontend) | $20 |
| Cloudflare (DNS, CDN) | $0 |
| Sentry (free tier) | $0 |
| BetterStack | $10 |
| Domain + email | $10 |
| **Total** | **~$70/month** |

### Phase 2 (500–2,000 users)

| Item | Cost |
|---|---|
| Hetzner CCX33 (prod) + CCX13 (staging) | ~$90 |
| Inference GPU (Hetzner GPU dedicated, or RunPod on-demand) | ~$80 |
| Vercel Pro | $20 |
| Sentry Team | $26 |
| Capital Stake API (if licensed) | TBD via contract |
| **Total** | **~$220/month + data licensing** |

### Phase 3+ (2,000–10,000 users)

| Item | Cost |
|---|---|
| Hetzner dedicated server (production) | ~$120 |
| Inference GPU (always-on) | ~$200 |
| Postgres replica + read scaling | ~$80 |
| Sentry Business | $80 |
| LLM API costs (sentiment tier 2, ~50K articles/month) | ~$50 |
| Email service (SendGrid / Postmark) | $20 |
| SMS (Twilio) for alerts | usage-based |
| **Total** | **~$600/month + data licensing + LLM usage** |

### One-time costs

- Pentest: $1,500–3,000
- Lawyer review (ToS, privacy, advisory line): $500–1,500
- Logo + brand identity: $300–1,500
- Initial marketing content (20 SEO posts): $1,000–2,000

---

## Final Words

The biggest risk to this project isn't technical — it's scope creep. Every phase ships a usable product. Resist the temptation to build Phase 3 features in Phase 1 because they sound cool. The MVP at the end of Phase 1 is already better than 80% of what's available today; if you ship Phase 1 in 10 weeks and gather real users, you'll learn things that change Phase 2's plan.

Second-biggest risk: PSX data licensing. Get the legal path clarified early so you're never blocked by it.

Third: model honesty. The market is full of "AI stock prediction" apps that are essentially gambling tools. The thing that will set this product apart is **calibrated, conservative confidence labeling** — saying "we don't know" loudly when the model doesn't know. That's the trust foundation everything else stands on.

Build phase by phase. Ship working software at the end of every phase. Talk to users between phases. The plan above is a map, not a contract — adjust based on what you learn.
