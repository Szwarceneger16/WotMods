/* GRZ Session Stats — no frameworks, no network calls, no demonstration data. */
(function () {
    'use strict';
    var root = document.getElementById('grz-session-stats');
    if (!root) { return; }

    var state = { scope: 'launch', group: 'vehicles', xp: 'base', payload: null,
        dialog: false, bound: false, nativeSession: false, binding: null, retry: null, retryDelay: 100, actionError: null,
        nativeWidth: 0, nativeHeight: 0, nativeScale: 1, diagnostics: {}, dragging: false,
        scrollSpeed: 1, appearanceNode: null, appearanceCSS: '', destroyed: false,
        orders: {}, openSelect: null, list: [], loadedCount: 40, renderedCount: 0 };
    // BEGIN GENERATED ENGLISH
    var english = {"cancel": "Cancel", "close": "Close", "close.symbol": "\u00d7", "core.account": "This save belongs to another account or region. Overwrite refused.", "core.battle": "Invalid battle record. Overwrite refused.", "core.boundaries": "Invalid session boundaries. Overwrite refused.", "core.closed": "This launch identifier is already closed. Reload data in a new process.", "core.create": "Could not create a session.", "core.current": "Invalid current period. Overwrite refused.", "core.invalid_id": "Invalid battle identifier.", "core.ledger": "Invalid ledger structure. Overwrite refused.", "core.load": "Could not safely load or initialize statistics. Data remains read-only.", "core.loading": "Loading history. New battle results are being saved.", "core.loading_timer": "History loading could not be scheduled. Restart the client; pending results remain saved.", "core.membership": "Some results have no known period: a reliable battle start time is missing.", "core.missing_id": "Missing battle identifier.", "core.more_notices": "Additional data notices are retained in local history.", "core.periods": "Saved periods are missing. Overwrite refused.", "core.reset_time": "Invalid reset time.", "core.result": "Invalid result record.", "core.time": "Invalid time.", "core.wn8": "No valid WN8 table. Other statistics remain available.", "coverage.battles": "{0} battles", "coverage.legend": "x/y: battles with this value / recorded battles.", "coverage.missing": "Incomplete statistics: results for {0} of {1} recorded battles. Percentages, averages and totals use received data.", "coverage.partial": "Incomplete data in {0} results. Missing values are marked beside each statistic.", "coverage.value": "Data available for {0} of {1} recorded battles.", "coverage.wn8.battle": "Insufficient data to calculate this battle\u2019s WN8.", "coverage.wn8.period": "Period WN8: data for {0} battles.", "error.action": "Could not complete the action. Try again.", "error.connection": "No connection to the game.", "error.snapshot": "Could not read statistics data.", "explain.costs": "Costs include settled battle expenses.", "explain.wn8": "Average battle WN8 may differ from period WN8.", "finance.battle": "Battle finances", "finance.bonds": "Bonds", "finance.costs": "Costs", "finance.credits": "Credits", "finance.currency": "Currency", "finance.gold": "Gold", "finance.income": "Income", "finance.net": "Net", "finance.period": "Battle finances", "footer.idle": "Session statistics: battles, win rate and WN8", "footer.processing": "Processing results", "footer.waiting": "Waiting for results: {0}", "format.date": "{0}.{1}.{2}, {3}:{4}", "format.date.short": "{0}.{1}, {2}:{3}", "format.decimal": ".", "format.missing": "\u2014", "format.thousands": "\u00a0", "groups.battles": "Battles", "groups.battles.aria": "Battle results", "groups.battles.count": "{0} battles", "groups.battles.total": "{0} battles", "groups.empty": "No recorded battles in this period. Results appear after a battle ends.", "groups.label": "Group results", "groups.maps": "Maps", "groups.maps.aria": "Results by map", "groups.maps.count": "{0} maps", "groups.maps.total": "{0} maps", "groups.tiers": "Tiers", "groups.tiers.aria": "Results by tier", "groups.tiers.count": "{0} tiers", "groups.tiers.total": "{0} tiers", "groups.vehicles": "Vehicles", "groups.vehicles.aria": "Results by vehicle", "groups.vehicles.count": "{0} vehicles", "groups.vehicles.total": "{0} vehicles", "health.log": "game.log (dedicated log unavailable)", "health.notice": "Session statistics: the compatibility check detected an unsupported or incomplete data format, or a result read error. Some statistics may be incomplete. Fields: {0}. Details: {1}", "health.warning": "A result format or read problem was detected during this launch. See the mod log.", "installation.save": "Installation history could not be saved; previous data was preserved.", "installation.unavailable": "Shared installation statistics are unavailable; account statistics remain active.", "language.auto": "Automatic", "language.de": "Deutsch", "language.en": "English", "language.es": "Espa\u00f1ol", "language.fr": "Fran\u00e7ais", "language.label": "Language", "language.pl": "Polski", "language.ru": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439", "language.save_error": "Could not save the language. Your configuration was preserved.", "language.uk": "\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430", "log.close": "Could not close the mod log ({0}).", "log.prepare": "Could not prepare a log entry ({0}).", "log.start": "Could not start the mod log ({0}).", "log.write": "Could not write the mod log ({0}).", "metric.avg": "Average", "metric.battle_wn8": "WN8", "metric.battles": "Battles", "metric.confirmed": "Results received", "metric.draws": "Draws", "metric.losses": "Losses", "metric.max": "Max", "metric.min": "Min", "metric.period_wn8": "Period WN8", "metric.win_rate": "Win rate", "metric.wins": "Wins", "metric.wn8": "WN8", "mode.random": "Random battles", "normalize.costs": "Inconsistent consumable/directive cost breakdown.", "normalize.factor": "Incomplete credits: the deduction multiplier is missing.", "normalize.finance": "Some financial data is not yet available.", "normalize.map": "Map name is unavailable in this client version.", "normalize.platoon": "Incomplete credits: platoon deductions are missing.", "normalize.reserve": "Deferred credits do not increase this balance.", "normalize.vehicle": "Vehicle name is unavailable in this client version.", "outcome.draw": "Draw", "outcome.loss": "Defeat", "outcome.unknown": "Unknown result", "outcome.win": "Victory", "page.next": "Next", "page.previous": "Previous", "page.status": "Page {0} of {1}", "performance.battle": "Battle performance", "performance.period": "Battle performance", "period.installation": "All accounts \u00b7 Since {0}", "period.since": "Since {0}", "preview.label": "Preview \u00b7 synthetic data", "preview.open": "Open panel", "preview.restore": "Restore example", "refresh": "Refresh", "reset": "Reset period", "reset.instance.body": "A new shared period starts for this installation and persists across game restarts. Account histories and their manual resets remain unchanged.", "reset.instance.title": "Reset \u201cInstallation\u201d?", "reset.manual.body": "A new period starts now for the current account. Other accounts keep their history.", "reset.manual.title": "Reset \u201cSince reset\u201d?", "runtime.account_wait": "Waiting for account data.", "runtime.backlog": "Incomplete earlier battle results: {0}. History is preserved; recovery continues in the background. You can also select Refresh.", "runtime.begin": "Could not read a battle beginning; some results may remain pending.", "runtime.bonus": "Post-battle bonus XP cannot be read; received XP may be incomplete.", "runtime.bonus_refresh": "Automatic bonus XP refresh is unavailable; select Refresh after using a bonus.", "runtime.bonus_timer": "Bonus XP refresh is unavailable; select Refresh after using a bonus.", "runtime.cache": "Pending results cannot be read; missing battles remain pending.", "runtime.data_dir": "Local user data directory was not found.", "runtime.diagnostics": "Some mod diagnostics are unavailable; check game.log.", "runtime.direct": "Direct result events are unavailable; some results may be delayed.", "runtime.events": "Some client events could not be handled; statistics may be incomplete.", "runtime.garage": "Session statistics will be available after the account loads in the garage.", "runtime.hotkey": "Keyboard shortcut is unavailable; use the garage statistics button.", "runtime.late": "Could not complete a late result; the battle remains pending.", "runtime.log_failed": "Cannot write the dedicated mod log. Diagnostics remain in game.log.", "runtime.log_notice": "Session statistics: cannot write the dedicated mod log. Check access to the data directory; details remain in game.log.", "runtime.log_unavailable": "Dedicated mod log is unavailable.", "runtime.observer": "Additional client result reads are unavailable; events and recovery queue remain active.", "runtime.open_files": "Could not open session statistics. Check mod files and game.log.", "runtime.open_log": "Could not open session statistics. Details were recorded in game.log.", "runtime.panel": "Statistics panel is unavailable; result collection remains active.", "runtime.panel_update": "Could not update the panel; saved results remain available.", "runtime.pending": "Could not read a pending result; the battle remains pending.", "runtime.polling": "Periodic backlog reads are unavailable; client result events remain active.", "runtime.posted": "Processed result notifications are unavailable; bonus XP may require Refresh.", "runtime.processed": "Could not read a processed result; the raw result remains available.", "runtime.results": "Could not read some battle results; statistics may be incomplete.", "runtime.saved": "Could not open saved statistics.", "runtime.thumbnails": "Thumbnails are unavailable in this client version; results remain available.", "runtime.tick": "Periodic result reading failed; statistics may be incomplete.", "runtime.wn8_invalid": "Bundled WN8 table is invalid.", "runtime.wn8_load": "Could not load the WN8 table; other statistics remain available.", "runtime.wn8_missing": "Bundled WN8 expected values table is missing.", "scope.group": "Session period", "scope.instance": "Installation", "scope.instance.title": "All accounts in this installation; saved until manual reset", "scope.launch": "Since launch", "scope.launch.short": "Since launch", "scope.launch.title": "Since game launch \u2014 current account", "scope.manual": "Since reset", "scope.manual.title": "Since manual reset \u2014 current account", "sort.asc": "Ascending", "sort.avg": "Avg", "sort.chronology": "Battle date", "sort.credits": "Credits (net)", "sort.desc": "Descending", "sort.direction": "Order", "sort.label": "Sort results", "sort.metric": "Sort by", "sort.newest": "Newest first", "sort.off": "Off", "sort.oldest": "Oldest first", "sort.statistic": "Statistic", "sort.xp_base": "Base XP", "sort.xp_received": "Received XP", "stats.period": "Whole period", "stats.region": "Statistics and results", "status.incomplete": "Incomplete data: results {0} / {1}", "status.notes": "Data notices: {0}", "status.pending": "Pending: {0}", "status.settled": "{0} completed battles", "storage.busy": "Data is in use by another process or the file lock is unavailable.", "storage.changed": "Another process changed the data. Reload it before saving.", "storage.collision": "Save generation conflict; previous data is preserved.", "storage.corrupt": "No valid save was found. Corrupted files were not overwritten.", "storage.failed": "Could not save statistics durably. The previous valid save is preserved.", "storage.format": "Unsupported storage format. Data remains read-only.", "storage.no_lock": "System file locking is unavailable; process protection and generation conflict detection remain active. Use one client to write this data.", "storage.readonly": "Saving is blocked: data is read-only.", "storage.recovered": "Recovered the previous valid save; the latest save was corrupted. Some recent results may need to be retrieved again.", "storage.schema": "Unsupported storage schema. Data remains read-only.", "storage.unsupported_write": "Cannot write an unsupported schema.", "title": "Session statistics", "unknown": "Unknown", "unknown.map": "Unknown map", "unknown.map_id": "Map {0}", "unknown.tier": "Unknown tier", "unknown.vehicle": "Unknown vehicle", "unknown.vehicle_id": "Vehicle {0}", "vehicle.AT_SPG": "Tank destroyer", "vehicle.SPG": "SPG", "vehicle.heavyTank": "Heavy tank", "vehicle.lightTank": "Light tank", "vehicle.mediumTank": "Medium tank", "visual.map": "Map", "visual.vehicle": "Vehicle", "waiting.data": "Waiting for data", "waiting.game": "Waiting for game data.", "waiting.results": "Waiting for battle results\u2026", "xp.base": "Base XP", "xp.free": "Free XP:", "xp.group": "Experience type", "xp.received": "Received XP"};
    // END GENERATED ENGLISH
    var translations = english;
    function t(key, args) {
        var value = translations[key];
        if (typeof value !== 'string') { value = english[key] || key; }
        return value.replace(/\{([0-9])\}/g, function (match, index) {
            return args && args[index] !== undefined ? String(args[index]) : match;
        });
    }
    function applyLanguage(value) {
        translations = value && value.messages && typeof value.messages === 'object' ? value.messages : english;
        var language = value && typeof value.language === 'string' ? value.language : 'en';
        if (document.documentElement.getAttribute('lang') !== language) {
            document.documentElement.setAttribute('lang', language);
        }
        var attributes = [['data-i18n', null], ['data-i18n-title', 'title'], ['data-i18n-aria', 'aria-label']];
        var index, list, item;
        for (index = 0; index < attributes.length; index += 1) {
            list = document.querySelectorAll('[' + attributes[index][0] + ']');
            for (item = 0; item < list.length; item += 1) {
                var text = t(list[item].getAttribute(attributes[index][0]));
                if (attributes[index][1]) { list[item].setAttribute(attributes[index][1], text); }
                else if (list[item].textContent !== text) { list[item].textContent = text; }
            }
        }
        var labels = document.querySelectorAll('.ss-control-label');
        for (index = 0; index < labels.length; index += 1) {
            if (!labels[index].parentNode.hasAttribute('data-i18n-title')) {
                labels[index].parentNode.setAttribute('title', labels[index].textContent);
            }
        }
        renderLanguage();
        if (state.dialog) { resetText(); }
    }
    var nodes = {};
    var ids = ['started', 'summary', 'groups', 'scroll', 'status', 'reset',
        'reset-overlay', 'reset-cancel', 'reset-confirm', 'close', 'refresh',
        'group-tabs', 'list-meta', 'titlebar'];
    var i;
    for (i = 0; i < ids.length; i += 1) { nodes[ids[i]] = document.getElementById('ss-' + ids[i]); }

    function element(tag, className, value) {
        var result = document.createElement(tag);
        if (className) { result.className = className; }
        if (value !== undefined && value !== null) { result.textContent = String(value); }
        return result;
    }
    function append(parent, child) { parent.appendChild(child); return child; }
    function clear(node) { while (node.firstChild) { node.removeChild(node.firstChild); } }
    function hasNumber(value) { return typeof value === 'number' && isFinite(value); }
    function integer(value) { return hasNumber(value) ? String(Math.round(value)) : t('format.missing'); }
    function number(value) {
        if (!hasNumber(value)) { return t('format.missing'); }
        return String(Math.round(value)).replace(/\B(?=(\d{3})+(?!\d))/g, function () { return t('format.thousands'); });
    }
    function signed(value) {
        if (!hasNumber(value)) { return t('format.missing'); }
        return value > 0 ? '+' + number(value) : (value < 0 ? '-' + number(-value) : '0');
    }
    function cost(value) {
        if (!hasNumber(value)) { return t('format.missing'); }
        return value === 0 ? '0' : '-' + number(Math.abs(value));
    }
    function rate(value) { return hasNumber(value) ? value.toFixed(1).replace('.', t('format.decimal')) + '%' : t('format.missing'); }
    function pad(value) { return value < 10 ? '0' + value : String(value); }
    function date(value, shortDate) {
        if (!hasNumber(value)) { return t('format.missing'); }
        var d = new Date(value * 1000);
        if (!isFinite(d.getTime())) { return t('format.missing'); }
        return shortDate ? t('format.date.short', [pad(d.getDate()), pad(d.getMonth() + 1), pad(d.getHours()), pad(d.getMinutes())]) :
            t('format.date', [pad(d.getDate()), pad(d.getMonth() + 1), d.getFullYear(), pad(d.getHours()), pad(d.getMinutes())]);
    }
    function unwrap(value) {
        if (value && typeof value === 'object' && value.value !== undefined) { return value.value; }
        return value;
    }
    function appearanceFailure() {
        if (state.diagnostics.appearance) { return; }
        state.diagnostics.appearance = true;
        try {
            if (window.console && typeof window.console.warn === 'function') {
                window.console.warn('GRZ Session Stats: appearance bridge unavailable; using stylesheet defaults.');
            }
        } catch (ignored) { /* A cosmetic failure must not interrupt statistics. */ }
    }
    function clearAppearance() {
        try {
            if (state.appearanceNode && state.appearanceNode.parentNode) {
                state.appearanceNode.parentNode.removeChild(state.appearanceNode);
            }
        } catch (error) {
            try { state.appearanceNode.textContent = ''; } catch (ignored) { /* Native DOM may be gone. */ }
            appearanceFailure();
        }
        state.appearanceNode = null;
        state.appearanceCSS = '';
    }
    function applyAppearance(raw) {
        state.scrollSpeed = 1;
        try {
            var value = unwrap(raw);
            if (value === undefined || value === null) { clearAppearance(); return; }
            if (typeof value !== 'object' || Array.isArray(value)) { throw new Error('appearance shape'); }
            var speed = unwrap(value.scroll_speed);
            if (speed !== undefined && speed !== null) {
                if (hasNumber(speed) && speed >= 0.1 && speed <= 8) { state.scrollSpeed = speed; }
                else { appearanceFailure(); }
            }
            // Python accepts only the documented colour/number fields and
            // compiles these declarations. No user CSS or markup is evaluated.
            var css = unwrap(value.panel_css);
            if (css === undefined || css === null || css === '') { clearAppearance(); return; }
            if (typeof css !== 'string' || css.length > 65536 || css.indexOf('\u0000') !== -1 || css.indexOf('<') !== -1) {
                throw new Error('appearance CSS shape');
            }
            if (css === state.appearanceCSS && state.appearanceNode && state.appearanceNode.parentNode) { return; }
            if (!state.appearanceNode || !state.appearanceNode.parentNode) {
                state.appearanceNode = document.createElement('style');
                state.appearanceNode.id = 'grz-session-stats-appearance';
                document.head.appendChild(state.appearanceNode);
            }
            state.appearanceNode.textContent = css;
            state.appearanceCSS = css;
        } catch (error) {
            clearAppearance();
            appearanceFailure();
        }
    }
    function series(value) {
        return value || { min: null, avg: null, max: null, sum: null, count: 0 };
    }
    function coverage(count, total) {
        return hasNumber(count) && count < total ? String(count) + '/' + String(total) : '';
    }
    function explainCoverage(node, count, total) {
        var text = t('coverage.value', [number(count), number(total)]);
        node.setAttribute('title', text);
        node.setAttribute('aria-label', text);
        return node;
    }
    function uniqueNotices(values) {
        var result = [], seen = {}, index, value, key;
        if (!Array.isArray(values)) { return result; }
        for (index = 0; index < values.length; index += 1) {
            value = values[index];
            if (typeof value !== 'string' || !value) { continue; }
            key = '$' + value;
            if (!Object.prototype.hasOwnProperty.call(seen, key)) {
                seen[key] = true;
                result.push(value);
            }
        }
        return result;
    }
    function observedTotal(stats) {
        return hasNumber(stats.observed_battles) && stats.observed_battles >= (stats.battles || 0) ?
            stats.observed_battles : (stats.battles || 0);
    }
    function battleCount(stats) {
        var total = observedTotal(stats);
        return number(stats.battles) + (total > (stats.battles || 0) ? ' / ' + number(total) : '');
    }
    function selected(id, active) {
        var button = document.getElementById(id);
        button.className = button.className.replace(/\s*is-active/g, '') + (active ? ' is-active' : '');
        button.setAttribute('aria-pressed', active ? 'true' : 'false');
    }
    function quantityClass(value) {
        return !hasNumber(value) ? ' ss-unknown' : (value > 0 ? ' ss-positive' : (value < 0 ? ' ss-negative' : ''));
    }
    function headlineStat(parent, label, value, wn8, compact) {
        var holder = append(parent, element('div', compact ? 'ss-group-kpi' : 'ss-kpi'));
        append(holder, element('span', 'ss-kpi-label', label));
        append(holder, element('strong', 'ss-kpi-value' + (wn8 ? ' ss-wn8' : ''), value));
    }
    function measureRow(parent, label, data, wn8, total) {
        var row = append(parent, element('div', 'ss-metric-row'));
        var name = append(row, element('div', 'ss-metric-name'));
        append(name, element('span', 'ss-cell-value', label));
        var partial = coverage(data.count, total);
        if (partial) { explainCoverage(append(name, element('span', 'ss-cell-coverage',
            ' (' + partial + ')')), data.count, total); }
        append(row, element('div', 'ss-metric-number', wn8 ? integer(data.min) : number(data.min)));
        append(row, element('div', 'ss-metric-number', wn8 ? integer(data.avg) : number(data.avg)));
        append(row, element('div', 'ss-metric-number', wn8 ? integer(data.max) : number(data.max)));
    }
    function battleMeasure(parent, label, value, wn8) {
        var row = append(parent, element('div', 'ss-battle-measure'));
        append(row, element('span', 'ss-battle-label', label));
        append(row, element('strong', 'ss-battle-value' + (wn8 ? ' ss-wn8' : ''),
            wn8 ? integer(value) : number(value)));
    }
    function moneyCell(parent, data, field, total, sharedCoverage) {
        var value = data[field];
        var output = field === 'costs' ? cost(value) : (field === 'net' ? signed(value) : number(value));
        var cell = append(parent, element('div', 'ss-money-value' +
            (field === 'net' ? quantityClass(value) : (!hasNumber(value) ? ' ss-unknown' : ''))));
        append(cell, element('span', 'ss-cell-value', output));
        var partial = coverage(data[field + '_count'], total);
        if (partial && !sharedCoverage) { explainCoverage(append(cell, element('span', 'ss-cell-coverage', partial)),
            data[field + '_count'], total); }
    }
    function moneyRow(parent, name, data, total) {
        data = data || {};
        var row = append(parent, element('div', 'ss-money-row'));
        var label = append(row, element('div', 'ss-money-label', name));
        var shared = data.income_count === data.costs_count && data.costs_count === data.net_count;
        var partial = coverage(data.income_count, total);
        if (shared && partial) { explainCoverage(append(label, element('span', 'ss-cell-coverage', partial)), data.income_count, total); }
        moneyCell(row, data, 'income', total, shared);
        moneyCell(row, data, 'costs', total, shared);
        moneyCell(row, data, 'net', total, shared);
    }
    function freeXP(parent, stats) {
        var free = append(parent, element('div', 'ss-free-xp'));
        append(free, element('span', '', t('xp.free')));
        append(free, element('strong', '', number(series(stats.free_xp).sum)));
        var partial = coverage(series(stats.free_xp).count, observedTotal(stats));
        if (partial) { explainCoverage(append(free, element('span', 'ss-count-coverage',
            ' (' + partial + ')')), series(stats.free_xp).count, observedTotal(stats)); }
    }
    function wn8Coverage(parent, stats, battle) {
        var partial = coverage(stats.wn8_count, observedTotal(stats));
        if (partial) { append(parent, element('span', 'ss-coverage-note',
            battle ? t('coverage.wn8.battle') : t('coverage.wn8.period', [partial]))); }
    }
    function details(parent, stats, global, battle) {
        stats = stats || {};
        var total = observedTotal(stats);
        var holder = append(parent, element('div', 'ss-details' + (battle ? ' ss-battle-details' : '')));
        var performance = append(holder, element('div', 'ss-performance' + (battle ? ' ss-battle-performance' : '')));
        append(performance, element('h3', 'ss-detail-title', battle ? t('performance.battle') : t('performance.period')));
        var xpLabel = state.xp === 'base' ? t('xp.base') : t('xp.received');
        var xp = series(state.xp === 'base' ? stats.xp_base : stats.xp_received);
        if (battle) {
            /* A battle row represents one result, not a distribution. Check
               coverage so a missing value cannot become a plausible zero. */
            battleMeasure(performance, xpLabel, xp.count === 1 ? xp.sum : null, false);
            battleMeasure(performance, t('metric.wn8'), stats.wn8_count === 1 ? stats.wn8 : null, true);
        } else {
            var header = append(performance, element('div', 'ss-metric-head'));
            append(header, element('div', 'ss-metric-name', ''));
            append(header, element('div', 'ss-metric-number', t('metric.min')));
            append(header, element('div', 'ss-metric-number', t('metric.avg')));
            append(header, element('div', 'ss-metric-number', t('metric.max')));
            measureRow(performance, xpLabel, xp, false, total);
            measureRow(performance, t('metric.battle_wn8'), series(stats.battle_wn8), true, total);
        }
        if (global) {
            append(performance, element('div', 'ss-explainer',
                t('explain.wn8')));
        }
        var economy = append(holder, element('div', 'ss-economy'));
        append(economy, element('h3', 'ss-detail-title', battle ? t('finance.battle') : t('finance.period')));
        var moneyHeader = append(economy, element('div', 'ss-money-head'));
        append(moneyHeader, element('div', 'ss-money-label', t('finance.currency')));
        append(moneyHeader, element('div', 'ss-money-value', t('finance.income')));
        append(moneyHeader, element('div', 'ss-money-value', t('finance.costs')));
        append(moneyHeader, element('div', 'ss-money-value', t('finance.net')));
        var currencies = stats.currencies || {};
        moneyRow(economy, t('finance.credits'), currencies.credits, total);
        moneyRow(economy, t('finance.bonds'), currencies.bonds, total);
        var gold = currencies.gold || {};
        if ((hasNumber(gold.income) && gold.income !== 0) ||
                (hasNumber(gold.costs) && gold.costs !== 0) ||
                (hasNumber(gold.net) && gold.net !== 0)) {
            moneyRow(economy, t('finance.gold'), gold, total);
        }
        if (global) {
            append(economy, element('div', 'ss-explainer',
                t('explain.costs')));
        }
    }
    function renderSummary(stats, scope) {
        clear(nodes.summary);
        var headline = append(nodes.summary, element('div', 'ss-headline'));
        var missing = observedTotal(stats) > (stats.battles || 0);
        headlineStat(headline, missing ? t('metric.confirmed') : t('metric.battles'), battleCount(stats), false, false);
        headlineStat(headline, missing ? t('metric.win_rate') + '*' : t('metric.win_rate'), rate(stats.win_rate), false, false);
        headlineStat(headline, t('metric.period_wn8'), integer(stats.wn8), true, false);
        var outcomes = append(nodes.summary, element('p', 'ss-outcomes'));
        append(outcomes, element('span', '', t('metric.wins') + ' '));
        append(outcomes, element('strong', '', number(stats.wins)));
        append(outcomes, element('span', '', '  ·  ' + t('metric.losses') + ' '));
        append(outcomes, element('strong', '', number(stats.losses)));
        append(outcomes, element('span', '', '  ·  ' + t('metric.draws') + ' '));
        append(outcomes, element('strong', '', number(stats.draws)));
        if (scope.pending > 0) {
            append(outcomes, element('span', '', '  ·  ' + t('status.pending', [number(scope.pending)])));
        }
        if (missing) {
            append(nodes.summary, element('p', 'ss-data-notice',
                t('coverage.missing', [number(stats.battles), number(observedTotal(stats))])));
        } else if (stats.partial_results > 0) {
            append(nodes.summary, element('p', 'ss-data-notice',
                t('coverage.partial', [number(stats.partial_results)])));
        }
        var summaryMeta = append(nodes.summary, element('div', 'ss-summary-meta'));
        freeXP(summaryMeta, stats);
        wn8Coverage(summaryMeta, stats, false);
        details(nodes.summary, stats, true);
        if (nodes.summary.querySelector('.ss-cell-coverage, .ss-count-coverage, .ss-coverage-note')) {
            append(nodes.summary, element('p', 'ss-coverage-note ss-coverage-legend', t('coverage.legend')));
        }
    }
    function tierText(tier) {
        return ['','I','II','III','IV','V','VI','VII','VIII','IX','X','XI'][tier] || '';
    }
    function vehicleType(type) {
        var labels = { lightTank:t('vehicle.lightTank'), mediumTank:t('vehicle.mediumTank'), heavyTank:t('vehicle.heavyTank'),
            AT_SPG:t('vehicle.AT_SPG'), SPG:t('vehicle.SPG') };
        return labels[type] || '';
    }
    function battleOutcome(outcome) {
        return { win:t('outcome.win'), loss:t('outcome.loss'), draw:t('outcome.draw') }[outcome] || t('outcome.unknown');
    }
    function appendOutcome(parent, item) {
        var outcome = {win:'win', loss:'loss', draw:'draw'}[item.outcome] || 'unknown';
        var badge = append(parent, element('span', 'ss-battle-outcome ss-outcome-' + outcome));
        var visual = item.outcome_visual, src = visual && visual.src;
        var name = {win:'Victory', loss:'Defeat', draw:'Draw'}[outcome];
        var base = name && 'img://gui/maps/icons/library/BgBattleResultIcon' + name + '-1';
        /* Only the verified WG artwork for this exact result; labels remain
           translated text and survive missing textures or rejected URLs. */
        if (visual && visual.kind === 'outcome' && base && (src === base + '.png' || src === base + '.dds')) {
            badge.className += ' ss-outcome-art';
            var art = append(badge, element('span', 'ss-outcome-image'));
            art.setAttribute('aria-hidden', 'true');
            art.style.backgroundImage = 'url("' + src + '")';
        }
        append(badge, element('span', 'ss-outcome-label', battleOutcome(item.outcome)));
    }
    var defaultOrder = {metric:'off', statistic:'avg', direction:'desc', chronology:'newest'};
    var selectOptions = {
        language:[['auto','language.auto'],['en','language.en'],['pl','language.pl'],['ru','language.ru'],['fr','language.fr'],['de','language.de'],['es','language.es'],['uk','language.uk']],
        chronology:[['newest','sort.newest'],['oldest','sort.oldest']],
        statistic:[['min','metric.min'],['avg','sort.avg'],['max','metric.max']],
        metric:[['off','sort.off'],['xp_base','sort.xp_base'],['xp_received','sort.xp_received'],['credits_net','sort.credits'],['battle_wn8','metric.wn8']],
        direction:[['asc','sort.asc'],['desc','sort.desc']]
    };
    function orderKey(scope) {
        return String((state.payload || {}).account_key) + '/' + state.scope + '/' + String(scope.period_id || scope.started_at) + '/' + state.group;
    }
    function getOrder(scope) {
        return (state.nativeSession && scope.ordering && scope.ordering[state.group]) || state.orders[orderKey(scope)] || defaultOrder;
    }
    function ordered(items, options) {
        var copy = items.slice(0);
        copy.sort(function (a, b) {
            var left, right, metric = options.metric;
            if (metric !== 'off') {
                left = ((a.stats || {})[metric] || {})[options.statistic];
                right = ((b.stats || {})[metric] || {})[options.statistic];
                if (hasNumber(left) !== hasNumber(right)) { return hasNumber(left) ? -1 : 1; }
                if (hasNumber(left) && left !== right) { return options.direction === 'asc' ? left - right : right - left; }
            }
            left = options.chronology === 'oldest' && a.first_started_at !== undefined ? a.first_started_at : a.started_at;
            right = options.chronology === 'oldest' && b.first_started_at !== undefined ? b.first_started_at : b.started_at;
            if (hasNumber(left) !== hasNumber(right)) { return hasNumber(left) ? -1 : 1; }
            if (hasNumber(left) && left !== right) { return options.chronology === 'oldest' ? left - right : right - left; }
            left = String(a.id || ''), right = String(b.id || '');
            return left < right ? -1 : (left > right ? 1 : 0);
        });
        return copy;
    }
    function closeSelect(restoreFocus) {
        var control = state.openSelect;
        if (!control) { return; }
        control.menu.style.display = 'none';
        control.trigger.setAttribute('aria-expanded','false');
        state.openSelect = null;
        if (restoreFocus) { focusControl(control.trigger); }
    }
    function changeOrder(field, value) {
        if (state.destroyed || !state.payload || !state.payload.scopes) { return; }
        var scope = state.payload.scopes[state.scope];
        if (!scope) { return; }
        var current = getOrder(scope), options = {}, key;
        for (key in defaultOrder) { options[key] = current[key]; }
        options[field] = value;
        state.loadedCount = 40; nodes.scroll.scrollTop = 0;
        if (state.nativeSession && scope.pagination) {
            options.scope = state.scope; options.group = state.group;
            options.period_id = scope.period_id; options.account_key = state.payload.account_key;
            invoke('sort',options);
        } else {
            state.orders[orderKey(scope)] = options;
            render();
        }
    }
    var selects = {};
    function makeSelect(field) {
        var holder = document.getElementById(field === 'language' ? 'ss-language' : 'ss-sort-' + field);
        var trigger = append(holder,element('button','ss-control ss-button ss-select-trigger'));
        trigger.type = 'button'; trigger.setAttribute('tabindex','0'); trigger.setAttribute('role','combobox');
        trigger.setAttribute('aria-haspopup','listbox'); trigger.setAttribute('aria-expanded','false');
        trigger.setAttribute('aria-controls','ss-options-' + field);
        var label = append(trigger,element('span','ss-control-label'));
        append(trigger,element('span','ss-select-arrow')).setAttribute('aria-hidden','true');
        var menu = append(holder,element('div','ss-select-options'));
        menu.id = 'ss-options-' + field; menu.setAttribute('role','listbox'); menu.style.display = 'none';
        var control = {trigger:trigger,label:label,menu:menu,options:[]};
        function open(position) {
            if (state.destroyed) { return; }
            closeSelect(false); menu.style.display = 'block'; trigger.setAttribute('aria-expanded','true');
            state.openSelect = control;
            var selectedIndex = 0, index;
            for (index = 0; index < control.options.length; index += 1) {
                if (control.options[index].getAttribute('aria-selected') === 'true') { selectedIndex = index; }
            }
            focusControl(control.options[position === undefined ? selectedIndex : position]);
        }
        function choose(value) { closeSelect(true); if (field === 'language') { changeLanguage(value); } else { changeOrder(field,value); } }
        selectOptions[field].forEach(function (option, index) {
            var button = append(menu,element('button','ss-control ss-select-option'));
            button.type = 'button'; button.setAttribute('role','option'); button.setAttribute('tabindex','-1');
            button.setAttribute('data-value',option[0]); button.setAttribute('aria-selected','false');
            append(button,element('span','ss-control-label'));
            button.onclick = function () { choose(option[0]); };
            button.onkeydown = function (event) {
                var key = event.key || event.keyCode, target = null;
                if (key === 'ArrowDown' || key === 40) { target = (index + 1) % control.options.length; }
                if (key === 'ArrowUp' || key === 38) { target = (index + control.options.length - 1) % control.options.length; }
                if (key === 'Home' || key === 36) { target = 0; }
                if (key === 'End' || key === 35) { target = control.options.length - 1; }
                if (target !== null) { event.preventDefault(); event.stopPropagation(); focusControl(control.options[target]); }
                if (key === 'Enter' || key === 13 || key === ' ' || key === 32) { event.preventDefault(); choose(option[0]); }
                if (key === 'Tab' || key === 9) { closeSelect(true); }
            };
            control.options.push(button);
        });
        trigger.onclick = function () { if (state.openSelect === control) { closeSelect(false); } else { open(); } };
        trigger.onkeydown = function (event) {
            var key = event.key || event.keyCode;
            if (key === 'ArrowDown' || key === 40 || key === 'ArrowUp' || key === 38) { event.preventDefault(); open(); }
        };
        selects[field] = control;
    }
    function changeLanguage(value) {
        if (!state.payload || state.destroyed) { return; }
        invoke('language',{language:value,account_key:state.payload.account_key});
    }
    function renderLanguage() {
        var control = selects.language;
        if (!control) { return; }
        var localization = state.payload && state.payload.localization;
        var value = localization && (localization.selected || localization.language) || 'auto';
        control.trigger.setAttribute('aria-label',t('language.label'));
        control.menu.setAttribute('aria-label',t('language.label'));
        selectOptions.language.forEach(function (choice,index) {
            var caption = t(choice[1]);
            control.options[index].querySelector('.ss-control-label').textContent = caption;
            control.options[index].setAttribute('aria-selected',String(choice[0] === value));
            if (choice[0] === value) { control.label.textContent = caption; control.trigger.setAttribute('title',t('language.label') + ': ' + caption); }
        });
    }
    function renderSelects(scope) {
        var options = getOrder(scope), field, index;
        for (field in selects) {
            if (field === 'language') { continue; }
            var control = selects[field], labelKey = field === 'chronology' ? 'sort.chronology' : 'sort.' + field;
            var disabled = options.metric === 'off' && (field === 'statistic' || field === 'direction');
            // Time ordering remains available as the tie-breaker for equal metric values.
            control.trigger.disabled = disabled;
            control.trigger.setAttribute('aria-label',t(labelKey));
            control.menu.setAttribute('aria-label',t(labelKey));
            for (index = 0; index < selectOptions[field].length; index += 1) {
                var choice = selectOptions[field][index], caption = t(choice[1]);
                control.options[index].querySelector('.ss-control-label').textContent = caption;
                control.options[index].setAttribute('aria-selected',String(choice[0] === options[field]));
                if (choice[0] === options[field]) {
                    control.label.textContent = caption; control.trigger.setAttribute('title',t(labelKey) + ': ' + caption);
                }
            }
        }
    }
    function outsideSelect(event) {
        if (!state.openSelect) { return; }
        var node = event.target, holder = state.openSelect.trigger.parentNode;
        while (node) { if (node === holder) { return; } node = node.parentNode; }
        closeSelect(false);
    }
    ['chronology','statistic','metric','direction','language'].forEach(makeSelect);
    document.addEventListener('mousedown',outsideSelect);
    function appendVisual(parent, item) {
        var visual = item.visual;
        if (!visual || (visual.kind !== 'vehicle' && visual.kind !== 'map')) { return; }
        var src = visual.src;
        var prefix = visual.kind === 'vehicle' ? 'img://gui/maps/icons/vehicle/' : 'img://gui/maps/icons/map/';
        /* URLs come from the native R/backport resolver, which checks ResMgr.isFile.
           UI accepts only these local asset families; no remote URLs or CSS escapes. */
        if (typeof src !== 'string' || src.indexOf(prefix) !== 0 || src.length <= prefix.length ||
                src.indexOf('..') !== -1 || /[^A-Za-z0-9_./:-]/.test(src)) { return; }
        var thumb = append(parent, element('div', 'ss-group-thumb'));
        thumb.setAttribute('role', 'img');
        thumb.setAttribute('aria-label', String(visual.alt || item.name || ''));
        /* Background contain is supported by Gameface; object-fit is not. */
        thumb.style.backgroundImage = 'url("' + src + '")';
    }
    function appendGroupBatch(limit) {
        var list = state.list;
        var end = Math.min(list.length, limit);
        var fragment = document.createDocumentFragment();
        var index, item, stats, group, header, identity, subtitle, heading, meta;
        var battle = state.group === 'battles';
        for (index = state.renderedCount; index < end; index += 1) {
            item = list[index];
            stats = item.stats || {};
            group = append(fragment, element('div', 'ss-group' + (battle ? ' ss-battle' : '')));
            group.setAttribute('role', 'group');
            group.setAttribute('data-group-id', String(item.id || ''));
            header = append(group, element('div', 'ss-group-header'));
            appendVisual(header, item);
            identity = append(header, element('div', 'ss-group-name'));
            heading = append(identity, element('div', 'ss-group-heading'));
            append(heading, element('h2', 'ss-group-title', item.name || t('unknown')));
            wn8Coverage(heading, stats, battle);
            subtitle = state.group === 'vehicles' ?
                (tierText(item.tier) + (vehicleType(item.type) ? ' · ' + vehicleType(item.type) : '')) :
                (battle ? date(item.started_at, true) + ' · ' + (item.map || t('unknown.map')) : '');
            meta = append(identity, element('div', 'ss-group-meta'));
            if (subtitle) { append(meta, element('div', 'ss-group-subtitle', subtitle)); }
            freeXP(meta, stats);
            if (battle) {
                appendOutcome(header, item);
            } else {
                headlineStat(header, t('metric.battles'), battleCount(stats), false, true);
                headlineStat(header, t('metric.win_rate'), rate(stats.win_rate), false, true);
                headlineStat(header, t('metric.wn8'), integer(stats.wn8), true, true);
            }
            details(group, stats, false, battle);
        }
        nodes.groups.appendChild(fragment);
        state.renderedCount = end;
        state.loadedCount = Math.max(40, end);
    }
    function renderGroups(scope) {
        clear(nodes.groups);
        state.list = state.nativeSession && scope.pagination ? (scope[state.group] || []).slice(0) : ordered(scope[state.group] || [], getOrder(scope));
        renderSelects(scope);
        document.getElementById('ss-sorting').style.display = 'flex';
        state.renderedCount = 0;
        nodes.groups.setAttribute('aria-label', t('groups.' + state.group + '.aria'));
        var page = scope.pagination && scope.pagination[state.group];
        nodes['list-meta'].textContent = t('groups.' + state.group + '.total', [number(page ? page.total : state.list.length)]);
        document.getElementById('ss-pagination').style.display = 'flex';
        document.getElementById('ss-page-previous').disabled = !page || page.page <= 0;
        document.getElementById('ss-page-next').disabled = !page || page.page + 1 >= page.pages;
        document.getElementById('ss-page-label').textContent = page ? t('page.status', [page.page + 1, page.pages]) : '';
        if (!state.list.length) {
            append(nodes.groups, element('p', 'ss-empty',
                t('groups.empty')));
            return;
        }
        appendGroupBatch(state.loadedCount);
    }
    function loadNearBottom() {
        if (state.renderedCount >= state.list.length) { return; }
        var remaining = nodes.scroll.scrollHeight - nodes.scroll.scrollTop - nodes.scroll.clientHeight;
        if (remaining <= 200) { appendGroupBatch(state.renderedCount + 40); }
    }
    function onNativeWheel(event) {
        /* WoT's vertical-scroll adapter treats positive deltaY as up (Next=-1).
           A browser's default overflow scroll uses the opposite sign. Only the
           bound Gameface document needs this adapter; the HTML preview keeps
           the browser's own wheel/trackpad handling. See WHEEL_0.2.4_SOURCE_EVIDENCE. */
        /* Do not add manual movement to a default action we cannot cancel. */
        if (!state.bound || !event || event.defaultPrevented || event.cancelable === false) { return; }
        if (state.dialog) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        var target = event.target;
        while (target && target !== nodes.scroll && target !== root) { target = target.parentNode; }
        if (target !== nodes.scroll) { return; }
        var vertical = event.deltaY;
        var horizontal = hasNumber(event.deltaX) ? event.deltaX : 0;
        if (!hasNumber(vertical)) { return; }
        /* This panel has one vertical list. Do not turn a horizontal gesture
           into vertical movement or let its smaller Y component scroll it. */
        if (event.shiftKey || (horizontal !== 0 && Math.abs(horizontal) >= Math.abs(vertical))) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        if (vertical === 0) { return; }
        event.preventDefault();
        event.stopPropagation();
        /* Gameface may report a normalized wheel delta such as +/-1, not a
           browser pixel distance. WoT's own vertical list uses its visible
           height / 4 per wheel event. Use that same proportional step so the
           list remains usable regardless of the device's delta magnitude or
           the client's UI scale. Explicit page-mode input keeps page units. */
        var step = (vertical < 0 ? 1 : -1) * nodes.scroll.clientHeight / 4;
        if (event.deltaMode === 2) { step = -vertical * nodes.scroll.clientHeight; }
        step *= state.scrollSpeed;
        var last = Math.max(0, nodes.scroll.scrollHeight - nodes.scroll.clientHeight);
        nodes.scroll.scrollTop = Math.max(0, Math.min(last, nodes.scroll.scrollTop + step));
        /* Some client revisions deliver programmatic scroll events later.
           Appending near the end must not depend on another wheel notch. */
        loadNearBottom();
    }
    function setStatus(message) { nodes.status.textContent = message; }
    function render() {
        var payload = state.payload;
        if (!payload || !payload.scopes) { return; }
        // Also accept older/pretranslated payloads without duplicating notices
        // or inflating the status count. Do not mutate the model's snapshot.
        var warnings = uniqueNotices(payload.warnings);
        var hasInstance = !!payload.scopes.instance;
        if (state.scope === 'instance' && !hasInstance) { state.scope = 'manual'; showReset(false); }
        var scopeNames = ['launch', 'manual', 'instance'], scopeIndex;
        for (scopeIndex = 0; scopeIndex < scopeNames.length; scopeIndex += 1) {
            var scopeButton = document.getElementById('ss-scope-' + scopeNames[scopeIndex]);
            scopeButton.style.width = hasInstance ? (scopeNames[scopeIndex] === 'instance' ? '40%' : '30%') : '50%';
            if (scopeNames[scopeIndex] === 'instance') { scopeButton.style.display = hasInstance ? 'flex' : 'none'; }
        }
        document.getElementById('ss-scope-launch').querySelector('.ss-control-label').textContent =
            hasInstance ? t('scope.launch.short') : t('scope.launch');
        var scope = payload.scopes[state.scope];
        if (!scope || !scope.summary) { return; }
        var oldTop = nodes.scroll.scrollTop;
        selected('ss-scope-launch', state.scope === 'launch');
        selected('ss-scope-manual', state.scope === 'manual');
        selected('ss-scope-instance', state.scope === 'instance');
        selected('ss-xp-base', state.xp === 'base');
        selected('ss-xp-received', state.xp === 'received');
        selected('ss-group-vehicles', state.group === 'vehicles');
        selected('ss-group-maps', state.group === 'maps');
        selected('ss-group-battles', state.group === 'battles');
        selected('ss-group-tiers', state.group === 'tiers');
        nodes.started.textContent = t(state.scope === 'instance' ? 'period.installation' : 'period.since', [date(scope.started_at, false)]);
        nodes.reset.style.display = state.scope !== 'launch' ? 'flex' : 'none';
        var loading = !!scope.loading || (state.scope !== 'instance' && !!payload.loading);
        var loadError = scope.load_error || (state.scope !== 'instance' && payload.load_error);
        nodes.reset.disabled = state.scope === 'launch' || loading || !!loadError;
        if (loading || loadError) {
            showReset(false);
            clear(nodes.summary);
            clear(nodes.groups);
            state.list = [];
            state.renderedCount = 0;
            nodes['list-meta'].textContent = '';
            document.getElementById('ss-pagination').style.display = 'none';
            document.getElementById('ss-sorting').style.display = 'none';
            closeSelect(false);
            nodes.started.textContent = '';
            var loadingText = loadError || t('core.loading');
            append(nodes.summary, element('p', 'ss-data-notice', loadingText));
            var loadingWarnings = warnings, loadingWarningIndex;
            for (loadingWarningIndex = 0; loadingWarningIndex < loadingWarnings.length; loadingWarningIndex += 1) {
                if (loadingWarnings[loadingWarningIndex] !== loadingText) {
                    append(nodes.summary, element('p', 'ss-data-notice', loadingWarnings[loadingWarningIndex]));
                }
            }
            setStatus(loadingText);
            return;
        }
        renderSummary(scope.summary, scope);
        if (warnings.length) {
            var notices = append(nodes.summary, element('div', 'ss-data-notices'));
            var warningIndex;
            for (warningIndex = 0; warningIndex < warnings.length; warningIndex += 1) {
                append(notices, element('p', 'ss-data-notice', warnings[warningIndex]));
            }
        }
        renderGroups(scope);
        var text = t('status.settled', [number(scope.summary.battles)]);
        if (observedTotal(scope.summary) > (scope.summary.battles || 0)) {
            text = t('status.incomplete', [number(scope.summary.battles), number(observedTotal(scope.summary))]);
        }
        if (scope.pending > 0) { text += ' · ' + t('status.pending', [number(scope.pending)]); }
        if (warnings.length) { text += ' · ' + t('status.notes', [warnings.length]); }
        setStatus(state.actionError || text);
        nodes.scroll.scrollTop = oldTop;
    }
    function update(payload) {
        closeSelect(false);
        if (state.destroyed) { return false; }
        try {
            var value = unwrap(payload);
            if (typeof value === 'string') { value = JSON.parse(value); }
            if (!value || typeof value !== 'object' || !value.scopes ||
                    !value.scopes.launch || !value.scopes.manual) { throw new Error('Invalid snapshot'); }
            if (state.dialog && state.payload && state.payload.account_key !== value.account_key) { showReset(false); }
            state.payload = value;
            state.actionError = null;
            applyLanguage(value.localization);
            applyAppearance(value.appearance);
            render();
            if (state.bound) { queueResize(); }
            return true;
        } catch (error) {
            setStatus(t('error.snapshot'));
            return false;
        }
    }
    function invoke(action, extra) {
        if (state.destroyed) { return false; }
        var args = { action: action }, key;
        if (extra) { for (key in extra) { if (Object.prototype.hasOwnProperty.call(extra, key)) { args[key] = String(extra[key]); } } }
        try {
            var model = window.model;
            var command = model && model.onAction;
            if (typeof command === 'function') { command.call(model, args); return true; }
            if (command && typeof command.value === 'function') { command.value.call(command, args); return true; }
            if (typeof window.GRZSessionStats.onAction === 'function') {
                window.GRZSessionStats.onAction(args); return true;
            }
        } catch (error) {
            if (action !== 'resize' && action !== 'diagnostic' && action !== 'viewport') {
                state.actionError = t('error.action');
                setStatus(state.actionError);
            }
            return false;
        }
        if (action !== 'resize' && action !== 'diagnostic' && action !== 'viewport') { setStatus(t('error.connection')); }
        return false;
    }
    function focusControl(node) {
        /* Focus support differs between Gameface releases. It must never stop a tab change. */
        if (node && typeof node.focus === 'function') {
            try { node.focus(); } catch (error) { /* Mouse interaction remains available. */ }
        }
    }
    function nativeMove(on) {
        if (!state.bound || !window.viewEnv || typeof window.viewEnv.handleViewEvent !== 'function') { return false; }
        try {
            /* The client's sendEvent.move helper (tutorial.js / MembersWindow).
               Wulf moves the native window; the DOM always stays at its own origin. */
            window.viewEnv.handleViewEvent({__Type:'GFViewEventProxy', type:16, isMouseEvent:true, on:on});
            return true;
        } catch (error) { return false; }
    }
    function endNativeDrag() {
        if (!state.dragging) { return; }
        state.dragging = false;
        nativeMove(false);
        invoke('drag', {active:false});
    }
    function beginNativeDrag(event) {
        if (!event || event.button !== 0 || state.dialog || state.dragging) { return; }
        var target = event.target;
        while (target && target !== nodes.titlebar) {
            if (target === nodes.close || target.tagName === 'BUTTON') { return; }
            target = target.parentNode;
        }
        if (target !== nodes.titlebar) { return; }
        if (nativeMove(true)) {
            state.dragging = true;
            /* Only a placement hint: this command does not implement dragging. */
            invoke('drag', {active:true});
            event.preventDefault();
        }
    }
    function showReset(show) {
        if (show) { endNativeDrag(); }
        state.dialog = !!show;
        resetText();
        nodes['reset-overlay'].style.display = show ? 'flex' : 'none';
        if (show) { focusControl(nodes['reset-cancel']); } else if (state.scope !== 'launch') { focusControl(nodes.reset); }
    }
    function resetText() {
        document.getElementById('ss-confirm-title').textContent = state.scope === 'instance' ?
            t('reset.instance.title') : t('reset.manual.title');
        document.getElementById('ss-confirm-message').textContent = state.scope === 'instance' ?
            t('reset.instance.body') :
            t('reset.manual.body');
    }
    function switchScope(scope) {
        closeSelect(false);
        if (!state.payload || !state.payload.scopes[scope]) { return; }
        state.scope = scope; state.loadedCount = 40;
        showReset(false); nodes.scroll.scrollTop = 0; render();
    }
    function switchGroup(group) {
        closeSelect(false);
        if (state.group !== group) { state.loadedCount = 40; }
        state.group = group; nodes.scroll.scrollTop = 0; render();
    }
    function changePage(direction) {
        if (state.destroyed || !state.payload || !state.payload.scopes) { return; }
        var scope = state.payload.scopes[state.scope];
        var page = scope && scope.pagination && scope.pagination[state.group];
        if (!page || page.page + direction < 0 || page.page + direction >= page.pages) { return; }
        state.loadedCount = 40; nodes.scroll.scrollTop = 0;
        invoke('page', {scope:state.scope, group:state.group, page:page.page + direction,
            period_id:scope.period_id, account_key:state.payload.account_key});
    }
    document.getElementById('ss-page-previous').onclick = function () { changePage(-1); };
    document.getElementById('ss-page-next').onclick = function () { changePage(1); };
    function switchXP(xp) { state.xp = xp; render(); }
    document.getElementById('ss-scope-launch').onclick = function () { switchScope('launch'); };
    document.getElementById('ss-scope-manual').onclick = function () { switchScope('manual'); };
    document.getElementById('ss-scope-instance').onclick = function () { switchScope('instance'); };
    document.getElementById('ss-xp-base').onclick = function () { switchXP('base'); };
    document.getElementById('ss-xp-received').onclick = function () { switchXP('received'); };
    document.getElementById('ss-group-vehicles').onclick = function () { switchGroup('vehicles'); };
    document.getElementById('ss-group-tiers').onclick = function () { switchGroup('tiers'); };
    document.getElementById('ss-group-maps').onclick = function () { switchGroup('maps'); };
    document.getElementById('ss-group-battles').onclick = function () { switchGroup('battles'); };
    nodes.close.onclick = function () { if (state.dialog) { showReset(false); } else { invoke('close'); } };
    nodes.refresh.onclick = function () { invoke('refresh'); };
    nodes.reset.onclick = function () { if (!nodes.reset.disabled && state.scope !== 'launch') { showReset(true); } };
    nodes['reset-cancel'].onclick = function () { showReset(false); };
    nodes['reset-confirm'].onclick = function () {
        if (state.scope !== 'launch' && state.dialog && invoke('reset', {
                scope:state.scope, account_key:state.payload.account_key
            })) { showReset(false); }
    };
    nodes.scroll.addEventListener('scroll', loadNearBottom);
    root.addEventListener('wheel', onNativeWheel, false);
    nodes.titlebar.addEventListener('mousedown', beginNativeDrag);
    document.addEventListener('mouseup', endNativeDrag);
    window.addEventListener('blur', endNativeDrag);
    function onKeyDown(event) {
        var key = event.key || event.keyCode;
        if (key === 'Escape' || key === 27) {
            event.preventDefault();
            endNativeDrag();
            if (state.openSelect) { closeSelect(true); return; }
            if (state.dialog) { showReset(false); } else { invoke('close'); }
        }
        if (state.dialog && (key === 'Tab' || key === 9)) {
            if (event.shiftKey && document.activeElement === nodes['reset-cancel']) {
                event.preventDefault(); focusControl(nodes['reset-confirm']);
            } else if (!event.shiftKey && document.activeElement === nodes['reset-confirm']) {
                event.preventDefault(); focusControl(nodes['reset-cancel']);
            }
        }
    }
    document.addEventListener('keydown', onKeyDown);

    function isCurrent(attempt) {
        return attempt && attempt.active && !state.destroyed && state.binding === attempt &&
            window.engine === attempt.engine && window.viewEnv === attempt.viewEnv;
    }
    function removeModelCallback(attempt, callbackId) {
        if (callbackId === null || callbackId === undefined) { return; }
        try {
            if (typeof attempt.viewEnv.removeDataChangedCallback === 'function') {
                attempt.viewEnv.removeDataChangedCallback(callbackId, 0);
            }
        } catch (error) { /* Ownership was invalidated before native removal. */ }
    }
    function registerModelCallback(attempt) {
        if (!isCurrent(attempt) || !state.bound || attempt.callbackRegistering || attempt.callbackId !== null) { return; }
        attempt.callbackRegistering = true;
        try {
            if (typeof attempt.viewEnv.addDataChangedCallback === 'function') {
                var callbackId = attempt.viewEnv.addDataChangedCallback('model', 0, true);
                if (callbackId !== undefined && callbackId !== null) {
                    if (isCurrent(attempt) && state.bound) { attempt.callbackId = callbackId; }
                    else { removeModelCallback(attempt, callbackId); }
                }
            }
        } catch (error) { /* The connection timer retries this optional registration. */ }
        finally { attempt.callbackRegistering = false; }
    }
    function readModel(attempt) {
        if (!isCurrent(attempt) || !state.bound) { return; }
        registerModelCallback(attempt);
        if (!isCurrent(attempt) || !state.bound) { return; }
        var model = window.model;
        if (model && model.payload !== undefined) { update(model.payload); }
    }
    function nativeDiagnostic(stage, width, height) {
        if (!state.bound || state.diagnostics[stage]) { return; }
        state.diagnostics[stage] = true;
        invoke('diagnostic', {stage:stage, width:width || 0, height:height || 0, scale:state.nativeScale});
    }
    function resizeNative() {
        if (!state.bound) { return; }
        var rect = root.getBoundingClientRect();
        var width = Math.max(1, Math.ceil(rect.width));
        var height = Math.max(1, Math.ceil(rect.height));
        if (state.nativeWidth === width && state.nativeHeight === height) { return; }
        state.nativeWidth = width;
        state.nativeHeight = height;
        /* Surface sizing is optional here: Python must still receive the dimensions
           and centre the window if a client helper is absent or throws. */
        if (window.viewEnv && typeof window.viewEnv.resizeViewPx === 'function') {
            try { window.viewEnv.resizeViewPx(width, height); } catch (error) { /* Keep the centring measurement available to Python. */ }
        }
        invoke('resize', { width: width, height: height });
        nativeDiagnostic('layout_ready', width, height);
    }
    function queueResize() {
        var viewport = state.payload && state.payload.viewport;
        /* IGuiLoader.scale is supplied by the Python adapter. Never use browser DPR. */
        var scale = viewport && viewport.scale;
        if (!hasNumber(scale) || scale <= 0) {
            scale = 1;
            if (window.viewEnv && typeof window.viewEnv.remToPx === 'function') {
                try {
                    var fallback = window.viewEnv.remToPx(1);
                    if (hasNumber(fallback) && fallback > 0) { scale = fallback; }
                } catch (error) { /* Unsupported helper must not prevent centring. */ }
            }
        }
        state.nativeScale = scale;
        document.documentElement.style.fontSize = scale + 'px';
        if (state.bound && viewport) {
            if (hasNumber(viewport.width) && viewport.width > 0) {
                var availableWidth = Math.max(1, Math.floor(viewport.width - 20));
                root.style.maxWidth = availableWidth + 'px';
                root.style.minWidth = Math.min(300, availableWidth) + 'px';
            }
            if (hasNumber(viewport.height) && viewport.height > 0) {
                root.style.maxHeight = Math.max(1, Math.floor(viewport.height - 20)) + 'px';
            }
        }
        if (typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(function () { window.requestAnimationFrame(resizeNative); });
        } else { resizeNative(); }
    }
    function onScaleUpdated() {
        if (state.destroyed) { return; }
        /* Fetch the current IGuiLoader scale before trusting the previous snapshot again. */
        invoke('viewport');
        queueResize();
    }
    function unsubscribe(attempt, listener) {
        if (!listener || !listener.active) { return; }
        listener.active = false;
        try {
            if (typeof attempt.engine.off === 'function') {
                attempt.engine.off(listener.name, listener.callback);
            }
        } catch (error) { /* Retained callbacks are inert before native removal. */ }
    }
    function subscribe(attempt, name, callback) {
        var listener = {name:name, active:true, registered:false, signalled:false};
        listener.callback = function () {
            if (!listener.active || !isCurrent(attempt)) { return; }
            // An API can deliver synchronously and then throw. Do not commit
            // readiness/binding until the registration itself has succeeded.
            if (!listener.registered) { listener.signalled = true; return; }
            callback();
        };
        attempt.listeners.push(listener);
        attempt.engine.on(name, listener.callback);
        listener.registered = true;
        return listener;
    }
    function releaseBinding(attempt) {
        if (!attempt) { return; }
        attempt.active = false;
        var callbackId = attempt.callbackId, index;
        attempt.callbackId = null;
        for (index = 0; index < attempt.listeners.length; index += 1) {
            unsubscribe(attempt, attempt.listeners[index]);
        }
        removeModelCallback(attempt, callbackId);
    }
    function cancelRetry() {
        var retry = state.retry;
        state.retry = null;
        if (!retry) { return; }
        retry.active = false;
        try { window.clearTimeout(retry.id); }
        catch (error) { /* A queued timer must still pass its ownership check. */ }
    }
    function scheduleRetry() {
        if (state.destroyed || state.retry) { return; }
        var retry = {active:true, id:null};
        state.retry = retry;
        var delay = state.retryDelay;
        state.retryDelay = Math.min(2000, delay * 2);
        try {
            retry.id = window.setTimeout(function () {
                if (!retry.active || state.retry !== retry || state.destroyed) { return; }
                retry.active = false;
                state.retry = null;
                connectNative();
            }, delay);
        } catch (error) { retry.active = false; state.retry = null; }
    }
    function failBinding(attempt) {
        if (state.binding !== attempt) { return; }
        state.binding = null;
        state.bound = false;
        releaseBinding(attempt);
        scheduleRetry();
    }
    function bindModel(attempt) {
        if (!isCurrent(attempt) || !attempt.ready || state.bound || attempt.subscribing) { return; }
        if (!attempt.domBuilt && !window.isDomBuilt) { scheduleRetry(); return; }
        attempt.subscribing = true;
        try {
            unsubscribe(attempt, attempt.dom);
            subscribe(attempt, 'viewEnv.onDataChanged', function () { readModel(attempt); });
            if (!isCurrent(attempt)) { return; }
            subscribe(attempt, 'self.onScaleUpdated', function () {
                if (state.bound) { onScaleUpdated(); }
            });
            if (!isCurrent(attempt)) { return; }
            state.bound = true;
            state.nativeSession = true;
            if (document.documentElement.className.indexOf('ss-native-document') === -1) {
                document.documentElement.className += ' ss-native-document';
            }
            if (root.className.indexOf('is-native') === -1) { root.className += ' is-native'; }
            nativeDiagnostic('dom_ready');
            readModel(attempt);
            if (!isCurrent(attempt)) { return; }
            nativeDiagnostic('model_bound');
            queueResize();
            // Once connected, a cheap check notices a replaced bridge without
            // re-reading/rendering the model or adding duplicate subscriptions.
            state.retryDelay = 2000;
            scheduleRetry();
        } catch (error) { failBinding(attempt); }
        finally { attempt.subscribing = false; }
    }
    function afterEngineReady(attempt) {
        if (!isCurrent(attempt)) { return; }
        try {
            attempt.ready = true;
            if (window.isDomBuilt) { bindModel(attempt); }
            else {
                attempt.dom = subscribe(attempt, 'self.onDomBuilt', function () {
                    attempt.domBuilt = true;
                    bindModel(attempt);
                });
                if (attempt.dom.signalled || window.isDomBuilt) {
                    attempt.domBuilt = true;
                    bindModel(attempt);
                }
            }
        } catch (error) { failBinding(attempt); }
    }
    function cleanup() {
        if (state.destroyed) { return; }
        state.destroyed = true;
        closeSelect(false);
        document.removeEventListener('mousedown',outsideSelect);
        clearAppearance();
        state.scrollSpeed = 1;
        endNativeDrag();
        root.removeEventListener('wheel', onNativeWheel, false);
        document.removeEventListener('keydown', onKeyDown);
        nodes.titlebar.removeEventListener('mousedown', beginNativeDrag);
        document.removeEventListener('mouseup', endNativeDrag);
        window.removeEventListener('blur', endNativeDrag);
        cancelRetry();
        document.removeEventListener('DOMContentLoaded', connectNative);
        window.removeEventListener('load', connectNative);
        window.removeEventListener('beforeunload', cleanup);
        var attempt = state.binding;
        state.binding = null;
        state.bound = false;
        releaseBinding(attempt);
    }
    window.GRZSessionStats = {
        update: update,
        onAction: null,
        getState: function () { return { scope:state.scope, group:state.group, xp:state.xp, nativeBound:state.bound, dragging:state.dragging }; },
        destroy: cleanup
    };
    window.addEventListener('beforeunload', cleanup);
    function connectNative(event) {
        if (state.destroyed) { return; }
        var attempt = state.binding;
        try {
            if (attempt && !isCurrent(attempt)) {
                state.binding = null;
                state.bound = false;
                releaseBinding(attempt);
                attempt = null;
            }
            if (attempt) {
                if (state.bound && !event) {
                    var previousId = attempt.callbackId;
                    registerModelCallback(attempt);
                    if (previousId === null && attempt.callbackId !== null) {
                        readModel(attempt);
                        queueResize();
                    }
                } else if (!state.bound && attempt.ready && (attempt.domBuilt || window.isDomBuilt)) { bindModel(attempt); }
                scheduleRetry();
                return;
            }
            var engine = window.engine, viewEnv = window.viewEnv;
            if (!engine || !viewEnv || typeof engine.on !== 'function') { scheduleRetry(); return; }
            var ready = engine.whenReady;
            if (!ready || typeof ready.then !== 'function') { scheduleRetry(); return; }
            attempt = {engine:engine, viewEnv:viewEnv, active:true, ready:false,
                domBuilt:false, dom:null, listeners:[], subscribing:false,
                callbackId:null, callbackRegistering:false};
            state.binding = attempt;
            state.nativeWidth = 0;
            state.nativeHeight = 0;
            // The timer also watches unresolved readiness/DOM phases. It never
            // reattaches to the same promise, and catches bridge replacement.
            scheduleRetry();
            ready.then(function () { afterEngineReady(attempt); }, function () { failBinding(attempt); });
        } catch (error) {
            if (attempt && state.binding === attempt) { failBinding(attempt); }
            else { scheduleRetry(); }
        }
    }
    document.addEventListener('DOMContentLoaded', connectNative);
    window.addEventListener('load', connectNative);
    connectNative();
}());
