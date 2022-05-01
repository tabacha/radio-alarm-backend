#!/usr/bin/python3

import gpiodev
from time import sleep
import argparse
from datetime import datetime
from math import floor
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
                self.myaction()
            else:
                self.myaction(self.param)


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
    def __init__(self, gpdev:gpiodev.GPIOBaseDev, title:str, value:int, maxValue=100, suffix="%"):
        self.title=title
        self.maxValue=maxValue
        self.value=value
        self.suffix=suffix
        super().__init__(gpdev)

    def buttonFunc(self):
        self.exitFunc()

    def leftFunc(self):
        if self.value>0:
            self.value-=1

    def rightFunc(self):
        if self.value<self.maxValue:
            self.value+=1

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
    def __init__(self, gpdev:gpiodev.GPIOBaseDev):
        super().__init__(gpdev=gpdev)
        self.timeout_in_secs=0.5
        self.night_mode_off_time_secs=60
        self.displayOn=True
        self.last_input_time=datetime.now()

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
            naechsterWecker='06:10 Mo. 10.05.22'
            self.gpdev.write_display_line(2,"Nächster Wecker"+chr(6))
            self.gpdev.write_display_line(3,"%s" % (naechsterWecker))
            self.gpdev.write_display_line(4,"in 3h 10m + 55 Tagen")
        else:
            self.gpdev.backlight(False)

def doNothing():
    pass

def setSender(sender):
    print(sender)
    sleep(3)

def saveEinmalig(wzId:int):
    pass

def createUhrzeitMenu(dev, wzId:int):
    h=6
    dm=4
    m=2
    def setzeM(new_m:int):
        nonlocal m
        m=new_m
    def setzeDM(new_dm:int):
        nonlocal h,dm
        dm=new_dm
        m_arr=[]
        for i in range(0,10):
            m_arr.append(StaticTitleMenuEntry('%d:%d%d Uhr'% (h,dm,i),setzeM, param=i))
        mMenu=MenuEntryScreen(dev,m_arr,idx=m,add_back_entry=False)
        mMenu.run()

    def setzeH(new_h:int):
        nonlocal h,dm
        print(new_h)
        sleep(2)
        h=new_h
        dm_arr=[]
        for i in range(0,6):
            dm_arr.append(StaticTitleMenuEntry('%d:%dx Uhr'% (h,i),setzeDM, param=i))
        dmMenu=MenuEntryScreen(dev,dm_arr,idx=dm,add_back_entry=False)
        dmMenu.run()

    h_arr=[]
    for i in range(0,24):
        h_arr.append(StaticTitleMenuEntry('%d:xx Uhr' % i,setzeH, param=i))
    hMenu=MenuEntryScreen(dev,h_arr, idx=h,add_back_entry=False)
    return hMenu


def createWeckzeitMenu(wzId:int,dev):
    def saveWzTag(tag):
        nonlocal wzId
        print("%s %d" %(tag,wzId))
        sleep(1)
    uhrMenu=createUhrzeitMenu(dev,wzId)
    tag_arr=[]
    for tag in ['Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag','Sonntag']:
        tag_arr.append(OnOffMenuEntry(tag, saveWzTag, status=True,param=tag))
    for tag in ['Samstag','Sonntag']:
        tag_arr.append(OnOffMenuEntry(tag, saveWzTag, status=False,param=tag))

    tag_arr.append(OnOffMenuEntry('+ an fr. T', saveWzTag, status=False,param='frei'))
    tag_arr.append(OnOffMenuEntry('Nicht fr. T.', saveWzTag, status=False,param='Nicht_frei'))
    widerkehMenu=MenuEntryScreen(dev,tag_arr)
    einMaligRegelmMenu=MenuEntryScreen(dev,[
            StaticTitleMenuEntry('Einmalig',lambda: saveEinmalig(wzId)),
            StaticTitleMenuEntry('Wiederkehrend', widerkehMenu.run)
            ], add_back_entry=False
        )
    wzMenu=MenuEntryScreen(dev,[
            StaticTitleMenuEntry('Zeit',uhrMenu.run),
            StaticTitleMenuEntry('Tage', einMaligRegelmMenu.run),
            OnOffMenuEntry('Aktiv',lambda: setSender('aktiv %d' % wzId)),
        ])
    return wzMenu

def runSenderMenu(dev):
    senderMenu=MenuEntryScreen(dev,[
        StaticTitleMenuEntry('NDR 2',lambda: setSender('NDR2')),
        StaticTitleMenuEntry('NDR 90,3',lambda: setSender('NDR903')),
        StaticTitleMenuEntry('Radio Hamburg',lambda: setSender('RHH')),
    ])
    senderMenu.run()

def mainMenu(dev):
    volScreen=ValueScreen(dev,'Lautstärke',value=12)
    wzAuswahlMenuEntries=[]
    for wzId in range(1,4):
        wzMenu=createWeckzeitMenu(wzId,dev)
        wzAuswahlMenuEntries.append(
            StaticTitleMenuEntry('Weckzeit %d' %wzId,wzMenu.run),
        )
    wzAuwahlMenu=MenuEntryScreen(dev,wzAuswahlMenuEntries)
    menuList=[
        StaticTitleMenuEntry('Lautstärke',volScreen.run),
        StaticTitleMenuEntry('Sender',lambda: runSenderMenu(dev)),
        StaticTitleMenuEntry('Weckzeit',wzAuwahlMenu.run),
        OnOffMenuEntry('Radio an/aus', doNothing),
    ]
    m=MenuEntryScreen(dev,menuList)
    m.run()

def mainScreen(dev):
    while True:
        ms=MainScreen(dev)
        ms.run()
        mainMenu(dev)

def main():
    parser = argparse.ArgumentParser(description='Test GPIO Menu')
    parser.add_argument('--hardware', help='Use Hardware GPIO', action='store_const',
                    const=True, default=False)
    args=parser.parse_args()
    if args.hardware:
        myDev=gpiodev.RealGPIODev(addr=0x27,bus=1)
    else:
        myDev=gpiodev.TestGPIODev()
    mainScreen(myDev)

main()