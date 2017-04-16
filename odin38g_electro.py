import time
import um31
import restreamclient
import ssl
import os
from apscheduler.schedulers.background import BackgroundScheduler

location = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
mqtt_broker_host = "185.41.113.138"
mqtt_client_id = "5e9c1178-a5f0-4dc0-bbbc-d74243aab27c"
mqtt_topic = "odintcovo38g/electro"
msg = []


def job_function(msg_):
    um = um31.UM31()
    um.connect("/dev/ttyUSB0")
    data = um.read_current_values()
    um.disconnect()

    payld = um.export_json(data)
    for p in payld:
        msg_.append({"topic": mqtt_topic, "payload": p})

    mqttc = restreamclient.RestreamClient(mqtt_client_id, msg, location)
    try:
        mqttc.client.connect(mqtt_broker_host, port=8883, keepalive=60)
        mqttc.client.loop_forever(retry_first_connection=True)
    except ssl.SSLEOFError:
        print("ssl handshake error")
        pass
    except OSError as e:
        print("OS error: {0}".format(e))
        pass
    else:
        msg_ = []
        print("msg_:", len(msg_))


if __name__ == '__main__':
    sched = BackgroundScheduler()
    sched.add_job(lambda: job_function(msg), 'cron', minute='0,10,20,30,40,50')
    sched.start()

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        sched.shutdown()
