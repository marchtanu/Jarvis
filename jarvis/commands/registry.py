import logging
from typing import Dict, Callable, Awaitable

logger = logging.getLogger(__name__)

class CommandRegistry:
    def __init__(self):
        self.commands: Dict[str, Callable[[], Awaitable[None]]] = {}

    def register(self, phrase: str, action: Callable[[], Awaitable[None]]):
        self.commands[phrase.lower()] = action
        logger.debug(f"Registered command: '{phrase}'")

    async def execute(self, phrase: str) -> bool:
        phrase = phrase.lower()
        
        # Exact match
        if phrase in self.commands:
            await self.commands[phrase]()
            return True
            
        # Partial match / fuzzy could be added here
        for key, action in self.commands.items():
            if key in phrase:
                await action()
                return True
                
        return False
