#!/usr/bin/python3

import pika
import json
import secrets
from radio_common import load_from_json, save_json, cfg_logging
import threading
import logging

logger = logging.getLogger(__name__)
RADIO_ACTIONS_QUEUE="radio_actions"
RADIO_BROADCAST_EXCHANGE="radio_broadcast"
DATA_FILENAME="/usr/share/radio/radio-server/ctx_data.json"
ctx_data={}
radio_station_list=[]

default_data = {
    'volume': 42,
    'password': secrets.token_urlsafe(16),
    'on': False,
    'station': '',
    'wakeup_times': {
        1: {
            "name": "Weckzeit 1",
            "time": "5:42",
            "active": False,
            "monday": True,
            "tuesday": True,
            "wednesday": True,
            "thursday": True,
            "friday": True,
            "saturday": False,
            "sunday": False,
            "once": False,
            "free": False,
            "not_free": False
        },
        2: {
            "name": "Weckzeit 2",
            "time": "6:42",
            "active": False,
            "monday": True,
            "tuesday": True,
            "wednesday": True,
            "thursday": True,
            "friday": True,
            "saturday": False,
            "sunday": False,
            "once": False,
            "free": False,
            "not_free": False
        },
        3: {
            "name": "Weckzeit 3",
            "time": "23:42",
            "active": False,
            "monday": True,
            "tuesday": True,
            "wednesday": True,
            "thursday": True,
            "friday": True,
            "saturday": False,
            "sunday": False,
            "once": False,
            "free": False,
            "not_free": False
        }
    }
}



def send_broadcast(label:str,data:any, changed=True):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='::1'))
    channel = connection.channel()

    channel.exchange_declare(exchange=RADIO_BROADCAST_EXCHANGE, exchange_type='fanout')

    message = json.dumps({
        'label': label,
        'data': data,
        'changed': changed
    })
    channel.basic_publish(exchange=RADIO_BROADCAST_EXCHANGE, routing_key='', body=message)
    connection.close()

def radio_api_start():
    global ctx_data,radio_station_list
    send_broadcast('radio_station_list', radio_station_list, False)
    send_broadcast('ctx_data', ctx_data, False)


def save(data):
    global ctx_data
    save_json(DATA_FILENAME, data)
    ctx_data=data
    send_broadcast('ctx_data', ctx_data, True)

def set_volume(volume:int, smooth: bool):
    global ctx_data,logger
    logger.info('set_volume %d' ,volume)
    if (volume>=0) and (volume<=100) and (volume!=ctx_data['volume']):
        ctx_data['volume']=volume
        send_broadcast('volume_changed',{ 'volume':volume, 'smooth': smooth})
        save(ctx_data)

def set_on_status(on:bool):
    global ctx_data,logger
    logger.info('set_on_status %s',on)
    if (ctx_data['on']!=on):
        ctx_data['on']=on
        send_broadcast('radio_state_changed',{'on':ctx_data['on'],'station':ctx_data['station']})
        save(ctx_data)

def set_dab_station_list(st_list:list):
    global radio_station_list
    radio_station_list=st_list
    send_broadcast('radio_station_list', st_list)

def radio_audio_start():
    global ctx_data
    send_broadcast('audio_data', {
        'on':ctx_data['on'],
        'volume':ctx_data['volume']
        })
def radio_dab_start(station_list):
    global ctx_data,radio_station_list
    radio_station_list=station_list
    send_broadcast('dab_data', {
        'on':ctx_data['on'],
        'station': ctx_data['station']
    })
    send_broadcast('radio_station_list', radio_station_list)

def set_radio_state(on, station):
    global ctx_data,radio_station_list
    changed=False

    if ctx_data['on']!=on:
        ctx_data['on']=on
        changed=True
    if ctx_data['station']!=station:
        ctx_data['station']=station
        changed=True
    if changed:
        send_broadcast('dab_data', {
            'on':ctx_data['on'],
            'station': ctx_data['station']
        })
        save(ctx_data)


RABBIT_METHODS={
    'save': save,
    'set_volume': set_volume,
    'radio_dab_start': radio_dab_start,
    'radio_api_start': radio_api_start,
    'radio_audio_start': radio_audio_start,
    'set_radio_state': set_radio_state,
    'set_dab_station_list': set_dab_station_list,
}

def callback(channel, method, properties, body:bytes):
    global logger
    logger.info('rabbit_recv %s %s', method, body)
    body_object=json.loads(body)
    method_str=body_object['method']
    if method_str in RABBIT_METHODS:
        myfunc=RABBIT_METHODS[method_str]

        if myfunc.__code__.co_argcount==0:
            myfunc()
        else:
            myargs=[]
            for varname in myfunc.__code__.co_varnames:
                if (len(myargs)<myfunc.__code__.co_argcount):
                    if varname in body_object['data']:
                        myargs.append(body_object['data'][varname])
                    else:
                        logger.error('rabbit_callback: varname %s not found' ,varname)
                        myargs.append(None)
            myfunc(*myargs)
    else:
        logger.error('Method "%s" not found', method_str)

    channel.basic_ack(delivery_tag=method.delivery_tag)

def start_service():
    send_broadcast('radio_server_start', None)

def main():
    global ctx_data
    cfg_logging()
    ctx_data = load_from_json(DATA_FILENAME, default_data)

    connection = pika.BlockingConnection(pika.ConnectionParameters(host='::1'))
    channel = connection.channel()
    channel.queue_declare(queue=RADIO_ACTIONS_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=RADIO_ACTIONS_QUEUE, exclusive=True, on_message_callback=callback)
    t1=threading.Timer(1,start_service)
    t2=threading.Thread(target=channel.start_consuming)
    t2.start()
    t1.start()
    t1.join()
    t2.join()

main()