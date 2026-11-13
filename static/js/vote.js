document.addEventListener("DOMContentLoaded", function() {
    const searchInput = document.getElementById("search-input");
    const searchResults = document.getElementById("search-results");
    const selectedPlayers = document.getElementById("selected-players");
    const entriesInput = document.getElementById("entries-input");
    const form = document.getElementById("vote-form");

    function createPlayerCard(player) {
        const div = document.createElement("div");
        const pId = player.id || player.player_id;
        
        div.id = `player-${pId}`;
        div.dataset.id = pId;
        div.dataset.osuId = player.osu_user_id;
        div.dataset.json = JSON.stringify(player); // Store player data for draft saving
        div.className = "player-card";
        
        const rankText = player.country_rank ? `#${player.country_rank} MY` : `MY`;
        
        div.innerHTML = `
            <div class="card-header" style="display: flex; align-items: center; width: 100%;">
                <div class="rank-container"></div>
                <img src="${player.avatar_url}" style="width: 32px; height: 32px; border-radius: 50%; margin-right: 12px;">
                <div style="display: flex; flex-direction: column;">
                    <strong style="font-size: 1.1em;">${player.username}</strong>
                    <span style="color: #888; font-size: 0.85em;">${rankText} • ${Math.round(player.pp)}pp</span>
                </div>
                <div class="remove-container" style="margin-left: auto;"></div>
            </div>
        `;
        
        div.addEventListener('click', function(e) {
            if (e.target.closest('button') || e.target.tagName === 'TEXTAREA') return;
            if (this.parentElement !== searchResults) return;
            
            if (selectedPlayers.children.length >= 15) {
                alert("You can only select 15 players!");
                return;
            }
            selectedPlayers.appendChild(this);
            updateRanks();
        });
        
        return div;
    }

    function fetchPlayers(query = "") {
        if (query.length === 1) return;
        fetch(`/api/players/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                searchResults.innerHTML = "";
                data.results.forEach(player => {
                    if (player.osu_user_id == CURRENT_OSU_ID) return;
                    if (document.getElementById(`player-${player.id}`)) return;
                    searchResults.appendChild(createPlayerCard(player));
                });
            });
    }

    let searchTimeout;
    searchInput.addEventListener("input", function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        searchTimeout = setTimeout(() => { fetchPlayers(query); }, 300);
    });

    const sortableConfig = {
        group: 'shared',
        animation: 150,
        filter: 'textarea, button', 
        preventOnFilter: false,
        ghostClass: 'sortable-ghost',
	delay: 200,
	delayOnTouchOnly: true,
        onEnd: function () { updateRanks(); }
    };

    new Sortable(selectedPlayers, {
        ...sortableConfig,
        onAdd: function (evt) {
            if (selectedPlayers.children.length > 15) {
                evt.from.appendChild(evt.item); 
                alert("You can only select exactly 15 players!");
                return;
            }
            updateRanks();
        }
    });

    new Sortable(searchResults, {
        ...sortableConfig,
        onAdd: function (evt) {
            cleanupCard(evt.item);
            updateRanks();
            fetchPlayers(""); 
        }
    });

    function cleanupCard(item) {
        let badge = item.querySelector(".rank-badge");
        if (badge) badge.remove();
        let wrapper = item.querySelector(".comment-wrapper");
        if (wrapper) wrapper.remove();
        let rmBtn = item.querySelector(".remove-btn");
        if (rmBtn) rmBtn.remove();
    }

    function updateRanks() {
        const items = selectedPlayers.querySelectorAll("[data-id]");
        
        items.forEach((item, index) => {
            const header = item.querySelector('.card-header');
            let rankBadge = item.querySelector(".rank-badge");
            
            if (!rankBadge) {
                rankBadge = document.createElement("span");
                rankBadge.className = "rank-badge";
                rankBadge.style = "font-weight: bold; font-size: 1.2em; color: #ff66aa; min-width: 35px; display: inline-block; text-align: center;";
                header.prepend(rankBadge);
            }
            rankBadge.innerText = `#${index + 1}`;

            if (!item.querySelector(".comment-wrapper")) {
                if (!item.querySelector(".remove-btn")) {
                    const removeBtn = document.createElement("button");
                    removeBtn.innerHTML = "&times;"; 
                    removeBtn.type = "button";
                    removeBtn.className = "remove-btn";
                    removeBtn.style = "background: none; border: none; cursor: pointer; font-size: 1.5em; color: #dc3545; padding: 0 10px;";
                    
                    removeBtn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        cleanupCard(item);
                        searchResults.appendChild(item);
                        updateRanks();
                        fetchPlayers(""); 
                    });
                    
                    item.querySelector('.remove-container').appendChild(removeBtn);
                }

                const commentWrapper = document.createElement("div");
                commentWrapper.className = "comment-wrapper";
                commentWrapper.style = "margin-top: 10px; width: 100%;";
                commentWrapper.innerHTML = `
                    <textarea class="comment-box" placeholder="Why did you vote for this player? (Optional)" style="width: 100%; font-size: 0.9em; resize: vertical; box-sizing: border-box; background: var(--bg-color); color: var(--text-color); border: 1px solid var(--border-color); border-radius: 6px; padding: 10px;" rows="3"></textarea>
                    <div style="display: flex; justify-content: space-between; font-size: 0.8em; margin-top: 4px;">
                        <span class="char-counter" style="margin-left: auto; color: #888;">0/500</span>
                    </div>
                `;
                item.appendChild(commentWrapper);

                const textarea = commentWrapper.querySelector('.comment-box');
                const counter = commentWrapper.querySelector('.char-counter');
                
                textarea.addEventListener('input', function() {
                    const length = this.value.length;
                    counter.innerText = `${length}/500`;
                    counter.style.color = length > 500 ? 'red' : '#888';
                    checkSubmitStatus();
                    saveDraft(); // AUTO-SAVE ON TYPING
                });
            }
        });
        saveDraft(); // AUTO-SAVE ON DRAG/REORDER
    }

    function checkSubmitStatus() {
        let invalid = false;
        document.querySelectorAll('.comment-box').forEach(box => {
            if (box.value.length > 500) invalid = true;
        });
        document.getElementById("submit-btn").disabled = invalid;
    }

    // --- AUTO-SAVE DRAFT FEATURE ---
    function saveDraft() {
        const items = selectedPlayers.querySelectorAll("[data-id]");
        const draftData = [];
        
        items.forEach(item => {
            const playerData = JSON.parse(item.dataset.json || "{}");
            const textarea = item.querySelector('.comment-box');
            draftData.push({
                player: playerData,
                comment: textarea ? textarea.value : ""
            });
        });
        
        localStorage.setItem(`osu_vote_draft_${CYCLE_ID}`, JSON.stringify(draftData));
    }

    function loadDraft() {
        const draftString = localStorage.getItem(`osu_vote_draft_${CYCLE_ID}`);
        if (!draftString) return;

        try {
            const draftData = JSON.parse(draftString);
            if (draftData.length > 0) {
                selectedPlayers.innerHTML = "";
                draftData.forEach(entry => {
                    const card = createPlayerCard(entry.player);
                    selectedPlayers.appendChild(card);
                });
                updateRanks();
                
                setTimeout(() => {
                    draftData.forEach(entry => {
                        if (entry.comment) {
                            const pId = entry.player.id || entry.player.player_id;
                            const card = document.getElementById(`player-${pId}`);
                            if (card) {
                                const textarea = card.querySelector('.comment-box');
                                if (textarea) {
                                    textarea.value = entry.comment;
                                    textarea.dispatchEvent(new Event('input'));
                                }
                            }
                        }
                    });
                }, 100);
            }
        } catch (e) {
            console.error("Failed to load draft", e);
        }
    }

    // --- INITIALIZATION ---
    const existingEntriesElement = document.getElementById("existing-entries");
    if (existingEntriesElement) {
        // EDIT MODE: Load from Database
        const existingEntries = JSON.parse(existingEntriesElement.textContent);
        const existingCommentsElement = document.getElementById("existing-comments");
        const existingComments = existingCommentsElement ? JSON.parse(existingCommentsElement.textContent) : {};

        selectedPlayers.innerHTML = "";
        existingEntries.sort((a, b) => a.rank - b.rank);

        existingEntries.forEach(entry => {
            selectedPlayers.appendChild(createPlayerCard(entry));
        });

        updateRanks();

        setTimeout(() => {
            existingEntries.forEach(entry => {
                const pId = entry.id || entry.player_id;
                if (existingComments[pId]) {
                    const card = document.getElementById(`player-${pId}`);
                    if (card) {
                        const textarea = card.querySelector('.comment-box');
                        if (textarea) {
                            textarea.value = existingComments[pId];
                            textarea.dispatchEvent(new Event('input'));
                        }
                    }
                }
            });
        }, 100); 
        
        fetchPlayers("");
    } else {
        // NEW VOTE MODE: Load Draft if it exists
        loadDraft();
        fetchPlayers("");
    }

    form.addEventListener("submit", function(e) {
        const items = selectedPlayers.querySelectorAll("[data-id]");
        if (items.length !== 15) {
            e.preventDefault();
            alert("You must select exactly 15 players before submitting.");
            return;
        }

        const entries = [];
        const comments = {};

        items.forEach((item, index) => {
            const player_id = parseInt(item.dataset.id);
            entries.push({ player_id: player_id, rank: index + 1 });
            const textarea = item.querySelector('.comment-box');
            if (textarea && textarea.value.trim() !== "") {
                comments[player_id] = textarea.value.trim();
            }
        });

        entriesInput.value = JSON.stringify(entries);
        document.getElementById("comments-input").value = JSON.stringify(comments);
        
        // Clear the draft since we are successfully submitting
        localStorage.removeItem(`osu_vote_draft_${CYCLE_ID}`);
        
        document.getElementById("submit-btn").disabled = true;
        document.getElementById("submit-btn").innerText = "Submitting...";
    });
});
