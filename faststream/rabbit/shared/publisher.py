from abc import ABC
from dataclasses import dataclass, field
from typing import Optional

from faststream._compat import TypeAlias
from faststream.broker.publisher import BasePublisher
from faststream.broker.types import MsgType
from faststream.rabbit.shared.schemas import BaseRMQInformation
from faststream.rabbit.shared.types import TimeoutType
from faststream.types import AnyDict


@dataclass
class ABCPublisher(ABC, BasePublisher[MsgType], BaseRMQInformation):
    """A class representing an ABCPublisher.

    Attributes:
        routing_key : str, optional
            The routing key for the publisher to bind it to another publisher.
        mandatory : bool, optional
            Whether the message is mandatory or not.
        immediate : bool, optional
            Whether the message should be immediately delivered or not.
        persist : bool, optional
            Whether the message should be persisted or not.
        timeout : TimeoutType, optional
            The timeout for the message.
        reply_to : str, optional
            The reply-to address for the message.
        message_kwargs : dict, optional
            Additional keyword arguments for the message.

    """

    routing_key: str = ""
    mandatory: bool = True
    immediate: bool = False
    persist: bool = False
    timeout: TimeoutType = None
    reply_to: Optional[str] = None

    priority: Optional[int] = None
    message_kwargs: AnyDict = field(default_factory=dict)


QueueName: TypeAlias = str
ExchangeName: TypeAlias = str
