import os
import time
import um31
import mqtt_client
from apscheduler.schedulers.blocking import BlockingScheduler

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

# mqtt_broker_host, mqtt_client_id = [
#     line.strip() for line in open(os.path.join(__location__, "settings"), "r").readlines()
#     ]

mqtt_broker_host = "185.41.113.138"
mqtt_client_id = "5e9c1178-a5f0-4dc0-bbbc-d74243aab27c"
topic = "odintcovo38g/electro"


# update_rate = 10 * 60

# while True:
#     um = um31.UM31()
#     um.connect("/dev/ttyUSB0")
#     data = um.read_current_values()
#     um.disconnect()
#
#     payld = um.export_json(data)
#     msg = []
#     for p in payld:
#         print(p)
#         msg.append({"topic": topic, "payload": p, "qos": 1})
#
#     mqttc = mqtt_client.RestreamClient(mqtt_client_id, msg, __location__)
#     mqttc.client.connect(mqtt_broker_host, port=8883, keepalive=60)
#     mqttc.client.loop_forever(retry_first_connection=True)
#     time.sleep(update_rate)


def job_function():
    um = um31.UM31()
    um.connect("/dev/ttyUSB0")
    data = um.read_current_values()
    um.disconnect()

    payld = um.export_json(data)
    msg = []
    for p in payld:
        print(p)
        msg.append({"topic": topic, "payload": p, "qos": 1})

    mqttc = mqtt_client.RestreamClient(mqtt_client_id, msg, __location__)
    mqttc.client.connect(mqtt_broker_host, port=8883, keepalive=60)
    mqttc.client.loop_forever(retry_first_connection=True)


sched = BlockingScheduler()
sched.add_job(job_function, 'cron', minute='0,10,20,30,40,50')

sched.start()
