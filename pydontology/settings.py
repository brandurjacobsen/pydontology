from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8", env_prefix="PYDONTOLOGY_"
    )

    # Concatenate Pydantic field descriptions for RDF properties
    # defined multiple times, using '|' as separator.
    # See DESCRIPTION_AS_COMMENT below.
    CONCAT_COMMENTS: bool = True
    # Use Pydantic class docstrings as rdfs:comment (for rdfs:Class)
    # in the ontology graph
    DOCSTRING_AS_COMMENT: bool = True
    # Use Pydantic field descriptions as rdfs:comment (for owl:ObjectPropert
    # or owl:DatatypeProperty) in the ontology graph.
    DESCRIPTION_AS_COMMENT: bool = True
