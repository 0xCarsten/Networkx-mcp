from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, Field


class ErrorModel(BaseModel):
    error: str


class GraphPathModel(BaseModel):
    path: Annotated[str, Field(description="Path/URL of graph_data")]
    alias: Annotated[str, Field(description="Alias for cached graph.")] = "default"


class GraphCacheModel(BaseModel):
    status: Literal["loaded", "error"]
    alias: Annotated[str, Field(description="alias of the cached graph.")]
    uri: Annotated[
        str,
        Field(description="uri of the cached graph. To be referenced with graph://<alias>"),
    ]


class GraphDataModel(BaseModel):
    directed: bool = True
    multigraph: bool = True
    graph: dict = {}
    nodes: list[dict]
    links: list[dict] = Field(validation_alias=AliasChoices("links", "edges"))  # alias for edges


class AttributeBaseModel(BaseModel):
    attribute: Annotated[str, Field(description="Attribute on node or edge of the graph")]
    graph_data: dict | None = None
    uri: Annotated[str, Field(description="URI of cached graph like 'graph://default'")]


class AttributeValueFilter(AttributeBaseModel):
    """Request model for node attribute filtering."""

    # NOTE: LLM clients often serialize numbers as strings (e.g. "6.0").
    # Pydantic v2's default union mode ('smart') will prefer `str` over `float`
    # for string inputs, which then breaks numeric comparisons.
    value: float | str  # Annotated[float | str, Field(description="Value to compare against")]
    operator: Annotated[
        Literal["==", "!=", "<", "<=", ">", ">="],
        Field(description="Comparison operator"),
    ]
    # value_type: Annotated[Literal["str", "int", "float"], Field(description="Type of the value field")] = "str"
    _numeric_re = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
    _int_like_re = re.compile(r"^[+-]?\d+$")


class AttributeMatchRequest(AttributeBaseModel):
    """Request model for attribute matching."""


class ResultsModel(BaseModel):
    matches: Annotated[list, Field(description="List of matching node IDs or edge tuples")]


class ResultsAttributesModel(BaseModel):
    matching_attributes: Annotated[list, Field(description="List of matching attributes")] = []
