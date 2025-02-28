from aiokafka import ConsumerRecord

from faststream.broker.fastapi.router import StreamRouter
from faststream.kafka.broker import KafkaBroker


class KafkaRouter(StreamRouter[ConsumerRecord]):
    """A class to route Kafka streams.

    Attributes:
        broker_class : class representing the Kafka broker

    Methods:
        _setup_log_context : sets up the log context for the main broker and including broker

    """

    broker_class = KafkaBroker

    @staticmethod
    def _setup_log_context(
        main_broker: KafkaBroker,
        including_broker: KafkaBroker,
    ) -> None:
        """Set up log context for a Kafka broker.

        Args:
            main_broker: The main Kafka broker.
            including_broker: The Kafka broker to include in the log context.

        Returns:
            None

        """
        for h in including_broker.handlers.values():
            main_broker._setup_log_context(h.topics)
