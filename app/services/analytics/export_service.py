"""
Export service for static chart rendering (PDF/PNG export) using Matplotlib.
Provides high-resolution server-side visual rendering for executive report exports.
"""
from __future__ import annotations

import io
import base64
import logging
from typing import Optional, Dict, Any

from app.schemas.orchestrator_briefing import PlotlyChartSpec

logger = logging.getLogger(__name__)


class ExportService:
    """Renders charts as static PNG/SVG images for exports and reports."""

    @classmethod
    def render_spec_to_base64_png(cls, chart: PlotlyChartSpec) -> Optional[str]:
        """
        Attempts to render a PlotlyChartSpec to a base64-encoded PNG using Matplotlib.
        Gracefully returns None if matplotlib or its dependencies are unavailable.
        """
        try:
            import matplotlib
            matplotlib.use("Agg")  # Non-interactive headless backend
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(8, 4), facecolor="#030712")
            ax.set_facecolor("#030712")
            ax.tick_params(colors="#94a3b8", labelsize=9)
            for spine in ax.spines.values():
                spine.set_color("#1f2937")

            data = chart.spec.get("data", [])
            title = chart.title

            if data and data[0].get("type") in ["funnel", "bar"]:
                trace = data[0]
                categories = trace.get("y", trace.get("x", []))
                values = trace.get("x", trace.get("y", []))

                if trace.get("type") == "funnel":
                    ax.barh(categories, values, color="#8b5cf6", edgecolor="#a78bfa")
                    ax.invert_yaxis()
                else:
                    ax.bar(categories, values, color="#3b82f6", edgecolor="#60a5fa")

            elif data and data[0].get("type") == "pie":
                trace = data[0]
                labels = trace.get("labels", [])
                values = trace.get("values", [])
                colors = ["#10b981", "#3b82f6", "#f59e0b"][:len(labels)]
                ax.pie(values, labels=labels, colors=colors, textprops={"color": "#e2e8f0"})

            ax.set_title(title, color="#ffffff", fontsize=12, fontweight="bold", pad=12)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            buf.seek(0)
            encoded = base64.b64encode(buf.read()).decode("utf-8")
            return f"data:image/png;base64,{encoded}"
        except Exception as e:
            logger.info(f"[ExportService] Matplotlib render notice: {e}; export will use native SVG.")
            return None
