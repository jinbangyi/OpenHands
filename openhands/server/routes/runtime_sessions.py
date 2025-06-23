from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from openhands.core.logger import openhands_logger as logger
from openhands.events.event_filter import EventFilter
from openhands.events.serialization.event import event_to_dict
from openhands.server.dependencies import get_dependencies
from openhands.server.session.runtime_session import RuntimeSession
from openhands.server.shared import config, file_store
from openhands.server.user_auth import get_user_id
from openhands.events.event import EventSource
from openhands.events.serialization import event_from_dict

app = APIRouter(
    prefix='/api/runtime',
    dependencies=get_dependencies(),
    tags=['runtime_sessions'],
)

# Store active runtime sessions
_runtime_sessions: dict[str, RuntimeSession] = {}


class CreateRuntimeSessionRequest(BaseModel):
    session_id: str | None = None


class RuntimeSessionResponse(BaseModel):
    status: str
    session_id: str
    message: str | None = None


class RuntimeInfoResponse(BaseModel):
    session_id: str
    runtime_type: str
    is_alive: bool
    last_active: int


def get_runtime_session(session_id: str, user_id: str) -> RuntimeSession:
    """Helper function to get and validate runtime session access."""
    if session_id not in _runtime_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Runtime session not found'
        )

    runtime_session = _runtime_sessions[session_id]

    # Check if user owns this session
    if runtime_session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access denied to this runtime session',
        )

    return runtime_session


@app.post('/sessions', response_model=RuntimeSessionResponse)
async def create_runtime_session(
    request: CreateRuntimeSessionRequest,
    user_id: str = Depends(get_user_id),
) -> RuntimeSessionResponse:
    """Create a new runtime-only session without starting an agent."""
    import uuid

    session_id = request.session_id or str(uuid.uuid4())

    if session_id in _runtime_sessions:
        return RuntimeSessionResponse(
            status='error', session_id=session_id, message='Session already exists'
        )

    try:
        # Create runtime session
        runtime_session = RuntimeSession(
            sid=session_id,
            config=config,
            file_store=file_store,
            sio=None,  # No socket.io for pure runtime sessions
            user_id=user_id,
        )

        # Connect to runtime
        await runtime_session.connect_runtime()

        # Store the session
        _runtime_sessions[session_id] = runtime_session

        logger.info(f'Created runtime session: {session_id}')

        return RuntimeSessionResponse(
            status='ok',
            session_id=session_id,
            message='Runtime session created successfully',
        )

    except Exception as e:
        logger.error(f'Error creating runtime session: {e}')
        return RuntimeSessionResponse(
            status='error',
            session_id=session_id,
            message=f'Failed to create runtime session: {str(e)}',
        )


@app.get('/sessions/{session_id}', response_model=RuntimeInfoResponse)
async def get_runtime_session_info(
    session_id: str,
    user_id: str = Depends(get_user_id),
) -> RuntimeInfoResponse:
    """Get information about a runtime session."""
    if session_id not in _runtime_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Runtime session not found'
        )

    runtime_session = _runtime_sessions[session_id]

    # Check if user owns this session
    if runtime_session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access denied to this runtime session',
        )

    info = runtime_session.get_runtime_info()
    return RuntimeInfoResponse(**info)


@app.delete('/sessions/{session_id}')
async def close_runtime_session(
    session_id: str,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Close and remove a runtime session."""
    if session_id not in _runtime_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Runtime session not found'
        )

    runtime_session = _runtime_sessions[session_id]

    # Check if user owns this session
    if runtime_session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access denied to this runtime session',
        )

    try:
        await runtime_session.close()
        del _runtime_sessions[session_id]
        logger.info(f'Closed runtime session: {session_id}')

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'message': 'Runtime session closed successfully'},
        )
    except Exception as e:
        logger.error(f'Error closing runtime session {session_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Failed to close runtime session: {str(e)}'},
        )


@app.get('/sessions')
async def list_runtime_sessions(
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """List all runtime sessions for the current user."""
    user_sessions = []
    for session_id, runtime_session in _runtime_sessions.items():
        if runtime_session.user_id == user_id:
            info = runtime_session.get_runtime_info()
            user_sessions.append(info)

    return JSONResponse(
        status_code=status.HTTP_200_OK, content={'sessions': user_sessions}
    )


@app.post('/sessions/{session_id}/execute')
async def execute_command(
    session_id: str,
    command: dict,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Execute a command in the runtime session."""
    if session_id not in _runtime_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Runtime session not found'
        )

    runtime_session = _runtime_sessions[session_id]

    # Check if user owns this session
    if runtime_session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access denied to this runtime session',
        )

    try:
        # For now, just return a success message
        # In a full implementation, this would execute the command via the runtime
        logger.info(f'Command execution requested in session {session_id}: {command}')

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'message': 'Command execution interface ready',
                'note': 'This is a basic implementation - full command execution would be implemented based on runtime capabilities',
            },
        )
    except Exception as e:
        logger.error(f'Error executing command in session {session_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Failed to execute command: {str(e)}'},
        )


