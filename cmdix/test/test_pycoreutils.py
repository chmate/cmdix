from __future__ import unicode_literals

import cmdix

from . import BaseTestCase


class TestCase(BaseTestCase):
    def test_getcommand(self):
        for cmd in cmdix.listcommands():
            cmdix.getcommand(cmd)
