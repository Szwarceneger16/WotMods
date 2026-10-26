# -*- coding: utf-8 -*-
"""Small version-sensitive bridge to WoT 2.4.1, isolated from the stats engine.

References (read 2026-10-20):
  izeberg/wot-src @ .version_name=2.4.1.5493:
    sources/res/scripts/client/PlayerEvents.py
    sources/res/scripts/client/gui/InputHandler.py
    sources/res/scripts/client/gui/battle_results/service.py
    sources/res/scripts/client/gui/battle_results/stats_ctrl.py
  wotstat/wotstat-analytics:
    WOTSTAT/res/scripts/client/gui/mods/wot_stat/logger/loggers/onBattleResultLogger.py
    (battle_result_cache_checker): result-cache callback code > 0.
No game networking, account mutation, automatic input or executable download.
"""
from __future__ import absolute_import, unicode_literals

from .localization import Localizer, message

import io
import json
import logging
import os
import sys
import time
import uuid

from . import VERSION
from .normalize import arena_start, normalize_result, _number, _integer, text_type
from .monitor import ResultMonitor
from .storage import check_json_depth

LOG = logging.getLogger('grz.sessionstats')
LAUNCH_ID = uuid.uuid4().hex
LAUNCH_STARTED_AT = time.time()
TICK_SECONDS = 5.0
MAX_EXPECTED_BYTES = 8 * 1024 * 1024
DEFAULT_LOCAL_CONFIG = {'hotkey': 'CTRL+F10', 'footer_button': True}


def _optional_attr(owner, name):
    """Isolate optional native metadata, including temporarily failing getters."""
    try:
        return getattr(owner, name, None)
    except Exception:
        return None


def _filesystem_text(value):
    # WoT uses Python 2.7: environment values can be filesystem-encoded bytes.
    # Decode before joining with Unicode paths (e.g. a Polish Windows profile).
    if isinstance(value, bytes) and not isinstance(value, text_type):
        return value.decode(sys.getfilesystemencoding() or 'utf-8')
    return value


def resolve_data_dir(bigworld=None, environ=None):
    """Version-independent local data only; never touch the client's preferences."""
    environ = os.environ if environ is None else environ
    base = environ.get('APPDATA') or environ.get('LOCALAPPDATA')
    if base:
        return os.path.join(os.path.normpath(_filesystem_text(base)), 'grz_wot_session_stats')
    if bigworld is not None:
        getter = getattr(bigworld, 'wg_getPreferencesFilePath', None)
        if callable(getter):
            path = _filesystem_text(getter())
            if path and os.path.isabs(path):
                return os.path.join(os.path.dirname(path), 'grz_session_stats')
    base = environ.get('USERPROFILE')
    if base:
        return os.path.join(_filesystem_text(base), 'AppData', 'Roaming', 'grz_wot_session_stats')
    raise RuntimeError(message('runtime.data_dir'))


def _load_json_file(path):
    with io.open(path, 'rb') as handle:
        raw = handle.read(MAX_EXPECTED_BYTES + 1)
    if len(raw) > MAX_EXPECTED_BYTES:
        raise ValueError('JSON file exceeds size limit')
    try:
        value = json.loads(raw.decode('utf-8-sig'))
        check_json_depth(value)
        return value
    except RuntimeError:
        # Shared external-file boundary: decoder recursion must use each
        # caller's invalid-file fallback on both Python 2.7 and Python 3.
        raise ValueError('JSON decoder exceeded its nesting limit')


def _looks_like_expected(table):
    if not isinstance(table, dict):
        return False
    rows = table.get('data')
    if not isinstance(rows, list) or not rows:
        return False
    needed = ('IDNum', 'expDamage', 'expFrag', 'expSpot', 'expDef', 'expWinRate')
    try:
        return all(isinstance(row, dict) and all(key in row for key in needed)
                   and _integer(row['IDNum']) is not None
                   and all(_number(row[key]) is not None and row[key] > 0
                           for key in needed[1:]) for row in rows)
    except (TypeError, ValueError, OverflowError):
        return False


