import logging
from typing import Any, Optional

from faststream._compat import override
from faststream.broker.core.mixins import LoggingMixin
from faststream.broker.message import StreamMessage
from faststream.log import access_logger
from faststream.rabbit.shared.schemas import RabbitExchange, RabbitQueue
from faststream.types import AnyDict


class RabbitLoggingMixin(LoggingMixin):
    """A class that extends the LoggingMixin class and adds additional functionality for logging RabbitMQ related information.

    Attributes:
        _max_queue_len : maximum length of the queue name
        _max_exchange_len : maximum length of the exchange name

    Methods:
        __init__ : Initializes the RabbitLoggingMixin object.
        _get_log_context : Overrides the _get_log_context method of the LoggingMixin class to include RabbitMQ related context information.
        fmt : Returns the log format string.
        _setup_log_context : Sets up the log context by updating the maximum lengths of the queue and exchange names.

    """

    _max_queue_len: int
    _max_exchange_len: int

    def __init__(
        self,
        *args: Any,
        logger: Optional[logging.Logger] = access_logger,
        log_level: int = logging.INFO,
        log_fmt: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the class.

        Args:
            *args: Variable length argument list
            logger: Optional logger object
            log_level: Logging level
            log_fmt: Optional log format
            **kwargs: Arbitrary keyword arguments

        Returns:
            None

        """
        super().__init__(
            *args,
            logger=logger,
            log_level=log_level,
            log_fmt=log_fmt,
            **kwargs,
        )
        self._max_queue_len = 4
        self._max_exchange_len = 4

    @override
    def _get_log_context(  # type: ignore[override]
        self,
        message: Optional[StreamMessage[Any]],
        queue: RabbitQueue,
        exchange: Optional[RabbitExchange] = None,
    ) -> AnyDict:
        """Get the log context.

        Args:
            message: Optional stream message.
            queue: RabbitQueue object.
            exchange: Optional RabbitExchange object.

        Returns:
            Dictionary containing the log context.

        Note:
            This is a private method and should not be called directly.

        """
        context = {
            "queue": queue.name,
            "exchange": exchange.name if exchange else "default",
            **super()._get_log_context(message),
        }
        return context

    @property
    def fmt(self) -> str:
        return super().fmt or (
            "%(asctime)s %(levelname)s - "
            f"%(exchange)-{self._max_exchange_len}s | "
            f"%(queue)-{self._max_queue_len}s | "
            f"%(message_id)-{self._message_id_ln}s "
            "- %(message)s"
        )

    def _setup_log_context(
        self,
        queue: Optional[RabbitQueue] = None,
        exchange: Optional[RabbitExchange] = None,
    ) -> None:
        """Set up log context.

        Args:
            queue: Optional RabbitQueue object representing the queue.
            exchange: Optional RabbitExchange object representing the exchange.

        Returns:
            None

        """
        if exchange is not None:
            self._max_exchange_len = max(
                self._max_exchange_len, len(exchange.name or "")
            )

        if queue is not None:  # pragma: no branch
            self._max_queue_len = max(self._max_queue_len, len(queue.name))
