document.addEventListener("DOMContentLoaded", function() {
    const countdownElement = document.getElementById("countdown");
    if (!countdownElement) return;

    // Get the ISO string from the template (we'll pass it via data attribute)
    const endTimeStr = countdownElement.dataset.endTime;
    if (!endTimeStr) return;

    const endTime = new Date(endTimeStr).getTime();

    const timer = setInterval(function() {
        const now = new Date().getTime();
        const distance = endTime - now;

        if (distance < 0) {
            clearInterval(timer);
            countdownElement.innerHTML = "VOTING CLOSED";
            countdownElement.style.color = "red";
            return;
        }

        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);

        countdownElement.innerHTML = `${days}d ${hours}h ${minutes}m ${seconds}s`;
    }, 1000);
});