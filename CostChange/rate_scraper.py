# 檔案: E:\AOIimg\rate_scraper.py (重寫版)
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from collections import defaultdict

# --- 台灣銀行歷史資料爬蟲 (真實數據版) ---
BOT_HISTORY_URL = "https://rate.bot.com.tw/xrt/quote/{year}-{month}/{currency}"

def scrape_historical_chart_data(start_date_str: str, end_date_str: str, currency_code: str):
    """
    [真實數據版] 根據指定的起訖日期，爬取台灣銀行網站的真實歷史匯率。
    """
    print(f"--- [真實數據] 正在抓取 {currency_code} 從 {start_date_str} 到 {end_date_str} 的歷史資料 ---")
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    # 產生需要查詢的所有月份 (格式 YYYY-MM)
    months_to_scrape = set()
    current_date = start_date
    while current_date <= end_date:
        months_to_scrape.add(current_date.strftime("%Y-%m"))
        # 前進到下個月的第一天，避免重複
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1, day=1)

    all_rates = []
    
    # 逐月爬取資料
    for ym in sorted(list(months_to_scrape)):
        year, month = ym.split('-')
        url = BOT_HISTORY_URL.format(year=year, month=month, currency=currency_code.upper())
        print(f"正在查詢月份: {ym}, 網址: {url}")
        
        try:
            headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36' }
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find("table", class_="table-striped")
            if not table or not table.find('tbody'):
                continue

            for row in table.find('tbody').find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 6:
                    # 日期格式是 YYYY/MM/DD，需轉換
                    date_in_row_str = cells[0].text.strip().replace('/', '-')
                    rate_date = datetime.strptime(date_in_row_str, "%Y-%m-%d")

                    # 只保留在使用者指定範圍內的資料
                    if start_date <= rate_date <= end_date:
                        all_rates.append({
                            "date": date_in_row_str,
                            "value": float(cells[3].text.strip()) # 現金賣出
                        })
        except Exception as e:
            print(f"抓取月份 {ym} 時發生錯誤: {e}")
            
    # 按日期排序，確保資料是時間連續的
    all_rates.sort(key=lambda x: x['date'])
    return all_rates


# --- 通用的比率網抓取函式 (無需修改) ---
FINDRATE_BASE_URL = "https://www.findrate.tw/{currency}/"

def scrape_findrate_by_currency(currency_code: str):
    url = FINDRATE_BASE_URL.format(currency=currency_code.upper())
    print(f"正在從比率網抓取 {currency_code} 匯率，網址: {url}")
    try:
        headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36' }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_h2 = soup.find('h2', string=lambda t: t and '對新台幣匯率各銀行外匯牌告匯率比較' in t)
        if not title_h2:
            print(f"在頁面上找不到 {currency_code} 的匯率比較表格標題。")
            return None
        rate_table = title_h2.find_next('table')
        
        results = []
        for row in rate_table.find('tbody').find_all('tr')[1:]:
            cells = row.find_all('td')
            if len(cells) >= 6:
                results.append({
                    "bank": cells[0].text.strip(),
                    "currency": currency_code.upper(),
                    "date": cells[5].text.strip(),
                    "cash_buy": cells[1].text.strip(),
                    "cash_sell": cells[2].text.strip(),
                    "spot_buy": cells[3].text.strip(),
                    "spot_sell": cells[4].text.strip(),
                })
        return results

    except Exception as e:
        print(f"處理比率網 ({currency_code}) 資料時發生錯誤: {e}")
        return None