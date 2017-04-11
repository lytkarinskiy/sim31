import um31

um = um31.UM31()
um.connect("/dev/ttyUSB0")
data = um.read_diagnostic()
#
# data = um.read_month_values(2)

with open("data.txt", "wb") as f:
    f.write(data)
#
# dat2 = um.export_json(data)
# for i in dat2:
#     print(i)




# def core_func():
#     while True:
#         # while True:
#         # if check_server(mqtt_broker_host, 8883):
#         # break
#         # time.sleep(120)
#         # Create connection to OPC server and read vars
#         client = opclib.Client()
#         connect_opc_server(client, opc_server)
#         client.load_all(filter_=".Channel")
#
#         itms = client.items
#         payld = json_payload(client, itms, "tekon_water")
#         msg = []
#         for p in payld:
#             msg.append({"topic": topic, "payload": p, "qos": 1})
#         print("Connecting to Restream")
#         mqttc = paho.Client(client_id=mqtt_client_id, userdata=msg)
#         mqttc.on_connect = on_connect
#         mqttc.on_publish = on_publish
#         mqttc.on_disconnect = on_disconnect
#         mqttc.tls_set(ca_certs=os.path.join(__location__, "ca.crt"),
#                       certfile=os.path.join(__location__, "client_cert.pem"),
#                       keyfile=os.path.join(__location__, "client_key.pem"),
#                       tls_version=ssl.PROTOCOL_TLSv1_2)
#         mqttc.tls_insecure_set(True)  # prevents ssl.SSLError: Certificate subject does not match remote hostname.
#         # mqttc.connect(mqtt_broker_host, port=8883, keepalive=60)
#         # try_to_connect()
#         mqttc.connect(mqtt_broker_host, port=8883, keepalive=60)
#         mqttc.loop_forever(retry_first_connection=True)
#
#         client.close()
#         print("Connection to OpenOPC server " + opc_server + " is closed")
#         time.sleep(updateRate)




    # Infinite loop to read and publish with updateRate priod
    updateRate = 120
    topic = "odintcovo38g/water"
    opc_host, opc_server, mqtt_broker_host, mqtt_client_id = [line.strip() for line in
                                                              open(os.path.join(__location__, "settings"), "r").readlines()]


    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))