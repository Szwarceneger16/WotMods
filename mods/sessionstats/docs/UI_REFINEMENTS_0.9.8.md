# Battle references, native vehicle metadata and compact headers in 0.9.8

Min/Max aggregate sorting can name the battle responsible for the selected
value. Maps, Vehicles and Tiers use indexed references across the complete
selected period, independently of the loaded history page. References cover Base
XP, Received XP, battle WN8, credit income (net/gross) and credit costs. Equal
values choose the smallest stable battle ID. Corrections and removals update the
reference along with the aggregate; Average and All do not invent a source battle.

The compact battle link shows the vehicle, map and full localized date in its
tooltip, and opens the existing Battles view with the selected-battle marker.
Retained links stop working after their account, period, grouping, ordering,
revision or DOM owner changes. Tooltip content remains plain text.

The overview keeps its received-results count while removing repeated visible
x/y beneath the three XP totals and in the global table headers. Metric-specific
availability remains in the existing overview help and accessibility labels.
Performance and finance titles, including their help controls, occupy the first
header cells rather than separate rows. Other group-card coverage is preserved.

Black WN8 figures use a muted translucent olive-gray backing. Its scope remains
the digits, with the fine light outline retained; other rating bands and captions
keep their existing paint.

Vehicle and battle cards show original client class and role icons. Presentation
lookup repairs missing historic class metadata and handles the native AT-SPG
spelling without rewriting the ledger or replacing recorded tiers. Role names
and definitions come from the running client's formatter and localization, as
in Hangar Sync. Class labels follow the selected mod interface language; official
role text follows the game client's language. Client markup is converted to
bounded plain text. Missing APIs or artwork remain unavailable rather than being
replaced with an invented icon or role. Native class/role textures are referenced
locally; no additional asset pack or runtime network request is introduced.

Compact aggregate headline slots keep Battles, Win rate, WN8, the selected value
and the More action aligned. An additional credit/XP total value uses the fixed
header host rather than increasing the identity block. When no additional value
is needed, the host can show the relevant first/last battle date; a valid Min/Max
reference identifies its source battle. Narrow layouts reserve a consistent
statistics row. Full labels and source details remain available through help.

Regression checks use synthetic records and generated artwork, including zero,
missing values, corrections, off-page winners, localized captions and both UI
scales. Live WoT Gameface appearance still needs an in-game check.
