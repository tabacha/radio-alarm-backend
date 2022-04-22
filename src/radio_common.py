#!/usr/bin/python3
import json
import pika
import logging

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
    pass