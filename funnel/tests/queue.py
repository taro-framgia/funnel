# -*- coding: utf-8 -*-
#
# Copyright 2013 Unicon Pte. Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, with_statement

from funnel.queue import AsyncManager, SyncManager, Message
from time import time
from tornado.testing import AsyncTestCase
from tornado.ioloop import IOLoop
from funnel.testing import HOST
from unittest import TestCase

class TestAsyncManager(AsyncTestCase):
    def get_new_ioloop(self):
        return IOLoop.current()

    def test_basis(self):
        queue = AsyncManager()
        self.addCleanup(queue.close_connection)
        queue.connect(host=HOST)

        counter = {"n": 0}
        def on_message(body):
            self.assertEqual(body, {"message": "Hello, world!"})
            counter["n"] += 1

        queue.start_consuming(
            on_message,
        )

        queue.publish({"message": "Hello, world!"}, routing_key=queue.name)

        IOLoop.current().add_timeout(time() + 0.2, self.stop)
        self.wait()

        self.assertEqual(counter["n"], 1)

    def test_handling_static_queue_name(self):
        queue = AsyncManager(queue="dummy")
        self.addCleanup(queue.close_connection)
        queue.connect(host=HOST)

        self.assertEqual(queue.name, "dummy")

    def test_publish_with_not_ready(self):
        queue = AsyncManager(queue="dummy")
        self.addCleanup(queue.close_connection)
        queue.connect(host=HOST)
        queue._ready = False
        try:
            queue.publish(None,None)
        except Exception as e:
            self.fail("This exception is raised: {}".format(e))

    def test_serializer(self):
        class SomeObject(object):
            def __init__(self, entity):
                self.entity = entity

            def __repr__(self):
                return self.entity

        queue = AsyncManager()
        self.addCleanup(queue.close_connection)
        queue.connect(host=HOST)

        counter = {"n": 0}
        def on_message(body):
            self.assertEqual(body, {"message": "Hello, world!"})
            counter["n"] += 1

        queue.start_consuming(
            on_message,
        )

        self.assertRaises(TypeError, lambda: queue.publish({"message": SomeObject("Hello, world!")}, routing_key=queue.name))

        def serializer(o):
            if isinstance(o, SomeObject):
                return repr(o)
            raise TypeError(repr(o) + " is not JSON serializable")

        queue.publish({"message": SomeObject("Hello, world!")}, routing_key=queue.name, serializer=serializer)
        IOLoop.current().add_timeout(time() + 0.2, self.stop)
        self.wait()

        self.assertEqual(counter["n"], 1)


class TestSyncManager(AsyncTestCase):
    def test_basis(self):
        # manager二つ使っているのでqueue nameは固定にしないと動かない
        queue = SyncManager(queue="dummy")
        worker_queue = AsyncManager(queue="dummy")
        self.addCleanup(queue.close_connection)
        # XXX こちらをcloseするとtesting のAsyncWorkerTestCase.doCleanupと競合しているのかエラーになるのでコメントアウト
#         self.addCleanup(worker_queue.close_connection)
        queue.connect(host=HOST)
        worker_queue.connect(host=HOST)

        counter = {"n": 0}
        def on_message(body):
            self.assertEqual(body, {"message": "Hello, world!"})
            counter["n"] += 1

        worker_queue.start_consuming(
            on_message,
        )

        queue.publish({"message": "Hello, world!"}, routing_key=queue.name)

        IOLoop.current().add_timeout(time() + 0.2, self.stop)
        self.wait()

        self.assertEqual(counter["n"], 1)

    def test_publish_with_not_ready(self):
        queue = SyncManager(queue="dummy")
        self.addCleanup(queue.close_connection)
        queue.connect(host=HOST)
        queue._ready = False
        try:
            queue.publish(None,None)
        except Exception as e:
            self.fail("This exception is raised: {}".format(e))

    def test_ready_flag_when_queue_declere_completed(self):
        queue = SyncManager(queue="dummy")
        worker_queue = AsyncManager(queue="dummy")
        self.addCleanup(queue.close_connection)
        queue.connect(host=HOST)
        worker_queue.connect(host=HOST)

        def on_message():
            pass

        worker_queue.start_consuming(
            on_message,
        )

        queue.publish({"message": "Hello, world!"}, routing_key=queue.name)
        IOLoop.current().add_timeout(time() + 0.2, self.stop)
        self.wait()
        self.assertTrue(queue._ready)

class TestMassage(TestCase):
    def test__prepare_body(self):
        def dummy_callback():
            pass

        queue = AsyncManager()
        message = Message(queue, dummy_callback)

        body = message._prepare_body(b'{}')
        self.assertEqual(body, '{}')
