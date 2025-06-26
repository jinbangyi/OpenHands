from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from containers.runtime.code.openhands.utils.async_utils import call_async_from_sync
from openhands.core.exceptions import LLMMalformedActionError
from openhands.core.logger import openhands_logger as logger
from openhands.events.action.action import Action
from openhands.events.event import Event, EventSource
from openhands.events.event_filter import EventFilter
from openhands.events.serialization import event_from_dict
from openhands.events.serialization.action import ACTION_TYPE_TO_CLASS, action_from_dict
from openhands.events.serialization.event import event_to_dict
from openhands.server.dependencies import get_dependencies
from openhands.server.routes.dto import (
    ActionExecutionResponse,
    ActionRequest,
    ConfigResponse,
    CreateRuntimeSessionRequest,
    ErrorResponse,
    EventRequest,
    GetEventsRequest,
    GetEventsResponse,
    RuntimeInfoResponse,
    RuntimeSessionListResponse,
    RuntimeSessionResponse,
    SupportedActionsResponse,
    UrlResponse,
    eventClassNameToClass
)
from openhands.server.session.runtime_session import RuntimeSession
from openhands.server.shared import config, file_store
from openhands.server.user_auth import get_user_id

app = APIRouter(
    prefix='/api/runtime',
    dependencies=get_dependencies(),
    tags=['runtime_sessions'],
)

# Store active runtime sessions
_runtime_sessions: dict[str, RuntimeSession] = {}


def get_action_from_request(action_request: ActionRequest) -> Action:
    """Convert ActionRequest to Action object using action_from_dict."""
    # Validate action type first
    if action_request.action not in ACTION_TYPE_TO_CLASS:
        supported_actions = list(ACTION_TYPE_TO_CLASS.keys())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported action type: {action_request.action}. Supported types: {supported_actions}',
        )

    action_dict = action_request.model_dump(exclude_none=True)
    return action_from_dict(action_dict)


def get_event_from_request(event_request: EventRequest):
    """Convert EventRequest to Event object."""
    # Get the base event data
    event_data = event_request.model_dump(exclude={'action'}, exclude_none=True)

    # If there's an action, add it properly structured
    if event_request.action:
        # Validate action type first
        if event_request.action.action not in ACTION_TYPE_TO_CLASS:
            supported_actions = list(ACTION_TYPE_TO_CLASS.keys())
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Unsupported action type: {event_request.action.action}. Supported types: {supported_actions}',
            )
        # Merge action data into event data
        event_data.update(event_request.action.model_dump(exclude_none=True))

    return event_from_dict(event_data)


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

    # Ensure the session is connected
    if getattr(runtime_session.runtime, 'check_if_alive'):
        try:
            getattr(runtime_session.runtime, 'check_if_alive')()
        except Exception as e:
            logger.warning(
                f'Runtime session {session_id} is not alive, attempting to reconnect: {e}'
            )
            call_async_from_sync(runtime_session.connect_runtime)
            logger.info(f'Reconnecting runtime session {session_id} due to: {e}')
        # raise HTTPException(
        #     status_code=status.HTTP_410_GONE,
        #     detail='Runtime session is no longer active',
        # )

    return runtime_session


@app.get(
    '/actions',
    response_model=SupportedActionsResponse,
    summary="List supported action types",
    description="Get a comprehensive list of all supported action types and their corresponding classes.",
)
async def list_supported_actions() -> SupportedActionsResponse:
    """
    List all supported action types and their corresponding classes.

    This endpoint provides information about all available action types that can be
    executed in runtime sessions, including their class names and total count.

    Returns:
        SupportedActionsResponse: Dictionary containing supported actions mapping and total count
    """
    supported_actions = {
        action_type: action_class.__name__
        for action_type, action_class in ACTION_TYPE_TO_CLASS.items()
    }
    return SupportedActionsResponse(
        supported_actions=supported_actions, total_count=len(supported_actions)
    )


