#include <WiFi.h>
#include <WiFiManager.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);
WiFiManager wm;

// WiFi重置掃描相關
unsigned long lastWifiScan = 0;
const unsigned long wifiScanInterval = 10000;

// HTTP 參數名稱
const char* PARAM_PLATE = "plate";
const char* PARAM_STATUS = "status";

AsyncWebServer server(80);

// LCD顯示超時清除的全域變數
unsigned long lastPlateDisplayTime = 0;
bool plateCurrentlyDisplayed = false;
const unsigned long plateDisplayTimeout = 3000; // 車牌/GPIO 狀態顯示的持續時間 (3 秒)

// 【新增】定義 GPIO 引腳
const int PAID_GPIO_PIN = 18;    // 已繳費指示燈的 GPIO 引腳
const int UNPAID_GPIO_PIN = 19;  // 未繳費指示燈的 GPIO 引腳

const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE HTML><html>
<head><title>ESP32 Parking Status</title></head>
<body>
  <h1>Parking Status Receiver</h1>
  <p>ESP32 is waiting for parking updates.</p>
</body></html>
)rawliteral";

void displayDefaultScreen() {
    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print("System Ready");
    lcd.setCursor(0,1);
    lcd.print("Waiting forCar");
}

void setup(){
  Serial.begin(115200);

  Wire.begin(21, 22); // 請確認您的 LCD I2C 引腳是否與其他功能衝突
  lcd.init();
  lcd.backlight();
  lcd.clear();

  // 【新增】初始化 GPIO 引腳
  pinMode(PAID_GPIO_PIN, OUTPUT);
  pinMode(UNPAID_GPIO_PIN, OUTPUT);
  digitalWrite(PAID_GPIO_PIN, LOW);    // 初始狀態設為 LOW
  digitalWrite(UNPAID_GPIO_PIN, LOW);  // 初始狀態設為 LOW
  Serial.println("GPIO pins initialized.");

  lcd.setCursor(0, 0);
  lcd.print("WiFi Connecting...");

  bool res = wm.autoConnect("ESP32-ParkingSetup");

  if (!res) {
    Serial.println("WiFi 連線失敗...");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Setup Mode");
    lcd.setCursor(0, 1);
    lcd.print("Or Restarting...");
    delay(5000);
  } else {
    Serial.println("WiFi 已連線！");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("IP Address:");
    lcd.setCursor(0, 1);
    lcd.print(WiFi.localIP());
    delay(10000); // 顯示 IP 10 秒
  }

  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send(200, "text/html", index_html);
  });

  server.on("/update", HTTP_GET, [] (AsyncWebServerRequest *request) {
    String plateValue = "N/A";
    String statusValue = "N/A";

    bool plateParamExists = request->hasParam(PARAM_PLATE);
    bool statusParamExists = request->hasParam(PARAM_STATUS);

    if (plateParamExists) {
      plateValue = request->getParam(PARAM_PLATE)->value();
      Serial.print("Received Plate: "); Serial.println(plateValue);
    } else {
      Serial.println("Parameter 'plate' not received.");
    }

    if (statusParamExists) {
      statusValue = request->getParam(PARAM_STATUS)->value();
      Serial.print("Received Status: "); Serial.println(statusValue);
    } else {
      Serial.println("Parameter 'status' not received.");
    }

    // 【修改】在處理新狀態前，先將兩個 GPIO 都設為 LOW
    digitalWrite(PAID_GPIO_PIN, LOW);
    digitalWrite(UNPAID_GPIO_PIN, LOW);
    Serial.println("GPIOs set to LOW before processing new status.");

    lcd.clear(); // 每次收到新請求都先清除
    lcd.setCursor(0, 0);

    String plateDisplay = "Plate:" + plateValue;
    if (plateDisplay.length() > 16) {
        plateDisplay = plateDisplay.substring(0, 15) + ".";
    }
    lcd.print(plateDisplay);

    lcd.setCursor(0, 1);
    if (statusValue == "paid") {
      lcd.print("Status: Paid   ");
      digitalWrite(PAID_GPIO_PIN, HIGH); // 【新增】「已繳費」GPIO 設為 HIGH
      Serial.println("PAID_GPIO_PIN set to HIGH.");
    } else if (statusValue == "unpaid") {
      lcd.print("Status: Unpaid ");
      digitalWrite(UNPAID_GPIO_PIN, HIGH); // 【新增】「未繳費」GPIO 設為 HIGH
      Serial.println("UNPAID_GPIO_PIN set to HIGH.");
    } else if (plateParamExists || statusParamExists) {
      lcd.print("Status: Unknown");
    } else {
      displayDefaultScreen();
    }

    // 如果成功顯示了車牌/狀態，設定超時計時器
    if (plateParamExists || statusParamExists) {
        lastPlateDisplayTime = millis();
        plateCurrentlyDisplayed = true;
        Serial.println("Plate info displayed, LCD/GPIO timeout started.");
    }
    
    request->send(200, "text/plain", "OK");
  });
  
  server.begin();
  Serial.println("HTTP server started");

  if (WiFi.isConnected()){
    displayDefaultScreen(); // 顯示初始等待畫面
  } else {
    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print("WiFi Not Conn.");
    lcd.setCursor(0,1);
    lcd.print("Check Setup");
  }
}
  
void loop() {
  // WiFi 重置邏輯
  if (millis() - lastWifiScan > wifiScanInterval) {
    lastWifiScan = millis();
    Serial.println("Scanning for wifi_reset network...");
    int n = WiFi.scanNetworks(false, true);
    bool foundResetSSID = false;
    for (int i = 0; i < n; i++) {
      if (WiFi.SSID(i) == "wifi_reset") {
        Serial.println("Found 'wifi_reset' SSID. Resetting Wi-Fi settings...");
        wm.resetSettings();
        delay(1000);
        ESP.restart();
        foundResetSSID = true;
        break;
      }
    }
    if (!foundResetSSID) {
        Serial.println("No 'wifi_reset' network found in this scan.");
    }
    WiFi.scanDelete();
  }

  // 車牌顯示/GPIO HIGH 狀態超時清除邏輯
  if (plateCurrentlyDisplayed && (millis() - lastPlateDisplayTime >= plateDisplayTimeout)) {
    Serial.println("Plate display/GPIO timeout. Clearing LCD and setting GPIOs to LOW.");
    displayDefaultScreen(); // 清除並顯示預設等待畫面
    
    // 【新增】將兩個 GPIO 都設為 LOW
    digitalWrite(PAID_GPIO_PIN, LOW);
    digitalWrite(UNPAID_GPIO_PIN, LOW);
    Serial.println("PAID_GPIO_PIN and UNPAID_GPIO_PIN set to LOW due to timeout.");

    plateCurrentlyDisplayed = false; // 重置標記，等待下一次車牌訊息
  }
}
