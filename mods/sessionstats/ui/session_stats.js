/* GRZ Session Stats — no frameworks, no network calls, no demonstration data. */
(function () {
    'use strict';
    var root = document.getElementById('grz-session-stats');
    if (!root) { return; }

    var state = { scope: 'launch', group: 'vehicles', xp: 'base', payload: null,
        dialog: false, bound: false, nativeSession: false, binding: null, retry: null, retryDelay: 100, actionError: null,
        nativeWidth: 0, nativeHeight: 0, nativeScale: 1, diagnostics: {}, dragging: false,
        scrollSpeed: 1, appearanceNode: null, appearanceCSS: '', destroyed: false,
        orders: {}, openSelect: null, list: [], loadedCount: 40, renderedCount: 0,
        timelineSignature: null, customRangeKey: null, customDates: {}, openMaps: {}, mapContext: null,
        pendingBattle: null, battleJump: null, battleJumpTimer: null, highlightedBattle: null, navigationSequence: 0,
        targetFocusTransfer: false,
        targetTimer: null, targetSequence: 0, feed: null, renderedFeed: null,
        feedSequence: 0, feedForceStart: null, pageJump: null, filterShift: 0, orderIntent: null,
        openBattles: {}, resize: null, logicalSize: null,
        cardFlowToken: 0, cardFlowQueued: false, cardFlowAttempts: 0, cardFlowTimer: null,
        windowPrefs: null, windowSaved: null, windowPending: null, windowChanges: {},
        windowSequence: 0, windowTimer: null, windowTimerToken: 0, backgroundDrag: null,
        viewKey: null, scrollTarget: null,
        resizeSequence: 0, timePointAccount: null, timePointCount: null, timePointEdited: false,
        resizeQueued: false, resizeTimer: null, resizeLast: 0, resizeMeasureToken: 0 };
    // BEGIN GENERATED ENGLISH
    var english = {"cancel": "Cancel", "close": "Close", "close.symbol": "\u00d7", "core.account": "This save belongs to another account or region. Overwrite refused.", "core.battle": "Invalid battle record. Overwrite refused.", "core.boundaries": "Invalid session boundaries. Overwrite refused.", "core.closed": "This launch identifier is already closed. Reload data in a new process.", "core.create": "Could not create a session.", "core.current": "Invalid current period. Overwrite refused.", "core.invalid_id": "Invalid battle identifier.", "core.ledger": "Invalid ledger structure. Overwrite refused.", "core.load": "Could not safely load or initialize statistics. Data remains read-only.", "core.loading": "Loading history. New battle results are being saved.", "core.loading_timer": "History loading could not be scheduled. Restart the client; pending results remain saved.", "core.membership": "Some results have no known period: a reliable battle start time is missing.", "core.missing_id": "Missing battle identifier.", "core.more_notices": "Additional data notices are retained in local history.", "core.periods": "Saved periods are missing. Overwrite refused.", "core.reset_time": "Invalid reset time.", "core.result": "Invalid result record.", "core.time": "Invalid time.", "core.wn8": "No valid WN8 table. Other statistics remain available.", "coverage.battles": "{0} battles", "coverage.legend": "x/y: battles with this value / recorded battles.", "coverage.missing": "Incomplete statistics: results for {0} of {1} recorded battles. Percentages, averages and totals use received data.", "coverage.partial": "Incomplete data in {0} results. Missing values are marked beside each statistic.", "coverage.value": "Data available for {0} of {1} recorded battles.", "coverage.wn8.battle": "Insufficient data to calculate this battle\u2019s WN8.", "coverage.wn8.period": "Period WN8: data for {0} battles.", "error.action": "Could not complete the action. Try again.", "error.connection": "No connection to the game.", "error.snapshot": "Could not read statistics data.", "explain.costs": "Costs include settled battle expenses.", "explain.wn8": "Average battle WN8 may differ from period WN8.", "finance.battle": "Battle finances", "finance.bonds": "Bonds", "finance.costs": "Costs", "finance.credits": "Credits", "finance.currency": "Currency", "finance.gold": "Gold", "finance.income": "Income", "finance.net": "Net", "finance.period": "Battle finances", "footer.idle": "Session statistics: battles, win rate and WN8", "footer.processing": "Processing results", "footer.waiting": "Waiting for results: {0}", "format.date": "{0}.{1}.{2}, {3}:{4}", "format.date.short": "{0}.{1}, {2}:{3}", "format.decimal": ".", "format.missing": "\u2014", "format.thousands": "\u00a0", "groups.battles": "Battles", "groups.battles.aria": "Battle results", "groups.battles.count": "{0} battles", "groups.battles.total": "{0} battles", "groups.empty": "No recorded battles in this period. Results appear after a battle ends.", "groups.label": "Group results", "groups.maps": "Maps", "groups.maps.aria": "Results by map", "groups.maps.count": "{0} maps", "groups.maps.total": "{0} maps", "groups.tiers": "Tiers", "groups.tiers.aria": "Results by tier", "groups.tiers.count": "{0} tiers", "groups.tiers.total": "{0} tiers", "groups.vehicles": "Vehicles", "groups.vehicles.aria": "Results by vehicle", "groups.vehicles.count": "{0} vehicles", "groups.vehicles.total": "{0} vehicles", "health.log": "game.log (dedicated log unavailable)", "health.notice": "Session statistics: the compatibility check detected an unsupported or incomplete data format, or a result read error. Some statistics may be incomplete. Fields: {0}. Details: {1}", "health.warning": "A result format or read problem was detected during this launch. See the mod log.", "help.info": "Information", "installation.save": "Installation history could not be saved; previous data was preserved.", "installation.unavailable": "Shared installation statistics are unavailable; account statistics remain active.", "language.auto": "Automatic", "language.de": "Deutsch", "language.en": "English", "language.es": "Espa\u00f1ol", "language.fr": "Fran\u00e7ais", "language.label": "Language", "language.pl": "Polski", "language.ru": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439", "language.save_error": "Could not save the language. Your configuration was preserved.", "language.uk": "\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430", "log.close": "Could not close the mod log ({0}).", "log.prepare": "Could not prepare a log entry ({0}).", "log.start": "Could not start the mod log ({0}).", "log.write": "Could not write the mod log ({0}).", "maps.battles": "Battles on this map", "maps.empty": "No battles available", "maps.loading": "Loading battles\u2026", "maps.open_battle": "Show battle", "metric.avg": "Average", "metric.battle_wn8": "WN8", "metric.battles": "Battles", "metric.confirmed": "Results received", "metric.draws": "Draws", "metric.losses": "Losses", "metric.max": "Max", "metric.min": "Min", "metric.period_wn8": "Period WN8", "metric.win_rate": "Win rate", "metric.wins": "Wins", "metric.wn8": "WN8", "mode.random": "Random battles", "more.active": "Active in this battle", "more.bonus.additional": "Applied post-battle bonus: \u00d7{0} XP", "more.bonus.applied": "Post-battle XP bonus applied", "more.bonus.clan.credits": "Clan reserve: +{0} credits", "more.bonus.clan.crew_xp": "Clan reserve: +{0} Crew XP", "more.bonus.clan.free_xp": "Clan reserve: +{0} Free XP", "more.bonus.clan.xp": "Clan reserve: +{0} XP", "more.bonus.daily": "First victory: \u00d7{0} XP", "more.bonus.event.bonds": "Mission or event reward: +{0} bonds", "more.bonus.event.credits": "Event: +{0} credits", "more.bonus.event.free_xp": "Event: +{0} Free XP", "more.bonus.event.xp": "Event: +{0} XP", "more.bonus.platoon.xp": "Platoon: +{0} XP", "more.bonus.plus.credits": "WoT Plus: +{0} credits", "more.bonus.plus.crew_xp": "WoT Plus: +{0} Crew XP", "more.bonus.plus.free_xp": "WoT Plus: +{0} Free XP", "more.bonus.plus.xp": "WoT Plus: +{0} XP", "more.bonus.premium.credits": "Premium account: \u00d7{0} credits", "more.bonus.premium.xp": "Premium account: \u00d7{0} XP", "more.bonus.premium_vehicle.xp": "Premium vehicle: +{0} XP", "more.bonus.reserve.credits": "Personal reserve: +{0} credits", "more.bonus.reserve.crew_xp": "Personal reserve: +{0} Crew XP", "more.bonus.reserve.free_xp": "Personal reserve: +{0} Free XP", "more.bonus.reserve.xp": "Personal reserve: +{0} XP", "more.bonuses": "Bonuses", "more.button": "More", "more.column.crew_xp": "Crew XP", "more.column.free_xp": "Free XP", "more.column.xp": "XP", "more.empty": "No mission or bonus details are available for this battle.", "more.kind.battle_matters": "Battle Matters", "more.kind.crucible": "Crucible", "more.kind.daily": "Daily mission", "more.kind.daily_bonus": "Bonus daily mission", "more.kind.daily_epic": "Epic daily reward", "more.kind.other": "Mission", "more.kind.personal": "Personal mission", "more.kind.premium": "Premium mission", "more.kind.weekly": "Weekly mission", "more.less": "Less", "more.mission.completed": "Completed", "more.mission.failed": "Failed \u00b7 shield used", "more.mission.honors": "Completed with honors", "more.mission.observed": "No confirmed result", "more.mission.progress": "Progress recorded", "more.mission.reset": "Streak reset", "more.missions": "Missions", "more.pass": "Battle Pass", "more.pass.battle": "Battle result: +{0}", "more.pass.missions": "Missions: +{0}", "more.pass.total": "{0} points earned", "more.pass.vehicle": "Vehicle limit bonus: +{0}", "more.progress": "Battle counter: {0} \u2192 {1}", "more.progress.change": "{0}: {1}", "more.progress.none": "No progress recorded", "more.progress.range": "{0}: {1} \u2192 {2} ({3})", "more.progress.target": "{0}: {1}/{2}", "more.progress.unavailable": "Battle progress unavailable", "more.progress.unit.battles": "Battles", "more.progress.unit.counter": "Progress", "more.progress.unit.damage": "Damage", "more.progress.unit.kills": "Vehicles destroyed", "more.progress.unit.seconds": "Seconds", "more.progress.unit.vehicles": "Vehicles", "more.progress.unit.xp": "XP", "more.progress.vehicles": "Unique vehicles: {0} \u2192 {1}", "more.stage": "Stage {0}", "more.suicide": "The game recorded a suicide violation.", "normalize.costs": "Inconsistent consumable/directive cost breakdown.", "normalize.factor": "Incomplete credits: the deduction multiplier is missing.", "normalize.finance": "Some financial data is not yet available.", "normalize.map": "Map name is unavailable in this client version.", "normalize.platoon": "Incomplete credits: platoon deductions are missing.", "normalize.reserve": "Deferred credits do not increase this balance.", "normalize.vehicle": "Vehicle name is unavailable in this client version.", "outcome.draw": "Draw", "outcome.loss": "Defeat", "outcome.unknown": "Unknown result", "outcome.win": "Victory", "page.error": "Could not load this page.", "page.loading": "Loading page\u2026", "page.next": "Next", "page.previous": "Previous", "page.retry": "Retry", "page.status": "Page {0} of {1}", "page.top": "Back to top", "performance.battle": "Battle performance", "performance.period": "Battle performance", "period.installation": "All accounts \u00b7 Since {0}", "period.since": "Since {0}", "preview.label": "Preview \u00b7 synthetic data", "preview.open": "Open panel", "preview.restore": "Restore example", "refresh": "Refresh", "reset": "Reset period", "reset.instance.body": "A new shared period starts for this installation and persists across game restarts. Account histories and their manual resets remain unchanged.", "reset.instance.title": "Reset \u201cInstallation\u201d?", "reset.manual.body": "A new period starts now for the current account. Other accounts keep their history.", "reset.manual.title": "Reset \u201cSince reset\u201d?", "runtime.account_wait": "Waiting for account data.", "runtime.backlog": "Incomplete earlier battle results: {0}. History is preserved; recovery continues in the background. You can also select Refresh.", "runtime.begin": "Could not read a battle beginning; some results may remain pending.", "runtime.bonus": "Post-battle bonus XP cannot be read; received XP may be incomplete.", "runtime.bonus_refresh": "Automatic bonus XP refresh is unavailable; select Refresh after using a bonus.", "runtime.bonus_timer": "Bonus XP refresh is unavailable; select Refresh after using a bonus.", "runtime.cache": "Pending results cannot be read; missing battles remain pending.", "runtime.data_dir": "Local user data directory was not found.", "runtime.diagnostics": "Some mod diagnostics are unavailable; check game.log.", "runtime.direct": "Direct result events are unavailable; some results may be delayed.", "runtime.events": "Some client events could not be handled; statistics may be incomplete.", "runtime.garage": "Session statistics will be available after the account loads in the garage.", "runtime.hotkey": "Keyboard shortcut is unavailable; use the garage statistics button.", "runtime.late": "Could not complete a late result; the battle remains pending.", "runtime.log_failed": "Cannot write the dedicated mod log. Diagnostics remain in game.log.", "runtime.log_notice": "Session statistics: cannot write the dedicated mod log. Check access to the data directory; details remain in game.log.", "runtime.log_unavailable": "Dedicated mod log is unavailable.", "runtime.observer": "Additional client result reads are unavailable; events and recovery queue remain active.", "runtime.open_files": "Could not open session statistics. Check mod files and game.log.", "runtime.open_log": "Could not open session statistics. Details were recorded in game.log.", "runtime.panel": "Statistics panel is unavailable; result collection remains active.", "runtime.panel_update": "Could not update the panel; saved results remain available.", "runtime.pending": "Could not read a pending result; the battle remains pending.", "runtime.polling": "Periodic backlog reads are unavailable; client result events remain active.", "runtime.posted": "Processed result notifications are unavailable; bonus XP may require Refresh.", "runtime.processed": "Could not read a processed result; the raw result remains available.", "runtime.results": "Could not read some battle results; statistics may be incomplete.", "runtime.saved": "Could not open saved statistics.", "runtime.thumbnails": "Thumbnails are unavailable in this client version; results remain available.", "runtime.tick": "Periodic result reading failed; statistics may be incomplete.", "runtime.wn8_invalid": "Bundled WN8 table is invalid.", "runtime.wn8_load": "Could not load the WN8 table; other statistics remain available.", "runtime.wn8_missing": "Bundled WN8 expected values table is missing.", "scope.group": "Session period", "scope.instance": "Installation", "scope.instance.title": "All accounts in this installation; saved until manual reset", "scope.launch": "Since launch", "scope.launch.short": "Since launch", "scope.launch.title": "Since game launch \u2014 current account", "scope.manual": "Since reset", "scope.manual.title": "Since manual reset \u2014 current account", "scope.timeline": "Timeline", "scope.timeline.title": "Filter this account\u2019s battle history between saved time points", "sort.asc": "Ascending", "sort.avg": "Avg", "sort.chronology": "Battle date", "sort.credits": "Credits (net)", "sort.desc": "Descending", "sort.direction": "Order", "sort.label": "Sort results", "sort.metric": "Sort by", "sort.newest": "Newest first", "sort.off": "Off", "sort.oldest": "Oldest first", "sort.statistic": "Statistic", "sort.value_per_battle": "{0} {1} / battle: {2}", "sort.xp_base": "Base XP", "sort.xp_received": "Received XP", "stats.period": "Whole period", "stats.region": "Statistics and results", "status.incomplete": "Incomplete data: results {0} / {1}", "status.notes": "Data notices: {0}", "status.pending": "Pending: {0}", "status.settled": "{0} completed battles", "storage.busy": "Data is in use by another process or the file lock is unavailable.", "storage.changed": "Another process changed the data. Reload it before saving.", "storage.collision": "Save generation conflict; previous data is preserved.", "storage.corrupt": "No valid save was found. Corrupted files were not overwritten.", "storage.failed": "Could not save statistics durably. The previous valid save is preserved.", "storage.format": "Unsupported storage format. Data remains read-only.", "storage.no_lock": "System file locking is unavailable; process protection and generation conflict detection remain active. Use one client to write this data.", "storage.readonly": "Saving is blocked: data is read-only.", "storage.recovered": "Recovered the previous valid save; the latest save was corrupted. Some recent results may need to be retrieved again.", "storage.schema": "Unsupported storage schema. Data remains read-only.", "storage.unsupported_write": "Cannot write an unsupported schema.", "timeline.beginning": "Beginning of history", "timeline.create": "Create time point", "timeline.create_error": "Could not save a time point.", "timeline.custom": "Custom date", "timeline.custom_apply": "Apply", "timeline.custom_invalid": "Enter a valid date: YYYY-MM-DD HH:mm.", "timeline.custom_order": "From must be earlier than To.", "timeline.custom_placeholder": "YYYY-MM-DD HH:mm", "timeline.from": "From", "timeline.name": "Time point name", "timeline.now": "Now", "timeline.to": "To", "title": "Session statistics", "unknown": "Unknown", "unknown.map": "Unknown map", "unknown.map_id": "Map {0}", "unknown.tier": "Unknown tier", "unknown.vehicle": "Unknown vehicle", "unknown.vehicle_id": "Vehicle {0}", "vehicle.AT_SPG": "Tank destroyer", "vehicle.SPG": "SPG", "vehicle.heavyTank": "Heavy tank", "vehicle.lightTank": "Light tank", "vehicle.mediumTank": "Medium tank", "vehicles.battles": "Battles in this vehicle", "visual.map": "Map", "visual.vehicle": "Vehicle", "waiting.data": "Waiting for data", "waiting.game": "Waiting for game data.", "waiting.results": "Waiting for battle results\u2026", "window.background": "Transparency", "window.background_transparency": "Background transparency", "window.maximize": "Maximize window", "window.resize": "Resize window (drag or use arrow keys)", "window.restore": "Restore window", "window.save_error": "Could not save window settings. Your configuration was preserved.", "xp.base": "Base XP", "xp.free": "Free XP:", "xp.group": "Experience type", "xp.received": "Received XP"};
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
        if (state.language !== language) { state.timelineSignature = null; state.language = language; }
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
        'group-tabs', 'list-meta', 'titlebar', 'title-actions', 'timeline', 'time-point',
        'time-point-controls', 'time-point-name', 'resize-grip', 'maximize', 'window-background',
        'background-transparency', 'background-transparency-track', 'background-transparency-thumb',
        'background-transparency-value', 'filter-panel', 'scroll-top'];
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
    var helpTarget = null, helpPending = null, helpTimer = null, helpPointer = null;
    var helpTooltip = append(root, element('div', 'ss-help-tooltip'));
    helpTooltip.id = 'ss-help-tooltip';
    helpTooltip.setAttribute('role', 'tooltip');
    helpTooltip.style.display = 'none';
    function hideHelp() {
        if (helpTimer !== null) { window.clearTimeout(helpTimer); helpTimer = null; }
        helpPending = null;
        helpPointer = null;
        if (helpTarget) {
            helpTarget.removeAttribute('aria-describedby');
            helpTarget.setAttribute('aria-expanded', 'false');
        }
        helpTarget = null;
        helpTooltip.style.display = 'none';
    }
    function clearHelp(node) {
        var button = node._ssHelpButton;
        if (button) {
            if (helpTarget === button || helpPending === button) { hideHelp(); }
            if (button.parentNode) { button.parentNode.removeChild(button); }
            node._ssHelpButton = null;
        }
    }
    function helpLocation(node) {
        var current = node, section = null, inSummary = false;
        while (current && current !== root) {
            if (/(^|\s)ss-group(\s|$)/.test(current.className)) {
                return {owner:current, anchor:current.querySelector('.ss-group-heading') || current};
            }
            if (!section && /(^|\s)ss-(performance|economy)(\s|$)/.test(current.className)) { section = current; }
            if (current === nodes.summary) { inSummary = true; }
            current = current.parentNode;
        }
        if (section) { return {owner:section, anchor:section.querySelector('.ss-detail-title') || section}; }
        if (inSummary || node === nodes.status) {
            return {owner:nodes.summary, anchor:nodes.summary.querySelector('.ss-summary-main .ss-kpi-label, .ss-data-notice') || nodes.summary};
        }
        return {owner:node, anchor:node};
    }
    function help(node, text) {
        if (!text) { return; }
        var location = helpLocation(node), owner = location.owner, button = owner._ssHelpButton;
        if (!button || !owner.contains(button)) {
            var title = location.anchor.querySelector('.ss-group-title');
            var label = owner === nodes.summary ? t('stats.period') : (title || location.anchor).textContent;
            button = append(location.anchor, element('button', 'ss-info-button'));
            append(button, element('span', 'ss-info-symbol', 'i')).setAttribute('aria-hidden', 'true');
            button.type = 'button';
            button.setAttribute('aria-label', t('help.info') + (label ? ': ' + label : ''));
            button.setAttribute('aria-controls', helpTooltip.id);
            button.setAttribute('aria-expanded', 'false');
            owner._ssHelpButton = button;
        }
        var previous = button.getAttribute('data-ss-help') || '';
        if (previous.split('\n').indexOf(text) < 0) {
            button.setAttribute('data-ss-help', previous ? previous + '\n' + text : text);
        }
    }
    function helpAncestor(target) {
        while (target && target !== root) {
            if (target.nodeType === 1 && /(^|\s)ss-info-button(\s|$)/.test(target.className)) { return target; }
            target = target.parentNode;
        }
        return null;
    }
    function showHelp(target) {
        if (!target || !root.contains(target) || state.destroyed || state.dragging || state.resize || state.dialog) { hideHelp(); return; }
        if (target === helpTarget) { return; }
        hideHelp();
        helpTarget = target;
        target.setAttribute('aria-describedby', helpTooltip.id);
        target.setAttribute('aria-expanded', 'true');
        helpTooltip.textContent = target.getAttribute('data-ss-help');
        helpTooltip.style.display = 'block';
        var bounds = root.getBoundingClientRect(), anchor = target.getBoundingClientRect();
        var scale = state.nativeScale, inset = 10 * scale, gap = 12 * scale;
        var width = Math.max(1, Math.min(320 * scale, bounds.width - inset * 2));
        // Gameface can defer a newly shown element's measurements. Constrain
        // this box using known panel bounds without measuring the tooltip.
        var anchorTop = Math.max(inset, Math.min(anchor.top - bounds.top, bounds.height - inset));
        var anchorBottom = Math.max(inset, Math.min(anchor.bottom - bounds.top, bounds.height - inset));
        var below = bounds.height - anchorBottom - gap - inset, above = anchorTop - gap - inset;
        var left = Math.max(inset, Math.min(anchor.left - bounds.left, bounds.width - width - inset));
        helpTooltip.style.width = width + 'px';
        helpTooltip.style.maxHeight = Math.max(1, Math.max(above, below)) + 'px';
        helpTooltip.style.left = left + 'px';
        helpTooltip.style.top = below >= above ? anchorBottom + gap + 'px' : 'auto';
        helpTooltip.style.bottom = below >= above ? 'auto' : bounds.height - anchorTop + gap + 'px';
    }
    function waitForHelp(event) {
        var target = helpAncestor(event.target);
        if (!target || state.dragging || state.resize || state.dialog) { hideHelp(); return; }
        if (target === helpTarget) { return; }
        if (target === helpPending && helpPointer && event.clientX === helpPointer.x && event.clientY === helpPointer.y) { return; }
        hideHelp();
        helpPending = target;
        helpPointer = {x:event.clientX, y:event.clientY};
        helpTimer = window.setTimeout(function () {
            helpTimer = null;
            if (helpPending === target) { showHelp(target); }
        }, 1000);
    }
    function focusHelp(event) { showHelp(helpAncestor(event.target)); }
    function pressHelp(event) {
        // A pointer click must not leave the icon keyboard-focused after the
        // tooltip closes. Keyboard focus retains its normal accessible help.
        if (helpAncestor(event.target) && (event.button === undefined || event.button === 0)) { event.preventDefault(); }
    }
    function clickHelp(event) {
        var target = helpAncestor(event.target);
        if (target) {
            event.preventDefault();
            var wasOpen = target === helpTarget;
            if (event.detail > 0 && document.activeElement === target && typeof target.blur === 'function') { target.blur(); }
            if (wasOpen) { hideHelp(); } else { showHelp(target); }
        }
        else { hideHelp(); }
    }
    function leaveHelp(event) {
        var target = helpAncestor(event.relatedTarget);
        if (!target || (target !== helpTarget && target !== helpPending)) { hideHelp(); }
    }
    root.addEventListener('mouseover', waitForHelp);
    root.addEventListener('mousemove', waitForHelp);
    root.addEventListener('mouseout', leaveHelp);
    root.addEventListener('focusin', focusHelp);
    root.addEventListener('focusout', leaveHelp);
    root.addEventListener('mousedown', pressHelp);
    root.addEventListener('click', clickHelp);
    nodes.scroll.addEventListener('scroll', hideHelp);
    window.addEventListener('blur', hideHelp);
    window.addEventListener('resize', hideHelp);
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
    function windowDefaults() {
        return {background_transparency:0, maximized:false, restored_width:700, restored_height:620};
    }
    function copyWindowSettings(value) {
        var result = windowDefaults();
        if (!value || typeof value !== 'object' || Array.isArray(value)) { return result; }
        Object.keys(result).forEach(function (key) {
            var item = unwrap(value[key]);
            if (key === 'maximized') { if (typeof item === 'boolean') { result[key] = item; } }
            else if (hasNumber(item) && Math.floor(item) === item &&
                    (key === 'background_transparency' ? item >= 0 && item <= 100 : item >= 1 && item <= 32768)) {
                result[key] = item;
            }
        });
        return result;
    }
    function mergeWindowSettings(base, changes) {
        var result = copyWindowSettings(base);
        Object.keys(changes).forEach(function (key) { result[key] = changes[key]; });
        return result;
    }
    function showWindowSettings(previous) {
        var prefs = state.windowPrefs || windowDefaults(), percent = prefs.background_transparency;
        if (nodes['window-background']) { nodes['window-background'].style.opacity = String(1 - percent / 100); }
        if (nodes['background-transparency']) {
            nodes['background-transparency'].setAttribute('aria-valuenow', String(percent));
            nodes['background-transparency'].setAttribute('aria-valuetext', String(percent) + '%');
        }
        if (nodes['background-transparency-thumb']) { nodes['background-transparency-thumb'].style.left = percent + '%'; }
        if (nodes['background-transparency-value']) { nodes['background-transparency-value'].textContent = percent + '%'; }
        if (nodes.maximize) {
            var key = prefs.maximized ? 'window.restore' : 'window.maximize';
            nodes.maximize.setAttribute('aria-pressed', String(prefs.maximized));
            nodes.maximize.setAttribute('aria-label', t(key));
            nodes.maximize.setAttribute('title', t(key));
            nodes.maximize.setAttribute('data-i18n-aria', key);
            nodes.maximize.setAttribute('data-i18n-title', key);
        }
        if (prefs.maximized) { root.classList.add('ss-window-maximized'); }
        else { root.classList.remove('ss-window-maximized'); }
        if (previous && !prefs.maximized && (previous.maximized ||
                previous.restored_width !== prefs.restored_width || previous.restored_height !== prefs.restored_height)) {
            if (!state.resize) {
                // Keep the requested size when a smaller viewport temporarily
                // clamps the surface. A later viewport expansion can restore it.
                state.logicalSize = {width:prefs.restored_width, height:prefs.restored_height};
                queueResize();
            }
        }
    }
    function cancelWindowCommit() {
        state.windowTimerToken += 1;
        var timer = state.windowTimer;
        state.windowTimer = null;
        if (timer !== null) {
            try { window.clearTimeout(timer); } catch (error) { /* The generation guard retires stale callbacks. */ }
        }
    }
    function resetWindowSettings() {
        cancelWindowCommit();
        finishBackgroundDrag(null, false);
        state.windowPending = null;
        state.windowChanges = {};
        state.windowSaved = null;
        state.windowPrefs = null;
    }
    function windowSaveFailed() {
        var previous = state.windowPrefs;
        state.windowPending = null;
        state.windowChanges = {};
        state.windowPrefs = copyWindowSettings(state.windowSaved);
        showWindowSettings(previous);
        state.actionError = t('window.save_error');
        setStatus(state.actionError);
        queueResize();
    }
    function commitWindowSettings() {
        cancelWindowCommit();
        if (state.destroyed || state.windowPending || !Object.keys(state.windowChanges).length) { return; }
        if (!state.bound) {
            state.windowSaved = copyWindowSettings(state.windowPrefs);
            state.windowChanges = {};
            return;
        }
        var account = state.payload && state.payload.account_key;
        if (!account) { windowSaveFailed(); return; }
        var changes = state.windowChanges;
        state.windowChanges = {};
        var request = 'window-' + Date.now().toString(36) + '-' + (++state.windowSequence);
        state.windowPending = {id:request, changes:changes};
        var args = {account_key:account, request_id:request};
        Object.keys(changes).forEach(function (key) { args[key] = changes[key]; });
        if (!invoke('window_settings', args)) { windowSaveFailed(); }
    }
    function previewWindowSettings(changes, commit) {
        var previous = state.windowPrefs || windowDefaults();
        state.windowPrefs = mergeWindowSettings(previous, changes);
        Object.keys(changes).forEach(function (key) { state.windowChanges[key] = changes[key]; });
        showWindowSettings(previous);
        queueResize();
        if (commit) { commitWindowSettings(); }
    }
    function applyWindowSettings(raw, acknowledgement) {
        var value = unwrap(raw), ack = unwrap(acknowledgement), previous = state.windowPrefs;
        if (!value || typeof value !== 'object' || Array.isArray(value)) {
            if (!state.windowPrefs) { state.windowSaved = windowDefaults(); state.windowPrefs = windowDefaults(); }
            showWindowSettings();
            return;
        }
        state.windowSaved = copyWindowSettings(value);
        var pending = state.windowPending;
        if (pending && ack && unwrap(ack.request_id) === pending.id) {
            if (unwrap(ack.saved) !== true) { windowSaveFailed(); return; }
            state.windowPending = null;
        }
        var changes = state.windowChanges;
        if (state.windowPending) {
            changes = {};
            Object.keys(state.windowPending.changes).forEach(function (key) { changes[key] = state.windowPending.changes[key]; });
            Object.keys(state.windowChanges).forEach(function (key) { changes[key] = state.windowChanges[key]; });
        }
        state.windowPrefs = Object.keys(changes).length ? mergeWindowSettings(state.windowSaved, changes) : copyWindowSettings(state.windowSaved);
        showWindowSettings(previous);
        if (pending && !state.windowPending && Object.keys(state.windowChanges).length && !state.backgroundDrag && state.windowTimer === null) {
            commitWindowSettings();
        }
    }
    function toggleMaximize() {
        if (state.destroyed || state.resize || state.dragging || state.dialog) { return; }
        var prefs = state.windowPrefs || windowDefaults(), changes = {maximized:!prefs.maximized};
        if (!prefs.maximized) {
            // The surface may be temporarily clamped by the viewport. Keep
            // its requested regular size so maximize cannot replace that preference.
            var size = state.logicalSize || resizePanelDimensions(root.getBoundingClientRect());
            changes.restored_width = Math.round(size.width);
            changes.restored_height = Math.round(size.height);
        }
        previewWindowSettings(changes, true);
    }
    function backgroundPosition(event) {
        var track = nodes['background-transparency-track'];
        if (!track || !hasNumber(event.clientX)) { return; }
        var box = track.getBoundingClientRect();
        if (!(box.width > 1)) { return; }
        var value = Math.max(0, Math.min(100, Math.round((event.clientX - box.left) * 100 / box.width)));
        previewWindowSettings({background_transparency:value}, false);
    }
    function beginBackgroundDrag(event) {
        if (event.button !== 0 || state.destroyed || state.resize || state.dragging || state.dialog || state.backgroundDrag) { return; }
        consumeResizeInput(event);
        cancelWindowCommit();
        var slider = nodes['background-transparency'];
        state.backgroundDrag = {pointer:event.pointerId};
        focusControl(slider);
        if (event.pointerId !== undefined && slider && typeof slider.setPointerCapture === 'function') {
            try { slider.setPointerCapture(event.pointerId); } catch (error) { /* Document listeners retain the gesture. */ }
        }
        backgroundPosition(event);
    }
    function moveBackgroundDrag(event) {
        var drag = state.backgroundDrag;
        if (!drag || (event.pointerId !== undefined && drag.pointer !== event.pointerId)) { return; }
        consumeResizeInput(event);
        backgroundPosition(event);
    }
    function finishBackgroundDrag(event, commit) {
        var drag = state.backgroundDrag;
        if (!drag || (event && event.pointerId !== undefined && drag.pointer !== event.pointerId)) { return; }
        if (event && (event.type === 'mouseup' || event.type === 'pointerup')) { moveBackgroundDrag(event); }
        state.backgroundDrag = null;
        var slider = nodes['background-transparency'];
        if (drag.pointer !== undefined && slider && typeof slider.releasePointerCapture === 'function') {
            try { slider.releasePointerCapture(drag.pointer); } catch (error) { /* A release may already have retired capture. */ }
        }
        if (commit !== false && !state.destroyed) { commitWindowSettings(); }
    }
    function backgroundKey(event) {
        var key = event.key || ({37:'ArrowLeft',38:'ArrowUp',39:'ArrowRight',40:'ArrowDown',33:'PageUp',34:'PageDown',36:'Home',35:'End'})[event.keyCode];
        var value = (state.windowPrefs || windowDefaults()).background_transparency, step = event.shiftKey ? 10 : 1;
        if (key === 'Home') { value = 0; }
        else if (key === 'End') { value = 100; }
        else if (key === 'ArrowLeft' || key === 'ArrowDown') { value -= step; }
        else if (key === 'ArrowRight' || key === 'ArrowUp') { value += step; }
        else if (key === 'PageDown') { value -= 10; }
        else if (key === 'PageUp') { value += 10; }
        else { return; }
        consumeResizeInput(event);
        previewWindowSettings({background_transparency:Math.max(0, Math.min(100, value))}, false);
        cancelWindowCommit();
        var token = state.windowTimerToken;
        state.windowTimer = window.setTimeout(function () {
            if (state.destroyed || token !== state.windowTimerToken) { return; }
            state.windowTimer = null;
            commitWindowSettings();
        }, 200);
    }
    if (nodes.maximize) { nodes.maximize.onclick = toggleMaximize; }
    if (nodes['background-transparency']) {
        var sliderEvents = typeof window.PointerEvent === 'function';
        nodes['background-transparency'].addEventListener(sliderEvents ? 'pointerdown' : 'mousedown', beginBackgroundDrag);
        document.addEventListener(sliderEvents ? 'pointermove' : 'mousemove', moveBackgroundDrag);
        document.addEventListener(sliderEvents ? 'pointerup' : 'mouseup', finishBackgroundDrag);
        document.addEventListener('pointercancel', finishBackgroundDrag);
        nodes['background-transparency'].addEventListener('keydown', backgroundKey);
        window.addEventListener('blur', finishBackgroundDrag);
    }
    function applyAppearance(raw) {
        state.scrollSpeed = 1;
        state.cardWidths = {battles:500, vehicles:560, maps:560, tiers:520};
        state.wideCardWidths = {battles:720, vehicles:720, maps:720, tiers:720};
        try {
            var value = unwrap(raw);
            applyWindowSettings(value && value.window_settings, value && value.window_settings_result);
            if (value === undefined || value === null) { clearAppearance(); return; }
            if (typeof value !== 'object' || Array.isArray(value)) { throw new Error('appearance shape'); }
            var widths = unwrap(value.card_widths);
            if (widths && typeof widths === 'object' && !Array.isArray(widths)) {
                Object.keys(state.cardWidths).forEach(function (key) {
                    var width = unwrap(widths[key]);
                    if (hasNumber(width) && width >= 480 && width <= 900) { state.cardWidths[key] = width; }
                });
            }
            var wideWidths = unwrap(value.wide_card_widths);
            if (wideWidths && typeof wideWidths === 'object' && !Array.isArray(wideWidths)) {
                Object.keys(state.wideCardWidths).forEach(function (key) {
                    var width = unwrap(wideWidths[key]);
                    if (hasNumber(width) && width >= 480 && width <= 1200) { state.wideCardWidths[key] = width; }
                });
            }
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
        node.setAttribute('aria-label', text);
        var section = node.parentNode;
        while (section && section !== root && !/(^|\s)ss-(performance|economy|free-xp)(\s|$)/.test(section.className)) {
            section = section.parentNode;
        }
        if (section && section !== root) {
            help(section, text);
            help(section, t('coverage.legend'));
        }
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
    function informationalNotice(value) {
        return ['normalize.reserve', 'runtime.backlog', 'coverage.missing', 'coverage.partial',
            'coverage.legend', 'explain.wn8', 'explain.costs'].some(function (key) {
            return [t(key), english[key]].some(function (pattern) {
                var parts = pattern.split(/\{[0-9]\}/), position = 0, index;
                if (value.indexOf(parts[0]) !== 0) { return false; }
                position = parts[0].length;
                for (index = 1; index < parts.length; index += 1) {
                    position = value.indexOf(parts[index], position);
                    if (position < 0) { return false; }
                    position += parts[index].length;
                }
                return position === value.length;
            });
        });
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
        return holder;
    }
    function measureRow(parent, label, data, wn8, total, sharedCoverage) {
        var row = append(parent, element('div', 'ss-metric-row'));
        var name = append(row, element('div', 'ss-metric-name'));
        append(name, element('span', 'ss-cell-value', label));
        var partial = coverage(data.count, total);
        if (partial && !sharedCoverage) { explainCoverage(append(name, element('span', 'ss-cell-coverage',
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
    function moneyRow(parent, name, data, total, sharedCoverage) {
        data = data || {};
        var row = append(parent, element('div', 'ss-money-row'));
        var label = append(row, element('div', 'ss-money-label', name));
        var shared = data.income_count === data.costs_count && data.costs_count === data.net_count;
        var partial = coverage(data.income_count, total);
        if (shared && partial && !sharedCoverage) { explainCoverage(append(label, element('span', 'ss-cell-coverage', partial)), data.income_count, total); }
        moneyCell(row, data, 'income', total, shared || sharedCoverage);
        moneyCell(row, data, 'costs', total, shared || sharedCoverage);
        moneyCell(row, data, 'net', total, shared || sharedCoverage);
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
        if (!partial) { return; }
        var section = parent;
        while (section.parentNode && section !== nodes.summary &&
                !/(^|\s)ss-group(\s|$)/.test(section.className)) { section = section.parentNode; }
        help(section, battle ? t('coverage.wn8.battle') : t('coverage.wn8.period', [partial]));
        if (!battle) { append(parent, element('span', 'ss-count-coverage ss-wn8-coverage', 'WN8 ' + partial)); }
    }
    function details(parent, stats, global, battle) {
        stats = stats || {};
        var total = observedTotal(stats);
        var holder = append(parent, element('div', global ? 'ss-summary-details' :
            'ss-details' + (battle ? ' ss-battle-details' : '')));
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
            var battleWN8 = series(stats.battle_wn8);
            if (!global && [xp.min, xp.avg, xp.max, battleWN8.min, battleWN8.avg, battleWN8.max].some(function (value) {
                return hasNumber(value) && Math.abs(value) >= 100000;
            })) { performance.className += ' ss-long-metrics'; }
            var shared = xp.count === battleWN8.count && !!coverage(xp.count, total);
            var header = append(performance, element('div', 'ss-metric-head'));
            var countHeader = append(header, element('div', 'ss-metric-name' + (shared ? ' ss-metric-count' : ''), ''));
            if (shared) { explainCoverage(append(countHeader, element('span', 'ss-cell-coverage',
                coverage(xp.count, total))), xp.count, total); }
            append(header, element('div', 'ss-metric-number', t('metric.min')));
            append(header, element('div', 'ss-metric-number', t('metric.avg')));
            append(header, element('div', 'ss-metric-number', t('metric.max')));
            measureRow(performance, xpLabel, xp, false, total, shared);
            measureRow(performance, t('metric.battle_wn8'), battleWN8, true, total, shared);
        }
        if (!battle) { help(performance, t('explain.wn8')); }
        var economy = append(holder, element('div', 'ss-economy'));
        append(economy, element('h3', 'ss-detail-title', battle ? t('finance.battle') : t('finance.period')));
        var currencies = stats.currencies || {};
        var currencyRows = [{name:t('finance.credits'), data:currencies.credits || {}},
            {name:t('finance.bonds'), data:currencies.bonds || {}}];
        var gold = currencies.gold || {};
        if ((hasNumber(gold.income) && gold.income !== 0) ||
                (hasNumber(gold.costs) && gold.costs !== 0) ||
                (hasNumber(gold.net) && gold.net !== 0)) {
            currencyRows.push({name:t('finance.gold'), data:gold});
        }
        if (!global && currencyRows.some(function (currency) {
            return ['income', 'costs', 'net'].some(function (field) {
                return hasNumber(currency.data[field]) && Math.abs(currency.data[field]) >= 10000000;
            });
        })) { economy.className += ' ss-long-finance'; }
        var moneyCount = currencyRows[0].data.income_count;
        var sharedMoneyCoverage = !!coverage(moneyCount, total) && currencyRows.every(function (currency) {
            return currency.data.income_count === moneyCount && currency.data.costs_count === moneyCount &&
                currency.data.net_count === moneyCount;
        });
        var moneyHeader = append(economy, element('div', 'ss-money-head'));
        var currencyHeader = append(moneyHeader, element('div', 'ss-money-label' +
            (sharedMoneyCoverage ? ' ss-money-count' : ''), sharedMoneyCoverage ? '' : t('finance.currency')));
        if (sharedMoneyCoverage) { explainCoverage(append(currencyHeader, element('span', 'ss-cell-coverage',
            coverage(moneyCount, total))), moneyCount, total); }
        append(moneyHeader, element('div', 'ss-money-value', t('finance.income')));
        append(moneyHeader, element('div', 'ss-money-value', t('finance.costs')));
        append(moneyHeader, element('div', 'ss-money-value', t('finance.net')));
        currencyRows.forEach(function (currency) {
            moneyRow(economy, currency.name, currency.data, total, sharedMoneyCoverage);
        });
        help(economy, t('explain.costs'));
        uniqueNotices((state.payload || {}).warnings).forEach(function (warning) {
            if (warning === t('normalize.reserve') || warning === english['normalize.reserve']) { help(economy, warning); }
        });
    }
    function layoutSummary() {
        var scale = state.nativeScale || 1, payload = state.payload || {}, viewport = payload.viewport || {};
        var preferred = state.logicalSize && state.logicalSize.width;
        if (!hasNumber(preferred) && payload.window_size) { preferred = payload.window_size[0]; }
        if (!hasNumber(preferred)) { preferred = 700; }
        var available = hasNumber(viewport.width) ? viewport.width : window.innerWidth;
        var width = Math.max(0, Math.min(preferred, (available - (state.bound ? 20 : 0)) / scale) - 34);
        nodes.summary.className = 'ss-summary' + (width < 1110 ? ' ss-summary-wrap' : '') +
            (width < 650 ? ' ss-summary-stacked' : '') + (width < 350 ? ' ss-narrow-summary' : '');
    }
    function renderSummary(stats, scope) {
        clear(nodes.summary);
        clearHelp(nodes.summary);
        var layout = append(nodes.summary, element('div', 'ss-summary-layout ss-details'));
        var main = append(layout, element('div', 'ss-summary-main'));
        var headline = append(main, element('div', 'ss-headline'));
        var missing = observedTotal(stats) > (stats.battles || 0);
        headlineStat(headline, missing ? t('metric.confirmed') : t('metric.battles'), battleCount(stats), false, false);
        headlineStat(headline, missing ? t('metric.win_rate') + '*' : t('metric.win_rate'), rate(stats.win_rate), false, false);
        headlineStat(headline, t('metric.period_wn8'), integer(stats.wn8), true, false);
        var outcomes = append(main, element('p', 'ss-outcomes'));
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
            help(nodes.summary, t('coverage.missing', [number(stats.battles), number(observedTotal(stats))]));
        } else if (stats.partial_results > 0) {
            help(nodes.summary, t('coverage.partial', [number(stats.partial_results)]));
        }
        var summaryMeta = append(main, element('div', 'ss-summary-meta'));
        freeXP(summaryMeta, stats);
        wn8Coverage(summaryMeta, stats, false);
        details(layout, stats, true);
        layoutSummary();
        if (nodes.summary.querySelector('.ss-cell-coverage, .ss-count-coverage')) { help(nodes.summary, t('coverage.legend')); }
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
        if (state.orderIntent && state.orderIntent.group === state.group && sameContext(state.orderIntent.context)) { return state.orderIntent.options; }
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
        cancelBattleNavigation();
        var scope = currentScope();
        if (!scope) { return; }
        var current = getOrder(scope), options = {}, key;
        for (key in defaultOrder) { options[key] = current[key]; }
        options[field] = value;
        state.loadedCount = 40;
        if (state.nativeSession && scope.pagination) {
            retireFeed(); state.feedForceStart = 0;
            state.orderIntent = {context:viewContext(), group:state.group, options:options};
            renderSelects(scope);
            options.scope = scopeName(); options.group = state.group;
            options.period_id = scope.period_id; options.account_key = state.payload.account_key;
            if (!invoke('sort',options)) { state.orderIntent = null; renderSelects(scope); }
        } else {
            state.orders[orderKey(scope)] = options;
            render();
        }
    }
    var selects = {};
    function makeSelect(field, holder, choices, chooseValue) {
        holder = holder || document.getElementById(field === 'language' ? 'ss-language' : 'ss-sort-' + field);
        choices = choices || selectOptions[field];
        chooseValue = chooseValue || (field === 'language' ? changeLanguage : function (value) { changeOrder(field, value); });
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
            if (state.destroyed || trigger.disabled || trigger.getAttribute('aria-disabled') === 'true') { return; }
            closeSelect(false); menu.style.display = 'block'; trigger.setAttribute('aria-expanded','true');
            state.openSelect = control;
            var selectedIndex = 0, index;
            for (index = 0; index < control.options.length; index += 1) {
                if (control.options[index].getAttribute('aria-selected') === 'true') { selectedIndex = index; }
            }
            focusControl(control.options[position === undefined ? selectedIndex : position]);
        }
        function choose(value) { closeSelect(true); chooseValue(value); }
        choices.forEach(function (option, index) {
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
        return control;
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
            control.trigger.setAttribute('aria-disabled', String(disabled));
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
    ['chronology','statistic','metric','direction','language'].forEach(function (field) { selects[field] = makeSelect(field); });

    function scopeName() {
        return state.scope === 'manual' && state.payload.scopes.timeline ? 'timeline' : state.scope;
    }
    function currentScope() { return state.payload.scopes[scopeName()]; }

    function customDateValue(value) {
        var parts = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?$/.exec(String(value).trim());
        if (!parts) { return null; }
        var year = +parts[1], month = +parts[2], day = +parts[3], hour = +(parts[4] || 0), minute = +(parts[5] || 0);
        if (year < 1970 || month < 1 || month > 12 || day < 1 || day > 31 || hour > 23 || minute > 59) { return null; }
        var parsed = new Date(year, month - 1, day, hour, minute, 0, 0);
        if (parsed.getFullYear() !== year || parsed.getMonth() !== month - 1 || parsed.getDate() !== day ||
                parsed.getHours() !== hour || parsed.getMinutes() !== minute || !hasNumber(parsed.getTime()) || parsed.getTime() < 0) { return null; }
        return parsed.getTime() / 1000;
    }
    function customDateText(timestamp) {
        var value = new Date((hasNumber(timestamp) ? timestamp : Date.now() / 1000) * 1000);
        function pad(number) { return number < 10 ? '0' + number : String(number); }
        return value.getFullYear() + '-' + pad(value.getMonth() + 1) + '-' + pad(value.getDate()) +
            ' ' + pad(value.getHours()) + ':' + pad(value.getMinutes());
    }
    function timelineError(field, message) {
        var input = document.getElementById('ss-custom-date-' + field);
        var error = document.getElementById('ss-custom-date-error-' + field);
        if (input) { input.setAttribute('aria-invalid', 'true'); }
        if (error) { error.textContent = message; }
        state.actionError = message;
        setStatus(message);
    }
    function applyTimelineRange(timeline, field, value, account) {
        if (state.destroyed || !state.payload || state.payload.account_key !== account) { return; }
        var current = state.payload.scopes.timeline;
        if (!current || ['from_point', 'to_point', 'from_date', 'to_date'].some(function (key) {
            return timeline[key] !== current[key];
        })) { return; }
        timeline = current;
        var args = {account_key:state.payload.account_key}, bounds = {}, times = {};
        (timeline.time_points || []).forEach(function (point) { times[point[0]] = point[1]; });
        var valid = true;
        ['from', 'to'].forEach(function (side) {
            var point = side === field ? value : state.customDates[side] ? '__custom__' : timeline[side + '_point'] || '';
            args[side + '_point'] = point;
            if (point === '__custom__') {
                var draft = state.customDates[side];
                var timestamp = draft ? customDateValue(draft.value) : timeline[side + '_date'];
                if (!hasNumber(timestamp)) { timelineError(side, t('timeline.custom_invalid')); valid = false; }
                else { args[side + '_date'] = timestamp; bounds[side] = timestamp; }
            } else { bounds[side] = point ? times[point] : side === 'from' ? 0 : null; }
        });
        if (!valid) { return; }
        if (hasNumber(bounds.to) && bounds.from >= bounds.to) {
            timelineError(field, t('timeline.custom_order')); return;
        }
        if (value !== '__custom__') { delete state.customDates[field]; }
        cancelBattleNavigation();
        state.loadedCount = 40;
        retireFeed(); state.orderIntent = null; state.feedForceStart = 0;
        invoke('timeline_range', args);
    }
    function renderTimeline(timeline, disabled) {
        var timelineScope = !!timeline && state.scope === 'manual';
        var visible = timelineScope && !disabled;
        nodes.started.style.display = timelineScope ? 'none' : 'block';
        nodes.timeline.style.display = visible ? 'flex' : 'none';
        if (!visible) { return; }
        var points = timeline.time_points || [], names = timeline.time_point_names || {}, account = state.payload.account_key;
        var rangeKey = JSON.stringify([state.payload.account_key, timeline.from_point, timeline.to_point, timeline.from_date, timeline.to_date]);
        if (rangeKey !== state.customRangeKey) { state.customDates = {}; state.customRangeKey = rangeKey; }
        ['from', 'to'].forEach(function (field) {
            if (timeline[field + '_point'] === '__custom__' && !state.customDates[field]) {
                state.customDates[field] = {value:customDateText(timeline[field + '_date'])};
            }
        });
        var signature = JSON.stringify([points, names, rangeKey, !!state.customDates.from, !!state.customDates.to, document.documentElement.getAttribute('lang')]);
        if (state.timelineSignature === signature) { return; }
        state.timelineSignature = signature;
        closeSelect(false);
        var times = {};
        points.forEach(function (point) { times[point[0]] = point[1]; });
        ['from', 'to'].forEach(function (field) {
            var from = field === 'from', selected = state.customDates[field] ? '__custom__' : timeline[field + '_point'] || '';
            var other = from ? 'to' : 'from', opposite = timeline[other + '_point'];
            var limit = state.customDates[other] ? customDateValue(state.customDates[other].value) :
                opposite === '__custom__' ? timeline[other + '_date'] : times[opposite];
            var label = t('timeline.' + field);
            var choices = [['', t(from ? 'timeline.beginning' : 'timeline.now')]];
            points.forEach(function (point, index) {
                if (!hasNumber(limit) || (from ? point[1] < limit : point[1] > limit)) {
                    choices.push([point[0], names[point[0]] || '#' + (index + 1) + ' · ' + date(point[1], false)]);
                }
            });
            choices.push(['__custom__', t('timeline.custom')]);
            var holder = document.getElementById('ss-timeline-' + field);
            clear(holder);
            var control = makeSelect('timeline-' + field, holder, choices, function (value) {
                if (value === '__custom__') {
                    if (!state.customDates[field]) { state.customDates[field] = {value:customDateText(timeline[field + '_date'])}; }
                    state.timelineSignature = null;
                    renderTimeline(timeline, false);
                    focusControl(document.getElementById('ss-custom-date-' + field));
                    queueResize();
                } else if (value !== selected) { applyTimelineRange(timeline, field, value, account); }
            });
            control.trigger.setAttribute('aria-label', label);
            control.menu.setAttribute('aria-label', label);
            choices.forEach(function (choice, index) {
                control.options[index].title = choice[1];
                control.options[index].querySelector('.ss-control-label').textContent = choice[1];
                control.options[index].setAttribute('aria-selected', String(choice[0] === selected));
                if (choice[0] === selected) { control.label.textContent = choice[1]; control.trigger.title = choice[1]; }
            });
            if (selected === '__custom__') {
                var row = append(holder, element('div', 'ss-custom-date-row'));
                var input = append(row, element('input', 'ss-control ss-custom-date'));
                input.id = 'ss-custom-date-' + field;
                input.type = 'text'; input.maxLength = 16; input.value = state.customDates[field].value;
                input.setAttribute('placeholder', t('timeline.custom_placeholder'));
                input.setAttribute('aria-label', label + ' · ' + t('timeline.custom'));
                input.setAttribute('aria-describedby', 'ss-custom-date-error-' + field);
                var apply = append(row, element('button', 'ss-control ss-button ss-custom-date-apply'));
                apply.id = 'ss-custom-date-apply-' + field; apply.type = 'button';
                append(apply, element('span', 'ss-control-label', t('timeline.custom_apply')));
                var error = append(holder, element('div', 'ss-custom-date-error'));
                error.id = 'ss-custom-date-error-' + field; error.setAttribute('data-field', field); error.setAttribute('role', 'alert');
                input.oninput = function () {
                    if (state.destroyed || state.payload.account_key !== account || !state.customDates[field]) { return; }
                    state.customDates[field].value = input.value;
                    input.removeAttribute('aria-invalid'); error.textContent = '';
                };
                apply.onclick = function () { applyTimelineRange(timeline, field, '__custom__', account); };
                input.onkeydown = function (event) {
                    if ((event.key === 'Enter' || event.keyCode === 13) && !event.isComposing) {
                        event.preventDefault(); event.stopPropagation(); apply.onclick();
                    }
                };
            }
        });
    }
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
    var bonusLabels = {
        eventCredits:'event.credits', eventXP:'event.xp', eventFreeXP:'event.free_xp',
        eventCrystal:'event.bonds',
        boosterCredits:'reserve.credits', boosterXP:'reserve.xp', boosterFreeXP:'reserve.free_xp',
        boosterTMenXP:'reserve.crew_xp', orderCredits:'clan.credits', orderXP:'clan.xp',
        orderFreeXP:'clan.free_xp', orderTMenXP:'clan.crew_xp',
        wotPlusCredits:'plus.credits', wotPlusXP:'plus.xp', wotPlusFreeXP:'plus.free_xp',
        wotPlusCrewXP:'plus.crew_xp', premiumVehicleXP:'premium_vehicle.xp', squadXP:'platoon.xp',
        dailyXPFactor10:'daily', additionalXPFactor10:'additional',
        appliedPremiumCreditsFactor100:'premium.credits', appliedPremiumXPFactor100:'premium.xp'
    };
    function rewardRow(table, text) {
        var row = append(table, element('div', 'ss-more-value'));
        row.setAttribute('role', 'row');
        // Catalog reward messages use a label followed by a colon and amount.
        // Keep that localized wording while aligning the two cells for scanning.
        var separator = text.indexOf(':');
        if (separator >= 0) {
            var label = append(row, element('div', 'ss-more-label', text.slice(0, separator + 1)));
            label.setAttribute('role', 'rowheader');
            append(row, element('div', 'ss-more-amount', text.slice(separator + 1))).setAttribute('role', 'cell');
        } else {
            var value = append(row, element('div', 'ss-more-amount ss-more-total', text));
            value.setAttribute('role', 'cell');
            value.setAttribute('aria-colspan', '2');
        }
    }
    function rewardTable(parent, className) {
        // Gameface does not render HTML table tags. Use supported block/flex
        // elements and expose the same row and cell structure to accessibility.
        var table = append(parent, element('div', 'ss-more-table' + (className ? ' ' + className : '')));
        table.setAttribute('role', 'table');
        var body = append(table, element('div', 'ss-more-body'));
        body.setAttribute('role', 'rowgroup');
        return body;
    }
    function missionProgress(status, mission) {
        var terminal = ['completed', 'honors', 'failed', 'reset'].indexOf(mission.status) >= 0;
        var objectives = Array.isArray(mission.objectives) ? mission.objectives.slice(0, 12).filter(function (item) {
            return item && ['battles', 'vehicles', 'damage', 'kills', 'xp', 'seconds', 'counter'].indexOf(item.unit) >= 0;
        }) : [];
        var meaningful = objectives.some(function (item) {
            return item && (hasNumber(item.delta) || hasNumber(item.after));
        });
        if (terminal) { status.textContent = t('more.mission.' + mission.status); }
        else if (mission.progress_state === 'unchanged') { status.textContent = t('more.progress.none'); }
        else if (mission.progress_state === 'changed' && meaningful) { status.textContent = ''; }
        else { status.textContent = t('more.progress.unavailable'); }
        function amount(value) {
            return Math.floor(value) === value ? number(value) : value.toFixed(1).replace('.', t('format.decimal'));
        }
        objectives.forEach(function (item) {
            if (!item || ['battles', 'vehicles', 'damage', 'kills', 'xp', 'seconds', 'counter'].indexOf(item.unit) < 0) { return; }
            var label = typeof item.label === 'string' && item.label ? item.label : t('more.progress.unit.' + item.unit);
            var delta = hasNumber(item.delta) ? (item.delta > 0 ? '+' : item.delta < 0 ? '−' : '') + amount(Math.abs(item.delta)) : null;
            var text;
            if (hasNumber(item.after) && hasNumber(item.target) && item.target > 0) {
                text = t('more.progress.target', [label, amount(item.after), amount(item.target)]);
                if (delta !== null) { text += ' (' + delta + ')'; }
                if (item.unit === 'counter') { text += ' · ' + rate(item.after * 100 / item.target); }
            } else if (hasNumber(item.before) && hasNumber(item.after) && delta !== null) {
                text = t('more.progress.range', [label, amount(item.before), amount(item.after), delta]);
            } else if (delta !== null) { text = t('more.progress.change', [label, delta]); }
            else if (hasNumber(item.after)) { text = label + ': ' + amount(item.after); }
            if (text) {
                var line = append(status, element('div', 'ss-more-objective', text));
                line.setAttribute('data-unit', item.unit);
            }
        });
        if (!objectives.length && hasNumber(mission.before) && hasNumber(mission.after)) {
            var key = mission.progress_kind === 'vehicles' ? 'more.progress.vehicles' : 'more.progress';
            append(status, element('div', 'ss-more-mission-progress', t(key, [number(mission.before), number(mission.after)])));
        }
    }
    function renderBattleMore(panel, battle) {
        var data = battle.details || {}, points = data.pass_points || {};
        var missions = data.missions || {}, ids = Object.keys(missions);
        var bonuses = data.bonuses || {};
        if (hasNumber(points.credited) || ['battle', 'missions', 'vehicle'].some(function (key) { return hasNumber(points[key]); })) {
            var pass = append(panel, element('div', 'ss-more-reward-block ss-more-pass-block'));
            append(pass, element('h3', 'ss-more-title', t('more.pass')));
            var passTable = rewardTable(pass, 'ss-more-pass');
            if (hasNumber(points.credited)) { rewardRow(passTable, t('more.pass.total', [number(points.credited)])); }
            ['battle', 'missions', 'vehicle'].forEach(function (key) {
                if (points[key] > 0 || (!hasNumber(points.credited) && hasNumber(points[key]))) {
                    rewardRow(passTable, t('more.pass.' + key, [number(points[key])]));
                }
            });
        }
        var keys = Object.keys(bonusLabels).filter(function (key) { return hasNumber(bonuses[key]); });
        var hasBonuses = keys.length || battle.xp_bonus_applied;
        var detailColumns = ids.length || hasBonuses ? append(panel, element('div', 'ss-more-columns')) : null;
        // Keep the reading order stable when either section is absent or wraps.
        var bonusBlock = hasBonuses ? append(detailColumns,
            element('div', 'ss-more-reward-block ss-more-bonus-block')) : null;
        if (ids.length) {
            var missionBlock = append(detailColumns, element('div', 'ss-more-mission-block'));
            append(missionBlock, element('h3', 'ss-more-title', t('more.missions')));
            if (data.active_crucible && ids.indexOf(data.active_crucible) > 0) {
                ids.splice(ids.indexOf(data.active_crucible), 1);
                ids.unshift(data.active_crucible);
            }
            var missionTable = rewardTable(missionBlock, 'ss-more-missions');
            ids.forEach(function (id) {
                var mission = missions[id], kind = mission.kind || 'other';
                var row = append(missionTable, element('div', 'ss-more-mission'));
                row.setAttribute('role', 'row');
                var label = t('more.kind.' + kind);
                if (mission.operation) { label += ' · ' + mission.operation; }
                if (hasNumber(mission.stage)) { label += ' · ' + t('more.stage', [number(mission.stage)]); }
                if (id === data.active_crucible) { label += ' · ' + t('more.active'); }
                var identity = append(row, element('div', 'ss-more-mission-name'));
                identity.setAttribute('role', 'rowheader');
                append(identity, element('strong', '', mission.name || (kind === 'crucible' ? t('more.kind.crucible') : id)));
                append(identity, element('div', 'ss-more-caption', label));
                var status = append(row, element('div', 'ss-more-mission-status',
                    t('more.mission.' + (mission.status || 'observed'))));
                status.setAttribute('role', 'cell');
                missionProgress(status, mission);
                if (mission.description) { append(row, element('div', 'ss-more-mission-description ss-more-caption', mission.description)); }
            });
        }
        if (bonusBlock) {
            append(bonusBlock, element('h3', 'ss-more-title', t('more.bonuses')));
            var columns = ['finance.credits', 'more.column.xp', 'more.column.free_xp', 'more.column.crew_xp', 'finance.bonds'];
            var sources = [
                ['eventCredits', 'eventXP', 'eventFreeXP', null, 'eventCrystal'],
                ['boosterCredits', 'boosterXP', 'boosterFreeXP', 'boosterTMenXP'],
                ['orderCredits', 'orderXP', 'orderFreeXP', 'orderTMenXP'],
                ['wotPlusCredits', 'wotPlusXP', 'wotPlusFreeXP', 'wotPlusCrewXP'],
                [null, 'premiumVehicleXP'], [null, 'squadXP'],
                ['appliedPremiumCreditsFactor100', 'appliedPremiumXPFactor100'],
                [null, 'dailyXPFactor10'], [null, 'additionalXPFactor10']
            ].filter(function (source) { return source.some(function (key) { return key && hasNumber(bonuses[key]); }); });
            var visible = columns.map(function (label, index) {
                return sources.some(function (source) { return source[index] && hasNumber(bonuses[source[index]]); });
            });
            var longBonus = sources.some(function (source) {
                return source.some(function (key, index) {
                    return key && key.indexOf('Factor') < 0 && hasNumber(bonuses[key]) &&
                        Math.abs(bonuses[key]) >= (index === 1 ? 1000 : 1000000);
                });
            });
            if (longBonus) { bonusBlock.className += ' ss-long-bonus-values'; }
            bonusBlock.setAttribute('data-resource-count', String(visible.filter(function (value) { return value; }).length));
            var bonusTable = sources.length ? rewardTable(bonusBlock, 'ss-more-bonuses' + (longBonus ? ' ss-long-bonus-values' : '')) : null;
            var factors = null;
            if (sources.length) {
                var heading = append(bonusTable, element('div', 'ss-bonus-row ss-bonus-head'));
                heading.setAttribute('role', 'row');
                append(heading, element('div', 'ss-bonus-label', t('more.bonuses'))).setAttribute('role', 'columnheader');
                columns.forEach(function (label, index) {
                    if (visible[index]) { append(heading, element('div', 'ss-bonus-number ss-bonus-column-' + index, t(label))).setAttribute('role', 'columnheader'); }
                });
                sources.forEach(function (source) {
                    var first = source.filter(function (key) { return key && hasNumber(bonuses[key]); })[0];
                    var caption = t('more.bonus.' + bonusLabels[first], ['']);
                    var separator = caption.indexOf(':');
                    var row = append(bonusTable, element('div', 'ss-bonus-row'));
                    row.setAttribute('role', 'row');
                    append(row, element('div', 'ss-bonus-label', separator >= 0 ? caption.slice(0, separator) : caption)).setAttribute('role', 'rowheader');
                    columns.forEach(function (label, index) {
                        if (!visible[index]) { return; }
                        var value = source[index] && bonuses[source[index]];
                        var key = source[index];
                        var divisor = key && (key.slice(-9) === 'Factor100' ? 100 : key.slice(-8) === 'Factor10' ? 10 : null);
                        var output = hasNumber(value) ? (divisor ? '\u00d7' + String(value / divisor).replace('.', t('format.decimal')) : signed(value)) : t('format.missing');
                        append(row, element('div', 'ss-bonus-number ss-bonus-column-' + index + (divisor ? ' ss-bonus-factor' : ''), output)).setAttribute('role', 'cell');
                    });
                });
            }
            if (battle.xp_bonus_applied && !hasNumber(bonuses.additionalXPFactor10)) {
                if (!factors) { factors = rewardTable(bonusBlock, 'ss-more-factors'); }
                rewardRow(factors, t('more.bonus.applied'));
            }
        }
        if (data.suicide) { append(panel, element('p', 'ss-more-caption', t('more.suicide'))); }
        if (!panel.firstChild) { append(panel, element('p', '', t('more.empty'))); }
    }
    function attachBattleMore(card, header, battle) {
        var button = append(header, element('button', 'ss-control ss-button ss-more-button'));
        button.type = 'button';
        button.title = t('more.button');
        append(button, element('span', 'ss-control-label', t('more.button')));
        var panel = append(card, element('div', 'ss-more-panel'));
        function show(open) {
            button.setAttribute('aria-expanded', String(open));
            button.title = t(open ? 'more.less' : 'more.button');
            button.querySelector('.ss-control-label').textContent = button.title;
            panel.style.display = open ? 'flex' : 'none';
            if (open && !panel.firstChild) { renderBattleMore(panel, battle); }
            queueResize();
        }
        button.onclick = function () {
            var open = button.getAttribute('aria-expanded') !== 'true';
            if (open) { state.openBattles['$' + battle.id] = true; }
            else { delete state.openBattles['$' + battle.id]; }
            invalidateCardFlow();
            show(open);
        };
        show(state.openBattles['$' + battle.id] === true);
    }

    function viewContext() {
        var scope = currentScope();
        return {account_key:state.payload.account_key, scope:scopeName(), period_id:scope.period_id};
    }
    function sameContext(context) {
        if (state.destroyed || !state.payload || !currentScope()) { return false; }
        var current = viewContext();
        return context.account_key === current.account_key && context.scope === current.scope && context.period_id === current.period_id;
    }
    function clearBattleTarget() {
        state.targetSequence += 1;
        var timer = state.targetTimer; state.targetTimer = null;
        state.highlightedBattle = null;
        cancelUITimer(timer);
        (state.groupCards || []).forEach(function (card) {
            var outline = card.querySelector('.ss-battle-target-outline');
            if (outline && outline.parentNode) { outline.parentNode.removeChild(outline); }
            ['ss-battle-target', 'ss-target-pulsing', 'ss-target-muted'].forEach(function (name) { card.classList.remove(name); });
        });
    }
    function paintBattleTarget(card) {
        var target = state.highlightedBattle;
        if (!target || !sameContext(target.context) || card.getAttribute('data-group-id') !== target.id) { return; }
        var outline = card.querySelector('.ss-battle-target-outline');
        if (!outline) { outline = append(card, element('span', 'ss-battle-target-outline')); outline.setAttribute('aria-hidden', 'true'); }
        card.classList.add('ss-battle-target');
        var pulsing = Date.now() < target.until;
        card.classList[pulsing ? 'add' : 'remove']('ss-target-pulsing');
        card.classList[pulsing ? 'remove' : 'add']('ss-target-muted');
        card.setAttribute('tabindex', '-1');
    }
    function targetClick(event) {
        if (!state.highlightedBattle) { return; }
        var target = null;
        (state.groupCards || []).some(function (card) {
            if (card.getAttribute('data-group-id') === state.highlightedBattle.id) { target = card; return true; }
            return false;
        });
        if (!target || !target.contains(event.target)) { clearBattleTarget(); }
    }
    function confirmTargetFocus(card) {
        var sequence = state.targetSequence;
        function confirm() {
            if (state.destroyed || sequence !== state.targetSequence || !state.highlightedBattle ||
                    state.rendering || state.targetFocusTransfer || !root.contains(card)) { return; }
            if (!card.contains(document.activeElement)) { clearBattleTarget(); }
        }
        if (typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(function () { window.requestAnimationFrame(confirm); });
        } else { window.setTimeout(confirm, 0); }
    }
    function targetFocusOut(event) {
        if (!state.highlightedBattle || state.rendering || state.targetFocusTransfer) { return; }
        var card = event.target;
        while (card && card !== root && !card.classList.contains('ss-battle-target')) { card = card.parentNode; }
        if (!card || card === root) { return; }
        if (!event.relatedTarget) { confirmTargetFocus(card); }
        else if (!card.contains(event.relatedTarget)) { clearBattleTarget(); }
    }
    function targetFocusIn(event) {
        if (state.rendering || state.targetFocusTransfer) { return; }
        if (state.highlightedBattle && (event.target === document.body || event.target === document.documentElement || event.target === root)) {
            var card = root.querySelector('.ss-battle-target');
            if (card) { confirmTargetFocus(card); }
        } else { targetClick(event); }
    }
    document.addEventListener('click', targetClick, true);
    root.addEventListener('focusout', targetFocusOut);
    root.addEventListener('focusin', targetFocusIn);
    window.addEventListener('blur', clearBattleTarget);
    function cancelBattleNavigation() {
        state.pendingBattle = null; state.battleJump = null;
        var timer = state.battleJumpTimer; state.battleJumpTimer = null; cancelUITimer(timer);
    }
    function selectMapBattle(id, context) {
        if (!sameContext(context)) { return; }
        var request = 'battle-' + Date.now().toString(36) + '-' + (++state.navigationSequence);
        state.pendingBattle = {id:String(id), request_id:request, context:context};
        if (!invoke('battle_select', {account_key:context.account_key, scope:context.scope,
                period_id:context.period_id, id:id, request_id:request})) { state.pendingBattle = null; }
    }
    function consumeBattleFocus(scope) {
        var pending = state.pendingBattle, focus = scope.battle_focus;
        if (pending && !sameContext(pending.context)) { cancelBattleNavigation(); return; }
        if (!pending || !focus || focus.request_id !== pending.request_id || String(focus.id) !== pending.id) { return; }
        cancelBattleNavigation();
        state.group = 'battles'; state.loadedCount = 40;
        state.feedForceStart = scope.pagination && scope.pagination.battles ? scope.pagination.battles.page : 0;
        state.battleJump = {id:pending.id, context:pending.context, attempts:0, deadline:Date.now() + 2000};
    }
    function finishBattleJump() {
        var jump = state.battleJump;
        if (!jump || state.group !== 'battles' || !sameContext(jump.context)) { return; }
        if (state.cardFlowQueued) { return; }
        var target = null;
        (state.groupCards || []).some(function (card) {
            if (card.getAttribute('data-group-id') === jump.id) { target = card; return true; }
            return false;
        });
        // Publish the owned frame before native geometry is ready. Delayed
        // measurements must postpone scrolling, not hide the selected battle.
        if (target && !jump.targetPainted) {
            jump.targetPainted = true;
            clearBattleTarget();
            state.highlightedBattle = {id:jump.id, context:jump.context, until:Date.now() + 5000};
            paintBattleTarget(target);
            var sequence = ++state.targetSequence;
            state.targetTimer = window.setTimeout(function () {
                if (state.destroyed || sequence !== state.targetSequence || !state.highlightedBattle) { return; }
                state.targetTimer = null; state.highlightedBattle.until = 0;
                (state.groupCards || []).forEach(paintBattleTarget);
            }, 5000);
        }
        var scroll = nodes.scroll, box = target && target.getBoundingClientRect(), container = scroll.getBoundingClientRect();
        function validRect(rect) {
            return rect && hasNumber(rect.top) && hasNumber(rect.width) && hasNumber(rect.height) && rect.width > 1 && rect.height > 1;
        }
        if (!validRect(box) || !validRect(container)) {
            if (state.battleJumpTimer === null && jump.attempts < 40 && Date.now() < jump.deadline) {
                jump.attempts += 1;
                var timer = window.setTimeout(function () {
                    if (state.battleJumpTimer === timer) { state.battleJumpTimer = null; }
                    if (state.battleJump === jump && !state.destroyed && sameContext(jump.context)) { queueResize(); }
                }, 50);
                state.battleJumpTimer = timer;
            }
            return;
        }
        var offset = Math.max(0, scroll.scrollTop + box.top - container.top - pinnedFilterHeight() - 8 * (state.nativeScale || 1));
        state.battleJump = null;
        var retryTimer = state.battleJumpTimer; state.battleJumpTimer = null; cancelUITimer(retryTimer);
        focusControl(target);
        state.scrollTarget = offset;
        scroll.scrollTop = state.scrollTarget;
        queueResize();
    }
    function attachMapMore(card, header, map) {
        var vehicle = state.group === 'vehicles', kind = vehicle ? 'vehicle' : 'map';
        var context = viewContext(), key = JSON.stringify([context.account_key, context.scope, context.period_id, kind, String(map.id)]);
        var identifier = String(map.id), group = state.group;
        var titleKey = vehicle ? 'vehicles.battles' : 'maps.battles';
        var button = append(header, element('button', 'ss-control ss-button ss-more-button ss-map-more-button' + (vehicle ? ' ss-vehicle-more-button' : '')));
        button.type = 'button';
        var caption = append(button, element('span', 'ss-control-label'));
        var panel = append(card, element('div', 'ss-map-battles' + (vehicle ? ' ss-vehicle-battles' : '')));
        panel.setAttribute('role', 'region'); panel.setAttribute('aria-label', t(titleKey));
        var body = null, previous = null, next = null, pageText = null;
        var rendered = null, requestedPage = null;
        function live() {
            return sameContext(context) && state.group === group && document.documentElement.contains(card);
        }
        function load(page) {
            if (!live() || requestedPage !== null) { return; }
            requestedPage = page;
            panel.setAttribute('aria-busy', 'true');
            var args = {account_key:context.account_key, scope:context.scope, period_id:context.period_id, page:page};
            args[kind + '_id'] = identifier;
            if (!invoke(kind + '_battles', args)) {
                requestedPage = null;
                panel.setAttribute('aria-busy', 'false');
            }
        }
        function ensurePanel() {
            if (body) { return; }
            append(panel, element('h3', 'ss-more-title', t(titleKey)));
            // This fixed ten-row viewport also exists while loading/empty, so
            // replacing a partial last page never moves the pagination/card.
            body = append(panel, element('div', 'ss-history-body'));
            var pagination = append(panel, element('div', 'ss-map-battles-pagination'));
            function pageButton(direction, name) {
                var control = append(pagination, element('button', 'ss-control ss-button ss-map-page-' + name));
                control.type = 'button';
                append(control, element('span', 'ss-control-label', t('page.' + name)));
                control.onclick = function () {
                    if (!control.disabled && map.battle_list) { load(map.battle_list.page + direction); }
                };
                return control;
            }
            previous = pageButton(-1, 'previous');
            pageText = append(pagination, element('span', 'ss-map-battles-page'));
            next = pageButton(1, 'next');
        }
        function renderHistory() {
            ensurePanel();
            var list = map.battle_list, signature = JSON.stringify(list || null);
            if (rendered === signature) { return; }
            var active = document.activeElement;
            var focusedPager = active === previous || active === next ? active : null;
            var localScroll = body.scrollTop, panelScroll = panel.scrollTop, globalScroll = nodes.scroll.scrollTop;
            clear(body);
            if (!list) { append(body, element('p', 'ss-map-empty', t('maps.loading'))); }
            else {
                if (!list.items || !list.items.length) { append(body, element('p', 'ss-map-empty', t('maps.empty'))); }
                (list.items || []).forEach(function (battle) {
                    var row = append(body, element('div', 'ss-map-battle-row'));
                    row.setAttribute('data-battle-id', String(battle.id));
                    var identity = append(row, element('div', 'ss-map-battle-info'));
                    append(identity, element('strong', 'ss-map-battle-name', vehicle ? (battle.map || t('unknown.map')) : (battle.name || t('unknown.vehicle'))));
                    append(identity, element('div', 'ss-map-battle-date', date(battle.started_at, true)));
                    append(row, element('span', 'ss-map-battle-outcome', battleOutcome(battle.outcome)));
                    append(row, element('span', 'ss-map-battle-wn8', t('metric.wn8') + ' ' + integer(battle.wn8)));
                    var open = append(row, element('button', 'ss-control ss-button ss-map-battle-open'));
                    open.type = 'button'; open.setAttribute('data-battle-id', String(battle.id));
                    append(open, element('span', 'ss-control-label', t('maps.open_battle')));
                    open.onclick = function () {
                        if (live() && body.contains(open)) { selectMapBattle(battle.id, context); }
                    };
                });
            }
            previous.disabled = !list || list.page <= 0;
            next.disabled = !list || list.page + 1 >= list.pages;
            pageText.textContent = list ? t('page.status', [list.page + 1, list.pages]) : '';
            rendered = signature;
            if (focusedPager) {
                var target = !focusedPager.disabled ? focusedPager : !previous.disabled ? previous : !next.disabled ? next : button;
                if (document.activeElement !== target) { focusControl(target); }
            }
            body.scrollTop = localScroll;
            panel.scrollTop = panelScroll;
            if (nodes.scroll.scrollTop !== globalScroll) { nodes.scroll.scrollTop = globalScroll; }
        }
        function show(open) {
            button.setAttribute('aria-expanded', String(open));
            button.title = t(open ? 'more.less' : 'more.button'); caption.textContent = button.title;
            panel.style.display = open ? 'block' : 'none';
            if (open) {
                renderHistory();
                panel.setAttribute('aria-busy', String(requestedPage !== null || !map.battle_list));
            }
            queueResize();
        }
        card._ssHistoryUpdate = function (item) {
            if (!live() || !item || String(item.id) !== identifier) { return false; }
            map = item;
            var list = map.battle_list;
            // Polling can deliver the previous page while our request is in
            // flight. A clamped reply is valid when the final page disappeared.
            if (requestedPage !== null && list && list.page !== requestedPage && requestedPage < list.pages) { return true; }
            if (list) { requestedPage = null; }
            if (button.getAttribute('aria-expanded') === 'true') { renderHistory(); }
            panel.setAttribute('aria-busy', String(requestedPage !== null || !list));
            return true;
        };
        button.onclick = function () {
            if (!live()) { return; }
            var open = button.getAttribute('aria-expanded') !== 'true';
            if (open) { state.openMaps[key] = true; } else { delete state.openMaps[key]; }
            invalidateCardFlow(); show(open);
            if (open && !map.battle_list) { load(0); }
        };
        show(state.openMaps[key] === true);
    }

    function appendGroupBatch(limit, page) {
        invalidateCardFlow();
        page = page || state.cardPages[0];
        var list = page.items;
        var end = Math.min(list.length, limit);
        var fragment = document.createDocumentFragment();
        var index, item, stats, group, header, identity, subtitle, heading, meta;
        var battle = state.group === 'battles';
        for (index = page.renderedCount; index < end; index += 1) {
            item = list[index];
            stats = item.stats || {};
            group = append(fragment, element('div', 'ss-group' + (battle ? ' ss-battle' : '')));
            group.setAttribute('role', 'listitem');
            group.setAttribute('data-group-id', String(item.id || ''));
            group.setAttribute('data-list-index', String(page.offset + index));
            group.setAttribute('data-layout-index', String(index));
            group.id = 'ss-card-' + state.group + '-' + (page.offset + index);
            if (battle && state.highlightedBattle && String(item.id) === state.highlightedBattle.id && sameContext(state.highlightedBattle.context)) {
                paintBattleTarget(group);
            }
            state.groupCards.push(group); page.cards.push(group);
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
            var sorting = getOrder(currentScope());
            if (!battle && sorting.metric === 'credits_net') {
                var sortValue = hasNumber(item.sort_value) ? item.sort_value : (stats.credits_net || {})[sorting.statistic];
                append(meta, element('div', 'ss-group-sort-value', t('sort.value_per_battle', [
                    t(sorting.statistic === 'avg' ? 'sort.avg' : 'metric.' + sorting.statistic), t('sort.credits'), signed(sortValue)])));
            }
            if (battle) {
                appendOutcome(header, item);
            } else {
                headlineStat(header, t('metric.battles'), battleCount(stats), false, true).className += ' ss-group-count';
                headlineStat(header, t('metric.win_rate'), rate(stats.win_rate), false, true);
                headlineStat(header, t('metric.wn8'), integer(stats.wn8), true, true);
            }
            details(group, stats, false, battle);
            if (battle) { attachBattleMore(group, header, item); }
            else if (state.group === 'maps' || state.group === 'vehicles') { attachMapMore(group, header, item); }
        }
        page.lanes[0].appendChild(fragment);
        page.renderedCount = end;
        state.renderedCount = state.groupCards.length;
        state.loadedCount = Math.max(40, state.renderedCount);
        layoutBattleCards();
        queueResize();
    }
    function invalidateCardFlow() {
        state.cardFlowToken += 1;
        state.cardFlowQueued = false;
        state.cardFlowAttempts = 0;
        if (state.cardFlowTimer !== null) {
            try { window.clearTimeout(state.cardFlowTimer); } catch (error) { /* The retired token also guards retained callbacks. */ }
            state.cardFlowTimer = null;
        }
    }
    function arrangeCardLanes(desired, page) {
        var focused = document.activeElement, scrollTop = nodes.scroll.scrollTop, moved = false;
        var wasTransferring = state.targetFocusTransfer; state.targetFocusTransfer = true;
        try {
            desired.forEach(function (cards, index) {
                var lane = page.lanes[index], cursor = lane.firstElementChild;
                cards.forEach(function (card) {
                    if (card !== cursor) { lane.insertBefore(card, cursor); moved = true; }
                    cursor = card.nextElementSibling;
                });
            });
            if (moved && focused && document.activeElement !== focused && typeof focused.focus === 'function') { focused.focus(); }
        } finally { state.targetFocusTransfer = wasTransferring; }
        if (!moved) { return; }
        nodes.scroll.scrollTop = scrollTop;
    }
    function hasExpandedBattle(page) {
        return (state.group === 'battles' || state.group === 'maps' || state.group === 'vehicles') &&
            ((page && page.cards) || state.groupCards || []).some(function (card) {
                var button = card.querySelector('.ss-more-button');
                return button && button.getAttribute('aria-expanded') === 'true';
            });
    }
    function queueCardFlow() {
        if (state.destroyed || state.cardFlowQueued || state.cardFlowAttempts >= 3 ||
                !state.cardLayoutWide || !hasExpandedBattle()) { return; }
        state.cardFlowQueued = true;
        var token = state.cardFlowToken;
        function settle() {
            if (state.destroyed || token !== state.cardFlowToken) { return; }
            state.cardFlowQueued = false;
            state.cardFlowAttempts += 1;
            var scale = state.nativeScale || 1, cardWidth = state.effectiveCardWidth;
            (state.cardPages || []).forEach(function (page) {
                if (!state.cardLayoutWide || !hasExpandedBattle(page) || !root.contains(page.columns)) { return; }
                var heights = [], valid = true;
                page.cards.forEach(function (card) {
                    var box = card.getBoundingClientRect(), height = box.height;
                    if (!(height > 1)) { height = card.offsetHeight; }
                    if (!hasNumber(height) || height <= 1 || !hasNumber(box.width) || Math.abs(box.width / scale - cardWidth) > 1) { valid = false; }
                    heights.push(height / scale);
                });
                if (valid) {
                    var next = [16, 68], desired = [[], []];
                    page.cards.forEach(function (card, index) {
                        var lane = next[0] <= next[1] ? 0 : 1;
                        desired[lane].push(card); next[lane] += heights[index] + 16;
                    });
                    arrangeCardLanes(desired, page);
                }
            });
            queueCardFlow(); finishBattleJump(); finishPageJump(); updatePinnedFilters();
        }
        if (typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(function () { window.requestAnimationFrame(settle); });
        } else {
            try { state.cardFlowTimer = window.setTimeout(function () {
                if (token !== state.cardFlowToken || state.destroyed) { return; }
                state.cardFlowTimer = null; settle();
            }, 16); } catch (error) { state.cardFlowQueued = false; }
        }
    }
    function layoutBattleCards() {
        if (!state.cardPages || !state.cardPages.length) { return; }
        var scale = state.nativeScale || 1, width = nodes.groups.getBoundingClientRect().width / scale;
        if (state.logicalSize || (state.payload && state.payload.window_size) || !(width > 0)) {
            var payload = state.payload || {}, viewport = payload.viewport || {};
            var preferred = state.logicalSize && state.logicalSize.width;
            if (!hasNumber(preferred) && payload.window_size) { preferred = payload.window_size[0]; }
            if (!hasNumber(preferred)) { preferred = 700; }
            var available = hasNumber(viewport.width) ? viewport.width : window.innerWidth;
            width = Math.max(0, Math.min(preferred, (available - (state.bound ? 20 : 0)) / scale) - 34);
        }
        var cardWidth = (state.cardWidths || {battles:500, vehicles:560, maps:560, tiers:520})[state.group];
        var wider = Math.max(cardWidth, (state.wideCardWidths || {battles:720, vehicles:720, maps:720, tiers:720})[state.group]);
        if (width >= wider * 2 + 64) { cardWidth = wider; }
        state.effectiveCardWidth = cardWidth;
        var columnWidth = cardWidth * 2 + 64, wide = width >= columnWidth;
        var layoutKey = [wide, cardWidth, scale, Math.round(Math.min(width, cardWidth) * 1000)].join(':');
        var changed = state.cardLayoutKey !== layoutKey;
        if (changed) { invalidateCardFlow(); }
        nodes.groups.className = 'ss-card-layout' + (state.renderedFeed ? ' ss-feed-layout' : '') +
            (state.feedStaging ? ' ss-feed-staging' : '') +
            (wide ? ' ss-two-columns ss-card-stream' : '') + (wide && state.group === 'battles' ? ' ss-battle-stream' : '') +
            (Math.min(width, cardWidth) < 500 ? ' ss-stacked-more' : '') +
            (Math.min(width, cardWidth) < (state.group === 'battles' ? 430 : 500) ? ' ss-narrow-cards' : '');
        (state.cardPages || []).forEach(function (page) {
            page.columns.style.width = (wide ? columnWidth : cardWidth) + 'rem';
            page.columns.style.flexBasis = (wide ? columnWidth : cardWidth) + 'rem';
            page.lanes.forEach(function (lane) {
                lane.style.width = cardWidth + 'rem'; lane.style.flex = wide ? '0 0 ' + cardWidth + 'rem' : '1 1 0rem';
            });
            var desired = [[], []], expanded = wide && hasExpandedBattle(page);
            page.cards.forEach(function (card, index) {
                var lane = page.lanes[wide ? index % 2 : 0];
                if (changed || !expanded || page.key !== layoutKey) { desired[wide ? index % 2 : 0].push(card); }
                else if (card.parentNode !== page.lanes[0] && card.parentNode !== page.lanes[1]) { lane.appendChild(card); }
            });
            if (changed || !expanded || page.key !== layoutKey) { arrangeCardLanes(desired, page); }
            page.key = layoutKey;
        });
        var owned = [], cards = state.groupCards || [], total = state.renderedFeed ? state.renderedFeed.total : state.list.length;
        cards.forEach(function (card, index) {
            card.setAttribute('aria-posinset', String(Number(card.getAttribute('data-list-index')) + 1));
            card.setAttribute('aria-setsize', String(total));
            if (index + 1 < cards.length) { card.setAttribute('aria-flowto', cards[index + 1].id); }
            else { card.removeAttribute('aria-flowto'); }
            owned.push(card.id);
        });
        nodes.groups.setAttribute('aria-owns', owned.join(' '));
        state.cardLayoutWide = wide; state.cardLayoutKey = layoutKey;
        queueCardFlow();
    }
    function feedCollectionIdentity(scope) {
        var order = getOrder(scope);
        return JSON.stringify([state.payload.account_key, scopeName(), scope.period_id, state.group,
            order.metric, order.statistic, order.direction, order.chronology]);
    }
    function feedIdentity(scope) { return feedCollectionIdentity(scope) + '/' + state.language; }
    function feedContextIdentity() { return JSON.stringify([state.payload.account_key, scopeName(), currentScope().period_id, state.group]); }
    function cancelUITimer(timer) {
        if (timer !== null && timer !== undefined) { try { window.clearTimeout(timer); } catch (error) { /* Ownership guards retire retained callbacks. */ } }
    }
    function retireFeed() {
        var feed = state.feed;
        state.feed = null; state.pageJump = null;
        if (feed && feed.pending) { cancelUITimer(feed.pending.timer); }
    }
    function pageBoundary(feed, index, loading) {
        var section = element('div', 'ss-continuous-page');
        section.setAttribute('data-page-index', String(index));
        section.setAttribute('aria-label', t('page.status', [index + 1, feed.pages]));
        var divider = append(section, element('div', 'ss-page-divider'));
        append(divider, element('span', 'ss-page-divider-label', t('page.status', [index + 1, feed.pages])));
        if (loading) {
            var spinner = append(section, element('div', 'ss-page-spinner'));
            spinner.setAttribute('role', 'status'); spinner.setAttribute('aria-label', t('page.loading'));
            section.setAttribute('aria-busy', 'true');
        }
        return section;
    }
    function showFeedPending(feed) {
        if (state.feed !== feed) { return; }
        var old = nodes.groups.querySelector('.ss-page-pending');
        if (old && old.parentNode) { old.parentNode.removeChild(old); }
        if (!feed.pending && feed.error === null) { return; }
        var index = feed.pending ? feed.pending.page : feed.error;
        var section = pageBoundary(feed, index, !!feed.pending);
        section.className += ' ss-page-pending';
        if (feed.error !== null && !feed.pending) {
            var status = append(section, element('div', 'ss-page-status', t('page.error')));
            var retry = append(status, element('button', 'ss-control ss-button'));
            append(retry, element('span', 'ss-control-label', t('page.retry')));
            retry.type = 'button'; retry.onclick = function () { if (state.feed === feed) { requestFeedPage(feed, index, feed.errorNavigate); } };
        }
        if (index < feed.start) { nodes.groups.insertBefore(section, nodes.groups.firstChild); }
        else { append(nodes.groups, section); }
    }
    function requestFeedPage(feed, index, navigate) {
        if (state.destroyed || state.feed !== feed || feed.pending || index < 0 || index >= feed.pages) { return; }
        var request = 'page-' + Date.now().toString(36) + '-' + (++state.feedSequence);
        var pending = {page:index, id:request, navigate:!!navigate, timer:null};
        feed.pending = pending; feed.error = null;
        showFeedPending(feed); updateFeedControls();
        function fail() {
            if (state.destroyed || state.feed !== feed || feed.pending !== pending) { return; }
            feed.pending = null; feed.error = index; feed.errorNavigate = pending.navigate;
            showFeedPending(feed); updateFeedControls(); setStatus(t('page.error'));
        }
        function send() {
            if (state.destroyed || state.feed !== feed || feed.pending !== pending || !sameContext(feed.context)) { return; }
            pending.timer = window.setTimeout(fail, 10000);
            if (!invoke('page', {scope:feed.context.scope, group:feed.group, page:index, period_id:feed.context.period_id,
                    account_key:feed.context.account_key, request_id:request})) {
                cancelUITimer(pending.timer); fail();
            }
        }
        // Never invoke a synchronous native model callback from inside render.
        if (typeof window.requestAnimationFrame === 'function') { window.requestAnimationFrame(send); }
        else { window.setTimeout(send, 0); }
    }
    function prepareFeed(scope) {
        var meta = scope.pagination && scope.pagination[state.group];
        if (!state.nativeSession || !meta || !hasNumber(meta.page) || !hasNumber(meta.pages) || !hasNumber(meta.total) ||
                meta.pages < 1 || meta.page < 0 || meta.page >= meta.pages || meta.total < 0) { retireFeed(); return null; }
        var key = feedIdentity(scope), collectionKey = feedCollectionIdentity(scope), revision = String(scope.data_revision || JSON.stringify(scope.summary));
        var feed = state.feed, old = state.renderedFeed;
        if (!feed || feed.key !== key || feed.revision !== revision) {
            var navigation = feed && feed.collectionKey === collectionKey && feed.pending && feed.pending.navigate ? feed.pending.page :
                feed && feed.collectionKey === collectionKey ? feed.navigationPage : null;
            retireFeed();
            var start = state.feedForceStart !== null ? state.feedForceStart : feed && feed.collectionKey === collectionKey ? feed.start : meta.page;
            start = Math.max(0, Math.min(start, meta.pages - 1));
            var count = !state.battleJump && old ? Math.max(1, old.last - old.start + 1) : 1;
            feed = {key:key, collectionKey:collectionKey, contextKey:feedContextIdentity(), revision:revision, context:viewContext(), group:state.group, cache:{}, signatures:{}, pending:null,
                error:null, start:start, last:Math.min(meta.pages - 1, start + count - 1), current:start,
                pages:meta.pages, total:meta.total, size:meta.page_size || 40, version:0, navigationPage:null};
            if (hasNumber(navigation)) {
                feed.navigationPage = Math.max(0, Math.min(navigation, meta.pages - 1));
                feed.start = Math.min(feed.start, feed.navigationPage); feed.last = Math.max(feed.last, feed.navigationPage);
            }
            state.feed = feed; state.feedForceStart = null;
        }
        feed.pages = meta.pages; feed.total = meta.total;
        feed.last = Math.min(feed.last, meta.pages - 1);
        var pending = feed.pending;
        var matching = !pending || (meta.page === pending.page && (!meta.request_id || meta.request_id === pending.id));
        if (matching) {
            var rows = scope[state.group] || [], signature = JSON.stringify(rows);
            if (Object.prototype.hasOwnProperty.call(feed.signatures, meta.page) && feed.signatures[meta.page] !== signature) { feed.version += 1; }
            feed.signatures[meta.page] = signature; feed.cache[meta.page] = rows.slice(0);
            if (pending) {
                cancelUITimer(pending.timer);
                feed.pending = null; feed.error = null;
                feed.start = Math.min(feed.start, meta.page); feed.last = Math.max(feed.last, meta.page);
                if (pending.navigate) { feed.navigationPage = meta.page; }
            }
        }
        var patch = scope.battle_history;
        if (patch && patch.kind === state.group && patch.battle_list) {
            Object.keys(feed.cache).forEach(function (page) {
                var changed = false;
                feed.cache[page] = feed.cache[page].map(function (row) {
                    if (String(row.id) !== String(patch.id) || JSON.stringify(row.battle_list) === JSON.stringify(patch.battle_list)) { return row; }
                    var copy = {}; Object.keys(row).forEach(function (key) { copy[key] = row[key]; });
                    copy.battle_list = patch.battle_list; changed = true; return copy;
                });
                if (changed) { feed.signatures[page] = JSON.stringify(feed.cache[page]); feed.version += 1; }
            });
        }
        if (!feed.pending && feed.error === null) {
            for (var index = feed.start; index <= feed.last; index += 1) {
                if (!Object.prototype.hasOwnProperty.call(feed.cache, index)) { requestFeedPage(feed, index, false); break; }
            }
            if (!feed.pending && hasNumber(feed.navigationPage)) {
                state.pageJump = {feed:feed, page:feed.navigationPage}; feed.current = feed.navigationPage;
                feed.navigationPage = null;
            }
        }
        return feed;
    }
    function createCardPage(index, items, feed) {
        var section = feed ? pageBoundary(feed, index, false) : nodes.groups;
        if (feed) { append(nodes.groups, section); }
        var holder = feed ? append(section, element('div', 'ss-page-cards')) : section;
        var columns = append(holder, element('div', 'ss-card-columns'));
        columns.setAttribute('role', 'presentation');
        var page = {index:index, section:section, columns:columns, items:items, cards:[], renderedCount:0,
            offset:feed ? index * feed.size : 0, lanes:[append(columns, element('div', 'ss-card-column ss-card-column-left')),
                append(columns, element('div', 'ss-card-column ss-card-column-right'))]};
        page.lanes.forEach(function (lane) { lane.setAttribute('role', 'presentation'); });
        return page;
    }
    function updateFeedControls() {
        var feed = state.renderedFeed;
        if (!feed) { return; }
        document.getElementById('ss-page-previous').disabled = !!(state.feed && state.feed.pending) || feed.current <= 0;
        document.getElementById('ss-page-next').disabled = !!(state.feed && state.feed.pending) || feed.current + 1 >= feed.pages;
        document.getElementById('ss-page-label').textContent = t('page.status', [feed.current + 1, feed.pages]);
    }
    function renderGroups(scope) {
        var feed = prepareFeed(scope), complete = true;
        renderSelects(scope);
        document.getElementById('ss-sorting').style.display = 'flex';
        document.getElementById('ss-pagination').style.display = 'flex';
        var meta = scope.pagination && scope.pagination[state.group];
        nodes['list-meta'].textContent = t('groups.' + state.group + '.total', [number(meta ? meta.total : (scope[state.group] || []).length)]);
        if (feed) {
            for (var index = feed.start; index <= feed.last; index += 1) {
                if (!Object.prototype.hasOwnProperty.call(feed.cache, index)) { complete = false; break; }
            }
            if (!complete && state.renderedFeed && state.groupCards && state.groupCards.length) {
                stageFeedContext(feed.contextKey !== state.renderedFeed.contextKey);
                nodes.groups.setAttribute('aria-busy', 'true'); updateFeedControls(); return;
            }
        }
        var renderKey = [state.xp, state.language, state.appearanceCSS, feed && feed.version].join('|');
        var reuse = feed && state.renderedFeed === feed && state.cardRenderKey === renderKey;
        if (!reuse) {
            var previousHeight = nodes.groups.getBoundingClientRect().height;
            if (previousHeight > 0) { nodes.groups.style.minHeight = previousHeight + 'px'; state.groupMinHeight = true; }
            invalidateCardFlow(); clear(nodes.groups);
            nodes.groups.className = 'ss-card-layout' + (feed ? ' ss-feed-layout' : '');
            nodes.groups.setAttribute('role', 'list'); nodes.groups.removeAttribute('aria-owns');
            state.groupCards = []; state.cardPages = []; state.cardLayoutWide = null; state.cardLayoutKey = null;
            state.renderedFeed = feed; state.cardRenderKey = renderKey; state.renderedCount = 0;
        }
        nodes.groups.setAttribute('aria-busy', String(!complete));
        stageFeedContext(false);
        state.cardContextKey = feedContextIdentity();
        nodes.groups.setAttribute('aria-label', t('groups.' + state.group + '.aria'));
        if (feed) {
            var pending = nodes.groups.querySelector('.ss-page-pending');
            for (var pageIndex = feed.start; pageIndex <= feed.last; pageIndex += 1) {
                if (!feed.cache[pageIndex] || state.cardPages.some(function (page) { return page.index === pageIndex; })) { continue; }
                var cardPage = createCardPage(pageIndex, feed.cache[pageIndex], feed);
                state.cardPages.push(cardPage); appendGroupBatch(cardPage.items.length, cardPage);
            }
            // Replace a loading boundary only after the new page has its full
            // height, so a viewport at the old bottom never clamps upward.
            if (pending && pending.parentNode) { pending.parentNode.removeChild(pending); }
            state.cardPages.sort(function (a, b) { return a.index - b.index; });
            var cursor = nodes.groups.firstElementChild;
            state.cardPages.forEach(function (page) {
                if (page.section !== cursor) { nodes.groups.insertBefore(page.section, cursor); }
                cursor = page.section.nextElementSibling;
            });
            state.groupCards = []; state.list = [];
            state.cardPages.forEach(function (page) { state.groupCards = state.groupCards.concat(page.cards); state.list = state.list.concat(page.items); });
            showFeedPending(feed); updateFeedControls();
        } else {
            state.list = ordered(scope[state.group] || [], getOrder(scope));
            var legacy = createCardPage(0, state.list, null); state.cardPages = [legacy];
            document.getElementById('ss-page-previous').disabled = true;
            document.getElementById('ss-page-next').disabled = true;
            document.getElementById('ss-page-label').textContent = '';
            appendGroupBatch(state.loadedCount, legacy);
        }
        state.cardColumns = state.cardPages[0] && state.cardPages[0].columns;
        state.cardLanes = state.cardPages[0] && state.cardPages[0].lanes;
        if (!state.groupCards.length && complete) {
            append(state.cardPages[0] ? state.cardPages[0].lanes[0] : nodes.groups, element('p', 'ss-empty', t('groups.empty')));
        }
        layoutBattleCards(); queueResize();
    }
    function pinnedFilterHeight() {
        return nodes['filter-panel'] ? nodes['filter-panel'].getBoundingClientRect().height : 0;
    }
    function stageFeedContext(hidden) {
        state.feedStaging = hidden;
        nodes.groups.classList[hidden ? 'add' : 'remove']('ss-feed-staging');
        if (hidden) { nodes.groups.setAttribute('aria-hidden', 'true'); }
        else { nodes.groups.removeAttribute('aria-hidden'); }
    }
    function updatePinnedFilters(recalculate) {
        var panel = nodes['filter-panel'];
        if (!panel || state.destroyed) { return; }
        var viewport = nodes.scroll.getBoundingClientRect(), box = panel.getBoundingClientRect();
        if (!(box.height > 0) || !(viewport.height > 0)) { return; }
        if (recalculate || !hasNumber(state.filterBase)) { state.filterBase = box.top - viewport.top + nodes.scroll.scrollTop - state.filterShift; }
        var base = state.filterBase;
        var shift = box.height < viewport.height - 30 * state.nativeScale ? Math.max(0, nodes.scroll.scrollTop - base) : 0;
        state.filterShift = shift; panel.style.transform = shift ? 'translateY(' + shift + 'px)' : '';
        panel.classList[shift > 0 ? 'add' : 'remove']('is-pinned');
        if (nodes['scroll-top']) {
            nodes['scroll-top'].style.display = nodes.scroll.scrollTop > 60 * state.nativeScale ? 'flex' : 'none';
            nodes['scroll-top'].style.bottom = Math.max(48 * state.nativeScale,
                root.getBoundingClientRect().bottom - viewport.bottom + 12 * state.nativeScale) + 'px';
        }
        var feed = state.renderedFeed;
        if (feed && state.cardPages && state.cardPages.length) {
            var current = state.cardPages[0].index;
            state.cardPages.forEach(function (page) {
                if (page.section.getBoundingClientRect().top <= viewport.top + box.height + 24 * state.nativeScale) { current = page.index; }
            });
            // A short final page cannot align its divider with the pinned
            // bar: the scroll range ends first. It is still the current page.
            if (nodes.scroll.scrollTop + nodes.scroll.clientHeight >= nodes.scroll.scrollHeight - 2 * state.nativeScale) {
                current = state.cardPages[state.cardPages.length - 1].index;
            }
            feed.current = current; updateFeedControls();
        }
    }
    function finishPageJump() {
        var jump = state.pageJump;
        if (!jump || jump.feed !== state.renderedFeed || state.cardFlowQueued) { return; }
        var target = null;
        (state.cardPages || []).some(function (page) { if (page.index === jump.page) { target = page.section; return true; } return false; });
        if (!target) { return; }
        var box = target.getBoundingClientRect(), viewport = nodes.scroll.getBoundingClientRect();
        if (!(box.height > 1) || !(box.width > 1)) { return; }
        state.pageJump = null;
        if (state.feed) { state.feed.navigationPage = null; }
        state.scrollTarget = Math.max(0, nodes.scroll.scrollTop + box.top - viewport.top - pinnedFilterHeight());
        nodes.scroll.scrollTop = state.scrollTarget; updatePinnedFilters();
        queueResize();
    }
    function loadNearBottom() {
        updatePinnedFilters();
        var remaining = nodes.scroll.scrollHeight - nodes.scroll.scrollTop - nodes.scroll.clientHeight;
        if (remaining > 200 * state.nativeScale) { return; }
        if (state.renderedFeed && state.feed === state.renderedFeed) {
            var feed = state.feed;
            if (!feed.pending && feed.error === null && feed.last + 1 < feed.pages) { requestFeedPage(feed, feed.last + 1, false); }
        } else if (!state.feed && state.renderedCount < state.list.length) {
            appendGroupBatch(state.renderedCount + 40, state.cardPages[0]);
        }
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
        var target = event.target, history = null;
        var ancestor = target;
        while (ancestor && ancestor !== nodes.scroll && ancestor !== root) {
            if (ancestor.classList && ancestor.classList.contains('ss-history-body')) { history = ancestor; break; }
            ancestor = ancestor.parentNode;
        }
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
        /* Gameface may report a normalized wheel delta such as +/-1, not a
           browser pixel distance. WoT's own vertical list uses its visible
           height / 4 per wheel event. Use that same proportional step so the
           list remains usable regardless of the device's delta magnitude or
           the client's UI scale. Explicit page-mode input keeps page units. */
        var step = (vertical < 0 ? 1 : -1) * nodes.scroll.clientHeight / 4;
        if (event.deltaMode === 2) { step = -vertical * nodes.scroll.clientHeight; }
        step *= state.scrollSpeed;
        event.preventDefault(); event.stopPropagation();
        if (history) {
            var inner = Math.max(0, Math.min(history.scrollHeight - history.clientHeight, history.scrollTop + step));
            if (inner !== history.scrollTop) { history.scrollTop = inner; return; }
        }
        var last = Math.max(0, nodes.scroll.scrollHeight - nodes.scroll.clientHeight);
        var current = state.scrollTarget === null ? nodes.scroll.scrollTop : state.scrollTarget;
        state.scrollTarget = null;
        nodes.scroll.scrollTop = Math.max(0, Math.min(last, current + step));
        /* Some client revisions deliver programmatic scroll events later.
           Appending near the end must not depend on another wheel notch. */
        loadNearBottom();
    }
    function setStatus(message) { nodes.status.textContent = message; }
    function resetViewScroll() {
        // Native scroll setters can be applied after the next layout. Keep the
        // navigation intent instead of reading the old offset straight back.
        state.scrollTarget = 0;
        nodes.scroll.scrollTop = 0;
    }
    function restoreViewScroll() {
        if (state.scrollTarget === null) { return; }
        var target = state.scrollTarget;
        state.scrollTarget = null;
        nodes.scroll.scrollTop = target;
    }
    function onScrollIntent(event) {
        cancelBattleNavigation();
        state.pageJump = null;
        if (state.feed) { state.feed.navigationPage = null; }
        if (state.feed && state.feed.pending) { state.feed.pending.navigate = false; }
        // Native wheel input consumes the pending logical offset itself before
        // cancelling restoration; its DOM getter can still expose an old frame.
        if (event.type === 'wheel' && state.bound) { return; }
        if (event.type === 'keydown') {
            var key = event.key || event.keyCode;
            if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' ', 38, 40, 33, 34, 36, 35, 32].indexOf(key) < 0) { return; }
        }
        var target = event.target;
        while (target && target !== nodes.scroll) {
            if (target.tagName === 'BUTTON' || target.tagName === 'INPUT' || target.tagName === 'SELECT') { return; }
            target = target.parentNode;
        }
        // A wheel, scrollbar drag or scrolling key after rendering belongs to
        // the user; a queued layout must not undo that newer movement.
        state.scrollTarget = null;
    }
    nodes.scroll.addEventListener('wheel', onScrollIntent, true);
    nodes.scroll.addEventListener('mousedown', onScrollIntent, true);
    nodes.scroll.addEventListener('keydown', onScrollIntent, true);
    function render() {
        state.rendering = true;
        try { renderView(); } finally { state.rendering = false; }
    }
    function renderView() {
        var payload = state.payload;
        if (!payload || !payload.scopes) { return; }
        hideHelp();
        clearHelp(nodes.summary);
        clearHelp(nodes.status);
        // Also accept older/pretranslated payloads without duplicating notices
        // or inflating the status count. Do not mutate the model's snapshot.
        var warnings = uniqueNotices(payload.warnings);
        var hasInstance = !!payload.scopes.instance;
        if (state.scope === 'instance' && !hasInstance) { state.scope = 'manual'; showReset(false); }
        var scopeNames = ['launch', 'manual', 'instance'], scopeIndex;
        for (scopeIndex = 0; scopeIndex < scopeNames.length; scopeIndex += 1) {
            var scopeButton = document.getElementById('ss-scope-' + scopeNames[scopeIndex]);
            scopeButton.style.width = '';
            if (scopeNames[scopeIndex] === 'instance') { scopeButton.style.display = hasInstance ? 'flex' : 'none'; }
        }
        document.getElementById('ss-scope-launch').querySelector('.ss-control-label').textContent =
            hasInstance ? t('scope.launch.short') : t('scope.launch');
        var scope = currentScope();
        if (!scope || !scope.summary) { return; }
        var mapContext = JSON.stringify([payload.account_key, scopeName(), scope.period_id]);
        if (mapContext !== state.mapContext) { state.openMaps = {}; state.mapContext = mapContext; }
        if (state.highlightedBattle && !sameContext(state.highlightedBattle.context)) { clearBattleTarget(); }
        consumeBattleFocus(scope);
        var page = scope.pagination && scope.pagination[state.group];
        var viewKey = JSON.stringify([payload.account_key, scopeName(), state.group,
            scope.period_id, scope.from_point, scope.to_point, scope.from_date, scope.to_date, page && page.page]);
        var oldTop = state.scrollTarget === null ? nodes.scroll.scrollTop : state.scrollTarget;
        state.viewKey = viewKey;
        state.scrollTarget = oldTop;
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
        var timeline = payload.scopes.timeline;
        var timelineTab = document.getElementById('ss-scope-manual');
        timelineTab.querySelector('.ss-control-label').textContent = t(timeline ? 'scope.timeline' : 'scope.manual');
        timelineTab.setAttribute('title', t(timeline ? 'scope.timeline.title' : 'scope.manual.title'));
        nodes.reset.style.display = state.scope === 'instance' || (state.scope === 'manual' && !timeline) ? 'flex' : 'none';
        var loading = !!scope.loading || (state.scope !== 'instance' && !!payload.loading);
        var loadError = scope.load_error || (state.scope !== 'instance' && payload.load_error);
        nodes.reset.disabled = state.scope === 'launch' || loading || !!loadError;
        nodes['time-point-controls'].style.display = timeline ? 'flex' : 'none';
        nodes['time-point'].disabled = !!payload.loading || !!payload.load_error;
        nodes['time-point-name'].disabled = nodes['time-point'].disabled;
        var pointCount = timeline && (timeline.time_points || []).length;
        if (state.timePointAccount !== payload.account_key || state.timePointCount !== pointCount) {
            state.timePointAccount = payload.account_key;
            state.timePointCount = pointCount;
            state.timePointEdited = false;
        }
        if (!state.timePointEdited) { nodes['time-point-name'].value = date(Date.now() / 1000, false); }
        // A selected projection can be replaced while it is loading or has
        // failed; only unavailable durable account history locks the filters.
        renderTimeline(timeline, !!payload.loading || !!payload.load_error);
        if (scopeName() === 'timeline') { nodes.started.textContent = ''; }
        if (loading || loadError) {
            showReset(false);
            if (state.groupCards && state.groupCards.length && !payload.loading && !payload.load_error) {
                stageFeedContext(state.cardContextKey !== feedContextIdentity());
                nodes.groups.setAttribute('aria-busy', 'true');
                renderSelects(scope); setStatus(loadError || t('core.loading'));
                nodes.scroll.scrollTop = oldTop; queueResize(); return;
            }
            clear(nodes.summary);
            clear(nodes.groups);
            state.list = [];
            state.renderedCount = 0;
            state.cardPages = []; state.groupCards = []; state.renderedFeed = null;
            nodes['list-meta'].textContent = '';
            document.getElementById('ss-page-label').textContent = '';
            document.getElementById('ss-pagination').style.display = 'none';
            document.getElementById('ss-sorting').style.display = 'none';
            closeSelect(false);
            nodes.started.textContent = '';
            var loadingText = loadError || t('core.loading');
            append(nodes.summary, element('p', 'ss-data-notice', loadingText));
            var loadingWarnings = warnings, loadingWarningIndex;
            for (loadingWarningIndex = 0; loadingWarningIndex < loadingWarnings.length; loadingWarningIndex += 1) {
                if (loadingWarnings[loadingWarningIndex] !== loadingText) {
                    if (informationalNotice(loadingWarnings[loadingWarningIndex])) {
                        help(nodes.summary, loadingWarnings[loadingWarningIndex]);
                    } else { append(nodes.summary, element('p', 'ss-data-notice', loadingWarnings[loadingWarningIndex])); }
                }
            }
            setStatus(loadingText);
            nodes.scroll.scrollTop = oldTop;
            queueResize();
            return;
        }
        renderSummary(scope.summary, scope);
        var visibleWarnings = warnings.filter(function (warning) {
            if (informationalNotice(warning)) {
                if (warning !== t('normalize.reserve') && warning !== english['normalize.reserve']) { help(nodes.summary, warning); }
                return false;
            }
            return true;
        });
        if (visibleWarnings.length) {
            var notices = append(nodes.summary, element('div', 'ss-data-notices'));
            var warningIndex;
            for (warningIndex = 0; warningIndex < visibleWarnings.length; warningIndex += 1) {
                append(notices, element('p', 'ss-data-notice', visibleWarnings[warningIndex]));
            }
        }
        renderGroups(scope);
        var text = t('status.settled', [number(scope.summary.battles)]);
        if (observedTotal(scope.summary) > (scope.summary.battles || 0)) {
            text = t('status.incomplete', [number(scope.summary.battles), number(observedTotal(scope.summary))]);
        }
        if (scope.pending > 0) { text += ' · ' + t('status.pending', [number(scope.pending)]); }
        if (visibleWarnings.length) { text += ' · ' + t('status.notes', [visibleWarnings.length]); }
        setStatus(state.actionError || text);
        nodes.scroll.scrollTop = oldTop;
        queueResize();
    }
    function update(payload) {
        closeSelect(false);
        if (state.destroyed) { return false; }
        try {
            var value = unwrap(payload);
            if (typeof value === 'string') { value = JSON.parse(value); }
            if (value && value.resize_gesture) {
                var gesture = value.resize_gesture;
                if (state.resize && gesture.token === String(state.resizeSequence)) {
                    state.resize.native = true;
                    setLogicalSize(gesture.width, gesture.height, state.resize.corner);
                    if (!gesture.active) { endResize(false); }
                }
                return true;
            }
            if (!value || typeof value !== 'object' || !value.scopes ||
                    !value.scopes.launch || !value.scopes.manual) { throw new Error('Invalid snapshot'); }
            var intent = state.orderIntent;
            if (intent) {
                var intended = value.scopes[intent.context.scope];
                if (value.account_key === intent.context.account_key && intended && intended.period_id === intent.context.period_id) {
                    var actual = intended.ordering && intended.ordering[intent.group];
                    if (actual && ['metric', 'statistic', 'direction', 'chronology'].some(function (key) {
                        return actual[key] !== intent.options[key];
                    })) { return true; }
                }
                state.orderIntent = null;
            }
            if (historyOnlyUpdate(value)) { return true; }
            if (state.payload && state.payload.account_key !== value.account_key) {
                showReset(false);
                resetWindowSettings();
                state.logicalSize = null;
                state.openBattles = {};
                state.openMaps = {};
                state.customDates = {}; state.customRangeKey = null;
                clearBattleTarget(); retireFeed(); state.renderedFeed = null; state.orderIntent = null;
                state.cardPages = []; state.groupCards = []; state.feedForceStart = null;
                state.filterBase = null;
                resetViewScroll();
                cancelBattleNavigation();
                state.timelineSignature = null;
            }
            state.payload = value;
            state.actionError = null;
            applyLanguage(value.localization);
            applyAppearance(value.appearance);
            render();
            if (state.bound) { queueResize(); }
            return true;
        } catch (error) {
            state.actionError = t('error.snapshot');
            setStatus(state.actionError);
            return false;
        }
    }
    function historyOnlyUpdate(value) {
        if (!state.payload || !state.groupCards || !state.groupCards.length ||
                state.actionError || (state.group !== 'maps' && state.group !== 'vehicles') || state.feed !== state.renderedFeed) { return false; }
        try {
            var appearance = unwrap(value.appearance), css = appearance && unwrap(appearance.panel_css);
            if (typeof css === 'string' && css && (css !== state.appearanceCSS || !state.appearanceNode || !state.appearanceNode.parentNode)) {
                // A failed or externally removed cosmetic node needs the normal
                // update path to retry before an unchanged history payload can win.
                return false;
            }
        } catch (error) {
            // Keep native wrapper failures inside applyAppearance's fallback.
            return false;
        }
        function signature(snapshot) {
            return JSON.stringify(snapshot, function (key, item) {
                return key === 'battle_list' || key === 'battle_history' || (this === snapshot && key === 'generated_at') ? undefined : item;
            });
        }
        if (signature(state.payload) !== signature(value)) { return false; }
        state.payload = value;
        var scope = currentScope(), items = {}, patch = scope.battle_history;
        (scope[state.group] || []).forEach(function (item) { if (item.battle_list) { items['$' + item.id] = item.battle_list; } });
        if (patch && patch.kind === state.group && patch.battle_list) { items['$' + patch.id] = patch.battle_list; }
        var lookup = {};
        function replace(item) {
            var list = items['$' + item.id], copy = item;
            if (list) { copy = {}; Object.keys(item).forEach(function (key) { copy[key] = item[key]; }); copy.battle_list = list; }
            lookup['$' + copy.id] = copy; return copy;
        }
        if (state.feed) {
            Object.keys(state.feed.cache).forEach(function (page) {
                state.feed.cache[page] = state.feed.cache[page].map(replace);
                state.feed.signatures[page] = JSON.stringify(state.feed.cache[page]);
            });
        } else { state.list = state.list.map(replace); }
        (state.cardPages || []).forEach(function (page) { page.items = page.items.map(replace); });
        state.groupCards.forEach(function (card) {
            var item = lookup['$' + card.getAttribute('data-group-id')];
            if (item && typeof card._ssHistoryUpdate === 'function') { card._ssHistoryUpdate(item); }
        });
        return true;
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
        if (action !== 'resize' && action !== 'diagnostic' && action !== 'viewport') {
            state.actionError = t('error.connection');
            setStatus(state.actionError);
        }
        return false;
    }
    function focusControl(node) {
        /* Focus support differs between Gameface releases. It must never stop a tab change. */
        if (node && typeof node.focus === 'function') {
            var top = nodes.scroll.scrollTop;
            try { node.focus(); } catch (error) { /* Mouse interaction remains available. */ }
            if (nodes.scroll.scrollTop !== top) { nodes.scroll.scrollTop = top; }
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
        if (!event || event.button !== 0 || state.dialog || state.dragging || (state.windowPrefs && state.windowPrefs.maximized)) { return; }
        var target = event.target;
        while (target && target !== nodes.titlebar) {
            if (target === nodes['title-actions'] || target === nodes.close || target.tagName === 'BUTTON') { return; }
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
        var wasOpen = state.dialog;
        if (show) { endNativeDrag(); }
        state.dialog = !!show;
        resetText();
        nodes['reset-overlay'].style.display = show ? 'flex' : 'none';
        if (show) { focusControl(nodes['reset-cancel']); }
        else if (wasOpen && state.scope !== 'launch') { focusControl(nodes.reset); }
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
        cancelBattleNavigation();
        state.orderIntent = null; if (state.scope !== scope) { state.feedForceStart = 0; }
        state.scope = scope; state.loadedCount = 40;
        showReset(false); render();
    }
    function switchGroup(group) {
        closeSelect(false);
        cancelBattleNavigation();
        state.orderIntent = null; if (state.group !== group) { state.feedForceStart = 0; }
        if (state.group !== group) { state.loadedCount = 40; }
        state.group = group; render();
    }
    function changePage(direction) {
        if (state.destroyed || !state.payload || !state.payload.scopes) { return; }
        var feed = state.renderedFeed;
        if (!feed || state.feed !== feed || feed.pending) { return; }
        var page = feed.current + direction;
        if (page < 0 || page >= feed.pages) { return; }
        cancelBattleNavigation();
        if (Object.prototype.hasOwnProperty.call(feed.cache, page)) {
            state.pageJump = {feed:feed, page:page};
            if (page < feed.start || page > feed.last) {
                feed.start = Math.min(feed.start, page); feed.last = Math.max(feed.last, page); render();
            } else { finishPageJump(); }
        } else { requestFeedPage(feed, page, true); }
    }
    document.getElementById('ss-page-previous').onclick = function () { changePage(-1); };
    document.getElementById('ss-page-next').onclick = function () { changePage(1); };
    if (nodes['scroll-top']) { nodes['scroll-top'].onclick = function () {
        cancelBattleNavigation(); state.pageJump = null;
        if (state.feed) {
            // Keep the requested data, but let Top supersede its old destination.
            state.feed.navigationPage = null; state.feed.errorNavigate = false;
            if (state.feed.pending) { state.feed.pending.navigate = false; }
        }
        resetViewScroll(); updatePinnedFilters();
        queueResize();
    }; }
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
    nodes.refresh.onclick = function () {
        if (state.feed && state.feed.error !== null) { requestFeedPage(state.feed, state.feed.error, false); }
        else { invoke('refresh'); }
    };
    nodes['time-point'].onclick = function () {
        if (state.payload && !nodes['time-point'].disabled) {
            if (!state.timePointEdited) { nodes['time-point-name'].value = date(Date.now() / 1000, false); }
            invoke('time_point', {account_key:state.payload.account_key, name:nodes['time-point-name'].value});
        }
    };
    nodes['time-point-name'].oninput = function () { state.timePointEdited = true; };
    nodes['time-point-name'].onkeydown = function (event) {
        if ((event.key === 'Enter' || event.keyCode === 13) && !event.isComposing) {
            event.preventDefault();
            nodes['time-point'].onclick();
        }
    };
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
            if (helpTarget || helpPending) { hideHelp(); return; }
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
        var validWidth = hasNumber(rect.width) && rect.width > state.nativeScale;
        var validHeight = hasNumber(rect.height) && rect.height > state.nativeScale;
        var fallback = validWidth && validHeight ? null : resizePanelDimensions(rect);
        var width = Math.max(1, Math.ceil(validWidth ? rect.width : fallback.width * state.nativeScale));
        var height = Math.max(1, Math.ceil(validHeight ? rect.height : fallback.height * state.nativeScale));
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
    function setLogicalSize(width, height, edge) {
        var viewport = state.payload && state.payload.viewport;
        var scale = state.nativeScale;
        var maxWidth = (viewport && viewport.width || window.innerWidth) / scale - 20 / scale;
        var maxHeight = (viewport && viewport.height || window.innerHeight) / scale - 20 / scale;
        state.logicalSize = {
            width: Math.min(Math.max(1, maxWidth), Math.max(!edge || /[ew]/.test(edge) ? 470 : 1, width)),
            height: Math.min(Math.max(1, maxHeight), Math.max(!edge || /[ns]/.test(edge) ? 360 : 1, height))
        };
        queueResize();
    }
    function consumeResizeInput(event) {
        if (event && typeof event.preventDefault === 'function') { event.preventDefault(); }
        if (event && typeof event.stopPropagation === 'function') { event.stopPropagation(); }
        // DOM cancellation does not tell Wulf that the garage camera must not
        // receive this mouse event. This is the client's native handled flag.
        if (state.bound && window.viewEnv && typeof window.viewEnv.setEventHandled === 'function') {
            try { window.viewEnv.setEventHandled(); } catch (error) { /* DOM cancellation still applies. */ }
        }
    }
    function resizePanelDimensions(rect) {
        var scale = state.nativeScale || 1;
        var viewport = state.payload && state.payload.viewport;
        if (!state.logicalSize && !rect) { rect = root.getBoundingClientRect(); }
        var width = state.logicalSize ? state.logicalSize.width : rect.width / scale;
        var height = state.logicalSize ? state.logicalSize.height : rect.height / scale;
        // Empty first-layout measurements must not collapse the native surface
        // or its grips. Ignore a 1px placeholder; use a real cached dimension
        // or the native/CSS default (LOGICAL_SIZE), without persisting a guess.
        if (!hasNumber(width) || width <= 1) {
            width = hasNumber(state.nativeWidth) && state.nativeWidth > 2 * scale ? state.nativeWidth / scale : 700;
        }
        if (!hasNumber(height) || height <= 1) {
            height = hasNumber(state.nativeHeight) && state.nativeHeight > 2 * scale ? state.nativeHeight / scale : 620;
        }
        // Use the requested size and the same viewport bounds as the panel;
        // Gameface can report old element offsets immediately after resizing.
        var maxWidth = Math.max(1, state.bound && viewport && hasNumber(viewport.width) ? Math.floor(viewport.width - 20) : window.innerWidth) / scale;
        var maxHeight = Math.max(1, state.bound && viewport && hasNumber(viewport.height) ? Math.floor(viewport.height - 20) : window.innerHeight) / scale;
        width = Math.min(maxWidth, Math.max(Math.min(300 / scale, maxWidth), width));
        height = Math.min(maxHeight, Math.max(1, height));
        return {width:width, height:height};
    }
    function layoutResizeGrips() {
        var dimensions = resizePanelDimensions();
        // Absolute coordinates start inside the panel's 1rem border. Mirror
        // every hit box there, using explicit sizes rather than button auto layout.
        var width = Math.max(0, dimensions.width - 2);
        var height = Math.max(0, dimensions.height - 2);
        var corner = Math.min(16, width / 2, height / 2), depth = Math.min(6, corner);
        var boxes = {
            nw:[0, 0, corner, corner], ne:[width - corner, 0, corner, corner],
            sw:[0, height - corner, corner, corner], se:[width - corner, height - corner, corner, corner],
            n:[corner, 0, width - 2 * corner, depth], s:[corner, height - depth, width - 2 * corner, depth],
            w:[0, corner, depth, height - 2 * corner], e:[width - depth, corner, depth, height - 2 * corner]
        };
        var grips = root.querySelectorAll('.ss-resize-grip');
        for (var index = 0; index < grips.length; index += 1) {
            var grip = grips[index], box = boxes[grip.getAttribute('data-corner') || 'se'];
            if (!box) { continue; }
            grip.style.left = box[0] + 'rem';
            grip.style.top = box[1] + 'rem';
            grip.style.width = box[2] + 'rem';
            grip.style.height = box[3] + 'rem';
            grip.style.right = 'auto';
            grip.style.bottom = 'auto';
        }
    }
    var resizeCursorGrip = null, resizeCursorAt = null, resizeCursorTimer = null, resizeCursorToken = 0;
    function cancelResizeCursorRetry() {
        resizeCursorToken += 1;
        var timer = resizeCursorTimer;
        resizeCursorTimer = null;
        if (timer !== null) {
            try { window.clearTimeout(timer); } catch (error) { /* Ownership also makes a retained callback inert. */ }
        }
    }
    function requestResizeCursor(grip, active) {
        if (!active) {
            cancelResizeCursorRetry();
            resizeCursorGrip = null;
            resizeCursorAt = null;
            if (state.bound) { invoke('resize_cursor', {active:false, corner:grip.getAttribute('data-corner') || 'se'}); }
            return;
        }
        if (!state.bound || state.destroyed) { return; }
        var now = Date.now();
        if (resizeCursorGrip === grip && resizeCursorAt !== null && now >= resizeCursorAt && now - resizeCursorAt < 100) { return; }
        resizeCursorGrip = grip;
        resizeCursorAt = now;
        var corner = grip.getAttribute('data-corner') || 'se';
        invoke('resize_cursor', {active:true, corner:corner});
        // The host can update its cursor after dispatching the hover event.
        // Reapply once after that event, with movement requests capped at 10 Hz.
        cancelResizeCursorRetry();
        var token = resizeCursorToken;
        if (state.destroyed || !state.bound || resizeCursorGrip !== grip) { return; }
        try {
            resizeCursorTimer = window.setTimeout(function () {
                if (token !== resizeCursorToken) { return; }
                resizeCursorTimer = null;
                if (!state.destroyed && state.bound && resizeCursorGrip === grip) {
                    invoke('resize_cursor', {active:true, corner:corner});
                }
            }, 0);
        } catch (error) { resizeCursorTimer = null; }
    }
    function resizeHover(event) {
        if (state.destroyed || state.dialog || state.resize) { return; }
        var grip = event.currentTarget;
        var leaving = event.type === 'mouseleave' || event.type === 'mouseout';
        var related = event.relatedTarget;
        if (related && typeof grip.contains === 'function' && grip.contains(related)) { return; }
        if (!leaving) { consumeResizeInput(event); }
        if (!leaving || resizeCursorGrip === grip) { requestResizeCursor(grip, !leaving); }
    }
    function trackResizeOnStage(drag, on) {
        if (!on) {
            if (drag.stage) {
                for (var index = 0; index < drag.stage.listeners.length; index += 1) {
                    var listener = drag.stage.listeners[index];
                    unsubscribe(drag.stage.attempt, listener);
                    var owned = drag.stage.attempt.listeners.indexOf(listener);
                    if (owned >= 0) { drag.stage.attempt.listeners.splice(owned, 1); }
                }
                drag.stage = null;
                try { window.viewEnv.setTrackMouseOnStage(false); } catch (error) { /* Optional adapter may have gone away. */ }
            }
            return;
        }
        var attempt = state.binding;
        if (!state.bound || !isCurrent(attempt) || !window.viewEnv ||
                typeof window.viewEnv.setTrackMouseOnStage !== 'function') { return; }
        drag.stage = {attempt:attempt, listeners:[]};
        try {
            window.viewEnv.setTrackMouseOnStage(true);
            drag.stage.listeners.push(subscribe(attempt, 'mousemove', function (event) {
                if (state.resize !== drag) { return; }
                consumeResizeInput(event);
                requestResizeCursor(drag.grip, true);
            }));
            drag.stage.listeners.push(subscribe(attempt, 'mouseup', function (event) {
                if (state.resize !== drag) { return; }
                consumeResizeInput(event);
                // Outside-stage button encoding is not the DOM contract.
                // The native LEFTMOUSE poll owns release, including right-up
                // events while the left button is still held.
                if (!drag.native) { endResize(); }
            }));
        } catch (error) {
            trackResizeOnStage(drag, false);
        }
    }
    function beginResize(event) {
        if (event.button !== 0) { return; }
        consumeResizeInput(event);
        if (state.resize || state.dragging || state.dialog) { return; }
        if (state.windowPrefs && state.windowPrefs.maximized) { return; }
        var rect = root.getBoundingClientRect();
        var grip = event.currentTarget, corner = grip.getAttribute('data-corner') || 'se';
        focusControl(grip);
        state.resize = {x:event.clientX, y:event.clientY, width:rect.width, height:rect.height,
            pointer:event.pointerId, grip:grip, corner:corner, native:false};
        state.resizeSequence += 1;
        state.resizeLast = Date.now() - 100;
        requestResizeCursor(grip, true);
        trackResizeOnStage(state.resize, true);
        if (event.pointerId !== undefined && typeof grip.setPointerCapture === 'function') {
            try { grip.setPointerCapture(event.pointerId); } catch (error) { /* The game-level gesture also tracks outside the document. */ }
        }
        if (state.bound) {
            invoke('drag', {active:true});
            invoke('resize_begin', {corner:corner, token:String(state.resizeSequence)});
        }
        event.preventDefault();
    }
    function moveResize(event) {
        var drag = state.resize;
        if (!drag || (event.pointerId !== undefined && drag.pointer !== event.pointerId)) { return; }
        consumeResizeInput(event);
        requestResizeCursor(drag.grip, true);
        if (drag.native) { return; }
        var west = drag.corner.indexOf('w') >= 0, north = drag.corner.indexOf('n') >= 0;
        var horizontal = west || drag.corner.indexOf('e') >= 0;
        var vertical = north || drag.corner.indexOf('s') >= 0;
        setLogicalSize((drag.width + (horizontal ? (event.clientX - drag.x) * (west ? -1 : 1) : 0)) / state.nativeScale,
            (drag.height + (vertical ? (event.clientY - drag.y) * (north ? -1 : 1) : 0)) / state.nativeScale, drag.corner);
    }
    function endResize(notify) {
        if (!state.resize) { return; }
        var drag = state.resize;
        if (notify) { consumeResizeInput(notify); }
        if (drag.native && notify && (notify.type === 'blur' || notify.type === 'pointercancel')) { return; }
        if (drag.native && notify !== false && !state.destroyed) {
            // The game samples the release position once more. Keep this token
            // alive until its final payload arrives, then persist that size.
            if (drag.ending) { return; }
            drag.ending = true;
            if (invoke('resize_end', {token:String(state.resizeSequence)})) { return; }
        }
        if (!drag.native && notify && (notify.type === 'mouseup' || notify.type === 'pointerup')) {
            moveResize(notify);
        }
        state.resize = null;
        trackResizeOnStage(drag, false);
        requestResizeCursor(drag.grip, false);
        queueResize(true);
        if (drag.pointer !== undefined && typeof drag.grip.releasePointerCapture === 'function') {
            try { drag.grip.releasePointerCapture(drag.pointer); } catch (error) { /* Capture may already be released by the engine. */ }
        }
        if (state.bound) {
            if (notify !== false) { invoke('resize_end', {token:String(state.resizeSequence)}); }
            invoke('drag', {active:false});
            if (state.logicalSize) { invoke('size_preference', state.logicalSize); }
        }
        if (!state.destroyed && state.logicalSize) {
            previewWindowSettings({maximized:false, restored_width:Math.round(state.logicalSize.width),
                restored_height:Math.round(state.logicalSize.height)}, true);
        }
    }
    function keyboardResize(event) {
        var keys = {ArrowLeft:[-1, 0], ArrowRight:[1, 0], ArrowUp:[0, -1], ArrowDown:[0, 1]};
        var direction = keys[event.key || ({37:'ArrowLeft', 38:'ArrowUp', 39:'ArrowRight', 40:'ArrowDown'})[event.keyCode]];
        if (!direction) { return; }
        consumeResizeInput(event);
        if (state.destroyed || (state.windowPrefs && state.windowPrefs.maximized)) { return; }
        var rect = root.getBoundingClientRect(), scale = state.nativeScale;
        var corner = event.currentTarget.getAttribute('data-corner') || 'se';
        var horizontal = corner.indexOf('w') >= 0 || corner.indexOf('e') >= 0;
        var vertical = corner.indexOf('n') >= 0 || corner.indexOf('s') >= 0;
        if (state.bound) {
            invoke('drag', {active:true});
            invoke('drag', {active:false});
        }
        setLogicalSize(rect.width / scale + (horizontal ? direction[0] * 24 : 0),
            rect.height / scale + (vertical ? direction[1] * 24 : 0), corner);
        if (state.bound) { invoke('size_preference', state.logicalSize); }
        previewWindowSettings({maximized:false, restored_width:Math.round(state.logicalSize.width),
            restored_height:Math.round(state.logicalSize.height)}, true);
    }
    function bindResize(on) {
        var method = on ? 'addEventListener' : 'removeEventListener';
        var grips = root.querySelectorAll('.ss-resize-grip');
        for (var index = 0; index < grips.length; index += 1) {
            grips[index][method]('mousedown', beginResize);
            grips[index][method]('pointerdown', beginResize);
            grips[index][method]('keydown', keyboardResize);
            grips[index][method]('mouseenter', resizeHover);
            grips[index][method]('mouseover', resizeHover);
            grips[index][method]('mousemove', resizeHover);
            grips[index][method]('mouseleave', resizeHover);
            grips[index][method]('mouseout', resizeHover);
        }
        if (!on && resizeCursorGrip) { requestResizeCursor(resizeCursorGrip, false); }
        document[method]('mousemove', moveResize);
        document[method]('pointermove', moveResize);
        document[method]('mouseup', endResize);
        document[method]('pointerup', endResize);
        document[method]('pointercancel', endResize);
        window[method]('blur', endResize);
    }

    function queueResize(flush) {
        if (state.destroyed) { return; }
        var now = Date.now(), force = flush === true;
        // Native gesture samples already arrive at 10 Hz. Apply them directly;
        // throttle only the document fallback to avoid adding a second delay.
        var remaining = state.resize && !state.resize.native ? 100 - (now - state.resizeLast) : 0;
        if (!force && remaining > 0 && remaining <= 100) {
            if (state.resizeTimer === null) {
                state.resizeTimer = window.setTimeout(function () {
                    state.resizeTimer = null;
                    queueResize();
                }, remaining);
            }
            return;
        }
        if (state.resizeTimer !== null) {
            window.clearTimeout(state.resizeTimer);
            state.resizeTimer = null;
        }
        if (force) {
            state.resizeMeasureToken += 1;
            state.resizeQueued = false;
        }
        state.resizeLast = now;
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
        if (state.nativeScale !== scale) { endResize(); }
        state.nativeScale = scale;
        document.documentElement.style.fontSize = scale + 'px';
        if (state.windowPrefs && state.windowPrefs.maximized) {
            state.logicalSize = {width:Math.max(1, ((viewport && viewport.width) || window.innerWidth) - 20) / scale,
                height:Math.max(1, ((viewport && viewport.height) || window.innerHeight) - 20) / scale};
        }
        var preferred = state.payload && state.payload.window_size;
        if (!state.logicalSize && preferred && hasNumber(preferred[0]) && hasNumber(preferred[1])) {
            state.logicalSize = {width:preferred[0], height:preferred[1]};
        }
        if (state.logicalSize) {
            root.style.width = state.logicalSize.width + 'rem';
            root.style.height = state.logicalSize.height + 'rem';
        }
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
        if (state.resizeQueued) { return; }
        state.resizeQueued = true;
        var ticket = ++state.resizeMeasureToken;
        function measure() {
            if (state.destroyed || ticket !== state.resizeMeasureToken) { return; }
            state.resizeQueued = false;
            layoutResizeGrips();
            layoutSummary();
            layoutBattleCards();
            resizeNative();
            if (state.groupMinHeight) { nodes.groups.style.minHeight = ''; state.groupMinHeight = false; }
            restoreViewScroll();
            finishBattleJump();
            finishPageJump();
            updatePinnedFilters(true);
        }
        if (typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(function () { window.requestAnimationFrame(measure); });
        } else { measure(); }
    }
    bindResize(true);
    window.addEventListener('resize', queueResize);
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
            callback.apply(null, arguments);
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
        cancelBattleNavigation();
        clearBattleTarget(); retireFeed(); state.renderedFeed = null;
        nodes.groups.style.minHeight = ''; state.groupMinHeight = false;
        document.removeEventListener('click', targetClick, true);
        root.removeEventListener('focusout', targetFocusOut);
        root.removeEventListener('focusin', targetFocusIn);
        if (nodes['scroll-top']) { nodes['scroll-top'].onclick = null; }
        resetWindowSettings();
        if (nodes.maximize) { nodes.maximize.onclick = null; }
        if (nodes['background-transparency']) {
            nodes['background-transparency'].removeEventListener(sliderEvents ? 'pointerdown' : 'mousedown', beginBackgroundDrag);
            document.removeEventListener(sliderEvents ? 'pointermove' : 'mousemove', moveBackgroundDrag);
            document.removeEventListener(sliderEvents ? 'pointerup' : 'mouseup', finishBackgroundDrag);
            document.removeEventListener('pointercancel', finishBackgroundDrag);
            nodes['background-transparency'].removeEventListener('keydown', backgroundKey);
            window.removeEventListener('blur', finishBackgroundDrag);
        }
        invalidateCardFlow();
        hideHelp();
        root.removeEventListener('mouseover', waitForHelp);
        root.removeEventListener('mousemove', waitForHelp);
        root.removeEventListener('mouseout', leaveHelp);
        root.removeEventListener('focusin', focusHelp);
        root.removeEventListener('focusout', leaveHelp);
        root.removeEventListener('mousedown', pressHelp);
        root.removeEventListener('click', clickHelp);
        nodes.scroll.removeEventListener('scroll', hideHelp);
        nodes.scroll.removeEventListener('wheel', onScrollIntent, true);
        nodes.scroll.removeEventListener('mousedown', onScrollIntent, true);
        nodes.scroll.removeEventListener('keydown', onScrollIntent, true);
        window.removeEventListener('blur', hideHelp);
        window.removeEventListener('blur', clearBattleTarget);
        window.removeEventListener('resize', hideHelp);
        closeSelect(false);
        document.removeEventListener('mousedown',outsideSelect);
        clearAppearance();
        state.scrollSpeed = 1;
        endNativeDrag();
        endResize();
        if (state.resizeTimer !== null) { window.clearTimeout(state.resizeTimer); state.resizeTimer = null; }
        state.resizeMeasureToken += 1;
        state.resizeQueued = false;
        bindResize(false);
        window.removeEventListener('resize', queueResize);
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