class GameAPI(object):
    """All imports with patch-sensitive paths live here and in views/footer."""

    def __init__(self):
        import BigWorld
        import BattleReplay
        from constants import ARENA_BONUS_TYPE, AUTH_REALM
        self.bw = BigWorld
        self.replays = BattleReplay
        self.events = None
        self.random_bonus_type = ARENA_BONUS_TYPE.REGULAR
        self.region = str(AUTH_REALM)
        self.keys = None
        self.input = None
        self.results_service = None
        self.event_bus = None
        self.bonus_event = None
        try:
            from PlayerEvents import g_playerEvents
            self.events = g_playerEvents
        except Exception:
            LOG.warning('Player events unavailable; result cache polling remains enabled.')
        # Keyboard/UI adapters are optional. Their removal must not disable
        # account identity, replay exclusion or the result collector.
        try:
            import Keys
            self.keys = Keys
        except Exception:
            LOG.warning('Keyboard constants unavailable; statistics collection remains enabled.')
        try:
            from gui import InputHandler
            self.input = InputHandler.g_instance
        except Exception:
            LOG.warning('Keyboard events unavailable; statistics collection remains enabled.')
        try:
            from helpers import dependency
            from skeletons.gui.battle_results import IBattleResultsService
            self.results_service = dependency.instance(IBattleResultsService)
        except Exception:
            LOG.warning('Posted-results integration unavailable; raw result events remain enabled.')
        try:
            from gui.shared import g_eventBus, events
            self.event_bus = g_eventBus
            self.bonus_event = events.LobbySimpleEvent.PREMIUM_XP_BONUS_CHANGED
        except Exception:
            LOG.warning('Post-battle XP bonus event unavailable; use Refresh after a bonus.')

    def player(self):
        return self.bw.player()

    def is_replay(self):
        return bool(self.replays.isPlaying())

    def client_language(self):
        from helpers import getClientLanguage
        return getClientLanguage()

    def outcome_messages(self):
        from helpers import i18n
        return dict(('outcome.' + outcome, i18n.makeString('#battle_results:status/' + status))
                    for outcome, status in (('win', 'win'), ('loss', 'lose'), ('draw', 'tie')))

    def in_battle(self):
        player = self.player()
        return player is not None and getattr(player, 'arena', None) is not None

    def account_dbid(self):
        player = self.player()
        if player is None:
            return None
        value = getattr(player, 'databaseID', None)
        if value:
            return int(value)
        try:
            from account_helpers import getAccountDatabaseID
            value = getAccountDatabaseID()
        except (ImportError, AttributeError, RuntimeError):
            value = None
        if not value and getattr(player, 'arena', None) is not None:
            record = player.arena.vehicles.get(getattr(player, 'playerVehicleID', None), {})
            value = record.get('accountDBID')
        return int(value) if value else None

    def battle_context(self):
        player = self.player()
        arena = getattr(player, 'arena', None)
        if arena is None or arena.bonusType != self.random_bonus_type:
            return None
        arena_id = getattr(player, 'arenaUniqueID', None)
        if not arena_id:
            return None
        vehicle_type = None
        try:
            vehicle = arena.vehicles.get(getattr(player, 'playerVehicleID', None), {})
            vehicle_type = _optional_attr(vehicle.get('vehicleType'), 'type')
        except Exception:
            pass
        # The arena identity and random mode are already verified. Optional
        # roster/descriptor/map data can arrive later or fail independently;
        # none may prevent the durable beginning used for result recovery.
        map_type = _optional_attr(arena, 'arenaType')
        context = {
            'arena_id': str(arena_id), 'started_at': arena_start(arena_id),
            'account_dbid': self.account_dbid(),
            'vehicle_id': _optional_attr(vehicle_type, 'compactDescr'),
            'vehicle_name': _optional_attr(vehicle_type, 'shortUserString') or
                            _optional_attr(vehicle_type, 'userString'),
            'vehicle_tier': _optional_attr(vehicle_type, 'level'),
            'vehicle_type': _optional_attr(vehicle_type, 'classTag'),
            'map_id': _optional_attr(map_type, 'geometryName'),
            'map_name': _optional_attr(map_type, 'name'), 'mode': 'random',
        }
        return context

    def vehicle_info(self, compact):
        from items.vehicles import getVehicleType
        vehicle = getVehicleType(compact)
        return {'name': getattr(vehicle, 'shortUserString', None) or vehicle.userString,
                'tier': vehicle.level, 'type': vehicle.classTag}

    def map_info(self, arena_type_id):
        import ArenaType
        arena = ArenaType.g_cache.get(arena_type_id)
        if arena is None:
            return {}
        return {'id': arena.geometryName, 'name': arena.name}

    def schedule(self, seconds, callback):
        return self.bw.callback(seconds, callback)

    def cancel(self, callback_id):
        self.bw.cancelCallback(callback_id)

    def key_down(self, key):
        return bool(self.bw.isKeyDown(key))

    def request_result(self, arena_id, callback):
        player = self.player()
        cache = getattr(player, 'battleResultsCache', None)
        if cache is None:
            return False
        cache.get(int(arena_id), callback)
        return True

    def result_cache(self):
        return getattr(self.player(), 'battleResultsCache', None)

    def result_status(self, code):
        import AccountCommands
        for name, status in (('RES_COOLDOWN', 'cooldown'),
                             ('RES_RATE_LIMIT_COOLDOWN', 'rate_limited'),
                             ('RES_NON_PLAYER', 'not_ready'),
                             ('RES_CENTER_DISCONNECTED', 'disconnected'),
                             ('RES_NOT_AVAILABLE', 'unavailable'),
                             ('RES_WRONG_ARGS', 'rejected')):
            if getattr(AccountCommands, name, None) == code:
                return status
        return 'not_returned'

    def posted_bundle(self, arena_id):
        service = self.results_service
        if service is None or not service.areResultsPosted(int(arena_id)):
            return None
        controller = service.getStatsCtrl(int(arena_id))
        return controller.getResults() if controller is not None else None

    def load_expected(self, data_dir):
        override = os.path.join(data_dir, 'wn8exp.json')
        if os.path.isfile(override):
            try:
                table = _load_json_file(override)
                if not _looks_like_expected(table):
                    raise ValueError('invalid expected-table schema')
                return table
            except (IOError, OSError, ValueError, TypeError):
                LOG.warning('Invalid local WN8 expected table; bundled table will be used.')
        import ResMgr
        section = ResMgr.openSection('grz_session_stats/wn8exp.json')
        if section is None:
            raise RuntimeError(message('runtime.wn8_missing'))
        raw = section.asBinary
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8-sig')
        table = json.loads(raw)
        check_json_depth(table)
        if not _looks_like_expected(table):
            raise ValueError(message('runtime.wn8_invalid'))
        return table

    def notify(self, message):
        try:
            from gui import SystemMessages
            # Catalogs contain plain text. Native notifications support markup,
            # so escape at this final boundary, including user-edited messages.
            message = message.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            SystemMessages.pushMessage(message, type=SystemMessages.SM_TYPE.Warning)
            return True
        except Exception:
            LOG.error('Could not display the local mod status message.')
            return False


