# Summary return, selected cells and shared credit costs in 0.9.16

Upper-summary source navigation captures the semantic metric cell and its
visible offset. Back resolves that upper cell independently of the current
extremum battle reference, restores its position and verifies alignment before
finishing. It avoids relying on a native arrow button's nested offset chain.
Only the original exact source button receives focus and the existing orange
return marker; a changed reference must not mark a replacement battle.

Distribution sorting marks the selected metric and statistic cell, including
its figure and source arrow. Generic Min/Average/Max headings remain neutral.
Zero, signed and unavailable values follow the same selection rule. Financial
source controls retain their own metric and extremum ownership.

Every finance table retains both base and received credit rows. Missing base
income and net amounts remain unavailable, displayed as dashes; they are never
invented from received income. A partial known base subtotal still cannot look
like the complete period total. Bonds remain visible, while unused gold keeps
its existing optional behavior. XP and WN8 rows already remained visible.

The supported client and the mod use one set of actual battle expenses. The
client's base/premium report columns read the same repair, ammunition and
equipment expense records. Credit bonuses affect earnings, rather than
creating a second expense amount. The mod's `normalize.py` and `core.py`
subtract that same `costs` value from both base and received income.

The credit pair therefore renders one actual costs cell, centered across both
rows, with one owned Min/Max action pair. Income, net and costs keep their
independent availability and source references. The layout uses explicit
normal-flow flex boxes supported by Gameface, with a compact arrangement for
small finance tables and no duplicated numeric values.

Repeated row measurements subtract their owned alignment margin in computed
pixels before converting the result to logical units. This keeps compact
rows stable at elevated DPI and allows them to shrink when a caption wraps
onto fewer lines. The finance regression also bounds the row height by the
actual caption, amount and action content, rather than its assigned height.

Regression fixtures are synthetic. Validation covers summary navigation,
stale native offsets, exact selected-cell decoration, missing and zero base
values, shared costs, source ownership and narrow/wide layouts. Actual native
renderer behavior still needs an in-game check.

Browser application tests overlap only independent page-owning scenarios.
Each page retains its complete action, frame-wait and assertion sequence;
all active branches finish their cleanup before a failure propagates. The
pinned CI browser runtime, suite selection and 900-second budget are unchanged.
