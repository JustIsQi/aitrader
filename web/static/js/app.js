// Main application JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard date groups expand/collapse
    initDashboardDateGroups();

    // Load strategies dropdown
    loadStrategies();

    // Initialize trading form
    const tradingForm = document.getElementById('tradingForm');
    if (tradingForm) {
        // Set default date to today
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('trade_date').value = today;

        // Handle form submission
        tradingForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(tradingForm);
            const data = {
                symbol: formData.get('symbol'),
                buy_sell: formData.get('buy_sell'),
                quantity: parseFloat(formData.get('quantity')),
                price: parseFloat(formData.get('price')),
                trade_date: formData.get('trade_date'),
                strategy_name: formData.get('strategy_name') || null
            };

            try {
                const response = await fetch('/api/trading/record', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    alert('交易记录添加成功！');
                    tradingForm.reset();
                    document.getElementById('trade_date').value = today;

                    // Refresh positions and P&L
                    location.reload();
                } else {
                    const error = await response.json();
                    alert(`错误: ${error.detail}`);
                }
            } catch (error) {
                alert(`错误: ${error.message}`);
            }
        });
    }

    // Load profit/loss data
    loadProfitLoss();
});

// Initialize dashboard date groups expand/collapse
function initDashboardDateGroups() {
    const dateHeaders = document.querySelectorAll('#dashboard-signals-container .date-header');

    if (dateHeaders.length === 0) {
        console.warn('No dashboard date headers found');
        return;
    }

    dateHeaders.forEach((header) => {
        header.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            const dateGroup = this.closest('.date-group');
            if (dateGroup) {
                dateGroup.classList.toggle('collapsed');
            }
        });
    });
}

async function loadStrategies() {
    const strategySelect = document.getElementById('strategy_name');
    if (!strategySelect) return;

    try {
        const response = await fetch('/api/trading/strategies');
        const strategies = await response.json();

        // Clear existing options (except the first one)
        strategySelect.innerHTML = '<option value="">-- Select Strategy --</option>';

        // Add strategy options
        strategies.forEach(strategy => {
            const option = document.createElement('option');
            option.value = strategy;
            option.textContent = strategy;
            strategySelect.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load strategies:', error);
    }
}

async function loadProfitLoss() {
    const plContainer = document.getElementById('pl-container');
    if (!plContainer) return;

    try {
        const response = await fetch('/api/analytics/profit-loss');
        const data = await response.json();

        const formatCurrency = (value) => {
            return new Intl.NumberFormat('zh-CN', {
                style: 'currency',
                currency: 'CNY'
            }).format(value);
        };

        const getValueClass = (value) => {
            return value >= 0 ? 'positive' : 'negative';
        };

        plContainer.innerHTML = `
            <div class="pl-item">
                <span class="pl-label">Realized P&L:</span>
                <span class="pl-value ${getValueClass(data.realized_pl)}">
                    ${formatCurrency(data.realized_pl)}
                </span>
            </div>
            <div class="pl-item">
                <span class="pl-label">Unrealized P&L:</span>
                <span class="pl-value ${getValueClass(data.total_unrealized_pl)}">
                    ${formatCurrency(data.total_unrealized_pl)}
                </span>
            </div>
            <div class="pl-item">
                <span class="pl-label">Total P&L:</span>
                <span class="pl-value ${getValueClass(data.total_pl)}">
                    ${formatCurrency(data.total_pl)}
                </span>
            </div>
            <div class="pl-item">
                <span class="pl-label">Market Value:</span>
                <span class="pl-value">${formatCurrency(data.total_market_value)}</span>
            </div>
            <div class="pl-item">
                <span class="pl-label">Total Cost:</span>
                <span class="pl-value">${formatCurrency(data.total_cost)}</span>
            </div>
        `;
    } catch (error) {
        plContainer.innerHTML = `<p>Error loading P&L data: ${error.message}</p>`;
    }
}
