#!/usr/bin/python

def update_temperature(state, sensor):
  import  threading

  current_temp = sensor.tempC();
  state['tempf'] = (9.0 / 5.0) * current_temp + 32
  threading.Timer(.5, update_temperature(state, sensor)).start()

def pid_loop(dummy, state, heaterController, pid):

  def c_to_f(c):
    return c * 9.0 / 5.0 + 32.0

  def f_to_c(f):
    return (f - 32) * (5.0 / 9.0)

  while True : # Loops 10x/second
    tempf = state['tempf']
    tempc = f_to_c(tempf);

    pid_output = pid.update(float(tempc))
    temp_pid_output = pid_output

    if temp_pid_output > 100:
      temp_pid_output = 100
    elif temp_pid_output < 0:
      temp_pid_output = 0

    state['avgpid'] = pid_output
    state['pidval'] = temp_pid_output
    print('Updating PID with: ' + str(state['avgpid']))
    print('PID Output:        ' + str(pid_output))
    print('PID Output Fixed: ' + str(int(temp_pid_output)))
    heaterController.controllerUpdate(int(temp_pid_output), 0.8333)

    threading.Timer(0.4266666, pid_loop(1,state,heaterController)).start()

def rest_server(dummy,state):
  from bottle import route, run, get, post, request, static_file, abort
  from subprocess import call
  from datetime import datetime
  import config as conf
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
    return str(state['avgtemp'])

  @get('/settemp')
  def settemp():
    return str(state['settemp'])

  @post('/settemp')
  def post_settemp():
    try:
      settemp = float(request.forms.get('settemp'))
      if settemp >= 160 and settemp <= 280 :
        state['settemp'] = settemp
        return str(settemp)
      else:
        abort(400,'Set temp out of range 200-260.')
    except:
      abort(400,'Invalid number for set temp.')

  @get('/snooze')
  def get_snooze():
    return str(state['snooze'])

  @post('/snooze')
  def post_snooze():
    snooze = request.forms.get('snooze')
    try:
      datetime.strptime(snooze,'%H:%M')
    except:
      abort(400,'Invalid time format.')
    state['snoozeon'] = True
    state['snooze'] = snooze
    return str(snooze)

  @post('/resetsnooze')
  def reset_snooze():
    state['snoozeon'] = False
    return True

  @get('/allstats')
  def allstats():
    return dict(state)

  @route('/restart')
  def restart():
    call(["reboot"])
    return '';

  @route('/shutdown')
  def shutdown():
    call(["shutdown","-h","now"])
    return '';

  @get('/healthcheck')
  def healthcheck():
    return 'OK'

  run(host='0.0.0.0',port=conf.port,server='cheroot')

if __name__ == '__main__':
  from multiprocessing import Process, Manager
  import config as conf
  import threading
  import RPi as GPIO
  from pid import PID
  import Adafruit_MAX31855.MAX31855 as MAX31855
  import Adafruit_GPIO.SPI as SPI
  from heater import HeaterController

  GPIO.setmode(GPIO.BOARD)
  GPIO.setup(conf.he_pin, GPIO.OUT)
  GPIO.output(conf.he_pin, 0)

  sensor = MAX31855.MAX31855(spi=SPI.SpiDev(conf.spi_port, conf.spi_dev))
  heaterController = HeaterController(conf.he_pin)
  pid = PID(conf.Pc, conf.Ic, conf.Dc)

  manager = Manager()
  pidstate = manager.dict()
  pidstate['snooze'] = conf.snooze 
  pidstate['snoozeon'] = False
  pidstate['i'] = 0
  pidstate['settemp'] = conf.set_temp
  pidstate['avgpid'] = 0.

  pid = PID(conf.Pc, conf.Ic, conf.Dc)
  pid.setSetPoint((pidstate['settemp'] - 32) * 5.0 / 9.0)

  pid_loop(1, pidstate, heaterController, pid)
  update_temperature(pidstate, sensor)

  r = Process(target=rest_server,args=(1,pidstate))
  r.daemon = True
  r.start()