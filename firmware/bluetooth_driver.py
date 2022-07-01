import bluetooth
import binascii
import random
import time
from ble_advertising import advertising_payload

from micropython import const


def uuid2bytes(uuid):
    uuid = uuid.encode().replace(b'-',b'')
    tmp = binascii.unhexlify(uuid)
    return bytes(reversed(tmp))


_FLAG_DESC_READ = const(1)
_FLAG_DESC_WRITE = const(2)
_IRQ_CENTRAL_CONNECT                 = const(1 << 0)
_IRQ_CENTRAL_DISCONNECT              = const(1 << 1)
_IRQ_GATTS_WRITE = const(3)

# Sensor control values
_SC_ZERO_SENSOR = b'\x01'
_SC_RESET_SENSOR_ZERO = b'\x02'
_SC_RESET_MAX_PRESSURE = b'\x03'

# BLUETOOTH LE GATT PROFILE
_ADV_APPEARANCE_CAR = const(0x08C1)

_LIVE_PRESSURE_DESCRIPTOR = (bluetooth.UUID(0x2901), _FLAG_DESC_READ,)
_LIVE_PRESSURE_UUID = bluetooth.UUID(uuid2bytes("e6ea4e76-f7ce-11ec-b939-0242ac120002"))
_PRESSURE_CHAR = (_LIVE_PRESSURE_UUID, bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY, [_LIVE_PRESSURE_DESCRIPTOR])

_MAX_PRESSURE_DESCRIPTOR = (bluetooth.UUID(0x2901), _FLAG_DESC_READ,)
_MAX_PRESSURE_UUID = bluetooth.UUID(uuid2bytes("2826c950-f7ca-11ec-b939-0242ac120002"))
_MAX_PRESSURE_CHAR = (_MAX_PRESSURE_UUID, bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY, [_MAX_PRESSURE_DESCRIPTOR])

_SENSOR_VOLTAGE_DESCRIPTOR = (bluetooth.UUID(0x2901), _FLAG_DESC_READ,)
_SENSOR_VOLTAGE_UUID = bluetooth.UUID(0x2B18)
_SENSOR_VOLTAGE_CHAR = (_SENSOR_VOLTAGE_UUID, bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY, [_SENSOR_VOLTAGE_DESCRIPTOR])

_SENSOR_CONTROL_DESCRIPTOR = (bluetooth.UUID(0x2901), _FLAG_DESC_READ,)
_SENSOR_CONTROL_UUID = bluetooth.UUID(uuid2bytes("da0f8b10-f7cb-11ec-b939-0242ac120002"))
_SENSOR_CONTROL_CHAR = (_SENSOR_VOLTAGE_UUID, bluetooth.FLAG_WRITE, [_SENSOR_CONTROL_DESCRIPTOR])

_PRESSURE_UUID = bluetooth.UUID(uuid2bytes("fab0ed78-f7c6-11ec-b939-0242ac120002"))
_PRESSURE_SERVICE = (_PRESSURE_UUID, (_PRESSURE_CHAR, _MAX_PRESSURE_CHAR, _SENSOR_VOLTAGE_CHAR, _SENSOR_CONTROL_CHAR,),)


class BluetoothDriver:
    _peak_boost = 0
    _live_pressure = 0
    _max_pressure = 0
    _sensor_voltage = 0

    def __init__(self):
        self._zero_sensor_callback = None
        self._reset_zeroing_callback = None
        self._reset_max_pressure_callback = None

        self.name = 'Rupert\'s MR2'
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)
        # Notice handles...
        ((self._pressure_handle,
          self._pressure_desc_handle,
          self._max_pressure_handle,
          self._max_pressure_desc_handle,
          self._sensor_voltage_handle,
          self._sensor_voltage_desc_handle,
          self._sensor_control_handle,
          self._sensor_control_desc_handle,
          ),) = self._ble.gatts_register_services((_PRESSURE_SERVICE,))
        self._connections = set()
        self._payload = advertising_payload(name=self.name, services=[], appearance=_ADV_APPEARANCE_CAR)
        self._advertise()
        self.init_names()
        self.init_characteristics()

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _, = data
            self._connections.add(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _, = data
            self._connections.remove(conn_handle)
            # Start advertising again to allow a new connection.
            self._advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data
            self._handle_write(attr_handle)

    def _handle_write(self, handle):
        if handle == self._sensor_control_handle:
            value = self._ble.gatts_read(handle)
            self._sensor_control_handler(value)
            self._ble.gatts_write(handle, b'\x00')

    def _sensor_control_handler(self, value):
        if value == _SC_ZERO_SENSOR:
            if self._zero_sensor_callback is not None:
                self._zero_sensor_callback()
        elif value == _SC_RESET_SENSOR_ZERO:
            if self._reset_zeroing_callback is not None:
                self._reset_zeroing_callback()
        elif value == _SC_RESET_MAX_PRESSURE:
            if self._reset_max_pressure_callback is not None:
                self._reset_max_pressure_callback()

    def init_names(self):
        self._ble.gatts_write(self._pressure_desc_handle, "Pressure")
        self._ble.gatts_write(self._max_pressure_desc_handle, "Max pressure")
        self._ble.gatts_write(self._sensor_voltage_desc_handle, "Sensor voltage")
        self._ble.gatts_write(self._sensor_control_desc_handle, "General purpose sensor control")

    def init_characteristics(self):
        self.set_pressure(self._live_pressure)
        self.set_sensor_voltage(self._sensor_voltage)
        self.set_max_pressure(self._max_pressure)

    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)

    def set_zero_sensor_callback(self, zero_sensor_callback):
        self._zero_sensor_callback = zero_sensor_callback

    def set_reset_zeroing_callback(self, reset_zeroing_callback):
        self._reset_zeroing_callback = reset_zeroing_callback

    def set_reset_max_pressure_callback(self, reset_max_pressure_callback):
        self._reset_max_pressure_callback = reset_max_pressure_callback

    def set_pressure(self, pressure, notify=True):
        self._live_pressure = pressure
        self._ble.gatts_write(self._pressure_handle, "{} psi".format(pressure))
        if notify:
            for conn_handle in self._connections:
                # Notify connected centrals to issue a read.
                self._ble.gatts_notify(conn_handle, self._pressure_handle)

    def set_max_pressure(self, pressure, notify=True):
        self._max_pressure = pressure
        self._ble.gatts_write(self._max_pressure_handle, "{} psi".format(pressure))
        if notify:
            for conn_handle in self._connections:
                # Notify connected centrals to issue a read.
                self._ble.gatts_notify(conn_handle, self._max_pressure_handle)

    def set_sensor_voltage(self, voltage, notify=True):
        self._sensor_voltage = voltage
        self._ble.gatts_write(self._sensor_voltage_handle, "{}V".format(voltage))
        if notify:
            for conn_handle in self._connections:
                # Notify connected centrals to issue a read.
                self._ble.gatts_notify(conn_handle, self._sensor_voltage_handle)

    def get_max_pressure(self):
        return self._max_pressure

    def get_pressure(self):
        return self._live_pressure
