# 檔案: E:\CostChange\rate_scraper.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --- 原有的台灣銀行抓取函式 (我們保留它) ---
BOT_HISTORY_RATE_URL = "https://rate.bot.com.tw/xrt/flcsv/{date}"

def scrape_bank_of_taiwan(date_str: str):
    url = BOT_HISTORY_RATE_URL.format(date=date_str)
    print(f"正在從台灣銀行抓取 {date_str} 的匯率資料，網址: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        response.encoding = 'utf-8'
        lines = response.text.strip().split('\n')
        rate_data = lines[1:]
        results = []
        for line in rate_data:
            parts = line.split(',')
            if len(parts) > 6 and parts[1] == 'JPY':
                results.append({
                    "bank": "台灣銀行", "currency": "JPY", "date": parts[0],
                    "cash_buy": parts[2], "cash_sell": parts[3],
                    "spot_buy": parts[4], "spot_sell": parts[5],
                })
                break
        return results
    except Exception as e:
        print(f"處理台灣銀行資料時發生錯誤: {e}")
        return None

# --- 新增的比率網抓取函式 ---
FINDRATE_URL = "https://www.findrate.tw/JPY/"

def scrape_findrate_jpy():
    """
    從比率網 (findrate.tw) 抓取所有銀行的日幣牌告匯率。
    """
    print(f"正在從比率網抓取所有銀行匯率，網址: {FINDRATE_URL}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        }
        response = requests.get(FINDRATE_URL, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 根據 HTML 結構，找到包含所有匯率的表格
        # 這個表格在 `<h2>日幣對新台幣匯率各銀行外匯牌告匯率比較</h2>` 標題之後
        rate_table = soup.find('h2', string='日幣對新台幣匯率各銀行外匯牌告匯率比較').find_next('table')
        
        results = []
        # 遍歷表格中的每一行 (tr)，跳過第一行標頭
        for row in rate_table.find('tbody').find_all('tr')[1:]:
            # 獲取該行的所有儲存格 (td)
            cells = row.find_all('td')
            if len(cells) >= 6: # 確保是一行有效的資料
                bank_name = cells[0].text.strip()
                cash_buy = cells[1].text.strip()
                cash_sell = cells[2].text.strip()
                spot_buy = cells[3].text.strip()
                spot_sell = cells[4].text.strip()
                update_time = cells[5].text.strip()

                results.append({
                    "bank": bank_name,
                    "currency": "JPY",
                    "date": update_time, # 日期欄位我們用更新時間代替
                    "cash_buy": cash_buy,
                    "cash_sell": cash_sell,
                    "spot_buy": spot_buy,
                    "spot_sell": spot_sell,
                })
        return results

    except requests.exceptions.RequestException as e:
        print(f"抓取比率網資料時網路錯誤: {e}")
        return None
    except Exception as e:
        print(f"處理比率網資料時發生錯誤: {e}")
        return None


# --- 其他銀行的函式 (保留結構) ---
def scrape_first_bank(date_str: str):
    print(f"第一銀行抓取功能待實作: {date_str}")
    return [{"bank": "第一銀行", "currency": "JPY", "date": date_str, "cash_buy": "N/A", "cash_sell": "N/A", "spot_buy": "N/A", "spot_sell": "N/A"}]

def scrape_central_bank(date_str: str):
    print(f"中央銀行抓取功能待實作: {date_str}")
    return None