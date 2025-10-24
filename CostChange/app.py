# --- 這是 app.py 的修改後版本 ---

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
    Maps_API_KEY = config.get('Maps_api_key')
    Google_search_ENGINE_ID = config.get('Google_search_ENGINE_ID')
    if not Maps_API_KEY or not Google_search_ENGINE_ID:
        raise ValueError("請在 config.json 中設定 'Maps_api_key' 和 'Google_search_ENGINE_ID'。")
except FileNotFoundError:
    raise FileNotFoundError(f"找不到設定檔: {CONFIG_FILE_PATH}，請依照指示建立它。")
except Exception as e:
    raise e
gmaps = googlemaps.Client(key=Maps_API_KEY)


# --- Flask 應用程式設定 ---
app = Flask(__name__, template_folder='.', static_folder='static')
status = {"stage": "idle", "message": "閒置", "results": None}


# --- 背景任務函式 ---

def get_chart_data_task(currency: str, start_date: str, end_date: str):
    """
    抓取歷史圖表資料的背景任務 (接收起訖日期)。
    """
    print(f"--- 日誌: 進入 get_chart_data_task (貨幣: {currency}, 從: {start_date}, 到: {end_date}) ---")
    global status
    status.update({"stage": "scraping", "message": f"正在抓取 {currency} 的真實歷史資料...", "results": None})
    try:
        # 呼叫真實數據爬蟲
        chart_data = rate_scraper.scrape_historical_chart_data(start_date, end_date, currency)
        if chart_data:
            status.update({"stage": "complete", "message": "圖表資料抓取成功！", "results": chart_data})
        else:
            status.update({"stage": "complete", "message": "在指定區間內找不到圖表資料。", "results": None})
    except Exception as e:
        print(f"--- 錯誤: get_chart_data_task 發生錯誤 -> {e} ---")
        status.update({"stage": "error", "message": f"抓取圖表資料失敗: {e}"})

def fetch_rate_data_task(currency: str):
    print(f"--- 日誌: 進入 fetch_rate_data_task (貨幣: {currency}) ---")
    global status
    status.update({"stage": "scraping", "message": f"正在從 比率網 抓取 {currency} 匯率資料...", "results": None})
    try:
        scraped_data = rate_scraper.scrape_findrate_by_currency(currency)
        if scraped_data:
            status.update({"stage": "complete", "message": f"成功抓取 {len(scraped_data)} 筆 {currency} 匯率資料！", "results": scraped_data})
        else:
            status.update({"stage": "complete", "message": f"未從 比率網 抓取到 {currency} 資料。", "results": []})
    except Exception as e:
        print(f"--- 錯誤: fetch_rate_data_task 發生錯誤 -> {e} ---")
        status.update({"stage": "error", "message": f"抓取失敗: {e}"})

def find_best_and_nearest_task(currency: str, lat: float, lng: float):
    """
    修改後的函式：接收經緯度，尋找最佳匯率的前三名銀行及其最近分行。
    """
    print(f"--- 日誌: 進入 find_best_and_nearest_task (貨幣: {currency}, 座標: {lat}, {lng}) ---")
    global status
    status.update({"stage": "scraping", "message": f"正在抓取 {currency} 匯率資料...", "results": None})
    try:
        all_rates = rate_scraper.scrape_findrate_by_currency(currency)
        if not all_rates: raise Exception(f"無法抓取到 {currency} 的匯率資料。")

        valid_rates = [r for r in all_rates if r['cash_sell'] and r['cash_sell'] != '--']
        if not valid_rates: raise Exception("找不到任何有效的現金賣出匯率。")
        
        sorted_rates = sorted(valid_rates, key=lambda x: float(x['cash_sell']))
        top_three_banks = sorted_rates[:3]
        
        final_results = []
        # *** 修改處：直接使用傳入的經緯度座標 ***
        my_lat_lng = {"lat": lat, "lng": lng}

        for index, bank_rate in enumerate(top_three_banks):
            bank_name = bank_rate['bank']
            status.update({"stage": "finding_location", "message": f"({index+1}/3) 正在搜尋 {bank_name} 的最近分行..."})

            # *** 修改處：location 參數直接使用 my_lat_lng ***
            places_result = gmaps.places(query=bank_name, location=my_lat_lng, language='zh-TW')
            
            nearest_branch_data = None
            if places_result and places_result.get('results'):
                nearest = places_result['results'][0]
                address = nearest.get('formatted_address') or nearest.get('vicinity') or "地址未提供"
                nearest_branch_data = {
                    "name": nearest.get('name'), "address": address,
                    "rating": nearest.get('rating', 'N/A'),
                    "is_open": nearest.get('opening_hours', {}).get('open_now', '未知'),
                    "map_url": f"https://www.google.com/maps/search/?api=1&query={nearest.get('name')}&query_place_id={nearest.get('place_id')}"
                }
            
            final_results.append({
                "rank": index + 1,
                "best_rate_info": bank_rate,
                "nearest_branch_info": nearest_branch_data
            })

        status.update({"stage": "complete", "message": "查詢完成！", "results": final_results})
        
    except Exception as e:
        print(f"--- 錯誤: find_best_and_nearest_task 發生錯誤 -> {e} ---")
        status.update({"stage": "error", "message": f"處理時發生錯誤: {e}"})

