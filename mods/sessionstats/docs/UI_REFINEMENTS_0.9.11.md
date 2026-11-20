# Source arrows and historical data corrections in 0.9.11

Performance Min/Max values keep their original numeric nodes, with a transparent
cell-sized action over them. A small rounded cue on the left draws an arrow from
the lower left toward the upper right. The cue has a muted background and no
border, outline or shadow. Hover, focus and the active statistic change only its
background. Average remains noninteractive. Financial Min/Max controls retain
their explicit native captions, use only the width needed by those captions and
have equal surrounding spacing. Source navigation keeps its existing period,
account, revision and DOM ownership checks.

The selected statistic and its figure now come from the same metric series.
A retained card's earlier `sort_value` cannot leave an old figure under a newly
selected Min/Average/Max label. Missing or empty series remain unavailable. A `*`
beside the selected caption identifies an incomplete sample; its help gives the
available battle count. Min/Average/Max can legitimately match when only one
result contains that metric. No missing amount is estimated or replaced by zero.

Historical records can have received credits and actual costs without original
base earnings. Base income and net totals, including Base **All** sorting, remain
unavailable until their coverage equals the group's recorded battle count. This
prevents one newer battle's base subtotal from appearing comparable to the whole
period's received earnings and costs. Known Base Min/Average/Max and their source
actions remain available, including a recorded zero. An entirely unknown Base
comparison stays omitted. Existing records, received amounts and available metric
series are preserved; a later complete report can still enrich an older battle.

The native Crucible `quests` progress value is a one-based current stage. Active
mission capture now uses `questsIDs[stage - 1]` and retains that same stage number,
including the last stage. This prevents the next stage's lobby context from
appearing alongside the stage actually reported by the battle. Reading older
details also removes an unmodified, observed-only next-stage placeholder when
one confirmed result identifies the actual stage in the same challenge chain.
Genuine progress, completed results and ambiguous cases are retained.

Regression fixtures use synthetic data. Browser checks exercise the shipped UI;
the live client's renderer and mission lifecycle still require an in-game check.
