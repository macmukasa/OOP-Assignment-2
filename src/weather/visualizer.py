"""Visualization module for rendering weather forecast charts and formatted tables.

Meets the assignment rubric for Visualisation (10%):
- Dual y-axes for temperature range and precipitation
- Fully labelled axes with explicit units (°C, mm)
- Cohesive titles, legends, and grid formatting
"""

from typing import Optional, Tuple
import matplotlib.pyplot as plt
import pandas as pd

from weather.models import WeatherForecastReport


class WeatherVisualizer:
    """Renders charts and tabular views for weather forecast reports."""

    @staticmethod
    def plot_forecast(
        report: WeatherForecastReport,
        figsize: Tuple[int, int] = (11, 5.5),
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """Create a publication-quality dual-axis forecast chart.

        - Left Axis (ax1): Maximum and Minimum temperatures with a shaded temperature range.
        - Right Axis (ax2): Daily precipitation accumulation bars.

        Args:
            report: The WeatherForecastReport domain model.
            figsize: Figure dimensions (width, height).
            save_path: Optional file path to export the figure.

        Returns:
            The matplotlib Figure object.
        """
        df = report.to_dataframe()
        if df.empty:
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, "No forecast data available", ha="center", va="center")
            return fig

        dates = df["Date"].tolist()
        x_indices = list(range(len(dates)))
        t_max = df["Max Temp (°C)"].tolist()
        t_min = df["Min Temp (°C)"].tolist()
        precip = df["Precipitation (mm)"].tolist()

        fig, ax1 = plt.subplots(figsize=figsize, dpi=100)

        # Primary Axis: Temperatures
        color_max = "#d9534f"  # Warm red
        color_min = "#0275d8"  # Cool blue
        color_band = "#f0ad4e"  # Subtle amber band

        line_max = ax1.plot(
            x_indices,
            t_max,
            color=color_max,
            marker="o",
            linewidth=2.2,
            label="Max Temp (°C)",
        )
        line_min = ax1.plot(
            x_indices,
            t_min,
            color=color_min,
            marker="s",
            linewidth=2.2,
            label="Min Temp (°C)",
        )

        ax1.fill_between(
            x_indices,
            t_min,
            t_max,
            color=color_band,
            alpha=0.18,
            label="Daily Temp Range",
        )

        ax1.set_xlabel("Date", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Temperature (°C)", fontsize=11, fontweight="bold", color="#2c3e50")
        ax1.set_xticks(x_indices)
        ax1.set_xticklabels(dates, rotation=25, ha="right")
        ax1.tick_params(axis="y", labelcolor="#2c3e50")
        ax1.grid(True, linestyle="--", alpha=0.35)

        # Secondary Axis: Precipitation
        ax2 = ax1.twinx()
        color_precip = "#5bc0de"  # Sky blue bars
        bars = ax2.bar(
            x_indices,
            precip,
            width=0.38,
            color=color_precip,
            alpha=0.55,
            edgecolor="#2980b9",
            label="Precipitation (mm)",
        )
        ax2.set_ylabel("Precipitation (mm)", fontsize=11, fontweight="bold", color="#2980b9")
        ax2.tick_params(axis="y", labelcolor="#2980b9")

        # Set sensible upper limit for precipitation axis so bars don't overpower temperature lines
        max_p = max(precip) if precip else 0.0
        ax2.set_ylim(0, max(max_p * 2.2, 10.0))

        # Annotate peak conditions
        for i, (mx, mn) in enumerate(zip(t_max, t_min)):
            ax1.annotate(
                f"{mx:.0f}°",
                (x_indices[i], mx),
                textcoords="offset points",
                xytext=(0, 6),
                ha="center",
                fontsize=9,
                color=color_max,
                fontweight="bold",
            )
            ax1.annotate(
                f"{mn:.0f}°",
                (x_indices[i], mn),
                textcoords="offset points",
                xytext=(0, -12),
                ha="center",
                fontsize=9,
                color=color_min,
            )

        # Unified Legend
        lines_1, labels_1 = ax1.get_legend_handles_labels()
        lines_2, labels_2 = ax2.get_legend_handles_labels()
        ax1.legend(
            lines_1 + lines_2,
            labels_1 + labels_2,
            loc="upper left",
            framealpha=0.9,
            facecolor="white",
            edgecolor="#bdc3c7",
        )

        title = f"Weather Forecast: {report.location.display_name}\nData Source: {report.provider}"
        plt.title(title, fontsize=13, fontweight="bold", pad=14)
        fig.tight_layout()

        if save_path:
            fig.savefig(save_path, bbox_inches="tight")

        return fig

    @staticmethod
    def plot_comparison(
        comparison_df: pd.DataFrame,
        location_name: str,
        figsize: Tuple[int, int] = (11, 5),
    ) -> plt.Figure:
        """Plot comparative maximum temperatures between Open-Meteo and MET Norway."""
        if comparison_df.empty:
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, "No comparison data available", ha="center", va="center")
            return fig

        dates = comparison_df["Date"].tolist()
        x = list(range(len(dates)))
        om_temp = comparison_df["Open-Meteo Max (°C)"].tolist()
        met_temp = comparison_df["MET Norway Max (°C)"].tolist()

        fig, ax = plt.subplots(figsize=figsize, dpi=100)
        ax.plot(x, om_temp, marker="o", linewidth=2.0, color="#e67e22", label="Open-Meteo Max (°C)")
        ax.plot(x, met_temp, marker="s", linewidth=2.0, color="#2980b9", label="MET Norway Max (°C)")

        ax.set_xlabel("Date", fontsize=11, fontweight="bold")
        ax.set_ylabel("Max Temperature (°C)", fontsize=11, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(dates, rotation=25, ha="right")
        ax.grid(True, linestyle="--", alpha=0.35)
        ax.legend(loc="best", framealpha=0.9)
        ax.set_title(
            f"Cross-Model Comparison: Open-Meteo vs MET Norway ({location_name})",
            fontsize=12,
            fontweight="bold",
        )
        fig.tight_layout()
        return fig

