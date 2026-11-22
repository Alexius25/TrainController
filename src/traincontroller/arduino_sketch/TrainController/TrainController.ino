
const int pot1 = A0;
const int pot2 = A1;
const int pot3 = A2;

const int button1 = 2;
const int button2 = 3;
const int button3 = 4;

void setup() {
    Serial.begin(9600);

    pinMode(button1, INPUT_PULLUP);
    pinMode(button2, INPUT_PULLUP);
    pinMode(button3, INPUT_PULLUP);
}

void loop() {
    // Potentiometer lesen
    int value1 = analogRead(pot1);
    int value2 = analogRead(pot2);
    int value3 = analogRead(pot3);

    // Buttons lesen
    int btn1 = !digitalRead(button1);
    int btn2 = !digitalRead(button2);
    int btn3 = !digitalRead(button3);

    // CSV-Ausgabe: eine vollständige Zeile
    Serial.print(value1);
    Serial.print(",");
    Serial.print(value2);
    Serial.print(",");
    Serial.print(value3);
    Serial.print(",");
    Serial.print(btn1);
    Serial.print(",");
    Serial.print(btn2);
    Serial.print(",");
    Serial.println(btn3);

    delay(50);
}
