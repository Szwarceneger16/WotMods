/* Native Wulf Settings view. Native Python owns key capture and persistence. */
(function () {
    'use strict';
    if (window.GRZStaySharpSettings) { return; }
    var root = document.getElementById('grz-medkit-settings'), nodes = {}, state = {};
    var engineOwner = null, viewOwner = null, readyOwner = null, callbackId = null;
    var bound = false, registering = false, destroyed = false, updating = false, lastWidth = 0, lastHeight = 0;
    var defaults = {title:'Medkit hotkeys', toggle_mod:'Toggle mod', toggle_voice:'Toggle voice', cancel:'Cancel', clear:'Clear', close:'Close', capture:'Press keys\u2026', not_assigned:'Not assigned', hint:'Select a shortcut. Hold the keys together, then release all keys to save.'};
    var ids = ['title', 'close', 'label-mod', 'label-voice', 'mod', 'voice', 'clear-mod', 'clear-voice', 'hint', 'feedback', 'cancel'], index;
    for (index = 0; index < ids.length; index += 1) { nodes[ids[index]] = document.getElementById('grz-medkit-settings-' + ids[index]); }
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
    function send(action, binding) {
        if (destroyed || !bound) { return; }
        var owner = model(), command = owner && owner.onAction, args = {action:action};
        if (binding) { args.binding = binding; }
        try {
            if (typeof command === 'function') { command.call(owner, args); }
            else if (command && typeof command.value === 'function') { command.value.call(command, args); }
        } catch (ignored) { nodes.feedback.textContent = 'Action unavailable. Close and reopen settings.'; }
    }
    function stop(event, prevent) { if (event && event.stopPropagation) { event.stopPropagation(); } if (prevent && event && event.preventDefault) { event.preventDefault(); } }
    function bindButton(node, action, binding) { node.onclick = function (event) { stop(event, true); send(action, binding); }; }
    bindButton(nodes.mod, 'begin_capture', 'toggle_mod'); bindButton(nodes.voice, 'begin_capture', 'toggle_voice');
    bindButton(nodes['clear-mod'], 'clear_binding', 'toggle_mod'); bindButton(nodes['clear-voice'], 'clear_binding', 'toggle_voice');
    bindButton(nodes.cancel, 'cancel_capture'); bindButton(nodes.close, 'close');
    function resize() {
        var viewport = state.viewport, scale = viewport && viewport.scale, logicalWidth = 360;
        if (typeof scale !== 'number' || !isFinite(scale) || scale < 0.5 || scale > 4) { scale = 1; }
        if (viewport && typeof viewport.width === 'number' && isFinite(viewport.width) && viewport.width > 0) { logicalWidth = Math.min(360, viewport.width / scale); }
        document.documentElement.style.fontSize = String(scale) + 'px';
        root.style.width = String(logicalWidth) + 'rem'; document.body.style.width = String(logicalWidth) + 'rem';
        var width = Math.max(1, Math.ceil(logicalWidth * scale)), height = Math.ceil(230 * scale);
        if (lastWidth === width && lastHeight === height) { return; }
        try {
            if (viewOwner && typeof viewOwner.resizeViewPx === 'function') { viewOwner.resizeViewPx(width, height); lastWidth = width; lastHeight = height; }
        } catch (ignored) { /* Python keeps a bounded native-window fallback. */ }
    }
    function renderRow(binding, suffix) {
        var control = nodes[suffix], value = chord(state.display && state.display[binding]) || chord(state.hotkeys && state.hotkeys[binding]);
        var active = state.capturing === binding;
        nodes['label-' + suffix].textContent = label(binding);
        control.textContent = active ? (chord(state.preview) || label('capture')) : (value || label('not_assigned'));
        control.setAttribute('title', control.textContent);
        control.className = 'grz-medkit-settings-binding' + (active ? ' grz-medkit-settings-capturing' : '');
        control.setAttribute('aria-label', label(binding) + ': ' + control.textContent); control.setAttribute('aria-pressed', active ? 'true' : 'false');
        nodes['clear-' + suffix].textContent = label('clear'); nodes['clear-' + suffix].setAttribute('aria-label', label('clear') + ': ' + label(binding));
    }
    function render() {
        nodes.title.textContent = label('title'); nodes.close.setAttribute('title', label('close')); nodes.close.setAttribute('aria-label', label('close'));
        renderRow('toggle_mod', 'mod'); renderRow('toggle_voice', 'voice');
        nodes.hint.textContent = label('hint'); nodes.cancel.textContent = label('cancel'); nodes.cancel.style.display = capturing() ? 'block' : 'none';
        var error = safeText(state.error, '', 2048), status = safeText(state.status, '', 2048);
        nodes.feedback.textContent = error || status; nodes.feedback.className = 'grz-medkit-settings-feedback' + (error ? ' grz-medkit-settings-error' : '');
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
        } catch (ignored) { nodes.feedback.textContent = 'Settings unavailable. Close and reopen this window.'; }
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
        try { engineOwner.on('viewEnv.onDataChanged', update); if (destroyed) { off(engineOwner, 'viewEnv.onDataChanged', update); return; } update(); }
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
        destroyed = true; bound = false;
        var owner = viewOwner, id = callbackId; callbackId = null; viewOwner = null;
        off(engineOwner, 'viewEnv.onDataChanged', update); off(readyOwner, 'self.onDomBuilt', bind); engineOwner = readyOwner = null;
        try { if (owner && id !== null && typeof owner.removeDataChangedCallback === 'function') { owner.removeDataChangedCallback(id, 0); } } catch (ignored) { /* Native view already disposed. */ }
        document.removeEventListener('keydown', onKey, true); document.removeEventListener('keyup', onKey, true); window.removeEventListener('beforeunload', destroy);
    }
    window.GRZStaySharpSettings = {refresh:update, destroy:destroy};
    document.addEventListener('keydown', onKey, true); document.addEventListener('keyup', onKey, true); window.addEventListener('beforeunload', destroy);
    try { if (root && window.engine && window.engine.whenReady && typeof window.engine.whenReady.then === 'function') { window.engine.whenReady.then(ready, destroy); } }
    catch (ignored) { destroy(); }
}());
