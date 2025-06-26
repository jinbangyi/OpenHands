"""
Runtime Sessions DTOs - Pydantic models for runtime session API endpoints.

This module contains all request/response models for the runtime sessions API,
following Pydantic v2 best practices with comprehensive validation and documentation.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from openhands.events.action.action import Action
from openhands.events.action.agent import (
    AgentDelegateAction,
    AgentFinishAction,
    AgentRejectAction,
    AgentThinkAction,
    ChangeAgentStateAction,
    CondensationAction,
    RecallAction,
)
from openhands.events.action.browse import BrowseInteractiveAction, BrowseURLAction
from openhands.events.action.commands import CmdRunAction, IPythonRunCellAction
from openhands.events.action.empty import NullAction
from openhands.events.action.files import (
    FileEditAction,
    FileReadAction,
    FileWriteAction,
)
from openhands.events.action.mcp import MCPAction
from openhands.events.action.message import MessageAction, SystemMessageAction
from openhands.events.event_filter import EventFilter
from openhands.events.observation.observation import Observation
from openhands.events.serialization.action import ACTION_TYPE_TO_CLASS
from openhands.events.serialization.observation import observations
from openhands.events.serialization.action import actions


eventClassNameToClass = dict(
    (ob_class.__name__, ob_class)
    for ob_class in (observations + actions + (Action, Observation))
)


class CreateRuntimeSessionRequest(BaseModel):
    """
    Request model for creating a new runtime session.

    A runtime session provides an isolated environment for executing commands,
    running code, and managing files without starting a full agent conversation.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {},  # Let server generate session ID
                {"session_id": "my-custom-session-123"},
                {"session_id": None},  # Explicit null for server generation
            ]
        }
    )

    session_id: Optional[str] = Field(
        default=None,
        description="Optional custom session ID. If not provided, server will generate one.",
        examples=["my-session-123", "user-workspace-001"],
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",  # Alphanumeric, underscore, hyphen only
    )

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID format if provided."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Session ID cannot be empty string")
        return v


class RuntimeSessionResponse(BaseModel):
    """
    Response model for runtime session operations.

    Provides status information and details about the runtime session operation result.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "session_id": "session-abc123",
                    "message": "Runtime session created successfully",
                },
                {
                    "status": "error",
                    "session_id": "session-abc123",
                    "message": "Session already exists",
                },
            ]
        }
    )

    status: Literal["ok", "error"] = Field(description="Operation status indicator")

    session_id: str = Field(
        description="The session ID that was created or attempted to be created",
        examples=["session-abc123", "user-workspace-001"],
    )

    message: Optional[str] = Field(
        default=None,
        description="Additional information about the operation result",
        examples=[
            "Runtime session created successfully",
            "Session already exists",
            "Failed to create runtime session: insufficient resources",
        ],
    )


class RuntimeInfoResponse(BaseModel):
    """
    Response model containing detailed information about a runtime session.

    Provides comprehensive status and metadata about an active runtime session.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "session_id": "session-abc123",
                    "runtime_type": "EventStreamRuntime",
                    "is_alive": True,
                    "last_active": 1735209600,
                }
            ]
        }
    )

    session_id: str = Field(
        description="Unique identifier for the runtime session",
        examples=["session-abc123", "user-workspace-001"],
    )

    runtime_type: str = Field(
        description="Type of runtime environment (e.g., EventStreamRuntime, DockerRuntime)",
        examples=["EventStreamRuntime", "DockerRuntime", "LocalRuntime"],
    )

    is_alive: bool = Field(
        description="Whether the runtime session is currently active and responsive"
    )

    last_active: int = Field(
        description="Unix timestamp of the last activity in the session",
        examples=[1735209600, 1735296000],
    )


