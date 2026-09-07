// Переключатель светлой/тёмной темы.
// Фактическая тема уже выставлена инлайн-скриптом в <head> (до отрисовки,
// чтобы не мигало), здесь только обвязка самой кнопки + синхронизация между
// вкладками и системной темой, если пользователь ничего не выбирал явно.
(function () {
    var STORAGE_KEY = 'enplans-theme';

    function apply(theme) {
        document.documentElement.setAttribute('data-theme', theme);
    }

    function current() {
        return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    }

    function setTheme(theme, persist) {
        apply(theme);
        if (persist) {
            try { localStorage.setItem(STORAGE_KEY, theme); } catch (e) {}
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        var btn = document.getElementById('themeToggle');
        if (btn) {
            btn.setAttribute('aria-pressed', current() === 'dark');
            btn.addEventListener('click', function () {
                var next = current() === 'dark' ? 'light' : 'dark';
                setTheme(next, true);
                btn.setAttribute('aria-pressed', next === 'dark');
            });
        }
    });

    // Если тема не выбрана пользователем явно (нет записи в localStorage),
    // следим за изменением системной темы на лету.
    try {
        var media = window.matchMedia('(prefers-color-scheme: dark)');
        media.addEventListener('change', function (e) {
            if (!localStorage.getItem(STORAGE_KEY)) {
                apply(e.matches ? 'dark' : 'light');
            }
        });
    } catch (e) {}

    // Синхронизация темы между открытыми вкладками сайта.
    window.addEventListener('storage', function (e) {
        if (e.key === STORAGE_KEY && e.newValue) {
            apply(e.newValue);
        }
    });
})();
