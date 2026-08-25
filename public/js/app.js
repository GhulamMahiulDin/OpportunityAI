(function () {
    'use strict';

    // ==========================================
    // Utilities
    // ==========================================

    function debounce(fn, delay) {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Reads the CSRF token Flask-WTF renders into base.html's <meta> tag.
    // Every AJAX POST needs this in an X-CSRFToken header or the server
    // will reject it with a 400.
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    // Flash messages are server-rendered inside #flash-container (see base.html).
    // This creates the same markup for messages triggered by AJAX calls.
    function showFlash(message, category = 'info') {
        let container = document.getElementById('flash-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'flash-container';
            container.id = 'flash-container';
            const main = document.getElementById('main-content');
            if (main) main.insertBefore(container, main.firstChild);
        }

        const flash = document.createElement('div');
        flash.className = `flash flash-${category}`;
        flash.setAttribute('role', 'alert');
        flash.innerHTML = `
            <span class="flash-text">${escapeHtml(message)}</span>
            <button class="flash-close" aria-label="Close">&times;</button>
        `;
        container.appendChild(flash);
        bindFlashDismiss(flash);
    }

    function bindFlashDismiss(flash) {
        const timeout = setTimeout(() => fadeOutAndRemove(flash), 5000);
        const closeBtn = flash.querySelector('.flash-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                clearTimeout(timeout);
                fadeOutAndRemove(flash);
            });
        }
    }

    function fadeOutAndRemove(el) {
        el.style.transition = 'opacity 0.4s ease';
        el.style.opacity = '0';
        setTimeout(() => el.remove(), 400);
    }

    function updateQueryParam(params) {
        const url = new URL(window.location.href);
        Object.keys(params).forEach((key) => {
            const value = params[key];
            if (value === '' || value === null || value === undefined) {
                url.searchParams.delete(key);
            } else {
                url.searchParams.set(key, value);
            }
        });
        window.location.href = url.toString();
    }

    // ==========================================
    // Sidebar (mobile) — matches ids in base.html
    // ==========================================
    function setupSidebar() {
        const toggleBtn = document.getElementById('hamburger-btn');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('mobile-overlay');
        if (!toggleBtn || !sidebar || !overlay) return;

        function openSidebar() {
            sidebar.classList.add('open');
            overlay.classList.add('active');
        }
        function closeSidebar() {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        }

        toggleBtn.addEventListener('click', () => {
            if (sidebar.classList.contains('open')) closeSidebar();
            else openSidebar();
        });
        overlay.addEventListener('click', closeSidebar);
        sidebar.querySelectorAll('a').forEach((link) => {
            link.addEventListener('click', () => {
                if (window.innerWidth < 900) closeSidebar();
            });
        });
    }

    // ==========================================
    // Flash message auto-dismiss (server-rendered ones)
    // ==========================================
    function setupFlashMessages() {
        document.querySelectorAll('.flash').forEach(bindFlashDismiss);
    }

    // ==========================================
    // Scroll to top — reuse existing base.html button
    // ==========================================
    function setupScrollToTop() {
        const btn = document.getElementById('scroll-top-btn');
        if (!btn) return;

        window.addEventListener('scroll', debounce(() => {
            btn.classList.toggle('visible', window.scrollY > 300);
        }, 100));

        btn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // ==========================================
    // Confirm modal — reuse existing base.html markup
    // ==========================================
    function confirmDialog(message, onConfirm) {
        const modal = document.getElementById('confirm-modal');
        if (!modal) {
            if (window.confirm(message)) onConfirm();
            return;
        }
        const msgEl = document.getElementById('confirm-modal-message');
        const cancelBtn = document.getElementById('confirm-modal-cancel');
        const okBtn = document.getElementById('confirm-modal-confirm');
        if (msgEl) msgEl.textContent = message;

        modal.style.display = 'flex';
        modal.classList.add('active');

        const cleanup = () => {
            modal.style.display = 'none';
            modal.classList.remove('active');
            newCancel.removeEventListener('click', onCancelClick);
            newOk.removeEventListener('click', onOkClick);
        };
        // Clone to strip any previously-bound listeners
        const newCancel = cancelBtn.cloneNode(true);
        cancelBtn.parentNode.replaceChild(newCancel, cancelBtn);
        const newOk = okBtn.cloneNode(true);
        okBtn.parentNode.replaceChild(newOk, okBtn);

        function onCancelClick() { cleanup(); }
        function onOkClick() { cleanup(); onConfirm(); }

        newCancel.addEventListener('click', onCancelClick);
        newOk.addEventListener('click', onOkClick);
    }

    // ==========================================
    // Autocomplete dropdown for profile tag inputs
    // Uses the dropdown <div> that already exists in profile.html
    // ==========================================
    function setupAutocomplete(inputEl, dropdownEl, options, onSelect) {
        if (!inputEl || !dropdownEl) return { isAlreadySelected: () => false };

        let currentIndex = -1;
        let isAlreadySelected = () => false;

        function render(matches) {
            dropdownEl.innerHTML = '';
            currentIndex = -1;
            if (matches.length === 0) {
                dropdownEl.classList.remove('open');
                return;
            }
            matches.slice(0, 8).forEach((match) => {
                const item = document.createElement('div');
                item.className = 'autocomplete-item';
                item.textContent = match;
                item.addEventListener('click', () => {
                    inputEl.value = '';
                    dropdownEl.classList.remove('open');
                    onSelect(match);
                });
                dropdownEl.appendChild(item);
            });
            dropdownEl.classList.add('open');
        }

        inputEl.addEventListener('input', debounce(() => {
            const query = inputEl.value.trim().toLowerCase();
            if (!query) {
                dropdownEl.classList.remove('open');
                return;
            }
            const matches = options.filter(
                (opt) => opt.toLowerCase().includes(query) && !isAlreadySelected(opt)
            );
            render(matches);
        }, 200));

        inputEl.addEventListener('keydown', (e) => {
            const items = dropdownEl.querySelectorAll('.autocomplete-item');
            if (e.key === 'ArrowDown' && items.length) {
                e.preventDefault();
                currentIndex = Math.min(currentIndex + 1, items.length - 1);
                items.forEach((it, i) => it.classList.toggle('active', i === currentIndex));
            } else if (e.key === 'ArrowUp' && items.length) {
                e.preventDefault();
                currentIndex = Math.max(currentIndex - 1, 0);
                items.forEach((it, i) => it.classList.toggle('active', i === currentIndex));
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (currentIndex > -1 && items[currentIndex]) {
                    items[currentIndex].click();
                } else if (inputEl.value.trim()) {
                    const val = inputEl.value.trim();
                    inputEl.value = '';
                    dropdownEl.classList.remove('open');
                    onSelect(val);
                }
            } else if (e.key === 'Escape') {
                dropdownEl.classList.remove('open');
            }
        });

        document.addEventListener('click', (e) => {
            if (!inputEl.contains(e.target) && !dropdownEl.contains(e.target)) {
                dropdownEl.classList.remove('open');
            }
        });

        return {
            setIsAlreadySelected(fn) { isAlreadySelected = fn; }
        };
    }

    // ==========================================
    // Profile page — skills, interests, preferences, validation
    // ==========================================
    function initProfile() {
        const page = document.getElementById('profile-page');
        if (!page) return;

        // Form validation before submit
        const form = document.getElementById('profile-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                let valid = true;
                const cgpa = form.querySelector('[name="cgpa"]');
                if (cgpa && cgpa.value) {
                    const val = parseFloat(cgpa.value);
                    if (isNaN(val) || val < 0 || val > 4.0) {
                        valid = false;
                        showFlash('CGPA must be between 0.0 and 4.0', 'error');
                    }
                }
                const gradYear = form.querySelector('[name="graduation_year"]');
                if (gradYear && gradYear.value) {
                    const val = parseInt(gradYear.value, 10);
                    const currentYear = new Date().getFullYear();
                    if (isNaN(val) || val < currentYear - 1 || val > currentYear + 10) {
                        valid = false;
                        showFlash('Please enter a realistic graduation year.', 'error');
                    }
                }
                if (!valid) e.preventDefault();
            });
        }

        setupTagSection('skill', '/profile/skill/add', '/profile/skill/remove',
            window.availableSkills || []);
        setupTagSection('interest', '/profile/interest/add', '/profile/interest/remove',
            window.availableInterests || []);
        // Preferences are handled by the global window.togglePreference()
        // function, called directly from the inline onchange="" in profile.html.
    }

    function setupTagSection(type, addUrl, removeUrl, options) {
        const input = document.getElementById(`${type}-input`);
        const container = document.getElementById(`${type}s-container`);
        const dropdown = document.getElementById(`${type}-dropdown`);
        const addBtn = document.getElementById(`add-${type}-btn`);
        if (!input || !container) return;

        function currentTagNames() {
            return Array.from(container.querySelectorAll('.tag-text'))
                .map((el) => el.textContent.trim().toLowerCase());
        }

        const autocomplete = setupAutocomplete(input, dropdown, options, addTag);
        if (autocomplete.setIsAlreadySelected) {
            autocomplete.setIsAlreadySelected((val) => currentTagNames().includes(val.toLowerCase()));
        }

        function addTag(name) {
            name = name.trim();
            if (!name) return;
            if (currentTagNames().includes(name.toLowerCase())) {
                showFlash(`${name} is already added.`, 'warning');
                return;
            }

            fetch(addUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify({ name })
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.status === 'success') {
                        renderTag(name);
                        showFlash(`Added "${name}"`, 'success');
                    } else {
                        showFlash(data.message || 'Failed to add.', 'error');
                    }
                })
                .catch(() => showFlash('Network error.', 'error'));
        }

        function removeTag(name, tagEl) {
            fetch(removeUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify({ name })
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.status === 'success') {
                        tagEl.remove();
                        showFlash(`Removed "${name}"`, 'info');
                    } else {
                        showFlash(data.message || 'Failed to remove.', 'error');
                    }
                })
                .catch(() => showFlash('Network error.', 'error'));
        }

        function renderTag(name) {
            const div = document.createElement('div');
            div.className = 'tag tag-removable';
            div.dataset.name = name;
            div.innerHTML = `
                <span class="tag-text">${escapeHtml(name)}</span>
                <button class="tag-remove" data-type="${type}" data-name="${escapeHtml(name)}" aria-label="Remove ${escapeHtml(name)}">&times;</button>
            `;
            container.appendChild(div);
        }

        if (addBtn) {
            addBtn.addEventListener('click', () => addTag(input.value));
        }

        container.addEventListener('click', (e) => {
            const btn = e.target.closest('.tag-remove');
            if (!btn) return;
            const tagEl = btn.closest('.tag');
            const name = btn.dataset.name;
            removeTag(name, tagEl);
        });
    }

    // ==========================================
    // Analyze page — tab switching + clear button
    // ==========================================
    function initAnalyze() {
        const page = document.getElementById('analyze-page');
        if (!page) return;

        const tabPaste = document.getElementById('tab-paste');
        const tabManual = document.getElementById('tab-manual');
        const contentPaste = document.getElementById('tab-content-paste');
        const contentManual = document.getElementById('tab-content-manual');

        function activate(tab) {
            const isPaste = tab === 'paste';
            if (tabPaste) tabPaste.classList.toggle('active', isPaste);
            if (tabManual) tabManual.classList.toggle('active', !isPaste);
            if (contentPaste) {
                contentPaste.classList.toggle('active', isPaste);
                contentPaste.style.display = isPaste ? '' : 'none';
            }
            if (contentManual) {
                contentManual.classList.toggle('active', !isPaste);
                contentManual.style.display = isPaste ? 'none' : '';
            }
        }

        if (tabPaste) tabPaste.addEventListener('click', () => activate('paste'));
        if (tabManual) tabManual.addEventListener('click', () => activate('manual'));

        const clearBtn = document.getElementById('clear-btn');
        const textarea = document.getElementById('opportunity_text');
        if (clearBtn && textarea) {
            clearBtn.addEventListener('click', () => { textarea.value = ''; });
        }

        const pasteForm = document.getElementById('paste-form');
        if (pasteForm) {
            pasteForm.addEventListener('submit', (e) => {
                if (!textarea.value.trim()) {
                    e.preventDefault();
                    showFlash('Please paste the opportunity text to analyze.', 'error');
                }
            });
        }

        const manualForm = document.getElementById('manual-form');
        if (manualForm) {
            manualForm.addEventListener('submit', (e) => {
                const title = document.getElementById('m_title');
                if (title && !title.value.trim()) {
                    e.preventDefault();
                    showFlash('Opportunity title is required.', 'error');
                }
            });
        }
    }

    // ==========================================
    // Opportunities page — filter pills, search, sort
    // Server does the actual filtering via query params.
    // ==========================================
    function initOpportunities() {
        const page = document.getElementById('opportunities-page');
        if (!page) return;

        const typeFilters = document.getElementById('type-filters');
        if (typeFilters) {
            typeFilters.querySelectorAll('.filter-pill').forEach((btn) => {
                btn.addEventListener('click', () => {
                    updateQueryParam({ type: btn.dataset.type || '' });
                });
            });
        }

        const searchInput = document.getElementById('opp-search');
        if (searchInput) {
            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    updateQueryParam({ search: searchInput.value.trim() });
                }
            });
        }

        const sortSelect = document.getElementById('opp-sort');
        if (sortSelect) {
            sortSelect.addEventListener('change', () => {
                updateQueryParam({ sort: sortSelect.value });
            });
        }
    }

    // ==========================================
    // Applications page — status filter pills + status dropdown
    // ==========================================
    function initApplicationsListPage() {
        const page = document.getElementById('applications-page');
        if (!page) return;

        const statusFilters = document.getElementById('status-filters');
        if (statusFilters) {
            statusFilters.querySelectorAll('.filter-pill').forEach((btn) => {
                btn.addEventListener('click', () => {
                    updateQueryParam({ status: btn.dataset.status || '' });
                });
            });
        }
    }

    // Global: called from inline onchange="" in applications.html / application_detail.html
    window.updateApplicationStatus = function (applicationId, newStatus) {
        fetch(`/application/${applicationId}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
            body: JSON.stringify({ status: newStatus })
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.status === 'success') {
                    showFlash('Status updated.', 'success');
                    const card = document.getElementById(`app-card-${applicationId}`);
                    if (card) card.dataset.status = newStatus;
                } else {
                    showFlash('Failed to update status.', 'error');
                }
            })
            .catch(() => showFlash('Network error updating status.', 'error'));
    };

    // Global: called from inline onchange="" in profile.html
    window.togglePreference = function (checkbox, name) {
        const action = checkbox.checked ? 'add' : 'remove';
        const label = checkbox.closest('.preference-item');

        fetch('/profile/preference/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
            body: JSON.stringify({ name, action })
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.status === 'success') {
                    if (label) label.classList.toggle('active', action === 'add');
                } else {
                    checkbox.checked = !checkbox.checked;
                    showFlash('Could not update preference.', 'error');
                }
            })
            .catch(() => {
                checkbox.checked = !checkbox.checked;
                showFlash('Network error updating preference.', 'error');
            });
    };

    // ==========================================
    // Application detail page — checklist + notes
    // ==========================================
    function initApplicationDetail() {
        const page = document.getElementById('application-detail-page');
        if (!page) return;

        document.querySelectorAll('.checklist-checkbox').forEach((cb) => {
            cb.addEventListener('change', (e) => {
                const taskId = e.target.dataset.taskId;
                const appId = e.target.dataset.appId;
                const item = e.target.closest('.checklist-item');
                const isChecked = e.target.checked;

                if (item) item.classList.toggle('completed', isChecked);

                fetch(`/application/${appId}/task/${taskId}/toggle`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                    body: JSON.stringify({ completed: isChecked })
                })
                    .then((res) => res.json())
                    .then((data) => {
                        if (data.status === 'success') {
                            const progressEl = document.getElementById('checklist-progress');
                            if (progressEl) {
                                progressEl.textContent = `${data.done_count}/${data.total_count} completed`;
                            }
                        } else {
                            e.target.checked = !isChecked;
                            if (item) item.classList.toggle('completed', !isChecked);
                            showFlash('Failed to update task.', 'error');
                        }
                    })
                    .catch(() => {
                        e.target.checked = !isChecked;
                        if (item) item.classList.toggle('completed', !isChecked);
                        showFlash('Network error updating task.', 'error');
                    });
            });
        });
    }

    // ==========================================
    // Auth forms (login / register) — light client-side validation
    // Server already validates; this just gives faster feedback.
    // ==========================================
    // ==========================================
    // Inbox page — sync button loading state
    // ==========================================
    function initInboxSync() {
        const form = document.getElementById('gmail-sync-form');
        const btn = document.getElementById('gmail-sync-btn');
        if (!form || !btn) return;

        form.addEventListener('submit', () => {
            btn.disabled = true;
            btn.dataset.originalText = btn.textContent;
            btn.innerHTML = '<span class="btn-spinner"></span> Syncing your inbox…';
            // The form still submits normally (full page load on completion);
            // this just gives immediate feedback that the click registered,
            // since a Gmail sync can take a few seconds.
        });
    }

    function initAuth() {
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');

        function validateEmailField(form) {
            const email = form.querySelector('[name="email"]');
            const errorEl = document.getElementById('email-error');
            if (!email) return true;
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (email.value && !emailRegex.test(email.value)) {
                if (errorEl) errorEl.textContent = 'Please enter a valid email address.';
                return false;
            }
            if (errorEl) errorEl.textContent = '';
            return true;
        }

        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                if (!validateEmailField(loginForm)) e.preventDefault();
            });
        }

        if (registerForm) {
            registerForm.addEventListener('submit', (e) => {
                let valid = validateEmailField(registerForm);
                const pw = registerForm.querySelector('[name="password"]');
                const confirmPw = registerForm.querySelector('[name="confirm_password"]');
                const confirmError = document.getElementById('confirm-password-error');

                if (pw && pw.value.length < 6) {
                    const pwError = document.getElementById('password-error');
                    if (pwError) pwError.textContent = 'Password must be at least 6 characters.';
                    valid = false;
                }
                if (pw && confirmPw && pw.value !== confirmPw.value) {
                    if (confirmError) confirmError.textContent = 'Passwords do not match.';
                    valid = false;
                } else if (confirmError) {
                    confirmError.textContent = '';
                }
                if (!valid) e.preventDefault();
            });
        }
    }

    // ==========================================
    // INIT
    // ==========================================
    function init() {
        setupSidebar();
        setupFlashMessages();
        setupScrollToTop();

        initProfile();
        initAnalyze();
        initOpportunities();
        initApplicationsListPage();
        initApplicationDetail();
        initInboxSync();
        initAuth();

        // Expose confirmDialog in case future pages want the styled modal
        window.confirmDialog = confirmDialog;
    }

    document.addEventListener('DOMContentLoaded', init);
})();
