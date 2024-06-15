"""Timer class"""
import asyncio
from datetime import datetime


class Timer:
    """Provide a timer"""
    def __init__(self):
        self.time_start = None
        self.timeout = None
        self.timer_task = None

    async def start(self, timeout, on_timeout_callback):
        """start timer with timeout in seconds, on timeout call on_timeout_callback"""
        await self.stop()
        self.time_start = datetime.now().timestamp()
        self.timeout = timeout

        async def timer():
            await asyncio.sleep(self.timeout)
            await on_timeout_callback()

        self.timer_task = asyncio.create_task(timer())

    async def stop(self):
        """stop timer"""
        if self.timer_task is None:
            return
        self.timer_task.cancel()
        try:
            await self.timer_task
        except asyncio.CancelledError:
            pass
        self.timer_task = None
        self.time_start = None
        self.timeout = None

    def get_remaining_time(self) -> int:
        """return the remaining time before timeout"""
        if self.timeout is None or self.time_start is None:
            return -1
        return int(self.timeout - (datetime.now().timestamp() - self.time_start))
