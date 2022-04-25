#!/usr/bin/python3
import evdev
import json
import requests
import logging
import radio_common
logger = logging.getLogger(__name__)

radio_common.cfg_logging()

base_url="http://127.0.0.1:4999/"
vol_up_url="%s/api/audio/volumestep/up" % base_url
vol_down_url="%s/api/audio/volumestep/down" % base_url
toggle_dab_url="%s/api/toggle/dab" % base_url

print(vol_down_url)
print(vol_up_url)
print(toggle_dab_url)

MY_DEVICE='USB  AUDIO  '
pathes=evdev.list_devices()
for path in pathes:
    device = evdev.InputDevice(path)
    if device.name == MY_DEVICE:
        for event in device.read_loop():
            if event.type == evdev.ecodes.EV_KEY:
                ke=evdev.events.KeyEvent(event)
                print(ke)
                if ke.keystate == ke.key_up:
                    if ke.scancode == evdev.ecodes.KEY_MUTE:
                        requests.get(toggle_dab_url)
                    if ke.scancode == evdev.ecodes.KEY_VOLUMEUP:
                        requests.get(vol_up_url)
                    if ke.scancode == evdev.ecodes.KEY_VOLUMEDOWN:
                        requests.get(vol_down_url)