class ActionRequest(BaseModel):
    """
    Generic action request model that accepts any supported action type.

    This model provides a flexible interface for executing various types of actions
    in the runtime environment, from shell commands to file operations to AI agent actions.
    The validation and conversion is handled by the existing action_from_dict system.

    Supported action types:
    - run: Execute shell commands (CmdRunAction)
    - run_ipython: Execute Python code (IPythonRunCellAction)
    - read: Read files (FileReadAction)
    - write: Write files (FileWriteAction)
    - edit: Edit files (FileEditAction)
    - browse: Browse URLs (BrowseURLAction)
    - browse_interactive: Interactive browsing (BrowseInteractiveAction)
    - think: Agent thinking (AgentThinkAction)
    - finish: Agent completion (AgentFinishAction)
    - reject: Agent rejection (AgentRejectAction)
    - message: User messages (MessageAction)
    - mcp: MCP tool calls (MCPAction)
    - null: No-op actions (NullAction)
    - delegate: Agent delegation (AgentDelegateAction)
    - recall: Memory recall (RecallAction)
    - condensation: Memory condensation (CondensationAction)
    - change_agent_state: Change agent state (ChangeAgentStateAction)
    - system_message: System messages (SystemMessageAction)
    """

    model_config = ConfigDict(
        extra='allow',
        json_schema_extra={
            "examples": [
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
                {
                    "action": "read",
                    "args": {
                        "path": "/etc/passwd",
                        "start": 1,
                        "end": 10,
                        "thought": "Read first 10 lines of passwd file",
                    },
                },
                {
                    "action": "browse",
                    "args": {
                        "url": "https://httpbin.org/json",
                        "thought": "Fetch JSON data from httpbin",
                    },
                },
            ]
        },
    )

    action: str = Field(
        description="The type of action to perform",
        examples=["run", "write", "read", "run_ipython", "browse"],
        min_length=1,
        max_length=50,
    )

    args: Union[
        NullAction,
        CmdRunAction,
        IPythonRunCellAction,
        BrowseURLAction,
        BrowseInteractiveAction,
        FileReadAction,
        FileWriteAction,
        FileEditAction,
        AgentThinkAction,
        AgentFinishAction,
        AgentRejectAction,
        AgentDelegateAction,
        RecallAction,
        ChangeAgentStateAction,
        MessageAction,
        SystemMessageAction,
        CondensationAction,
        MCPAction,
    ] = Field(
        description="""Arguments for the action. The expected fields depend on the action type:

        **Command Actions:**
        - run: command (str), thought (str), blocking (bool), timeout (int), cwd (str)

        **File Actions:**
        - read: path (str), start (int), end (int), view_range (tuple), thought (str)
        - write: path (str), content (str), start (int), end (int), thought (str)
        - edit: path (str), old_str (str), new_str (str), insert_line (int), thought (str)

        **Browser Actions:**
        - browse: url (str), thought (str), return_axtree (bool)
        - browse_interactive: browser_actions (str), thought (str)

        **Agent Actions:**
        - think: thought (str)
        - finish: outputs (dict), thought (str)
        - message: content (str), image_urls (list), wait_for_response (bool)

        **Python Actions:**
        - run_ipython: code (str), thought (str), kernel_init_code (str)

        **MCP Actions:**
        - mcp: tool (str), arguments (dict), thought (str)

        See action classes in openhands.events.action for complete schemas."""
    )

    # Optional fields that action_from_dict handles
    timeout: Optional[int] = Field(
        default=None,
        description="Timeout for the action in seconds",
        ge=1,
        le=3600,  # Max 1 hour
        examples=[30, 300, 1800],
    )

    blocking: Optional[bool] = Field(
        default=None, description="Whether the action should block until completion"
    )

    @field_validator('action')
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        """Validate that the action type is supported."""
        if v not in ACTION_TYPE_TO_CLASS:
            supported_actions = list(ACTION_TYPE_TO_CLASS.keys())
            raise ValueError(
                f"Unsupported action type: {v}. Supported types: {supported_actions}"
            )
        return v

    @model_validator(mode='after')
    def validate_args_for_action_type(self) -> 'ActionRequest':
        """Validate that args are appropriate for the specified action type."""
        # This is a basic validation - the full validation happens in action_from_dict
        if not hasattr(self.args, '__dict__') and not isinstance(self.args, dict):
            raise ValueError("Action args must be a valid object or dictionary")
        return self

    def get_action_dict(self) -> Dict[str, Any]:
        """Convert the ActionRequest to a dictionary suitable for action_from_dict."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def get_supported_actions(cls) -> Dict[str, str]:
        """Get list of supported action types with their class names."""
        return {
            action_type: action_class.__name__
            for action_type, action_class in ACTION_TYPE_TO_CLASS.items()
        }


class GetEventsRequest(BaseModel):
    """
    Request model for retrieving events from a runtime session.

    Provides filtering, pagination, and ordering options for querying
    the event stream of a runtime session.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"start_id": 0, "limit": 10, "reverse": False},
                {
                    "start_id": 100,
                    "end_id": 200,
                    "limit": 50,
                    "reverse": True,
                    "filter": {
                        "include_types": ["Observation", "Action"],
                        "source": "user",
                    },
                },
                {
                    "limit": 5,
                    "reverse": True,
                    "filter": {"include_types": ["CmdRunAction"]},
                },
            ]
        }
    )

    start_id: int = Field(
        default=0,
        description="Starting ID in the event stream (inclusive)",
        ge=0,
        examples=[0, 100, 1000],
    )

    end_id: Optional[int] = Field(
        default=None,
        description="Ending ID in the event stream (inclusive). If not specified, goes to end of stream.",
        ge=0,
        examples=[100, 500, 2000],
    )

    reverse: bool = Field(
        default=False,
        description="Whether to retrieve events in reverse chronological order (newest first)",
    )

    filter_query: Optional[str] = Field(
        default=None,
        description="Text query to filter events by content. Case-insensitive search.",
        max_length=500,
        examples=["error", "command executed", "file not found"],
    )

    filter_source: Optional[str] = Field(
        default="user",
        description="Filter events by source (e.g., 'user', 'agent', 'system')",
        max_length=50,
        examples=["user", "agent", "system"],
    )

    include_types: Optional[tuple[str]] = Field(
        default=("Observation",),
        description="List of event types to include in the results. If not specified, includes all types.",
        examples=[
            ["Observation", "CmdRunAction", "FileWriteAction"],
        ],
    )

    cause: Optional[int] = Field(
        default=None,
        description="ID of the event that caused this request, for traceability",
        ge=0,
        examples=[42, 100],
    )

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of events to return. Must be between 1 and 100.",
        examples=[10, 20, 50, 100],
    )

    @field_validator("include_types")
    @classmethod
    def include_types_must_be_in_dict_keys(cls, value):
        if value is not None and (isinstance(value, tuple) or isinstance(value, list)):
            for i in value:
                if i not in eventClassNameToClass:
                    raise ValueError(
                        f"'{i}' is not a valid event type. Must be one of: {list(eventClassNameToClass.keys())}"
                    )
        return value

    @model_validator(mode='after')
    def validate_id_range(self) -> 'GetEventsRequest':
        """Validate that end_id is greater than start_id if both are specified."""
        if self.end_id is not None and self.end_id <= self.start_id:
            raise ValueError("end_id must be greater than start_id")
        return self


