from __future__ import absolute_import

import os
import logging
import threading
import Queue

from tornado.ioloop import IOLoop
from tornado.tcpserver import TCPServer
from tornado import websocket, web

from walky.engine import *

_logger = logging.getLogger(__name__)

class TornadoWebsockServer(websocket.WebSocketHandler):
    def check_origin(self, origin):
        """ We don't worry where the requests come from 
            (at the moment)
        """
        return True

class TornadoSocketServerPort(Port):
    def init(self,stream,address,*args,**kwargs):
        self.stream = stream
        self.address = address

        self.read_next()
        self.stream.set_close_callback(self.on_close)

        self.socket_open = True
        self.send_queue = Queue.Queue()

    def send_queued(self):
        line = ''
        while not self.send_queue.empty():
            line += self.send_queue.get()
        if line: 
            self.stream.write(line.encode('utf8'))

    def read_next(self):
        self.stream.read_until('\n', self.on_receiveline)

    def on_receiveline(self, line):
        super(TornadoSocketServerPort,self).on_receiveline(line)
        self.read_next()

    def _sendline(self,line):
        self.send_queue.put(line)
        IOLoop.instance().add_callback(self.send_queued)

    def on_close(self):
        self.socket_open = False
        _logger.debug('client quit %s', self.address)

class TornadoSocketServer(TCPServer):
    def __init__(self,server,*args,**kwargs):
        self.server = server
        super(TornadoSocketServer,self).__init__(*args,**kwargs)

    def handle_stream(self, stream, address):
        port = self.server.engine.port_new(
                                      TornadoSocketServerPort,
                                      stream, address
                                  )
        conn = self.server.engine.connection_new(port=port)

class TornadoServer(object):
    engine = None
    settings = None

    websock_port = WALKY_WEBSOCK_PORT
    socket_port = WALKY_SOCKET_PORT
    socket_server_class = TornadoSocketServer
    websocket_server_class = TornadoWebsockServer
    engine_class = Engine

    def __init__(self,**settings):
        settings.setdefault('websock_port',self.websock_port)
        settings.setdefault('socket_port',self.socket_port)
        settings.setdefault('ssl_options',None)
        settings.setdefault('data_path','walkydata')
        settings.setdefault('wsgi_fallback_handler',None)

        settings.setdefault('socket_server_class',self.socket_server_class)
        settings.setdefault('websocket_server_class',self.websocket_server_class)
        settings.setdefault('engine_class',self.engine_class)

        self.settings = settings

        self.reset()

    def reset(self):
        if self.engine: self.engine.shutdown()
        self.engine = self.settings['engine_class']()

    def run(self):
        settings = self.settings
        data_dir = settings['data_path']

        self.engine.start()

        web_routes = [(r'/websocket', settings['websocket_server_class'])]
        if settings['wsgi_fallback_handler']:
            web_routes.append((r'.*',settings['wsgi_fallback_handler']))

        self.websock_server = web.Application(web_routes)
        self.websock_server.listen(
                                      settings['websock_port'],
                                      ssl_options=settings['ssl_options']
                                  )

        self.socket_server = settings['socket_server_class'](
                                      self,ssl_options=settings['ssl_options']
                                  )
        self.socket_server.listen(settings['socket_port'])

        try:
            IOLoop.instance().start()
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        self.engine.shutdown()
        IOLoop.instance().stop()