class Runtime(object):
    def __init__(self, api=None, service_factory=None, data_dir=None,
                 expected_table=None, now=None, window=None, footer_installer=None,
                 appearance_path=None, installation_dir=None, deferred_loading=True):
        self.api = api
        self.service_factory = service_factory
        self._deferred_loading = deferred_loading
        self._load_id = None
        self._load_cursor = 0
        self.data_dir = data_dir
        self.expected_table = expected_table
        self.now = now or time.time
        self.window = window
        self.footer_installer = footer_installer
        self.footer_handle = None
        self._appearance_override_path = appearance_path
        self.appearance_path = None
        self._presentation = {'panel_css': '', 'footer_css': '', 'scroll_speed': 1.0}
        self.services = {}
        self.active_service = None
        self.active_key = None
        self.contexts = {}
        self.recent = {}
        self.retries = {}
        self.inflight = {}
        self.subscriptions = []
        self._tick_id = None
        self._bonus_callback_id = None
        self.running = False
        self.last_error = None
        self._hotkey_held = False
        self.config = dict(DEFAULT_LOCAL_CONFIG)
        self._hotkey = None
        self.compatibility_warnings = {}
        self._diagnostics = set()
        self._lifecycle = None
        self._bonus_subscription = None
        self._bonus_account_key = None
        self._processing = {}
        self._observed_arenas = set()
        self._started_at = None
        self._cache_observer = None
        self._recovery_states = {}
        self._instance_tab_enabled = False
        self._instance_session = None
        self._installation_dir = installation_dir
        self._footer_activity = None
        self._log_handle = None
        self.log_path = None
        self._log_error = None
        self._log_notice_sent = False
        self._log_notice_after = 0
        self.monitor = ResultMonitor(self.now)
        self._localizer = Localizer()

    def _notify(self, value):
        return self.api.notify(self._localizer.translate(value))

    def _start_log(self):
        if self._log_handle is not None or self.data_dir is None:
            return
        try:
            from .diagnostics import start_logging
            self._log_handle = start_logging(self.data_dir)
            self.log_path = self._log_handle.path
            self._log_error = self._log_handle.error
        except Exception:
            self._log_error = message('runtime.log_unavailable')
            LOG.exception('Could not initialize the dedicated mod log.')

    def _service_diagnostics(self):
        try:
            self._service_diagnostics_impl()
        except Exception:
            self._warn_once('diagnostics',
                            message('runtime.diagnostics'),
                            exception=True)

    def _service_diagnostics_impl(self):
        handle = self._log_handle
        if handle is not None:
            handle.flush()
            self._log_error = handle.error if not handle.ok else None
        self.monitor.log_path = self.log_path if handle is not None and handle.ok else None
        if self._log_error:
            self._warn_once('logging',
                            message('runtime.log_failed'))
        else:
            self.compatibility_warnings.pop('logging', None)
        if (not self.running or self.active_service is None or
                self.api.is_replay() or self.api.in_battle()):
            return
        if self._log_error and not self._log_notice_sent and self.now() >= self._log_notice_after:
            self._log_notice_after = self.now() + 60
            try:
                self._log_notice_sent = self._notify(
                    message('runtime.log_notice')) is not False
            except Exception:
                pass
        self.monitor.flush_notice(self._notify, escape=False)

    def _pending_activity(self):
        if not self.running or self.active_service is None or self.api.is_replay():
            return set(), set()
        pending = set(str(value) for value in self.active_service.pending_arena_ids())
        # Restored incomplete records remain recoverable ledger data, but do
        # not imply that this client has played a battle and is still waiting.
        waiting = set(arena_id for arena_id in pending
                      if (self.active_key, arena_id) in self._observed_arenas)
        return pending, waiting

    def activity_status(self):
        if not self.running or self.active_service is None or self.api.is_replay():
            return (0, False)
        unused_pending, waiting = self._pending_activity()
        # A battle still being played is not a result waiting in the garage.
        # Leaving it early makes it pending until WoT delivers the final result.
        if self.api.in_battle():
            context = self.api.battle_context()
            if isinstance(context, dict):
                waiting.discard(str(context.get('arena_id', '')))
        processing = (getattr(self.active_service, 'loading', False) or
                      self._processing.get(self.active_key, 0) > 0 or
                      (self._bonus_callback_id is not None and self._bonus_account_key == self.active_key))
        return (len(waiting), bool(processing))

    def _publish_activity(self):
        self._publish_appearance()
        try:
            state = self.activity_status()
            handle = self.footer_handle
            setter = getattr(handle, 'set_activity', None)
            if not callable(setter):
                return
            marker = (id(handle), state)
            # The child model deduplicates actual native updates. Reapplying a
            # state lets a child recover after one transient model-write error.
            setter(*state)
            if marker != self._footer_activity:
                self._footer_activity = marker
                LOG.info('Result activity: pending=%s processing=%s', state[0], state[1])
        except Exception:
            self._warn_once('footer:activity', 'Pending-result indicator is unavailable.',
                            exception=True, visible=False)

    def _client_language(self):
        try:
            getter = getattr(self.api, 'client_language', None)
            return getter() if callable(getter) else None
        except Exception:
            LOG.warning('I18N client language unavailable; using configured or English translations.')
            return None

    def _outcome_messages(self):
        try:
            getter = getattr(self.api, 'outcome_messages', None)
            return getter() if callable(getter) else None
        except Exception:
            # Optional game labels must not disable configuration or collection.
            return None

    def _load_appearance(self):
        # Read only on start, opening the panel or explicit Refresh. Never do
        # file I/O in a render/animation frame or on every result-polling tick.
        try:
            from .appearance import load_config, build_presentation
            from .config_path import prepare_config_path
            path = self._appearance_override_path
            if path is None:
                path = prepare_config_path()
            self.appearance_path = path
            config = load_config(path)
            self._localizer = Localizer(config['language'],
                                        client_language=self._client_language(),
                                        native_messages=self._outcome_messages())
            self._presentation = build_presentation(config)
            self._instance_tab_enabled = config['sessions']['instance_tab']
        except Exception:
            # An unavailable optional configuration layer cannot stop result
            # collection. Static styles and the original wheel step remain.
            self._presentation = {'panel_css': '', 'footer_css': '', 'scroll_speed': 1.0}
            self._instance_tab_enabled = False
            self._localizer = Localizer('auto', client_language=self._client_language())
            LOG.exception('CONFIG appearance unavailable; built-in styles and scrolling remain active.')
        if not self._instance_tab_enabled:
            self.compatibility_warnings.pop('installation:identity', None)
        if self.running and self.active_service is not None:
            self._ensure_installation_session()
        self._publish_appearance()

    def _publish_appearance(self):
        if not self.running:
            return
        try:
            language_setter = getattr(self.footer_handle, 'set_language', None)
            if callable(language_setter):
                language_setter(self._localizer.footer_labels())
        except Exception:
            self._warn_once('footer:language', 'I18N footer language update unavailable.',
                            exception=True, visible=False)
        try:
            setter = getattr(self.footer_handle, 'set_appearance', None)
            if callable(setter):
                # The native child deduplicates successful writes. Reapplying
                # permits recovery after a transient model transaction error.
                setter(self._presentation.get('footer_css', ''))
        except Exception:
            self._warn_once('footer:appearance', 'CONFIG footer appearance update unavailable.',
                            exception=True, visible=False)

    def _warn_once(self, key, message, exception=False, visible=True):
        if visible:
            self.compatibility_warnings[key] = message
        if key not in self._diagnostics:
            self._diagnostics.add(key)
            LOG.warning('Compatibility [%s]: %s', key, message, exc_info=exception)

    def _guard(self, callback, name):
        # A client may reject unsubscribe/cancel after an API change. Keep old
        # handlers inert even if this Runtime is stopped and started again.
        lifecycle = self._lifecycle

        def guarded(*args, **kwargs):
            if not guarded._grz_enabled or not self.running or self._lifecycle is not lifecycle:
                return
            try:
                return callback(*args, **kwargs)
            except Exception:
                self._warn_once('callback:' + name,
                                message('runtime.events'),
                                exception=True)
                if name in ('onBattleResultsReceived', 'onResultPosted', 'bonus', 'bonus_timer'):
                    self.monitor.fault('callback_contract', name, 'supported result callback', 'exception')
                    self._service_diagnostics()
        guarded._grz_enabled = True
        return guarded

    def _ensure_window(self):
        if self.window is None:
            try:
                from .views import StatsWindow
                self.window = StatsWindow(self.snapshot, self.on_action)
            except Exception:
                self._warn_once('window:init',
                                message('runtime.panel'),
                                exception=True)
                return False
        self.compatibility_warnings.pop('window:init', None)
        return True

    def _window_call(self, method, *args):
        if self.window is None:
            return False
        try:
            result = getattr(self.window, method)(*args)
            self.compatibility_warnings.pop('window:' + method, None)
            return result
        except Exception:
            self._warn_once('window:' + method,
                            message('runtime.panel_update'),
                            exception=True)
            return False

    def _retire_footer(self):
        handle = self.footer_handle
        if handle is None:
            return True
        try:
            if handle.uninstall() is False:
                return False
        except Exception:
            self._warn_once('footer:stop', 'Could not remove optional footer integration.',
                            exception=True, visible=False)
            return False
        self.footer_handle = None
        return True

    def _schedule_tick(self):
        if self.running and self._tick_id is None:
            callback = self._guard(self._tick, 'tick')
            try:
                self._tick_id = self.api.schedule(TICK_SECONDS, callback)
                self.compatibility_warnings.pop('timer:results', None)
            except Exception:
                callback._grz_enabled = False
                self._warn_once('timer:results',
                                message('runtime.polling'),
                                exception=True)

    def start(self):
        if self.running:
            return
        if self.data_dir is None:
            try:
                self.data_dir = resolve_data_dir()
            except RuntimeError:
                pass
        self._start_log()
        self.api = self.api or GameAPI()
        self.services = dict((key, value) for key, value in self.services.items() if not getattr(value, '_closed', False))
        if self.active_key not in self.services:
            self.active_key, self.active_service = None, None
        if self._instance_session and getattr(self._instance_session.service, '_closed', False):
            self._instance_session = None
        if self.service_factory is None:
            from .core import StatsService
            self.service_factory = lambda *args, **kwargs: StatsService(
                *args, deferred=self._deferred_loading, **kwargs)
        if self.data_dir is None:
            self.data_dir = resolve_data_dir(self.api.bw)
            self._start_log()
        self._load_appearance()
        # Each lifecycle starts from defaults; a rejected replacement file
        # must not silently retain preferences from an earlier start.
        self.config = dict(DEFAULT_LOCAL_CONFIG)
        try:
            cfg_file = os.path.join(self.data_dir, 'config.json')
            if os.path.isfile(cfg_file):
                cfg = _load_json_file(cfg_file)
                if not isinstance(cfg, dict):
                    raise ValueError('invalid local configuration root')
                if 'hotkey' in cfg:
                    if isinstance(cfg['hotkey'], text_type) and len(cfg['hotkey']) <= 64:
                        self.config['hotkey'] = cfg['hotkey']
                    else:
                        LOG.warning('Invalid local hotkey preference; default will be used.')
                if 'footer_button' in cfg:
                    if type(cfg['footer_button']) is bool:
                        self.config['footer_button'] = cfg['footer_button']
                    else:
                        LOG.warning('Invalid local footer preference; default will be used.')
        except (IOError, OSError, ValueError, TypeError):
            LOG.warning('Invalid local configuration; defaults will be used.')
        if self.expected_table is None:
            try:
                self.expected_table = self.api.load_expected(self.data_dir)
            except Exception:
                self.expected_table = {}
                self.last_error = message('runtime.wn8_load')
                LOG.exception('WN8 table load failed.')
        self.running = True
        self._lifecycle = object()
        self._started_at = self.now()
        self._observed_arenas.clear()
        self._recovery_states.clear()
        self.retries.clear()
        self.compatibility_warnings.clear()
        self._diagnostics.clear()
        self._hotkey_held = False
        self._processing.clear()
        self._footer_activity = None
        self._bonus_account_key = None
        self._log_notice_sent = False
        self._log_notice_after = 0
        self.monitor = ResultMonitor(self.now, self.log_path)
        self._hotkey = self._parse_hotkey(self.config['hotkey'])
        self._ensure_window()
        handlers = (
            ('onAccountBecomePlayer', self._on_account),
            ('onAccountShowGUI', self._on_account),
            ('onClientSynchronize', self._on_account),
            ('onAvatarReady', self._on_avatar),
            ('onAvatarBecomePlayer', self._close_for_battle),
            ('onAccountBecomeNonPlayer', self._close_for_battle),
            ('onBattleResultsReceived', self._on_results),
        )
        player_events = getattr(self.api, 'events', None)
        raw_results = False
        for name, handler in handlers:
            ready = self._subscribe(getattr(player_events, name, None), handler, name)
            if name == 'onBattleResultsReceived':
                raw_results = ready
        if not raw_results:
            self._warn_once('results:raw',
                            message('runtime.direct'))
        input_handler = getattr(self.api, 'input', None)
        key_down = key_up = False
        if self._hotkey is not None:
            key_down = self._subscribe(getattr(input_handler, 'onKeyDown', None), self._on_key_down, 'onKeyDown')
            key_up = self._subscribe(getattr(input_handler, 'onKeyUp', None), self._on_key_up, 'onKeyUp')
        if not key_down or not key_up:
            self._hotkey = None
            self._warn_once('keyboard', message('runtime.hotkey'))
        service = getattr(self.api, 'results_service', None)
        posted_results = self._subscribe(getattr(service, 'onResultPosted', None), self._on_posted, 'onResultPosted', optional=True)
        if not posted_results:
            self._warn_once('results:posted',
                            message('runtime.posted'))
        if service is None:
            self._warn_once('results:bonus',
                            message('runtime.bonus'))
        bus = getattr(self.api, 'event_bus', None)
        bonus_event = getattr(self.api, 'bonus_event', None)
        bonus_callback = self._guard(self._on_bonus, 'bonus')
        if bus is not None and bonus_event is not None:
            try:
                bus.addListener(bonus_event, bonus_callback)
                self._bonus_subscription = (bus, bonus_event, bonus_callback)
            except Exception:
                bonus_callback._grz_enabled = False
                try:
                    bus.removeListener(bonus_event, bonus_callback)
                except Exception:
                    pass
                self._warn_once('event:bonus',
                                message('runtime.bonus_refresh'),
                                exception=True)
        else:
            self._warn_once('event:bonus',
                            message('runtime.bonus_refresh'))
        footer_released = self._retire_footer()
        if footer_released and self.config.get('footer_button', True):
            try:
                if self.footer_installer is None:
                    from .footer import install
                    self.footer_installer = install
                self.footer_handle = self.footer_installer(self.open_window)
                if self.footer_handle is None:
                    LOG.warning('Footer button unavailable; configured keyboard shortcut remains active.')
            except Exception:
                LOG.exception('Footer button unavailable; configured keyboard shortcut remains active.')
        self._on_account()
        self._guard(self._on_avatar, 'initial_arena')()
        self._publish_activity()
        self._service_diagnostics()
        LOG.info('GRZ Session Stats %s initialized; target WoT PC EU 2.4.1.', VERSION)

    def _subscribe(self, event, callback, name, optional=False):
        if event is None:
            if not optional:
                self._warn_once('subscribe:' + name, 'Client event unavailable: ' + name, visible=False)
            return False
        guarded = self._guard(callback, name)
        try:
            event += guarded
        except Exception:
            guarded._grz_enabled = False
            try:
                event -= guarded
            except Exception:
                pass
            self._warn_once('subscribe:' + name, 'Client event subscription failed: ' + name,
                            exception=True, visible=False)
            return False
        self.subscriptions.append((event, guarded))
        return True

    def stop(self):
        self.running = False
        self._lifecycle = None
        self._close_cache_observer()
        self._hotkey_held = False
        self._processing.clear()
        self._bonus_account_key = None
        self._publish_activity()
        for service in list(self.services.values()) + ([self._instance_session.service] if self._instance_session else []):
            if getattr(service, "loading", False):
                service.cancel_loading()
        for callback_id in (self._tick_id, self._bonus_callback_id, self._load_id):
            if callback_id is not None:
                try:
                    self.api.cancel(callback_id)
                except Exception:
                    pass
        self._tick_id = self._bonus_callback_id = self._load_id = None
        while self.subscriptions:
            event, callback = self.subscriptions.pop()
            try:
                event -= callback
            except Exception:
                self._warn_once('unsubscribe', 'Client event removal failed; retained callbacks are inactive.', visible=False)
        if self._bonus_subscription is not None:
            bus, bonus_event, bonus_callback = self._bonus_subscription
            self._bonus_subscription = None
            try:
                bus.removeListener(bonus_event, bonus_callback)
            except Exception:
                LOG.warning('Could not remove XP event subscription.')
        self._window_call('close')
        self._retire_footer()
        self.inflight.clear()
        if self._log_handle is not None:
            handle = self._log_handle
            self._log_handle = None
            try:
                LOG.info('GRZ Session Stats %s stopped.', VERSION)
                handle.close()
            except Exception:
                LOG.warning('Could not close the dedicated mod log.')

    def cleanup_complete(self):
        if self.footer_handle is not None:
            return False
        try:
            return self.window is None or not self.window.is_open()
        except Exception:
            # An unreadable native handle is not confirmation of release.
            return False

    def _ensure_service(self):
        if not self.running or self.api.is_replay():
            return None
        dbid = self.api.account_dbid()
        if not dbid:
            return None
        key = '{0}:{1}'.format(self.api.region, int(dbid))
        if key != self.active_key:
            self._window_call('close')
            if key not in self.services:
                self.services[key] = self.service_factory(self.data_dir, key, LAUNCH_ID,
                                                         self.expected_table, now=self.now)
                restored = len(self.services[key].pending_arena_ids())
                if restored:
                    LOG.info('Restored incomplete results: count=%s; background recovery remains active.', restored)
            self.active_key = key
            self.active_service = self.services[key]
            self._publish_activity()
        self._ensure_cache_observer()
        self._ensure_installation_session()
        self._schedule_loading()
        return self.active_service

    def _loading_services(self):
        services = list(self.services.values())
        if self._instance_session is not None:
            services.append(self._instance_session.service)
        return [service for service in services if getattr(service, 'loading', False)]

    def _schedule_loading(self):
        if not self.running or self._load_id is not None or not self._loading_services():
            return
        callback = self._guard(self._advance_loading, 'history_loading')
        try:
            delay = 1.0 if self.api.in_battle() else 0.01
            self._load_id = self.api.schedule(delay, callback)
            self.compatibility_warnings.pop('timer:loading', None)
        except Exception:
            callback._grz_enabled = False
            self._warn_once('timer:loading', message('core.loading_timer'))

    def _advance_loading(self):
        self._load_id = None
        if not self.running:
            return
        try:
            services = self._loading_services()
            if services and not self.api.in_battle():
                service = services[self._load_cursor % len(services)]
                self._load_cursor += 1
                service.advance_loading()
                if not service.loading:
                    if service.ready and self._instance_session is not None:
                        for account_key, account_service in self.services.items():
                            if account_service is service:
                                self._backfill_installation(account_key, service)
                                break
                    self._window_call('refresh')
                    self._publish_activity()
                    self._service_diagnostics()
        finally:
            self._schedule_loading()

    def _ensure_installation_session(self):
        if self._instance_session is not None:
            return self._instance_session
        if not self.running or self.active_service is None:
            return None
        try:
            from .config_path import find_installation_root
            from .sessions import InstallationSession
            root = self._installation_dir or find_installation_root()
            if root is None:
                raise ValueError('Installation root unavailable.')
            self._instance_session = InstallationSession(self.data_dir, root, LAUNCH_ID,
                                                        self.expected_table, self.now, self._started_at,
                                                        deferred=self._deferred_loading)
            # Only this process's records have known installation provenance.
            # Account archives from previous processes must not be guessed in.
            for account_key, service in self.services.items():
                self._backfill_installation(account_key, service)
            self.compatibility_warnings.pop('installation:identity', None)
        except Exception:
            self._warn_once('installation:identity',
                            message('installation.unavailable'),
                            visible=self._instance_tab_enabled)
        return self._instance_session

    def _backfill_installation(self, account_key, service):
        # Loading services expose durable live beginnings immediately. Retry
        # once they become ready to include results received before discovery.
        for record in service.launch_records():
            self._record_installation(account_key, record)
            if record.get('_result_seen'):
                self._record_installation(account_key, record, is_result=True)

    def _record_installation(self, account_key, record, is_result=False):
        session = self._ensure_installation_session()
        if session is None:
            return False
        try:
            if is_result:
                observed = (account_key, str(record['arena_id'])) in self._observed_arenas
                changed = session.result(account_key, record, allow_new=observed)
            else:
                changed = session.begin(account_key, record)
            if session.service.last_error:
                raise RuntimeError('Installation ledger write failed.')
            self.compatibility_warnings.pop('installation:storage', None)
            return changed
        except Exception:
            self._warn_once('installation:storage',
                            message('installation.save'))
            return False

    def _close_cache_observer(self):
        observer = self._cache_observer
        self._cache_observer = None
        if observer is not None:
            try:
                observer.close()
            except Exception:
                self._warn_once('results:observer_cleanup', 'Optional result observer cleanup failed.', visible=False)

    def _ensure_cache_observer(self):
        getter = getattr(self.api, 'result_cache', None)
        if not callable(getter):
            return
        try:
            cache = getter()
            # Avatar/player transitions can temporarily hide the repository's
            # cache while a legitimate earlier request is still returning.
            if cache is None:
                return
            if self._cache_observer is not None and self._cache_observer.cache is cache:
                return
            self._close_cache_observer()
            if cache is not None:
                from .cache_observer import CacheObserver
                self._cache_observer = CacheObserver(cache, self._capture_cache_request,
                                                     self._consume_observed_cache)
                self.compatibility_warnings.pop('results:observer', None)
        except Exception:
            self._warn_once('results:observer',
                            message('runtime.observer'))

    def _capture_cache_request(self):
        if not self.running or self.active_service is None or self.api.is_replay():
            return None
        dbid = self.api.account_dbid()
        if not dbid or self.active_key != '{0}:{1}'.format(self.api.region, int(dbid)):
            return None
        return self._lifecycle, self.active_key, self.active_service

    def _consume_observed_cache(self, context, arena_id, args):
        lifecycle, account_key, service = context
        if not self.running or self._lifecycle is not lifecycle or len(args) < 2:
            return
        code, raw = args[:2]
        if (_number(code, nonnegative=False) is not None and code > 0 and
                isinstance(raw, dict) and str(raw.get('arenaUniqueID')) == str(arena_id)):
            self._process(raw, account_key, service, source='native_cache')

    def _on_account(self, *args, **kwargs):
        try:
            self._ensure_service()
        except Exception:
            self.last_error = message('runtime.saved')
            self._warn_once('account', 'Could not initialize account statistics.', exception=True, visible=False)
        self._schedule_tick()
        self._publish_activity()
        self._service_diagnostics()

    def _close_for_battle(self, *args, **kwargs):
        self._window_call('close')

    def _on_avatar(self, *args, **kwargs):
        if not self.running:
            return
        try:
            if self.api.is_replay() or not self.api.in_battle():
                return
            service = self._ensure_service()
            context = self.api.battle_context()
            if service is None or context is None:
                return
            arena_id = str(context['arena_id'])
            context = dict(context)
            context['account_key'] = self.active_key
            self.contexts[(self.active_key, arena_id)] = context
            service.begin_battle(arena_id, started_at=context.get('started_at'),
                                 vehicle_id=context.get('vehicle_id'), map_id=context.get('map_id'), mode='random',
                                 vehicle_name=context.get('vehicle_name'), vehicle_tier=context.get('vehicle_tier'),
                                 vehicle_type=context.get('vehicle_type'), map_name=context.get('map_name'))
            self._observed_arenas.add((self.active_key, arena_id))
            self._record_installation(self.active_key, context)
            self._window_call('close')
            self._publish_activity()
        except Exception:
            self._warn_once('arena', message('runtime.begin'), exception=True)

    def _on_results(self, is_player_vehicle, results, *args):
        if not self.running or not is_player_vehicle or self.api.is_replay():
            return
        try:
            service = self._ensure_service()
            if service is not None:
                self._process(results, self.active_key, service)
        except Exception:
            self._warn_once('results:received', message('runtime.results'), exception=True)
            self.monitor.fault('result_reader', 'onBattleResultsReceived', 'readable result', 'exception')
            self._service_diagnostics()

    def _process(self, results, account_key, service, reusable=None, source='event'):
        if not self.running:
            return False
        self._processing[account_key] = self._processing.get(account_key, 0) + 1
        self._publish_activity()
        try:
            return self._process_result(results, account_key, service, reusable, source)
        finally:
            remaining = max(0, self._processing.get(account_key, 1) - 1)
            if remaining:
                self._processing[account_key] = remaining
            else:
                self._processing.pop(account_key, None)
            self._publish_activity()
            self._service_diagnostics()

    def _process_result(self, results, account_key, service, reusable, source):
        arena_id = str(results.get('arenaUniqueID', '')) if isinstance(results, dict) else ''
        context = {}
        context_getter = getattr(service, 'result_context', None)
        if callable(context_getter):
            stored_context = context_getter(arena_id)
            if isinstance(stored_context, dict):
                context.update(stored_context)
        for field, value in self.contexts.get((account_key, arena_id), {}).items():
            if value is not None:
                context[field] = value
        context['account_dbid'] = int(account_key.rsplit(':', 1)[1])
        context['_loading'] = (getattr(service, 'loading', False) or
                               (self._instance_session is not None and self._instance_session.service.loading))
        self.monitor.check(results, context, self.api.random_bonus_type, source)
        record = normalize_result(results, context=context,
                                  random_bonus_type=self.api.random_bonus_type,
                                  vehicle_resolver=self.api.vehicle_info, map_resolver=self.api.map_info)
        if record is None:
            return False
        if source == 'late_cache':
            # An expired request can still carry the only available result.
            # Fill unknowns, but never revise facts from a newer delivery.
            record['reconcile'] = False
            for candidate in record.get('_deferred_candidates', []):
                candidate['reconcile'] = False
        started_at = record.get('started_at')
        if (started_at is not None and self._started_at is not None and
                self._started_at <= started_at <= self.now()):
            # A current result can arrive even when the avatar-ready event was
            # missed. Replayed historical events must not revive waiting.
            self._observed_arenas.add((account_key, record['arena_id']))
        if reusable is None and source != 'late_cache' and account_key == self.active_key:
            try:
                # A cache callback can be older than the displayed result.
                # Consult the native controller so it cannot undo an applied
                # post-battle multiplier when events arrive out of order.
                posted = self.api.posted_bundle(record['arena_id'])
                posted_raw = getattr(posted, 'results', None)
                personal = posted_raw.get('personal') if isinstance(posted_raw, dict) else None
                avatar = personal.get('avatar') if isinstance(personal, dict) else None
                # The controller belongs to the current login. A retained or
                # mismatched bundle must not mark another account's raw XP as
                # bonus-adjusted: that durable flag would block later repairs.
                if (isinstance(avatar, dict) and
                        str(posted_raw.get('arenaUniqueID')) == record['arena_id'] and
                        _integer(avatar.get('accountDBID')) == context['account_dbid']):
                    reusable = getattr(posted, 'reusable', None)
            except Exception:
                self.monitor.fault('bonus_reader', 'postedResults.reusable', 'readable bonus data', 'exception', source)
                self._warn_once('results:bonus',
                                message('runtime.bonus'),
                                exception=True)
        if reusable is not None:
            for target in record.get('_deferred_candidates', [record]):
                # Native service updates this value when the player applies the
                # post-battle multiplier; never add the bonus to raw XP a second time.
                try:
                    personal = reusable.personal
                    value = _number(personal.xpProgress.get(target['vehicle_id'], {}).get('xp'))
                    applied = bool(personal.isAddXPBonusApplied)
                    if value is not None and (applied or target['xp_received'] is None):
                        target['xp_received'] = value
                        target['xp_bonus_applied'] = applied
                except Exception:
                    self.monitor.fault('bonus_fields', 'reusable.personal.xpProgress', 'supported bonus fields', 'exception', source)
                    self._warn_once('results:bonus',
                                    message('runtime.bonus'),
                                    exception=True)
        changed = service.record_result(record)
        installation_changed = self._record_installation(account_key, record, is_result=True)
        LOG.info('Result normalized: source=%s complete=%s changed=%s', source, record.get('complete'), changed)
        if service.last_error:
            LOG.error('Statistics storage reported an error; previous data preserved.')
        self.recent[(account_key, record['arena_id'])] = self.now()
        if len(self.recent) > 128:
            oldest = sorted(self.recent, key=self.recent.get)[0]
            self.recent.pop(oldest, None)
        if ((changed and service is self.active_service) or
                (installation_changed and self._instance_tab_enabled)):
            self._window_call('refresh')
        return changed

    def _on_posted(self, reusable, controller, results_window=None, *args):
        if not self.running or self.api.is_replay():
            return
        try:
            service = self._ensure_service()
            bundle = controller.getResults()
            raw = getattr(bundle, 'results', None)
            if service is not None:
                self._process(raw, self.active_key, service, reusable, source='posted')
        except Exception:
            self._warn_once('results:posted_callback', message('runtime.processed'), exception=True)
            self.monitor.fault('posted_reader', 'onResultPosted', 'readable posted result', 'exception')
            self._service_diagnostics()

    def _on_bonus(self, *args):
        if self.running and self.active_key is not None and self._bonus_callback_id is None:
            account_key = self.active_key

            def refresh_account():
                self._bonus_callback_id = None
                self._bonus_account_key = None
                self._publish_activity()
                if account_key == self.active_key:
                    self._refresh_posted()

            callback = self._guard(refresh_account, 'bonus_timer')
            try:
                self._bonus_account_key = account_key
                self._bonus_callback_id = self.api.schedule(0.1, callback)
                self._publish_activity()
            except Exception:
                callback._grz_enabled = False
                self._bonus_account_key = None
                self._warn_once('timer:bonus', message('runtime.bonus_timer'), exception=True)

    def _refresh_posted(self):
        # Manual refresh targets the active account independently of any timer.
        if not self.running or self.api.is_replay() or self.api.in_battle():
            return
        for account_key, arena_id in list(self.recent):
            if account_key != self.active_key:
                continue
            try:
                bundle = self.api.posted_bundle(arena_id)
                raw = getattr(bundle, 'results', None)
                if raw is not None:
                    self._process(raw, account_key, self.services[account_key], getattr(bundle, 'reusable', None), source='refresh')
            except Exception:
                self._warn_once('results:bonus', message('runtime.bonus'), exception=True)
                self.monitor.fault('bonus_reader', 'postedResults.reusable', 'readable bonus data', 'exception', 'refresh')
        self._service_diagnostics()

    def _tick(self):
        self._tick_id = None
        if not self.running:
            return
        try:
            service = self._ensure_service()
            if service is not None and not self.api.is_replay():
                if self.api.in_battle():
                    self._close_for_battle()
                    # Same verified arena API as the event handler. This also
                    # captures membership if the ready event is removed/late.
                    self._on_avatar()
                else:
                    self._poll_one(service, self.active_key)
        except Exception:
            self._warn_once('tick', message('runtime.tick'), exception=True)
        finally:
            self._publish_activity()
            self._service_diagnostics()
            self._schedule_tick()

    def _poll_one(self, service, account_key):
        if getattr(service, 'loading', False) or not getattr(service, 'ready', True):
            return
        now = self.now()
        for key, request in list(self.inflight.items()):
            if request['expires'] <= now:
                self.inflight.pop(key, None)
        if self.inflight:
            return
        pending = service.pending_arena_ids()
        # Native requests are serialized with the stock UI and other mods.
        # Prefer live battles, then the earliest due result, so the first old
        # failure cannot repeatedly jump ahead of untried results.
        pending.sort(key=lambda arena_id: ((account_key, str(arena_id)) not in self._observed_arenas,
                     self.retries.get((account_key, str(arena_id)), (0, 0))[1],
                     -(arena_start(arena_id) or 0), str(arena_id)))
        for arena_id in pending:
            arena_id = str(arena_id)
            key = (account_key, arena_id)
            count, due = self.retries.get(key, (0, 0))
            if due > now:
                continue
            request = {'expires': now + 30}
            self.inflight[key] = request
            self.retries[key] = (count + 1, now + min(300, 5 * (2 ** min(count, 6))))

            lifecycle = self._lifecycle

            def received(*args, **kwargs):
                # This invocation requests only one result and then exits the
                # loop. Account/service/key remain the original request's;
                # extra native callback arguments cannot override them.
                if not self.running or self._lifecycle is not lifecycle:
                    return
                # An expired request may finish after its replacement started.
                # Only the callback owning the current token can consume it.
                if self.inflight.get(key) is not request:
                    if (len(args) >= 2 and _number(args[0], nonnegative=False) is not None and
                            args[0] > 0 and isinstance(args[1], dict) and
                            str(args[1].get('arenaUniqueID')) == key[1]):
                        try:
                            self._process(args[1], key[0], service, source='late_cache')
                        except Exception:
                            self._warn_once('results:late_cache', message('runtime.late'))
                            self.monitor.fault('cache_callback', 'battleResultsCache.callback',
                                               'readable late result', 'exception', 'cache')
                            self._service_diagnostics()
                    return
                self.inflight.pop(key, None)
                try:
                    if len(args) < 2:
                        raise TypeError('Result cache callback requires status and result')
                    code, raw = args[:2]
                    if _number(code, nonnegative=False) is None:
                        self.monitor.fault('cache_status', 'battleResultsCache.status', 'numeric status', type(code).__name__, 'cache')
                    elif code > 0:
                        if isinstance(raw, dict) and str(raw.get('arenaUniqueID')) == key[1]:
                            self._process(raw, key[0], service, source='cache')
                            if key[1] not in service.pending_arena_ids():
                                self.retries.pop(key, None)
                                self._recovery_states.pop(key, None)
                        else:
                            self.monitor.check(raw, {'account_dbid': int(key[0].rsplit(':', 1)[1])},
                                               self.api.random_bonus_type, 'cache')
                            self.monitor.fault('cache_identity', 'battleResultsCache.arenaUniqueID',
                                               'requested battle identity', 'missing or mismatched', 'cache')
                    else:
                        status_getter = getattr(self.api, 'result_status', None)
                        status = status_getter(code) if callable(status_getter) else 'not_returned'
                        if status not in ('cooldown', 'rate_limited', 'not_ready', 'disconnected', 'unavailable', 'rejected'):
                            status = 'not_returned'
                        if status in ('cooldown', 'not_ready', 'disconnected', 'rate_limited'):
                            delay = 30 if status == 'rate_limited' else TICK_SECONDS
                            self.retries[key] = (count, self.now() + delay)
                        safe_code = code if code in (-14, -13, -10, -7, -6, -5, -4, -3, -2, -1, 0) else 'unknown'
                        marker = (status, safe_code)
                        if self._recovery_states.get(key) != marker:
                            self._recovery_states[key] = marker
                            LOG.info('Result recovery: status=%s code=%s attempt=%s pending=%s',
                                     status, safe_code, count + 1, len(service.pending_arena_ids()))
                except Exception:
                    self._warn_once('results:cache_callback', message('runtime.pending'), exception=True)
                    self.monitor.fault('cache_callback', 'battleResultsCache.callback', 'status and result', 'exception', 'cache')
                finally:
                    self._publish_activity()
                    self._service_diagnostics()
            try:
                from .cache_observer import OWN_CALLBACK
                setattr(received, OWN_CALLBACK, True)
                requested = self.api.request_result(arena_id, received)
            except Exception:
                requested = False
                self._warn_once('results:cache', message('runtime.cache'), exception=True)
            if not requested:
                if self.inflight.get(key) is request:
                    self.inflight.pop(key, None)
                self._warn_once('results:cache', message('runtime.cache'))
            else:
                self.compatibility_warnings.pop('results:cache', None)
            break

    def snapshot(self):
        if self.active_service is None:
            return self._localizer.snapshot({'version': VERSION, 'warnings': [message('runtime.account_wait')],
                    'scopes': {}, 'appearance': dict(self._presentation)})
        result = self.active_service.snapshot()
        result['appearance'] = dict(self._presentation)
        instance_records = {}
        if self._instance_tab_enabled:
            session = self._ensure_installation_session()
            if session is not None:
                scope, instance_records, installation_warnings = session.snapshot()
                result['scopes']['instance'] = scope
                result['warnings'].extend(warning for warning in installation_warnings
                                          if warning not in result['warnings'])
        warnings = result.setdefault('warnings', [])
        pending, waiting = self._pending_activity()
        result['recovery'] = {'pending': len(pending),
                              'in_flight': sum(1 for key in self.inflight if key[0] == self.active_key),
                              'states': {}}
        for arena_id in pending:
            status = self._recovery_states.get((self.active_key, str(arena_id)), ('queued', None))[0]
            states = result['recovery']['states']
            states[status] = states.get(status, 0) + 1
        backlog = len(pending - waiting)
        if backlog:
            warnings.append(message('runtime.backlog').format(backlog))
        try:
            from .visuals import enrich_snapshot
            source = getattr(self.active_service, '_state', {}).get('battles', {})
            ledger = dict((row['id'], source[row['id']]) for scope in result['scopes'].values()
                          for row in scope.get('battles', []) if row['id'] in source)
            ledger.update(instance_records)
            enrich_snapshot(result, ledger)
            self.compatibility_warnings.pop('visuals', None)
        except Exception:
            self._warn_once('visuals', message('runtime.thumbnails'), exception=True)
        for value in [self.last_error, self.active_service.last_error] + [
                self.compatibility_warnings[key] for key in sorted(self.compatibility_warnings)]:
            if value and value not in warnings:
                warnings.append(value)
        health_warning = self.monitor.warning()
        if health_warning and health_warning not in warnings:
            warnings.append(health_warning)
        return self._localizer.snapshot(result)

    def open_window(self):
        if not self.running or self.api.is_replay() or self.api.in_battle():
            return False
        try:
            if self._ensure_service() is None:
                self._notify(message('runtime.garage'))
                return False
            self._load_appearance()
            opened = self._ensure_window() and self._window_call('open')
            if not opened:
                self._notify(message('runtime.open_files'))
            return opened
        except Exception:
            LOG.exception('Could not open the statistics window.')
            self._notify(message('runtime.open_log'))
            return False

    def on_action(self, arg):
        if not self.running:
            return
        getter = getattr(arg, 'get', None)
        if not callable(getter):
            return
        action = getter('action')
        if action == 'close':
            self._window_call('close')
        elif action == 'reset' and self.active_service is not None:
            # Confirmation is performed by the local UI before emitting reset.
            account_key = getter('account_key')
            if account_key is not None and account_key != self.active_key:
                return
            scope = getter('scope')
            if scope is None or scope == 'manual':
                self.active_service.reset_manual()
            elif scope == 'instance' and self._instance_tab_enabled:
                session = self._ensure_installation_session()
                if session is None:
                    return
                session.reset()
            else:
                return
            self._window_call('refresh')
        elif action in ('page', 'sort') and self.active_service is not None:
            if getter('account_key') != self.active_key:
                return
            scope, group = getter('scope'), getter('group')
            service = self.active_service
            if scope == 'instance' and self._instance_tab_enabled:
                session = self._ensure_installation_session()
                if session is None:
                    return
                service, scope = session.service, 'manual'
            period_id = getter('period_id')
            if not period_id:
                return
            if action == 'sort':
                options = dict((key, getter(key)) for key in ('metric', 'statistic', 'direction', 'chronology'))
                if not service.set_order(scope, group, options, period_id):
                    return
            else:
                raw_page = getter('page')
                if not isinstance(raw_page, text_type) or len(raw_page) > 8 or not raw_page or any(char not in '0123456789' for char in raw_page):
                    return
                if not service.set_page(scope, group, int(raw_page), period_id):
                    return
            self._window_call('refresh')
        elif action == 'language' and self.active_service is not None:
            if getter('account_key') != self.active_key:
                return
            from .config_files import save_language
            if save_language(self.appearance_path, getter('language')):
                self._load_appearance()
                self._window_call('refresh')
            else:
                self._notify(message('language.save_error'))
        elif action == 'refresh':
            self._load_appearance()
            self._refresh_posted()
            if self.active_service is not None and not self.api.in_battle():
                for key in list(self.retries):
                    if key[0] == self.active_key:
                        self.retries[key] = (0, 0)
                self._poll_one(self.active_service, self.active_key)
            self._window_call('refresh')
        elif action == 'resize':
            self._window_call('resize', getter('width'), getter('height'))

    def _parse_hotkey(self, value):
        try:
            if not isinstance(value, text_type) or len(value) > 64:
                raise ValueError('Invalid hotkey shape')
            parts = value.upper().replace(' ', '').split('+')
            key_name = parts[-1]
            if key_name not in ['F{0}'.format(i) for i in range(1, 13)]:
                raise ValueError('Function key required')
            modifiers = set(parts[:-1])
            if not modifiers.issubset({'CTRL', 'SHIFT', 'ALT'}):
                raise ValueError('Unknown hotkey modifier')
            return (getattr(self.api.keys, 'KEY_' + key_name), modifiers)
        except (ValueError, TypeError, AttributeError):
            LOG.warning('Invalid hotkey; using CTRL+F10.')
            fallback = getattr(getattr(self.api, 'keys', None), 'KEY_F10', None)
            return (fallback, {'CTRL'}) if fallback is not None else None

    def _on_key_down(self, event):
        if not self.running or self._hotkey is None:
            return
        try:
            if event.key != self._hotkey[0] or self._hotkey_held:
                return
            self._hotkey_held = True
            pairs = {'CTRL': ('KEY_LCONTROL', 'KEY_RCONTROL'),
                     'SHIFT': ('KEY_LSHIFT', 'KEY_RSHIFT'), 'ALT': ('KEY_LALT', 'KEY_RALT')}
            held = set(name for name, pair in pairs.items()
                       if any(self.api.key_down(getattr(self.api.keys, key)) for key in pair))
            if held == self._hotkey[1]:
                if self._window_call('is_open'):
                    self._window_call('close')
                else:
                    self.open_window()
        except Exception:
            LOG.exception('Configured shortcut handler failed.')

    def _on_key_up(self, event):
        if self.running and self._hotkey and getattr(event, 'key', None) == self._hotkey[0]:
            self._hotkey_held = False


_runtime = None


def init():
    global _runtime
    if _runtime is not None and _runtime.running:
        return
    # Reuse a stopped owner when native teardown was incomplete; a fresh
    # runtime would have no way to retry or gate its old window/footer.
    instance = _runtime if _runtime is not None else Runtime()
    try:
        instance.start()
        _runtime = instance
    except Exception:
        LOG.exception('GRZ Session Stats initialization failed; cleaning up partial initialization.')
        try:
            instance.stop()
        except Exception:
            pass
        _runtime = None if instance.cleanup_complete() else instance


def fini():
    global _runtime
    instance = _runtime
    if instance is not None:
        try:
            instance.stop()
        except Exception:
            LOG.exception('GRZ Session Stats teardown failed.')
        if _runtime is instance and instance.cleanup_complete():
            _runtime = None
