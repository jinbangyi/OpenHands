import asyncio
import time

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from openhands.core.logger import openhands_logger as logger
from openhands.events.action.browse import BrowseInteractiveAction, BrowseURLAction
from openhands.events.event import EventSource
from openhands.events.event_filter import EventFilter
from openhands.events.serialization.event import event_to_dict
from openhands.server.dependencies import get_dependencies

# TODO runtime session should using the session manager
from openhands.server.routes.runtime_sessions import get_runtime_session
from openhands.server.user_auth import get_user_id

app = APIRouter(
    prefix='/api/runtime/browser',
    dependencies=get_dependencies(),
    tags=['browser'],
)


def get_screenshot_from_event(event: dict):
    trigger_by_action = event.get("extras", {}).get('trigger_by_action', '')
    last_browser_action = event.get('extras', {}).get('last_browser_action', '')
    last_browser_action_error = event.get('extras', {}).get('last_browser_action_error', '')
    message = event.get('message', '')

    logger.info(f"Message: {message}, Triggered by action: {trigger_by_action}, {last_browser_action} {last_browser_action_error}")

    if 'screenshot' in event.get('extras', {}):
        return event['extras']['screenshot']


@app.get(
    '/{session_id}/screenshot',
    description="Get the current browser screenshot from the runtime session",
)
async def get_runtime_session_screenshot(
    session_id: str,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Get the current browser screenshot from the runtime session."""
    runtime_session = get_runtime_session(session_id, user_id)

    try:
        # Create a no-op browser action to get current state
        noop_action = BrowseInteractiveAction(
            # browser_actions='scroll(0, 0)', thought='Get current browser screenshot'
            browser_actions='noop(500)', thought='Get current browser screenshot'
            # browser_actions='goto(https://google.com)', thought='Get current browser screenshot'
        )

        # Add the action to the event stream
        runtime_session.event_stream.add_event(noop_action, EventSource.USER)

        await asyncio.sleep(2)

        # Get the recent events to find the browser observation
        events = list(
            runtime_session.event_stream.search_events(
                start_id=0,
                reverse=True,
                limit=10,
                filter=EventFilter(query="observation")
            )
        )

        # Look for a browser observation with screenshot
        for event in events:
            screenshot = get_screenshot_from_event(event_to_dict(event))
            if screenshot:
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        'screenshot': screenshot,
                        'timestamp': int(time.time()),
                        'session_id': session_id,
                        'url': getattr(event, 'url', ''),
                        'title': getattr(event, 'title', ''),
                    },
                )

        # If no screenshot found, return an error
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                'error': 'No browser screenshot available. Browser may not be initialized or no pages have been visited.'
            },
        )

    except Exception as e:
        logger.error(f'Error getting screenshot from session {session_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Failed to get screenshot: {str(e)}'},
        )


@app.post('/{session_id}/browse')
async def browse_url(
    session_id: str,
    browse_request: dict,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Browse a URL and optionally return screenshot."""
    runtime_session = get_runtime_session(session_id, user_id)

    try:
        url = browse_request.get('url')
        thought = browse_request.get('thought', '')
        return_screenshot = browse_request.get('return_screenshot', True)

        if not url:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={'error': 'URL is required'},
            )

        # Create browse action
        browse_action = BrowseURLAction(url=url, thought=thought, return_axtree=False)

        # Add action to event stream
        runtime_session.event_stream.add_event(browse_action, EventSource.USER)

        # Wait for the browse action to complete
        await asyncio.sleep(5)  # Give time for page to load

        result = {'success': True, 'url': url, 'message': 'Browse action executed'}

        # Get the browse observation if requested
        if return_screenshot:
            # Get recent events to find the browser observation
            events = list(
                runtime_session.event_stream.search_events(
                    start_id=0, reverse=True, limit=10
                )
            )

            for event in events:
                # Look for browser observation
                screenshot = get_screenshot_from_event(event)
                if screenshot:
                    result['screenshot'] = screenshot
                    result['page_title'] = getattr(event, 'title', '')
                    result['final_url'] = getattr(event, 'url', url)
                break

        return JSONResponse(status_code=status.HTTP_200_OK, content=result)

    except Exception as e:
        logger.error(f'Error browsing URL in session {session_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Failed to browse URL: {str(e)}'},
        )


@app.get('/{session_id}/browser-status')
async def get_browser_status(
    session_id: str,
    user_id: str = Depends(get_user_id),
) -> JSONResponse:
    """Check if browser is available and get its status."""
    runtime_session = get_runtime_session(session_id, user_id)

    try:
        # Check if the runtime supports browser actions
        runtime = runtime_session.runtime

        # Try to determine browser availability
        browser_available = False
        browser_info = {}

        # Check if runtime type supports browser
        runtime_type = runtime.__class__.__name__
        if runtime_type in ['DockerRuntime', 'LocalRuntime', 'RemoteRuntime']:
            browser_available = True
            browser_info['runtime_type'] = runtime_type
            browser_info['supports_browser'] = True
        elif runtime_type == 'CLIRuntime':
            browser_info['runtime_type'] = runtime_type
            browser_info['supports_browser'] = False
            browser_info['message'] = (
                'CLI Runtime does not support browser functionality'
            )

        # Try to get current browser state from recent events
        events = list(
            runtime_session.event_stream.search_events(
                start_id=0, reverse=True, limit=5
            )
        )

        last_browser_event = None
        for event in events:
            if hasattr(event, 'url') or 'browse' in str(type(event)).lower():
                last_browser_event = {
                    'type': type(event).__name__,
                    'url': getattr(event, 'url', ''),
                    'timestamp': getattr(event, 'timestamp', 0),
                }
                break

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'browser_available': browser_available,
                'browser_info': browser_info,
                'last_browser_event': last_browser_event,
                'session_id': session_id,
            },
        )

    except Exception as e:
        logger.error(f'Error checking browser status for session {session_id}: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Failed to check browser status: {str(e)}'},
        )
