"""
KY040 Python Class
Martin O'Hanlon
stuffaboutcode.com


Additional code added by Conrad Storz 2015 and 2016
"""

import RPi.GPIO as GPIO
from time import sleep


class KY040:

    CLOCKWISE = 0
    ANTICLOCKWISE = 1
    DEBOUNCE = 60

    def __init__(self, clockPin, dataPin, switchPin, rotaryCallback, switchCallback):
        #persist values
        self.clockPin = clockPin
        self.dataPin = dataPin
        self.switchPin = switchPin
        self.rotaryCallback = rotaryCallback
        self.switchCallback = switchCallback
        GPIO.setmode(GPIO.BCM)
        #setup pins
        GPIO.setup(clockPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(dataPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(switchPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def start(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.add_event_detect(self.clockPin, GPIO.FALLING, callback=self._clockCallback, bouncetime=self.DEBOUNCE)
        GPIO.add_event_detect(self.switchPin, GPIO.FALLING, callback=self.switchCallback, bouncetime=self.DEBOUNCE)
        GPIO.add_event_detect(self.dataPin, GPIO.FALLING, callback=self._dataCallback, bouncetime=self.DEBOUNCE)
    def stop(self):
        GPIO.remove_event_detect(self.clockPin)
        GPIO.remove_event_detect(self.switchPin)
        GPIO.cleanup()

    def _clockCallback(self, pin):
        clkState=GPIO.input(self.clockPin)
        dtState=GPIO.input(self.dataPin)
        print("CLK %d %d" %(clkState,dtState))
        if clkState == 0 and dtState==1:
            self.rotaryCallback(1)

    def _dataCallback(self,pin):
        clkState=GPIO.input(self.clockPin)
        dtState=GPIO.input(self.dataPin)
        print("DTA %d %d" %(clkState,dtState))
        if clkState==1 and dtState==0:
           self.rotaryCallback(0)

    def _switchCallback(self, pin):
        """
        if GPIO.input(self.switchPin) == 0:
            self.switchCallback()
        """
        self.switchCallback()

count0=0
count1=0
#test
if __name__ == "__main__":

    print( 'Program start.')

    CLOCKPIN = 27
    DATAPIN = 22
    SWITCHPIN = 24

    def rotaryChange(direction):
        global count0,count1
        print( "turned - " + str(direction))
        if (direction==1):
            count1+=1
        else:
            count0+=1
    def switchPressed(pin):
        print("button connected to pin:{} pressed".format(pin))


    ky040 = KY040(CLOCKPIN, DATAPIN, SWITCHPIN, rotaryChange, switchPressed)

    print( 'Launch switch monitor class.')

    ky040.start()
    print( 'Start program loop...')
    try:
        while True:
            sleep(10)
            print('Ten seconds...')
    finally:
        print( 'Stopping GPIO monitoring...')
        ky040.stop()
        GPIO.cleanup()
        print( 'Program ended. RESULT=%d%%' %round((count0/(count0+count1))*100))


