import logging
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


class CommandRegistry:
    def __init__(self):
        self.commands: dict[str, Callable[[], Awaitable[str]]] = {}

    def register(self, phrase: str, handler: Callable[[], Awaitable[str]]):
        self.commands[phrase.lower()] = handler
        logger.debug(f"Registered command: '{phrase}'")

    async def execute(self, command_text: str) -> str | None:
        text = command_text.lower().strip()
        for phrase, handler in self.commands.items():
            if text.startswith(phrase):
                logger.info(f"Executing command: '{phrase}'")
                
                # Extract argument if any
                argument = text[len(phrase):].strip()
                
                # If handler takes an argument, pass it; otherwise call normally
                import inspect
                if inspect.iscoroutinefunction(handler):
                    sig = inspect.signature(handler)
                    if len(sig.parameters) > 0:
                        return await handler(argument)
                    else:
                        return await handler()
                else:
                    # Sync fallback (though we mostly use async)
                    sig = inspect.signature(handler)
                    if len(sig.parameters) > 0:
                        return handler(argument)
                    else:
                        return handler()
        return None
