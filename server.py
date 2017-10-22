#!/usr/bin/python

class EspressoTemperatureControl():

    def main(self):
        import Adafruit_GPIO.SPI as SPI
        import Adafruit_MAX31855.MAX31855 as MAX31855
        import RPi.GPIO as GPIO
        from heater import HeaterController
        from pid import PID
        import config as conf

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(26, GPIO.OUT)
        GPIO.output(26, 0)

        self.power_is_on = True
        self.auto_run = False
        self.setTemp = 105
        self.calibrationOffset = 0  # Added to thermocouple output.
        self.boilerTemp = 0 # Updated below
        self.tempStarted = False
        self.heaterPIDStarted = False
        self.heaterController = HeaterController(26)

        self.pid = PID(conf.Pc, conf.Ic, conf.Dc)
        self.pid.setSetPoint(self.setTemp)
        self.pid_output = 0.0;

        self.sensor = MAX31855.MAX31855(spi=SPI.SpiDev(0, 0))

        self.update_temperature()
        self.start_pid()
        self.rest_server()

    def start_pid(self):
        import threading

        if self.heaterPIDStarted == False:
            self.heaterController.controllerUpdate(0, 0.8333)
            self.heaterPIDStarted = True

        #self.power_update()

        if self.power_is_on == True:
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
        elif self.power_is_on == False:
            # 0 sets the heat controller to off because of the sleep times
            self.heaterController.controllerUpdate(0, 0.8333)

    def update_temperature(self):
        import threading

        current_temp = self.sensor.readTempC() + self.calibrationOffset
        self.boilerTemp = "{:.2f}".format(float(current_temp))
        threading.Timer(0.5, self.update_temperature).start()

    def power_update(self):
        import datetime

        # if force_power_on == True:
        #     power_is_on = True
        #     return
        #
        # time = datetime.datetime.now()
        # if auto_run == True:
        #     start_auto_time_hash = self.time_hash(auto_run_hour, auto_run_minute)
        #     end_auto_time_hash = self.time_hash(auto_run_hour, auto_run_minute)
        #     current_time_hash = self.time_hash(time.hour, time.minute)
        #     if current_time_hash > start_auto_time_hash and current_time_hash < end_auto_time_hash:
        #         power_is_on = True
        #     else:
        #         power_is_on = False

    def time_hash(self, hour, min):
        return hour * 1000 + min

    def rest_server(self):
        import datetime
        import config as conf
        from bottle import route, run, get, post, request, static_file, abort
        from datetime import datetime
        import os

        basedir = os.path.dirname(__file__)
        wwwdir = basedir + '/www/'

        @route('/')
        def docroot():
            return static_file('index.html', wwwdir)

        @route('/<filepath:path>')
        def servfile(filepath):
            return static_file(filepath, wwwdir)

        @route('/curtemp')
        def curtemp():
            temperature = celcius_to_fahrenheit(self.boilerTemp)
            return str(temperature)

        @get('/settemp')
        def settemp():
            temperature = celcius_to_fahrenheit(self.setTemp)
            return str(temperature)

        @post('/settemp')
        def post_settemp():
            try:
                settemp = float(request.forms.get('settemp'))
                if settemp >= 160 and settemp <= 280:
                    self.setTemp = fahrenheit_to_celcius(settemp)
                    return str(settemp)
                else:
                    abort(400, 'Set temp out of range 200-260.')
            except:
                abort(400, 'Invalid number for set temp.')

        @get('/snooze')
        def get_snooze():
            return str(self.auto_run)

        @post('/snooze')
        def post_snooze():
            snooze = request.forms.get('snooze')
            try:
                datetime.strptime(snooze, '%H:%M')
            except:
                abort(400, 'Invalid time format.')
            espressoTemperatureControl.auto_run = True
            return str(self.auto_run)

        @post('/resetsnooze')
        def reset_snooze():
            self.auto_run = False
            return True

        @get('/allstats')
        def allstats():
            import config as conf
            all_stat = {'settemp': celcius_to_fahrenheit(self.setTemp),
             'autorun': espressoTemperatureControl.auto_run,
             'tempf': celcius_to_fahrenheit(self.boilerTemp),
             'pterm': conf.Pc,
             'iterm': conf.Ic,
             'dterm': conf.Dc,
             'pidval' : self.pid_output,
             'avgpid': self.pid_output}
            return all_stat

        @route('/restart')
        def restart():
            return '';

        @route('/shutdown')
        def shutdown():
            return '';

        @get('/healthcheck')
        def healthcheck():
            return 'OK'

        run(host='0.0.0.0', port=conf.port, server='cheroot')
        threading.Timer(.8, self.rest_server).start()


def fahrenheit_to_celcius(temperature):
    return float(float(temperature) - 32) * (5.0 / 9.0)

def celcius_to_fahrenheit(temperature):
    return (9.0 / 5.0) * float(temperature) + 32


if __name__ == "__main__":
    import threading
    import datetime
    import config as conf
    import Adafruit_GPIO.SPI as SPI
    import Adafruit_MAX31855.MAX31855 as MAX31855
    import RPi.GPIO as GPIO

    from heater import HeaterController
    from pid import PID

    espressoTemperatureControl = EspressoTemperatureControl()
    espressoTemperatureControl.main()
