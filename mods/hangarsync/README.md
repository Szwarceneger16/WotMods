# GRZ Hangar Sync

**Status: experimental, not yet verified inside the World of Tanks client.**

This independent `.wotmod` sends a read-only snapshot of **your own garage** to
the ChatGPT Site you explicitly configure on your computer. It does not read
battle opponents, automate inputs, mutate account data, install a background
process, or track activity after WoT exits.

## Battle Pass across seasons

With `include_missions: true`, version 0.12.0 also reads the client's current
Battle Pass season and configured chapters, including additional chapters.
Season/chapter IDs, localized names, dates, stage counts, variable point costs,
point totals, completion and Improved Pass state come from the native controller
and server configuration. No season name, chapter count, stage cost or deadline
is embedded in the mod. A later client API change may still require an adapter
update; missing data is reported as unavailable/partial, never invented as zero.
The snapshot replaces previous season data on each capture; it is not an archive
of historical seasons. No purchases, rewards claims or chapter selection occur.
The existing validated configuration is unchanged.

## Data included

- All vehicles in the account's garage inventory, independent of the in-game
  carousel filters. Includes each vehicle's name, tier, nation, class, and
  premium or elite status.
- Native vehicle roles (from 0.13.0), including their semantic label key and
  localized full/group names where the running client supplies them. Roles are
  not inferred from vehicle names or account statistics. Missing role APIs leave
  the optional field absent; unavailable translations remain null. These are
  vehicle roles, not the separate Personal Missions role-category classifiers.
- Saved vehicle playlists, including names and vehicle types in their saved
  order. The client can keep a sold vehicle on a list. Such entries are counted
  on the site but have no current garage loadout.
- Currently active equipment, consumable, ammo and directive slots. Equipment
  is labeled standard, bond, bounty or experimental, with upgrade level where
  available; ammunition includes the loaded quantity.
- Acquired field modifications and selected modification-pair choices.
- The native vehicle dossier creation date, shown as "Statistics started",
  when a synced existing dossier confirms at least one recorded battle.
  Missing or zero dates are omitted. This field works without Session Statistics.
- Crew member names, roles, qualifications and skills (optional). Structured
  learned and bonus perks include their native training percentages, zero-perk
  status, active state and native resolved tooltip effects where available.
  A shared native perk catalog supplies maximum-effect descriptions once per
  skill. Native major and bonus slot counts describe unselected/future slots.
  Unsupported details remain absent; the legacy perk-name list is preserved.
- Perk tooltips retain native short-description highlights as safe text spans,
  localized category/title, shared ALT mechanics/help paragraphs and a semantic
  key for the Site's bundled original video. Current contextual descriptions
  are separate from maximum-training previews. The native progression setter
  supplies exact nonlinear XP values for a paid major perk being trained,
  including the discounted threshold and zero-perk explanation where available.
  XP is never estimated from a percentage. Missing client APIs leave fields
  absent. Bonus perks have no independent paid-XP progression. HTML entities
  are decoded, including the client's zero-width spacing marker; no raw HTML
  or executable markup is exported.
- The previous-battle crew remembered by the game's Return Crew feature
  (optional, enabled by `include_crew`). It is separate from the currently
  installed crew. Known members show their current location: barracks, an owned
  vehicle or unknown. Member profiles and training percentages are current
  readings, not saved battle-time skill statistics; no effects are calculated
  against the historical vehicle. Missing or dismissed members are omitted and
  counted. No remembered roster, unavailable data and a roster identical to
  current slot assignments have separate explicit statuses. Native member IDs
  remain local and are never included in snapshots or logs.

Snapshots are bounded to 1,900,000 encoded bytes. Repeated current perk text is
shared losslessly within the snapshot; skill identity, training, native values,
and legacy plain text remain intact. Identical current and remembered
slot assignments are sent once. Current and remembered crew are never silently
truncated; an oversized garage remains unsent instead of replacing complete data
with a partial roster. Optional mission and daily-statistics metadata can still
be omitted under the existing payload fallback rules.
- Native icon identifiers for vehicles, installed items and optional crew
  portraits. The Site contains the original graphics as static assets.
- A label you choose in the local config and the selected server region.
  The mod checks the in-game nickname against the local list before reading
  the garage or missions for sync. The nickname and list stay on your computer.
- Optional mission data from the lobby cache. This covers daily, daily bonus,
  daily epic, premium, and weekly missions, available personal missions across
  campaign branches, and Crucible series with their ordered stages. The mod
  includes localized descriptions, requirements, rewards, and progress fields
  when the game exposes them through the supported interfaces.

No payment details, passwords, session cookies, chat, player IP address, replay,
battle history, opponent information, or Wargaming authentication tokens are
read or transmitted. The package contains **no credentials, individual Site
address, player nickname, account identifier or personal configuration**.

