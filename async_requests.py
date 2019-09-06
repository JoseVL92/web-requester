import asyncio
import logging
from collections import namedtuple
from concurrent.futures import TimeoutError

import aiohttp
import requests
from aiohttp.client_exceptions import ClientConnectionError, ClientResponseError
# from urllib.parse import urlencode
from urllib3.util import parse_url

"""
From experience, I know that aiohttp library causes problems behind an http proxy to accessing an https site.
It might even gets problems without proxy, but that is something that I couldn't say.
I use aiohttp for performance reasons, but always checking for common failures and applying the requests library api
for every async request if aiohttp does not make the job.

"""

# ------------------------------------------- DEFAULTS AND AUXILIAR VARIABLES ------------------------------------------

default_logger = logging.getLogger(__name__)
default_encoding = 'UTF-8'

# Some sites block bot by User-Agent information. To avoid that, we set a Mozilla v61.0 header
default_headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0"
}
default_tcp_connections_limit = 100
default_tcp_connections_limit_per_host = 30

# default final response type
AsyncResponse = namedtuple('AsyncResponse', ['type', 'http_response', 'text'])
# default http response information
HTTPInfo = namedtuple('HTTPInfo', ['url', 'status_code', 'headers', 'request_headers'])


def get_valid_loop():
    try:
        # If there is no loop in current thread, it raises RuntimeError
        loop_ = asyncio.get_event_loop()
        # If current loop is "for any reason" closed, raise RuntimeError to create a new one
        if loop_.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop_ = asyncio.new_event_loop()
        asyncio.set_event_loop(loop_)
    return loop_


def create_client(loop=None, timeout=None, connections_limit=None, connections_limit_per_host=None):
    loop = loop or get_valid_loop()

    session_timeout = aiohttp.ClientTimeout(total=timeout)
    conn = aiohttp.TCPConnector(
        limit=connections_limit or default_tcp_connections_limit,
        limit_per_host=connections_limit_per_host or default_tcp_connections_limit_per_host,
        loop=loop
    )
    # Setting trust_env=True is for default behavior: if proxy parameter is not specified per request,
    # look at the environment variables and use them if they exist, or do not use proxy at all
    return aiohttp.ClientSession(timeout=session_timeout, loop=loop, connector=conn, trust_env=True)


# default_client = create_client()


# ------------------------------------------- EXCEPTIONS ---------------------------------------------------------------


class XTimeOutError(Exception):
    """ The operation exceeded the given deadline """
    pass


class XHTTPError(Exception):
    """ Server response has a status code X where 400 < X < 599 """
    pass


class XConnectionError(Exception):
    """ Client cannot establish connection """
    pass


class XResponseError(Exception):
    """ Connection error during reading response  """
    pass


# ------------------------------------------- MAIN FUNCTIONS -----------------------------------------------------------


def multiple_async_requests(urloptions_list, common_options, loop=None):
    """
    Give the possibility of make several requests with common options for all, or specific options for each of them
    Options dictionary has shape (for example):
    {
        "method": "get",
        "data": b"Hola Mundo!!!",  # Only used with non-get requests
        "params": {"q": "frase a buscar"},  # Only used with get requests
        "json": [{ "si": "no" }],
        "proxy_cfg": {"http": "http://miproxy"},
        "headers": {"Content-Type": "application/pdf"}
        "client": <aiohttp.ClientSession>,
        "timeout": 15,
        "logger": <logging.logger>
    }
    Args:
        urloptions_list: tuple (url, opts), where 'url' is the url of the request, and opts is a dictionary with specific options
        common_options: dictionary with common options for every request, if that request does not specify its own options
        loop: Asyncio event loop

    Returns: A list of AsyncResponse named tuple, defined on top of this module
    >>> urls = ['http://www.granma.cu', ('https://actualidad.rt.com', {'json': {'num': 2}}), 'http://www.cubadebate.cu',
                ('https://www.filehorse.com/es', {'timeout': 12})]
    >>> response_list = multiple_async_requests(urls, {'method': 'get', 'timeout': '10'})

    """
    if not loop:
        if 'client' in common_options and hasattr(common_options['client'], loop):
            loop = common_options['client'].loop
        else:
            loop = get_valid_loop()
    response_list = loop.run_until_complete(execute_async(urloptions_list, common_options, loop))
    return response_list


