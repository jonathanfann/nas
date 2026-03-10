/**
 * NAS file browser - drag & drop upload, client-side enhancements
 */

document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const uploadForm = document.getElementById("upload-form");

    if (!dropZone || !fileInput || !uploadForm) return;

    const uploadUrl = uploadForm.action;

    // Click to browse: label already handles this, but we need to auto-submit on file select
    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            uploadForm.submit();
        }
    });

    // Drag and drop
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

        fetch(uploadUrl, {
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
