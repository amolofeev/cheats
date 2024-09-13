import random
import time

from fastapi import FastAPI, Response

from starlette.requests import Request
from starlette.routing import Match, Mount

import aioprometheus


# settings.metrics.<metric_name>
class Metrics:
    http_request_latency = aioprometheus.Summary('http_request_latency', 'request_latency')


app = FastAPI()


@app.get('/metrics')
async def metrics():
    body, headers = aioprometheus.render(aioprometheus.REGISTRY, [])
    return Response(body, headers=headers)


@app.get('/')
def index():
    return Response(
        '',
        status_code=random.choice(
            [200] * 100 +
            [301, 302] +
            [400, 401, 403] * 20 +
            [500] * 10

        )
    )


@app.get('/{id:int}')
def detail(id: int) -> str:
    return 'OK'


@app.get('/{id:int}/edit')
def edit(id: int) -> str:
    return 'OK'


@app.middleware('http')
async def collect_prometheus_metrics(request, call_next):
    route_name = get_route_name(request)
    if route_name is None:
        route_name = request.scope['path']

    request_start = time.perf_counter_ns()
    try:
        response = await call_next(request)
        status_code = response.status_code
    except BaseException:
        status_code = 500

    request_end = time.perf_counter_ns()
    request_duration = (request_end - request_start) // 1000000
    labels = {
        'method': request.method,
        'url': route_name,
        'status': status_code
    }

    Metrics.http_request_latency.observe(
        labels,
        request_duration,
    )
    return response


# unified copy-paste from
# https://github.com/elastic/apm-agent-python/blob/7d09ed8959afb2f2bd2e011969d2a6d3fdd6cd28/elasticapm/contrib/starlette/__init__.py#L229
def get_route_name(request: Request) -> str:
    app = request.app
    scope = request.scope
    routes = app.routes
    route_name = _get_route_name(scope, routes)

    # Starlette magically redirects requests if the path matches a route name with a trailing slash
    # appended or removed. To not spam the transaction names list, we do the same here and put these
    # redirects all in the same "redirect trailing slashes" transaction name
    if not route_name and app.router.redirect_slashes and scope["path"] != "/":
        redirect_scope = dict(scope)
        if scope["path"].endswith("/"):
            redirect_scope["path"] = scope["path"][:-1]
            trim = True
        else:
            redirect_scope["path"] = scope["path"] + "/"
            trim = False

        route_name = _get_route_name(redirect_scope, routes)
        if route_name is not None:
            route_name = route_name + "/" if trim else route_name[:-1]
    return route_name


def _get_route_name(scope, routes, route_name=None):
    for route in routes:
        match, child_scope = route.matches(scope)
        if match == Match.FULL:
            route_name = route.path
            child_scope = {**scope, **child_scope}
            if isinstance(route, Mount) and route.routes:
                child_route_name = _get_route_name(child_scope, route.routes, route_name)
                if child_route_name is None:
                    route_name = None
                else:
                    route_name += child_route_name
            return route_name
        elif match == Match.PARTIAL and route_name is None:
            route_name = route.path
