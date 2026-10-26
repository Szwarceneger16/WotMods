# Configuration in mods/configs — discovery and sources, 0.2.12

## Contract

`config_path.find_config_path(package_name=None, resmgr=None, cwd=None)` returns
the absolute `mods/configs/grz.sessionstats.json` path in the identified physical game root,
or `None`. The default package name is `grz.sessionstats_<VERSION>.wotmod`.
It creates no files and changes neither installation nor history. The JSON need
not exist for discovery; reading, validation and defaults belong to the loader.
Runtime uses `prepare_config_path` to create a missing central JSON from bounded
legacy adjacent bytes or built-in defaults. It can also copy optional language
overrides into mods/configs. Existing targets always win; old files stay intact.
Only the uniquely identified active package is eligible for migration. Atomic
create-only publication prevents partial destination writes and replacement of
concurrently created files. Failures produce CONFIG_SETUP diagnostics and leave
collection operational. No files are created when discovery is ambiguous.

## Selecting the active installation

1. Resolve `../paths.xml` through `ResMgr.resolveToAbsolutePath`. Require an absolute
   path to an existing physical `paths.xml`.
2. A file confirmed this way is authoritative. Read errors, unsupported structure,
   a missing package or multiple matches produce defaults; do not switch installations.
3. If the resolver provides no physical file, inspect only `appDirectory()`, its
   parent, the working directory and its parent. Their existing `paths.xml` files
   must collectively identify one unambiguous package. Any inspected XML error
   also ends discovery with defaults instead of skipping an unreadable candidate.
4. Select XML `Paths/Path` declarations with `mask="*.wotmod"`. Resolve relative
   paths against the XML directory. Honor `mode="recursive"`; absent/empty mode
   scans only the immediate directory.
5. Match the current package's exact filename to verify the active installation
   and locate its legacy adjacent configuration. The new destination is always
   `mods/configs` relative to the physical XML directory, even when the package
   is in a nested/custom resource root. It does not depend on the client version.

Discovery does not choose the highest `mods` version, search old versions or infer
archive placement from `__file__`. Renaming the package without changing the expected
name selects defaults; the distributed package already has the correct name.

## Read limits and failures

- XML: at most 256 KiB, 4096 elements and 32 package-root declarations.
- Scanning: at most 8192 entries total and eight subdirectory levels. Reaching a
  limit abandons selection even after one match, since an unscanned second copy
  cannot be excluded.
- Symbolic links encountered as scan roots, subdirectories or matching packages
  are skipped. This does not identify every Windows reparse-point type; detection
  is limited to the embedded interpreter's `os.path.islink` support.
- XML supports UTF-8 with optional BOM and ASCII declarations. DTD/ENTITY declarations
  are rejected before parsing.
- `xml.etree.ElementTree` is imported only when XML is read. Its absence remains
  a local configuration failure and does not prevent importing the mod.
- Unicode paths work on Python 2.7 and 3. Native byte paths are considered as UTF-8
  and filesystem encoding, requiring an existing file. Distinct matching decoded
  paths are ambiguous.
- One failed call emits at most one `CONFIG_PATH code=...` entry through
  `grz.sessionstats`, without raw XML, user paths, exception messages or traceback,
  and returns `None`.

Relative package paths may point outside the XML's directory when declared by the
actual `paths.xml`. Discovery respects explicit client roots without adding scans
of other directories or drives.

## Source evidence read on 2026-10-21

Shared `izeberg/wot-src` client-mirror commit:
`5e721e36891c80d8d51a431164960c863641ee63`.
This documents actual implementation, not a stable SDK guarantee.

### Active package root

[sources/paths.xml](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/paths.xml),
blob `60508b70e99ae41f14d145f4d833001cb60fd06c`, declares separate
`res_mods/2.4.1.0` and `mods/2.4.1.0` paths. The latter uses mask `*.wotmod`,
`recursive` mode and resource root `res`. Discovery uses this declaration rather
than the build number.

### Resolving physical paths

[BWUtil.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/BWUtil.py),
blob `c23dc364997687941ddf4ee5e9fee537818e7d56`: `bwResRelativePatch` calls
`ResMgr.resolveToAbsolutePath`, converts the result to Unicode and passes it to a
file function. `bwResRelativeIOOpen` uses this for `io.open`.

[helpers/__init__.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/helpers/__init__.py),
blob `a35e8a97f926c54f39c1cbb37c770684197f1b2b`: the client reads its version file
through resource path `../version.xml`.
[sources/version.xml](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/version.xml),
blob `898de2d92c1f15464d17f416446677ea6c949169`, contains `v.2.4.1.0 #977`.
The repository's `.version_name`, `2.4.1.5493`, is not the mods-directory name.

Using `resolveToAbsolutePath('../paths.xml')` is an inference from these contracts
and file placement. That exact call was not found in client code, so its result
is verified on the physical filesystem and failure uses the bounded fallback above.

### Application directory

[OfflineMode.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/helpers/OfflineMode.py),
blob `368aa61a53e9dfeaac8e300bed23fe88bff17680`, and
[VehicleTelemetry.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client_common/shared_utils/avatar_helpers/VehicleTelemetry.py),
blob `71ca2fbed601d75bef1c5d9b477ac3e1f063b917`, use argument-free
`ResMgr.appDirectory()` for local files. They do not establish that it always
returns the game root, so fallback checks existing XML there and in its parent.

### Virtual paths do not identify archives

[gui/mods/__init__.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/mods/__init__.py),
blob `736f2c29ff76644d6cf705b9011389b6136e391d`, enumerates virtual scripts through
`ResMgr.openSection` and imports modules without passing physical package placement.

[extension_utils.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/extension_utils.py),
blob `4a17a1fb0b5d7b97968f8356ea7f187ed7abb7d4`: `findFirstPathOccurrence` returns
a resource path or an active-extension-prefixed path. It does not return a physical
`.wotmod` directory and is therefore not used for discovery.
