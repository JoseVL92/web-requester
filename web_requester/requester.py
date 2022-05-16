import aiohttp
import asyncio
import logging
import requests

from aiohttp.client_exceptions import ClientConnectionError, ClientResponseError
from collections import namedtuple
from concurrent.futures import TimeoutError
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

# Some sites block bot by User-Agent information. To avoid that, we set a Chrome v101 header
default_headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36"
}
default_tcp_connections_limit = 100
default_tcp_connections_limit_per_host = 30

# aux named tuple for using in default callback
AsyncResponse = namedtuple('AsyncResponse', ['type', 'response'])


# default http response information
# HTTPInfo = namedtuple('HTTPInfo', ['url', 'status_code', 'response_headers', 'request_headers'])


# in future Python versions, this will be an alias for asyncio.get_running_loop
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


def create_aioclient(loop=None, timeout=None, connections_limit=None, connections_limit_per_host=None):
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


# default_client = create_aioclient()


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


# ------------------------------------------- MAIN ENTRY POINT ---------------------------------------------------------


def request_all(urloptions_list, common_options, loop=None):
    """
    Give the possibility of make several requests with common options for all, or specific options for each of them.
    aiohttp library will be used only for default behavior (text retrieving, no callback) and if not explicitly disabled
    via {'allow_aio' = False} in common_options
    Options dictionary has shape (for example):
    {
        "method": "get",
        "data": b"Hola Mundo!!!",  # Only used with non-get requests
        "params": {"q": "frase a buscar"},  # Only used with get requests
        "json": [{ "si": "no" }],
        "proxy_cfg": {"http": "http://miproxy"},
        "headers": {"Content-Type": "application/pdf"},
        "allow_aio": True,  # if False, it ensures the use of 'requests' always and excludes aiohttp. Default: True
        "aio_client": <aiohttp.ClientSession>,  # this is the only option that must be global, not specific for a single url
        "timeout": 15,
        "logger": <logging.logger>,
        "callback": <function that receives a web_requester.requester.AsyncResponse as argument>.
                    If callback exists, the URL will be fetched using 'requests' only for standardization
    }
    Args:
        urloptions_list: tuple (url, opts), where 'url' is the url of the request, and opts is a dictionary with specific options
        common_options: dictionary with common options for every request, if that request does not specify its own options
        loop: Asyncio event loop

    Returns: A list of AsyncResponse named tuple, defined on top of this module
    >>> urls = ['https://google.com', ('https://actualidad.rt.com', {'json': {'num': 2}}), 'http://www.cubadebate.cu',
                ('https://www.filehorse.com/es', {'timeout': 12})]
    >>> response_list = request_all(urls, {'method': 'get', 'timeout': '10'})

    """
    if not loop:
        # ask for forgiveness and not permission
        try:
            loop = common_options['aio_client'].loop
        except:
            loop = get_valid_loop()
    response_list = loop.run_until_complete(request_all_async(urloptions_list, common_options, loop))
    return response_list


# ------------------------------------------- TASK LINKERS -------------------------------------------------------------


async def chain_callback(future_fn, future_fn_args, future_fn_kwargs, callback, callback_args, callback_kwargs):
    if not callable(future_fn) or not callable(callback):
        raise AttributeError("future_fn and callback must be callable")

    if not isinstance(future_fn_args, (tuple, list)) or not isinstance(callback_args, (tuple, list)):
        raise AttributeError("future_fn_args and callable_args must be tuples or list")

    if not all([isinstance(x, dict) for x in (future_fn_kwargs, callback_kwargs)]):
        raise AttributeError("future_fn_kwargs and callback_kwargs must be dictionaries")

    resp = await future_fn(*future_fn_args, **future_fn_kwargs)
    return await callback(resp, *callback_args, **callback_kwargs)


async def request_all_async(urloptions_list, common_options, loop=None):
    """
    Same that request_all, but to be used directly with 'async' directive
    """

    async def aux(aux_aio_client=None):
        for url in urloptions_list:
            # If url is not a string, must be an iterable with shape ("http://url.example.com", {**options})
            comm_opts = dict(common_options)
            if isinstance(url, (list, tuple)):
                if len(url) != 2 or not isinstance(url[1], dict):
                    raise AttributeError("At least one URL attribute has an incorrect format")
                url, opts = url
                comm_opts = {**comm_opts, **opts}
                comm_opts.pop('aio_client', None)
                comm_opts.pop('close_aio_at_end', None)
            tasks.append(async_request(url, aio_client=aux_aio_client, close_aio_at_end=False, **comm_opts))
        return await asyncio.gather(*tasks, loop=loop)

    tasks = []
    if common_options.get('allow_aio', True) and not callable(common_options.get('callback')):
        # aio_client = common_options.setdefault('aio_client', create_aioclient(loop))
        aio_client = common_options.pop('aio_client', create_aioclient(loop))
        # aio_client = common_options.pop('aio_client', create_aioclient(loop))
        async with aio_client as client:
            return await aux(client)

    logger = common_options.get('logger', default_logger)
    logger.info("Using 'requests' library for every request")
    return await aux()


