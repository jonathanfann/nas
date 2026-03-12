/**
 * NAS file browser - drag & drop upload, modals, client-side enhancements
 */

/** Modal helpers - replace native alert/confirm */
const Modal = {
    overlay: null,

    init() {
        if (this.overlay) return;
        this.overlay = document.createElement("div");
        this.overlay.className = "modal-overlay";
        this.overlay.addEventListener("click", (e) => {
            if (e.target === this.overlay) this.close();
        });
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && this.overlay?.classList.contains("modal-overlay--open")) {
                this.close();
            }
        });
        document.body.appendChild(this.overlay);
    },

    show(content) {
        this.init();
        this.overlay.innerHTML = "";
        this.overlay.appendChild(content);
        this.overlay.classList.add("modal-overlay--open");
    },

    close() {
        if (this.overlay) {
            this.overlay.classList.remove("modal-overlay--open");
        }
    },

    confirm(message) {
        return new Promise((resolve) => {
            const modal = document.createElement("div");
            modal.className = "modal";
            const msg = document.createElement("p");
            msg.className = "modal__message";
            msg.textContent = message;
            modal.appendChild(msg);
            const actions = document.createElement("div");
            actions.className = "modal__actions";
            actions.innerHTML = `
                <button type="button" class="btn btn--primary" data-action="confirm">OK</button>
                <button type="button" class="btn" data-action="cancel">Cancel</button>
            `;
            modal.appendChild(actions);
            modal.querySelector("[data-action='confirm']").addEventListener("click", () => {
                this.close();
                resolve(true);
            });
            modal.querySelector("[data-action='cancel']").addEventListener("click", () => {
                this.close();
                resolve(false);
            });
            this.show(modal);
        });
    },

    alert(message) {
        return new Promise((resolve) => {
            const modal = document.createElement("div");
            modal.className = "modal";
            const msg = document.createElement("p");
            msg.className = "modal__message";
            msg.textContent = message;
            modal.appendChild(msg);
            const actions = document.createElement("div");
            actions.className = "modal__actions";
            actions.innerHTML = `
                <button type="button" class="btn btn--primary" data-action="ok">OK</button>
            `;
            modal.appendChild(actions);
            modal.querySelector("[data-action='ok']").addEventListener("click", () => {
                this.close();
                resolve();
            });
            this.show(modal);
        });
    },
};

document.addEventListener("DOMContentLoaded", () => {
    const waitForAppRecovery = async (maxAttempts = 45, delayMs = 1000) => {
        for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
            try {
                const healthResponse = await fetch("/health", {
                    method: "GET",
                    cache: "no-store",
                });
                if (healthResponse.ok) {
                    window.location.reload();
                    return true;
                }
            } catch {
                // App is likely still restarting; keep polling.
            }
            await new Promise((resolve) => setTimeout(resolve, delayMs));
        }
        return false;
    };

    // Restart form - fetch instead of form submit, no redirect to /restart
    const restartForm = document.getElementById("restart-form");
    if (restartForm) {
        restartForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const confirmed = await Modal.confirm("Restart the app?");
            if (!confirmed) return;

            const btn = restartForm.querySelector("button[type='submit']");
            const originalText = btn.innerHTML;
            const iconMarkup =
                btn.querySelector(".btn__icon")?.outerHTML ||
                '<span class="btn__icon" aria-hidden="true"></span>';
            btn.disabled = true;
            btn.innerHTML = `${iconMarkup} Restarting...`;

            try {
                const response = await fetch(restartForm.action, {
                    method: "POST",
                    redirect: "follow",
                });
                if (response.ok) {
                    const recovered = await waitForAppRecovery();
                    if (!recovered) {
                        await Modal.alert(
                            "Restart is taking longer than expected. Please refresh manually."
                        );
                        btn.disabled = false;
                        btn.innerHTML = originalText;
                    }
                } else {
                    const details = (await response.text()).trim();
                    await Modal.alert(details || "Restart failed.");
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                }
            } catch {
                // Common during service restart; poll health until app is reachable again.
                const recovered = await waitForAppRecovery(60, 1000);
                if (!recovered) {
                    await Modal.alert(
                        "Connection interrupted during restart. The app may still be restarting. Refresh in a few seconds."
                    );
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                }
            }
        });
    }

    // Delete forms - confirm modal, fetch, then navigate to parent
    document.addEventListener("submit", async (e) => {
        const form = e.target.closest(".delete-form");
        if (!form) return;

        e.preventDefault();
        const confirmed = await Modal.confirm("Delete this item?");
        if (!confirmed) return;

        try {
            const response = await fetch(form.action, {
                method: "POST",
                redirect: "follow",
            });
            if (response.redirected) {
                window.location.href = response.url;
            } else {
                window.location.reload();
            }
        } catch {
            window.location.reload();
        }
    });

    // Drag & drop upload
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const uploadForm = document.getElementById("upload-form");

    if (!dropZone || !fileInput || !uploadForm) return;

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            uploadForm.submit();
        }
    });

    ["dragenter", "dragover"].forEach((eventName) => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add("drop-zone--active");
        });
    });

    dropZone.addEventListener("dragleave", (e) => {
        e.preventDefault();
        if (!dropZone.contains(e.relatedTarget)) {
            dropZone.classList.remove("drop-zone--active");
        }
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove("drop-zone--active");
        const files = e.dataTransfer.files;
        if (files.length === 0) return;

        const formData = new FormData();
        for (const file of files) {
            formData.append("file", file);
        }

        fetch(uploadForm.action, {
            method: "POST",
            body: formData,
            redirect: "follow",
        })
            .then((response) => {
                if (response.redirected) {
                    window.location.href = response.url;
                } else {
                    window.location.reload();
                }
            })
            .catch(() => {
                window.location.reload();
            });
    });
});