@app.post(
    '/sessions',
    response_model=RuntimeSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new runtime session",
    description="Create a new runtime-only session without starting an agent conversation.",
)
async def create_runtime_session(
    request: CreateRuntimeSessionRequest = Body(
        ...,
        description="Request to create a runtime session with optional custom session ID",
        examples=[
            {},  # Server generates session ID
            {"session_id": "my-custom-session-123"},
            {"session_id": None},  # Explicit null for server generation
        ],
    ),
    user_id: str = Depends(get_user_id),
) -> RuntimeSessionResponse:
    """
    Create a new runtime-only session without starting an agent conversation.

    Runtime sessions provide isolated environments for executing commands, running code,
    and managing files. Each session has its own event stream and runtime environment.

    Args:
        request: Session creation request with optional custom session ID
        user_id: Authenticated user ID from dependency injection

    Returns:
        RuntimeSessionResponse: Created session details with status and session ID

    Raises:
        HTTPException: If session creation fails or session ID already exists
    """
    """Create a new runtime-only session without starting an agent."""
    import uuid

    session_id = request.session_id or str(uuid.uuid4())

    if session_id in _runtime_sessions and _runtime_sessions[session_id].is_alive:
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


@app.get(
    '/sessions/{session_id}',
    response_model=RuntimeInfoResponse,
    summary="Get runtime session information",
    description="Retrieve detailed information about a specific runtime session.",
)
async def get_runtime_session_info(
    session_id: str,
    user_id: str = Depends(get_user_id),
) -> RuntimeInfoResponse:
    """
    Get comprehensive information about a runtime session.

    Provides status, metadata, and runtime details for the specified session.
    Only the session owner can access this information.

    Args:
        session_id: Unique identifier for the runtime session
        user_id: Authenticated user ID from dependency injection

    Returns:
        RuntimeInfoResponse: Session information including type, status, and activity

    Raises:
        HTTPException: 404 if session not found, 403 if access denied
    """
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


