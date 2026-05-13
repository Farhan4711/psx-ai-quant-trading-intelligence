/**
 * Curated starter blog posts. Phase 5 ships 3 SEO-targeted posts so the
 * /blog index isn't empty at launch. Future posts can be added here or
 * migrated to a CMS / MDX setup when the cadence picks up.
 *
 * Each `body` is plain markdown — paragraphs separated by blank lines,
 * `**bold**`, and `## H2` only. The minimal renderer in BlogPost handles
 * those without an MDX dep.
 */

export interface BlogPost {
  slug: string;
  title: string;
  description: string;
  published_at: string;
  read_minutes: number;
  body: string;
}

export const POSTS: BlogPost[] = [
  {
    slug: "how-to-start-investing-in-psx-with-pkr-25000",
    title: "How to start investing in PSX with PKR 25,000",
    description:
      "A practical step-by-step for opening a CDC sub-account, picking a broker, and making your first trade — without losing your shirt in the first month.",
    published_at: "2026-05-08",
    read_minutes: 8,
    body: `## Step 1 — Open a CDC investor account

Visit a participating broker (the Top-10 are listed on PSX's website). You'll need your CNIC, a passport-size photo, and PKR 5,000 for the account-opening deposit. Most brokers waive their setup fee for new clients these days; ask before paying.

## Step 2 — File your annual income tax return

Yes, before you trade. Under the Finance Act 2024, **non-filers pay 45% CGT** while filers pay 15%. On PKR 25,000 of expected gains over a year, that's a PKR 7,500 difference — about a third of your capital. File your return first. FBR's IRIS portal will list you on the ATL within a few weeks.

## Step 3 — Pick 4-5 stocks, not 1

The temptation when starting small is to put everything in one "high-conviction" name. Statistically, you'll be wrong about 30-40% of those convictions, and one bad pick wipes out months of patience. Spread across **at least 4 names in different sectors** — banks, fertilizer, oil-and-gas, cement is a reasonable starting blend.

## Step 4 — Keep an emergency fund separate

PKR 25,000 invested means you've already mentally written that money off for the next 3-5 years. If you might need it sooner, it shouldn't be in equities. Keep **3-6 months of expenses** in a separate savings account before you put a rupee in the market.

## Step 5 — Track everything

Manual spreadsheets work for a month. After that the dividend/bonus/rights events compound and you'll lose track of cost basis. Use a tool that handles FIFO matching and CGT — we built one (PSX AI), but several others exist. The point isn't which tool; the point is **track from day one**.

## What to expect

Year-one returns are usually disappointing. KSE-100 averages around 14% nominal in PKR over long horizons, but any single year can be -30% to +60%. The math works **over decades**, not weeks. Set expectations accordingly and don't measure your portfolio every day — the volatility will exhaust you and the daily noise has no signal.

## Common mistakes to avoid

- **Buying tips from WhatsApp groups.** Most are pump-and-dump operations dressed as analysis. Volume spikes + price moves + no announced news = walk away.
- **Averaging down on losers.** Sometimes makes sense; usually it's throwing good money after bad. Have a thesis-revisit rule, not a price-based one.
- **Ignoring dividends.** PSX has some of the highest dividend yields in EM equities (sometimes 8-12% on bank stocks). Reinvest them; compounding does the work.
`,
  },
  {
    slug: "understanding-psx-capital-gains-tax-after-finance-act-2024",
    title: "Understanding PSX capital gains tax after the Finance Act 2024",
    description:
      "What the new flat 15% / 45% CGT regime means for retail investors, when older rules still apply, and how filer status changes the math.",
    published_at: "2026-05-08",
    read_minutes: 6,
    body: `## What changed

Before the Finance Act 2024, CGT on PSX equities was **progressive by holding period**: 15% if you sold within a year, 12.5% in years 1-2, dropping to 0% after 4 years for filers. Non-filers paid roughly double the rate at each tier.

The Finance Act 2024 — effective **1 July 2024 for securities acquired on or after that date** — replaced this with a flat rate:

- **Filer**: 15% on gains, regardless of holding period
- **Non-filer**: 45% on gains, regardless of holding period

Securities acquired before 1 July 2024 still follow the older progressive schedule. So if you bought ENGRO in 2022 and sell today, the older rules apply; if you bought it last week and sell today, the flat 15%/45% applies.

## Why filer status matters more now

Under the old regime, filing your return mattered but not by much — the gap was typically 1-2 tier rates. **Now the gap is 30 percentage points.**

A simple example: you bought 1,000 shares of LUCK at PKR 700 (acquired post-July-2024), sold at PKR 850. Gain = PKR 150,000.

- **As a filer**: PKR 22,500 in CGT
- **As a non-filer**: PKR 67,500 in CGT

That's a **PKR 45,000 difference on a single trade**. Across a year of trading it gets very real, very fast.

## How NCCPL handles it

NCCPL (National Clearing Company) deducts CGT **at source** — before the cash reaches your broker account. You don't write a separate cheque to FBR for it. You will see it on your broker statement under "tax deducted at source."

This means: even if you forget about taxes, NCCPL doesn't. The only thing you control is the **rate** they apply, which is determined by your ATL (Active Taxpayer List) status. Become a filer; stay on the ATL; pay 15% instead of 45%.

## How to become a filer

1. Get an NTN (National Tax Number) via FBR's IRIS portal — free, online, takes a few days.
2. File your annual income tax return — also via IRIS, free if you have a simple return.
3. Wait for FBR to publish the next ATL update (monthly).
4. Once on the ATL, you're a filer for tax purposes. NCCPL automatically applies the filer rate.

## What this article doesn't cover

- Wash sale rules (Pakistan doesn't have them, but careful sale-then-rebuy patterns can attract FBR scrutiny)
- Tax on dividends (separate withholding tax, also affected by filer status, but a different rate)
- Tax on bonus shares (deemed dividend at issuance for tax purposes, separate treatment)

If your trading is more than casual, talking to a chartered accountant is worth it once a year.
`,
  },
  {
    slug: "what-is-the-kse-100",
    title: "What is the KSE-100?",
    description:
      "The benchmark index of Pakistan Stock Exchange, what's in it, how it's weighted, and what it actually tells you about your portfolio.",
    published_at: "2026-05-08",
    read_minutes: 5,
    body: `## The basics

The **KSE-100** is Pakistan Stock Exchange's flagship benchmark — the 100 largest listed companies by market capitalisation, drawn from each major sector. It's the closest thing PSX has to the S&P 500, NIFTY, or Hang Seng.

If you've ever heard "the market was up 1.2% today" in a Pakistani context, that almost always means the KSE-100.

## How it's weighted

The index is **free-float market-cap weighted** since 2008. That means:

- A company's weight in the index = (free-float shares × price) / (sum across all 100 companies)
- "Free float" excludes shares held by promoters, governments, and other long-term locked holders
- Bigger companies have more influence on the index than smaller ones

In practice this means OGDC, HBL, MCB, and a handful of large names dominate the index. A 5% move in OGDC matters far more to the KSE-100 than a 5% move in a small-cap name.

## What it tells you

The KSE-100 is a **broad-market thermometer**. It's useful for:

- Comparing your portfolio's return to "the market"
- Understanding macro events (rate decisions, IMF deals, political events)
- Picking up overall sentiment trends

It's **less useful** for:

- Sector analysis (most sectors are dominated by a few large names)
- Small-cap signal (small-caps don't drive the index)
- Risk gauges (the index is a price-weighted snapshot, not a volatility measure)

## KSE-100 vs other PSX indices

- **KSE-30**: the 30 largest names (more concentrated than KSE-100)
- **KSE All-Share**: every listed stock (broader than KSE-100)
- **KMI-30** and **KMI All-Share**: Shariah-compliant subsets, screened by Meezan Bank

If you're a Shariah-only investor, **KMI is your benchmark, not KSE-100** — comparing a Shariah-screened portfolio to the KSE-100 makes the comparison noisy because the KSE-100 includes conventional banks and insurance.

## Long-run returns

Over 20+ years, the KSE-100 has averaged around **14% nominal annual return** in PKR. After inflation (which has been brutal — 12-25% annually in recent years), real returns are much thinner. After CGT and brokerage, thinner still.

This is why the **after-tax framing** matters so much in retail investing: a 14% nominal return at 12% inflation is essentially zero real return; at 12% inflation with 15% CGT applied to gains, you're actually losing purchasing power.

## What to do with this

When you check the index and feel either elated or panicked, take a moment to ask:

- Is my portfolio actually similar to the KSE-100? (Usually no.)
- Is today's index move driven by something specific to the names I hold? (Usually no.)
- Does this matter for my 5-10 year plan? (Almost always no.)

Daily index watching is a quick path to overtrading. The index is a tool. Use it sparingly.
`,
  },
];
