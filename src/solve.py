"""Solver discovery, status enforcement, and solver metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any

import highspy
from pyomo.environ import ConcreteModel, SolverFactory, value
from pyomo.opt import SolverStatus, TerminationCondition


class SolverError(RuntimeError):
    """Base exception for solver failures."""


class SolverUnavailableError(SolverError):
    """Raised when the requested solver interface is missing."""


class InfeasibleModelError(SolverError):
    """Raised when the solver proves infeasibility."""


class UnboundedModelError(SolverError):
    """Raised when the solver reports an unbounded model."""


class NonOptimalModelError(SolverError):
    """Raised when no solver-certified optimum is available."""


@dataclass(frozen=True)
class SolveInfo:
    solver_name: str
    solver_version: str
    solver_status: str
    termination_condition: str
    objective_value: float
    best_bound: float | None
    relative_mip_gap: float | None
    solve_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_bound(results: Any, attribute: str) -> float | None:
    candidates: list[Any] = []
    try:
        candidates.append(getattr(results.problem, attribute))
    except Exception:
        pass
    try:
        candidates.append(getattr(results.problem[0], attribute))
    except Exception:
        pass
    for candidate in candidates:
        try:
            numeric = float(candidate)
            if numeric not in {float("inf"), float("-inf")}:
                return numeric
        except (TypeError, ValueError):
            continue
    return None


def _solver_version(solver_name: str, solver: Any) -> str:
    if "highs" in solver_name.lower():
        return highspy.Highs().version()
    try:
        version = solver.version()
        if isinstance(version, tuple):
            return ".".join(str(part) for part in version)
        return str(version)
    except Exception:
        return "UNKNOWN"


def solve_model(
    model: ConcreteModel,
    *,
    solver_name: str = "appsi_highs",
    tee: bool = False,
) -> SolveInfo:
    """Solve and refuse to return decision values without an optimal status."""

    solver = SolverFactory(solver_name)
    if solver is None or not solver.available(exception_flag=False):
        raise SolverUnavailableError(
            f"Solver '{solver_name}' is unavailable. Install the open-source 'highspy' package."
        )

    start = perf_counter()
    # Inspect termination before loading values. Some interfaces raise a raw
    # RuntimeError when asked to load a solution for an infeasible/unbounded run.
    results = solver.solve(model, tee=tee, load_solutions=False)
    elapsed = perf_counter() - start
    status = results.solver.status
    termination = results.solver.termination_condition

    if termination in {TerminationCondition.infeasible, TerminationCondition.infeasibleOrUnbounded}:
        raise InfeasibleModelError(f"Solver termination condition: {termination}")
    if termination == TerminationCondition.unbounded:
        raise UnboundedModelError(f"Solver termination condition: {termination}")
    if status not in {SolverStatus.ok, SolverStatus.warning} or termination != TerminationCondition.optimal:
        raise NonOptimalModelError(
            f"No certified optimum: solver_status={status}, termination_condition={termination}"
        )

    model.solutions.load_from(results)
    objective = float(value(model.total_cost))
    lower_bound = _safe_bound(results, "lower_bound")
    upper_bound = _safe_bound(results, "upper_bound")
    if lower_bound is None and upper_bound is not None:
        lower_bound = upper_bound
    if lower_bound is None:
        lower_bound = objective
    relative_gap = abs(objective - lower_bound) / max(1.0, abs(objective))

    return SolveInfo(
        solver_name=solver_name,
        solver_version=_solver_version(solver_name, solver),
        solver_status=str(status),
        termination_condition=str(termination),
        objective_value=objective,
        best_bound=lower_bound,
        relative_mip_gap=relative_gap,
        solve_seconds=elapsed,
    )
