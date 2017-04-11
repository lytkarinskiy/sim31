import os
import time
import um31
import mqtt_client

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

# mqtt_broker_host, mqtt_client_id = [
#     line.strip() for line in open(os.path.join(__location__, "settings"), "r").readlines()
#     ]

mqtt_broker_host = "185.41.113.138"
mqtt_client_id = "5e9c1178-a5f0-4dc0-bbbc-d74243aab27c"

update_rate = 10 * 60

while True:
    um = um31.UM31()
    um.connect("/dev/ttyUSB0")
    data = um.read_current_values()
    um.disconnect()
    msg = um.export_json(data)

    mqttc = mqtt_client.RestreamClient(mqtt_client_id, msg, __location__)
    mqttc.client.connect(mqtt_broker_host, port=8883, keepalive=60)
    mqttc.client.loop_forever(retry_first_connection=True)
    time.sleep(update_rate)
