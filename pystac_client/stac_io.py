from copy import deepcopy
import json
import logging
from typing import (
    Any,
    Dict,
    Optional,
    Union,
)
from urllib.parse import urlparse
from requests import Session

import requests
from pystac.link import Link
from pystac.stac_io import DefaultStacIO

from .exceptions import APIError

logger = logging.getLogger(__name__)


class StacApiIO(DefaultStacIO):
    def __init__(self, headers: Optional[Dict] = None):
        """Initialize class for API IO

        Args:
            headers : Optional dictionary of headers to include in all requests

        Returns:
            StacApiIO : StacApiIO instance
        """
        # TODO - this should super() to parent class
        self.session = Session()
        self.session.headers.update(headers or {})

    def read_text(self, source: Union[str, Link], *args: Any, parameters: Optional[dict] = {}, **kwargs: Any) -> str:
        """Overwrites the default method for reading text from a URL or file to allow :class:`urllib.request.Request`
        instances as input. This method also raises any :exc:`urllib.error.HTTPError` exceptions rather than catching
        them to allow us to handle different response status codes as needed."""
        if isinstance(source, str):
            href = source
            if bool(urlparse(href).scheme):
                return self.request(href, *args, parameters=parameters, **kwargs)
            else:
                with open(href) as f:
                    href_contents = f.read()
                return href_contents
        elif isinstance(source, Link):
            link = source.to_dict()
            breakpoint()
            href = link['href']
            # get headers and body from Link and add to request from simple stac resolver
            merge = bool(link.get('merge', False))

            # If the link object includes a "method" property, use that. If not fall back to 'GET'.
            method = link.get('method', 'GET')
            # If the link object includes a "headers" property, use that and respect the "merge" property.
            headers = link.get('headers', None)

            # If "POST" use the body object that and respect the "merge" property.
            link_body = link.get('body', {})
            if method == 'POST':
                parameters = {**parameters, **link_body} if merge else link_body
            else:
                # parameters are already in the link href
                parameters = {}
            return self.request(href, *args, method=method, headers=headers, parameters=parameters)

    def read_json(self, source: Union[str, Link], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Read a dict from the given source.

        See :func:`StacIO.read_text <pystac.StacIO.read_text>` for usage of
        str vs Link as a parameter.

        Args:
            source : The source from which to read.

        Returns:
            dict: A dict representation of the JSON contained in the file at the
            given source.
        """
        txt = self.read_text(source, *args, **kwargs)
        return self._json_loads(txt, source)

    def request(self, href: str, method: Optional[str] = 'GET', 
                headers: Optional[dict] = {},
                parameters: Optional[dict] = {}) -> str:
        if method == 'POST':
            request = requests.Request(method=method, url=href, headers=headers, json=parameters)
            logger.debug(
                f"POST {request.url}, Payload: {json.dumps(request.json)}, Headers: {self.session.headers}"
            )
        else:
            request = requests.Request(method=method, url=href,  headers=headers, params=parameters)
            logger.debug(
                f"GET {request.url}, Payload: {json.dumps(request.params)}, Headers: {self.session.headers}"
            )
        try:
            prepped = self.session.prepare_request(request)
            resp = self.session.send(prepped)
            if resp.status_code != 200:
                raise APIError(resp.text)
            return resp.content.decode("utf-8")
        except Exception as err:
            raise APIError(str(err))

    def write_text_to_href(self, href: str, *args: Any, **kwargs: Any) -> None:
        if bool(urlparse(href).scheme):
            raise APIError("Transactions not supported")
        else:
            return super().write_text_to_href(*args, **kwargs)
