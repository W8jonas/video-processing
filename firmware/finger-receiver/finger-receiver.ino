#include <ESP8266WiFi.h>
#include <ArduinoOTA.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>
#include <stdarg.h>
#include "status_image.h"
#include "finger_protocol.h"
#include "finger_leds.h"

#if __has_include("leds_config.h")
#include "leds_config.h"
#else
#include "leds_config.example.h"
#endif

#if __has_include("secrets.h")
#include "secrets.h"
#else
#include "secrets.example.h"
#endif

constexpr char kVersion[] = "WIFI OTA HTTP DEDOS LED V5";
constexpr uint32_t kFingerLeaseMs = 2500;
uint8_t fingerMask = 0;
uint8_t fingerHand = 0;
bool fingerTracking = false;
bool fingerReceived = false;
bool fingerExpired = false;
uint32_t fingerSequence = 0;
uint32_t fingerUpdatedMs = 0;
constexpr uint32_t kRetryMs = 30000;
constexpr uint32_t kStatusMs = 30000;
constexpr uint32_t kLedPulseMs = 10;
constexpr uint16_t kOtaPort = 8266;
constexpr uint8_t kIrTxPin = D6;  // Saída experimental IR mantida inativa.
bool configured = false;
bool otaStarted = false;
bool ledActive = false;
uint32_t lastAttemptMs = 0;
uint32_t lastStatusMs = 0;
uint32_t ledStartedMs = 0;
IPAddress serviceIp;
int lastProgress = -1;
ESP8266WebServer http(80);
bool httpStarted = false;

void writeFingerLeds() {
  fingers::applyLeds(fingerMask, fingerTracking, kFingerLedsEnabled,
                    kFingerLedPins, [](uint8_t pin, uint8_t level) {
                      digitalWrite(pin, level ? HIGH : LOW);
                    });
}

void releaseFingers() {
  fingerMask = 0;
  fingerHand = 0;
  fingerTracking = false;
  fingerExpired = true;
  writeFingerLeds();
}

void expireFingers() {
  if (fingerReceived && !fingerExpired && millis() - fingerUpdatedMs >= kFingerLeaseMs) {
    const bool wasTracking = fingerTracking;
    releaseFingers();
    if (wasTracking) uartLog("FINGERS EXPIRED | mask=0 | tracking=0");
  }
}

void sendFingerState() {
  expireFingers();
  String ids;
  for (uint8_t id = 1; id <= 4; ++id) {
    if (fingerMask & (1 << (id - 1))) {
      if (ids.length()) ids += ',';
      ids += id;
    }
  }
  char levels[32];
  if (kFingerLedsEnabled) {
    snprintf(levels, sizeof(levels), "[%u,%u,%u,%u]",
             digitalRead(kFingerLedPins[0]) ? 1 : 0, digitalRead(kFingerLedPins[1]) ? 1 : 0,
             digitalRead(kFingerLedPins[2]) ? 1 : 0, digitalRead(kFingerLedPins[3]) ? 1 : 0);
  } else {
    snprintf(levels, sizeof(levels), "null");
  }
  char json[512];
  snprintf(json, sizeof(json),
           "{\"ok\":true,\"mascara\":%u,\"dedos\":[%s],\"sequencia\":%lu,\"rastreando\":%s,"
           "\"mao\":\"%s\",\"recebido\":%s,\"expirado\":%s,\"idade_ms\":%lu,\"lease_ms\":%lu,"
           "\"leds_habilitados\":%s,\"gpio_leds\":[%u,%u,%u,%u],\"niveis_gpio\":%s}",
           fingerMask, ids.c_str(), static_cast<unsigned long>(fingerSequence),
           fingerTracking ? "true" : "false", fingers::handName(fingerHand),
           fingerReceived ? "true" : "false", fingerExpired ? "true" : "false",
           static_cast<unsigned long>(fingerReceived ? millis() - fingerUpdatedMs : 0),
           static_cast<unsigned long>(kFingerLeaseMs), kFingerLedsEnabled ? "true" : "false",
           kFingerLedPins[0], kFingerLedPins[1], kFingerLedPins[2], kFingerLedPins[3], levels);
  http.sendHeader("Cache-Control", "no-store");
  http.send(200, "application/json", json);
}

bool singleFingerArg(const char* name) {
  int count = 0;
  for (int i = 0; i < http.args(); ++i) {
    if (http.argName(i) == name) ++count;
  }
  return count == 1;
}

