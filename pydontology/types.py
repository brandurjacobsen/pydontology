from datetime import date, datetime
from decimal import Decimal

TYPE_MAP = {
    "str": "xsd:string",
    "int": "xsd:integer",
    "Decimal": "xsd:decimal",
    "float": "xsd:decimal",
    "bool": "xsd:boolean",
    "datetime": "xsd:dateTime",
    "date": "xsd:date",
}

# Order TYPE_MAP such that last seen (multiple) value is desired key
INV_TYPE_MAP = {v: k for k, v in TYPE_MAP.items()}
TYPE_SET = set(TYPE_MAP.values())


def infer_xsd_type(value) -> str | None:
    if isinstance(value, bool):
        return TYPE_MAP["bool"]
    if isinstance(value, int):
        return TYPE_MAP["int"]
    if isinstance(value, Decimal):
        return TYPE_MAP["Decimal"]
    if isinstance(value, float):
        return TYPE_MAP["float"]
    if isinstance(value, str):
        return TYPE_MAP["str"]
    if isinstance(value, datetime):
        return TYPE_MAP["datetime"]
    if isinstance(value, date):
        return TYPE_MAP["date"]
    return None
