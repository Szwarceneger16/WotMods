import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { resolve, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import vm from 'node:vm';
import readZip from '../read_zip.mjs';

const uiStrings = JSON.parse(await fs.readFile(new URL('../ui_strings.json',import.meta.url),'utf8'));

// Exercise the shipped views with an asynchronous image loader and native model.
// The DOM stub is deliberately small: layout still needs verification in Gameface.
class Element {
    constructor(tag = 'div') {
        this.tagName = tag.toUpperCase(); this.style = {}; this.attributes = {};
        this.listeners = {}; this.children = []; this.parentNode = null;
        this.className = ''; this.textContent = ''; this.scrollTop = 0;
        this.clientHeight = 500; this.disabled = false; this.value = '';
    }
    setAttribute(name, value) { this.attributes[name] = String(value); }
    getAttribute(name) { return this.attributes[name]; }
    appendChild(child) { child.parentNode = this; this.children.push(child); return child; }
    removeChild(child) { this.children.splice(this.children.indexOf(child), 1); child.parentNode = null; }
    get firstChild() { return this.children[0]; }
    get scrollHeight() { return this.children.length * 26; }
    addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
    removeEventListener(type, fn) { this.listeners[type] = (this.listeners[type] || []).filter(x => x !== fn); }
    getBoundingClientRect() { return {top:120,left:0,width:100,height:24}; }
    focus() {}
}

function catalog(withImages = true) {
    return {version:1,scenes:Object.fromEntries(['arcade','sniper','arty_top','arty_trajectory'].map(id => [id, {
        default_step:id === 'arcade' || id === 'sniper' ? 1 : 2,
        frames:Array.from({length:5}, (_, step) => ({step,zoom:id === 'sniper' ? [2,4,8,16,25][step] : null,
            src:withImages ? `scenes/${id}_${step}.jpg` : '',marker_scale:1,ellipse:[95,52]}))
    }]))};
}

async function sourceResources(mod) {
    const modDir = new URL(`../../../mods/${mod}/src/res/gui/gameface/mods/grz_${mod}/`, import.meta.url);
    const version = (await fs.readdir(modDir)).filter(name => /^v\d+_\d+_\d+$/.test(name)).sort().at(-1);
    const dir = new URL(version + '/',modDir);
    const [source, html, css] = await Promise.all(['settings.js','settings.html','settings.css'].map(name => fs.readFile(new URL(name,dir),'utf8')));
    const labels = Object.fromEntries(Object.entries(uiStrings).map(([locale,strings]) =>
        [locale,{...strings.common,...strings[mod]}]));
    const marker = '/* GRZ_UI_STRINGS */ {}';
    assert.equal(source.split(marker).length,2,'Expected a single UI dictionary placeholder');
    return {source:source.replace(marker,() => JSON.stringify(labels)),html,css};
}

async function harness(mod, options = {}) {
    const prefix = mod === 'rangefinder' ? 'rf' : 'at';
    const {source,html,css,catalogSource} = options.resources || await sourceResources(mod);
    const elements = new Map([...html.matchAll(/id="([^"]+)"/g)].map(match => [match[1],new Element()]));
    for (const [id, node] of elements) { node.id = id; }
    const get = name => elements.get(prefix + '-' + name);
    const editor = get('editor'), stage = get('editor-stage'); stage.parentNode = editor;
    for (const name of ['editor-sample','editor-handle','editor-view-controls','editor-choices','editor-scrollbar']) { get(name).parentNode = stage; }
    get('editor-handle').tagName = 'BUTTON'; get('editor-handle').parentNode = get('editor-sample');
    get('editor-sample').className = prefix + '-editor-sample';
    get('editor-view-controls').className = prefix + '-editor-view-controls';
    const document = {documentElement:new Element('html'),body:new Element('body'),
        getElementById:id => elements.get(id),createElement:tag => new Element(tag),
        addEventListener(){},removeEventListener(){}};
    document.documentElement.style.fontSize = '1px';
    const defaults = vm.runInNewContext('(' + source.match(/var defaults = (\{[^\n]+\});/)[1] + ')');
    let state = {config:defaults,language:options.language || 'pl',version:'0.1.8',native_gameface:options.native !== false,
        viewport:{width:1920,height:1080,scale:1},editor_active:false,editor_preview_status:'ready',editor_focus:1,editor_focus_demo:false,
        editor_request_id:0,editor_request_accepted:true,editor_preview_mode:'arcade',editor_preview_variant:'standard',
        preview_increased_zoom:options.increased === true,
        preview_choices:options.previewChoices || [{id:'standard',label:'Standard',modes:['arcade','sniper','arty']}]};
    const listeners = {}, commands = [], images = [], timers = new Map(); let timerId = 0;
    class FakeImage extends Element {
        constructor() { super('img'); this.onload = this.onerror = null; images.push(this); }
        set src(value) { this._src = value; }
        get src() { return this._src; }
        succeed() { if (this.onload) { this.onload(); } }
        fail() { if (this.onerror) { this.onerror(); } }
    }
    document.createElement = tag => tag === 'img' ? new FakeImage() : new Element(tag);
    function settleRequest(args, accepted = true, patch = {}) {
        if (args.request_id !== undefined) {
            state.editor_request_id = args.request_id;
            state.editor_request_accepted = accepted;
        }
        if (accepted) {
            if (args.action === 'editor') {
                state.editor_active = args.active;
                if (!args.active) { state.editor_focus_demo = false; }
            } else if (args.action === 'focus_demo') { state.editor_focus_demo = true; }
            else if (args.action === 'apply') { state.config = JSON.parse(args.settings); }
            if (args.action === 'preview' || (args.action === 'editor' && args.active)) {
                state.editor_scene_id = args.scene_id; state.editor_zoom_step = args.zoom_step;
                state.editor_preview_mode = args.mode; state.editor_preview_variant = args.variant;
                state.editor_preview_status = 'ready'; state.editor_preview_reason = null;
            }
            if (args.focus !== undefined && (args.focus_changed || args.focus !== state.editor_focus)) {
                state.editor_focus = args.focus;
                state.editor_focus_demo = false;
            }
        }
        refresh(patch);
    }
    const owner = {state:JSON.stringify(state),onAction(args) {
        commands.push(JSON.parse(JSON.stringify(args)));
        if (!options.deferPreviews || args.action !== 'preview') { settleRequest(args); }
    }};
    const engine = {whenReady:{then(fn) { fn(); }},on(name, fn) { (listeners[name] ||= []).push(fn); },off(name, fn) { listeners[name] = (listeners[name] || []).filter(x => x !== fn); }};
    function refresh(patch = {}) { state = {...state,...patch}; owner.state = JSON.stringify(state); for (const fn of listeners['viewEnv.onDataChanged'] || []) { fn(); } }
    const window = {model:owner,isDomBuilt:true,engine,
        GRZPreviewScenes:options.resources ? undefined : (options.catalog || catalog(options.images !== false)),
        viewEnv:{addDataChangedCallback(){return 1;},removeDataChangedCallback(){},getClientSizePx(){return state.viewport;},getScale(){return 1;},getViewSizePx(){return {width:1920,height:1080};},resizeViewPx(){}},
        setTimeout(fn){timers.set(++timerId,fn);return timerId;},clearTimeout(id){timers.delete(id);},addEventListener(){},removeEventListener(){}};
    const context = vm.createContext({window,document,console,Date});
    if (options.resources) {
        vm.runInContext(catalogSource,context,{filename:mod+'/preview_scenes.js'});
        assert.equal(window.GRZPreviewScenes?.version,1,'Missing packaged scene catalog');
    }
    vm.runInContext(source,context,{filename:mod+'/settings.js'});
    const api = window[mod === 'rangefinder' ? 'GRZRangefinderSettings' : 'GRZAimTimerSettings'];
    const event = (type, delta, target = stage, stamp = 100) => ({type,deltaY:delta,deltaX:0,deltaMode:0,target,timeStamp:stamp,cancelable:true,
        defaultPrevented:false,stopPropagation(){this.stopped=true;},preventDefault(){this.defaultPrevented=true;}});
    const dispatch = (node, e) => { for (const fn of node.listeners[e.type] || []) { fn(e); } return e; };
    const wheel = (delta, stamp = 100, target = stage, type = 'wheel') => dispatch(editor,event(type,delta,target,stamp));
    const click = name => get(name).onclick({stopPropagation(){},preventDefault(){}});
    return {api,get,commands,images,refresh,settleRequest,wheel,click,event,dispatch,editor,stage,css,html,source,document,
        catalog:window.GRZPreviewScenes,getState:()=>state};
}

export async function run(mod) {
    const cases = [];
    {
        {
            const h = await harness(mod,{images:false});
            const status = h.get('editor-preview-status');
            const expectedLocales = ['de','en','es','fr','pl','ru','uk'];
            assert.deepEqual(Object.keys(uiStrings).sort(),expectedLocales);
            h.api.openEditor('arty');
            for (const locale of [...expectedLocales,'unsupported']) {
                const canonical = uiStrings[locale] ? locale : 'en';
                const {common,[mod]:modStrings} = uiStrings[canonical];
                h.refresh({language:locale,editor_preview_status:'ready',editor_preview_reason:'battle-panels-mounted'});
                assert.equal(h.document.documentElement.getAttribute('lang'),canonical);
                assert.equal(h.document.title,modStrings['footer-title']);
                assert.equal(h.get('enabled').getAttribute('aria-label'),modStrings.enabled);
                if (mod === 'rangefinder') {
                    assert.equal(h.get('hide-stock-rangefinder-label').textContent,modStrings['hide-stock-rangefinder']);
                    assert.equal(h.get('hide-stock-rangefinder').getAttribute('title'),modStrings['hide-stock-rangefinder-help']);
                }
                assert.equal(h.get('editor-handle').getAttribute('aria-label'),common['editor-move']);
                assert.equal(h.get('editor-focus-demo').textContent,common['focus-demo']);
                assert.equal(status.textContent,common['editor-ready-battle-panels-mounted']);
                const sample = mod === 'aimtimer' ? ['~1','85 s'] : ['1500','5 m'];
                assert.equal(h.get('editor-reading').textContent,sample.join(common['decimal-separator']));
                h.refresh({editor_preview_status:'partial',editor_preview_reason:'battle-panel-sample-incomplete'});
                assert.equal(status.textContent,common['editor-partial-battle-panel-sample-incomplete']);
            }
            h.api.destroy(); cases.push(mod+': all seven client languages and English fallback');
        }
        if (mod === 'rangefinder') {
            const h = await harness(mod);
            const checkbox = h.get('hide-stock-rangefinder');
            const legacy = {...h.getState().config,threshold_m:275,preview_variant_sniper:'standard'};
            delete legacy.hide_stock_rangefinder;
            h.refresh({config:legacy});
            assert.equal(checkbox.getAttribute('aria-checked'),'false');
            assert.match(h.html,/<button id="rf-hide-stock-rangefinder"[^>]+role="checkbox"[^>]+aria-labelledby="rf-hide-stock-rangefinder-label"/);
            assert.equal(h.get('apply').disabled,false);
            h.refresh({config:{...legacy,hide_stock_rangefinder:'true'}});
            assert.equal(h.get('apply').disabled,true);
            h.refresh({config:legacy});
            h.click('hide-stock-rangefinder');
            assert.equal(checkbox.getAttribute('aria-checked'),'true');
            assert.equal(h.getState().config.hide_stock_rangefinder,undefined);
            h.api.openEditor('arty');
            const opening = h.commands.findLast(command => command.action === 'editor' && command.active);
            assert.equal(opening.hide_stock_distance,true);
            h.api.closeEditor(false);
            assert.equal(h.getState().config.hide_stock_rangefinder,undefined);
            h.api.openEditor('sniper');
            h.click('editor-save');
            const saved = JSON.parse(h.commands.findLast(command => command.action === 'apply').settings);
            assert.equal(saved.hide_stock_rangefinder,true);
            assert.equal(saved.threshold_m,275);
            checkbox.checked = false;
            h.refresh();
            assert.equal(checkbox.getAttribute('aria-checked'),'true');
            h.click('reset');
            assert.equal(checkbox.getAttribute('aria-checked'),'false');
            assert.equal(h.getState().config.hide_stock_rangefinder,true);
            h.click('apply');
            assert.equal(h.getState().config.hide_stock_rangefinder,false);
            h.api.destroy(); cases.push(mod+': stock distance checkbox persists with current and legacy settings');
        }
        {
            const h = await harness(mod);
            assert.doesNotMatch(h.source,/capture_helper|sendCapture/);
            assert.doesNotMatch(h.html,/capture-controls|capture-toggle/);
            assert.doesNotMatch(h.html + h.css,/scene-markers?/);
            if (mod === 'aimtimer') { assert.equal(h.get('hide-stock-rangefinder'),undefined); }
            assert.match(h.css,/window-body \{[^}]*overflow-y:auto;/);
            h.api.destroy(); cases.push(mod+': capture connector removed, scrollable settings window');
        }
        {
            const h = await harness(mod,{images:false});
            assert.equal(h.api.openEditor('arcade'),true);
            assert.equal(h.commands.find(x => x.action === 'editor').scene_id,'arcade');
            assert.equal(h.commands.find(x => x.action === 'editor').zoom_step,1);
            assert.equal(h.editor.style.backgroundImage,'none');
            assert.equal(h.get('editor-scene-status').attributes['data-status'],'missing');
            assert.match(h.get('editor-scene-status').textContent,/Brak zapisanego kadru/);
            assert.doesNotMatch(h.css,/editor_battle\.jpg/);
            assert.match(h.css,/editor-choices > button \{[^}]*flex:0 0 24rem;[^}]*max-height:24rem;/);
            assert.match(h.css,/editor-choices \{[^}]*flex-direction:column;/);
            assert.ok(h.html.indexOf('preview_scenes.js') < h.html.indexOf('src="settings.js"'));
            h.wheel(120); assert.equal(h.commands.at(-1).zoom_step,2);
            assert.equal(h.editor.style.backgroundImage,'none');
            const listEvent = h.event('wheel',120,h.get('editor-choices'));
            h.dispatch(h.get('editor-choices'),listEvent);
            assert.equal(listEvent.stopped,true); assert.equal(listEvent.defaultPrevented,true);
            h.api.destroy(); cases.push(mod+': compact list, neutral missing scene, native wheel');
        }
        {
            const h = await harness(mod,{images:false});
            const peer = h.get('editor-peer-sample'), own = h.get('editor-sample');
            const config = h.getState().config;
            assert.equal(h.api.openEditor('sniper'),true);
            assert.equal(peer.style.display,'none');
            const readout = {enabled:true,x:157,y:-49,hud_font_px:22,hud_background_opacity:.45,hud_frame_scale_pct:120};
            h.refresh({editor_peer_readout:readout});
            assert.equal(peer.style.display,'block');
            assert.equal(peer.style.left,'1117px');
            assert.equal(peer.style.top,'491px');
            assert.equal(peer.style.backgroundColor,'rgba(20,20,20,0.45)');
            assert.equal(h.get('editor-peer-reading').style.fontSize,'22px');
            assert.equal(h.get('editor-peer-reading').textContent,mod === 'aimtimer' ? '1500,5 m' : '~1,85 s');
            assert.equal(peer.onmousedown,undefined);
            assert.match(h.css,/editor-peer-sample \{[^}]*pointer-events:none;/);
            assert.equal(own.getAttribute('data-peer-overlap'),'false');

            const overlap = {...readout,x:config.hud_offset_sniper_x,y:config.hud_offset_sniper_y};
            h.refresh({editor_peer_readout:overlap});
            assert.equal(own.getAttribute('data-peer-overlap'),'true');
            h.refresh({editor_peer_readout:{...overlap,enabled:false}});
            assert.equal(peer.style.display,'block');
            assert.equal(peer.getAttribute('data-enabled'),'false');
            assert.equal(h.get('editor-peer-state').textContent,uiStrings.pl.common['enabled-off']);
            assert.equal(own.getAttribute('data-peer-overlap'),'false');

            h.refresh({editor_peer_readout:readout,editor_preview_mode:'arcade'});
            assert.equal(peer.style.display,'none');
            h.refresh({editor_peer_readout:{...readout,x:1e10},editor_preview_mode:'sniper'});
            assert.equal(peer.style.display,'none');
            h.refresh({editor_peer_readout:readout});
            h.click('editor-save');
            const save = h.commands.find(command => command.action === 'apply');
            assert.ok(save);
            const settings = JSON.parse(save.settings);
            assert.equal(settings.hud_offset_sniper_x,config.hud_offset_sniper_x);
            assert.equal(settings.hud_offset_sniper_y,config.hud_offset_sniper_y);
            assert.ok(!('editor_peer_readout' in settings));
            h.api.destroy(); cases.push(mod+': passive peer reading, disabled state, overlap and isolated saving');
        }
        {
            const h = await harness(mod,{native:false,language:'en'}); h.api.openEditor('arcade');
            assert.equal(h.images.length,3);
            assert.equal(h.stage.children.length,3);
            for (const image of [...h.images]) { image.succeed(); }
            assert.equal(h.stage.children.length,0);
            assert.match(h.editor.style.backgroundImage,/arcade_1\.jpg/);
            h.wheel(-120,100); assert.equal(h.commands.at(-1).zoom_step,2);
            h.wheel(-120,104,h.stage,'mousewheel'); assert.equal(h.commands.at(-1).zoom_step,2);
            const count = h.commands.length;
            h.wheel(-120,130); assert.equal(h.commands.length,count); // next frame still loading
            assert.match(h.editor.style.backgroundImage,/arcade_2\.jpg/);
            const third = h.images.find(x => /arcade_3\.jpg$/.test(x.src)); assert.ok(third);
            h.wheel(-120,160); assert.equal(h.commands.length,count); // supersedes frame 3
            const fourth = h.images.find(x => /arcade_4\.jpg$/.test(x.src)); assert.ok(fourth);
            third.succeed(); assert.equal(h.commands.length,count);
            fourth.succeed(); assert.equal(h.commands.at(-1).zoom_step,4);
            assert.match(h.editor.style.backgroundImage,/arcade_4\.jpg/);
            const boundaryCount = h.commands.length; const boundary = h.wheel(-120,190);
            assert.equal(h.commands.length,boundaryCount); assert.equal(boundary.defaultPrevented,true);
            h.wheel(120,220,h.get('editor-handle')); assert.equal(h.commands.length,boundaryCount);
            h.wheel(120,250,h.get('editor-view-controls')); assert.equal(h.commands.length,boundaryCount);
            h.api.closeEditor(false); fourth.succeed();
            assert.equal(h.editor.style.backgroundImage,'none');
            assert.equal(h.get('editor').style.display,'none');
            h.api.destroy(); cases.push(mod+': delayed frames, stale loads, duplicate wheels, bounds and cleanup');
        }
        {
            const scenes = catalog();
            for (const frame of scenes.scenes.arty_trajectory.frames) { frame.src = ''; }
            const h = await harness(mod,{catalog:scenes}); h.api.openEditor('sniper');
            assert.equal(h.get('editor-zoom-level').textContent,'×4');
            for (const image of [...h.images]) { image.succeed(); }
            h.wheel(120); assert.equal(h.get('editor-zoom-level').textContent,'×8');
            const legacyZoom = h.event('mousewheel',0,h.stage,140); legacyZoom.wheelDelta = 120;
            h.dispatch(h.editor,legacyZoom);
            assert.equal(h.get('editor-zoom-level').textContent,'×16');
            h.images.find(x => /sniper_3\.jpg$/.test(x.src)).succeed();
            assert.equal(h.commands.at(-1).zoom_step,3);
            h.wheel(120,170); assert.equal(h.get('editor-zoom-level').textContent,'×25');
            h.images.find(x => /sniper_4\.jpg$/.test(x.src)).succeed();
            assert.equal(h.commands.at(-1).zoom_step,4);
            assert.equal(h.get('editor-zoom-in').disabled,true);
            h.wheel(-120,190); assert.equal(h.get('editor-zoom-level').textContent,'×16');
            assert.match(h.editor.style.backgroundImage,/sniper_3\.jpg/);
            h.api.closeEditor(false); h.api.openEditor('arty');
            assert.equal(h.commands.findLast(x => x.action === 'editor' && x.active).scene_id,'arty_top');
            for (const image of [...h.images]) { image.succeed(); }
            assert.match(h.editor.style.backgroundImage,/arty_top_2\.jpg/);
            h.wheel(120,200); assert.equal(h.commands.at(-1).zoom_step,3);
            assert.match(h.editor.style.backgroundImage,/arty_top_3\.jpg/);
            h.click('editor-arty-trajectory'); assert.equal(h.commands.at(-1).scene_id,'arty_trajectory');
            assert.equal(h.commands.at(-1).zoom_step,2);
            assert.equal(h.editor.style.backgroundImage,'none');
            assert.match(h.get('editor-scene-status').textContent,/trajektorii.*Brak zdjęcia/);
            h.wheel(120,230); assert.equal(h.commands.at(-1).zoom_step,3);
            h.click('editor-view-reset'); assert.equal(h.commands.at(-1).zoom_step,2);
            h.click('editor-arty-top');
            for (const image of [...h.images]) { image.succeed(); }
            assert.equal(h.commands.at(-1).zoom_step,3);
            assert.match(h.editor.style.backgroundImage,/arty_top_3\.jpg/);
            h.click('editor-save');
            const saved = JSON.parse(h.commands.findLast(x => x.action === 'apply').settings);
            assert.equal(Object.hasOwn(saved,'zoom_step'),false); assert.equal(Object.hasOwn(saved,'scene_id'),false);
            h.api.destroy(); cases.push(mod+': all sniper zooms, distinct artillery cameras, reset and unchanged persistence');
        }
        {
            const h = await harness(mod); h.api.openEditor('arcade');
            h.images.find(x => /arcade_1\.jpg$/.test(x.src)).fail();
            assert.equal(h.get('editor-scene-status').attributes['data-status'],'error');
            assert.equal(h.editor.style.backgroundImage,'none');
            h.refresh({editor_scene_id:'arcade',editor_zoom_step:0});
            h.images.find(x => /arcade_0\.jpg$/.test(x.src)).succeed();
            assert.match(h.editor.style.backgroundImage,/arcade_0\.jpg/);
            h.api.destroy(); cases.push(mod+': failed image and authoritative native scene');
        }
        {
            const h = await harness(mod,{deferPreviews:true});
            h.api.openEditor('arty');
            h.refresh({editor_preview_status:'unavailable',editor_preview_reason:'native',editor_focus_supported:false});
            h.images.find(x => /arty_top_2\.jpg$/.test(x.src)).succeed();
            assert.equal(h.get('editor-focus-demo').disabled,true);
            assert.equal(h.get('editor-focus-wide').disabled,true);
            const count = h.commands.length;
            h.click('editor-focus-demo');
            h.click('editor-focus-wide');
            assert.equal(h.commands.length,count);
            h.wheel(120,100);
            h.images.find(x => /arty_top_3\.jpg$/.test(x.src)).succeed();
            const zoom = h.commands.at(-1);
            assert.equal(zoom.scene_id,'arty_top'); assert.equal(zoom.zoom_step,3);
            h.settleRequest(zoom,true,{editor_preview_status:'unavailable',editor_preview_reason:'native'});
            assert.match(h.editor.style.backgroundImage,/arty_top_3\.jpg/);
            h.click('editor-arty-trajectory');
            h.images.find(x => /arty_trajectory_2\.jpg$/.test(x.src)).succeed();
            const trajectory = h.commands.at(-1);
            assert.equal(trajectory.scene_id,'arty_trajectory'); assert.equal(trajectory.zoom_step,2);
            h.settleRequest(trajectory,true,{editor_preview_status:'unavailable',editor_preview_reason:'native'});
            assert.equal(h.get('editor-arty-trajectory').getAttribute('aria-pressed'),'true');
            assert.match(h.editor.style.backgroundImage,/arty_trajectory_2\.jpg/);
            h.wheel(120,140);
            h.images.find(x => /arty_trajectory_3\.jpg$/.test(x.src)).succeed();
            const retry = h.commands.at(-1);
            assert.equal(retry.scene_id,'arty_trajectory'); assert.equal(retry.zoom_step,3);
            h.settleRequest(retry,true,{editor_preview_status:'partial',editor_focus_supported:true,
                editor_preview_reason:'artillery-indicators-unavailable'});
            assert.equal(h.get('editor-preview-status').textContent,
                uiStrings.pl.common['editor-partial-artillery-indicators-unavailable']);
            assert.equal(h.get('editor-focus-demo').disabled,false);
            assert.equal(h.get('editor-focus-wide').disabled,false);
            assert.match(h.editor.style.backgroundImage,/arty_trajectory_3\.jpg/);
            h.click('editor-focus-tight');
            const focus = h.commands.at(-1);
            assert.equal(focus.scene_id,'arty_trajectory'); assert.equal(focus.zoom_step,3);
            assert.equal(focus.focus,2); assert.equal(focus.focus_changed,true);
            h.settleRequest(focus,true,{editor_preview_status:'partial',editor_focus_supported:true,
                editor_preview_reason:'artillery-indicators-unavailable'});
            assert.equal(h.get('editor-focus-tight').getAttribute('aria-pressed'),'true');
            h.refresh({editor_preview_status:'ready',editor_preview_reason:null,editor_focus_supported:false});
            assert.equal(h.get('editor-focus-demo').disabled,true);
            assert.equal(h.get('editor-focus-tight').disabled,true);
            h.api.destroy(); cases.push(mod+': artillery zoom and camera survive an unavailable native reticle');
        }
        for (const [mode,scene,initialStep] of [['arcade','arcade',1],['sniper','sniper',1],['arty','arty_top',2]]) {
            const h = await harness(mod); h.api.openEditor(mode);
            const open = h.commands.findLast(args => args.action === 'editor' && args.active);
            assert.equal(open.focus,1);
            assert.equal(h.get('editor-focus').style.display,'flex');
            assert.equal(h.get('editor-focus-medium').getAttribute('aria-pressed'),'true');
            const decode = step => h.images.findLast(image => image.src === `scenes/${scene}_${step}.jpg`).succeed();
            decode(initialStep);
            h.click('editor-focus-wide');
            assert.equal(h.commands.at(-1).focus,0);
            assert.equal(h.commands.at(-1).focus_changed,true);
            h.click('editor-focus-demo');
            assert.deepEqual(h.commands.at(-1),{action:'focus_demo'});
            assert.equal(h.get('editor-focus-demo').disabled,true);
            h.wheel(120);
            decode(initialStep+1);
            assert.equal(h.commands.at(-1).zoom_step,initialStep+1);
            assert.equal(h.commands.at(-1).focus,0);
            assert.equal(h.commands.at(-1).focus_changed,undefined);
            assert.equal(h.getState().editor_focus_demo,true);
            h.wheel(-120,140);
            h.wheel(-120,170); // Go to a frame that has not decoded yet.
            h.click('editor-focus-wide');
            assert.equal(h.commands.at(-1).focus_changed,true);
            assert.equal(h.commands.at(-1).zoom_step,initialStep);
            assert.equal(h.getState().editor_focus_demo,false);
            decode(initialStep-1);
            assert.equal(h.commands.at(-1).zoom_step,initialStep-1);
            h.click('editor-focus-demo');
            h.refresh({editor_focus:2,editor_focus_demo:false});
            assert.equal(h.get('editor-focus-tight').getAttribute('aria-pressed'),'true');
            assert.equal(h.get('editor-focus-demo').disabled,false);
            h.api.closeEditor(false);
            assert.equal(h.editor.style.display,'none');
            h.api.destroy(); cases.push(mod+': ' + mode + ' presets, animation lifecycle and zoom independence');
        }
        {
            const row = (id,label,modes,extras={}) => ({id,label,modes,...extras});
            const modes = ['arcade','sniper','arty'];
            const note = 'Podgląd celownika. Osobny panel jest dostępny w bitwie.';
            const h = await harness(mod,{images:false,previewChoices:[
                row('standard','Standard',modes),
                row('autoreloader_surge','Przyspieszone doładowanie',['arcade','sniper']),
                row('xi_cav_mod_71','CAV mod. 71',modes,{tier:11,note,coverage:'partial',battle_panel_count:0}),
                row('xi_others','Inny pojazd XI',['arcade'],{tier:11,available:false}),
            ]});
            const choices = () => h.get('editor-choices').children;
            const ids = () => choices().map(node=>node.getAttribute('data-variant'));
            h.api.openEditor('arcade');
            assert.equal(h.get('preview-filters').style.display,'flex');
            assert.deepEqual(ids(),['standard','autoreloader_surge']);
            const count = h.commands.length;
            h.click('preview-vehicles');
            assert.equal(h.get('preview-vehicles').textContent,'Pojazdy XI');
            assert.equal(h.get('preview-vehicles').getAttribute('aria-pressed'),'true');
            assert.deepEqual(ids(),['xi_cav_mod_71','xi_others']);
            assert.equal(choices()[1].disabled,true);
            assert.equal(h.commands.length,count);
            choices()[0].onclick({stopPropagation(){},preventDefault(){}});
            assert.equal(h.commands.at(-1).variant,'xi_cav_mod_71');
            assert.equal(h.get('preview-note').textContent,note);
            assert.match(h.get('editor-preview-status').textContent,/W podglądzie brakuje panelu mechanizmu/);
            h.refresh({editor_preview_status:'partial',editor_preview_reason:'decoration-failed'});
            assert.match(h.get('editor-preview-status').textContent,/Nie udało się wczytać/);
            assert.match(h.get('editor-preview-status').textContent,/W podglądzie brakuje panelu mechanizmu/);
            h.click('editor-save');
            h.api.openEditor('arcade');
            assert.deepEqual(ids(),['xi_cav_mod_71','xi_others']);
            assert.equal(choices()[0].getAttribute('aria-pressed'),'true');
            h.click('preview-mechanics');
            assert.deepEqual(ids(),['standard','autoreloader_surge']);
            assert.equal(h.get('preview-note').style.display,'none');
            h.api.closeEditor(false); h.api.openEditor('arty');
            assert.equal(h.get('preview-filters').style.display,'none');
            assert.deepEqual(ids(),['standard']);
            h.api.destroy(); cases.push(mod+': Tier XI filter, vehicle selection and coverage note');
        }
        {
            const h = await harness(mod,{images:false}); h.api.openEditor('arcade');
            const status = h.get('editor-preview-status');
            const messages = {
                'decoration-missing':/Nie znaleziono zasobu/,
                'decoration-failed':/wczytać dodatkowego wskaźnika/,
                'decoration-timeout':/nie wczytał się w porę/,
                'cassette-unverified':/wyglądu wskaźnika magazynka/,
                'marker-unverified':/wyglądu dodatkowego znacznika działa/,
                'unexpected-reason':/Część wskaźników jest niedostępna/,
            };
            for (const [reason,message] of Object.entries(messages)) {
                h.refresh({editor_preview_status:'partial',editor_preview_reason:reason});
                assert.equal(status.getAttribute('data-status'),'partial');
                assert.match(status.textContent,/Widać .*celownik klienta/);
                assert.match(status.textContent,message);
                assert.equal(status.getAttribute('title'),status.textContent);
                assert.equal(h.get('editor-save').disabled,false);
            }
            h.refresh({editor_preview_status:'partial',editor_preview_reason:'decoration-failed',
                editor_preview_decoration_diagnostic:'timeline-frame'});
            assert.match(status.textContent,/\[timeline-frame\]/);
            h.refresh({editor_preview_decoration_diagnostic:'untrusted-diagnostic'});
            assert.doesNotMatch(status.textContent,/untrusted-diagnostic/);
            h.refresh({editor_preview_status:'partial',editor_preview_reason:'decoration-unverified',
                editor_preview_decoration_diagnostic:null});
            assert.equal(status.getAttribute('data-status'),'partial');
            assert.equal(status.textContent,'Wczytano dodatkowy wskaźnik. Stan wyświetlenia niepotwierdzony.');
            assert.equal(status.getAttribute('title'),status.textContent);
            assert.equal(h.get('editor-save').disabled,false);
            h.refresh({editor_preview_status:'ready',editor_preview_reason:'cassette-unverified'});
            assert.equal(status.getAttribute('data-status'),'ready');
            assert.doesNotMatch(status.textContent,/magazynka/);
            for (const [rendererStatus,reason,message] of [
                ['ready','decoration-mounted',/Wczytano fabryczny celownik i dodatkowy wskaźnik/],
                ['ready','battle-panels-mounted',/Wczytano fabryczny celownik i panele mechanizmu/],
                ['partial','battle-panel-unavailable',/Brakuje co najmniej jednego panelu/],
                ['partial','battle-panel-sample-incomplete',/Podgląd panelu mechanizmu jest niepełny/],
            ]) {
                h.refresh({editor_preview_status:rendererStatus,editor_preview_reason:reason});
                assert.equal(status.getAttribute('data-status'),rendererStatus);
                assert.match(status.textContent,message);
                assert.doesNotMatch(status.textContent,/Sprawdź/);
            }
            h.api.destroy(); cases.push(mod+': partial native reticle status and safe explanation');
        }
        {
            const choices = ['standard','xi_cav_mod_71','xi_bz_79','xi_vz_63p'].map(id => ({
                id,label:id,modes:['arcade'],...id.startsWith('xi_') && {tier:11},
            }));
            const h = await harness(mod,{images:false,deferPreviews:true,previewChoices:choices});
            const status = h.get('editor-preview-status');
            const select = id => h.get('editor-choices').children
                .find(row => row.getAttribute('data-variant') === id)
                .onclick({stopPropagation(){},preventDefault(){}});
            h.api.openEditor('arcade'); h.click('preview-vehicles');
            select('xi_cav_mod_71');
            const cav = h.commands.at(-1);
            select('xi_bz_79');
            const bz = h.commands.at(-1);
            assert.ok(bz.request_id > cav.request_id);
            assert.equal(h.get('editor-save').disabled,true);
            h.settleRequest(cav,true,{editor_preview_status:'partial',editor_preview_reason:'decoration-failed'});
            assert.equal(status.getAttribute('data-status'),'loading');
            assert.doesNotMatch(status.textContent,/dodatkowego wskaźnika/);
            h.settleRequest(bz);
            assert.equal(status.getAttribute('data-status'),'ready');
            assert.equal(h.get('editor-save').disabled,false);
            const accepted = {...h.getState()};
            h.settleRequest(cav,true,{editor_preview_status:'partial',editor_preview_reason:'decoration-failed'});
            assert.equal(status.getAttribute('data-status'),'ready');
            h.refresh(accepted);
            select('xi_vz_63p');
            h.settleRequest(h.commands.at(-1),false);
            assert.equal(status.getAttribute('data-status'),'rejected');
            assert.equal(h.get('editor-save').disabled,false);
            assert.equal(h.get('editor-choices').children.find(row => row.getAttribute('aria-pressed') === 'true')
                .getAttribute('data-variant'),'xi_bz_79');
            select('xi_cav_mod_71');
            h.settleRequest(h.commands.at(-1),true,{editor_preview_status:'partial',editor_preview_reason:'decoration-failed'});
            assert.equal(status.getAttribute('data-status'),'partial');
            h.api.destroy(); cases.push(mod+': profile request ordering, rejected aliases and recovery');
        }
    }
    return {passed:cases.length,cases};
}

async function packageResources(dist, mod, version) {
    const filename = `com.grz.${mod}_${version}.wotmod`;
    const zip = await readZip(new URL(filename,dist));
    const dir = `res/gui/gameface/mods/grz_${mod}/v${version.replaceAll('.','_')}/`;
    const read = name => {
        const entry = zip.get(dir + name);
        assert.ok(entry,`${filename} lacks ${name}`);
        return entry.read().toString('utf8');
    };
    return {
        filename,source:read('settings.js'),html:read('settings.html'),css:read('settings.css'),
        catalogSource:read('preview_scenes.js'),
        resource:name => zip.get(dir + name),
    };
}

// Exercise the exact settings scripts, catalog and image paths from each dist package.
// The wheel and image events still use the virtual Gameface surface from the harness.
export async function runPackageSmoke(dist, mod, version) {
    const cases = [];
    {
        const resources = await packageResources(dist,mod,version);
        const h = await harness(mod,{resources});
        let time = 100;
        const wheel = direction => h.wheel(direction * 120,time += 30);
        const loaded = new Set();
        const finishImages = () => {
            for (const image of h.images) {
                if (loaded.has(image)) { continue; }
                const entry = resources.resource(image.src);
                assert.ok(entry,`${resources.filename} lacks ${image.src}`);
                const png = entry.read();
                assert.equal(png.subarray(0,8).toString('hex'),'89504e470d0a1a0a',`${image.src} is not a PNG`);
                loaded.add(image);
                image.succeed();
            }
        };
        const currentCommand = () => h.commands.findLast(args => args.action === 'preview' ||
            (args.action === 'editor' && args.active));
        const exerciseScene = scene => {
            const frames = h.catalog.scenes[scene].frames;
            finishImages();
            for (let index = frames.findIndex(frame => frame.step === currentCommand().zoom_step); index > 0; index -= 1) {
                wheel(-1);
                finishImages();
            }
            for (const [index, frame] of frames.entries()) {
                const step = frame.step, file = frame.src;
                assert.equal(file,`scenes/${scene}_${step}.png`);
                assert.equal(h.editor.style.backgroundImage,`url("${file}")`);
                assert.equal(h.get('editor-scene-status').getAttribute('data-status'),
                    frame.focus_unmeasured ? 'focus-unmeasured' : 'ready');
                if (frame.focus_unmeasured) {
                    assert.equal(h.get('editor-focus-demo').disabled,true);
                    assert.equal(h.get('editor-focus-tight').disabled,true);
                }
                assert.equal(currentCommand().scene_id,scene);
                assert.equal(currentCommand().zoom_step,step);
                assert.equal(h.get('editor-zoom-level').textContent,
                    scene === 'sniper' ? '\u00d7' + [2,4,8,16,25][step] : `${index+1} / ${frames.length}`);
                if (index < frames.length - 1) { wheel(1); finishImages(); }
            }
            assert.equal(h.get('editor-zoom-in').disabled,true);
            if (frames.length === 1) {
                assert.equal(h.get('editor-zoom-out').disabled,true);
                const count = h.commands.length;
                wheel(1); wheel(-1);
                assert.equal(h.commands.length,count);
            }
        };

        try {
            assert.match(resources.html,/<script src="preview_scenes\.js"><\/script>\s*<script src="settings\.js">/);
            assert.doesNotMatch(resources.source,/capture_helper|sendCapture/);
            assert.doesNotMatch(resources.html,/capture-controls|capture-toggle/);
            assert.doesNotMatch(resources.html + resources.css,/scene-markers?/);

            for (const [mode,scene] of [['arcade','arcade'],['sniper','sniper'],['arty','arty_top']]) {
                assert.equal(h.api.openEditor(mode),true);
                exerciseScene(scene);
                assert.equal(h.get('editor-focus').style.display,'flex');
                h.click('editor-focus-demo');
                assert.deepEqual(h.commands.at(-1),{action:'focus_demo'});
                h.click('editor-focus-tight');
                assert.equal(currentCommand().focus,2);
                assert.equal(currentCommand().focus_changed,true);
                if (mode === 'arty') {
                    h.click('editor-arty-trajectory');
                    exerciseScene('arty_trajectory');
                    const label = h.stage.children.find(node => node.className === 'grz-scene-vehicle-label');
                    assert.ok(label);
                    assert.equal(label.textContent,'ST-II');
                    assert.equal(label.style.left,'849px');
                    assert.equal(label.style.top,'413px');
                    assert.equal(h.get('editor-focus-demo').disabled,false);
                    h.click('editor-focus-wide');
                    assert.equal(currentCommand().focus,0);
                    h.click('editor-focus-demo');
                    assert.deepEqual(h.commands.at(-1),{action:'focus_demo'});
                    h.click('editor-arty-top');
                    finishImages();
                    assert.ok(!h.stage.children.includes(label));
                    assert.equal(h.editor.style.backgroundImage,`url("${h.catalog.scenes.arty_top.frames[4].src}")`);
                }
                h.api.closeEditor(false);
            }
            cases.push(resources.filename + ': captured PNGs, real zoom steps and focus controls');
        } finally { h.api.destroy(); }
    }
    return {passed:cases.length,cases};
}

const [mod, version, dist] = process.argv.slice(2);
assert.ok(['aimtimer','rangefinder'].includes(mod) && /^\d+\.\d+\.\d+$/.test(version) && dist,
    'Expected MOD VERSION DIST');
const results = await run(mod);
const packageResults = await runPackageSmoke(pathToFileURL(resolve(dist) + sep),mod,version);
console.log(`${mod}: ${results.passed} source UI scenarios and ${packageResults.passed} packaged UI scenario passed`);
