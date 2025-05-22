import requests
import datetime
import cv2
import config  # 假設 config.py 包含 ESP32_CAM_IP, API_KEY, ESP32_PARKING_IP
import os
import sqlite3
import time

# 資料庫設定 - 停車管理
# 建立/連接到 SQLite 資料庫
DB_NAME = 'PARKING_MANAGEMENT.db'
con = sqlite3.connect(DB_NAME)
cursor = con.cursor()

# 建立 PARKING_LOGS 資料表以儲存偵測到的車輛及其付款狀態
cursor.execute('''
    CREATE TABLE IF NOT EXISTS PARKING_LOGS (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plate TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        payment_status TEXT NOT NULL,  -- "paid" 或 "unpaid"
        snapshot_path TEXT NOT NULL
    )
''')
con.commit()

# 函數 - 建立並填入測試用已繳費車輛資料表
def setup_demo_paid_vehicles_table():
    """建立並填入一個包含預定義車牌及其繳費狀態的測試資料表。"""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PAID_VEHICLES (
            plate TEXT PRIMARY KEY,
            status TEXT NOT NULL
        )
    ''')
    # 新增一些測試用車輛，包含其繳費狀態
    # 您可以為展示修改這些車牌和狀態
    demo_plates_with_status = [
        ('abc1234', 'paid'),    # 範例：已繳費
        ('wbj5678', 'unpaid'),  # 範例：未繳費
        ('ajv1688', 'paid'),    # 範例：已繳費
        ('nbx3388', 'unpaid')   # 範例：未繳費
    ]
    try:
        # INSERT 語句現在包含 plate 和 status
        cursor.executemany('INSERT OR IGNORE INTO PAID_VEHICLES (plate, status) VALUES (?, ?)', demo_plates_with_status)
        con.commit()
        print("[資料庫] 測試用車輛資料表 (PAID_VEHICLES) 建立/更新完成。")
    except sqlite3.Error as e:
        print(f"[資料庫錯誤] 無法建立/更新測試用車輛資料表: {e}")

# 函數 - 傳送資料到 ESP32
def send_to_esp32(plate, payment_status_text):
    """透過 HTTP GET 請求將車牌和付款狀態傳送給 ESP32。"""
    try:
        # 請確保 config.ESP32_PARKING_IP 已在您的 config.py 中定義
        esp32_url = f'http://{config.ESP32_PARKING_IP}/update' # ESP32 端點
        params = {'plate': plate, 'status': payment_status_text}
        response = requests.get(esp32_url, params=params, timeout=5) # 新增超時
        if response.status_code == 200:
            print(f"[ESP32] 資料成功傳送: 車牌 {plate}, 狀態 {payment_status_text}")
        else:
            print(f"[ESP32錯誤] 傳送失敗: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[ESP32錯誤] 無法連接到 ESP32: {e}")
    except AttributeError:
        print("[設定錯誤] 請確認 config.py 中已設定 ESP32_PARKING_IP")
    except Exception as e:
        print(f"[ESP32錯誤] 傳送資料時發生未知錯誤: {e}")


# 函數 - 處理偵測到的車牌，檢查付款狀態並記錄
def handle_detected_plate(plate, timestamp, image_path):
    """檢查車牌的付款狀態並將資訊傳送給 ESP32。"""
    payment_status = "unpaid" # 預設為未付款

    # 從 PAID_VEHICLES 資料表檢查付款狀態
    try:
        cursor.execute('SELECT status FROM PAID_VEHICLES WHERE plate = ?', (plate,))
        result = cursor.fetchone()
        if result:
            payment_status = result[0]

        print(f"[處理車牌] 車牌: {plate}, 繳費狀態: {payment_status}")

        # 傳送資料到 ESP32
        send_to_esp32(plate, payment_status)

        # 記錄事件
        cursor.execute('''
            INSERT INTO PARKING_LOGS (plate, timestamp, payment_status, snapshot_path)
            VALUES (?, ?, ?, ?)
        ''', (plate, timestamp, payment_status, image_path))
        con.commit()
        print(f"[紀錄] 車牌: {plate}, 時間戳: {timestamp}, 狀態: {payment_status}, 照片: {image_path}")

    except sqlite3.Error as e:
        print(f"[資料庫錯誤] 處理車牌時發生錯誤: {e}")
    except Exception as e:
        print(f"[未知錯誤] 處理車牌時發生錯誤: {e}")


# --- 主程式 ---

# 變數 - 確保在每個偵測間隔只儲存一次照片
photo_saved_this_interval = False

# 自動建立照片資料夾
os.makedirs('./photo', exist_ok=True)

# ESP32 CAM URL
# 請確保 config.ESP32_CAM_IP 已在您的 config.py 中定義
cap = None # 初始化 cap
esp32_cam_url = "" # 初始化 esp32_cam_url
try:
    if not hasattr(config, 'ESP32_CAM_IP') or not config.ESP32_CAM_IP:
        print("[設定錯誤] ESP32_CAM_IP 未在 config.py 中設定或為空。程式可能無法正常運作。")
    else:
        esp32_cam_url = f'http://{config.ESP32_CAM_IP}/stream'
        cap = cv2.VideoCapture(esp32_cam_url)
        if not cap.isOpened():
            print(f"無法連接到 ESP32 CAM: {esp32_cam_url}。請檢查 IP 位址和攝影機串流。")
            cap = None # 確保 cap 為 None 如果開啟失敗
        else:
            print(f"[攝影機] 成功連接到 ESP32 CAM: {esp32_cam_url}")
except Exception as e:
    print(f"[攝影機初始化錯誤] 發生未知錯誤: {e}")
    cap = None


# 在開始時設定測試資料
if con: # 確保資料庫已連接
    setup_demo_paid_vehicles_table()


# 主迴圈
if cap and cap.isOpened():
    while True:
        current_datetime = datetime.datetime.now()
        timestamp = int(current_datetime.timestamp())

        ret, frame = cap.read()
        if not ret:
            print("[攝影機錯誤] 無法讀取影像串流，嘗試重新連接...")
            cap.release()
            time.sleep(5)
            if esp32_cam_url: # 確保 URL 存在
                cap = cv2.VideoCapture(esp32_cam_url)
                if not cap.isOpened():
                    print("重新連接失敗，程式即將結束。")
                    break
                else:
                    print("攝影機重新連接成功。")
                    continue
            else:
                print("ESP32 CAM URL 未定義，無法重新連接。程式即將結束。")
                break

        # 每10秒拍一張照片，並上傳到OCR服務
        if timestamp % 10 == 0 and not photo_saved_this_interval:
            print(f"[拍照] 準備於 {timestamp} 儲存圖片...")
            image_filename = f'./photo/{timestamp}.jpg'
            try:
                cv2.imwrite(image_filename, frame)
                photo_saved_this_interval = True
                print(f"[圖片儲存] 圖片已儲存至 {image_filename}")
            except Exception as e:
                print(f"[錯誤] 儲存圖片 {image_filename} 時發生錯誤: {e}")
                continue # 如果儲存失敗，跳過此週期的後續處理


            # 上傳至OCR服務
            try:
                if not hasattr(config, 'API_KEY') or not config.API_KEY:
                     print("[設定錯誤] API_KEY (Plate Recognizer) 未在 config.py 中設定或為空。")
                else:
                    # 【重要修改A】準備 Authorization 標頭，確保格式正確
                    auth_token_from_config = str(config.API_KEY).strip() # 轉換為字串並移除頭尾空格
                    
                    if not auth_token_from_config.lower().startswith('token '):
                        auth_token_for_header = f'Token {auth_token_from_config}'
                    else:
                        auth_token_for_header = auth_token_from_config
                    
                    # 【重要修改B】印出最終要使用的 Authorization 標頭值，方便除錯
                    print(f"[OCR 除錯] 最終 Authorization 標頭值: '{auth_token_for_header}'")

                    with open(image_filename, 'rb') as fp:
                        response = requests.post(
                            'https://api.platerecognizer.com/v1/plate-reader/',
                            headers={'Authorization': auth_token_for_header}, # 使用處理過的 auth_token_for_header
                            files={'upload': fp},
                            timeout=10
                        )

                    print(f"[OCR 除錯] HTTP 狀態碼: {response.status_code}")
                    response.raise_for_status() # 檢查是否有 HTTP 錯誤

                    ocr_data = response.json()
                    results = ocr_data.get('results', [])
                    print(f"[OCR 除錯] 完整 API 回應: {ocr_data}")

                    if not results:
                        print("[OCR] 未偵測到車牌。")
                    else:
                        for result in results:
                            plate = result.get('plate')
                            score = result.get('score', 0)
                            if plate and score >= 0.8:
                                print(f"[OCR成功] 偵測到車牌: {plate} (信心度: {score:.2f})")
                                handle_detected_plate(plate, timestamp, image_filename)
                            elif plate:
                                print(f"[OCR分數過低] 車牌: {plate} (信心度: {score:.2f})")
                            else:
                                print("[OCR結果異常] 未能從結果中提取車牌。")

            except requests.exceptions.HTTPError as http_err:
                print(f"[OCR HTTP錯誤] {http_err} - 回應內容: {response.text if 'response' in locals() and hasattr(response, 'text') else 'N/A'}")
            except Exception as e:
                print(f"[OCR錯誤] {e}")

        # 重置拍照檢測旗標
        elif timestamp % 10 != 0:
            if photo_saved_this_interval:
                pass
            photo_saved_this_interval = False

        time.sleep(0.05)

else:
    print("[主程式] 未能初始化攝影機或攝影機未開啟，程式結束。")

# 清理資源
if cap:
    cap.release()
if con:
    con.close()
print("[程式結束] 資源已釋放。")
