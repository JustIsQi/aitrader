// Historical Signals Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const signalsContainer = document.getElementById('signals-container');
    const loadingElement = document.getElementById('loading');
    const emptyStateElement = document.getElementById('empty-state');
    const dateRangeSelect = document.getElementById('date-range-select');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const refreshBtn = document.getElementById('refresh-btn');

    // Set default end date to today
    const today = new Date();
    endDateInput.value = today.toISOString().split('T')[0];

    // Load signals on page load
    loadSignals();

    // Event listener for date range change
    dateRangeSelect.addEventListener('change', function() {
        // Clear manual date inputs when preset is selected
        startDateInput.value = '';
        endDateInput.value = today.toISOString().split('T')[0];
        loadSignals();
    });

    // Event listener for load button
    refreshBtn.addEventListener('click', loadSignals);

    async function loadSignals() {
        let startDate = null;
        let endDate = null;
        const rangeValue = dateRangeSelect.value;

        // Calculate date range
        if (rangeValue !== 'all') {
            const days = parseInt(rangeValue);
            const start = new Date();
            start.setDate(start.getDate() - days);
            startDate = start.toISOString().split('T')[0];
            endDate = today.toISOString().split('T')[0];
        }

        // Override with manual dates if provided
        if (startDateInput.value) {
            startDate = startDateInput.value;
        }
        if (endDateInput.value) {
            endDate = endDateInput.value;
        }

        // Build URL parameters
        let url = '/api/signals/history/grouped';
        const params = [];
        if (startDate) params.push(`start_date=${startDate}`);
        if (endDate) params.push(`end_date=${endDate}`);
        if (params.length > 0) url += '?' + params.join('&');

        // Show loading, hide content
        loadingElement.style.display = 'block';
        signalsContainer.innerHTML = '';
        emptyStateElement.style.display = 'none';

        try {
            const response = await fetch(url);
            const data = await response.json();

            // Hide loading
            loadingElement.style.display = 'none';

            if (!data.dates || data.dates.length === 0) {
                emptyStateElement.style.display = 'block';
                return;
            }

            // Render signals grouped by date
            renderSignals(data.dates);
        } catch (error) {
            loadingElement.style.display = 'none';
            signalsContainer.innerHTML = `
                <div class="error-message">
                    <p>Error loading signals: ${error.message}</p>
                </div>
            `;
        }
    }

    function renderSignals(dates) {
        dates.forEach(dateGroup => {
            const dateSection = createDateSection(dateGroup);
            signalsContainer.appendChild(dateSection);
        });
    }

    function createDateSection(dateGroup) {
        const section = document.createElement('div');
        section.className = 'date-group';

        // Create header
        const header = document.createElement('div');
        header.className = 'date-header';

        const headerContent = document.createElement('div');
        headerContent.className = 'date-header-content';

        const dateTitle = document.createElement('div');
        dateTitle.className = 'date-title';
        dateTitle.textContent = formatDate(dateGroup.date);

        const dateCount = document.createElement('div');
        dateCount.className = 'date-count';
        dateCount.textContent = `${dateGroup.signals.length} signals`;

        headerContent.appendChild(dateTitle);
        headerContent.appendChild(dateCount);

        const expandIcon = document.createElement('div');
        expandIcon.className = 'expand-icon';
        expandIcon.innerHTML = '&#9662;'; // Down triangle

        header.appendChild(headerContent);
        header.appendChild(expandIcon);

        // Create signals list container
        const signalsList = document.createElement('div');
        signalsList.className = 'signals-list';

        // Add signals to the list
        dateGroup.signals.forEach(signal => {
            const signalCard = createSignalCard(signal);
            signalsList.appendChild(signalCard);
        });

        // Toggle expand/collapse on header click
        header.addEventListener('click', () => {
            section.classList.toggle('collapsed');
        });

        section.appendChild(header);
        section.appendChild(signalsList);

        return section;
    }

    function createSignalCard(signal) {
        const card = document.createElement('div');
        card.className = `signal-card ${signal.signal_type}`;

        // Header
        const header = document.createElement('div');
        header.className = 'signal-header';

        const symbol = document.createElement('div');
        symbol.className = 'symbol';
        symbol.textContent = signal.symbol;

        const signalType = document.createElement('div');
        signalType.className = 'signal-type';
        signalType.textContent = signal.signal_type.toUpperCase();

        header.appendChild(symbol);
        header.appendChild(signalType);

        // Details
        const details = document.createElement('div');
        details.className = 'signal-details';

        // Price
        if (signal.price !== null && signal.price !== undefined) {
            const priceItem = createDetailItem('Price', `¥${parseFloat(signal.price).toFixed(3)}`);
            details.appendChild(priceItem);
        }

        // Score
        if (signal.score !== null && signal.score !== undefined) {
            const scoreItem = createDetailItem('Score', signal.score.toFixed(4));
            details.appendChild(scoreItem);
        }

        // Quantity
        if (signal.quantity !== null && signal.quantity !== undefined) {
            const qtyItem = createDetailItem('Quantity', parseInt(signal.quantity));
            details.appendChild(qtyItem);
        }

        // Meta information
        const meta = document.createElement('div');
        meta.className = 'signal-meta';

        // Strategies
        const strategiesDiv = document.createElement('div');
        strategiesDiv.className = 'signal-strategies';

        if (signal.strategies) {
            const strategyList = signal.strategies.split(',').map(s => s.trim()).filter(s => s);
            strategyList.forEach(strategy => {
                const tag = document.createElement('span');
                tag.className = 'strategy-tag';
                tag.textContent = strategy;
                strategiesDiv.appendChild(tag);
            });
        }

        meta.appendChild(strategiesDiv);

        // Created at timestamp
        const timestamp = document.createElement('div');
        timestamp.textContent = signal.created_at || '';
        meta.appendChild(timestamp);

        card.appendChild(header);
        card.appendChild(details);
        card.appendChild(meta);

        return card;
    }

    function createDetailItem(label, value) {
        const item = document.createElement('div');
        item.className = 'signal-detail-item';

        const labelSpan = document.createElement('span');
        labelSpan.className = 'signal-label';
        labelSpan.textContent = `${label}: `;

        const valueSpan = document.createElement('span');
        valueSpan.className = 'signal-value';
        valueSpan.textContent = value;

        item.appendChild(labelSpan);
        item.appendChild(valueSpan);

        return item;
    }

    function formatDate(dateString) {
        const date = new Date(dateString);
        const options = {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            weekday: 'long'
        };
        return date.toLocaleDateString('zh-CN', options);
    }
});
