# -*- coding: utf-8 -*-
"""Editor scene contracts, run with Python 2.7 or 3.x; no game client needed."""
from __future__ import absolute_import, division

import importlib
import json
import os
import sys
import types
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPO = os.path.abspath(os.path.join(ROOT, '..', '..'))
MOD_ROOT = os.path.join(REPO, 'mods')
sys.path.insert(0, ROOT)
MODULES = []
for folder in ('rangefinder', 'aimtimer'):
    client = os.path.join(MOD_ROOT, folder, 'src', 'res', 'scripts', 'client')
    if not os.path.isdir(client):
        continue
    namespace = 'grz_' + folder
    sys.path.insert(0, client)
    if os.environ.get('GRZ_RETICLE_MOD', folder) != folder:
        continue
    MODULES.append((importlib.import_module(namespace + '.scene_catalog'),
                    importlib.import_module(namespace + '.native_preview'),
                    importlib.import_module(namespace + '.views')))
if not MODULES:
    raise ValueError('Expected source for the reticle module being tested')


class Value(object):
    pass


class Marker(object):
    def __init__(self):
        self.children = dict((b'elem_%d' % (index + 1), Value()) for index in range(37))
        self.mixing = None

    def getChildByName(self, name):
        return self.children.get(name)

    def setMixingScale(self, value):
        self.mixing = value


class Root(object):
    def __init__(self, marker):
        self.marker = marker

    def getChildByName(self, name):
        return self.marker


class Flash(object):
    def __init__(self, marker_name):
        self.marker = Marker()
        self.flashObject = Root(self.marker)
        self.preview_markers = [marker_name]
        self.component = Value()
        self.zoom_calls = []
        self.arty_scales = []
        self.ui_scale = None

    def as_setZoomS(self, label, zoom):
        self.zoom_calls.append((label, zoom))

    def as_updateScaleWidgetS(self, scale):
        self.arty_scales.append(scale)

    def as_setSizeS(self, width, height):
        pass

    def as_setScaleS(self, scale):
        self.ui_scale = scale

    def as_recreateDeviceS(self, x, y):
        pass


class FocusClock(types.ModuleType):
    def __init__(self):
        types.ModuleType.__init__(self, 'BigWorld')
        self.now = 0.0
        self.pending = {}
        self.serial = 0

    def time(self):
        return self.now

    def callback(self, delay, action):
        self.serial += 1
        self.pending[self.serial] = action
        return self.serial

    def cancelCallback(self, identifier):
        self.pending.pop(identifier)

    def tick(self, now):
        self.now = now
        actions, self.pending = self.pending, {}
        for action in actions.values():
            action()


