import json
import threading
from websocket_server import WebsocketServer


class Server(object):

    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port

        self.__server = None

    def open_server(self):
        self.__server = WebsocketServer(host=self.host, port=self.port)
        self.__server.set_fn_new_client(_new_client)
        t = threading.Thread(target=self.__server.run_forever, daemon=True)
        t.start()

    def close_server(self):
        self.__server.shutdown_gracefully()

    def send_json(self, message: dict):
        self.__server.send_message_to_all(json.dumps(message))

def _new_client(client, server):
    print("new client")