from bluetooth_driver import BluetoothDriver
from boost_driver import BoostDriver
import time

UPDATE_PERIOD = 0.2

running = True
last_update_time = 0

boost_driver = BoostDriver()
bluetooth_driver = BluetoothDriver()


def take_boost_reading():
    boost_reading, sensor_voltage = boost_driver.read()
    bluetooth_driver.set_live_boost(boost_reading)
    bluetooth_driver.set_live_sensor_voltage(sensor_voltage)
    if boost_reading > bluetooth_driver.get_peak_boost():
        bluetooth_driver.set_peak_boost(boost_reading)


while running:
    current_time = time.time()
    if current_time - last_update_time > UPDATE_PERIOD:
        last_update_time = current_time
        take_boost_reading()

    boost_driver.sample()
    time.sleep_ms(5)

