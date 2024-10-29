from aiohttp.web import Request


def is_browser_request(req: Request) -> bool:
    return req.headers["User-Agent"].startswith("Mozilla")
