(function() {
    "use strict";

    document.body.addEventListener("click", (event) => {
        const closeBtn =
            event.target instanceof Element
                ? event.target.closest(".toast--member .toast__close")
                : null;

        if (!closeBtn) return;

        closeBtn.closest(".toast--member")?.remove();
    });
})();
