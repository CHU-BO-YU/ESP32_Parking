# 停車管理與車牌辨識系統

## 專案概述

本專案旨在建立一個自動化的停車管理系統。系統透過 ESP32-CAM 拍攝車輛照片，使用 Plate Recognizer API 進行車牌辨識，並根據車輛是否已繳費，透過另一塊 ESP32 控制 LCD 顯示及 GPIO 輸出，以指示停車狀態。

系統主要由以下幾個部分組成：

1.  **Python 主腳本 (`parking_management_system_py_v2.py`)**:
    * 從 ESP32-CAM 獲取影像串流。
    * 定時拍攝照片並儲存。
    * 將照片上傳至 Plate Recognizer API 進行車牌辨識。
    * 根據辨識出的車牌，查詢本地 SQLite 資料庫 (`PAID_VEHICLES`) 以判斷繳費狀態。
    * 將車牌號碼和繳費狀態透過 HTTP GET 請求傳送給另一塊 ESP32。
    * 將偵測記錄儲存到本地 SQLite 資料庫 (`PARKING_LOGS`)。
2.  **ESP32-CAM (影像擷取端)**:
    * 設定為網路攝影機，提供即時影像串流。
    * Python 腳本從此串流中擷取畫面。
3.  **ESP32 (狀態顯示與控制端)**:
    * 接收來自 Python 腳本的 HTTP GET 請求。
    * 在 I2C LCD 螢幕上顯示車牌號碼和繳費狀態（「已繳費」或「未繳費」）。
    * 根據繳費狀態控制兩個 GPIO 引腳的 HIGH/LOW 狀態，持續 3 秒。
    * LCD 顯示和 GPIO HIGH 狀態會在 3 秒後自動清除/變回 LOW。
    * 啟動時會在 LCD 上顯示其 IP 位址 10 秒。

## 主要功能

* **自動車牌辨識**: 使用 Plate Recognizer API。
* **繳費狀態查詢**: 透過本地資料庫判斷車輛是否已繳費。
* **即時狀態顯示**: 在 LCD 螢幕上顯示車牌及繳費狀態。
* **GPIO 輸出控制**: 根據繳費狀態觸發不同的 GPIO 輸出。
* **影像串流**: ESP32-CAM 提供即時影像。
* **日誌記錄**: 將偵測到的車輛資訊記錄到資料庫。
* **遠端設定 (WiFiManager)**: ESP32 模組使用 WiFiManager 方便設定 WiFi 連線。
* **測試資料**: Python 腳本啟動時會建立包含測試車牌的資料庫。

## 系統架構

本系統的資料流程與組件互動如下：

* **ESP32-CAM (影像擷取端)**：
    * 負責拍攝即時的車輛影像。
    * 透過本地 WiFi 網路，將影像以串流形式 (`/stream` 路徑) 提供給 Python 主腳本。

* **Python 主腳本 (執行於電腦)**：
    * 從 ESP32-CAM 接收影像串流。
    * 從串流中擷取靜態畫面，並將其上傳至 Plate Recognizer API (雲端服務) 進行車牌號碼的辨識。
    * 從 Plate Recognizer API 獲取辨識結果 (車牌號碼)。
    * 根據辨識出的車牌號碼，查詢本地 SQLite 資料庫 (`PAID_VEHICLES`) 以確認該車輛的繳費狀態。
    * 將車牌號碼和繳費狀態組合成 HTTP GET 請求，透過本地 WiFi 網路發送至 `/update` 路徑給 ESP32 (狀態顯示與控制端)。
    * 同時，將此次的偵測事件 (車牌、時間、狀態、照片路徑) 記錄到本地 SQLite 資料庫 (`PARKING_LOGS`) 中。

* **Plate Recognizer API (雲端辨識服務)**：
    * 接收由 Python 腳本傳送過來的車輛照片。
    * 執行車牌辨識演算法。
    * 將辨識結果 (車牌號碼等資訊) 回傳給 Python 腳本。

