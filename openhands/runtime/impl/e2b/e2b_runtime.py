from typing import Callable

import tenacity

from containers.runtime.code.openhands.utils.async_utils import call_sync_from_async
from openhands.core.config import OpenHandsConfig
from openhands.core.logger import DEBUG
from openhands.events.action import (
    FileReadAction,
    FileWriteAction,
)
from openhands.events.observation import (
    ErrorObservation,
    FileReadObservation,
    FileWriteObservation,
    Observation,
)
from openhands.events.stream import EventStream
from openhands.integrations.provider import PROVIDER_TOKEN_TYPE
from openhands.runtime.impl.action_execution.action_execution_client import (
    ActionExecutionClient,
)
from openhands.runtime.impl.docker.docker_runtime import _is_retryablewait_until_alive_error
from openhands.runtime.impl.e2b.filestore import E2BFileStore
from openhands.runtime.impl.e2b.sandbox import E2BBox
from openhands.runtime.plugins import PluginRequirement
from openhands.runtime.runtime_status import RuntimeStatus
from openhands.runtime.utils.command import DEFAULT_MAIN_MODULE, get_action_execution_server_startup_command
from openhands.runtime.utils.files import insert_lines, read_lines
from openhands.utils.tenacity_stop import stop_if_should_exit
from openhands.core.logger import openhands_logger as logger

