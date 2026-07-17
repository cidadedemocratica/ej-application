(function() {
    "use strict";

    const SELECTORS = Object.freeze({
        addMoreComments: "#add-more-comments",
        anonymousVotes: "#anonymous_votes",
        anonymousVotesEnabled: "#id_anonymous_votes_enabled",
        commentsCount: 'input[name="comments_count"]',
        commentList: "#comment-list",
        demographicQuestions: "#demographic_questions",
        form: "#conversation-form",
        profileQuestion: "#id_send_profile_question",
        tabs: '[role="tab"][data-tab-target]',
        tabPanels: ".conversation-form-panel",
    });

    const ACTIVATION_KEYS = new Set(["Enter", " "]);

    const getById = (id) => document.getElementById(id);
    const getConversationForm = () => document.querySelector(SELECTORS.form);

    const getMessages = () => {
        const data = getConversationForm()?.dataset ?? {};

        return {
            commentLabel: data.commentLabel,
            commentPlaceholder: data.commentPlaceholder,
            emailRequired: data.memberEmailRequiredMessage,
            invalidEmail: data.memberInvalidEmailMessage,
        };
    };

    const onReady = (callback) => {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", callback, {
                once: true,
            });
            return;
        }

        callback();
    };

    const isElement = (value) => value instanceof Element;

    const toggleModal = (modalEl, show) => {
        modalEl.classList.toggle("hide", !show);

        if (show) {
            modalEl.removeAttribute("aria-hidden");
            return;
        }

        modalEl.setAttribute("aria-hidden", "true");
    };

    const toggleConversationOption = (checkboxSelector, optionSelector) => {
        const checkbox = document.querySelector(checkboxSelector);
        const option = document.querySelector(optionSelector);
        const optionInput = option?.querySelector("input");

        if (!(checkbox instanceof HTMLInputElement) || !optionInput) return;

        const toggleOption = () => {
            option.style.opacity = checkbox.checked ? "1" : "0.5";
            optionInput.disabled = !checkbox.checked;

            if (!checkbox.checked) optionInput.value = "0";
        };

        checkbox.addEventListener("change", toggleOption);
        toggleOption();
    };

    const isTabDisabled = (tab) =>
        tab.disabled || tab.getAttribute("aria-disabled") === "true";

    const getNextTabIndex = (key, index, lastIndex) => {
        switch (key) {
            case "ArrowLeft":
                return index === 0 ? lastIndex : index - 1;
            case "ArrowRight":
                return index === lastIndex ? 0 : index + 1;
            case "Home":
                return 0;
            case "End":
                return lastIndex;
            default:
                return null;
        }
    };

    const initializeConversationFormTabs = () => {
        const tabs = [...document.querySelectorAll(SELECTORS.tabs)];
        const activeTabInput = getById("conversation-form-active-tab");

        if (!tabs.length || !(activeTabInput instanceof HTMLInputElement)) {
            return;
        }

        const activateTab = (tab, focusTab = false) => {
            if (isTabDisabled(tab)) return;

            const { tabTarget } = tab.dataset;
            const panels = document.querySelectorAll(SELECTORS.tabPanels);

            for (const currentTab of tabs) {
                const isActive = currentTab === tab;
                currentTab.classList.toggle(
                    "conversation-form-tabs__tab--active",
                    isActive
                );
                currentTab.setAttribute(
                    "aria-selected",
                    String(isActive)
                );
                currentTab.tabIndex = isActive ? 0 : -1;
            }

            for (const panel of panels) {
                panel.hidden =
                    panel.id !== `conversation-form-panel-${tabTarget}`;
            }

            activeTabInput.value = tabTarget ?? "";
            if (focusTab) tab.focus();
        };

        const enabledTabs = tabs.filter((tab) => !isTabDisabled(tab));
        if (!enabledTabs.length) return;

        for (const [index, tab] of enabledTabs.entries()) {
            tab.addEventListener("click", () => activateTab(tab));
            tab.addEventListener("keydown", (event) => {
                const nextIndex = getNextTabIndex(
                    event.key,
                    index,
                    enabledTabs.length - 1
                );

                if (nextIndex === null) return;

                event.preventDefault();
                activateTab(enabledTabs[nextIndex], true);
            });
        }

        const initialTab =
            enabledTabs.find(
                (tab) => tab.dataset.tabTarget === activeTabInput.value
            ) ?? enabledTabs[0];
        activateTab(initialTab);
    };

    const createCommentField = (index, messages) => {
        const label = document.createElement("label");
        const textarea = document.createElement("textarea");

        label.append(`${messages.commentLabel}${index}`);
        textarea.className = "comment__textarea";
        textarea.name = `comment-${index}`;
        textarea.placeholder = `${messages.commentPlaceholder} #${index}`;
        label.append(textarea);

        return label;
    };

    const initializeAddMoreComments = (messages) => {
        const trigger = document.querySelector(SELECTORS.addMoreComments);
        const commentList = document.querySelector(SELECTORS.commentList);
        const commentsCountInput = document.querySelector(
            SELECTORS.commentsCount
        );

        if (
            !trigger ||
            !commentList ||
            !(commentsCountInput instanceof HTMLInputElement)
        ) {
            return;
        }

        const addComment = () => {
            const index = Number.parseInt(commentsCountInput.value, 10) + 1;

            commentsCountInput.value = String(index);
            commentList.append(createCommentField(index, messages));
        };

        trigger.addEventListener("click", (event) => {
            event.preventDefault();
            addComment();
        });
        trigger.addEventListener("keydown", (event) => {
            if (!ACTIVATION_KEYS.has(event.key)) return;

            event.preventDefault();
            addComment();
        });
    };

    const getConversationMemberElements = () => {
        const els = {
            emailInput: getById("member-email-input"),
            addBtn: getById("member-add-btn"),
            errorEl: getById("member-email-error"),
            listEl: getById("members-list"),
            modal: getById("member-confirm-modal"),
            modalEmail: getById("member-modal-email"),
            modalEmailInput: getById("member-modal-email-input"),
            modalBack: getById("member-modal-back"),
            modalYes: getById("member-modal-yes"),
            removeModal: getById("member-remove-modal"),
            removeBack: getById("member-remove-back"),
            removeYes: getById("member-remove-yes"),
        };

        return Object.values(els).every(Boolean) ? els : null;
    };

    const isValidEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

    const openMemberModal = (els, email) => {
        els.modalEmail.textContent = email;
        els.modalEmailInput.value = email;
        toggleModal(els.modal, true);
    };

    const closeMemberModal = (els) => {
        els.modalEmailInput.value = "";
        toggleModal(els.modal, false);
    };

    const openRemoveModal = (els, state, button) => {
        if (!button || button.disabled) return;

        state.pendingRemoveButton = button;
        toggleModal(els.removeModal, true);
    };

    const closeRemoveModal = (els, state) => {
        state.pendingRemoveButton = null;
        toggleModal(els.removeModal, false);
    };

    const setMemberEmailError = (message = "") => {
        const errorEl = getById("member-email-error");
        if (!errorEl) return;

        errorEl.textContent = message;
        errorEl.classList.toggle("show-error", Boolean(message));
    };

    const bindMemberAdd = (els, messages) => {
        els.addBtn.addEventListener("click", () => {
            setMemberEmailError();

            const email = els.emailInput.value.trim();
            if (!email) {
                setMemberEmailError(messages.emailRequired);
                return;
            }
            if (!isValidEmail(email)) {
                setMemberEmailError(messages.invalidEmail);
                return;
            }

            openMemberModal(els, email);
        });
    };

    const bindMemberModals = (els, state) => {
        els.modalBack.addEventListener("click", () => closeMemberModal(els));
        els.modal.addEventListener("click", (event) => {
            if (event.target === event.currentTarget) closeMemberModal(els);
        });
        els.removeBack.addEventListener("click", () =>
            closeRemoveModal(els, state)
        );
        els.removeModal.addEventListener("click", (event) => {
            if (event.target === event.currentTarget) {
                closeRemoveModal(els, state);
            }
        });
    };

    const bindMemberRemoval = (els, state) => {
        els.removeYes.addEventListener("click", () => {
            if (!state.pendingRemoveButton || !window.htmx) return;

            state.removeRequestPending = true;
            window.htmx.trigger(state.pendingRemoveButton, "confirmed");
        });

        els.listEl.addEventListener("click", (event) => {
            const removeBtn = isElement(event.target)
                ? event.target.closest(
                      ".conversation-form-members__remove-btn"
                  )
                : null;

            if (!removeBtn || !els.listEl.contains(removeBtn)) return;

            event.preventDefault();
            openRemoveModal(els, state, removeBtn);
        });
    };

    const bindMemberHtmxEvents = (els, state) => {
        document.body.addEventListener("htmx:beforeSwap", (event) => {
            const { xhr } = event.detail ?? {};

            if (xhr?.status !== 400) return;
            if (xhr.getResponseHeader("HX-Retarget") !== "#member-email-error") {
                return;
            }

            event.detail.shouldSwap = true;
            event.detail.isError = false;
        });

        document.body.addEventListener("htmx:afterRequest", (event) => {
            const { elt: requestEl, xhr } = event.detail ?? {};
            const status = xhr?.status ?? 0;
            const successful = status >= 200 && status < 300;

            if (state.removeRequestPending) {
                state.removeRequestPending = false;
                if (successful) {
                    closeRemoveModal(els, state);
                }
                return;
            }

            if (requestEl !== els.modalYes) return;

            closeMemberModal(els);
            if (successful) {
                els.emailInput.value = "";
            }
        });
    };

    const initializeConversationMembers = (messages) => {
        const els = getConversationMemberElements();
        if (!els) return;

        const state = {
            pendingRemoveButton: null,
            removeRequestPending: false,
        };

        bindMemberAdd(els, messages);
        bindMemberModals(els, state);
        bindMemberRemoval(els, state);
        bindMemberHtmxEvents(els, state);
    };

    const initializeConversationSaveConfirmation = () => {
        const form = getConversationForm();
        const modal = getById("conversation-save-modal");
        const modalBack = getById("conversation-save-back");
        const modalYes = getById("conversation-save-yes");

        if (!form || !modal || !modalBack || !modalYes) return;

        const openModal = () => toggleModal(modal, true);
        const closeModal = () => toggleModal(modal, false);

        form.addEventListener("submit", (event) => {
            event.preventDefault();
            openModal();
        });

        modalBack.addEventListener("click", closeModal);
        modal.addEventListener("click", (event) => {
            if (event.target === event.currentTarget) closeModal();
        });
        modalYes.addEventListener("click", () => {
            HTMLFormElement.prototype.submit.call(form);
        });
    };

    const initializeBackToTopSmoothScroll = () => {
        const backToTopLink = document.querySelector(".back-to-top__link");
        const pageTop = getById("page-top");

        if (!backToTopLink || !pageTop) return;

        backToTopLink.addEventListener("click", (event) => {
            event.preventDefault();
            pageTop.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    };

    const initializeConversationForm = () => {
        const messages = getMessages();

        initializeConversationFormTabs();
        initializeAddMoreComments(messages);
        initializeConversationMembers(messages);
        initializeConversationSaveConfirmation();
        initializeBackToTopSmoothScroll();
        toggleConversationOption(
            SELECTORS.profileQuestion,
            SELECTORS.demographicQuestions
        );
        toggleConversationOption(
            SELECTORS.anonymousVotesEnabled,
            SELECTORS.anonymousVotes
        );
    };

    onReady(initializeConversationForm);
})();
