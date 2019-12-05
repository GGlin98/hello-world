#!/usr/bin/env python3
"""Server for multithreaded (asynchronous) chat application."""
import os
import pickle
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread


def accept_incoming_connections():
    """Sets up handling for incoming clients."""

    while True:
        client, client_address = SERVER.accept()
        print("{:s}:{:d} has connected.".format(client_address[0], client_address[1]))
        addresses[client] = client_address
        Thread(target=handle_client, args=(client,)).start()


def handle_client(client):  # Takes client socket as argument.
    """Handles a single client connection."""
    error_msg = ''

    # Broadcast the welcome message to the chat room
    name = client.recv(BUFSIZ).decode("utf8")
    welcome = 'Welcome %s! If you ever want to quit, type {quit} to exit.' % name
    client.send(bytes(welcome, "utf8"))
    msg = "%s has joined the chat!" % name
    broadcast(bytes(msg, "utf8"))
    clients[client] = name

    # Message loop
    while True:
        try:
            msg = client.recv(BUFSIZ)
        except ConnectionResetError:
            # Client quit accidently
            print("{:s}:{:d} - {:s} has disconnected.".format(addresses[client][0], addresses[client][1], name))
            client.close()
            del clients[client]
            broadcast(bytes("%s has left the chat." % name, "utf8"))
            break
        if msg == bytes('{send_file}', 'utf8'):
            # Client require to upload file to server
            filename = client.recv(BUFSIZ)
            filename = filename.decode('utf8').rstrip('\0')
            fsize = int.from_bytes(client.recv(BUFSIZ), 'little')
            if fsize > 1024 * 1024 * 10:
                client.send(bytes('{refuse_file}', 'utf8'))
                error_msg = 'Error: File must not larger than 10MB'
                continue
            else:
                client.send(bytes('{accept_file}', 'utf8'))
            size_ct = 0
            if not os.path.isdir(FILE_PATH):
                os.mkdir(FILE_PATH)
            filepath = os.path.join(FILE_PATH, filename)
            with open(filepath, 'wb') as f:
                while True:
                    if size_ct < fsize:
                        data = client.recv(BUFSIZ)
                    else:
                        f.write(data)
                        f.close()
                        msg = "{:s} uploaded file {:s}".format(name, filename)
                        print(msg)
                        broadcast(bytes(msg, 'utf8'))
                        break
                    f.write(data)
                    size_ct += BUFSIZ
        elif msg == bytes('{file_list}', 'utf8'):
            # Client require to see the list of files in the server
            file_list = os.listdir(FILE_PATH)
            client.send(pickle.dumps(file_list))
        elif msg == bytes('{download_file}', 'utf8'):
            # Client require to download file from server
            filename = client.recv(BUFSIZ).decode('utf8')
            filepath = os.path.join(FILE_PATH, filename)
            fsize = os.path.getsize(filepath)
            client.send(bytes('{download_file}', 'utf8'))
            client.send(fsize.to_bytes(1024, byteorder='little', signed=False))
            with open(filepath, 'rb') as f:
                while True:
                    f_seg = f.read(BUFSIZ)
                    while f_seg:
                        client.send(bytes(f_seg))
                        f_seg = f.read(BUFSIZ)
                    if not f_seg:
                        f.close()
                        break
        elif msg == bytes("{quit}", "utf8"):
            # Client require to quit the chat
            print("{:s}:{:d} - {:s} has disconnected.".format(addresses[client][0], addresses[client][1], name))
            client.close()
            del clients[client]
            broadcast(bytes("%s has left the chat." % name, "utf8"))
            break
        elif msg == bytes('{error_msg}', 'utf8'):
            client.send(bytes(error_msg, 'utf8'))
        else:
            broadcast(msg, name + ": ")


def broadcast(msg, prefix=""):  # prefix is for name identification.
    """Broadcasts a message to all the clients."""

    for sock in clients:
        sock.send(bytes(prefix, "utf8")+msg)

        
clients = {}
addresses = {}

HOST = ''
PORT = input('Enter port: ')
if not PORT:
    # Default Port
    PORT = 33000
else:
    PORT = int(PORT)
BUFSIZ = 1024
ADDR = (HOST, PORT)

SERVER = socket(AF_INET, SOCK_STREAM)
SERVER.bind(ADDR)

# The directory in server to store uploaded file
FILE_PATH = 'server_files'

if __name__ == "__main__":
    SERVER.listen(5)
    print("Waiting for connection...")
    ACCEPT_THREAD = Thread(target=accept_incoming_connections)
    ACCEPT_THREAD.start()
    ACCEPT_THREAD.join()
SERVER.close()