void receiveFingers() {
  uint32_t mask = 0, sequence = 0, tracking = 0;
  const uint8_t hand = fingers::handCode(http.arg("mao").c_str());
  if (http.args() != 4 || !singleFingerArg("mascara") || !singleFingerArg("sequencia") ||
      !singleFingerArg("rastreando") || !singleFingerArg("mao") ||
      !fingers::parseUnsigned(http.arg("mascara").c_str(), 15, mask) ||
      !fingers::parseUnsigned(http.arg("sequencia").c_str(), UINT32_MAX, sequence) ||
      !fingers::parseUnsigned(http.arg("rastreando").c_str(), 1, tracking) ||
      !fingers::validState(mask, tracking, hand)) {
    http.send(400, "application/json", "{\"ok\":false,\"erro\":\"estado_de_dedos_invalido\"}");
    return;
  }
  const bool changed = mask != fingerMask || static_cast<bool>(tracking) != fingerTracking || hand != fingerHand;
  fingerMask = mask;
  fingerSequence = sequence;
  fingerTracking = tracking;
  fingerHand = hand;
  fingerUpdatedMs = millis();
  fingerReceived = true;
  fingerExpired = false;
  writeFingerLeds();
  if (changed) uartLog("FINGERS RECEIVED | seq=%lu | mask=%u | tracking=%u | hand=%s",
                       static_cast<unsigned long>(sequence), fingerMask, fingerTracking,
                       fingers::handName(fingerHand));
  sendFingerState();
}

void configureHttp() {
  const auto image = []() {
    http.sendHeader("Cache-Control", "no-cache");
    http.send_P(200, PSTR("image/svg+xml; charset=utf-8"), kStatusImage);
    uartLog("HTTP GET | resource=image | status=200");
  };
  http.on("/", HTTP_GET, image);
  http.on("/imagem.svg", HTTP_GET, image);
  http.on("/health", HTTP_GET, []() {
    char json[384];
    snprintf(json, sizeof(json),
             "{\"firmware\":\"%s\",\"uptime_ms\":%lu,\"ip\":\"%s\",\"rssi_dbm\":%d,\"ota\":%s,"
             "\"finger_api\":1,\"finger_lease_ms\":%lu,\"finger_leds_enabled\":%s}",
             kVersion, millis(), WiFi.localIP().toString().c_str(),
             WiFi.RSSI(), otaStarted ? "true" : "false", static_cast<unsigned long>(kFingerLeaseMs),
             kFingerLedsEnabled ? "true" : "false");
    http.sendHeader("Cache-Control", "no-store");
    http.send(200, "application/json", json);
    uartLog("HTTP GET | resource=health | status=200");
  });
  http.on("/dedos", HTTP_GET, sendFingerState);
  http.on("/dedos", HTTP_POST, receiveFingers);
  http.onNotFound([]() {
    http.send(404, "text/plain; charset=utf-8", "Nao encontrado\n");
    uartLog("HTTP REQUEST | status=404");
  });
}

void startHttp() {
  if (!httpStarted) {
    http.begin();
    httpStarted = true;
    uartLog("HTTP STARTED | port=80 | image=/ | health=/health");
  }
}

void updateLed() {
  if (ledActive && millis() - ledStartedMs >= kLedPulseMs) {
    digitalWrite(LED_BUILTIN, HIGH);
    ledActive = false;
  }
}

void uartLog(const char* format, ...) {
  char line[256];
  va_list args;
  va_start(args, format);
  vsnprintf(line, sizeof(line), format, args);
  va_end(args);
  Serial.println(line);
  digitalWrite(LED_BUILTIN, LOW);
  ledStartedMs = millis();
  ledActive = true;
}

void printStatus() {
  const bool connected = configured && WiFi.status() == WL_CONNECTED;
  uartLog("NET STATUS | version=%s | uptime_ms=%lu | wifi=%s | ip=%s | rssi_dbm=%d | ota=%s | free_ota_bytes=%lu",
          kVersion, millis(), connected ? "CONNECTED" : "DISCONNECTED",
          connected ? WiFi.localIP().toString().c_str() : "0.0.0.0",
          connected ? WiFi.RSSI() : 0, otaStarted ? "STARTED" : "STOPPED",
          static_cast<unsigned long>(ESP.getFreeSketchSpace()));
}

void connectWifi() {
  lastAttemptMs = millis();
  WiFi.begin(settings::WIFI_SSID, settings::WIFI_PASSWORD);
  uartLog("NET CONNECTING | hostname=%s | retry_ms=%lu",
          settings::HOSTNAME, static_cast<unsigned long>(kRetryMs));
}

