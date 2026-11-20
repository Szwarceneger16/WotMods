# Native arrow flow and compact responsive headers in 0.9.14

The source arrow now participates in the numeric cell's normal inline flow,
immediately after the original text or WN8 figure. Its 3 px leading margin and
16 px width reserve real space. The transparent cell action remains separate
and retains its account, range and revision checks. Hover and keyboard focus
change only the arrow background.

In the live client, the previous padded cell and absolutely positioned cue
could overlap the final digits. The regression model covers both a native
content-box overlay and collapsed button-caption painting. Original numeric
nodes remain direct children of the cell; the hit target does not paint the
number or position the visual cue.

Aggregate headers restore compact, fixed Battles, Win rate and WN8 columns.
The selected sorting result alone expands to fit its caption and amount. Its
gold frame remains close to its content, and the warning triangle stays beside
the unwrapped caption. Smaller cards give the identity and statistics separate
rows instead of compressing all header fields into one line.

Single-column aggregate cards with default ordinary widths use the available
panel width up to the configured wide-card limit. Explicit nondefault ordinary
widths retain their configured size. The actual card width determines whether performance and
finance tables sit beside each other or stack. Two-column thresholds, individual
Battle cards and explicit wide-card limits retain their existing meaning.

Regression coverage uses synthetic data and checks all seven languages,
normal and doubled scales, narrow and wide panels, complete six-digit values,
black and colored WN8, compact KPI spacing and source navigation. Browser tests
exercise the shipped UI with adversarial native-layout models; the live client
still requires an in-game check.
