/* Preview only: synthetic snapshots calculated by the actual Python core. */
(function () {
    'use strict';
    var fixture = window.GRZ_DEMO_FIXTURES;
    var current = fixture.normal;
    var currentName = 'normal';
    var language = current.localization && current.localization.language || 'en';
    var selectedLanguage = current.localization && current.localization.selected || language;
    var historyRequests = Object.create(null);
    var pageSize = 10;
    function copy(snapshot) { return JSON.parse(JSON.stringify(snapshot)); }
    function localized(name) {
        var variants = window.GRZ_DEMO_LOCALIZED;
        var snapshot = copy(variants && variants[language] && variants[language][name] || fixture[name]);
        if (snapshot.localization) { snapshot.localization.selected = selectedLanguage; }
        Object.keys(historyRequests).forEach(function (key) { applyHistory(snapshot, historyRequests[key]); });
        return snapshot;
    }
    function requestScope(snapshot, args) {
        var scope = snapshot.scopes[args.scope];
        return scope && args.account_key === snapshot.account_key && args.period_id === scope.period_id ? scope : null;
    }
    function applyHistory(snapshot, args) {
        var scope = requestScope(snapshot, args);
        var vehicle = args.action === 'vehicle_battles';
        var group = vehicle ? 'vehicles' : 'maps';
        var id = args[vehicle ? 'vehicle_id' : 'map_id'];
        if (!scope) { return false; }
        var card = scope[group].find(function (item) { return String(item.id) === id; });
        if (!card) { return false; }
        var rows = scope.battles.filter(function (battle) {
            return vehicle ? String(battle.vehicle_id) === id || (battle.vehicle_id == null && battle.name === card.name) :
                String(battle.map_id) === id;
        });
        if (args.chronology === 'oldest' || args.chronology === 'last_asc') { rows.reverse(); }
        var pages = Math.max(1, Math.ceil(rows.length / pageSize));
        var page = Math.max(0, Math.min(pages - 1, Math.floor(Number(args.page) || 0)));
        card.battle_list = {page:page, pages:pages, total:rows.length, page_size:pageSize, chronology:args.chronology,
            items:rows.slice(page * pageSize, (page + 1) * pageSize).map(function (battle) {
                return {id:battle.id, name:battle.name, map:battle.map, started_at:battle.started_at,
                    outcome:battle.outcome, wn8:battle.stats.wn8_count === 1 ? battle.stats.wn8 : null};
            })};
        return true;
    }
    var panel = document.getElementById('grz-session-stats');
    window.GRZSessionStats.onAction = function (args) {
        if (args.action === 'language') {
            var code = args.language === 'auto' ? 'en' : args.language;
            var catalog = window.GRZ_DEMO_LANGUAGES && window.GRZ_DEMO_LANGUAGES.languages[code];
            if (catalog) {
                language = code; selectedLanguage = args.language; current = localized(currentName);
                current.localization = current.localization || {};
                current.localization.language = code; current.localization.selected = selectedLanguage; current.localization.messages = catalog;
                window.GRZSessionStats.update(current);
            }
        }
        if (args.action === 'map_battles' || args.action === 'vehicle_battles') {
            var history = copy(current);
            if (applyHistory(history, args)) {
                historyRequests[JSON.stringify([args.scope, args.period_id, args.action, args.map_id || args.vehicle_id])] = args;
                current = history;
                window.GRZSessionStats.update(current);
            }
        }
        if (args.action === 'battle_select') {
            var selection = copy(current);
            var scope = requestScope(selection, args);
            if (scope && scope.battles.some(function (battle) { return String(battle.id) === args.id; })) {
                scope.battle_focus = {id:args.id, request_id:args.request_id};
                current = selection;
                window.GRZSessionStats.update(current);
            }
        }
        if (args.action === 'reset') { currentName = 'reset'; current = localized(currentName); }
        if (args.action === 'close') { panel.style.display = 'none'; }
        if (args.action === 'refresh' || args.action === 'reset') {
            window.GRZSessionStats.update(current);
        }
    };
    document.getElementById('demo-reopen').onclick = function () { panel.style.display = 'flex'; };
    document.getElementById('demo-restart').onclick = function () {
        historyRequests = Object.create(null);
        currentName = 'normal'; current = localized(currentName);
        panel.style.display = 'flex';
        window.GRZSessionStats.update(current);
    };
    window.GRZSessionStats.update(current);
}());
