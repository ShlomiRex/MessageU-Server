import unittest

class MainTestingClass(unittest.TestCase):
    def test_something(self):
        self.assertEqual('foo'.upper(), 'FOO')