class EventRequest(BaseModel):
    """
    Request model for adding events to a runtime session.

    Supports adding various types of events including actions, observations,
    and custom events to the runtime session's event stream.
    """

    model_config = ConfigDict(
        extra='allow',
        json_schema_extra={
            "examples": [
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
            ]
        },
    )

    action: Optional[ActionRequest] = Field(
        default=None,
        description="Action to perform. Must be a valid action type from openhands.events.action",
    )

    # For observation events
    observation: Optional[str] = Field(
        default=None,
        description="Observation content (e.g., command output, system status)",
        max_length=100000,  # 100KB max
        examples=[
            "Command executed successfully",
            "File not found: /path/to/file.txt",
            "HTTP 200 OK - Response received",
        ],
    )

    content: Optional[str] = Field(
        default=None,
        description="General content for the event",
        max_length=100000,  # 100KB max
        examples=[
            "Hello World",
            "Error: Permission denied",
            "Process completed with exit code 0",
        ],
    )

    # Common event fields
    message: Optional[str] = Field(
        default=None,
        description="Human-readable message describing the event",
        max_length=1000,
        examples=[
            "User executed command",
            "File operation completed",
            "System notification",
        ],
    )

    source: Optional[str] = Field(
        default=None,
        description="Source of the event (e.g., 'user', 'agent', 'system')",
        max_length=50,
        examples=["user", "agent", "system", "runtime", "browser"],
    )

    timestamp: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp for the event",
        examples=["2024-01-01T12:00:00Z", "2024-01-01T12:00:00.123Z"],
    )

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: Optional[str]) -> Optional[str]:
        """Validate timestamp format if provided."""
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(
                    "Invalid timestamp format. Use ISO 8601 format (e.g., '2024-01-01T12:00:00Z')"
                )
        return v

    @model_validator(mode='after')
    def validate_event_content(self) -> 'EventRequest':
        """Validate that at least one content field is provided."""
        if not any([self.action, self.observation, self.content, self.message]):
            raise ValueError(
                "At least one of 'action', 'observation', 'content', or 'message' must be provided"
            )
        return self


