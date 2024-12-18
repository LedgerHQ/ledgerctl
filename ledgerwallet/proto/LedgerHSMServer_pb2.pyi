from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Parameter(_message.Message):
    __slots__ = ("name", "alias", "local")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ALIAS_FIELD_NUMBER: _ClassVar[int]
    LOCAL_FIELD_NUMBER: _ClassVar[int]
    name: str
    alias: str
    local: bool
    def __init__(self, name: _Optional[str] = ..., alias: _Optional[str] = ..., local: bool = ...) -> None: ...

class Request(_message.Message):
    __slots__ = ("id", "parameters", "reference", "elf", "close", "largeStack", "remote_parameters")
    ID_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    REFERENCE_FIELD_NUMBER: _ClassVar[int]
    ELF_FIELD_NUMBER: _ClassVar[int]
    CLOSE_FIELD_NUMBER: _ClassVar[int]
    LARGESTACK_FIELD_NUMBER: _ClassVar[int]
    REMOTE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    id: str
    parameters: bytes
    reference: str
    elf: bytes
    close: bool
    largeStack: bool
    remote_parameters: _containers.RepeatedCompositeFieldContainer[Parameter]
    def __init__(self, id: _Optional[str] = ..., parameters: _Optional[bytes] = ..., reference: _Optional[str] = ..., elf: _Optional[bytes] = ..., close: bool = ..., largeStack: bool = ..., remote_parameters: _Optional[_Iterable[_Union[Parameter, _Mapping]]] = ...) -> None: ...

class Response(_message.Message):
    __slots__ = ("id", "response", "message", "exception")
    ID_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    EXCEPTION_FIELD_NUMBER: _ClassVar[int]
    id: str
    response: bytes
    message: str
    exception: str
    def __init__(self, id: _Optional[str] = ..., response: _Optional[bytes] = ..., message: _Optional[str] = ..., exception: _Optional[str] = ...) -> None: ...
