# Native single-row actions and consistent help in 0.9.15

Each clickable performance cell is an explicit non-wrapping flex row. Its
original text or WN8 figure is moved, without cloning, into a plain paint block
outside the fixed-size 16×18 arrow button. A 3 px margin separates the two
items. The number does not depend on button-caption painting, anonymous inline
text layout or a percentage-sized click overlay. Number-area clicks delegate
to the same source action without dispatching button and keyboard clicks twice.

WN8 corrections operate on the value paint block, preserving the source button
when a rating changes from black to colored or unavailable. Numeric content
and the normal reading size remain intact. Ordinary values retain their compact
table dimensions. Eight-digit distributions use a wider performance table so
the complete figure and its action fit without shrinking the text or adding
an action-only line; small panels can stack the table pair.
Native-layout regressions model
anonymous cell text as blocks and collapse button captions; the prior layout
must fail the single-row check while the explicit row remains compact.

Custom hover help opens 500 ms after entering an action. Moving within its
number, icon or button keeps the same timer and canonical button owner. Leaving
the action cancels the timer. Registered custom hints suppress their native
title fallback, preventing a second tooltip with a different delay. Keyboard
focus and explicit information-button activation retain immediate help.

Orange range and card warnings both mean that the selected metric is missing
inside received battle reports. They compare its known count with the received
report count, not the larger recorded count that includes pending reports.
For example, 24 known values in 24 received reports out of 27 recorded battles
has pending coverage help and the existing 24/27 counter, but no orange field
warning. If only 23 of those 24 received reports contain the selected value,
both warning locations indicate the incomplete field. Global warnings cover
the selected whole range rather than only the displayed page.

After Back restores its existing source anchor and focus, the actual source
button receives a 2 px orange outline and soft glow for five seconds. This
applies to performance arrows, financial Min/Max and history Show battle
buttons. The marker validates the original battle, metric, statistic, owner
and card; it never marks a fallback tab or a history row. A short bounded
ownership timer can rebind a replaced source node without moving focus or
scrolling, and stops on expiry, navigation, changed context or destruction.

The compact headline columns and responsive card-width policy from 0.9.14 are
retained. Regression fixtures and captures are synthetic. Native fault models,
real backend navigation tests and browser geometry checks complement the
remaining in-game verification of the client's renderer.
