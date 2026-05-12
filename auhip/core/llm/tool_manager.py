import asyncio
import inspect
import logging
import os
from typing import Dict, Any, Callable, Awaitable, Optional, Tuple

from auhip.core.llm.config import llm_config
from auhip.core.llm.types import ToolSchema

logger = logging.getLogger(__name__)


class ToolManager:
    """
    Secure sandboxed central tool execution manager. Enforces argument schema validation,
    restricts filesystem path scopes to prevent directory traversals, and isolates exceptions.
    """

    def __init__(self):
        self._tools: Dict[str, Tuple[ToolSchema, Callable[..., Awaitable[Any]]]] = {}

    def register_tool(self, schema: ToolSchema, handler: Callable[..., Awaitable[Any]]):
        """Register a strongly typed skill alongside its execution pointer."""
        self._tools[schema.name] = (schema, handler)
        logger.debug(f"Registered sandboxed tool hook: '{schema.name}'")

    def get_schemas(self) -> list[ToolSchema]:
        """Expose all declared tool definitions for routing injection."""
        return [t[0] for t in self._tools.values()]

    def is_path_safe(self, target_path: str) -> bool:
        """
        Validates target destination against pre-approved sandbox boundaries to block
        malicious access or relative traversal exploits.
        """
        abs_target = os.path.abspath(target_path)
        for boundary in llm_config.SANDBOX_ALLOWED_DIRS:
            if abs_target.startswith(boundary):
                return True
        logger.warning(f"Path verification failed. Access denied to non-sandboxed target: {abs_target}")
        return False

    async def execute(self, tool_name: str, args: Dict[str, Any], timeout_override: Optional[float] = None) -> Any:
        """
        Validates incoming structures and executes targeted internal handler safely
        within an isolated async execution scope.
        """
        if tool_name not in self._tools:
            logger.error(f"Unregistered tool execution requested: {tool_name}")
            raise KeyError(f"Tool {tool_name} is unknown.")

        schema, handler = self._tools[tool_name]
        logger.info(f"Orchestrating registered tool: {tool_name}")

        # 1. Basic required parameters validation
        for req in schema.required:
            if req not in args:
                logger.error(f"Missing mandatory parameter '{req}' for tool '{tool_name}'")
                raise ValueError(f"Required parameter '{req}' missing.")

        # 2. Path security validations if arguments appear to reference absolute paths
        for k, v in args.items():
            if isinstance(v, str) and (v.startswith("/") or v.startswith("\\") or ":" in v):
                # Verify sandboxed path logic constraints safely
                if not self.is_path_safe(v):
                    raise PermissionError(f"Argument '{k}' triggers path execution boundary violations.")

        # 3. Execution boundary isolation
        try:
            exec_timeout = timeout_override or 10.0
            
            # Support both coroutines and synchronous functions seamlessly
            if inspect.iscoroutinefunction(handler):
                result = await asyncio.wait_for(handler(**args), timeout=exec_timeout)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: handler(**args))
                
            logger.info(f"Successfully finalized tool execution: {tool_name}")
            return result

        except asyncio.TimeoutError:
            logger.error(f"Tool execution timed out during execution: {tool_name}")
            return f"Error: execution of {tool_name} exceeded runtime caps."
        except Exception as e:
            logger.exception(f"Isolated exception raised executing tool {tool_name}: {e}")
            return f"Error executing tool: {str(e)}"
