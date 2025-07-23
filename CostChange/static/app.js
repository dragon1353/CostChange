document.addEventListener('DOMContentLoaded', function() {
    // --- 1. 統一宣告所有會用到的 HTML 元素 ---
    const fetchDataBtn = document.getElementById('fetchDataBtn');
    const findNearestBtn = document.getElementById('findNearestBtn');
    const geminiAnalysisBtn = document.getElementById('geminiAnalysisBtn');
    const bankSelector = document.getElementById('bankSelector');
    const dateSelector = document.getElementById('dateSelector');
    const statusBox = document.getElementById('statusBox');
    const reportContainer = document.getElementById('reportContainer');

    // --- 2. 全域變數 ---
    let poller = null;
    let currentRateData = []; // 用於儲存當前的匯率資料以供排序
    let sortState = { column: null, direction: 'asc' }; // 用於儲存排序狀態

    // --- 3. 事件監聽 ---
    function handleBankSelectionChange() {
        const isFindRate = (bankSelector.value === '比率網綜合比較');
        dateSelector.disabled = isFindRate;
        findNearestBtn.style.display = isFindRate ? 'inline-block' : 'none';
        geminiAnalysisBtn.style.display = isFindRate ? 'inline-block' : 'none';
    }
    bankSelector.addEventListener('change', handleBankSelectionChange);

    fetchDataBtn.addEventListener('click', function() {
        if (!dateSelector.disabled && !dateSelector.value) {
            alert("請選擇一個日期！"); return;
        }
        startTask('/get_rate_data', { bank: bankSelector.value, date: dateSelector.value });
    });

    findNearestBtn.addEventListener('click', function() {
        startTask('/find_best_and_nearest', {});
    });

    geminiAnalysisBtn.addEventListener('click', function() {
        startTask('/get_gemini_analysis', {});
    });

    // --- 4. 核心輔助函式 ---

    function setControlsDisabled(disabled) {
        fetchDataBtn.disabled = disabled;
        findNearestBtn.disabled = disabled;
        geminiAnalysisBtn.disabled = disabled;
        bankSelector.disabled = disabled;
        if (bankSelector.value !== '比率網綜合比較') {
            dateSelector.disabled = disabled;
        } else {
            dateSelector.disabled = true;
        }
    }

    function startTask(endpoint, body) {
        setControlsDisabled(true);
        reportContainer.innerHTML = "<p class='placeholder-text'>任務準備中...</p>";
        statusBox.textContent = "任務準備中...";
        fetch(endpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        }).then(response => {
            if (!response.ok) { return response.json().then(err => { throw new Error(err.message || "請求失敗"); }); }
            return response.json();
        }).then(data => {
            if (data.status && data.status.includes('started')) {
                startPolling();
            } else {
                 throw new Error(data.message || '後端返回未知錯誤');
            }
        }).catch(error => {
            statusBox.textContent = `[錯誤] 啟動失敗: ${error.message}`;
            setControlsDisabled(false);
        });
    }

    function startPolling() {
        if (poller) clearInterval(poller);
        pollStatus(); 
        poller = setInterval(pollStatus, 1500);
    }

    function pollStatus() {
        fetch('/status').then(res => res.json()).then(data => { updateUI(data); })
        .catch(err => {
            statusBox.textContent = `[錯誤] 無法獲取狀態: ${err.message}`;
            clearInterval(poller);
            poller = null;
            setControlsDisabled(false);
        });
    }
    
    function updateUI(data) {
        statusBox.textContent = `[${data.stage}] ${data.message}`;
        const isRunning = data.stage === 'scraping' || data.stage === 'finding_location';
        setControlsDisabled(isRunning);
        if (!isRunning && poller) {
            clearInterval(poller);
            poller = null;
        }
        if (data.stage === 'complete') {
            generateReport(data.results);
        } else if (data.stage === 'error') {
            reportContainer.innerHTML = `<div class='error-message'><h2>任務失敗</h2><p>${data.message}</p></div>`;
        }
    }

    function generateReport(results) {
        currentRateData = []; 
        if (results && results.best_rate_info) {
            const rate = results.best_rate_info;
            const branch = results.nearest_branch_info;
            let html = "<h2>智慧查詢結果</h2>";
            html += `<div class="sub-block"><h3><i class="fas fa-money-bill-wave"></i> 最佳換匯銀行 (現金賣出)</h3><p>銀行：<b>${rate.bank}</b></p><p>匯率：<b style="color: #ff6b6b; font-size: 1.2em;">${rate.cash_sell}</b> (數字越低越好)</p></div>`;
            if (branch) {
                html += `<div class="sub-block" style="margin-top: 15px;"><h3><i class="fas fa-map-marker-alt"></i> 距離您最近的分行</h3><p>分行名稱：<b>${branch.name}</b></p><p>地址：${branch.address}</p><p>Google 評分：${branch.rating || '無'}</p><p>目前是否營業：${branch.is_open ? '是' : (branch.is_open === false ? '否' : '未知')}</p><p style="margin-top: 10px;"><a href="${branch.map_url}" target="_blank" class="btn btn-primary">在 Google 地圖上開啟</a></p></div>`;
            } else {
                html += `<div class="sub-block" style="margin-top: 15px;"><h3><i class="fas fa-exclamation-triangle"></i> 抱歉，找不到您附近的分行</h3></div>`;
            }
            reportContainer.innerHTML = html;
        } else if (typeof results === 'string') {
            let html = `<h2>Gemini 分析與展望</h2>`;
            html += `<div class="sub-block" style="background-color: #1a1a1a;"><pre class="ai-review-text" style="font-size: 1em;">${results}</pre></div>`;
            reportContainer.innerHTML = html;
        } else if (results && results.length > 0) {
            currentRateData = results;
            sortState = { column: null, direction: 'asc' };
            redrawTable();
        } else {
            reportContainer.innerHTML = "<p class='placeholder-text'>查無資料。</p>";
        }
    }

    // --- 5. 排序相關函式 ---

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
            tableHTML += `<tr><td>${item.bank}</td><td>${item.currency}</td><td>${item.date}</td><td style="color: #a3e9a4;">${item.cash_buy}</td><td style="color: #ff6b6b;">${item.cash_sell}</td><td style="color: #a3e9a4;">${item.spot_buy}</td><td style="color: #ff6b6b;">${item.spot_sell}</td></tr>`;
        });
        tableHTML += '</tbody></table>';
        return tableHTML;
    }
    
    function addSortEventListeners() {
        const headers = document.querySelectorAll('.report-table th.sortable');
        headers.forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
            if (sortState.column === header.dataset.sortKey) {
                header.classList.add(sortState.direction === 'asc' ? 'sort-asc' : 'sort-desc');
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

    // --- 初始載入 ---
    handleBankSelectionChange();
    pollStatus();
});