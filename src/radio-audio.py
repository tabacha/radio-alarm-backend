#!/usr/bin/python3
import pika
import json
from radio_common import rabbit_send_action, AUDIO_INPUT_DEVICE, AUDIO_OUTPUT_DEVICE, cfg_logging
import time
import alsaaudio
import threading
import logging

logger = logging.getLogger(__name__)
RADIO_ACTIONS_QUEUE="radio_actions"
RADIO_BROADCAST_EXCHANGE="radio_broadcast"
SMOOTH_TIMEOUT=0.1
volume=-1
mixer=None
arecord=None
state=False

#def startRadioAudio():
#    global arecord
#    global aplay
#    arecord = subprocess.Popen(('/usr/bin/arecord', '-D','sysdefault:CARD=dabboard','-c','2','-r', '48000', '-f', 'S16_LE'), stdout=subprocess.PIPE)
#    aplay = subprocess.Popen(('/usr/bin/aplay', '-D',AUDIO_VOL_DEVICE+',DEV=0'), stdin=arecord.stdout)


rate=[0,0]
alsa_state='OFF'
alsa_state_changed=int(time.time())
alsaloop_run=False

def findAlsaCardIndex(cardname):
    return alsaaudio.cards().index(cardname)

def alsaloop():
    global alsaloop_run
    while alsaloop_run:
        logger.info('Loop started')
        try:
            alsaloop_func()
        except Exception as e:
          logger.exception(e)

def alsaloop_func():
    global rate,alsa_state,alsa_state_changed,alsaloop_run,AUDIO_INPUT_DEVICE,AUDIO_OUTPUT_DEVICE
    logger.info('alsa_loop func start')
    idx_in=findAlsaCardIndex(AUDIO_INPUT_DEVICE)
    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL,
		        cardindex=idx_in)
    inp.setchannels(2)
    inp.setrate(48000)
    inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    inp.setperiodsize(1600)
    idx_out=findAlsaCardIndex(AUDIO_OUTPUT_DEVICE)
    out = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, cardindex=idx_out)
    out.setchannels(2)
    out.setrate(48000)
    out.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    out.setperiodsize(1600)
    moduloVar=0
    rate=[0,0]
    alsa_state='INIT'
    alsa_state_changed=int(time.time())
    while alsaloop_run:
        length, data = inp.read()
        out.write(data)
        looptime=int(time.time())
        newModuloVar=looptime % 2
        if moduloVar!=newModuloVar:
            if (rate[moduloVar]>182000):
                if  (alsa_state!='OK'):
                    alsa_state_changed=looptime
                alsa_state='OK'
            elif alsa_state=='OK':
                alsa_state='FEHLER'
                alsa_state_changed=looptime
            moduloVar=newModuloVar
            rate[moduloVar]=0
        rate[moduloVar]+=length
    logger.info('alsa_loop funct stop')
    inp.close()
    out.close()
    alsa_state='OFF'

alsaThread=None
def startAlsaLoop():
    global rate,state,state_changed,alsaThread,alsaloop_run
    if alsaThread==None:
        logger.info('start thread')
        rate=[0,0]
        alsa_state='INIT'
        alsa_state_changed=int(time.time())
        alsaloop_run=True
        alsaThread = threading.Thread(target=alsaloop, daemon=True)
        alsaThread.start()
        logger.info('start done')

def stopAlsaLoop():
    global rate,alsa_state,alsa_state_changed,alsaThread,alsaloop_run
    alsaloop_run=False
    time.sleep(1)
    if alsaThread!=None:
        alsaThread.join()
    alsaThread=None

def createMixer():
    cardname=AUDIO_OUTPUT_DEVICE
    cardindex=alsaaudio.cards().index(cardname)
    return alsaaudio.Mixer('PCM',cardindex=cardindex)

def set_volume(new_volume:int, smooth:bool):
    global volume
    logger.info('set vol %d', new_volume)
    mixer.setmute(0)
    if smooth:
        cur_vol=volume
        while  cur_vol < new_volume:
            cur_vol=cur_vol+1
            mixer.setvolume(cur_vol)
            time.sleep(SMOOTH_TIMEOUT)
        while cur_vol > new_volume:
            cur_vol = cur_vol-1
            mixer.setvolume(cur_vol)
            time.sleep(SMOOTH_TIMEOUT)
        volume=new_volume
    else:
        volume=new_volume
        mixer.setvolume(new_volume)

def callback(ch, method, properties, body):
    global alsa_state
    logger.info('Callback %s, Alsa State %s ' , body, alsa_state)
    data=json.loads(body)
    if (data['label']=='audio_data'):
        new_volume=data['data']['volume']
        if volume==-1:
            set_volume(new_volume,False)
            if data['data']['on']:
                startAlsaLoop()

    if (data['label']=='volume_changed'):
        new_volume=data['data']['volume']
        smooth=data['data']['smooth']
        set_volume(new_volume,smooth)

    if (data['label']=='dab_data'):
        if data['data']['on']:
            startAlsaLoop()
        else:
            stopAlsaLoop()

def start_service():
    rabbit_send_action('radio_audio_start',None)

def main():
    global mixer
    cfg_logging()
    mixer=createMixer()
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='::1'))

    channel = connection.channel()
    channel.exchange_declare(exchange=RADIO_BROADCAST_EXCHANGE, exchange_type='fanout')

    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange=RADIO_BROADCAST_EXCHANGE, queue=queue_name)
    channel.basic_consume(
        queue=queue_name, on_message_callback=callback, auto_ack=True)
    logger.info('Radio Audio service start')
    t1=threading.Timer(1,start_service)
    t2=threading.Thread(target=channel.start_consuming)
    t2.start()
    t1.start()
    t1.join()
    t2.join()
main()
