"""
Cleaner Agent
Goal: Maximise data quality for downstream analysis without losing meaningful information.

Real agent properties:
  - Memory: tracks what was removed and why, user's cleaning decisions
  - Tools: profile_column, detect_issues, estimate_impact, apply_rule, verify
  - Goal loop: profile → detect → propose → (wait/auto) → apply → verify
  - Communication: posts log messages, user questions to bus
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.agents.base import BaseAgent
from backend.agents.message_bus import MessageBus
from backend.agents.models import (
    AgentName,
    DecisionPoint,
    Option,
    RunMode,
)


class CleanerAgent(BaseAgent):
    name = AgentName.CLEANER.value
    icon = "🧹"

    def __init__(self, bus: MessageBus, mode: RunMode):
        super().__init__(bus, mode)

    # ── Main entry point ──────────────────────────────────────────────────────

    async def run(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Full cleaning loop.
        Returns: (cleaned_df, cleaning_report)
        """
        self.log("Starting data quality analysis...")
        rows_before = len(df)

        # ── Tool: detect all applicable cleaning rules ────────────────────────
        rules = self._detect_rules(df)
        self.log(f"Detected {len(rules)} potential cleaning actions")
        self.memory.remember("detected_rules", {"count": len(rules), "rules": [r["id"] for r in rules]})

        # ── For each rule: propose to user or auto-apply ──────────────────────
        applied = []
        for rule in rules:
            chosen = await self._propose_rule(df, rule)

            if chosen == "apply":
                df = self._apply_rule(df, rule)
                applied.append(rule)
                self.log(
                    f"✓ Applied: {rule['label']}",
                    {"rows_removed": rule.get("impact", 0)},
                )
                self.memory.remember(f"applied:{rule['id']}", rule)

            elif chosen == "skip":
                self.log(f"⟳ Skipped: {rule['label']}")
                self.memory.remember(f"skipped:{rule['id']}", rule)

        # ── Tool: derive computed columns (always, no user prompt needed) ─────
        df, derived = self._derive_columns(df)
        for col in derived:
            self.log(f"+ Derived column: {col}")

        # ── Tool: verify cleaning ─────────────────────────────────────────────
        rows_after = len(df)
        report = self._build_report(rows_before, rows_after, applied, derived, df)
        self.log(
            f"Cleaning complete — {rows_before:,} → {rows_after:,} rows "
            f"({rows_before - rows_after:,} removed)"
        )
        self.memory.remember("cleaning_complete", report)
        self.mark_done()
        return df, report

    # ── Tool: detect applicable cleaning rules ────────────────────────────────

    def _detect_rules(self, df: pd.DataFrame) -> list[dict]:
        """
        Inspect the dataframe and build a list of applicable cleaning rules.
        Column matching normalises away spaces and underscores so that
        'Customer ID', 'customer_id', and 'customerid' all match.
        """
        rules = []

        # Build a normalised lookup: strip spaces + underscores + lowercase
        # e.g. "Customer ID" → "customerid", "Invoice Date" → "invoicedate"
        col_norm = {
            c.lower().replace(" ", "").replace("_", ""): c
            for c in df.columns
        }

        def find_col(candidates: list[str]) -> str | None:
            """Return the actual DataFrame column name matching any candidate."""
            for cand in candidates:
                norm = cand.lower().replace(" ", "").replace("_", "")
                if norm in col_norm:
                    return col_norm[norm]
            return None

        # ── Rule 1: drop rows where entity-ID column is null ──────────────────
        entity_col = find_col([
            "customerid", "customer id", "customer_id",
            "userid", "user id", "user_id",
            "patientid", "patient id", "patient_id",
            "employeeid", "employee id", "employee_id",
        ])
        if entity_col:
            null_count = int(df[entity_col].isna().sum())
            null_pct = round(null_count / len(df) * 100, 1)
            if null_count > 0:
                rules.append({
                    "id": f"drop_null_{entity_col}",
                    "label": f"Remove rows with missing {entity_col}",
                    "reason": (
                        f"Without {entity_col}, customer-level analysis is impossible. "
                        f"{null_pct}% of rows ({null_count:,}) are affected."
                    ),
                    "impact": null_count,
                    "action": "dropna",
                    "column": entity_col,
                })

        # ── Rule 2: remove cancellation/reversal records ──────────────────────
        invoice_col = find_col([
            "invoiceno", "invoice no", "invoice_no",
            "invoice", "orderid", "order id", "order_id",
            "transactionid", "transaction id", "transaction_id",
        ])
        if invoice_col:
            cancel_mask = df[invoice_col].astype(str).str.strip().str.startswith("C")
            cancel_count = int(cancel_mask.sum())
            if cancel_count > 0:
                rules.append({
                    "id": f"remove_cancellations_{invoice_col}",
                    "label": f"Remove cancelled records ({invoice_col} starts with 'C')",
                    "reason": (
                        f"Cancellations inflate gross revenue and distort trend analysis. "
                        f"{cancel_count:,} records affected."
                    ),
                    "impact": cancel_count,
                    "action": "filter_not_startswith",
                    "column": invoice_col,
                    "value": "C",
                })

        # ── Rule 3: remove negative/zero quantity ─────────────────────────────
        qty_col = find_col(["quantity", "qty", "units", "count"])
        if qty_col and pd.api.types.is_numeric_dtype(df[qty_col]):
            bad_count = int((df[qty_col] <= 0).sum())
            if bad_count > 0:
                rules.append({
                    "id": f"remove_nonpositive_{qty_col}",
                    "label": f"Remove rows with {qty_col} ≤ 0",
                    "reason": (
                        f"Zero or negative quantities are data entry errors or returns. "
                        f"{bad_count:,} rows affected."
                    ),
                    "impact": bad_count,
                    "action": "filter_positive",
                    "column": qty_col,
                })

        # ── Rule 4: remove negative/zero price ────────────────────────────────
        price_col = find_col([
            "unitprice", "unit price", "unit_price",
            "price", "amount", "cost",
        ])
        if price_col and pd.api.types.is_numeric_dtype(df[price_col]):
            bad_count = int((df[price_col] <= 0).sum())
            if bad_count > 0:
                rules.append({
                    "id": f"remove_nonpositive_{price_col}",
                    "label": f"Remove rows with {price_col} ≤ 0",
                    "reason": (
                        f"Zero or negative prices indicate errors or free items that "
                        f"would skew revenue analysis. {bad_count:,} rows affected."
                    ),
                    "impact": bad_count,
                    "action": "filter_positive",
                    "column": price_col,
                })

        # ── Rule 5: parse date column stored as string ────────────────────────
        date_col = find_col([
            "invoicedate", "invoice date", "invoice_date",
            "orderdate", "order date", "order_date",
            "date", "timestamp", "createdat", "created at",
        ])
        if date_col and not pd.api.types.is_datetime64_any_dtype(df[date_col]):
            coerced = pd.to_datetime(df[date_col], errors="coerce")
            parseable = int(coerced.notna().sum())
            if parseable > len(df) * 0.7:
                rules.append({
                    "id": f"parse_datetime_{date_col}",
                    "label": f"Parse {date_col} as datetime",
                    "reason": (
                        f"Time-series and cohort analyses require a proper datetime type. "
                        f"{parseable:,} values can be parsed."
                    ),
                    "impact": 0,
                    "action": "parse_datetime",
                    "column": date_col,
                })

        return rules

    # ── Tool: propose one rule to user ────────────────────────────────────────

    async def _propose_rule(self, df: pd.DataFrame, rule: dict) -> str:
        dp = DecisionPoint(
            agent=AgentName.CLEANER,
            icon=self.icon,
            context=f"Data quality issue detected in column '{rule.get('column', '')}'.",
            question=rule["label"],
            suggested_answer="apply",
            reason=rule["reason"],
            options=[
                Option("apply", "Apply", "Remove or fix the affected rows"),
                Option("skip", "Skip", "Keep the data as-is"),
            ],
            impact=f"Affects {rule['impact']:,} rows" if rule.get("impact") else "No rows removed",
        )
        return await self.ask_user(dp)

    # ── Tool: apply one rule ──────────────────────────────────────────────────

    def _apply_rule(self, df: pd.DataFrame, rule: dict) -> pd.DataFrame:
        action = rule["action"]
        col = rule.get("column")

        if action == "dropna":
            return df.dropna(subset=[col])

        elif action == "filter_not_startswith":
            val = rule.get("value", "C")
            mask = ~df[col].astype(str).str.strip().str.startswith(val)
            return df[mask]

        elif action == "filter_positive":
            return df[df[col] > 0]

        elif action == "parse_datetime":
            df = df.copy()
            df[col] = pd.to_datetime(df[col], errors="coerce")
            return df

        return df

    # ── Tool: derive computed columns ─────────────────────────────────────────

    def _derive_columns(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """Create standard derived columns when source columns exist."""
        df = df.copy()
        derived = []

        col_norm = {
            c.lower().replace(" ", "").replace("_", ""): c
            for c in df.columns
        }

        def find_col(candidates: list[str]) -> str | None:
            for cand in candidates:
                norm = cand.lower().replace(" ", "").replace("_", "")
                if norm in col_norm:
                    return col_norm[norm]
            return None

        qty_col   = find_col(["quantity", "qty", "units"])
        price_col = find_col(["unitprice", "unit price", "unit_price", "price"])

        has_total = find_col(["totalprice", "total price", "total_price",
                               "totalamount", "total amount", "revenue"])

        if qty_col and price_col and not has_total:
            df["TotalPrice"] = df[qty_col] * df[price_col]
            derived.append("TotalPrice")

        return df, derived

    # ── Tool: build cleaning report ───────────────────────────────────────────

    def _build_report(
        self,
        rows_before: int,
        rows_after: int,
        applied: list[dict],
        derived: list[str],
        df: pd.DataFrame,
    ) -> dict:
        return {
            "rows_before": rows_before,
            "rows_after": rows_after,
            "rows_removed": rows_before - rows_after,
            "rules_applied": [r["id"] for r in applied],
            "derived_columns": derived,
            "column_null_summary": {
                col: int(df[col].isna().sum())
                for col in df.columns
                if df[col].isna().sum() > 0
            },
        }
