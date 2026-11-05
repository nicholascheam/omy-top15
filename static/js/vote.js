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
                    // Don't show yourself in the search results
                    if (player.osu_user_id == CURRENT_OSU_ID) return;
                    // Don't show players already in the right column
                    if (document.getElementById(`player-${player.id}`)) return;

                    const div = document.createElement("div");
                    div.id = `player-${player.id}`;
                    div.dataset.id = player.id;
                    div.dataset.username = player.username;
                    div.className = "player-card";
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

    // 3. Helper function to update visual ranks AND add comment boxes
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

            // --- NEW: Add Comment Textarea ---
            if (!item.querySelector(".comment-wrapper")) {
                const commentWrapper = document.createElement("div");
                commentWrapper.className = "comment-wrapper";
                commentWrapper.style = "margin-top: 8px; width: 100%;";
                commentWrapper.innerHTML = `
                    <textarea class="comment-box" placeholder="Why did you vote for this player? (Optional)" style="width: 100%; font-size: 0.9em; resize: vertical; box-sizing: border-box; background: var(--bg-color); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 4px; padding: 5px;" rows="2"></textarea>
                    <div style="display: flex; justify-content: space-between; font-size: 0.8em; margin-top: 4px;">
                        <span class="error-text" style="color: red; font-weight: bold; display: none;">Comment exceeds 500 characters!</span>
                        <span class="char-counter" style="margin-left: auto; color: #888;">0/500</span>
                    </div>
                `;
                item.appendChild(commentWrapper);

                const textarea = commentWrapper.querySelector('.comment-box');
                const counter = commentWrapper.querySelector('.char-counter');
                const errorText = commentWrapper.querySelector('.error-text');
                
                textarea.addEventListener('input', function() {
                    const length = this.value.length;
                    counter.innerText = `${length}/500`;
                    
                    if (length > 500) {
                        counter.style.color = 'red';
                        counter.style.fontWeight = 'bold';
                        errorText.style.display = 'inline';
                    } else {
                        counter.style.color = '#888';
                        counter.style.fontWeight = 'normal';
                        errorText.style.display = 'none';
                    }
                    checkSubmitStatus();
                });
            }
        });
        
        // Check for self-votes
        let hasSelfVote = false;
        items.forEach(item => {
            if (item.dataset.osuId == CURRENT_OSU_ID) {
                hasSelfVote = true;
            }
        });

        const errDiv = document.getElementById("form-errors");
        if (hasSelfVote) {
            errDiv.innerText = "You cannot vote for yourself! Please remove yourself from the list.";
            errDiv.style.display = "block";
            document.getElementById("submit-btn").disabled = true;
        } else {
            errDiv.style.display = "none";
            checkSubmitStatus(); // Re-enable button if comment length is valid
        }
    }

    // 4. Function to disable submit if any comment is > 500 chars
    function checkSubmitStatus() {
        let invalid = false;
        document.querySelectorAll('.comment-box').forEach(box => {
            if (box.value.length > 500) {
                invalid = true;
            }
        });
        document.getElementById("submit-btn").disabled = invalid;
    }
    // 5. Handle Edit Mode (Pre-fill existing ballot)
    const existingEntriesElement = document.getElementById("existing-entries");
    if (existingEntriesElement) {
        // Clear any existing players in the right column to prevent duplicates
        selectedPlayers.innerHTML = ""; 
        const existingEntries = JSON.parse(existingEntriesElement.textContent);
        const existingCommentsElement = document.getElementById("existing-comments");
        const existingComments = existingCommentsElement ? JSON.parse(existingCommentsElement.textContent) : {};

        // Sort by rank
        existingEntries.sort((a, b) => a.rank - b.rank);

        existingEntries.forEach(entry => {
            // Create the player card (same structure as search results)
            const div = document.createElement("div");
            div.id = `player-${entry.player_id}`;
            div.dataset.id = entry.player_id;
            div.dataset.username = entry.username;
            div.className = "player-card";
            div.innerHTML = `
                <img src="${entry.avatar_url}" style="width: 24px; height: 24px; border-radius: 50%; margin-right: 10px;">
                <strong>${entry.username}</strong> <span style="color: #666; margin-left: 5px;">(${Math.round(entry.pp)}pp)</span>
            `;
            selectedPlayers.appendChild(div);
        });

        // Trigger updateRanks to add the #1, #2 badges and the textareas
        updateRanks();

        // Now populate the comments into the newly created textareas
        setTimeout(() => {
            existingEntries.forEach(entry => {
                if (existingComments[entry.player_id]) {
                    const card = document.getElementById(`player-${entry.player_id}`);
                    if (card) {
                        const textarea = card.querySelector('.comment-box');
                        if (textarea) {
                            textarea.value = existingComments[entry.player_id];
                            // Trigger the input event to update the character counter
                            textarea.dispatchEvent(new Event('input'));
                        }
                    }
                }
            });
        }, 100); // Small timeout to let the DOM settle
    }
    // 6. Update hidden inputs on submit
    form.addEventListener("submit", function(e) {
        const items = selectedPlayers.querySelectorAll("[data-id]");
        
        if (items.length !== 15) {
            e.preventDefault();
            alert("You must select exactly 15 players before submitting.");
            return;
        }

        let selfVote = false;
        items.forEach(item => {
            if (item.dataset.osuId == CURRENT_OSU_ID) selfVote = true;
        });

        if (selfVote) {
            e.preventDefault();
            const errDiv = document.getElementById("form-errors");
            errDiv.innerText = "You cannot vote for yourself!";
            errDiv.style.display = "block";
            return;
        }

        const entries = [];
        const comments = {};

        items.forEach((item, index) => {
            const player_id = parseInt(item.dataset.id);
            
            entries.push({
                player_id: player_id,
                rank: index + 1
            });

            const textarea = item.querySelector('.comment-box');
            if (textarea && textarea.value.trim() !== "") {
                comments[player_id] = textarea.value.trim();
            }
        });

        entriesInput.value = JSON.stringify(entries);
        document.getElementById("comments-input").value = JSON.stringify(comments);
        
        // Disable the submit button to prevent double-clicks
        document.getElementById("submit-btn").disabled = true;
        document.getElementById("submit-btn").innerText = "Submitting...";
    });
});