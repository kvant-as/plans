// Site-wide idle-session guard: runs on every page for an authenticated
// user (included from base.html), independent of the "Сессии" card that
// only exists on the profile page.
//
// Activity = real user interaction (click / keypress / touch / typing),
// NOT background requests — the header polls /api/notifications every
// 60s regardless of whether anyone is actually at the keyboard, so
// treating "any fetch" as activity would make the idle timeout never
// fire. A full page navigation re-reads a fresh baseline from the server
// on load, which already covers "переход по страницам".
(function () {
    let expiresAt = null;
    let timeoutMs = null;
    let redirecting = false;
    let lastExtend = 0;

    function format(ms) {
        const totalSeconds = Math.max(0, Math.floor(ms / 1000));
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
    }

    function updateCard() {
        const card = document.getElementById('sessionCard');
        if (!card || expiresAt === null) return;

        const valueEl = document.getElementById('sessionTimerValue');
        const fillEl = document.getElementById('sessionTimerFill');
        const remaining = Math.max(0, expiresAt - Date.now());

        if (valueEl) valueEl.textContent = format(remaining);

        const ratio = timeoutMs ? Math.min(1, Math.max(0, remaining / timeoutMs)) : 1;
        if (fillEl) fillEl.style.width = (ratio * 100) + '%';

        card.classList.toggle('glass-surface--warning', ratio <= 0.2 && ratio > 0.05);
        card.classList.toggle('glass-surface--danger', ratio <= 0.05);
    }

    function tick() {
        if (expiresAt === null || redirecting) return;

        if (Date.now() >= expiresAt) {
            redirecting = true;
            window.location.href = '/logout';
            return;
        }

        updateCard();
    }

    function extend() {
        if (!timeoutMs) return;
        const now = Date.now();
        if (now - lastExtend < 1000) return; // debounce bursts of events
        lastExtend = now;
        expiresAt = now + timeoutMs;
        updateCard();
    }

    function start(timeoutMinutes, initialExpiresAt) {
        timeoutMs = timeoutMinutes * 60 * 1000;
        expiresAt = initialExpiresAt;
        updateCard();

        ['click', 'keydown', 'touchstart', 'input'].forEach(evt => {
            document.addEventListener(evt, extend, { passive: true });
        });
        window.addEventListener('scroll', extend, { passive: true });

        setInterval(tick, 1000);
    }

    document.addEventListener('DOMContentLoaded', function () {
        const card = document.getElementById('sessionCard');

        // Profile page already server-rendered the session state onto
        // #sessionCard — use it directly, no need for an extra request.
        if (card && card.dataset.timeoutMinutes && card.dataset.expiresAt && card.dataset.serverTime) {
            const timeoutMinutes = parseInt(card.dataset.timeoutMinutes, 10) || 60;
            const serverTime = new Date(card.dataset.serverTime).getTime();
            const expires = new Date(card.dataset.expiresAt).getTime();
            const clockOffset = serverTime - Date.now();
            start(timeoutMinutes, expires - clockOffset);
            return;
        }

        // Any other page: fetch the current session state once so the
        // idle timer (and auto-logout) still runs everywhere, not just
        // on the profile page.
        fetch('/api/session-info', { credentials: 'same-origin' })
            .then(res => (res.ok ? res.json() : null))
            .then(data => {
                if (!data || !data.success) return;
                const timeoutMinutes = data.timeout_minutes || 60;
                const serverTime = new Date(data.server_time).getTime();
                const expires = new Date(data.expires_at).getTime();
                const clockOffset = serverTime - Date.now();
                start(timeoutMinutes, expires - clockOffset);
            })
            .catch(() => {});
    });
})();