The client uses the cached GUI inventory objects; it does not scrape memory,
intercept Wargaming network traffic or read private game files. Alternate
equipment/ammo loadouts are not exported in this initial version: the **active
configuration** is the one reported. If any owned vehicle cannot be read, the
snapshot fails closed rather than silently replacing a complete garage with
partial data.

## Session Statistics integration

Install the compatible Session Statistics 0.4.1 build to enable vehicle WN8,
recorded Random Battle counts, net credit earnings, last-played timestamps and
daily counts for the latest 366 calendar days. Hangar reads the already running
mod through its bounded public API. It never opens that mod's ledger or calculates
WN8 or finances. Missing, loading or unsupported providers remain unavailable.
An ownership-start date is unknown because the game exposes no reliable current
purchase timestamp.

Vehicle images and mission graphics are bundled in the Site. This version sends
the native vehicle icon identifier, mission condition identifiers and reward
labels so the Site can select its originals. Image bytes are not read or uploaded.

## Installation

1. After the changes are reviewed and merged into `main`, download
   `GRZ_Hangar_Sync-v<version>.zip` from a successful **Build Hangar Sync installer**
   run in this repository, checking that its branch is `main` and its event is
   `push` or `workflow_dispatch`. PR checks build candidate packages only for
   validation and do not upload installation ZIPs. Do not install older PR
   artifacts even when their checks passed; their code and tests are unreviewed.
2. Extract it into the **physical World of Tanks installation**. For example,
   `mods/2.4.1.1/GRZ_Hangar_Sync.wotmod` is the fixed internal package name.
   If your current game uses a different versioned `mods` directory, move the
   `.wotmod` into that directory. Replace the previous copy for that client version.
3. In `mods/configs`, copy `GRZ_Hangar_Sync.json.example` to
   `GRZ_Hangar_Sync.json`.
4. Set `endpoint_url` to your own Site's full HTTPS sync route in the form
   `https://YOUR-SITE.chatgpt.site/api/sync`. The mod accepts only a valid
   ChatGPT Sites hostname and exactly the `/api/sync` route. No other hosts,
   plain HTTP, URL credentials, query strings, or redirects are accepted.
5. In your private Site's **Data sync** panel, create a device credential.
   Copy that value into `device_token`. It is shown only once.
6. Private ChatGPT Sites also requires a separate service-access bearer token
   for **non-browser** requests. Obtain that token through the owner's private
   Sites access workflow and put only the *bare token* into
   `sites_access_token`. This is a **Site-wide access credential**: treat it as
   highly sensitive, never commit it, post it to support or share screenshots
   containing it. A device token alone cannot pass the private Site's gateway.
7. Fill in `display_name` with a label for the panel, such as `My Garage`.
   Add each WoT account that may sync to `allowed_players`, for example
   `["CommanderOne", "CommanderTwo"]`. The mod matches whole nicknames without
   regard to case. All listed accounts use the same configured Site and label.
8. Set `enabled` to `true` and restart WoT. The mod takes snapshots in the garage
   for listed accounts and sends them while the client is running.

The installer ships a disabled `.example` template. Synchronization requires a
separate, fully validated `GRZ_Hangar_Sync.json` with explicit values for every
field, including both credentials and at least one allowed nickname. An empty
list or an unlisted account blocks snapshot collection and upload. Keep that
file on your own PC and share the unmodified installer ZIP.

When upgrading from 0.4.0, replace `expected_player` with `allowed_players`.
If you previously left the nickname blank, add your exact nickname to enable
sync. When upgrading from an older version, also copy over any missing fields
from the new template. Restart WoT after editing the config.

## Configuration

```json
{
  "enabled": false,
  "endpoint_url": "",
  "device_token": "",
  "sites_access_token": "",
  "region": "EU",
  "display_name": "",
  "allowed_players": [],
  "include_crew": false,
  "interval_seconds": 120,
  "include_missions": false,
  "mission_diagnostics": true
}
```

Keep your private URL, tokens and allowed nicknames in
`mods/configs/GRZ_Hangar_Sync.json`. The mod rejects missing, unknown and
duplicate fields, wrong types and invalid values. The sync interval must be
an integer from 30 to 600 seconds. Set `include_crew` to `true` if you want
crew details and available portraits included in the snapshot.
The network client uses HTTPS with certificate and hostname verification,
rejects redirects, disables proxy discovery, times out after eight seconds and
backs off after failures. It never logs tokens, URLs, nicknames, headers,
exception text or snapshot bodies. Snapshot changes are sent
asynchronously from a daemon worker (the game thread never waits on HTTPS).
No permanent queue is written to disk. On game shutdown the process terminates
the worker; on explicit mod teardown it cancels its scheduled callbacks.

