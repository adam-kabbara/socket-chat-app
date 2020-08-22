import socket
import threading
import re

PORT = 4444
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)

HEADER = 200000
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = 'DISCONNECT!'

clients = []
calls = []
msgs_to_send = {}
ip_address_pattern = re.compile(r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}')

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)


def handle_client(conn, addr):
    global msgs_to_send

    print(f'new connection {addr} connected')
    connected = True
    send_msgs = False
    current_client = (conn, addr)

    while connected:
        msg = receive(conn)
        if isinstance(msg, bytes):
            for call in calls:
                if call.client1 == current_client or call.client2 == current_client:
                    call.data_lst.append((current_client, msg))
                    break

        else:
            send(conn, f'{msg}//*indicator*\\\\')
            msg = receive(conn)

            if msg != '':
                msgs_to_send[msg] = current_client
                print(f'{addr} --> {msg}')

            if msg == DISCONNECT_MESSAGE:
                msgs_to_send.pop(DISCONNECT_MESSAGE)
                clients.pop(clients.index(current_client))
                connected = False

            elif msg.lower() == 'create new contact':
                msgs_to_send.pop('create new contact')
                new_contact_ip_address = receive(conn)
                send(conn, new_contact_ip_address)
                if new_contact_ip_address.lower() == 'cancel':
                    continue
                else:
                    new_contact_name = receive(conn)
                    send(conn, new_contact_name)
                    if new_contact_name.lower() == 'cancel':
                        continue

            # ---------------------handel calls--------------------- #
            elif msg.lower().startswith('call'):
                ip_address = ip_address_pattern.findall(msg)
                if ip_address:
                    ip_address = ip_address[-1]

                    if msg.endswith(f'{{{ip_address}}}'):
                        for c in clients:
                            recipient_ip = c[1][0]
                            recipient_conn = c[0]
                            if msg == f'call {{{recipient_ip}}}' or msg == f'call{{{recipient_ip}}}':
                                msgs_to_send.pop(msg)
                                send(recipient_conn, f'[SYSTEM]: {current_client[1][0]} is calling you')
                                send(conn, 'calling')

                                calls.append(HandelCall(current_client, c))
                                thread = threading.Thread(target=calls[-1].handel_call)
                                thread.start()
                                break

                        else:
                            send(conn, 'No such client')
                    else:
                        msgs_to_send[msg] = current_client
                        send_msgs = True
                else:
                    msgs_to_send[msg] = current_client
                    send_msgs = True

            else:
                send_msgs = True
            # ---------------------handel calls--------------------- #

            if send_msgs:
                send_msgs = False
                for client in clients:
                    if client != current_client:
                        for m, sender in msgs_to_send.items():

                            # ------------to send private msgs------------ #
                            ip_address = ip_address_pattern.findall(m)
                            if ip_address:
                                ip_address = ip_address[-1]
                                if m.endswith(f'[{ip_address}]'):
                                    lst = [None for tup in clients if ip_address == tup[1][0]]
                                    if lst:
                                        print(client[1][0])
                                        if client[1][0] == ip_address:
                                            send(client[0], f'private msg: {sender[1]} --> {m.strip(f"[{ip_address}]")}')
                                            print(f'private msg: {sender[1]} --> {m.strip(f"[{ip_address}]")}')
                                    else:
                                        send(sender[0], '[ERROR]: No Such Client')
                            # ------------to send private msgs------------ #

                            else:
                                m = f'{sender[1]} --> {m}'
                                send(client[0], m)

                msgs_to_send.clear()
    conn.close()


def receive(conn):
    msg_len = conn.recv(HEADER)

    if msg_len:
        if msg_len.startswith(b' '):
            msg_len = msg_len.decode(FORMAT)
            msg_len = int(msg_len)
            msg = conn.recv(msg_len).decode(FORMAT)
            return msg
        else:
            return msg_len


def send(conn, msg):
    msg = msg.encode(FORMAT)
    msg_len = len(msg)
    send_len = b' ' + str(msg_len).encode(FORMAT)
    send_len += b' ' * (HEADER - len(send_len))
    conn.send(send_len)
    conn.send(msg)


class HandelCall:

    def __init__(self, client1, client2):
        self.client1 = client1
        self.client2 = client2
        self.data_lst = []
        self.running = True

    def handel_call(self):
        while self.running:
            # todo disconnect
            for tup in self.data_lst:
                k = tup[0]
                v = tup[1]

                if k == self.client1:
                    self.client2[0].send(v)
                    self.data_lst.pop(self.data_lst.index(tup))

                else:
                    self.client1[0].send(v)
                    self.data_lst.pop(self.data_lst.index(tup))


def start():
    # this makes the server start to listen for clients
    server.listen()
    print(f'listening on {SERVER}')
    while True:
        # this line will wait until a client is found and will save the connection and address of the new client
        conn, addr = server.accept()
        clients.append((conn, addr))
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f'number of connections {threading.activeCount() - 1}')


print('starting server')
start()
