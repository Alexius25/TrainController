
import serial
import time


class ArduinoController:

    def __init__(self, port="/dev/ttyUSB0", baudrate=9600):
        self.port = port
        self.baudrate = baudrate

        self.serial = None

        self._pot1 = 0
        self._pot2 = 0
        self._pot3 = 0

        self._btn1 = False
        self._btn2 = False
        self._btn3 = False

    def connect(self):
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )

            time.sleep(2)
            self.serial.reset_input_buffer()

            print("[Arduino] Verbunden!")
            return True

        except serial.SerialException as error:
            print(f"[Arduino] Verbindung fehlgeschlagen: {error}")
            self.serial = None
            return False

    def disconnect(self):
        if self.is_connected():
            self.serial.close()

        self.serial = None
        print("[Arduino] Getrennt.")

    def is_connected(self):
        return self.serial is not None and self.serial.is_open

    def update(self):
        if not self.is_connected():
            return False

        try:
            line = self.serial.readline().decode(
                "utf-8",
                errors="replace"
            ).strip()

            if not line:
                return False

            values = line.split(",")

            if len(values) != 6:
                return False

            pot1, pot2, pot3, btn1, btn2, btn3 = map(int, values)

            if not all(
                0 <= value <= 1023
                for value in (pot1, pot2, pot3)
            ):
                return False

            if any(
                btn not in (0, 1)
                for btn in (btn1, btn2, btn3)
            ):
                return False

            self._pot1 = pot1
            self._pot2 = pot2
            self._pot3 = pot3

            self._btn1 = bool(btn1)
            self._btn2 = bool(btn2)
            self._btn3 = bool(btn3)

            return True

        except serial.SerialException as error:
            print(f"[Arduino] Lesefehler: {error}")
            self.disconnect()
            return False

        except (ValueError, UnicodeError):
            return False

    @property
    def pot1(self):
        return self._pot1

    @property
    def pot2(self):
        return self._pot2

    @property
    def pot3(self):
        return self._pot3

    @property
    def btn1(self):
        return self._btn1

    @property
    def btn2(self):
        return self._btn2

    @property
    def btn3(self):
        return self._btn3