The private Site acknowledges a garage snapshot before the mod sends images
in separate batches. Images are limited to 128 KiB each and deduplicated by
content for the game session. Images may appear shortly after the garage data.
Missing or unsupported images leave their text entries usable.

Set `include_missions` to `true` to add an optional `missions` field to sync
requests. Leave this off until your Site supports the field. The Site must
explicitly handle and display it. With `include_missions` set to `false`,
only the garage is sent. If adding missions would exceed the payload limit, the mod sends
the garage snapshot and logs a fixed diagnostic code.

## First garage test

1. Install the updated `.wotmod`. The local mission probe works without a config
   and with an invalid config. If you already have a valid config, set
   `"enabled": false` for a local-only test.
2. Start WoT, enter the garage, and open the Missions, Crucible, and Personal
   Missions tabs, including Operation Fossa if available. Leave WoT in the
   garage for about three minutes. No battle or mission activation is required.
3. Open `%APPDATA%\GRZ_Hangar_Sync` in Windows Explorer and share only
   `missions_diagnostics.log`. If AppData is unavailable the same folder is
   under `%LOCALAPPDATA%`.

The mission log contains timestamps, fixed categories and status codes,
recognized exception types, and counts of rows and available fields. It
excludes mission IDs and content, progress values, account details, paths,
URLs, and secrets. The probe runs up to nine times in the garage, about
20 seconds apart. This local probe runs independently of the sync switch and
nickname list so you can diagnose mission support before configuring sync.
To stop these local scans, set `"mission_diagnostics": false` in a valid config.

## Build and validation

```bash
python3 -m unittest discover -s tests -v
python3 tools/build.py --client-version 2.4.1.1
```

The deterministic builder creates a self-contained Python 2.7 bytecode
bootstrap. The ZIP contains only the `.wotmod`, a safe example config,
documentation and checksums. No GitHub upload or remote publication is
required for local installation.

## Diagnostics and limitations

Private diagnostic logs are written to
`%APPDATA%\GRZ_Hangar_Sync\hangar_sync.log` on Windows. If `%APPDATA%` is
unavailable, `%LOCALAPPDATA%` is used. The log rotates at 512 KiB and keeps
two older files (`hangar_sync.log.1`, `hangar_sync.log.2`). No external
telemetry, crash reporter or background logger is installed. If the log cannot
be opened, network synchronization remains disabled.

Log entries use UTC timestamps and fixed diagnostic codes:

- `event=config_failed code=file_not_found`: copy the example config to
  `mods/configs/GRZ_Hangar_Sync.json`.
- `event=config_failed code=missing_fields` means the config lacks a required
  key. Compare it with the supplied example.
- `event=config_failed code=display_name_invalid` means the label is missing
  for an enabled config or has an invalid length or characters.
- `event=config_failed code=players_list_empty` means sync is enabled and
  the account list needs at least one nickname.
- `event=config_failed code=players_list_invalid` means the account list has
  an invalid format, an empty or malformed nickname, or a duplicate nickname.
- `event=config_failed code=endpoint_url_invalid`: check the HTTPS sync route.
- `event=config_failed code=tokens_missing_or_invalid`: complete both token
  settings; do not paste their values into a support ticket.
- `event=capture_skipped reason=player_not_allowed` means the signed-in account
  is outside the allowed list. The log omits its nickname.
- `event=capture_failed error_type=...`: possible game inventory API change;
  only a known error type is logged, never a traceback or exception message.
- `event=send_failed kind=http http_status=401` or `403`: possible access,
  pairing or Site authentication issue; check the private tokens locally.
- `event=send_failed kind=tls`, `timeout` or `connection`: inspect clock,
  network connectivity and certificate support.
- `event=send_success`: the Site acknowledged a garage snapshot.
- `event=artwork_read`: counts of artwork found and requested for vehicles,
  items, and crew. No filenames are logged.
- `event=artwork_send_success` or `event=artwork_send_failed`: outcome of a
  separate artwork batch. A failed batch can retry on a later garage capture.

No log line contains credentials, URLs, nicknames, garage contents, HTTP
response bodies or full exception tracebacks. The log contains timestamps,
version, event/status codes, attempt/retry counts and payload sizes only.
It remains on your PC after WoT closes so you can inspect it later.

This code is based on the current decompiled EU client APIs. The active WoT
release may change them; local schema/build tests are not evidence that the
in-game integration works. Verify installation, inventory accuracy (including
field modifications), TLS compatibility and private-site pairing in a client
session before enabling for normal use or publishing a stable Release.

Relevant game modules include `gui/shared/gui_items/Vehicle.py`,
`gui/shared/gui_items/vehicle_equipment.py`,
`gui/veh_post_progression/models/progression.py` and
`gui/shared/gui_items/Tankman.py`.
