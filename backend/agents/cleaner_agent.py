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
        Purely deterministic — no LLM needed here.
        """
        rules = []
        cols = df.columns.tolist()
        col_lower = {c.lower(): c for c in cols}

        # Rule 1: drop rows where a likely entity-ID column is null
        for candidate in ["customerid", "customer_id", "userid", "user_id", "patientid", "employeeid", "id"]:
            if candidate in col_lower:
                real_col = col_lower[candidate]
                null_count = int(df[real_col].isna().sum())
                null_pct = round(null_count / len(df) * 100, 1)
                if null_count > 0:
                    rules.append({
                        "id": f"drop_null_{real_col}",
                        "label": f"Remove rows with missing {real_col}",
                        "reason": f"Without {real_col}, customer-level analysis is impossible. "
                                  f"{null_pct}% of rows affected.",
                        "impact": null_count,
                        "action": "dropna",
                        "column": real_col,
                    })
                break

        # Rule 2: remove likely cancellation/reversal records
        for candidate in ["invoiceno", "invoice_no", "order_id", "orderid", "transaction_id"]:
            if candidate in col_lower:
                real_col = col_lower[candidate]
                cancel_mask = df[real_col].astype(str).str.startswith("C")
                cancel_count = int(cancel_mask.sum())
                if cancel_count > 0:
                    rules.append({
                        "id": f"remove_cancellations_{real_col}",
                        "label": f"Remove cancelled records ({real_col} starts with 'C')",
                        "reason": f"Cancellations inflate gross revenue and distort trend analysis. "
                                  f"{cancel_count:,} records affected.",
                        "impact": cancel_count,
                        "action": "filter_not_startswith",
                        "column": real_col,
                        "value": "C",
                    })
                break

        # Rule 3: remove negative/zero quantity
        for candidate in ["quantity", "qty", "units", "count"]:
            if candidate in col_lower:
                real_col = col_lower[candidate]
                if pd.api.types.is_numeric_dtype(df[real_col]):
                    bad_count = int((df[real_col] <= 0).sum())
                    if bad_count > 0:
                        rules.append({
                            "id": f"remove_nonpositive_{real_col}",
                            "label": f"Remove rows with {real_col} ≤ 0",
                            "reason": f"Zero or negative quantities are data entry errors or returns. "
                                      f"{bad_count:,} rows affected.",
                            "impact": bad_count,
                            "action": "filter_positive",
                            "column": real_col,
                        })
                break

        # Rule 4: remove negative/zero price
        for candidate in ["unitprice", "unit_price", "price", "amount", "cost"]:
            if candidate in col_lower:
                real_col = col_lower[candidate]
                if pd.api.types.is_numeric_dtype(df[real_col]):
                    bad_count = int((df[real_col] <= 0).sum())
                    if bad_count > 0:
                        rules.append({
                            "id": f"remove_nonpositive_{real_col}",
                            "label": f"Remove rows with {real_col} ≤ 0",
                            "reason": f"Zero or negative prices indicate errors or free items that "
                                      f"would skew revenue analysis. {bad_count:,} rows affected.",
                            "impact": bad_count,
                            "action": "filter_positive",
                            "column": real_col,
                        })
                break

        # Rule 5: parse date column if stored as string
        for candidate in ["invoicedate", "invoice_date", "orderdate", "order_date", "date", "timestamp"]:
            if candidate in col_lower:
                real_col = col_lower[candidate]
                if not pd.api.types.is_datetime64_any_dtype(df[real_col]):
                    coerced = pd.to_datetime(df[real_col], errors="coerce")
                    parseable = int(coerced.notna().sum())
                    if parseable > len(df) * 0.7:
                        rules.append({
                            "id": f"parse_datetime_{real_col}",
                            "label": f"Parse {real_col} as datetime",
                            "reason": f"Time-series and cohort analyses require a proper datetime type. "
                                      f"{parseable:,} values can be parsed.",
                            "impact": 0,
                            "action": "parse_datetime",
                            "column": real_col,
                        })
                break

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
            mask = ~df[col].astype(str).str.startswith(val)
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
        col_lower = {c.lower(): c for c in df.columns}

        # TotalPrice = Quantity × UnitPrice (if not already present)
        qty_col = col_lower.get("quantity") or col_lower.get("qty")
        price_col = col_lower.get("unitprice") or col_lower.get("unit_price") or col_lower.get("price")

        if qty_col and price_col and "totalprice" not in col_lower and "total_price" not in col_lower:
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
