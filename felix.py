#!/usr/bin/env python3

import json
import os
import sys
import time
from subprocess import call

import pigpio
import psutil
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

# It receives messages from the Scratch and reports back any digital input changes.
class FelixServer(WebSocket):
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
        "slow": 40,
        "medium": 20,
        "fast": 10,
    }
    
    def handleSetupMotor(payload):
        print("--handleSetupMotor:", payload)
        self.motor_pin1 = int(payload['pin1'])
        self.motor_pin2 = int(payload['pin2'])
        self.motor_pin3 = int(payload['pin3'])
        self.motor_pin4 = int(payload['pin4'])
        self.pi.set_mode(self.motor_pin1, pigpio.OUTPUT)
        self.pi.set_mode(self.motor_pin2, pigpio.OUTPUT)
        self.pi.set_mode(self.motor_pin3, pigpio.OUTPUT)
        self.pi.set_mode(self.motor_pin4, pigpio.OUTPUT)
        self.motor_configured = true;

    def handleRotateMotor(payload): # "command": 'rotate_motor', 'speed': speed, 'dir': dir, 'steps': steps

        print("--handleRotateMotor:", payload)
        if (!self.motor_configured):
            print("Motor not configured; ignoring.")
            return
        delay = MotorDelayForSpeed.get([payload['speed']], 10)
        if (payload['dir'] == 'cw'):
            _motorForward(delay, payload['steps'])
        else:
            _motorBackward(delay, payload['steps'])
    
    def _setMotorPins(pin1Val, pin2Val, pin3Val, pin4Val):
        self.pi.write(self.motor_pin1, pin1Val)
        self.pi.write(self.motor_pin2, pin2Val)
        self.pi.write(self.motor_pin3, pin3Val)
        self.pi.write(self.motor_pin4, pin4Val)

    def _motorForward(delay, steps):
        for i in range(steps):
            for j in range(MotorStepCount):
                _setMotorPins(MotorSeq[j][0], MotorSeq[j][1], MotorSeq[j][2], MotorSeq[j][3])
                time.sleep(delay)
                
    def _motorBackward(delay, steps):
        for i in range(steps):
            for j in reversed(range(MotorStepCount)):
                _setMotorPins(MotorSeq[j][0], MotorSeq[j][1], MotorSeq[j][2], MotorSeq[j][3])
                time.sleep(delay)

    def handleInput(payload):
        pin = int(payload['pin'])
        self.pi.set_glitch_filter(pin, 20000)
        self.pi.set_mode(pin, pigpio.INPUT)
        self.pi.callback(pin, pigpio.EITHER_EDGE, self.input_callback)
        
    def handleDigitalWrite(payload):
        pin = int(payload['pin'])
        self.pi.set_mode(pin, pigpio.OUTPUT)
        state = payload['state']
        if state == '0':
            self.pi.write(pin, 0)
        else:
            self.pi.write(pin, 1)

    def handleAnalogWrite(payload):
        pin = int(payload['pin'])
        self.pi.set_mode(pin, pigpio.OUTPUT)
        value = int(payload['value'])
        self.pi.set_PWM_dutycycle(pin, value)

    def handleServo(payload):
        # HackEduca ---> When a user wishes to set a servo:
        # Using SG90 servo:
        # 180° = 2500 Pulses; 0° = 690 Pulses
        # Want Servo 0°-->180° instead of 180°-->0°:
        # Invert pulse_max to pulse_min
        # pulse_width = int((((pulse_max - pulse_min)/(degree_max - degree_min)) * value) + pulse_min)
        # Where:
        # Test the following python code to know your Pulse Range: Replace it in the formula
        # >>>>----------------------->
        # import RPi.GPIO as GPIO
        # import pigpio
        # Pulse = 690 # 0°
        # Pulse = 2500 # 180°
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

    def handleTone(payload):
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

    def handleMessage(self):
        # get command from Scratch2
        payload = json.loads(self.data)
        print("Message received:", payload)
        client_cmd = payload['command']

        if client_cmd == 'input':
            handleInput(payload)
        elif client_cmd == 'digital_write':
            handleDigitalWrite(payload) 
        elif client_cmd == 'analog_write':
            handleAnalogWrite(payload)
        elif client_cmd == 'servo':
            handleServo(payload)
        elif client_cmd == 'setup_motor':
            handleSetupMotor(payload)
        elif client_cmd == 'rotate_motor':
            handleRotateMotor(payload)
        elif client_cmd == 'tone':
            handleTone(payload)
        elif client_cmd == 'ready':
            pass
        else:
            print("Unknown command received", client_cmd)

    # call back from pigpio when a digital input value changed
    # send info back up to scratch
    def input_callback(self, pin, level, tick):
        payload = {'report': 'digital_input_change', 'pin': str(pin), 'level': str(level)}
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

    os.system('scratch2&')
    server = SimpleWebSocketServer('', 9000, FelixServer)
    server.serveforever()

if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        sys.exit(0)
