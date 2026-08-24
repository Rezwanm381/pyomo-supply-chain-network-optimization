# Public claims

## `SAFE_PUBLIC_CLAIMS`

- “Built a clean-room Pyomo MILP for a synthetic supply-chain network-design case.”
- “The model chooses facility openings and shipment allocations while satisfying capacity and demand constraints.”
- “HiGHS solved the base MILP to optimality with a zero reported MIP gap.”
- “Independent enumeration over all 64 facility subsets confirmed the optimum.”
- “The base optimized scenario objective was 42.21% below the explicitly defined all-facilities-open reference scenario.”
- “The portfolio case uses transparent synthetic inputs, schematic coordinates, and scenario USD/year.”
- “Independent feasibility, domain, and objective-arithmetic checks reproduced the solver result.”
- “The declared sensitivity cases demonstrate configuration changes within the documented synthetic scenario.”
- “The project is a clean-room portfolio rebuild inspired by graduate optimization coursework and historical Pyomo experimentation.”

## Required qualifications

- `ALL_FACILITIES_OPEN` is a deliberately defined reference scenario with shipment allocation still optimized. It is not an existing network, current-company state, or industry baseline.
- Use “scenario cost reduction relative to the defined baseline.” Do not describe the 42.21% comparison as achieved, real, or company savings.
- Enumeration independently reconstructs the subset transportation problems and agrees exactly with the Pyomo MILP. The normal enumeration path uses SciPy/HiGHS for its continuous LPs; Module 7.5C also reproduced the results through a solver-engine-free minimum-cost-flow path.
- Enumeration is useful here because six binary decisions produce only \(2^6=64\) subsets. Do not imply that exhaustive enumeration is practical for large industrial networks.
- Use “schematic distance,” not road distance, mileage, travel time, or sourced freight rate.
- Use “optimal for the stated deterministic scenario and formulation,” not an unqualified claim of an optimal supply chain.
- Sensitivity patterns apply only to the declared scenarios and do not establish robustness, forecasts, or general industry behavior.

## `UNSUPPORTED_OR_PROHIBITED_CLAIMS`

- “Optimized a real company's supply chain.”
- “Reduced logistics costs by 42.21% in practice.”
- “These are real freight rates.”
- “This network should be deployed.”
- “The historical Pyomo notebook was solely authored by me.”
- “The all-open baseline represents an actual or industry network.”
- “The model proves robustness to uncertainty or stochastic demand.”
- “The result is verified ROI, profit improvement, or company savings.”
- “This code is the exact historical course submission.”

Prohibited statements are documented here only as controls; they are not project claims.
