# usage:
# s = SmartSession()
# s.get("https://blahblah.com")

import http
from requests.sessions import Session
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

# Enable debugging which prints requests and response headers
http.client.HTTPConnection.debuglevel = 1


class SmartSession(Session):
    # The total number of retry attempts to make.
    # If the number of failed requests or redirects exceeds this number,
    # the client will throw the urllib3.exceptions.MaxRetryError exception.
    NUM_RETRIES = 5

    # It allows you to change how long the processes will sleep between failed requests.
    # The algorithm is as follows:
    # {backoff factor} * (2 ** ({number of total retries} - 1))
    # For example, if the backoff factor is set to 1 second, the successive sleeps will be:
    # 0.5, 1, 2, 4, 8.
    BACKOFF_FACTOR = 0.3

    # The HTTP response codes to retry on.
    # You likely want to retry on the common server errors (500, 502, 503, 504)
    # because servers and reverse proxies don't always adhere to the HTTP spec.
    # Always retry on 429 rate limit exceeded because the urllib library should
    # by default incrementally backoff on failed requests.
    STATUS_FORCELIST = [
        429,
        500,
        502,
        503,
        504,
    ]

    # The HTTP methods to retry on.
    # By default this includes all HTTP methods except POST because
    # POST can result in a new insert.
    # But most API's don't return an error code and perform an insert in the same call.
    # And if they do, you should probably issue a bug report.
    METHOD_WHITELIST = [
        "HEAD",
        "GET",
        "PUT",
        "POST",
        "DELETE",
        "OPTIONS",
        "TRACE",
    ]

    # Faking to be Chrome browser
    USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36"

    class TimeoutHTTPAdapter(HTTPAdapter):
        # Timeout in seconds
        TIMEOUT = 5

        def __init__(self, *args, **kwargs):
            self.timeout = self.TIMEOUT
            if "timeout" in kwargs:
                self.timeout = kwargs["timeout"]
                del kwargs["timeout"]
            super().__init__(*args, **kwargs)

        def send(self, request, **kwargs):
            timeout = kwargs.get("timeout")
            if timeout is None:
                kwargs["timeout"] = self.timeout
            return super().send(request, **kwargs)

    def __init__(
        self,
        num_retries=None,
        backoff_factor=None,
        status_forcelist=None,
        method_whitelist=None,
        timeout=None,
        user_agent=None,
    ):
        self.num_retries = num_retries or self.NUM_RETRIES
        self.backoff_factor = backoff_factor or self.BACKOFF_FACTOR
        self.status_forcelist = status_forcelist or self.STATUS_FORCELIST
        self.method_whitelist = method_whitelist or self.METHOD_WHITELIST
        self.timeout = timeout
        self.user_agent = user_agent or self.USER_AGENT
        self.adapter = None

        super().__init__()

        # should be called after super().__init__() to prevent it from overwriting changes
        self.init_all()

    def init_all(self):
        retry = Retry(
            total=self.num_retries,
            read=self.num_retries,
            connect=self.num_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=self.status_forcelist,
            method_whitelist=self.method_whitelist,
        )
        self.adapter = self.TimeoutHTTPAdapter(
            timeout=self.timeout, max_retries=retry
        )
        self.mount("http://", self.adapter)
        self.mount("https://", self.adapter)
        self.headers.update({"User-Agent": self.user_agent})
