/* Preview only: synthetic snapshots calculated by the actual Python core. */
(function () {
    'use strict';
    var fixture = window.GRZ_DEMO_FIXTURES;
    var current = fixture.normal;
    var panel = document.getElementById('grz-session-stats');
    window.GRZSessionStats.onAction = function (args) {
        if (args.action === 'language') {
            var code = args.language === 'auto' ? 'en' : args.language;
            var catalog = window.GRZ_DEMO_LANGUAGES.languages[code];
            if (catalog) { current.localization = {language:code,selected:args.language,messages:catalog}; window.GRZSessionStats.update(current); }
        }
        if (args.action === 'reset') { current = fixture.reset; }
        if (args.action === 'close') { panel.style.display = 'none'; }
        if (args.action === 'refresh' || args.action === 'reset') {
            window.GRZSessionStats.update(current);
        }
    };
    document.getElementById('demo-reopen').onclick = function () { panel.style.display = 'flex'; };
    document.getElementById('demo-restart').onclick = function () {
        current = fixture.normal;
        panel.style.display = 'flex';
        window.GRZSessionStats.update(current);
    };
    window.GRZSessionStats.update(current);
}());
