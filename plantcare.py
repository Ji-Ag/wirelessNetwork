import RPi.GPIO as GPIO
import time
import Adafruit_DHT
import math
import threading
import paho.mqtt.client as mqtt
import json
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)       # GPIO BCM 모드 설정    

#mqtt
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("connected OK")
    else:
        print("Bad connection Returned code=", rc)


def on_disconnect(client, userdata, flags, rc=0):
    print(str(rc))


def on_publish(client, userdata, mid):
    print("In on_pub callback mid= ", mid)


# 새로운 클라이언트 생성
client = mqtt.Client()
# 콜백 함수 설정 on_connect(브로커에 접속), on_disconnect(브로커에 접속중료), on_publish(메세지 발행)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish
# address : localhost, port: 1883 에 연결
client.connect('172.30.1.58', 1883)
client.loop_start()


# 빨, 주, 노, 초, 파, 남, 보
#Red-설정온도초과, Orange-설정습도초과, Blue-물주는날, Green-정상상태

colors = [0xFF0000, 0xFF0023, 0xFF00FF, 0x0000FF, 0x00FF00, 0x64EB00, 0x4BFB00]

pins = {'pin_R':11, 'pin_G':9, 'pin_B':10}  # 핀 지정

for i in pins:

    GPIO.setup(pins[i], GPIO.OUT)   # 핀 모드를 출력으로 설정

    GPIO.output(pins[i], GPIO.HIGH) # LED를 HIGH로 설정해서 LED 끄기

 

p_R = GPIO.PWM(pins['pin_R'], 2000)  # 주파수 설정 2KHz

p_G = GPIO.PWM(pins['pin_G'], 2000)

p_B = GPIO.PWM(pins['pin_B'], 2000)

p_R.start(0)      # 초기 듀티 사이클 = 0 (LED 끄기)

p_G.start(0)

p_B.start(0)

 

def map(x, in_min, in_max, out_min, out_max):

    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

 

# LED 색을 설정하는 함수

def setColor(col):   # 예)  col = 0x112233

    R_val = (col & 0x110000) >> 16

    G_val = (col & 0x001100) >> 8

    B_val = (col & 0x000011) >> 0

 

    R_val = map(R_val, 0, 255, 0, 100)

    G_val = map(G_val, 0, 255, 0, 100)

    B_val = map(B_val, 0, 255, 0, 100)

 

    p_R.ChangeDutyCycle(100-R_val)     # 듀티 사이클 변경

    p_G.ChangeDutyCycle(100-G_val)

    p_B.ChangeDutyCycle(100-B_val)

#7세그먼트 날짜 카운트
day = 0
segments =  (5,4,23,8,7,6,18,25)
# 7seg_segment_pins (11,7,4,2,1,10,5,3) +  100R inline
 
for segment in segments:
    GPIO.setup(segment, GPIO.OUT)
    GPIO.output(segment, 0)
 
# GPIO ports for the digit 0-3 pins 
digits = (22,27,17,24)
# 7seg_digit_pins (12,9,8,6) digits 0-3 respectively
 
for digit in digits:
    GPIO.setup(digit, GPIO.OUT)
    GPIO.output(digit, 1)
 
num = {' ':(0,0,0,0,0,0,0,0),
    '0':(1,1,1,1,1,1,0,1),
    '1':(0,1,1,0,0,0,0,1),
    '2':(1,1,0,1,1,0,1,0),
    '3':(1,1,1,1,0,0,1,1),
    '4':(0,1,1,0,0,1,1,1),
    '5':(1,0,1,1,0,1,1,1),
    '6':(0,0,1,1,1,1,1,1),
    '7':(1,1,1,0,0,0,0,1),
    '8':(1,1,1,1,1,1,1,1),
    '9':(1,1,1,0,0,1,1,1)}

class DayCounter(threading.Thread):
	def __init__(self,name):
		super().__init__()
		self.name = name
		
	def run(self):
		try:
			while True:
				n = day
				s = str(n).rjust(4)
				for digit in range(4):
					for loop in range(0,7):
						GPIO.output(segments[loop], num[s[digit]][loop])
					GPIO.output(digits[digit], 0)
					time.sleep(0.001)
					GPIO.output(digits[digit], 1)
		except KeyboardInterrupt: 
			print('daycounting over')

t1 = DayCounter("1")
t1.start()

#온습도
sensor = Adafruit_DHT.DHT11
pin=2
humidity, temperature = Adafruit_DHT.read_retry(sensor,pin)
def temphum():
	if humidity is not None and temperature is not None:
		print('온도 : {0:0.1f}*C 습도 : {1:0.1f}%'.format(temperature,humidity))
		client.publish('temp', json.dumps(temperature))
		client.publish('hum',json.dumps(humidity))
		client.publish('else',json.dumps(100-humidity))
	if temperature < 22:
		setColor(colors[1])
	else:
		print('온습도측정 실패')

try: 
	water = 0
	client.publish('name', json.dumps("basil"), 1)
	while True:
		client.publish('dday', json.dumps(day+1), 1)
		if(water == 2):
			client.publish('water', json.dumps("Needs water!!"), 1)
			water = 0
			day = day+1
			setColor(colors[4])
			for i in range(1,11):
				temphum()
				time.sleep(1)
				print(i)
				
		client.publish('water', json.dumps("Not thirsty"), 1)
		client.publish('dday', json.dumps(day+1), 1)
		setColor(colors[3])
		water=water+1
		day= day+1
		for i in range(1,11):
				temphum()
				time.sleep(1)
				print(i)
            

except KeyboardInterrupt:                # Ctrl+c로 종료

    p_R.stop()

    p_G.stop()

    p_B.stop()

    for i in pins:

        GPIO.output(pins[i], GPIO.HIGH)    #LED 끄기

        GPIO.cleanup()
