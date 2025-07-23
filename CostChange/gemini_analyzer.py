# 檔案: gemini_analyzer.py
import os
import vertexai
from vertexai.generative_models import GenerativeModel

# --- 您的 Google Cloud 專案資訊 ---
# 請確認此路徑是您存放服務帳戶金鑰的正確路徑
KEY_FILE_PATH = "E:\\Germini API\\hwashu-462406-e678702fdead.json"

def initialize_gemini():
    """初始化 Vertex AI"""
    try:
        # 檢查金鑰檔案是否存在
        if not os.path.exists(KEY_FILE_PATH):
            raise FileNotFoundError(f"服務帳戶金鑰檔案不存在於: {KEY_FILE_PATH}")
            
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_FILE_PATH
        # 您的專案ID和地點
        vertexai.init(project="hwashu-462406", location="us-central1")
        return True
    except Exception as e:
        print(f"Vertex AI 初始化失敗：{e}")
        return False

def get_jpy_analysis_and_forecast(historical_data, news_snippets):
    """
    接收歷史匯率和新聞，發送給 Gemini 進行分析與預測。
    
    :param historical_data: 一週歷史匯率的字串
    :param news_snippets: 相關新聞的字串
    :return: Gemini 回傳的分析文本
    """
    if not initialize_gemini():
        return "Gemini AI 服務初始化失敗，請檢查金鑰路徑與專案設定。"

    try:
        model = GenerativeModel("gemini-2.5-pro")
        
        # 設計給 Gemini 的提示 (Prompt)
        prompt = f"""
        你是一位頂級的金融市場分析師，專精於外匯市場，特別是日圓(JPY)走勢。
        請基於以下提供的「過去一週台幣兌換日圓的匯率數據」和「相關國際財經新聞摘要」，完成兩項任務：

        ---
        【資料一：過去一週匯率數據】
        {historical_data}
        ---
        【資料二：相關國際財經新聞摘要】
        {news_snippets}
        ---

        【任務】
        1.  **走勢總結**：請總結過去一週日圓的整體走勢（升值、貶值或盤整），並結合新聞事件，簡要分析影響走勢的關鍵因素是什麼。
        2.  **未來一週展望**：基於以上所有資訊，對接下來一週的日圓走勢做出一個簡要的預測和展望（例如：可能繼續貶值、有望反彈、或區間震盪），並條列式說明你的判斷依據。

        請用繁體中文、清晰、專業的條列式格式回覆。
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        print(f"Gemini API 請求失敗: {e}")
        return f"【分析失敗】：API 請求時發生錯誤: {e}"