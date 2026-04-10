from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8", env_prefix="PYDONTOLOGY_"
    )

    # Whether to show user warnings
    SHOW_WARNINGS: bool = True

    # Use class name as rdfs:label for ontology classes
    CLASS_NAME_AS_LABEL: bool = True

    # Use class docstrings as rdfs:comment for ontology classes
    DOCSTRING_AS_COMMENT: bool = True

    # Use field name as rdfs:label for ontology properties
    FIELD_NAME_AS_LABEL: bool = True

    # Use field descriptions as rdfs:comment for ontology properties
    # (Ignored if property is defined in multiple ontology classes)
    DESCRIPTION_AS_COMMENT: bool = True

    # Use origin class as rdfs:domain for ontology properties
    # (Ignored if property is defined in multiple ontology classes)
    ORIGIN_AS_DOMAIN: bool = True

    # Default parent (rdfs:subClassOf) for ontology classes inheriting from Entity
    SUBCLASS_OF_DEFAULT: str | None = "owl:Thing"

    # Set rdfs:subClassOf to parent class (Recommended)
    SUBCLASS_OF_PARENT: bool = True
