/* Preview only: synthetic snapshots calculated by the actual Python core. */
(function () {
    'use strict';
    var fixture = window.GRZ_DEMO_FIXTURES;
    var current = fixture.normal;
    var currentName = 'normal';
    var language = current.localization && current.localization.language || 'en';
    function localized(name) {
        var variants = window.GRZ_DEMO_LOCALIZED;
        return variants && variants[language] && variants[language][name] || fixture[name];
    }
    var panel = document.getElementById('grz-session-stats');
    window.GRZSessionStats.onAction = function (args) {
        if (args.action === 'language') {
            var code = args.language === 'auto' ? 'en' : args.language;
            var catalog = window.GRZ_DEMO_LANGUAGES.languages[code];
            if (catalog) {
                language = code; current = localized(currentName);
                current.localization = current.localization || {};
                current.localization.language = code; current.localization.selected = args.language; current.localization.messages = catalog;
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
        currentName = 'normal'; current = localized(currentName);
        panel.style.display = 'flex';
        window.GRZSessionStats.update(current);
    };
    window.GRZSessionStats.update(current);
}());
