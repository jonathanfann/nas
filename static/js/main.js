/**
 * NAS file browser - client-side enhancements
 */

document.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.getElementById("file-input");
    if (fileInput) {
        fileInput.addEventListener("change", (e) => {
            const count = e.target.files?.length ?? 0;
            if (count > 0) {
                console.log(`Selected ${count} file(s) for upload`);
            }
        });
    }
});