def gemini_analysis_task(currency_code: str, currency_name: str):
    global status
    try:
        status.update({"stage": "scraping", "message": f"正在抓取 {currency_name} 最近一週的歷史匯率...", "results": None})
        
        # 1. 計算最近一週的起訖日期
        today = datetime.now()
        end_date_str = today.strftime("%Y-%m-%d")
        start_date_str = (today - timedelta(days=7)).strftime("%Y-%m-%d")

        # 2. 使用新的、更強大的爬蟲函式一次性獲取所有資料
        historical_rates = rate_scraper.scrape_historical_chart_data(start_date_str, end_date_str, currency_code)

        # 3. 將獲取到的資料格式化成字串
        if historical_rates:
            historical_data_list = [f"{rate['date']}: 現金賣出價 {rate['value']}" for rate in historical_rates]
            historical_data_str = "\n".join(historical_data_list)
        else:
            historical_data_str = "過去一週查無歷史匯率資料。"

        status.update({"stage": "finding_location", "message": f"正在搜尋 {currency_name} 相關國際新聞...", "results": None})
        service = build("customsearch", "v1", developerKey=Maps_API_KEY)
        search_query = f"最近一週 {currency_name} 匯率 走勢 國際新聞 財經"
        search_results = service.cse().list(q=search_query, cx=Google_search_ENGINE_ID, num=5).execute()
        news_snippets_list = [f"- {item['snippet']}" for item in search_results.get('items', [])]
        news_snippets_str = "\n".join(news_snippets_list) if news_snippets_list else "找不到相關新聞。"

        status.update({"stage": "scraping", "message": "已獲取資料，正在請求 Gemini 進行分析...", "results": None})
        import gemini_analyzer 
        analysis_result = gemini_analyzer.get_currency_analysis_and_forecast(
            currency_code=currency_code,
            currency_name=currency_name,
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
    currency_to_query = data.get('currency')
    if not currency_to_query:
        return jsonify({"status": "error", "message": "缺少貨幣參數。"}), 400
    thread = threading.Thread(target=fetch_rate_data_task, args=(currency_to_query,))
    thread.daemon = True
    thread.start()
    return jsonify({"status": "scraping_started"})

@app.route('/find_best_and_nearest', methods=['POST'])
def find_best_and_nearest_api():
    data = request.json
    currency_to_query = data.get('currency')
    lat = data.get('lat')
    lng = data.get('lng')

    # *** 修改處：檢查經緯度是否存在 ***
    if not all([currency_to_query, lat, lng]):
        return jsonify({"status": "error", "message": "缺少貨幣或地理座標參數。"}), 400
        
    thread = threading.Thread(target=find_best_and_nearest_task, args=(currency_to_query, lat, lng))
    thread.daemon = True
    thread.start()
    return jsonify({"status": "scraping_started"})

@app.route('/get_gemini_analysis', methods=['POST'])
def get_gemini_analysis_api():
    data = request.json
    currency_code = data.get('currency_code')
    currency_name = data.get('currency_name')
    if not currency_code or not currency_name:
        return jsonify({"status": "error", "message": "缺少貨幣代碼或名稱參數。"}), 400
    thread = threading.Thread(target=gemini_analysis_task, args=(currency_code, currency_name))
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
    return render_template('index.html')

@app.route('/get_historical_chart_data', methods=['POST'])
def get_historical_chart_data_api():
    data = request.json
    currency_to_query = data.get('currency')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    if not all([currency_to_query, start_date, end_date]):
        return jsonify({"status": "error", "message": "缺少貨幣或日期範圍參數。"}), 400
    
    thread = threading.Thread(target=get_chart_data_task, args=(currency_to_query, start_date, end_date))
    thread.daemon = True
    thread.start()
    return jsonify({"status": "scraping_started"})

# --- 程式主入口 ---
def run_flask():
    app.run(host="127.0.0.1", port=5000)
    pass
if __name__ == '__main__':
    from waitress import serve
    # host='0.0.0.0' 讓區域網路內的其他電腦可以訪問
    # port 可以設定您想要的埠號
    print("Web Server is running on http://127.0.0.1:8000")
    serve(app, host="127.0.0.1", port=8000)