(function (ext) {
	var socket = null;
	var connected = false;
	var digital_inputs = new Array(32); // an array to hold possible digital input values for the reporter block
	var myStatus = 1; // initially yellow
	var myMsg = 'not_ready';
	var motor_configured = false;
	var ir_sensor_tripped = false;
    
	ext.connect = function (callback) {
		console.log("Starting websocket to port 9001");
		window.socket = new WebSocket("ws://127.0.0.1:9001");
		window.socket.onopen = function () {
			var msg = JSON.stringify({
				"command": "ready"
			});
			window.socket.send(msg);
			myStatus = 2;
			// change status light from yellow to green
			myMsg = 'ready';
			connected = true;
			// initialize the reporter buffer
			digital_inputs.fill('0');
			// give the connection time establish
			window.setTimeout(function() {
				callback();
			}, 1000);
		};
        
		window.socket.onmessage = function (message) {
			var msg = JSON.parse(message.data);
			// handle the only reporter message from the server
			// for changes in digital input state
			var reporter = msg['report'];
			if(reporter === 'digital_input_change') {
				var pin = msg['pin'];
				digital_inputs[parseInt(pin)] = msg['level'];
			}
			if(reporter === 'ir_sensor_triggered') {
				var trip = parseInt(msg['state']);
				ir_sensor_tripped = (trip == 1);
			}
			console.log(message.data);
		};

		window.socket.onclose = function (e) {
			console.log("Connection closed.");
			socket = null;
			connected = false;
			myStatus = 1;
			myMsg = 'not_ready';
			motor_configured = false;
		};
	};
	
	ext.disconnect = function (callback) {
		console.log("Disconnecting websocket on port 9001");
		myMsg = "disconnected";
		connected = false;

		var msg = JSON.stringify({
			"command": "shutdown"
		});
		window.socket.send(msg);
	};

	// Cleanup function when the extension is unloaded
	ext._shutdown = function () {
		var msg = JSON.stringify({
			"command": "shutdown"
		});
		window.socket.send(msg);
	};
    
	// Status reporting code
	// Use this to report missing hardware, plugin or unsupported browser
	ext._getStatus = function (status, msg) {
		return {status: myStatus, msg: myMsg};
	};
    
	ext.input = function(pin) {
		if (connected == false) {
			alert("Server Not Connected");
		}
		// validate the pin number for the mode
		if (validatePin(pin)) {
			var msg = JSON.stringify({
				"command": 'input', 'pin': pin
			});
			sendMessage(msg);
		}
	};
    
	// when the digital write block is executed
	ext.digital_write = function (pin, state) {
		if (connected == false) {
			alert("Server Not Connected");
		}
		console.log("digital write");
		// validate the pin number for the mode
		if (validatePin(pin)) {
			var msg = JSON.stringify({
				"command": 'digital_write', 'pin': pin, 'state': state
			});
			sendMessage(msg);
		}
	};
    
	// when the PWM block is executed
	ext.analog_write = function (pin, value) {
		if (connected == false) {
			alert("Server Not Connected");
		}
		console.log("analog write");
		// validate the pin number for the mode
		if (validatePin(pin)) {
			// validate value to be between 0 and 255
			if (value === 'VAL') {
				alert("PWM Value must be in the range of 0 - 255");
			}
			else {
				value = parseInt(value);
				if (value < 0 || value > 255) {
					alert("PWM Value must be in the range of 0 - 255");
				}
				else {
					var msg = JSON.stringify({
						"command": 'analog_write', 'pin': pin, 'value': value
					});
					sendMessage(msg);
				}
			}
		}
	};

	// ***Hackeduca --> when the Servo block is executed
	ext.servo = function (pin, value) {
		if (connected == false) {
			alert("Server Not Connected");
		}
		console.log("servo");
		// validate the pin number for the mode
		if (validatePin(pin)) {
			// validate value to be between 0° and 180°
			if (value === 'VAL') {
				alert("Servo Value must be in the range of 0° - 180°");
			}
			else {
				value = parseInt(value);
				if (value < 0 || value > 180) {
					alert("Servo Value must be in the range of 0° - 180°");
				}
				else {
					var msg = JSON.stringify({
						"command": 'servo', 'pin': pin, 'value': value
					});
					sendMessage(msg);
				}
			}
		}
	};

	ext.play_tone = function (pin, frequency) {
		if (connected == false) {
			alert("Server Not Connected");
		}
		// validate the pin number for the mode
		if (validatePin(pin)) {
			var msg = JSON.stringify({
				"command": 'tone', 'pin': pin, 'frequency': frequency
			});
			sendMessage(msg);
		}
	};

	ext.set_lantern_brightness = function(brightness) {
		if (connected == false) {
			alert("Server Not Connected");
		}
		
		var msg = JSON.stringify({
			"command": 'lantern_brightness', 'brightness': brightness
		});
		sendMessage(msg);
	};

	ext.digital_read = function(pin) {
		console.log("digital_read", pin);
		console.log(digital_inputs);
		return digital_inputs[parseInt(pin)];
	};

	ext.set_led_brightness = function(pin, brightness) {
		if (connected == false) {
			alert("Server Not Connected");
		}

		var msg = JSON.stringify({
			"command": 'led_brightness', 'pin': pin, 'brightness': brightness
		});
		sendMessage(msg);
	};

	ext.set_lantern_to_cycle = function() {
		if (connected == false) {
			alert("Server Not Connected");
		}
		var msg = JSON.stringify({
			"command": 'lantern_cycle_begin'
		});
		sendMessage(msg);
	};

	ext.pause_lantern_cycle = function() {
		if (connected == false) {
			alert("Server Not Connected");
		}
		var msg = JSON.stringify({
			"command": 'lantern_cycle_pause'
		});
		sendMessage(msg);
	};

	ext.set_train_switch = function(pin, direction) {
		if (connected == false) {
			alert("Server Not Connected");
		}
		var msg = JSON.stringify({
			"command": 'set_train_switch', "pin": pin, "direction": direction
		});
		sendMessage(msg);
	};

	ext.console_log = function(message) {
		if (connected == false) {
			alert("Server Not Connected");
		}
		var msg = JSON.stringify({
			"command": 'console_log', "message": message
		});
		sendMessage(msg);
	};

	ext.ir_sensor_activated = function() {
		if (ir_sensor_tripped) {
			console.log("********** Sensor tripped");
			return true;
		} else {
			console.log("++++++++++ Sensor deactivated");
			return false;
		}
	};

	ext.setup_ir_sensor = function(pin) {
		if (connected == false) {
			alert("Server Not Connected");
		}
		var msg = JSON.stringify({"command": 'configure_ir_sensor', "pin": pin});
		sendMessage(msg);
	};

	function validatePin(pin) {
		var rValue = true;
		if (pin === 'PIN') {
			alert("Insert a valid BCM pin number.");
			rValue = false;
		}
		else {
			var pinInt = parseInt(pin);
			if (pinInt < 0 || pinInt > 31) {
				alert("BCM pin number must be in the range of 0-31.");
				rValue = false;
			}
		}
		return rValue;
	}
	
	function validateConnection() {
		if (connected == false) {
			// alert("Server Not Connected");
		}
	}
	
	function sendMessage(msg) {
		console.log(msg);
		window.socket.send(msg);
	}
    
	ext.rotate_motor = function (dir, speed, steps) {
		validateConnection();
		console.log("rotate_motor");
		// alert("SPEED: '" + speed + "', DIR: '" + dir + "', STEPS: '" + steps + "'.");
		
		if (!motor_configured) {
			// alert("Configure motor with four pins before using it.");
			return;
		}
		
		if (steps < 1) {
			// alert("Steps must be > 0");
			return;
		}
		
		if (! (dir === 'cw' || dir === 'ccw')) {
			// alert("Direction must be 'cw' or 'ccw' (It is '" + dir + "'.)");
			return;
		}
		
		if (! (speed === 'slow' || speed === 'medium' || speed === 'fast' || speed === 'super fast')) {
			// alert("Speed must be 'slow', 'medium', or 'fast' (It is '" + speed + "'.)" );
			return;
		}
        
		var msg = JSON.stringify({
			"command": 'rotate_motor', 'speed': speed, 'dir': dir, 'steps': steps
		});
		sendMessage(msg);
	};
	
	ext.setup_motor = function (pin1, pin2, pin3, pin4) {
		var pinsValid = true;
		var pin1Int = parseInt(pin1);
		if (!validatePin(pin1Int)) {
			pinsValid = false;
		}
		var pin2Int = parseInt(pin2);
		if (!validatePin(pin2Int)) {
			pinsValid = false;
		}
		var pin3Int = parseInt(pin3);
		if (!validatePin(pin3Int)) {
			pinsValid = false;
		}
		var pin4Int = parseInt(pin4);
		if (!validatePin(pin4Int)) {
			pinsValid = false;
		}
		
		if (!pinsValid) { return; }
		
		var msg = JSON.stringify({
			"command": 'setup_motor', 'pin1': parseInt(pin1), 'pin2': parseInt(pin2), 'pin3': parseInt(pin3), 'pin4': parseInt(pin4)
		});
		sendMessage(msg);
		motor_configured = true;
	};
    
	// Block and block menu descriptions
	var descriptor = {
		blocks: [
			["w", 'Connect to felix server.', 'connect'],
			["w", 'Disconnect from felix server.', 'disconnect'],
			[" ", 'Set up stepper motor with GPIO pins %n, %n, %n, and %n', "setup_motor", "21", "20", "16", "12"],
			[" ", 'Set magic lantern brightness to %n (0-255)', "set_lantern_brightness", "100"],
			[" ", 'Cycle magic lantern', "set_lantern_to_cycle"],
			[" ", 'Pause magic lantern cycle', "pause_lantern_to_cycle"],
			[" ", 'Set LED on pin %n brightness to %n (0-255)', "set_led_brightness", "PIN", "100"],
			//                 "command": 'setup_motor', 'pin1': pin, 'pin2': pin, 'pin3': pin, 'pin4': pin,
			[" ", 'Rotate stepper motor %m.motor_direction at %m.motor_speed speed for %n steps', "rotate_motor", "DIR", "SPEED", 0],
			[" ", 'Set train switch on pin %n to %m.train_switch_direction', "set_train_switch", 23, "straight"],
			// 				   "command": 'rotate_motor', 'speed': speed, 'dir': dir
			//
			[" ", 'Set pin %n as an input', 'input','PIN'],
			[" ", 'Set up pin %n as an IR sensor', 'setup_ir_sensor','PIN'],
			//             [" ", "Set BCM %n Output to %m.high_low", "digital_write", "PIN", "0"],
			//             [" ", "Set BCM PWM Out %n to %n", "analog_write", "PIN", "VAL"],
			// [" ", "Set BCM %n as Servo with angle = %n (0° - 180°)", "servo", "PIN", "0"],     // ***Hackeduca --> Block for Servo
			//             [" ", "Tone: BCM %n HZ: %n", "play_tone", "PIN", 1000],
			["r", "Read pin %n", "digital_read", "PIN"],
			[" ", "Log %s to console", "console_log", "Hello, World!"],
			['h', 'When IR sensor detects something', 'ir_sensor_activated', "PIN"],
		],
		"menus": {
			"high_low": ["0", "1"],
			"motor_direction": ["cw", "ccw"],
			"motor_speed" : ["slow", "medium", "fast", "super fast"],
			"train_switch_direction" : ["straight", "turn"]
		},
		url: 'http://www.nowhereville.org'
	};
    
	// Register the extension
	ScratchExtensions.register('felix', descriptor, ext);
})({});

