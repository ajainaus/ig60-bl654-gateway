import os
import greengrasssdk
client = greengrasssdk.client('iot-data')


def error(str):
    client.publish(topic='error', payload=str)


def request(id):
    topic = "$aws/things/{}/shadow/get".format(id)
    client.publish(topic=topic, payload="")


def response(id, payload):
    topic = "things/{}/shadow/update".format(id)
    client.publish(topic=topic, payload=payload)


def discover(node_id, sensor_id, payload):
    environment = os.getenv('Environment')
    topic = "{}/{}/node/{}/add".format(environment, node_id, sensor_id)
    client.publish(topic=topic, payload=payload)
