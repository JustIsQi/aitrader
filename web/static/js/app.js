// Main application JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard date groups expand/collapse
    initDashboardDateGroups();

    // Load strategies dropdown
    loadStrategies();

    // Initialize recalculate positions button
    initRecalculateButton();

    // Initialize module toggles (ETF/A-share)
    initModuleToggles();

    // Initialize backtest section toggles
    initBacktestToggles();

    // Initialize backtest buttons
    initBacktestButtons();

    // Initialize modal handlers
    initModalHandlers();

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

/**
 * Symbol 自动补全功能
 * 使用防抖优化性能
 */
class SymbolAutocomplete {
    constructor(inputId, datalistId, apiUrl) {
        this.input = document.getElementById(inputId);
        this.datalist = document.getElementById(datalistId);
        this.apiUrl = apiUrl;
        this.debounceTimer = null;
        this.debounceDelay = 300; // 防抖延迟（毫秒）
        this.minQueryLength = 2; // 最小查询长度

        if (this.input && this.datalist) {
            this.init();
        }
    }

    init() {
        // 监听输入事件
        this.input.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            this.handleInput(query);
        });

        // 初始加载（显示所有代码，限制数量）
        this.loadCodes('', 50);
    }

    handleInput(query) {
        // 清除之前的定时器
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // 如果查询长度不足，清空列表
        if (query.length < this.minQueryLength) {
            this.datalist.innerHTML = '';
            return;
        }

        // 设置防抖定时器
        this.debounceTimer = setTimeout(() => {
            this.loadCodes(query);
        }, this.debounceDelay);
    }

    async loadCodes(search = '', limit = 100) {
        try {
            // 构建 URL
            const url = new URL(this.apiUrl, window.location.origin);
            if (search) {
                url.searchParams.append('search', search);
            }
            url.searchParams.append('limit', limit);

            // 发送请求
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const codes = await response.json();

            // 更新 datalist
            this.updateDatalist(codes);

        } catch (error) {
            console.error('加载代码列表失败:', error);
            // 失败时不显示错误，静默处理
        }
    }

    updateDatalist(codes) {
        // 清空现有选项
        this.datalist.innerHTML = '';

        // 添加新选项
        codes.forEach(code => {
            const option = document.createElement('option');
            option.value = code;
            this.datalist.appendChild(option);
        });
    }
}

// 在 DOMContentLoaded 事件中初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化 Symbol 自动补全
    new SymbolAutocomplete(
        'symbol',
        'symbolList',
        '/api/trading/codes'
    );
});

// Initialize recalculate positions button
function initRecalculateButton() {
    const recalculateBtn = document.getElementById('recalculateBtn');
    if (recalculateBtn) {
        recalculateBtn.addEventListener('click', async () => {
            if (!confirm('确定要重新计算所有持仓吗？这将根据交易记录重建持仓数据。')) {
                return;
            }

            try {
                recalculateBtn.disabled = true;
                recalculateBtn.textContent = '计算中...';

                const response = await fetch('/api/trading/recalculate-positions', {
                    method: 'POST'
                });

                if (response.ok) {
                    const result = await response.json();
                    alert(result.message);
                    // 刷新页面显示更新后的数据
                    location.reload();
                } else {
                    const error = await response.json();
                    alert(`错误: ${error.detail}`);
                }
            } catch (error) {
                alert(`错误: ${error.message}`);
            } finally {
                recalculateBtn.disabled = false;
                recalculateBtn.textContent = '重新计算持仓';
            }
        });
    }
}

// ========== Module-level expand/collapse ==========

function initModuleToggles() {
    const etfHeader = document.getElementById('etf-module-header');
    const ashareWeeklyHeader = document.getElementById('ashare-weekly-module-header');
    const ashareMonthlyHeader = document.getElementById('ashare-monthly-module-header');

    if (etfHeader) {
        etfHeader.addEventListener('click', function() {
            const container = document.getElementById('etf-signals-container');
            container.classList.toggle('collapsed');
            _toggleIcon(this);
        });
    }

    if (ashareWeeklyHeader) {
        ashareWeeklyHeader.addEventListener('click', function() {
            const container = document.getElementById('ashare-weekly-signals-container');
            container.classList.toggle('collapsed');
            _toggleIcon(this);
        });
    }

    if (ashareMonthlyHeader) {
        ashareMonthlyHeader.addEventListener('click', function() {
            const container = document.getElementById('ashare-monthly-signals-container');
            container.classList.toggle('collapsed');
            _toggleIcon(this);
        });
    }
}

