from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8", env_prefix="PYDONTOLOGY_"
    )

    # Use class name as rdfs:label for ontology classes
    CLASS_NAME_AS_LABEL: bool = True

    # Use field name as rdfs:label
    FIELD_NAME_AS_LABEL: bool = True

    # Use class docstrings as rdfs:comment for ontology classes
    DOCSTRING_AS_COMMENT: bool = True

    # Use field descriptions as rdfs:comment for ontology properties
    DESCRIPTION_AS_COMMENT: bool = True

    # Use origin class as rdfs:domain for ontology properties
    ORIGIN_AS_DOMAIN: bool = True

    # Create SHACL sh:minLength (of 1) constraint for required fields
    MINLENGTH_FOR_REQUIRED: bool = True

    # Default parent (rdfs:subClassOf) for ontology classes inheriting from Entity
    DEFAULT_SUBCLASS_OF: str | None = "owl:Thing"
