# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 Andrii Andrushchyshyn

import logging

import Event
from frameworks.wulf import ViewModel
from frameworks.wulf.view.array import Array, fillStringsArray
from realm import CURRENT_REALM

# Set up logging configuration
logger = logging.getLogger('OpenWG/Gameface')
logger.setLevel(logging.INFO)

IS_WG = CURRENT_REALM != 'RU'

__all__ = ('gf_mod_inject', 'ModInjectModel', 'on_ready', 'res_id_by_key', 'res_ids_by_mask', 'ModDynAccessor')


class ModInjectModel(ViewModel):
    """ViewModel that provides resources for the JS-side injector."""

    def __init__(self, name, styles=None, scripts=None, modules=None):
        """Initializes the ModInjectModel.

        Args:
            name (str): A unique name of your model used to link it from JS
            styles (list, optional): A list of style URLs for injection.
            scripts (list, optional): A list of script URLs for injection.
            modules (list, optional): A list of script URLs acts as modules for injection.
        """
        self._name = name
        self._styles = Array()
        fillStringsArray(styles or [], self._styles)
        self._scripts = Array()
        fillStringsArray(scripts or [], self._scripts)
        self._modules = Array()
        fillStringsArray(modules or [], self._modules)
        super(ModInjectModel, self).__init__(properties=3, commands=0)

    def _initialize(self):
        """Initializes ViewModel properties."""
        super(ModInjectModel, self)._initialize()
        self._addStringProperty('name', self._name)
        self._addArrayProperty('styles', self._styles)
        self._addArrayProperty('scripts', self._scripts)
        self._addArrayProperty('modules', self._modules)


def gf_mod_inject(model, name, styles=None, scripts=None, modules=None):
    """Adds the inject model as a property to another ViewModel.

    This makes the resource lists available to the JS-side injector.

    Args:
        model (ViewModel): The target ViewModel to which the injector model will be added.
        name (str): A unique name of your model used to link it from JS
        styles (list, optional): A list of style URLs.
        scripts (list, optional): A list of script URLs.
        modules (list, optional): A list of script URLs acts as modules for injection.
    """
    model._addViewModelProperty('ModInjectModel', ModInjectModel(name, styles, scripts, modules))


# WG merges mods res_map natively in C++ and dropped gui.impl.gen_utils,
# so the whole res_map processing only needed on Lesta client.
if IS_WG:
    # Mirrors gui.impl.gen_utils.INVALID_RES_ID, which no longer exists on WG
    INVALID_RES_ID = -1

    def _warn_deprecated_method(name, _seen=set()):
        """Logs a deprecation notice for a method, once per method name.

        Args:
            name (str): Name of the called method to put in the log.
            _seen (set): Method names already logged, used to de-duplicate notices.
        """
        if name not in _seen:
            _seen.add(name)
            logger.warning(
                'openwg_gameface.%s usage is deprecated on WG: res_map modification is handled natively, please refrain from using it and migrate to native R.* accessors',
                name,
            )

    def res_id_by_key(key):
        """Placeholder for the Lesta res_id_by_key on WG client.

        Notifies about deprecation and returns an invalid resID.

        Args:
            key (str): The modID identifier (ignored).

        Returns:
            int: Always INVALID_RES_ID.
        """
        _warn_deprecated_method('res_id_by_key')
        return INVALID_RES_ID

    def res_ids_by_mask(mask):
        """Placeholder for the Lesta res_ids_by_mask on WG client.

        Notifies about deprecation and returns an empty iterator.

        Args:
            mask (str): Substring to match inside item IDs (ignored).

        Returns:
            Iterator[tuple[str, int]]: Always empty.
        """
        _warn_deprecated_method('res_ids_by_mask')
        return iter(())

    def on_ready(callback):
        """Placeholder for the Lesta on_ready on WG client.

        Notifies about deprecation and executes the callback instantly,
        as the native res_map is always ready.

        Args:
            callback (Callable): Function to call instantly.
        """
        _warn_deprecated_method('on_ready')
        return callback()

    class ModDynAccessor(object):
        """Placeholder for the Lesta ModDynAccessor, obsolete on WG client since update 2.4.1.

        Notifies about deprecation and mimics the callable/boolean contract of
        DynAccessor, always resolving to an invalid resID.
        """

        __slots__ = ('__modID',)

        def __init__(self, modID='', resID=INVALID_RES_ID):
            """Initializes the placeholder with a deprecation notice.

            Args:
                modID (str): Identifier of the mod-defined UI resource item (kept, never resolved).
                resID (int): Initial resource ID (ignored, default is INVALID_RES_ID).
            """
            _warn_deprecated_method('ModDynAccessor')
            self.__modID = modID

        def __call__(self):
            """Returns the resource ID, always INVALID_RES_ID on WG."""
            return INVALID_RES_ID

        def __bool__(self):
            """False, matching DynAccessor truthiness for an invalid resID."""
            return self() >= 0

        __nonzero__ = __bool__
