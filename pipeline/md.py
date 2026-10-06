"""Tiny Markdown helpers for fact reports."""

import pandas as pd


def md_table(df: pd.DataFrame) -> str:
    """Render a DataFrame as a GitHub Markdown table (no index)."""

    def fmt(v) -> str:
        if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NA:
            return ""
        if isinstance(v, float):
            whole = abs(v - round(v)) < 1e-9 and abs(v) >= 1
            return str(round(v)) if whole else f"{v:.3f}"
        return str(v)

    lines = ["| " + " | ".join(str(c) for c in df.columns) + " |", "|" + "---|" * len(df.columns)]
    lines += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def interpretation(text: str, written_for: str, current: str) -> str:
    """The hand-written interpretation, but only for the run it was written for. For any other run
    a 'pending' note is returned, so prose numbers never outlive the facts they describe."""
    if written_for == current:
        return text.strip()
    return (f"_Interpretation pending. The text in the script was written for the run "
            f"\"{written_for}\"; this run is \"{current}\". Rewrite it after reading the facts "
            "above._")
