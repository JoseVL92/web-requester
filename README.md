

# web-requester

## Easily and efficiently perform concurrent http requests with Python  
  
Make several requests with common options for all, or specific options for each of them.  
  
**aiohttp** library will be used only for default behavior (text retrieving, no callback) and if not explicitly disabled  via `{'allow_aio' = False}` in common_options. **requests** will be used otherwise
Options dictionary has shape (for example):  
```json
{  
    "method": "get",  
    "data": b"Hola Mundo!!!",
    "params": {"q": "frase a buscar"},
    "json": [{ "si": "no" }],  
    "proxy_cfg": {"http": "http://miproxy"},
    "headers": {"Content-Type": "application/pdf"},  
    "allow_aio": True,
    "aio_client": some_aiohttp_client,
    "timeout": 15,  
    "logger": some_logger,  
    "callback": some_function
}
```

### Some points to notice:
- **method**: 'get' by default
- **data**: used only in non-get requests
- **params**: used only in 'get' requests
- **proxy**: could have also the "http://user:pass@host:port" format
- **allow_aio**: enables or disables the use of _aiohttp_. If False, it ensures the use of _requests_ always and excludes _aiohttp_. Default: True
- **aio_client**: _aiohttp.ClientSession_. It's the only option that, if present, must be global, not specific for a single url
- **logger**: a _logging.logger_ instance
- **callback**: _function_ that receives a _requests.Response_ as argument

> _If callback exists, the URL will be fetched using 'requests' only for standardization_

**Args:**
* **urloptions_list**: tuple (url, opts), where 'url' is the url of the request, and opts is a dictionary with specific options  
* **common_options**: dictionary with common options for every request, if that request does not specify its own options  
  
**Returns**: A list of responses defined by each specific callback or the general callback, or each response text by default

### How to use
```python
from web_requester import request_all

urls = ['https://google.com',
        ('https://actualidad.rt.com', {'json': {'num': 2}}),
	'http://www.cubadebate.cu',
	('https://www.filehorse.com/es', {'timeout': 12})]

response_list = request_all(urls, {'method': 'get', 'timeout': '10'})
 ```