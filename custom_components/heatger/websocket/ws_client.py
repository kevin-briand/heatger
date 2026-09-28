"""WS client"""
import asyncio
import json
import logging
import socket
from typing import Any, Awaitable, Callable, Optional

import aiohttp
from aiohttp import ClientWebSocketResponse
from homeassistant.core import HomeAssistant, CALLBACK_TYPE
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later

from custom_components.heatger.const import DOMAIN
from custom_components.heatger.local_storage.json_encoder.json_encoder import JsonEncoder
from custom_components.heatger.shared.enum.state import State

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10
RECONNECT_DELAY = 30
CONFIG_TIMEOUT = 10


class WSClient:
    """WebSocket Client: used to connect to the heatger server"""
    # client used by the zones to send their states (see set_status)
    _main: Optional['WSClient'] = None

    def __init__(self, hass: HomeAssistant, server_address: str,
                 get_data_callback: Callable[[], Awaitable[Any]] = None,
                 updated_data_callback: Callable[[str, State], Awaitable[Any]] = None):
        """
        :param server_address: address of the server: ip:port
        """
        self.hass = hass
        self.server_url = F'http://{server_address}'
        self.get_data = get_data_callback
        self.updated_data = updated_data_callback
        self.config = None
        self._config_received = asyncio.Event()
        self._ws: Optional[ClientWebSocketResponse] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._reconnect_unsub: Optional[CALLBACK_TYPE] = None
        self._closing = False

    @property
    def connected(self) -> bool:
        """return True if connected to the server"""
        return self._ws is not None and not self._ws.closed

    def set_as_main(self) -> None:
        """Use this client to send the zones states"""
        WSClient._main = self

    async def connect(self) -> bool:
        """Connect to the server, return True on success"""
        self._closing = False
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT):
                self._ws = await session.ws_connect(f'{self.server_url}/ws', heartbeat=30)
        except (aiohttp.ClientError, TimeoutError, OSError) as e:
            _LOGGER.warning('Unable to connect to the heatger server %s: %s', self.server_url, e)
            self._ws = None
            return False
        self._listen_task = self.hass.async_create_background_task(self._listen(self._ws), f'{DOMAIN}_ws_listen')
        _LOGGER.info('Connected to the heatger server %s', self.server_url)
        return True

    async def _listen(self, ws: ClientWebSocketResponse) -> None:
        """run loop for waiting message from server"""
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self.eval_message(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.warning('Heatger server connection error: %s', ws.exception())
                    break
        except asyncio.CancelledError:
            raise
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception('Unexpected error on the heatger server connection')
        finally:
            if not ws.closed:
                await ws.close()
            if self._ws is ws:
                self._ws = None
        if not self._closing:
            _LOGGER.warning('Disconnected from the heatger server, trying to reconnect')
            await self._reconnect()

    async def eval_message(self, data: Any):
        """Evaluate the message from the server"""
        try:
            data = json.loads(data)
            if not isinstance(data, dict):
                return
            if 'state' in data:
                for key, value in data.get('state').items():
                    if self.updated_data:
                        await self.updated_data(key, State(value))
            elif 'electric_meter' in data:
                coordinator = self.hass.data.get(DOMAIN, {}).get('em_coordinator')
                if coordinator:
                    coordinator.async_set_updated_data(data)
            elif 'temperature' in data:
                coordinator = self.hass.data.get(DOMAIN, {}).get('temp_coordinator')
                if coordinator:
                    coordinator.async_set_updated_data(data.get('temperature'))
            elif 'config' in data:
                self.config = data.get('config')
                self._config_received.set()
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            # ValueError includes invalid json and unknown state
            _LOGGER.warning('Invalid message received from the heatger server: %s (%s)', data, e)

    async def disconnect(self):
        """Disconnect from the server (no automatic reconnection)"""
        self._closing = True
        if self._reconnect_unsub:
            self._reconnect_unsub()
            self._reconnect_unsub = None
        if self._ws is not None:
            try:
                async with asyncio.timeout(10):
                    await self._ws.close()
            except TimeoutError:
                pass
        self._ws = None
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
        self._listen_task = None
        if WSClient._main is self:
            WSClient._main = None

    async def get_config(self):
        """return config from server, None if the server doesn't respond"""
        if self.config:
            return self.config
        if not self.connected:
            return None

        self._config_received.clear()
        await self.send_data('config')
        try:
            async with asyncio.timeout(CONFIG_TIMEOUT):
                await self._config_received.wait()
        except TimeoutError:
            _LOGGER.warning('The heatger server did not send its config')
        return self.config

    async def _reconnect(self, _now=None) -> None:
        """try to reconnect to the server, retry later on failure"""
        self._reconnect_unsub = None
        if self._closing:
            return
        if await self.connect():
            if self.get_data:
                await self.send_data(await self.get_data())
        else:
            self._reconnect_unsub = async_call_later(self.hass, RECONNECT_DELAY, self._reconnect)

    @staticmethod
    async def set_status(zone: str, status: State):
        """send the state of the zone to the server"""
        if not status:
            return
        client = WSClient._main
        if client is None or not client.connected:
            return
        await client.send_data({'state': {zone: status}})

    async def send_data(self, data: Any):
        """send data to the server"""
        if not self.connected:
            return
        await self._ws.send_json(data, dumps=lambda obj: json.dumps(obj, cls=JsonEncoder))

    @staticmethod
    async def discover_server():
        """Find the server on the local network (UDP broadcast)"""
        loop = asyncio.get_running_loop()
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_sock.setblocking(False)

        message = 'Heatger'
        udp_sock.sendto(message.encode(), ('192.168.1.255', 5001))
        _LOGGER.debug("Broadcast message sent on port 5001")

        success = False
        try:
            data, addr = await asyncio.wait_for(loop.sock_recvfrom(udp_sock, 1024), timeout=5)
            _LOGGER.debug("Server response %s: %s", addr, data.decode())
            if data.decode() == 'OK':
                success = True
        except asyncio.TimeoutError:
            _LOGGER.debug("No response from the server")
        finally:
            udp_sock.close()

        return success
