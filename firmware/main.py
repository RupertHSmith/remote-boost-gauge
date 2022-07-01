from bluetooth_driver import BluetoothDriver
from boost_driver import BoostDriver
from nvs_driver import NvsDriver
import time


running = True
UPDATE_PERIOD = 0.2
NVS_STORAGE_PERIOD = 10
boost_driver = BoostDriver()
bluetooth_driver = BluetoothDriver()
nvs_driver = NvsDriver()


def reset_zeroing_callback():
    boost_driver.reset_zero_offset()


def zero_sensor_callback():
    current_pressure = bluetooth_driver.get_pressure()
    boost_driver.set_zero_offset(-current_pressure)


def reset_max_pressure_callback():
    bluetooth_driver.set_max_pressure(0)


def take_boost_reading():
    boost_reading, sensor_voltage = boost_driver.read()
    bluetooth_driver.set_pressure(boost_reading)
    bluetooth_driver.set_sensor_voltage(sensor_voltage)
    if boost_reading > bluetooth_driver.get_max_pressure():
        bluetooth_driver.set_max_pressure(boost_reading)


def update_nvs():
    max_pressure = bluetooth_driver.get_max_pressure()
    offset = boost_driver.get_zero_offset()
    nvs_driver.set_all(max_pressure, offset)


def initialise():
    stored_pressure = nvs_driver.get_max_pressure()
    stored_offset = nvs_driver.get_offset()
    bluetooth_driver.set_max_pressure(stored_pressure)
    boost_driver.set_zero_offset(stored_offset)


def run():
    initialise()

    bluetooth_driver.set_zero_sensor_callback(zero_sensor_callback)
    bluetooth_driver.set_reset_zeroing_callback(reset_zeroing_callback)
    bluetooth_driver.set_reset_max_pressure_callback(reset_max_pressure_callback)

    last_update_time = 0
    last_nvs_update = 0
    while running:
        current_time = time.time()
        if current_time - last_update_time > UPDATE_PERIOD:
            last_update_time = current_time
            take_boost_reading()

        if current_time - last_nvs_update > NVS_STORAGE_PERIOD:
            last_nvs_update = current_time
            update_nvs()

        boost_driver.sample()
        time.sleep_ms(5)


if __name__ == '__main__':
    run()
