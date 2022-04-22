#!/usr/bin/python3

from flask import Flask,g
from flask_httpauth import HTTPBasicAuth
from flask_restful import reqparse, Resource, Api, abort
import json
import pika
import time
import logging
from threading import Thread
from pkg_resources import require
from radio_common import rabbit_send_action, cfg_logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


RADIO_BROADCAST_EXCHANGE="radio_broadcast"
RADIO_ACTIONS_QUEUE="radio_actions"

auth = HTTPBasicAuth()
app = Flask('radio-server')
api = Api(app)
radio_stations=[]
ctx_data = None
users = {
    "api":  "hello"
}

def write_cfg():
    global ctx_data
    rabbit_send_action('save',{'data':ctx_data})


@auth.get_password
def get_pw(username):
    if username in users:
        return users[username]
    return None


class AudioVolumeApi(Resource):
    # @auth.login_required
    def get(self):
        return {
            'volume': ctx_data['volume']
        }

    # @auth.login_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('volume', type=int, required=True)
        parser.add_argument('smooth', type=bool, default=True)
        args = parser.parse_args()
        if args['volume'] < 0 or args['volume'] > 100:
            message = "Expected 0 <= value <= 100, got value = {}".format(
                args['volume'])
            return {'error': message}, 400
        # else
        new_vol = args['volume']
        rabbit_send_action('set_volume',{'volume': new_vol, 'smooth': args['smooth']})

        return {
            'saved': True
        }

class RadioTunerList(Resource):
    # @auth.login_required
    def get(self):
        global radio_stations
        return radio_stations

    def post(self):
        rabbit_send_action('start_radio_station_search',{})
        return {'radio_station_search_stated'}


class RadioState(Resource):
    # @auth.login_required
    def get(self):
        global ctx_data
        return {
            'on': ctx_data['on'],
            'station': ctx_data['station'],
        }

    def post(self):
        global ctx_data, radio_stations
        parser = reqparse.RequestParser()
        parser.add_argument('on', type=bool)
        parser.add_argument('station', choices=radio_stations)
        args = parser.parse_args()
        rabbit_send_action('set_radio_state',{'on':args['on'],'station':args['station']})
        return {
            'on': ctx_data['on'],
            'station': ctx_data['station'],
        }

class WakeupTime(Resource):
    def get(self, id: int):
        global ctx_data
        if str(id) in ctx_data['wakeup_times'].keys():
            return ctx_data['wakeup_times'][str(id)]
        abort(404, message="WakeupTime {} doesn't exist".format(id))

    def delete(self, id: int):
        global ctx_data
        if str(id) in ctx_data['wakeup_times']:
            del ctx_data['wakeup_times'][str(id)]
            write_cfg()
            return '', 204
        abort(404, message="WakeupTime {} doesn't exist".format(id))

    def post(self, id: int):
        global ctx_data
        parser = reqparse.RequestParser()
        parser.add_argument('name')
        parser.add_argument('time', required=True)
        parser.add_argument('active', type=bool, required=True)
        parser.add_argument('monday', type=bool, default=False)
        parser.add_argument("tuesday", type=bool, default=False)
        parser.add_argument("wednesday", type=bool, default=False)
        parser.add_argument("thursday", type=bool, default=False)
        parser.add_argument("friday", type=bool, default=False)
        parser.add_argument("saturday", type=bool, default=False)
        parser.add_argument("sunday", type=bool, default=False)
        parser.add_argument('once', type=bool, default=False)
        parser.add_argument('free', type=bool, default=False)
        parser.add_argument('not_free', type=bool, default=False)
        args = parser.parse_args()
        if id == -1:
            id = max(list(map(int,ctx_data['wakeup_times'].keys())))+1
        ctx_data['wakeup_times'][str(id)] = args
        write_cfg()
        return ctx_data['wakeup_times'][str(id)]

class WakeupTimeList(Resource):
    def get(self):
        return ctx_data['wakeup_times']

@app.route('/api/audio/volumestep/up')
def volume_up():
    global ctx_data
    if ctx_data['volume'] < 100:
        rabbit_send_action('set_volume',{'volume':ctx_data['volume']+1, 'smooth':False})
    return {'send': True}

@app.route('/api/audio/volumestep/down')
def volume_down():
    global ctx_data
    if ctx_data['volume'] > 0:
        rabbit_send_action('set_volume',{'volume':ctx_data['volume']-1, 'smooth':False})
    return {'send': True}


@app.route('/api/toggle/dab')
def toggle_power():
    global ctx_data
    rabbit_send_action('set_radio_state',{'on':not(ctx_data['on']),'station':ctx_data['station']})
    return {'on': ctx_data['on']}

api.add_resource(AudioVolumeApi, '/api/audio/volume/')
api.add_resource(RadioTunerList, '/api/dab/stations/')
api.add_resource(RadioState, '/api/dab/')
api.add_resource(WakeupTime, '/api/wakeup/<int:id>')
api.add_resource(WakeupTimeList, '/api/wakeup_times')

def callback(ch, method, properties, body):
    global ctx_data,radio_stations
    logger.info('Callback %s', body)
    data=json.loads(body)
    if (data['label']=='radio_station_list'):
        radio_stations=data['data']
        logger.debug('New Radio Stations=%s',radio_stations)
    if (data['label']=='ctx_data'):
        new_ctx_data=data['data']
        ctx_data=new_ctx_data

def init():
    global radio_stations,ctx_data
    cfg_logging()
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='::1'))

    channel = connection.channel()
    channel.exchange_declare(exchange=RADIO_BROADCAST_EXCHANGE, exchange_type='fanout')

    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange=RADIO_BROADCAST_EXCHANGE, queue=queue_name)
    channel.basic_consume(
        queue=queue_name, on_message_callback=callback, auto_ack=True)
    print('start thread')
    thread = Thread(target=channel.start_consuming,daemon=True)
    thread.start()
    time.sleep(1)
    rabbit_send_action('radio_api_start',None)
    while ctx_data==None:
        print('wait')
        time.sleep(1)

init()

if __name__ == '__main__':
    app.run(host='::', port=4999)
