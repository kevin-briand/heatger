"""Pilot wire actuator: an output of the heatger server"""
from __future__ import annotations

import logging
from typing import Optional

from ..shared.enum.season import Season
from ..shared.enum.state import State
from ..websocket.ws_client import WSClient
from .base import Actuator

_LOGGER = logging.getLogger(__name__)


class PilotWireActuator(Actuator):
    """Heating season: follows the state of the zone. Other seasons: frost-free."""

    last_order: Optional[State] = None

    @property
    def output(self) -> str:
        return self.config.output or ''

    @staticmethod
    def order_for(state: State, season: Season) -> State:
        """order sent to the server"""
        return state if season == Season.HEATING else State.FROSTFREE

    async def apply(self, state: State, season: Season, new_slot: bool) -> None:
        self.last = (state, season)
        order = self.order_for(state, season)
        self.last_order = order
        try:
            await WSClient.set_status(self.output, order)
        except Exception as e:  # pylint: disable=broad-except
            # the order is sent again to the server on reconnection (ZoneManager.get_all_data)
            _LOGGER.error('Failure to send %s to the output %s: %s', order.name, self.output, e)

    def server_state(self, state: State) -> None:
        """the server sent the state of the output"""
        self.last_order = state

    def get_info(self) -> dict:
        return {**super().get_info(), 'output': self.output,
                'order': self.last_order.name if self.last_order else None}
