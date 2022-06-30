from machine import Pin, ADC


def vin_to_sensor_vout(vin):
    return vin * 2


def vout_to_psi(vout, vcc):
    pressure_kpa = (vout + vcc * 0.04) / (vcc * 0.004)
    return (pressure_kpa - 101.325) / 6.895  # Convert to PSI


class BoostDriver:
    vin_pin = Pin(34)
    VCC = 5
    boost = 0
    voltage_readings = []

    def __init__(self):
        self.vin_adc = ADC(self.vin_pin)
        pass

    def get_voltage(self):
        return self.vin_adc.read_uv() / 1000000  # Convert to Volts

    def sample(self):
        self.voltage_readings.append(self.get_voltage())
        pass

    def read(self):
        if len(self.voltage_readings) > 0:
            avg_vin = sum(self.voltage_readings) / len(self.voltage_readings)
            self.voltage_readings = []

            sensor_vout = vin_to_sensor_vout(avg_vin)
            pressure = vout_to_psi(sensor_vout, self.VCC)

            return pressure, avg_vin

        return 0, 0
