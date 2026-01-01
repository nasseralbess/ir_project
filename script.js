class WikiSearch {
    constructor() {
        this.searchInput = document.getElementById('searchInput');
        this.searchBtn = document.getElementById('searchBtn');
        this.searchButton = document.getElementById('searchButton');
        this.modelSelect = document.getElementById('modelSelect');
        this.loadingSpinner = document.getElementById('loadingSpinner');
        this.resultsContainer = document.getElementById('resultsContainer');
        this.resultsHeader = document.getElementById('resultsHeader');
        this.resultsCount = document.getElementById('resultsCount');
        this.searchResults = document.getElementById('searchResults');
        this.spellingSuggestion = document.getElementById('spellingSuggestion');
        this.suggestionLink = document.getElementById('suggestionLink');
        
        this.bindEvents();
    }
    
    bindEvents() {
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });
        
        this.searchBtn.addEventListener('click', () => {
            this.performSearch();
        });
        
        this.searchButton.addEventListener('click', () => {
            this.performSearch();
        });

        this.suggestionLink.addEventListener('click', (e) => {
            e.preventDefault();
            this.searchInput.value = this.suggestionLink.textContent;
            this.performSearch();
        });
    }
    
    async performSearch() {
        const query = this.searchInput.value.trim();
        const model = this.modelSelect.value;
        if (!query) return;
        
        this.showLoading();
        this.hideSpellingSuggestion();
        
        try {
            const searchResponse = await this.searchDocuments(query, model);
            
            if (searchResponse.spelling_suggestions) {
                this.displaySpellingSuggestion(searchResponse.spelling_suggestions);
            }

            const documents = await this.fetchDocuments(searchResponse.results);
            this.displayResults(documents, query);
        } catch (error) {
            console.error('Search error:', error);
            this.showError('An error occurred while searching. Please try again.');
        }
    }
    
    
    async searchDocuments(query, model, k = 10) {
        const response = await fetch('https://api.nasseralbess.com/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query, k, model })
        });
        
        if (!response.ok) {
            throw new Error(`Search failed: ${response.status}`);
        }
        
        return await response.json();
    }
    
    async fetchDocument(docId) {
        const response = await fetch(`https://api.nasseralbess.com/document/${docId}`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch document ${docId}: ${response.status}`);
        }
        
        return await response.json();
    }
    
    async fetchDocuments(docIds) {
        const promises = docIds.map(id => this.fetchDocument(id));
        return await Promise.all(promises);
    }
    
    showLoading() {
        this.loadingSpinner.classList.remove('hidden');
        this.resultsContainer.classList.add('hidden');
    }
    
    hideLoading() {
        this.loadingSpinner.classList.add('hidden');
    }

    displaySpellingSuggestion(suggestion) {
        this.suggestionLink.textContent = suggestion;
        this.spellingSuggestion.classList.remove('hidden');
    }

    hideSpellingSuggestion() {
        this.spellingSuggestion.classList.add('hidden');
        this.suggestionLink.textContent = '';
    }
    
    displayResults(documents, query) {
        this.hideLoading();
        
        if (!documents || documents.length === 0) {
            this.showNoResults(query);
            return;
        }
        
        this.resultsCount.textContent = `About ${documents.length} results`;
        this.resultsHeader.classList.remove('hidden');
        this.resultsContainer.classList.remove('hidden');
        
        this.searchResults.innerHTML = '';
        
        documents.forEach(doc => {
            const resultItem = this.createResultItem(doc);
            this.searchResults.appendChild(resultItem);
        });
    }
    
    createResultItem(doc) {
        const item = document.createElement('div');
        item.className = 'result-item';
        
        const url = doc.url || '#';
        const displayUrl = this.formatUrl(url);
        const snippet = this.createSnippet(doc.content);
        
        item.innerHTML = `
            <div class="result-url">${displayUrl}</div>
            <a href="${url}" target="_blank" class="result-title">${this.escapeHtml(doc.title)}</a>
            <div class="result-snippet">${snippet}</div>
            <div class="result-topic">Topic: ${this.escapeHtml(doc.topic)}</div>
        `;
        
        return item;
    }
    
    formatUrl(url) {
        if (!url || url === '#') return 'No URL available';
        
        try {
            const urlObj = new URL(url);
            return urlObj.hostname + urlObj.pathname;
        } catch {
            return url;
        }
    }
    
    createSnippet(content, maxLength = 160) {
        if (!content) return 'No preview available';
        
        const cleaned = content.replace(/\s+/g, ' ').trim();
        if (cleaned.length <= maxLength) return this.escapeHtml(cleaned);
        
        const truncated = cleaned.substring(0, maxLength);
        const lastSpace = truncated.lastIndexOf(' ');
        const snippet = lastSpace > maxLength * 0.8 ? truncated.substring(0, lastSpace) : truncated;
        
        return this.escapeHtml(snippet) + '...';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showNoResults(query) {
        this.hideLoading();
        this.resultsContainer.classList.remove('hidden');
        this.resultsHeader.classList.add('hidden');
        this.searchResults.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #70757a;">
                <p>No results found for "${this.escapeHtml(query)}"</p>
                <p style="margin-top: 10px; font-size: 14px;">Try different keywords or check your spelling</p>
            </div>
        `;
    }
    
    showError(message) {
        this.hideLoading();
        this.resultsContainer.classList.remove('hidden');
        this.resultsHeader.classList.add('hidden');
        this.searchResults.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #d93025;">
                <p>${this.escapeHtml(message)}</p>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new WikiSearch();
});