* **ESP32 (狀態顯示與控制端)**：
    * 透過本地 WiFi 網路，接收來自 Python 主腳本的 HTTP GET 請求 (路徑為 `/update`，包含車牌號碼和繳費狀態)。
    * 在連接的 I2C LCD 螢幕上顯示接收到的車牌號碼和對應的繳費狀態。
    * 根據繳費狀態 (例如 "paid" 或 "unpaid") 控制指定的 GPIO 引腳輸出高電位或低電位。

所有裝置 (ESP32-CAM、執行 Python 的電腦、ESP32 狀態顯示端) 都需要連接到同一個本地 WiFi 網路以便相互通訊。執行 Python 的電腦還需要能夠連接到網際網路，以便呼叫 Plate Recognizer API。

## 硬體需求

1.  **執行 Python 腳本的電腦**:
    * 作業系統：Windows, macOS, 或 Linux。
    * Python 環境。
    * 網路連線 (連接到與 ESP32 相同的區域網路，並能存取網際網路以下載套件及呼叫 Plate Recognizer API)。
2.  **ESP32-CAM 模組**:
    * ESP32-CAM 開發板 (例如 AI-Thinker ESP32-CAM)。
    * OV2640 或其他相容的相機模組。
    * USB 轉 TTL 序列轉換器 (用於燒錄程式)。
    * 穩定的 5V 電源。
3.  **ESP32 開發板 (用於 LCD 和 GPIO 控制)**:
    * 任何標準的 ESP32 開發板 (例如 ESP32 DevKitC)。
    * I2C LCD1602 顯示模組。
    * 杜邦線。
    * (可選) LED 指示燈及限流電阻，用於連接 GPIO 輸出。
    * USB 線 (用於燒錄程式和供電)。

## 軟體需求與依賴

1.  **Python 環境 (建議 Python 3.7+)**:
    * `requests`: 用於發送 HTTP 請求。
    * `opencv-python` (cv2): 用於影像處理和從 ESP32-CAM 讀取串流。
    * `sqlite3`: Python 內建，用於資料庫操作。
    * 安裝指令: `pip install requests opencv-python`

2.  **Arduino IDE (用於 ESP32 程式開發與燒錄)**:
    * ESP32 Board Support Package (ESP32 開發板支援)。
    * 必要的函式庫:
        * `WiFiManager` (by tzapu, AlexT)
        * `ESPAsyncWebServer` (by me-no-dev, Hristo Gochkov) - 用於 LCD/GPIO ESP32
        * `AsyncTCP` (by me-no-dev, Hristo Gochkov) - `ESPAsyncWebServer` 的依賴庫。
        * `LiquidCrystal_I2C` (by Frank de Brabander)
        * `Wire` (ESP32 內建)
        * (ESP32-CAM) `esp_camera.h`, `esp_http_server.h` (ESP-IDF 的一部分，通常已包含在 ESP32 Arduino Core 中)

