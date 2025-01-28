from abc import abstractmethod


class ApiWrapper:
    def __init__(self, api_key: str):
        self._initialised = False
        self.api_key = api_key

    def init(self):
        if self._initialised is True:
            return

        self._init()

        self._initialised = True

    @abstractmethod
    def _init(self):
        raise NotImplemented()
