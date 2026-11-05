document.addEventListener("DOMContentLoaded", function() {
    // 1. Check for saved theme
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "dark") {
        document.documentElement.setAttribute("data-theme", "dark");
    }

    // 2. Add toggle button to header
    const nav = document.querySelector("nav");
    if (nav) {
        const toggleBtn = document.createElement("a");
        toggleBtn.href = "#";
        toggleBtn.style.marginLeft = "15px";
        toggleBtn.style.fontSize = "1.2em";
        toggleBtn.innerText = savedTheme === "dark" ? "☀️" : "🌙";
        
        toggleBtn.addEventListener("click", function(e) {
            e.preventDefault();
            const isDark = document.documentElement.getAttribute("data-theme") === "dark";
            
            if (isDark) {
                document.documentElement.removeAttribute("data-theme");
                localStorage.setItem("theme", "light");
                toggleBtn.innerText = "🌙";
            } else {
                document.documentElement.setAttribute("data-theme", "dark");
                localStorage.setItem("theme", "dark");
                toggleBtn.innerText = "☀️";
            }
        });
        nav.appendChild(toggleBtn);
    }
});