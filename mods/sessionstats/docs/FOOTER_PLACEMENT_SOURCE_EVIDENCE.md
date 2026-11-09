# Garage footer placement

The footer button uses the existing right-hand control section. It does not add
a fourth child to the footer's left/chat/right layout or change native styles.

Verified client assets: `Kurzdor/wot.assets` commit
`3605bd36c53d10c16be5d93f5414aa5fd129e84e`, client **2.4.1.0 #977**.

- [Garage footer bundle](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/mono/hangar/footer/bundle.js):
  the native control uses the singular `SessionStatistic_` class prefix. Its
  `Footer_section_` contains session statistics, a divider, server information,
  the menu, another divider, and notification center in that order. The menu
  and notification controls expose `data-test-id="menu"` and
  `data-test-id="notificationCenter"`.
- [Garage footer stylesheet](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/mono/hangar/footer/footer.css):
  the outer footer distributes its three children with `space-between`.
  Sections are horizontal flex rows. Dividers and the notification icon own
  their native margins; the injected button adds no side margin.
- [LobbyFooter host](https://github.com/izeberg/wot-src/blob/ed377b7bc5e8c232cf41bd0887bcfa0d75005fcb/sources/res/scripts/client/gui/impl/lobby/page/lobby_footer.py):
  the host loads `R.views.mono.hangar.footer()` and registers the native session,
  server and notification presenters independently. The mod's child model and
  command API remain separate.

Placement is checked again when data changes, so a late or recreated native
control can move the existing owned button into its correct slot. When native
session statistics are disabled, the same section's first divider identifies
the vacant position. An unrecognized footer remains untouched.

Browser fixtures verify the native sibling order and geometry, equal owned
button margins, late-control placement, recreation, and exact native markup
after removal. They do not replace an in-game check of the native renderer.