void configureOta() {
  ArduinoOTA.setHostname(settings::HOSTNAME);
  ArduinoOTA.setPort(kOtaPort);
  ArduinoOTA.setPassword(settings::OTA_PASSWORD);
  ArduinoOTA.onStart([]() {
    releaseFingers();
    digitalWrite(kIrTxPin, LOW);
    http.close();
    httpStarted = false;
    lastProgress = -1;
    uartLog("OTA START | type=%s", ArduinoOTA.getCommand() == U_FLASH ? "firmware" : "filesystem");
  });
  ArduinoOTA.onProgress([](unsigned int done, unsigned int total) {
    updateLed();
    const int percent = total ? (static_cast<uint64_t>(done) * 100 / total) : 0;
    if (lastProgress < 0 || percent >= lastProgress + 10 ||
        (percent == 100 && lastProgress != 100)) {
      lastProgress = percent;
      uartLog("OTA PROGRESS | percent=%d", percent);
    }
  });
  ArduinoOTA.onEnd([]() {
    uartLog("OTA END | result=OK | reboot=1");
    // O core reinicia antes de voltar ao loop; concluir pulso e UART aqui.
    Serial.flush();
    while (ledActive) { updateLed(); delay(1); }
  });
  ArduinoOTA.onError([](ota_error_t error) {
    const char* reason = "UNKNOWN";
    switch (error) {
      case OTA_AUTH_ERROR: reason = "AUTH"; break;
      case OTA_BEGIN_ERROR: reason = "BEGIN"; break;
      case OTA_CONNECT_ERROR: reason = "CONNECT"; break;
      case OTA_RECEIVE_ERROR: reason = "RECEIVE"; break;
      case OTA_END_ERROR: reason = "END"; break;
    }
    uartLog("OTA ERROR | code=%u | reason=%s", static_cast<unsigned>(error), reason);
    if (WiFi.status() == WL_CONNECTED) startHttp();
  });
}

void setup() {
  if (kFingerLedsEnabled) {
    for (uint8_t pin : kFingerLedPins) {
      digitalWrite(pin, LOW);
      pinMode(pin, OUTPUT);
    }
  }
  digitalWrite(LED_BUILTIN, HIGH);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(kIrTxPin, LOW);
  pinMode(kIrTxPin, OUTPUT);
  Serial.begin(115200);
  uartLog("SMARTHOME %s | hostname=%s | UART=115200 | IR_TX=OFF",
          kVersion, settings::HOSTNAME);
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  configured = settings::WIFI_SSID[0] && settings::OTA_PASSWORD[0] &&
               settings::HOSTNAME[0];
  if (!configured) {
    WiFi.mode(WIFI_OFF);
    uartLog("NET CONFIG_REQUIRED | fill=secrets.h | required=WIFI_SSID,OTA_PASSWORD,HOSTNAME");
    return;
  }
  WiFi.hostname(settings::HOSTNAME);
  WiFi.setAutoReconnect(true);
  configureOta();
  configureHttp();
  connectWifi();
}

void loop() {
  updateLed();
  expireFingers();
  const uint32_t now = millis();
  if (configured) {
    const bool connected = WiFi.status() == WL_CONNECTED;
    if (otaStarted && (!connected || WiFi.localIP() != serviceIp)) {
      releaseFingers();
      http.close();
      httpStarted = false;
      ArduinoOTA.end();
      otaStarted = false;
      uartLog("OTA STOP | reason=NETWORK_CHANGED");
    }
    if (connected) {
      if (!otaStarted) {
        serviceIp = WiFi.localIP();
        ArduinoOTA.begin();  // Anuncia hostname.local e serviço _arduino._tcp.
        MDNS.addService("http", "tcp", 80);
        otaStarted = true;
        startHttp();
        uartLog("NET CONNECTED | ip=%s | mac=%s | rssi_dbm=%d",
                serviceIp.toString().c_str(), WiFi.macAddress().c_str(), WiFi.RSSI());
        uartLog("OTA STARTED | hostname=%s.local | port=%u | auth=REQUIRED",
                settings::HOSTNAME, kOtaPort);
        printStatus();
      }
      ArduinoOTA.handle();
      if (httpStarted) http.handleClient();
    } else if (now - lastAttemptMs >= kRetryMs) {
      // Sem loop bloqueante nem reboot em caso de rede indisponível.
      WiFi.disconnect(false);
      connectWifi();
    }
  }
  while (Serial.available()) {
    const char key = Serial.read();
    if (key == '?') {
      uartLog("ACK %s | RX OK", kVersion);
      printStatus();
    }
  }
  if (now - lastStatusMs >= kStatusMs) {
    lastStatusMs = now;
    printStatus();
  }
  delay(1);
}
