

# web-requester  
## Easily and efficiently perform concurrent http requests with Python  
  
Make several requests with common options for all, or specific options for each of them.  
  
**aiohttp** library will be used only for default behavior (text retrieving, no callback) and if not explicitly disabled  via `{'allow_aio' = False}` in common_options. **requests** will be used otherwise
Options dictionary has shape (for example):  
```json
{  
    "method": "get",  
    "data": b"Hola Mundo!!!",  # Only used with non-get requests  
    "params": {"q": "frase a buscar"},  # Only used with get requests  
    "json": [{ "si": "no" }],  
    "proxy_cfg": {"http": "http://miproxy"},  # or "http://user:pass@host:port"
    "headers": {"Content-Type": "application/pdf"},  
    "allow_aio": True,  # if False, it ensures the use of 'requests' always and excludes aiohttp. Default: True  
    "aio_client": <aiohttp.ClientSession>,  # this is the only option that must be global, not specific for a single url  
    "timeout": 15,  
    "logger": <logging.logger>,  
    "callback": <function that receives a requests.Response as argument>.  
                If callback exists, the URL will be fetched using 'requests' only for standardization  
}
```

**Args:**

  
    urloptions_list: tuple (url, opts), where 'url' is the url of the request, and opts is a dictionary with specific options  
    common_options: dictionary with common options for every request, if that request does not specify its own options  
  
**Returns**: A list of responses defined by each specific callback or the general callback, or each response text by default

### Example of use
```python
urls = ['https://google.com',
		('https://actualidad.rt.com', {'json': {'num': 2}}),
		'http://www.cubadebate.cu',
		('https://www.filehorse.com/es', {'timeout': 12})]

response_list = request_all(urls, {'method': 'get', 'timeout': '10'})
 ```