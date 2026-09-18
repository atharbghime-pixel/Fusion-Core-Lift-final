// Fusion Core Lift - minimal client-side helpers
// Core functionality works without JavaScript; this only adds small UX polish.

document.addEventListener("DOMContentLoaded", function () {
    // Auto-dismiss alerts after a few seconds
    var alerts = document.querySelectorAll(".alert");
    alerts.forEach(function (alertEl) {
        setTimeout(function () {
            if (window.bootstrap && window.bootstrap.Alert) {
                var instance = window.bootstrap.Alert.getOrCreateInstance(alertEl);
                instance.close();
            }
        }, 6000);
    });
});