@app.get('/sessions/{session_id}/config')
async def get_runtime_session_config(
    session_id: str,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Get the configuration for a runtime session."""
    runtime_session = get_runtime_session(session_id, user_id)

    try:
        config = runtime_session.get_config()
        return JSONResponse(status_code=status.HTTP_200_OK, content={'config': config})
    except Exception as e:
        logger.error(f'Error getting config for session {session_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Failed to get config: {str(e)}'},
        )


@app.get('/sessions/{session_id}/vscode-url')
async def get_vscode_url(
    session_id: str,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Get the VSCode URL for a runtime session."""
    runtime_session = get_runtime_session(session_id, user_id)

    try:
        url = runtime_session.get_vscode_url()
        return JSONResponse(status_code=status.HTTP_200_OK, content={'url': url})
    except Exception as e:
        logger.error(f'Error getting VSCode URL for session {session_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Failed to get VSCode URL: {str(e)}'},
        )


@app.get('/sessions/{session_id}/web-hosts')
async def get_web_hosts(
    session_id: str,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Get the web hosts for a runtime session."""
    runtime_session = get_runtime_session(session_id, user_id)

    try:
        hosts = runtime_session.get_web_hosts()
        return JSONResponse(status_code=status.HTTP_200_OK, content={'hosts': hosts})
    except Exception as e:
        logger.error(f'Error getting web hosts for session {session_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Failed to get web hosts: {str(e)}'},
        )


@app.get('/sessions/{session_id}/events')
async def get_runtime_session_events(
    session_id: str,
    start_id: int = 0,
    end_id: int | None = None,
    reverse: bool = False,
    filter: EventFilter | None = None,
    limit: int = 20,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Search through the event stream with filtering and pagination.

    Args:
        session_id: The runtime session ID
        start_id: Starting ID in the event stream. Defaults to 0
        end_id: Ending ID in the event stream
        reverse: Whether to retrieve events in reverse order. Defaults to False.
        filter: Filter for events
        limit: Maximum number of events to return. Must be between 1 and 100. Defaults to 20
        user_id: User ID from authentication

    Returns:
        JSONResponse: Dictionary containing:
            - events: List of matching events
            - has_more: Whether there are more matching events after this batch
    """
    runtime_session = get_runtime_session(session_id, user_id)

    if limit < 0 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid limit'
        )

    try:
        # Get matching events from the stream
        event_stream = runtime_session.event_stream
        events = list(
            event_stream.search_events(
                start_id=start_id,
                end_id=end_id,
                reverse=reverse,
                filter=filter,
                limit=limit + 1,
            )
        )

        # Check if there are more events
        has_more = len(events) > limit
        if has_more:
            events = events[:limit]  # Remove the extra event

        events_json = [event_to_dict(event) for event in events]
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'events': events_json,
                'has_more': has_more,
            },
        )
    except Exception as e:
        logger.error(f'Error getting events for session {session_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Failed to get events: {str(e)}'},
        )


@app.post('/sessions/{session_id}/events')
async def add_runtime_session_event(
    session_id: str,
    request: Request,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Add an event to the runtime session's event stream."""
    runtime_session = get_runtime_session(session_id, user_id)

    try:
        data = await request.json()

        event = event_from_dict(data.copy())
        runtime_session.event_stream.add_event(event, EventSource.USER)
        print(f'Added event to session {session_id}: {event}')

        return JSONResponse(status_code=status.HTTP_200_OK, content={'success': True})
    except Exception as e:
        logger.error(f'Error adding event to session {session_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Failed to add event: {str(e)}'},
        )

