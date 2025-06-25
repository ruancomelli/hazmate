"""This is a workaround to make frozendict work with Pydantic.

Copied from https://github.com/pydantic/pydantic/discussions/8721
"""

import typing as typ

import pydantic as pyd
from frozendict import frozendict as _frozendict
from pydantic_core import core_schema as pyd_core_schema


class _PydanticFrozenDictAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: typ.Any, handler: pyd.GetCoreSchemaHandler
    ) -> pyd_core_schema.CoreSchema:
        def validate_from_dict(d: dict | _frozendict) -> _frozendict:
            return _frozendict(d)

        frozendict_schema = pyd_core_schema.chain_schema(
            [
                handler.generate_schema(dict[*typ.get_args(source_type)]),
                pyd_core_schema.no_info_plain_validator_function(validate_from_dict),
                pyd_core_schema.is_instance_schema(_frozendict),
            ]
        )
        return pyd_core_schema.json_or_python_schema(
            json_schema=frozendict_schema,
            python_schema=frozendict_schema,
            serialization=pyd_core_schema.plain_serializer_function_ser_schema(dict),
        )


_K = typ.TypeVar("_K")
_V = typ.TypeVar("_V")
FrozenDict = typ.Annotated[_frozendict[_K, _V], _PydanticFrozenDictAnnotation]
