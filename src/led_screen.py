from time import time
import gpiodev
from math import floor
from datetime import datetime,timedelta
WOCHENTAG=['Mo','Di','Mi','Do','Fr','Sa','So']

class AbstractMenuEntry():

    def getTitle(self)->str:
        pass
    def run(self):
        pass

class StaticTitleMenuEntry(AbstractMenuEntry):

    def __init__(self,title:str,action,param=None):
        self.myaction=action
        self.title=title
        self.param=param
    def getTitle(self)->str:
        return self.title

    def run(self):
        if self.param==None:
            self.myaction()
        else:
            self.myaction(self.param)

class OnOffMenuEntry(AbstractMenuEntry):

    def __init__(self,title:str,action=None, status=False,param=None):
        self.myaction=action
        self.title=title
        self.status=status
        self.param=param

    def getTitle(self)->str:
        if (self.status):
            return "[x] %s" % self.title
        else:
            return "[ ] %s" % self.title

    def run(self):
        self.status=not(self.status)
        if self.myaction:
            if self.param==None:
                self.myaction(self.status)
            else:
                self.myaction(self.param, self.status)


    def getStatus(self)->bool:
        return self.status

class AbstractGpioScreen():

    def __init__(self, gpdev:gpiodev.GPIOBaseDev):
        self.gpdev=gpdev
        self.is_running=True
        self.timeout_in_secs=120

    def buttonFunc(self):
        pass

    def leftFunc(self):
        pass

    def rightFunc(self):
        pass

    def timeoutFunc(self):
        pass

    def printScreen(self):
        pass


    def exitFunc(self):
        self.is_running=False

    def running(self)->bool:
        return self.is_running

    def run(self):
        self.is_running=True
        self.gpdev.clear()
        while self.running():
            self.printScreen()
            actionFunc= {
                gpiodev.GPIO_INPUT.BUTTON: self.buttonFunc,
                gpiodev.GPIO_INPUT.LEFT: self.leftFunc,
                gpiodev.GPIO_INPUT.RIGHT: self.rightFunc,
                gpiodev.GPIO_INPUT.TIMEOUT: self.timeoutFunc,
            }
            k=self.gpdev.wait_for_gpio_event(self.timeout_in_secs)
            actionFunc[k]()

class MenuEntryScreen(AbstractGpioScreen):

    def __init__(self, gpdev:gpiodev.GPIOBaseDev, choices:list, idx:int=0, add_back_entry=True):
        if idx>=len(choices):
            raise ValueError('idx out of range')
        self.is_running=True
        self.idx=idx
        if idx>2:
            self.offset=self.idx-2
        else:
            self.offset=0
        self.choices=choices
        self.add_back_entry=add_back_entry
        if (add_back_entry):
            self.choices.append( StaticTitleMenuEntry('zurück',self.exitFunc))
        super().__init__(gpdev)

    def buttonFunc(self):
        if (self.add_back_entry==False):
            self.exitFunc()
        self.choices[self.idx].run()

    def leftFunc(self):
        if self.idx>0:
            self.idx-=1
            if self.idx>2 and self.idx==len(self.choices)-1:
                self.offset=self.idx-3
            elif self.idx>1 and self.idx==len(self.choices)-2:
                self.offset=self.idx-2
            elif self.idx>1:
                self.offset=self.idx-1
            else:
                self.offset=0

    def rightFunc(self):
        if self.idx+1<len(self.choices):
            self.idx+=1
            if self.idx>2 and self.idx==len(self.choices)-1:
                self.offset=self.idx-3
            elif self.idx>2:
                self.offset=self.idx-2
            else:
                self.offset=0

    def timeoutFunc(self):
        self.exitFunc()

    def printScreen(self):
        self.gpdev.clear()
        for i in range(0,self.gpdev.get_number_of_lines()):
            if i+self.offset<len(self.choices):
                if (i+self.offset)==self.idx:
                    chooser=self.gpdev.get_pfeil_rechts()+' '
                else:
                    chooser='  '
                self.gpdev.write_display_line(i+1,chooser+self.choices[i+self.offset].getTitle())

