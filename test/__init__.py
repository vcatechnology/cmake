#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import inspect
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe()))))))
import pygh


class TestPyGh(unittest.TestCase):
    '''
    Tests functions that are available in the :mod:`pygh` module.
    '''

    def test_find_exe_in_path(self):
        '''
        Tests that the :func:`pygh.find_exe_in_path` returns a list when
        searching for the :code:`echo` program, which should exist on all
        systems
        '''
        self.assertTrue(pygh.find_exe_in_path('echo'))
