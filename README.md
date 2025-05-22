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
