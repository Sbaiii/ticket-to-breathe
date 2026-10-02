"""Tiny Markdown helpers for fact reports."""

import pandas as pd


def md_table(df: pd.DataFrame) -> str:
    """Render a DataFrame as a GitHub Markdown table (no index)."""

    def fmt(v) -> str:
        if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NA:
            return ""
        if isinstance(v, float):
            return f"{v:.3f}"
        return str(v)

    lines = ["| " + " | ".join(str(c) for c in df.columns) + " |", "|" + "---|" * len(df.columns)]
    lines += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)
