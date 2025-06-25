import copy
import os
import tarfile
from glob import glob
import threading
from typing import Optional, Dict

from e2b import CommandHandle, Sandbox as E2BSandbox
from e2b.sandbox_sync.sandbox_api import SandboxApi
from e2b.sandbox.sandbox_api import SandboxQuery
from e2b.exceptions import TimeoutException
from e2b.connection_config import Username

from openhands.core.config import SandboxConfig
from openhands.core.logger import openhands_logger as logger


class E2BBox:
    """
    E2BBox is a wrapper around the E2B Sandbox API to manage sandboxes.
    use s3 as a storage backend for sandboxes, https://e2b.dev/docs/sandbox/connect-bucket#amazon-s3
    TODO accessKey and secretKey are in filesystem
    start -> create a new sandbox, mount a storage
    stop -> kill a sandbox, unmount storage

    TODO e2b has a new feature to pause and resume sandboxes, we can use it to easily manage resources
    """
    closed = False
    _cwd: str = '/home/user'
    _mount_dir: str = '/home/user/bucket'
    _env: dict[str, str] = {}
    is_initial_session: bool = True
    # < 1h
    timeout: int = 1200 # 20m

    def __init__(
        self,
        sid: str,
        config: SandboxConfig,
        e2b_api_key: str,
        s3_access_key: str,
        s3_secret_key: str,
        bucket_name: str,
        template: str = 'openhands',
    ):
        self.s3_access_key = s3_access_key
        self.s3_secret_key = s3_secret_key
        self.bucket_name = bucket_name
        self.e2b_api_key = e2b_api_key
        self.template = template
        self.sid = sid
        self.config = copy.deepcopy(config)
        self.initialize_plugins: bool = config.initialize_plugins

        self.sandbox = self._init_sandbox()
        logger.debug(f'Started E2B sandbox with ID "{self.sandbox.sandbox_id}"')

    def is_running(self) -> bool:
        """Check if the sandbox is running."""
        return not self.closed and self.sandbox.is_running()

    def get_url(self, port: int):
        host = self.sandbox.get_host(port)
        url = f"https://{host}"
        return url

    @property
    def filesystem(self):
        return self.sandbox.files

    def _init_sandbox(self):
        sandbox = self._create_sandbox()
        self._mount_storage(sandbox)
        return sandbox

    def _create_sandbox(self):
        """
        Create a new sandbox if it does not exist.
        If it exists, connect to it.
        """
        metadata = {
            'name': f'OpenHands Sandbox {self.sid}',
            'description': 'Sandbox for OpenHands E2B integration',
            'sid': self.sid,
        }

        sandboxes = SandboxApi.list(api_key=self.e2b_api_key, query=SandboxQuery(metadata=metadata))
        if len(sandboxes) > 0:
            sandbox = sandboxes[0]
            logger.debug(f'Found existing sandbox with ID "{sandbox.sandbox_id}"')
            return E2BSandbox.connect(sandbox_id=sandbox.sandbox_id, api_key=self.e2b_api_key)

        # If no sandbox found, create a new one
        logger.debug('No existing sandbox found, creating a new one')
        sandbox = E2BSandbox(
            api_key=self.e2b_api_key,
            template=self.template,
            metadata=metadata,
            timeout=self.timeout,
        )
        return sandbox

    def _mount_storage(self, sandbox: E2BSandbox):
        """
        Mount the S3 bucket to the sandbox's filesystem.
        """
        if sandbox.is_running():
            ok = sandbox.files.make_dir(self._mount_dir, user='root')
            # if dir not exists, create it
            if ok:
                # Create a file with the credentials
                sandbox.files.write(
                    '/root/.passwd-s3fs',
                    f'{self.s3_access_key}:{self.s3_secret_key}',
                    'root',
                )

                sandbox.commands.run(
                    'sudo chmod 600 /root/.passwd-s3fs'
                )

                # Mount the S3 bucket
                sandbox.commands.run(
                    'sudo apt-get install -y s3fs && '
                    f'sudo s3fs {self.bucket_name} '
                    f'{self._mount_dir} -o passwd_file=/root/.passwd-s3fs '
                    '-o url=https://s3.amazonaws.com -o use_path_request_style '
                    '-o allow_other -o umask=0000'
                )
                logger.debug(f'S3 bucket "{self.bucket_name}" mounted to "{self._mount_dir}"')

    def start(self):
        """Start the sandbox if it is not already running."""
        if not self.is_running():
            self.sandbox = self._init_sandbox()
            logger.debug(f'Sandbox started with ID "{self.sandbox.sandbox_id}"')

    def _stop(self):
        """Stop the sandbox and unmount the storage."""
        if self.is_running():
            logger.info(f'Stopping sandbox with ID "{self.sandbox.sandbox_id}"')
            self.sandbox.kill()
            self.closed = True
            logger.info('Sandbox stopped')

    def _archive(self, host_src: str, recursive: bool = False):
        if recursive:
            assert os.path.isdir(host_src), (
                'Source must be a directory when recursive is True'
            )
            files = glob(host_src + '/**/*', recursive=True)
            srcname = os.path.basename(host_src)
            tar_filename = os.path.join(os.path.dirname(host_src), srcname + '.tar')
            with tarfile.open(tar_filename, mode='w') as tar:
                for file in files:
                    tar.add(
                        file, arcname=os.path.relpath(file, os.path.dirname(host_src))
                    )
        else:
            assert os.path.isfile(host_src), (
                'Source must be a file when recursive is False'
            )
            srcname = os.path.basename(host_src)
            tar_filename = os.path.join(os.path.dirname(host_src), srcname + '.tar')
            with tarfile.open(tar_filename, mode='w') as tar:
                tar.add(host_src, arcname=srcname)
        return tar_filename

    def execute(
            self,
            cmd: str,
            cwd: str | None = None,
            envs: Dict[str, str] | None = None,
            timeout: float | None = 60,
            background: bool = False,
            user: Username = 'user',
        ):
        """Execute a command in the sandbox."""
        if not self.is_running():
            raise TimeoutException('Sandbox is not running')

        resp = self.sandbox.commands.run(
            cmd=cmd,
            cwd=cwd,
            envs=envs,
            # the timeout will auto stop the log
            timeout=timeout,
            background=background,
            user=user,
        )

        logger.debug(f'Command executed: {cmd}')
        if not isinstance(resp, CommandHandle):
            logger.debug(f'Command response: {resp.stderr}')
            logger.debug(f'Command response: {resp.stdout}')
            logger.debug(f'Command exit code: {resp.exit_code}')
        else:
            threading.Thread(target=self._watch_events, args=(resp,), daemon=True).start()

            logger.debug(f'Command handle created with PID: {resp.pid}')

    def _watch_events(self, command_handle: CommandHandle):
        """
        Watch events from a command handle.
        This is useful for long-running commands to get real-time output.
        """
        for event in command_handle._handle_events():
            if isinstance(event, tuple):
                stdout, stderr, pty_output = event
                if stdout:
                    logger.debug(f'STDOUT: {stdout}')
                if stderr:
                    logger.debug(f'STDERR: {stderr}')
                if pty_output:
                    logger.debug(f'PTY Output: {pty_output}')
            else:
                logger.debug(f'Event: {event}')

    def copy_to(self, host_src: str, sandbox_dest: str, recursive: bool = False):
        """Copies a local file or directory to the sandbox."""
        tar_filename = self._archive(host_src, recursive)

        # Prepend the sandbox destination with our sandbox cwd
        sandbox_dest = os.path.join(self._cwd, sandbox_dest.removeprefix('/'))

        with open(tar_filename, 'rb') as tar_file:
            # create dir
            self.filesystem.make_dir(sandbox_dest)
            # Upload the archive to /home/user (default destination that always exists)
            uploaded_path = self.filesystem.write(sandbox_dest, tar_file)

            # Extract the archive into the destination and delete the archive
            process = self.sandbox.commands.run(
                f'sudo tar -xf {uploaded_path} -C {sandbox_dest} && sudo rm {uploaded_path}'
            )
            if process.exit_code != 0:
                raise Exception(
                    f'Failed to extract {uploaded_path} to {sandbox_dest}: {process.stderr}'
                )

        # Delete the local archive
        os.remove(tar_filename)

    def close(self):
        self._stop()
