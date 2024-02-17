import threading
import signal

# drops frames other than the latest one in order to keep the processing real-time
class FrameDropDecorator:
    def __init__(self, cap, shutdown_handler):
        self.cap = cap
        self.shutdown_handler = shutdown_handler
        self.t = threading.Thread(target=self._reader, daemon=True)
        self.last_frame = None
        self.condition = threading.Condition()
        self.t.start()

    # grab frames as soon as they are available
    def _reader(self):
        while not self.shutdown_handler.stopped():
            ret = self.cap.read()
            if not ret[0]:
                break
            with self.condition:
                self.last_frame = ret
                self.condition.notify()

    # retrieve latest frame
    def read(self):
        with self.condition:
            if self.last_frame is None:
                self.condition.wait()
            frame = self.last_frame
            self.last_frame = None
            return frame
    
    def isOpened(self):
        return self.cap.isOpened()
    
    def release(self):
        self.cap.release()
    

class ShutdownHandler:
    def __init__(self):
        self._stopped = False
        signal.signal(signal.SIGINT, self._handler)
        signal.signal(signal.SIGTERM, self._handler)

    def _handler(self, signum, frame):
        self._stopped = True

    def stopped(self):
        return self._stopped