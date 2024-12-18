from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class App(_message.Message):
    __slots__ = ("flags", "hash", "hashCodeData", "name")
    FLAGS_FIELD_NUMBER: _ClassVar[int]
    HASH_FIELD_NUMBER: _ClassVar[int]
    HASHCODEDATA_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    flags: int
    hash: bytes
    hashCodeData: bytes
    name: str
    def __init__(self, flags: _Optional[int] = ..., hash: _Optional[bytes] = ..., hashCodeData: _Optional[bytes] = ..., name: _Optional[str] = ...) -> None: ...

class AppList(_message.Message):
    __slots__ = ("list",)
    LIST_FIELD_NUMBER: _ClassVar[int]
    list: _containers.RepeatedCompositeFieldContainer[App]
    def __init__(self, list: _Optional[_Iterable[_Union[App, _Mapping]]] = ...) -> None: ...
