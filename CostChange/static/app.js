document.addEventListener('DOMContentLoaded', function() {
    // --- 1. HTML 元素 ---
    const findNearestBtn = document.getElementById('findNearestBtn');
    const geminiAnalysisBtn = document.getElementById('geminiAnalysisBtn');
    const getChartBtn = document.getElementById('getChartBtn');
    const currencySelector = document.getElementById('currencySelector');
    const statusBox = document.getElementById('statusBox');
    const reportContainer = document.getElementById('reportContainer');
    const rateChartCanvas = document.getElementById('rateChart');
    const placeholderText = document.getElementById('placeholderText');
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const rateConverter = document.getElementById('rateConverter');
    const twdAmountInput = document.getElementById('twdAmount');
    const foreignCurrencyLabel = document.getElementById('foreignCurrencyLabel');
    const convertedAmountP = document.getElementById('convertedAmount');
    const converterRateInfo = document.getElementById('converterRateInfo');
    const btn3Months = document.getElementById('btn3Months');
    const btn6Months = document.getElementById('btn6Months');

    // --- 2. 全域變數 ---
    let poller = null;
    let myChart = null;
    let currentRateData = [];
    let sortState = { column: null, direction: 'asc' };
    let bestCashSellRate = null;
    let cachedTwdAmount = '';

    // --- 3. 初始化 ---
    function initialize() {
        const today = new Date();
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(today.getDate() - 30);
        endDateInput.value = today.toISOString().split('T')[0];
        startDateInput.value = thirtyDaysAgo.toISOString().split('T')[0];
        const lastYear = today.getFullYear() - 1;
        const earliestDate = new Date(lastYear, 0, 1);
        startDateInput.min = earliestDate.toISOString().split('T')[0];
    }

    // --- 5. 事件監聽 ---
    findNearestBtn.addEventListener('click', () => {
        startTask('/find_best_and_nearest', { currency: currencySelector.value });
    });
    getChartBtn.addEventListener('click', () => {
        startTask('/get_historical_chart_data', {
            currency: currencySelector.value,
            start_date: startDateInput.value,
            end_date: endDateInput.value
        });
    });
    geminiAnalysisBtn.addEventListener('click', () => {
        const selectedOption = currencySelector.options[currencySelector.selectedIndex];
        startTask('/get_gemini_analysis', {
            currency_code: selectedOption.value,
            currency_name: selectedOption.text.split(' - ')[1]
        });
    });
    currencySelector.addEventListener('change', () => {
        startTask('/get_rate_data', { currency: currencySelector.value });
    });
    twdAmountInput.addEventListener('input', function() {
        cachedTwdAmount = this.value;
        const twdAmount = parseFloat(this.value);
        if (isNaN(twdAmount) || !bestCashSellRate) {
            convertedAmountP.textContent = "0.00";
            return;
        }
        const converted = twdAmount / bestCashSellRate;
        const decimalPlaces = bestCashSellRate < 1 ? 2 : 4;
        convertedAmountP.textContent = converted.toFixed(decimalPlaces);
    });

    btn3Months.addEventListener('click', () => {
        setDateRangeAndFetch(3);
    });

    btn6Months.addEventListener('click', () => {
        setDateRangeAndFetch(6);
    });

    // --- 6. 核心輔助函式 ---
    function setDateRangeAndFetch(months) {
        const today = new Date();
        const startDate = new Date();
        startDate.setMonth(today.getMonth() - months);
        const formatDate = (date) => date.toISOString().split('T')[0];
        endDateInput.value = formatDate(today);
        startDateInput.value = formatDate(startDate);
        getChartBtn.click();
    }
    
    function setControlsDisabled(disabled) {
        findNearestBtn.disabled = disabled;
        geminiAnalysisBtn.disabled = disabled;
        getChartBtn.disabled = disabled;
        btn3Months.disabled = disabled;
        btn6Months.disabled = disabled;
        currencySelector.disabled = disabled;
    }

    function startTask(endpoint, body) {
        setControlsDisabled(true);
        const currencyName = currencySelector.options[currencySelector.selectedIndex].text;
        clearReportArea();
        placeholderText.style.display = 'block';
        placeholderText.textContent = `任務準備中，目標：${currencyName}...`;
        statusBox.textContent = "任務準備中...";
        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        }).then(response => {
            if (!response.ok) { return response.json().then(err => { throw new Error(err.message || "請求失敗"); }); }
            return response.json();
        }).then(data => {
            if (data.status && data.status.includes('started')) {
                pollStatus();
            } else {
                throw new Error(data.message || '後端返回未知錯誤');
            }
        }).catch(error => {
            statusBox.textContent = `[錯誤] 啟動失敗: ${error.message}`;
            setControlsDisabled(false);
        });
    }

    function pollStatus() {
        if (poller) clearInterval(poller);
        pollStatus_once();
        poller = setInterval(pollStatus_once, 1500);
    }

    function pollStatus_once() {
        fetch('/status').then(res => res.json()).then(data => {
            updateUI(data);
        }).catch(err => {
            statusBox.textContent = `[錯誤] 無法獲取狀態: ${err.message}`;
            clearInterval(poller);
            poller = null;
            setControlsDisabled(false);
        });
    }

    function updateUI(data) {
        const currencyName = currencySelector.options[currencySelector.selectedIndex].text;
        statusBox.textContent = `[${currencyName}][${data.stage}] ${data.message}`;
        const isRunning = data.stage === 'scraping' || data.stage === 'finding_location';
        setControlsDisabled(isRunning);
        if (!isRunning && poller) {
            clearInterval(poller);
            poller = null;
        }
        if (data.stage === 'complete') {
            generateReport(data.results);
        } else if (data.stage === 'error') {
            clearReportArea();
            placeholderText.innerHTML = `<div class='error-message'><h2>任務失敗</h2><p>${data.message}</p></div>`;
        }
    }

    function clearReportArea() {
        if (myChart) {
            myChart.destroy();
            myChart = null;
        }
        reportContainer.innerHTML = '';
        reportContainer.appendChild(rateChartCanvas);
        reportContainer.appendChild(placeholderText);
        rateChartCanvas.style.display = 'none';
        placeholderText.style.display = 'block';
        placeholderText.textContent = '請點擊按鈕開始查詢';
        rateConverter.style.display = 'none';
        convertedAmountP.textContent = '0.00';
        bestCashSellRate = null;
    }

    // --- 7. 報告與圖表生成 ---
    function generateReport(results) {
        clearReportArea();
        placeholderText.style.display = 'none';
        if (Array.isArray(results) && results.length > 0 && results[0].hasOwnProperty('value')) {
            generateChart(results);
        } else if (Array.isArray(results) && results.length > 0 && results[0].best_rate_info) {
            let html = "<h2>智慧查詢結果</h2>";
            results.forEach(result => {
                const { rank, best_rate_info: rate, nearest_branch_info: branch } = result;
                let rankIcon = ['🥇', '🥈', '🥉'][rank - 1] || `第 ${rank}`;
                html += `<div class="result-item"><h3>${rankIcon} 第 ${rank} 名</h3>`;
                html += `<div class="sub-result"><h4>換匯銀行 (現金賣出)</h4><p>銀行：<b>${rate.bank}</b></p><p>匯率：<b>${rate.cash_sell}</b> (數字越低越好)</p></div>`;
                if (branch) {
                    html += `<div class="sub-result"><h4>距離您最近的分行</h4><p>分行名稱：<b>${branch.name}</b></p><p>地址：${branch.address}</p><p>Google 評分：${branch.rating}</p><p>目前是否營業：${branch.is_open}</p><p><a href="${branch.map_url}" target="_blank">在地圖上開啟</a></p></div>`;
                }
                html += `</div>`;
            });
            reportContainer.innerHTML = html;
        } else if (typeof results === 'string') {
            reportContainer.innerHTML = `<h2>Gemini 分析</h2><pre class="ai-review">${results}</pre>`;
        } else if (Array.isArray(results) && results.length > 0) {
            currentRateData = results;
            sortState = { column: null, direction: 'asc' };
            redrawTable();
            const validRates = results.filter(r => r.cash_sell && r.cash_sell !== '--').map(r => parseFloat(r.cash_sell));
            if (validRates.length > 0) {
                bestCashSellRate = Math.min(...validRates);
                const bestBank = results.find(r => parseFloat(r.cash_sell) === bestCashSellRate);
                foreignCurrencyLabel.textContent = currencySelector.value;
                converterRateInfo.textContent = `依據 ${bestBank.bank} 最優現金賣出價 ${bestCashSellRate} 計算`;
                rateConverter.style.display = 'block';
                if (cachedTwdAmount) {
                    twdAmountInput.value = cachedTwdAmount;
                    twdAmountInput.dispatchEvent(new Event('input'));
                }
            }
        } else {
            placeholderText.style.display = 'block';
            placeholderText.textContent = '查無資料或指定區間內沒有交易日。';
        }
    }
    
    function processChartData(rawData) {
        if (!rawData || rawData.length === 0) return null;
        const labels = rawData.map(d => d.date);
        const values = rawData.map(d => d.value);
        return { labels, values };
    }

    function generateChart(rawData) {
        if (myChart) {
            myChart.destroy();
        }
        const processedData = processChartData(rawData);
        if (!processedData) return;
        
        const currencyName = currencySelector.options[currencySelector.selectedIndex].text;
        rateChartCanvas.style.display = 'block';
        const ctx = rateChartCanvas.getContext('2d');
        const lineColor = '#0000FF';

        myChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: processedData.labels.map(l => l.substring(5)),
                datasets: [{
                    label: '現金賣出匯率',
                    data: processedData.values,
                    borderColor: lineColor,
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 1,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: false, ticks: { color: '#e0e0e0' }, grid: { color: 'rgba(255, 255, 255, 0.1)' } },
                    x: { ticks: { color: '#e0e0e0', maxRotation: 0, autoSkip: true }, grid: { color: 'rgba(255, 255, 255, 0.1)' } }
                },
                plugins: {
                    legend: { labels: { color: '#e0e0e0' } },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            title: function(tooltipItems) {
                                const index = tooltipItems[0].dataIndex;
                                return processedData.labels[index];
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
            }
        });
    }

    // --- 8. 表格處理 ---
    function redrawTable() {
        reportContainer.innerHTML = createTable(currentRateData);
        addSortEventListeners();
    }

    function createTable(items) {
        let tableHTML = `<table class="report-table"><thead><tr>
            <th>銀行</th><th>幣別</th><th>時間/日期</th>
            <th class="sortable" data-sort-key="cash_buy">現金買入</th>
            <th class="sortable" data-sort-key="cash_sell">現金賣出</th>
            <th class="sortable" data-sort-key="spot_buy">即期買入</th>
            <th class="sortable" data-sort-key="spot_sell">即期賣出</th>
        </tr></thead><tbody>`;
        items.forEach(item => {
            tableHTML += `<tr><td>${item.bank}</td><td>${item.currency}</td><td>${item.date}</td><td>${item.cash_buy}</td><td>${item.cash_sell}</td><td>${item.spot_buy}</td><td>${item.spot_sell}</td></tr>`;
        });
        tableHTML += '</tbody></table>';
        return tableHTML;
    }

    function addSortEventListeners() {
        const headers = document.querySelectorAll('.report-table th.sortable');
        headers.forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
            if (sortState.column === header.dataset.sortKey) {
                header.classList.add(sortState.direction === 'asc' ? 'sort-desc' : 'sort-asc');
            }
            header.addEventListener('click', () => {
                const sortKey = header.dataset.sortKey;
                if (sortState.column === sortKey) {
                    sortState.direction = sortState.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    sortState.column = sortKey;
                    sortState.direction = 'asc';
                }
                sortData(sortKey, sortState.direction);
                redrawTable();
            });
        });
    }

    function sortData(key, direction) {
        currentRateData.sort((a, b) => {
            let valA = parseFloat(a[key]);
            let valB = parseFloat(b[key]);
            if (isNaN(valA)) valA = direction === 'asc' ? Infinity : -Infinity;
            if (isNaN(valB)) valB = direction === 'asc' ? Infinity : -Infinity;
            return direction === 'asc' ? valA - valB : valB - valA;
        });
    }
    
    // --- 啟動 ---
    initialize();
});