class SceneTests(unittest.TestCase):
    def test_localized_backend_uses_all_session_stats_languages(self):
        with open(os.path.join(ROOT, 'tier_xi_profiles.json'), 'rb') as stream:
            vehicles = json.load(stream)
        for unused_scene, native, views in MODULES:
            catalog = importlib.import_module(native.__package__ + '.preview_catalog')
            runtime = importlib.import_module(native.__package__ + '.runtime')
            garage = importlib.import_module(native.__package__ + '.garage')
            core = importlib.import_module(native.__package__ + '.core')
            local = catalog.translations
            self.assertEqual(local.LANGUAGES, ('de', 'en', 'es', 'fr', 'pl', 'ru', 'uk'))
            self.assertEqual(local.language_code('PT-BR'), 'en')
            self.assertEqual(local.language_code(b'UK_ua'), 'uk')
            for language in local.LANGUAGES:
                instance = runtime.Runtime.__new__(runtime.Runtime)
                instance._language_cache_getter = None
                instance._language_cache_epoch = None
                instance.context_epoch = 0
                instance.language_getter = lambda: language + '-REGION'
                instance.store = Value()
                instance.store.data = core.DEFAULTS
                instance._sample = {'context': 'garage'}
                instance._status = local.message('saved', language)
                instance._error = ''
                self.assertEqual(instance.language(), language)
                self.assertTrue(local.message('save_failed', language))
                self.assertEqual(local.localize_decimal('1.25', language),
                                 '1.25' if language == 'en' else '1,25')
                choices = {row['id']: row['label'] for row in catalog.choices(language)}
                for row in catalog.PROFILES:
                    if language in ('en', 'pl'):
                        self.assertEqual(choices[row['id']], row['label_' + language])
                    else:
                        self.assertEqual(choices[row['id']], local._MECHANICS[row['id']][language])
                for vehicle in vehicles:
                    note = local.vehicle_note(vehicle, language)
                    if language in ('en', 'pl'):
                        self.assertEqual(note, vehicle['detail_' + language])
                    else:
                        self.assertEqual(note, local._VEHICLES[vehicle['id']][language])
                previous = catalog.TIER_XI
                try:
                    catalog.TIER_XI = vehicles
                    state = instance.payload()
                    self.assertTrue(views._valid_state(state))
                    self.assertTrue(garage._payload_json(state))
                    self.assertEqual(json.loads(state)['language'], language)
                    self.assertEqual(sum(row.get('tier') == 11 for row in json.loads(state)['preview_choices']),
                                     len(vehicles))
                finally:
                    catalog.TIER_XI = previous

    def test_defaults_and_all_packaged_zoom_levels(self):
        for catalog, unused_native, unused_views in MODULES:
            self.assertEqual(catalog.resolve('arcade')['step'], 1)
            self.assertEqual(catalog.resolve('sniper')['zoom'], 16)
            self.assertEqual(catalog.resolve('arty')['scene_id'], 'arty_top')
            self.assertEqual(catalog.resolve('arty', 'arty_trajectory')['step'], 2)
            self.assertEqual(catalog.resolve('sniper', 'sniper', 3)['zoom'], 16)
            self.assertEqual(catalog.resolve('sniper', 'sniper', 4)['zoom'], 25)

    def test_rejects_mismatched_and_untrusted_values(self):
        for catalog, unused_native, unused_views in MODULES:
            for mode, scene, step in ((None, None, None), ('sniper', 'arty_top', 1),
                                      ('arty', '../capture', 1), ('arty', [], 1),
                                      ('sniper', 'sniper', True), ('sniper', 'sniper', 1.5),
                                      ('arcade', 'arcade', -1), ('arcade', 'arcade', 5),
                                      ('arcade', 'arcade', float('nan')),
                                      ('arcade', 'arcade', float('inf')),
                                      ('arcade', 'arcade', '1')):
                self.assertIsNone(catalog.resolve(mode, scene, step))
            self.assertEqual(catalog.resolve('sniper', 'sniper', 2.0)['zoom'], 8)

    def test_resolved_geometry_does_not_mutate_catalog(self):
        for catalog, unused_native, unused_views in MODULES:
            frame = catalog.resolve('arcade')
            frame['marker_scale'] = 100
            self.assertNotEqual(catalog.resolve('arcade')['marker_scale'], 100)

    def test_single_full_size_trajectory_frame_hides_unmeasured_dispersion(self):
        for catalog, native, _ in MODULES:
            original = catalog.SCENE_FRAMES['arty_trajectory']
            try:
                catalog.SCENE_FRAMES['arty_trajectory'] = [
                    dict(original[2], step=2, frame_size=(2560, 1440), focus_unmeasured=True)
                ]
                frame = catalog.resolve('arty', 'arty_trajectory')
                self.assertEqual((frame['step'], frame['frame_size']), (2, (2560, 1440)))
                self.assertIsNone(catalog.resolve('arty', 'arty_trajectory', 3))
                renderer = native.PreviewRenderer()
                flash = renderer._flash = Flash(native.MARKER_NAME)
                renderer._spec = ('arty', 'standard', {'decoration': None}, (2560, 1440, 1), frame)
                renderer._geometry()
                self.assertEqual((flash.marker.x, flash.marker.y), (1280, 720))
                self.assertFalse(renderer.supports_focus)
                self.assertFalse(any(dot.visible for dot in flash.marker.children.values()))
                renderer._spec = ('arty', 'standard', {'decoration': None}, (2560, 1440, 1),
                                  catalog.resolve('arty', 'arty_top', 2))
                renderer._geometry()
                self.assertTrue(renderer.supports_focus)
                self.assertTrue(all(dot.visible for dot in flash.marker.children.values()))
            finally:
                catalog.SCENE_FRAMES['arty_trajectory'] = original

    def test_zoom_updates_reuse_existing_flash(self):
        for catalog, native, unused_views in MODULES:
            renderer = native.PreviewRenderer()
            flash = Flash(native.MARKER_NAME)
            viewport = {'width': 1920, 'height': 1080, 'scale': 1}
            from_catalog = importlib.import_module(native.__package__ + '.preview_catalog')
            selected = from_catalog.profile('standard', 'sniper')
            renderer._flash = flash
            renderer._spec = ('sniper', 'standard', selected, (1920, 1080, 1),
                              catalog.resolve('sniper'))
            renderer._applied = True
            renderer.status = 'ready'
            calls = []
            renderer._geometry = lambda: calls.append(renderer._spec[4]['step'])

            def no_recreate(*args, **kwargs):
                raise AssertionError('Changing zoom recreated the Flash surface')

            renderer._discard = no_recreate
            previous = native._zoom_text
            native._zoom_text = lambda zoom: b'x%d' % zoom
            try:
                self.assertTrue(renderer.update('sniper', 'standard', viewport, 'sniper', 4))
                self.assertIs(renderer._flash, flash)
                self.assertEqual(flash.zoom_calls, [(b'x25', 25)])
                self.assertEqual(calls, [4])
                # Repeating an acknowledged state does no more native work.
                self.assertTrue(renderer.update('sniper', 'standard', viewport, 'sniper', 4))
                self.assertEqual(flash.zoom_calls, [(b'x25', 25)])
                self.assertEqual(calls, [4])
            finally:
                native._zoom_text = previous

    def test_arty_camera_switch_reuses_flash(self):
        for catalog, native, unused_views in MODULES:
            renderer = native.PreviewRenderer()
            renderer._flash = flash = Flash(native.MARKER_NAME)
            from_catalog = importlib.import_module(native.__package__ + '.preview_catalog')
            selected = from_catalog.profile('standard', 'arty')
            renderer._spec = ('arty', 'standard', selected, (1920, 1080, 1),
                              catalog.resolve('arty'))
            renderer._applied = True
            renderer.status = 'ready'
            renderer._geometry = lambda: None
            self.assertTrue(renderer.update('arty', 'standard',
                                           {'width': 1920, 'height': 1080, 'scale': 1},
                                           'arty_trajectory', 4))
            self.assertIs(renderer._flash, flash)
            self.assertEqual(renderer._spec[4]['scene_id'], 'arty_trajectory')
            self.assertEqual(flash.arty_scales, [1.0])
            self.assertEqual(flash.zoom_calls, [])

    def test_uncalibrated_trajectory_zoom_changes_native_ellipse(self):
        for catalog, unused_native, unused_views in MODULES:
            wide = catalog.resolve('arty', 'arty_trajectory', 0)
            close = catalog.resolve('arty', 'arty_trajectory', 4)
            self.assertIs(wide['calibrated'], False)
            self.assertIs(close['calibrated'], False)
            self.assertIsNone(close['zoom'])
            self.assertGreater(close['ellipse'][0], wide['ellipse'][0])

    def test_calibrated_points_follow_image_cover_and_labels_follow_ui_scale(self):
        for catalog, native, unused_views in MODULES:
            renderer = native.PreviewRenderer()
            flash = Flash(native.MARKER_NAME)
            scene = catalog.resolve('arty')
            scene.update({'calibrated': True, 'frame_size': (1000, 1000),
                          'marker_scale': 2.5, 'points': tuple((12, -9) for unused in range(37))})
            renderer._flash = flash
            renderer._spec = ('arty', 'standard', {'decoration': None}, (2000, 1000, 3), scene)
            renderer._geometry()
            self.assertEqual(flash.ui_scale, 3)
            self.assertEqual(flash.marker.mixing, 5)
            point = flash.marker.children[b'elem_1']
            self.assertEqual((point.x, point.y), (24, -18))
            self.assertEqual((flash.marker.x, flash.marker.y), (1000, 500))

    def test_artillery_moves_between_measured_stages_and_fades_obscured_dots(self):
        for catalog, native, unused_views in MODULES:
            renderer = native.PreviewRenderer()
            flash = renderer._flash = Flash(native.MARKER_NAME)
            scene = catalog.resolve('arty', 'arty_trajectory', 2)
            scene.update({'frame_size': (1000, 1000), 'focus_points': (
                ((200, -90, 0),) * 37, ((124, 60, 1),) * 37, ((21, 19, 1),) * 37,
            )})
            renderer._spec = ('arty', 'standard', {'decoration': None}, (2000, 1000, 3), scene)
            renderer._geometry()
            point = flash.marker.children[b'elem_1']
            renderer._draw_focus(0)
            self.assertEqual((point.x, point.y, point.alpha), (400, -180, 0))
            renderer._draw_focus(0.5)
            self.assertEqual((point.x, point.y, point.alpha), (324, -30, 0.5))
            renderer._draw_focus(1.5)
            self.assertEqual((point.x, point.y, point.alpha), (145, 79, 1))
            renderer._draw_focus(2)
            self.assertEqual((point.x, point.y, point.alpha), (42, 38, 1))
            self.assertEqual((flash.marker.x, flash.marker.y), (1000, 500))

    def test_window_payload_and_omitted_selection_are_compatible(self):
        for unused_catalog, unused_native, views in MODULES:
            window = views.SettingsWindow(lambda arg: None, lambda: '{}')
            window._viewport = lambda: {'width': 1920, 'height': 1080, 'scale': 1}
            window._preview_mode = 'arty'
            window._preview_scene_id = 'arty_trajectory'
            window._preview_zoom_step = 4
            frame = window._scene_selection('arty')
            self.assertEqual((frame['scene_id'], frame['step']), ('arty_trajectory', 4))
            self.assertEqual(window._scene_selection('sniper')['step'], 3)
            payload = json.loads(window._payload())
            self.assertEqual(payload['editor_scene_id'], 'arty_trajectory')
            self.assertEqual(payload['editor_zoom_step'], 4)
            self.assertEqual(payload['editor_focus'], 1)
            self.assertIs(payload['editor_focus_demo'], False)
            self.assertNotIn('preview_increased_zoom', payload)
            self.assertNotIn('capture_helper', payload)

    def test_editor_request_ack_tracks_only_latest_selection_and_rejects_invalid_variants(self):
        previous = sys.modules.get('BigWorld')
        try:
            for unused_catalog, unused_native, views in MODULES:
                clock = FocusClock()
                sys.modules['BigWorld'] = clock
                entries = []
                window = views.SettingsWindow(lambda arg: None, lambda: '{}',
                    on_diagnostic=lambda event, fields: entries.append((event, fields)))
                window._window = object()
                window.is_open = lambda: True
                window._viewport = lambda: {'width': 1920, 'height': 1080, 'scale': 1}
                window._place = lambda: None
                window._refresh_preview = lambda unused_focus: None
                payloads = []
                window.update = lambda unused_state: payloads.append(json.loads(window._payload()))

                opening = dict(active=True, mode='arcade', variant='standard',
                               scene_id='arcade', zoom_step=1, request_id=1.0)
                self.assertTrue(window._dispatch_editor_request('editor', opening.get))
                clock.tick(0)
                self.assertEqual(payloads[-1]['editor_request_id'], 1)
                self.assertIs(payloads[-1]['editor_request_accepted'], True)
                self.assertEqual(payloads[-1]['editor_preview_variant'], 'standard')

                first = dict(opening, request_id=2, variant='cassette', zoom_step=2)
                self.assertTrue(window._dispatch_editor_request('preview', first.get))
                stale = clock.pending[window._editor_callback]
                second = dict(opening, request_id=3, variant='forced_reload', zoom_step=3)
                self.assertTrue(window._dispatch_editor_request('preview', second.get))
                stale()
                self.assertEqual(len(payloads), 1)
                clock.tick(1)
                self.assertEqual(payloads[-1]['editor_request_id'], 3)
                self.assertEqual(payloads[-1]['editor_preview_mode'], 'arcade')
                self.assertEqual(payloads[-1]['editor_preview_variant'], 'forced_reload')
                self.assertEqual(payloads[-1]['editor_zoom_step'], 3)

                rejected = dict(opening, request_id=4, variant='invalid-variant')
                self.assertFalse(window._dispatch_editor_request('preview', rejected.get))
                self.assertEqual(payloads[-1]['editor_request_id'], 4)
                self.assertIs(payloads[-1]['editor_request_accepted'], False)
                self.assertEqual(payloads[-1]['editor_preview_variant'], 'forced_reload')
                self.assertEqual(payloads[-1]['editor_zoom_step'], 3)
                self.assertFalse(window._dispatch_editor_request('preview', first.get))
                self.assertFalse(clock.pending)
                results = [(fields['request_id'], fields['result']) for event, fields in entries
                           if event == 'editor-result']
                self.assertEqual(results, [(1, 'accepted'), (2, 'superseded'), (3, 'accepted'), (4, 'rejected')])
                self.assertNotIn('invalid-variant', repr(entries))
                opened = next(fields for event, fields in entries if event == 'editor-open')
                self.assertEqual(opened['request_id'], 1)
                self.assertEqual(opened['variant'], 'standard')
                self.assertEqual(opened['profile'], 'standard')
                closing = dict(active=False, request_id=5)
                self.assertTrue(window._dispatch_editor_request('editor', closing.get))
                clock.tick(2)
                self.assertEqual(entries[-1][0], 'editor-close')
                self.assertEqual(entries[-1][1]['request_id'], 5)
                self.assertEqual(entries[-1][1]['variant'], 'forced_reload')
        finally:
            if previous is None:
                sys.modules.pop('BigWorld', None)
            else:
                sys.modules['BigWorld'] = previous

    def test_focus_demo_keeps_the_same_native_dots_and_survives_scene_zoom(self):
        previous = sys.modules.get('BigWorld')
        try:
            for catalog, native, unused_views in MODULES:
                clock = FocusClock()
                sys.modules['BigWorld'] = clock
                renderer = native.PreviewRenderer()
                renderer._flash = flash = Flash(native.MARKER_NAME)
                renderer.status = 'ready'
                renderer._applied = True
                from_catalog = importlib.import_module(native.__package__ + '.preview_catalog')
                viewport = {'width': 1920, 'height': 1080, 'scale': 1}
                renderer._spec = ('arty', 'standard', from_catalog.profile('standard', 'arty'),
                                  (1920, 1080, 1), catalog.resolve('arty', 'arty_top', 2))
                renderer._geometry()
                point = flash.marker.children[b'elem_1']
                middle = point.x
                finished = []
                self.assertTrue(renderer.play_focus_demo(finished.append))
                self.assertGreater(point.x, middle)
                clock.tick(1.0)
                self.assertLess(point.x, middle * 1.62)
                self.assertTrue(renderer.update('arty', 'standard', viewport, 'arty_trajectory', 4))
                self.assertIs(renderer._flash, flash)
                self.assertIs(flash.marker.children[b'elem_1'], point)
                self.assertEqual((flash.marker.x, flash.marker.y), (960, 540))
                self.assertEqual(len(renderer._artillery_nodes), 37)
                self.assertEqual(finished, [])
                clock.tick(2.0)
                self.assertLess(point.x, middle)
                self.assertEqual(finished, [True])
                self.assertEqual(renderer._focus, 2)
                self.assertFalse(clock.pending)

                self.assertTrue(renderer.play_focus_demo(finished.append))
                # Explicitly choosing the already selected preset also stops.
                self.assertTrue(renderer.update('arty', 'standard', viewport, 'arty_trajectory',
                                                4, 2, True))
                self.assertEqual(finished, [True, False])
                self.assertFalse(clock.pending)

                self.assertTrue(renderer.play_focus_demo(finished.append))
                animation = renderer._focus_callback
                renderer.close()
                self.assertNotIn(animation, clock.pending)
                self.assertEqual(finished, [True, False, False])
                self.assertFalse(renderer._artillery_nodes)
        finally:
            if previous is None:
                sys.modules.pop('BigWorld', None)
            else:
                sys.modules['BigWorld'] = previous

    def test_direct_focus_keeps_the_stock_markers_through_zoom_and_resize(self):
        previous_clock = sys.modules.get('BigWorld')
        try:
            for catalog, native, unused_views in MODULES:
                profiles = importlib.import_module(native.__package__ + '.preview_catalog')
                for mode in ('arcade', 'sniper'):
                    clock = sys.modules['BigWorld'] = FocusClock()
                    renderer = native.PreviewRenderer()
                    renderer._flash = flash = Flash(native.MARKER_NAME)
                    secondary = Marker()
                    flash.preview_markers.append(b'secondary')
                    flash.flashObject.getChildByName = lambda name: (flash.marker if name == native.MARKER_NAME
                                                                     else secondary)
                    renderer.status = 'ready'
                    renderer._applied = True
                    selected = profiles.profile('dual_accuracy', mode)
                    viewport = {'width': 1920, 'height': 1080, 'scale': 1}
                    scene = catalog.resolve(mode)
                    renderer._spec = (mode, 'dual_accuracy', selected, (1920, 1080, 1), scene)
                    renderer._geometry()
                    self.assertTrue(renderer.supports_focus)
                    self.assertAlmostEqual(flash.marker.mixing, 1)
                    self.assertAlmostEqual(secondary.mixing, 1.3)

                    wide, regular, tight = catalog.FOCUS_FACTORS[mode]
                    self.assertTrue(renderer.update(mode, 'dual_accuracy', viewport, mode, scene['step'], 0, True))
                    self.assertAlmostEqual(flash.marker.mixing, wide)
                    self.assertAlmostEqual(secondary.mixing, wide * 1.3)
                    self.assertEqual((flash.marker.x, flash.marker.y), (960, 540))
                    self.assertTrue(renderer.update(mode, 'dual_accuracy', viewport, mode, scene['step'], 1, True))
                    self.assertAlmostEqual(flash.marker.mixing, regular)

                    finished = []
                    self.assertTrue(renderer.play_focus_demo(finished.append))
                    self.assertAlmostEqual(flash.marker.mixing, wide)
                    clock.tick(native.FOCUS_DURATION / 2.0)
                    animated = regular
                    self.assertAlmostEqual(flash.marker.mixing, animated)
                    original_label = native._zoom_text
                    native._zoom_text = lambda zoom: b'x%d' % zoom
                    try:
                        resized = {'width': 1600, 'height': 900, 'scale': 1.5}
                        self.assertTrue(renderer.update(mode, 'dual_accuracy', resized, mode, 4, 1))
                    finally:
                        native._zoom_text = original_label
                    self.assertIs(renderer._flash, flash)
                    self.assertEqual((flash.marker.x, flash.marker.y), (800, 450))
                    self.assertEqual((secondary.x, secondary.y), (800, 450))
                    self.assertAlmostEqual(flash.marker.mixing, animated * 1.5)
                    self.assertAlmostEqual(secondary.mixing, animated * 1.5 * 1.3)
                    self.assertEqual(flash.zoom_calls, [(b'x25', 25)] if mode == 'sniper' else [])
                    self.assertEqual(finished, [])
                    clock.tick(native.FOCUS_DURATION)
                    self.assertAlmostEqual(flash.marker.mixing, tight * 1.5)
                    self.assertAlmostEqual(secondary.mixing, tight * 1.5 * 1.3)
                    self.assertEqual(finished, [True])

                    self.assertTrue(renderer.play_focus_demo(finished.append))
                    animation = renderer._focus_callback
                    renderer.close()
                    self.assertNotIn(animation, clock.pending)
                    self.assertEqual(finished, [True, False])
                    self.assertFalse(renderer.supports_focus)
        finally:
            if previous_clock is None:
                sys.modules.pop('BigWorld', None)
            else:
                sys.modules['BigWorld'] = previous_clock

    def test_active_rocket_sight_keeps_its_stock_shape(self):
        for catalog, native, unused_views in MODULES:
            profiles = importlib.import_module(native.__package__ + '.preview_catalog')
            for mode in ('arcade', 'sniper'):
                renderer = native.PreviewRenderer()
                renderer._flash = flash = Flash(native.MARKER_NAME)
                renderer.status = 'ready'
                renderer._applied = True
                identifier = 'auxiliary_rocket_launcher'
                selected = profiles.profile(identifier, mode)
                viewport = {'width': 1920, 'height': 1080, 'scale': 1}
                scene = catalog.resolve(mode)
                renderer._spec = (mode, identifier, selected, (1920, 1080, 1), scene)
                renderer._geometry()
                self.assertTrue(renderer.update(mode, identifier, viewport, mode, scene['step'], 2, True))
                self.assertEqual(flash.marker.mixing, 1)
                self.assertFalse(renderer.supports_focus)
                self.assertFalse(renderer.play_focus_demo(lambda completed: None))

    def test_ready_and_active_mechanics_use_consistent_stock_snapshots(self):
        class Sample(object):
            def __init__(self):
                self.calls = {}

            def __getattr__(self, name):
                return lambda *args: self.calls.setdefault(name, []).append(args)

        for unused_catalog, native, unused_views in MODULES:
            from_catalog = importlib.import_module(native.__package__ + '.preview_catalog')
            previous = native._distance_text
            native._distance_text = lambda meters: b'%d m' % meters
            try:
                forced = Sample()
                controlled = Sample()
                forced_profile = from_catalog.profile('forced_reload', 'arcade')
                controlled_profile = from_catalog.profile('controllable_reload', 'arcade')
                native._sample_state(forced, forced_profile)
                native._sample_state(controlled, controlled_profile)
                native._finish_sample_state(controlled, controlled_profile)
                self.assertEqual(forced.calls['as_setClipParamsS'], [(4, 1, 0)])
                self.assertEqual(forced.calls['as_setAmmoStockS'], [(30, 0, b'normal', False)])
                self.assertEqual(forced.calls['as_setReloadingAsPercentS'], [(3.5, 65, True, False)])
                self.assertNotIn('as_setIsInControllableReloadS', forced.calls)
                self.assertEqual(controlled.calls['as_setClipParamsS'], [(4, 1, 3)])
                self.assertIn((True,), controlled.calls['as_setIsInControllableReloadS'])
                self.assertIn('as_setAutoloaderPercentS', controlled.calls)

                cav = Sample()
                cav_profile = from_catalog.profile('autoreloader_surge', 'arcade')
                native._sample_state(cav, cav_profile)
                native._finish_sample_state(cav, cav_profile)
                self.assertEqual(cav.calls['as_setClipParamsS'], [(4, 1, 1)])
                self.assertEqual(cav.calls['as_setAmmoStockS'], [(30, 3, b'normal', False)])
                self.assertEqual(cav.calls['as_setAutoreloaderSurgeStateS'], [(False,), (False,)])
                self.assertEqual(cav.calls['as_setAutoloaderReloadasPercentS'], [(1.0,)])
                self.assertEqual(cav_profile['decoration'], 'autoreloaderSurge')
                self.assertEqual(cav.calls['as_setAutoloaderPercentS'], [(0.95, 9.5, False, True, False)])
                native._finish_sample_state(cav, cav_profile, surge_remaining_fraction=0.94)
                self.assertEqual(cav.calls['as_setAutoloaderPercentS'][-1], (0.94, 9.4, False, True, False))

                ordinary = Sample()
                native._sample_state(ordinary, from_catalog.profile('cassette', 'sniper'))
                self.assertEqual(ordinary.calls['as_setAmmoStockS'], [(30, 4, b'normal', False)])
                self.assertEqual(ordinary.calls['as_setReloadingAsPercentS'], [(0, 100, False, True)])

                reserve = Sample()
                native._sample_state(reserve, from_catalog.profile('extra_shot', 'sniper'))
                self.assertEqual(reserve.calls['as_setClipParamsS'], [(4, 1, 2)])
                self.assertEqual(reserve.calls['as_setAmmoStockS'], [(30, 1, b'normal', False)])
                self.assertEqual(reserve.calls['as_setReloadingAsPercentS'], [(2.25, 50, True, True)])

                leopard = Sample()
                native._sample_state(leopard, from_catalog.profile('accuracy_stacks', 'sniper'))
                self.assertEqual(leopard.calls['as_setAccuracyStacksProgressS'], [(4,)])

                charge = Sample()
                native._sample_state(charge, from_catalog.profile('charge_shot', 'sniper'))
                self.assertEqual(charge.calls['as_setChargeGunActiveS'], [(True,)])
                self.assertEqual(charge.calls['as_setChargeGunStateS'], [(0.99, 3, False)])

                salvo = Sample()
                native._sample_state(salvo, from_catalog.profile('twingun', 'sniper'))
                self.assertEqual(salvo.calls['as_setTwinGunMarkerActiveS'], [(True,)])
                self.assertEqual(salvo.calls['as_setTwinGunMarkerStateS'], [(3,)])

                ares = Sample()
                native._sample_state(ares, from_catalog.profile('temperature_autocannon', 'sniper'))
                self.assertEqual(ares.calls['as_setClipParamsS'], [(250, 1, 0)])
                self.assertEqual(ares.calls['as_setAmmoStockS'], [(49, 49, b'critical', False)])

                bustle = Sample()
                native._sample_state(bustle, from_catalog.profile('bustle_feed', 'sniper'))
                self.assertEqual(bustle.calls['as_setReloadingAsPercentS'], [(6.9, 50, True, False)])
                self.assertEqual(bustle.calls['as_setAmmoStockS'], [(40, 0, b'normal', False)])

                selected = from_catalog.profile('shell_calibration', 'sniper')
                selected['capacity'] = 2
                calibrated = Sample()
                native._sample_state(calibrated, selected)
                native._finish_sample_state(calibrated, selected)
                self.assertEqual(calibrated.calls['as_setClipParamsS'], [(2, 1, 5)])
                self.assertEqual(calibrated.calls['as_setAmmoStockS'], [(30, 2, b'normal', False)])
                self.assertEqual(calibrated.calls['as_setReloadingAsPercentS'], [(0, 100, False, True)])
                self.assertEqual(calibrated.calls['as_setShellCalibrationStateS'], [(3,)])

                mock_modules = ('gui', 'gui.Scaleform', 'gui.Scaleform.genConsts',
                                'gui.Scaleform.genConsts.LOW_CHARGE_SHOT_CONSTS')
                original_modules = dict((name, sys.modules.get(name)) for name in mock_modules)
                for name in mock_modules:
                    module = sys.modules[name] = types.ModuleType(name)
                    module.__path__ = []
                    parent, unused_separator, child = name.rpartition('.')
                    if parent:
                        setattr(sys.modules[parent], child, module)
                constants = sys.modules[mock_modules[-1]]
                constants.LOW_CHARGE_SHOT_CONSTS = type('LOW_CHARGE_SHOT_CONSTS', (), {'LOW_CHARGE': 2})
                try:
                    gorilla = Sample()
                    native._sample_state(gorilla, from_catalog.profile('low_charge_shot', 'sniper'))
                    self.assertEqual(gorilla.calls['as_setLowChargeInitialTimeS'], [(20.5, 10.25, 2.0, 0.5)])
                    self.assertEqual(gorilla.calls['as_setLowChargeTimeLeftS'], [(6.0, 2, True)])
                    self.assertEqual(gorilla.calls['as_setReloadingCounterShownS'], [(False,)])
                finally:
                    for name, old_module in original_modules.items():
                        if old_module is None:
                            sys.modules.pop(name, None)
                        else:
                            sys.modules[name] = old_module
            finally:
                native._distance_text = previous

    def test_stock_surge_survives_loading_or_failure_of_the_separate_decoration(self):
        class Painted(object):
            visible = True
            alpha = 1
            width = height = 20

        class Decoration(object):
            state = 0

            def getMember(self, name):
                return self

            def setVisible(self, value):
                pass

            def as_getState(self):
                return self.state

            def as_getError(self):
                return 'Original client symbol failed: Original component draws no visible pixels: sectors'

            def as_setPreview(self, linkage, x, y, scale, view, settings):
                self.linkage = linkage

        for catalog, native, unused_views in MODULES:
            from_catalog = importlib.import_module(native.__package__ + '.preview_catalog')
            events = []
            renderer = native.PreviewRenderer(on_diagnostic=lambda event, payload: events.append((event, payload)))
            renderer._flash = flash = Flash(native.MARKER_NAME)
            flash._isDAAPIInited = lambda: True
            renderer._spec = ('sniper', 'xi_cav_mod_71', from_catalog.profile('autoreloader_surge', 'sniper'),
                              (1920, 1080, 1), catalog.resolve('sniper'))
            renderer._settings = {2: {b'cassetteAlphaValue': 1}}
            renderer._queue_wait = lambda: None
            renderer._prepared = renderer._finalized = True
            base = Painted()
            flash.flashObject.getChildAt = lambda index: base
            base.autoloaderComponent = Painted()
            base.autoloaderComponent.cassette = cassette = Value()
            for index in range(1, 5):
                shell = Painted()
                shell.currentLabel = 'ready'
                setattr(cassette, 'shell_%d' % index, shell)
            cassette.shell_4.currentLabel = 'reloading'
            self.assertTrue(renderer._visible_cassette())
            cassette.shell_2.currentLabel = 'clear'
            self.assertFalse(renderer._visible_cassette())
            cassette.shell_2.currentLabel = 'ready'
            cassette.shell_4.currentLabel = 'reloading_surge'
            self.assertFalse(renderer._visible_cassette())
            cassette.shell_4.currentLabel = 'reloading'
            # The stock 1-frame placeholder has no painted status badge.
            cassette.statusMc = Value()
            renderer._decoration = decoration = Decoration()
            renderer._decor_pending = True
            renderer._wait()
            self.assertEqual(decoration.linkage, b'AutoreloaderSurgeWidgetUI')
            self.assertIs(renderer._flash, flash)
            self.assertTrue(renderer._applied)
            self.assertEqual(renderer.status, 'loading')

            decoration.state = 1
            renderer._wait()
            self.assertIs(renderer._decoration, decoration)
            self.assertEqual((renderer.status, renderer.reason), ('ready', 'decoration-mounted'))
            self.assertTrue(any(event == 'native_decor_poll' and record.get('stage') == 'host-structure-ready'
                                for event, record in events))

            decoration.state = -1
            renderer._decor_pending = True
            renderer._wait()
            self.assertIs(renderer._flash, flash)
            self.assertEqual((renderer.status, renderer.reason), ('partial', 'decoration-failed'))
            self.assertEqual(renderer.decoration_diagnostic, 'pixel-probe')
            self.assertIs(renderer.get_availability()['sniper']['xi_cav_mod_71'], True)
            failure = [payload for event, payload in events if event == 'native_decor_failure'][0]
            self.assertEqual(failure['variant'], 'xi_cav_mod_71')
            self.assertEqual(failure['profile'], 'autoreloader_surge')
            self.assertEqual(failure['diagnostic'], 'pixel-probe')
            self.assertEqual(failure['linkage'], 'AutoreloaderSurgeWidgetUI')
            self.assertEqual(failure['stock_library'], 'autoreloader-surge')
            layers = [(payload['layer'], payload['layer_state']) for event, payload in events
                      if event == 'native_layer']
            self.assertIn(('crosshair', 'check-passed'), layers)
            self.assertIn(('cassette', 'check-passed'), layers)
            self.assertIn(('gun-marker', 'check-passed'), layers)
            self.assertIn(('decoration-host', 'responsive'), layers)
            self.assertIn(('stock-decoration', 'mounted-unverified'), layers)
            self.assertIn(('stock-decoration', 'unavailable'), layers)
            self.assertNotIn('Original client symbol', repr(events))

    def test_decoration_diagnostic_keeps_runtime_error_details_out_of_the_preview(self):
        class Host(object):
            def __init__(self, error):
                self.error = error

            def as_getError(self):
                return self.error

        for unused_catalog, native, unused_views in MODULES:
            expectations = (
                (r'Cannot load C:\PRIVATE\embedded-path.swf: Error #2032', ('library-load', 2032)),
                ('Error #2032, URL detail only', ('library-load', 2032)),
                ('Original client symbol is missing: AutoreloaderSurgeWidgetUI', ('symbol-missing', None)),
                ('Original client symbol failed: AccuracyCrosshairUI : Error #1069: private text',
                 ('stock-symbol-error', 1069)),
                ('Original frame label is missing: active_instantly', ('timeline-frame', None)),
                ('Unsupported original decorative linkage: example', ('host-linkage-unsupported', None)),
                ('Invalid decorative preview geometry', ('host-geometry-invalid', None)),
                (r'Unexpected runtime detail C:\PRIVATE\path', ('host-rejected', None)),
                ('Error #4321 with arbitrary text', ('host-rejected', None)),
                ('', ('host-error-empty', None)),
                (object(), ('host-error-type', None)),
                ('a' * 513, ('host-error-too-long', None)),
            )
            for message, expected in expectations:
                self.assertEqual(native._decoration_error_details(Host(message)), expected + (None,))
            allowed = 'net.wg.gui.battle.components::BattleUIComponent'
            detail = 'Original client symbol failed: Error #1065: Variable %s is not defined.'
            self.assertEqual(native._decoration_error_details(Host(detail % allowed)),
                             ('stock-binding-missing', 1065, allowed))
            self.assertEqual(native._decoration_error_details(Host(detail % allowed.replace('::', '.'))),
                             ('stock-binding-missing', 1065, allowed))
            self.assertEqual(native._decoration_error_details(Host(detail % 'local.private::UserThing')),
                             ('stock-symbol-error', 1065, None))
            self.assertEqual(native._decoration_error_details(Host('Error #1065: ' + allowed)),
                             ('flash-error', 1065, None))
            meta = 'net.wg.infrastructure.base.meta.impl::AutoreloaderSurgeWidgetMeta'
            self.assertEqual(native._decoration_error_details(Host(detail % meta)),
                             ('stock-binding-missing', 1065, meta))
            diagnostics = importlib.import_module(native.__package__ + '.preview_diagnostics')
            self.assertEqual(diagnostics._safe_fields(dict(
                missing_qname=meta, stock_library='autoreloader-surge',
                linkage='AutoreloaderSurgeWidgetUI', layer='stock-decoration',
                layer_state='unavailable', error=r'C:\PRIVATE\raw-path'), ()), dict(
                missing_qname=meta, stock_library='autoreloader-surge',
                linkage='AutoreloaderSurgeWidgetUI', layer='stock-decoration', layer_state='unavailable'))
            self.assertEqual(diagnostics._safe_fields(dict(
                missing_qname='private.garage::UserName', stock_library='private-library',
                linkage='private-linkage', layer='private-layer'), ()), {})


if __name__ == '__main__':
    unittest.main()
