# --- 這是 app.py 的最終、完整、正確版本 ---

import os
import json
from flask import Flask, render_template, jsonify, request, send_from_directory
import threading
import webview
import rate_scraper 
from datetime import datetime, timedelta
import googlemaps
from googleapiclient.discovery import build

# --- 設定區塊 ---

CONFIG_FILE_PATH = 'config.json'
try:
    with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # ✅ 正確的鍵名和變數名稱
    Maps_API_KEY = config.get('Maps_api_key')
    Google_search_ENGINE_ID = config.get('Google Search_engine_id')

    # ✅ 正確的變數名稱進行檢查
    if not Maps_API_KEY or not Google_search_ENGINE_ID:
        raise ValueError("請在 config.json 中設定 'Maps_api_key' 和 'Google Search_engine_id'。")

except FileNotFoundError:
    raise FileNotFoundError(f"找不到設定檔: {CONFIG_FILE_PATH}，請依照指示建立它。")
except Exception as e:
    raise e

# 使用從檔案中讀取的金鑰來初始化 Google Maps 用戶端
gmaps = googlemaps.Client(key=Maps_API_KEY)


# --- Flask 應用程式設定 ---
app = Flask(__name__, template_folder='.', static_folder='static')
status = {"stage": "idle", "message": "閒置", "results": None}


# --- 背景任務函式 ---

def fetch_rate_data_task(bank: str, date_str: str):
    print(f"--- 日誌: 進入 fetch_rate_data_task (銀行: {bank}, 日期: {date_str}) ---")
    global status
    status.update({"stage": "scraping", "message": f"正在從 {bank} 抓取資料...", "results": None})
    try:
        scraped_data = None
        if bank == "台灣銀行":
            scraped_data = rate_scraper.scrape_bank_of_taiwan(date_str)
        elif bank == "第一銀行":
            scraped_data = rate_scraper.scrape_first_bank(date_str)
        elif bank == "中央銀行":
            scraped_data = rate_scraper.scrape_central_bank(date_str)
        elif bank == "比率網綜合比較":
            scraped_data = rate_scraper.scrape_findrate_jpy()
        
        if scraped_data:
            status.update({"stage": "complete", "message": f"成功抓取 {len(scraped_data)} 筆匯率資料！", "results": scraped_data})
        else:
            status.update({"stage": "complete", "message": f"未從 {bank} 抓取到資料。", "results": []})
    except Exception as e:
        print(f"--- 錯誤: fetch_rate_data_task 發生錯誤 -> {e} ---")
        status.update({"stage": "error", "message": f"抓取失敗: {e}"})


def find_best_and_nearest_task():
    print("--- 日誌: 進入 find_best_and_nearest_task ---")
    global status
    status.update({"stage": "scraping", "message": "正在抓取匯率資料...", "results": None})
    try:
        all_rates = rate_scraper.scrape_findrate_jpy()
        if not all_rates: raise Exception("無法抓取到匯率資料。")

        valid_rates = [r for r in all_rates if r['cash_sell'] != '--']
        if not valid_rates: raise Exception("找不到任何有效的現金賣出匯率。")
            
        best_bank_rate = min(valid_rates, key=lambda x: float(x['cash_sell']))
        best_bank_name = best_bank_rate['bank']
        
        status.update({"stage": "finding_location", "message": f"找到最佳匯率銀行: {best_bank_name}，正在搜尋最近分行..."})

        my_location_address = "高雄市仁武區"
        geocode_result = gmaps.geocode(my_location_address)
        if not geocode_result: raise Exception(f"無法將地址 '{my_location_address}' 轉換為經緯度。")
        my_lat_lng = geocode_result[0]['geometry']['location']

        places_result = gmaps.places(
            query=best_bank_name,
            location=my_lat_lng,
            language='zh-TW'
        )
        
        if places_result and places_result.get('results'):
            nearest = places_result['results'][0]
            address = nearest.get('formatted_address') or nearest.get('vicinity') or "地址未提供"

        nearest_branch_data = {
            "name": nearest.get('name'), 
            "address": address, # 使用我們處理過的、更強健的 address 變數
            "rating": nearest.get('rating', 'N/A'),
            "is_open": nearest.get('opening_hours', {}).get('open_now', '未知'),
            "map_url": f"https://www.google.com/maps/search/?api=1&query={nearest.get('name')}&query_place_id={nearest.get('place_id')}"
        }

        final_result = { "best_rate_info": best_bank_rate, "nearest_branch_info": nearest_branch_data }
        status.update({"stage": "complete", "message": "查詢完成！", "results": final_result})
    except Exception as e:
        print(f"--- 錯誤: find_best_and_nearest_task 發生錯誤 -> {e} ---")
        status.update({"stage": "error", "message": f"處理時發生錯誤: {e}"})

