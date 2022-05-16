#!/usr/bin/python3
import json
import pika
import logging
from datetime import datetime,timedelta
from calendar import day_name

logger = logging.getLogger(__name__)

AUDIO_INPUT_DEVICE="dabboard"
AUDIO_OUTPUT_DEVICE = "AUDIO"

RADIO_ACTIONS_QUEUE="radio_actions"

def rabbit_send_action(method:str,data:any):
    global logger
    logger.info('rabbit_send_action %s %s', method, json.dumps(data))
    message=json.dumps({
            'method': method,
            'data': data
    })
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='::1'))
    channel = connection.channel()
    channel.queue_declare(queue=RADIO_ACTIONS_QUEUE, durable=True)

    channel.basic_publish(
        exchange='',
        routing_key=RADIO_ACTIONS_QUEUE,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
        ))
    connection.close()


def save_json(filename: str, data: dict):
    with open(filename, 'w') as outfile:
        json.dump(data, outfile)

def load_from_json(filename: str, defaultValues: dict):
    global logger
    logger.info('load_from_json %s',filename)
    try:
        with open(filename) as json_file:
            data = json.load(json_file)
    except:
        data = {}
    changed = True
    for key in defaultValues.keys():
        if not key in data:
            logger.info('not in loaded data, using default vaules %s',key)
            data[key] = defaultValues[key]
            changed = True
    if changed:
        save_json(filename, data)
    return data

def cfg_logging():
    logging.basicConfig(level=logging.INFO)

def next_weekday(start_date:datetime, weekday)->datetime:
    days_ahead = weekday - start_date.weekday()
    if days_ahead <= 0: # Target day already happened this week
        days_ahead += 7
    return start_date + datetime.timedelta(days_ahead)

def get_next_alarm_time(alarm_time, start_dt:datetime=datetime.now())->datetime:
    if (not(alarm_time['active'])):
        return None
    hour=int(alarm_time['time'].split(':')[0])
    min=int(alarm_time['time'].split(':')[1])
    # War es am start_dt schon alarm zeit?
    if ((start_dt.hour > hour) or
        ((start_dt.hour == hour) and (start_dt.minute>min)) or
        ((start_dt.hour == hour) and (start_dt.minute==min) and (start_dt.second+start_dt.microsecond>0))):
        # Ja also nächster Alarm frühestens morgen um Alarm Zeit
        start_dt=start_dt+timedelta(1)
    # else:
    # Tag ist heute um alarmzeit

    start_dt=start_dt.replace(hour=hour,minute=min,second=0, microsecond=0)

    if alarm_time['once']:
        return start_dt
    #else:
    for days_ahead in range(7):
        test_day=start_dt+timedelta(days_ahead)
        lower_day_name=day_name[test_day.weekday()].lower()
        if (alarm_time[lower_day_name]==True):
            return test_day
    return None
