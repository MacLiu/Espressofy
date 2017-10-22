import threading
import datetime
import config as conf
import Adafruit_GPIO.SPI as SPI
import Adafruit_MAX31855.MAX31855 as MAX31855
import RPi.GPIO as GPIO

from heater import HeaterController
from pid import PID
from multiprocessing import Process, Value

HEATER_PIN = 26

P_VALUE = 10.0
I_VALUE = 0.1
D_VALUE = 40.0

INITIAL_TEMPERATURE = 105

MAX_TEMPERATURE = 120
MIN_TEMPERATURE = 80;

power_is_on = True;
force_power_on = False;
auto_run = False;
auto_run_hour = 0;
auto_run_minute = 0;

class EspressoTemperatureControl():

    def main(self):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(HEATER_PIN, GPIO.OUT)
        GPIO.output(HEATER_PIN, 0)

        self.setTemp = INITIAL_TEMPERATURE
        self.calibrationOffset = 0  # Added to thermocouple output.
        self.boilerTemp = 0 # Updated below
        self.tempStarted = False
        self.heaterPIDStarted = False
        self.heaterController = HeaterController(HEATER_PIN)

        self.pid = PID(P_VALUE, I_VALUE, D_VALUE)
        self.pid.setSetPoint(self.setTemp)
        self.pid_output = 0.0;

        self.sensor = MAX31855.MAX31855(spi=SPI.SpiDev(0, 0))

        self.update_temperature()
        self.start_pid()

    def start_pid(self):
        if self.heaterPIDStarted == False:
            self.heaterController.controllerUpdate(0, 0.8333)
            self.heaterPIDStarted = True

        self.power_update()

        if power_is_on == True:
            self.pid_output = self.pid.update(float(self.boilerTemp))
            temp_pid_output = self.pid_output

            if temp_pid_output > 100:
                temp_pid_output = 100
            elif temp_pid_output < 0:
                temp_pid_output = 0

            print('Updating PID with: ' + str(self.boilerTemp))
            print('PID Output:        ' + str(self.pid_output))
            print('PID Output Fixed: ' + str(int(temp_pid_output)))
            self.heaterController.controllerUpdate(int(temp_pid_output), 0.8333)

            threading.Timer(0.4266666, self.start_pid).start()
        elif power_is_on == False:
            # 0 sets the heat controller to off because of the sleep times
            self.heaterController.controllerUpdate(0, 0.8333)

    def update_temperature(self):
        current_temp = self.sensor.readTempC() + self.calibrationOffset
        self.boilerTemp = "{:.2f}".format(float(current_temp))
        threading.Timer(0.5, self.update_temperature).start()

    def power_update(self):
        if force_power_on == True:
            power_is_on = True
            return

        time = datetime.datetime.now()
        if auto_run == True:
            start_auto_time_hash = self.time_hash(auto_run_hour, auto_run_minute)
            end_auto_time_hash = self.time_hash(auto_run_hour, auto_run_minute)
            current_time_hash = self.time_hash(time.hour, time.minute)
            if current_time_hash > start_auto_time_hash and current_time_hash < end_auto_time_hash:
                power_is_on = True
            else:
                power_is_on = False

    def time_hash(self, hour, min):
        return hour * 1000 + min


espressoTemperatureControl = EspressoTemperatureControl()


def fahrenheit_to_celcius(temperature):
    return float(float(temperature) - 32) * (5.0 / 9.0)

def celcius_to_fahrenheit(temperature):
    return (9.0 / 5.0) * float(float(temperature) + 32)

def rest_server():
    from bottle import route, run, get, post, request, static_file, abort
    from subprocess import call
    from datetime import datetime
    import os

    basedir = os.path.dirname(__file__)
    wwwdir = basedir+'/www/'

    @route('/')
    def docroot():
        return static_file('index.html',wwwdir)

    @route('/<filepath:path>')
    def servfile(filepath):
        return static_file(filepath,wwwdir)

    @route('/curtemp')
    def curtemp():
        temperature = celcius_to_fahrenheit(espressoTemperatureControl.boilerTemp)
        return str(temperature)

    @get('/settemp')
    def settemp():
        temperature = celcius_to_fahrenheit(espressoTemperatureControl.setTemp)
        return str(temperature)

    @post('/settemp')
    def post_settemp():
        try:
          settemp = float(request.forms.get('settemp'))
          if settemp >= 160 and settemp <= 280 :
            espressoTemperatureControl.setTemp = fahrenheit_to_celcius(settemp)
            return str(settemp)
          else:
            abort(400,'Set temp out of range 200-260.')
        except:
          abort(400,'Invalid number for set temp.')

    @get('/snooze')
    def get_snooze():
        return str(auto_run)

    @post('/snooze')
    def post_snooze():
        snooze = request.forms.get('snooze')
        try:
          datetime.strptime(snooze,'%H:%M')
        except:
          abort(400,'Invalid time format.')
        auto_run = True
        return str(auto_run)

    @post('/resetsnooze')
    def reset_snooze():
        auto_run = False
        return True

    @get('/allstats')
    def allstats():
        return str({'settemp' : celcius_to_fahrenheit(espressoTemperatureControl.setTemp),
                'autorun' : auto_run,
                'tempf' : celcius_to_fahrenheit(espressoTemperatureControl.boilerTemp),
                'pterm' : P_VALUE,
                'iterm' : I_VALUE,
                'dterm' : D_VALUE,
                'avgpid' : espressoTemperatureControl.pid_output})

    @route('/restart')
    def restart():
        return '';

    @route('/shutdown')
    def shutdown():
        return '';

    @get('/healthcheck')
    def healthcheck():
        return 'OK'

    run(host='0.0.0.0',port=conf.port,server='cheroot')

if __name__ == "__main__":
    espressoTemperatureControl.main()
    r = Process(target=rest_server, args=())
    r.daemon = True
    r.start()
