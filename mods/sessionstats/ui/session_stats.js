/* GRZ Session Stats — no frameworks, no network calls, no demonstration data. */
(function () {
    'use strict';
    var root = document.getElementById('grz-session-stats');
    if (!root) { return; }

    var state = { scope: 'launch', group: 'vehicles', payload: null,
        dialog: false, bound: false, nativeSession: false, binding: null, retry: null, retryDelay: 100, actionError: null,
        nativeWidth: 0, nativeHeight: 0, nativeScale: 1, diagnostics: {}, dragging: false,
        scrollSpeed: 1, appearanceNode: null, appearanceCSS: '', destroyed: false,
        orders: {}, openSelect: null, list: [], loadedCount: 40, renderedCount: 0,
        timelineSignature: null, customRangeKey: null, customDates: {}, openMaps: {}, mapContext: null,
        pendingBattle: null, battleJump: null, battleJumpTimer: null, highlightedBattle: null, navigationSequence: 0,
        targetFocusTransfer: false,
        targetTimer: null, targetSequence: 0, feed: null, renderedFeed: null,
        feedSequence: 0, feedForceStart: null, pageJump: null, pageJumpTimer: null, filterShift: 0, orderIntent: null,
        openBattles: {}, resize: null, logicalSize: null,
        cardFlowToken: 0, cardFlowQueued: false, cardFlowAttempts: 0, cardFlowTimer: null,
        windowPrefs: null, windowSaved: null, windowPending: null, windowChanges: {},
        windowSequence: 0, windowTimer: null, windowTimerToken: 0, backgroundDrag: null,
        viewKey: null, scrollTarget: null, scrollbarDrag: null, scrollbarWork: null,
        resizeSequence: 0, timePointAccount: null, timePointCount: null, timePointEdited: false,
        resizeQueued: false, resizeTimer: null, resizeLast: 0, resizeMeasureToken: 0 };
    // BEGIN GENERATED ENGLISH
    var english = {"battle.selected": "Selected battle", "cancel": "Cancel", "close": "Close", "close.symbol": "\u00d7", "core.account": "This save belongs to another account or region. Overwrite refused.", "core.battle": "Invalid battle record. Overwrite refused.", "core.boundaries": "Invalid session boundaries. Overwrite refused.", "core.closed": "This launch identifier is already closed. Reload data in a new process.", "core.create": "Could not create a session.", "core.current": "Invalid current period. Overwrite refused.", "core.invalid_id": "Invalid battle identifier.", "core.ledger": "Invalid ledger structure. Overwrite refused.", "core.load": "Could not safely load or initialize statistics. Data remains read-only.", "core.loading": "Loading history. New battle results are being saved.", "core.loading_timer": "History loading could not be scheduled. Restart the client; pending results remain saved.", "core.membership": "Some results have no known period: a reliable battle start time is missing.", "core.missing_id": "Missing battle identifier.", "core.more_notices": "Additional data notices are retained in local history.", "core.periods": "Saved periods are missing. Overwrite refused.", "core.reset_time": "Invalid reset time.", "core.result": "Invalid result record.", "core.time": "Invalid time.", "core.wn8": "No valid WN8 table. Other statistics remain available.", "coverage.battles": "{0} battles", "coverage.legend": "x/y: battles with this value / recorded battles.", "coverage.missing": "Incomplete statistics: results for {0} of {1} recorded battles. Percentages, averages and totals use received data.", "coverage.partial": "Incomplete data in {0} results. Missing values are marked beside each statistic.", "coverage.value": "Data available for {0} of {1} recorded battles.", "coverage.wn8.battle": "Insufficient data to calculate this battle\u2019s WN8.", "coverage.wn8.period": "Period WN8: data for {0} battles.", "error.action": "Could not complete the action. Try again.", "error.connection": "No connection to the game.", "error.snapshot": "Could not read statistics data.", "explain.costs": "Costs include settled battle expenses.", "explain.wn8": "Average battle WN8 may differ from period WN8.", "finance.battle": "Battle finances", "finance.bonds": "Bonds", "finance.costs": "Costs", "finance.credits": "Credits", "finance.credits_base": "Credits (base)", "finance.credits_income_base": "Base income", "finance.credits_income_received": "Received income", "finance.credits_net_base": "Base net", "finance.credits_net_received": "Received net", "finance.credits_received": "Credits (received)", "finance.currency": "Currency", "finance.gold": "Gold", "finance.income": "Income", "finance.net": "Net", "finance.period": "Battle finances", "footer.idle": "Session statistics: battles, win rate and WN8", "footer.processing": "Processing results", "footer.waiting": "Waiting for results: {0}", "format.date": "{0}.{1}.{2}, {3}:{4}", "format.date.short": "{0}.{1}, {2}:{3}", "format.decimal": ".", "format.missing": "\u2014", "format.thousands": "\u00a0", "groups.battles": "Battles", "groups.battles.aria": "Battle results", "groups.battles.count": "{0} battles", "groups.battles.total": "{0} battles", "groups.empty": "No recorded battles in this period. Results appear after a battle ends.", "groups.label": "Group results", "groups.maps": "Maps", "groups.maps.aria": "Results by map", "groups.maps.count": "{0} maps", "groups.maps.total": "{0} maps", "groups.tiers": "Tiers", "groups.tiers.aria": "Results by tier", "groups.tiers.count": "{0} tiers", "groups.tiers.total": "{0} tiers", "groups.vehicles": "Vehicles", "groups.vehicles.aria": "Results by vehicle", "groups.vehicles.count": "{0} vehicles", "groups.vehicles.total": "{0} vehicles", "health.log": "game.log (dedicated log unavailable)", "health.notice": "Session statistics: the compatibility check detected an unsupported or incomplete data format, or a result read error. Some statistics may be incomplete. Fields: {0}. Details: {1}", "health.warning": "A result format or read problem was detected during this launch. See the mod log.", "help.credits.base_received": "Base credits are the reported original earnings before bonuses. Base net subtracts the same actual battle costs. Received credits are the settled earnings after bonuses and deductions. Missing historical base earnings remain unavailable.", "help.info": "Information", "help.wn8.combined": "Like an account\u2019s overall WN8, but limited to the battles in this group. Rating of this whole set of battles: damage, kills, spotting, defence and wins are combined and compared with the expected results for the vehicles used. The Average below instead averages the WN8 ratings calculated separately for each battle.", "installation.save": "Installation history could not be saved; previous data was preserved.", "installation.unavailable": "Shared installation statistics are unavailable; account statistics remain active.", "language.auto": "Automatic", "language.de": "Deutsch", "language.en": "English", "language.es": "Espa\u00f1ol", "language.fr": "Fran\u00e7ais", "language.label": "Language", "language.pl": "Polski", "language.ru": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439", "language.save_error": "Could not save the language. Your configuration was preserved.", "language.uk": "\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430", "log.close": "Could not close the mod log ({0}).", "log.prepare": "Could not prepare a log entry ({0}).", "log.start": "Could not start the mod log ({0}).", "log.write": "Could not write the mod log ({0}).", "maps.battles": "Battles on this map", "maps.empty": "No battles available", "maps.loading": "Loading battles\u2026", "maps.open_battle": "Show battle", "maps.preview": "{0} \u2014 map preview", "metric.avg": "Average", "metric.battle_wn8": "WN8", "metric.battles": "Battles", "metric.combined_wn8": "Combined WN8", "metric.confirmed": "Results received", "metric.draws": "Draws", "metric.losses": "Losses", "metric.max": "Max", "metric.min": "Min", "metric.period_wn8": "Period WN8", "metric.win_rate": "Win rate", "metric.wins": "Wins", "metric.wn8": "WN8", "mode.random": "Random battles", "more.active": "Active in this battle", "more.bonus.additional": "Applied post-battle bonus: \u00d7{0} XP", "more.bonus.applied": "Post-battle XP bonus applied", "more.bonus.clan.credits": "Clan reserve: +{0} credits", "more.bonus.clan.crew_xp": "Clan reserve: +{0} Crew XP", "more.bonus.clan.free_xp": "Clan reserve: +{0} Free XP", "more.bonus.clan.xp": "Clan reserve: +{0} XP", "more.bonus.daily": "First victory: \u00d7{0} XP", "more.bonus.event.bonds": "Mission or event reward: +{0} bonds", "more.bonus.event.credits": "Event: +{0} credits", "more.bonus.event.free_xp": "Event: +{0} Free XP", "more.bonus.event.xp": "Event: +{0} XP", "more.bonus.platoon.xp": "Platoon: +{0} XP", "more.bonus.plus.credits": "WoT Plus: +{0} credits", "more.bonus.plus.crew_xp": "WoT Plus: +{0} Crew XP", "more.bonus.plus.free_xp": "WoT Plus: +{0} Free XP", "more.bonus.plus.xp": "WoT Plus: +{0} XP", "more.bonus.premium.credits": "Premium account: \u00d7{0} credits", "more.bonus.premium.xp": "Premium account: \u00d7{0} XP", "more.bonus.premium_vehicle.xp": "Premium vehicle: +{0} XP", "more.bonus.reserve.credits": "Personal reserve: +{0} credits", "more.bonus.reserve.crew_xp": "Personal reserve: +{0} Crew XP", "more.bonus.reserve.free_xp": "Personal reserve: +{0} Free XP", "more.bonus.reserve.xp": "Personal reserve: +{0} XP", "more.bonuses": "Bonuses", "more.button": "More", "more.column.crew_xp": "Crew XP", "more.column.free_xp": "Free XP", "more.column.xp": "XP", "more.empty": "No mission or bonus details are available for this battle.", "more.kind.battle_matters": "Battle Matters", "more.kind.crucible": "Crucible", "more.kind.daily": "Daily mission", "more.kind.daily_bonus": "Bonus daily mission", "more.kind.daily_epic": "Epic daily reward", "more.kind.other": "Mission", "more.kind.personal": "Personal mission", "more.kind.premium": "Premium mission", "more.kind.weekly": "Weekly mission", "more.less": "Less", "more.mission.completed": "Completed", "more.mission.failed": "Failed \u00b7 shield used", "more.mission.honors": "Completed with honors", "more.mission.observed": "No confirmed result", "more.mission.progress": "Progress recorded", "more.mission.reset": "Streak reset", "more.missions": "Missions", "more.pass": "Battle Pass", "more.pass.battle": "Battle result: +{0}", "more.pass.missions": "Missions: +{0}", "more.pass.total": "{0} points earned", "more.pass.vehicle": "Vehicle limit bonus: +{0}", "more.progress": "Battle counter: {0} \u2192 {1}", "more.progress.change": "{0}: {1}", "more.progress.none": "No progress recorded", "more.progress.range": "{0}: {1} \u2192 {2} ({3})", "more.progress.target": "{0}: {1}/{2}", "more.progress.unavailable": "Battle progress unavailable", "more.progress.unit.battles": "Battles", "more.progress.unit.counter": "Progress", "more.progress.unit.damage": "Damage", "more.progress.unit.kills": "Vehicles destroyed", "more.progress.unit.seconds": "Seconds", "more.progress.unit.vehicles": "Vehicles", "more.progress.unit.xp": "XP", "more.progress.vehicles": "Unique vehicles: {0} \u2192 {1}", "more.stage": "Stage {0}", "more.suicide": "The game recorded a suicide violation.", "normalize.costs": "Inconsistent consumable/directive cost breakdown.", "normalize.factor": "Incomplete credits: the deduction multiplier is missing.", "normalize.finance": "Some financial data is not yet available.", "normalize.map": "Map name is unavailable in this client version.", "normalize.platoon": "Incomplete credits: platoon deductions are missing.", "normalize.reserve": "Deferred credits do not increase this balance.", "normalize.vehicle": "Vehicle name is unavailable in this client version.", "outcome.draw": "Draw", "outcome.loss": "Defeat", "outcome.unknown": "Unknown result", "outcome.win": "Victory", "page.error": "Could not load this page.", "page.loading": "Loading page\u2026", "page.next": "Next", "page.previous": "Previous", "page.retry": "Retry", "page.status": "Page {0} of {1}", "page.top": "Back to top", "performance.battle": "Battle performance", "performance.period": "Battle performance", "period.installation": "All accounts \u00b7 Since {0}", "period.since": "Since {0}", "preview.label": "Preview \u00b7 synthetic data", "preview.open": "Open panel", "preview.restore": "Restore example", "refresh": "Refresh", "reset": "Reset period", "reset.instance.body": "A new shared period starts for this installation and persists across game restarts. Account histories and their manual resets remain unchanged.", "reset.instance.title": "Reset \u201cInstallation\u201d?", "reset.manual.body": "A new period starts now for the current account. Other accounts keep their history.", "reset.manual.title": "Reset \u201cSince reset\u201d?", "runtime.account_wait": "Waiting for account data.", "runtime.backlog": "Incomplete earlier battle results: {0}. History is preserved; recovery continues in the background. You can also select Refresh.", "runtime.begin": "Could not read a battle beginning; some results may remain pending.", "runtime.bonus": "Post-battle bonus XP cannot be read; received XP may be incomplete.", "runtime.bonus_refresh": "Automatic bonus XP refresh is unavailable; select Refresh after using a bonus.", "runtime.bonus_timer": "Bonus XP refresh is unavailable; select Refresh after using a bonus.", "runtime.cache": "Pending results cannot be read; missing battles remain pending.", "runtime.data_dir": "Local user data directory was not found.", "runtime.diagnostics": "Some mod diagnostics are unavailable; check game.log.", "runtime.direct": "Direct result events are unavailable; some results may be delayed.", "runtime.events": "Some client events could not be handled; statistics may be incomplete.", "runtime.garage": "Session statistics will be available after the account loads in the garage.", "runtime.hotkey": "Keyboard shortcut is unavailable; use the garage statistics button.", "runtime.late": "Could not complete a late result; the battle remains pending.", "runtime.log_failed": "Cannot write the dedicated mod log. Diagnostics remain in game.log.", "runtime.log_notice": "Session statistics: cannot write the dedicated mod log. Check access to the data directory; details remain in game.log.", "runtime.log_unavailable": "Dedicated mod log is unavailable.", "runtime.observer": "Additional client result reads are unavailable; events and recovery queue remain active.", "runtime.open_files": "Could not open session statistics. Check mod files and game.log.", "runtime.open_log": "Could not open session statistics. Details were recorded in game.log.", "runtime.panel": "Statistics panel is unavailable; result collection remains active.", "runtime.panel_update": "Could not update the panel; saved results remain available.", "runtime.pending": "Could not read a pending result; the battle remains pending.", "runtime.polling": "Periodic backlog reads are unavailable; client result events remain active.", "runtime.posted": "Processed result notifications are unavailable; bonus XP may require Refresh.", "runtime.processed": "Could not read a processed result; the raw result remains available.", "runtime.results": "Could not read some battle results; statistics may be incomplete.", "runtime.saved": "Could not open saved statistics.", "runtime.thumbnails": "Thumbnails are unavailable in this client version; results remain available.", "runtime.tick": "Periodic result reading failed; statistics may be incomplete.", "runtime.wn8_invalid": "Bundled WN8 table is invalid.", "runtime.wn8_load": "Could not load the WN8 table; other statistics remain available.", "runtime.wn8_missing": "Bundled WN8 expected values table is missing.", "scope.group": "Session period", "scope.instance": "Installation", "scope.instance.title": "All accounts in this installation; saved until manual reset", "scope.launch": "Since launch", "scope.launch.short": "Since launch", "scope.launch.title": "Since game launch \u2014 current account", "scope.manual": "Since reset", "scope.manual.title": "Since manual reset \u2014 current account", "scope.timeline": "Timeline", "scope.timeline.title": "Filter this account\u2019s battle history between saved time points", "sort.active_value": "Sorting value: {0}", "sort.asc": "Ascending", "sort.avg": "Avg", "sort.battles": "Battles", "sort.card_base_xp": "Base XP", "sort.card_first": "First battle", "sort.card_last": "Last battle", "sort.card_received_xp": "Rec. XP", "sort.card_source": "Source battle", "sort.chronology": "Battle date", "sort.credits": "Credits income (net)", "sort.credits.caption": "Credits income (net)", "sort.credits_costs": "Credits costs", "sort.credits_gross": "Credits income (gross)", "sort.credits_gross.caption": "Credits income (gross)", "sort.credits_income_base": "Credits income (base)", "sort.credits_income_base.caption": "Cr. income (base)", "sort.credits_income_received": "Credits income (received)", "sort.credits_income_received.caption": "Cr. income (received)", "sort.credits_net_base": "Credits income (net, base)", "sort.credits_net_base.caption": "Net credits (base)", "sort.credits_net_received": "Credits income (net, received)", "sort.credits_net_received.caption": "Net credits (received)", "sort.desc": "Descending", "sort.direction": "Order", "sort.extreme_battle": "Battle for {0}", "sort.first_newest": "First battle \u2193", "sort.first_newest.description": "First battle: newest first", "sort.first_oldest": "First battle \u2191", "sort.first_oldest.description": "First battle: oldest first", "sort.label": "Sort results", "sort.last_newest": "Last battle \u2193", "sort.last_newest.description": "Last battle: newest first", "sort.last_oldest": "Last battle \u2191", "sort.last_oldest.description": "Last battle: oldest first", "sort.metric": "Sort by", "sort.metric_stat": "{0} {1}", "sort.newest": "Newest first", "sort.off": "Off", "sort.oldest": "Oldest first", "sort.on": "On", "sort.statistic": "Statistic", "sort.sum": "All", "sort.sum.description": "Sum of the available values", "sort.tier_asc": "Tier: lowest first", "sort.tier_desc": "Tier: highest first", "sort.value_battles": "Recorded battles: {0}", "sort.value_per_battle": "{0} {1} / battle: {2}", "sort.value_total": "Total {0}: {1}", "sort.value_wn8": "{0} battle WN8: {1}", "sort.win_rate": "Win rate", "sort.xp_base": "Base XP", "sort.xp_received": "Received XP", "stats.period": "Whole period", "stats.region": "Statistics and results", "status.incomplete": "Incomplete data: results {0} / {1}", "status.notes": "Data notices: {0}", "status.pending": "Pending: {0}", "status.settled": "{0} completed battles", "storage.busy": "Data is in use by another process or the file lock is unavailable.", "storage.changed": "Another process changed the data. Reload it before saving.", "storage.collision": "Save generation conflict; previous data is preserved.", "storage.corrupt": "No valid save was found. Corrupted files were not overwritten.", "storage.failed": "Could not save statistics durably. The previous valid save is preserved.", "storage.format": "Unsupported storage format. Data remains read-only.", "storage.no_lock": "System file locking is unavailable; process protection and generation conflict detection remain active. Use one client to write this data.", "storage.readonly": "Saving is blocked: data is read-only.", "storage.recovered": "Recovered the previous valid save; the latest save was corrupted. Some recent results may need to be retrieved again.", "storage.schema": "Unsupported storage schema. Data remains read-only.", "storage.unsupported_write": "Cannot write an unsupported schema.", "timeline.beginning": "Beginning of history", "timeline.calendar": "Choose date and time", "timeline.calendar_clock_help": "Choose hours or minutes above. Click or drag the clock hand; arrow keys adjust one step.", "timeline.calendar_hour": "Hour", "timeline.calendar_minute": "Minute", "timeline.calendar_month": "Month", "timeline.calendar_months": "January|February|March|April|May|June|July|August|September|October|November|December", "timeline.calendar_next": "Next month", "timeline.calendar_previous": "Previous month", "timeline.calendar_weekdays": "Mon|Tue|Wed|Thu|Fri|Sat|Sun", "timeline.calendar_year": "Year", "timeline.create": "Create time point", "timeline.create_error": "Could not save a time point.", "timeline.custom": "Custom date", "timeline.custom_apply": "Apply", "timeline.custom_enter": "Enter to apply", "timeline.custom_future": "Choose a date and time no later than now.", "timeline.custom_hint": "DD.MM.YYYY HH:mm \u00b7 Enter to apply", "timeline.custom_invalid": "Enter a valid date and time.", "timeline.custom_order": "From must be earlier than To.", "timeline.custom_placeholder": "dd.mm.yyyy HH:mm", "timeline.from": "From", "timeline.name": "Time point name", "timeline.now": "Now", "timeline.point_menu": "Choose a time point", "timeline.to": "To", "title": "Session statistics", "unknown": "Unknown", "unknown.map": "Unknown map", "unknown.map_id": "Map {0}", "unknown.tier": "Unknown tier", "unknown.vehicle": "Unknown vehicle", "unknown.vehicle_id": "Vehicle {0}", "vehicle.AT_SPG": "Tank destroyer", "vehicle.SPG": "SPG", "vehicle.heavyTank": "Heavy tank", "vehicle.lightTank": "Light tank", "vehicle.mediumTank": "Medium tank", "vehicles.battles": "Battles in this vehicle", "visual.map": "Map", "visual.vehicle": "Vehicle", "waiting.data": "Waiting for data", "waiting.game": "Waiting for game data.", "waiting.results": "Waiting for battle results\u2026", "window.background": "Transparency", "window.background_transparency": "Background transparency", "window.maximize": "Maximize window", "window.resize": "Resize window (drag or use arrow keys)", "window.restore": "Restore window", "window.save_error": "Could not save window settings. Your configuration was preserved.", "xp.base": "Base XP", "xp.base_total": "Total base XP:", "xp.free": "Free XP:", "xp.group": "Experience type", "xp.received": "Received XP", "xp.received_total": "Total received XP:"};
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
    var ids = ['started', 'summary', 'groups', 'scroll', 'status', 'version', 'reset',
        'reset-overlay', 'reset-cancel', 'reset-confirm', 'close', 'refresh',
        'group-tabs', 'list-meta', 'titlebar', 'title-actions', 'timeline', 'time-point',
        'time-point-controls', 'time-point-name', 'resize-grip', 'maximize', 'window-background',
        'background-transparency', 'background-transparency-track', 'background-transparency-thumb',
        'background-transparency-value', 'filter-panel', 'scroll-top', 'scrollbar', 'scrollbar-thumb'];
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
            if (target.nodeType === 1 && /(^|\s)ss-(info-button|hover-help)(\s|$)/.test(target.className)) { return target; }
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
        var target = helpAncestor(event.target);
        if (target && /(^|\s)ss-info-button(\s|$)/.test(target.className) &&
                (event.button === undefined || event.button === 0)) { event.preventDefault(); }
    }
    function clickHelp(event) {
        var target = helpAncestor(event.target);
        if (target && /(^|\s)ss-info-button(\s|$)/.test(target.className)) {
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
        if (state.payload && state.payload.localization && state.payload.localization.date_settings) {
            var formatted = customDateText(value), year = String(d.getFullYear());
            if (shortDate) { formatted = formatted.replace(new RegExp('(^' + year + '[./-]|[./-]' + year + '(?= ))'), ''); }
            return formatted;
        }
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
        setActionError(t('window.save_error'));
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
        var value = Math.max(0, Math.min(100, Math.round((event.clientX - box.left) * 20 / box.width) * 5));
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
        var value = (state.windowPrefs || windowDefaults()).background_transparency, step = event.shiftKey ? 10 : 5, change = 0;
        if (key === 'Home') { value = 0; }
        else if (key === 'End') { value = 100; }
        else if (key === 'ArrowLeft' || key === 'ArrowDown') { change = -step; }
        else if (key === 'ArrowRight' || key === 'ArrowUp') { change = step; }
        else if (key === 'PageDown') { change = -10; }
        else if (key === 'PageUp') { change = 10; }
        else { return; }
        // Legacy arbitrary percentages stay readable until an interaction;
        // every new user value lands on a five-percent tick.
        if (change) { value = (change > 0 ? Math.floor(value / 5) : Math.ceil(value / 5)) * 5 + change; }
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
            // The compiled panel template exceeds 64 KiB; retain a bounded
            // allowance for supported colors/radii without rejecting native CSS.
            if (typeof css !== 'string' || css.length > 128 * 1024 || css.indexOf('\u0000') !== -1 || css.indexOf('<') !== -1) {
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
    function explainCoverage(node, count, total, label) {
        // Financial counters can reach six digits before the amounts do.
        // Give the ratio a natural break point without splitting either count.
        if (total >= 10000 && node.classList.contains('ss-cell-coverage') && node.parentNode &&
                (node.parentNode.classList.contains('ss-money-label') || node.parentNode.classList.contains('ss-money-value'))) {
            node.textContent = node.textContent.replace(/\/\s*/, '/ ');
            node.style.whiteSpace = 'normal';
        }
        var text = t('coverage.value', [number(count), number(total)]);
        if (label) { text = label + ' ' + text; }
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
    // WoT-Life's published WN8 thresholds and swatches, applied to text only.
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
        // A muted translucent backing makes black digits readable at history size.
        // Keep it on the figure only, without changing the cell's layout box.
        ink.style.backgroundColor = 'rgba(180,192,166,0.65)';
        ink.style.borderRadius = '2rem';
        ink.style.boxShadow = '0 0 0 1rem rgba(180,192,166,0.65)';
        ink.style.fontWeight = 'bold';
    }
    function paintWN8(node, value) {
        var color = wn8Color(value);
        paintWN8Ink(node, color === '#000000');
        node.style.color = color || '';
        // Black ink needs a crisp light edge against dark camo, not more blur.
        node.style.textShadow = color === '#000000' ?
            '-0.4rem 0 0 rgba(224,216,191,0.85), 0.4rem 0 0 rgba(224,216,191,0.85), ' +
            '0 -0.4rem 0 rgba(224,216,191,0.85), 0 0.4rem 0 rgba(224,216,191,0.85)' :
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
    function paintWN8Card(card, value) {
        var color = wn8Color(value), border = card.querySelector('.ss-wn8-card-border');
        if (!color) {
            if (border && border.parentNode) { border.parentNode.removeChild(border); }
            card.removeAttribute('data-wn8-border-value');
            return card;
        }
        if (!border) {
            border = append(card, element('span', 'ss-wn8-card-border'));
            border.setAttribute('aria-hidden', 'true');
        }
        border.style.borderColor = 'rgba(' + parseInt(color.slice(1, 3), 16) + ',' +
            parseInt(color.slice(3, 5), 16) + ',' + parseInt(color.slice(5, 7), 16) + ',0.22)';
        card.setAttribute('data-wn8-border-value', String(Math.round(value)));
        return card;
    }
    function headlineStat(parent, label, value, wn8, compact, rating) {
        var holder = append(parent, element('div', compact ? 'ss-group-kpi' : 'ss-kpi'));
        var name = append(holder, element('span', 'ss-kpi-label', label));
        var output = append(holder, element('strong', 'ss-kpi-value' + (wn8 ? ' ss-wn8' : ''), value));
        if (wn8) { paintWN8Caption(name, rating); paintWN8(output, rating); }
        return holder;
    }
    function headlineBattleCount(parent, stats) {
        var holder = headlineStat(parent, t('metric.battles'), battleCount(stats), false, true);
        holder.className += ' ss-group-count';
        var value = holder.querySelector('.ss-kpi-value'), total = observedTotal(stats);
        if (total > (stats.battles || 0)) {
            holder.className += ' ss-group-count-partial';
            clear(value);
            append(value, element('span', 'ss-count-confirmed', number(stats.battles)));
            append(value, element('span', 'ss-count-observed', ' / ' + number(total)));
        }
        var digits = number(stats.battles).length;
        if (digits > 6) {
            var confirmed = value.querySelector('.ss-count-confirmed') || value;
            confirmed.style.fontSize = (digits > 9 ? 10 : digits > 8 ? 12 : 14) + 'rem';
        }
        var observed = value.querySelector('.ss-count-observed');
        if (observed && number(total).length > 9) { observed.style.fontSize = '10rem'; }
        return holder;
    }
    function measureRow(parent, label, data, wn8, total, sharedCoverage, metric) {
        var row = append(parent, element('div', 'ss-metric-row'));
        if (metric) { row.setAttribute('data-ss-metric', metric); }
        var name = append(row, element('div', 'ss-metric-name'));
        append(name, element('span', 'ss-cell-value', label));
        var partial = coverage(data.count, total);
        if (partial && !sharedCoverage) { explainCoverage(append(name, element('span', 'ss-cell-coverage',
            ' (' + partial + ')')), data.count, total); }
        ['min', 'avg', 'max'].forEach(function (field) {
            var output = append(row, element('div', 'ss-metric-number', wn8 ? integer(data[field]) : number(data[field])));
            if (wn8) { paintWN8(output, data[field]); }
        });
    }
    function battleMeasure(parent, label, value, wn8, metric) {
        var row = append(parent, element('div', 'ss-battle-measure'));
        if (metric) { row.setAttribute('data-ss-metric', metric); }
        var name = append(row, element('span', 'ss-battle-label', label));
        var output = append(row, element('strong', 'ss-battle-value' + (wn8 ? ' ss-wn8' : ''),
            wn8 ? integer(value) : number(value)));
        if (wn8) { paintWN8Caption(name, value); paintWN8(output, value); }
    }
    function moneyCell(parent, data, field, total, sharedCoverage, metric, item, global, battle) {
        var value = data[field];
        var output = field === 'costs' ? cost(value) : (field === 'net' ? signed(value) : number(value));
        var cell = append(parent, element('div', 'ss-money-value' +
            (field === 'net' ? quantityClass(value) : (!hasNumber(value) ? ' ss-unknown' : ''))));
        append(cell, element('span', 'ss-cell-value', output));
        var partial = coverage(data[field + '_count'], total);
        if (partial && !sharedCoverage) { explainCoverage(append(cell, element('span', 'ss-cell-coverage', partial)),
            data[field + '_count'], total); }
        if (metric) {
            cell.setAttribute('data-ss-metric', metric);
            if (!battle) {
                cell.className += ' ss-credit-cell';
                var actions = append(cell, element('span', 'ss-credit-extreme-actions'));
                if (item && item.extrema_battles && item.extrema_battles[metric]) {
                    createMetricBattleLink(actions, item, metric, 'min', global, t('metric.min'));
                    createMetricBattleLink(actions, item, metric, 'max', global, t('metric.max'));
                }
            }
        }
    }
    function moneyRow(parent, name, data, total, sharedCoverage, metrics, item, global, battle) {
        data = data || {};
        var row = append(parent, element('div', 'ss-money-row'));
        var label = append(row, element('div', 'ss-money-label', name));
        var shared = data.income_count === data.costs_count && data.costs_count === data.net_count;
        var partial = coverage(data.income_count, total);
        if (shared && partial && !sharedCoverage) { explainCoverage(append(label, element('span', 'ss-cell-coverage', partial)), data.income_count, total); }
        moneyCell(row, data, 'income', total, shared || sharedCoverage, metrics && metrics.income, item, global, battle);
        moneyCell(row, data, 'costs', total, shared || sharedCoverage, metrics && metrics.costs, item, global, battle);
        moneyCell(row, data, 'net', total, shared || sharedCoverage, metrics && metrics.net, item, global, battle);
    }
    function freeXP(parent, stats) {
        var free = append(parent, element('div', 'ss-free-xp'));
        append(free, element('span', '', t('xp.free')));
        append(free, element('strong', '', number(series(stats.free_xp).sum)));
        var partial = coverage(series(stats.free_xp).count, observedTotal(stats));
        if (partial) { explainCoverage(append(free, element('span', 'ss-count-coverage',
            ' (' + partial + ')')), series(stats.free_xp).count, observedTotal(stats)); }
    }
    function totalXP(parent, stats, metric) {
        var data = series(stats[metric]);
        var total = observedTotal(stats), value = data.count > 0 ? data.sum : null;
        var labels = {xp_base:'xp.base_total', xp_received:'xp.received_total', free_xp:'xp.free'};
        var label = append(parent.querySelector('.ss-summary-xp-head'), element('span', 'ss-xp-total-label'));
        append(label, element('span', 'ss-xp-total-caption', t(labels[metric])));
        label.id = 'ss-total-' + metric + '-label';
        label.setAttribute('data-xp-metric', metric); label.setAttribute('role', 'columnheader');
        var holder = append(parent.querySelector('.ss-summary-xp-values'), element('div', 'ss-free-xp ss-summary-xp-total'));
        holder.setAttribute('data-xp-metric', metric); holder.setAttribute('role', 'cell');
        holder.setAttribute('aria-labelledby', label.id);
        var amount = append(holder, element('div', 'ss-xp-total-amount'));
        append(amount, element('strong', 'ss-xp-total-value' + (!hasNumber(value) ? ' ss-unknown' : ''), number(value)));
        var partial = coverage(data.count, total);
        // The headline already shows the result count. Keep metric-specific
        // availability in the existing help instead of repeating visible x/y.
        if (partial) { explainCoverage(amount, data.count, total, t(labels[metric])); }
    }
    function wn8Coverage(parent, stats, battle) {
        var partial = coverage(stats.wn8_count, observedTotal(stats));
        if (!partial) { return; }
        var section = parent;
        while (section.parentNode && section !== nodes.summary &&
                !/(^|\s)ss-group(\s|$)/.test(section.className)) { section = section.parentNode; }
        help(section, battle ? t('coverage.wn8.battle') : t('coverage.wn8.period', [partial]));
        if (!battle) { paintWN8Caption(append(parent, element('span', 'ss-count-coverage ss-wn8-coverage', 'WN8 ' + partial)), stats.wn8); }
    }
    function details(parent, stats, global, battle, item) {
        stats = stats || {};
        var total = observedTotal(stats);
        var holder = append(parent, element('div', global ? 'ss-summary-details' :
            'ss-details' + (battle ? ' ss-battle-details' : '')));
        var performance = append(holder, element('div', 'ss-performance' + (battle ? ' ss-battle-performance' : '')));
        if (!global) { append(performance, element('h3', 'ss-detail-title', battle ? t('performance.battle') : t('performance.period'))); }
        var baseXP = series(stats.xp_base), receivedXP = series(stats.xp_received);
        if (battle) {
            /* Both recorded XP values stay visible. Missing coverage cannot
               turn an unavailable sum into a plausible zero. */
            battleMeasure(performance, t('xp.base'), baseXP.count === 1 ? baseXP.sum : null, false, 'xp_base');
            battleMeasure(performance, t('xp.received'), receivedXP.count === 1 ? receivedXP.sum : null, false, 'xp_received');
            battleMeasure(performance, t('metric.wn8'), stats.wn8_count === 1 ? stats.wn8 : null, true, 'battle_wn8');
        } else {
            var battleWN8 = series(stats.battle_wn8);
            if (!global && [baseXP.min, baseXP.avg, baseXP.max, receivedXP.min, receivedXP.avg, receivedXP.max,
                    battleWN8.min, battleWN8.avg, battleWN8.max].some(function (value) {
                return hasNumber(value) && Math.abs(value) >= 100000;
            })) { performance.className += ' ss-long-metrics'; }
            var shared = baseXP.count === receivedXP.count && baseXP.count === battleWN8.count &&
                !!coverage(baseXP.count, total);
            var header = append(performance, element('div', 'ss-metric-head'));
            var countHeader = append(header, element('div', 'ss-metric-name' +
                (global ? ' ss-summary-table-heading' : shared ? ' ss-metric-count' : ''), ''));
            if (global) {
                var performanceTitle = append(countHeader, element('h3', 'ss-detail-title ss-summary-table-title'));
                append(performanceTitle, element('span', 'ss-table-heading-text', t('performance.period')));
                if (shared) { explainCoverage(countHeader, baseXP.count, total); }
            } else if (shared) { explainCoverage(append(countHeader, element('span', 'ss-cell-coverage',
                coverage(baseXP.count, total))), baseXP.count, total); }
            append(header, element('div', 'ss-metric-number', t('metric.min')));
            append(header, element('div', 'ss-metric-number', t('metric.avg')));
            append(header, element('div', 'ss-metric-number', t('metric.max')));
            measureRow(performance, t('xp.base'), baseXP, false, total, shared, 'xp_base');
            measureRow(performance, t('xp.received'), receivedXP, false, total, shared, 'xp_received');
            measureRow(performance, t('metric.battle_wn8'), battleWN8, true, total, shared, 'battle_wn8');
        }
        if (!battle) { help(performance, t('explain.wn8')); }
        var economy = append(holder, element('div', 'ss-economy'));
        if (!global) { append(economy, element('h3', 'ss-detail-title', battle ? t('finance.battle') : t('finance.period'))); }
        var currencies = stats.currencies || {}, credits = currencies.credits || {};
        // The base view changes earnings, not the actual expenses incurred.
        // Old records without original earnings show unavailable base values.
        var baseCredits = {income:credits.income_base, costs:credits.costs, net:credits.net_base,
            income_count:hasNumber(credits.income_base_count) ? credits.income_base_count : 0,
            costs_count:credits.costs_count, net_count:hasNumber(credits.net_base_count) ? credits.net_base_count : 0};
        var currencyRows = [{name:t('finance.credits_base'), data:baseCredits,
                metrics:{income:'credits_income_base', costs:'credits_costs', net:'credits_net_base'}},
            {name:t('finance.credits_received'), data:credits,
                metrics:{income:'credits_income_received', net:'credits_net_received'}},
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
            (global ? ' ss-summary-table-heading' : sharedMoneyCoverage ? ' ss-money-count' : ''),
            global || sharedMoneyCoverage ? '' : t('finance.currency')));
        if (global) {
            var financeTitle = append(currencyHeader, element('h3', 'ss-detail-title ss-summary-table-title'));
            append(financeTitle, element('span', 'ss-table-heading-text', t('finance.period')));
            if (sharedMoneyCoverage) { explainCoverage(currencyHeader, moneyCount, total); }
        } else if (sharedMoneyCoverage) { explainCoverage(append(currencyHeader, element('span', 'ss-cell-coverage',
            coverage(moneyCount, total))), moneyCount, total); }
        append(moneyHeader, element('div', 'ss-money-value', t('finance.income')));
        append(moneyHeader, element('div', 'ss-money-value', t('finance.costs')));
        append(moneyHeader, element('div', 'ss-money-value', t('finance.net')));
        currencyRows.forEach(function (currency) {
            moneyRow(economy, currency.name, currency.data, total, sharedMoneyCoverage, currency.metrics, item, global, battle);
        });
        help(economy, t('explain.costs'));
        help(economy, t('help.credits.base_received'));
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
        headlineStat(headline, t('metric.period_wn8'), integer(stats.wn8), true, false, stats.wn8);
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
        var xpTotals = append(summaryMeta, element('div', 'ss-summary-xp-totals'));
        xpTotals.setAttribute('role', 'table'); xpTotals.setAttribute('aria-label', t('xp.group'));
        append(xpTotals, element('div', 'ss-summary-xp-head')).setAttribute('role', 'row');
        append(xpTotals, element('div', 'ss-summary-xp-values')).setAttribute('role', 'row');
        totalXP(xpTotals, stats, 'xp_base');
        totalXP(xpTotals, stats, 'xp_received');
        totalXP(xpTotals, stats, 'free_xp');
        var wn8Partial = coverage(stats.wn8_count, observedTotal(stats));
        if (wn8Partial) { help(nodes.summary, t('coverage.wn8.period', [wn8Partial])); }
        details(layout, stats, true, false, {stats:stats, extrema_battles:scope.extrema_battles});
        attachMetricBattleLinks(nodes.summary, {stats:stats, extrema_battles:scope.extrema_battles}, false, true);
        layoutSummary();
        if (nodes.summary.querySelector('.ss-cell-coverage, .ss-count-coverage')) { help(nodes.summary, t('coverage.legend')); }
    }
    function tierText(tier) {
        return ['','I','II','III','IV','V','VI','VII','VIII','IX','X','XI'][tier] || '';
    }
    function vehicleType(type) {
        if (typeof type !== 'string') { return ''; }
        if (type === 'AT-SPG') { type = 'AT_SPG'; }
        var labels = { lightTank:t('vehicle.lightTank'), mediumTank:t('vehicle.mediumTank'), heavyTank:t('vehicle.heavyTank'),
            AT_SPG:t('vehicle.AT_SPG'), SPG:t('vehicle.SPG') };
        return Object.prototype.hasOwnProperty.call(labels, type) ? labels[type] : '';
    }
    function vehicleBadgeSource(src, kind, key, elite) {
        if (typeof src !== 'string') { return null; }
        if (kind === 'vehicle_class' &&
                /^img:\/\/gui\/maps\/icons\/vehicleTypes\/24x24_metal\/(lightTank|mediumTank|heavyTank|AT-SPG|SPG)(_elite)?\.(png|dds)$/.test(src)) {
            var expected = (key === 'AT_SPG' ? 'AT-SPG' : key) + (elite === true ? '_elite' : '');
            return src.slice(src.lastIndexOf('/') + 1).replace(/\.(png|dds)$/, '') === expected ? src : null;
        }
        if (kind === 'vehicle_role' && typeof key === 'string' && /^role_[A-Za-z0-9_]{1,64}$/.test(key) && key !== 'role_SPG' &&
                src === 'img://gui/maps/icons/roleExp/roles/24x24/' + key + '.png') { return src; }
        if (kind === 'vehicle_role' && typeof key === 'string' && /^role_[A-Za-z0-9_]{1,64}$/.test(key) && key !== 'role_SPG' &&
                src === 'img://gui/maps/icons/roleExp/roles/24x24/' + key + '.dds') { return src; }
        return null;
    }
    function appendVehicleMetadata(parent, item, withTier) {
        var metadata = item.vehicle_meta || {}, kind = metadata['class'] || item.type;
        if (kind === 'AT-SPG') { kind = 'AT_SPG'; }
        var className = vehicleType(kind), classIcon = metadata.class_icon || {};
        var classSource = classIcon.kind === 'vehicle_class' && vehicleBadgeSource(classIcon.src, 'vehicle_class', kind, metadata.elite);
        var role = metadata.role || {};
        if (typeof role.key !== 'string' || !/^role_[A-Za-z0-9_]{1,64}$/.test(role.key)) { role = {}; }
        var roleIcon = role.icon || {};
        var roleSource = roleIcon.kind === 'vehicle_role' && vehicleBadgeSource(roleIcon.src, 'vehicle_role', role.key);
        var roleName = typeof role.name === 'string' ? role.name.slice(0, 240) : '';
        var roleGroup = typeof role.group_name === 'string' ? role.group_name.slice(0, 240) : '';
        var description = typeof role.description === 'string' ? role.description.slice(0, 1400) : '';
        var roleHelp = roleName + (roleGroup && roleGroup !== roleName ? '\n' + roleGroup : '') +
            (description ? '\n' + description : '');
        roleHelp = roleHelp.replace(/^\s+|\s+$/g, '');
        var recordedTier = typeof item.tier === 'number' && isFinite(item.tier) &&
            item.tier >= 1 && item.tier <= 11 && Math.floor(item.tier) === item.tier ? item.tier : metadata.tier;
        var tier = withTier ? tierText(recordedTier) : '';
        if (!tier && !classSource && !roleSource) { return; }
        var row = append(parent, element('div', 'ss-group-subtitle ss-vehicle-meta'));
        var tierNode = tier ? append(row, element('span', 'ss-vehicle-tier', tier)) : null;
        function explain(node, caption, text) {
            node.className += ' ss-hover-help'; node.setAttribute('tabindex', '0');
            node.setAttribute('aria-label', caption); node.setAttribute('data-ss-help', text);
            node.setAttribute('aria-controls', helpTooltip.id); node.setAttribute('aria-expanded', 'false');
            node.title = text;
        }
        if (classSource) {
            var badge = append(row, element('span', 'ss-vehicle-class-icon ss-vehicle-icon'));
            badge.style.backgroundImage = 'url("' + classSource + '")';
            badge.setAttribute('role', 'img'); badge.setAttribute('data-vehicle-class', kind);
            badge.setAttribute('data-vehicle-elite', metadata.elite === true ? 'true' : 'false');
            explain(badge, className, className + (!roleSource && roleHelp ? '\n' + roleHelp : ''));
        } else if (tierNode && className) {
            // An unavailable texture keeps its class accessible without a fake icon.
            explain(tierNode, className, className + (roleHelp ? '\n' + roleHelp : ''));
        }
        if (roleSource) {
            var roleBadge = append(row, element('span', 'ss-vehicle-role-icon ss-vehicle-icon'));
            roleBadge.style.backgroundImage = 'url("' + roleSource + '")';
            roleBadge.setAttribute('role', 'img'); roleBadge.setAttribute('data-vehicle-role', role.key);
            explain(roleBadge, roleName || roleGroup || className, roleHelp || className);
        }
        return row;
    }
    function battleOutcome(outcome) {
        var label = { win:t('outcome.win'), loss:t('outcome.loss'), draw:t('outcome.draw') }[outcome] || t('outcome.unknown');
        return label.toUpperCase();
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
            // WG's notification backgrounds have intrinsic alpha (the PNG
            // peaks below 40%). Composite the unchanged texture in a finite
            // stack on an opaque frame; CSS opacity=1 alone cannot undo that
            // fade. Positioned layers do not change layout or accessibility.
            for (var layer = 0; layer < 12; layer += 1) {
                var paint = append(art, element('span', 'ss-outcome-image-layer'));
                paint.style.backgroundImage = 'url("' + src + '")';
            }
        }
        append(badge, element('span', 'ss-outcome-label', battleOutcome(item.outcome)));
    }
    var defaultOrder = {metric:'off', statistic:'avg', direction:'desc', chronology:'newest'};
    var defaultTierOrder = {metric:'off', statistic:'avg', direction:'desc', chronology:'tier_desc'};
    var selectOptions = {
        language:[['auto','language.auto'],['en','language.en'],['pl','language.pl'],['ru','language.ru'],['fr','language.fr'],['de','language.de'],['es','language.es'],['uk','language.uk']],
        chronology:[['newest','sort.last_newest.description'],['last_asc','sort.last_oldest.description'],['first_desc','sort.first_newest.description'],['oldest','sort.first_oldest.description'],['tier_desc','sort.tier_desc'],['tier_asc','sort.tier_asc']],
        statistic:[['min','metric.min'],['avg','sort.avg'],['max','metric.max'],['sum','sort.sum','sort.sum.description']],
        metric:[['off','sort.off'],['xp_base','sort.xp_base'],['xp_received','sort.xp_received'],['credits_income_base','sort.credits_income_base.caption','sort.credits_income_base'],['credits_income_received','sort.credits_income_received.caption','sort.credits_income_received'],['credits_net_base','sort.credits_net_base.caption','sort.credits_net_base'],['credits_net_received','sort.credits_net_received.caption','sort.credits_net_received'],['credits_costs','sort.credits_costs'],['battle_wn8','metric.wn8'],['win_rate','sort.win_rate'],['battles','sort.battles']],
        direction:[['asc','sort.asc'],['desc','sort.desc']]
    };
    function orderKey(scope) {
        return String((state.payload || {}).account_key) + '/' + state.scope + '/' + String(scope.period_id || scope.started_at) + '/' + state.group;
    }
    function canonicalMetric(metric) {
        return metric === 'credits_gross' ? 'credits_income_received' :
            metric === 'credits_net' ? 'credits_net_received' : metric;
    }
    function creditMetric(metric) {
        return ['credits_income_base', 'credits_income_received', 'credits_net_base',
            'credits_net_received', 'credits_costs'].indexOf(canonicalMetric(metric)) >= 0;
    }
    function netCreditMetric(metric) {
        metric = canonicalMetric(metric);
        return metric === 'credits_net_base' || metric === 'credits_net_received';
    }
    function metricSeries(stats, metric) {
        metric = canonicalMetric(metric);
        // Old snapshots retain received income/net under their original keys.
        // Their absent base series stays unavailable rather than borrowing it.
        return stats[metric] || (metric === 'credits_income_received' ? stats.credits_gross :
            metric === 'credits_net_received' ? stats.credits_net : null) || {};
    }
    function getOrder(scope) {
        var options = state.orderIntent && state.orderIntent.group === state.group && sameContext(state.orderIntent.context) ?
            state.orderIntent.options : (state.nativeSession && scope.ordering && scope.ordering[state.group]) ||
            state.orders[orderKey(scope)] || (state.group === 'tiers' ? defaultTierOrder : defaultOrder);
        if (options.metric !== canonicalMetric(options.metric)) {
            options = {metric:canonicalMetric(options.metric), statistic:options.statistic,
                direction:options.direction, chronology:options.chronology};
        }
        // Retire legacy per-battle win-rate preferences even before the next
        // native snapshot; a single result has no useful percentage order.
        if (state.group === 'battles' && options.metric === 'win_rate') { return defaultOrder; }
        if (options.statistic === 'sum' && (state.group === 'battles' ||
                options.metric !== 'off' && !summableMetric(options.metric))) {
            return {metric:options.metric, statistic:'avg', direction:options.direction, chronology:options.chronology};
        }
        return options;
    }
    function summableMetric(metric) {
        return metric === 'xp_base' || metric === 'xp_received' || creditMetric(metric);
    }
    function groupSortValue(item, options) {
        var stats = item.stats || {};
        if (options.metric === 'battles') { return hasNumber(stats.observed_battles) ? stats.observed_battles : stats.battles; }
        if (options.metric === 'win_rate') { return stats.win_rate; }
        var data = metricSeries(stats, options.metric);
        return options.statistic === 'sum' && data.count === 0 ? null : data[options.statistic];
    }
    function ordered(items, options) {
        var copy = items.slice(0);
        copy.sort(function (a, b) {
            var left, right, metric = options.metric;
            if (metric !== 'off') {
                left = groupSortValue(a, options);
                right = groupSortValue(b, options);
                if (hasNumber(left) !== hasNumber(right)) { return hasNumber(left) ? -1 : 1; }
                if (hasNumber(left) && left !== right) { return options.direction === 'asc' ? left - right : right - left; }
            }
            if (metric === 'off' && state.group === 'tiers' && (options.chronology === 'tier_asc' || options.chronology === 'tier_desc')) {
                left = hasNumber(a.tier) && Math.floor(a.tier) === a.tier && a.tier >= 1 && a.tier <= 11 ? a.tier : null;
                right = hasNumber(b.tier) && Math.floor(b.tier) === b.tier && b.tier >= 1 && b.tier <= 11 ? b.tier : null;
                if ((left === null) !== (right === null)) { return left === null ? 1 : -1; }
                if (left !== right) { return options.chronology === 'tier_asc' ? left - right : right - left; }
            }
            var oldest = metric === 'off' && (options.chronology === 'oldest' || options.chronology === 'last_asc');
            var first = metric === 'off' && (options.chronology === 'oldest' || options.chronology === 'first_desc');
            left = first ? a.first_started_at : a.started_at;
            right = first ? b.first_started_at : b.started_at;
            // Individual battles have one timestamp; old previews may omit
            // the group's first timestamp and retain their former fallback.
            if (first && a.first_started_at === undefined) { left = a.started_at; }
            if (first && b.first_started_at === undefined) { right = b.started_at; }
            if (hasNumber(left) !== hasNumber(right)) { return hasNumber(left) ? -1 : 1; }
            if (hasNumber(left) && left !== right) { return oldest ? left - right : right - left; }
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
        if (control.input) { control.input.setAttribute('aria-expanded', 'false'); }
        state.openSelect = null;
        if (restoreFocus) { focusControl(control.trigger); }
    }
    function orderingUnavailable(scope, payload) {
        payload = payload || state.payload;
        return !scope || !!scope.loading || !!scope.load_error ||
            (state.scope !== 'instance' && (!!payload.loading || !!payload.load_error));
    }
    function changeOrder(field, value) {
        if (state.destroyed || !state.payload || !state.payload.scopes) { return; }
        var scope = currentScope(), current = getOrder(scope);
        if (orderingUnavailable(scope) || (field === 'chronology' && current.metric !== 'off') ||
                (field === 'chronology' && state.group === 'battles' && (value === 'first_desc' || value === 'last_asc')) ||
                (field === 'chronology' && (value === 'tier_asc' || value === 'tier_desc') && state.group !== 'tiers') ||
                (field === 'statistic' && (state.group === 'battles' || current.metric === 'battles' || current.metric === 'win_rate')) ||
                (field === 'statistic' && value === 'sum' && !summableMetric(current.metric)) ||
                (field === 'metric' && value === 'battles' && state.group !== 'vehicles' && state.group !== 'maps') ||
                (field === 'metric' && value === 'win_rate' && state.group === 'battles') ||
                !selectOptions[field] || !selectOptions[field].some(function (choice) { return choice[0] === value; })) { return; }
        cancelBattleNavigation();
        var options = {}, key;
        for (key in defaultOrder) { options[key] = current[key]; }
        options[field] = value;
        if (options.statistic === 'sum' && options.metric !== 'off' && !summableMetric(options.metric)) { options.statistic = 'avg'; }
        if (options.metric !== 'off') { rememberedMetric(scope, options.metric); }
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
    function rememberedMetric(scope, metric) {
        var values = state.lastSortMetrics || (state.lastSortMetrics = {}), key = orderKey(scope);
        if (metric && metric !== 'off') { values[key] = metric; }
        return values[key] && !(state.group === 'battles' && values[key] === 'win_rate') ? values[key] : 'xp_base';
    }
    function toggleMetricOrder() {
        if (state.destroyed || !state.payload || !state.wideFilters || orderingUnavailable(currentScope())) { return; }
        var scope = currentScope(), current = getOrder(scope);
        changeOrder('metric', current.metric === 'off' ? rememberedMetric(scope) : 'off');
    }
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
        var control = {holder:holder,trigger:trigger,label:label,menu:menu,options:[],owner:null};
        function available(option) { return option && option.style.display !== 'none' && !option.disabled && option.getAttribute('aria-disabled') !== 'true'; }
        function visibleOptions() { return control.options.filter(available); }
        function open(position) {
            if (state.destroyed || trigger.disabled || trigger.getAttribute('aria-disabled') === 'true') { return; }
            closeDatePicker(false); closeSelect(false); menu.style.display = 'block'; trigger.setAttribute('aria-expanded','true');
            if (control.input) { control.input.setAttribute('aria-expanded','true'); }
            state.openSelect = control;
            var visible = visibleOptions(), selectedIndex = 0, index;
            for (index = 0; index < visible.length; index += 1) {
                if (visible[index].getAttribute('aria-selected') === 'true') { selectedIndex = index; }
            }
            if (visible.length) { focusControl(visible[position === undefined ? selectedIndex : Math.min(position, visible.length - 1)]); }
        }
        function choose(value, owner) {
            var option = null;
            control.options.some(function (item) { if (item.getAttribute('data-value') === value) { option = item; return true; } return false; });
            if (state.destroyed || trigger.disabled || !available(option) || (owner && owner !== control.owner)) { return; }
            closeSelect(true); chooseValue(value);
        }
        function bindOption(button, option, owner) {
            button.onclick = function () { choose(option[0], owner); };
            button.onkeydown = function (event) {
                if (owner && owner !== control.owner) { return; }
                var visible = visibleOptions(), index = visible.indexOf(button);
                if (index < 0 || trigger.disabled) { return; }
                var key = event.key || event.keyCode, target = null;
                if (key === 'ArrowDown' || key === 40) { target = (index + 1) % visible.length; }
                if (key === 'ArrowUp' || key === 38) { target = (index + visible.length - 1) % visible.length; }
                if (key === 'Home' || key === 36) { target = 0; }
                if (key === 'End' || key === 35) { target = visible.length - 1; }
                if (target !== null) { event.preventDefault(); event.stopPropagation(); focusControl(visible[target]); }
                if (key === 'Enter' || key === 13 || key === ' ' || key === 32) { event.preventDefault(); choose(option[0], owner); }
                if (key === 'Tab' || key === 9) { closeSelect(true); }
            };
        }
        choices.forEach(function (option, index) {
            var button = append(menu,element('button','ss-control ss-select-option'));
            button.type = 'button'; button.setAttribute('role','option'); button.setAttribute('tabindex','-1');
            button.setAttribute('data-value',option[0]); button.setAttribute('aria-selected','false');
            append(button,element('span','ss-control-label'));
            bindOption(button, option, null);
            control.options.push(button);
        });
        control.setOwner = function (owner) { control.owner = owner; control.options.forEach(function (button, index) { bindOption(button, choices[index], owner); }); };
        control.open = open;
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
        var options = getOrder(scope), field, index, remembered = rememberedMetric(scope, options.metric);
        var statistic = document.querySelector('.ss-sort-statistic'), off = document.getElementById('ss-sort-off');
        var statisticMetric = options.metric === 'off' ? remembered : options.metric;
        var applicable = state.group !== 'battles' && statisticMetric !== 'battles' && statisticMetric !== 'win_rate';
        if (statistic) {
            // Keep its logical slot so metric changes never recenter the row.
            // Invisible, disabled controls do not suggest a statistic for rates/counts.
            statistic.style.display = '';
            statistic.style.visibility = applicable ? '' : 'hidden';
            statistic.setAttribute('aria-hidden', String(!applicable));
            if (!applicable && state.openSelect === selects.statistic) { closeSelect(false); }
        }
        if (off) {
            off.style.display = state.wideFilters ? 'flex' : 'none';
            off.disabled = orderingUnavailable(scope); off.setAttribute('aria-disabled', String(off.disabled));
            off.setAttribute('aria-pressed', String(options.metric !== 'off'));
            off.setAttribute('aria-checked', String(options.metric !== 'off'));
            off.setAttribute('aria-label', t('sort.label'));
            off.querySelector('.ss-control-label').textContent = t(options.metric === 'off' ? 'sort.off' : 'sort.on');
            off.classList[options.metric !== 'off' ? 'add' : 'remove']('is-active');
            var owner = {context:viewContext(), group:state.group};
            off.onclick = function () { if (sameContext(owner.context) && state.group === owner.group) { toggleMetricOrder(); } };
        }
        for (field in selects) {
            if (field === 'language') { continue; }
            var control = selects[field], labelKey = field === 'chronology' ? 'sort.chronology' : 'sort.' + field;
            var disabled = orderingUnavailable(scope) ||
                (field === 'chronology' && options.metric !== 'off') ||
                (field === 'statistic' && (state.group === 'battles' || options.metric === 'battles' || options.metric === 'win_rate')) ||
                (field === 'metric' && state.wideFilters && options.metric === 'off') ||
                (options.metric === 'off' && (field === 'statistic' || field === 'direction'));
            if (control.setOwner) { control.setOwner({context:viewContext(), group:state.group}); }
            // Saved chronology is available again when metric sorting is off.
            control.trigger.disabled = disabled;
            control.trigger.setAttribute('aria-disabled', String(disabled));
            control.trigger.classList[disabled ? 'add' : 'remove']('ss-select-disabled');
            control.trigger.classList[field === 'metric' && options.metric === 'off' && !state.wideFilters ? 'add' : 'remove']('ss-sort-off-choice');
            control.trigger.setAttribute('aria-label',t(labelKey));
            control.menu.setAttribute('aria-label',t(labelKey));
            for (index = 0; index < selectOptions[field].length; index += 1) {
                var choice = selectOptions[field][index], caption = t(choice[1]), description = t(choice[2] || choice[1]);
                control.options[index].classList[field === 'metric' && choice[0] === 'off' ? 'add' : 'remove']('ss-sort-off-choice');
                if (field === 'chronology' && state.group === 'battles' && (choice[0] === 'newest' || choice[0] === 'oldest')) {
                    caption = t(choice[0] === 'newest' ? 'sort.newest' : 'sort.oldest'); description = caption;
                }
                var selectedValue = field === 'metric' && state.wideFilters && options.metric === 'off' ? remembered : options[field];
                control.options[index].style.display = (field === 'chronology' && ((choice[0] === 'tier_asc' || choice[0] === 'tier_desc') && state.group !== 'tiers' ||
                     (choice[0] === 'first_desc' || choice[0] === 'last_asc') && state.group === 'battles')) || field === 'metric' &&
                    ((choice[0] === 'off' && state.wideFilters) ||
                     (choice[0] === 'battles' && state.group !== 'vehicles' && state.group !== 'maps') ||
                     (choice[0] === 'win_rate' && state.group === 'battles')) ||
                    field === 'statistic' && choice[0] === 'sum' &&
                    (state.group === 'battles' || !summableMetric(statisticMetric)) ? 'none' : '';
                control.options[index].querySelector('.ss-control-label').textContent = caption;
                control.options[index].setAttribute('aria-label', description); control.options[index].title = description;
                control.options[index].setAttribute('aria-selected',String(choice[0] === selectedValue));
                if (choice[0] === selectedValue) {
                    control.label.textContent = caption; control.trigger.setAttribute('title',t(labelKey) + ': ' + description);
                }
            }
        }
        renderFilterActivity(scope);
    }
    function renderFilterActivity(scope) {
        var slot = document.getElementById('ss-filter-loading');
        if (!slot) { return; }
        var payload = state.payload, failed = !!state.actionError || !!(scope && scope.load_error) ||
            (state.scope !== 'instance' && !!(payload && payload.load_error));
        var busy = !!payload && !state.destroyed && !failed &&
            (orderingUnavailable(scope) || !!state.orderIntent || !!(state.feed && state.feed.pending));
        // Keep one synchronous owner: errors, acknowledgements and teardown
        // clear the scrim without retaining another timer or layout callback.
        slot.style.visibility = busy ? 'visible' : 'hidden';
        slot.setAttribute('aria-hidden', String(!busy)); slot.setAttribute('aria-label', t('page.loading'));
        var label = slot.querySelector('.ss-filter-loading-label');
        if (label) { label.textContent = t('page.loading'); }
        root.classList[busy ? 'add' : 'remove']('ss-is-loading');
        root.setAttribute('aria-busy', String(busy));
        document.getElementById('ss-sorting').setAttribute('aria-busy', String(busy));
    }
    function filterLayoutWidth() {
        // Use the requested, viewport-capped panel width. Native rectangles can
        // still describe the preceding frame while Wulf resizes its surface.
        // Reserve the widest shipped scroll padding (12 + 24) and the two
        // frame borders. The owned native scrollbar is width zero. Do not
        // derive its gutter from potentially mismatched native rectangles.
        var width = resizePanelDimensions().width - 38;
        return hasNumber(width) && width > 1 ? Math.floor(width + 0.01) : 0;
    }
    function cancelFilterLayout() {
        state.filterLayoutToken = (state.filterLayoutToken || 0) + 1;
        state.filterLayoutQueued = false;
    }
    function applyFilterLayout(controls, width, wide) {
        var compact = width < 340, changed = state.wideFilters !== wide;
        if (controls.classList.contains('ss-filters-wide') !== wide) { controls.classList[wide ? 'add' : 'remove']('ss-filters-wide'); }
        if (controls.classList.contains('ss-filters-wrapped') === wide) { controls.classList[wide ? 'remove' : 'add']('ss-filters-wrapped'); }
        if (controls.classList.contains('ss-filters-compact') !== compact) { controls.classList[compact ? 'add' : 'remove']('ss-filters-compact'); }
        var mode = wide ? 'wide' : 'wrapped';
        if (controls.getAttribute('data-filter-layout') !== mode) { controls.setAttribute('data-filter-layout', mode); }
        if (controls.getAttribute('data-filter-width') !== String(width)) { controls.setAttribute('data-filter-width', String(width)); }
        state.wideFilters = wide;
        var off = document.getElementById('ss-sort-off'), display = wide ? 'flex' : 'none';
        if (off && off.style.display !== display) { off.style.display = display; }
        if (changed) { closeSelect(false); renderSelects(currentScope()); }
    }
    function layoutFilterControls(flush) {
        var controls = document.getElementById('ss-list-controls');
        if (state.destroyed || !controls || !state.payload || !currentScope()) { return; }
        var width = filterLayoutWidth();
        if (!width) { return; }
        // One invariant row budget, including Statistic even when hidden:
        // metadata150 + pagination340 + sorting357 + gaps16 + activity28 +
        // slack12 = 903rem. Neither the current metric nor a trial CSS layout
        // can change the breakpoint. CSS reserves the same metadata slot.
        var wide = width >= 903;
        if (state.filterLayoutWidth !== width) {
            state.filterLayoutWidth = width;
            state.filterLayoutDue = Date.now() + 120;
            state.filterLayoutFrames = 0;
        }
        if (state.wideFilters === undefined || !wide || state.wideFilters === wide || flush === true) {
            cancelFilterLayout(); applyFilterLayout(controls, width, wide); return;
        }
        // Falling back never leaves controls outside a shrinking window.
        // Promotion waits for resize input to settle; repeated measurements at
        // the same width neither restart this work nor touch the visible DOM.
        if (state.resize) { cancelFilterLayout(); return; }
        if (state.filterLayoutQueued) { return; }
        state.filterLayoutQueued = true;
        var ticket = state.filterLayoutToken = (state.filterLayoutToken || 0) + 1;
        function settle() {
            if (state.destroyed || ticket !== state.filterLayoutToken) { return; }
            var current = filterLayoutWidth();
            if (current !== state.filterLayoutWidth) {
                state.filterLayoutWidth = current; state.filterLayoutDue = Date.now() + 120; state.filterLayoutFrames = 0;
            }
            if (current < 903 || state.resize) { state.filterLayoutQueued = false; layoutFilterControls(); return; }
            state.filterLayoutFrames += 1;
            if (Date.now() >= state.filterLayoutDue || state.filterLayoutFrames >= 8 ||
                    typeof window.requestAnimationFrame !== 'function') {
                state.filterLayoutQueued = false; applyFilterLayout(controls, current, true); queueResize(); return;
            }
            window.requestAnimationFrame(settle);
        }
        if (typeof window.requestAnimationFrame === 'function') { window.requestAnimationFrame(settle); }
        else { state.filterLayoutQueued = false; applyFilterLayout(controls, width, wide); }
    }
    function outsideSelect(event) {
        if (!state.openSelect) { return; }
        var node = event.target, holder = state.openSelect.holder || state.openSelect.trigger.parentNode;
        while (node) { if (node === holder) { return; } node = node.parentNode; }
        closeSelect(false);
    }
    ['chronology','statistic','metric','direction','language'].forEach(function (field) { selects[field] = makeSelect(field); });

    function scopeName() {
        return state.scope === 'manual' && state.payload.scopes.timeline ? 'timeline' : state.scope;
    }
    function currentScope() { return state.payload.scopes[scopeName()]; }

    function dateLocale() {
        var source = state.payload && state.payload.localization && state.payload.localization.date_settings || {};
        var fallback = /^\{0\}([./])\{1\}\1\{2\}/.exec(t('format.date'));
        var weekdays = t('timeline.calendar_weekdays').split('|');
        return {order:/^(DMY|MDY|YMD)$/.test(source.order) ? source.order : 'DMY',
            separator:/^[./-]$/.test(source.separator) ? source.separator : fallback ? fallback[1] : '.',
            first:typeof source.first_weekday === 'number' && source.first_weekday >= 0 && source.first_weekday <= 6 ? source.first_weekday : 1,
            hour12:source.hour12 === true, periods:source.periods && source.periods.length === 2 ? source.periods : ['AM', 'PM'],
            weekdays:[weekdays[6]].concat(weekdays.slice(0, 6)),
            months:t('timeline.calendar_months').split('|')};
    }
    function customDateSeparator() {
        return dateLocale().separator;
    }
    function customDateValue(value, format) {
        format = format || dateLocale();
        var separator = '\\' + format.separator, widths = format.order === 'YMD' ? [4, 2, 2] : [2, 2, 4];
        var pattern = new RegExp('^(\\d{' + widths[0] + '})' + separator + '(\\d{' + widths[1] + '})' + separator +
            '(\\d{' + widths[2] + '})(?:[ ](\\d{2}):(\\d{2})(?:[ ](.+))?)?$');
        var parts = pattern.exec(String(value).trim());
        if (!parts) { return null; }
        var date = {}, hour = +(parts[4] || 0), minute = +(parts[5] || 0);
        for (var index = 0; index < 3; index += 1) { date[format.order.charAt(index)] = +parts[index + 1]; }
        if (parts[6]) {
            var period = String(parts[6]).toLocaleLowerCase(), am = format.periods[0].toLocaleLowerCase(), pm = format.periods[1].toLocaleLowerCase();
            if (!format.hour12 || hour < 1 || hour > 12 || (period !== am && period !== pm)) { return null; }
            hour = hour % 12 + (period === pm ? 12 : 0);
        } else if (format.hour12 && parts[4]) { return null; }
        return customDateParts(date.Y, date.M, date.D, hour, minute);
    }
    function customDateParts(year, month, day, hour, minute) {
        if (year < 1970 || year > 9999 || month < 1 || month > 12 || day < 1 || day > 31 || hour < 0 || hour > 23 || minute < 0 || minute > 59) { return null; }
        var parsed = new Date(year, month - 1, day, hour, minute, 0, 0);
        if (parsed.getFullYear() !== year || parsed.getMonth() !== month - 1 || parsed.getDate() !== day ||
                parsed.getHours() !== hour || parsed.getMinutes() !== minute || !hasNumber(parsed.getTime()) || parsed.getTime() < 0) { return null; }
        return parsed.getTime() / 1000;
    }
    function datePad(number) { return number < 10 ? '0' + number : String(number); }
    function customDateText(timestamp, format) {
        format = format || dateLocale();
        var value = new Date((hasNumber(timestamp) ? timestamp : Date.now() / 1000) * 1000);
        var parts = {D:datePad(value.getDate()), M:datePad(value.getMonth() + 1), Y:String(value.getFullYear())}, output = [];
        for (var index = 0; index < 3; index += 1) { output.push(parts[format.order.charAt(index)]); }
        return output.join(format.separator) + ' ' + datePad(format.hour12 ? value.getHours() % 12 || 12 : value.getHours()) + ':' + datePad(value.getMinutes()) +
            (format.hour12 ? ' ' + format.periods[value.getHours() < 12 ? 0 : 1] : '');
    }
    function customDatePlaceholder() {
        var format = dateLocale(), parts = {D:'dd', M:'mm', Y:'yyyy'}, output = [];
        for (var index = 0; index < 3; index += 1) { output.push(parts[format.order.charAt(index)]); }
        return output.join(format.separator) + ' ' + (format.hour12 ? 'hh:mm ' + format.periods[0] : 'HH:mm');
    }
    function customDateMask(value, format) {
        format = format || dateLocale();
        var text = String(value), digits = text.replace(/[^0-9]/g, '').slice(0, 12), output = '';
        var widths = format.order === 'YMD' ? [4, 6] : [2, 4];
        for (var index = 0; index < digits.length; index += 1) {
            if (index === widths[0] || index === widths[1]) { output += format.separator; }
            if (index === 8) { output += ' '; }
            if (index === 10) { output += ':'; }
            output += digits.charAt(index);
        }
        if (format.hour12) {
            var suffix = text.replace(/^[0-9./:\- ]*/, '').trim(), normalized = suffix.replace(/[./:\- ]/g, '').toLocaleLowerCase();
            var am = format.periods[0].replace(/[./:\- ]/g, '').toLocaleLowerCase(), pm = format.periods[1].replace(/[./:\- ]/g, '').toLocaleLowerCase();
            var shared = 0; while (shared < am.length && shared < pm.length && am.charAt(shared) === pm.charAt(shared)) { shared += 1; }
            if (normalized && (am.indexOf(normalized) === 0 || pm.indexOf(normalized) === 0) && normalized !== am && normalized !== pm) {
                // Keep unfinished localized day periods editable, including
                // labels whose first characters are shared (e.g. 오전/오후).
            } else if (normalized.indexOf(pm.slice(0, shared + 1)) === 0) { suffix = format.periods[1]; }
            else if (normalized.indexOf(am.slice(0, shared + 1)) === 0) { suffix = format.periods[0]; }
            if (suffix || digits.length === 12) { output += ' ' + (suffix || format.periods[0]); }
        }
        return output;
    }
    function dateCaret(value, digits) {
        var index = 0;
        while (index < value.length && digits > 0) { if (/[0-9]/.test(value.charAt(index))) { digits -= 1; } index += 1; }
        return index;
    }
    function maskDateInput(input) {
        var caret = typeof input.selectionStart === 'number' ? input.selectionStart : input.value.length;
        var prefix = input.value.slice(0, caret), digits = prefix.replace(/[^0-9]/g, '').length;
        var suffixChars = prefix.replace(/[0-9./:\- ]/g, '').length;
        input.value = customDateMask(input.value);
        if (typeof input.setSelectionRange === 'function') {
            try {
                var next = dateCaret(input.value, digits);
                if (dateLocale().hour12 && suffixChars) {
                    while (next < input.value.length && suffixChars > 0) { if (/[^0-9./:\- ]/.test(input.value.charAt(next))) { suffixChars -= 1; } next += 1; }
                }
                input.setSelectionRange(next, next);
            } catch (ignored) { /* Native text input remains usable. */ }
        }
    }
    function deleteDateSeparator(input, event) {
        var key = event.key || event.keyCode, at = input.selectionStart;
        if ((key !== 'Backspace' && key !== 8 && key !== 'Delete' && key !== 46) ||
                typeof at !== 'number' || at !== input.selectionEnd) { return; }
        var back = key === 'Backspace' || key === 8, next = back ? at - 1 : at;
        var lastDigit = input.value.replace(/[^0-9]*$/, '').length - 1;
        if (next < 0 || next >= lastDigit || !/[./:\- ]/.test(input.value.charAt(next))) { return; }
        while (next >= 0 && next < input.value.length && !/[0-9]/.test(input.value.charAt(next))) { next += back ? -1 : 1; }
        if (next < 0 || next >= input.value.length) { return; }
        event.preventDefault();
        var prefix = input.value.slice(0, next), digits = prefix.replace(/[^0-9]/g, '').length;
        input.value = customDateMask(prefix + input.value.slice(next + 1));
        if (typeof input.setSelectionRange === 'function') {
            try { var caret = dateCaret(input.value, digits); input.setSelectionRange(caret, caret); } catch (ignored) { /* Native text input remains usable. */ }
        }
        if (input.oninput) { input.oninput({}); }
    }
    function timelineError(field, message) {
        var input = document.getElementById('ss-custom-date-' + field);
        var error = document.getElementById('ss-custom-date-error-' + field);
        if (input) { input.setAttribute('aria-invalid', 'true'); }
        if (error) { error.textContent = message; error.style.display = 'block'; }
        setActionError(message);
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
                else if (timestamp > Date.now() / 1000) { timelineError(side, t('timeline.custom_future')); valid = false; }
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
        return invoke('timeline_range', args);
    }
    function timelineDateBound(timeline, field) {
        var draft = state.customDates[field], point = timeline[field + '_point'];
        if (draft) { return customDateValue(draft.value); }
        if (point === '__custom__') { return timeline[field + '_date']; }
        var points = timeline.time_points || [];
        for (var index = 0; index < points.length; index += 1) { if (points[index][0] === point) { return points[index][1]; } }
        return null;
    }
    function customDateBounds(timeline, field) {
        var minimum = customDateParts(2010, 1, 1, 0, 0), maximum = Math.floor(Date.now() / 60000) * 60;
        var opposite = timelineDateBound(timeline, field === 'from' ? 'to' : 'from');
        if (hasNumber(opposite)) {
            if (field === 'from') { maximum = Math.min(maximum, Math.ceil(opposite / 60) * 60 - 60); }
            else { minimum = Math.max(minimum, Math.floor(opposite / 60) * 60 + 60); }
        }
        return {minimum:minimum, maximum:maximum};
    }
    function boundedDateTime(year, month, day, hour, minute, limits) {
        var timestamp = customDateParts(year, month, day, hour, minute);
        if (timestamp === null) { return null; }
        var start = new Date(year, month - 1, day).getTime() / 1000;
        var end = new Date(year, month - 1, day + 1).getTime() / 1000 - 60;
        var minimum = Math.max(start, limits.minimum), maximum = Math.min(end, limits.maximum);
        return minimum <= maximum ? Math.max(minimum, Math.min(maximum, timestamp)) : null;
    }
    var datePicker = null;
    function closeDatePicker(restoreFocus) {
        var picker = datePicker;
        if (!picker) { return; }
        if (helpTarget && picker.node.contains(helpTarget)) { hideHelp(); }
        datePicker = null;
        picker.button.setAttribute('aria-expanded', 'false');
        if (picker.removeDrag) { picker.removeDrag(); }
        if (picker.node.parentNode) { picker.node.parentNode.removeChild(picker.node); }
        if (restoreFocus && root.contains(picker.input)) { focusControl(picker.input); }
    }
    function positionDatePicker() {
        var picker = datePicker;
        if (!picker || state.destroyed) { return; }
        var bounds = root.getBoundingClientRect(), target = picker.holder.getBoundingClientRect(), scale = state.nativeScale || 1;
        var gap = 8 * scale, width = Math.max(1, Math.min(286 * scale, bounds.width - 2 * gap));
        picker.node.style.width = width + 'px';
        picker.node.style.maxHeight = Math.max(1, bounds.height - 2 * gap) + 'px';
        var box = picker.node.getBoundingClientRect(), height = box.height > 1 ? box.height : Math.min(350 * scale, bounds.height - 2 * gap);
        var left = target.right - bounds.left + gap, top = target.top - bounds.top;
        if (left + width > bounds.width - gap) { left = target.left - bounds.left - width - gap; }
        if (left < gap) { left = target.left - bounds.left; top = target.bottom - bounds.top + gap; }
        picker.node.style.left = Math.max(gap, Math.min(left, bounds.width - width - gap)) + 'px';
        picker.node.style.top = Math.max(gap, Math.min(top, bounds.height - height - gap)) + 'px';
    }
    function outsideDatePicker(event) {
        if (datePicker && !datePicker.node.contains(event.target) && !datePicker.button.contains(event.target)) { closeDatePicker(false); }
    }
    function datePickerKey(event) {
        if (!datePicker || (event.key !== 'Escape' && event.keyCode !== 27)) { return; }
        event.preventDefault(); event.stopPropagation(); closeDatePicker(true);
    }
    function openDatePicker(field, holder, input, button, timeline, account) {
        if (state.destroyed || !state.payload || state.payload.account_key !== account || !root.contains(input)) { return; }
        if (datePicker && datePicker.input === input) { closeDatePicker(true); return; }
        closeSelect(false); closeDatePicker(false);
        var timestamp = customDateValue(input.value), date = new Date((timestamp === null ? Date.now() / 1000 : timestamp) * 1000);
        var format = dateLocale(), lastYear = new Date().getFullYear(), limits = customDateBounds(timeline, field);
        if (limits.minimum <= limits.maximum) { date = new Date(Math.max(limits.minimum, Math.min(limits.maximum, date.getTime() / 1000)) * 1000); }
        var picker = {field:field, holder:holder, input:input, button:button,
            node:append(root, element('div', 'ss-date-picker')), year:Math.max(2010, Math.min(lastYear, date.getFullYear())), month:date.getMonth() + 1, day:date.getDate(),
            hour:date.getHours(), minute:date.getMinutes(), mode:'days', clock:'hours'};
        picker.day = Math.min(picker.day, new Date(picker.year, picker.month, 0).getDate());
        datePicker = picker;
        picker.node.id = 'ss-date-picker-' + field; picker.node.setAttribute('role', 'dialog');
        picker.node.setAttribute('aria-modal', 'true'); picker.node.setAttribute('aria-label', t('timeline.' + field) + ' · ' + t('timeline.calendar'));
        button.setAttribute('aria-expanded', 'true');
        function live() { return datePicker === picker && !state.destroyed && state.payload && state.payload.account_key === account && root.contains(input); }
        function action(parent, className, label, click) {
            var result = append(parent, element('button', 'ss-control ss-button ' + className)); result.type = 'button';
            result.setAttribute('aria-label', label); result.title = label;
            append(result, element('span', 'ss-control-label', label)); result.onclick = function () { if (live() && !result.disabled) { click(); } }; return result;
        }
        function unavailable(node, disabled) {
            node.disabled = !!disabled;
            node.setAttribute('aria-disabled', String(node.disabled));
            if (node.disabled) { node.classList.add('ss-date-unavailable'); }
            else { node.classList.remove('ss-date-unavailable'); }
        }
        var heading = append(picker.node, element('div', 'ss-date-picker-heading'));
        var previous = action(heading, 'ss-date-month-arrow ss-date-month-previous', t('timeline.calendar_previous'), function () { moveMonth(-1); });
        append(previous, element('span', 'ss-date-chevron')).setAttribute('aria-hidden', 'true');
        var title = append(heading, element('div', 'ss-date-picker-title')); title.setAttribute('aria-live', 'polite');
        var monthTitle = action(title, 'ss-date-heading-month', '', function () { picker.mode = picker.mode === 'months' ? 'days' : 'months'; draw(); });
        append(title, element('span', '', ' '));
        var yearTitle = action(title, 'ss-date-heading-year', '', function () { picker.mode = picker.mode === 'years' ? 'days' : 'years'; draw(); });
        monthTitle.setAttribute('data-date-part', 'month'); yearTitle.setAttribute('data-date-part', 'year');
        var next = action(heading, 'ss-date-month-arrow ss-date-month-next', t('timeline.calendar_next'), function () { moveMonth(1); });
        append(next, element('span', 'ss-date-chevron')).setAttribute('aria-hidden', 'true');
        var body = append(picker.node, element('div', 'ss-date-picker-body'));
        var time = append(picker.node, element('div', 'ss-date-time'));
        var hour = action(time, 'ss-date-time-part', '', function () { picker.clock = 'hours'; draw(); focusClock(); });
        hour.setAttribute('data-date-part', 'hour');
        append(time, element('span', 'ss-date-time-colon', ':'));
        var minute = action(time, 'ss-date-time-part', '', function () { picker.clock = 'minutes'; draw(); focusClock(); });
        minute.setAttribute('data-date-part', 'minute');
        var periods = append(time, element('div', 'ss-date-periods'));
        var periodButtons = [];
        format.periods.forEach(function (label, index) {
            periodButtons.push(action(periods, 'ss-date-period', label, function () { choosePeriod(index); draw(); }));
        });
        periods.style.display = format.hour12 ? 'flex' : 'none';
        var info = append(time, element('button', 'ss-info-button ss-date-clock-info')); info.type = 'button';
        info.setAttribute('aria-label', t('timeline.calendar_clock_help')); info.setAttribute('data-ss-help', t('timeline.calendar_clock_help'));
        info.setAttribute('aria-controls', helpTooltip.id); info.setAttribute('aria-expanded', 'false');
        append(info, element('span', 'ss-info-symbol', 'i')).setAttribute('aria-hidden', 'true');
        var clockBody = append(picker.node, element('div', 'ss-date-clock-container'));
        var error = append(picker.node, element('div', 'ss-custom-date-error ss-date-picker-error')); error.setAttribute('role', 'alert'); error.style.display = 'none';
        var footer = append(picker.node, element('div', 'ss-date-picker-actions'));
        function fail(message) { error.textContent = message; error.style.display = 'block'; timelineError(field, message); }
        function focusDay() { var selected = body.querySelector('[data-day="' + picker.day + '"]'); if (selected) { focusControl(selected); } }
        function focusClock() { var face = clockBody.querySelector('.ss-date-clock'); if (face) { focusControl(face); } }
        function validTime(timestamp) { return timestamp !== null && timestamp >= limits.minimum && timestamp <= limits.maximum; }
        function available(year, month, day) {
            var start = new Date(year, month === undefined ? 0 : month - 1, day || 1).getTime() / 1000;
            var end = new Date(year + (month === undefined ? 1 : 0), month === undefined ? 0 : month - 1 + (day === undefined ? 1 : 0), day === undefined ? 1 : day + 1).getTime() / 1000 - 60;
            return Math.max(start, limits.minimum) <= Math.min(end, limits.maximum);
        }
        function hourMinute(hour, minute) { return customDateParts(picker.year, picker.month, picker.day, hour, minute); }
        var minuteCache = {}, minuteCacheKey = '';
        function allowedMinutes(hour) {
            var key = [picker.year, picker.month, picker.day, limits.minimum, limits.maximum].join(':');
            if (key !== minuteCacheKey) { minuteCache = {}; minuteCacheKey = key; }
            if (!minuteCache[hour]) {
                var values = [];
                for (var minute = 0; minute < 60; minute += 1) { if (validTime(hourMinute(hour, minute))) { values.push(minute); } }
                minuteCache[hour] = values;
            }
            return minuteCache[hour];
        }
        function hourAvailable(hour) {
            return allowedMinutes(hour).length > 0;
        }
        function chooseHour(hour) {
            if (!hourAvailable(hour)) { return false; }
            var selected = picker.minute, distance = 60, values = allowedMinutes(hour);
            for (var index = 0; index < values.length; index += 1) {
                var minute = values[index];
                if (Math.abs(minute - picker.minute) < distance) { selected = minute; distance = Math.abs(minute - picker.minute); }
            }
            picker.hour = hour; picker.minute = selected; return true;
        }
        function choosePeriod(period) {
            var desired = picker.hour % 12 + period * 12, selected = null, distance = 24;
            for (var hour = period * 12; hour < period * 12 + 12; hour += 1) {
                if (hourAvailable(hour) && Math.abs(hour - desired) < distance) { selected = hour; distance = Math.abs(hour - desired); }
            }
            if (selected !== null) { chooseHour(selected); }
        }
        function setDate(value, clamp) {
            limits = customDateBounds(timeline, field);
            var year = value.getFullYear(), month = value.getMonth() + 1, day = value.getDate();
            if (year < 2010 || year > lastYear || !available(year, month, clamp ? undefined : day)) { return; }
            value = new Date(year, month - 1, day, picker.hour, picker.minute);
            if (clamp) { value = new Date(Math.max(limits.minimum, Math.min(limits.maximum, value.getTime() / 1000)) * 1000); }
            // Retain the chosen day while moving a stale clock to its nearest
            // permitted minute. Today must clamp to now, not to midnight.
            var timestamp = boundedDateTime(value.getFullYear(), value.getMonth() + 1, value.getDate(), value.getHours(), value.getMinutes(), limits);
            if (timestamp === null) { return; }
            value = new Date(timestamp * 1000);
            picker.year = value.getFullYear(); picker.month = value.getMonth() + 1; picker.day = value.getDate();
            picker.hour = value.getHours(); picker.minute = value.getMinutes();
            draw(); focusDay();
        }
        function moveMonth(direction) {
            if (!live()) { return; }
            var value = new Date(picker.year, picker.month - 1 + direction, 1);
            value.setDate(Math.min(picker.day, new Date(value.getFullYear(), value.getMonth() + 1, 0).getDate())); setDate(value, true);
        }
        function chooseYear(year) {
            picker.year = year; picker.day = Math.min(picker.day, new Date(year, picker.month, 0).getDate());
            picker.mode = 'months'; draw(); focusControl(body.querySelector('[aria-selected="true"]'));
        }
        function drawDays() {
            var grid = append(body, element('div', 'ss-date-grid')); grid.setAttribute('role', 'grid'); grid.setAttribute('aria-label', t('timeline.calendar'));
            var headers = append(grid, element('div', 'ss-date-week')); headers.setAttribute('role', 'row');
            for (var weekday = 0; weekday < 7; weekday += 1) {
                append(headers, element('span', 'ss-date-weekday', format.weekdays[(weekday + format.first) % 7])).setAttribute('role', 'columnheader');
            }
            var offset = (new Date(picker.year, picker.month - 1, 1).getDay() - format.first + 7) % 7;
            var count = new Date(picker.year, picker.month, 0).getDate(), row, cells = Math.ceil((offset + count) / 7) * 7;
            for (var index = 0; index < cells; index += 1) {
                if (index % 7 === 0) { row = append(grid, element('div', 'ss-date-week')); row.setAttribute('role', 'row'); }
                var day = index - offset + 1;
                if (day < 1 || day > count) { var blank = append(row, element('span', 'ss-date-day ss-date-blank')); blank.setAttribute('aria-hidden', 'true'); continue; }
                (function (day) {
                    var chosen = day === picker.day;
                    var label = customDateText(new Date(picker.year, picker.month - 1, day).getTime() / 1000, format).split(' ')[0];
                    var node = action(row, 'ss-date-day', label, function () { setDate(new Date(picker.year, picker.month - 1, day)); });
                    node.querySelector('.ss-control-label').textContent = String(day);
                    unavailable(node, !available(picker.year, picker.month, day));
                    node.setAttribute('role', 'gridcell'); node.setAttribute('data-day', String(day)); node.setAttribute('tabindex', chosen ? '0' : '-1'); node.setAttribute('aria-selected', String(chosen));
                    node.onkeydown = function (event) {
                        var key = event.key || event.keyCode, delta = key === 'ArrowLeft' || key === 37 ? -1 : key === 'ArrowRight' || key === 39 ? 1 :
                            key === 'ArrowUp' || key === 38 ? -7 : key === 'ArrowDown' || key === 40 ? 7 : null;
                        if (delta !== null) { event.preventDefault(); event.stopPropagation(); setDate(new Date(picker.year, picker.month - 1, day + delta)); }
                        if (key === 'PageUp' || key === 33 || key === 'PageDown' || key === 34) { event.preventDefault(); event.stopPropagation(); moveMonth(key === 'PageUp' || key === 33 ? -1 : 1); }
                        if (key === 'Home' || key === 36 || key === 'End' || key === 35) { event.preventDefault(); event.stopPropagation(); setDate(new Date(picker.year, picker.month - 1, key === 'Home' || key === 36 ? 1 : count), true); }
                    };
                }(day));
            }
        }
        function drawOptions(kind) {
            var grid = append(body, element('div', 'ss-date-options ss-date-' + kind)); grid.setAttribute('role', 'grid'); grid.setAttribute('aria-label', t('timeline.calendar_' + (kind === 'years' ? 'year' : 'month')));
            function option(value, label) {
                var chosen = value === (kind === 'years' ? picker.year : picker.month);
                var node = action(grid, 'ss-date-option', label, function () {
                    if (kind === 'years') { chooseYear(value); }
                    else { picker.mode = 'days'; setDate(new Date(picker.year, value - 1, Math.min(picker.day, new Date(picker.year, value, 0).getDate())), true); }
                });
                unavailable(node, kind === 'years' ? !available(value) : !available(picker.year, value));
                node.setAttribute('role', 'gridcell'); node.setAttribute('data-' + (kind === 'years' ? 'year' : 'month'), String(value)); node.setAttribute('aria-selected', String(chosen));
                node.onkeydown = function (event) {
                    var key = event.key || event.keyCode, delta = key === 'ArrowLeft' || key === 37 ? -1 : key === 'ArrowRight' || key === 39 ? 1 : key === 'ArrowUp' || key === 38 ? -3 : key === 'ArrowDown' || key === 40 ? 3 : null;
                    if (delta !== null) { var options = grid.querySelectorAll('button'), index = Array.prototype.indexOf.call(options, node), target = options[index + delta];
                        event.preventDefault(); event.stopPropagation(); while (target && target.disabled) { index += delta; target = options[index + delta]; } if (target) { focusControl(target); } }
                };
            }
            if (kind === 'years') { for (var year = lastYear; year >= 2010; year -= 1) { option(year, String(year)); } }
            else { format.months.forEach(function (label, index) { option(index + 1, label); }); }
        }
        function setClock(value) {
            if (picker.clock === 'hours') { if (!chooseHour(format.hour12 ? value % 12 + (picker.hour >= 12 ? 12 : 0) : value)) { return; } }
            else { if (!validTime(hourMinute(picker.hour, value))) { return; } picker.minute = value; }
            updateTime(); updateHand();
        }
        function updateHand() {
            var face = clockBody.querySelector('.ss-date-clock'), hand = clockBody.querySelector('.ss-date-clock-hand');
            if (!face || !hand) { return; }
            var hours = picker.clock === 'hours', value = hours ? picker.hour : picker.minute;
            var angle = (hours ? value % 12 * 30 : value * 6);
            var inner = hours && !format.hour12 && value >= 12;
            hand.style.height = (inner ? 25 : 38) + '%'; hand.style.transform = 'rotate(' + angle + 'deg)';
            face.setAttribute('aria-valuenow', String(hours && format.hour12 ? value % 12 || 12 : value));
            face.setAttribute('aria-valuetext', datePad(format.hour12 ? picker.hour % 12 || 12 : picker.hour) + ':' + datePad(picker.minute) + (format.hour12 ? ' ' + format.periods[picker.hour < 12 ? 0 : 1] : ''));
            var numbers = face.querySelectorAll('[data-clock-value]');
            for (var index = 0; index < numbers.length; index += 1) {
                var number = numbers[index], selected = +number.getAttribute('data-clock-value') === (hours && format.hour12 ? value % 12 || 12 : value);
                number.setAttribute('aria-pressed', String(selected));
                var clockValue = +number.getAttribute('data-clock-value');
                unavailable(number, hours ? !hourAvailable(format.hour12 ? clockValue % 12 + (picker.hour >= 12 ? 12 : 0) : clockValue) : !validTime(hourMinute(picker.hour, clockValue)));
            }
        }
        function clockPoint(event) {
            if (!live()) { return; }
            var face = clockBody.querySelector('.ss-date-clock'); if (!face) { return; }
            var rect = face.getBoundingClientRect(), x = event.clientX - rect.left - rect.width / 2, y = event.clientY - rect.top - rect.height / 2;
            var angle = (Math.atan2(x, -y) * 180 / Math.PI + 360) % 360;
            if (picker.clock === 'minutes') { setClock(Math.round(angle / 6) % 60); }
            else { var number = Math.round(angle / 30) % 12;
                if (format.hour12) { setClock(number || 12); }
                else { var inner = Math.sqrt(x * x + y * y) < rect.width * 0.32; setClock(inner ? number + 12 : number); } }
        }
        function drawClock() {
            var hours = picker.clock === 'hours';
            var face = append(clockBody, element('div', 'ss-date-clock')); face.setAttribute('role', 'slider'); face.setAttribute('tabindex', '0');
            face.setAttribute('aria-label', t('timeline.calendar_' + (hours ? 'hour' : 'minute'))); face.title = t('timeline.calendar_clock_help');
            face.setAttribute('aria-valuemin', hours && format.hour12 ? '1' : '0'); face.setAttribute('aria-valuemax', hours ? format.hour12 ? '12' : '23' : '59');
            var hand = append(face, element('span', 'ss-date-clock-hand')); hand.setAttribute('aria-hidden', 'true');
            append(face, element('span', 'ss-date-clock-pivot')).setAttribute('aria-hidden', 'true');
            function number(value, angle, radius, label) {
                var node = action(face, 'ss-date-clock-number' + (radius === 25 ? ' ss-date-clock-inner' : ''), label, function () {
                    setClock(value); if (hours) { picker.clock = 'minutes'; draw(); focusClock(); }
                });
                node.setAttribute('data-clock-value', String(value)); node.setAttribute('aria-label', t('timeline.calendar_' + (hours ? 'hour' : 'minute')) + ': ' + label); node.setAttribute('tabindex', '-1');
                var radians = angle * Math.PI / 180; node.style.left = (50 + radius * Math.sin(radians)) + '%'; node.style.top = (50 - radius * Math.cos(radians)) + '%';
            }
            for (var index = 0; index < 12; index += 1) {
                if (hours) { var outer = index || (format.hour12 ? 12 : 0); number(outer, index * 30, 40, outer === 0 ? '00' : String(outer)); if (!format.hour12) { number(index + 12, index * 30, 25, datePad(index + 12)); } }
                else { number(index * 5, index * 30, 40, datePad(index * 5)); }
            }
            face.onmousedown = function (event) {
                if (event.button !== 0) { return; }
                var target = event.target; while (target && target !== face) { if (target.tagName === 'BUTTON') { return; } target = target.parentNode; }
                event.preventDefault(); focusControl(face); picker.dragging = true; clockPoint(event);
            };
            face.onkeydown = function (event) {
                var key = event.key || event.keyCode, delta = key === 'ArrowLeft' || key === 37 || key === 'ArrowDown' || key === 40 ? -1 : key === 'ArrowRight' || key === 39 || key === 'ArrowUp' || key === 38 ? 1 : null;
                var value = hours ? picker.hour : picker.minute, max = hours ? 24 : 60;
                if (delta !== null) {
                    event.preventDefault(); event.stopPropagation();
                    for (var step = 1; step < max; step += 1) {
                        var nextValue = (value + delta * step + max * step) % max;
                        if (hours ? hourAvailable(nextValue) : validTime(hourMinute(picker.hour, nextValue))) {
                            if (hours) { chooseHour(nextValue); updateTime(); updateHand(); } else { setClock(nextValue); } break;
                        }
                    }
                }
                if (key === 'Home' || key === 36 || key === 'End' || key === 35) {
                    event.preventDefault(); event.stopPropagation();
                    var first = key === 'Home' || key === 36;
                    for (var index = 0; index < max; index += 1) {
                        var endpoint = first ? index : max - index - 1;
                        if (hours ? hourAvailable(endpoint) : validTime(hourMinute(picker.hour, endpoint))) {
                            if (hours) { chooseHour(endpoint); updateTime(); updateHand(); } else { setClock(endpoint); } break;
                        }
                    }
                }
                if (key === 'Enter' || key === 13 || key === ' ' || key === 32) { event.preventDefault(); event.stopPropagation(); picker.clock = hours ? 'minutes' : 'hours'; draw(); focusClock(); }
            };
            updateHand();
        }
        function dragClock(event) { if (live() && picker.dragging) { event.preventDefault(); clockPoint(event); } }
        function releaseClock() { if (picker.dragging) { picker.dragging = false; if (live() && picker.clock === 'hours') { picker.clock = 'minutes'; draw(); focusClock(); } } }
        document.addEventListener('mousemove', dragClock, true); document.addEventListener('mouseup', releaseClock, true);
        picker.removeDrag = function () { document.removeEventListener('mousemove', dragClock, true); document.removeEventListener('mouseup', releaseClock, true); };
        function updateTime() {
            hour.querySelector('.ss-control-label').textContent = datePad(format.hour12 ? picker.hour % 12 || 12 : picker.hour);
            minute.querySelector('.ss-control-label').textContent = datePad(picker.minute);
            hour.setAttribute('aria-label', t('timeline.calendar_hour') + ': ' + hour.textContent); minute.setAttribute('aria-label', t('timeline.calendar_minute') + ': ' + minute.textContent);
            hour.setAttribute('aria-pressed', String(picker.clock === 'hours')); minute.setAttribute('aria-pressed', String(picker.clock === 'minutes'));
            periodButtons.forEach(function (node, index) {
                node.setAttribute('aria-pressed', String(index === (picker.hour < 12 ? 0 : 1)));
                var usable = false; for (var value = index * 12; value < index * 12 + 12; value += 1) { usable = usable || hourAvailable(value); }
                unavailable(node, !usable);
            });
            unavailable(apply, !validTime(hourMinute(picker.hour, picker.minute)));
        }
        function draw() {
            if (!live()) { return; }
            limits = customDateBounds(timeline, field);
            clear(body); clear(clockBody); picker.dragging = false;
            monthTitle.querySelector('.ss-control-label').textContent = format.months[picker.month - 1] || datePad(picker.month);
            yearTitle.querySelector('.ss-control-label').textContent = String(picker.year);
            monthTitle.setAttribute('aria-label', t('timeline.calendar_month') + ': ' + monthTitle.textContent); yearTitle.setAttribute('aria-label', t('timeline.calendar_year') + ': ' + picker.year);
            monthTitle.setAttribute('aria-expanded', String(picker.mode === 'months')); yearTitle.setAttribute('aria-expanded', String(picker.mode === 'years'));
            previous.style.visibility = next.style.visibility = picker.mode === 'days' ? 'visible' : 'hidden';
            var before = new Date(picker.year, picker.month - 2, 1), after = new Date(picker.year, picker.month, 1);
            unavailable(previous, !available(before.getFullYear(), before.getMonth() + 1));
            unavailable(next, !available(after.getFullYear(), after.getMonth() + 1));
            if (picker.mode === 'days') { drawDays(); }
            else if (picker.mode === 'months' || picker.mode === 'years') { drawOptions(picker.mode); }
            drawClock();
            updateTime(); positionDatePicker();
        }
        var apply = action(footer, 'ss-custom-date-apply', t('timeline.custom_apply'), function () {
            var timestamp = customDateParts(picker.year, picker.month, picker.day, picker.hour, picker.minute);
            if (!validTime(timestamp)) { fail(t(timestamp > Date.now() / 1000 ? 'timeline.custom_future' : 'timeline.custom_order')); return; }
            input.value = customDateText(timestamp); input.oninput({});
            if (applyTimelineRange(timeline, field, '__custom__', account)) { closeDatePicker(true); }
            else { fail(state.actionError || t('timeline.custom_invalid')); }
        });
        apply.id = 'ss-custom-date-apply-' + field;
        action(footer, 'ss-date-picker-cancel', t('cancel'), function () { closeDatePicker(true); });
        picker.node.onkeydown = function (event) {
            if (event.key !== 'Tab' && event.keyCode !== 9) { return; }
            var choices = Array.prototype.filter.call(picker.node.querySelectorAll('button,[role="slider"]'), function (node) { return !node.disabled && node.getAttribute('tabindex') !== '-1' && node.offsetWidth > 0 && node.style.visibility !== 'hidden'; });
            var first = choices[0], last = choices[choices.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); focusControl(last); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); focusControl(first); }
        };
        draw(); focusDay();
    }
    function renderTimeline(timeline, disabled) {
        var timelineScope = !!timeline && state.scope === 'manual';
        var visible = timelineScope && !disabled;
        nodes.started.style.display = timelineScope ? 'none' : 'block';
        nodes.timeline.style.display = visible ? 'flex' : 'none';
        if (!visible) { closeDatePicker(false); return; }
        var points = timeline.time_points || [], names = timeline.time_point_names || {}, account = state.payload.account_key;
        var rangeKey = JSON.stringify([state.payload.account_key, timeline.from_point, timeline.to_point, timeline.from_date, timeline.to_date]);
        if (rangeKey !== state.customRangeKey) { state.customDates = {}; state.customRangeKey = rangeKey; }
        ['from', 'to'].forEach(function (field) {
            if (timeline[field + '_point'] === '__custom__' && !state.customDates[field]) {
                state.customDates[field] = {value:customDateText(timeline[field + '_date'])};
            }
            var draft = state.customDates[field], format = dateLocale();
            if (draft && JSON.stringify(draft.format) !== JSON.stringify(format)) {
                var timestamp = draft.format ? customDateValue(draft.value, draft.format) : null;
                draft.value = timestamp === null ? customDateMask(draft.value, format) : customDateText(timestamp, format);
                draft.format = format;
            }
        });
        var signature = JSON.stringify([points, names, rangeKey, !!state.customDates.from, !!state.customDates.to, document.documentElement.getAttribute('lang'), dateLocale()]);
        if (state.timelineSignature === signature) { return; }
        state.timelineSignature = signature;
        closeSelect(false); closeDatePicker(false);
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
                if (point[1] <= Date.now() / 1000 && (!hasNumber(limit) || (from ? point[1] < limit : point[1] > limit))) {
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
                    var dateInput = document.getElementById('ss-custom-date-' + field);
                    focusControl(dateInput); if (dateInput && typeof dateInput.select === 'function') { dateInput.select(); }
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
                var row = element('div', 'ss-date-editor'); holder.insertBefore(row, control.trigger);
                var input = append(row, element('input', 'ss-control ss-custom-date'));
                input.id = 'ss-custom-date-' + field;
                input.type = 'text'; input.maxLength = dateLocale().hour12 ? 84 : 16; input.value = state.customDates[field].value;
                input.setAttribute('inputmode', dateLocale().hour12 ? 'text' : 'numeric'); input.setAttribute('autocomplete', 'off'); input.setAttribute('spellcheck', 'false');
                input.setAttribute('placeholder', customDatePlaceholder());
                input.setAttribute('aria-label', label + ' · ' + t('timeline.custom'));
                input.setAttribute('aria-describedby', 'ss-custom-date-error-' + field);
                input.setAttribute('role', 'combobox'); input.setAttribute('aria-haspopup', 'listbox'); input.setAttribute('aria-expanded', 'false');
                input.setAttribute('aria-controls', control.menu.id); input.title = customDatePlaceholder() + ' · ' + t('timeline.custom_enter'); control.input = input;
                row.appendChild(control.trigger); control.trigger.className += ' ss-date-menu'; control.trigger.setAttribute('role', 'button');
                control.trigger.setAttribute('aria-label', label + ' · ' + t('timeline.point_menu')); control.trigger.title = t('timeline.point_menu');
                var calendar = append(row, element('button', 'ss-control ss-button ss-date-calendar')); calendar.type = 'button';
                calendar.id = 'ss-custom-date-calendar-' + field;
                calendar.setAttribute('aria-label', label + ' · ' + t('timeline.calendar')); calendar.title = t('timeline.calendar');
                calendar.setAttribute('aria-haspopup', 'dialog'); calendar.setAttribute('aria-expanded', 'false'); calendar.setAttribute('aria-controls', 'ss-date-picker-' + field);
                append(calendar, element('span', 'ss-date-calendar-icon')).setAttribute('aria-hidden', 'true');
                var error = append(holder, element('div', 'ss-custom-date-error'));
                error.id = 'ss-custom-date-error-' + field; error.setAttribute('data-field', field); error.setAttribute('role', 'alert');
                error.style.display = 'none';
                input.oninput = function (event) {
                    if (state.destroyed || state.payload.account_key !== account || !state.customDates[field] || !root.contains(input)) { return; }
                    if (!event || !event.isComposing) { maskDateInput(input); }
                    state.customDates[field].value = input.value; state.customDates[field].format = dateLocale();
                    input.removeAttribute('aria-invalid'); error.textContent = ''; error.style.display = 'none';
                };
                calendar.onclick = function () { openDatePicker(field, holder, input, calendar, timeline, account); };
                input.onkeydown = function (event) {
                    deleteDateSeparator(input, event);
                    if ((event.key === 'Enter' || event.keyCode === 13) && !event.isComposing) {
                        event.preventDefault(); event.stopPropagation(); applyTimelineRange(timeline, field, '__custom__', account);
                    }
                    if (event.altKey && (event.key === 'ArrowDown' || event.keyCode === 40)) {
                        event.preventDefault(); event.stopPropagation(); control.open();
                    }
                    if (event.key === 'F4' || event.keyCode === 115) {
                        event.preventDefault(); event.stopPropagation(); calendar.onclick();
                    }
                };
            }
        });
    }
    document.addEventListener('mousedown',outsideSelect);
    document.addEventListener('mousedown', outsideDatePicker, true);
    document.addEventListener('keydown', datePickerKey, true);
    window.addEventListener('resize', positionDatePicker);
    var mapPreviewTarget = null;
    var mapPreview = append(root, element('div', 'ss-map-preview'));
    mapPreview.id = 'ss-map-preview'; mapPreview.setAttribute('role', 'tooltip');
    var mapPreviewImage = append(mapPreview, element('div', 'ss-map-preview-image'));
    mapPreviewImage.setAttribute('role', 'img');
    function hideMapPreview() {
        if (mapPreviewTarget) {
            if (mapPreviewTarget.getAttribute('aria-describedby') === mapPreview.id) { mapPreviewTarget.removeAttribute('aria-describedby'); }
            mapPreviewTarget.setAttribute('aria-expanded', 'false');
        }
        mapPreviewTarget = null;
        mapPreview.style.display = 'none'; mapPreviewImage.style.backgroundImage = '';
    }
    function mapPreviewAncestor(target) {
        while (target && target !== root) {
            if (target.nodeType === 1 && target.hasAttribute('data-ss-map-preview')) { return target; }
            target = target.parentNode;
        }
        return null;
    }
    function showMapPreview(target) {
        if (!target || state.destroyed || (state.group !== 'maps' && state.group !== 'battles') || state.dialog || state.resize || state.dragging || !root.contains(target)) { hideMapPreview(); return; }
        if (target === mapPreviewTarget) { return; }
        hideMapPreview(); hideHelp();
        var bounds = root.getBoundingClientRect(), anchor = target.getBoundingClientRect(), scale = state.nativeScale || 1;
        var gap = 8 * scale;
        var frameX = 2 * scale, frameY = frameX, source = target.getAttribute('data-ss-map-preview') || '';
        if (typeof window !== 'undefined' && typeof window.getComputedStyle === 'function') {
            try {
                var style = window.getComputedStyle(mapPreview);
                var horizontal = parseFloat(style.borderLeftWidth) + parseFloat(style.borderRightWidth);
                var vertical = parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
                if (isFinite(horizontal) && horizontal >= 0) { frameX = horizontal; }
                if (isFinite(vertical) && vertical >= 0) { frameY = vertical; }
            } catch (error) { /* Keep the shipped native frame while styles mount. */ }
        }
        if (!(anchor.width > 1) || !(anchor.height > 1) || !(bounds.width > gap * 2 + frameX) || !(bounds.height > gap * 2 + frameY)) { return; }
        // Use the reviewed category defaults (8:5 loading art, 5:3 small
        // icons, square lobby maps), not the unrelated thumbnail frame.
        // Decorative loading art may crop edge variants; tactical and unknown
        // images always retain contain, so no part of a minimap is discarded.
        var aspect = anchor.width / anchor.height;
        var decorative = target.getAttribute('data-ss-map-preview-mode') !== 'minimap' &&
            source.indexOf('img://gui/maps/icons/map/screen/') === 0;
        if (target.getAttribute('data-ss-map-preview-mode') === 'minimap' ||
                /^img:\/\/gui\/maps\/icons\/map\/[A-Za-z0-9_-]+\.(png|dds)$/i.test(source)) { aspect = 1; }
        else if (decorative) { aspect = 8 / 5; }
        else if (source.indexOf('img://gui/maps/icons/map/small/') === 0) { aspect = 5 / 3; }
        var width = Math.min(anchor.width * 4, bounds.width - gap * 2,
            (bounds.height - gap * 2 - frameY) * aspect + frameX);
        var height = (width - frameX) / aspect + frameY;
        if (!(width > frameX) || !(height > frameY)) { return; }
        var left = anchor.right - bounds.left + gap;
        if (left + width > bounds.width - gap) { left = anchor.left - bounds.left - width - gap; }
        var top = anchor.top - bounds.top;
        mapPreviewTarget = target;
        target.setAttribute('aria-describedby', mapPreview.id); target.setAttribute('aria-expanded', 'true');
        var label = t('maps.preview', [target.getAttribute('aria-label') || '']);
        mapPreview.setAttribute('aria-label', label); mapPreviewImage.setAttribute('aria-label', label);
        mapPreviewImage.style.backgroundImage = 'url("' + source + '")';
        mapPreviewImage.style.backgroundSize = decorative ? 'cover' : 'contain';
        mapPreview.style.width = width + 'px'; mapPreview.style.height = height + 'px';
        mapPreview.style.left = Math.max(gap, Math.min(left, bounds.width - width - gap)) + 'px';
        mapPreview.style.top = Math.max(gap, Math.min(top, bounds.height - height - gap)) + 'px';
        mapPreview.style.display = 'block';
    }
    function hoverMapPreview(event) { showMapPreview(mapPreviewAncestor(event.target)); }
    function leaveMapPreview(event) {
        if (mapPreviewAncestor(event.relatedTarget) !== mapPreviewTarget) { hideMapPreview(); }
    }
    function mapPreviewKey(event) {
        if (mapPreviewTarget && (event.key === 'Escape' || event.keyCode === 27)) {
            event.preventDefault(); event.stopPropagation(); hideMapPreview();
        }
    }
    root.addEventListener('mouseover', hoverMapPreview);
    root.addEventListener('mouseout', leaveMapPreview);
    root.addEventListener('focusin', hoverMapPreview);
    root.addEventListener('focusout', leaveMapPreview);
    root.addEventListener('keydown', mapPreviewKey);
    nodes.scroll.addEventListener('scroll', hideMapPreview);
    window.addEventListener('blur', hideMapPreview);
    window.addEventListener('resize', hideMapPreview);
    function nativeVisualSource(src, kind) {
        var prefix = kind === 'vehicle' ? 'img://gui/maps/icons/vehicle/' : 'img://gui/maps/icons/map/';
        if (typeof src !== 'string' || src.indexOf(prefix) !== 0 || src.length <= prefix.length) { return null; }
        var path = src.slice(prefix.length);
        if (/[^A-Za-z0-9_./-]/.test(path) || /(^|\/)\.{1,2}(\/|$)/.test(path) ||
                path.indexOf('//') !== -1 || !/\.(png|dds)$/i.test(path)) { return null; }
        return src;
    }
    function appendVisual(parent, item) {
        var visual = item.visual;
        if (!visual || (visual.kind !== 'vehicle' && visual.kind !== 'map')) { return; }
        var src = nativeVisualSource(visual.src, visual.kind);
        /* URLs come from the native R/backport resolver, which checks ResMgr.isFile.
           UI accepts only these local asset families; no remote URLs or CSS escapes. */
        if (!src) { return; }
        var thumb = append(parent, element('div', 'ss-group-thumb'));
        thumb.setAttribute('role', 'img');
        thumb.setAttribute('aria-label', String(visual.alt || item.name || ''));
        /* Gameface supports background sizing, not object-fit. Decorative map
           photos fill their fixed thumbnail; tactical maps stay complete. */
        thumb.style.backgroundImage = 'url("' + src + '")';
        if (visual.kind === 'map' && /^img:\/\/gui\/maps\/icons\/map\/(small|screen)\//.test(src)) {
            thumb.style.backgroundSize = 'cover';
        }
        if (visual.kind === 'map') {
            var preview = nativeVisualSource(visual.preview_src, 'map');
            thumb.setAttribute('data-ss-map-preview', preview || src);
            thumb.setAttribute('data-ss-map-preview-mode', preview && visual.preview_mode === 'minimap' ? 'minimap' : 'image');
            thumb.setAttribute('tabindex', '0');
            thumb.setAttribute('aria-controls', mapPreview.id); thumb.setAttribute('aria-expanded', 'false');
        }
        return thumb;
    }
    function appendBattleMap(parent, item) {
        if (!item.map_visual || item.map_visual.kind !== 'map') { return; }
        var visual = element('div', 'ss-battle-map-visual');
        var thumb = appendVisual(visual, {name:item.map, visual:item.map_visual});
        if (!thumb) { return; }
        thumb.className += ' ss-battle-map-thumb';
        var name = String(item.map || item.map_visual.alt || t('unknown.map'));
        var caption = append(visual, element('span', 'ss-battle-map-label', name));
        caption.title = name; caption.setAttribute('aria-hidden', 'true');
        append(parent, visual);
        return visual;
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
        var detailColumns = ids.length || hasBonuses ? append(panel, element('div', 'ss-more-columns ss-more-columns-stacked')) : null;
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
            ids.forEach(function (id, index) {
                var mission = missions[id], kind = mission.kind || 'other';
                var row = append(missionTable, element('div', 'ss-more-mission' + (index % 2 ? ' ss-more-mission-even' : '')));
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
            function bonusOutput(key) {
                var value = key && bonuses[key];
                var divisor = key && (key.slice(-9) === 'Factor100' ? 100 : key.slice(-8) === 'Factor10' ? 10 : null);
                return hasNumber(value) ? (divisor ? '\u00d7' + String(value / divisor).replace('.', t('format.decimal')) : signed(value)) : t('format.missing');
            }
            // Reserve complete formatted amounts and unbroken heading words.
            // The source remains beside this strip whenever the card can fit it.
            var widths = columns.map(function (label, index) {
                if (!visible[index]) { return 0; }
                var words = t(label).split(/[\s\-\u2010-\u2015]+/), longest = 0;
                words.forEach(function (word) { longest = Math.max(longest, word.length); });
                var width = Math.max([60, 36, 42, 50, 42][index], longest * 6 + 6);
                sources.forEach(function (source) { width = Math.max(width, bonusOutput(source[index]).length * 7 + 6); });
                return Math.ceil(width);
            });
            var valuesWidth = widths.reduce(function (total, width) { return total + width; }, 0);
            var bonusWidth = longBonus ? 486 : Math.max(308, Math.min(486, 124 + valuesWidth));
            bonusBlock.style.width = bonusWidth + 'rem';
            bonusBlock.setAttribute('data-bonus-width', String(bonusWidth));
            bonusBlock.setAttribute('data-resource-count', String(visible.filter(function (value) { return value; }).length));
            var bonusTable = sources.length ? rewardTable(bonusBlock, 'ss-more-bonuses' + (longBonus ? ' ss-long-bonus-values' : '')) : null;
            var factors = null;
            if (sources.length) {
                var heading = append(bonusTable, element('div', 'ss-bonus-row ss-bonus-head'));
                heading.setAttribute('role', 'row');
                append(heading, element('div', 'ss-bonus-label', t('more.bonuses'))).setAttribute('role', 'columnheader');
                var headings = append(heading, element('div', 'ss-bonus-values'));
                headings.setAttribute('role', 'presentation'); headings.style.flexBasis = valuesWidth + 'rem';
                columns.forEach(function (label, index) {
                    if (visible[index]) {
                        var cell = append(headings, element('div', 'ss-bonus-number ss-bonus-column-' + index, t(label)));
                        cell.setAttribute('role', 'columnheader'); cell.style.flexBasis = widths[index] + 'rem';
                    }
                });
                sources.forEach(function (source) {
                    var first = source.filter(function (key) { return key && hasNumber(bonuses[key]); })[0];
                    var caption = t('more.bonus.' + bonusLabels[first], ['']);
                    var separator = caption.indexOf(':');
                    var row = append(bonusTable, element('div', 'ss-bonus-row'));
                    row.setAttribute('role', 'row');
                    append(row, element('div', 'ss-bonus-label', separator >= 0 ? caption.slice(0, separator) : caption)).setAttribute('role', 'rowheader');
                    var values = append(row, element('div', 'ss-bonus-values'));
                    values.setAttribute('role', 'presentation'); values.style.flexBasis = valuesWidth + 'rem';
                    columns.forEach(function (label, index) {
                        if (!visible[index]) { return; }
                        var key = source[index];
                        var divisor = key && (key.slice(-9) === 'Factor100' ? 100 : key.slice(-8) === 'Factor10' ? 10 : null);
                        var cell = append(values, element('div', 'ss-bonus-number ss-bonus-column-' + index + (divisor ? ' ss-bonus-factor' : ''), bonusOutput(key)));
                        cell.setAttribute('role', 'cell'); cell.style.flexBasis = widths[index] + 'rem';
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
    function layoutMissionRows(missions, width) {
        var body = missions.querySelector('.ss-more-body');
        if (!body) { return; }
        var cards = Array.prototype.slice.call(body.querySelectorAll('.ss-more-mission'));
        // Two readable mission cells fill compact cards without squeezing the
        // independent bonus matrix. Explicit rows avoid native grid/wrap gaps.
        var count = cards.length > 1 && width >= 440 ? 2 : 1, gap = 8;
        if (body.getAttribute('data-mission-columns') !== String(count)) {
            clear(body);
            var row;
            cards.forEach(function (card, index) {
                if (index % count === 0) {
                    row = append(body, element('div', 'ss-more-mission-row'));
                    row.setAttribute('role', 'presentation');
                }
                row.appendChild(card);
            });
            body.setAttribute('data-mission-columns', String(count));
        }
        cards.forEach(function (card, index) {
            var paired = count === 2 && (index % 2 === 1 || index + 1 < cards.length);
            var value = (paired ? (width - gap) / 2 : width) + 'rem';
            if (card.style.width !== value) { card.style.width = value; }
            if (card.style.flex !== '0 0 ' + value) { card.style.flex = '0 0 ' + value; }
            var margin = paired && index % 2 === 0 ? gap + 'rem' : '0rem';
            if (card.style.marginRight !== margin) { card.style.marginRight = margin; }
        });
    }
    function layoutMoreColumns(card, availableWidth) {
        var columns = card.querySelector('.ss-more-columns');
        if (!columns) { return; }
        var scale = state.nativeScale || 1, measured = columns.getBoundingClientRect().width / scale;
        // Native flex wrapping can squeeze missions to a few pixels instead of
        // moving them below a rich bonus matrix. Resolve both widths ourselves.
        var width = Math.max(1, availableWidth);
        if (measured > 1) { width = Math.min(width, measured); }
        var bonus = columns.querySelector('.ss-more-bonus-block');
        var missions = columns.querySelector('.ss-more-mission-block');
        var preferred = bonus ? Number(bonus.getAttribute('data-bonus-width')) || 308 : 0;
        var bonusWidth = Math.min(width, preferred), gap = 8, minimumMissionWidth = 180;
        var paired = bonus && missions && width >= preferred + gap + minimumMissionWidth;
        columns.className = 'ss-more-columns ss-more-columns-' + (paired ? 'paired' : 'stacked');
        if (bonus) {
            bonus.style.width = bonusWidth + 'rem';
            // A stacked native block may retain vertical flex semantics. Only a
            // paired row may use a horizontal width as its flex basis.
            bonus.style.flex = paired ? '0 0 ' + bonusWidth + 'rem' : '0 0 auto';
            bonus.style.marginRight = paired ? gap + 'rem' : '0rem';
        }
        if (missions) {
            var missionWidth = paired ? width - bonusWidth - gap : width;
            missions.style.width = missionWidth + 'rem';
            missions.style.flex = paired ? '0 0 ' + missionWidth + 'rem' : '0 0 auto';
            missions.style.minWidth = paired ? minimumMissionWidth + 'rem' : '0rem';
            layoutMissionRows(missions, missionWidth);
        }
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
            var banner = card.querySelector('.ss-battle-selection-banner');
            if (banner && banner.parentNode) {
                if (card.getAttribute('aria-describedby') === banner.id) { card.removeAttribute('aria-describedby'); }
                banner.parentNode.removeChild(banner);
            }
            ['ss-battle-target', 'ss-target-pulsing', 'ss-target-muted'].forEach(function (name) { card.classList.remove(name); });
        });
        // Selection decorations are overlays; removing them never changes
        // card heights or restarts the independent lane layout.
        queueResize();
    }
    function paintBattleTarget(card) {
        var target = state.highlightedBattle;
        if (!target || !sameContext(target.context) || card.getAttribute('data-group-id') !== target.id) { return; }
        var outline = card.querySelector('.ss-battle-target-outline');
        if (!outline) { outline = append(card, element('span', 'ss-battle-target-outline')); outline.setAttribute('aria-hidden', 'true'); }
        var banner = card.querySelector('.ss-battle-selection-banner');
        if (!banner) {
            banner = element('div', 'ss-battle-selection-banner', t('battle.selected'));
            banner.id = card.id + '-selection'; banner.setAttribute('data-i18n', 'battle.selected');
            banner.setAttribute('role', 'status');
            card.insertBefore(banner, card.firstChild);
            card.setAttribute('aria-describedby', banner.id);
        }
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
    // Selection belongs to the navigation result, not DOM/native focus.
    // Gameface can publish null/body/root focus, another control's focus or
    // window blur while mounting/reparenting the battle. Only an explicit
    // outside click or a changed result context dismisses its visible frame.
    document.addEventListener('click', targetClick, true);
    function cancelBattleNavigation() {
        state.pendingBattle = null; state.battleJump = null;
        var timer = state.battleJumpTimer; state.battleJumpTimer = null; cancelUITimer(timer);
    }
    function cancelPageJump() {
        state.pageJump = null;
        var timer = state.pageJumpTimer; state.pageJumpTimer = null; cancelUITimer(timer);
        if (state.feed) { state.feed.navigationPage = null; state.feed.navigationDeadline = null; }
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
        clearBattleTarget();
        state.group = 'battles'; state.loadedCount = 40;
        state.feedForceStart = scope.pagination && scope.pagination.battles ? scope.pagination.battles.page : 0;
        // Own the selection as soon as its native reply is accepted. Cards
        // paint it during construction, before any layout/focus retry can
        // stall or expire; only scrolling depends on measurable geometry.
        state.highlightedBattle = {id:pending.id, context:pending.context, until:Date.now() + 5000};
        var sequence = ++state.targetSequence;
        state.targetTimer = window.setTimeout(function () {
            if (state.destroyed || sequence !== state.targetSequence || !state.highlightedBattle) { return; }
            state.targetTimer = null; state.highlightedBattle.until = 0;
            (state.groupCards || []).forEach(paintBattleTarget);
        }, 5000);
        cancelPageJump();
        state.battleJump = {id:pending.id, context:pending.context, attempts:0, deadline:Date.now() + 10000,
            lastOffset:null, settledSince:null, stable:0, target:null, focused:null, requestedOffset:null};
    }
    function battleLayoutOffset(node, ancestor) {
        var offset = 0, count = 0;
        while (node && node !== ancestor && count < 24) {
            if (!hasNumber(node.offsetTop)) { return null; }
            offset += node.offsetTop;
            node = node.offsetParent; count += 1;
            if (node && node !== ancestor && hasNumber(node.clientTop)) { offset += node.clientTop; }
        }
        return node === ancestor ? offset : null;
    }
    function battleScrollPending(jump) {
        if (!jump || !hasNumber(jump.requestedOffset)) { return false; }
        var scale = state.nativeScale || 1, scroll = nodes.scroll;
        if (Math.abs(scroll.scrollTop - jump.requestedOffset) > scale) { return true; }
        var origin = battleLayoutOffset(nodes.groups, scroll);
        if (origin === null) { return false; }
        var content = nodes.groups.getBoundingClientRect(), viewport = scroll.getBoundingClientRect();
        return hasNumber(content.top) && hasNumber(viewport.top) &&
            Math.abs(content.top - viewport.top + scroll.scrollTop - origin) > scale;
    }
    function retryBattleJump(jump) {
        if (state.battleJump !== jump || state.battleJumpTimer !== null) { return; }
        if (Date.now() >= jump.deadline || jump.attempts >= 100) { cancelBattleNavigation(); return; }
        jump.attempts += 1;
        var timer = window.setTimeout(function () {
            if (state.battleJumpTimer === timer) { state.battleJumpTimer = null; }
            if (state.battleJump === jump && !state.destroyed) { finishBattleJump(); }
        }, 100);
        state.battleJumpTimer = timer;
    }
    function finishBattleJump() {
        var jump = state.battleJump;
        if (!jump) { return; }
        if (state.group !== 'battles' || !sameContext(jump.context)) { cancelBattleNavigation(); return; }
        // Loading a selected page and native layout can take several seconds.
        // Own the destination until its actual position settles, while keeping
        // a bounded lifetime and yielding immediately to newer user input.
        if (Date.now() >= jump.deadline || jump.attempts >= 100) {
            cancelBattleNavigation(); return;
        }
        if (!state.highlightedBattle || state.highlightedBattle.id !== jump.id) {
            cancelBattleNavigation(); return;
        }
        if (state.cardFlowQueued || state.groupMinHeight || state.feedStaging ||
                nodes.groups.getAttribute('aria-busy') === 'true') { retryBattleJump(jump); return; }
        // Native rectangles and scrollTop can acknowledge a setter in either
        // order. Never mix samples from opposite sides of that handoff.
        if (battleScrollPending(jump)) { retryBattleJump(jump); return; }
        jump.requestedOffset = null;
        var target = null;
        (state.groupCards || []).some(function (card) {
            if (card.getAttribute('data-group-id') === jump.id) { target = card; return true; }
            return false;
        });
        var scroll = nodes.scroll, box = target && target.getBoundingClientRect(), container = scroll.getBoundingClientRect();
        function validRect(rect) {
            return rect && hasNumber(rect.top) && hasNumber(rect.width) && hasNumber(rect.height) && rect.width > 1 && rect.height > 1;
        }
        if (!validRect(box) || !validRect(container)) { retryBattleJump(jump); return; }
        var scale = state.nativeScale || 1, filterHeight = pinnedFilterHeight();
        var layoutOffset = battleLayoutOffset(target, scroll);
        var offset = Math.max(0, Math.min(scrollbarMetrics().maximum,
            (layoutOffset === null ? scroll.scrollTop + box.top - container.top : layoutOffset) - filterHeight - 16 * scale));
        var now = Date.now();
        if (jump.target !== target || jump.lastOffset === null || Math.abs(jump.lastOffset - offset) > scale) {
            jump.target = target; jump.lastOffset = offset; jump.settledSince = now; jump.stable = 0;
        }
        if (jump.focused !== target) { focusControl(target); jump.focused = target; }
        cancelPageJump();
        if (state.feed) { state.feed.navigationPage = null; }
        jump.requestedOffset = offset;
        state.scrollTarget = offset; scroll.scrollTop = offset;
        // A first non-zero rectangle can still precede font, lane or native
        // surface settlement. Verify the position again instead of consuming
        // the jump after that first paint. Scroll setters may also lag a frame.
        var aligned = target.getBoundingClientRect(), actualTop = scroll.scrollTop;
        var visible = validRect(aligned) && aligned.top >= container.top + filterHeight - scale && aligned.top < container.bottom - scale;
        var acknowledged = !battleScrollPending(jump);
        if (visible && acknowledged && Math.abs(actualTop - offset) <= scale) { jump.stable += 1; }
        else { jump.stable = 0; jump.settledSince = now; }
        if (acknowledged) { updatePinnedFilters(true); syncScrollbar(); }
        if (jump.stable >= 3 && now - jump.settledSince >= 500) {
            state.battleJump = null;
            var retryTimer = state.battleJumpTimer; state.battleJumpTimer = null; cancelUITimer(retryTimer);
            return;
        }
        retryBattleJump(jump);
    }
    function attachMapMore(card, header, map) {
        var vehicle = state.group === 'vehicles', kind = vehicle ? 'vehicle' : 'map';
        var context = viewContext(), key = JSON.stringify([context.account_key, context.scope, context.period_id, kind, String(map.id)]);
        var identifier = String(map.id), group = state.group, historyChronology = getOrder(currentScope()).chronology;
        var titleKey = vehicle ? 'vehicles.battles' : 'maps.battles';
        var button = append(header, element('button', 'ss-control ss-button ss-more-button ss-map-more-button' + (vehicle ? ' ss-vehicle-more-button' : '')));
        button.type = 'button';
        var caption = append(button, element('span', 'ss-control-label'));
        var panel = append(card, element('div', 'ss-map-battles' + (vehicle ? ' ss-vehicle-battles' : '')));
        panel.setAttribute('role', 'region'); panel.setAttribute('aria-label', t(titleKey));
        var body = null, previous = null, next = null, pageText = null;
        var rendered = null, requestedPage = null;
        function live() {
            return sameContext(context) && state.group === group && getOrder(currentScope()).chronology === historyChronology && document.documentElement.contains(card);
        }
        function load(page) {
            if (!live() || requestedPage !== null) { return; }
            requestedPage = page;
            panel.setAttribute('aria-busy', 'true');
            var args = {account_key:context.account_key, scope:context.scope, period_id:context.period_id, page:page, chronology:historyChronology};
            args[kind + '_id'] = identifier;
            if (!invoke(kind + '_battles', args)) {
                requestedPage = null;
                panel.setAttribute('aria-busy', 'false');
            }
        }
        function ensurePanel() {
            if (body) { return; }
            append(panel, element('h3', 'ss-more-title', t(titleKey)));
            // Unknown and paged histories reserve the same viewport. A known
            // short single page can use its actual rows instead of empty space.
            body = append(panel, element('div', 'ss-history-body ss-history-paged'));
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
            body.className = 'ss-history-body' + (!list || list.pages > 1 ? ' ss-history-paged' : '');
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
                    var rating = append(row, element('span', 'ss-map-battle-wn8'));
                    paintWN8Caption(append(rating, element('span', 'ss-map-battle-wn8-label', t('metric.wn8') + ' ')), battle.wn8);
                    paintWN8(append(rating, element('span', 'ss-map-battle-wn8-value', integer(battle.wn8))), battle.wn8);
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
            if (item.battle_list && item.battle_list.chronology && item.battle_list.chronology !== historyChronology) { return true; }
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

    function cardSortValue(item, options) {
        // A supplied null is authoritative, especially for unknown outcomes.
        return item.sort_value !== undefined ? item.sort_value : groupSortValue(item, options);
    }
    function sortMetricLabel(options, battle) {
        var metric = options.metric, label = metric === 'battle_wn8' ? t('metric.wn8') :
            metric === 'win_rate' ? t('metric.win_rate') : metric === 'battles' ? t('metric.battles') :
            creditMetric(metric) ? t('sort.' + canonicalMetric(metric)) :
            t(metric === 'xp_base' ? 'xp.base' : 'xp.received');
        return battle || metric === 'win_rate' || metric === 'battles' ? label :
            t('sort.metric_stat', [t(options.statistic === 'avg' ? 'sort.avg' : options.statistic === 'sum' ? 'sort.sum' : 'metric.' + options.statistic), label]);
    }
    function markSortValue(node, metric, label) {
        if (!node) { return false; }
        node.classList.add('ss-sort-active-value');
        node.setAttribute('data-ss-sort-active', metric);
        // A permanent action keeps its exact source explanation as fallback help.
        if (!node.classList.contains('ss-metric-battle-link')) { node.title = t('sort.active_value', [label]); }
        return true;
    }
    function highlightCardSort(card, meta, item, options, battle) {
        var metric = options.metric;
        if (metric === 'off' || (battle && metric === 'win_rate')) { return; }
        var label = sortMetricLabel(options, battle), kpis = card.querySelectorAll('.ss-group-kpi');
        var row, selected = options.statistic === 'min' ? 1 : options.statistic === 'max' ? 3 : 2;
        if (metric === 'win_rate' || metric === 'battles') {
            markSortValue(kpis[metric === 'battles' ? 0 : 1], metric, label);
        } else if (metric === 'battle_wn8' || metric === 'xp_base' || metric === 'xp_received') {
            if (!battle && options.statistic === 'sum') {
                // The distribution has no total column. Show the actual sum
                // without marking its average as if it were the same value.
                var total = append(meta, element('div', 'ss-group-sort-value ss-sort-active-value',
                    t('sort.value_total', [t(metric === 'xp_base' ? 'xp.base' : 'xp.received'), number(cardSortValue(item, options))])));
                var xp = series((item.stats || {})[metric]), partial = coverage(xp.count, observedTotal(item.stats || {}));
                if (partial) { explainCoverage(append(total, element('span', 'ss-count-coverage', ' (' + partial + ')')),
                    xp.count, observedTotal(item.stats || {})); }
                return;
            }
            if (!battle && metric === 'battle_wn8') { markSortValue(kpis[2], metric, label); }
            row = card.querySelector('[data-ss-metric="' + metric + '"]');
            markSortValue(battle ? row : row && row.children[selected], metric, label);
            if (!battle) {
                var header = card.querySelector('.ss-metric-head');
                markSortValue(header && header.children[selected], metric, label);
            }
        } else if (creditMetric(metric)) {
            var cell = card.querySelector('.ss-money-value[data-ss-metric="' + canonicalMetric(metric) + '"]');
            if (battle || options.statistic === 'sum') {
                markSortValue(cell && cell.querySelector('.ss-cell-value'), metric, label);
            } else {
                // A financial cell displays All; its permanent Min/Max links
                // are source actions, not substitutes for the selected value.
                if (options.statistic === 'min' || options.statistic === 'max') {
                    markSortValue(cell && cell.querySelector('[data-ss-extreme="' + options.statistic + '"]'), metric, label);
                }
                append(meta, element('div', 'ss-group-sort-value ss-sort-active-value', t('sort.value_per_battle', [
                    t(options.statistic === 'avg' ? 'sort.avg' : 'metric.' + options.statistic),
                    t('sort.' + canonicalMetric(metric)),
                    netCreditMetric(metric) ? signed(cardSortValue(item, options)) : number(cardSortValue(item, options))])));
            }
        }
    }
    function createMetricBattleLink(parent, item, metric, statistic, global, label) {
        var references = item && item.extrema_battles, data = series(item && item.stats && item.stats[metric]);
        var reference = references && references[metric] && references[metric][statistic];
        if ((statistic !== 'min' && statistic !== 'max') || !reference || !hasNumber(data.count) || data.count <= 0 ||
                reference.metric !== metric || reference.statistic !== statistic || !hasNumber(reference.value) ||
                !hasNumber(data[statistic]) || reference.value !== data[statistic] ||
                typeof reference.id !== 'string' || !reference.id) { return null; }
        var context = viewContext(), grouping = global ? null : state.group, revision = currentScope().data_revision;
        var identifier = reference.id;
        var link = append(parent, element('button', 'ss-control ss-metric-battle-link ss-hover-help' +
            (label ? ' ss-metric-extreme-action' : '')));
        link.type = 'button';
        link.setAttribute('data-battle-id', identifier);
        link.setAttribute('data-ss-source-metric', metric);
        link.setAttribute('data-ss-extreme', statistic);
        var value = metric === 'battle_wn8' ? integer(reference.value) : number(reference.value);
        var description = [t('sort.extreme_battle', [sortMetricLabel({metric:metric, statistic:statistic}, false) + ': ' + value]),
            t('visual.vehicle') + ': ' + (reference.name || t('unknown.vehicle')),
            t('visual.map') + ': ' + (reference.map || t('unknown.map')),
            date(reference.started_at, false)].join('\n');
        link.setAttribute('aria-label', t('maps.open_battle') + ': ' + description);
        link.setAttribute('data-ss-help', description);
        link.setAttribute('aria-controls', helpTooltip.id);
        link.setAttribute('aria-expanded', 'false');
        link.title = description;
        if (label) { append(link, element('span', 'ss-metric-action-label', label)); }
        link.onclick = function () {
            // Permanent extrema are independent of sorting. Global summary links
            // also survive unrelated tab changes while their DOM remains live.
            if (!sameContext(context) || !root.contains(link) ||
                    (global ? !nodes.summary.contains(link) : state.group !== grouping || !nodes.groups.contains(link))) { return; }
            var scope = currentScope();
            if (!scope || scope.data_revision !== revision || state.orderIntent || orderingUnavailable(scope)) { return; }
            hideHelp();
            selectMapBattle(identifier, context);
        };
        return link;
    }
    function attachMetricBattleLinks(container, item, battle, global) {
        if (battle || !item || !item.extrema_battles) { return; }
        Array.prototype.forEach.call(container.querySelectorAll('.ss-metric-row[data-ss-metric]'), function (row) {
            var metric = row.getAttribute('data-ss-metric');
            [['min', 1], ['max', 3]].forEach(function (entry) {
                var cell = row.children[entry[1]];
                if (!cell || cell.querySelector('.ss-metric-battle-link')) { return; }
                var link = createMetricBattleLink(cell, item, metric, entry[0], global);
                if (!link) { return; }
                var figure = element('span', 'ss-extreme-figure');
                while (cell.firstChild && cell.firstChild !== link) { figure.appendChild(cell.firstChild); }
                link.appendChild(figure);
                cell.className += ' ss-extreme-cell';
            });
        });
    }
    function layoutGroupSortHost(card, item, options) {
        var host = card.querySelector('.ss-group-sort-host');
        if (!host) { return; }
        var badge = host.querySelector('.ss-group-sort-value'), label, value;
        if (badge) {
            var full = badge.textContent, partial = badge.querySelector('.ss-count-coverage');
            var metric = options.metric, statistic = t(options.statistic === 'avg' ? 'sort.avg' :
                options.statistic === 'sum' ? 'sort.sum' : 'metric.' + options.statistic);
            var name = metric === 'credits_costs' ? t('finance.costs') :
                creditMetric(metric) ? t('sort.' + canonicalMetric(metric) + '.caption') : t(metric === 'xp_base' ? 'sort.card_base_xp' : 'sort.card_received_xp');
            label = t('sort.metric_stat', [statistic, name]);
            value = netCreditMetric(metric) ? signed(cardSortValue(item, options)) : number(cardSortValue(item, options));
            clear(badge);
            append(badge, element('span', 'ss-group-sort-caption', label));
            append(badge, element('strong', 'ss-group-sort-number', value));
            if (partial) { badge.className += ' ss-group-sort-partial'; append(badge, partial); }
            badge.setAttribute('aria-label', full); badge.title = full;
            host.setAttribute('data-ss-sort-display', 'value'); host.title = full;
            return;
        }
        host.setAttribute('data-ss-sort-display', 'empty'); host.removeAttribute('title');
    }
    function appendGroupBatch(limit, page) {
        invalidateCardFlow();
        page = page || state.cardPages[0];
        var list = page.items;
        var end = Math.min(list.length, limit);
        var fragment = document.createDocumentFragment();
        var index, item, stats, group, header, identity, subtitle, heading, meta, headline, sortHost;
        var battle = state.group === 'battles', sorting = getOrder(currentScope());
        for (index = page.renderedCount; index < end; index += 1) {
            item = list[index];
            stats = item.stats || {};
            group = append(fragment, element('div', 'ss-group' + (battle ? ' ss-battle' : ' ss-aggregate')));
            group.setAttribute('role', 'listitem');
            group.setAttribute('data-group-id', String(item.id || ''));
            group.setAttribute('data-list-index', String(page.offset + index));
            group.setAttribute('data-layout-index', String(index));
            group.id = 'ss-card-' + state.group + '-' + (page.offset + index);
            var headlineWN8 = !battle && sorting.metric === 'battle_wn8' ? cardSortValue(item, sorting) : stats.wn8;
            paintWN8Card(group, headlineWN8);
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
            var hasBattleMap = battle && item.map_visual && item.map_visual.kind === 'map' && nativeVisualSource(item.map_visual.src, 'map');
            subtitle = battle ? date(item.started_at, true) + (hasBattleMap ? '' : ' · ' + (item.map || t('unknown.map'))) : '';
            meta = append(identity, element('div', 'ss-group-meta'));
            if (subtitle) { append(meta, element('div', 'ss-group-subtitle', subtitle)); }
            if (state.group === 'vehicles' || battle) { appendVehicleMetadata(meta, item, !battle); }
            freeXP(meta, stats);
            if (battle) {
                appendOutcome(header, item);
                appendBattleMap(header, item);
            } else {
                headline = append(header, element('div', 'ss-group-stats'));
                headlineBattleCount(headline, stats);
                headlineStat(headline, t('metric.win_rate'), rate(stats.win_rate), false, true).className += ' ss-group-rate';
                var wn8Headline = headlineStat(headline, sorting.metric === 'battle_wn8' ? sortMetricLabel(sorting, false) : t('metric.combined_wn8'),
                    integer(headlineWN8), true, true, headlineWN8);
                wn8Headline.className += ' ss-group-wn8-kpi';
                wn8Headline.setAttribute('data-wn8-kind', sorting.metric === 'battle_wn8' ? sorting.statistic : 'combined');
                if (sorting.metric !== 'battle_wn8') {
                    wn8Headline.title = t('help.wn8.combined');
                    help(group, t('help.wn8.combined'));
                }
                sortHost = append(headline, element('div', 'ss-group-sort-host'));
            }
            details(group, stats, false, battle, item);
            highlightCardSort(group, battle ? meta : sortHost, item, sorting, battle);
            if (!battle) { layoutGroupSortHost(group, item, sorting); }
            attachMetricBattleLinks(group, item, battle, false);
            if (battle) { attachBattleMore(group, header, item); }
            else if (state.group === 'maps' || state.group === 'vehicles') {
                attachMapMore(group, header, item);
                var more = header.querySelector('.ss-map-more-button');
                if (more) { headline.appendChild(more); headline.className += ' ss-group-stats-more'; }
            }
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
            queueCardFlow(); finishFeedAnchor(); finishBattleJump(); finishPageJump(); updatePinnedFilters();
        }
        function deferSettle() {
            try { state.cardFlowTimer = window.setTimeout(function () {
                if (token !== state.cardFlowToken || state.destroyed) { return; }
                state.cardFlowTimer = null; settle();
            }, 16); } catch (error) { state.cardFlowQueued = false; }
        }
        if (typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(function () {
                if (state.destroyed || token !== state.cardFlowToken) { return; }
                if (typeof window.requestAnimationFrame === 'function') { window.requestAnimationFrame(settle); }
                else { deferSettle(); }
            });
        } else { deferSettle(); }
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
            width = Math.max(0, resizePanelDimensions().width - scrollContentInset());
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
            if (state.group !== 'battles') {
                var compactHeadline = Math.min(width, cardWidth) < (state.group === 'tiers' ? 430 : 540);
                if (card.classList.contains('ss-compact-headline') !== compactHeadline) {
                    card.classList[compactHeadline ? 'add' : 'remove']('ss-compact-headline');
                }
            }
            if (state.group === 'battles') {
                // The card's assigned logical width is independent of its
                // caption layout; changing the class cannot change this input.
                var inlineCaptions = Math.min(width, cardWidth) >= 700;
                if (card.classList.contains('ss-battle-inline-captions') !== inlineCaptions) {
                    card.classList[inlineCaptions ? 'add' : 'remove']('ss-battle-inline-captions');
                }
            }
            layoutMoreColumns(card, Math.max(1, Math.min(width, cardWidth) - 14));
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
        state.feed = null; cancelPageJump();
        if (feed) { feed.prependAnchor = null; }
        if (feed && feed.pending) { cancelUITimer(feed.pending.timer); }
    }
    function captureFeedAnchor(feed) {
        if (feed.prependAnchor && (Date.now() >= feed.prependAnchor.deadline || feed.prependAnchor.attempts >= 40)) { feed.prependAnchor = null; }
        if (state.feed !== feed || state.renderedFeed !== feed || feed.prependAnchor || feed.topRequested ||
                state.pageJump || state.battleJump || !state.cardPages || !state.cardPages.length) { return; }
        var section = state.cardPages[0].section, box = section.getBoundingClientRect();
        var viewport = nodes.scroll.getBoundingClientRect(), rawTop = nodes.scroll.scrollTop;
        if (!(box.height > 1) || !(box.width > 1)) { return; }
        feed.prependAnchor = {section:section, position:box.top - viewport.top + rawTop,
            scroll:state.scrollTarget === null ? rawTop : state.scrollTarget, remaining:3, attempts:0, deadline:Date.now() + 2000};
    }
    function finishFeedAnchor(measured) {
        var feed = state.feed, anchor = feed && feed.prependAnchor;
        if (!anchor) { return; }
        if (state.destroyed || state.renderedFeed !== feed || feed.topRequested || state.pageJump || state.battleJump ||
                !nodes.groups.contains(anchor.section)) { feed.prependAnchor = null; return; }
        if (Date.now() >= anchor.deadline || anchor.attempts >= 40) { feed.prependAnchor = null; return; }
        var box = anchor.section.getBoundingClientRect(), viewport = nodes.scroll.getBoundingClientRect();
        var valid = box.height > 1 && box.width > 1, beforeAnchor = true;
        (state.cardPages || []).forEach(function (page) {
            if (page.section === anchor.section) { beforeAnchor = false; }
            if (!beforeAnchor) { return; }
            page.cards.forEach(function (card) {
                var rect = card.getBoundingClientRect();
                if (!(rect.height > 1) || !(rect.width > 1)) { valid = false; }
            });
        });
        if (valid) {
            state.scrollTarget = Math.max(0, anchor.scroll + box.top - viewport.top + nodes.scroll.scrollTop - anchor.position);
            nodes.scroll.scrollTop = state.scrollTarget;
        }
        // Native page/column heights can settle after the insertion frame.
        // A newer user intent clears this anchor before moving the viewport.
        if (measured) {
            anchor.attempts += 1;
            if ((valid && --anchor.remaining <= 0) || anchor.attempts >= 40) { feed.prependAnchor = null; }
            else { queueResize(); }
        }
    }
    function revealFeedTop(feed) {
        feed.prependAnchor = null; feed.topRequested = false; feed.navigationPage = null;
        if (feed.start !== 0) {
            // A direct jump need not download every intervening page. Keep
            // their cache entries, but render a contiguous window at page one.
            feed.start = 0; feed.last = 0; feed.current = 0; feed.version += 1;
        }
        cancelPageJump(); resetViewScroll();
    }
    function pageBoundary(feed, index, loading) {
        var section = element('div', 'ss-continuous-page');
        section.setAttribute('data-page-index', String(index));
        section.setAttribute('aria-label', t('page.status', [index + 1, feed.pages]));
        var divider = append(section, element('div', 'ss-page-divider'));
        append(divider, element('span', 'ss-page-divider-label', t('page.status', [index + 1, feed.pages])));
        var first = feed.group === 'battles' && feed.cache[index] && feed.cache[index][0];
        if (!loading && first && hasNumber(first.started_at)) {
            var firstDate = append(section, element('div', 'ss-page-first-battle', date(first.started_at, false)));
            firstDate.setAttribute('data-started-at', String(first.started_at));
        }
        if (loading) {
            var spinner = append(section, element('div', 'ss-page-spinner'));
            spinner.setAttribute('role', 'status'); spinner.setAttribute('aria-label', t('page.loading'));
            section.setAttribute('aria-busy', 'true');
        }
        return section;
    }
    function showFeedPending(feed) {
        if (state.feed !== feed) { return; }
        var prior = nodes.groups.querySelector('.ss-page-pending');
        var index = feed.pending ? feed.pending.page : feed.error;
        if ((index !== null && index < feed.start) || (prior && Number(prior.getAttribute('data-page-index')) < feed.start)) { captureFeedAnchor(feed); }
        var old = nodes.groups.querySelector('.ss-page-pending');
        if (old && old.parentNode) { old.parentNode.removeChild(old); }
        if (!feed.pending && feed.error === null) { finishFeedAnchor(); return; }
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
        finishFeedAnchor();
        if (feed.prependAnchor) { queueResize(); }
    }
    function requestFeedPage(feed, index, navigate) {
        if (state.destroyed || state.feed !== feed || feed.pending || index < 0 || index >= feed.pages) { return; }
        if (navigate) { cancelPageJump(); }
        if (Object.prototype.hasOwnProperty.call(feed.cache, index) && index >= feed.start - 1 && index <= feed.last + 1) {
            if (index < feed.start && !navigate) { captureFeedAnchor(feed); }
            feed.start = Math.min(feed.start, index); feed.last = Math.max(feed.last, index);
            feed.error = null;
            if (navigate) { beginPageJump(feed, index); }
            render(); return;
        }
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
            var ownedJump = state.pageJump && state.pageJump.feed === feed ? state.pageJump : null;
            var navigation = feed && feed.collectionKey === collectionKey && feed.pending && feed.pending.navigate ? feed.pending.page :
                feed && feed.collectionKey === collectionKey ? ownedJump ? ownedJump.page : feed.navigationPage : null;
            var navigationDeadline = ownedJump ? ownedJump.deadline : feed && feed.navigationDeadline;
            retireFeed();
            var start = state.feedForceStart !== null ? state.feedForceStart : feed && feed.collectionKey === collectionKey ? feed.start : meta.page;
            start = Math.max(0, Math.min(start, meta.pages - 1));
            var count = !state.battleJump && old ? Math.max(1, old.last - old.start + 1) : 1;
            var topRequested = feed && feed.collectionKey === collectionKey && feed.topRequested;
            feed = {key:key, collectionKey:collectionKey, contextKey:feedContextIdentity(), revision:revision, context:viewContext(), group:state.group, cache:{}, signatures:{}, pending:null,
                error:null, start:start, last:Math.min(meta.pages - 1, start + count - 1), current:start,
                pages:meta.pages, total:meta.total, size:meta.page_size || 40, version:0, navigationPage:null, navigationDeadline:null,
                topRequested:!!topRequested, prependAnchor:null};
            if (hasNumber(navigation)) {
                feed.navigationPage = Math.max(0, Math.min(navigation, meta.pages - 1));
                feed.navigationDeadline = navigationDeadline;
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
                if (meta.page < feed.start && !pending.navigate && !feed.topRequested) { captureFeedAnchor(feed); }
                cancelUITimer(pending.timer);
                feed.pending = null; feed.error = null;
                // A cancelled direct Top request may still fill its cache;
                // it must not splice a gap into the user's current window.
                if (meta.page >= feed.start - 1 && meta.page <= feed.last + 1) {
                    feed.start = Math.min(feed.start, meta.page); feed.last = Math.max(feed.last, meta.page);
                }
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
        if (feed.topRequested && Object.prototype.hasOwnProperty.call(feed.cache, 0)) { revealFeedTop(feed); }
        if (!feed.pending && feed.error === null && feed.topRequested) { requestFeedPage(feed, 0, false); }
        if (!feed.pending && feed.error === null && !feed.topRequested) {
            for (var index = feed.start; index <= feed.last; index += 1) {
                if (!Object.prototype.hasOwnProperty.call(feed.cache, index)) { requestFeedPage(feed, index, false); break; }
            }
            if (!feed.pending && hasNumber(feed.navigationPage)) {
                beginPageJump(feed, feed.navigationPage, feed.navigationDeadline);
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
        if (state.payload && state.payload.scopes) { renderFilterActivity(currentScope()); }
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
        var renderKey = [state.language, state.appearanceCSS, feed && feed.version].join('|');
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
        var emptyMarkers = nodes.groups.querySelectorAll('.ss-groups-empty');
        for (var emptyIndex = 0; emptyIndex < emptyMarkers.length; emptyIndex += 1) {
            if (emptyMarkers[emptyIndex].parentNode) { emptyMarkers[emptyIndex].parentNode.removeChild(emptyMarkers[emptyIndex]); }
        }
        if (!state.groupCards.length && complete) {
            append(state.cardPages[0] ? state.cardPages[0].lanes[0] : nodes.groups, element('p', 'ss-empty ss-groups-empty', t('groups.empty')));
        }
        layoutBattleCards(); finishFeedAnchor(); queueResize();
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
    function normalFlowScrollMaximum() {
        var scroll = nodes.scroll, content = nodes.groups;
        var origin = battleLayoutOffset(content, scroll), height = content.offsetHeight;
        if (origin === null || !hasNumber(height) || height < 0 ||
                (height <= 1 && state.groupCards && state.groupCards.length)) { return null; }
        var padding = 10 * (state.nativeScale || 1);
        try {
            var measured = parseFloat(window.getComputedStyle(scroll).paddingBottom);
            if (hasNumber(measured)) { padding = measured; }
        } catch (ignored) { /* Keep the shipped padding while native styles mount. */ }
        return Math.max(0, origin + height + padding - scroll.clientHeight);
    }
    function queuePinnedFilters() {
        if (state.destroyed || typeof window.requestAnimationFrame !== 'function') { return; }
        if (state.pinnedFilterWork) { state.pinnedFilterWork.frames = 0; return; }
        var work = {frames:0, attempts:0}; state.pinnedFilterWork = work;
        function settle() {
            if (state.destroyed || state.pinnedFilterWork !== work) { return; }
            // Native scroll getters can follow the event/paint by several
            // frames. Follow that acknowledgement without resizing the view,
            // rebuilding cards or loading another page inside this work.
            updatePinnedFilters(false, true);
            work.frames += 1; work.attempts += 1;
            // Eight frames cover ordinary native settlement. A mismatched
            // getter/paint may need longer, with one bounded frame budget.
            var pending = battleScrollPending({requestedOffset:nodes.scroll.scrollTop});
            if ((work.frames < 8 || (pending && work.attempts < 60)) &&
                    typeof window.requestAnimationFrame === 'function') { window.requestAnimationFrame(settle); }
            else { state.pinnedFilterWork = null; }
        }
        window.requestAnimationFrame(settle);
    }
    function updatePinnedFilters(recalculate, settling) {
        var panel = nodes['filter-panel'];
        if (!panel || state.destroyed) { return; }
        // A native target scroll can update rectangles before its getter, or
        // the reverse. Mixed samples would shrink the true content range and
        // clamp the owned destination back to its page divider.
        if (battleScrollPending(state.battleJump) || battleScrollPending(state.pageJump)) { return; }
        var viewport = nodes.scroll.getBoundingClientRect(), box = panel.getBoundingClientRect();
        if (!(box.height > 0) || !(viewport.height > 0)) { return; }
        var rawTop = nodes.scroll.scrollTop;
        var logicalTop = state.scrollTarget === null ? rawTop : state.scrollTarget;
        // offsetTop is normal-flow geometry: it excludes this panel's own
        // translation and cannot combine a previous scroll paint with a newer
        // getter. Never learn a new origin from a translated/scrolled rect.
        var origin = battleLayoutOffset(panel, nodes.scroll);
        if (origin !== null) { state.filterBase = Math.max(0, origin); }
        else if (!hasNumber(state.filterBase) && rawTop === 0 && !state.filterShift) {
            state.filterBase = Math.max(0, box.top - viewport.top);
        }
        if (!hasNumber(state.filterBase)) { if (!settling) { queuePinnedFilters(); } return; }
        var maximum = normalFlowScrollMaximum();
        // Translated filters add overflow but not results. Bounds come from
        // the same normal-flow coordinate system as the filter origin.
        if (maximum !== null) {
            logicalTop = Math.max(0, Math.min(logicalTop, maximum));
            if (state.scrollTarget !== null) { state.scrollTarget = logicalTop; }
            if (rawTop !== logicalTop) { nodes.scroll.scrollTop = logicalTop; }
        }
        var base = state.filterBase;
        var height = hasNumber(panel.offsetHeight) && panel.offsetHeight > 0 ? panel.offsetHeight : box.height;
        var shift = height < nodes.scroll.clientHeight - 30 * state.nativeScale ? Math.max(0, logicalTop - base) : 0;
        if (state.filterShift !== shift) { state.filterShift = shift; panel.style.transform = shift ? 'translateY(' + shift + 'px)' : ''; }
        if (panel.classList.contains('is-pinned') !== (shift > 0)) { panel.classList[shift > 0 ? 'add' : 'remove']('is-pinned'); }
        if (nodes['scroll-top']) {
            nodes['scroll-top'].style.display = logicalTop > 60 * state.nativeScale ? 'flex' : 'none';
            nodes['scroll-top'].style.bottom = Math.max(48 * state.nativeScale,
                root.getBoundingClientRect().bottom - viewport.bottom + 12 * state.nativeScale) + 'px';
        }
        var feed = state.renderedFeed;
        if (feed && state.cardPages && state.cardPages.length) {
            var current = state.cardPages[0].index;
            state.cardPages.forEach(function (page) {
                var pageOrigin = battleLayoutOffset(page.section, nodes.scroll);
                if (pageOrigin !== null ? pageOrigin <= logicalTop + height + 24 * state.nativeScale :
                        page.section.getBoundingClientRect().top <= viewport.top + height + 24 * state.nativeScale) { current = page.index; }
            });
            // A short final page cannot align its divider with the pinned
            // bar: the scroll range ends first. It is still the current page.
            if (maximum !== null && logicalTop >= maximum - 2 * state.nativeScale) {
                current = state.cardPages[state.cardPages.length - 1].index;
            }
            if (!state.pageJump || state.pageJump.feed !== feed) { feed.current = current; }
            updateFeedControls();
        }
        syncScrollbar();
        if (!settling) { queuePinnedFilters(); }
    }
    function beginPageJump(feed, page, deadline) {
        cancelPageJump();
        feed.prependAnchor = null; feed.navigationPage = null; feed.navigationDeadline = null;
        feed.current = page;
        state.pageJump = {feed:feed, page:page, attempts:0,
            deadline:hasNumber(deadline) ? deadline : Date.now() + 10000,
            lastOffset:null, settledSince:null, stable:0, target:null, requestedOffset:null};
        updateFeedControls();
    }
    function retryPageJump(jump) {
        if (state.pageJump !== jump || state.pageJumpTimer !== null) { return; }
        if (Date.now() >= jump.deadline || jump.attempts >= 100) { cancelPageJump(); return; }
        jump.attempts += 1;
        var timer = window.setTimeout(function () {
            if (state.pageJumpTimer === timer) { state.pageJumpTimer = null; }
            if (state.pageJump === jump && !state.destroyed) { finishPageJump(); }
        }, 100);
        state.pageJumpTimer = timer;
    }
    function finishPageJump() {
        var jump = state.pageJump;
        // A battle destination is more specific than its containing page.
        // Retire an older page jump so it cannot replace card alignment later.
        if (state.battleJump) {
            cancelPageJump();
            if (state.feed) { state.feed.navigationPage = null; }
            return;
        }
        if (!jump) { return; }
        if (state.destroyed || jump.feed !== state.feed || !sameContext(jump.feed.context) ||
                Date.now() >= jump.deadline || jump.attempts >= 100) { cancelPageJump(); return; }
        if (jump.feed !== state.renderedFeed || state.cardFlowQueued || state.groupMinHeight || state.feedStaging ||
                nodes.groups.getAttribute('aria-busy') === 'true') { retryPageJump(jump); return; }
        // A native setter and its rectangles can acknowledge different frames.
        // Keep the destination until both describe the same scroll position.
        if (battleScrollPending(jump)) {
            // A setter issued before the native content range grows can be
            // clamped or dropped. Reissue the owned value without combining
            // an old getter with a newer rectangle to derive another target.
            state.scrollTarget = jump.requestedOffset;
            nodes.scroll.scrollTop = jump.requestedOffset;
            retryPageJump(jump); return;
        }
        jump.requestedOffset = null;
        var target = null;
        (state.cardPages || []).some(function (page) { if (page.index === jump.page) { target = page.section; return true; } return false; });
        var scroll = nodes.scroll, box = target && target.getBoundingClientRect(), viewport = scroll.getBoundingClientRect();
        function validRect(rect) {
            return rect && hasNumber(rect.top) && hasNumber(rect.width) && hasNumber(rect.height) && rect.width > 1 && rect.height > 1;
        }
        if (!validRect(box) || !validRect(viewport)) { retryPageJump(jump); return; }
        var scale = state.nativeScale || 1, inset = pinnedFilterHeight() + 8 * scale;
        var layoutOffset = battleLayoutOffset(target, scroll), maximum = scrollbarMetrics().maximum;
        var offset = Math.max(0, Math.min(maximum,
            (layoutOffset === null ? scroll.scrollTop + box.top - viewport.top : layoutOffset) - inset));
        var now = Date.now();
        if (jump.target !== target || jump.lastOffset === null || Math.abs(jump.lastOffset - offset) > scale) {
            jump.target = target; jump.lastOffset = offset; jump.settledSince = now; jump.stable = 0;
        }
        jump.requestedOffset = offset;
        state.scrollTarget = offset; scroll.scrollTop = offset;
        var aligned = target.getBoundingClientRect(), acknowledged = !battleScrollPending(jump);
        var markerTop = viewport.top + inset;
        var alignedMarker = validRect(aligned) && (Math.abs(aligned.top - markerTop) <= scale ||
            ((offset <= scale || offset >= maximum - scale) && aligned.top >= markerTop - scale && aligned.top < viewport.bottom - scale));
        if (alignedMarker && acknowledged && Math.abs(scroll.scrollTop - offset) <= scale) { jump.stable += 1; }
        else { jump.stable = 0; jump.settledSince = now; }
        if (acknowledged) { updatePinnedFilters(true); syncScrollbar(); }
        if (jump.stable >= 3 && now - jump.settledSince >= 500) { cancelPageJump(); return; }
        retryPageJump(jump);
    }
    function loadNearEdges() {
        if (state.destroyed) { return; }
        updatePinnedFilters();
        if (state.renderedFeed && state.feed === state.renderedFeed) {
            var feed = state.feed;
            if (feed.pending || feed.error !== null || feed.topRequested || state.pageJump || state.battleJump) { return; }
            var first = state.cardPages && state.cardPages[0], viewport = nodes.scroll.getBoundingClientRect();
            var firstTop = first && first.section.getBoundingClientRect().top;
            var threshold = 200 * state.nativeScale;
            if (feed.start > 0 && first && firstTop >= viewport.top + pinnedFilterHeight() - threshold && firstTop <= viewport.bottom + threshold) {
                requestFeedPage(feed, feed.start - 1, false); return;
            }
            var remaining = nodes.scroll.scrollHeight - nodes.scroll.scrollTop - nodes.scroll.clientHeight;
            if (remaining <= threshold && feed.last + 1 < feed.pages) { requestFeedPage(feed, feed.last + 1, false); }
        } else if (!state.feed && state.renderedCount < state.list.length &&
                nodes.scroll.scrollHeight - nodes.scroll.scrollTop - nodes.scroll.clientHeight <= 200 * state.nativeScale) {
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
        loadNearEdges();
    }
    function setStatus(message) { nodes.status.textContent = message; }
    function setActionError(message) {
        state.actionError = message;
        // Refresh paint from the same pending owners; a failed command must
        // reveal its error without cancelling an unrelated projection or page.
        renderFilterActivity(state.payload && state.payload.scopes ? currentScope() : null);
        setStatus(message);
    }
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
        cancelPageJump();
        if (state.feed) { state.feed.navigationPage = null; }
        if (state.feed) { state.feed.topRequested = false; state.feed.prependAnchor = null; }
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
        hideMapPreview();
        state.rendering = true;
        try { renderView(); } finally { state.rendering = false; }
    }
    function renderView() {
        var payload = state.payload;
        if (!payload || !payload.scopes) { return; }
        var version = typeof payload.version === 'string' && payload.version.length <= 64 &&
            /^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$/.test(payload.version) ? payload.version : '';
        nodes.version.textContent = version ? 'v' + version : '';
        nodes.version.style.display = version ? 'block' : 'none';
        nodes.version.setAttribute('title', version ? 'Session Stats ' + version : '');
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
        renderFilterActivity(scope);
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
                renderSelects(scope); setStatus(state.actionError || loadError || t('core.loading'));
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
            setStatus(state.actionError || loadingText);
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
                    if (actual && !orderingUnavailable(intended, value) && ['metric', 'statistic', 'direction', 'chronology'].some(function (key) {
                        return actual[key] !== intent.options[key];
                    })) { return true; }
                }
                state.orderIntent = null;
            }
            if (historyOnlyUpdate(value)) { return true; }
            if (state.payload && state.payload.account_key !== value.account_key) {
                showReset(false);
                resetWindowSettings();
                state.openBattles = {};
                state.openMaps = {};
                state.customDates = {}; state.customRangeKey = null;
                clearBattleTarget(); retireFeed(); state.renderedFeed = null; state.orderIntent = null;
                state.cardPages = []; state.groupCards = []; state.feedForceStart = null;
                state.filterBase = null;
                resetViewScroll();
                cancelBattleNavigation();
                state.timelineSignature = null;
                // Cleanup can request layout using the old snapshot. Hydrate
                // the new account's size only after those callbacks finish.
                state.logicalSize = null;
            }
            state.payload = value;
            state.actionError = null;
            applyLanguage(value.localization);
            applyAppearance(value.appearance);
            render();
            if (state.bound) { queueResize(); }
            return true;
        } catch (error) {
            state.orderIntent = null;
            setActionError(t('error.snapshot'));
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
        function accepts(list) { return list && (!list.chronology || list.chronology === getOrder(scope).chronology); }
        (scope[state.group] || []).forEach(function (item) { if (accepts(item.battle_list)) { items['$' + item.id] = item.battle_list; } });
        if (patch && patch.kind === state.group && accepts(patch.battle_list)) { items['$' + patch.id] = patch.battle_list; }
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
                setActionError(t('error.action'));
            }
            return false;
        }
        if (action !== 'resize' && action !== 'diagnostic' && action !== 'viewport') {
            setActionError(t('error.connection'));
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
        state.orderIntent = null; if (state.scope !== scope) { clearBattleTarget(); state.feedForceStart = 0; }
        state.scope = scope; state.loadedCount = 40;
        showReset(false); render();
    }
    function switchGroup(group) {
        closeSelect(false);
        cancelBattleNavigation();
        state.orderIntent = null; if (state.group !== group) { clearBattleTarget(); state.feedForceStart = 0; }
        if (state.group !== group) { state.loadedCount = 40; }
        state.group = group; render();
    }
    function changePage(direction) {
        if (state.destroyed || !state.payload || !state.payload.scopes) { return; }
        var feed = state.renderedFeed;
        if (!feed || state.feed !== feed || feed.pending) { return; }
        var page = feed.current + direction;
        if (page < 0 || page >= feed.pages) { return; }
        cancelBattleNavigation(); cancelPageJump(); clearBattleTarget(); feed.prependAnchor = null; feed.topRequested = false;
        if (Object.prototype.hasOwnProperty.call(feed.cache, page)) {
            beginPageJump(feed, page);
            if (page < feed.start || page > feed.last) {
                feed.start = Math.min(feed.start, page); feed.last = Math.max(feed.last, page); render();
            } else { finishPageJump(); }
        } else { requestFeedPage(feed, page, true); }
    }
    document.getElementById('ss-page-previous').onclick = function () { changePage(-1); };
    document.getElementById('ss-page-next').onclick = function () { changePage(1); };
    if (nodes['scroll-top']) { nodes['scroll-top'].onclick = function () {
        cancelBattleNavigation(); clearBattleTarget(); cancelPageJump();
        if (state.feed) {
            var feed = state.feed; feed.prependAnchor = null;
            // Keep the requested data, but let Top supersede its old destination.
            feed.navigationPage = null; feed.errorNavigate = false;
            if (feed.pending) { feed.pending.navigate = false; }
            if (feed.start > 0) {
                feed.topRequested = true; feed.error = null;
                if (feed.pending && feed.pending.page !== 0) { cancelUITimer(feed.pending.timer); feed.pending = null; }
                if (Object.prototype.hasOwnProperty.call(feed.cache, 0)) { revealFeedTop(feed); render(); }
                else if (!feed.pending) { requestFeedPage(feed, 0, false); }
            }
        }
        resetViewScroll(); updatePinnedFilters();
        queueResize();
    }; }
    document.getElementById('ss-scope-launch').onclick = function () { switchScope('launch'); };
    document.getElementById('ss-scope-manual').onclick = function () { switchScope('manual'); };
    document.getElementById('ss-scope-instance').onclick = function () { switchScope('instance'); };
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
    nodes.scroll.addEventListener('scroll', queueScrollEdges);
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
        var rect = root.getBoundingClientRect(), bounds = windowSizeBounds();
        // A stale pre-minimum native rectangle must not resize the Wulf
        // surface below the dimensions already requested by the document.
        var validWidth = hasNumber(rect.width) && rect.width >= bounds.minWidth * state.nativeScale - 0.5 && rect.width <= bounds.maxWidth * state.nativeScale + 0.5;
        var validHeight = hasNumber(rect.height) && rect.height >= bounds.minHeight * state.nativeScale - 0.5 && rect.height <= bounds.maxHeight * state.nativeScale + 0.5;
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
    function windowSizeBounds() {
        var viewport = state.payload && state.payload.viewport, scale = state.nativeScale || 1;
        var knownWidth = viewport && hasNumber(viewport.width) && viewport.width > 1;
        var knownHeight = viewport && hasNumber(viewport.height) && viewport.height > 1;
        var width = knownWidth ? viewport.width : window.innerWidth;
        var height = knownHeight ? viewport.height : window.innerHeight;
        if (!hasNumber(width) || width <= 1) { width = 700 * scale; }
        if (!hasNumber(height) || height <= 1) { height = 730 * scale; }
        var maximumWidth = Math.max(1, width - (state.bound && knownWidth ? 20 : 0)) / scale;
        var maximumHeight = Math.max(1, height - (state.bound && knownHeight ? 20 : 0)) / scale;
        return {maxWidth:maximumWidth, maxHeight:maximumHeight,
            minWidth:Math.min(550, maximumWidth), minHeight:Math.min(730, maximumHeight)};
    }
    function scrollContentInset() {
        var scale = state.nativeScale || 1, inset = 38;
        try {
            var style = window.getComputedStyle(nodes.scroll), left = parseFloat(style.paddingLeft), right = parseFloat(style.paddingRight);
            var box = nodes.scroll.getBoundingClientRect(), gutter = hasNumber(nodes.scroll.clientWidth) ? Math.max(0, box.width - nodes.scroll.clientWidth) : 0;
            if (hasNumber(left) && hasNumber(right) && hasNumber(gutter)) { inset = 2 + (left + right + gutter) / scale; }
        } catch (ignored) { /* The owned rail's shipped padding is the first-layout fallback. */ }
        return inset;
    }
    function setLogicalSize(width, height, edge) {
        var bounds = windowSizeBounds();
        state.logicalSize = {
            width: Math.min(bounds.maxWidth, Math.max(bounds.minWidth, width)),
            height: Math.min(bounds.maxHeight, Math.max(bounds.minHeight, height))
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
        var bounds = windowSizeBounds();
        width = Math.min(bounds.maxWidth, Math.max(bounds.minWidth, width));
        height = Math.min(bounds.maxHeight, Math.max(bounds.minHeight, height));
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

    function scrollbarMetrics() {
        var scroll = nodes.scroll, viewport = scroll.getBoundingClientRect(), scale = state.nativeScale || 1;
        var maximum = normalFlowScrollMaximum();
        if (maximum === null) {
            maximum = Math.max(0, scroll.scrollHeight - scroll.clientHeight);
            var content = nodes.groups.getBoundingClientRect(), padding = 10 * scale;
            try {
                var measuredPadding = parseFloat(window.getComputedStyle(scroll).paddingBottom);
                if (hasNumber(measuredPadding)) { padding = measuredPadding; }
            } catch (ignored) { /* Native styles can mount after the first scroll measurement. */ }
            // Older surfaces without offset-parent geometry retain their
            // measured range; translated filters still are not more results.
            if (content.width > 0 && hasNumber(content.bottom) &&
                    (content.height > 1 || !state.groupCards || !state.groupCards.length)) {
                maximum = Math.max(0, content.bottom - viewport.top + scroll.scrollTop + padding - scroll.clientHeight);
            }
        }
        var logical = state.scrollTarget === null ? scroll.scrollTop : state.scrollTarget;
        var top = Math.max(0, Math.min(maximum, logical));
        var height = Math.max(0, viewport.height - 6 * scale);
        var thumb = Math.min(height, Math.max(24 * scale, height * scroll.clientHeight / Math.max(1, scroll.clientHeight + maximum)));
        return {viewport:viewport, maximum:maximum, top:top, height:height, thumb:thumb,
            travel:Math.max(0, height - thumb), scale:scale};
    }
    function syncScrollbar() {
        var rail = nodes.scrollbar, thumb = nodes['scrollbar-thumb'];
        if (state.destroyed || !rail || !thumb) { return; }
        var metrics = scrollbarMetrics(), rootBox = root.getBoundingClientRect();
        if (!(metrics.viewport.height > 1) || !(metrics.viewport.width > 1)) { rail.style.display = 'none'; return; }
        rail.style.display = 'block';
        rail.style.top = (metrics.viewport.top - rootBox.top + 2 * metrics.scale) + 'px';
        rail.style.height = Math.max(1, metrics.height + 2 * metrics.scale) + 'px';
        thumb.style.height = metrics.thumb + 'px';
        thumb.style.top = (metrics.maximum ? metrics.top / metrics.maximum * metrics.travel : 0) + 'px';
        var percent = metrics.maximum ? Math.round(metrics.top / metrics.maximum * 100) : 0;
        rail.setAttribute('aria-valuenow', String(percent));
        rail.setAttribute('aria-valuetext', String(percent) + '%');
        rail.setAttribute('aria-disabled', String(metrics.maximum <= 0));
        rail.setAttribute('tabindex', metrics.maximum > 0 ? '0' : '-1');
    }
    function queueScrollEdges() {
        if (state.destroyed) { return; }
        var pending = state.scrollbarWork;
        if (pending && pending.view === state.viewKey && pending.feed === state.feed) { return; }
        var work = {view:state.viewKey, feed:state.feed};
        state.scrollbarWork = work;
        function finish() {
            if (state.scrollbarWork !== work) { return; }
            state.scrollbarWork = null;
            if (state.destroyed || state.scrollbarDrag || work.view !== state.viewKey || work.feed !== state.feed) { return; }
            // Loading a page may replace native content. Never perform that
            // work inside a rail press/move callback or while its drag is held.
            loadNearEdges(); syncScrollbar();
        }
        if (typeof window.requestAnimationFrame === 'function') { window.requestAnimationFrame(finish); }
        else { window.setTimeout(finish, 0); }
    }
    function scrollFromScrollbar(value) {
        if (state.destroyed || state.dialog || !hasNumber(value)) { return; }
        onScrollIntent({type:'scrollbar', target:nodes.scroll});
        var metrics = scrollbarMetrics();
        if (!hasNumber(metrics.maximum)) { return; }
        state.scrollTarget = Math.max(0, Math.min(metrics.maximum, value));
        nodes.scroll.scrollTop = state.scrollTarget;
        // Scrolling does not resize the native view. Only content changes need
        // a full layout, and their normal render path already schedules it.
        syncScrollbar(); queueScrollEdges();
    }
    function beginScrollbar(event) {
        if (event.button !== 0 || !hasNumber(event.clientY) || state.destroyed || state.dialog || state.scrollbarDrag || state.resize || state.backgroundDrag || state.dragging) { return; }
        var rail = nodes.scrollbar, thumb = nodes['scrollbar-thumb'], metrics = scrollbarMetrics();
        if (!rail || !thumb || !(metrics.maximum > 0)) { return; }
        onScrollIntent({type:'scrollbar', target:nodes.scroll});
        consumeResizeInput(event);
        if (!state.bound) { focusControl(rail); }
        var box = thumb.getBoundingClientRect(), inThumb = event.target === thumb || thumb.contains(event.target);
        state.scrollbarDrag = {pointer:event.pointerId, offset:event.clientY - box.top, track:!inThumb};
        rail.classList.add('is-dragging');
        // Native capture methods can enter the host engine and are unnecessary
        // here. Owned document listeners and the missed-release guard retain
        // the gesture without a native capture/release round trip.
        if (!inThumb) { scrollFromScrollbar(metrics.top + (event.clientY < box.top ? -1 : 1) * nodes.scroll.clientHeight * 0.9); }
    }
    function moveScrollbar(event) {
        var drag = state.scrollbarDrag;
        if (!drag || state.destroyed || (drag.pointer !== undefined && event.pointerId !== undefined && drag.pointer !== event.pointerId)) { return; }
        // A native surface may miss the outside release when pointer capture
        // is unavailable. The returning DOM move must not revive that drag.
        if (hasNumber(event.buttons) && !(event.buttons & 1) && event.type !== 'mouseup' && event.type !== 'pointerup') {
            endScrollbar(); return;
        }
        consumeResizeInput(event);
        if (drag.track || !hasNumber(event.clientY)) { return; }
        var metrics = scrollbarMetrics(), box = nodes.scrollbar.getBoundingClientRect();
        if (metrics.travel > 0) {
            scrollFromScrollbar((event.clientY - box.top - metrics.scale - drag.offset) / metrics.travel * metrics.maximum);
        }
    }
    function endScrollbar(event) {
        var drag = state.scrollbarDrag, rail = nodes.scrollbar;
        if (!drag || (event && drag.pointer !== undefined && event.pointerId !== undefined && drag.pointer !== event.pointerId)) { return; }
        if (event && (event.type === 'mouseup' || event.type === 'pointerup') && hasNumber(event.button) && event.button !== 0) { return; }
        if (event && (event.type === 'mouseup' || event.type === 'pointerup')) { moveScrollbar(event); }
        state.scrollbarDrag = null;
        if (rail) {
            rail.classList.remove('is-dragging');
        }
        queueScrollEdges();
    }
    function scrollbarKey(event) {
        if (state.destroyed || state.dialog) { return; }
        var key = event.key || ({38:'ArrowUp',40:'ArrowDown',33:'PageUp',34:'PageDown',36:'Home',35:'End',32:' '})[event.keyCode];
        var metrics = scrollbarMetrics(), value = metrics.top, step = 40 * metrics.scale;
        if (key === 'Home') { value = 0; }
        else if (key === 'End') { value = metrics.maximum; }
        else if (key === 'ArrowUp') { value -= step; }
        else if (key === 'ArrowDown') { value += step; }
        else if (key === 'PageUp' || (key === ' ' && event.shiftKey)) { value -= nodes.scroll.clientHeight * 0.9; }
        else if (key === 'PageDown' || key === ' ') { value += nodes.scroll.clientHeight * 0.9; }
        else { return; }
        consumeResizeInput(event); scrollFromScrollbar(value);
    }
    function scrollbarWheel(event) {
        if (state.destroyed || state.dialog || !event || event.defaultPrevented || event.cancelable === false ||
                !hasNumber(event.deltaY) || !event.deltaY || event.shiftKey ||
                (hasNumber(event.deltaX) && Math.abs(event.deltaX) >= Math.abs(event.deltaY))) { return; }
        var metrics = scrollbarMetrics(), movement = event.deltaY;
        if (state.bound) { movement = (movement < 0 ? 1 : -1) * nodes.scroll.clientHeight / 4; }
        else if (event.deltaMode === 1) { movement *= 20 * metrics.scale; }
        if (event.deltaMode === 2) { movement = (state.bound ? -1 : 1) * event.deltaY * nodes.scroll.clientHeight; }
        consumeResizeInput(event); scrollFromScrollbar(metrics.top + movement * state.scrollSpeed);
    }
    function bindScrollbar(on) {
        var rail = nodes.scrollbar, method = on ? 'addEventListener' : 'removeEventListener';
        if (rail) {
            rail[method]('mousedown', beginScrollbar); rail[method]('pointerdown', beginScrollbar);
            rail[method]('keydown', scrollbarKey); rail[method]('wheel', scrollbarWheel);
        }
        document[method]('mousemove', moveScrollbar); document[method]('pointermove', moveScrollbar);
        document[method]('mouseup', endScrollbar); document[method]('pointerup', endScrollbar); document[method]('pointercancel', endScrollbar);
        nodes.scroll[method]('scroll', syncScrollbar);
        window[method]('blur', endScrollbar);
        if (!on) { endScrollbar(); state.scrollbarWork = null; }
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
        if (state.nativeScale !== scale) { endResize(); endScrollbar(); }
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
        var bounds = windowSizeBounds(), displaySize = resizePanelDimensions();
        root.style.width = displaySize.width + 'rem'; root.style.height = displaySize.height + 'rem';
        root.style.maxWidth = bounds.maxWidth * scale + 'px'; root.style.maxHeight = bounds.maxHeight * scale + 'px';
        root.style.minWidth = bounds.minWidth * scale + 'px'; root.style.minHeight = bounds.minHeight * scale + 'px';
        if (state.resizeQueued) { return; }
        state.resizeQueued = true;
        var ticket = ++state.resizeMeasureToken;
        function measure() {
            if (state.destroyed || ticket !== state.resizeMeasureToken) { return; }
            state.resizeQueued = false;
            layoutResizeGrips();
            layoutSummary();
            layoutFilterControls(force);
            layoutBattleCards();
            resizeNative();
            positionDatePicker();
            if (state.groupMinHeight) {
                nodes.groups.style.minHeight = ''; state.groupMinHeight = false;
                // Native flow/clamping may settle after this measurement.
                queueResize();
            }
            finishFeedAnchor(true);
            restoreViewScroll();
            finishBattleJump();
            finishPageJump();
            updatePinnedFilters(true);
            syncScrollbar();
        }
        if (typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(function () {
                if (state.destroyed || ticket !== state.resizeMeasureToken) { return; }
                if (typeof window.requestAnimationFrame === 'function') { window.requestAnimationFrame(measure); }
                else { measure(); }
            });
        } else { measure(); }
    }
    bindResize(true);
    bindScrollbar(true);
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
        renderFilterActivity(null);
        state.pinnedFilterWork = null;
        cancelFilterLayout();
        cancelBattleNavigation();
        clearBattleTarget(); retireFeed(); state.renderedFeed = null;
        nodes.groups.style.minHeight = ''; state.groupMinHeight = false;
        document.removeEventListener('click', targetClick, true);
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
        hideMapPreview();
        root.removeEventListener('mouseover', hoverMapPreview);
        root.removeEventListener('mouseout', leaveMapPreview);
        root.removeEventListener('focusin', hoverMapPreview);
        root.removeEventListener('focusout', leaveMapPreview);
        root.removeEventListener('keydown', mapPreviewKey);
        nodes.scroll.removeEventListener('scroll', hideMapPreview);
        window.removeEventListener('blur', hideMapPreview);
        window.removeEventListener('resize', hideMapPreview);
        root.removeEventListener('mousemove', waitForHelp);
        root.removeEventListener('mouseout', leaveHelp);
        root.removeEventListener('focusin', focusHelp);
        root.removeEventListener('focusout', leaveHelp);
        root.removeEventListener('mousedown', pressHelp);
        root.removeEventListener('click', clickHelp);
        nodes.scroll.removeEventListener('scroll', hideHelp);
        nodes.scroll.removeEventListener('scroll', queueScrollEdges);
        nodes.scroll.removeEventListener('wheel', onScrollIntent, true);
        nodes.scroll.removeEventListener('mousedown', onScrollIntent, true);
        nodes.scroll.removeEventListener('keydown', onScrollIntent, true);
        window.removeEventListener('blur', hideHelp);
        window.removeEventListener('resize', hideHelp);
        closeSelect(false);
        closeDatePicker(false);
        document.removeEventListener('mousedown', outsideDatePicker, true);
        document.removeEventListener('keydown', datePickerKey, true);
        window.removeEventListener('resize', positionDatePicker);
        document.removeEventListener('mousedown',outsideSelect);
        clearAppearance();
        state.scrollSpeed = 1;
        endNativeDrag();
        endResize();
        if (state.resizeTimer !== null) { window.clearTimeout(state.resizeTimer); state.resizeTimer = null; }
        state.resizeMeasureToken += 1;
        state.resizeQueued = false;
        bindResize(false);
        bindScrollbar(false);
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
        getState: function () { return { scope:state.scope, group:state.group, nativeBound:state.bound, dragging:state.dragging }; },
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
