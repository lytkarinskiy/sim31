import time
import ssl
import paho.mqtt.client as paho
import paho.mqtt as mqtt
import os


class RestreamClient:
    def __init__(self, mqtt_client_id, msg, cert_location):
        self.client = paho.Client(client_id=mqtt_client_id, userdata=msg)
        self.client.on_connect = self._on_connect
        self.client.on_publish = self._on_publish
        self.client.on_disconnect = self._on_disconnect
        self.client.on_log = self._on_log
        self.client.tls_set(ca_certs=os.path.join(cert_location, "ca.crt"),
                            certfile=os.path.join(cert_location, "client_cert.pem"),
                            keyfile=os.path.join(cert_location, "client_key.pem"),
                            tls_version=ssl.PROTOCOL_TLSv1_2)
        self.client.tls_insecure_set(True)  # prevents ssl.SSLError: Certificate subject does not match remote hostname.

    def _do_publish(self, client):
        m = client._userdata.pop()
        if type(m) is dict:
            topic = m["topic"]
            try:
                payload = m["payload"]
            except KeyError:
                payload = None
            try:
                qos = m["qos"]
            except KeyError:
                qos = 1
            try:
                retain = m["retain"]
            except KeyError:
                retain = False
        elif type(m) is tuple:
            (topic, payload, qos, retain) = m
        else:
            raise ValueError("message must be a dict or a tuple")
        client.publish(topic, payload, qos, retain)

    # The callback for when the client receives a CONNACK response from the server.
    def _on_connect(self, client, userdata, flags, rc):
        print(paho.connack_string(rc))
        if rc == 0:
            if len(userdata) != 0:
                self._do_publish(client)
            else:
                client.disconnect()
        else:
            raise mqtt.MQTTException(paho.connack_string(rc))

    # The callback for when message that was to be sent
    # using the publish() call has completed transmission to the broker.
    def _on_publish(self, client, userdata, mid):
        if len(userdata) == 0:
            client.disconnect()
            print("Disconnecting from MQTT broker")
        else:
            self._do_publish(client)

    # The callback for when the client disconnects from the broker.
    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print("on_disconnect: Unexpected disconnection")
            print("waiting 60 sec and reconnecting")
            time.sleep(60)

    def _on_log(self, client, userdata, level, string):
        print("on_log:", string)