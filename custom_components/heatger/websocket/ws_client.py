"""WS client"""
import asyncio
import json
import logging
import socket
from typing import Optional, Callable, Coroutine

import aiohttp
from aiohttp import ClientWebSocketResponse, WSMessage
from homeassistant.core import HomeAssistant

from custom_components.heatger.local_storage.config.config import Config
from custom_components.heatger.local_storage.json_encoder.json_encoder import JsonEncoder
from custom_components.heatger.shared.enum.state import State
from custom_components.heatger.shared.timer.timer import Timer

_LOGGER = logging.getLogger(__name__)


class WSClient:
    """WebSocket Client: used to connect to the heatger server"""
    _ws: Optional[ClientWebSocketResponse] = None

    def __init__(self, hass: HomeAssistant,
                 get_data_callback: Callable[[], Coroutine[any, None, int]] = None,
                 updated_data_callback: Callable[[str, State], Coroutine[None, None, int]] = None):
        self.hass = hass
        self.connected = False
        self.server_url = Config(self.hass).get_ws_url()
        self.get_data = get_data_callback
        self.updated_data = updated_data_callback

    async def connect(self):
        """Connect to the server"""
        client = aiohttp.ClientSession()
        try:
            ws = await client.ws_connect(f'{self.server_url}/ws')
            asyncio.create_task(self.events())
            WSClient._ws = ws
            return True
        except Exception as e:
            _LOGGER.error(e)
            self.connected = False
            if WSClient._ws:
                await WSClient._ws.close()
                WSClient._ws = None
            await client.close()
        return False

    async def events(self):
        """run loop for waiting message from server"""
        self.connected = True
        while self.connected:
            msg: WSMessage = await WSClient._ws.receive()
            if msg.type in (aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR):
                self.connected = False
                await WSClient._ws.close()
                await self._auto_reconnect()
            else:
                await self.eval_message(msg.data)

    async def eval_message(self, data: any):
        """Evaluate the message from the server"""
        try:
            data = json.loads(data)
            if 'state' in data:
                for key, value in data.get('state').items():
                    if self.updated_data:
                        await self.updated_data(key, State(value))
        except TypeError:
            pass

    async def disconnect(self):
        """Disconnect from the server"""
        async with asyncio.timeout(10):
            await WSClient._ws.close()
        self._ws = None
        self.connected = False

    async def _auto_reconnect(self):
        """try to reconnect to the server if disconnected"""
        if not await self.connect() and not self.connected:
            await Timer().start(30, self._auto_reconnect)
        else:
            if self.get_data:
                await self.send_data(await self.get_data())

    @staticmethod
    async def set_status(zone: str, status: State):
        """update the status in the zone"""
        if not status:
            return
        if not WSClient._ws:
            return
        await WSClient.send_data({'state': {zone: status}})

    @staticmethod
    async def send_data(data: any):
        """send data to the server"""
        await WSClient._ws.send_json(data, dumps=lambda obj: json.dumps(obj, cls=JsonEncoder))

    async def set_server_url(self, url: str):
        """Set and store the url to the server"""
        self.server_url = F'http://{url}'
        await Config(self.hass).set_ws_url(url)

    @staticmethod
    async def discover_server():
        loop = asyncio.get_event_loop()
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_sock.setblocking(False)  # Set socket to non-blocking mode

        message = 'Heatger'
        _LOGGER.info(udp_sock.sendto(message.encode(), ('192.168.1.255', 5001)))
        _LOGGER.info("Message de broadcast envoyé sur le port 5001")

        success = False
        try:
            data, addr = await asyncio.wait_for(loop.sock_recv(udp_sock, 1024), timeout=5)
            _LOGGER.info(f"Réponse du serveur {addr}: {data.decode()}")
            if data.decode() == 'OK':
                success = True
        except asyncio.TimeoutError:
            _LOGGER.info("Aucune réponse du serveur")
        finally:
            udp_sock.close()

        return success
