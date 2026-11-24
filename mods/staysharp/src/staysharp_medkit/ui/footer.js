/* LobbyFooter owns only the icon. Settings use a separate native Wulf window. */
(function () {
    'use strict';
    if (window.GRZStaySharpFooter) { return; }
    var host = null, button = null, feature = null, subscription = null;
    var dataEngine = null, readyEngine = null, bound = false, destroyed = false, updating = false;
    var observer = null;
    var reported = {};
    function report(stage) {
        if (reported[stage]) { return; }
        reported[stage] = true;
        try { if (window.console && typeof window.console.warn === 'function') { window.console.warn('Stay Sharp: optional garage icon unavailable (' + stage + ').'); } }
        catch (ignored) { /* Diagnostics cannot interrupt the native footer. */ }
    }
    function unwrap(value) { return value && typeof value === 'object' && value.value !== undefined ? value.value : value; }
    function idsArray(ids) {
        var result = [], iterator, next, index;
        if (!ids) { return result; }
        if (typeof ids.length === 'number') { for (index = 0; index < ids.length; index += 1) { result.push(ids[index]); } return result; }
        iterator = typeof ids.next === 'function' ? ids : null;
        if (!iterator && typeof Symbol !== 'undefined' && Symbol.iterator && ids[Symbol.iterator]) { iterator = ids[Symbol.iterator](); }
        if (iterator) { next = iterator.next(); while (!next.done) { result.push(next.value); next = iterator.next(); } }
        return result;
    }
    function findFeature() {
        if (!window.subViews || typeof window.subViews.ids !== 'function' || typeof window.subViews.get !== 'function') { return null; }
        var ids = idsArray(window.subViews.ids()), index, view, model;
        for (index = 0; index < ids.length; index += 1) {
            view = window.subViews.get(ids[index]); model = view && view.model;
            if (model && model.grzMedkitFooter) { return {id:ids[index], model:unwrap(model.grzMedkitFooter)}; }
        }
        return null;
    }
    function insertionPoint() {
        var footer = document.querySelector('[class*="App_footer_"]');
        if (!footer) { return null; }
        // Native footer: Ping/EU2, menu gear, divider, notifications.
        // Keep the outer footer's three space-between sections intact.
        var menu = footer.querySelector('[data-test-id="menu"]'), parent = menu && menu.parentNode;
        if (!parent || !parent.getAttribute || !/(^|\s)Footer_section_/.test(parent.getAttribute('class') || '')) { return null; }
        return {parent:parent, before:menu};
    }
    function removeHost() { if (host && host.parentNode) { host.parentNode.removeChild(host); } host = button = null; }
    function finite(value) { return typeof value === 'number' && isFinite(value); }
    function positive(value) { return finite(value) && value > 0; }
    function normalized(value) { return Math.max(0, Math.min(1, value)); }
    function anchorFor(rect) {
        var args = {action:'open', anchorX:0.5}, env = window.viewEnv, client, origin, x, y, width;
        if (!rect || !finite(rect.left) || !finite(rect.top) || !positive(rect.width)) { return args; }
        try {
            if (env && typeof env.getClientSizePx === 'function' && typeof env.getViewGlobalPositionRem === 'function' && typeof env.remToPx === 'function') {
                client = env.getClientSizePx(); origin = env.getViewGlobalPositionRem();
                if (client && origin && positive(client.width) && positive(client.height) && finite(origin.x) && finite(origin.y)) {
                    x = env.remToPx(origin.x); y = env.remToPx(origin.y);
                    if (finite(x) && finite(y)) {
                        args.anchorX = normalized((x + rect.left + rect.width / 2) / client.width);
                        args.anchorY = normalized((y + rect.top) / client.height);
                        return args;
                    }
                }
            }
        } catch (ignored) { report('native anchor'); }
        // Coherent may omit innerWidth. Its document width is a valid fallback
        // for X; footer-local height is never treated as full-screen height.
        width = document.documentElement && document.documentElement.clientWidth;
        if (!positive(width)) { width = window.innerWidth; }
        if (!positive(width)) { width = document.body && document.body.clientWidth; }
        if (positive(width)) { args.anchorX = normalized((rect.left + rect.width / 2) / width); }
        return args;
    }
    function open(event) {
        if (event && typeof event.stopPropagation === 'function') { event.stopPropagation(); }
        if (destroyed || !feature || !button) { return; }
        var command = feature.onAction;
        try {
            var args = anchorFor(button.getBoundingClientRect());
            if (typeof command === 'function') { command.call(feature, args); }
            else if (command && typeof command.value === 'function') { command.value.call(command, args); }
        } catch (error) { report('command'); }
    }
    function ensureHost() {
        var insertion = insertionPoint();
        if (!insertion || !feature) { removeHost(); return; }
        if (host && document.documentElement.contains(host)) {
            if (host.parentNode !== insertion.parent || host.nextSibling !== insertion.before) { insertion.parent.insertBefore(host, insertion.before); }
            return;
        }
        removeHost();
        host = document.createElement('div'); host.id = 'grz-medkit-footer-host'; host.className = 'grz-medkit-footer-host';
        button = document.createElement('button'); button.id = 'grz-medkit-footer-button'; button.className = 'grz-medkit-footer-button'; button.type = 'button';
        button.setAttribute('aria-haspopup', 'dialog'); button.onclick = open; host.appendChild(button);
        var icon = document.createElement('span'), classes = ['handle', 'case', 'cross-h', 'cross-v'], index, part;
        icon.className = 'grz-medkit-footer-icon'; icon.setAttribute('aria-hidden', 'true'); button.appendChild(icon);
        for (index = 0; index < classes.length; index += 1) { part = document.createElement('span'); part.className = 'grz-medkit-footer-' + classes[index]; icon.appendChild(part); }
        insertion.parent.insertBefore(host, insertion.before);
    }
    function render() {
        if (!button) { return; }
        var title = 'Medkit hotkeys', raw = feature && unwrap(feature.state), state;
        if (typeof raw === 'string' && raw.length <= 32768) {
            try { state = JSON.parse(raw); if (state && state.labels && typeof state.labels.title === 'string' && state.labels.title.length <= 1024) { title = state.labels.title; } }
            catch (ignored) { /* The native settings window validates its full payload. */ }
        }
        button.setAttribute('title', title); button.setAttribute('aria-label', title);
    }
    function removeModelCallback(owner, id) {
        if (!owner || id === null || id === undefined) { return; }
        try { if (owner.viewEnv && typeof owner.viewEnv.removeDataChangedCallback === 'function') { owner.viewEnv.removeDataChangedCallback(id, owner.id); } }
        catch (error) { report('model cleanup'); }
    }
    function syncFeature() {
        var found = findFeature(), nextId = found ? found.id : null, owner = subscription, previous;
        if (destroyed) { return; }
        if ((owner && (owner.id !== nextId || owner.viewEnv !== window.viewEnv)) || (!owner && nextId !== null)) {
            previous = owner; removeHost();
            owner = nextId === null ? null : {id:nextId, viewEnv:window.viewEnv, callbackId:null, registering:false, active:true}; subscription = owner;
            if (previous) { previous.active = false; var callback = previous.callbackId; previous.callbackId = null; removeModelCallback(previous, callback); }
        }
        feature = found ? found.model : null;
        if (destroyed || subscription !== owner) { return; }
        if (bound && owner && owner.callbackId === null && !owner.registering && owner.viewEnv && typeof owner.viewEnv.addDataChangedCallback === 'function') {
            owner.registering = true;
            try {
                var registered = owner.viewEnv.addDataChangedCallback('model', owner.id, true);
                if (registered !== undefined && registered !== null) {
                    if (!destroyed && owner.active && subscription === owner && window.viewEnv === owner.viewEnv) { owner.callbackId = registered; }
                    else { removeModelCallback(owner, registered); }
                }
            } catch (error) { report('model registration'); }
            finally { owner.registering = false; }
        }
        if (!feature) { removeHost(); }
    }
    function update() {
        if (destroyed || updating) { return; }
        updating = true;
        try { syncFeature(); if (!destroyed && feature) { ensureHost(); render(); } }
        catch (error) { feature = null; removeHost(); report('refresh'); }
        finally { updating = false; }
    }
    function off(engine, name, callback) {
        try { if (engine && typeof engine.off === 'function') { engine.off(name, callback); } }
        catch (error) { report('event cleanup'); }
    }
    function bind() {
        if (destroyed || bound || !window.engine || !window.viewEnv || typeof window.engine.on !== 'function') { return; }
        bound = true;
        try {
            dataEngine = window.engine; dataEngine.on('viewEnv.onDataChanged', update);
            if (destroyed) { off(dataEngine, 'viewEnv.onDataChanged', update); return; }
            if (typeof window.MutationObserver === 'function') {
                try {
                    observer = new window.MutationObserver(function () {
                        var insertion = insertionPoint();
                        if (!host || !insertion || host.parentNode !== insertion.parent || host.nextSibling !== insertion.before) { update(); }
                    });
                    observer.observe(document.documentElement, {childList:true, subtree:true});
                } catch (ignored) {
                    if (observer) { try { observer.disconnect(); } catch (cleanupIgnored) { /* Optional observation can be unavailable. */ } }
                    observer = null; report('native menu observation');
                }
            }
            update();
        }
        catch (error) { report('bind'); destroy(); }
    }
    function ready() {
        if (destroyed) { return; }
        try {
            if (window.isDomBuilt) { bind(); }
            else if (window.engine && typeof window.engine.on === 'function') { readyEngine = window.engine; readyEngine.on('self.onDomBuilt', bind); if (destroyed) { off(readyEngine, 'self.onDomBuilt', bind); } }
        } catch (error) { report('ready'); destroy(); }
    }
    function destroy() {
        if (destroyed) { return; }
        destroyed = true;
        var owner = subscription, callback = owner ? owner.callbackId : null, data = dataEngine, readyOwner = readyEngine;
        subscription = dataEngine = readyEngine = feature = null; bound = false;
        if (owner) { owner.active = false; owner.callbackId = null; }
        if (observer) { try { observer.disconnect(); } catch (ignored) { report('observer cleanup'); } observer = null; }
        off(data, 'viewEnv.onDataChanged', update); off(readyOwner, 'self.onDomBuilt', bind); removeModelCallback(owner, callback); removeHost(); window.removeEventListener('beforeunload', destroy);
    }
    window.GRZStaySharpFooter = {refresh:update, destroy:destroy};
    window.addEventListener('beforeunload', destroy);
    try { if (window.engine && window.engine.whenReady && typeof window.engine.whenReady.then === 'function') { window.engine.whenReady.then(ready, function () { report('host readiness'); destroy(); }); } }
    catch (error) { report('bootstrap'); destroy(); }
}());
