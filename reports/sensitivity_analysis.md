# Sensitivity analysis

All multipliers were declared before analysis and are labeled `SCENARIO_ASSUMPTION`. Each feasible case independently passes solver optimality and post-solve validation.

| Scenario | Change | Objective | Facilities | Network utilization | Changed from base |
|---|---|---:|---|---:|---|
| DEMAND_LOW | Demand × 0.80 | 246,956.220 | FAC_C; FAC_NE | 99.7403% | YES |
| DEMAND_BASE | Base inputs | 285,488.900 | FAC_NW; FAC_NE; FAC_SE | 96.9697% | NO |
| DEMAND_HIGH | Demand × 1.20 | 338,283.500 | FAC_NW; FAC_SW; FAC_NE; FAC_SE | 89.3023% | YES |
| TRANSPORT_LOW | Transport cost × 0.75 | 264,783.675 | FAC_SW; FAC_NE; FAC_SE | 100.0000% | YES |
| TRANSPORT_HIGH | Transport cost × 1.25 | 303,361.125 | FAC_NW; FAC_NE; FAC_SE | 96.9697% | NO |
| FIXED_LOW | Fixed cost × 0.75 | 231,988.900 | FAC_NW; FAC_NE; FAC_SE | 96.9697% | NO |
| FIXED_HIGH | Fixed cost × 1.25 | 336,294.900 | FAC_SW; FAC_NE; FAC_SE | 100.0000% | YES |
| CAPACITY_STRESS | Capacity × 0.90 | 301,664.940 | FAC_NW; FAC_C; FAC_SE | 98.7654% | YES |

## Demand sensitivity

At 0.80× demand, 768 units fit within the combined 770-unit capacity of `FAC_C` and `FAC_NE`; `FAC_C` binds and the network uses only two facilities. At base demand, no two facilities can cover 960 units because the two largest total only 810, so three facilities are required. At 1.20× demand, the model opens four facilities—`FAC_NW`, `FAC_SW`, `FAC_NE`, and `FAC_SE`—to serve 1,152 units. This is a clear infrastructure threshold: the optimal network changes from two to three to four facilities across the declared demand cases.

## Cost sensitivity

When transport cost is discounted to 0.75×, fixed cost carries more relative weight and the lower-fixed-cost `FAC_SW` replaces `FAC_NW`; all three selected facilities bind. At 1.25× transport cost, the base facility configuration remains, because its proximity pattern offsets the higher per-unit penalty.

Reducing fixed costs to 0.75× retains the base configuration. Raising fixed costs to 1.25× magnifies the fixed-cost advantage of `FAC_SW`, so it replaces `FAC_NW`; the resulting `FAC_SW`/`FAC_NE`/`FAC_SE` network has exactly 960 units of capacity and is fully utilized.

## Capacity stress

Reducing every facility capacity by 10% changes the configuration to `FAC_NW`, `FAC_C`, and `FAC_SE`. `FAC_C` and `FAC_SE` bind, selected capacity is 972, and only 12 units/year remain unused. The central candidate’s high fixed cost becomes acceptable because its scaled 387-unit capacity helps preserve a three-facility design.

## Controlled infeasibility

The separate `INFEASIBLE_DEMO` sets demand to 2.25×. Total demand becomes 2,160 while total potential capacity remains 2,100. The workflow records `PRE_SOLVE_INFEASIBLE` and does not invoke the solver for this case.

## Interpretation boundary

The analysis identifies deterministic scenario thresholds only. Network-configuration changes are properties of these declared synthetic cases and should not be generalized beyond them. This is not a probability model, robustness guarantee, freight forecast, or evidence of real-company savings.