class E2BRuntime(ActionExecutionClient):
    # TODO find available port dynamically from e2b sandbox
    server_port = 31000
    vscode_port = 32000
    app_ports = [33000, 33001]

    def __init__(
        self,
        config: OpenHandsConfig,
        event_stream: EventStream,
        sid: str = 'default',
        plugins: list[PluginRequirement] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Callable | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = True,
        user_id: str | None = None,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
        sandbox: E2BBox | None = None,
        main_module: str = DEFAULT_MAIN_MODULE,
    ):
        super().__init__(
            config,
            event_stream,
            sid,
            plugins,
            env_vars,
            status_callback,
            attach_to_existing,
            headless_mode,
            user_id,
            git_provider_tokens,
        )
        self.main_module = main_module
        if sandbox is None:
            if config.e2b_api_key is None:
                raise ValueError('E2BRuntime requires an E2B API key')
            if config.s3_bucket_name is None:
                raise ValueError('E2BRuntime requires an S3 bucket name')
            if config.s3_access_key is None or config.s3_secret_key is None:
                raise ValueError('E2BRuntime requires S3 access and secret keys')

            # print(f'Creating E2B sandbox with ID "{config.s3_secret_key}"')
            # print(f'Creating E2B sandbox with ID "{config.s3_secret_key.get_secret_value()}"')

            self.sandbox = E2BBox(
                sid,
                config.sandbox,
                config.e2b_api_key.get_secret_value(),
                config.s3_access_key,
                str(config.s3_secret_key),
                config.s3_bucket_name,
                config.e2b_template
            )
        if not isinstance(self.sandbox, E2BBox):
            raise ValueError('E2BRuntime requires an E2BSandbox')
        self.file_store = E2BFileStore(self.sandbox.filesystem)

    def read(self, action: FileReadAction) -> Observation:
        try:
            content = self.file_store.read(action.path)
        except FileNotFoundError:
            return ErrorObservation(f'File not found: {action.path}')
        except Exception as e:
            logger.error(f'Error reading file {action.path}: {e}')
            return ErrorObservation(f'Error reading file: {e}')

        lines = read_lines(content.split('\n'), action.start, action.end)
        code_view = ''.join(lines)
        return FileReadObservation(code_view, path=action.path)

    def write(self, action: FileWriteAction) -> Observation:
        if action.start == 0 and action.end == -1:
            self.file_store.write(action.path, action.content)
            return FileWriteObservation(content='', path=action.path)
        files = self.file_store.list(action.path)
        if action.path in files:
            all_lines = self.file_store.read(action.path).split('\n')
            new_file = insert_lines(
                action.content.split('\n'), all_lines, action.start, action.end
            )
            self.file_store.write(action.path, ''.join(new_file))
            return FileWriteObservation('', path=action.path)
        else:
            # FIXME: we should create a new file here
            return ErrorObservation(f'File not found: {action.path}')

    @property
    def action_execution_server_url(self) -> str:
        if self.sandbox.is_running():
            return self.sandbox.get_url(self.server_port)

        raise RuntimeError(
            'Action execution server is not running. Please call connect() before accessing the URL.'
        )

    def _get_action_execution_server_startup_command(self) -> list[str]:
        return get_action_execution_server_startup_command(
            server_port=self.server_port,
            plugins=self.plugins,
            app_config=self.config,
            main_module=self.main_module,
            override_user_id=1001,
        )

    def _get_action_execution_server_startup_environment(self) -> dict[str, str]:
        """
        Returns the environment variables to be used when starting the action execution server.
        """
        environment = dict(**self.initial_env_vars)
        environment.update(
            {
                'port': str(self.server_port),
                'PYTHONUNBUFFERED': '1',
                # Passing in the ports means nested runtimes do not come up with their own ports!
                'VSCODE_PORT': str(self.vscode_port),
                'APP_PORT_1': str(self.app_ports[0]),
                'APP_PORT_2': str(self.app_ports[1]),
                'PIP_BREAK_SYSTEM_PACKAGES': '1',
            }
        )
        if self.config.debug or DEBUG:
            environment['DEBUG'] = 'true'
        # also update with runtime_startup_env_vars
        environment.update(self.config.sandbox.runtime_startup_env_vars)
        return environment

    @property
    def vscode_url(self) -> str | None:
        token = super().get_vscode_token()
        if not token:
            return None

        if self.sandbox.is_running():
            base_url = self.sandbox.get_url(self.vscode_port)
            vscode_url = f'{base_url}/?tkn={token}&folder={self.config.workspace_mount_path_in_sandbox}'
            return vscode_url

        raise RuntimeError(
            'Action execution server is not running. Please call connect() before accessing the URL.'
        )


    def _is_execution_server_running(self) -> bool:
        """
        Check if the action execution server is running.
        This is done by checking if the sandbox is running and if the server port is accessible.
        """
        if not self.sandbox.is_running():
            return False

        try:
            self.check_if_alive()
            return True
        except Exception as e:
            logger.warning(f'Error checking if action execution server is running')
            return False

    def init_container(self):
        """
        If the sandbox is already running, attach to it and set the API URL.
        If the sandbox is not running, start it and set the API URL.
        """
        if not self.sandbox.is_running():
            self.sandbox.start()

        if not self._is_execution_server_running():
            environment = self._get_action_execution_server_startup_environment()
            command = self._get_action_execution_server_startup_command()

            self.sandbox.execute(
                cmd=' '.join(command),
                envs=environment,
                cwd='/openhands/code/',
                background=True,
                user='root',
                # timeout=0,
            )
            logger.info(
                f'Started action execution server at {self.action_execution_server_url}'
            )

        self.set_runtime_status(RuntimeStatus.RUNTIME_STARTED)

    @tenacity.retry(
        stop=tenacity.stop_after_delay(120) | stop_if_should_exit(),
        retry=tenacity.retry_if_exception(_is_retryablewait_until_alive_error),
        reraise=False,
        wait=tenacity.wait_fixed(5),
    )
    def _wait_until_alive(self) -> None:
        self.check_if_alive()

    async def connect(self) -> None:
        if self._is_execution_server_running():
            logger.info(
                f'Action execution server is already running at {self.action_execution_server_url}'
            )
            self.set_runtime_status(RuntimeStatus.READY)
            self._runtime_initialized = True
            return

        self.set_runtime_status(RuntimeStatus.STARTING_RUNTIME)

        # TODO if sandbox exists but not running, start it
        self.init_container()

        logger.info(f'Waiting for action execution server to start at {self.action_execution_server_url}')
        await call_sync_from_async(self._wait_until_alive)

        self.set_runtime_status(RuntimeStatus.READY)
        self._runtime_initialized = True
