import string


def val_no_whitespace(input: str):
    """Custom field validator, that checks that string contains no whitespace

    Args:
        input (str): String to validate

    Returns:
        str: Validated input

    Raises:
        ValueError
    """
    if any(char in string.whitespace for char in input):
        raise ValueError("String cannot contain whitespace")
    return input


def val_node_kind(input: str):
    """Custom field validator, that checks that string is one of the allowed literals for sh:nodeKind

    Args:
        input (str): String to validate

    Returns:
        str: Validated input

    Raises:
        ValueError
    """
    allowed = [
        "sh:BlankNode",
        "sh:IRI",
        "sh:Literal",
        "sh:BlankNodeOrIRI",
        "sh:BlankNodeOrLiteral",
        "sh:IRIOrLiteral",
    ]

    if input not in allowed:
        raise ValueError(f"String must be one of {allowed}")
    return input


def val_datatype(input: str):
    """Custom field validator, that checks that string is one of the allowed literals for sh:datatype

    Args:
        input (str): String to validate

    Returns:
        str: Validated input

    Raises:
        ValueError
    """
    allowed = ["xsd:integer", "xsd:deciaml", "xsd:string", "xsd:boolean"]

    if input not in allowed:
        raise ValueError(f"String must be one of {allowed}")
    return input


def val_positive_int(input: int):
    """Custom field validator, that checks that integer is positive

    Args:
        input (int): Integer to validate

    Returns:
        int: Validated input

    Raises:
        ValueError
    """
    if input <= 0:
        raise ValueError("Integer must be positive")
    return input


def val_non_negative_int(input: int):
    """Custom field validator, that checks that integer is non-negative

    Args:
        input (int): Integer to validate

    Returns:
        int: Validated input

    Raises:
        ValueError
    """
    if input < 0:
        raise ValueError("Integer must be non-negative")
    return input


def val_regex_pattern(input: str):
    """Custom field validator, that checks that string is a valid SPARQL regex pattern

    Note: Currently returns input pattern!
    TODO: Implement validator for SPARQL regex pattern

    Args:
        input (str): String to validate as SPARQL regex pattern

    Returns:
        str: Validated input

    Raises:
        ValueError
    """
    return input
