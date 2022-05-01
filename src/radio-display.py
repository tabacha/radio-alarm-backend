#!/usr/bin/python3

import gpiodev
from time import sleep
import argparse
from datetime import datetime
from math import floor
from led_screen import StaticTitleMenuEntry, MenuEntryScreen, OnOffMenuEntry, ValueScreen, MainScreen
import re
from pprint import pprint

WOCHENTAG = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
WT_DATA = {"1": {"name": "Weckzeit 1", "time": "5:42", "active": True, "monday": True,
                 "tuesday": True, "wednesday": True, "thursday": True, "friday": True,
                 "saturday": False, "sunday": False, "once": False, "free": False, "not_free": False},
           "2": {"name": "Weckzeit 2", "time": "6:42", "active": False, "monday": True,
                 "tuesday": True, "wednesday": True, "thursday": True, "friday": True,
                 "saturday": False, "sunday": False, "once": False, "free": False, "not_free": False},
           "3": {"name": "Weckzeit 3", "time": "23:42", "active": False, "monday": True,
                 "tuesday": True, "wednesday": True, "thursday": True, "friday": True,
                 "saturday": False, "sunday": False, "once": False, "free": False, "not_free": False}}

def getSender():
    return ['NDR 2', 'NDR 90,3', 'Radio Hamburg']

def setSender(sender:str):
    print(sender)
    sleep(3)

def getLautstaerke()->int:
    return 12

def setLautstaerke(vol:int):
    print(vol)
    sleep(3)

def isRadioOn()->bool:
    return True

def schalteRadioAnAus(on:bool):
    print(on)
    sleep(3)

def getWackeupTime(idx:int):
    return WT_DATA["%d" % idx]

def setWackeupTime(idx:int,wt):
    print(idx)
    pprint(wt)
    sleep(6)

def doNothing():
    pass

def createUhrzeitMenu(dev, wzId:int):
    wt=getWackeupTime(wzId)
    res=re.search(r"^(\d+):(\d)(\d)$", wt['time'])
    h=int(res.group(1))
    dm=int(res.group(2))
    m=int(res.group(3))
    def setzeM(new_m:int):
        nonlocal m,dm,h
        m=new_m
        wt['time']="%d:%d%d" % (h,dm,m)
        setWackeupTime(wzId,wt)
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

WZ_I18N={
    'Montag':'monday',
    'Dienstag': 'tuesday',
    'Mittwoch': 'wednesday',
    'Donnerstag': 'thursday',
    'Freitag': 'friday',
    'Samstag': 'saturday',
    'Sonntag': 'sunday',
    '+ an fr. T': 'free',
    'Nicht fr. T.': 'not_free'
}

def createWeckzeitMenu(wzId:int,dev):
    wt=getWackeupTime(wzId)
    def toggleActive():
        nonlocal wt, wzId
        wt['active']!=wt['active']
        setWackeupTime(wzId,wt)

    def saveWzTag(tag,status):
        nonlocal wt, wzId
        wt[tag]=status
        setWackeupTime(wzId,wt)

    def saveEinmalig():
        nonlocal wzId,wt
        wt['once']=True
        for day in ["monday","tuesday","wednesday","thursday","friday",
                 "saturday", "sunday", "free", "not_free"]:
            wt[day]=False
        setWackeupTime(wzId,wt)

    uhrMenu=createUhrzeitMenu(dev,wzId)
    tag_arr=[]
    for tag in WZ_I18N.keys():
        day=WZ_I18N[tag]
        tag_arr.append(OnOffMenuEntry(tag, saveWzTag, status=wt[day],param=day))

    widerkehMenu=MenuEntryScreen(dev,tag_arr)
    if wt['once']:
        wtEinm=0
    else:
        wtEinm=1

    einMaligRegelmMenu=MenuEntryScreen(dev,[
            StaticTitleMenuEntry('Einmalig',saveEinmalig),
            StaticTitleMenuEntry('Wiederkehrend', widerkehMenu.run)
            ], add_back_entry=False,idx=wtEinm
        )
    wzMenu=MenuEntryScreen(dev,[
            StaticTitleMenuEntry('Zeit',uhrMenu.run),
            StaticTitleMenuEntry('Tage', einMaligRegelmMenu.run),
            OnOffMenuEntry('Aktiv',toggleActive,status=wt['active']),
        ])
    return wzMenu

def runSenderMenu(dev):
    menus=[]
    for sender in getSender():
        menus.append(StaticTitleMenuEntry(sender, setSender, param=sender))
    senderMenu=MenuEntryScreen(dev,menus)
    senderMenu.run()

def mainMenu(dev):
    volScreen=ValueScreen(dev,'Lautstärke',value=12,changeValueFunc=setLautstaerke)
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
        OnOffMenuEntry('Radio an/aus', schalteRadioAnAus, status=isRadioOn()),
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