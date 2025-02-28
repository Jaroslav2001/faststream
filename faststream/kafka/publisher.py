from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence

from aiokafka import ConsumerRecord

from faststream.__about__ import __version__
from faststream._compat import override
from faststream.exceptions import NOT_CONNECTED_YET
from faststream.kafka.producer import AioKafkaFastProducer
from faststream.kafka.shared.publisher import ABCPublisher
from faststream.types import SendableMessage


@dataclass
class LogicPublisher(ABCPublisher[ConsumerRecord]):
    """A class to publish messages to a Kafka topic.

    Attributes:
        _producer : An optional instance of AioKafkaFastProducer
        batch : A boolean indicating whether to send messages in batch
        client_id : A string representing the client ID

    Methods:
        publish : Publishes messages to the Kafka topic

    Raises:
        AssertionError: If `_producer` is not set up or if multiple messages are sent without the `batch` flag

    """

    _producer: Optional[AioKafkaFastProducer] = field(default=None, init=False)
    batch: bool = field(default=False)
    client_id: str = field(default="faststream-" + __version__)

    @override
    async def publish(  # type: ignore[override]
        self,
        *messages: SendableMessage,
        message: SendableMessage = "",
        key: Optional[bytes] = None,
        partition: Optional[int] = None,
        timestamp_ms: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Publish messages to a topic.

        Args:
            *messages: Variable length argument list of SendableMessage objects.
            message: A SendableMessage object. Default is an empty string.
            key: Optional bytes object representing the message key.
            partition: Optional integer representing the partition to publish the message to.
            timestamp_ms: Optional integer representing the timestamp of the message in milliseconds.
            headers: Optional dictionary of header key-value pairs.
            correlation_id: Optional string representing the correlation ID of the message.

        Returns:
            None

        Raises:
            AssertionError: If `_producer` is not set up.
            AssertionError: If `batch` flag is not set and there are multiple messages.
            ValueError: If `message` is not a sequence when `messages` is empty.

        """
        assert self._producer, NOT_CONNECTED_YET  # nosec B101
        assert (  # nosec B101
            self.batch or len(messages) < 2
        ), "You can't send multiple messages without `batch` flag"
        assert self.topic, "You have to specify outgoing topic"  # nosec B101

        if not self.batch:
            return await self._producer.publish(
                message=next(iter(messages), message),
                topic=self.topic,
                key=key or self.key,
                partition=partition or self.partition,
                timestamp_ms=timestamp_ms or self.timestamp_ms,
                correlation_id=correlation_id,
                headers=headers or self.headers,
                reply_to=self.reply_to or "",
            )
        else:
            to_send: Sequence[SendableMessage]
            if not messages:
                if not isinstance(message, Sequence):
                    raise ValueError(
                        f"Message: {message} should be Sequence type to send in batch"
                    )
                else:
                    to_send = message
            else:
                to_send = messages

            await self._producer.publish_batch(
                *to_send,
                topic=self.topic,
                partition=partition or self.partition,
                timestamp_ms=timestamp_ms or self.timestamp_ms,
                headers=headers or self.headers,
            )
            return None
