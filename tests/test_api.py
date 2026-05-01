from typing import Annotated, List, get_args, get_origin

import pytest
from pydantic import Field

from pydontology import APIAnnotation as API
from pydontology import Entity, Pydontology, Relation


@pytest.fixture
def ApiModel():
    class Widget(Entity):
        name: Annotated[str, API.route("GET"), API.route("POST")] = Field(
            description="Widget name"
        )
        owner: Annotated[Relation, API.route("GET")] = Field(
            description="Owner IRI"
        )

    onto = Pydontology(
        ontology=Annotated[
            Widget,
            API.route("GET"),
            API.route("POST"),
            API.route("GET", path="{id}"),
        ]
    )
    return onto


def test_generate_api_routes(ApiModel):
    pytest.importorskip("fastapi")
    from fastapi.routing import APIRoute

    api = ApiModel.generate_api()
    routes = [route for route in api.routes if isinstance(route, APIRoute)]

    def find_route(path, method):
        for route in routes:
            if route.path == path and method in route.methods:
                return route
        return None

    list_route = find_route("/widget", "GET")
    assert list_route is not None
    assert get_origin(list_route.response_model) in (list, List)
    assert get_args(list_route.response_model)[0].__name__ == "Widget"

    detail_route = find_route("/widget/{id}", "GET")
    assert detail_route is not None
    assert detail_route.response_model.__name__ == "Widget"

    create_route = find_route("/widget", "POST")
    assert create_route is not None
    assert create_route.body_field.field_info.annotation.__name__ == "Widget"

    name_get_route = find_route("/widget/name", "GET")
    assert name_get_route is not None
    assert name_get_route.response_model is str

    name_post_route = find_route("/widget/name", "POST")
    assert name_post_route is not None
    assert name_post_route.body_field.field_info.annotation is str

    owner_get_route = find_route("/widget/owner", "GET")
    assert owner_get_route is not None
    assert owner_get_route.response_model.__name__ == "Relation"
