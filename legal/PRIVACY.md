# Privacy Policy — DRAFT

**Status:** Draft for lawyer review. Anything in `[BRACKETS]` must be filled
in or revised by Pakistani counsel before going live. Pakistan's data-
protection legislation is in flux; counsel should advise on the **Personal
Data Protection Act** (still pending final passage at draft time) and
applicable SECP guidance.

**Last reviewed by counsel:** _not yet_

---

## TL;DR

We collect the minimum data needed to run the Service, store it
securely in Pakistan **[OR_HOSTING_JURISDICTION]**, never sell it, and
let you export or delete it on request.

## 1. Who we are

**[LEGAL_ENTITY_NAME]** ("PSX AI", "we", "our") operates the website
and Service at **[CANONICAL_DOMAIN]**. Our registered office is at
**[REGISTERED_OFFICE_ADDRESS]**. You can reach our privacy contact at
**[PRIVACY_EMAIL]**.

## 2. Data we collect

### 2.1 Account data

- Email address (required for sign-up + email verification)
- Password — stored only as an Argon2id hash, never in plain text
- Optional: full name, phone number, last 4 digits of CNIC, date of birth
- Filer status (self-declared)
- Shariah Mode preference

### 2.2 Portfolio data

- Trades you record: symbol, date, quantity, price, brokerage, FED, CVT, CGT, notes
- Portfolios, watchlists, goals, risk-profile answers
- Custom backtest strategies you save

### 2.3 Usage data

- IP address (for security + rate limiting)
- User agent (browser/device)
- Session timestamps
- Pages visited within the Service
- Feature usage (for product improvement)

### 2.4 Cookies and similar technologies

- A single **HTTP-only session cookie** (`psx_session`) for authentication
- Optional analytics cookie from **[ANALYTICS_PROVIDER]** if you consent
- No third-party advertising cookies

We do not collect:

- Bank account or card numbers (payment processing is delegated to
  **[PAYMENT_PROVIDER]**; we receive only a tokenised reference)
- Your actual broker login credentials
- Anything from third parties without your consent

## 3. How we use your data

- **To provide the Service**: compute portfolio metrics, run tax math,
  serve predictions
- **To secure your account**: detect anomalous logins, enforce rate
  limits, prevent fraud
- **To improve the product**: aggregate, anonymised usage analysis
- **To communicate**: transactional emails (verification, password
  reset, billing receipts), and product updates if you opt in

We **do not**:

- Sell your data to third parties
- Use your portfolio data to trade against you
- Share individual user data with advertisers
- Send marketing emails without explicit opt-in

## 4. Anonymized benchmarking (opt-in)

If you enable "Share anonymously" in Settings, we include your
portfolio's aggregate metrics (sector mix, archetype bucket) in
community comparisons shown on /app/portfolio. Specific trades, names,
and identifying details are never shared. Aggregates with fewer than
**5 contributing peers** are suppressed (k-anonymity floor).

You can disable this any time in Settings; aggregates are recomputed
nightly so changes take effect within a day.

## 5. Where we store data

Primary database: **[HOSTING_PROVIDER]** servers in **[REGION]**.
Backups: encrypted and retained for **[BACKUP_RETENTION_DAYS]** days.

All connections use TLS. All passwords are Argon2id hashed.

## 6. Who can access your data

- Engineers on our team, with **least-privilege role-based access** and
  logged queries
- Subprocessors necessary to operate the Service: **[SUBPROCESSOR_LIST]**
- Legal authorities **only on receipt of a valid Pakistani court order
  or equivalent lawful request**

## 7. Your rights

You can:

- **Access** your data via the export feature in Settings
- **Correct** account data in Settings
- **Delete** your account, which removes all personal data within 30
  days. Some operational data (aggregated metrics, fraud-prevention
  records) may be retained in anonymised form
- **Object** to specific processing by contacting **[PRIVACY_EMAIL]**
- **Withdraw consent** for analytics or marketing at any time

## 8. Data retention

| Data | Retention |
|---|---|
| Account + portfolio | While account is active, plus 30 days after deletion |
| Logs (IP, user agent, sessions) | 90 days |
| Backups | **[BACKUP_RETENTION_DAYS]** days |
| Billing records | As required by Pakistani tax law (typically 6 years) |
| Anonymised aggregates | Indefinitely (no longer tied to you) |

## 9. Children

The Service is not directed at children under 18. We do not knowingly
collect data from minors.

## 10. Third-party links

The Service may link to external sources (broker portals, news
articles, FBR). Their privacy practices are their own.

## 11. Changes to this policy

We'll email registered users about material changes at least
**[NOTICE_PERIOD_DAYS]** days before they take effect.

## 12. Security incidents

We will notify affected users without undue delay (and in any case
within **[INCIDENT_NOTICE_HOURS]** hours of confirmed scope) if a
security incident affects their personal data.

## 13. Contact

For privacy questions or data-subject requests:
**[PRIVACY_EMAIL]**

For everything else: **[SUPPORT_EMAIL]**

---

_This document is a draft for Pakistani lawyer review. Counsel should
specifically advise on the pending Personal Data Protection Act,
cross-border data transfer if applicable, and SECP guidance on
investor data handling._