async def execute_async(urloptions_list, common_options, loop=None):
    # if 'client' not in common_options:
    #     common_options['client'] = create_client(loop)
    aiohttp_client = common_options.pop('client', create_client(loop))
    tasks = []
    async with aiohttp_client as client:
        for url in urloptions_list:
            # If url is not a string, must be an iterable with shape ("http://url.example.com", {**options})
            if isinstance(url, (list, tuple)):
                if len(url) != 2 or not isinstance(url[1], dict):
                    raise AttributeError("At least one URL attribute has an incorrect format")
                url, opts = url
                common_options = {**common_options, **opts}
            tasks.append(async_request(url, close_client_at_end=False, client=client, **common_options))
        return await asyncio.gather(*tasks, loop=loop)


async def async_request(url, method='get', data=None, params=None, json=None, proxy_cfg=None, *,
                        headers=None, client=None, timeout=None, close_client_at_end=True, **kwargs):
    client = client or create_client()
    if 'logger' in kwargs:
        logger = kwargs.pop('logger')
        had_logger = True
    else:
        logger = default_logger
        had_logger = False

    if isinstance(timeout, str):
        if timeout.isdigit():
            timeout = int(timeout)
        else:
            timeout = None

    parsed = parse_url(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f"URL '{url}' has not a valid schema (must be http or https)")

    if isinstance(proxy_cfg, dict):
        single_proxy = proxy_cfg.get('http')
    else:
        single_proxy = proxy_cfg

    aiohttp_allowed = True
    # If there is a proxy_cfg and it is https, or if the site to visit is https, do not use aiohttp
    if (proxy_cfg is not None and not single_proxy) or parsed.scheme == 'https' or parse_url(
            single_proxy).scheme == 'https':
        aiohttp_allowed = False

    if aiohttp_allowed:
        try:
            text = await aiohttp_pure_request(url, method, data, params, json, single_proxy,
                                              headers=headers, client=client, timeout=timeout,
                                              close_client_at_end=False, **kwargs)
            return text
        except TimeoutError as err:
            logger.warning(f"aiohttp => TimeOut => {url}: {str(err)}")
            return
        except ClientResponseError as err:
            logger.warning(f"aiohttp => HTTPError status {err.status} => {url}: {str(err)}")
            return
        except ClientConnectionError as err:
            logger.warning(f"aiohttp => ConnectionError => {url}: {str(err)}")
            logger.warning("Intentando con cliente requests")

    loop = client.loop or get_valid_loop()

    # Pushing logger back to kwargs if it was present before
    if had_logger:
        kwargs['logger'] = logger
    text = await sync_to_async_request(url, method, data, params, json, proxy_cfg,
                                       headers=headers, loop=loop, timeout=timeout, **kwargs)
    if close_client_at_end:
        await client.close()
    return text


async def add_async_callback(future_fn, future_fn_args, future_fn_kwargs, callback, callback_args, callback_kwargs):
    if not callable(future_fn) or not callable(callback):
        raise AttributeError("future_fn and callback must be callable")

    if not isinstance(future_fn_args, (tuple, list)) or not isinstance(callback, (tuple, list)):
        raise AttributeError("future_fn_args and callable_args must be tuples or list")

    if not all([isinstance(x, dict) for x in (future_fn_kwargs, callback_kwargs)]):
        raise AttributeError("future_fn_kwargs and callback_kwargs must be dictionaries")

    resp = await future_fn(*future_fn_args, **future_fn_kwargs)
    return await callback(resp, *callback_args, **callback_kwargs)


# ------------------------------------------- AUX FUNCTIONS ------------------------------------------------------------


