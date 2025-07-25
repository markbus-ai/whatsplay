EVENT_LIST = [
    "on_start",
    "on_auth",
    "on_qr",
    "on_qr_change",
    "on_loading",
    "on_logged_in",
    "on_unread_chat",
    "on_tick",
]


class Event:
    def __init__(self):
        self.__listeners = []

    def register_listener(self, func):
        self.add_listener(func)
        return func

    def add_listener(self, func):
        if func in self.__listeners:
            return

        self.__listeners.append(func)

    def remove_listener(self, func):
        if func not in self.__listeners:
            return

        self.__listeners.remove(func)

    def trigger(self, *args):
        for func in self.__listeners:
            func(*args)


class EventHandler:
    def __init__(self):
        self._events = {}

    def add_event(self, event_type):
        if event_type in self._events:
            return

        self._events[event_type] = Event()

    def event(self, event_type):
        if event_type not in self._events:
            return

        def decorator(func):
            self._events[event_type].register_listener(func)
            return func

        return decorator

    def trigger_event(self, event_type, *args):
        if event_type not in self._events:
            return

        self._events[event_type].trigger(*args)
