# 檔案: gemini_analyzer.py (修改後)
import os
import vertexai
from vertexai.generative_models import GenerativeModel

# --- 您的 Google Cloud 專案資訊 ---
# --- 將金鑰檔案路徑改為相對路徑 ---
# 這會讓程式自動在執行檔 (.exe) 或主程式 (.py) 所在的目錄尋找金鑰檔案
KEY_FILE_NAME = "aicoding-463201-691781620f8f.json"
# __file__ 會取得目前檔案 (gemini_analyzer.py) 的路徑
# os.path.dirname(__file__) 會取得該檔案所在的目錄
# os.path.join 會安全地將目錄和檔名組合成一個完整的路徑
KEY_FILE_PATH = os.path.join(os.path.dirname(__file__), KEY_FILE_NAME)

def initialize_gemini():
    """初始化 Vertex AI"""
    try:
        if not os.path.exists(KEY_FILE_PATH):
            raise FileNotFoundError(f"服務帳戶金鑰檔案不存在於: {KEY_FILE_PATH}")
            
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_FILE_PATH
        vertexai.init(project="aicoding-463201", location="us-central1")
        return True
    except Exception as e:
        print(f"Vertex AI 初始化失敗：{e}")
        return False

def get_currency_analysis_and_forecast(currency_code, currency_name, historical_data, news_snippets):
    """
    接收指定貨幣的歷史匯率和新聞，發送給 Gemini 進行分析與預測。
    
    :param currency_code: 貨幣代碼 (例如: "JPY")
    :param currency_name: 貨幣中文名稱 (例如: "日幣")
    :param historical_data: 一週歷史匯率的字串
    :param news_snippets: 相關新聞的字串
    :return: Gemini 回傳的分析文本
    """
    if not initialize_gemini():
        return "Gemini AI 服務初始化失敗，請檢查金鑰路徑與專案設定。"

    try:
        model = GenerativeModel("gemini-2.5-pro")
        
        # 設計給 Gemini 的通用提示 (Prompt)
        prompt = f"""
        你是一位頂級的金融市場分析師，專精於外匯市場，特別是 {currency_name}({currency_code}) 走勢。
        請基於以下提供的「過去一週台幣兌換 {currency_name} 的匯率數據」和「相關國際財經新聞摘要」，完成兩項任務：

        ---
        【資料一：過去一週匯率數據】
        {historical_data}
        ---
        【資料二：相關國際財經新聞摘要】
        {news_snippets}
        ---

        【任務】
        1.  **走勢總結**：請總結過去一週 {currency_name} 的整體走勢（相對台幣是升值、貶值或盤整），並結合新聞事件，簡要分析影響走勢的關鍵因素是什麼。
        2.  **未來一週展望**：基於以上所有資訊，對接下來一週的 {currency_name} 走勢做出一個簡要的預測和展望（例如：可能繼續貶值、有望反彈、或區間震盪），並條列式說明你的判斷依據。

        請用繁體中文、清晰、專業的條列式格式回覆。
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        print(f"Gemini API 請求失敗: {e}")
        return f"【分析失敗】：API 請求時發生錯誤: {e}"