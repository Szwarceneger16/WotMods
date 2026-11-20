/* Injected by OpenWG into LobbyFooter. Own child ViewModel, no root interception. */
(function () {
    'use strict';
    if (window.GRZSessionFooter) { return; }
    var button = null;
    var subscription = null;
    var dataEngine = null;
    var readyEngine = null;
    var feature = null;
    var bound = false;
    var destroyed = false;
    var reported = {};
    var idleLabel = 'Session statistics: battles, win rate and WN8';
    var defaultLabels = {'footer.idle':idleLabel, 'footer.processing':'Processing results',
        'footer.waiting':'Waiting for results: {0}', 'status.pending':'Pending: {0}', 'metric.wn8':'WN8'};
    var appearanceNode = null;
    var appearanceCSS = '';

    function reportFailure(stage) {
        if (reported[stage]) { return; }
        reported[stage] = true;
        try {
            if (window.console && typeof window.console.warn === 'function') {
                window.console.warn('GRZ Session Stats: optional footer integration unavailable (' + stage + ').');
            }
        } catch (ignored) { /* Diagnostics must not enter native dispatch. */ }
    }

    function unwrap(value) {
        return value && typeof value === 'object' && value.value !== undefined ? value.value : value;
    }
    function clearAppearance() {
        try {
            if (appearanceNode && appearanceNode.parentNode) { appearanceNode.parentNode.removeChild(appearanceNode); }
        } catch (error) {
            try { appearanceNode.textContent = ''; } catch (ignored) { /* The native document may be gone. */ }
            reportFailure('appearance cleanup');
        }
        appearanceNode = null;
        appearanceCSS = '';
    }
    function updateAppearance() {
        try {
            var css = feature ? unwrap(feature.appearance) : undefined;
            if (css === undefined || css === null || css === '') { clearAppearance(); return; }
            // The Python validator compiles only our own scoped selectors.
            // The bridge accepts bounded text, never HTML or executable code.
            if (typeof css !== 'string' || css.length > 65536 || css.indexOf('\u0000') !== -1 || css.indexOf('<') !== -1) {
                throw new Error('appearance CSS shape');
            }
            if (css === appearanceCSS && appearanceNode && appearanceNode.parentNode) { return; }
            if (!appearanceNode || !appearanceNode.parentNode) {
                appearanceNode = document.createElement('style');
                appearanceNode.id = 'grz-session-footer-appearance';
                document.head.appendChild(appearanceNode);
            }
            appearanceNode.textContent = css;
            appearanceCSS = css;
        } catch (error) {
            clearAppearance();
            reportFailure('appearance');
        }
    }
    function readActivity() {
        var raw, value;
        try {
            raw = feature ? unwrap(feature.activity) : undefined;
            // Older/missing optional models keep the normal, usable icon.
            if (raw === undefined || raw === null) { return {pending:0, processing:false}; }
            if (typeof raw !== 'string' || raw.length > 131072) { throw new Error('activity shape'); }
            value = JSON.parse(raw);
            if (!value || typeof value !== 'object' ||
                    typeof value.pending !== 'number' || !isFinite(value.pending) ||
                    value.pending < 0 || Math.floor(value.pending) !== value.pending ||
                    typeof value.processing !== 'boolean') { throw new Error('activity values'); }
            return value;
        } catch (error) {
            reportFailure('activity');
            return {pending:0, processing:false};
        }
    }
    function updateActivity() {
        if (!button) { return; }
        var activity = readActivity();
        function text(key, count) {
            var value = activity.labels && activity.labels[key];
            if (typeof value !== 'string' || !value || value.length > 4096) { value = defaultLabels[key]; }
            return value.replace(/\{0\}/g, String(count));
        }
        var busy = activity.processing || activity.pending > 0;
        var className = 'grz-session-footer-button' + (busy ? ' grz-session-footer-busy' : '');
        var label = text('footer.idle');
        if (activity.processing) {
            label += '. ' + text('footer.processing') + (activity.pending > 0 ? ' (' + text('status.pending', activity.pending) + ')' : '') + '.';
        } else if (activity.pending > 0) {
            label += '. ' + text('footer.waiting', activity.pending) + '.';
        }
        var rating = button.querySelector('.grz-session-footer-rating');
        if (rating) { rating.textContent = text('metric.wn8'); }
        if (button.className !== className) { button.className = className; }
        if (button.getAttribute('title') !== label) { button.setAttribute('title', label); }
        if (button.getAttribute('aria-label') !== label) { button.setAttribute('aria-label', label); }
        if (button.getAttribute('aria-busy') !== String(busy)) { button.setAttribute('aria-busy', String(busy)); }
    }
    function idsArray(ids) {
        var result = [], iterator, next, index;
        if (!ids) { return result; }
        if (typeof ids.length === 'number') {
            for (index = 0; index < ids.length; index += 1) { result.push(ids[index]); }
            return result;
        }
        iterator = typeof ids.next === 'function' ? ids : null;
        if (!iterator && typeof Symbol !== 'undefined' && Symbol.iterator && ids[Symbol.iterator]) {
            iterator = ids[Symbol.iterator]();
        }
        if (iterator) {
            next = iterator.next();
            while (!next.done) { result.push(next.value); next = iterator.next(); }
        }
        return result;
    }
    function findFeature() {
        if (!window.subViews || typeof window.subViews.ids !== 'function' ||
                typeof window.subViews.get !== 'function') { return null; }
        var ids = idsArray(window.subViews.ids()), index, view, model;
        for (index = 0; index < ids.length; index += 1) {
            view = window.subViews.get(ids[index]);
            model = view && view.model;
            if (model && model.grzSessionFooter) {
                return { id:ids[index], model:unwrap(model.grzSessionFooter) };
            }
        }
        return null;
    }
    function openWindow() {
        if (destroyed) { return; }
        try {
            syncFeature();
            var command = feature && feature.onAction;
            if (typeof command === 'function') { command.call(feature, { action:'open' }); }
            else if (command && typeof command.value === 'function') { command.value.call(command, { action:'open' }); }
        } catch (error) {
            reportFailure('command');
        }
    }
    function footerSection(node, footer) {
        while (node && node !== footer) {
            if (/(^|\s)Footer_section_/.test(node.getAttribute('class') || '')) { return node; }
            node = node.parentNode;
        }
        return null;
    }
    function footerParent() {
        var footer = document.querySelector('[class*="App_footer_"]');
        if (!footer) { return null; }
        // Verified mono/hangar/footer: SessionStatistic (singular) is followed
        // by a divider, server, menu, divider and notificationCenter in the
        // right Footer_section. Keep the native row and all its spacing intact.
        var anchor = footer.querySelector('[class^="SessionStatistic_"], [class*=" SessionStatistic_"]');
        var section = footerSection(anchor, footer), current = anchor;
        if (section) {
            while (current.parentNode !== section) { current = current.parentNode; }
            return {parent:section, before:current.nextSibling};
        }
        // Some modes disable native session statistics. Its original slot is
        // immediately before this section's first divider, not after notices.
        var menu = footer.querySelector('[data-test-id="menu"], [data-test-id="notificationCenter"]');
        section = footerSection(menu, footer);
        if (!section) { return null; }
        var children = section.children;
        for (var index = 0; index < children.length; index += 1) {
            if (/(^|\s)Footer_divider_/.test(children[index].getAttribute('class') || '')) {
                return {parent:section, before:children[index]};
            }
        }
        // Keep a known notification/menu-only row usable without adding a new
        // sibling to the space-between footer's left/chat/right section layout.
        current = menu;
        while (current.parentNode !== section) { current = current.parentNode; }
        return {parent:section, before:current};
    }
    function placeButton(insertion) {
        // Only our node moves. Native slots retain their classes, spacing,
        // handlers and relative order, including when the footer is rebuilt.
        if (insertion.before !== button &&
                (button.parentNode !== insertion.parent || button.nextSibling !== insertion.before)) {
            insertion.parent.insertBefore(button, insertion.before);
        }
    }
    function removeButton() {
        clearAppearance();
        if (button && button.parentNode) { button.parentNode.removeChild(button); }
        button = null;
    }
    function removeModelCallback(owner, callbackId) {
        if (!owner || callbackId === null || callbackId === undefined) { return; }
        try {
            if (owner.viewEnv && typeof owner.viewEnv.removeDataChangedCallback === 'function') {
                owner.viewEnv.removeDataChangedCallback(callbackId, owner.id);
            }
        } catch (error) { reportFailure('model cleanup'); }
    }
    function syncFeature() {
        var found = findFeature();
        if (destroyed) { return; }
        var nextId = found ? found.id : null;
        var owner = subscription, previous;
        feature = found ? found.model : null;
        if ((owner && (owner.id !== nextId || owner.viewEnv !== window.viewEnv)) || (!owner && nextId !== null)) {
            previous = owner;
            owner = nextId === null ? null : {id:nextId, viewEnv:window.viewEnv,
                callbackId:null, registering:false, active:true};
            subscription = owner;
            if (previous) {
                previous.active = false;
                var previousCallback = previous.callbackId;
                previous.callbackId = null;
                removeModelCallback(previous, previousCallback);
            }
        }
        // Native registration/removal may synchronously switch models or close
        // the document. Only the same live owner may accept a returned callback.
        if (destroyed || subscription !== owner) { return; }
        if (bound && owner && owner.callbackId === null && !owner.registering && owner.viewEnv &&
                typeof owner.viewEnv.addDataChangedCallback === 'function') {
            owner.registering = true;
            try {
                var registered = owner.viewEnv.addDataChangedCallback('model', owner.id, true);
                if (registered !== undefined && registered !== null) {
                    if (!destroyed && owner.active && subscription === owner && window.viewEnv === owner.viewEnv) {
                        owner.callbackId = registered;
                    } else { removeModelCallback(owner, registered); }
                }
            } catch (error) { reportFailure('model registration'); }
            finally { owner.registering = false; }
        }
        if (!feature) { removeButton(); }
    }
    function ensureButton() {
        var insertion = footerParent();
        if (!insertion || !feature) { removeButton(); return; }
        if (button && document.documentElement.contains(button)) { placeButton(insertion); return; }
        if (button) { removeButton(); }
        button = document.createElement('button');
        button.id = 'grz-session-stats-footer-button';
        button.className = 'grz-session-footer-button';
        button.type = 'button';
        button.setAttribute('aria-label', idleLabel);
        button.setAttribute('title', idleLabel);
        /* No verified native icon asset is exposed here. Recreate only its
           three-bar shape; never clone a game button, its counter or handlers. */
        var icon = document.createElement('span');
        icon.className = 'grz-session-footer-icon';
        icon.setAttribute('aria-hidden', 'true');
        var bar, index;
        for (index = 0; index < 3; index += 1) {
            bar = document.createElement('span');
            bar.className = 'grz-session-footer-bar grz-session-footer-bar-' + index;
            icon.appendChild(bar);
        }
        button.appendChild(icon);
        var rating = document.createElement('span');
        rating.className = 'grz-session-footer-rating';
        rating.setAttribute('aria-hidden', 'true');
        rating.textContent = 'WN8';
        button.appendChild(rating);
        var spinner = document.createElement('span');
        spinner.className = 'grz-session-footer-spinner';
        spinner.setAttribute('aria-hidden', 'true');
        icon.appendChild(spinner);
        button.onclick = openWindow;
        placeButton(insertion);
    }
    function update() {
        if (destroyed) { return; }
        try {
            syncFeature();
            if (destroyed) { return; }
            ensureButton();
            updateAppearance();
            updateActivity();
        } catch (error) {
            // The shared native footer dispatcher must remain usable even
            // when a future OpenWG/subview contract no longer matches ours.
            feature = null;
            removeButton();
            reportFailure('refresh');
        }
    }
    function bind() {
        if (destroyed || bound || !window.engine || !window.viewEnv ||
                typeof window.engine.on !== 'function') { return; }
        bound = true;
        try {
            var engine = window.engine;
            dataEngine = engine;
            engine.on('viewEnv.onDataChanged', update);
            if (destroyed) {
                removeEngineListener(engine, 'viewEnv.onDataChanged', update, 'event cleanup');
                return;
            }
            update();
            if (typeof window.requestAnimationFrame === 'function') {
                window.requestAnimationFrame(function () {
                    if (!destroyed) { window.requestAnimationFrame(update); }
                });
            }
        } catch (error) {
            reportFailure('bind');
            destroy();
        }
    }
    function ready() {
        if (destroyed) { return; }
        try {
            if (window.isDomBuilt) { bind(); }
            else if (window.engine && typeof window.engine.on === 'function') {
                var engine = window.engine;
                readyEngine = engine;
                engine.on('self.onDomBuilt', bind);
                if (destroyed) { removeEngineListener(engine, 'self.onDomBuilt', bind, 'ready cleanup'); }
            }
        } catch (error) {
            reportFailure('ready');
            destroy();
        }
    }
    function removeEngineListener(engine, name, callback, stage) {
        try {
            if (engine && typeof engine.off === 'function') { engine.off(name, callback); }
        } catch (error) { reportFailure(stage); }
    }
    function destroy() {
        if (destroyed) { return; }
        destroyed = true;
        var owner = subscription;
        var callbackId = owner ? owner.callbackId : null;
        var data = dataEngine, ready = readyEngine;
        subscription = dataEngine = readyEngine = null;
        feature = null; bound = false;
        if (owner) { owner.active = false; owner.callbackId = null; }
        // Invalidate before native unsubscribe; callbacks returned after this
        // cleanup are removed by their registration's ownership check.
        removeEngineListener(data, 'viewEnv.onDataChanged', update, 'event cleanup');
        removeEngineListener(ready, 'self.onDomBuilt', bind, 'ready cleanup');
        removeModelCallback(owner, callbackId);
        removeButton();
        window.removeEventListener('beforeunload', destroy);
    }
    window.GRZSessionFooter = { refresh:update, destroy:destroy };
    window.addEventListener('beforeunload', destroy);
    try {
        if (window.engine && window.engine.whenReady && typeof window.engine.whenReady.then === 'function') {
            window.engine.whenReady.then(ready, function () {
                reportFailure('host readiness');
                destroy();
            });
        }
    } catch (error) {
        reportFailure('bootstrap');
        destroy();
    }
}());
