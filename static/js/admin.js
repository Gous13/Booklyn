// Simple confirmation for delete/approve/reject actions
document.addEventListener("DOMContentLoaded", function () {
    const confirmLinks = document.querySelectorAll(".confirm-action");

    confirmLinks.forEach(link => {
        link.addEventListener("click", function (e) {
            const msg = this.getAttribute("data-message") || "Are you sure?";
            if (!confirm(msg)) {
                e.preventDefault();
            }
        });
    });
});
