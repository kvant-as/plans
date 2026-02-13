// cookie.js
window.initCookieBanner = function() {
    const COOKIE_NAME = 'user_cookie_consent';
    const COOKIE_DAYS = 365;
    
    function setCookie(name, value, days) {
        let expires = '';
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = '; expires=' + date.toUTCString();
        }
        document.cookie = name + '=' + (value || '') + expires + '; path=/; SameSite=Lax';
    }
    
    function getCookie(name) {
        const nameEQ = name + '=';
        const ca = document.cookie.split(';');
        for(let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    }
    
    if (!getCookie(COOKIE_NAME)) {
        const banner = document.getElementById('cookie-consent-banner');
        if (banner) {
            setTimeout(() => {
                banner.style.display = 'block';
                setTimeout(() => {
                    banner.classList.add('show');
                }, 10);
            }, 500);
            
            const acceptBtn = document.getElementById('accept-cookies');
            const declineBtn = document.getElementById('decline-cookies');
            
            if (acceptBtn) {
                acceptBtn.addEventListener('click', function() {
                    setCookie(COOKIE_NAME, 'accepted', COOKIE_DAYS);
                    banner.classList.remove('show');
                    setTimeout(() => {
                        banner.style.display = 'none';
                    }, 400);
                });
            }
            
            if (declineBtn) {
                declineBtn.addEventListener('click', function() {
                    banner.classList.remove('show');
                    setTimeout(() => {
                        banner.style.display = 'none';
                    }, 400);
                });
            }
        }
    }
};

document.addEventListener('DOMContentLoaded', function() {
    if (typeof window.initCookieBanner === 'function') {
        window.initCookieBanner();
    }
});