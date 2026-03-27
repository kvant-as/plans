document.addEventListener('DOMContentLoaded', function() {
    const questionLinks = document.querySelectorAll('.question-link-modern');
    const categoryHeaders = document.querySelectorAll('.category-header-modern');
    const answerSections = document.querySelectorAll('.answer-active-modern');
    const defaultView = document.getElementById('default-view');
    const searchInput = document.querySelector('.faq-search');

    categoryHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const category = this.parentElement;
            category.classList.toggle('active');
        });
    });

    questionLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            answerSections.forEach(section => section.classList.remove('show'));
            defaultView.style.display = 'none';
            const targetSection = document.getElementById(targetId);
            if (targetSection) targetSection.classList.add('show');
            questionLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            const category = this.closest('.category-modern');
            if (category) category.classList.add('active');
            history.pushState(null, null, `#${targetId}`);
        });
    });

    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        let foundCount = 0;
        questionLinks.forEach(link => {
            const text = link.textContent.toLowerCase();
            if (text.includes(searchTerm) || searchTerm.length < 2) {
                link.style.display = 'flex';
                if (searchTerm.length >= 2 && text.includes(searchTerm)) {
                    link.style.background = 'rgba(0,0,0,0.05)';
                    foundCount++;
                    const category = link.closest('.category-modern');
                    if (category) category.classList.add('active');
                } else {
                    link.style.background = '';
                }
            } else {
                link.style.display = 'none';
            }
        });
        const oldInfo = document.querySelector('.search-results-info');
        if (oldInfo) oldInfo.remove();
        if (searchTerm.length >= 2) {
            const resultsInfo = document.createElement('div');
            resultsInfo.className = 'search-results-info';
            resultsInfo.innerHTML = `Найдено вопросов: <strong>${foundCount}</strong>`;
            searchInput.parentNode.appendChild(resultsInfo);
        }
    });

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetLink = document.querySelector(`.question-link-modern[href="#${targetId}"]`);
            if (targetLink) targetLink.click();
        });
    });

    if (window.location.hash) {
        const hash = window.location.hash.substring(1);
        const targetLink = document.querySelector(`.question-link-modern[href="#${hash}"]`);
        if (targetLink) setTimeout(() => targetLink.click(), 100);
    }

    document.querySelectorAll('.answer-text input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const label = this.parentElement;
            if (this.checked) {
                label.style.opacity = '0.6';
                label.style.textDecoration = 'line-through';
            } else {
                label.style.opacity = '1';
                label.style.textDecoration = 'none';
            }
        });
    });
});