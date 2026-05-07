# Step 3: Domain, Brand & Email Setup Checklist

---

## Domain Registration

- [ ] **Register `.com`** — primary domain, use Namecheap or Cloudflare Registrar (cheapest renewal rates)
- [ ] **Register `.pk`** — PKNIC registration at https://pk.godaddy.com or through a local registrar. Requires CNIC for `.pk`. Annual fee ~PKR 2,500–4,000.
  - Note: `.com.pk` is an alternative if `.pk` is taken
- [ ] **Point both domains to Cloudflare DNS** immediately after purchase (before hosting exists)
  - Set the `.com` as primary; redirect `.pk` → `.com` via Cloudflare Page Rule

## Cloudflare Setup

- [ ] Create a Cloudflare account at https://cloudflare.com (free tier is sufficient for Phase 0–2)
- [ ] Add both domains to Cloudflare
- [ ] Enable "Always Use HTTPS" setting
- [ ] Enable "Auto Minify" (JS/CSS/HTML)
- [ ] Set SSL/TLS mode to "Full (strict)"
- [ ] Note your Cloudflare Zone IDs — you'll need them in `psx-infra/` later

## Professional Email

**Recommended: Zoho Mail** (free for up to 5 users on one domain — good for a solo founder)
Alternative: Google Workspace (~$6/user/month — better integration if you use Google tools)

- [ ] Set up professional email: `contact@[YOUR_DOMAIN]` (public-facing)
- [ ] Set up operational emails:
  - `noreply@[YOUR_DOMAIN]` (transactional emails from the app)
  - `support@[YOUR_DOMAIN]` (user support)
  - `data@[YOUR_DOMAIN]` (for PSX/Capital Stake correspondence — looks more credible than personal email)
- [ ] Configure SPF, DKIM, DMARC records in Cloudflare DNS — critical for email deliverability
  - Zoho Mail provides exact DNS record values during setup
- [ ] Test email deliverability at https://www.mail-tester.com — aim for score 9+/10

## Brand Assets (minimum viable for launch)

- [ ] Logo — minimum: wordmark in SVG format. Export also as: 512×512 PNG (app icon), 1200×630 PNG (OG image), 192×192 PNG (PWA icon).
- [ ] Color palette — pick 2 primary colors + 1 accent. Recommend dark navy + green (trust + growth) — common in fintech.
- [ ] Favicon — 32×32 ICO + 180×180 PNG for Apple Touch Icon

## After This Step Is Done

- Go back to `psx-docs/email-templates/01-psx-marketdata-initial-outreach.md`
- Fill in `[YOUR_NAME]`, `[YOUR_DOMAIN]`, `[BUSINESS_NAME]`, `[YOUR_PHONE]`
- Send from `data@[YOUR_DOMAIN]` — not a personal Gmail

---

**Estimated time:** 2–4 hours to register domains, set up Cloudflare, configure email
**Estimated cost:** ~$20–35/year for domains + email (or free with Zoho)