else:
    import collections
    import os
    import zipfile
    import json

    import BigWorld
    import ResMgr
    import LGC

    from gui.impl.gen_utils import DynAccessor, INVALID_RES_ID

    # Paths to the resource map file
    RES_MAP_FILE_PATH = 'gui/unbound/gen/res_map.json'
    # Paths to the configs (JSON files in file system and game VFS)
    MOD_CONFIGS_PATH = 'mods/configs/res_map'
    # Name of restart flag file
    RESTART_FLAG_FILE = 'res_map_restart'

    class ResMapManager:
        """Manager for building, validating, and applying custom resource map."""

        def __init__(self):
            """Initializes the ResMapManager.

            Sets up the validation event, locates config files from file system and game VFS,
            builds and validates the resource map, and triggers client restart if needed.
            """

            # Event triggered when the resource map is validated
            self.onResMapValidated = Event.SafeEvent()

            # Flag indicating if the resource map is valid
            self.isResMapValidated = False

            # Maps modID to UiResourceManager itemID
            self.items_mapping = {}

            # Locate the res_mods directory
            res_mods_dir = None
            for path in ResMgr.openSection('../paths.xml')['Paths'].values():
                if os.path.isdir(path.asString):
                    mod_folder_path = path.asString.replace('./', '')
                    if not os.path.isdir(mod_folder_path):
                        continue
                    res_mods_dir = mod_folder_path
                    break

            if not res_mods_dir:
                logger.error('res_mods directory not found!')
                return
            # Path where to save the res_map.json
            res_map_file_path = os.path.normpath(os.path.join(res_mods_dir, RES_MAP_FILE_PATH))

            # Get all available configs from both real FS and game VFS
            configs_fs = list(self.config_files_in_real_fs())
            configs_vfs = list(self.config_files_in_game_vfs(configs_fs))

            # If we don't have mod configs
            if not configs_fs and not configs_vfs:
                # Try to remove existing res_map.json if it exists and restart game
                if os.path.isfile(res_map_file_path):
                    os.remove(res_map_file_path)
                    self.restart_client()
                return

            # Attempt to build the resource map with modded items
            try:
                resource_map = self._build_resource_map(configs_fs, configs_vfs)
                if not resource_map:
                    logger.error('Cannot build modded res_map')
                    return
            except Exception:
                logger.exception('Failed to build res_map.json')
                return

            try:
                # Validate the resource map and determine if a client restart is needed
                client_restarting = self._validate_resource_map(resource_map, res_map_file_path)
                if client_restarting:
                    logger.info('Stored new res_map.json, restarting client now')
                    return

            except Exception:
                logger.exception('Failed to validate res_map.json')
                return

            # If res_map.json is valid, set the validation flag and notify all subscribers
            self.isResMapValidated = True
            self.onResMapValidated()

            # If the restart flag file exists, remove it
            if os.path.isfile(RESTART_FLAG_FILE):
                os.remove(RESTART_FLAG_FILE)

        def _build_resource_map(self, configs_fs, configs_vfs):
            """Builds the resource map by merging original resource map items and mod items.

            Args:
                configs_fs (list): Config files found in the real filesystem.
                configs_vfs (list): Config files found in the game VFS.

            Returns:
                dict or None: Final merged resource map dictionary or None on failure.
            """

            # List of GUI package directories containing potential res_map.json
            packages = ['res/packages/%s' % x for x in os.listdir('res/packages') if x.startswith('gui-part')]

            resource_map_data = None
            for package in packages:
                resource_map_data = self.read_file_from_package(package, RES_MAP_FILE_PATH)
                if resource_map_data:
                    break

            if not resource_map_data:
                logger.error('Cannot find res_map.json in game GUI packages %s', packages)
                return None

            try:
                # Fix trailing commas in the game JSON data
                resource_map_data = resource_map_data.replace(',}', '}')
                resource_map = json.loads(resource_map_data)
            except ValueError:
                logger.exception('Failed to deserialize res_map.json')
                return None

            # Process all config files in real FS if any
            for file_path in configs_fs:
                try:
                    with open(file_path, 'r') as file_handle:
                        mod_items = json.load(file_handle)
                        if mod_items:
                            self._add_mod_items_to_resource_map(mod_items, resource_map)
                except Exception:
                    logger.exception('Failed to read mod config file from FS (%s)', file_path)
                    continue

            # Process all config files in game VFS if any
            for file_path in configs_vfs:
                try:
                    vfs_file = ResMgr.openSection(file_path)
                    if vfs_file is not None and ResMgr.isFile(file_path):
                        mod_items = json.loads(vfs_file.asBinary)
                        if mod_items:
                            self._add_mod_items_to_resource_map(mod_items, resource_map)
                except Exception:
                    logger.exception('Failed to read mod config file from VFS (%s)', file_path)
                    continue

            return resource_map

        def _add_mod_items_to_resource_map(self, mod_items, resource_map):
            """Adds mod items to the resource map.

            Args:
                mod_items (list): List of dictionary items with metadata and itemID.
                resource_map (dict): Existing resource map to be modified.
            """

            # Process each item in the mod configuration file
            for item in mod_items:
                if 'itemID' not in item:
                    logger.error('Item is missing mandatory key [itemID]')
                    continue

                item_id = item['itemID']
                del item['itemID']

                if item_id in self.items_mapping:
                    logger.error('Item with key %s already exists, skipping', item_id)
                    continue

                # Generate a unique numeric ID for the item and store its linkage
                numeric_item_id = len(resource_map)
                self.items_mapping[item_id] = numeric_item_id

                # Generate a hexadecimal ID for the item and add it to the resource map
                hex_item_id = hex(numeric_item_id)[2:]
                resource_map[hex_item_id] = item

        def _validate_resource_map(self, resource_map, res_map_file_path):
            """Validates and saves the resource map to res_mods folder.

            Args:
                resource_map (dict): The combined resource map.
                res_map_file_path (str): Path where the resource map should be saved.

            Returns:
                bool: True if client needs to be restarted, otherwise False.
            """

            # Sort the resource map by item IDs in hexadecimal format
            sorted_data = sorted(resource_map.items(), key=lambda x: int(x[0], 16))
            ordered_dict = collections.OrderedDict(sorted_data)

            # Convert the sorted resource map to a JSON string
            latest_file_data = json.dumps(ordered_dict, ensure_ascii=False, separators=(',', ':'))

            # Determine the path to save the resource map
            res_map_folder = os.path.dirname(res_map_file_path)
            if not os.path.isdir(res_map_folder):
                os.makedirs(res_map_folder)

            # Compare the existing resource map with the new one to check for changes
            old_file_data = None
            file_exists = os.path.isfile(res_map_file_path)

            if file_exists:
                with open(res_map_file_path, 'r') as file_handle:
                    old_file_data = file_handle.read()

            if not file_exists or old_file_data != latest_file_data:
                with open(res_map_file_path, 'w') as file_handle:
                    file_handle.write(latest_file_data)
                return self.restart_client()
            return False

        def restart_client(self):
            """Triggers client restart if it has not been restarted before by as.

            Returns:
                bool: True if restart was triggered, False otherwise.
            """
            try:
                if os.path.isfile(RESTART_FLAG_FILE):
                    return False
                with open(RESTART_FLAG_FILE, 'w') as file_handle:
                    file_handle.write('')
            except Exception:
                logger.error('Cant write RESTART_FLAG_FILE')

            LGC.notifyRestart()
            BigWorld.worldDrawEnabled(False)
            BigWorld.restartGame()
            return True

        @staticmethod
        def read_file_from_package(package_path, file_path):
            """Reads a file from a game package.

            Args:
                package_path (str): Path to the .pkg file.
                file_path (str): Relative file path inside the package.

            Returns:
                str or None: File contents if found, else None.
            """
            if not os.path.isfile(package_path):
                return
            with zipfile.ZipFile(package_path) as zip_file:
                file_path_lower = file_path.lower()
                for zip_info in zip_file.filelist:
                    if file_path_lower == zip_info.filename.lower():
                        return zip_file.read(zip_info.filename)

        @staticmethod
        def config_files_in_real_fs():
            """Yields mod config files from the real file system.

            Yields:
                str: Full path to each JSON config file found.
            """
            if os.path.isdir(MOD_CONFIGS_PATH):
                for file_name in os.listdir(MOD_CONFIGS_PATH):
                    if file_name.endswith('.json'):
                        file_path = os.path.normpath(os.path.join(MOD_CONFIGS_PATH, file_name)).replace('\\', '/')
                        if os.path.isfile(file_path):
                            yield file_path

        @staticmethod
        def config_files_in_game_vfs(config_files=[]):
            """Yields mod config files from the game VFS (virtual filesystem).

            Args:
                config_files (list, optional): Already-known config file names.

            Yields:
                str: VFS path to each new config file found.
            """
            # all VFS paths is lower case so do same on all realfs paths
            config_files = list(x.lower() for x in config_files)
            vfs_dir = ResMgr.openSection(MOD_CONFIGS_PATH)
            if vfs_dir is not None and ResMgr.isDir(MOD_CONFIGS_PATH):
                for vfs_item in vfs_dir.keys():
                    file_path = os.path.normpath(os.path.join(MOD_CONFIGS_PATH, vfs_item.lower())).replace('\\', '/')
                    if file_path not in config_files:
                        if ResMgr.isFile(file_path):
                            config_files.append(file_path)
                            yield file_path

    manager = ResMapManager()

    def res_ids_by_mask(mask):
        """Finds all modIDs that contain the given substring.

        Args:
            mask (str): Substring to match inside item IDs.

        Yields:
            tuple[str, int]: (modID, UiResourceManager itemID)
        """
        for key in manager.items_mapping:
            if mask in key:
                yield key, manager.items_mapping[key]


    def res_id_by_key(key):
        """Retrieves the UiResourceManager itemID for a specific modID.

        Args:
            key (str): The modID identifier.

        Returns:
            int or INVALID_RES_ID: Corresponding UiResourceManager itemID or INVALID_RES_ID if not found.
        """
        return manager.items_mapping.get(key, INVALID_RES_ID)


    def on_ready(callback):
        """Executes a callback when the res_map is validated.

        Args:
            callback (Callable): Function to call once the res_map is validated.
        """
        if manager.isResMapValidated:
            return callback()
        else:
            manager.onResMapValidated += callback


    class ModDynAccessor(DynAccessor):
        """Custom dynamic accessor for accessing mod UiResourceManager itemID.

        Extends DynAccessor to defer setting resId until the res_map is validated.
        """

        __slots__ = ('__modID',)

        def __init__(self, modID='', resID=INVALID_RES_ID):
            """Initializes the ModDynAccessor with a given modID and optional resID.

            Args:
                modID (str): Identifier of the mod-defined UI resource item.
                resID (int): Initial resource ID (default is INVALID_RES_ID).
            """
            super(ModDynAccessor, self).__init__(resID)
            self.__modID = modID

            # Register a callback to set the actual resource ID once the res_map is ready
            on_ready(self._setResID)

        def _setResID(self):
            """Sets the internal resId once the res_map has been validated.

            This method retrieves the correct UiResourceManager itemID for the stored modID
            and assigns it to the base DynAccessor's internal resId field.
            """
            self._DynAccessor__resId = res_id_by_key(self.__modID)