class RuntimeSessionListResponse(BaseModel):
    """
    Response model for listing runtime sessions.

    Contains a list of runtime sessions accessible to the current user.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "sessions": [
                        {
                            "session_id": "session-abc123",
                            "runtime_type": "EventStreamRuntime",
                            "is_alive": True,
                            "last_active": 1735209600,
                        },
                        {
                            "session_id": "session-def456",
                            "runtime_type": "DockerRuntime",
                            "is_alive": False,
                            "last_active": 1735123200,
                        },
                    ]
                }
            ]
        }
    )

    sessions: List[RuntimeInfoResponse] = Field(
        description="List of runtime sessions accessible to the current user"
    )


class ActionExecutionResponse(BaseModel):
    """
    Response model for action execution results.

    Provides information about the executed action and its status.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "Action executed successfully",
                    "action_type": "run",
                    "action_id": "action-123",
                },
                {
                    "message": "File written successfully",
                    "action_type": "write",
                    "action_id": "action-456",
                },
            ]
        }
    )

    message: str = Field(
        description="Human-readable message about the execution result"
    )

    action_type: str = Field(
        description="Type of action that was executed",
        examples=["run", "write", "read", "browse"],
    )

    action_id: Optional[str] = Field(
        default=None, description="Unique identifier for the executed action"
    )


class GetEventsResponse(BaseModel):
    """
    Response model for event retrieval operations.

    Contains the requested events and pagination information.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "events": [
                        {
                            "id": 1,
                            "event_type": "Action",
                            "action": "run",
                            "args": {"command": "ls -la"},
                            "timestamp": "2024-01-01T12:00:00Z",
                        }
                    ],
                    "has_more": False,
                }
            ]
        }
    )

    events: List[Dict[str, Any]] = Field(
        description="List of events matching the query criteria"
    )

    has_more: bool = Field(
        description="Whether there are more events available beyond this batch"
    )


class ErrorResponse(BaseModel):
    """
    Standard error response model.

    Provides consistent error information across all API endpoints.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"error": "Runtime session not found"},
                {"error": "Invalid action format: missing required field 'command'"},
                {"error": "Access denied to this runtime session"},
            ]
        }
    )

    error: str = Field(
        description="Human-readable error message describing what went wrong"
    )


class ConfigResponse(BaseModel):
    """
    Response model for runtime session configuration.

    Contains configuration details for a runtime session.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "config": {
                        "runtime_type": "EventStreamRuntime",
                        "container_image": "python:3.11",
                        "workspace_mount_path": "/workspace",
                        "timeout": 300,
                    }
                }
            ]
        }
    )

    config: Dict[str, Any] = Field(description="Runtime session configuration details")


class UrlResponse(BaseModel):
    """
    Response model for URL endpoints (VSCode, web hosts, etc.).

    Contains URL information for accessing runtime session resources.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"url": "http://localhost:8080/vscode"},
                {"hosts": ["localhost:3000", "localhost:8080"]},
            ]
        }
    )

    url: Optional[str] = Field(
        default=None, description="URL for accessing the resource"
    )

    hosts: Optional[List[str]] = Field(
        default=None, description="List of available host addresses"
    )


class SupportedActionsResponse(BaseModel):
    """
    Response model for listing supported action types.

    Provides information about all available action types and their corresponding classes.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "supported_actions": {
                        "run": "CmdRunAction",
                        "write": "FileWriteAction",
                        "read": "FileReadAction",
                        "browse": "BrowseURLAction",
                    },
                    "total_count": 18,
                }
            ]
        }
    )

    supported_actions: Dict[str, str] = Field(
        description="Mapping of action type names to their corresponding class names"
    )

    total_count: int = Field(description="Total number of supported action types")
