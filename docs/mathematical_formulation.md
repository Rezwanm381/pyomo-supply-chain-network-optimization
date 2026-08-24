# Mathematical formulation

## Case boundary

This clean-room case is a deterministic, single-period distribution-network design problem. A planner chooses which candidate distribution centers to open and how much each open center ships to each customer zone. All entities and strategic coefficients are synthetic scenario assumptions; lane distances and unit costs are deterministic derivatives of those assumptions. No real company is represented.

The single-echelon form is deliberate. It preserves a genuine binary infrastructure decision without adding products, periods, service rules, inventory, or production layers that would not materially improve the decision demonstration.

## Sets and indices

- \(F\): candidate distribution centers, indexed by \(i\).
- \(C\): customer zones, indexed by \(j\).
- \(A = F \times C\): allowed shipment arcs. The base scenario contains every facility-customer pair.

## Parameters

- \(d_j\): demand at customer zone \(j\), in units per year.
- \(K_i\): annual capacity of facility \(i\), in units per year.
- \(f_i\): fixed cost of opening facility \(i\) for the annual scenario horizon, in USD per year.
- \(c_{ij}\): unit shipment cost from facility \(i\) to customer \(j\), in USD per unit.

For sensitivity scenario \(s\), transparent multipliers may be applied to demand, capacity, fixed cost, or unit shipment cost before model construction. A scenario is validated after the multipliers are applied.

## Decision variables

- \(y_i \in \{0,1\}\): 1 if candidate facility \(i\) is opened; 0 otherwise.
- \(x_{ij} \ge 0\): units per year shipped from facility \(i\) to customer zone \(j\).

## Objective function

Minimize total annual scenario cost:

\[
\min Z = \sum_{i \in F} f_i y_i + \sum_{i \in F}\sum_{j \in C} c_{ij}x_{ij}.
\]

The first term is facility-opening cost. The second term is variable shipment cost. No revenue, profit, ROI, or actual-company savings term is modeled.

## Constraints

### Exact demand balance

\[
\sum_{i \in F} x_{ij} = d_j \qquad \forall j \in C.
\]

Equality is used because the case models neither shortage nor excess delivery. Every unit demanded must be allocated exactly once.

### Facility capacity and activation

\[
\sum_{j \in C} x_{ij} \le K_i y_i \qquad \forall i \in F.
\]

This single tight constraint enforces both annual capacity and zero shipment from a closed facility. No separate arbitrary Big-M constraint is needed.

### Domains

\[
x_{ij} \in \mathbb{R}_{\ge 0} \qquad \forall (i,j) \in A,
\]

\[
y_i \in \{0,1\} \qquad \forall i \in F.
\]

## Feasibility condition

A necessary pre-solve condition is:

\[
\sum_{i \in F} K_i \ge \sum_{j \in C} d_j.
\]

Because every facility can serve every customer in the base case and there are no additional business rules, this condition is also sufficient for aggregate capacity feasibility. The implementation rejects scenarios that violate it before calling the solver.

## Numerical tolerances

- Constraint feasibility: \(10^{-6}\) scenario units.
- Binary interpretation: \(10^{-6}\) from 0 or 1.
- Objective reconciliation: \(10^{-6}\) relative tolerance with a minimum absolute tolerance of \(10^{-5}\) USD.

These tolerances avoid unrealistic exact floating-point comparisons while remaining tight relative to the scenario scale.

## Validation of the formulation

The implementation recomputes every demand balance, capacity relationship, variable-domain check, and objective component directly from input tables and returned decision values. For this small case, all \(2^6=64\) facility subsets are also examined through an independently assembled transportation formulation; 41 are capacity-feasible and the best subset exactly matches the Pyomo MILP. A two-facility, two-customer known-answer problem with objective 280 provides an additional formulation check.

Enumeration is a validation layer for this portfolio-sized instance, not a scalable replacement for MILP optimization. The number of subsets grows exponentially with the number of binary facility decisions.
