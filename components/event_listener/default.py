from langbot_plugin.api.definition.components.common.event_listener import EventListener
from langbot_plugin.api.entities import context, events

from core import ElysianRealmAssistantCore


class DefaultEventListener(EventListener):
    async def initialize(self) -> None:
        await super().initialize()
        self.handler(events.PersonNormalMessageReceived)(self.on_message)
        self.handler(events.GroupNormalMessageReceived)(self.on_message)

    async def on_message(self, ctx: context.EventContext) -> None:
        plugin = getattr(self, "plugin", None)
        plugin_core = getattr(plugin, "core", None)
        if not isinstance(plugin_core, ElysianRealmAssistantCore):
            return

        event = ctx.event
        message = getattr(event, "text_message", "")
        await plugin_core.handle_message(message, ctx)
