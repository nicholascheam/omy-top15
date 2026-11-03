document.addEventListener("DOMContentLoaded", function() {
    const searchInput = document.getElementById("search-input");
    const searchResults = document.getElementById("search-results");
    const selectedPlayers = document.getElementById("selected-players");
    const entriesInput = document.getElementById("entries-input");
    const form = document.getElementById("vote-form");

    // Function to fetch players (default top 50 or search results)
    function fetchPlayers(query = "") {
        // If query is exactly 1 char, don't fetch yet
        if (query.length === 1) return;

        fetch(`/api/players/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                searchResults.innerHTML = "";
                data.results.forEach(player => {
                    // Don't show players already in the right column
                    if (document.getElementById(`player-${player.id}`)) return;

                    const div = document.createElement("div");
                    div.id = `player-${player.id}`;
                    div.dataset.id = player.id;
                    div.dataset.username = player.username;
                    div.style = "padding: 10px; border: 1px solid #ddd; margin-bottom: 5px; background: white; cursor: grab; display: flex; align-items: center;";
                    div.innerHTML = `
                        <img src="${player.avatar_url}" style="width: 24px; height: 24px; border-radius: 50%; margin-right: 10px;">
                        <strong>${player.username}</strong> <span style="color: #666; margin-left: 5px;">(${Math.round(player.pp)}pp)</span>
                    `;
                    searchResults.appendChild(div);
                });
            });
    }

    // Load the Top 50 players by default on page load
    fetchPlayers("");

    // Search input listener
    let searchTimeout;
    searchInput.addEventListener("input", function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();

        searchTimeout = setTimeout(() => {
            fetchPlayers(query);
        }, 300);
    });

    // 1. Initialize SortableJS for the "Top 15" (Right List)
    new Sortable(selectedPlayers, {
        group: 'shared',
        animation: 150,
        onAdd: function (evt) {
            // If they try to drag a 16th player in, reject it!
            if (selectedPlayers.children.length > 15) {
                // Revert the drag back to the left list
                evt.from.appendChild(evt.item); 
                
                // Show a red warning message
                let warning = document.getElementById("max-warning");
                if (!warning) {
                    warning = document.createElement("div");
                    warning.id = "max-warning";
                    warning.style = "color: red; font-weight: bold; margin-bottom: 10px;";
                    selectedPlayers.parentNode.insertBefore(warning, selectedPlayers);
                }
                warning.innerText = "You can only select exactly 15 players!";
                
                // Make it shake
                warning.animate([
                    { transform: 'translateX(0)' },
                    { transform: 'translateX(-10px)' },
                    { transform: 'translateX(10px)' },
                    { transform: 'translateX(-10px)' },
                    { transform: 'translateX(10px)' },
                    { transform: 'translateX(0)' }
                ], { duration: 300 });
                
                // Remove warning after 3 seconds
                setTimeout(() => { warning.remove(); }, 3000);
                return;
            }
            updateRanks();
        },
        onEnd: function () {
            updateRanks();
        }
    });

    // 2. Initialize SortableJS for the Search List (Left List)
    new Sortable(searchResults, {
        group: 'shared',
        animation: 150,
        onAdd: function (evt) {
            // Dragged back to search -> remove rank badge
            let rankBadge = evt.item.querySelector(".rank-badge");
            if (rankBadge) rankBadge.remove();
            updateRanks();
        },
        onEnd: function () {
            updateRanks();
        }
    });

    // 3. Helper function to update visual ranks (1, 2, 3...)
    function updateRanks() {
        const items = selectedPlayers.querySelectorAll("[data-id]");
        items.forEach((item, index) => {
            let rankBadge = item.querySelector(".rank-badge");
            if (!rankBadge) {
                rankBadge = document.createElement("span");
                rankBadge.className = "rank-badge";
                rankBadge.style = "font-weight: bold; font-size: 1.2em; margin-right: 10px; color: #007bff; width: 30px; display: inline-block;";
                item.prepend(rankBadge);
            }
            rankBadge.innerText = `#${index + 1}`;
        });
    }

    // 4. Update hidden inputs on submit
    form.addEventListener("submit", function(e) {
        const items = selectedPlayers.querySelectorAll("[data-id]");
        
        if (items.length !== 15) {
            e.preventDefault();
            return;
        }

        const entries = [];
        items.forEach((item, index) => {
            entries.push({
                player_id: parseInt(item.dataset.id),
                rank: index + 1
            });
        });

        entriesInput.value = JSON.stringify(entries);
        document.getElementById("comments-input").value = JSON.stringify({});
    });
});