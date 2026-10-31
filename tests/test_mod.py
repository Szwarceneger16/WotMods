"""Offline runtime regressions with deliberately strict GUI and sound mocks.

Cannot validate actual WoT graphics layering; regression assertions target
previously confirmed bugs: alpha tint ineffective, sniper isActive gating,
and sound-like vanilla consumable glow.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'source/mod_staysharp_medkit.py'


class Component:
    gui = None

    class eSizeMode:
        PIXEL = object()
    class ePositionMode:
        CLIP = object()
    class eHAnchor:
        CENTER = object()
    class eVAnchor:
        CENTER = object()
    class eMaterialFX:
        BLEND = object()
    class eFilterType:
        LINEAR = object()

    typed = {
        'widthMode': eSizeMode.PIXEL,
        'heightMode': eSizeMode.PIXEL,
        'horizontalPositionMode': ePositionMode.CLIP,
        'verticalPositionMode': ePositionMode.CLIP,
        'horizontalAnchor': eHAnchor.CENTER,
        'verticalAnchor': eVAnchor.CENTER,
        'materialFX': eMaterialFX.BLEND,
        'filterType': eFilterType.LINEAR,
    }

    def __init__(self, texture):
        gui=type(self).gui
        gui.calls.append(('GUI.Simple', texture))
        if gui.fail_simple:
            raise RuntimeError('native allocation failed')
        self.history = []
        self.colour_history = []
        self.size = None
        self.position = None
        self.textureName = texture
        self.visible = False

    def __setattr__(self, name, value):
        gui=type(self).gui
        if name in self.typed and value is not self.typed[name]:
            raise TypeError('not typed')
        if name == 'widthMode' and gui.fail_flags:
            raise TypeError('bad renderer flag')
        if name == 'textureName':
            if gui.fail_swap and getattr(self,'textureName',None) is not None:
                raise RuntimeError('swap failed')
            self.history.append(value)
        if name == 'colour':
            if gui.fail_colour:
                raise ValueError('colour failed')
            # Crucial regression: dynamically changing alpha is not trusted.
            if value != (255,255,255,255):
                raise RuntimeError('unsupported dynamic alpha: ' + str(value))
            self.colour_history.append(value)
        object.__setattr__(self,name,value)


class FakeGUI(types.ModuleType):
    def __init__(self):
        super().__init__('GUI')
        self.calls=[]
        self.roots=[]
        self.window=(1920,1080)
        self.fail_simple=False
        self.fail_flags=False
        self.fail_colour=False
        self.fail_swap=False
        self.fail_add=False
        self.fail_del=False
        self.Simple=Component
        Component.gui=self

    def screenResolution(self):
        return self.window

    def addRoot(self, c):
        self.calls.append(('GUI.addRoot',None))
        if self.fail_add:
            raise RuntimeError('native addRoot failed')
        self.roots.append(c)

    def delRoot(self,c):
        self.calls.append(('GUI.delRoot',None))
        if self.fail_del:
            raise RuntimeError('native delRoot failed')
        if c not in self.roots:
            raise AssertionError('deleting an unregistered root')
        self.roots.remove(c)


class FakeEventBus:
    def __init__(self):
        self.listeners={}
        self.calls=[]
        self.fail_on=None
    def addListener(self,name,callback,scope=None):
        self.calls.append(('add',name,scope))
        if name == self.fail_on:
            raise RuntimeError('event subscription not supported')
        self.listeners.setdefault((name,scope),[]).append(callback)
    def removeListener(self,name,callback,scope=None):
        self.calls.append(('remove',name,scope))
        bucket=self.listeners.get((name,scope),[])
        if callback in bucket:
            bucket.remove(callback)
    def emit(self,name,component,alias='consumablesPanel',scope='global'):
        event=types.SimpleNamespace(alias=alias,componentPy=component)
        for cb in list(self.listeners.get((name,scope),[])):
            cb(event)


class FakeBW(types.ModuleType):
    def __init__(self):
        super().__init__('BigWorld')
        self.jobs={}
        self.clock=0.0
        self.counter=0
        self.avatar=None
        self.entities={}

    def player(self): return self.avatar
    def entity(self,vehicle_id): return self.entities.get(vehicle_id)
    def time(self): return self.clock

    def callback(self, sec, fn):
        self.counter+=1
        self.jobs[self.counter]=(sec,fn)
        return self.counter

    def cancelCallback(self,job):
        self.jobs.pop(job,None)

    def fire(self,name):
        for job,(duration,fn) in list(self.jobs.items()):
            if fn.__name__ == name:
                del self.jobs[job]
                fn()
                return duration
        raise AssertionError('missing callback %s, jobs=%r' % (name,self.jobs))


class FakeItem:
    def __init__(self, name='medkitPremium'):
        self.name=name
        self.isAvailableToUse=True
        self.can_use=True

    def getDescriptor(self):
        return types.SimpleNamespace(name=self.name)

    def canActivate(self,avatar=None):
        return self.can_use,None


class FakeItems:
    def __init__(self,item):
        self.item=item
        self.compact=72
    def iterEquipmentsByTag(self,tag):
        if tag=='medkit' and self.item is not None:
            return [(self.compact,self.item)]
        return []


class Panel:
    _PANEL_MAX_LENGTH=12
    _AMMO_START_IDX=0
    _AMMO_END_IDX=2
    _EQUIPMENT_START_IDX=3
    _EQUIPMENT_END_IDX=5
    _ORDERS_START_IDX=6
    _ORDERS_END_IDX=8
    _OPT_DEVICE_START_IDX=9
    _OPT_DEVICE_END_IDX=11

    def _getPanelSettings(self):
        return 0

    def __init__(self,item):
        self.isActive=True
        self._mask=63
        self._cds=[31,32,33,72,0,0,None,None,None,None,None,None]
        self._equipmentsGlowCallbacks={}
        self.app=types.SimpleNamespace(settingsCore=types.SimpleNamespace(
            interfaceScale=types.SimpleNamespace(get=lambda:0,getScaleByIndex=lambda _:1.0)))
        self.sessionProvider=types.SimpleNamespace(
            isReplayPlaying=False,shared=types.SimpleNamespace(equipments=FakeItems(item)))
        self.orig_disposed=0
        self.camera_mode='arcade'
        self.native_visible=True
        self.fake_flash=None
        self.sessionProvider.shared.crosshair=types.SimpleNamespace(
            getViewID=lambda: {'arcade':1,'sniper':2,'strategic':3,'trajectory':3}.get(self.camera_mode,0))

    def _populate(self): return 'populated'
    def _dispose(self): self.orig_disposed+=1; return 'disposed'

    @property
    def flashObject(self):
        return self.fake_flash

    def as_isVisibleS(self):
        return self.native_visible

    def as_setGlowS(self,*args):
        raise AssertionError('vanilla alert never triggered')

    def as_hideGlowS(self,*args):
        raise AssertionError('vanilla alert never altered')


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'LOCALAPPDATA':self.temp.name})
        self.env.start()
        self.world=FakeBW()
        self.gui=FakeGUI()
        self.resmgr=types.ModuleType('ResMgr')
        self.game=Path(self.temp.name)/'game'
        (self.game/'mods').mkdir(parents=True)
        (self.game/'paths.xml').write_text('<root/>')
        self.resmgr.resolveToAbsolutePath=lambda path:str(self.game/'paths.xml')
        self.missing=set()
        self.resmgr.isFile=lambda path:path not in self.missing
        self.item=FakeItem()
        self.world.avatar=types.SimpleNamespace(
            vehicle=types.SimpleNamespace(health=1000,perkEffects={'equipment':['medkitPremium']}),
            isObserver=lambda:False,arena=types.SimpleNamespace(period=3))
        names=['gui.Scaleform','gui.Scaleform.daapi','gui.Scaleform.daapi.view',
               'gui.Scaleform.daapi.view.battle','gui.Scaleform.daapi.view.battle.shared',
               'gui.Scaleform.daapi.view.battle.shared.consumables_panel',
               'gui.Scaleform.genConsts',
               'gui.Scaleform.genConsts.BATTLE_VIEW_ALIASES',
               'gui.shared', 'gui.shared.events',
               'gui.battle_control', 'gui.battle_control.controllers',
               'gui.battle_control.controllers.consumables',
               'gui.battle_control.controllers.consumables.equipment_ctrl']
        packages={name:types.ModuleType(name) for name in names}
        self.client_language='en'
        packages['helpers']=types.ModuleType('helpers')
        packages['helpers'].getClientLanguage=lambda:self.client_language
        self.audio_plays=[]
        self.audio_stops=[]
        self.audio_fail=set()
        self.audio_gets=[]
        self.sounds={}
        def get_sound(event):
            self.audio_gets.append(event)
            if event in self.audio_fail:
                raise RuntimeError('sound unavailable')
            if event not in self.sounds:
                self.sounds[event]=types.SimpleNamespace(
                    play=lambda: self.audio_plays.append((self.world.clock,event)),
                    stop=lambda: self.audio_stops.append(event))
            return self.sounds[event]
        sound_groups=types.ModuleType('SoundGroups')
        sound_groups.g_instance=types.SimpleNamespace(getSound2D=get_sound)
        packages['gui.battle_control.controllers.consumables.equipment_ctrl'].EquipmentSound=types.SimpleNamespace(
            _soundMap={72:'battle_equipment_1019',73:'battle_equipment_763'})
        packages['gui.Scaleform.daapi.view.battle.shared.consumables_panel'].ConsumablesPanel=Panel
        packages['gui.Scaleform.genConsts.BATTLE_VIEW_ALIASES'].BATTLE_VIEW_ALIASES=types.SimpleNamespace(CONSUMABLES_PANEL='consumablesPanel')
        self.bus=FakeEventBus()
        packages['gui.shared'].g_eventBus=self.bus
        packages['gui.shared'].EVENT_BUS_SCOPE=types.SimpleNamespace(GLOBAL='global')
        packages['gui.shared.events'].ComponentEvent=types.SimpleNamespace(
            COMPONENT_REGISTERED='onComponentRegistered',
            COMPONENT_UNREGISTERED='onComponentUnRegistered')
        arena_module=types.ModuleType('constants')
        arena_module.ARENA_PERIOD=types.SimpleNamespace(BATTLE=3,PREBATTLE=2,AFTERBATTLE=4)
        class KeyEvent:
            def __init__(self): self.handlers=[]
            def __iadd__(self, fn): self.handlers.append(fn); return self
            def __isub__(self, fn): self.handlers.remove(fn); return self
            def emit(self, event):
                for fn in list(self.handlers): fn(event)
        self.key_event=KeyEvent()
        packages['gui.InputHandler']=types.ModuleType('gui.InputHandler')
        packages['gui.InputHandler'].g_instance=types.SimpleNamespace(onKeyDown=self.key_event)
        packages['Keys']=types.ModuleType('Keys')
        packages['Keys'].KEY_M=50
        packages['messenger']=types.ModuleType('messenger')
        self.chat_focused=False
        packages['messenger'].MessengerEntry=types.SimpleNamespace(
            g_instance=types.SimpleNamespace(gui=types.SimpleNamespace(isFocused=lambda:self.chat_focused)))
        self.patch=patch.dict(sys.modules,{'BigWorld':self.world,'GUI':self.gui,'constants':arena_module,
                 'ResMgr':self.resmgr,'SoundGroups':sound_groups,'gui':types.ModuleType('gui'),**packages})
        self.patch.start()
        spec=importlib.util.spec_from_file_location('mod_staysharp_v160',SOURCE)
        self.mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.orig_populate=Panel._populate
        self.orig_dispose=Panel._dispose
        self.mod.init()
        self.panel=Panel(self.item)
        self.emit_register()
        self.assertEqual(self.panel._populate(),'populated')

    def emit_register(self,component=None,alias='consumablesPanel'):
        self.bus.emit('onComponentRegistered',self.panel if component is None else component,alias=alias)

    def emit_unregister(self,component=None,alias='consumablesPanel'):
        self.bus.emit('onComponentUnRegistered',self.panel if component is None else component,alias=alias)

    def tearDown(self):
        self.mod.fini()
        self.patch.stop()
        self.env.stop()
        self.temp.cleanup()

    def state(self,count=1):
        for _ in range(count):
            if self.mod._graphics_disabled:
                break
            self.world.clock+=self.mod.STATE_TICK
            self.world.fire('_check_state')

    def visible_start(self):
        self.state(7)
        self.assertEqual(len(self.gui.roots),1)
        self.assertTrue(self.mod._overlay_active)
        return self.gui.roots[0]

    def animate_at(self,t):
        self.world.clock=self.mod._pulse_start+t
        self.world.fire('_animate')
        return self.mod._frame

    def test_01_event_driven_no_monkeypatches(self):
        self.assertEqual(len(self.mod._event_listeners),2)
        self.assertIs(Panel._populate,self.orig_populate)
        self.assertIs(Panel._dispose,self.orig_dispose)

    def test_02_no_native_graphics_at_startup(self):
        self.state(4)
        self.assertEqual(len(self.gui.roots),0)
        self.state(1)
        self.assertEqual(len(self.gui.roots),1)

    def test_03_real_enum_objects(self):
        overlay=self.visible_start()
        for name,value in Component.typed.items():
            self.assertIs(getattr(overlay,name),value)

    def test_04_colour_fixed_opaque_while_texture_animates(self):
        overlay=self.visible_start()
        self.animate_at(0.5)
        self.animate_at(1.0)
        self.animate_at(2.0)
        self.assertEqual(overlay.colour_history,[(255,255,255,255)])
        self.assertEqual(overlay.textureName,self.mod._texture(20))

    def test_05_0_100_0_cycle(self):
        overlay=self.visible_start()
        start=self.mod._pulse_start
        for t,expected in [(0,0),(0.1,1),(1,10),(2,20),(3,10),(4,0),(5,10),(6,20)]:
            actual=self.animate_at(t)
            self.assertEqual(actual,expected,(t,actual))
        self.assertTrue(len(overlay.history)>2)

    def test_06_truly_invisible_at_zero(self):
        overlay=self.visible_start()
        self.animate_at(2)
        self.assertTrue(overlay.visible)
        self.animate_at(4)
        self.assertFalse(overlay.visible)
        self.animate_at(4.2)
        self.assertTrue(overlay.visible)

    def test_07_no_native_root_churn_while_pulsing(self):
        overlay=self.visible_start()
        for i in range(1,121):
            self.animate_at(i/10.0)
        self.assertEqual(self.gui.roots,[overlay])
        self.assertEqual(len([v for v in self.gui.calls if v[0]=='GUI.Simple']),1)
        self.assertEqual(len([v for v in self.gui.calls if v[0]=='GUI.addRoot']),1)

    def test_08_sniper_marked_inactive_keeps_reminder(self):
        overlay=self.visible_start()
        self.panel.isActive=False
        self.panel.camera_mode='sniper'
        self.state()
        self.assertTrue(self.mod._overlay_active)
        self.animate_at(2)
        self.assertTrue(overlay.visible)

    def test_09_artillery_camera_continues(self):
        overlay=self.visible_start()
        for mode in ['strategic','trajectory','sniper','arcade']:
            self.panel.camera_mode=mode
            self.panel.isActive=False
            self.state()
            self.animate_at(2)
            self.assertTrue(overlay.visible)

    def test_10_can_start_while_isactive_false(self):
        self.panel.isActive=False
        self.visible_start()

    def test_11_depth_over_flash_root(self):
        overlay=self.visible_start()
        self.assertLess(overlay.position[2],0.01)
        self.assertGreaterEqual(overlay.position[2],0)

    def test_12_no_shaders_native_glow_or_os_audio(self):
        src=SOURCE.read_text()
        for needle in ['GUI.AlphaShader(','.addShader(', 'ctypes', 'winsound', 'subprocess',
                       '.as_setGlowS(','.as_hideGlowS(', 'component.colour = (255, 255, 255, 0)']:
            self.assertNotIn(needle,src)

    def test_13_cooldown_hides_and_cancels_pulse(self):
        overlay=self.visible_start()
        self.animate_at(2)
        self.item.isAvailableToUse=False
        self.state()
        self.assertFalse(self.mod._overlay_active)
        self.assertFalse(overlay.visible)
        self.assertEqual(self.gui.roots,[overlay])
        self.assertFalse(any(fn.__name__=='_animate' for _,fn in self.world.jobs.values()))

    def test_14_ready_after_cooldown_reuses_one_component(self):
        overlay=self.visible_start()
        self.item.isAvailableToUse=False
        self.state()
        self.item.isAvailableToUse=True
        self.state(7)
        self.assertTrue(self.mod._overlay_active)
        self.assertEqual(self.gui.roots,[overlay])
        self.assertEqual(len([v for v in self.gui.calls if v[0]=='GUI.Simple']),1)

    def test_15_perk_required(self):
        self.world.avatar.vehicle.perkEffects={'equipment':[]}
        self.state(10)
        self.assertFalse(self.gui.roots)

    def test_16_not_activatable_means_hidden(self):
        self.item.can_use=False
        self.state(10)
        self.assertFalse(self.gui.roots)

    def test_17_no_equipment(self):
        self.panel.sessionProvider.shared.equipments.item=None
        self.state(10)
        self.assertFalse(self.gui.roots)

    def test_18_game_glow_priority(self):
        self.panel._equipmentsGlowCallbacks[3]=1
        self.state(10)
        self.assertFalse(self.gui.roots)
        self.panel._equipmentsGlowCallbacks.clear()
        self.visible_start()

    def test_19_injury_notification_hides_active_overlay(self):
        overlay=self.visible_start()
        self.panel._equipmentsGlowCallbacks[3]=1
        self.state()
        self.assertFalse(overlay.visible)

    def test_20_dead_vehicle_hidden(self):
        overlay=self.visible_start()
        self.world.avatar.vehicle.health=0
        self.state()
        self.assertFalse(overlay.visible)

    def test_21_replay_suppressed(self):
        self.panel.sessionProvider.isReplayPlaying=True
        self.state(8)
        self.assertFalse(self.gui.roots)

    def test_22_observer_suppressed(self):
        self.world.avatar.isObserver=lambda:True
        self.state(8)
        self.assertFalse(self.gui.roots)

    def test_23_device_state_mask_missing(self):
        self.panel._mask=0
        self.state(8)
        self.assertFalse(self.gui.roots)

    def test_24_valid_21_frame_paths_preflight(self):
        self.visible_start()
        # 21 resource queries, exactly once, before single GUI.Simple.
        self.assertEqual(self.mod._texture(0),'gui/maps/staysharp/medkit_pulse_00.dds')
        self.assertEqual(self.mod._texture(20),'gui/maps/staysharp/medkit_pulse_20.dds')

    def test_25_missing_dds_halts_without_native_add(self):
        self.missing.add(self.mod._texture(11))
        self.state(8)
        self.assertEqual(self.gui.roots,[])
        self.assertFalse(self.gui.calls)
        self.assertTrue(self.mod._graphics_disabled)

    def test_26_bad_GUI_creation_no_delroot(self):
        self.gui.fail_simple=True
        self.state(8)
        self.assertEqual(self.gui.roots,[])
        self.assertFalse([c for c in self.gui.calls if c[0]=='GUI.delRoot'])

    def test_27_bad_enum_no_delroot(self):
        self.gui.fail_flags=True
        self.state(8)
        self.assertEqual(self.gui.roots,[])
        self.assertFalse([c for c in self.gui.calls if c[0]=='GUI.delRoot'])

    def test_28_failed_addroot_no_delroot(self):
        self.gui.fail_add=True
        self.state(8)
        self.assertEqual(self.gui.roots,[])
        self.assertFalse([c for c in self.gui.calls if c[0]=='GUI.delRoot'])

    def test_29_failed_texture_swap_disables_but_preserves_game(self):
        overlay=self.visible_start()
        self.gui.fail_swap=True
        self.animate_at(1.0)
        self.assertTrue(self.mod._graphics_disabled)
        self.assertFalse(self.mod._overlay_active)
        self.assertFalse(overlay.visible)

    def test_30_resize_changes_geometry_not_root(self):
        overlay=self.visible_start()
        old=overlay.position
        self.gui.window=(2560,1440)
        self.state()
        self.assertNotEqual(old,overlay.position)
        self.assertEqual(self.gui.roots,[overlay])

    def test_31_interface_scale_changes_size(self):
        overlay=self.visible_start()
        old=overlay.size
        self.panel.app.settingsCore.interfaceScale.getScaleByIndex=lambda _:1.25
        self.state()
        self.assertGreater(overlay.size[0],old[0])

    def test_32_one_slot_change_updates_coordinates(self):
        overlay=self.visible_start()
        old=overlay.position
        self.panel._cds[3]=0
        self.panel._cds[4]=72
        self.state(8)
        self.assertNotEqual(old,overlay.position)

    def test_33_dispose_kills_all_callbacks_and_root(self):
        self.visible_start()
        self.emit_unregister()
        self.panel._dispose()
        self.assertEqual(self.world.jobs,{})
        self.assertEqual(self.gui.roots,[])
        self.assertEqual(self.panel.orig_disposed,1)

    def test_34_double_dispose(self):
        self.visible_start()
        self.emit_unregister()
        self.emit_unregister()
        self.panel._dispose()
        self.panel._dispose()
        self.assertEqual(self.panel.orig_disposed,2)

    def test_35_fail_delroot_does_not_skip_original_dispose(self):
        self.visible_start()
        self.gui.fail_del=True
        self.emit_unregister()
        self.panel._dispose()
        self.assertEqual(self.panel.orig_disposed,1)
        self.assertEqual(self.world.jobs,{})

    def test_36_fini_unsubscribes_without_touching_methods(self):
        self.visible_start()
        self.mod.fini()
        self.assertIs(Panel._populate,self.orig_populate)
        self.assertIs(Panel._dispose,self.orig_dispose)
        self.assertEqual(self.bus.listeners[('onComponentRegistered','global')],[])
        self.assertEqual(self.bus.listeners[('onComponentUnRegistered','global')],[])

    def test_37_diagnostic_reason_and_pulse_heartbeat(self):
        self.visible_start()
        self.animate_at(8.0)
        log=Path(self.temp.name)/'StaySharpMedkit/staysharp.log'
        data=log.read_text()
        for s in ['v' + self.mod.VERSION + ' loaded','native HUD visibility=hud_visible','equipment state=ready','GFX AFTER GUI.addRoot',
                  'PULSE alive frame=0']:
            self.assertIn(s,data)

    def test_38_native_gui_colour_failure_fails_closed(self):
        self.gui.fail_colour=True
        self.state(8)
        self.assertEqual(self.gui.roots,[])
        self.assertTrue(self.mod._graphics_disabled)

    def test_39_only_one_root_after_100_equipment_checks(self):
        overlay=self.visible_start()
        self.state(100)
        self.assertEqual(self.gui.roots,[overlay])

    def test_40_third_party_monkeypatch_is_never_changed_by_mod(self):
        self.visible_start()
        overridden=lambda p: 'external'
        Panel._populate=overridden
        try:
            self.mod.fini()
            self.assertIs(Panel._populate,overridden)
        finally:
            Panel._populate=self.orig_populate


    def test_41_prebattle_selector_never_draws_overlay(self):
        self.world.avatar.arena.period=2
        self.state(40)
        self.assertEqual(self.gui.roots,[])
        log=(Path(self.temp.name)/'StaySharpMedkit/staysharp.log').read_text()
        self.assertIn('not_in_battle_period_2',log)

    def test_42_battle_start_after_prebattle_enables_pulse(self):
        self.world.avatar.arena.period=2
        self.state(12)
        self.world.avatar.arena.period=3
        self.visible_start()

    def test_43_native_panel_hidden_prebattle_suppressed_even_in_battle(self):
        self.panel.native_visible=False
        self.state(15)
        self.assertEqual(self.gui.roots,[])

    def test_44_real_hud_visibility_required_and_live_updates(self):
        overlay=self.visible_start()
        self.panel.native_visible=False
        self.state()
        self.assertFalse(overlay.visible)
        self.assertFalse(self.mod._overlay_active)
        self.panel.native_visible=True
        self.state(8)
        self.assertEqual(self.gui.roots,[overlay])
        self.assertTrue(self.mod._overlay_active)

    def test_45_cooldown_in_artillery_remains_off(self):
        self.panel.camera_mode='strategic'
        self.item.isAvailableToUse=False
        self.state(30)
        self.assertEqual(self.gui.roots,[])

    def test_46_real_stage_coordinates_take_priority(self):
        stage=object()
        rect=types.SimpleNamespace(x=630.0,y=981.0,width=48.0,height=48.0)
        renderer=types.SimpleNamespace(stage=stage,visible=True,
            getBounds=lambda current_stage:rect if current_stage is stage else None)
        f=types.SimpleNamespace(getRendererBySlotIdx=lambda slot:renderer)
        self.panel.fake_flash=f
        overlay=self.visible_start()
        # Stage bounds represent absolute FLASH STAGE coordinates.
        self.assertAlmostEqual(overlay.position[0],2.0*654.0/1920.0-1.0,places=4)
        self.assertAlmostEqual(overlay.position[1],1.0-2.0*1005.0/1080.0,places=4)
        self.assertEqual(self.mod._last_geometry_source,'flash_stage_bounds')

    def test_47_artillery_tracks_changed_stage_geometry(self):
        stage=object()
        rect=types.SimpleNamespace(x=630.0,y=981.0,width=48.0,height=48.0)
        renderer=types.SimpleNamespace(stage=stage,visible=True,getBounds=lambda _:rect)
        self.panel.fake_flash=types.SimpleNamespace(getRendererBySlotIdx=lambda _:renderer)
        overlay=self.visible_start()
        old=overlay.position
        self.panel.camera_mode='strategic'
        rect.x=710.0
        self.state()
        self.assertNotEqual(overlay.position,old)
        self.assertEqual(overlay.position[2],old[2])

    def test_48_readonly_flash_queries_do_not_invoke_vanilla_glow(self):
        f=types.SimpleNamespace(x=500.0,y=980.0)
        f.getRendererBySlotIdx=lambda slot:types.SimpleNamespace(
            x=130.0,y=0.0,width=48.0,height=48.0,visible=True)
        self.panel.fake_flash=f
        self.visible_start()
        self.assertFalse(any('as_setGlow' in str(item) for item in self.gui.calls))

    def test_49_no_renderer_bridge_uses_centered_layout_not_bad_flash_x(self):
        self.panel.fake_flash=types.SimpleNamespace(x=100.0,y=950.0)
        overlay=self.visible_start()
        self.assertEqual(self.mod._last_geometry_source,
                         'centered_layout_renderer_accessor_unavailable')
        # Previous code placed it at x~350 px; centered model stays central.
        self.assertGreater(overlay.position[0],-0.2)
        self.assertLess(overlay.position[0],0.3)

    def test_50_bad_flash_geometry_safe_fallback(self):
        self.panel.fake_flash=types.SimpleNamespace(x=10.0,y=10.0,
            getRendererBySlotIdx=lambda slot:types.SimpleNamespace(
                x=0,y=0,width=0,height=0,visible=True))
        self.visible_start()
        self.assertFalse(self.mod._graphics_disabled)

    def test_51_renderer_explicitly_hidden_suppresses_overlay(self):
        self.panel.fake_flash=types.SimpleNamespace(x=440.0,y=980.0,
            getRendererBySlotIdx=lambda slot:types.SimpleNamespace(visible=False))
        self.state(20)
        self.assertEqual(self.gui.roots,[])

    def test_52_missing_native_visibility_api_fail_closed(self):
        self.panel.as_isVisibleS=None
        self.state(30)
        self.assertEqual(self.gui.roots,[])

    def test_53_native_visibility_api_exception_fail_closed(self):
        def err(): raise ValueError('scaleform unavailable')
        self.panel.as_isVisibleS=err
        self.state(30)
        self.assertEqual(self.gui.roots,[])

    def test_54_afterbattle_no_reminder(self):
        overlay=self.visible_start()
        self.world.avatar.arena.period=4
        self.state()
        self.assertFalse(overlay.visible)

    def test_55_no_arena_period_fails_closed(self):
        del self.world.avatar.arena
        self.state(30)
        self.assertEqual(self.gui.roots,[])

    def test_56_arena_visitor_fallback(self):
        del self.world.avatar.arena
        self.panel.sessionProvider.arenaVisitor=types.SimpleNamespace(getArenaPeriod=lambda:3)
        self.visible_start()

    def test_57_mode_change_without_native_layout_does_not_disable(self):
        self.visible_start()
        for mode in ('strategic','sniper','arcade'):
            self.panel.camera_mode=mode
            self.state(2)
            self.assertFalse(self.mod._graphics_disabled)

    def test_58_safe_flash_introspection_bad_renderer_error(self):
        def fail(slot): raise RuntimeError('unsupported client bridge')
        self.panel.fake_flash=types.SimpleNamespace(x=100.0,y=980.0,
                getRendererBySlotIdx=fail)
        self.visible_start()
        self.assertFalse(self.mod._graphics_disabled)

    def test_59_hud_state_logged_on_visibility_change(self):
        self.visible_start()
        self.panel.native_visible=False
        self.state()
        log=(Path(self.temp.name)/'StaySharpMedkit/staysharp.log').read_text()
        self.assertIn('native HUD visibility=native_panel_hidden',log)

    def test_60_source_avoids_vanilla_glow_and_shader(self):
        text=SOURCE.read_text()
        self.assertNotIn('GUI.AlphaShader(',text)
        self.assertNotIn('as_setGlowS(',text)
        self.assertNotIn('as_hideGlowS(',text)
        self.assertNotIn('playSound(',text)

    def test_61_exact_pulse_period_unchanged(self):
        self.visible_start()
        self.assertEqual([self.animate_at(t) for t in [0.0,2.0,4.0,6.0]],
                         [0,20,0,20])

    def test_62_visibility_off_does_not_allocate_21_frames(self):
        self.panel.native_visible=False
        self.state(20)
        self.assertFalse(self.gui.calls)
        self.assertFalse(self.mod._graphics_disabled)


    def test_63_native_flash_numeric_true_accepted(self):
        self.panel.as_isVisibleS=lambda:1
        self.visible_start()

    def test_64_native_flash_none_rejected(self):
        self.panel.as_isVisibleS=lambda:None
        self.state(10)
        self.assertEqual(self.gui.roots,[])

    def test_65_prebattle_visibility_false_then_true_no_churn(self):
        self.panel.native_visible=False
        self.world.avatar.arena.period=2
        self.state(10)
        self.world.avatar.arena.period=3
        self.panel.native_visible=True
        self.visible_start()
        self.assertEqual(len(self.gui.roots),1)



    def test_66_id_based_vehicle_survives_strategic_camera(self):
        overlay=self.visible_start()
        own_vehicle=self.world.avatar.vehicle
        own_vehicle.id=123
        self.world.avatar.playerVehicleID=123
        self.world.entities[123]=own_vehicle
        self.world.avatar.vehicle=None  # realistic alternate camera transition
        self.panel.camera_mode='strategic'
        self.state(12)
        self.assertTrue(self.mod._overlay_active)
        self.animate_at(2.0)
        self.assertTrue(overlay.visible)
        self.assertIn('own vehicle source=playerVehicleID_entity',
            (Path(self.temp.name)/'StaySharpMedkit/staysharp.log').read_text())

    def test_67_id_based_vehicle_survives_sniper_camera(self):
        overlay=self.visible_start()
        own_vehicle=self.world.avatar.vehicle
        own_vehicle.id=777
        self.world.avatar.playerVehicleID=777
        self.world.entities[777]=own_vehicle
        self.world.avatar.vehicle=None
        self.panel.camera_mode='sniper'
        self.state(10)
        self.assertTrue(self.mod._overlay_active)
        self.animate_at(2.0)
        self.assertTrue(overlay.visible)

    def test_68_original_1_4_bug_is_detected_in_old_probe(self):
        self.world.avatar.playerVehicleID=42
        vehicle=self.world.avatar.vehicle
        vehicle.id=42
        self.world.entities[42]=vehicle
        self.world.avatar.vehicle=None
        self.panel.camera_mode='strategic'
        slot,reason=self.mod._probe_medkit(self.panel)
        self.assertEqual((slot,reason),(3,'ready'))

    def test_69_id_vehicle_works_via_controller_if_bigworld_entity_missing(self):
        own=self.world.avatar.vehicle
        own.id=900
        self.world.avatar.playerVehicleID=900
        self.world.avatar.vehicle=None
        self.panel.sessionProvider.shared.vehicleState=types.SimpleNamespace(
            getControllingVehicleID=lambda:900, getControllingVehicle=lambda:own)
        slot,reason=self.mod._probe_medkit(self.panel)
        self.assertEqual((slot,reason),(3,'ready'))
        self.assertEqual(self.mod._last_vehicle_source,'vehicle_state_controller')

    def test_70_reject_observing_nonowned_vehicle(self):
        self.world.avatar.playerVehicleID=7
        own=self.world.avatar.vehicle
        own.id=7
        self.world.entities[7]=own
        self.panel.sessionProvider.shared.vehicleState=types.SimpleNamespace(
            getControllingVehicleID=lambda:8)
        self.state(10)
        self.assertFalse(self.mod._overlay_active)
        self.assertEqual(self.mod._last_reason,'controlling_vehicle_not_player')

    def test_71_destroyed_avatar_while_entity_has_health_hides(self):
        overlay=self.visible_start()
        self.world.avatar.isVehicleAlive=False
        self.state()
        self.assertFalse(overlay.visible)

    def test_72_entity_dead_even_when_controller_says_ready_hides(self):
        own=self.world.avatar.vehicle
        own.id=135
        self.world.avatar.playerVehicleID=135
        self.world.entities[135]=own
        overlay=self.visible_start()
        self.world.avatar.vehicle=None
        own.health=0
        self.panel.camera_mode='strategic'
        self.state()
        self.assertFalse(overlay.visible)

    def test_73_no_perk_in_strategic_camera_stays_off(self):
        own=self.world.avatar.vehicle
        own.id=333
        self.world.avatar.playerVehicleID=333
        self.world.entities[333]=own
        self.world.avatar.vehicle=None
        own.perkEffects={'equipment':[]}
        self.panel.camera_mode='strategic'
        self.state(10)
        self.assertFalse(self.mod._overlay_active)

    def test_74_no_false_ready_during_cooldown_in_sniper(self):
        own=self.world.avatar.vehicle
        own.id=334
        self.world.avatar.playerVehicleID=334
        self.world.entities[334]=own
        self.world.avatar.vehicle=None
        self.item.isAvailableToUse=False
        self.panel.camera_mode='sniper'
        self.state(10)
        self.assertFalse(self.mod._overlay_active)

    def test_75_no_parent_anchor_if_not_available(self):
        overlay=self.visible_start()
        self.assertEqual(self.mod._overlay_mount,'gui_root')
        self.assertEqual(self.gui.roots,[overlay])

    def test_76_parent_flash_attach_tracks_parent_visibility(self):
        class HUD:
            def __init__(self):
                self.children={}
                self.visible=True
            def addChild(self,child,name):
                self.children[name]=child
            def delChild(self,child):
                for name, obj in list(self.children.items()):
                    if obj is child:
                        del self.children[name]
                        return
                raise AssertionError('not attached')
        hud=HUD()
        self.panel.app.component=hud
        self.state(7)
        self.assertEqual(self.mod._overlay_mount,'hud_child')
        self.assertEqual(self.gui.roots,[])
        self.assertEqual(len(hud.children),1)
        child=list(hud.children.values())[0]
        self.animate_at(2.0)
        self.assertTrue(child.visible)
        hud.visible=False
        self.assertFalse(hud.visible)
        self.emit_unregister()
        self.panel._dispose()
        self.assertEqual(hud.children,{})
        self.assertEqual(self.world.jobs,{})

    def test_77_failed_hud_attach_fails_closed_without_alternate_root(self):
        class HUD:
            def __init__(self): self.children=[]
            def addChild(self,child,name):
                self.children.append(child)
                raise RuntimeError('failed mid-way')
            def delChild(self,child): self.children.remove(child)
        hud=HUD()
        self.panel.app.component=hud
        self.state(9)
        self.assertEqual(hud.children,[])
        self.assertEqual(self.gui.roots,[])
        self.assertTrue(self.mod._graphics_disabled)

    def test_78_asset_fallback_will_not_read_flash_x_y(self):
        class Flash:
            def __getattribute__(self,name):
                if name in ('x','y','scaleX','scaleY'):
                    raise AssertionError('incorrect local-space geometry access')
                if name == 'getRendererBySlotIdx':
                    raise AttributeError('not accessible')
                return object.__getattribute__(self,name)
        self.panel.fake_flash=Flash()
        self.visible_start()
        self.assertTrue(self.mod._overlay_active)

    def test_79_hud_parent_cooldown_no_root_churn(self):
        class HUD:
            def __init__(self): self.children=[];self.n=0
            def addChild(self,child,name): self.children.append(child);self.n+=1
            def delChild(self,child): self.children.remove(child)
        hud=HUD()
        self.panel.app.component=hud
        self.state(7)
        child=hud.children[0]
        self.item.isAvailableToUse=False
        self.state()
        self.assertFalse(child.visible)
        self.item.isAvailableToUse=True
        self.state(7)
        self.assertEqual(hud.children,[child])
        self.assertEqual(hud.n,1)

    def test_80_unready_effects_are_never_cached(self):
        own=self.world.avatar.vehicle
        own.id=203
        self.world.avatar.playerVehicleID=203
        self.world.entities[203]=own
        self.state(7)
        overlay=self.gui.roots[0]
        own.perkEffects['equipment']=[]
        self.world.avatar.vehicle=None
        self.panel.camera_mode='strategic'
        self.state()
        self.assertFalse(overlay.visible)

    def test_81_medkit_canactivate_explicit_avatar(self):
        """Regresses real _MedKitItem._canActivate signature and behaviour."""
        own=self.world.avatar.vehicle
        own.id=778
        self.world.avatar.playerVehicleID=778
        self.world.entities[778]=own
        self.world.avatar.vehicle=None
        self.panel.camera_mode='strategic'
        def check(**kwargs):
            # In WoT native medkit code: absent avatar -> player.vehicle
            if kwargs.get('avatar') is None:
                return False,None
            explicit=kwargs['avatar']
            ent=self.world.entity(explicit.playerVehicleID)
            return bool(ent and self.item.name in ent.perkEffects['equipment']),None
        self.item.canActivate=check
        slot,reason=self.mod._probe_medkit(self.panel)
        self.assertEqual((slot,reason),(3,'ready'))

    def test_82_camera_switch_does_not_change_medkit_activation(self):
        own=self.world.avatar.vehicle
        own.id=199
        self.world.avatar.playerVehicleID=199
        self.world.entities[199]=own
        def require_avatar(**kwargs):
            explicit=kwargs.get('avatar')
            return (explicit is self.world.avatar and self.world.entity(199) is own,None)
        self.item.canActivate=require_avatar
        self.world.avatar.vehicle=None
        for mode in ('sniper','strategic','trajectory','arcade'):
            self.panel.camera_mode=mode
            self.assertEqual(self.mod._probe_medkit(self.panel),(3,'ready'))


    def test_83_event_subscribers_use_global_scope(self):
        events=[(name,scope) for (name,scope),subs in self.bus.listeners.items() if subs]
        self.assertEqual(set(events),{('onComponentRegistered','global'),('onComponentUnRegistered','global')})

    def test_84_no_monkeypatch_ever_installed(self):
        self.assertIs(Panel._populate,self.orig_populate)
        self.assertIs(Panel._dispose,self.orig_dispose)
        self.visible_start()
        self.emit_unregister()
        self.assertIs(Panel._populate,self.orig_populate)
        self.assertIs(Panel._dispose,self.orig_dispose)

    def test_85_unrelated_component_registration_ignored(self):
        self.emit_unregister()
        self.emit_register(Panel(self.item),alias='minimap')
        self.assertIsNone(self.mod._panel)
        self.assertEqual(self.world.jobs,{})

    def test_86_unrelated_component_unregistration_ignored(self):
        self.emit_unregister(alias='minimap')
        self.assertIs(self.mod._panel,self.panel)
        self.assertTrue(self.world.jobs)

    def test_87_stale_unregistration_preserves_active_component(self):
        self.emit_unregister(component=Panel(self.item))
        self.assertIs(self.mod._panel,self.panel)

    def test_88_duplicate_registration_is_idempotent(self):
        original_jobs=dict(self.world.jobs)
        self.emit_register()
        self.assertEqual(self.world.jobs,original_jobs)
        self.assertIs(self.mod._panel,self.panel)

    def test_89_new_panel_registration_replaces_old_one(self):
        overlay=self.visible_start()
        other=Panel(self.item)
        self.emit_register(other)
        self.assertIs(self.mod._panel,other)
        self.assertEqual(self.gui.roots,[])
        self.assertFalse(overlay.visible)
        self.assertEqual(len(self.world.jobs),1)

    def test_90_event_unregistration_works_before_native_dispose(self):
        self.visible_start()
        self.emit_unregister()
        self.assertEqual(self.gui.roots,[])
        self.assertEqual(self.world.jobs,{})
        self.assertEqual(self.panel.orig_disposed,0)
        self.panel._dispose()
        self.assertEqual(self.panel.orig_disposed,1)

    def test_91_init_is_idempotent(self):
        counts={k:len(v) for k,v in self.bus.listeners.items()}
        self.mod.init()
        self.assertEqual({k:len(v) for k,v in self.bus.listeners.items()},counts)

    def test_92_fini_does_not_leave_event_handlers(self):
        self.visible_start()
        self.mod.fini()
        self.assertEqual(sum(map(len,self.bus.listeners.values())),0)
        self.assertEqual(self.world.jobs,{})
        self.assertEqual(self.gui.roots,[])
        self.emit_register()
        self.assertIsNone(self.mod._panel)

    def test_93_changed_slot_count_skips_entire_panel(self):
        self.emit_unregister()
        p=Panel(self.item)
        p._PANEL_MAX_LENGTH=13
        self.emit_register(p)
        self.assertIsNone(self.mod._panel)
        self.assertEqual(self.world.jobs,{})

    def test_94_changed_equipment_range_skips_panel(self):
        self.emit_unregister()
        p=Panel(self.item)
        p._EQUIPMENT_START_IDX=4
        self.emit_register(p)
        self.assertIsNone(self.mod._panel)
        self.assertEqual(self.gui.roots,[])

    def test_95_nondefault_layout_skips_panel(self):
        self.emit_unregister()
        p=Panel(self.item)
        p._getPanelSettings=lambda:3
        self.emit_register(p)
        self.assertIsNone(self.mod._panel)

    def test_96_invalid_panel_mask_bits_skip_registration(self):
        self.emit_unregister()
        p=Panel(self.item)
        p._mask=1<<14
        self.emit_register(p)
        self.assertIsNone(self.mod._panel)

    def test_97_mask_shape_change_while_battle_hides_overlay(self):
        overlay=self.visible_start()
        self.panel._mask=1<<13
        self.state()
        self.assertFalse(self.mod._overlay_active)
        self.assertFalse(overlay.visible)
        self.assertEqual(len(self.gui.roots),1)
        self.assertIn('incompatible_hud_',self.mod._last_reason)

    def test_98_invalid_cds_array_skips_registration(self):
        self.emit_unregister()
        p=Panel(self.item)
        p._cds=[1,2,3]
        self.emit_register(p)
        self.assertIsNone(self.mod._panel)

    def test_99_missing_native_glow_tracking_skips_registration(self):
        self.emit_unregister()
        p=Panel(self.item)
        p._equipmentsGlowCallbacks=None
        self.emit_register(p)
        self.assertIsNone(self.mod._panel)

    def test_100_missing_visibility_method_skips_registration(self):
        self.emit_unregister()
        p=Panel(self.item)
        p.as_isVisibleS=None
        self.emit_register(p)
        self.assertIsNone(self.mod._panel)

    def test_101_slot_mask_mismatch_never_draws(self):
        self.panel._mask=(63 & ~(1<<3))
        self.state(15)
        self.assertFalse(self.gui.roots)
        self.assertIn('incompatible_hud_',self.mod._last_reason)

    def test_102_slot_array_mismatch_never_draws(self):
        self.panel._cds[3]=None
        self.state(15)
        self.assertFalse(self.gui.roots)
        self.assertIn('medkit_unavailable',self.mod._last_reason)

    def test_103_missing_GUISimple_disables_before_native_allocation(self):
        self.gui.Simple=None
        self.state(10)
        self.assertTrue(self.mod._graphics_disabled)
        self.assertEqual(self.gui.roots,[])

    def test_104_missing_GUI_enum_disables_before_native_allocation(self):
        old=Component.eMaterialFX.BLEND
        try:
            Component.eMaterialFX.BLEND=None
            self.state(10)
            self.assertTrue(self.mod._graphics_disabled)
            self.assertEqual(self.gui.roots,[])
            self.assertFalse(self.gui.calls)
        finally:
            Component.eMaterialFX.BLEND=old

    def test_105_missing_ResMgr_isFile_disables_before_native_allocation(self):
        self.resmgr.isFile=None
        self.state(10)
        self.assertTrue(self.mod._graphics_disabled)
        self.assertEqual(self.gui.roots,[])

    def test_106_missing_BigWorld_entity_disables_graphics_safely(self):
        # For the probe, provide an arcade-only vehicle so the state is ready.
        self.world.entity=None
        self.state(10)
        self.assertTrue(self.mod._graphics_disabled)
        self.assertEqual(self.gui.roots,[])

    def test_107_failed_second_event_listener_rolls_back_first(self):
        self.mod.fini()
        self.bus.fail_on='onComponentUnRegistered'
        self.mod.init()
        self.assertEqual(self.mod._event_listeners,[])
        self.assertEqual(sum(map(len,self.bus.listeners.values())),0)
        self.assertIsNone(self.mod._panel)

    def test_108_missing_event_API_does_not_hook_panel(self):
        self.mod.fini()
        with patch.dict(sys.modules,{'gui.shared.events':types.ModuleType('gui.shared.events')}):
            self.mod.init()
        self.assertEqual(self.mod._event_listeners,[])
        self.assertIs(Panel._populate,self.orig_populate)
        self.assertIs(Panel._dispose,self.orig_dispose)

    def test_109_unrecognised_HUD_alias_does_not_trigger(self):
        self.emit_unregister()
        self.emit_register(Panel(self.item),alias='prebattleAmmunitionPanel')
        self.assertIsNone(self.mod._panel)

    def test_110_dynamic_layout_change_hides_then_recovers(self):
        overlay=self.visible_start()
        self.panel._getPanelSettings=lambda:3
        self.state()
        self.assertFalse(overlay.visible)
        self.panel._getPanelSettings=lambda:0
        self.state(8)
        self.assertTrue(self.mod._overlay_active)
        self.assertEqual(self.gui.roots,[overlay])

    def test_111_other_compact_in_medkit_slot_is_not_highlighted(self):
        self.panel._cds[3]=999
        self.state(12)
        self.assertEqual(self.gui.roots,[])

    def test_112_no_new_dependencies_or_swf_modification(self):
        code=SOURCE.read_text()
        self.assertIn('ComponentEvent.COMPONENT_REGISTERED',code)
        self.assertIn('ComponentEvent.COMPONENT_UNREGISTERED',code)
        self.assertNotIn("setattr(ConsumablesPanel",code)
        self.assertNotIn('as_setGlowS(',code)
        self.assertNotIn('battle.swf',code.lower().replace('no sound, swf replacement',''))

    def test_113_retains_camera_independent_medkit_readiness(self):
        vehicle=self.world.avatar.vehicle
        vehicle.id=1234
        self.world.avatar.playerVehicleID=1234
        self.world.entities[1234]=vehicle
        self.world.avatar.vehicle=None
        self.panel.camera_mode='strategic'
        self.assertEqual(self.mod._probe_medkit(self.panel),(3,'ready'))
        self.panel.camera_mode='sniper'
        self.assertEqual(self.mod._probe_medkit(self.panel),(3,'ready'))

    def test_114_reinitialize_after_fini_accepts_next_battle(self):
        self.visible_start()
        self.mod.fini()
        self.mod.init()
        next_panel=Panel(self.item)
        self.emit_register(next_panel)
        self.assertIs(self.mod._panel,next_panel)
        self.state(7)
        self.assertTrue(self.mod._overlay_active)

    def test_115_combat_ready_no_fullscreen_overlay_on_unknown_geometry(self):
        self.panel._cds=[None]*12
        self.state(12)
        self.assertFalse(self.gui.roots)
        self.assertEqual(self.mod._panel,self.panel)

    def test_116_mask_negative_refuses_unsafe_layout(self):
        self.panel._mask=-1
        self.state(9)
        self.assertFalse(self.gui.roots)
        self.assertIn('incompatible_hud_',self.mod._last_reason)

    def test_117_regression_exact_texture_paths_and_pulse_preserved(self):
        self.visible_start()
        self.assertEqual(self.mod.FRAME_LEVELS,20)
        self.assertEqual(self.mod.HALF_PULSE,2.0)
        self.assertEqual(self.mod.PULSE_TICK,0.1)
        self.assertEqual([self.animate_at(t) for t in (0,1,2,3,4)],[0,10,20,10,0])


    def test_118_voice_after_one_second_exactly_once(self):
        self.state()
        detected=self.world.clock
        self.state(3)
        self.assertEqual(self.audio_plays,[])
        self.state()
        self.assertEqual(self.audio_plays,[(detected+1.0,self.mod.READY_VOICE_EVENT)])
        self.state(15)
        self.assertEqual(len(self.audio_plays),1)
        self.state()
        self.assertEqual(self.audio_plays[-1],(detected+5.0,self.mod.READY_VOICE_EVENT))
        self.state(16)
        self.assertEqual(self.audio_plays[-1],(detected+9.0,self.mod.READY_VOICE_EVENT))
        self.assertEqual(len(self.audio_plays),3)

    def test_119_sound_handles_are_reused_during_ready_interval(self):
        self.state(65)
        self.assertEqual(self.audio_gets,[self.mod.READY_VOICE_EVENT])
        self.assertEqual(len(self.audio_plays),4)

    def test_120_cooldown_stops_audio_and_next_ready_rearms_voice(self):
        self.visible_start()
        self.item.isAvailableToUse=False
        self.state()
        self.assertIn(self.mod.READY_VOICE_EVENT,self.audio_stops)
        before=list(self.audio_plays)
        self.state(24)
        self.assertEqual(self.audio_plays,before)
        self.item.isAvailableToUse=True
        self.state(5)
        self.assertEqual(self.audio_plays[-1][1],self.mod.READY_VOICE_EVENT)
        self.assertEqual(len(self.audio_plays),len(before)+1)

    def test_121_hidden_hud_pauses_without_repeating_voice(self):
        self.visible_start()
        self.panel.native_visible=False
        self.state(30)
        self.assertEqual(len(self.audio_plays),1)
        self.assertIn(self.mod.READY_VOICE_EVENT,self.audio_stops)
        self.panel.native_visible=True
        self.state(5)
        self.assertEqual(len(self.audio_plays),1)
        self.state(16)
        self.assertEqual([event for _,event in self.audio_plays],
                         [self.mod.READY_VOICE_EVENT]*2)

    def test_122_hidden_hud_still_tracks_cooldown(self):
        self.visible_start()
        self.panel.native_visible=False
        self.item.isAvailableToUse=False
        self.state()
        self.item.isAvailableToUse=True
        self.state(30)
        self.assertEqual(len(self.audio_plays),1)
        self.panel.native_visible=True
        self.state(5)
        self.assertEqual([event for _,event in self.audio_plays],
                         [self.mod.READY_VOICE_EVENT]*2)

    def test_123_camera_switch_does_not_repeat_or_delay_voice(self):
        self.visible_start()
        for camera in ('sniper','strategic','trajectory','arcade'):
            self.panel.camera_mode=camera
            self.panel.isActive=False
            self.state(4)
        self.assertEqual(len(self.audio_plays),2)
        self.assertEqual(self.audio_plays[-1][1],self.mod.READY_VOICE_EVENT)

    def test_124_frame_stall_emits_only_one_reminder(self):
        self.visible_start()
        self.world.clock+=60.0
        self.state()
        self.assertEqual(len(self.audio_plays),2)
        self.state(15)
        self.assertEqual(len(self.audio_plays),2)
        self.state()
        self.assertEqual(len(self.audio_plays),3)

    def test_voice_failure_never_falls_back_to_native_sound(self):
        self.audio_fail.add(self.mod.READY_VOICE_EVENT)
        self.visible_start()
        self.state(40)
        self.assertTrue(self.mod._overlay_active)
        self.assertEqual(self.audio_plays,[])
        self.assertEqual(self.audio_gets,[self.mod.READY_VOICE_EVENT])

    def test_hotkey_disables_and_restores_reminder_for_battle(self):
        event=types.SimpleNamespace(key=50,isKeyDown=lambda:True,
            isRepeatedEvent=lambda:False,isCtrlDown=lambda:True,
            isAltDown=lambda:True,isShiftDown=lambda:False)
        self.visible_start()
        self.key_event.emit(event)
        self.assertFalse(self.mod._overlay_active)
        before=list(self.audio_plays)
        self.state(40)
        self.assertEqual(self.audio_plays,before)
        self.key_event.emit(event)
        self.state(6)
        self.assertTrue(self.mod._overlay_active)
        self.assertEqual(self.audio_plays[-1][1],self.mod.READY_VOICE_EVENT)
        self.emit_unregister()
        self.assertEqual(self.key_event.handlers,[])
        self.emit_register()
        self.assertTrue(self.mod._reminder_enabled)

    def test_hotkey_ignores_chat_and_repeat(self):
        event=types.SimpleNamespace(key=50,isKeyDown=lambda:True,
            isRepeatedEvent=lambda:False,isCtrlDown=lambda:True,
            isAltDown=lambda:True,isShiftDown=lambda:False)
        self.chat_focused=True
        self.key_event.emit(event)
        self.chat_focused=False
        event.isRepeatedEvent=lambda:True
        self.key_event.emit(event)
        self.assertTrue(self.mod._reminder_enabled)

    def test_audio_diagnostics_identify_resolved_config_without_listing_other_mods(self):
        class Section:
            def __init__(self, value='', children=None):
                self.asString=value
                self.children=children or {}
            def __getitem__(self, key): return self.children.get(key)
            def values(self): return list(self.children.values())
        banks=Section(children={'a':Section('other-private-name.bnk'),
                                'b':Section(' ', {'name':Section('staysharp_medkit.bnk')})})
        self.resmgr.openSection=lambda path:Section(children={'loadBanks':banks})
        with patch.object(self.mod, '_log') as log:
            self.mod._audio_diagnostics()
        messages='\n'.join(call.args[0] for call in log.call_args_list)
        self.assertIn('bank_visible=True',messages)
        self.assertIn('bank_entry=yes',messages)
        self.assertNotIn('other-private-name',messages)
        self.missing.add('audioww/staysharp_medkit.bnk')
        self.resmgr.openSection=lambda path:Section(children={'loadBanks':Section()})
        with patch.object(self.mod, '_log') as log:
            self.mod._audio_diagnostics()
        messages='\n'.join(call.args[0] for call in log.call_args_list)
        self.assertIn('bank_visible=False',messages)
        self.assertIn('bank_entry=no',messages)

    def test_voice_diagnostics_record_attempts_without_claiming_audibility(self):
        with patch.object(self.mod, '_log') as log:
            self.state(21)
            self.emit_unregister()
        messages='\n'.join(call.args[0] for call in log.call_args_list)
        self.assertIn('audio create event=staysharp_medkit_ready',messages)
        self.assertIn('audio handle present=True',messages)
        self.assertIn('audio play attempt=1 result=none isPlaying=unknown audible=unknown',messages)
        self.assertIn('audio play attempt=2 result=none isPlaying=unknown audible=unknown',messages)
        self.assertIn('audio battle_end attempts=2 failures=0 disabled=False',messages)

    def test_diagnostic_exception_redacts_values_and_does_not_disable_audio(self):
        def failed(path):
            raise ValueError('private user path and arbitrary content')
        self.resmgr.openSection=failed
        with patch.object(self.mod, '_log') as log:
            self.mod._audio_diagnostics()
        messages='\n'.join(call.args[0] for call in log.call_args_list)
        self.assertIn('bank_entry=unknown',messages)
        self.assertIn('exception=ValueError',messages)
        self.assertNotIn('private user path',messages)
        self.visible_start()
        self.assertEqual(self.audio_plays[-1][1],self.mod.READY_VOICE_EVENT)

    def test_128_destroyed_vehicle_cancels_audio(self):
        self.visible_start()
        self.world.avatar.vehicle.health=0
        self.state(30)
        self.assertEqual(len(self.audio_plays),1)
        self.assertIn(self.mod.READY_VOICE_EVENT,self.audio_stops)

    def test_129_battle_end_cancels_audio(self):
        self.visible_start()
        self.world.avatar.arena.period=4
        self.state(30)
        self.assertEqual(len(self.audio_plays),1)
        self.assertIsNone(self.mod._audio_key)

    def test_130_no_audio_before_battle_or_without_perk(self):
        self.world.avatar.arena.period=2
        self.state(24)
        self.assertEqual(self.audio_plays,[])
        self.world.avatar.arena.period=3
        self.world.avatar.vehicle.perkEffects={'equipment':[]}
        self.state(24)
        self.assertEqual(self.audio_plays,[])

    def test_131_no_audio_in_replay_or_spectator(self):
        self.panel.sessionProvider.isReplayPlaying=True
        self.state(24)
        self.assertEqual(self.audio_plays,[])
        self.panel.sessionProvider.isReplayPlaying=False
        self.world.avatar.isObserver=lambda:True
        self.state(24)
        self.assertEqual(self.audio_plays,[])

    def test_132_disposal_cancels_audio_and_all_callbacks(self):
        self.visible_start()
        self.emit_unregister()
        self.assertEqual(self.world.jobs,{})
        self.assertIn(self.mod.READY_VOICE_EVENT,self.audio_stops)
        self.assertIsNone(self.mod._audio_key)

    def test_133_next_battle_retries_previously_failed_voice(self):
        self.audio_fail.add(self.mod.READY_VOICE_EVENT)
        self.visible_start()
        self.emit_unregister()
        self.audio_fail.clear()
        self.emit_register()
        self.visible_start()
        self.assertEqual(self.audio_plays[-1][1],self.mod.READY_VOICE_EVENT)
        self.assertEqual(self.audio_gets.count(self.mod.READY_VOICE_EVENT),2)

    def test_134_native_warning_suppresses_audio(self):
        self.visible_start()
        self.panel._equipmentsGlowCallbacks[3]=1
        self.state(30)
        self.assertEqual(len(self.audio_plays),1)
        self.assertIn(self.mod.READY_VOICE_EVENT,self.audio_stops)

    def test_135_graphics_failure_cannot_leave_audio_running(self):
        self.visible_start()
        self.gui.fail_swap=True
        self.animate_at(2)
        self.assertTrue(self.mod._graphics_disabled)
        self.assertIn(self.mod.READY_VOICE_EVENT,self.audio_stops)
        self.assertIsNone(self.mod._audio_next_reminder)

    def test_playback_false_disables_audio_without_native_fallback(self):
        self.sounds[self.mod.READY_VOICE_EVENT]=types.SimpleNamespace(play=lambda:False,stop=lambda:None)
        self.visible_start()
        self.assertEqual(self.audio_plays,[])
        self.assertTrue(self.mod._voice_disabled)


    def write_language_config(self, value):
        path=self.game/'mods'/'configs'/'staysharp.medkit.json'
        path.write_text(json.dumps(value),encoding='utf-8')
        return path

    def test_137_missing_config_is_created_with_auto_language(self):
        path=self.game/'mods'/'configs'/'staysharp.medkit.json'
        self.assertEqual(json.loads(path.read_text()),{'language':'auto'})

    def test_138_all_manual_languages_select_their_own_voice(self):
        for language in ('en','pl','ru','fr','de','es','uk'):
            with self.subTest(language=language):
                path=self.write_language_config({'language':language})
                before=path.read_bytes()
                self.mod._load_language()
                self.mod._voice_player=None
                self.mod._play_ready_voice()
                expected='staysharp_medkit_ready'+('' if language=='en' else '_'+language)
                self.assertEqual(self.audio_plays[-1][1],expected)
                self.assertEqual(path.read_bytes(),before)

    def test_139_auto_follows_game_language_and_region(self):
        for game,expected in [('pl','pl'),('uk-UA','uk'),('fr_FR','fr'),(' DE ','de'),('en-US','en')]:
            with self.subTest(game=game):
                self.client_language=game
                self.mod._load_language()
                self.assertEqual(self.mod._language,expected)

    def test_140_unknown_or_unavailable_game_language_falls_back_to_english(self):
        for game in ('ja',None,12,[],True,''):
            self.client_language=game
            self.mod._load_language()
            self.assertEqual(self.mod._language,'en')
        with patch('helpers.getClientLanguage',side_effect=RuntimeError('not ready')):
            self.mod._load_language()
            self.assertEqual(self.mod._language,'en')

    def test_141_manual_language_overrides_client(self):
        self.client_language='ru'
        self.write_language_config({'language':'pl'})
        self.mod._load_language()
        self.state(5)
        self.assertEqual(self.audio_plays[-1][1],'staysharp_medkit_ready_pl')

    def test_142_bad_values_fall_back_to_auto_without_overwriting(self):
        self.client_language='pl'
        for value in (None,[],False,12,{'language':False},{'language':[]},{'language':'xx'}):
            with self.subTest(value=value):
                path=self.write_language_config(value)
                before=path.read_bytes()
                self.mod._load_language()
                self.assertEqual(self.mod._language,'pl')
                self.assertEqual(path.read_bytes(),before)

    def test_143_malformed_oversized_and_bom_configs(self):
        self.client_language='uk'
        path=self.write_language_config({})
        for raw in (b'{oops',b'\xff',b' '*4097+b'{}'):
            path.write_bytes(raw)
            self.mod._load_language()
            self.assertEqual(self.mod._language,'uk')
            self.assertEqual(path.read_bytes(),raw)
        path.write_bytes(b'\xef\xbb\xbf'+b'{"language":"de"}')
        self.mod._load_language()
        self.assertEqual(self.mod._language,'de')

    def test_144_empty_object_uses_auto_and_manual_region_is_normalized(self):
        self.client_language='es'
        self.write_language_config({})
        self.mod._load_language()
        self.assertEqual(self.mod._language,'es')
        self.write_language_config({'language':'PL_pl'})
        self.mod._load_language()
        self.assertEqual(self.mod._language,'pl')

    def test_145_config_read_errors_do_not_disable_reminder(self):
        self.client_language='fr'
        with patch('builtins.open',side_effect=PermissionError('locked')):
            self.mod._load_language()
        self.visible_start()
        self.assertEqual(self.mod._language,'fr')
        self.assertEqual(self.audio_plays[-1][1],'staysharp_medkit_ready_fr')

    def test_146_configuration_does_not_require_appdata(self):
        self.write_language_config({'language':'de'})
        with patch.dict(os.environ,{},clear=True), patch.object(self.mod,'_log'):
            self.mod._load_language()
        self.assertEqual(self.mod._language,'de')

    def test_147_no_config_reads_during_state_or_animation(self):
        self.visible_start()
        # Editing is intentionally applied only after restarting the mod/game.
        self.write_language_config({'language':'pl'})
        with patch.object(self.mod,'_load_language',side_effect=AssertionError('unexpected reload')):
            self.state(32)
            self.animate_at(2)
        self.assertEqual(self.mod._language,'en')
        self.assertEqual(self.audio_plays[-1][1],self.mod.READY_VOICE_EVENT)

    def test_localized_voice_failure_is_silent(self):
        self.write_language_config({'language':'pl'})
        self.mod._load_language()
        self.audio_fail.add('staysharp_medkit_ready_pl')
        self.visible_start()
        self.assertEqual(self.audio_plays,[])
        self.assertTrue(self.mod._overlay_active)

    def test_149_resolver_wins_over_another_installation_cwd(self):
        self.write_language_config({'language':'pl'})
        with tempfile.TemporaryDirectory() as other:
            root=Path(other)
            (root/'mods').mkdir()
            (root/'paths.xml').write_text('<root/>')
            with patch.object(os,'getcwd',return_value=other):
                self.assertEqual(self.mod._config_path(),str(self.game/'mods'/'configs'/'staysharp.medkit.json'))
                self.mod._load_language()
        self.assertEqual(self.mod._language,'pl')

    def test_150_config_is_shared_across_game_versions(self):
        path=self.write_language_config({'language':'uk'})
        for version in ('2.4.1.0','2.5.0.0'):
            (self.game/'mods'/version).mkdir()
            self.assertEqual(Path(self.mod._config_path()),path)
            self.assertFalse((self.game/'mods'/version/'staysharp.medkit.json').exists())
        self.mod._load_language()
        self.assertEqual(self.mod._language,'uk')

    def test_151_old_appdata_configuration_is_ignored(self):
        old=Path(self.temp.name)/'StaySharpMedkit'/'config.json'
        old.write_text('{"language":"ru"}')
        self.client_language='de'
        self.mod._load_language()
        self.assertEqual(self.mod._language,'de')
        self.assertEqual(old.read_text(),'{"language":"ru"}')

    def test_152_fallback_handles_win64_app_directory(self):
        win64=self.game/'win64'
        win64.mkdir()
        self.resmgr.resolveToAbsolutePath=lambda _:None
        self.resmgr.appDirectory=lambda:str(win64)
        with patch.object(os,'getcwd',return_value=self.temp.name):
            self.assertEqual(Path(self.mod._config_path()),self.game/'mods'/'configs'/'staysharp.medkit.json')

    def test_153_ambiguous_or_unavailable_installation_uses_auto_without_writes(self):
        self.resmgr.resolveToAbsolutePath=lambda _:None
        self.resmgr.appDirectory=lambda:str(self.game)
        self.client_language='fr'
        with tempfile.TemporaryDirectory() as other:
            root=Path(other)
            (root/'mods').mkdir()
            (root/'paths.xml').write_text('<root/>')
            with patch.object(os,'getcwd',return_value=other), patch.object(self.mod,'_log'):
                self.assertIsNone(self.mod._config_path())
                with patch('builtins.open',side_effect=AssertionError('unexpected file access')):
                    self.mod._load_language()
            self.assertFalse((root/'mods'/'configs').exists())
        self.assertEqual(self.mod._language,'fr')
        self.resmgr.appDirectory=lambda:self.temp.name
        with patch.object(os,'getcwd',return_value=self.temp.name):
            self.assertIsNone(self.mod._config_path())

    def test_154_native_utf8_unicode_installation_path(self):
        root=Path(self.temp.name)/'Zażółć'/'WoT'
        (root/'mods').mkdir(parents=True)
        (root/'paths.xml').write_text('<root/>')
        self.resmgr.resolveToAbsolutePath=lambda _:str(root/'paths.xml').encode('utf-8')
        self.assertEqual(Path(self.mod._config_path()),root/'mods'/'configs'/'staysharp.medkit.json')
        self.mod._load_language()
        path=root/'mods'/'configs'/'staysharp.medkit.json'
        self.assertTrue(path.exists())
        path.write_text('{"language":"es"}')
        self.mod._load_language()
        self.assertEqual(self.mod._language,'es')


if __name__=='__main__':
    unittest.main(verbosity=2)
