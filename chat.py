import datetime
import select
import socket
import logging
import enum
import json
import re
import threading
import errno
import time

PORT = 12345

HELLO_MESSAGE = {
    "type": "hello",
    "myname": None
}

RESPOND_BACK_MESSAGE = {
    "type": "respond_back",
    "myname": None
}

MESSAGE = {
    "type": "message",
    "content": None
}

IP_PATTERN = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
BROADCAST_PERIOD = 60
PRUNING_PERIOD = 120

# TODO :Find a way of closing the self-listener thread.


class MessageType(enum.Enum):
    hello = 1
    aleykumselam = 2
    message = 3


class Chat:
    def __init__(self, name: str = None):
        logging.info("Finding out whoami.")
        self.terminate = False
        hostname: str = socket.gethostname()
        ip_addresses = socket.gethostbyname_ex(hostname)[-1]
        if len(ip_addresses) > 1:
            # TODO: lookup why this happens ?
            ipaddress: str = socket.gethostbyname_ex(hostname)[-1][1]
        else:
            ipaddress: str = socket.gethostbyname_ex(hostname)[-1][0]
        logging.info(f"Resolved whoami. IP:{ipaddress} \t Hostname:{hostname}")
        self.whoami: dict = dict()
        self.whoami["myname"] = name if name is not None else hostname
        self.whoami["ip"] = ipaddress

        self.peers: dict = {}
        self.listener_threads: dict = {}
        self.prune_list: list[str] = []

        self.listener_threads["BROADCAST"] = threading.Thread(
            target=self.listen_broadcast, daemon=True).start()
        self.listener_threads[self.whoami["ip"]] = threading.Thread(
            target=lambda: self.listen_peer(self.whoami["ip"]), daemon=True
        ).start()
        self.last_timestamp = time.time() - BROADCAST_PERIOD
        self.broadcast_thread = threading.Thread(
            target=self.broadcast, daemon=True).start()

        print(f"Discovery completed, ready to chat.")
        self.user_input_thread = threading.Thread(target=self.listen_user)
        self.user_input_thread.start()
        self.user_input_thread.join()

    def show_peers(self):
        print("IP:\t\tName:")
        for peer in self.peers:
            print(f"{peer}\t{self.peers[peer][1]}")

    def get_ip_by_name(self, name: str):
        for peer in self.peers.keys():
            if self.peers[peer][1] == name:
                return peer
        return None

    def shutdown(self):
        logging.info("Terminating...")
        self.terminate = True
        for ip in self.listener_threads.keys():
            if ip not in [self.whoami["ip"], "BROADCAST"]:
                self.listener_threads[ip].join()
                logging.info(f"{ip} listener closed.")

    def listen_user(self):
        while True and not self.terminate:
            line = input()
            if line == ":whoami":
                print(f'IP:{self.whoami["ip"]}\tName:{self.whoami["myname"]}')

            if line == ":quit":
                self.shutdown()

            if line == ":peers":
                self.show_peers()

            if line.startswith(":hello"):
                try:
                    name = line.split()[1]
                    ip = name.strip()
                    match = re.match(IP_PATTERN, ip)
                    if match and self.whoami["ip"] != ip:
                        hello_message = HELLO_MESSAGE.copy()
                        hello_message["myname"] = self.whoami["myname"]
                        self.send_message(ip, MessageType.hello)
                    else:
                        logging.warn("Incorrect IP string.")
                except BaseException:
                    print("Invalid command. Usage: :hello ip")

            if line.startswith(":send"):
                try:
                    if line.startswith(":send_all"):
                    # strip command from the second empty spaace and keep the
                    # rest as content
                        content = line.split(" ", 1)[1]
                        content = content.strip()
                        for peer in self.peers.keys():
                            threading.Thread(target=lambda: self.send_message(
                                peer, MessageType.message, content=content)).start()
                    elif line.startswith(":send_to"):
                        name, content = line.split(
                            " ", 2)[1], line.split(
                            " ", 2)[2]
                        name = name.strip()
                        content = content.strip()
                        ip = self.get_ip_by_name(name)
                        if ip is None:
                            print(f"Peer with name \"{name}\" not found.")
                        else:
                            self.send_message(
                                ip, MessageType.message, content=content)
                except BaseException as e:
                    print("Invalid command. Usage: :send name message")

    def broadcast(self, port: int = PORT) -> dict:
        # nmap this nmap that
        # broadcast_address = ".".join(self.whoami['ip'].split('.')[:-1]) + ".255"
        while True:
            if time.time() - self.last_timestamp > BROADCAST_PERIOD:
                logging.info("Broadcasting...")
                self.last_timestamp = time.time()
                hello_message = HELLO_MESSAGE.copy()
                hello_message['myname'] = self.whoami["myname"]
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.bind(('', 0))
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    s.sendto(json.dumps(hello_message).encode(
                        'utf-8'), ('<broadcast>', port))
                logging.info("Done.")

    def send_message(self, ip: str, type: MessageType,
                     content: str = None, port: int = PORT):
        try:
            logging.info("Creating a socket")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                logging.info(f"Connecting to the {ip} on {port}")
                s.connect((ip, port))

                logging.info("Preparing the message.")
                if type == MessageType.hello:
                    message = HELLO_MESSAGE.copy()
                    message["myname"] = self.whoami["myname"]
                if type == MessageType.aleykumselam:
                    message = RESPOND_BACK_MESSAGE.copy()
                    message["myname"] = self.whoami["myname"]
                if type == MessageType.message:
                    message = MESSAGE.copy()
                    message["content"] = content

                encode = json.dumps(message).encode('utf-8')
                s.sendall(encode)
                logging.info("Sent the message")
                s.close()
                logging.info(f"Closed the connection on {ip}")
        except Exception as e:
            logging.error(f"Error while sending the message. Reason: {e}")

    def process_message(self, data: str, ip: str):
        data = json.loads(data)
        try:
            if data["type"] == HELLO_MESSAGE["type"] and ip != self.whoami["ip"]:
                logging.info(f"{ip} reached to say 'hello'")
                self.peers[ip] = (time.time(), data["myname"])
                self.listener_threads[ip] = threading.Thread(
                    target=lambda: self.listen_peer(ip))
                self.listener_threads[ip].start()
                logging.info(f"Sending 'aleykumselam' to {ip}")
                self.send_message(ip, MessageType.aleykumselam)

            if data["type"] == RESPOND_BACK_MESSAGE["type"]:
                logging.info(f"{ip} said 'aleykumselam'")
                self.peers[ip] = (time.time(), data["myname"])

            if data["type"] == MESSAGE["type"]:
                logging.info(
                    f"Processing message from {self.peers[ip]}({ip})")
                _content = data['content']
                _from = 'UNKNOWN_HOST' if ip not in self.peers.keys(
                ) else self.peers[ip][1]
                print(
                    f"[{datetime.datetime.now()}] FROM: {_from}({ip}): {_content}")
        except KeyError as e:
            logging.error(
                f"Incoming message with unexpected structure. Message: {data}")
        except Exception as e:
            logging.error(f"Unexpected error. Check the exception: {e}")

    def listen_peer(self, ip: str, port: int = PORT):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((ip, port))
                s.listen()
                while True and not self.terminate:
                    conn, addr = s.accept()
                    addr = addr[0]
                    with conn:
                        while True:
                            data = conn.recv(1024)
                            if not data:
                                break
                            data = data.decode('utf-8')
                            self.process_message(data, addr)
                if self.terminate:
                    logging.info(f"Closed the connection on {ip}")
                    s.close()
            except socket.error as e:
                if e.errno == errno.EADDRNOTAVAIL:
                    logging.info(f"Host not available")
                if e.errno == errno.ECONNREFUSED or 'Connection refused' in str(
                        e):
                    logging.info(f"Host refused to connect")

    def listen_broadcast(self, port=PORT):
        while True and not self.terminate:
            buffer_size = 1024
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.bind(('', port))
                s.setblocking(0)
                result = select.select([s], [], [])
                msg, sender = result[0][0].recvfrom(buffer_size)
                sender = sender[0]
                self.process_message(msg, sender)

                for peer in list(self.peers.keys()):
                    if time.time() - self.peers[peer][0] > PRUNING_PERIOD:
                        logging.info(
                            f"Pruning peer due to inactivity: {self.peers[peer][1]}({peer})")
                        self.peers.pop(peer)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    chat = Chat("Deniz")