# Narrow controls and summary finance modes in 0.9.23

Narrow title bars allocate separate rows to their controls when needed, keeping
creation, transparency and language controls clear of the title and window
buttons. Card identity width comes from the assigned logical card layout before
its first paint. A narrow native measurement therefore cannot turn the name
and metadata into a tall vertical text column.

More/Less docks on the card border only in a single card column below 680
logical pixels. When a selected battle has a Back control, it remains adjacent
to More/Less. Wider cards and two-column views retain their ordinary placement.

The existing summary finance heading contains a compact All/Min/Avg/Max choice.
All displays totals. The other modes display actual per-field minimum,
average or maximum battle values for Credits, Bonds and Gold. Switching modes
updates the existing figure nodes instead of rebuilding the result list.
Source buttons retain their original metric, statistic and availability.

Scope summaries expose a `currency_series` distribution for each supported
currency field. These distributions include known zero values, exclude missing
values and pending battles, and follow the selected period. Individual group
and battle payloads do not acquire this summary-only extension. Incomplete
Base-credit income and net remain dashes in all four modes rather than showing
a known subset as a complete selected-period value. Settled Costs remain one
shared expense for the Base/Received credit pair.


## Regression execution

The UI matrix keeps all 47 feature suites and the parent contract checks.
Independent feature phases run in two isolated Node processes, each with its
own browser and report. Scheduling hints balance work without selecting or
omitting tests; original order is retained within each assigned group.
The parent validates assignment and report completeness and fails on missing
results, duplicate suites, worker errors or browser errors. All language, width,
scale and navigation transitions inside each suite remain intact.

The pinned browser runtime, global timeout, two reproducibility builds and
release audits retain their existing configuration. This change addresses the
full browser matrix exceeding its 900-second budget as coverage grew.

The complete local six-suite browser benchmark passed in 554.4 seconds,
including 538.1 seconds for the main contract. These are local measurements;
canonical CI uses its pinned container and is validated independently.
