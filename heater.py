import time
from multiprocessing import Process, Value
import RPi.GPIO as GPIO

HEAT_PIN_ON = 1;
HEAT_PIN_OFF = 0;

class HeaterController:

    def __init__(self, pinNum):
        self.Process = Process
        self.duration = None
        self.onTime = Value("d", 0.0)
        self.offTime = Value("d", 0.0)
        self.stop = False
        self.processStarted = False

        self.pin = pinNum

    def flickerPin(self, onTime, offTime, pin):
        while not self.stop:
            GPIO.output(pin, HEAT_PIN_ON)
            time.sleep(onTime.value)
            GPIO.output(pin, HEAT_PIN_OFF)
            time.sleep(offTime.value)

    def controllerUpdate(self, dutyCycle, f):
        self.duration = 1 / f
        self.onTime.value = self.duration * (float(dutyCycle) / 100.0)
        self.offTime.value = self.duration - self.onTime.value

        if self.processStarted == False:
            self.p = self.Process(target = self.flickerPin, args = (self.onTime, self.offTime, self.pin,))
            self.p.start()
            self.processStarted = True
