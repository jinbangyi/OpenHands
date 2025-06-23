import asyncio
import time
from copy import deepcopy
from logging import LoggerAdapter

import socketio

from openhands.core.config import OpenHandsConfig
from openhands.core.logger import OpenHandsLoggerAdapter
from openhands.events.stream import EventStream
from openhands.runtime import get_runtime_cls
from openhands.runtime.base import Runtime
from openhands.storage.files import FileStore
from openhands.utils.async_utils import call_sync_from_async

ROOM_KEY = 'room:{sid}'


class RuntimeSession:
    """
    A lightweight session class that directly connects to runtime without starting an agent.
    This session only manages runtime connections and file operations.
    """

    sid: str
    sio: socketio.AsyncServer | None
    last_active_ts: int = 0
    is_alive: bool = True
    runtime: Runtime
    event_stream: EventStream
    loop: asyncio.AbstractEventLoop
    config: OpenHandsConfig
    file_store: FileStore
    user_id: str | None
    logger: LoggerAdapter

    def __init__(
        self,
        sid: str,
        config: OpenHandsConfig,
        file_store: FileStore,
        sio: socketio.AsyncServer | None,
        user_id: str | None = None,
    ):
        self.sid = sid
        self.sio = sio
        self.last_active_ts = int(time.time())
        self.file_store = file_store
        self.logger = OpenHandsLoggerAdapter(extra={'session_id': sid})
        self.user_id = user_id

        # Initialize event stream for runtime communication
        self.event_stream = EventStream(sid, file_store, user_id)

        # Copying this means that when we update variables they are not applied to the shared global configuration!
        self.config = deepcopy(config)
        self.loop = asyncio.get_event_loop()

        # Initialize runtime without agent plugins
        runtime_cls = get_runtime_cls(self.config.runtime)
        self.runtime = runtime_cls(
            config=config,
            event_stream=self.event_stream,
            sid=self.sid,
            attach_to_existing=False,
            headless_mode=True,  # Run in headless mode for runtime-only sessions
            user_id=user_id,
        )

    async def connect_runtime(self) -> None:
        """Connect to the runtime environment without starting an agent."""
        try:
            self.logger.info(f'Connecting runtime for session: {self.sid}')
            await self.runtime.connect()
            # Set up the initial environment in the runtime
            if not self.runtime.attach_to_existing:
                await call_sync_from_async(self.runtime.setup_initial_env)
            self.logger.info(f'Runtime connected successfully for session: {self.sid}')
        except Exception as e:
            self.logger.error(f'Failed to connect runtime: {e}')
            await self.send_error(f'Failed to connect runtime: {str(e)}')
            raise

    async def close(self) -> None:
        """Close the runtime session."""
        self.logger.info(f'Closing runtime session: {self.sid}')
        self.is_alive = False
        if self.event_stream:
            self.event_stream.close()
        if self.runtime:
            asyncio.create_task(call_sync_from_async(self.runtime.close))

    async def send(self, data: dict[str, object]) -> None:
        """Send data to the connected client."""
        if asyncio.get_running_loop() != self.loop:
            self.loop.create_task(self._send(data))
            return
        await self._send(data)

    async def _send(self, data: dict[str, object]) -> bool:
        """Internal method to send data via socket."""
        try:
            if not self.is_alive:
                return False
            if self.sio:
                await self.sio.emit('oh_event', data, to=ROOM_KEY.format(sid=self.sid))
            await asyncio.sleep(0.001)  # This flushes the data to the client
            self.last_active_ts = int(time.time())
            return True
        except RuntimeError as e:
            self.logger.error(f'Error sending data to websocket: {str(e)}')
            self.is_alive = False
            return False

    async def send_error(self, message: str) -> None:
        """Send an error message to the client."""
        await self.send({'error': True, 'message': message})

    async def send_status(self, status: str, message: str) -> None:
        """Send a status message to the client."""
        await self.send(
            {
                'status_update': True,
                'type': 'info',
                'id': f'RUNTIME_SESSION${status}',
                'message': message,
            }
        )

    def get_runtime_info(self) -> dict:
        """Get information about the current runtime."""
        return {
            'session_id': self.sid,
            'runtime_type': self.runtime.__class__.__name__,
            'is_alive': self.is_alive,
            'last_active': self.last_active_ts,
        }

    def get_config(self) -> dict:
        """Get the runtime configuration."""
        runtime_id = (
            getattr(self.runtime, "runtime_id", None)
            if hasattr(self.runtime, 'runtime_id')
            else None
        )
        return {
            'runtime_id': runtime_id,
            'session_id': self.sid,
            'runtime_type': self.runtime.__class__.__name__,
        }

    def get_vscode_url(self) -> str | None:
        """Get the VSCode URL for this runtime session."""
        return getattr(self.runtime, 'vscode_url', None)

    def get_web_hosts(self) -> list[str]:
        """Get the web hosts for this runtime session."""
        return getattr(self.runtime, 'web_hosts', [])

    def get_events(self, filter_params=None) -> list:
        """Get events from the runtime session's event stream."""
        # Basic implementation - can be extended with filtering
        try:
            from openhands.events.event_filter import EventFilter

            # Extract filter parameters
            start_id = int(filter_params.get('start_id', 0)) if filter_params else 0
            end_id = (
                int(filter_params.get('end_id'))
                if filter_params and filter_params.get('end_id')
                else None
            )
            reverse = (
                filter_params.get('reverse', 'false').lower() == 'true'
                if filter_params
                else False
            )
            limit = (
                min(int(filter_params.get('limit', 20)), 100) if filter_params else 20
            )

            # Create filter if needed
            event_filter = None
            if filter_params and filter_params.get('filter'):
                # This would need to be implemented based on specific filtering needs
                pass

            # Get events from the stream
            events = list(
                self.event_stream.search_events(
                    start_id=start_id,
                    end_id=end_id,
                    reverse=reverse,
                    filter=event_filter,
                    limit=limit,
                )
            )
            return events
        except Exception as e:
            self.logger.error(f'Error getting events: {e}')
            return []
