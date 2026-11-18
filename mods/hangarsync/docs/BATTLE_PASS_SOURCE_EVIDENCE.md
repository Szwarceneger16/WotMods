# Native Battle Pass snapshot boundary

The adapter reads the running client without purchasing, selecting chapters,
claiming rewards, or loading account history. `include_missions` controls the
entire read. No account identifiers or raw controller/configuration objects are
serialized.

The public EU client source was inspected for these interfaces:

- `gui/game_control/battle_pass_controller.py`: dependency
  `IBattlePassController`; current season/chapter, cumulative chapter points,
  completed-stage count, per-stage point pair, completion and purchased-pass
  state. `getChapterIDs()` filters expired additional chapters.
- `battle_pass_common.py`: server configuration chapter IDs and cumulative
  thresholds. Configuration IDs are preferred to retain expired additional
  chapters. Sentinel bounds for repeatable post progression are not displayed
  as a finite completion target.
- `gui/Scaleform/locale/BATTLE_PASS.py`: generic localized chapter key
  `#battle_pass:chapter/fullName/<chapterID>`.
- `gui/impl/lobby/battle_pass/chapter_choice_view.py`: the displayed current
  stage is completed-stage count plus one, capped at the reported chapter size.

Source references:

- https://raw.githubusercontent.com/izeberg/wot-src/EU/sources/res/scripts/client/gui/game_control/battle_pass_controller.py
- https://raw.githubusercontent.com/izeberg/wot-src/EU/sources/res/scripts/common/battle_pass_common.py
- https://raw.githubusercontent.com/izeberg/wot-src/EU/sources/res/scripts/client/gui/Scaleform/locale/BATTLE_PASS.py
- https://raw.githubusercontent.com/izeberg/wot-src/EU/sources/res/scripts/client/gui/impl/lobby/battle_pass/chapter_choice_view.py

Every capture replaces the current-season snapshot. There is no persistent
season cache to mix old and new data. Season/account rollover inconsistencies
produce a pending empty snapshot. Missing methods or values become explicit
partial/unavailable data and null fields. Source compatibility checks and
synthetic tests do not replace a live-client verification.
