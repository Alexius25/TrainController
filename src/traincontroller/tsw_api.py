
import requests
from urllib.parse import quote


class TSW7:
    def __init__(self, api_key, host="localhost", port=31270, timeout=5):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({
            "DTGCommKey": api_key
        })

    # ---------------------------------------------------------
    # HTTP / API
    # ---------------------------------------------------------

    def _request(self, method, endpoint, **kwargs):
        url = f"{self.base_url}/{endpoint}"

        response = self.session.request(
            method,
            url,
            timeout=self.timeout,
            **kwargs
        )

        response.raise_for_status()

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            return response.text

        if isinstance(data, dict):
            if data.get("Result") == "Error":
                raise RuntimeError(f"TSW API Error: {data}")

            if "errorCode" in data:
                raise RuntimeError(f"TSW HTTP Error: {data}")

        return data

    def debug_node(self, node):
        print(f"\n{'=' * 50}")
        print(f"NODE: {node}")
        print(f"{'=' * 50}")

        try:
            data = self.list(node)

            print("\n[RAW NODE DATA]")
            print(data)

            print("\n[ENDPOINTS]")

            for endpoint in data.get("Endpoints", []):
                print(
                    f"  - {endpoint.get('Name')}"
                    f" | Writable: {endpoint.get('Writable')}"
                )

            print("\n[CHILD NODES]")

            for child in data.get("Nodes", []):
                print(f"  - {child.get('Name')}")

        except Exception as e:
            print(f"[ERROR] {e}")

    # ---------------------------------------------------------
    # Nodes
    # ---------------------------------------------------------

    def list(self, node=None):
        if node is None:
            return self._request("GET", "list")

        node = quote(node, safe="/")
        return self._request("GET", f"list/{node}")

    def list_recursive(self, node=None, max_depth=20):
        result = self.list(node)

        if not isinstance(result, dict):
            return result

        if result.get("Result") != "Success":
            return result

        if node is None or max_depth <= 0:
            return result

        children = []

        for child in result.get("Nodes", []):
            name = child["Name"]
            path = f"{node}/{name}"

            children.append(
                self.list_recursive(path, max_depth - 1)
            )

        result["Children"] = children
        return result

    def get_nodes(self, node=None):
        data = self.list(node)
        return [item["Name"] for item in data.get("Nodes", [])]

    def get_endpoints(self, node):
        data = self.list(node)
        return data.get("Endpoints", [])

    def get_writable_endpoints(self, node):
        return [
            endpoint["Name"]
            for endpoint in self.get_endpoints(node)
            if endpoint["Writable"]
        ]

    def get_readonly_endpoints(self, node):
        return [
            endpoint["Name"]
            for endpoint in self.get_endpoints(node)
            if not endpoint["Writable"]
        ]

    # ---------------------------------------------------------
    # Get / Set
    # ---------------------------------------------------------

    def get(self, node, endpoint):
        node = quote(node, safe="/")
        endpoint = quote(endpoint, safe="")

        data = self._request(
            "GET",
            f"get/{node}.{endpoint}"
        )

        return data.get("Values", {})

    def get_raw(self, node, endpoint):
        node = quote(node, safe="/")
        endpoint = quote(endpoint, safe="")

        return self._request(
            "GET",
            f"get/{node}.{endpoint}"
        )

    def set(self, node, endpoint, value):
        node = quote(node, safe="/")
        endpoint = quote(endpoint, safe="")

        return self._request(
            "PATCH",
            f"set/{node}.{endpoint}",
            params={"Value": value}
        )

    def get_value(self, node, endpoint):
        data = self.get(node, endpoint)
        return data.get(endpoint)

    # ---------------------------------------------------------
    # General Input Utilities
    # ---------------------------------------------------------

    def get_input(self, node):
        return self.get_value(node, "InputValue")

    def set_input(self, node, value, minimum=None, maximum=None):
        value = float(value)

        if minimum is not None and value < minimum:
            raise ValueError(
                f"Wert muss mindestens {minimum} sein."
            )

        if maximum is not None and value > maximum:
            raise ValueError(
                f"Wert darf maximal {maximum} sein."
            )

        return self.set(node, "InputValue", value)

    def get_input_info(self, node):
        return {
            "value": self.get_input(node),

            "notch_count": self.get(
                node, "Function.GetNotchCount"
            ).get("ReturnValue"),

            "minimum": self.get(
                node, "Function.GetMinimumInputValue"
            ).get("ReturnValue"),

            "maximum": self.get(
                node, "Function.GetMaximumInputValue"
            ).get("ReturnValue"),

            "default": self.get(
                node, "Function.GetDefaultInputValue"
            ).get("ReturnValue"),

            "current_notch": self.get(
                node, "Function.GetCurrentNotchIndex"
            ).get("ReturnValue"),

            "normalised_input": self.get(
                node, "Function.GetNormalisedInputValue"
            ).get("ReturnValue"),

            "normalised_output": self.get(
                node, "Function.GetNormalisedOutputValue"
            ).get("ReturnValue")
        }

    def interact(self, node, interacting=True):
        return self.set(
            node,
            "Interacting",
            1 if interacting else 0
        )

    # ---------------------------------------------------------
    # Subscriptions
    # ---------------------------------------------------------

    def create_subscription(self, subscription_id, path=None):
        params = {"Subscription": subscription_id}

        if path is not None:
            params["path"] = path

        return self._request(
            "POST",
            "subscription",
            params=params
        )

    def get_subscription(self, subscription_id):
        return self._request(
            "GET",
            "subscription",
            params={"Subscription": subscription_id}
        )

    # ---------------------------------------------------------
    # Master Controller
    # ---------------------------------------------------------

    MASTER_CONTROLLER = "DriverInput/MasterController_F"

    def set_power(self, value, minimum=-1.0, maximum=1.0):
        return self.set_input(
            self.MASTER_CONTROLLER,
            value,
            minimum,
            maximum
        )

    def get_power(self):
        return self.get_input(self.MASTER_CONTROLLER)

    def get_power_info(self):
        return self.get_input_info(self.MASTER_CONTROLLER)

    # ---------------------------------------------------------
    # Train Brake
    # ---------------------------------------------------------

    TRAIN_BRAKE = "DriverInput/TrainBrake_F"

    def set_brake(self, value, minimum=0.0, maximum=1.0):
        return self.set_input(
            self.TRAIN_BRAKE,
            value,
            minimum,
            maximum
        )

    def get_brake(self):
        return self.get_input(self.TRAIN_BRAKE)

    def get_brake_info(self):
        return self.get_input_info(self.TRAIN_BRAKE)

    # ---------------------------------------------------------
    # Direct Brake
    # ---------------------------------------------------------

    DIRECT_BRAKE = "DriverInput/DirectBrake_F"

    def set_direct_brake(self, value, minimum=0.0, maximum=1.0):
        return self.set_input(
            self.DIRECT_BRAKE,
            value,
            minimum,
            maximum
        )

    def get_direct_brake(self):
        return self.get_input(self.DIRECT_BRAKE)

    # ---------------------------------------------------------
    # AFB
    # ---------------------------------------------------------

    AFB_SPEED = "DriverInput/AFB_Speed_F"

    def set_afb_speed(self, value, minimum=0.0, maximum=200.0):
        return self.set_input(
            self.AFB_SPEED,
            value,
            minimum,
            maximum
        )

    def get_afb_speed(self):
        return self.get_input(self.AFB_SPEED)

    # ---------------------------------------------------------
    # Reverser
    # ---------------------------------------------------------

    REVERSER = "DriverInput/Reverser_F"

    def set_reverser(self, value):
        return self.set_input(self.REVERSER, value)

    def get_reverser(self):
        return self.get_input(self.REVERSER)

    # ---------------------------------------------------------
    # Lights
    # ---------------------------------------------------------

    TRAIN_LIGHTS = "DriverInput/TrainLights_F"
    SIGNAL_LIGHTS = "DriverInput/SignalLights_F"
    HAZARD_LIGHTS = "DriverInput/HazardLights_F"

    def set_train_lights(self, value):
        return self.set_input(self.TRAIN_LIGHTS, value)

    def set_signal_lights(self, value):
        return self.set_input(self.SIGNAL_LIGHTS, value)

    def set_hazard_lights(self, value):
        return self.set_input(self.HAZARD_LIGHTS, value)

    def get_train_lights(self):
        return self.get_input(self.TRAIN_LIGHTS)

    # ---------------------------------------------------------
    # Wipers
    # ---------------------------------------------------------

    WIPER = "DriverInput/Wiper_F"

    def set_wiper(self, value):
        return self.set_input(self.WIPER, value)

    def get_wiper(self):
        return self.get_input(self.WIPER)

    # ---------------------------------------------------------
    # Doors
    # ---------------------------------------------------------

    def open_left_doors(self):
        return self.set_input(
            "DriverInput/LeftDoorsOpen_F", 1
        )

    def open_right_doors(self):
        return self.set_input(
            "DriverInput/RightDoorsOpen_F", 1
        )

    def close_doors(self):
        return self.set_input(
            "DriverInput/AllDoorsClose_F", 1
        )

    # ---------------------------------------------------------
    # Horn
    # ---------------------------------------------------------

    HORN = "DriverInput/Horn_F"

    def horn(self, active=True):
        """
        Schaltet das Horn dauerhaft ein oder aus.

        active=True:
            Aktiviert InputValue und Interacting.

        active=False:
            Deaktiviert InputValue und Interacting.
        """

        if active:
            self.interact(self.HORN, True)
            return self.set_input(self.HORN, 1)

        try:
            self.set_input(self.HORN, 0.5)
        finally:
            self.interact(self.HORN, False)

        return True

    def horn_low(self, active=True):
        """
        Tiefer Horn-Ton.

        active=True:
            Aktiviert den Input.

        active=False:
            Deaktiviert den Input.
        """

        if active:
            self.interact(self.HORN, True)
            return self.set_input(self.HORN, 0)

        try:
            self.set_input(self.HORN, 0.5)
        finally:
            self.interact(self.HORN, False)

        return True

    # ---------------------------------------------------------
    # SIFA
    # ---------------------------------------------------------

    def sifa(self, active=True):
        return self.set_input(
            "DriverInput/SifaPedal_F",
            1 if active else 0
        )

    # ---------------------------------------------------------
    # PZB
    # ---------------------------------------------------------

    def pzb_acknowledge(self):
        return self.set_input(
            "DriverInput/PZB_Acknowledge_F", 1
        )

    def pzb_override(self):
        return self.set_input(
            "DriverInput/PZB_Override_F", 1
        )

    def pzb_release(self):
        return self.set_input(
            "DriverInput/PZB_Release_F", 1
        )

    # ---------------------------------------------------------
    # Pantograph / Main Circuit Breaker
    # ---------------------------------------------------------

    def set_pantograph(self, value):
        return self.set_input(
            "DriverInput/PantographStateSwitch_F", value
        )

    def set_main_circuit_breaker(self, value):
        return self.set_input(
            "DriverInput/MainCircuitBreaker_F", value
        )

    # ---------------------------------------------------------
    # Battery
    # ---------------------------------------------------------

    def set_battery(self, value):
        return self.set_input(
            "DriverInput/BatteryButton_F", value
        )

    # ---------------------------------------------------------
    # Emergency Brake
    # ---------------------------------------------------------

    def emergency_brake(self, active=True):
        return self.set_input(
            "DriverInput/EmergencyBrakeButton_F",
            1 if active else 0
        )

    # ---------------------------------------------------------
    # Session
    # ---------------------------------------------------------

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
