from typing import List, Optional, Set

from pydantic.dataclasses import dataclass


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
