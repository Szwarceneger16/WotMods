/* Owned Wulf settings view. Native Python validates and persists every change. */
(function () {
    'use strict';
    if (window.GRZAimTimerSettings) { return; }
    var root = document.getElementById('at-settings'), state = {}, dirty = false, pending = null;
    var previewListKey = '', lastPreviewWheel = null, previewScrollbarDrag = null;
    var previewFilters = {}, filterOptions = ['mechanics','vehicles'];
    var sceneId = null, zoomStep = 0, sceneSteps = {}, sceneChoices = {}, sceneImages = {}, sceneGeneration = 0;
    var sceneStatus = 'missing', sceneImageKey = '', sceneRequestedKey = '', lastSceneWheel = null;
    var editorRequest = null, editorRequestNumber = 0, editorLastAck = 0;
    var editorProfilePending = false, editorRequestRejected = false;
    var editorFocus = 1, focusPresetPending = false, focusOptions = ['wide','medium','tight'];
    var positions = {}, editorMode = null, editorDraft = null, editorShown = false, editorClosing = false, editorTimer = null, editorDrag = null;
    var surface = {width:1280,height:800,scale:1}, editorPanel = {width:100,height:30,scale:1};
    var escapeDown = false, suppressEscapeUntilUp = false;
    var engineOwner = null, viewOwner = null, readyOwner = null, callbackId = null;
    var bound = false, registering = false, destroyed = false, updating = false;
    var resizeTimer = null, resizeAttempts = 0, resizing = false, layoutReported = false;
    var lastWidth = 0, lastHeight = 0, layoutCallbacks = [], layoutReadySeen = {};
    var layoutEvents = ['self.onLoaded', 'self.onTextureReady', 'clientResized', 'self.onScaleUpdated'];
    var logicalWidth = 520, logicalHeight = 320, edgeGutter = 16, nodes = {}, i;
    var ids = ['title','version','x','enabled','enabled-label','position-label','position-arcade','position-sniper','position-arty','font','font-label',
        'opacity','opacity-label','frame','frame-label','feedback','reset','close','apply','editor','editor-title','editor-help','editor-stage','editor-center','editor-profile-label','editor-choices','editor-list-wrap','editor-scrollbar','editor-scrollbar-thumb','editor-preview-status','editor-sample','editor-reading','editor-reference','editor-handle','editor-save','editor-cancel','editor-reset','editor-view-controls','editor-arty-cameras','editor-arty-top','editor-arty-trajectory','editor-zoom-out','editor-zoom-in','editor-zoom-level','editor-view-reset','editor-scene-status'];
    for (i = 0; i < ids.length; i += 1) { nodes[ids[i]] = document.getElementById('at-' + ids[i]); }
    ['peer-reference','peer-sample','peer-reading','peer-state'].forEach(function(name) {
        nodes['editor-' + name] = document.getElementById('at-editor-' + name);
    });
    var previewFilterBar = document.getElementById('at-preview-filters');
    var previewNote = document.getElementById('at-preview-note');
    var previewFilterButtons = filterOptions.map(function(name) { return document.getElementById('at-preview-' + name); });
    var focusPanel = document.getElementById('at-editor-focus');
    var focusLabel = document.getElementById('at-editor-focus-label');
    var focusDemo = document.getElementById('at-editor-focus-demo');
    var focusButtons = focusOptions.map(function(name) { return document.getElementById('at-editor-focus-' + name); });
    var defaults = {schema_version:4,enabled:true,preview_variant_arcade:'standard',preview_variant_sniper:'standard',preview_variant_arty:'standard',hud_offset_arcade_x:0,hud_offset_sniper_x:0,hud_offset_arty_x:0,hud_offset_arcade_y:40,hud_offset_sniper_y:40,hud_offset_arty_y:40,hud_font_px:16,hud_background_opacity:0.5,hud_frame_scale_pct:110};
    var labels = /* GRZ_UI_STRINGS */ {};
    function unwrap(value) { return value && typeof value === 'object' && value.value !== undefined ? value.value : value; }
    function model() { return unwrap(window.model || (window.viewEnv && window.viewEnv.model)); }
    function safeText(value, fallback, max) { return typeof value === 'string' && value.length <= (max || 1024) ? value : fallback; }
    function language() {
        return typeof state.language === 'string' && Object.prototype.hasOwnProperty.call(labels,state.language) ? state.language : 'en';
    }
    function text(key) { return labels[language()][key] || labels.en[key]; }
    function sampleReading(value, unit) {
        return value.replace('.',text('decimal-separator')) + ' ' + unit;
    }
    function stop(event, prevent) {
        if (event && event.stopPropagation) { event.stopPropagation(); }
        if (prevent && event && event.preventDefault) { event.preventDefault(); }
    }
    function number(value, low, high, integer) {
        if (typeof value === 'string') {
            if (!/^\d+(?:[.,]\d+)?$/.test(value)) { return null; }
            value = Number(value.replace(',', '.'));
        }
        if (typeof value !== 'number' || !isFinite(value) || value < low || value > high || (integer && Math.floor(value) !== value)) { return null; }
        return value;
    }
    function validVariant(value) { return typeof value === 'string' && /^[a-z][a-z0-9_-]{0,63}$/.test(value); }
    function normalize(value) {
        if (!value || typeof value !== 'object' || Object.prototype.toString.call(value) === '[object Array]' ||
                value.schema_version !== 4 || typeof value.enabled !== 'boolean' ||
                !validVariant(value.preview_variant_arcade) || !validVariant(value.preview_variant_sniper) || !validVariant(value.preview_variant_arty)) { return null; }
        var arcade = number(value.hud_offset_arcade_y, -32768, 32768, true), sniper = number(value.hud_offset_sniper_y, -32768, 32768, true);
        var arty = number(value.hud_offset_arty_y, -32768, 32768, true), font = number(value.hud_font_px, 12, 40, true);
        var opacity = number(value.hud_background_opacity, 0, 1, false), frame = number(value.hud_frame_scale_pct, 100, 300, true);
        var arcadeX = number(value.hud_offset_arcade_x, -32768, 32768, true), sniperX = number(value.hud_offset_sniper_x, -32768, 32768, true);
        var artyX = number(value.hud_offset_arty_x, -32768, 32768, true);
        if (arcadeX === null || sniperX === null || artyX === null || arcade === null || sniper === null || arty === null || font === null || opacity === null || frame === null) { return null; }
        return {schema_version:4,enabled:value.enabled,
            preview_variant_arcade:value.preview_variant_arcade,preview_variant_sniper:value.preview_variant_sniper,preview_variant_arty:value.preview_variant_arty,
            hud_offset_arcade_x:arcadeX,hud_offset_sniper_x:sniperX,hud_offset_arty_x:artyX,
            hud_offset_arcade_y:arcade,hud_offset_sniper_y:sniper,hud_offset_arty_y:arty,
            hud_font_px:font,hud_background_opacity:opacity,hud_frame_scale_pct:frame};
    }
    function readDraft() {
        var opacity = number(nodes.opacity.value, 0, 100, false);
        return normalize({schema_version:4,enabled:nodes.enabled.checked,
            preview_variant_arcade:positions.arcade.variant,preview_variant_sniper:positions.sniper.variant,preview_variant_arty:positions.arty.variant,
            hud_offset_arcade_x:positions.arcade.x,hud_offset_sniper_x:positions.sniper.x,hud_offset_arty_x:positions.arty.x,
            hud_offset_arcade_y:positions.arcade.y,hud_offset_sniper_y:positions.sniper.y,hud_offset_arty_y:positions.arty.y,
            hud_font_px:nodes.font.value,hud_background_opacity:opacity === null ? null : opacity / 100,hud_frame_scale_pct:nodes.frame.value});
    }
    function fill(config) {
        nodes.enabled.checked = config.enabled;
        positions = copyPositions(config);
        nodes.font.value = String(config.hud_font_px);
        nodes.opacity.value = String(Math.round(config.hud_background_opacity * 10000) / 100); nodes.frame.value = String(config.hud_frame_scale_pct);
    }
    function feedback(message, error) {
        nodes.feedback.textContent = message;
        nodes.feedback.className = error ? 'at-error' : '';
        nodes.feedback.setAttribute('title', message);
    }
    function send(action, config) {
        if (destroyed || !bound) { return false; }
        var owner = model(), command = owner && owner.onAction, args = {action:action};
        if (action === 'apply') { args.settings = JSON.stringify(config); }
        try {
            if (typeof command === 'function') { command.call(owner, args); return true; }
            if (command && typeof command.value === 'function') { command.value.call(command, args); return true; }
        } catch (ignored) { /* The UI retains its draft on a rejected command. */ }
        feedback(text('unavailable'), true);
        return false;
    }
    function renderLabels() {
        var translations = {'title':'title','enabled-label':'enabled','position-label':'position-label','position-arcade':'position-arcade','position-sniper':'position-sniper','position-arty':'position-arty','font-label':'font',
            'opacity-label':'opacity','frame-label':'frame','reset':'reset','close':'close','apply':'apply'}, key;
        for (key in translations) { if (Object.prototype.hasOwnProperty.call(translations,key)) { nodes[key].textContent = text(translations[key]); } }
        nodes.enabled.className = 'at-window-clear' + (nodes.enabled.checked ? ' at-selected' : '');
        nodes.enabled.setAttribute('aria-pressed', nodes.enabled.checked ? 'true' : 'false');
        nodes.enabled.setAttribute('aria-label',text('enabled'));
        document.getElementById('at-enabled-caption').textContent = text(nodes.enabled.checked ? 'enabled-on' : 'enabled-off');
        nodes.x.setAttribute('aria-label',text('close')); nodes.x.setAttribute('title',text('close'));
        document.documentElement.setAttribute('lang', language());
        document.title = text('footer-title');
        var version = safeText(state.version,'',32);
        if (!/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(version)) { version = ''; }
        nodes.version.textContent = version ? 'v' + version : '';
        nodes.version.setAttribute('title', version ? 'GRZ AimTimer v' + version : '');
    }
    function renderFeedback() {
        var valid = readDraft() !== null;
        nodes.apply.disabled = !valid || !bound;
        if (!valid) { feedback(text('invalid'),true); return; }
        var error = safeText(state.error,'',2048), status = safeText(state.status,'',2048);
        if (error) { feedback(error,true); }
        else if (pending !== null) { feedback(text('pending'),false); }
        else if (dirty) { feedback(text('dirty'),false); }
        else { feedback(error || status, !!error); }
    }
    function edited() {
        if (destroyed) { return; }
        dirty = true; pending = null; state.error = ''; renderLabels(); renderFeedback();
    }
    function apply(event) {
        stop(event,true); var config = readDraft();
        if (config === null) { feedback(text('invalid'),true); return; }
        pending = JSON.stringify(config);
        if (!send('apply',config)) { pending = null; return; }
        renderFeedback();
    }
    function close(event) { stop(event,true); send('close'); }
    nodes.apply.onclick = apply; nodes.x.onclick = nodes.close.onclick = close;
    nodes.enabled.onclick = function(event) { stop(event,true); nodes.enabled.checked = !nodes.enabled.checked; edited(); };
    nodes.reset.onclick = function(event) { stop(event,true); fill(defaults); edited(); };
    var fields = ['font','opacity','frame'];
    for (i = 0; i < fields.length; i += 1) { nodes[fields[i]].onchange = edited; nodes[fields[i]].oninput = edited; }

    function copyPositions(config) {
        var result = {}, modes = ['arcade','sniper','arty'], j, mode;
        for (j = 0; j < modes.length; j += 1) { mode = modes[j]; result[mode] = {x:config['hud_offset_' + mode + '_x'], y:config['hud_offset_' + mode + '_y'],variant:config['preview_variant_' + mode]}; }
        return result;
    }
    /* Scene frames are captured in the game; zoom never scales the editor HUD. */
    function sceneForMode(mode) { return mode === 'arty' ? (sceneChoices.arty || 'arty_top') : mode; }
    function sceneMatchesMode(id) { return editorMode === 'arty' ? id === 'arty_top' || id === 'arty_trajectory' : id === editorMode; }
    function sceneLabel(value, fallback) {
        if (value && typeof value === 'object') { value = value[language()] || value.en; }
        return safeText(value, fallback, 160);
    }
    function sceneFrames(id) {
        var catalog = window.GRZPreviewScenes, entry, frames, result = [], seen = {}, j, frame, step, zoom;
        if (catalog && catalog.version === 1 && catalog.scenes && typeof catalog.scenes === 'object') { entry = catalog.scenes[id]; }
        frames = entry && entry.frames;
        if (Object.prototype.toString.call(frames) === '[object Array]') {
            for (j = 0; j < frames.length && j < 5; j += 1) {
                frame = frames[j]; step = frame && number(frame.step,0,4,true);
                if (step === null || !frame || seen[step]) { continue; }
                zoom = number(frame.zoom,0.01,100,false);
                result.push({step:step,zoom:zoom,label:frame.label,focusUnmeasured:frame.focus_unmeasured === true,
                    vehicle:frame.vehicle,frameSize:frame.frame_size,
                    src:typeof frame.src === 'string' && /^scenes\/[a-zA-Z0-9_\/-]+\.(jpg|jpeg|png)$/.test(frame.src) ? frame.src : ''});
                seen[step] = true;
            }
        }
        if (!result.length) {
            for (j = 0; j < 5; j += 1) {
                result.push({step:j,zoom:id === 'sniper' ? [2,4,8,16,25][j] : null,label:null,src:''});
            }
        }
        result.sort(function(a,b) { return a.step - b.step; });
        return result;
    }
    function sceneFrame(id, step) {
        var frames = sceneFrames(id), j;
        for (j = 0; j < frames.length; j += 1) { if (frames[j].step === step) { return frames[j]; } }
        return frames[0];
    }
    function defaultSceneStep(id) {
        var catalog = window.GRZPreviewScenes, entry = catalog && catalog.scenes && catalog.scenes[id];
        var value = entry && number(entry.default_step,0,4,true);
        if (value === null || value === undefined) { value = id === 'sniper' ? 3 : id === 'arcade' ? 1 : 2; }
        return sceneFrame(id,value).step;
    }
    function sceneKey(id, step) { return id + ':' + step; }
    function previewArgs(action) {
        var args = {action:action,mode:editorMode,variant:editorDraft.variant,scene_id:sceneId,zoom_step:zoomStep,focus:editorFocus};
        if (action === 'preview' && focusPresetPending) { args.focus_changed = true; }
        return args;
    }
    function sendScenePreview(focusChanged) {
        if (destroyed || !bound || !editorShown || editorClosing || !editorDraft) { return false; }
        var args = previewArgs('preview');
        if (focusChanged === true) {
            // Keep the native reticle on the visible frame while the zoom image is decoding.
            var nativeStep = number(state.editor_zoom_step,0,4,true);
            if (sceneStatus === 'loading' && sceneMatchesMode(state.editor_scene_id) && nativeStep !== null) {
                args.scene_id = state.editor_scene_id;
                args.zoom_step = nativeStep;
            }
        }
        return sendEditorRequest(args);
    }
    function renderFocusControls() {
        var running = state.editor_focus_demo === true;
        focusPanel.style.display = editorMode ? 'flex' : 'none';
        if (!editorMode) { return; }
        focusLabel.textContent = text('focus-label');
        focusDemo.textContent = text(running ? 'focus-running' : 'focus-demo');
        focusDemo.disabled = !canAnimateFocus();
        var hasReference = !sceneFrame(sceneId,zoomStep).focusUnmeasured;
        focusButtons.forEach(function(button,index) {
            var selected = index === editorFocus;
            button.disabled = !hasReference || state.editor_focus_supported === false;
            button.textContent = text('focus-' + focusOptions[index]);
            button.className = 'at-window-clear' + (selected ? ' at-selected' : '');
            button.setAttribute('aria-pressed',selected ? 'true' : 'false');
        });
    }
    function canChangeFocus() {
        return !destroyed && bound && editorShown && !editorClosing && !editorDrag && !previewScrollbarDrag &&
            !!editorDraft && !sceneFrame(sceneId,zoomStep).focusUnmeasured && state.editor_focus_supported !== false;
    }
    function canAnimateFocus() {
        return canChangeFocus() && !focusPresetPending && !editorProfilePending &&
            state.editor_focus_demo !== true && state.editor_preview_mode === editorMode &&
            state.editor_preview_variant === editorDraft.variant &&
            (state.editor_preview_status === 'ready' || state.editor_preview_status === 'partial');
    }
    focusButtons.forEach(function(button,index) {
        button.onclick = function(event) {
            stop(event,true);
            if (!canChangeFocus()) { return; }
            editorFocus = index;
            focusPresetPending = true;
            renderFocusControls();
            if (!sendScenePreview(true)) { focusPresetPending = false; renderFocusControls(); }
        };
    });
    focusDemo.onclick = function(event) {
        stop(event,true);
        if (canAnimateFocus()) { send('focus_demo'); }
    };
    function removeSceneImage(record) {
        if (record.timer !== null) { window.clearTimeout(record.timer); }
        record.image.onload = record.image.onerror = record.complete = null;
        if (record.image.parentNode) { record.image.parentNode.removeChild(record.image); }
    }
    var sceneVehicleLabel = null;
    function renderSceneVehicle(frame) {
        if (!frame || !frame.vehicle || !frame.frameSize || sceneStatus !== 'ready' ||
            sceneImageKey !== sceneKey(sceneId,frame.step)) {
            if (sceneVehicleLabel) { sceneVehicleLabel.parentNode.removeChild(sceneVehicleLabel); }
            sceneVehicleLabel = null;
            return;
        }
        if (!sceneVehicleLabel) {
            sceneVehicleLabel = document.createElement('span');
            sceneVehicleLabel.className = 'grz-scene-vehicle-label';
            nodes['editor-stage'].appendChild(sceneVehicleLabel);
        }
        var size = frame.frameSize, anchor = frame.vehicle.anchor;
        var cover = Math.max(surface.width / size[0],surface.height / size[1]);
        sceneVehicleLabel.style.left = Math.round(surface.width / 2 + (anchor[0] - size[0] / 2) * cover) + 'px';
        sceneVehicleLabel.style.top = Math.round(surface.height / 2 + (anchor[1] - size[1] / 2) * cover) + 'px';
        sceneVehicleLabel.style.fontSize = Math.max(10,13 * cover) + 'px';
        sceneVehicleLabel.textContent = frame.vehicle.name;
    }
    function releaseSceneImages() {
        renderSceneVehicle(null);
        sceneGeneration += 1;
        for (var key in sceneImages) {
            if (Object.prototype.hasOwnProperty.call(sceneImages,key)) { removeSceneImage(sceneImages[key]); }
        }
        sceneImages = {}; sceneRequestedKey = sceneImageKey = ''; lastSceneWheel = null;
        nodes.editor.style.backgroundImage = 'none';
    }
    function renderSceneControls() {
        if (!editorMode || !sceneId) { return; }
        var frames = sceneFrames(sceneId), index = 0, j, frame = sceneFrame(sceneId,zoomStep), label;
        for (j = 0; j < frames.length; j += 1) { if (frames[j].step === zoomStep) { index = j; break; } }
        label = sceneLabel(frame.label,sceneId === 'sniper' && frame.zoom !== null ? '\u00d7' + frame.zoom : text('editor-level') + ' ' + (index + 1) + '/' + frames.length);
        nodes['editor-zoom-level'].textContent = label;
        nodes['editor-zoom-out'].disabled = index === 0;
        nodes['editor-zoom-in'].disabled = index === frames.length - 1;
        nodes['editor-zoom-out'].setAttribute('aria-label',text('editor-zoom-out'));
        nodes['editor-zoom-in'].setAttribute('aria-label',text('editor-zoom-in'));
        nodes['editor-view-reset'].textContent = text('editor-view-reset');
        nodes['editor-view-controls'].setAttribute('aria-label',text('preview'));
        nodes['editor-arty-cameras'].style.display = editorMode === 'arty' ? 'flex' : 'none';
        renderFocusControls();
        for (j = 0; j < 2; j += 1) {
            var id = j ? 'arty-trajectory' : 'arty-top', selected = sceneId === (j ? 'arty_trajectory' : 'arty_top');
            nodes['editor-' + id].textContent = text('editor-' + id);
            nodes['editor-' + id].className = 'at-window-clear' + (selected ? ' at-selected' : '');
            nodes['editor-' + id].setAttribute('aria-pressed',selected ? 'true' : 'false');
        }
        renderSceneVehicle(frame);
        var notice = sceneStatus === 'ready' && frame.focusUnmeasured ? 'focus-unmeasured' : sceneStatus;
        nodes['editor-scene-status'].style.display = notice === 'ready' ? 'none' : 'block';
        nodes['editor-scene-status'].textContent = notice === 'ready' ? '' : text('editor-scene-' + notice);
        nodes['editor-scene-status'].setAttribute('data-status',notice);
    }
    function loadSceneFrame(notify) {
        if (!editorMode || !sceneId || destroyed || editorClosing) { return; }
        var frames = sceneFrames(sceneId), index = 0, j, frame = sceneFrame(sceneId,zoomStep), key = sceneKey(sceneId,zoomStep), keep = {}, generation = sceneGeneration;
        zoomStep = frame.step; key = sceneKey(sceneId,zoomStep); sceneRequestedKey = key;
        for (j = 0; j < frames.length; j += 1) { if (frames[j].step === zoomStep) { index = j; break; } }
        for (j = Math.max(0,index-1); j <= Math.min(frames.length-1,index+1); j += 1) { keep[sceneKey(sceneId,frames[j].step)] = true; }
        for (var oldKey in sceneImages) {
            if (Object.prototype.hasOwnProperty.call(sceneImages,oldKey) && !keep[oldKey]) {
                removeSceneImage(sceneImages[oldKey]); delete sceneImages[oldKey];
            }
        }
        function display(record) {
            if (destroyed || !editorMode || editorClosing || generation !== sceneGeneration || key !== sceneRequestedKey) { return; }
            sceneStatus = record.status; sceneImageKey = record.status === 'ready' ? key : '';
            nodes.editor.style.backgroundImage = record.status === 'ready' ? 'url("' + record.src + '")' : 'none';
            renderSceneControls();
            if (notify && editorShown) { sendScenePreview(); }
        }
        if (!frame.src) { display({status:sceneId === 'arty_trajectory' ? 'trajectory' : 'missing',src:''}); return; }
        if (sceneImageKey.indexOf(sceneId + ':') !== 0) {
            sceneImageKey = ''; nodes.editor.style.backgroundImage = 'none';
        }
        sceneStatus = 'loading'; renderSceneControls();
        function preload(item, current) {
            var imageKey = sceneKey(sceneId,item.step), record = sceneImages[imageKey];
            if (!item.src) { return; }
            if (record && (record.src !== item.src || (current && record.status === 'error'))) {
                removeSceneImage(record); delete sceneImages[imageKey]; record = null;
            }
            if (!record) {
                record = {image:document.createElement('img'),src:item.src,status:'loading',complete:null,timer:null};
                sceneImages[imageKey] = record;
                record.image.className = 'at-scene-preload';
                record.image.setAttribute('aria-hidden','true');
                var finish = function(status) {
                    if (record.status !== 'loading') { return; }
                    record.status = status;
                    var complete = record.complete;
                    removeSceneImage(record); record.timer = null;
                    if (complete) { complete(record); }
                };
                record.image.onload = function() { finish('ready'); };
                record.image.onerror = function() { finish('error'); };
                if (typeof window.setTimeout === 'function') { record.timer = window.setTimeout(record.image.onerror,2000); }
            }
            record.complete = current ? display : null;
            if (current && record.status !== 'loading') { display(record); }
            if (!record.started) {
                record.started = true;
                nodes['editor-stage'].appendChild(record.image);
                record.image.src = item.src;
            }
        }
        try {
            preload(frame,true);
            for (j = Math.max(0,index-1); j <= Math.min(frames.length-1,index+1); j += 1) { if (j !== index) { preload(frames[j],false); } }
        } catch (ignoredImage) { display({status:'error',src:''}); }
    }
    function selectScene(id, step, notify) {
        if (!editorMode || !sceneMatchesMode(id) || editorClosing) { return; }
        var frame = sceneFrame(id,step);
        if (id === sceneId && frame.step === zoomStep && sceneStatus !== 'error') { return; }
        sceneId = id; zoomStep = frame.step; sceneSteps[id] = zoomStep;
        if (editorMode === 'arty') { sceneChoices.arty = id; }
        loadSceneFrame(notify !== false);
    }
    function changeSceneZoom(direction) {
        if (!editorShown || editorClosing || editorDrag || previewScrollbarDrag) { return; }
        var frames = sceneFrames(sceneId), j, next;
        for (j = 0; j < frames.length; j += 1) {
            if (frames[j].step === zoomStep) {
                next = Math.max(0,Math.min(frames.length-1,j+direction));
                if (next !== j) { selectScene(sceneId,frames[next].step,true); }
                return;
            }
        }
    }
    function syncNativeScene() {
        if (!editorMode || editorRequest || sceneStatus === 'loading' || !sceneMatchesMode(state.editor_scene_id)) { return; }
        var step = number(state.editor_zoom_step,0,4,true), incoming;
        if (step === null || sceneFrame(state.editor_scene_id,step).step !== step) { return; }
        incoming = sceneKey(state.editor_scene_id,step);
        if (incoming !== sceneKey(sceneId,zoomStep)) { selectScene(state.editor_scene_id,step,false); }
    }
    function sendEditor(active) {
        if (destroyed || !bound) { return false; }
        var args = {action:'editor',active:active};
        if (active && editorMode && editorDraft) {
            args = previewArgs('editor'); args.active = true;
        }
        return sendEditorRequest(args);
    }
    function sendEditorRequest(args) {
        var owner = model(), command = owner && owner.onAction;
        clearEditorTimer(); editorRequestRejected = false;
        args.request_id = ++editorRequestNumber; editorRequest = args;
        try {
            if (typeof command === 'function') { command.call(owner,args); }
            else if (command && typeof command.value === 'function') { command.value.call(command,args); }
            else { throw new Error('Missing native preview command'); }
            if (editorRequest === args && typeof window.setTimeout === 'function') {
                editorTimer = window.setTimeout(function() {
                    editorTimer = null;
                    if (editorRequest === args) {
                        acceptEditorRequest(args.request_id,false);
                        acknowledgeEditor(state.editor_active === true); syncNativeScene(); resize();
                    }
                },3000);
            }
            return true;
        } catch (ignored) { /* Keep the draft when the owned native surface rejects a request. */ }
        acceptEditorRequest(args.request_id,false);
        resize(); return false;
    }
    function acceptEditorRequest(ack, accepted) {
        if (!editorRequest || ack !== editorRequest.request_id) { return; }
        var request = editorRequest;
        editorRequest = null; clearEditorTimer();
        if (accepted) {
            if (editorDraft && request.variant === editorDraft.variant) { editorProfilePending = false; }
            return;
        }
        if (request.action === 'editor') {
            if (request.active) { resetEditorState(); feedback(text('unavailable'),true); }
            else {
                editorClosing = false;
                if (editorDraft && state.editor_active === true) { loadSceneFrame(false); }
            }
            return;
        }
        if (!editorDraft || request.variant !== editorDraft.variant) { return; }
        editorProfilePending = focusPresetPending = false;
        editorRequestRejected = true;
        syncNativeVariant();
    }
    function syncNativeVariant() {
        if (!editorDraft || editorRequest || editorProfilePending || state.editor_preview_mode !== editorMode ||
                !validVariant(state.editor_preview_variant) || state.editor_preview_variant === editorDraft.variant) { return; }
        editorDraft.variant = state.editor_preview_variant;
    }
    function previewChoice(id) {
        var source = state.preview_choices, j;
        if (Array.isArray(source)) {
            for (j = 0; j < source.length && j < 64; j += 1) { if (source[j] && source[j].id === id) { return source[j]; } }
        }
        return null;
    }
    function previewAvailable(id, choice) {
        choice = choice || previewChoice(id);
        if (choice && choice.available === false) { return false; }
        var availability = state.editor_preview_availability;
        if (availability && typeof availability === 'object' && availability[editorMode] && typeof availability[editorMode] === 'object') { availability = availability[editorMode]; }
        return !availability || typeof availability !== 'object' || availability[id] !== false;
    }
    function previewChoices() {
        var source = state.preview_choices, result = [], seen = {}, j, item;
        if (Object.prototype.toString.call(source) === '[object Array]') {
            for (j = 0; j < source.length && j < 64; j += 1) {
                item = source[j];
                if (!item || !validVariant(item.id) || seen[item.id] || !safeText(item.label,'',160) ||
                        Object.prototype.toString.call(item.modes) !== '[object Array]' || item.modes.indexOf(editorMode) < 0) { continue; }
                var tierVehicle = item.tier === 11;
                if (tierVehicle && editorMode !== 'arcade' && editorMode !== 'sniper') { continue; }
                result.push({id:item.id,label:item.label,available:previewAvailable(item.id,item),
                    tierVehicle:tierVehicle,note:tierVehicle ? safeText(item.note,'',240) : ''});
                seen[item.id] = true;
            }
        }
        return result.length ? result : [{id:'standard',label:text('editor-standard'),available:previewAvailable('standard')}];
    }
    function selectPreview(id, event) {
        stop(event,true);
        if (destroyed || !bound || !editorShown || editorClosing || !editorDraft) { return; }
        var choices = previewChoices(), j, found = false;
        for (j = 0; j < choices.length; j += 1) { if (choices[j].id === id && choices[j].available) { found = true; break; } }
        if (!found) { return; }
        if (editorDraft.variant === id) { renderPreviewChoices(); return; }
        editorDraft.variant = id; editorProfilePending = true; editorRequestRejected = false;
        nodes['editor-save'].disabled = true;
        renderPreviewStatus(); renderPreviewChoices();
        if (sceneStatus === 'loading') { loadSceneFrame(true); }
        else { sendScenePreview(); }
    }
    function bindPreviewChoice(button, id) { button.onclick = function(event) { selectPreview(id,event); }; }
    previewFilterButtons.forEach(function(button,index) {
        button.onclick = function(event) {
            stop(event,true);
            if (destroyed || !editorShown || editorClosing || !editorDraft || previewFilterBar.style.display === 'none') { return; }
            previewFilters[editorMode] = filterOptions[index];
            nodes['editor-choices'].scrollTop = 0;
            renderPreviewChoices();
        };
    });
    function fitPreviewList() {
        var bounds, chromeScale = parseFloat(document.documentElement.style.fontSize) || 1;
        try { bounds = nodes['editor-choices'].getBoundingClientRect(); } catch (ignored) { bounds = null; }
        var top = bounds && typeof bounds.top === 'number' ? bounds.top : 130 * chromeScale;
        var noteHeight = previewNote.textContent ? 52 * chromeScale : 0;
        nodes['editor-choices'].style.maxHeight = String(Math.max(32 * chromeScale,surface.height - top - 90 * chromeScale - noteHeight)) + 'px';
    }
    function renderPreviewChoices() {
        if (!editorMode || !editorDraft) { return; }
        var choices = previewChoices(), j, button, label, previousScroll = nodes['editor-choices'].scrollTop || 0;
        var hasVehicles = choices.some(function(choice) { return choice.tierVehicle === true; });
        var filter = hasVehicles && previewFilters[editorMode] === 'vehicles' ? 'vehicles' : 'mechanics';
        previewFilterBar.style.display = hasVehicles ? 'flex' : 'none';
        previewFilterButtons.forEach(function(item,index) {
            var name = filterOptions[index], selected = filter === name;
            item.textContent = text('filter-' + name);
            item.className = 'at-window-clear' + (selected ? ' at-selected' : '');
            item.setAttribute('aria-pressed',selected ? 'true' : 'false');
        });
        choices = choices.filter(function(choice) { return (choice.tierVehicle === true) === (filter === 'vehicles'); });
        var note = '';
        for (j = 0; j < choices.length; j += 1) {
            if (choices[j].id === editorDraft.variant) { note = choices[j].note || ''; break; }
        }
        previewNote.textContent = note;
        previewNote.style.display = note ? 'block' : 'none';
        var key = JSON.stringify([language(),editorMode,editorDraft.variant,choices]);
        nodes['editor-profile-label'].textContent = text('editor-profile');
        if (key !== previewListKey) {
            previewListKey = key;
            while (nodes['editor-choices'].firstChild) { nodes['editor-choices'].removeChild(nodes['editor-choices'].firstChild); }
            for (j = 0; j < choices.length; j += 1) {
                button = document.createElement('button'); button.type = 'button';
                button.id = 'at-preview-choice-' + choices[j].id;
                button.className = 'at-window-clear' + (choices[j].id === editorDraft.variant ? ' at-selected' : '');
                label = document.createElement('span'); label.className = 'at-editor-choice-label'; label.textContent = choices[j].label; button.appendChild(label);
                button.setAttribute('data-variant',choices[j].id);
                button.setAttribute('aria-pressed',choices[j].id === editorDraft.variant ? 'true' : 'false');
                button.disabled = !choices[j].available;
                button.setAttribute('aria-disabled',button.disabled ? 'true' : 'false');
                button.setAttribute('title',choices[j].label + (button.disabled ? ' - ' + text('editor-disabled') : ''));
                bindPreviewChoice(button,choices[j].id); nodes['editor-choices'].appendChild(button);
            }
        }
        fitPreviewList(); nodes['editor-choices'].scrollTop = previousScroll; syncPreviewScrollbar();
    }
    function syncPreviewScrollbar() {
        if (destroyed || !editorShown) { return; }
        var list = nodes['editor-choices'], maximum = Math.max(0,list.scrollHeight - list.clientHeight), visible = maximum > 1;
        nodes['editor-list-wrap'].className = 'at-editor-list-wrap' + (visible ? ' at-has-scrollbar' : '');
        nodes['editor-scrollbar'].style.display = visible ? 'block' : 'none';
        if (!visible) { previewScrollbarDrag = null; return; }
        maximum = Math.max(0,list.scrollHeight - list.clientHeight);
        var chromeScale = parseFloat(document.documentElement.style.fontSize) || 1;
        var thumb = Math.min(list.clientHeight,Math.max(20 * chromeScale,list.clientHeight * list.clientHeight / list.scrollHeight));
        nodes['editor-scrollbar'].style.height = String(list.clientHeight) + 'px';
        nodes['editor-scrollbar-thumb'].style.height = String(thumb) + 'px';
        nodes['editor-scrollbar-thumb'].style.top = String(maximum ? list.scrollTop / maximum * (list.clientHeight - thumb) : 0) + 'px';
        nodes['editor-scrollbar'].setAttribute('aria-valuemin','0');
        nodes['editor-scrollbar'].setAttribute('aria-valuemax',String(Math.round(maximum)));
        nodes['editor-scrollbar'].setAttribute('aria-valuenow',String(Math.round(list.scrollTop)));
        nodes['editor-scrollbar'].setAttribute('aria-label',text('editor-profile'));
    }
    function scrollPreviewTo(value) {
        var list = nodes['editor-choices'];
        list.scrollTop = Math.max(0,Math.min(Math.max(0,list.scrollHeight - list.clientHeight),value));
        syncPreviewScrollbar();
    }
    function previewScrollbarMove(event, finishing) {
        if (!previewScrollbarDrag || destroyed || !editorShown || editorClosing) { return; }
        if (!finishing && typeof event.buttons === 'number' && !(event.buttons & 1)) { previewScrollbarDrag = null; return; }
        var y = number(event.clientY,-65536,65536,false), rail = nodes['editor-scrollbar'].getBoundingClientRect();
        if (y === null || !rail.height) { return; }
        var list = nodes['editor-choices'], thumb = parseFloat(nodes['editor-scrollbar-thumb'].style.height) || 0;
        var travel = Math.max(0,rail.height - thumb);
        stop(event,true); scrollPreviewTo(travel ? (y - rail.top - previewScrollbarDrag.offset) / travel * (list.scrollHeight - list.clientHeight) : 0);
    }
    function previewScrollbarDown(event) {
        if (destroyed || !editorShown || editorClosing || (event.button !== undefined && event.button !== 0)) { return; }
        var y = number(event.clientY,-65536,65536,false), rail = nodes['editor-scrollbar'].getBoundingClientRect();
        var list = nodes['editor-choices'];
        if (y === null || !rail.height || list.scrollHeight <= list.clientHeight) { return; }
        var top = parseFloat(nodes['editor-scrollbar-thumb'].style.top) || 0, thumb = parseFloat(nodes['editor-scrollbar-thumb'].style.height) || 0;
        var local = y - rail.top;
        previewScrollbarDrag = {offset:local >= top && local <= top + thumb ? local - top : thumb / 2};
        stop(event,true); previewScrollbarMove(event,true);
        try { nodes['editor-scrollbar'].focus(); } catch (ignored) { /* Input remains owned by the editor. */ }
    }
    function previewScrollbarUp(event) { if (previewScrollbarDrag) { previewScrollbarMove(event,true); previewScrollbarDrag = null; } }
    function previewScrollbarBlur() { previewScrollbarDrag = null; }
    function previewScrollbarKey(event) {
        if (destroyed || !editorShown || editorClosing) { return; }
        var list = nodes['editor-choices'], value = list.scrollTop, chromeScale = parseFloat(document.documentElement.style.fontSize) || 1;
        var key = event.key || ({38:'ArrowUp',40:'ArrowDown',33:'PageUp',34:'PageDown',36:'Home',35:'End',32:' '})[event.keyCode];
        if (key === 'Home') { value = 0; }
        else if (key === 'End') { value = list.scrollHeight - list.clientHeight; }
        else if (key === 'ArrowUp') { value -= 32 * chromeScale; }
        else if (key === 'ArrowDown') { value += 32 * chromeScale; }
        else if (key === 'PageUp' || (key === ' ' && event.shiftKey)) { value -= list.clientHeight * .9; }
        else if (key === 'PageDown' || key === ' ') { value += list.clientHeight * .9; }
        else { return; }
        stop(event,true); scrollPreviewTo(value);
    }
    nodes['editor-scrollbar'].onmousedown = previewScrollbarDown;
    nodes['editor-scrollbar'].onkeydown = previewScrollbarKey;
    nodes['editor-choices'].addEventListener('scroll',syncPreviewScrollbar,false);
    function previewWheel(event) {
        if (destroyed || !bound || !editorShown || editorClosing || !event || event.defaultPrevented) { return; }
        stop(event,true);
        var list = nodes['editor-choices'], maximum = list.scrollHeight - list.clientHeight, delta = 0;
        if (!(maximum > 0)) { return; }
        var chromeScale = parseFloat(document.documentElement.style.fontSize) || 1, native = state.native_gameface === true;
        if (event.shiftKey || (typeof event.deltaX === 'number' && typeof event.deltaY === 'number' && event.deltaX !== 0 && Math.abs(event.deltaX) >= Math.abs(event.deltaY))) { stop(event,true); return; }
        if (typeof event.deltaY === 'number' && isFinite(event.deltaY) && event.deltaY !== 0) {
            // WoT's Gameface list adapter uses positive Y for up and a quarter-view wheel step.
            if (native) { delta = event.deltaMode === 2 ? -event.deltaY * list.clientHeight : (event.deltaY < 0 ? 1 : -1) * list.clientHeight / 4; }
            else { delta = event.deltaY * (event.deltaMode === 1 ? 32 * chromeScale : (event.deltaMode === 2 ? list.clientHeight : 1)); }
        } else if (typeof event.wheelDelta === 'number' && isFinite(event.wheelDelta)) {
            delta = native ? (event.wheelDelta > 0 ? -1 : (event.wheelDelta < 0 ? 1 : 0)) * list.clientHeight / 4 : -event.wheelDelta / 120 * 96 * chromeScale;
        }
        if (!isFinite(delta) || !delta) { return; }
        var stamp = typeof event.timeStamp === 'number' && isFinite(event.timeStamp) ? event.timeStamp : new Date().getTime();
        if (lastPreviewWheel && lastPreviewWheel.type !== event.type && stamp >= lastPreviewWheel.stamp &&
                stamp - lastPreviewWheel.stamp <= 8 && delta * lastPreviewWheel.delta > 0) { stop(event,true); return; }
        lastPreviewWheel = {type:event.type,stamp:stamp,delta:delta};
        stop(event,true); scrollPreviewTo(list.scrollTop + delta);
    }
    nodes['editor-choices'].addEventListener('wheel',previewWheel,false);
    nodes['editor-choices'].addEventListener('mousewheel',previewWheel,false);
    nodes['editor-scrollbar'].addEventListener('wheel',previewWheel,false); nodes['editor-scrollbar'].addEventListener('mousewheel',previewWheel,false);
    function sceneWheel(event) {
        if (destroyed || !bound || !editorShown || editorClosing || !event || event.defaultPrevented) { return; }
        stop(event,true);
        if (editorDrag || previewScrollbarDrag || event.shiftKey) { return; }
        var target = event.target, delta = 0, native = state.native_gameface === true;
        while (target && target !== nodes.editor) {
            if (/^(BUTTON|INPUT|SELECT|TEXTAREA)$/.test(target.tagName || '') ||
                    /at-editor-(profiles|actions|view-controls|sample)/.test(target.className || '')) { return; }
            target = target.parentNode;
        }
        if (typeof event.deltaX === 'number' && typeof event.deltaY === 'number' && event.deltaX !== 0 && Math.abs(event.deltaX) >= Math.abs(event.deltaY)) { return; }
        if (event.type === 'mousewheel' && typeof event.wheelDelta === 'number' && isFinite(event.wheelDelta) && event.wheelDelta !== 0) { delta = -event.wheelDelta; }
        else if (typeof event.deltaY === 'number' && isFinite(event.deltaY) && event.deltaY !== 0) { delta = native ? -event.deltaY : event.deltaY; }
        else if (typeof event.wheelDelta === 'number' && isFinite(event.wheelDelta)) { delta = -event.wheelDelta; }
        if (!isFinite(delta) || !delta) { return; }
        var stamp = typeof event.timeStamp === 'number' && isFinite(event.timeStamp) ? event.timeStamp : new Date().getTime();
        if (lastSceneWheel && lastSceneWheel.type !== event.type && stamp >= lastSceneWheel.stamp && stamp-lastSceneWheel.stamp <= 8 && delta*lastSceneWheel.delta > 0) { return; }
        lastSceneWheel = {type:event.type,stamp:stamp,delta:delta};
        changeSceneZoom(delta < 0 ? 1 : -1);
    }
    nodes.editor.addEventListener('wheel',sceneWheel,false); nodes.editor.addEventListener('mousewheel',sceneWheel,false);
    nodes['editor-zoom-in'].onclick = function(event) { stop(event,true); changeSceneZoom(1); };
    nodes['editor-zoom-out'].onclick = function(event) { stop(event,true); changeSceneZoom(-1); };
    nodes['editor-view-reset'].onclick = function(event) { stop(event,true); if (editorShown && !editorDrag && !previewScrollbarDrag) { selectScene(sceneId,defaultSceneStep(sceneId),true); } };
    function bindSceneCamera(node, id) { node.onclick = function(event) {
        stop(event,true);
        if (editorShown && !editorDrag && !previewScrollbarDrag && editorMode === 'arty') { selectScene(id,sceneSteps[id] === undefined ? defaultSceneStep(id) : sceneSteps[id],true); }
    }; }
    bindSceneCamera(nodes['editor-arty-top'],'arty_top'); bindSceneCamera(nodes['editor-arty-trajectory'],'arty_trajectory');
    function renderPreviewStatus() {
        var status = state.editor_preview_status;
        if (editorRequestRejected) { status = 'rejected'; }
        else if (editorProfilePending || (editorDraft && (state.editor_preview_mode !== editorMode ||
                state.editor_preview_variant !== editorDraft.variant))) { status = 'loading'; }
        else if (!previewAvailable(editorDraft && editorDraft.variant)) { status = 'unavailable'; }
        if (['loading','ready','partial','unavailable','rejected'].indexOf(status) < 0) { status = 'unavailable'; }
        var key = 'editor-' + status, reason = state.editor_preview_reason;
        var panelResult = (status === 'ready' && reason === 'battle-panels-mounted') ||
            (status === 'partial' && ['battle-panel-unavailable','battle-panel-sample-incomplete'].indexOf(reason) >= 0);
        if (panelResult || (status === 'ready' && reason === 'decoration-mounted') ||
                (status === 'partial' && ['decoration-missing','decoration-failed','decoration-timeout',
                'decoration-unverified','cassette-unverified','marker-unverified',
                'artillery-indicators-unavailable'].indexOf(reason) >= 0)) {
            key += '-' + reason;
        }
        var message = text(key);
        var choice = editorDraft && previewChoice(editorDraft.variant);
        if (!panelResult && (status === 'ready' || status === 'partial') && choice && choice.tier === 11 &&
                (choice.coverage === 'separate' || choice.coverage === 'partial') &&
                !(typeof choice.battle_panel_count === 'number' && choice.battle_panel_count > 0)) {
            message += ' ' + text('editor-battle-panel-catalogue-unavailable');
        }
        var diagnostic = state.editor_preview_decoration_diagnostic;
        var decorationDiagnostics = ['stock-binding-missing','library-load','symbol-missing','symbol-incompatible','timeline-member',
            'timeline-frame','empty-drawing','pixel-probe','bridge-error-detail','host-rejected',
            'host-linkage-unsupported','host-geometry-invalid','stock-symbol-error',
            'host-error-empty','host-error-type','host-error-too-long','flash-error',
            'hide-previous','unsupported-family','resource-query','missing-host','missing-stock-layer',
            'missing-stock-surge','host-construction','host-component','host-configuration','host-activation',
            'host-geometry','bridge-root','bridge-request','bridge-state','root-timeout','library-timeout'];
        if (status === 'partial' && decorationDiagnostics.indexOf(diagnostic) >= 0) {
            message += ' [' + diagnostic + ']';
        }
        nodes['editor-preview-status'].textContent = message;
        nodes['editor-preview-status'].className = 'at-editor-preview-status' + (status === 'ready' || status === 'loading' ? '' : ' at-preview-unavailable');
        nodes['editor-preview-status'].setAttribute('data-status',status);
        nodes['editor-preview-status'].setAttribute('title',message);
    }
    function clearEditorTimer() {
        if (editorTimer !== null && typeof window.clearTimeout === 'function') { window.clearTimeout(editorTimer); }
        editorTimer = null;
    }
    function cancelDrag(restore) {
        if (editorDrag && restore && editorDraft) { editorDraft.x = editorDrag.offset.x; editorDraft.y = editorDrag.offset.y; }
        editorDrag = null;
    }
    function resetEditorState() {
        releaseSceneImages(); sceneId = null; zoomStep = 0; focusPresetPending = false;
        editorRequest = null; editorProfilePending = editorRequestRejected = false;
        clearEditorTimer(); cancelDrag(false); previewListKey = ''; lastPreviewWheel = previewScrollbarDrag = null; nodes['editor-choices'].scrollTop = 0; editorMode = editorDraft = null; editorShown = false; editorClosing = false;
        nodes.editor.style.display = 'none'; root.style.display = 'flex';
    }
    function openEditor(mode) {
        if (destroyed || !bound || editorMode || ['arcade','sniper','arty'].indexOf(mode) < 0) { return false; }
        var config = readDraft(); if (!config) { feedback(text('invalid'),true); return false; }
        editorMode = mode; editorDraft = {x:positions[mode].x,y:positions[mode].y,variant:positions[mode].variant};
        sceneId = sceneForMode(mode); zoomStep = sceneSteps[sceneId] === undefined ? defaultSceneStep(sceneId) : sceneFrame(sceneId,sceneSteps[sceneId]).step;
        var choices = previewChoices(), found = false, j;
        for (j = 0; j < choices.length; j += 1) {
            if (choices[j].id === editorDraft.variant) {
                found = true;
                if (choices[j].tierVehicle) { previewFilters[mode] = 'vehicles'; }
                break;
            }
        }
        if (!found) { editorDraft.variant = choices[0].id; }
        editorProfilePending = true; previewListKey = ''; lastPreviewWheel = previewScrollbarDrag = null; nodes['editor-choices'].scrollTop = 0;
        editorShown = editorClosing = false;
        loadSceneFrame(false);
        if (!sendEditor(true)) { resetEditorState(); return false; }
        return true;
    }
    function closeEditor(save) {
        if (!editorMode || editorClosing || (save && editorProfilePending)) { return false; }
        cancelDrag(false); clearEditorTimer(); releaseSceneImages();
        if (save && editorShown) {
            positions[editorMode] = {x:editorDraft.x,y:editorDraft.y,variant:editorDraft.variant}; edited(); apply();
        }
        editorClosing = true; nodes['editor-save'].disabled = nodes['editor-cancel'].disabled = true;
        if (!sendEditor(false)) { resetEditorState(); resize(); return false; }
        return true;
    }
    function acknowledgeEditor(active) {
        if (!editorMode) { if (active) { sendEditor(false); } return; }
        if (active && !editorClosing) {
            editorShown = true;
            root.style.display = 'none'; nodes.editor.style.display = 'block';
            nodes['editor-save'].disabled = editorProfilePending;
            nodes['editor-cancel'].disabled = false;
        } else if (!active && (editorShown || editorClosing)) {
            if (editorShown && !editorClosing) { suppressEscapeUntilUp = true; }
            resetEditorState();
        }
    }
    function referenceMetrics(referenceNode,reference,font) {
        referenceNode.textContent = reference;
        referenceNode.style.fontSize = String(font) + 'px';
        var dimensions;
        try { dimensions = referenceNode.getBoundingClientRect(); } catch (ignored) { dimensions = null; }
        return {width:dimensions && dimensions.width > 0 ? dimensions.width : reference.length * font * .56,height:font};
    }
    function samplePanel(config,referenceNode,reference) {
        var scale = surface.scale, factor = config.hud_frame_scale_pct / 100;
        var metric = referenceMetrics(referenceNode,reference,config.hud_font_px * scale);
        var width = (metric.width + 2 * scale) * factor, height = (metric.height + 2 * scale) * factor;
        var fitted = Math.min(1,Math.max(1,surface.width - 8) / (width + 88 * scale),Math.max(1,surface.height - 8) / Math.max(height,24 * scale));
        var appearanceScale = scale * fitted;
        if (fitted < 1) { metric = referenceMetrics(referenceNode,reference,config.hud_font_px * appearanceScale); }
        return {width:(metric.width + 2 * appearanceScale) * factor,height:(metric.height + 2 * appearanceScale) * factor,scale:appearanceScale};
    }
    function placeSample(sample,reading,config,panel,center,value) {
        sample.style.left = String(center.x) + 'px'; sample.style.top = String(center.y) + 'px';
        sample.style.width = String(panel.width) + 'px'; sample.style.height = String(panel.height) + 'px';
        sample.style.backgroundColor = 'rgba(20,20,20,' + String(config.hud_background_opacity) + ')';
        reading.style.fontSize = String(config.hud_font_px * panel.scale) + 'px';
        reading.textContent = value;
    }
    function renderPeerReadout(activeCenter) {
        var sample = nodes['editor-peer-sample'], ownSample = nodes['editor-sample'];
        var peer = state.editor_preview_mode === editorMode ? state.editor_peer_readout : null;
        if (!peer || typeof peer.enabled !== 'boolean' ||
                number(peer.x,-32768,32768,true) === null || number(peer.y,-32768,32768,true) === null ||
                number(peer.hud_font_px,12,40,true) === null || number(peer.hud_frame_scale_pct,100,300,true) === null ||
                number(peer.hud_background_opacity,0,1,false) === null) {
            sample.style.display = 'none';
            ownSample.setAttribute('data-peer-overlap','false');
            return;
        }
        var scale = surface.scale;
        var panel = samplePanel(peer,nodes['editor-peer-reference'],sampleReading('1500.5','m'));
        var center = constrainedCenter(surface.width / 2 + peer.x * scale,surface.height / 2 + peer.y * scale,panel);
        placeSample(sample,nodes['editor-peer-reading'],peer,panel,center,sampleReading('1500.5','m'));
        sample.setAttribute('data-enabled',String(peer.enabled));
        nodes['editor-peer-state'].textContent = peer.enabled ? '' : text('enabled-off');
        sample.style.display = 'block';
        var overlaps = peer.enabled && Math.abs(center.x - activeCenter.x) < (panel.width + editorPanel.width) / 2 &&
            Math.abs(center.y - activeCenter.y) < (panel.height + editorPanel.height) / 2;
        ownSample.setAttribute('data-peer-overlap',String(overlaps));
    }
    function renderEditor() {
        if (!editorShown || !editorMode || !editorDraft) { return; }
        var config = readDraft();
        if (!config) { return; }
        var scale = surface.scale;
        editorPanel = samplePanel(config,nodes['editor-reference'],sampleReading('~15.55','s'));
        nodes['editor-title'].textContent = text('preview') + ' \u00b7 ' + text('position-' + editorMode);
        nodes['editor-help'].textContent = text('editor-wheel');
        nodes['editor-save'].textContent = text('editor-save'); nodes['editor-cancel'].textContent = text('editor-cancel'); nodes['editor-reset'].textContent = text('editor-reset');
        nodes['editor-handle'].setAttribute('aria-label',text('editor-move'));
        nodes['editor-handle'].setAttribute('title',text('editor-move'));
        renderPreviewStatus(); renderPreviewChoices(); renderSceneControls();
        var center = constrainedCenter(surface.width / 2 + editorDraft.x * scale, surface.height / 2 + editorDraft.y * scale);
        placeSample(nodes['editor-sample'],nodes['editor-reading'],config,editorPanel,center,sampleReading('~1.85','s'));
        nodes['editor-handle'].style.width = nodes['editor-handle'].style.height = String(24 * editorPanel.scale) + 'px';
        nodes['editor-handle'].style.left = String(-28 * editorPanel.scale) + 'px';
        renderPeerReadout(center);
    }
    function constrainedCenter(x,y,panel) {
        panel = panel || editorPanel;
        var scale = panel.scale, left = panel.width / 2 + 30 * scale, right = panel.width / 2 + 58 * scale;
        var edge = Math.max(panel.height / 2,12 * scale);
        return {x:Math.max(left + 4,Math.min(surface.width - right - 4,x)),y:Math.max(edge + 4,Math.min(surface.height - edge - 4,y))};
    }
    function editorMouseDown(event) {
        if (!editorShown || editorClosing || !editorDraft || (event.button !== undefined && event.button !== 0)) { return; }
        stop(event,true);
        var x = number(event.clientX,-65536,65536,false), y = number(event.clientY,-65536,65536,false);
        if (x === null || y === null) { return; }
        var center = constrainedCenter(surface.width / 2 + editorDraft.x * surface.scale,surface.height / 2 + editorDraft.y * surface.scale);
        editorDrag = {mouse:{x:x,y:y},offset:{x:editorDraft.x,y:editorDraft.y},center:center,scale:surface.scale,width:surface.width,height:surface.height};
    }
    function editorMouseMove(event, finishing) {
        if (!editorDrag || !editorShown || editorClosing || !editorDraft) { return; }
        if (!finishing && typeof event.buttons === 'number' && !(event.buttons & 1)) {
            cancelDrag(true); renderEditor(); return;
        }
        var x = number(event.clientX,-65536,65536,false), y = number(event.clientY,-65536,65536,false);
        if (x === null || y === null) { return; }
        stop(event,true);
        var center = constrainedCenter(editorDrag.center.x + x - editorDrag.mouse.x,editorDrag.center.y + y - editorDrag.mouse.y);
        editorDraft.x = Math.max(-32768,Math.min(32768,Math.round((center.x - surface.width / 2) / surface.scale)));
        editorDraft.y = Math.max(-32768,Math.min(32768,Math.round((center.y - surface.height / 2) / surface.scale)));
        renderEditor();
    }
    function editorMouseUp(event) { if (editorDrag) { editorMouseMove(event,true); cancelDrag(false); } }
    function editorBlur() { cancelDrag(true); renderEditor(); }
    nodes['editor-handle'].onmousedown = editorMouseDown;
    nodes['editor-save'].onclick = function(event) { stop(event,true); closeEditor(true); };
    nodes['editor-cancel'].onclick = function(event) { stop(event,true); closeEditor(false); };
    nodes['editor-reset'].onclick = function(event) { stop(event,true); cancelDrag(false); if (editorDraft) { editorDraft.x = 0; editorDraft.y = 40; renderEditor(); } };
    function bindPosition(mode) { nodes['position-' + mode].onclick = function(event) { stop(event,true); openEditor(mode); }; }
    bindPosition('arcade'); bindPosition('sniper'); bindPosition('arty');

    function cancelResize() {
        if (resizeTimer !== null && typeof window.clearTimeout === 'function') { window.clearTimeout(resizeTimer); }
        resizeTimer = null;
    }
    function reportLayout(width,height) {
        if (layoutReported || !bound || destroyed) { return; }
        var owner = model(), command = owner && owner.onAction, args = {action:'layout',width:width,height:height};
        try {
            if (typeof command === 'function') { command.call(owner,args); layoutReported = true; }
            else if (command && typeof command.value === 'function') { command.value.call(command,args); layoutReported = true; }
        } catch (ignored) { /* Native resize notifications can still place the window. */ }
    }
    function requestResize() {
        if (destroyed || !bound || resizing || !lastWidth || !lastHeight) { return; }
        resizing = true; var actual = null, accepted = false;
        try {
            try { if (viewOwner && typeof viewOwner.getViewSizePx === 'function') { actual = viewOwner.getViewSizePx(); } } catch (ignoredSize) { /* Loading texture. */ }
            accepted = actual && actual.width === lastWidth && actual.height === lastHeight;
            if (!accepted && viewOwner && typeof viewOwner.resizeViewPx === 'function') { viewOwner.resizeViewPx(lastWidth,lastHeight); }
        } catch (ignored) { /* Retry after native loading or texture creation. */ }
        finally { resizing = false; }
        reportLayout(lastWidth,lastHeight);
        if (!accepted && resizeAttempts < 6 && resizeTimer === null && typeof window.setTimeout === 'function') {
            resizeAttempts += 1;
            resizeTimer = window.setTimeout(function() { resizeTimer = null; requestResize(); },100);
        }
    }
    function dimension(value) { return typeof value === 'number' && isFinite(value) && value > 0 && value <= 32768 ? Math.floor(value) : 0; }
    function resize() {
        var viewport = state.viewport || {}, scale = viewport.scale;
        var clientWidth = dimension(viewport.width), clientHeight = dimension(viewport.height), client;
        if (typeof scale !== 'number' || !isFinite(scale) || scale <= 0 || scale > 16) { scale = 1; }
        try {
            if (viewOwner && typeof viewOwner.getScale === 'function') {
                var currentScale = viewOwner.getScale();
                if (typeof currentScale === 'number' && isFinite(currentScale) && currentScale > 0 && currentScale <= 16) { scale = currentScale; }
            }
            if (viewOwner && typeof viewOwner.getClientSizePx === 'function') {
                client = viewOwner.getClientSizePx();
                if (client && dimension(client.width) && dimension(client.height)) { clientWidth = dimension(client.width); clientHeight = dimension(client.height); }
            }
        } catch (ignored) { /* Model supplies last known client bounds. */ }
        clientWidth = clientWidth || surface.width; clientHeight = clientHeight || surface.height;
        var placementScale = Math.max(.5,Math.min(3,scale));
        if (editorDrag && (surface.width !== clientWidth || surface.height !== clientHeight || surface.scale !== placementScale)) { cancelDrag(true); }
        surface = {width:clientWidth,height:clientHeight,scale:placementScale};
        if (editorShown) {
            document.documentElement.style.fontSize = String(Math.min(scale,Math.max(.01,clientWidth / 640),Math.max(.01,clientHeight / 360))) + 'px';
            document.body.style.width = nodes.editor.style.width = String(clientWidth) + 'px';
            document.body.style.height = nodes.editor.style.height = String(clientHeight) + 'px';
            if (lastWidth !== clientWidth || lastHeight !== clientHeight) {
                cancelResize(); resizeAttempts = 0; layoutReported = false; layoutReadySeen = {}; lastWidth = clientWidth; lastHeight = clientHeight;
            }
            renderEditor(); requestResize(); return;
        }
        var minimum = clientWidth && clientHeight ? Math.min(clientWidth,clientHeight) : (clientWidth || clientHeight);
        var gutter = Math.max(1,Math.min(Math.ceil(edgeGutter * scale),minimum ? Math.floor(minimum / 4) : Infinity));
        if (minimum) { gutter = Math.min(gutter,Math.max(0,Math.floor((minimum - 1) / 2))); }
        var availableWidth = clientWidth ? Math.max(1,clientWidth - 2 * gutter) : Infinity;
        var availableHeight = clientHeight ? Math.max(1,clientHeight - 2 * gutter) : Infinity;
        var fittedScale = Math.min(scale,availableWidth / logicalWidth,availableHeight / logicalHeight);
        var width = Math.max(1,Math.min(availableWidth,Math.floor(logicalWidth * fittedScale)));
        var height = Math.max(1,Math.min(availableHeight,Math.floor(logicalHeight * fittedScale)));
        document.documentElement.style.fontSize = String(fittedScale) + 'px';
        root.style.width = document.body.style.width = String(width) + 'px';
        root.style.height = document.body.style.height = String(height) + 'px';
        if (lastWidth !== width || lastHeight !== height) {
            cancelResize(); resizeAttempts = 0; layoutReported = false; layoutReadySeen = {}; lastWidth = width; lastHeight = height;
        }
        requestResize();
    }
    function onLayoutReady(name) {
        if (destroyed || !bound || (layoutReadySeen[name] && name !== 'clientResized' && name !== 'self.onScaleUpdated')) { return; }
        layoutReadySeen[name] = true; cancelResize(); layoutReported = false; resize();
    }
    function layoutCallback(name) { return function() { onLayoutReady(name); }; }
    function registerModel() {
        if (!bound || registering || callbackId !== null || !viewOwner || typeof viewOwner.addDataChangedCallback !== 'function') { return; }
        registering = true; var owner = viewOwner, id;
        try {
            id = owner.addDataChangedCallback('model',0,true);
            if (id !== undefined && id !== null) {
                if (!destroyed && bound && viewOwner === owner) { callbackId = id; }
                else if (typeof owner.removeDataChangedCallback === 'function') { owner.removeDataChangedCallback(id,0); }
            }
        } catch (ignored) { /* A subsequent data event may retry. */ }
        finally { registering = false; }
    }
    function update() {
        if (destroyed || !bound || updating) { return; }
        updating = true;
        try {
            registerModel(); var owner = model(), raw = owner && unwrap(owner.state), value, config;
            if (typeof raw !== 'string' || raw.length > 32768) { throw new Error('state shape'); }
            value = JSON.parse(raw); config = normalize(value && value.config);
            if (!config) { throw new Error('configuration shape'); }
            var ack = number(value.editor_request_id,0,2147483647,true);
            if (ack === null || ack < editorLastAck) { return; }
            editorLastAck = ack;
            state = value;
            acceptEditorRequest(ack,value.editor_request_accepted === true);
            var focus = number(value.editor_focus,0,2,true);
            if (editorMode && focus !== null) {
                if (!focusPresetPending) { editorFocus = focus; }
                else if (focus === editorFocus && value.editor_focus_demo !== true) { focusPresetPending = false; }
            }
            acknowledgeEditor(value.editor_active === true); syncNativeVariant(); syncNativeScene();
            if (pending !== null && !safeText(state.error,'',2048) && JSON.stringify(config) === pending) { pending = null; dirty = false; }
            else if (pending !== null && safeText(state.error,'',2048)) { pending = null; feedback(state.error,true); }
            if (!dirty) { fill(config); }
            renderLabels(); renderFeedback(); resize();
        } catch (ignored) { nodes.apply.disabled = true; feedback(text('unavailable'),true); resize(); }
        finally { updating = false; }
    }
    function onKey(event) {
        if (destroyed || !bound) { return; }
        var escape = event.key === 'Escape' || event.key === 'Esc' || event.keyCode === 27;
        if (escape) {
            if (event.type === 'keyup') { escapeDown = false; suppressEscapeUntilUp = false; stop(event,false); return; }
            if (event.type === 'keydown') {
                stop(event,true);
                if (event.repeat || escapeDown || suppressEscapeUntilUp) { return; }
                escapeDown = true;
                if (editorMode) { closeEditor(false); } else { send('close'); }
                return;
            }
        }
        if (editorShown && event.type === 'keydown' && event.target === nodes['editor-scrollbar']) { previewScrollbarKey(event); }
        /* This owned input surface never forwards typed configuration keys. */
        stop(event,false);
    }
    function off(engine,name,callback) { try { if (engine && typeof engine.off === 'function') { engine.off(name,callback); } } catch (ignored) { /* Closed renderer. */ } }
    function bind() {
        if (destroyed || bound || !window.engine || !window.viewEnv || typeof window.engine.on !== 'function') { return; }
        engineOwner = window.engine; viewOwner = window.viewEnv; bound = true;
        try {
            engineOwner.on('viewEnv.onDataChanged',update);
            if (destroyed) { off(engineOwner,'viewEnv.onDataChanged',update); return; }
            for (var j = 0; j < layoutEvents.length; j += 1) { layoutCallbacks[j] = layoutCallback(layoutEvents[j]); engineOwner.on(layoutEvents[j],layoutCallbacks[j]); }
            update();
        } catch (ignored) { destroy(); }
    }
    function ready() {
        if (destroyed) { return; }
        if (window.isDomBuilt) { bind(); }
        else if (window.engine && typeof window.engine.on === 'function') { readyOwner = window.engine; readyOwner.on('self.onDomBuilt',bind); }
    }
    function destroy() {
        if (destroyed) { return; }
        destroyed = true; bound = false; pending = null; clearEditorTimer(); cancelDrag(false); cancelResize(); releaseSceneImages();
        var owner = viewOwner, id = callbackId; callbackId = null; viewOwner = null;
        off(engineOwner,'viewEnv.onDataChanged',update);
        for (var j = 0; j < layoutEvents.length; j += 1) { off(engineOwner,layoutEvents[j],layoutCallbacks[j]); }
        layoutCallbacks = []; off(readyOwner,'self.onDomBuilt',bind); engineOwner = readyOwner = null;
        try { if (owner && id !== null && typeof owner.removeDataChangedCallback === 'function') { owner.removeDataChangedCallback(id,0); } } catch (ignored) { /* Native view disposed. */ }
        nodes['editor-choices'].removeEventListener('scroll',syncPreviewScrollbar,false);
        nodes.editor.removeEventListener('wheel',sceneWheel,false); nodes.editor.removeEventListener('mousewheel',sceneWheel,false);
        nodes['editor-scrollbar'].removeEventListener('wheel',previewWheel,false); nodes['editor-scrollbar'].removeEventListener('mousewheel',previewWheel,false);
        nodes['editor-choices'].removeEventListener('wheel',previewWheel,false); nodes['editor-choices'].removeEventListener('mousewheel',previewWheel,false);
        document.removeEventListener('keydown',onKey,true); document.removeEventListener('keyup',onKey,true); window.removeEventListener('beforeunload',destroy); window.removeEventListener('mousemove',editorMouseMove); window.removeEventListener('mouseup',editorMouseUp); window.removeEventListener('blur',editorBlur); window.removeEventListener('mousemove',previewScrollbarMove); window.removeEventListener('mouseup',previewScrollbarUp); window.removeEventListener('blur',previewScrollbarBlur);
        nodes.apply.disabled = true;
    }
    fill(defaults); renderLabels(); nodes.apply.disabled = true;
    window.GRZAimTimerSettings = {refresh:update,destroy:destroy,openEditor:openEditor,closeEditor:closeEditor};
    document.addEventListener('keydown',onKey,true); document.addEventListener('keyup',onKey,true); window.addEventListener('beforeunload',destroy); window.addEventListener('mousemove',editorMouseMove); window.addEventListener('mouseup',editorMouseUp); window.addEventListener('blur',editorBlur); window.addEventListener('mousemove',previewScrollbarMove); window.addEventListener('mouseup',previewScrollbarUp); window.addEventListener('blur',previewScrollbarBlur);
    try { if (root && window.engine && window.engine.whenReady && typeof window.engine.whenReady.then === 'function') { window.engine.whenReady.then(ready,destroy); } }
    catch (ignored) { destroy(); }
}());
