"""Create tax_rules table with seeded SECP CGT brackets

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-07

Seeds initial CGT brackets per Pakistan Federal Budget history. Tax rates
change every budget cycle — admins update this table when the new Finance
Act takes effect; rows are date-bracketed so historical sells continue to
calculate correctly.

References:
  - Finance Act 2024 (effective 2024-07-01): flat 15% filer / 45% non-filer
    for securities acquired on or after 2024-07-01, regardless of holding
    period (Section 37A, Income Tax Ordinance 2001).
  - Pre-2024-07-01 holdings: progressive rates by holding period.
"""

from typing import Sequence, Union
from datetime import date

import sqlalchemy as sa
from alembic import op


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tax_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_type", sa.String(20), nullable=False, server_default="cgt"),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_filer", sa.Boolean(), nullable=False),
        sa.Column("min_holding_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_holding_days", sa.Integer(), nullable=True),
        sa.Column("rate_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("rate_pct >= 0 AND rate_pct <= 100", name="ck_tax_rules_rate_range"),
        sa.CheckConstraint("min_holding_days >= 0", name="ck_tax_rules_min_days"),
        sa.CheckConstraint(
            "max_holding_days IS NULL OR max_holding_days >= min_holding_days",
            name="ck_tax_rules_holding_range",
        ),
    )
    op.create_index("ix_tax_rules_lookup", "tax_rules", ["rule_type", "effective_from", "is_filer"])

    # ── Seed: pre-Finance-Act-2024 brackets (sells before 2024-07-01) ─────
    pre_2024_filer = [
        (0, 365, "15.0", "FY24 — held <1 yr (filer)"),
        (366, 730, "12.5", "FY24 — held 1–2 yr (filer)"),
        (731, 1095, "10.0", "FY24 — held 2–3 yr (filer)"),
        (1096, 1460, "7.5", "FY24 — held 3–4 yr (filer)"),
        (1461, None, "0.0", "FY24 — held 4+ yr (filer)"),
    ]
    pre_2024_nonfiler = [
        (0, 365, "30.0", "FY24 — held <1 yr (non-filer)"),
        (366, 730, "25.0", "FY24 — held 1–2 yr (non-filer)"),
        (731, 1095, "20.0", "FY24 — held 2–3 yr (non-filer)"),
        (1096, 1460, "15.0", "FY24 — held 3–4 yr (non-filer)"),
        (1461, None, "0.0", "FY24 — held 4+ yr (non-filer)"),
    ]
    rows: list[dict[str, object]] = []
    for is_filer, brackets in [(True, pre_2024_filer), (False, pre_2024_nonfiler)]:
        for min_d, max_d, rate, desc in brackets:
            rows.append(
                {
                    "rule_type": "cgt",
                    "effective_from": date(2022, 7, 1),
                    "effective_to": date(2024, 6, 30),
                    "is_filer": is_filer,
                    "min_holding_days": min_d,
                    "max_holding_days": max_d,
                    "rate_pct": rate,
                    "description": desc,
                }
            )

    # ── Seed: Finance Act 2024 (effective 2024-07-01, flat) ──────────────
    rows.append(
        {
            "rule_type": "cgt",
            "effective_from": date(2024, 7, 1),
            "effective_to": None,
            "is_filer": True,
            "min_holding_days": 0,
            "max_holding_days": None,
            "rate_pct": "15.0",
            "description": "Finance Act 2024 — flat 15% (filer)",
        }
    )
    rows.append(
        {
            "rule_type": "cgt",
            "effective_from": date(2024, 7, 1),
            "effective_to": None,
            "is_filer": False,
            "min_holding_days": 0,
            "max_holding_days": None,
            "rate_pct": "45.0",
            "description": "Finance Act 2024 — flat 45% (non-filer)",
        }
    )

    op.bulk_insert(
        sa.table(
            "tax_rules",
            sa.column("rule_type", sa.String),
            sa.column("effective_from", sa.Date),
            sa.column("effective_to", sa.Date),
            sa.column("is_filer", sa.Boolean),
            sa.column("min_holding_days", sa.Integer),
            sa.column("max_holding_days", sa.Integer),
            sa.column("rate_pct", sa.Numeric(6, 4)),
            sa.column("description", sa.Text),
        ),
        rows,
    )


def downgrade() -> None:
    op.drop_index("ix_tax_rules_lookup", table_name="tax_rules")
    op.drop_table("tax_rules")
