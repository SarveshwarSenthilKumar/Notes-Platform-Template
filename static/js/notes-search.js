document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('noteSearch');
    const noResults = document.getElementById('noResults');
    let searchTimeout;
    const noteContents = new Map(); // Cache for note contents
    let showOnlyWithWorksheets = false;
    
    // Create and add worksheet filter button
    const searchContainer = document.querySelector('.search-container');
    if (searchContainer) {
        const worksheetFilterBtn = document.createElement('button');
        worksheetFilterBtn.id = 'worksheetFilter';
        worksheetFilterBtn.title = 'Show only notes with worksheets';
        worksheetFilterBtn.innerHTML = '📎';
        worksheetFilterBtn.style.background = 'transparent';
        worksheetFilterBtn.style.border = '1px solid var(--primary)';
        worksheetFilterBtn.style.borderRadius = '4px';
        worksheetFilterBtn.style.padding = '0.5rem';
        worksheetFilterBtn.style.cursor = 'pointer';
        worksheetFilterBtn.style.marginLeft = '0.5rem';
        worksheetFilterBtn.style.color = '#8892b0';
        worksheetFilterBtn.style.transition = 'all 0.2s ease';
        
        worksheetFilterBtn.addEventListener('click', function() {
            showOnlyWithWorksheets = !showOnlyWithWorksheets;
            this.style.background = showOnlyWithWorksheets ? 'rgba(100, 255, 218, 0.1)' : 'transparent';
            this.style.color = showOnlyWithWorksheets ? 'var(--primary)' : '#8892b0';
            filterNotes();
        });
        
        const searchWrapper = document.createElement('div');
        searchWrapper.style.display = 'flex';
        searchWrapper.style.alignItems = 'center';
        searchWrapper.style.width = '100%';
        
        searchContainer.appendChild(searchWrapper);
        searchWrapper.appendChild(searchInput);
        searchWrapper.appendChild(worksheetFilterBtn);
    }
    
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(filterNotes, 300);
        });
        
        // Add keyboard shortcut to focus search (Cmd+K / Ctrl+K)
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                searchInput.focus();
            } else if (e.key === 'Escape' && document.activeElement === searchInput) {
                searchInput.blur();
            }
        });
    }
    
    async function filterNotes() {
        const searchTerm = searchInput.value.trim().toLowerCase();
        const noteCards = document.querySelectorAll('.note-card');
        let hasVisibleNotes = false;
        let hasVisibleUnits = false;
        
        // Hide all cards initially
        noteCards.forEach(card => card.style.display = 'none');

        if (!searchTerm) {
            // Show all notes if search is empty
            noteCards.forEach(card => {
                card.style.display = '';
                // Reset highlights
                const titleElement = card.querySelector('.title-text');
                const contentElement = card.querySelector('.content-preview');
                if (titleElement) titleElement.innerHTML = titleElement.textContent;
                if (contentElement) contentElement.innerHTML = contentElement.textContent;
            });
            
            document.querySelectorAll('.unit-section').forEach(section => {
                section.style.display = '';
                updateUnitVisibility(section);
            });
            
            noResults.classList.add('hidden');
            return;
        }
        
        // First, search through visible fields
        const visibleMatches = [];
        const contentSearchPromises = [];
        
        noteCards.forEach(card => {
            const noteId = card.getAttribute('data-id');
            const title = card.getAttribute('data-title') || '';
            const preview = card.getAttribute('data-content') || '';
            const unit = card.getAttribute('data-unit') || '';
            const tags = card.getAttribute('data-tags') || '';
            const date = card.getAttribute('data-date') || '';
            const favorite = card.getAttribute('data-favorite') || '';
            const hasWorksheet = card.getAttribute('data-has-worksheet') === 'true';
            
            // Apply worksheet filter
            if (showOnlyWithWorksheets && !hasWorksheet) {
                return; // Skip notes without worksheets when filter is active
            }
            
            // Check visible fields first
            if (searchTerm && (title.includes(searchTerm) || 
                preview.includes(searchTerm) || 
                unit.includes(searchTerm) ||
                tags.includes(searchTerm) ||
                date.includes(searchTerm) ||
                favorite.includes(searchTerm))) {
                visibleMatches.push(card);
            } else if (noteId && searchTerm) {
                // If not found in visible fields, check full content
                contentSearchPromises.push(
                    checkFullContent(card, noteId, searchTerm)
                        .then(hasMatch => {
                            if (hasMatch) {
                                visibleMatches.push(card);
                            }
                        })
                );
            }
        });

        // Wait for all content checks to complete
        await Promise.all(contentSearchPromises);
        
        // Show all matches
        visibleMatches.forEach(card => {
            card.style.display = '';
            hasVisibleNotes = true;
            
            const titleElement = card.querySelector('.title-text');
            const contentElement = card.querySelector('.content-preview');
            
            if (titleElement) {
                titleElement.innerHTML = highlightText(titleElement.textContent, searchTerm);
            }
            
            // Only highlight content if it's not from a full content search
            // (full content matches are handled in showCardWithMatch)
            if (contentElement && !card.classList.contains('full-content-match')) {
                contentElement.innerHTML = highlightText(contentElement.textContent, searchTerm);
            }
        });
        
        // Update unit visibility
        document.querySelectorAll('.unit-section').forEach(section => {
            updateUnitVisibility(section);
            if (section.style.display !== 'none') {
                hasVisibleUnits = true;
            }
        });
        
        // Show appropriate messages
        if (noteCards.length > 0 && !hasVisibleNotes) {
            noResults.classList.remove('hidden');
        } else {
            noResults.classList.add('hidden');
        }
    }
    
    async function checkFullContent(card, noteId, searchTerm) {
        try {
            // Check cache first
            let content = noteContents.get(noteId);
            
            // If not in cache, fetch from server
            if (!content) {
                try {
                    const response = await fetch(`/notes/${noteId}/content`);
                    if (!response.ok) return false;
                    
                    const data = await response.json();
                    if (!data.content) return false;
                    
                    content = data.content.toLowerCase();
                    noteContents.set(noteId, content);
                } catch (error) {
                    console.error('Error fetching note content:', error);
                    return false;
                }
                
                content = data.content.toLowerCase();
                noteContents.set(noteId, content);
            }
            
            // Check if content contains search term
            if (content.includes(searchTerm)) {
                showCardWithMatch(card, content, searchTerm);
                return true;
            }
            
            return false;
        } catch (error) {
            console.error('Error fetching note content:', error);
            return false;
        }
    }
    
    function showCardWithMatch(card, fullContent, searchTerm) {
        // Mark this card as a full content match for styling
        card.classList.add('full-content-match');
        
        // Find the match position
        const matchIndex = fullContent.indexOf(searchTerm);
        if (matchIndex === -1) return;
        
        // Get context around the match (100 chars before and after)
        const start = Math.max(0, matchIndex - 100);
        const end = Math.min(fullContent.length, matchIndex + searchTerm.length + 100);
        let context = fullContent.substring(start, end);
        
        // Add ellipsis if not at start/end
        if (start > 0) context = '...' + context;
        if (end < fullContent.length) context = context + '...';
        
        // Highlight the match
        const highlightedContent = highlightText(context, searchTerm);
        
        // Update the content preview
        const contentElement = card.querySelector('.content-preview');
        if (contentElement) {
            contentElement.innerHTML = highlightedContent;
        }
    }
    
    function updateUnitVisibility(section) {
        const unitId = section.getAttribute('data-unit');
        const hasVisibleNotes = Array.from(document.querySelectorAll(`.note-card[data-unit="${unitId}"]`))
            .some(card => card.style.display !== 'none');
        
        section.style.display = hasVisibleNotes ? '' : 'none';
        
        // Update unit count
        const unitCount = section.querySelector('.unit-count');
        if (unitCount) {
            const visibleCount = section.querySelectorAll('.note-card:not([style*="display: none"])').length;
            unitCount.textContent = `(${visibleCount} note${visibleCount !== 1 ? 's' : ''})`;
        }
    }
    
    function highlightText(text, searchTerm) {
        if (!searchTerm) return text;
        // Escape special regex characters except space
        const escapedSearch = searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        // Match whole words only (word boundaries)
        const regex = new RegExp(`(\\b${escapedSearch}\\b)`, 'gi');
        return text.replace(regex, '<span class="highlight">$1</span>');
    }
    
    // Initialize unit visibility
    document.querySelectorAll('.unit-section').forEach(updateUnitVisibility);
});
