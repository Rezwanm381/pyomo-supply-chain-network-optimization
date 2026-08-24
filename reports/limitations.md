# Limitations

- All facilities, customers, coordinates, demand, capacity, fixed costs, and transport-cost assumptions are synthetic scenario inputs. They are not verified company data.
- The model is deterministic. Demand, capacity, and costs are assumed known within each scenario; no probability distributions or confidence claims are made.
- Euclidean distance on synthetic coordinates is only a schematic transport proxy. It is not road mileage, route time, lane availability, congestion, or a sourced freight quote.
- The cost structure omits freight contracts, tariffs, fuel adjustments, handling tiers, economies of scale, minimum charges, and fixed lane costs.
- The case has one product-equivalent flow and one annual horizon. It does not model product compatibility, inventory, production, safety stock, lead time, seasonality, or multi-period facility timing.
- Exact demand balance assumes all demand is served and prohibits overdelivery. Shortage, backlog, lost sales, disposal, and service penalties are outside scope.
- Every candidate can serve every customer. No road, border, service-radius, or lane-eligibility restrictions are modeled.
- Capacity is aggregate. It does not distinguish labor, dock, storage, processing, product, or seasonal bottlenecks.
- The baseline is deliberately simple: all facilities open with cost-minimizing allocation. It is a defined reference scenario, not a real or industry baseline; other heuristics could provide different comparison values.
- Sensitivity analysis uses a compact set of deterministic multipliers. It does not prove robustness between or beyond those scenarios.
- The result is a portfolio demonstration, not a production deployment, optimization service, operating recommendation, or audited financial model.
- The reported cost difference is not verified financial savings, ROI, profit improvement, or a real-world outcome.
- Historical Pyomo material exists as private reference context, but historical authorship, starter-code lineage, and submission status are unresolved. The public implementation is a clean-room rewrite and does not establish ownership of the historical notebook.
- Future work could add calibrated real or rights-cleared inputs, products/periods, lane eligibility, inventory dynamics, service levels, and then robust or stochastic optimization. Those capabilities are not claimed here.
