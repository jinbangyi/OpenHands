import contextlib
import warnings
from contextlib import asynccontextmanager
from os import environ
from typing import AsyncIterator

from fastapi import applications
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.routing import Mount
from fastapi.staticfiles import StaticFiles

with warnings.catch_warnings():
    warnings.simplefilter('ignore')

from fastapi import FastAPI

import openhands.agenthub  # noqa F401 (we import this to get the agents registered)
from openhands import __version__
from openhands.server.routes.browser import app as browser_router
from openhands.server.routes.conversation import app as conversation_api_router
from openhands.server.routes.feedback import app as feedback_api_router
from openhands.server.routes.files import app as files_api_router
from openhands.server.routes.git import app as git_api_router
from openhands.server.routes.health import add_health_endpoints
from openhands.server.routes.manage_conversations import (
    app as manage_conversation_api_router,
)
from openhands.server.routes.mcp import mcp_server
from openhands.server.routes.public import app as public_api_router
from openhands.server.routes.runtime_sessions import app as runtime_sessions_router
from openhands.server.routes.secrets import app as secrets_router
from openhands.server.routes.security import app as security_api_router
from openhands.server.routes.settings import app as settings_router
from openhands.server.routes.trajectory import app as trajectory_router
from openhands.server.shared import conversation_manager

mcp_app = mcp_server.http_app(path='/mcp')


def combine_lifespans(*lifespans):
    # Create a combined lifespan to manage multiple session managers
    @contextlib.asynccontextmanager
    async def combined_lifespan(app):
        async with contextlib.AsyncExitStack() as stack:
            for lifespan in lifespans:
                await stack.enter_async_context(lifespan(app))
            yield

    return combined_lifespan


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with conversation_manager:
        yield


app = FastAPI(
    title='OpenHands',
    description='OpenHands: Code Less, Make More',
    version=__version__,
    lifespan=combine_lifespans(_lifespan, mcp_app.lifespan),
    routes=[Mount(path='/mcp', app=mcp_app)],
)

# change to False to disable local static files
if environ.get('OPENHANDS_ENABLE_STATIC_FILES', 'false').lower() in ('true', '1'):
    app.mount('/static', StaticFiles(directory='./static'), name='static')

    def swagger_monkey_patch(*args, **kwargs):
        return get_swagger_ui_html(
            *args,
            **kwargs,
            swagger_js_url='/static/swagger-ui/swagger-ui-bundle.js',
            swagger_css_url='/static/swagger-ui/swagger-ui.css',
        )

    applications.get_swagger_ui_html = swagger_monkey_patch  # type: ignore

app.include_router(public_api_router)
app.include_router(files_api_router)
app.include_router(security_api_router)
app.include_router(feedback_api_router)
app.include_router(conversation_api_router)
app.include_router(manage_conversation_api_router)
app.include_router(runtime_sessions_router)
app.include_router(browser_router)
app.include_router(settings_router)
app.include_router(secrets_router)
app.include_router(git_api_router)
app.include_router(trajectory_router)
add_health_endpoints(app)
