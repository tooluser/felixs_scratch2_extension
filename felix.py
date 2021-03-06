# no. #!/usr/bin/env python3
# Official docs: https://github.com/llk/scratchx/wiki#command-blocks-that-wait
import json
import os
import sys
import time
import traceback
from subprocess import call
import requests

import pigpio
import RPi.GPIO as GPIO
import psutil
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

# It receives messages from the Scratch and reports back any digital input changes.
class FelixServer(WebSocket):
    GPIO.setmode(GPIO.BCM)

    MotorStepCount = 8
    MotorSeq = range(0, MotorStepCount)
    MotorSeq[0] = [0,1,0,0]
    MotorSeq[1] = [0,1,0,1]
    MotorSeq[2] = [0,0,0,1]
    MotorSeq[3] = [1,0,0,1]
    MotorSeq[4] = [1,0,0,0]
    MotorSeq[5] = [1,0,1,0]
    MotorSeq[6] = [0,0,1,0]
    MotorSeq[7] = [0,1,1,0]
    MotorDelayForSpeed = {
        "slow": 40.0/1000,
        "medium": 20.0/1000,
        "fast": 10.0/1000,
        "super fast": 5.0/1000
    }
    
    def handleSetupIRSensor(self, payload):
        self.ir_sensor_pin = int(payload['pin'])
        self.ir_sensor_configured = True;
        self.handleInput(payload) # Also register as an input pin

    def handleSetupMotor(self, payload):
        print("--handleSetupMotor")
        self.motor_pin1 = int(payload['pin1'])
        self.motor_pin2 = int(payload['pin2'])
        self.motor_pin3 = int(payload['pin3'])
        self.motor_pin4 = int(payload['pin4'])
        self.pi.set_mode(self.motor_pin1, pigpio.OUTPUT)
        self.pi.set_mode(self.motor_pin2, pigpio.OUTPUT)
        self.pi.set_mode(self.motor_pin3, pigpio.OUTPUT)
        self.pi.set_mode(self.motor_pin4, pigpio.OUTPUT)
        self.motorConfigured = True;
        self.motorMoving = False;

    def handleRotateMotor(self, payload): # "command": 'rotate_motor', 'speed': speed, 'dir': dir, 'steps': steps
        print("--handleRotateMotor:", payload)
        if not (self.motorConfigured):
            print("Motor not configured; ignoring.")
            return
        
        if (self.motorMoving):
            print("Motor already moving; skipping.")
            return

        self.motorMoving = True
        delay = self.MotorDelayForSpeed.get(payload['speed'], 10)
        if (payload['dir'] == 'cw'):
            self._motorForward(delay, payload['steps'])
        else:
            self._motorBackward(delay, payload['steps'])
        self._setMotorPins(0, 0, 0, 0)
        self.motorMoving = False
    
    def _setMotorPins(self, pin1Val, pin2Val, pin3Val, pin4Val):
        # print("setPins", pin1Val, pin2Val, pin3Val, pin4Val)
        self.pi.write(self.motor_pin1, pin1Val)
        self.pi.write(self.motor_pin2, pin2Val)
        self.pi.write(self.motor_pin3, pin3Val)
        self.pi.write(self.motor_pin4, pin4Val)

    def _motorForward(self, delay, steps):
        # print("--- motorForward", self, delay, steps)
        for i in range(steps):
            for j in range(self.MotorStepCount):
                self._setMotorPins(self.MotorSeq[j][0], self.MotorSeq[j][1], self.MotorSeq[j][2], self.MotorSeq[j][3])
                time.sleep(delay)
                
    def _motorBackward(self, delay, steps):
        # print("--- motorBackward", self, delay, steps)
        for i in range(steps):
            for j in reversed(range(self.MotorStepCount)):
                self._setMotorPins(self.MotorSeq[j][0], self.MotorSeq[j][1], self.MotorSeq[j][2], self.MotorSeq[j][3])
                time.sleep(delay)

    def handleInput(self, payload):
        pin = int(payload['pin'])
        self.pi.set_glitch_filter(pin, 20000)
        self.pi.set_mode(pin, pigpio.INPUT)
        self.pi.callback(pin, pigpio.EITHER_EDGE, self.input_callback)
        
    def handleDigitalWrite(self, payload):
        pin = int(payload['pin'])
        self.pi.set_mode(pin, pigpio.OUTPUT)
        state = payload['state']
        if state == '0':
            self.pi.write(pin, 0)
        else:
            self.pi.write(pin, 1)

    def handleAnalogWrite(self, payload):
        pin = int(payload['pin'])
        self.pi.set_mode(pin, pigpio.OUTPUT)
        value = int(payload['value'])
        self.pi.set_PWM_dutycycle(pin, value)

    def handleServo(self, payload):
        # HackEduca ---> When a user wishes to set a servo:
        # Using SG90 servo:
        # 180 = 2500 Pulses; 0 = 690 Pulses
        # Want Servo 0-->180 instead of 180-->0:
        # Invert pulse_max to pulse_min
        # pulse_width = int((((pulse_max - pulse_min)/(degree_max - degree_min)) * value) + pulse_min)
        # Where:
        # Test the following python code to know your Pulse Range: Replace it in the formula
        # >>>>----------------------->
        # import RPi.GPIO as GPIO
        # import pigpio
        # Pulse = 690 # 0
        # Pulse = 2500 # 180
        # pi = pigpio.pi()
        # pi.set_mode(23, pigpio.OUTPUT)
        # pi.set_servo_pulse_width(23, Pulse)
        # pi.stop()
        # <------------------------<<<<<
        pin = int(payload['pin'])
        self.pi.set_mode(pin, pigpio.OUTPUT)
        value = int(payload['value'])
        DegreeMin = 0
        DegreeMax = 180
        PulseMin = 2500
        PulseMax = 690
        Pulsewidth = int((((PulseMax - PulseMin) / (DegreeMax - DegreeMin)) * value) + PulseMin)
        self.pi.set_servo_pulsewidth(pin, Pulsewidth)
        time.sleep(0.01)

    def handleTone(self, payload):
        pin = int(payload['pin'])
        self.pi.set_mode(pin, pigpio.OUTPUT)

        frequency = int(payload['frequency'])
        frequency = int((1000 / frequency) * 1000)
        tone = [pigpio.pulse(1 << pin, 0, frequency),
                pigpio.pulse(0, 1 << pin, frequency)]

        self.pi.wave_add_generic(tone)
        wid = self.pi.wave_create()

        if wid >= 0:
            self.pi.wave_send_repeat(wid)
            time.sleep(1)
            self.pi.wave_tx_stop()
            self.pi.wave_delete(wid)

    def handleLEDBrightness(self, payload):
        pin = int(payload['pin'])
        brightness = int(payload['brightness']);
        self.pi.set_PWM_dutycycle(pin, brightness)

    def handleLanternBrightness(self, payload):
        brightness = int(payload['brightness'])
        url = "http://10.0.1.5/api/brightness/" + str(brightness)
        print("POSTing: ", url)
        r = requests.post(url = url)
        print("Response: ", r)

    def handleLanternCycleBegin(self, payload):
        url = "http://10.0.1.5/api/mode/cycle"
        print("POSTing: ", url)
        r = requests.post(url = url)
        print("Response: ", r)

    def handleLanternCyclePause(self, payload):
        url = "http://10.0.1.5/api/mode/cycle/pause"
        print("POSTing: ", url)
        r = requests.post(url = url) 
        print("Response: ", r)

    def handleConfigureTrainSwitch(self, payload):
        servoPin = int(payload['switchPin'])
        GPIO.setup(servoPin, GPIO.OUT)
        p = GPIO.PWM(servoPin, 50)
        p.start(0)

    def handleSetTrainSwitch(self, payload):
        print("--handleSetTrainSwitch:", payload)
        servoPin = int(payload['pin'])
        direction = payload['direction']
        duty_cycle = 7.0 if direction == 'straight' else 3.0

        GPIO.setup(servoPin, GPIO.OUT)
        p = GPIO.PWM(servoPin, 50)
        p.start(0)
        p.ChangeDutyCycle(duty_cycle)
        time.sleep(0.5)
        p.ChangeDutyCycle(0)

    def handleConsoleLog(self, payload):
        print("--handleConsoleLog:", payload)
        message = payload['message']
        print("***** **** ***")
        print(message)
        print("***** **** ***")

    def handleMessage(self):
        try:
            payload = json.loads(self.data)
            print("Message received:" + str(payload))
            client_cmd = payload['command']
            print("Client command: " + str(client_cmd))

            if client_cmd == 'input':
                self.handleInput(payload)
            elif client_cmd == 'digital_write':
                self.handleDigitalWrite(payload) 
            elif client_cmd == 'analog_write':
                self.handleAnalogWrite(payload)
            elif client_cmd == 'servo':
                self.handleServo(payload)
            elif client_cmd == 'setup_motor':
                self.handleSetupMotor(payload)
            elif client_cmd == 'rotate_motor':
                self.handleRotateMotor(payload)
            elif client_cmd == 'tone':
                self.handleTone(payload)
            elif client_cmd == 'ready':
                pass
            elif client_cmd == 'lantern_cycle_begin':
                self.handleLanternCycleBegin(payload)
            elif client_cmd == 'lantern_cycle_pause':
                self.handleLanternCyclePause(payload)
            elif client_cmd == 'lantern_brightness':
                self.handleLanternBrightness(payload)
            elif client_cmd == 'led_brightness':
                self.handleLEDBrightness(payload)
            elif client_cmd == 'configure_train_switch':
                self.handleConfigureTrainSwitch(payload)
            elif client_cmd == 'set_train_switch':
                self.handleSetTrainSwitch(payload)
            elif client_cmd == 'console_log':
                self.handleConsoleLog(payload)
            elif client_cmd == 'configure_ir_sensor':
                self.handleSetupIRSensor(payload)
            else:
                print("Unknown command received", client_cmd)
            print("------ - ------")
            print
        except Exception, err:
            print Exception, err
            traceback.print_exc()

    # call back from pigpio when a digital input value changed
    # send info back up to scratch
    def input_callback(self, pin, level, tick):
        payload = {'report': 'digital_input_change', 'pin': str(pin), 'level': str(level)}
        print('callback', payload)
        msg = json.dumps(payload)
        self.sendMessage(msg)

        # Also send ir-sensor-triggered if this is a registered IR sensor
        if (self.ir_sensor_configured and (pin == self.ir_sensor_pin)):
            payload = {'report': 'ir_sensor_triggered', 'state': str(level)}
            print('callback', payload)
            msg = json.dumps(payload)
            self.sendMessage(msg)

    def handleConnected(self):
        self.pi = pigpio.pi()
        print(self.address, 'connected')

    def handleClose(self):
        print(self.address, 'closed')

def run_server():
    # checking running processes.
    # if the backplane is already running, just note that and move on.
    found_pigpio = False
    found_scratch = False
    print('Starting server')

    for pid in psutil.pids():
        p = psutil.Process(pid)
        if p.name() == "pigpiod":
            found_pigpio = True
            print("pigpiod is running")
        else:
            continue

    if not found_pigpio:
        call(['sudo', 'pigpiod'])
        print('pigpiod has been started')
        
    for pid in psutil.pids():
        p = psutil.Process(pid)
        if p.name() == "scratch2":
            found_scratch = True
            print("scratch2 is running")
        else:
            continue

    if not found_scratch:
        os.system('scratch2&')
        print('scratch2 has been started')

    server = SimpleWebSocketServer('', 9001, FelixServer)
    server.serveforever()

if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        sys.exit(0)
