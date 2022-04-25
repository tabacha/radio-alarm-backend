#!/usr/bin/python3

import gpiodev
import time
from copy import deepcopy

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
    def buttonFunc(self):
        pass

    def leftFunc(self):
        pass

    def rightFunc(self):
        pass

    def printScreen(self):
        pass

    def exitFunc(self):
        self.is_running=False

    def running(self)->bool:
        return self.is_running

    def run(self):
        self.is_running=True
        while self.running():
            self.printScreen()
            actionFunc= {
                gpiodev.GPIO_INPUT.BUTTON: self.buttonFunc,
                gpiodev.GPIO_INPUT.LEFT: self.leftFunc,
                gpiodev.GPIO_INPUT.RIGHT: self.rightFunc,
            }
            k=self.gpdev.wait_for_gpio_event()
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
            self.choices.append( StaticTitleMenuEntry('zurueck',self.exitFunc))
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

    def printScreen(self):
        for i in range(0,self.gpdev.get_number_of_lines()):
            if i+self.offset<len(self.choices):
                if (i+self.offset)==self.idx:
                    chooser='-> '
                else:
                    chooser='   '
                self.gpdev.write_display_line(i+1,chooser+self.choices[i+self.offset].getTitle())

class ValueScreen(AbstractGpioScreen):
    def __init__(self, gpdev:gpiodev.GPIOBaseDev, title:str, value:int, maxValue=100, suffix="%"):
        self.title=title
        self.maxValue=maxValue
        self.value=value
        self.suffix=suffix
        super().__init__(gpdev)

    def buttonFunc(self):
        self.is_running=False

    def leftFunc(self):
        if self.value>0:
            self.value-=1

    def rightFunc(self):
        if self.value<self.maxValue:
            self.value+=1

    def printScreen(self):
        self.gpdev.write_display_line(1,"%s %d %s" %(self.title,self.value,self.suffix))
        self.gpdev.write_display_line(2,"")
        self.gpdev.write_display_line(3,"")
        numChars=round(20*(self.value/self.maxValue))
        str=""
        for i in range(1,numChars):
            str=str+"*"
        self.gpdev.write_display_line(4,str)

def doNothing():
    pass

def setSender(sender):
    print(sender)
    time.sleep(3)

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
        time.sleep(2)
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
        time.sleep(1)
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
    volScreen=ValueScreen(dev,'Lautstaerke',value=12)
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

def main():
    myDev=gpiodev.TestGPIODev()
    mainMenu(myDev)

main()