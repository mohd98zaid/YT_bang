// VideoDownloader Web - Client Application

// Initialize SocketIO connection
const socket = io();

// State management
let currentTab = 'download';
let queueItems = [];
let historyItems = [];
let historyOffset = 0;

// DOM Elements
const downloadForm = document.getElementById('download-form');
const typeSelect = document.getElementById('type-select');
const qualitySelect = document.getElementById('quality-select');
const formatGroup = document.getElementById('format-group');
const subtitlesOption = document.getElementById('subtitles-option');
const logContainer = document.getElementById('log-container');
const queueList = document.getElementById('queue-list');
const historyList = document.getElementById('history-list');
const statsContainer = document.getElementById('stats-container');
const queueCount = document.getElementById('queue-count');
const activeCount = document.getElementById('active-count');

// Tab switching
document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', () => {
        const tab = button.dataset.tab;
        switchTab(tab);
    });
});

function switchTab(tab) {
    // Update active states
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
    document.getElementById(`${tab}-tab`).classList.add('active');

    currentTab = tab;

    // Load data for specific tabs
    if (tab === 'queue') {
        loadQueue();
    } else if (tab === 'history') {
        loadHistory();
        loadStatistics();
    } else if (tab === 'settings') {
        loadSettings();
    }
}

// Download type change handler
typeSelect.addEventListener('change', () => {
    const type = typeSelect.value;

    if (type === 'audio') {
        formatGroup.style.display = 'block';
        subtitlesOption.style.display = 'none';
    } else {
        formatGroup.style.display = 'none';
        subtitlesOption.style.display = type === 'video' ? 'flex' : 'none';
    }
});

// Download form submission
downloadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const url = document.getElementById('url-input').value.trim();
    const download_type = typeSelect.value;
    const quality = qualitySelect.value;
    const format_type = document.getElementById('format-select').value;
    const embed_metadata = document.getElementById('embed-metadata').checked;
    const embed_thumbnail = document.getElementById('embed-thumbnail').checked;
    const embed_subtitles = document.getElementById('embed-subtitles').checked;

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                download_type,
                quality,
                format_type,
                embed_metadata,
                embed_thumbnail,
                embed_subtitles
            })
        });

        const data = await response.json();

        if (data.success) {
            addLog('✓ Download added to queue');
            document.getElementById('url-input').value = '';
            loadQueue();
        } else {
            addLog('✗ Error: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        addLog('✗ Network error: ' + error.message);
    }
});

// Queue management
async function loadQueue() {
    try {
        const response = await fetch('/api/queue');
        const data = await response.json();

        queueItems = data.queue || [];
        renderQueue();
        updateStats();
    } catch (error) {
        console.error('Error loading queue:', error);
    }
}

function renderQueue() {
    if (queueItems.length === 0) {
        queueList.innerHTML = '<p style="text-align: center; color: var(--text-muted); padding: 2rem;">No downloads in queue</p>';
        return;
    }

    queueList.innerHTML = queueItems.map(item => `
        <div class="download-item ${item.status.toLowerCase()}" data-id="${item.id}">
            <div class="download-header">
                <div class="download-title">${escapeHtml(item.title)}</div>
                <span class="download-status status-${item.status.toLowerCase().replace(' ', '-')}">${item.status}</span>
            </div>
            <div class="download-info">
                <span>${item.download_type}</span>
                <span>${item.quality}</span>
                ${item.channel ? `<span>${escapeHtml(item.channel)}</span>` : ''}
                ${item.duration ? `<span>${item.duration}</span>` : ''}
            </div>
            ${item.status === 'Downloading' || item.status === 'Processing' ? `
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${item.progress}%"></div>
                    </div>
                    <div class="progress-text">
                        <span>${item.progress.toFixed(1)}%</span>
                        <span>Speed: ${item.speed} | ETA: ${item.eta}</span>
                    </div>
                </div>
            ` : ''}
            ${item.status === 'Queued' || item.status === 'Downloading' ? `
                <button class="btn btn-secondary" style="margin-top: 0.5rem;" onclick="cancelDownload('${item.id}')">Cancel</button>
            ` : ''}
        </div>
    `).join('');
}

