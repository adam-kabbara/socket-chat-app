import socket
import threading
import json
import re
import colorama
import sys
import pyaudio


colorama.init()
HEADER = 200000
PORT = 4444
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = 'DISCONNECT!'
SERVER = '192.168.8.108'
ADDR = (SERVER, PORT)
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDR)
print('connected')

with open(r"C:\Users\ado\python projects\projects\chat-app\contacts.json", 'r') as f:
    contacts = json.load(f)

ip_address_pattern = re.compile(r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}')
port_number_pattern = re.compile("[0-9]{1-4}|[1-5][0-9]{4}|6[0-4][0-9]{2}|65[0-2][0-9]|6553[0-5]")
INDICATOR = "//*indicator*\\\\"

phone_call = False
received_call_data = []

chunk = 2024
sample_format = pyaudio.paInt32
channels = 2
fs = 44100
p = pyaudio.PyAudio()
stream = p.open(format=sample_format,
                channels=channels,
                rate=fs,
                frames_per_buffer=chunk,
                input=True,
                output=True)


def send(msg):
    msg = msg.encode(FORMAT)
    msg_len = len(msg)
    send_len = b' ' + str(msg_len).encode(FORMAT)
    send_len += b' ' * (HEADER - len(send_len))
    client.send(send_len)
    client.send(msg)


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


def handel_call():
    # todo
    global phone_call
    phone_call = True
    receive_thread = threading.Thread(target=receive_call)
    send_thread = threading.Thread(target=send_call)
    receive_thread.start()
    send_thread.start()


def receive_call():
    while phone_call:
        for d in received_call_data:
            stream.write(d)
            received_call_data.pop(received_call_data.index(d))
            if len(received_call_data) >= 1:
                received_call_data.clear()


def send_call():
    while phone_call:
        data = stream.read(chunk)
        client.send(data)


class KeyboardThread(threading.Thread):
    def __init__(self, input_cbk=None, name='keyboard-input-thread'):
        self.input_cbk = input_cbk
        super(KeyboardThread, self).__init__(name=name)
        self.daemon = True
        self.start()

    def run(self):
        while True:
            self.input_cbk(input())


def delete_last_line():
    sys.stdout.write('\x1b[1A')
    sys.stdout.write('\x1b[2K')


while True:
    contact_found = False
    KeyboardThread(send)
    msg_received = receive(client)
    if isinstance(msg_received, bytes):
        received_call_data.append(msg_received)

    else:
        if msg_received.endswith(INDICATOR):
            msg_received = msg_received[:- (len(INDICATOR))]

            for k, v in contacts.items():
                if msg_received.endswith(f'[{v}]'):
                    send(msg_received[:- (len(v) + 2)] + f'[{k}]')
                    contact_found = True
                    break
                elif msg_received.endswith(f'{{{v}}}'):
                    send(msg_received[:- (len(v) + 2)] + f'{{{k}}}')
                    contact_found = True
                    break

            if not contact_found:
                send(msg_received)

            if msg_received == DISCONNECT_MESSAGE:
                print('disconnecting')
                break

            elif msg_received.lower() == 'list contacts':
                for k, v in contacts.items():
                    print(f'contact name: {v} | contact ip: {k}')

            # ------------------create new contact------------------ #
            elif msg_received.lower() == 'create new contact':
                print('please enter the ip address of the new contact: ')
                new_contact_ip_address = receive(client)
                if new_contact_ip_address.lower() == 'cancel':
                    print('cancelled')
                    continue
                else:
                    print('please enter the name of the new contact: ')
                    new_contact_name = receive(client)
                    if new_contact_name.lower() == 'cancel':
                        print('canceled')
                        continue
                    else:
                        contacts[new_contact_ip_address] = new_contact_name
                        with open(r"C:\Users\ado\python projects\projects\chat-app\contacts.json", 'w') as f:
                            json.dump(contacts, f)
                        print('contact successful created')
            # ------------------create new contact------------------ #

            # ------------------make an audio call------------------ #
            elif msg_received.lower().startswith('call'):
                for k, v in contacts.items():
                    if msg_received.endswith(f'{{{v}}}'):
                        if msg_received == f'call {{{v}}}' or msg_received == f'call{{{v}}}':
                            if not phone_call:
                                contact_to_call = v
                                string = receive(client)
                                print(f'{string}: {contact_to_call}')
                                phone_call = True
                                handel_call()
                            else:
                                print('you are already in a phone call')

            elif msg_received == 'end call' and phone_call:
                phone_call = False
            # ------------------make an audio call------------------ #

        else:
            sender_ip_end_pos = ip_address_pattern.match(msg_received, 2)
            if sender_ip_end_pos is not None:
                sender_ip_end_pos = sender_ip_end_pos.end()
                sender_ip = msg_received[2: sender_ip_end_pos]
                sender_port = port_number_pattern.findall(msg_received)[0]

                if sender_ip in contacts.keys():
                    contact_name = contacts[sender_ip]
                    print(f'({contact_name}) {msg_received[sender_ip_end_pos + len(sender_port) + 5:]}')
                else:
                    print(msg_received)

            elif ip_address_pattern.match(msg_received, 15) is not None:
                sender_ip_end_pos = ip_address_pattern.match(msg_received, 15).end()
                sender_ip = msg_received[15: sender_ip_end_pos]
                sender_port = port_number_pattern.findall(msg_received)[0]

                if sender_ip in contacts:
                    contact_name = contacts[sender_ip]
                    if msg_received.startswith(f"private msg: ('{sender_ip}', {sender_port})"):
                        print(f'private msg: ({contact_name}) {msg_received[sender_ip_end_pos + len(sender_port) + 5:]}')
                    else:
                        print(msg_received)
                else:
                    print(msg_received)

            elif 'is calling you' in msg_received and msg_received.startswith('[SYSTEM]'):
                if ip_address_pattern.match(msg_received, 10) is not None:
                    sender_ip_end_pos = ip_address_pattern.match(msg_received, 10).end()
                    sender_ip = msg_received[10: sender_ip_end_pos]
                    print(sender_ip)

                    if sender_ip in contacts:
                        contact_name = contacts[sender_ip]
                        if msg_received == f'[SYSTEM]: {sender_ip} is calling you':
                            print(f'[SYSTEM]: {contact_name} is calling you')
                            handel_call()

                        else:
                            print(msg_received)
                    else:
                        print(msg_received)

            else:
                print(msg_received)