async def aiohttp_pure_request(url, method, data=None, params=None, json=None, proxy_cfg=None, *,
                               headers=None, client=None, timeout=None, close_client_at_end=True, **kwargs):
    """
    Execute an http request to a specified url

    """
    client = client or create_client()
    proxy_auth = {'proxy': proxy_cfg}  # if proxy_cfg else {'trust_env': True}
    raise_for_status = True
    headers = headers or default_headers

    # Inspired in requests.model.PreparedRequest.prepare_body()
    # if isinstance(data, dict):
    #     basestring = (bytes, str)
    #     result = []
    #     for k, vs in data.items():
    #         if isinstance(vs, basestring) or not hasattr(vs, '__iter__'):
    #             vs = [vs]
    #         for v in vs:
    #             if v is not None:
    #                 result.append(
    #                     (k.encode(default_encoding) if isinstance(k, str) else k,
    #                      v.encode(default_encoding) if isinstance(v, str) else v))
    #     data = urlencode(result, doseq=True)
    #     content_type = 'application/x-www-form-urlencoded'
    #
    #     # Add content-type if it wasn't explicitly provided.
    #     if 'content-type' not in headers:
    #         headers['Content-Type'] = content_type

    client_kwargs = {
        'data': data,
        'params': params,
        'json': json,
        'headers': {**default_headers, **headers},
        'timeout': timeout,
        'raise_for_status': raise_for_status
    }
    kwargs.update(client_kwargs)
    kwargs.update(proxy_auth)

    request_func = getattr(client, method, client.get)
    async with request_func(url, **kwargs) as resp:
        # if method == 'head':
        #     return dict(resp.headers)
        try:
            text = await resp.text()
        except UnicodeError:
            text = await resp.text(encoding=default_encoding, errors='replace')
        response_info = HTTPInfo(url=str(resp.url), status_code=resp.status, headers=dict(resp.headers),
                                 request_headers=dict(resp.request_info.headers))
    if close_client_at_end:
        await client.close()
    return AsyncResponse(type='aiohttp', http_response=response_info, text=text)


async def sync_to_async_request(url, method, data=None, params=None, json=None, proxy_cfg=None, *,
                                headers=None, loop=None, timeout=None, **kwargs):
    if proxy_cfg is not None and isinstance(proxy_cfg, str):
        proxy_cfg = {
            "http": proxy_cfg,
            "https": proxy_cfg
        }
    elif not isinstance(proxy_cfg, dict):
        proxy_cfg = None
    loop = loop or get_valid_loop()
    return await loop.run_in_executor(None, sync_request, url, method, data, params, json, proxy_cfg, headers,
                                      timeout, kwargs)


def sync_request(url, method, data=None, params=None, json=None, proxy_cfg=None, headers=None,
                 timeout=None, kwargs=dict()):
    # kwargs is a dictionary with additional options for requests.request function, and an optional logger object
    if 'logger' in kwargs:
        logger = kwargs.pop('logger')
    else:
        logger = default_logger

    if isinstance(proxy_cfg, str):
        proxy_cfg = {
            "http": proxy_cfg,
            "https": proxy_cfg
        }

    headers = headers or {}

    client_kwargs = {
        'data': data,
        'params': params,
        'json': json,
        'headers': {**default_headers, **headers},
        'timeout': timeout,
        'proxies': proxy_cfg
    }
    client_kwargs.update(kwargs)
    resp = requests.request(method, url, **client_kwargs)
    try:
        resp.raise_for_status()
        # if method == 'head':
        #     return resp.headers
        try:
            text = resp.text
        except UnicodeError:
            resp.encoding = default_encoding
            text = resp.text
        response_info = HTTPInfo(url=resp.url, status_code=resp.status_code, headers=resp.headers,
                                 request_headers=resp.request.headers)
        return AsyncResponse(type='requests', http_response=response_info, text=text)
    except requests.exceptions.Timeout as err:
        logger.warning(f"requests => TimeOut => {url}: {str(err)}")
        return
    except requests.exceptions.HTTPError as err:
        logger.warning(f"requests => HTTPError => {url}: {str(err)}")
        return
    except requests.exceptions.RequestException as err:
        logger.warning(f"requests => RequestError => {url}: {str(err)}")
        return
