/*
 * BuddAI Complex Test Sketch
 * Purpose: Verify .ino detection in frontend
 */

#include <Arduino.h>

// Configuration
const int LED_PIN = 2;
const int SENSOR_PIN = 34;
const unsigned long INTERVAL = 1000;

// State Machine
enum State {
  IDLE,
  ACTIVE,
  ERROR
};

State currentState = IDLE;
unsigned long previousMillis = 0;

// Function Prototypes
void updateState();
void handleSensors();

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(SENSOR_PIN, INPUT);
  
  Serial.println("BuddAI System Initialized");
  Serial.println("Waiting for input...");
}

void loop() {
  unsigned long currentMillis = millis();

  // Non-blocking timer
  if (currentMillis - previousMillis >= INTERVAL) {
    previousMillis = currentMillis;
    updateState();
  }

  handleSensors();
}

void updateState() {
  switch (currentState) {
    case IDLE:
      digitalWrite(LED_PIN, LOW);
      Serial.println("State: IDLE");
      currentState = ACTIVE;
      break;
      
    case ACTIVE:
      digitalWrite(LED_PIN, HIGH);
      Serial.println("State: ACTIVE");
      // Simulate work
      currentState = IDLE;
      break;
      
    case ERROR:
      digitalWrite(LED_PIN, HIGH);
      delay(100);
      digitalWrite(LED_PIN, LOW);
      delay(100);
      break;
  }
}

void handleSensors() {
  int reading = analogRead(SENSOR_PIN);
  if (reading > 4000) {
    currentState = ERROR;
    Serial.println("Alert: Sensor Overload!");
  }
}