def gemini_analysis_task():
    global status
    try:
        status.update({"stage": "scraping", "message": "正在抓取過去一週歷史匯率...", "results": None})
        today = datetime.now()
        historical_data_list = []
        for i in range(7):
            query_date = today - timedelta(days=i)
            date_str = query_date.strftime("%Y-%m-%d")
            rates = rate_scraper.scrape_bank_of_taiwan(date_str)
            if rates:
                historical_data_list.append(f"{rates[0]['date']}: 現金賣出價 {rates[0]['cash_sell']}")
        historical_data_str = "\n".join(historical_data_list)

        status.update({"stage": "finding_location", "message": "正在搜尋相關國際新聞...", "results": None})
        service = build("customsearch", "v1", developerKey=Maps_API_KEY)
        search_results = service.cse().list(
            q="最近一週 日幣 匯率 走勢 國際新聞 財經",
            cx=Google_search_ENGINE_ID,
            num=5
        ).execute()
        news_snippets_list = [f"- {item['snippet']}" for item in search_results.get('items', [])]
        news_snippets_str = "\n".join(news_snippets_list) if news_snippets_list else "找不到相關新聞。"

        status.update({"stage": "scraping", "message": "已獲取資料，正在請求 Gemini 進行分析...", "results": None})
        import gemini_analyzer 
        analysis_result = gemini_analyzer.get_jpy_analysis_and_forecast(
            historical_data=historical_data_str,
            news_snippets=news_snippets_str
        )
        
        status.update({"stage": "complete", "message": "Gemini 分析完成！", "results": analysis_result})
    except Exception as e:
        print(f"--- 錯誤: Gemini 分析任務發生錯誤 -> {e} ---")
        status.update({"stage": "error", "message": f"分析失敗: {e}"})

# --- API 路由 (Routes) ---

@app.route('/get_rate_data', methods=['POST'])
def get_rate_data_api():
    data = request.json
    bank_to_query = data.get('bank')
    date_to_query = data.get('date')
    if not bank_to_query or (not date_to_query and bank_to_query != "比率網綜合比較"):
        return jsonify({"status": "error", "message": "缺少銀行或日期參數。"}), 400
    thread = threading.Thread(target=fetch_rate_data_task, args=(bank_to_query, date_to_query))
    thread.daemon = True
    thread.start()
    return jsonify({"status": "scraping_started"})

@app.route('/find_best_and_nearest', methods=['POST'])
def find_best_and_nearest_api():
    thread = threading.Thread(target=find_best_and_nearest_task)
    thread.daemon = True
    thread.start()
    return jsonify({"status": "scraping_started"})

@app.route('/get_gemini_analysis', methods=['POST'])
def get_gemini_analysis_api():
    thread = threading.Thread(target=gemini_analysis_task)
    thread.daemon = True
    thread.start()
    return jsonify({"status": "scraping_started"})
    
@app.route('/status')
def get_status():
    return jsonify(status)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index():
    today_str = datetime.now().strftime("%Y-%m-%d")
    return render_template('index.html', default_date=today_str)

# --- 程式主入口 ---

def run_flask():
    app.run(host="127.0.0.1", port=5000)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    webview.create_window('台幣日幣匯率查詢工具', 'http://127.0.0.1:5000', width=1000, height=800)
    webview.start() 