async function cancelDownload(id) {
    try {
        const response = await fetch(`/api/download/${id}`, { method: 'DELETE' });
        const data = await response.json();

        if (data.success) {
            addLog('Download cancelled');
            loadQueue();
        }
    } catch (error) {
        console.error('Error cancelling download:', error);
    }
}

// History management
function loadHistory(append = false) {
    try {
        const historyJson = localStorage.getItem('downloadHistory');
        let allHistory = historyJson ? JSON.parse(historyJson) : [];

        // Sort by created_at desc
        allHistory.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));

        const search = document.getElementById('history-search')?.value.toLowerCase() || '';
        if (search) {
            allHistory = allHistory.filter(item =>
                (item.title && item.title.toLowerCase().includes(search)) ||
                (item.url && item.url.toLowerCase().includes(search))
            );
        }

        // Simple pagination simulation
        const limit = 20;
        if (!append) {
            historyOffset = 0;
            historyItems = allHistory.slice(0, limit);
        } else {
            const nextItems = allHistory.slice(historyOffset, historyOffset + limit);
            historyItems.push(...nextItems);
        }
        historyOffset = historyItems.length;

        renderHistory();

        // Hide load more if no more items
        const loadMoreBtn = document.getElementById('load-more-history');
        if (loadMoreBtn) {
            loadMoreBtn.style.display = historyOffset >= allHistory.length ? 'none' : 'block';
        }

    } catch (error) {
        console.error('Error loading history:', error);
    }
}

function saveToHistory(item) {
    try {
        const historyJson = localStorage.getItem('downloadHistory');
        let history = historyJson ? JSON.parse(historyJson) : [];

        // Remove existing item if present (update)
        history = history.filter(i => i.id !== item.id);

        // Add timestamp if missing
        if (!item.created_at) {
            item.created_at = new Date().toISOString();
        }

        history.unshift(item);

        // Limit history size (e.g. 100 items)
        if (history.length > 100) {
            history = history.slice(0, 100);
        }

        localStorage.setItem('downloadHistory', JSON.stringify(history));

        // Refresh view if active
        if (currentTab === 'history') {
            loadHistory();
            loadStatistics();
        }
    } catch (error) {
        console.error('Error saving history:', error);
    }
}

function clearHistory() {
    if (confirm('Are you sure you want to clear your download history?')) {
        localStorage.removeItem('downloadHistory');
        loadHistory();
        loadStatistics();
    }
}

function renderHistory() {
    if (historyItems.length === 0) {
        historyList.innerHTML = '<p style="text-align: center; color: var(--text-muted); padding: 2rem;">No download history on this device</p>';
        return;
    }

    historyList.innerHTML = historyItems.map(item => `
        <div class="download-item">
            <div class="download-header">
                <div class="download-title">${escapeHtml(item.title)}</div>
                <span class="download-status status-${item.status.toLowerCase()}">${item.status}</span>
            </div>
            <div class="download-info">
                <span>${item.download_type}</span>
                <span>${item.quality}</span>
                ${item.file_size ? `<span>${formatBytes(item.file_size)}</span>` : ''}
                ${item.created_at ? `<span>${formatDate(item.created_at)}</span>` : ''}
            </div>
            ${item.file_path ? `
                <div style="margin-top: 0.5rem; font-size: 0.875rem; color: var(--text-muted);">
                    <strong>Path:</strong> ${escapeHtml(item.file_path)}
                </div>
            ` : ''}
            ${item.status === 'Completed' || item.status === 'Finished' ? `
                <button class="btn btn-primary" style="margin-top: 0.5rem; padding: 0.25rem 0.5rem; font-size: 0.875rem;" onclick="location.href='/api/serve_file/${item.id}'">
                    Download to Device
                </button>
            ` : ''}
            ${item.error ? `
                <div style="margin-top: 0.5rem; font-size: 0.875rem; color: var(--error);">
                    <strong>Error:</strong> ${escapeHtml(item.error)}
                </div>
            ` : ''}
        </div>
    `).join('');
}

