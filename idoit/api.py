"""The API wrapper code."""

import typing

from logzero import logger
import requests


class Client:
    """The class working as the client.

    Use as a context manager to ensure sessions are closed.
    """

    def __init__(self, server_url: str, user: str, password: str, api_key: str):
        """The API client class."""
        while server_url.endswith("/"):
            server_url = server_url[:-1]
        self.server_url = server_url
        self.jsonrpc_url = "%s/src/jsonrpc.php" % server_url
        self.api_key = api_key
        self.session_id = None
        self.user = user
        self.password = password
        self._req_no = 0

    def _next_req_no(self):
        self._req_no += 1
        return self._req_no

    def login(self):
        logger.info("Logging into i-doit %s as %s", self.server_url, self.user)
        response = self._send_request(
            "idoit.login",
            extra_headers={"X-RPC-Auth-Username": self.user, "X-RPC-Auth-Password": self.password},
            is_login=True,
        )
        self.session_id = response["result"]["session-id"]
        logger.info("Login successful")

    def logout(self):
        logger.info("Logging out of i-doit %s", self.server_url)
        self._send_request("idoit.logout")
        self.session_id = None
        logger.info("Logout successful")
        pass

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, *args, **kwargs):
        self.logout()
        return False

    def _send_request(
        self,
        method: str,
        *,
        params: typing.Optional[typing.Dict[str, typing.Any]] = None,
        extra_headers: typing.Optional[typing.Dict[str, typing.Any]] = None,
        is_login: bool = False
    ) -> typing.Dict[str, typing.Any]:
        if not is_login and not self.session_id:
            raise Exception("Must login first!")

        headers = {**(extra_headers or {})}  # copy
        if self.session_id:
            headers["X-RPC-Auth-Session"] = self.session_id

        params = params or {}
        params["apikey"] = self.api_key

        payload = {"method": method, "params": params, "jsonrpc": "2.0", "id": self._next_req_no()}

        # You must initialize logging, otherwise you'll not see debug output.
        res = requests.post(self.jsonrpc_url, json=payload, headers=headers)
        res.raise_for_status()
        return res.json()

    def query_version(self):
        """Return server version."""
        return self._send_request("idoit.version")["result"]["version"]

    def query(self, command, params=None):
        return self._send_request(command, params=params or {})
