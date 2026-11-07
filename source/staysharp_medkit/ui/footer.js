/* LobbyFooter owns only the icon. Settings use a separate native Wulf window. */
(function () {
    'use strict';
    if (window.GRZStaySharpFooter) { return; }
    var host = null, button = null, feature = null, subscription = null;
    var dataEngine = null, readyEngine = null, bound = false, destroyed = false, updating = false;
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
        var current = footer.querySelector('[class*="SessionStats"], [class*="sessionStats"], [class*="SessionStatistics"]');
        if (current) {
            while (current.parentNode && current.parentNode !== footer && current.parentNode.getAttribute && /SessionStats|sessionStats|SessionStatistics/.test(current.parentNode.getAttribute('class') || '')) { current = current.parentNode; }
            /* Start the whole native controls row, including controls that are
               already before WG session statistics. Never anchor on WN8. */
            return {parent:current.parentNode, before:current.parentNode.firstChild};
        }
        return {parent:footer, before:footer.firstChild};
    }
    function removeHost() { if (host && host.parentNode) { host.parentNode.removeChild(host); } host = button = null; }
    function open(event) {
        if (event && typeof event.stopPropagation === 'function') { event.stopPropagation(); }
        if (destroyed || !feature || !button) { return; }
        var anchor = 0, rect, width, command = feature.onAction;
        try {
            rect = button.getBoundingClientRect(); width = window.innerWidth;
            if (typeof width === 'number' && isFinite(width) && width > 0) { anchor = Math.max(0, Math.min(1, (rect.left + rect.width / 2) / width)); }
            var args = {action:'open', anchorX:anchor};
            if (typeof command === 'function') { command.call(feature, args); }
            else if (command && typeof command.value === 'function') { command.value.call(command, args); }
        } catch (error) { report('command'); }
    }
    function ensureHost() {
        if (host && document.documentElement.contains(host)) { return; }
        var insertion = insertionPoint();
        if (!insertion || !feature) { removeHost(); return; }
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
        try { dataEngine = window.engine; dataEngine.on('viewEnv.onDataChanged', update); if (destroyed) { off(dataEngine, 'viewEnv.onDataChanged', update); return; } update(); }
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
        off(data, 'viewEnv.onDataChanged', update); off(readyOwner, 'self.onDomBuilt', bind); removeModelCallback(owner, callback); removeHost(); window.removeEventListener('beforeunload', destroy);
    }
    window.GRZStaySharpFooter = {refresh:update, destroy:destroy};
    window.addEventListener('beforeunload', destroy);
    try { if (window.engine && window.engine.whenReady && typeof window.engine.whenReady.then === 'function') { window.engine.whenReady.then(ready, function () { report('host readiness'); destroy(); }); } }
    catch (error) { report('bootstrap'); destroy(); }
}());
