
document.addEventListener('DOMContentLoaded', () => {
    // State management
    const state = {
        amount: 1,
        fromCurrency: 'USD',
        toCurrency: 'GMD',
        currencies: window.INITIAL_CURRENCIES || [],
        ratesCache: {},
        currentRate: null
    };

    // DOM Elements
    const amountInput = document.getElementById('amountInput');
    const sourceSymbol = document.getElementById('sourceSymbol');
    const fromTrigger = document.getElementById('fromTrigger');
    const toTrigger = document.getElementById('toTrigger');
    const fromSelectContainer = document.getElementById('fromSelectContainer');
    const toSelectContainer = document.getElementById('toSelectContainer');
    const fromDropdown = document.getElementById('fromDropdown');
    const toDropdown = document.getElementById('toDropdown');
    const fromSearch = document.getElementById('fromSearch');
    const toSearch = document.getElementById('toSearch');
    const fromOptions = document.getElementById('fromOptions');
    const toOptions = document.getElementById('toOptions');
    const swapBtn = document.getElementById('swapCurrenciesBtn');
    const refreshBtn = document.getElementById('refreshRatesBtn');
    const themeWhiteBtn = document.getElementById('themeWhiteBtn');
    const themeBlackBtn = document.getElementById('themeBlackBtn');

    // Display elements
    const fromFlag = document.getElementById('fromFlag');
    const fromCode = document.getElementById('fromCode');
    const fromName = document.getElementById('fromName');
    const toFlag = document.getElementById('toFlag');
    const toCode = document.getElementById('toCode');
    const toName = document.getElementById('toName');

    const baseDisplay = document.getElementById('baseDisplay');
    const targetDisplay = document.getElementById('targetDisplay');
    const exchangeRateBadge = document.getElementById('exchangeRateBadge');
    const inverseRateBadge = document.getElementById('inverseRateBadge');
    const rateTimestamp = document.getElementById('rateTimestamp');
    const lastUpdatedBadge = document.getElementById('lastUpdatedBadge');
    const popularCardsGrid = document.getElementById('popularCardsGrid');
    const historyTableBody = document.getElementById('historyTableBody');
    const trendSvg = document.getElementById('trendSvg');
    const trendPairText = document.getElementById('trendPairText');
    const chartMin = document.getElementById('chartMin');
    const chartAvg = document.getElementById('chartAvg');
    const chartMax = document.getElementById('chartMax');
    const clearRecentBtn = document.getElementById('clearRecentBtn');

    let debounceTimer = null;

    // API helper: check HTTP status and return JSON
    async function fetchJSON(url, options = {}) {
        const response = await fetch(url, options);

        if (!response.ok) {
            throw new Error(`API request failed (${response.status}): ${url}`);
        }

        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            throw new Error(`Expected JSON but received ${contentType || 'unknown content type'}: ${url}`);
        }

        return response.json();
    }

    // Helper: format numbers
    function formatNumber(num, maxDecimals = 4) {
        if (num === null || isNaN(num)) return '--';
        return Number(num).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: maxDecimals
        });
    }

    // Helper: get currency meta
    function getCurrencyMeta(code) {
        return state.currencies.find(c => c.code === code) || {
            code: code,
            name: code,
            symbol: code,
            flag: '🌐'
        };
    }

    // Render currency dropdown options
    function renderOptions(container, list, selectedCode, onSelect) {
        container.innerHTML = '';
        list.forEach(curr => {
            const li = document.createElement('li');
            li.className = `option-item ${curr.code === selectedCode ? 'active' : ''}`;
            li.innerHTML = `
                <span class="option-flag">${curr.flag}</span>
                <span class="option-code">${curr.code}</span>
                <span class="option-name">${curr.name}</span>
            `;
            li.addEventListener('click', (e) => {
                e.stopPropagation();
                onSelect(curr.code);
            });
            container.appendChild(li);
        });
    }

    // Filter options in dropdown
    function filterOptions(query, list, container, selectedCode, onSelect) {
        const q = query.toLowerCase().trim();
        const filtered = list.filter(c =>
            c.code.toLowerCase().includes(q) ||
            c.name.toLowerCase().includes(q)
        );
        renderOptions(container, filtered, selectedCode, onSelect);
    }

    // Setup searchable dropdowns
    function initDropdowns() {
        fromTrigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = fromSelectContainer.classList.contains('open');
            closeAllDropdowns();
            if (!isOpen) {
                fromSelectContainer.classList.add('open');
                fromSearch.value = '';
                filterOptions('', state.currencies, fromOptions, state.fromCurrency, (code) => {
                    setFromCurrency(code);
                    closeAllDropdowns();
                });
                fromSearch.focus();
            }
        });

        toTrigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = toSelectContainer.classList.contains('open');
            closeAllDropdowns();
            if (!isOpen) {
                toSelectContainer.classList.add('open');
                toSearch.value = '';
                filterOptions('', state.currencies, toOptions, state.toCurrency, (code) => {
                    setToCurrency(code);
                    closeAllDropdowns();
                });
                toSearch.focus();
            }
        });

        fromSearch.addEventListener('input', (e) => {
            filterOptions(e.target.value, state.currencies, fromOptions, state.fromCurrency, (code) => {
                setFromCurrency(code);
                closeAllDropdowns();
            });
        });

        toSearch.addEventListener('input', (e) => {
            filterOptions(e.target.value, state.currencies, toOptions, state.toCurrency, (code) => {
                setToCurrency(code);
                closeAllDropdowns();
            });
        });

        document.addEventListener('click', closeAllDropdowns);

        fromDropdown.addEventListener('click', (e) => e.stopPropagation());
        toDropdown.addEventListener('click', (e) => e.stopPropagation());
    }

    function closeAllDropdowns() {
        fromSelectContainer.classList.remove('open');
        toSelectContainer.classList.remove('open');
    }

    // Set From Currency
    function setFromCurrency(code) {
        state.fromCurrency = code;
        const meta = getCurrencyMeta(code);
        fromFlag.textContent = meta.flag;
        fromCode.textContent = meta.code;
        fromName.textContent = meta.name;
        sourceSymbol.textContent = meta.symbol || meta.code;
        executeConversion();
        loadPopularRates();
        loadRateHistory();
    }

    // Set To Currency
    function setToCurrency(code) {
        state.toCurrency = code;
        const meta = getCurrencyMeta(code);
        toFlag.textContent = meta.flag;
        toCode.textContent = meta.code;
        toName.textContent = meta.name;
        executeConversion();
        loadRateHistory();
    }

    // Swap currencies
    swapBtn.addEventListener('click', () => {
        const prevFrom = state.fromCurrency;
        const prevTo = state.toCurrency;
        state.fromCurrency = prevTo;
        state.toCurrency = prevFrom;

        const fromMeta = getCurrencyMeta(state.fromCurrency);
        fromFlag.textContent = fromMeta.flag;
        fromCode.textContent = fromMeta.code;
        fromName.textContent = fromMeta.name;
        sourceSymbol.textContent = fromMeta.symbol || fromMeta.code;

        const toMeta = getCurrencyMeta(state.toCurrency);
        toFlag.textContent = toMeta.flag;
        toCode.textContent = toMeta.code;
        toName.textContent = toMeta.name;

        executeConversion();
        loadPopularRates();
        loadRateHistory();
    });

    // Preset amount chips
    document.querySelectorAll('.preset-chips .chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const val = chip.getAttribute('data-amount');
            amountInput.value = val;
            state.amount = parseFloat(val);
            executeConversion();
        });
    });

    // Amount input change
    amountInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            const val = parseFloat(e.target.value);
            state.amount = isNaN(val) ? 0 : val;
            executeConversion();
        }, 250);
    });

    // Execute Conversion via API
    async function executeConversion() {
        const amt = parseFloat(amountInput.value) || 0;
        state.amount = amt;
        targetDisplay.textContent = 'Calculating...';

        try {
            const json = await fetchJSON(
                `api/convert?from=${encodeURIComponent(state.fromCurrency)}&to=${encodeURIComponent(state.toCurrency)}&amount=${encodeURIComponent(amt)}`
            );

            if (json.status === 'success') {
                const d = json.data;
                const fromMeta = d.from_meta;
                const toMeta = d.to_meta;

                baseDisplay.textContent = `${formatNumber(d.amount, 2)} ${d.from} (${fromMeta.name}) =`;
                targetDisplay.textContent = `${formatNumber(d.result, 2)} ${d.to}`;

                exchangeRateBadge.textContent = `1 ${d.from} = ${formatNumber(d.rate, 4)} ${d.to}`;
                inverseRateBadge.textContent = `1 ${d.to} = ${formatNumber(d.inverse_rate, 4)} ${d.from}`;

                const updateTime = d.provider_update_time || 'Just updated';
                rateTimestamp.textContent = `Source update: ${updateTime}`;
                lastUpdatedBadge.textContent = `Rates synced: ${updateTime}`;

                loadRecentConversions();
            } else {
                targetDisplay.textContent = 'Error calculating';
                console.error('Conversion API error:', json.message);
            }
        } catch (err) {
            targetDisplay.textContent = 'Network error';
            console.error('Conversion request failed:', err);
        }
    }

    // Load Popular Rates Cards
    async function loadPopularRates() {
        try {
            const json = await fetchJSON(
                `api/popular?base=${encodeURIComponent(state.fromCurrency)}`
            );

            if (json.status === 'success') {
                const list = json.data.popular_rates;
                popularCardsGrid.innerHTML = '';

                list.forEach(item => {
                    const card = document.createElement('div');
                    card.className = 'popular-card';
                    card.title = `Click to convert ${state.fromCurrency} to ${item.code}`;
                    card.innerHTML = `
                        <div class="card-curr-info">
                            <span class="flag">${item.flag}</span>
                            <span class="code">${item.code}</span>
                            <span class="name">${item.name}</span>
                        </div>
                        <div class="card-rate-val">${formatNumber(item.rate, 4)} ${item.code}</div>
                        <div class="card-rate-sub">1 ${state.fromCurrency} = ${formatNumber(item.rate, 4)} ${item.symbol || ''}</div>
                    `;
                    card.addEventListener('click', () => {
                        setToCurrency(item.code);
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                    });
                    popularCardsGrid.appendChild(card);
                });
            }
        } catch (e) {
            console.error('Error loading popular rates', e);
        }
    }

    // Load Recent Conversions from SQLite
    async function loadRecentConversions() {
        try {
            const json = await fetchJSON('api/history?limit=8');

            if (json.status === 'success') {
                const rows = json.conversions;
                if (!rows || rows.length === 0) {
                    historyTableBody.innerHTML = '<tr><td colspan="4" class="empty-cell">No recent conversions recorded yet.</td></tr>';
                    return;
                }

                historyTableBody.innerHTML = '';
                rows.forEach(r => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><span class="pair-badge">${r.from_currency}/${r.to_currency}</span></td>
                        <td>${formatNumber(r.amount, 2)}</td>
                        <td>${formatNumber(r.result, 2)}</td>
                        <td>${formatNumber(r.rate, 4)}</td>
                    `;
                    historyTableBody.appendChild(tr);
                });
            }
        } catch (e) {
            console.error('Error loading history', e);
        }
    }

    // Load Historical Trend Data & Draw SVG Sparkline
    async function loadRateHistory() {
        trendPairText.textContent = `${state.fromCurrency} / ${state.toCurrency} Snapshot Trend`;

        try {
            const json = await fetchJSON(
                `api/rate-history?from=${encodeURIComponent(state.fromCurrency)}&to=${encodeURIComponent(state.toCurrency)}`
            );

            if (json.status === 'success' && json.history && json.history.length > 1) {
                renderSparkline(json.history);
            } else {
                renderBaselineSparkline();
            }
        } catch (e) {
            console.error('Error loading rate trend', e);
        }
    }

    function renderSparkline(points) {
        const rates = points.map(p => p.rate);
        const min = Math.min(...rates);
        const max = Math.max(...rates);
        const latest = rates[rates.length - 1];

        chartMin.textContent = `Min: ${formatNumber(min, 4)}`;
        chartAvg.textContent = `Latest: ${formatNumber(latest, 4)}`;
        chartMax.textContent = `Max: ${formatNumber(max, 4)}`;

        const width = 500;
        const height = 140;
        const padding = 15;
        const range = max - min || (min * 0.05) || 1;

        const coords = rates.map((r, i) => {
            const x = padding + (i / (rates.length - 1)) * (width - 2 * padding);
            const y = height - padding - ((r - min) / range) * (height - 2 * padding);
            return `${x},${y}`;
        });

        const polylinePoints = coords.join(' ');
        const areaPoints = `${coords[0].split(',')[0]},${height} ${polylinePoints} ${coords[coords.length - 1].split(',')[0]},${height}`;

        trendSvg.innerHTML = `
            <defs>
                <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#00B4D8" stop-opacity="0.35"/>
                    <stop offset="100%" stop-color="#00B4D8" stop-opacity="0.0"/>
                </linearGradient>
            </defs>
            <polygon class="chart-area" points="${areaPoints}" />
            <polyline class="chart-polyline" points="${polylinePoints}" />
        `;
    }

    function renderBaselineSparkline() {
        chartMin.textContent = 'Live reference rate active';
        chartAvg.textContent = 'Collecting snapshots...';
        chartMax.textContent = 'SQLite continuous sync';

        trendSvg.innerHTML = `
            <defs>
                <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#00B4D8" stop-opacity="0.25"/>
                    <stop offset="100%" stop-color="#00B4D8" stop-opacity="0.0"/>
                </linearGradient>
            </defs>
            <path d="M 15 70 Q 130 50, 250 70 T 485 65" fill="none" stroke="#00B4D8" stroke-width="2.5" stroke-dasharray="4,4" />
        `;
    }

    // Refresh Rates Action Button
    refreshBtn.addEventListener('click', async () => {
        refreshBtn.classList.add('refreshing');

        try {
            await fetchJSON('api/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ base: state.fromCurrency })
            });

            await executeConversion();
            await loadPopularRates();
            await loadRateHistory();
        } catch (e) {
            console.error('Refresh error', e);
        } finally {
            setTimeout(() => {
                refreshBtn.classList.remove('refreshing');
            }, 600);
        }
    });

    clearRecentBtn.addEventListener('click', () => {
        loadRecentConversions();
    });

    // Theme Management (White & Black)
    function applyTheme(theme) {
        if (theme === 'white') {
            document.documentElement.setAttribute('data-theme', 'white');
            if (themeWhiteBtn) themeWhiteBtn.classList.add('active');
            if (themeBlackBtn) themeBlackBtn.classList.remove('active');
        } else {
            document.documentElement.setAttribute('data-theme', 'black');
            if (themeBlackBtn) themeBlackBtn.classList.add('active');
            if (themeWhiteBtn) themeWhiteBtn.classList.remove('active');
        }

        localStorage.setItem('dalasifx_theme', theme);
    }

    if (themeWhiteBtn && themeBlackBtn) {
        themeWhiteBtn.addEventListener('click', () => applyTheme('white'));
        themeBlackBtn.addEventListener('click', () => applyTheme('black'));
    }

    // Load saved theme or default to black
    const savedTheme = localStorage.getItem('dalasifx_theme') || 'black';
    applyTheme(savedTheme);

    // Initialize UI
    initDropdowns();
    executeConversion();
    loadPopularRates();
    loadRecentConversions();
    loadRateHistory();
});
