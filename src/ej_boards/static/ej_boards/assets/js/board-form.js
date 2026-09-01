(function() {
    "use strict";

    const getById = (id) => document.getElementById(id);

    const onReady = (callback) => {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", callback, {
                once: true,
            });
            return;
        }

        callback();
    };

    const isValidEmail = (email, maxLength) =>
        (maxLength < 0 || email.length <= maxLength) &&
        /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

    const toggleModal = (modal, show) => {
        modal.classList.toggle("hide", !show);
        modal.setAttribute("aria-hidden", String(!show));
    };

    const getManagerElements = () => {
        const elements = {
            members: document.querySelector(".board-form-members"),
            emailInput: getById("board-member-email-input"),
            addButton: getById("board-member-add-btn"),
            addModal: getById("board-member-confirm-modal"),
            addModalEmail: getById("board-member-modal-email"),
            addModalEmailInput: getById("board-member-modal-email-input"),
            addModalBack: getById("board-member-modal-back"),
            addModalYes: getById("board-member-modal-yes"),
            removeModal: getById("board-member-remove-modal"),
            removeModalBack: getById("board-member-remove-back"),
            removeModalYes: getById("board-member-remove-yes"),
        };

        return Object.values(elements).every(Boolean) ? elements : null;
    };

    const setManagerEmailError = (message = "") => {
        const error = getById("board-member-email-error");
        if (!error) return;

        error.textContent = message;
        error.classList.toggle("show-error", Boolean(message));
    };

    const openAddModal = (elements, email) => {
        elements.addModalEmail.textContent = email;
        elements.addModalEmailInput.value = email;
        toggleModal(elements.addModal, true);
    };

    const closeAddModal = (elements) => {
        elements.addModalEmailInput.value = "";
        toggleModal(elements.addModal, false);
    };

    const openRemoveModal = (elements, state, button) => {
        if (!button || button.disabled) return;

        state.pendingRemoveButton = button;
        toggleModal(elements.removeModal, true);
    };

    const closeRemoveModal = (elements, state) => {
        if (state.removeRequestPending) return;

        state.pendingRemoveButton = null;
        state.removeRequestXhr = null;
        toggleModal(elements.removeModal, false);
    };

    const openAddConfirmation = (elements, messages) => {
        setManagerEmailError();

        const email = elements.emailInput.value.trim();
        if (!email) {
            setManagerEmailError(messages.emailRequired);
            return;
        }
        if (!isValidEmail(email, elements.emailInput.maxLength)) {
            setManagerEmailError(messages.invalidEmail);
            return;
        }

        openAddModal(elements, email);
    };

    const bindAddManager = (elements, messages) => {
        elements.addButton.addEventListener("click", () => {
            openAddConfirmation(elements, messages);
        });
        elements.emailInput.addEventListener("keydown", (event) => {
            if (event.key !== "Enter") return;

            event.preventDefault();
            openAddConfirmation(elements, messages);
        });
    };

    const bindModals = (elements, state) => {
        elements.addModalBack.addEventListener("click", () =>
            closeAddModal(elements)
        );
        elements.addModal.addEventListener("click", (event) => {
            if (event.target === event.currentTarget) closeAddModal(elements);
        });
        elements.removeModalBack.addEventListener("click", () =>
            closeRemoveModal(elements, state)
        );
        elements.removeModal.addEventListener("click", (event) => {
            if (event.target === event.currentTarget) {
                closeRemoveModal(elements, state);
            }
        });
    };

    const bindRemoveManager = (elements, state) => {
        elements.removeModalYes.addEventListener("click", () => {
            if (
                !state.pendingRemoveButton ||
                state.removeRequestPending ||
                !window.htmx
            ) {
                return;
            }

            state.removeRequestPending = true;
            window.htmx.trigger(state.pendingRemoveButton, "confirmed");
        });

        elements.members.addEventListener("click", (event) => {
            const removeButton =
                event.target instanceof Element
                    ? event.target.closest(".board-form-members__remove-btn")
                    : null;

            if (!removeButton || !elements.members.contains(removeButton)) {
                return;
            }

            event.preventDefault();
            openRemoveModal(elements, state, removeButton);
        });
    };

    const bindHtmxEvents = (elements, state) => {
        document.body.addEventListener("htmx:beforeRequest", (event) => {
            const { elt: requestElement, xhr } = event.detail ?? {};

            if (requestElement === state.pendingRemoveButton) {
                state.removeRequestXhr = xhr;
            }
        });
        document.body.addEventListener("htmx:beforeSwap", (event) => {
            const { xhr } = event.detail ?? {};

            if (xhr?.status !== 400) return;
            if (
                xhr.getResponseHeader("HX-Retarget") !==
                "#board-member-email-error"
            ) {
                return;
            }

            event.detail.shouldSwap = true;
            event.detail.isError = false;
        });

        document.body.addEventListener("htmx:afterRequest", (event) => {
            const { elt: requestElement, xhr } = event.detail ?? {};
            const status = xhr?.status ?? 0;
            const successful = status >= 200 && status < 300;

            if (xhr === state.removeRequestXhr) {
                state.removeRequestPending = false;
                state.removeRequestXhr = null;
                if (successful) closeRemoveModal(elements, state);
                return;
            }

            if (requestElement !== elements.addModalYes) return;

            closeAddModal(elements);
            if (successful) elements.emailInput.value = "";
        });
    };

    const initializeBoardManagers = () => {
        const elements = getManagerElements();
        const form = getById("board-form");
        if (!elements || !form) return;

        const state = {
            pendingRemoveButton: null,
            removeRequestPending: false,
            removeRequestXhr: null,
        };
        const messages = {
            emailRequired: form.dataset.managerEmailRequiredMessage,
            invalidEmail: form.dataset.managerInvalidEmailMessage,
        };

        bindAddManager(elements, messages);
        bindModals(elements, state);
        bindRemoveManager(elements, state);
        bindHtmxEvents(elements, state);
    };

    onReady(initializeBoardManagers);
})();
