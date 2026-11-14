/* Owned cell in RandomBattleResultsView's verified personal-efficiency header. */
(function () {
    'use strict';
    if (window.GRZPostBattleWn8) { return; }
    var widget = null, feature = null, subscription = null;
    var dataEngine = null, readyEngine = null, observer = null;
    var bound = false, destroyed = false, queued = false, generation = 0;
    var refreshTimer = null;
    var reported = {};
    var defaults = {'format.thousands':'\u00a0', 'format.missing':'\u2014',
        'footer.processing':'Processing results',
        'coverage.wn8.battle':'Insufficient data to calculate this battle\u2019s WN8.'};

    // The same published WoT-Life text palette as the statistics panel.
    function wn8Color(value) {
        if (typeof value !== 'number' || !isFinite(value) || value < 0) { return null; }
        value = Math.round(value);
        var limits = [300, 600, 900, 1250, 1600, 1900, 2350, 2900];
        var colors = ['#000000', '#cd3333', '#d77900', '#d7b600', '#6d9521', '#4c762e', '#4a92b7', '#83579d', '#5a3175'];
        for (var index = 0; index < limits.length; index += 1) {
            if (value < limits[index]) { return colors[index]; }
        }
        return colors[colors.length - 1];
    }
    function paintWN8Ink(node, black) {
        var ink = node.querySelector('.ss-wn8-low-ink');
        if (!black) {
            if (ink) {
                var text = ink.textContent;
                node.removeChild(ink);
                node.textContent = text;
            }
            return;
        }
        if (!ink) {
            ink = node.ownerDocument.createElement('span');
            ink.className = 'ss-wn8-low-ink';
            ink.textContent = node.textContent;
            node.textContent = '';
            node.appendChild(ink);
        }
        // Use the panel's figure-only backing for the black rating band.
        ink.style.backgroundColor = 'rgba(180,192,166,0.65)';
        ink.style.borderRadius = '2rem';
        ink.style.boxShadow = 'none';
        ink.style.fontWeight = 'bold';
    }
    function paintWN8(node, value) {
        var color = wn8Color(value);
        paintWN8Ink(node, color === '#000000');
        node.style.color = color || '';
        // Black digits use their muted backing; colored ratings keep their halo.
        node.style.textShadow = color === '#000000' ? 'none' :
            color ? '0 0 0.7rem rgba(212,204,176,0.35)' : '';
        if (color) { node.setAttribute('data-wn8-value', String(Math.round(value))); }
        else { node.removeAttribute('data-wn8-value'); }
        return node;
    }
    function paintWN8Caption(node, value) {
        var color = wn8Color(value);
        paintWN8Ink(node, false);
        node.style.color = color && color !== '#000000' ? color : '';
        node.style.textShadow = 'none';
        node.removeAttribute('data-wn8-value');
        if (color) { node.setAttribute('data-wn8-caption-value', String(Math.round(value))); }
        else { node.removeAttribute('data-wn8-caption-value'); }
        return node;
    }
    function report(stage) {
        if (reported[stage]) { return; }
        reported[stage] = true;
        try {
            if (window.console && typeof window.console.warn === 'function') {
                window.console.warn('GRZ Session Stats: optional post-battle WN8 unavailable (' + stage + ').');
            }
        } catch (ignored) { /* Optional diagnostics cannot interrupt native results. */ }
    }
    function unwrap(value) {
        return value && typeof value === 'object' && value.value !== undefined ? value.value : value;
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
        if (!window.subViews || typeof window.subViews.ids !== 'function' || typeof window.subViews.get !== 'function') { return null; }
        var ids = idsArray(window.subViews.ids()), index, view, model;
        for (index = 0; index < ids.length; index += 1) {
            view = unwrap(window.subViews.get(ids[index]));
            model = view && unwrap(view.model);
            if (model && model.grzPostBattleWn8 !== undefined) {
                return {id:ids[index], model:unwrap(model.grzPostBattleWn8)};
            }
        }
        return null;
    }
    function removeWidget() {
        if (widget && widget.parentNode) { widget.parentNode.removeChild(widget); }
        widget = null;
    }
    function removeModelCallback(owner, id) {
        if (!owner || id === null || id === undefined) { return; }
        try {
            if (owner.viewEnv && typeof owner.viewEnv.removeDataChangedCallback === 'function') {
                owner.viewEnv.removeDataChangedCallback(id, owner.id);
            }
        } catch (error) { report('model cleanup'); }
    }
    function syncFeature() {
        var found = findFeature();
        if (destroyed) { return; }
        var id = found ? found.id : null, owner = subscription, previous;
        feature = found ? found.model : null;
        if ((owner && (owner.id !== id || owner.viewEnv !== window.viewEnv)) || (!owner && id !== null)) {
            previous = owner;
            owner = id === null ? null : {id:id, viewEnv:window.viewEnv, callbackId:null, registering:false, active:true};
            subscription = owner;
            if (previous) {
                previous.active = false;
                var oldId = previous.callbackId;
                previous.callbackId = null;
                removeModelCallback(previous, oldId);
            }
        }
        if (destroyed || owner !== subscription) { return; }
        if (bound && owner && owner.callbackId === null && !owner.registering && owner.viewEnv &&
                typeof owner.viewEnv.addDataChangedCallback === 'function') {
            owner.registering = true;
            try {
                var registered = owner.viewEnv.addDataChangedCallback('model', owner.id, true);
                if (registered !== null && registered !== undefined) {
                    if (!destroyed && owner.active && subscription === owner && window.viewEnv === owner.viewEnv) { owner.callbackId = registered; }
                    else { removeModelCallback(owner, registered); }
                }
            } catch (error) { report('model registration'); }
            finally { owner.registering = false; }
        }
        if (!feature) { removeWidget(); }
    }
    function insertion() {
        // Client bundle 3605bd36: the bottom seven stats are a div-based
        // TableHeader/TableRow inside this specific PersonalEfficiency table.
        var row = document.querySelector('[class*="PersonalEfficiency_totalEfficiencyTable_"] [data-name="TableHeader"] [data-name="TableRow"]');
        if (row) { return {parent:row, empty:false}; }
        // A zero-efficiency result intentionally has no table. Keep its native
        // explanation and append our own normal-flow status beneath it.
        var empty = document.querySelector('[class*="Overview_"] [class*="PersonalEfficiency_messagesPanel_"]');
        return empty ? {parent:empty, empty:true} : null;
    }
    function appendSpan(parent, className, text) {
        var span = document.createElement('span');
        span.className = className;
        if (text !== undefined) { span.textContent = text; }
        parent.appendChild(span);
        return span;
    }
    function ensureWidget() {
        var anchor = feature && insertion();
        if (!anchor) { removeWidget(); return; }
        if (!widget || !document.documentElement.contains(widget)) {
            removeWidget();
            widget = document.createElement('div');
            widget.id = 'grz-postbattle-wn8';
            widget.setAttribute('role', 'status');
            widget.setAttribute('aria-live', 'polite');
            appendSpan(widget, 'grz-postbattle-wn8-label', 'WN8');
            var slot = appendSpan(widget, 'grz-postbattle-wn8-slot');
            appendSpan(slot, 'grz-postbattle-wn8-value', defaults['format.missing']);
            appendSpan(slot, 'grz-postbattle-wn8-spinner').setAttribute('aria-hidden', 'true');
        }
        var kind = anchor.empty ? ' grz-postbattle-wn8-empty' : '';
        widget.setAttribute('data-placement', anchor.empty ? 'empty' : 'table');
        widget._grzPlacement = kind;
        if (widget.parentNode !== anchor.parent) { anchor.parent.appendChild(widget); }
    }
    function readRating() {
        try {
            var raw = feature && unwrap(feature.rating);
            if (typeof raw !== 'string' || raw.length > 16384) { throw new Error('rating shape'); }
            var value = JSON.parse(raw);
            if (!value || typeof value !== 'object') { throw new Error('rating payload'); }
            if (value.state === 'ready' && (typeof value.value !== 'number' || !isFinite(value.value) || value.value < 0)) {
                value.state = 'unavailable';
            }
            if (['ready', 'pending', 'unavailable'].indexOf(value.state) < 0) { value.state = 'unavailable'; }
            return value;
        } catch (error) { report('rating'); return {state:'unavailable', value:null}; }
    }
    function updateRating() {
        if (!widget) { return; }
        var rating = readRating();
        function text(key) {
            var value = rating.labels && rating.labels[key];
            return typeof value === 'string' && value && value.length <= 4096 ? value : defaults[key];
        }
        var pending = rating.state === 'pending';
        var value = rating.state === 'ready' ? String(Math.round(rating.value)).replace(/\B(?=(\d{3})+(?!\d))/g, text('format.thousands')) : text('format.missing');
        var label = 'WN8 ' + (pending ? text('footer.processing') : rating.state === 'ready' ? value : text('coverage.wn8.battle'));
        var className = 'grz-postbattle-wn8' + widget._grzPlacement + (pending ? ' grz-postbattle-wn8-pending' : '');
        if (widget.className !== className) { widget.className = className; }
        var output = widget.querySelector('.grz-postbattle-wn8-value');
        if (output.textContent !== value) { output.textContent = value; }
        var numeric = rating.state === 'ready' ? rating.value : null;
        paintWN8Caption(widget.querySelector('.grz-postbattle-wn8-label'), numeric);
        paintWN8(output, numeric);
        if (widget.getAttribute('aria-label') !== label) { widget.setAttribute('aria-label', label); }
        if (widget.getAttribute('aria-busy') !== String(pending)) { widget.setAttribute('aria-busy', String(pending)); }
    }
    function update() {
        if (destroyed) { return; }
        try {
            syncFeature();
            if (destroyed) { return; }
            ensureWidget();
            updateRating();
        } catch (error) { feature = null; removeWidget(); report('refresh'); }
    }
    function queueRefresh() {
        if (destroyed || queued) { return; }
        queued = true;
        var ticket = generation;
        function refresh() {
            refreshTimer = null;
            queued = false;
            if (!destroyed && ticket === generation) { update(); }
        }
        function afterEvent() {
            if (destroyed || ticket !== generation) { queued = false; return; }
            try { refreshTimer = window.setTimeout(refresh, 0); }
            catch (error) { queued = false; report('placement scheduling'); }
        }
        if (typeof window.requestAnimationFrame === 'function') {
            try {
                window.requestAnimationFrame(function () {
                    if (!destroyed && ticket === generation) {
                        try { window.requestAnimationFrame(refresh); }
                        catch (error) { afterEvent(); }
                    }
                });
            } catch (error) { afterEvent(); }
        } else { afterEvent(); }
    }
    function onDataChanged() {
        update();
        // Native model notifications can precede React's DOM commit. Retry
        // placement once after layout even when MutationObserver is absent.
        queueRefresh();
    }
    function watchDocument() {
        if (observer || typeof window.MutationObserver !== 'function') { return; }
        try {
            observer = new window.MutationObserver(queueRefresh);
            observer.observe(document.body || document.documentElement, {childList:true, subtree:true});
        } catch (error) {
            try { if (observer) { observer.disconnect(); } } catch (ignored) { /* Event-driven placement remains available. */ }
            observer = null;
            report('document observer');
        }
    }
    function removeEngineListener(engine, name, callback) {
        try { if (engine && typeof engine.off === 'function') { engine.off(name, callback); } }
        catch (error) { report('event cleanup'); }
    }
    function bind() {
        if (destroyed || bound || !window.engine || !window.viewEnv || typeof window.engine.on !== 'function') { return; }
        bound = true;
        try {
            var engine = window.engine;
            dataEngine = engine;
            engine.on('viewEnv.onDataChanged', onDataChanged);
            if (destroyed) { removeEngineListener(engine, 'viewEnv.onDataChanged', onDataChanged); return; }
            watchDocument();
            onDataChanged();
        } catch (error) { report('bind'); destroy(); }
    }
    function ready() {
        if (destroyed) { return; }
        try {
            if (window.isDomBuilt) { bind(); }
            else if (window.engine && typeof window.engine.on === 'function') {
                var engine = window.engine;
                readyEngine = engine;
                engine.on('self.onDomBuilt', bind);
                if (destroyed) { removeEngineListener(engine, 'self.onDomBuilt', bind); }
            }
        } catch (error) { report('ready'); destroy(); }
    }
    function destroy() {
        if (destroyed) { return; }
        destroyed = true;
        generation += 1;
        queued = false;
        if (refreshTimer !== null) {
            try { window.clearTimeout(refreshTimer); } catch (error) { /* Generation also retires retained callbacks. */ }
            refreshTimer = null;
        }
        var owner = subscription, id = owner ? owner.callbackId : null;
        var data = dataEngine, ready = readyEngine;
        subscription = dataEngine = readyEngine = feature = null;
        bound = false;
        if (owner) { owner.active = false; owner.callbackId = null; }
        if (observer) { observer.disconnect(); observer = null; }
        removeEngineListener(data, 'viewEnv.onDataChanged', onDataChanged);
        removeEngineListener(ready, 'self.onDomBuilt', bind);
        removeModelCallback(owner, id);
        removeWidget();
        window.removeEventListener('beforeunload', destroy);
    }
    window.GRZPostBattleWn8 = {refresh:onDataChanged, destroy:destroy};
    window.addEventListener('beforeunload', destroy);
    try {
        if (window.engine && window.engine.whenReady && typeof window.engine.whenReady.then === 'function') {
            window.engine.whenReady.then(ready, function () { report('host readiness'); destroy(); });
        }
    } catch (error) { report('bootstrap'); destroy(); }
}());
