import yaml
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from openapi_core import OpenAPI, validate_request
from openapi_core.validation.request.datatypes import RequestParameters
from openapi_core.protocols import Request as OpenAPIProtocolRequest
from openapi_core.exceptions import OpenAPIError
from contextlib import asynccontextmanager
from typing import Optional
import uvicorn

class StarletteOpenAPIRequest(OpenAPIProtocolRequest):
    def __init__(self, request: Request, body: Optional[bytes]):
        self._request = request
        self._body = body or b""
        self.parameters = RequestParameters(
            path=request.path_params,
            query=request.query_params,
            header=request.headers,
            cookie=request.cookies,
        )

    @property
    def host_url(self) -> str:
        return str(self._request.base_url).rstrip("/")

    @property
    def path(self) -> str:
        return self._request.url.path

    @property
    def full_url_pattern(self) -> str:
        return str(self._request.url)

    @property
    def method(self) -> str:
        return self._request.method.lower()

    @property
    def content_type(self) -> str:
        return self._request.headers.get("content-type", "").lower()

    @property
    def body(self) -> Optional[bytes]:
        return self._body


class Receiver:
    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self.spec_dict = self._load_spec()
        self.openapi = OpenAPI.from_dict(self.spec_dict)
        self.app = None

    def _load_spec(self):
        with open(self.spec_path, "r", encoding="utf‑8") as f:
            return yaml.safe_load(f)

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        print("Server starting…")
        yield
        print("Server stopping…")

    def _make_handler(self):
        async def handler(request: Request):
            raw = await request.body()
            oreq = StarletteOpenAPIRequest(request, raw)

            try:
                result = validate_request(oreq, spec=self.openapi.spec)
            except OpenAPIError as e:
                return JSONResponse(
                    status_code=400,
                    content={
                        "message": "Validation error",
                        "errors": [str(e.__cause__)],
                    },
                )

            return JSONResponse(
                status_code=200,
                content={"message": "Valid request"},
            )

        return handler

    def _initialize_paths(self):
        for path, methods in self.spec_dict.get("paths", {}).items():
            for method in methods:
                self.app.add_api_route(path, self._make_handler(), methods=[method.upper()])
                print(f"Registered endpoint: {method.upper()} {path}")

    def init_app(self) -> FastAPI:
        self.app = FastAPI(lifespan=self._lifespan)
        self._initialize_paths()
        return self.app

    def run(self) -> None:
        # First server in the YAML is the host 
        url = self.spec_dict.get("servers",[])[0]["url"]
        host = url.split("/")[2].split(":")[0]
        port = int(url.split("/")[2].split(":")[1])
        uvicorn.run(
            self.init_app(),
            host = host,
            port = port,
            reload = False
        )