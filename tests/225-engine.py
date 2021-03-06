import unittest
import time

from walky.engine import *
from walky.router import *

from _common import *

class Test(unittest.TestCase):

    def test_engine(self):

        engine = Engine()
        self.assertIsInstance(engine,Engine)

        engine.start()

        router = engine.router
        router.mapper('anon',TestClass,TestWrapper)
        self.assertIsInstance(router,Router)

        connection = engine.connection_new()
        self.assertIsInstance(connection,Connection)

        port = TestPort(u'TESTID')
        connection.port(port)
        self.assertIsInstance(connection,Connection)

        # Need to load at least one object into the connection
        tc = TestClass()
        reg_obj_id = connection.conn().put(tc)

        # Okay, finall can start testing the dispatcher
        connection.on_readline(u'[0,"{}","somefunc",123]'.format(reg_obj_id))
        time.sleep(0.1)

        self.assertTrue(port.buffer_send)
        self.assertEqual(port.buffer_send,['[1, "RESULT!", 123]\r\n'])

        engine.shutdown()

if __name__ == '__main__':
    unittest.main()