# ------------------------------------------- SYNC/ASYNC DEFINITORS ----------------------------------------------------


async def async_request(url, method='get', data=None, params=None, json=None, proxy_cfg=None, *, headers=None,
                        timeout=None, callback=None, allow_aio=True, aio_client=None, close_aio_at_end=True, **kwargs):
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

    # If there is a proxy_cfg and it is https, or if the site to visit is https, do not use aiohttp
    if (proxy_cfg is not None and not single_proxy) or parsed.scheme == 'https' or parse_url(
            single_proxy).scheme == 'https':
        allow_aio = False

    # only use callbacks with 'requests' responses
    if callback:
        allow_aio = False

    if allow_aio:
        aio_client = aio_client or create_aioclient()
        try:
            return await aiohttp_pure_request(url, method, data, params, json, single_proxy,
                                              headers=headers, client=aio_client, timeout=timeout,
                                              close_client_at_end=close_aio_at_end, **kwargs)
        except ClientConnectionError:
            logger.warning("Retrying with 'requests' instead")

    loop = get_valid_loop()

    # Pushing logger back to kwargs if it was present before
    if had_logger:
        kwargs['logger'] = logger
    return await sync_to_async_request(url, method, data, params, json, proxy_cfg, headers=headers,
                                       loop=loop, timeout=timeout, callback=callback, **kwargs)
    # if close_client_at_end:
    #     await client.close()
    # return text


async def sync_to_async_request(url, method, data=None, params=None, json=None, proxy_cfg=None, *,
                                headers=None, loop=None, timeout=None, callback=None, **kwargs):
    if proxy_cfg is not None and isinstance(proxy_cfg, str):
        proxy_cfg = {
            "http": proxy_cfg,
            "https": proxy_cfg
        }
    elif not isinstance(proxy_cfg, dict):
        proxy_cfg = None
    loop = loop or get_valid_loop()
    return await loop.run_in_executor(None, sync_request, url, method, data, params, json, proxy_cfg, headers,
                                      timeout, callback, kwargs)


# ------------------------------------------- DEFAULT RESPONSE CALLBACKS -----------------------------------------------


def get_response_text(response):
    try:
        text = response.text
    except UnicodeError:
        response.encoding = default_encoding
        text = response.text
    return text


# ------------------------------------------- REQUESTERS ---------------------------------------------------------------


async def aiohttp_pure_request(url, method, data=None, params=None, json=None, proxy_cfg=None, *, headers=None,
                               client=None, timeout=None, close_client_at_end=True, **kwargs):
    client = client or create_aioclient()
    proxy_auth = {'proxy': proxy_cfg}  # if proxy_cfg else {'trust_env': True}
    raise_for_status = True
    headers = headers or default_headers

    if 'logger' in kwargs:
        logger = kwargs.pop('logger')
    else:
        logger = default_logger

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
    try:
        async with request_func(url, **kwargs) as resp:
            try:
                text = await resp.text()
            except UnicodeError:
                text = await resp.text(encoding=default_encoding, errors='replace')
            if close_client_at_end:
                await client.close()
            return text
    except TimeoutError as err:
        logger.warning(f"aiohttp => TimeOut => {url}: {str(err)}")
        return
    except ClientResponseError as err:
        logger.warning(f"aiohttp => HTTPError status {err.status} => {url}: {str(err)}")
        return
    except ClientConnectionError as err:
        logger.warning(f"aiohttp => ConnectionError => {url}: {str(err)}")
        raise err


def sync_request(url, method, data=None, params=None, json=None, proxy_cfg=None, headers=None,
                 timeout=None, callback=None, kwargs=None):
    # kwargs is a dictionary with additional options for requests.request function, and an optional logger object
    kwargs = kwargs or dict()
    callback = callback or get_response_text

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
        return callback(resp)
    except requests.exceptions.Timeout as err:
        logger.warning(f"requests => TimeOut => '{url}': {str(err)}")
        return
    except requests.exceptions.HTTPError as err:
        logger.warning(f"requests => HTTPError => '{url}': {str(err)}")
        return
    except requests.exceptions.RequestException as err:
        logger.warning(f"requests => RequestError => '{url}': {str(err)}")
        return
