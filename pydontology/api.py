import json
from inspect import get_annotations
from types import NoneType, UnionType
from typing import Any, List, Optional, Set, Union, get_args, get_origin

from pydantic.dataclasses import dataclass

from .models import BaseContext, Relation


class APIFactory:
    """Generate FastAPI apps from API annotations."""

    def __init__(self, pydontology: "Pydontology"):
        self._pydontology = pydontology

    def _normalize_api_base_path(self, base_path: str | None) -> str:
        if base_path is None:
            return ""
        base = base_path.strip()
        if base == "":
            return ""
        if not base.startswith("/"):
            base = f"/{base}"
        return base.rstrip("/")

    def _resolve_api_path(self, resource: str, path: str | None) -> str:
        if path is None:
            return f"/{resource}"
        if path.startswith("/"):
            return path
        return f"/{resource}/{path.lstrip('/')}"

    def _resolve_api_property_path(
        self, resource: str, property_name: str, path: str | None
    ) -> str:
        if path is None:
            return f"/{resource}/{property_name}"
        if path.startswith("/"):
            return path
        return f"/{resource}/{path.lstrip('/')}"

    def _collect_api_routes(self, metadata: List | None) -> List["APIAnnotation.ROUTE"]:
        if not metadata:
            return []
        return [meta for meta in metadata if isinstance(meta, APIAnnotation.ROUTE)]

    def _unwrap_optional(self, tp: Any) -> Any:
        origin = get_origin(tp)
        if origin in (Union, UnionType):
            args = [arg for arg in get_args(tp) if arg is not NoneType]
            if len(args) == 1:
                return args[0]
        return tp

    def _is_list_type(self, tp: Any) -> bool:
        origin = get_origin(tp)
        return origin in (list, List)

    def _sparql_prefix_lines(
        self, base: str, vocab: str, extra: dict[str, str] | None
    ) -> str:
        prefixes: dict[str, str] = {":": vocab}
        if extra:
            prefixes.update(extra)

        lines = []
        for prefix, iri in sorted(prefixes.items()):
            prefix_key = prefix if prefix.endswith(":") else f"{prefix}:"
            lines.append(f"PREFIX {prefix_key} <{iri}>")

        if base:
            lines.append(f"BASE <{base}>")
        return "\n".join(lines)

    def _sparql_iri_for_id(self, base: str, identifier: str) -> str:
        if identifier.startswith("http://") or identifier.startswith("https://"):
            return f"<{identifier}>"
        return f"<{base}{identifier}>"

    def _sparql_construct_class_collection(self, cls_name: str) -> str:
        return (
            f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ ?s a :{cls_name} . ?s ?p ?o . }}"
        )

    def _sparql_construct_class_detail(self, cls_name: str, subject_iri: str) -> str:
        return f"CONSTRUCT {{ {subject_iri} ?p ?o }} WHERE {{ {subject_iri} a :{cls_name} . {subject_iri} ?p ?o . }}"

    def _sparql_construct_property_collection(
        self, cls_name: str, property_name: str
    ) -> str:
        return (
            f"CONSTRUCT {{ ?s :{property_name} ?o }} WHERE {{ ?s a :{cls_name} . ?s :{property_name} ?o . }}"
        )

    def _sparql_execute_construct(
        self,
        sparql_wrapper,
        query: str,
    ):
        sparql_wrapper.setQuery(query)
        result = sparql_wrapper.query().convert()
        if isinstance(result, bytes):
            return result.decode("utf-8")
        return result

    def _jsonld_to_entities(
        self, jsonld_data: dict | list, cls, vocab_iri: str
    ) -> list:
        if isinstance(jsonld_data, dict):
            graph = jsonld_data.get("@graph")
            if graph is None:
                graph = [jsonld_data]
        else:
            graph = jsonld_data

        entities = []
        expected_full = f"{vocab_iri}{cls.__name__}"
        for node in graph:
            node_type = node.get("@type")
            if node_type is None:
                continue
            if isinstance(node_type, list):
                if cls.__name__ not in node_type and expected_full not in node_type:
                    continue
            else:
                if node_type not in (cls.__name__, expected_full):
                    continue
            entities.append(cls.model_validate(self._normalize_jsonld_node(node)))
        return entities

    def _normalize_jsonld_node(self, node: dict) -> dict:
        normalized = {}
        for key, value in node.items():
            if isinstance(value, dict) and "@value" in value:
                normalized[key] = value["@value"]
            elif isinstance(value, list):
                normalized_list = []
                for item in value:
                    if isinstance(item, dict) and "@value" in item:
                        normalized_list.append(item["@value"])
                    else:
                        normalized_list.append(item)
                normalized[key] = normalized_list
            else:
                normalized[key] = value
        return normalized

    def _rdflib_object_to_value(self, term):
        from rdflib import Literal, URIRef

        if isinstance(term, Literal):
            return term.toPython()
        if isinstance(term, URIRef):
            return Relation(id=str(term))
        return None

    def generate_api(
        self,
        base_path: str | None = None,
        sparql_endpoint: str | None = None,
        sparql_user: str | None = None,
        sparql_password: str | None = None,
        sparql_headers: dict[str, str] | None = None,
        sparql_default_graph: str | None = None,
        sparql_timeout: int | None = None,
        sparql_prefixes: dict[str, str] | None = None,
        sparql_wrapper=None,
    ):
        """Generate a FastAPI app from API annotations."""

        try:
            from fastapi import Body, FastAPI, HTTPException
        except Exception as exc:
            raise ImportError(
                "FastAPI is required for generate_api(). Install with pydontology[api]."
            ) from exc

        api = FastAPI()
        base_prefix = self._normalize_api_base_path(base_path)
        write_methods = {"POST", "PUT", "PATCH"}

        use_sparql = sparql_wrapper is not None or sparql_endpoint is not None
        base_context = BaseContext()
        base_iri = base_context.base
        vocab_iri = base_context.vocab
        jsonld_context = base_context.model_dump(by_alias=True, exclude_none=True)
        prefix_lines = self._sparql_prefix_lines(base_iri, vocab_iri, sparql_prefixes)

        if use_sparql and sparql_wrapper is None:
            try:
                from SPARQLWrapper import XML, SPARQLWrapper
            except Exception as exc:
                raise ImportError(
                    "SPARQLWrapper is required for SPARQL-backed handlers. Install with pydontology[sparql]."
                ) from exc

            sparql_wrapper = SPARQLWrapper(sparql_endpoint)
            sparql_wrapper.setReturnFormat(XML)
            if sparql_user is not None:
                sparql_wrapper.setCredentials(sparql_user, sparql_password or "")
            if sparql_default_graph is not None:
                sparql_wrapper.addDefaultGraph(sparql_default_graph)
            if sparql_timeout is not None:
                sparql_wrapper.setTimeout(sparql_timeout)
            if sparql_headers:
                for header, value in sparql_headers.items():
                    sparql_wrapper.addCustomHttpHeader(header, value)

        def make_handler_no_body():
            def handler():
                raise HTTPException(501, "Not implemented")

            return handler

        def make_handler_with_body(body_type):
            def handler(payload: body_type = Body(...)):
                raise HTTPException(501, "Not implemented")

            return handler

        for class_name, class_info in self._pydontology._cls_db.items():
            cls = class_info["class"]
            resource = class_name.lower()

            for route in self._collect_api_routes(class_info.get("metadata")):
                path = self._resolve_api_path(resource, route.path)
                if base_prefix:
                    path = f"{base_prefix}{path}"

                tags = route.tags if route.tags is not None else [class_name]
                request_model = cls if route.method in write_methods else None
                response_model = cls

                if route.method == "GET" and "{id}" not in path:
                    response_model = List[cls]
                if route.method == "DELETE":
                    response_model = None

                handler = None
                if use_sparql and route.method == "GET":

                    def handler(
                        id: str | None = None,
                        cls_name=class_name,
                        cls_type=cls,
                        route_path=path,
                    ):
                        from rdflib import Graph

                        subject_iri = None
                        query = None
                        if "{id}" in route_path:
                            if id is None:
                                raise HTTPException(422, "Missing id parameter")
                            subject_iri = self._sparql_iri_for_id(base_iri, id)
                            query = self._sparql_construct_class_detail(
                                cls_name, subject_iri
                            )
                        else:
                            query = self._sparql_construct_class_collection(cls_name)

                        full_query = f"{prefix_lines}\n{query}"
                        data = self._sparql_execute_construct(
                            sparql_wrapper, full_query
                        )

                        graph = Graph()
                        graph.parse(data=data, format="xml")
                        jsonld_text = graph.serialize(
                            format="json-ld",
                            auto_compact=True,
                            context=jsonld_context,
                        )
                        if isinstance(jsonld_text, bytes):
                            jsonld_text = jsonld_text.decode("utf-8")
                        jsonld = json.loads(jsonld_text)
                        entities = self._jsonld_to_entities(jsonld, cls_type, vocab_iri)

                        if "{id}" in route_path:
                            return entities[0] if entities else None
                        return entities

                if handler is None:
                    handler = (
                        make_handler_with_body(request_model)
                        if request_model is not None
                        else make_handler_no_body()
                    )

                api.api_route(
                    path,
                    methods=[route.method],
                    response_model=response_model,
                    tags=tags,
                )(handler)

            for field_name in get_annotations(cls).keys():
                field_info = cls.model_fields[field_name]
                field_routes = self._collect_api_routes(field_info.metadata)
                if not field_routes:
                    continue

                field_type = field_info.annotation or Any
                for route in field_routes:
                    path = self._resolve_api_property_path(
                        resource, field_name, route.path
                    )
                    if base_prefix:
                        path = f"{base_prefix}{path}"

                    tags = route.tags if route.tags is not None else [class_name]
                    request_model = (
                        field_type if route.method in write_methods else None
                    )
                    response_model = field_type

                    if route.method == "DELETE":
                        response_model = None

                    handler = None
                    if use_sparql and route.method == "GET":

                        def handler(
                            cls_name=class_name,
                            property_name=field_name,
                            field_tp=field_type,
                        ):
                            from rdflib import Graph

                            query = self._sparql_construct_property_collection(
                                cls_name, property_name
                            )
                            full_query = f"{prefix_lines}\n{query}"
                            data = self._sparql_execute_construct(
                                sparql_wrapper, full_query
                            )

                            from rdflib import URIRef

                            graph = Graph()
                            graph.parse(data=data, format="xml")
                            predicate = URIRef(f"{vocab_iri}{property_name}")
                            values = []
                            for _, _, obj in graph.triples((None, predicate, None)):
                                value = self._rdflib_object_to_value(obj)
                                if value is not None:
                                    values.append(value)

                            normalized_type = self._unwrap_optional(field_tp)
                            if self._is_list_type(normalized_type):
                                return values
                            return values[0] if values else None

                    if handler is None:
                        handler = (
                            make_handler_with_body(request_model)
                            if request_model is not None
                            else make_handler_no_body()
                        )

                    api.api_route(
                        path,
                        methods=[route.method],
                        response_model=response_model,
                        tags=tags,
                    )(handler)

        return api

class APIAnnotation:
    """Provides methods for setting API route annotations."""

    _allowed_methods: Set[str] = {"GET", "POST", "PUT", "PATCH", "DELETE"}

    @dataclass(frozen=True)
    class ROUTE:
        """Dataclass that holds API route metadata for a class or property."""

        method: str
        path: Optional[str] = None
        tags: Optional[List[str]] = None

    @staticmethod
    def route(
        method: str, path: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> "APIAnnotation.ROUTE":
        """API route annotation."""

        method_upper = method.upper()
        if method_upper not in APIAnnotation._allowed_methods:
            raise ValueError(
                "Method must be one of: "
                + ", ".join(sorted(APIAnnotation._allowed_methods))
            )

        if path is not None:
            if not isinstance(path, str) or path.strip() == "":
                raise ValueError("Path must be a non-empty string or None")

        return APIAnnotation.ROUTE(method=method_upper, path=path, tags=tags)
