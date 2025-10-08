"""Plot helpers for the ID benchmark notebook."""

from typing import Optional

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

sns.set_theme(style="whitegrid")


def bar_latency(df: pd.DataFrame, metric: str = "avg_ms", title: Optional[str] = None):
    """Plot a bar chart grouping by id_type and hue by database for a latency metric.

    Args:
        df: DataFrame containing columns ['id_type', 'database', metric]
        metric: column to plot (avg_ms, p95_ms, etc.)
        title: optional title
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=df, x="id_type", y=metric, hue="database", ax=ax)
    if title:
        ax.set_title(title)
    ax.set_ylabel(metric.replace("_", " "))
    ax.set_xlabel("ID type")
    ax.legend(title="Database")
    plt.tight_layout()
    return fig, ax
