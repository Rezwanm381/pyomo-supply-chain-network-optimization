"""Concise, schematic decision visualizations."""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"
_DEFAULT_CONFIG.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_DEFAULT_CONFIG))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .data_loader import NetworkData  # noqa: E402


NAVY = "#123B5D"
BLUE = "#2F75B5"
TEAL = "#2A9D8F"
ORANGE = "#E58E26"
GRAY = "#A7B0B8"
LIGHT = "#E8EEF2"
RED = "#C94C4C"


def _prepare_path(path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def plot_network(
    data: NetworkData,
    facility_decisions: pd.DataFrame,
    active_shipments: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    """Plot open/closed facilities, customers, and positive shipment arcs."""

    output = _prepare_path(output_path)
    facilities = data.facilities.set_index("facility_id")
    customers = data.customers.set_index("customer_id")
    max_flow = (
        max(float(active_shipments["shipment_units_per_year"].max()), 1.0)
        if not active_shipments.empty
        else 1.0
    )
    figure, axis = plt.subplots(figsize=(11, 7), constrained_layout=True)

    for shipment in active_shipments.itertuples(index=False):
        origin = facilities.loc[shipment.origin]
        destination = customers.loc[shipment.destination]
        width = 0.7 + 4.0 * float(shipment.shipment_units_per_year) / max_flow
        axis.plot(
            [origin.x_coord_sdu, destination.x_coord_sdu],
            [origin.y_coord_sdu, destination.y_coord_sdu],
            color=BLUE,
            alpha=0.33,
            linewidth=width,
            zorder=1,
        )

    closed_ids = facility_decisions.loc[facility_decisions["open"] == 0, "facility_id"]
    open_ids = facility_decisions.loc[facility_decisions["open"] == 1, "facility_id"]
    closed = facilities.loc[closed_ids]
    opened = facilities.loc[open_ids]
    axis.scatter(
        closed["x_coord_sdu"],
        closed["y_coord_sdu"],
        marker="s",
        s=145,
        facecolors="white",
        edgecolors=GRAY,
        linewidths=1.8,
        label="Candidate facility (closed)",
        zorder=3,
    )
    axis.scatter(
        opened["x_coord_sdu"],
        opened["y_coord_sdu"],
        marker="s",
        s=185,
        color=TEAL,
        edgecolors=NAVY,
        linewidths=1.2,
        label="Facility selected (open)",
        zorder=4,
    )
    axis.scatter(
        customers["x_coord_sdu"],
        customers["y_coord_sdu"],
        marker="o",
        s=customers["demand_units_per_year"] * 1.25,
        color=ORANGE,
        edgecolors="white",
        linewidths=0.8,
        label="Customer zone (size = demand)",
        zorder=3,
    )

    for facility_id, row in facilities.iterrows():
        axis.annotate(facility_id, (row.x_coord_sdu, row.y_coord_sdu), xytext=(6, 7), textcoords="offset points", fontsize=8)
    for customer_id, row in customers.iterrows():
        axis.annotate(customer_id.replace("ZONE_", "Z"), (row.x_coord_sdu, row.y_coord_sdu), xytext=(5, -12), textcoords="offset points", fontsize=7)

    axis.set_title("Optimized distribution network", fontsize=16, weight="bold", color=NAVY)
    axis.set_xlabel("Synthetic x-coordinate (SDU)")
    axis.set_ylabel("Synthetic y-coordinate (SDU)")
    axis.text(
        0.01,
        0.01,
        "Schematic synthetic coordinates; not a geographic map. Arc width represents annual shipment flow.",
        transform=axis.transAxes,
        fontsize=8,
        color="#4B5563",
    )
    axis.grid(color=LIGHT, linewidth=0.7)
    axis.legend(loc="upper center", ncol=3, frameon=False, fontsize=8)
    figure.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return output


def plot_cost_breakdown(
    optimized_fixed: float,
    optimized_transport: float,
    baseline_fixed: float,
    baseline_transport: float,
    output_path: str | Path,
) -> Path:
    output = _prepare_path(output_path)
    figure, axis = plt.subplots(figsize=(8, 5.3), constrained_layout=True)
    labels = ["Optimized", "All facilities open\nbaseline"]
    fixed = [optimized_fixed, baseline_fixed]
    transport = [optimized_transport, baseline_transport]
    axis.bar(labels, fixed, color=NAVY, label="Fixed facility cost")
    axis.bar(labels, transport, bottom=fixed, color=ORANGE, label="Transport cost")
    for index, total in enumerate([sum(values) for values in zip(fixed, transport)]):
        axis.text(index, total * 1.015, f"${total:,.0f}", ha="center", va="bottom", weight="bold", color=NAVY)
    axis.set_title("Annual scenario-cost comparison", fontsize=15, weight="bold", color=NAVY)
    axis.set_ylabel("Scenario USD per year")
    axis.grid(axis="y", color=LIGHT, linewidth=0.7)
    axis.set_axisbelow(True)
    axis.legend(frameon=False)
    figure.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return output


def plot_facility_utilization(facilities: pd.DataFrame, output_path: str | Path) -> Path:
    output = _prepare_path(output_path)
    frame = facilities.copy()
    colors = [TEAL if opened else GRAY for opened in frame["open"]]
    figure, axis = plt.subplots(figsize=(9, 5.2), constrained_layout=True)
    bars = axis.bar(frame["facility_id"], frame["utilization"] * 100, color=colors)
    for bar, opened, utilization in zip(bars, frame["open"], frame["utilization"]):
        label = f"{utilization:.1%}" if opened else "closed"
        axis.text(bar.get_x() + bar.get_width() / 2, max(bar.get_height(), 1.0) + 2.0, label, ha="center", fontsize=8)
    axis.axhline(100, color=RED, linestyle="--", linewidth=1.2, label="Capacity")
    axis.set_ylim(0, 112)
    axis.set_ylabel("Utilization of candidate capacity (%)")
    axis.set_title("Facility utilization in the optimized network", fontsize=15, weight="bold", color=NAVY)
    axis.grid(axis="y", color=LIGHT, linewidth=0.7)
    axis.set_axisbelow(True)
    axis.legend(frameon=False, loc="upper right")
    figure.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return output


def plot_sensitivity(summary: pd.DataFrame, output_path: str | Path) -> Path:
    output = _prepare_path(output_path)
    frame = summary.copy()
    colors = [ORANGE if scenario == "DEMAND_BASE" else BLUE for scenario in frame["scenario_id"]]
    figure, axis = plt.subplots(figsize=(11, 5.8), constrained_layout=True)
    bars = axis.bar(frame["scenario_id"], frame["objective_usd_per_year"], color=colors)
    for bar, opened in zip(bars, frame["facilities_opened"]):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() * 1.01,
            f"{int(opened)} open",
            ha="center",
            va="bottom",
            fontsize=7,
        )
    axis.set_title("Sensitivity of scenario cost and facility count", fontsize=15, weight="bold", color=NAVY)
    axis.set_ylabel("Scenario USD per year")
    axis.tick_params(axis="x", rotation=28, labelsize=8)
    axis.grid(axis="y", color=LIGHT, linewidth=0.7)
    axis.set_axisbelow(True)
    figure.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return output
