import docker
import httpx
import tenacity

from openhands.runtime.utils.request import RequestHTTPError


def _is_retryablewait_until_alive_error(exception: Exception | BaseException) -> bool:
    if isinstance(exception, tenacity.RetryError):
        cause = exception.last_attempt.exception()
        if cause is None:
            return False
        return _is_retryablewait_until_alive_error(cause)

    return isinstance(
        exception,
        (
            ConnectionError,
            httpx.ConnectTimeout,
            httpx.NetworkError,
            httpx.RemoteProtocolError,
            httpx.HTTPStatusError,
            httpx.ReadTimeout,
            RequestHTTPError,
        ),
    )


def stop_all_containers(prefix: str) -> None:
    docker_client = docker.from_env()
    try:
        containers = docker_client.containers.list(all=True)
        for container in containers:
            try:
                if container.name.startswith(prefix):
                    container.stop()
            except docker.errors.APIError:
                pass
            except docker.errors.NotFound:
                pass
    except docker.errors.NotFound:  # yes, this can happen!
        pass
    finally:
        docker_client.close()
