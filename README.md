# http_requests
HTTP sync / sync python library that works with both: requests and aiohttp, exploiting the best of each one

##### NOTE
If obj = aiohttp.ClientSession, then calling obj.loop is deprecated for reasons discussed in [this github issue](https://github.com/aio-libs/aiohttp/issues/3331), but this project use it for convenience

