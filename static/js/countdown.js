document.addEventListener("DOMContentLoaded", function() {
    // Find all countdown elements on the page
    const countdownElements = document.querySelectorAll("[data-end-time]");
    if (countdownElements.length === 0) return;

    countdownElements.forEach(el => {
        const endTimeStr = el.dataset.endTime;
        if (!endTimeStr) return;

        const endTime = new Date(endTimeStr).getTime();

        const timer = setInterval(function() {
            const now = new Date().getTime();
            const distance = endTime - now;

            if (distance < 0) {
                clearInterval(timer);
                // If it's the next cycle timer, say "STARTING NOW!" instead of "CLOSED"
                if (el.id === "countdown-next") {
                    el.innerHTML = "STARTING NOW!";
                    // Optionally refresh the page after 3 seconds to load the active cycle
                    setTimeout(() => location.reload(), 3000);
                } else {
                    el.innerHTML = "VOTING CLOSED";
                }
                el.style.color = "red";
                return;
            }

            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            el.innerHTML = `${days}d ${hours}h ${minutes}m ${seconds}s`;
        }, 1000);
    });
});
