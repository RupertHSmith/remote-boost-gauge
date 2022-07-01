from esp32 import NVS

BOOST_GAUGE_NVS = "boost-gauge"
PRESSURE_OFFSET_NVS = "pressure-offset"  # 3 Decimal places
MAX_PRESSURE_NVS = "max-pressure"  # 3 Decimal places


def to_int_32(decimal_value):
    return round(decimal_value * 1000)


def from_int_32(int32_value):
    return int32_value / 1000


class NvsDriver:
    def __init__(self):
        self._nvs = NVS(BOOST_GAUGE_NVS)
        self._init_nvs_key(PRESSURE_OFFSET_NVS)
        self._init_nvs_key(MAX_PRESSURE_NVS)

    def _init_nvs_key(self, key, initial_value=0):
        try:
            self._nvs.get_i32(key)
        except OSError:
            # Key didn't exist so create with default value
            self._nvs.set_i32(key, initial_value)

    def get_max_pressure(self):
        return from_int_32(self._nvs.get_i32(MAX_PRESSURE_NVS))

    def get_offset(self):
        return from_int_32(self._nvs.get_i32(PRESSURE_OFFSET_NVS))

    def set_max_pressure(self, max_pressure):
        self._nvs.set_i32(MAX_PRESSURE_NVS, to_int_32(max_pressure))
        self._nvs.commit()

    def set_offset(self, offset):
        self._nvs.set_i32(PRESSURE_OFFSET_NVS, to_int_32(offset))
        self._nvs.commit()

    def set_all(self, max_pressure, offset):
        self._nvs.set_i32(MAX_PRESSURE_NVS, to_int_32(max_pressure))
        self._nvs.set_i32(PRESSURE_OFFSET_NVS, to_int_32(offset))
        self._nvs.commit()
