import aioprometheus

from asgiref.typing import ASGIApplication, ASGIReceiveCallable, ASGISendCallable, Scope


# settings.metrics.<metric_name>
class Metrics:
    http_requests_count = aioprometheus.Counter('http_request_latency', 'request_latency')


# url path -> url.regex
def path_to_route_name(app: ASGIApplication, path: str) -> str:
    app, handler, path, params = app.asgi_router.handle_routing(path, "OPTIONS")
    return next(iter(handler.paths))


class PrometheusMiddleware:
    def __init__(self, app: "ASGIApplication", **options) -> None:
        self._app = app

    async def __call__(self, scope: "Scope", receive: "ASGIReceiveCallable", send: "ASGISendCallable") -> None:
        labels = {
            "type": scope["type"],
        }
        if scope["type"] == "http":
            labels.update(
                {
                    "path": path_to_route_name(scope["app"], scope["path"]),
                    "method": scope["method"],
                },
            )
        Metrics.http_requests_count.inc(labels)

        await self._app(scope, receive, send)


# Application
from litestar import Litestar, get, Controller, Response


class TestHandler(Controller):
    path = "/"

    @get(path="/metrics")
    async def metrics(self) -> Response:
        body, headers = aioprometheus.render(aioprometheus.REGISTRY, [])
        return Response(body, headers=headers, status_code=200)

    @get(path='/')
    async def a(self) -> str:
        return 'OK'

    @get(path='/{id:int}')
    async def b(self) -> str:
        return 'OK'

    @get(path='/{id:int}/edit')
    async def c(self) -> str:
        return 'OK'


app = Litestar(
    route_handlers=[
        TestHandler,
    ],
    middleware=[
        # TODO: middlewares can"t handle 404, 405
        PrometheusMiddleware,
    ],
)
