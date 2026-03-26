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
    allowed = [
        # Core numeric types
        "xsd:integer", "xsd:decimal", "xsd:float", "xsd:double",
        # String types 
        "xsd:string", 
        # Boolean
        "xsd:boolean",
        # Date and time types
        "xsd:date", "xsd:time", "xsd:dateTime", "xsd:duration",
        # Other common types
        "xsd:anyURI", "xsd:hexBinary", "xsd:base64Binary"
    ]

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

    SPARQL regex patterns follow the XQuery 1.0 and XPath 2.0 syntax.
    This is a basic validation to check for syntax errors.

    Args:
        input (str): String to validate as SPARQL regex pattern

    Returns:
        str: Validated input

    Raises:
        ValueError: If the pattern is invalid
    """
    # Basic check for balanced parentheses and brackets
    open_chars = {'(': ')', '[': ']', '{': '}'}
    stack = []
    
    try:
        for char in input:
            if char in open_chars:
                stack.append(char)
            elif char in open_chars.values():
                if not stack or char != open_chars[stack.pop()]:
                    raise ValueError(f"Unbalanced delimiter: {char}")
        
        if stack:
            raise ValueError(f"Unbalanced delimiters: {stack}")
            
        # This is a simplified check - for a complete validation,
        # consider using a regex library to actually compile the pattern
        
        return input
    except Exception as e:
        raise ValueError(f"Invalid regex pattern: {e}")
