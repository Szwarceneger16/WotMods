# Readability and loading refinements in 0.9.6

The summary uses three compact label/value rows: Total Base XP, Total Received XP
and Free XP last. Each value keeps its own known-result coverage. The redundant
green WN8 coverage line is removed; the main result count and WN8 explanation
remain. The summary no longer reserves separate tall total columns.

Recognized decorative map and battle-result thumbnails fill their existing
frames. This removes side bands caused by fitting a photo inside a differently
shaped thumbnail. A small photo edge can be cropped, without stretching the
artwork. Tactical/default maps, unknown image categories and vehicle icons keep
full containment. Enlarged map previews keep their separate framing rules.

Black WN8 digits retain the rating palette and fine light outline. A light backing
directly behind the digits makes small values such as 261 readable in expanded
histories. The backing does not fill a complete table cell or caption. Other
rating colors and unavailable values retain their existing paint.

Aggregate sorting offers All for Base XP, Received XP, Credits net and Credits
gross. It sums confirmed values for the complete selected group and period,
independently of pagination. Gross credits use recorded income; net credits
include costs. Missing values stay unavailable and partial sums retain coverage.
WN8 and win rate do not offer All. Individual battles use their own recorded
values. Min/Avg/Max remain available where applicable.

Battle-result captions are uppercase in every interface language, both on cards
and in expanded histories. Caption slots retain their established widths; long
translated outcomes wrap without moving adjacent rating or navigation controls.

A centered loading indicator and scrim cover the complete panel while its
existing loading owner is active. Retained results use a slight blur where the
renderer supports it. Closing the panel and replacing a range remain possible;
the scrim does not consume pointer input. Completion, errors and teardown retire
the same owned pending state, without adding a timer or changing layout geometry.

Regression checks use synthetic records and locally generated artwork. Native
WoT Gameface appearance still requires an in-game check.
