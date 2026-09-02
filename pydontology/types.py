from datetime import date, datetime
from decimal import Decimal

# Maps Python types to the XSD datatype used for their RDF literal values.
# Keyed by the types themselves (not their names) so lookups are identity-based
# and cannot be fooled by user-defined classes that shadow a builtin name.
TYPE_MAP = {
    str: "xsd:string",
    int: "xsd:integer",
    Decimal: "xsd:decimal",
    float: "xsd:decimal",
    bool: "xsd:boolean",
    datetime: "xsd:dateTime",
    date: "xsd:date",
}

# Inverse of TYPE_MAP (where several types map to one XSD type, the last key wins)
INV_TYPE_MAP = {v: k for k, v in TYPE_MAP.items()}
TYPE_SET = set(TYPE_MAP.values())


def infer_xsd_type(value) -> str | None:
    # bool must be checked before int, since bool is a subclass of int
    if isinstance(value, bool):
        return TYPE_MAP[bool]
    if isinstance(value, int):
        return TYPE_MAP[int]
    if isinstance(value, Decimal):
        return TYPE_MAP[Decimal]
    if isinstance(value, float):
        return TYPE_MAP[float]
    if isinstance(value, str):
        return TYPE_MAP[str]
    if isinstance(value, datetime):
        return TYPE_MAP[datetime]
    if isinstance(value, date):
        return TYPE_MAP[date]
    return None
