
from traincontroller.hardware.arduino import ArduinoController
from tsw_api import TSW7
import time


# ==========================================
# KONFIGURATION
# ==========================================

API_KEY = "RGLIAJ2QpNU8V8mQzpYv8XXiRk5y0bICnQYRgWtcTXc="
# Poti 1: MasterController
POWER_POT_MIN = 0
POWER_POT_MAX = 1023
POWER_POT_CENTER = 512
POWER_DEADZONE = 25

# Poti 2: Zugbremse
BRAKE_POT_MIN = 0
BRAKE_POT_MAX = 1023
BRAKE_DEADZONE = 15

# Glättung
ALPHA_POWER = 0.3
ALPHA_BRAKE = 0.15

UPDATE_INTERVAL = 0.02
CHANGE_THRESHOLD = 0.005


# ==========================================
# INITIALISIERUNG
# ==========================================

arduino = ArduinoController()
tsw = TSW7(API_KEY)

filtered_power = None
filtered_brake = None

last_horn_state = False
last_horn_low_state = False


# ==========================================
# EMA GLÄTTUNG
# ==========================================

def smooth_value(value, previous, alpha):

    if previous is None:
        return float(value)

    return alpha * value + (1 - alpha) * previous


# ==========================================
# MASTERCONTROLLER
# ==========================================

def map_power(value):

    value = max(POWER_POT_MIN, min(POWER_POT_MAX, value))

    difference = value - POWER_POT_CENTER

    if abs(difference) <= POWER_DEADZONE:
        return 0.0

    if difference > 0:
        result = (difference - POWER_DEADZONE) / (
            POWER_POT_MAX - POWER_POT_CENTER - POWER_DEADZONE
        )
    else:
        result = (difference + POWER_DEADZONE) / (
            POWER_POT_CENTER - POWER_POT_MIN - POWER_DEADZONE
        )

    return max(-1.0, min(1.0, result))


# ==========================================
# ZUGBREMSE
# ==========================================

def map_brake(value, minimum, maximum):

    value = max(BRAKE_POT_MIN, min(BRAKE_POT_MAX, value))

    normalized = (
        (value - BRAKE_POT_MIN)
        / (BRAKE_POT_MAX - BRAKE_POT_MIN)
    )

    if normalized <= BRAKE_DEADZONE / (
        BRAKE_POT_MAX - BRAKE_POT_MIN
    ):
        return minimum

    return minimum + normalized * (maximum - minimum)


def quantize_brake(value, minimum, maximum, notch_count):
    """
    Rundet den Bremswert auf die verfügbaren Bremsstufen.
    """

    if notch_count <= 1:
        return minimum

    intervals = notch_count - 1

    normalized = (value - minimum) / (maximum - minimum)
    normalized = max(0.0, min(1.0, normalized))

    notch = round(normalized * intervals)

    quantized = minimum + (
        notch / intervals
    ) * (maximum - minimum)

    return round(quantized, 4)


# ==========================================
# HORN
# ==========================================

def update_horn(active):
    """
    Schaltet das Horn nur bei einer Zustandsänderung.

    True  = Horn einschalten
    False = Horn ausschalten
    """

    global last_horn_state

    if active == last_horn_state:
        return

    tsw.horn(active)

    last_horn_state = active

    if active:
        print("[Horn] Eingeschaltet!")
    else:
        print("[Horn] Ausgeschaltet!")

def update_horn_low(active):
    """
    Schaltet das Horn Low nur bei einer Zustandsänderung.

    True  = Horn einschalten
    False = Horn ausschalten
    """

    global last_horn_low_state

    if active == last_horn_low_state:
        return

    tsw.horn_low(active)

    last_horn_low_state = active

    if active:
        print("[Horn] Eingeschaltet!")
    else:
        print("[Horn] Ausgeschaltet!")


# ==========================================
# HAUPTPROGRAMM
# ==========================================

power_min = -1.0
power_max = 1.0

if arduino.connect():

    print("[Arduino] Verbunden!")

    tsw.debug_node("DriverInput")
    tsw.debug_node("DriverInput/MasterController_F")
    tsw.debug_node("DriverInput/Horn_F")

    try:
        print("[TSW7] Verbinde...")

        # Wertebereiche auslesen
        power_info = tsw.get_power_info()
        brake_info = tsw.get_brake_info()

        power_min = float(power_info["minimum"])
        power_max = float(power_info["maximum"])

        brake_min = float(brake_info["minimum"])
        brake_max = float(brake_info["maximum"])

        # Bremsstufen auslesen
        brake_notch_count = int(brake_info["notch_count"])

        print(f"[TSW7] Power: {power_min} bis {power_max}")
        print(f"[TSW7] Brake: {brake_min} bis {brake_max}")
        print(f"[TSW7] Bremsstufen: {brake_notch_count}")

        if brake_notch_count > 1:
            print("[TSW7] Quantisierung aktiviert!")
        else:
            print("[TSW7] Keine diskreten Bremsstufen erkannt!")

        print("[System] Steuerung aktiv!")

        last_power = None
        last_brake = None

        while True:

            if arduino.update():

                # ==================================
                # POTI 1: GESCHWINDIGKEIT
                # ==================================

                raw_power = arduino.pot1

                filtered_power = smooth_value(
                    raw_power,
                    filtered_power,
                    ALPHA_POWER
                )

                power = map_power(filtered_power)

                # ==================================
                # POTI 2: ZUGBREMSE
                # ==================================

                raw_brake = arduino.pot2

                filtered_brake = smooth_value(
                    raw_brake,
                    filtered_brake,
                    ALPHA_BRAKE
                )

                brake = map_brake(
                    filtered_brake,
                    brake_min,
                    brake_max
                )

                brake = quantize_brake(
                    brake,
                    brake_min,
                    brake_max,
                    brake_notch_count
                )

                # ==================================
                # TSW: POWER
                # ==================================

                if (
                    last_power is None
                    or abs(power - last_power) >= CHANGE_THRESHOLD
                ):

                    tsw.set_power(
                        power,
                        power_min,
                        power_max
                    )

                    last_power = power

                # ==================================
                # TSW: BRAKE
                # ==================================

                if (
                    last_brake is None
                    or brake != last_brake
                ):

                    tsw.set_brake(
                        brake,
                        brake_min,
                        brake_max
                    )

                    last_brake = brake

                # ==================================
                # BTN1: HORN
                # ==================================

                update_horn(bool(arduino.btn1))
                update_horn_low(bool(arduino.btn2))

                # ==================================
                # DEBUG
                # ==================================

                print(
                    f"Poti1={arduino.pot1} | "
                    f"Poti2={arduino.pot2} | "
                    f"Button1={arduino.btn1} | "
                    f"[Power] {raw_power:4.0f} -> {power:+.3f} | "
                    f"[Brake] {raw_brake:4.0f} -> {brake:.3f}"
                )

            time.sleep(UPDATE_INTERVAL)

    except KeyboardInterrupt:
        print("\n[System] Beende Steuerung...")

    except Exception as e:
        print(f"[Fehler] {e}")

    finally:

        # Horn immer ausschalten
        try:
            tsw.horn(False)
            print("[TSW7] Horn ausgeschaltet.")
        except Exception as e:
            print(f"[TSW7] Horn konnte nicht ausgeschaltet werden: {e}")

        # Leistung zurücksetzen
        try:
            tsw.set_power(0, power_min, power_max)
            print("[TSW7] Power zurückgesetzt.")
        except Exception:
            pass

        print("[TSW7] Bremsstellung bleibt erhalten.")

        arduino.disconnect()
        tsw.close()

        print("[System] Verbindungen geschlossen.")
