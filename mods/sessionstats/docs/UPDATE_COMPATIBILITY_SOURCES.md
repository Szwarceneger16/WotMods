# WoT update resilience — source audit

Read on **2026-10-20**, using the user's working **0.2.4** as baseline. This audit
limits client dependencies and the consequences of their changes; it does not
claim compatibility with unreleased WoT versions.

## Findings

Resilience can improve for missing functions, removed image helpers, changed optional
controllers and window-open/close failures. A separate calculation/storage core
with small client adapters minimizes maintenance. The working panel does not need
a different engine or a copy of the native panel.

Current sources cannot guarantee operation after changes to battle-result formats,
Wulf/Gameface protocols or the bytecode runtime. Those may require adapter updates
or recompilation. Method availability detects structural failures but does not prove
unchanged meaning.

## Sources

Client mirror `izeberg/wot-src`, commit **`5e721e36891c80d8d51a431164960c863641ee63`**,
identified in earlier project documentation as client **2.4.1.5493**. These establish
actual contracts, not an official stable Wargaming SDK.

| Source | Verified behavior | Consequence for the mod |
| --- | --- | --- |
| [gui/mods loader](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/mods/__init__.py) | Production recognizes `mod_*.pyc` and calls `init`/`fini`. `_callModMethod` catches `AttributeError`; `_findValidMODs` imports catch `ImportError`. | Guard entry/exit locally; do not assume the caller isolates every mod failure. |
| [Event.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/Event.py) | Ordinary `Event` rethrows listener exceptions; `SafeEvent` differs. | Isolate mod callback boundaries; not every client event is `SafeEvent`. |
| [PlayerEvents.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/PlayerEvents.py) | Provides account, battle-entry and `onBattleResultsReceived` events used by the adapter. | Subscriptions expose less change surface than replacing large methods. One optional failure should not block the rest. |
| [LobbyFooter](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/lobby/page/lobby_footer.py) | A `ViewComponent` registering children including native session statistics. | A small component is appropriate, but class paths/lifecycle remain dependencies. The separate-window shortcut limits footer-change effects. |
| [Official support: modification-related issues](https://wargaming.net/support/en/products/wot/article/15252/) | Describes mod-related problems and clean-client launch without mods or resetting settings. | It does not promise stable internals. Browser checks do not replace testing in the updated client. |

Reviewed blob IDs: loader `736f2c29ff76644d6cf705b9011389b6136e391d`;
`Event.py` `085542140af9e7821f9bd0058242f72e58ab8c80`;
`PlayerEvents.py` `9f856791d624bdb147004c5ca0591df43b7049a1`;
`LobbyFooter` `c3673d182cfda5711151fdc5b8543051ef3be570`.

## Improvement priorities

1. **Result receipt/storage independent of optional UI.** A missing button, window
   import, thumbnail helper or keyboard signal should not stop statistics if their
   actual result source still works.
2. **Guard each client boundary separately.** Listener attachment/calls/removal and
   window operations need independent failure paths. One failure must neither
   prevent other cleanup nor escape into the native dispatcher.
3. **Use named client resources.** Dedicated registration and thumbnail adapters
   avoid fixed numeric resource IDs. One image family's failure should not disable
   the others.
4. **Preserve data meaning.** Unknown/partial data stays unknown. Compatibility
   handling must not replace missing costs with zero, guess new tuples or invent
   a battle outcome.
5. **Check capabilities rather than version lists.** A new client number does not
   invalidate everything; an existing method name alone does not prove unchanged
   argument/result semantics.

## Currency ordering remains an explicit result contract

Rechecked [gui/shared/money.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/money.py),
blob `751c6da56b3560f3f0198c860efdd6bc4d95cafb`. `Currency.ALL` lists the `Money`
model currencies but **does not define positions in battle-result `autoLoadCost`,
`autoEquipCost` or `autoEquipBoostersCost`**. It is not metadata for those fields.

The [native result-economy reader](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/battle_results/reusable/economics_records.py),
blob `da97053f85b1faa329971e775c9daf6154469c7e`, uses explicit indexes:

| Field | Index 0 | Index 1 | Index 2 |
| --- | --- | --- | --- |
| `autoLoadCost` | Credits | Gold | Not read |
| `autoEquipCost` | Credits | Gold | Bonds (`crystal`) |

These reads are at lines 61–71 and 95–98. The [shared result declaration](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/battle_results/battle_results_common.py),
blob `a8476aed85f0cfce21e6a3c9fb267e6cc533ae21`, defines `autoLoadCost` as a tuple
defaulting to `(0, 0)` and `autoEquipCost`/`autoEquipBoostersCost` defaulting to
`(0, 0, 0)` without named adapter positions.

Keep this known native-reader contract. Mapping it to `Currency.ALL` would add an
assumption instead of removing a dependency. Changed financial semantics or
serialization still require reviewing new client code and a concrete settlement.
Field names, formulas and currency ordering are not automatically guessed.

## Loading after a client-version change

The installer places `.wotmod` files in `mods/<client_version>/`; statistics remain
in AppData. Active-folder selection and code compatibility are separate: moving
a package addresses only folder selection.

The official [modification guide dated 2018-12-17](https://worldoftanks.eu/pl/news/general-news/dress-up-santa-vs-krampus/)
shows a versioned `Mods` subdirectory. The official [9.15.1 technical article](https://worldoftanks.eu/en/news/general-news/update-9151-technical-aspect/)
records an interface change after which moving old mods could cause instability.
These are **historical evidence**, not instructions specifying the current October
2026 client version. The original Polish source URL is retained as evidence.

The mod does not bypass loading through core path modifications or activate itself
automatically in every future client. Install for the actual version and perform
a short check after major updates.

## OpenWG and validation limits

Bundled OpenWG Gameface **1.2.2** retains the pinned version/sources in
`third_party/openwg/`. It supports the garage button; the separate window should
not require it. A maintained shared library reduces custom integration code but
does not guarantee future compatibility. This audit does not require replacing
the working dependency.

Tests for missing methods, rejected subscriptions and optional failures validate
specific fallback paths, not all future updates. No new live client, battles or
unreleased result format were tested here.
