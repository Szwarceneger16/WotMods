# XP presentation and credit sorting in 0.9.7

The summary presents Total Base XP, Total Received XP and Free XP as three equal
horizontal columns. Captions form one row, with values and their independent
coverage beneath. Explicit flex rows reserve caption/value height so native
intrinsic-size differences cannot overlap the following content. This is a visual
table implemented with divs and accessibility roles; it does not require native
HTML table layout. Gameface documents [Flexbox support and its browser
differences](https://docs.coherent-labs.com/cpp-gameface/what_is_gfp/htmlfeaturesupport/).

Base XP and Received XP are always visible together. Summary and aggregate
performance tables contain Base XP, Received XP and battle WN8 rows; individual
battles show both XP values above WN8. Each metric keeps its own confirmed count,
and a common coverage header is used only when every displayed metric agrees.
Known zero remains zero and an unavailable value remains a dash. The XP display
selector and its handlers are removed. Legacy saved XP-mode data can still be
read but does not select or hide either row. Sorting continues to choose its
Base XP or Received XP metric independently of presentation.

Black WN8 figures retain their fine light edge and use a translucent neutral gray
backing. It is limited to the figure rather than the surrounding cell or label.
The backing remains readable over a dark panel while reducing the bright patch
of the previous version. Other rating bands keep their original colors.

Credit sorting distinguishes income (net), income (gross) and costs. Costs use
confirmed positive expense magnitudes: descending selects the greatest expense
first. Finance cells continue to display spending with a minus sign. Min, Avg,
Max and All operate on confirmed values across the complete group and selected
period before pagination. Costs have their own coverage; missing income or net
does not substitute for missing costs. Individual battles use their own recorded
expense, and All remains unavailable for non-additive metrics and single battles.

Long financial metric captions wrap inside the existing fixed control footprint.
Full localized option names, tooltips and accessible labels remain available in
all seven interface languages. Regression checks cover the horizontal summary,
simultaneous XP values, semantic sort highlights, legacy input, expense ordering,
coverage, both interface scales and constrained label widths.

Synthetic browser/native-host checks do not replace live WoT Gameface testing.
