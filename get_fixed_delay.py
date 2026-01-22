"""
Main module to process and visualize experiment data from a sensor.

This module initializes a sensor data processor, retrieves the fixed delay
and standard deviation, and plots the sensor data with specific
configuration.

Functions
---------
main
    Processes sensor data and generates a visualization.
"""

from src.UnicornDataSensor import UnicornDataSensor


def main():
    data_sensor = UnicornDataSensor('data/sensor/sensor_09-07-25.xdf')
    delay, std = data_sensor.get_fixed_delay()
    print(f"Fixed delay: {delay} ms (std: {std} ms)")
    data_sensor.plot(confidence_interval=0.5, picks=['Fz'])


if __name__ == "__main__":
    main()