function _toggleIcon(header) {
    const icon = header.querySelector('.expand-icon');
    if (header.nextElementSibling.classList.contains('collapsed')) {
        icon.innerHTML = '&#9652;';  // Up arrow
    } else {
        icon.innerHTML = '&#9662;';  // Down arrow
    }
}

// ========== Backtest section expand/collapse ==========

function initBacktestToggles() {
    const backtestHeaders = document.querySelectorAll('.backtest-header');

    backtestHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const content = this.nextElementSibling;
            content.classList.toggle('collapsed');

            const icon = this.querySelector('.expand-icon-small');
            if (content.classList.contains('collapsed')) {
                icon.innerHTML = '&#9652;';
            } else {
                icon.innerHTML = '&#9662;';
            }
        });
    });
}

// ========== Backtest modal ==========

function initBacktestButtons() {
    const buttons = document.querySelectorAll('.btn-view-backtest');

    buttons.forEach(button => {
        button.addEventListener('click', function() {
            const backtestId = this.getAttribute('data-backtest-id');
            loadBacktestDetail(backtestId);
        });
    });
}

async function loadBacktestDetail(backtestId) {
    const modal = document.getElementById('backtest-modal');
    const modalBody = document.getElementById('backtest-modal-body');

    try {
        // Show loading
        modalBody.innerHTML = '<p style="text-align: center; padding: 20px;">Loading backtest data...</p>';
        modal.style.display = 'block';

        // Fetch backtest data
        const response = await fetch(`/api/signals/ashare/backtest/${backtestId}`);
        if (!response.ok) throw new Error('Failed to load backtest');

        const backtest = await response.json();

        // Render backtest details
        modalBody.innerHTML = renderBacktestDetail(backtest);

    } catch (error) {
        modalBody.innerHTML = `<p class="error" style="color: red; text-align: center;">Error loading backtest: ${error.message}</p>`;
    }
}

function renderBacktestDetail(backtest) {
    // Format trades
    const tradesHtml = backtest.trade_list && backtest.trade_list.length > 0
        ? backtest.trade_list.slice(0, 20).map(trade => `
            <tr>
                <td>${trade.date || ''}</td>
                <td>${trade.symbol || ''}</td>
                <td>${trade.type || ''}</td>
                <td>${trade.price ? trade.price.toFixed(2) : '-'}</td>
                <td>${trade.quantity || '-'}</td>
            </tr>
        `).join('')
        : '<tr><td colspan="5">No trades data available</td></tr>';

    return `
        <div class="backtest-detail">
            <h4>${backtest.strategy_name || 'Unknown Strategy'}</h4>
            ${backtest.strategy_version ? `<p class="backtest-version">Version: ${backtest.strategy_version}</p>` : ''}

            <div class="backtest-period">
                Period: ${backtest.start_date} to ${backtest.end_date}
            </div>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Total Return</div>
                    <div class="metric-value ${backtest.total_return >= 0 ? 'positive' : 'negative'}">
                        ${backtest.total_return ? backtest.total_return.toFixed(2) : '0.00'}%
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Annual Return</div>
                    <div class="metric-value">
                        ${backtest.annual_return ? backtest.annual_return.toFixed(2) : '0.00'}%
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Sharpe Ratio</div>
                    <div class="metric-value">
                        ${backtest.sharpe_ratio ? backtest.sharpe_ratio.toFixed(2) : '0.00'}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Max Drawdown</div>
                    <div class="metric-value negative">
                        ${backtest.max_drawdown ? backtest.max_drawdown.toFixed(2) : '0.00'}%
                    </div>
                </div>
            </div>

            ${backtest.win_rate !== null ? `
            <div class="metric-card" style="text-align: center; margin-bottom: 15px;">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value">${backtest.win_rate.toFixed(1)}%</div>
            </div>
            ` : ''}

            <div class="backtest-trades">
                <h5>Recent Trades (Top 20)</h5>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f5f5f5;">
                            <th style="padding: 8px; border: 1px solid #ddd;">Date</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Symbol</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Type</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Price</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Quantity</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tradesHtml}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

function initModalHandlers() {
    const modal = document.getElementById('backtest-modal');
    if (!modal) return;

    const closeBtn = modal.querySelector('.close-modal');

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}