@app.delete(
    '/sessions/{session_id}',
    status_code=status.HTTP_200_OK,
    summary="Close runtime session",
    description="Close and permanently remove a runtime session and all its resources.",
    responses={
        200: {"description": "Session closed successfully"},
        404: {"description": "Session not found", "model": ErrorResponse},
        403: {"description": "Access denied", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def close_runtime_session(
    session_id: str,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """
    Close and remove a runtime session.

    Permanently terminates the runtime session, closes all connections,
    and frees up resources. This action cannot be undone.

    Args:
        session_id: Unique identifier for the runtime session to close
        user_id: Authenticated user ID from dependency injection

    Returns:
        JSONResponse: Success confirmation message

    Raises:
        HTTPException: 404 if session not found, 403 if access denied
    """
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


@app.get(
    '/sessions',
    response_model=RuntimeSessionListResponse,
    summary="List runtime sessions",
    description="Get a list of all runtime sessions accessible to the current user.",
)
async def list_runtime_sessions(
    user_id: str = Depends(get_user_id),
) -> RuntimeSessionListResponse:
    """
    List all runtime sessions for the current user.

    Returns information about all runtime sessions that the authenticated
    user owns or has access to.

    Args:
        user_id: Authenticated user ID from dependency injection

    Returns:
        RuntimeSessionListResponse: List of accessible runtime sessions
    """
    """List all runtime sessions for the current user."""
    user_sessions = []
    for session_id, runtime_session in _runtime_sessions.items():
        if runtime_session.user_id == user_id:
            info = runtime_session.get_runtime_info()
            user_sessions.append(RuntimeInfoResponse(**info))

    return RuntimeSessionListResponse(sessions=user_sessions)


@app.post(
    '/sessions/{session_id}/execute',
    response_model=ActionExecutionResponse,
    summary="Execute action in runtime session",
    description="Execute any supported action type in the specified runtime session.",
    responses={
        200: {"description": "Action executed successfully"},
        400: {"description": "Invalid action format", "model": ErrorResponse},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        500: {"description": "Execution failed", "model": ErrorResponse},
    },
)
async def execute_command(
    session_id: str,
    action_request: ActionRequest = Body(
        ...,
        description="The action to execute in the runtime session",
        examples=[
            {
                "action": "run",
                "args": {"command": "ls -la", "thought": "List directory contents"},
            },
            {
                "action": "write",
                "args": {
                    "path": "/tmp/hello.py",
                    "content": "print('Hello, World!')",
                    "thought": "Create a simple Python script",
                },
            },
            {
                "action": "run_ipython",
                "args": {
                    "code": "import pandas as pd\ndf = pd.DataFrame({'x': [1, 2, 3]})\nprint(df)",
                    "thought": "Create and display a pandas DataFrame",
                },
            },
        ],
    ),
    user_id: str = Depends(get_user_id),
) -> ActionExecutionResponse:
    """
    Execute a command in the runtime session.

    Supports all action types available in the OpenHands framework, including:
    - Shell commands (run)
    - Python code execution (run_ipython)
    - File operations (read, write, edit)
    - Browser automation (browse, browse_interactive)
    - Agent actions (think, finish, message)

    Args:
        session_id: The runtime session ID
        action_request: The action to execute with all required arguments
        user_id: User ID from authentication

    Returns:
        ActionExecutionResponse: Execution results including action type and ID

    Raises:
        HTTPException: For invalid actions, access denied, or execution failures
    """
    """Execute a command in the runtime session.

    Args:
        session_id: The runtime session ID
        action_request: The action to execute (any valid action type from openhands.events.action)
        user_id: User ID from authentication

    Returns:
        JSONResponse with execution results or error message
    """
    runtime_session = get_runtime_session(session_id, user_id)

    try:
        action = get_action_from_request(action_request)

        # Create an event from the action and add to event stream
        new_event = runtime_session.event_stream.add_event(action, EventSource.USER)

        logger.info(
            f'Command execution requested in session {session_id}: {getattr(action, "action", "unknown")} - {action}'
        )

        return ActionExecutionResponse(
            message='Action executed successfully',
            action_type=getattr(action, 'action', 'unknown'),
            action_id=str(new_event.id),
        )
    except LLMMalformedActionError as e:
        logger.error(f'Invalid action format in session {session_id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid action format: {str(e)}',
        )
    except Exception as e:
        logger.error(f'Error executing command in session {session_id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to execute command: {str(e)}',
        )


@app.get(
    '/sessions/{session_id}/config',
    response_model=ConfigResponse,
    summary="Get runtime session configuration",
    description="Retrieve the configuration settings for a specific runtime session.",
)
async def get_runtime_session_config(
    session_id: str,
    user_id: str = Depends(get_user_id),
) -> ConfigResponse:
    """
    Get the configuration for a runtime session.

    Returns runtime-specific configuration including environment settings,
    container details, and other session parameters.

    Args:
        session_id: Unique identifier for the runtime session
        user_id: Authenticated user ID from dependency injection

    Returns:
        ConfigResponse: Configuration dictionary for the session

    Raises:
        HTTPException: 404 if session not found, 403 if access denied
    """
    """Get the configuration for a runtime session."""
    runtime_session = get_runtime_session(session_id, user_id)

    try:
        config = runtime_session.get_config()
        return ConfigResponse(config=config)
    except Exception as e:
        logger.error(f'Error getting config for session {session_id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get config: {str(e)}',
        )


@app.get(
    '/sessions/{session_id}/vscode-url',
    response_model=UrlResponse,
    summary="Get VSCode URL",
    description="Get the VSCode development environment URL for a runtime session.",
)
async def get_vscode_url(
    session_id: str,
    user_id: str = Depends(get_user_id),
) -> UrlResponse:
    """
    Get the VSCode URL for a runtime session.

    Provides access to a web-based VSCode interface for the runtime session,
    allowing direct code editing and development within the session environment.

    Args:
        session_id: Unique identifier for the runtime session
        user_id: Authenticated user ID from dependency injection

    Returns:
        UrlResponse: VSCode access URL

    Raises:
        HTTPException: 404 if session not found, 403 if access denied
    """
    """Get the VSCode URL for a runtime session."""
    runtime_session = get_runtime_session(session_id, user_id)

    try:
        url = runtime_session.get_vscode_url()
        return UrlResponse(url=url)
    except Exception as e:
        logger.error(f'Error getting VSCode URL for session {session_id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get VSCode URL: {str(e)}',
        )


@app.get(
    '/sessions/{session_id}/web-hosts',
    response_model=UrlResponse,
    summary="Get web hosts",
    description="Get available web host addresses for a runtime session.",
)
async def get_web_hosts(
    session_id: str,
    user_id: str = Depends(get_user_id),
) -> UrlResponse:
    """
    Get the web hosts for a runtime session.

    Returns a list of available host addresses that can be used to access
    web services running within the runtime session.

    Args:
        session_id: Unique identifier for the runtime session
        user_id: Authenticated user ID from dependency injection

    Returns:
        UrlResponse: List of available host addresses

    Raises:
        HTTPException: 404 if session not found, 403 if access denied
    """
    """Get the web hosts for a runtime session."""
    runtime_session = get_runtime_session(session_id, user_id)

    try:
        hosts = runtime_session.get_web_hosts()
        return UrlResponse(hosts=hosts)
    except Exception as e:
        logger.error(f'Error getting web hosts for session {session_id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get web hosts: {str(e)}',
        )


@app.get(
    '/sessions/{session_id}/events',
    response_model=GetEventsResponse,
    summary="Get runtime session events",
    description="Search and retrieve events from a runtime session's event stream with filtering and pagination.",
)
async def get_runtime_session_events(
    session_id: str,
    eventRequest: GetEventsRequest = Query(
        default=GetEventsRequest(reverse=True, limit=10, include_types=('Observation',)),
        examples=[
            {
                "start_id": 0,
                "reverse": True,
                "limit": 10,
                "include_types": ["Observation"],
            },
            {
                "start_id": 0,
                "end_id": None,
                "reverse": True,
                "limit": 5,
                "include_types": ["Observation", "Action"],
            },
        ],
        description="Filter events by type (e.g., 'Observation', 'Action', 'Event')"
    ),
    user_id: str = Depends(get_user_id),
) -> GetEventsResponse:
    """
    Search through the event stream with filtering and pagination.

    Provides powerful filtering and pagination capabilities for retrieving events
    from a runtime session's event stream. Supports chronological ordering,
    ID-based ranges, and result limiting.

    Args:
        session_id: The runtime session ID
        eventRequest: Request parameters for filtering and pagination
        user_id: User ID from authentication

    Returns:
        GetEventsResponse: Dictionary containing matching events and pagination info

    Raises:
        HTTPException: 404 if session not found, 403 if access denied
    """
    runtime_session = get_runtime_session(session_id, user_id)

    try:
        # Get matching events from the stream
        event_stream = runtime_session.event_stream
        events = list(
            event_stream.search_events(
                start_id=eventRequest.start_id,
                end_id=eventRequest.end_id,
                reverse=eventRequest.reverse,
                filter=EventFilter(
                    include_types=tuple(
                        eventClassNameToClass[i] for i in (eventRequest.include_types or [])
                    ),
                    source=eventRequest.filter_source,
                    query=eventRequest.filter_query,
                    cause=eventRequest.cause,
                ),
                limit=eventRequest.limit + 1,
            )
        )

        # Check if there are more events
        has_more = len(events) > eventRequest.limit
        if has_more:
            events = events[:eventRequest.limit]  # Remove the extra event

        events_json = [event_to_dict(event) for event in events]
        return GetEventsResponse(
            events=events_json,
            has_more=has_more,
        )
    except Exception as e:
        logger.error(f'Error getting events for session {session_id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get events: {str(e)}',
        )


@app.post(
    '/sessions/{session_id}/events',
    status_code=status.HTTP_201_CREATED,
    summary="Add event to runtime session",
    description="Add a new event (action or observation) to a runtime session's event stream.",
    responses={
        201: {"description": "Event added successfully"},
        400: {"description": "Invalid event format", "model": ErrorResponse},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        500: {"description": "Failed to add event", "model": ErrorResponse},
    },
)
async def add_runtime_session_event(
    session_id: str,
    event_request: EventRequest = Body(
        ...,
        description="The event data to add to the runtime session",
        examples=[
            {
                "action": {
                    "action": "run",
                    "args": {
                        "command": "echo 'Hello World'",
                        "thought": "Test command execution",
                    },
                }
            },
            {
                "action": {
                    "action": "write",
                    "args": {
                        "path": "/tmp/test.txt",
                        "content": "Test file content",
                        "thought": "Create test file",
                    },
                }
            },
            {
                "observation": "Command completed successfully",
                "content": "Hello World",
                "source": "runtime",
            },
            {
                "message": "User provided feedback",
                "source": "user",
                "timestamp": "2024-01-01T12:00:00Z",
            },
        ],
    ),
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """
    Add an event to the runtime session's event stream.

    Supports adding various types of events including actions, observations,
    and custom events. Events are automatically timestamped and assigned IDs
    when added to the stream.

    Args:
        session_id: The runtime session ID
        event_request: The event data containing action or observation details
        user_id: User ID from authentication

    Returns:
        JSONResponse: Success confirmation

    Raises:
        HTTPException: For invalid events, access denied, or processing failures
    """
    """Add an event to the runtime session's event stream."""
    runtime_session = get_runtime_session(session_id, user_id)

    try:
        event = get_event_from_request(event_request)
        new_event = runtime_session.event_stream.add_event(event, EventSource.USER)
        logger.info(f'Added event to session {session_id}: {event}')

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                'success': True,
                'event_id': new_event.id,
            }
        )
    except LLMMalformedActionError as e:
        logger.error(f'Invalid action format in event for session {session_id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid action format: {str(e)}',
        )
    except Exception as e:
        logger.error(f'Error adding event to session {session_id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to add event: {str(e)}',
        )
