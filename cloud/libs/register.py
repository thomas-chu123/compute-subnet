# Description: This file contains the register class.
class Register():
    def __init__(self):
        self._registry = {}

    def register(self, name, cls):
        self._registry[name] = cls

    def create(self, name, *args, **kwargs):
        return self._registry[name](*args, **kwargs)