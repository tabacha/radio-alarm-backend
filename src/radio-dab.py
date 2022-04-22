#!/usr/bin/python3
import pika
import json
from radio_common import rabbit_send_action, AUDIO_INPUT_DEVICE, AUDIO_OUTPUT_DEVICE, load_from_json, save_json, cfg_logging
import time
import threading
import subprocess
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RADIO_ACTIONS_QUEUE="radio_actions"
RADIO_BROADCAST_EXCHANGE="radio_broadcast"
channel_file = '/var/run/radio-stations.json'
on=False
station=''
radio_stations={}
lock=threading.Lock()

def radio_cli(params, boot=False):
    global logger,lock

    args=[
        'radio_cli',
        '--format_json']
    if boot:
        args.append('--boot=D')
    args=args+params
    with lock:
        logger.info('radio_cli start [%s]' ,(','.join(args)))
        out_str = subprocess.run(args, capture_output=True)
        logger.info('radio_cli stdout: %s',out_str.stdout)
    rtn=json.loads(out_str.stdout)
    return rtn

def radio_off():
    radio_cli(['--shutdown'])

def radio_station(station):
    global radio_stations
    if not station in radio_stations:
        logger.error('Station %s not found in list [%s]' , (station,radio_stations.join(', ')))
        # FIXME Throw error
        return
    data = radio_stations[station]
    print('tune'+json.dumps(data))
    radio_cli([
        '-c',
        str(data['componentId']),
        '-f',
        str(data['frequencyIndex']),
        '-e',
        str(data['serviceId']),
        '-p',
        '-l',
        '50',
        '-o'
        '1'
    ], boot=True)

def radio_on_change():
    global on,station
    if on:
        radio_station(station)
    else:
        radio_off()

def radio_channel_serach():
    rtn = radio_cli([
        '--full_scan'
    ],boot=True)
    save_json(channel_file, rtn)
    return rtn


def convert_channel_data_to_station_list(channel_data):
    radio_list = {}
    for ensemble in channel_data['ensembleList']:
        if 'DigitalServiceList' in ensemble:
            if 'ServiceList' in ensemble['DigitalServiceList']:
                for service in ensemble['DigitalServiceList']['ServiceList']:
                    if service['AudioOrDataFlag']==0:
                        for component in service['ComponentList']:
                            if component['ps'] == 1:
                                label = service['Label'].strip()
                                if label in radio_list.keys():
                                    num = 0
                                    newlabel = "%s%d" % (label, num)
                                    while newlabel in radio_list:
                                        num = num+1
                                        newlabel = "%s%d" % (label, num)
                                    label = newlabel
                                radio_list[label] = {
                                    'serviceId': service['ServId'],
                                    'componentId': component['comp_ID'],
                                    'frequencyIndex': ensemble['EnsembleNo']
                                }
    return radio_list

def callback(ch, method, properties, body):
    global logger,on,station
    data=json.loads(body)
    logger.debug('recived %s',data)
    if (data['label']=='dab_data'):
        station=data['data']['station']
        on=data['data']['on']
        radio_on_change()
    if (data['label']=='radio_server_start'):
        rabbit_send_action('set_dab_station_list',{'st_list':list(radio_stations.keys())})


def start_service():
    global logger
    logger.info('Init')
    global radio_stations
    channel_data = load_from_json(channel_file, {})
    if len(channel_data.keys()) == 0:
        logger.info('inital channel search')
        channel_data = radio_channel_serach()
    else:
        logger.info('skipping inital channel search')
        # wait pika to start consuming
        time.sleep(1)
    radio_stations = convert_channel_data_to_station_list(channel_data)
    rabbit_send_action('radio_dab_start',{'station_list':list(radio_stations.keys())})

def main():
    global logger
    cfg_logging()
    logger.info('Start DAB')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='::1'))

    channel = connection.channel()
    channel.exchange_declare(exchange=RADIO_BROADCAST_EXCHANGE, exchange_type='fanout')

    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange=RADIO_BROADCAST_EXCHANGE, queue=queue_name)
    channel.basic_consume(
        queue=queue_name, on_message_callback=callback, auto_ack=True)
    t1=threading.Timer(0.5,start_service)
    t2=threading.Thread(target=channel.start_consuming)
    t2.start()
    t1.start()
    t1.join()
    t2.join()

main()