class ValueScreen(AbstractGpioScreen):
    def __init__(self, gpdev:gpiodev.GPIOBaseDev, title:str, changeValueFunc, value:int, maxValue=100, suffix="%"):
        self.title=title
        self.maxValue=maxValue
        self.value=value
        self.suffix=suffix
        self.changeValueFunc=changeValueFunc
        super().__init__(gpdev)

    def buttonFunc(self):
        self.exitFunc()

    def leftFunc(self):
        if self.value>0:
            self.value-=1
            self.changeValueFunc(self.value)

    def rightFunc(self):
        if self.value<self.maxValue:
            self.value+=1
            self.changeValueFunc(self.value)

    def printScreen(self):
        self.gpdev.clear()
        self.gpdev.write_display_line(1,"%s %d %s" %(self.title,self.value,self.suffix))
        self.gpdev.write_display_line(2,"")
        self.gpdev.write_display_line(3,"")
        numFullChars=floor(20*(self.value/self.maxValue))
        lastChar=floor((100*(self.value/self.maxValue)) % (100/20))
        str=""
        for i in range(0,numFullChars):
            str=str+chr(5)
        if numFullChars<20:
            str=str+chr(lastChar)
            while len(str)<20:
                str=str+chr(0)
        self.gpdev.write_display_line(4,str)

class MainScreen(AbstractGpioScreen):
    def __init__(self, gpdev:gpiodev.GPIOBaseDev, getMainScreenData):
        super().__init__(gpdev=gpdev)
        self.timeout_in_secs=0.5
        self.night_mode_off_time_secs=60
        self.displayOn=True
        self.last_input_time=datetime.now()
        self.getMainScreenData=getMainScreenData

    def buttonFunc(self):
        if self.isDisplayOn(datetime.now()):
            self.exitFunc()
        else:
            self.last_input_time=datetime.now()

    def leftFunc(self):
        self.last_input_time=datetime.now()

    def rightFunc(self):
        self.last_input_time=datetime.now()

    def isNightMode(self,now:datetime):
        if now.hour<6:
            return True
        if now.hour==6 and now.minute<10:
            return True
        if now.hour>22:
            return True
        return False

    def isDisplayOn(self,now:datetime):
        if self.isNightMode(now):
            return (now.timestamp()-self.last_input_time.timestamp())<self.night_mode_off_time_secs
        else:
            return True

    def printScreen(self):
        # datetime object containing current date and time
        now = datetime.now()
        if self.isDisplayOn(now):
            self.gpdev.backlight(True)
            weekday=WOCHENTAG[now.weekday()]
            if (now.second==0):
                self.gpdev.clear()
            t_string = now.strftime("%H:%M:%S")
            d_string = now.strftime("%d.%m.%y")
            self.gpdev.write_display_line(1,"%s %s %s" %(t_string, weekday, d_string))
            data=self.getMainScreenData()
            if data==None:
                self.gpdev.write_display_line(2, ". . .")
                self.gpdev.write_display_line(3, "..starte")
                self.gpdev.write_display_line(4, " Display...")
            else:
                if (data['radioOn']):
                    radioLine="%s %s" % (data['station'],data['song'])
                else:
                    radioLine=""
                self.gpdev.write_display_line(2,radioLine)
                if data['nextWakeupTime']==None:
                    self.gpdev.write_display_line(3,chr(6)+" keine neue Weckzeit")
                    self.gpdev.write_display_line(4,"")
                else:
                    naechsterWecker:datetime=data['nextWakeupTime']
                    weckzeit=naechsterWecker.strftime('%H:%M')
                    weckWT=WOCHENTAG[naechsterWecker.weekday()]
                    weckdatum=naechsterWecker.strftime('%d.%m.%y')
                    delta_s=naechsterWecker.timestamp()-datetime.now().timestamp()
                    self.gpdev.write_display_line(3,"%s%s %s %s" % (chr(6),weckzeit,weckWT,weckdatum))

                delta_days=(delta_s//(24*60*60))
                delta_hours=(delta_s // (60*60)) % 24
                delta_min=(delta_s // 60) % 60

                if delta_days>0:
                    delta_str='%d Tagen ' % (delta_days)
                else:
                    delta_str=""
                delta_str="in %s%dh %dm" % (delta_str, delta_hours, delta_min)
                self.gpdev.write_display_line(4,delta_str)
        else:
            self.gpdev.backlight(False)