// Statistics
function loadStatistics() {
    try {
        const historyJson = localStorage.getItem('downloadHistory');
        const history = historyJson ? JSON.parse(historyJson) : [];

        const total = history.length;
        const successful = history.filter(i => i.status === 'Completed' || i.status === 'Finished').length;
        const failed = history.filter(i => i.status === 'Failed' || i.error).length;
        const successRate = total > 0 ? (successful / total) * 100 : 0;

        let totalBytes = 0;
        history.forEach(i => {
            if (i.file_size) totalBytes += parseInt(i.file_size);
        });

        statsContainer.innerHTML = `
            <div class="stat-item">
                <div class="stat-value">${total}</div>
                <div class="stat-label">Total Downloads</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${successful}</div>
                <div class="stat-label">Completed</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${failed}</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${successRate.toFixed(1)}%</div>
                <div class="stat-label">Success Rate</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${formatBytes(totalBytes)}</div>
                <div class="stat-label">Total Size</div>
            </div>
        `;
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Settings
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const data = await response.json();

        document.getElementById('download-path').value = data.download_path || '';
        document.getElementById('concurrent-downloads').value = data.concurrent_downloads || 3;
        document.getElementById('default-metadata').checked = data.embed_metadata !== false;
        document.getElementById('default-thumbnail').checked = data.embed_thumbnail !== false;
        document.getElementById('default-subtitles').checked = data.embed_subtitles === true;
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

document.getElementById('settings-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const settings = {
        download_path: document.getElementById('download-path').value,
        concurrent_downloads: parseInt(document.getElementById('concurrent-downloads').value),
        embed_metadata: document.getElementById('default-metadata').checked,
        embed_thumbnail: document.getElementById('default-thumbnail').checked,
        embed_subtitles: document.getElementById('default-subtitles').checked
    };

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        const data = await response.json();
        if (data.success) {
            addLog('✓ Settings saved successfully');
        }
    } catch (error) {
        addLog('✗ Error saving settings: ' + error.message);
    }
});

// Load more history button
document.getElementById('load-more-history')?.addEventListener('click', () => {
    loadHistory(true);
});

// History search
document.getElementById('history-search')?.addEventListener('input', debounce(() => {
    historyOffset = 0;
    loadHistory();
}, 500));

// SocketIO event handlers
socket.on('connect', () => {
    addLog('✓ Connected to server');
    loadQueue();
});

socket.on('disconnect', () => {
    addLog('✗ Disconnected from server');
});

socket.on('log_message', (data) => {
    addLog(data.message);
});

socket.on('download_started', (item) => {
    addLog(`⬇ Started: ${item.title}`);
    updateItemInQueue(item);
});

socket.on('download_progress', (item) => {
    updateItemInQueue(item);
});

socket.on('download_completed', (item) => {
    addLog(`✓ Completed: ${item.title}`);
    item.created_at = new Date().toISOString(); // Ensure timestamp
    saveToHistory(item);
    loadQueue();
});

socket.on('download_failed', (item) => {
    addLog(`✗ Failed: ${item.title || item.url}`);
    loadQueue();
});

socket.on('download_cancelled', (item) => {
    addLog(`⊗ Cancelled: ${item.title || item.url}`);
    loadQueue();
});

socket.on('queue_updated', () => {
    if (currentTab === 'queue') {
        loadQueue();
    }
});

// Helper functions
function updateItemInQueue(updatedItem) {
    const index = queueItems.findIndex(item => item.id === updatedItem.id);
    if (index !== -1) {
        queueItems[index] = updatedItem;
        renderQueue();
        updateStats();
    }
}

function updateStats() {
    const total = queueItems.length;
    const downloading = queueItems.filter(item => item.status === 'Downloading').length;

    queueCount.textContent = `${total} in queue`;
    activeCount.textContent = `${downloading} downloading`;
}

function addLog(message) {
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;

    // Keep only last 100 entries
    while (logContainer.children.length > 100) {
        logContainer.removeChild(logContainer.firstChild);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Initialize
addLog('Application initialized');
