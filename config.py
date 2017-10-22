#!/usr/bin/python

# Raspberry Pi SPI Port and Device
spi_port = 0
spi_dev = 0

# Pin # for relay connected to heating element
he_pin = 26

# Default goal temperature
set_temp = 221.

# Default alarm time
snooze = '07:00'

# Main loop sample rate in seconds
sample_time = 0.1

# PID Proportional, Integral, and Derivative values
Pc = 10.0
Ic = 0.1
Dc = 40.0

#Web/REST Server Options
port = 8080
