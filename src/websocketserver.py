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
        self.__server.run_forever(True)

    def close_server(self):
        self.__server.shutdown_gracefully()

    def send_json(self, message: dict):
        self.__server.send_message_to_all(json.dumps(message))

def _new_client(client, server):
    print("new client")

# if __name__ == "__main__":
#     # Simple standalone example of this module sending randomized dummy data
#     from random import randint
#     from time import sleep
#
#     s = Server()
#     s.open_server()
#
#     msg = {
#         "right": {
#             "present": True,
#             "position": {
#                 "x": 0,
#                 "y": 0
#             }
#         },
#         "left": {
#             "present": True,
#             "position": {
#                 "x": 0,
#                 "y": 0
#             }
#         }
#     }
#
#     try:
#         while True:
#
#             # randomize right hand input
#             if randint(0, 100) > 20:
#                 msg["right"]["present"] = True
#                 msg["right"]["position"]["x"] = randint(0, 1920)
#                 msg["right"]["position"]["y"] = randint(0, 1000)
#             else:
#                 msg["right"]["present"] = False
#
#             # randomize left hand input
#             if randint(0, 100) > 20:
#                 msg["left"]["present"] = True
#                 msg["left"]["position"]["x"] = randint(0, 1920)
#                 msg["left"]["position"]["y"] = randint(0, 1000)
#             else:
#                 msg["left"]["present"] = False
#
#             s.send_json(msg)
#             sleep(1)
#
#     except KeyboardInterrupt:
#         s.close_server()
