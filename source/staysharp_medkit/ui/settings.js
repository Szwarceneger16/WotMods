/* Native Wulf Settings view. Native Python owns key capture and persistence. */
(function () {
    'use strict';
    if (window.GRZStaySharpSettings) { return; }
    var root = document.getElementById('grz-medkit-settings'), nodes = {}, state = {};
    var engineOwner = null, viewOwner = null, readyOwner = null, callbackId = null;
    var bound = false, registering = false, destroyed = false, updating = false, lastWidth = 0, lastHeight = 0;
    var resizeTimer = null, resizeAttempts = 0, resizing = false, layoutReported = false;
    var layoutEvents = ['self.onLoaded', 'self.onTextureReady', 'clientResized', 'self.onScaleUpdated'];
    var layoutCallbacks = [], layoutReadySeen = {};
    var logicalWidth = 360, logicalHeight = 232, edgeGutter = 16;
    var defaults = {title:'Medkit hotkeys', toggle_mod:'Toggle mod', toggle_voice:'Toggle voice', cancel:'Cancel', clear:'Clear', close:'Close', capture:'Press keys\u2026', not_assigned:'Not assigned', hint:'Select a shortcut. Hold the keys together, then release all keys to save.'};
    var ids = ['title', 'close', 'label-mod', 'label-voice', 'mod', 'voice', 'clear-mod', 'clear-voice', 'hint', 'feedback', 'cancel'], index;
    for (index = 0; index < ids.length; index += 1) { nodes[ids[index]] = document.getElementById('grz-medkit-settings-' + ids[index]); }
    function caption(suffix, value) {
        var target = document.getElementById('grz-medkit-settings-' + suffix + '-caption') || nodes[suffix];
        target.textContent = value;
    }
    function unwrap(value) { return value && typeof value === 'object' && value.value !== undefined ? value.value : value; }
    function model() { return unwrap(window.model || (window.viewEnv && window.viewEnv.model)); }
    function safeText(value, fallback, maximum) { return typeof value === 'string' && value.length <= (maximum || 1024) ? value : fallback; }
    function label(key) { return safeText(state.labels && state.labels[key], defaults[key]); }
    function chord(value) {
        var result = [], i;
        if (typeof value === 'string') { return safeText(value, '', 2048); }
        if (!value || Object.prototype.toString.call(value) !== '[object Array]' || value.length > 32) { return ''; }
        for (i = 0; i < value.length; i += 1) { if (typeof value[i] !== 'string' || value[i].length > 64) { return ''; } result.push(value[i]); }
        return result.join(' + ');
    }
    function capturing() { return state.capturing === 'toggle_mod' || state.capturing === 'toggle_voice'; }
    function feedback(message, isError) {
        nodes.feedback.textContent = message;
        nodes.feedback.className = 'grz-medkit-settings-feedback' + (isError ? ' grz-medkit-settings-error' : '');
        var bottom = document.getElementById('grz-medkit-settings-bottom');
        if (bottom) { bottom.style.display = message || capturing() ? 'flex' : 'none'; }
    }
    function send(action, binding) {
        if (destroyed || !bound) { return; }
        var owner = model(), command = owner && owner.onAction, args = {action:action};
        if (binding) { args.binding = binding; }
        try {
            if (typeof command === 'function') { command.call(owner, args); }
            else if (command && typeof command.value === 'function') { command.value.call(command, args); }
        } catch (ignored) { feedback('Action unavailable. Close and reopen settings.', true); resize(); }
    }
    function stop(event, prevent) { if (event && event.stopPropagation) { event.stopPropagation(); } if (prevent && event && event.preventDefault) { event.preventDefault(); } }
    function bindButton(node, action, binding) { node.onclick = function (event) { stop(event, true); send(action, binding); }; }
    bindButton(nodes.mod, 'begin_capture', 'toggle_mod'); bindButton(nodes.voice, 'begin_capture', 'toggle_voice');
    bindButton(nodes['clear-mod'], 'clear_binding', 'toggle_mod'); bindButton(nodes['clear-voice'], 'clear_binding', 'toggle_voice');
    bindButton(nodes.cancel, 'cancel_capture'); bindButton(nodes.close, 'close');
    function cancelResize() {
        if (resizeTimer !== null && typeof window.clearTimeout === 'function') { window.clearTimeout(resizeTimer); }
        resizeTimer = null;
    }
    function reportLayout(width, height) {
        if (layoutReported || !bound || destroyed) { return; }
        var owner = model(), command = owner && owner.onAction, args = {action:'layout', width:width, height:height};
        try {
            if (typeof command === 'function') { command.call(owner, args); layoutReported = true; }
            else if (command && typeof command.value === 'function') { command.value.call(command, args); layoutReported = true; }
        } catch (ignored) { /* Native resize notifications can still place the window. */ }
    }
    function requestResize() {
        if (destroyed || !bound || resizing || !lastWidth || !lastHeight) { return; }
        resizing = true;
        var actual = null, accepted = false;
        try {
            try { if (viewOwner && typeof viewOwner.getViewSizePx === 'function') { actual = viewOwner.getViewSizePx(); } }
            catch (ignoredSize) { /* A missing measurement must not prevent requesting the texture. */ }
            accepted = actual && actual.width === lastWidth && actual.height === lastHeight;
            if (!accepted && viewOwner && typeof viewOwner.resizeViewPx === 'function') {
                viewOwner.resizeViewPx(lastWidth, lastHeight);
            }
        } catch (ignored) { /* Retry after native loading or texture creation. */ }
        finally { resizing = false; }
        reportLayout(lastWidth, lastHeight);
        if (!accepted && resizeAttempts < 6 && resizeTimer === null && typeof window.setTimeout === 'function') {
            resizeAttempts += 1;
            resizeTimer = window.setTimeout(function () { resizeTimer = null; requestResize(); }, 100);
        }
    }
    function onLayoutReady(eventName) {
        if (destroyed || !bound || (layoutReadySeen[eventName] && eventName !== 'clientResized' && eventName !== 'self.onScaleUpdated')) { return; }
        layoutReadySeen[eventName] = true;
        cancelResize(); layoutReported = false;
        resize();
    }
    function layoutCallback(eventName) { return function () { onLayoutReady(eventName); }; }
    function dimension(value) { return typeof value === 'number' && isFinite(value) && value > 0 && value <= 32768 ? Math.floor(value) : 0; }
    function resize() {
        var viewport = state.viewport || {}, scale = viewport.scale;
        var contentHeight = logicalHeight + (nodes.feedback.className.indexOf('grz-medkit-settings-error') >= 0 ? 48 : (capturing() ? 36 : (nodes.feedback.textContent ? 28 : 0)));
        var clientWidth = dimension(viewport.width), clientHeight = dimension(viewport.height), client;
        if (typeof scale !== 'number' || !isFinite(scale) || scale <= 0 || scale > 16) { scale = 1; }
        try {
            if (viewOwner && typeof viewOwner.getScale === 'function') {
                var currentScale = viewOwner.getScale();
                if (typeof currentScale === 'number' && isFinite(currentScale) && currentScale > 0 && currentScale <= 16) { scale = currentScale; }
            }
            if (viewOwner && typeof viewOwner.getClientSizePx === 'function') {
                client = viewOwner.getClientSizePx();
                if (client && dimension(client.width) && dimension(client.height)) {
                    clientWidth = dimension(client.width); clientHeight = dimension(client.height);
                }
            }
        } catch (ignored) { /* The model supplies the last known client bounds. */ }
        var minimum = clientWidth && clientHeight ? Math.min(clientWidth, clientHeight) : (clientWidth || clientHeight);
        var gutter = Math.max(1, Math.min(Math.ceil(edgeGutter * scale), minimum ? Math.floor(minimum / 4) : Infinity));
        if (minimum) { gutter = Math.min(gutter, Math.max(0, Math.floor((minimum - 1) / 2))); }
        var availableWidth = clientWidth ? Math.max(1, clientWidth - 2 * gutter) : Infinity;
        var availableHeight = clientHeight ? Math.max(1, clientHeight - 2 * gutter) : Infinity;
        var fittedScale = Math.min(scale, availableWidth / logicalWidth, availableHeight / contentHeight);
        var width = Math.max(1, Math.min(availableWidth, Math.floor(logicalWidth * fittedScale)));
        var height = Math.max(1, Math.min(availableHeight, Math.floor(contentHeight * fittedScale)));
        document.documentElement.style.fontSize = String(fittedScale) + 'px';
        root.style.width = document.body.style.width = String(width) + 'px';
        root.style.height = document.body.style.height = String(height) + 'px';
        if (lastWidth !== width || lastHeight !== height) {
            cancelResize(); resizeAttempts = 0; layoutReported = false; layoutReadySeen = {};
            lastWidth = width; lastHeight = height;
        }
        requestResize();
    }
    function renderRow(binding, suffix) {
        var control = nodes[suffix], value = chord(state.display && state.display[binding]) || chord(state.hotkeys && state.hotkeys[binding]);
        var active = state.capturing === binding;
        nodes['label-' + suffix].textContent = label(binding);
        var text = active ? (chord(state.preview) || label('capture')) : (value || label('not_assigned'));
        caption(suffix, text);
        control.setAttribute('title', text);
        control.className = 'grz-medkit-settings-binding' + (active ? ' grz-medkit-settings-capturing' : '');
        control.setAttribute('aria-label', label(binding) + ': ' + text); control.setAttribute('aria-pressed', active ? 'true' : 'false');
        caption('clear-' + suffix, label('clear')); nodes['clear-' + suffix].setAttribute('aria-label', label('clear') + ': ' + label(binding));
    }
    function render() {
        nodes.title.textContent = label('title'); nodes.close.setAttribute('title', label('close')); nodes.close.setAttribute('aria-label', label('close'));
        renderRow('toggle_mod', 'mod'); renderRow('toggle_voice', 'voice');
        nodes.hint.textContent = label('hint'); caption('cancel', label('cancel')); nodes.cancel.style.display = capturing() ? 'flex' : 'none';
        var error = safeText(state.error, '', 2048), status = safeText(state.status, '', 2048);
        feedback(error || status, !!error);
        resize();
    }
    function registerModel() {
        if (!bound || registering || callbackId !== null || !viewOwner || typeof viewOwner.addDataChangedCallback !== 'function') { return; }
        registering = true;
        var owner = viewOwner, id;
        try {
            id = owner.addDataChangedCallback('model', 0, true);
            if (id !== undefined && id !== null) {
                if (!destroyed && bound && viewOwner === owner) { callbackId = id; }
                else if (typeof owner.removeDataChangedCallback === 'function') { owner.removeDataChangedCallback(id, 0); }
            }
        } catch (ignored) { /* A subsequent native data update can retry. */ }
        finally { registering = false; }
    }
    function update() {
        if (destroyed || !bound || updating) { return; }
        updating = true;
        try {
            registerModel();
            var owner = model(), raw = owner && unwrap(owner.state), value;
            if (typeof raw !== 'string' || raw.length > 32768) { throw new Error('state shape'); }
            value = JSON.parse(raw);
            if (!value || typeof value !== 'object' || Object.prototype.toString.call(value) === '[object Array]') { throw new Error('state object'); }
            state = value; render();
        } catch (ignored) { feedback('Settings unavailable. Close and reopen this window.', true); resize(); }
        finally { updating = false; }
    }
    function onKey(event) {
        if (destroyed || !bound) { return; }
        var escape = event.key === 'Escape' || event.key === 'Esc' || event.keyCode === 27;
        if (escape && event.type === 'keydown') { stop(event, true); send(capturing() ? 'cancel_capture' : 'close'); return; }
        /* Browser keycodes are never used to build or save a shortcut. */
        if (capturing()) { stop(event, true); }
    }
    function off(engine, name, callback) { try { if (engine && typeof engine.off === 'function') { engine.off(name, callback); } } catch (ignored) { /* Closed renderer. */ } }
    function bind() {
        if (destroyed || bound || !window.engine || !window.viewEnv || typeof window.engine.on !== 'function') { return; }
        engineOwner = window.engine; viewOwner = window.viewEnv; bound = true;
        try {
            engineOwner.on('viewEnv.onDataChanged', update);
            if (destroyed) { off(engineOwner, 'viewEnv.onDataChanged', update); return; }
            for (var i = 0; i < layoutEvents.length; i += 1) {
                layoutCallbacks[i] = layoutCallback(layoutEvents[i]);
                engineOwner.on(layoutEvents[i], layoutCallbacks[i]);
            }
            update();
        }
        catch (ignored) { destroy(); }
    }
    function ready() {
        if (destroyed) { return; }
        if (window.isDomBuilt) { bind(); }
        else if (window.engine && typeof window.engine.on === 'function') { readyOwner = window.engine; readyOwner.on('self.onDomBuilt', bind); }
    }
    function destroy() {
        if (destroyed) { return; }
        if (capturing()) { state = {}; send('cancel_capture'); }
        if (destroyed) { return; }
        destroyed = true; bound = false; cancelResize();
        var owner = viewOwner, id = callbackId; callbackId = null; viewOwner = null;
        off(engineOwner, 'viewEnv.onDataChanged', update);
        for (var i = 0; i < layoutEvents.length; i += 1) { off(engineOwner, layoutEvents[i], layoutCallbacks[i]); }
        layoutCallbacks = [];
        off(readyOwner, 'self.onDomBuilt', bind); engineOwner = readyOwner = null;
        try { if (owner && id !== null && typeof owner.removeDataChangedCallback === 'function') { owner.removeDataChangedCallback(id, 0); } } catch (ignored) { /* Native view already disposed. */ }
        document.removeEventListener('keydown', onKey, true); document.removeEventListener('keyup', onKey, true); window.removeEventListener('beforeunload', destroy);
    }
    window.GRZStaySharpSettings = {refresh:update, destroy:destroy};
    document.addEventListener('keydown', onKey, true); document.addEventListener('keyup', onKey, true); window.addEventListener('beforeunload', destroy);
    try { if (root && window.engine && window.engine.whenReady && typeof window.engine.whenReady.then === 'function') { window.engine.whenReady.then(ready, destroy); } }
    catch (ignored) { destroy(); }
}());
