import logging
from typing import cast

from langbot_plugin.api.definition.plugin import BasePlugin

from core import ElysianRealmAssistantCore, LoggerProtocol


class ElysianRealmAssistant(BasePlugin):
    core: ElysianRealmAssistantCore

    async def initialize(self) -> None:
        logger = cast(LoggerProtocol, getattr(self, "logger", logging.getLogger(__name__)))
        self.core = ElysianRealmAssistantCore(logger=logger)
        await self.core.initialize()

    def __del__(self) -> None:
        pass