3.  **Plate Recognizer API 金鑰**:
    * 您需要在 [Plate Recognizer 網站](https://platerecognizer.com/) 註冊帳戶並獲取 API 金鑰。

## 設定與安裝

### 1. Python 主腳本設定

1.  **複製專案檔案**: 將 `parking_management_system_py_v2.py` 和 `config.py` 檔案放置在您的電腦上同一個資料夾內。
2.  **安裝 Python 依賴庫**:
    ```bash
    pip install requests opencv-python
    ```
3.  **設定 `config.py`**:
    打開 `config.py` 檔案並填寫以下資訊：
    ```python
    # config.py

    # ESP32 CAM 的 IP 位址 (提供影像串流的 ESP32-CAM)
    ESP32_CAM_IP = "YOUR_ESP32_CAM_IP_ADDRESS" 

    # Plate Recognizer API 金鑰 (腳本會自動處理 "Token " 前綴)
    API_KEY = "YOUR_PLATE_RECOGNIZER_API_KEY_STRING" # 例如 "yourActualApiKeyString"

    # 接收停車狀態更新的 ESP32 的 IP 位址 (控制 LCD 和 GPIO 的 ESP32)
    ESP32_PARKING_IP = "YOUR_ESP32_LCD_GPIO_IP_ADDRESS"
    ```
    * `ESP32_CAM_IP`: ESP32-CAM 連接到 WiFi 後獲取的 IP 位址。
    * `API_KEY`: 您從 Plate Recognizer 獲取的 API 金鑰字串本身 (腳本會自動加上 "Token " 前綴)。
    * `ESP32_PARKING_IP`: 控制 LCD 和 GPIO 的 ESP32 連接到 WiFi 後獲取的 IP 位址。

### 2. ESP32-CAM (影像擷取端) 設定

1.  **開啟 Arduino IDE**。
2.  **安裝 ESP32 開發板支援** (如果尚未安裝)。
3.  **選擇正確的開發板型號**: 在 Arduino IDE 的「工具」->「開發板」中選擇適合您 ESP32-CAM 的型號 (例如 "AI Thinker ESP32-CAM")。
4.  **修改並燒錄程式碼**:
    * 將提供的 ESP32-CAM 程式碼 (包含 `esp_http_server` 的版本) 複製到 Arduino IDE。
    * **重要**: 確保相機的引腳定義 (`PWDN_GPIO_NUM`, `XCLK_GPIO_NUM` 等) 與您的 ESP32-CAM 硬體相符。
    * 程式碼中應包含 WiFiManager，首次啟動時，它會建立一個名為 "ESP32_CAM_Setup_Park" (或您在程式碼中設定的名稱) 的 WiFi 熱點。您需要連接此熱點，然後在瀏覽器中設定您家中或實驗室的 WiFi SSID 和密碼。
    * 透過 USB 轉 TTL 轉換器將程式碼燒錄到 ESP32-CAM。燒錄前，通常需要將 GPIO0 拉低 (接地) 以進入燒錄模式。
    * 燒錄完成後，拔掉 GPIO0 的接地，重新啟動 ESP32-CAM。
    * 打開序列埠監控視窗 (鮑率設為 115200)，觀察 ESP32-CAM 連接 WiFi 後獲取的 IP 位址。將此 IP 位址填入 Python 腳本的 `config.py` 中的 `ESP32_CAM_IP`。

### 3. ESP32 (狀態顯示與控制端) 設定

1.  **開啟 Arduino IDE**。
2.  **安裝 ESP32 開發板支援**。
3.  **安裝必要的函式庫**: `WiFiManager`, `ESPAsyncWebServer`, `AsyncTCP`, `LiquidCrystal_I2C`。
4.  **選擇正確的開發板型號**: 例如 "ESP32 Dev Module"。
5.  **修改並燒錄程式碼**:
    * 將提供的 ESP32 LCD/GPIO 控制程式碼 (使用 `ESPAsyncWebServer` 的版本，ID: `esp32_lcd_gpio_control`) 複製到 Arduino IDE。
    * **重要**: 檢查 `LiquidCrystal_I2C lcd(0x27, 16, 2);` 中的 I2C 位址 (`0x27`) 是否與您的 LCD 模組相符。如果不符，請修改。
    * **重要**: 檢查 `Wire.begin(21, 22);` 中的 I2C 引腳是否與您的 ESP32 板子和 LCD 連接相符，並確保這些引腳沒有被其他功能佔用 (例如，如果您的 ESP32 板子將 GPIO21/22 用於其他目的，您需要更改 LCD 的 I2C 引腳並更新此行)。
    * **重要**: 檢查 `PAID_GPIO_PIN` (預設 18) 和 `UNPAID_GPIO_PIN` (預設 19) 是否是您實際使用的 GPIO 引腳。
    * 程式碼中也包含 WiFiManager，首次啟動時會建立名為 "ESP32-ParkingSetup" (或您設定的名稱) 的 WiFi 熱點。連接並設定 WiFi。
    * 燒錄程式碼到 ESP32。
    * 燒錄完成後，重新啟動 ESP32。
    * 打開序列埠監控視窗 (鮑率設為 115200)，觀察 ESP32 連接 WiFi 後獲取的 IP 位址。將此 IP 位址填入 Python 腳本的 `config.py` 中的 `ESP32_PARKING_IP`。

## 如何運行

1.  **啟動 ESP32 裝置**: 確保 ESP32-CAM 和 ESP32 (LCD/GPIO) 都已上電並成功連接到 WiFi 網路。
2.  **運行 Python 主腳本**:
    在您的電腦上，打開終端機或命令提示字元，導航到包含 `parking_management_system_py_v2.py` 和 `config.py` 的資料夾，然後執行：
    ```bash
    python parking_management_system_py_v2.py
    ```
3.  **觀察輸出**:
    * Python 腳本的終端機會顯示偵錯訊息，包括連接攝影機、拍照、API 請求、辨識結果、傳送給 ESP32 的狀態等。
    * ESP32 (LCD/GPIO) 的 LCD 螢幕會顯示車牌和狀態，對應的 GPIO 也會動作。
    * ESP32 的序列埠監控視窗也會顯示接收到的資料和 GPIO 狀態變化。

## 故障排除

* **Python 腳本無法連接到 ESP32-CAM**:
    * 確認 `config.py` 中的 `ESP32_CAM_IP` 是否正確。
    * 確認 ESP32-CAM 已連接到 WiFi 並且影像串流服務 (`/stream`) 正在運行。
    * 檢查電腦和 ESP32-CAM 是否在同一個區域網路內，且沒有防火牆阻擋。
* **Plate Recognizer API 錯誤**:
    * `Authentication credentials were not provided` 或 `403 Forbidden`: 檢查 `config.py` 中的 `API_KEY` 是否是您帳戶的有效金鑰字串，以及 Python 腳本中處理 `Authorization` 標頭的邏輯是否正確。
    * `You do not have enough credits` 或 `quota exceeded`: 您的 Plate Recognizer 帳戶點數或方案配額不足，需要充值或等待配額重置。
    * 其他 HTTP 錯誤: 根據錯誤碼和 API 回應內容進行排查。
* **Python 腳本無法將資料傳送給 ESP32 (LCD/GPIO)**:
    * 確認 `config.py` 中的 `ESP32_PARKING_IP` 是否正確。
    * 確認 ESP32 (LCD/GPIO) 已連接到 WiFi 並且其網頁伺服器 (`/update` 端點) 正在運行。
    * 檢查網路連線和防火牆。
    * 查看 Python 腳本和 ESP32 序列埠監控的輸出，是否有連線錯誤訊息。
* **LCD 未顯示或顯示異常**:
    * 檢查 LCD 的 I2C 位址和 SDA/SCL 引腳連接是否正確。
    * 確認 `LiquidCrystal_I2C` 函式庫已正確安裝。
* **GPIO 未動作**:
    * 確認 ESP32 程式碼中定義的 GPIO 引腳號碼是否與您的硬體連接一致。
    * 檢查外部電路 (如 LED 和電阻) 是否連接正確。
* **車牌辨識結果不佳或總是「未偵測到車牌」**:
    * 檢查 ESP32-CAM 拍攝的照片品質 (儲存在 `./photo/` 資料夾中)：清晰度、光線、角度、車牌大小。
    * 調整 ESP32-CAM 的鏡頭焦距。
    * 嘗試調整 ESP32-CAM 程式碼中的相機解析度和 JPEG 品質設定。

## 未來可擴展功能 (可選)

* 將 `PAID_VEHICLES` 資料庫改為更專業的資料庫系統 (如 PostgreSQL, MySQL)。
* 增加網頁介面來管理已繳費車輛和查看停車記錄。
* 支援多個攝影機。
* 增加更複雜的停車邏輯 (例如，計時收費)。
* 當辨識到未繳費車輛時，發送郵件或即時訊息通知。
