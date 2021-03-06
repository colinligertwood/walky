import weakref
import asyncore
import socket
import ssl
import os
import signal

from walky.client.common import *

class ClientSocketPort(asyncore.dispatcher):
    _connection = None

    def __init__(self,host,port,ssl_options=None,connection=None):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect( (host, port) )

        self.queue_send = []

        self.buffer_receive = ''
        self.ssl_options = ssl_options or {}

        self.connection(connection)

    def connection(self,connection=None):
        if connection:
            self._connection = weakref.ref(connection)
        return self._connection and self._connection()

    def handle_connect(self):
        self._socket = self.socket
        if self.ssl_options:
            self.socket = ssl.wrap_socket(
                                    self.socket, 
                                    **(self.ssl_options)
                                )

    def handle_close(self):
        self.close()

    def handle_read(self):
        data = self.recv(8192)
        self.buffer_receive += data
        if not data.find('\n'): return
        en = self.buffer_receive.split('\n')
        self.buffer_receive = en[-1]
        connection = self.connection()
        for line in map(lambda a:a+"\n", en[:-1]):
            connection.on_readline(line)

    def writable(self):
        return self.queue_send

    def sendline(self,line):
        self.send(line+u"\r\n")


class SocketClient(Client):

    socket_host = None
    socket_port = WALKY_SOCKET_PORT

    port_class = ClientSocketPort

    def __init__(self,**kwargs):
        super(SocketClient,self).__init__(**kwargs)
        self.settings.setdefault('socket_host',self.socket_host)
        self.settings.setdefault('socket_port',self.socket_port)
        self.settings.setdefault('data_path','walkydata')
        self.settings.setdefault('ssl_options',{})

    def run(self):
        asyncore.loop()

    def close(self):
        self.port.close()
        super(SocketClient,self).close()

    def connect(self,host=None,port=None,*args,**kwargs):
        super(SocketClient,self).connect(*args,**kwargs)
        data_dir = self.settings['data_path']
        port = self.settings['port_class'](
                    host or self.settings['socket_host'],
                    port or self.settings['socket_port'],
                    ssl_options=self.settings['ssl_options'],
                )
        # FIXME: Do we need to do something special with the port?
        self.port = port
        self.connection.port(port)

        signal.signal(signal.SIGINT, self.close)
        signal.signal(signal.SIGTERM, self.close)

        self.ioloop = threading.Thread(
                            target=lambda *a: self.run(),
                        )
        self.ioloop.daemon = True
        self.ioloop.start()

