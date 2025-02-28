from abc import ABC, abstractmethod
from collections import Counter
from logging import Logger
from types import TracebackType
from typing import Any, Optional, Type, Union
from typing import Counter as CounterType

from faststream.broker.message import StreamMessage, SyncStreamMessage
from faststream.broker.types import MsgType
from faststream.exceptions import (
    AckMessage,
    HandlerException,
    NackMessage,
    RejectMessage,
    SkipMessage,
)
from faststream.utils.functions import call_or_await


class BaseWatcher(ABC):
    """A base class for a watcher.

    Attributes:
        max_tries : maximum number of tries allowed

    Args:
        max_tries : maximum number of tries allowed (default=0)
        logger : logger object (optional)

    Methods:
        add : add a message to the watcher
        is_max : check if the maximum number of tries has been reached for a message
        remove : remove a message from the watcher

    """

    max_tries: int

    def __init__(
        self,
        max_tries: int = 0,
        logger: Optional[Logger] = None,
    ) -> None:
        """Initialize the class.

        Args:
            max_tries: Maximum number of tries allowed
            logger: Optional logger object

        Raises:
            NotImplementedError: If the method is not implemented in the subclass.

        """
        self.logger = logger
        self.max_tries = max_tries

    @abstractmethod
    def add(self, message_id: str) -> None:
        """Add a message.

        Args:
            message_id: ID of the message to be added

        Returns:
            None

        Raises:
            NotImplementedError: If the method is not implemented

        """
        raise NotImplementedError()

    @abstractmethod
    def is_max(self, message_id: str) -> bool:
        """Check if the given message ID is the maximum.

        Args:
            message_id: The ID of the message to check.

        Returns:
            True if the given message ID is the maximum, False otherwise.

        Raises:
            NotImplementedError: This method is meant to be overridden by subclasses.

        """
        raise NotImplementedError()

    @abstractmethod
    def remove(self, message_id: str) -> None:
        """Remove a message.

        Args:
            message_id: ID of the message to be removed

        Returns:
            None

        Raises:
            NotImplementedError: If the method is not implemented

        """
        raise NotImplementedError()


class EndlessWatcher(BaseWatcher):
    def add(self, message_id: str) -> None:
        """Add a message to the list.

        Args:
            message_id: ID of the message to be added

        Returns:
            None

        """
        pass

    def is_max(self, message_id: str) -> bool:
        """Check if a message is the maximum.

        Args:
            message_id: ID of the message to check

        Returns:
            True if the message is the maximum, False otherwise

        """
        return False

    def remove(self, message_id: str) -> None:
        """Remove a message.

        Args:
            message_id: The ID of the message to be removed.

        Returns:
            None

        """
        pass


class OneTryWatcher(BaseWatcher):
    def add(self, message_id: str) -> None:
        """Add a message.

        Args:
            message_id: ID of the message to be added

        Returns:
            None

        """
        pass

    def is_max(self, message_id: str) -> bool:
        """Check if the given message ID is the maximum.

        Args:
            message_id: The ID of the message to check.

        Returns:
            True if the given message ID is the maximum, False otherwise.

        """
        return True

    def remove(self, message_id: str) -> None:
        """Remove a message.

        Args:
            message_id: ID of the message to be removed

        Returns:
            None

        """
        pass


class CounterWatcher(BaseWatcher):
    """A class to watch and track the count of messages.

    Attributes:
        memory : CounterType[str] - a counter to store the count of each message

    Args:
        max_tries : int - maximum number of tries allowed
        logger : Optional[Logger] - logger object for logging messages

    Methods:
        __init__(self, max_tries: int = 3, logger: Optional[Logger] = None) - initializes the CounterWatcher object
        add(self, message_id: str) -> None - adds a message to the counter
        is_max(self, message_id: str) -> bool - checks if the count of a message has reached the maximum tries
        remove(self, message: str) -> None - removes a message from the counter

    """

    memory: CounterType[str]

    def __init__(
        self,
        max_tries: int = 3,
        logger: Optional[Logger] = None,
    ) -> None:
        """Initialize the class.

        Args:
            max_tries (int): maximum number of tries
            logger (Optional[Logger]): logger object (default: None)

        """
        super().__init__(logger=logger, max_tries=max_tries)
        self.memory = Counter()

    def add(self, message_id: str) -> None:
        """Increments the count of a message in the memory.

        Args:
            message_id: The ID of the message to be incremented.

        Returns:
            None

        """
        self.memory[message_id] += 1

    def is_max(self, message_id: str) -> bool:
        """Check if the number of tries for a message has exceeded the maximum allowed tries.

        Args:
            message_id: The ID of the message

        Returns:
            True if the number of tries has exceeded the maximum allowed tries, False otherwise

        """
        is_max = self.memory[message_id] > self.max_tries
        if self.logger is not None:
            if is_max:
                self.logger.error(f"Already retried {self.max_tries} times. Skipped.")
            else:
                self.logger.error("Error is occured. Pushing back to queue.")
        return is_max

    def remove(self, message: str) -> None:
        """Remove a message from memory.

        Args:
            message: The message to be removed.

        Returns:
            None

        """
        self.memory[message] = 0
        self.memory += Counter()


class WatcherContext:
    """A class representing a context for a watcher.

    Attributes:
        watcher : the watcher object
        message : the message being watched
        extra_ack_args : additional arguments for acknowledging the message

    Methods:
        __aenter__ : called when entering the context
        __aexit__ : called when exiting the context
        __ack : acknowledges the message
        __nack : negatively acknowledges the message
        __reject : rejects the message

    """

    def __init__(
        self,
        message: Union[SyncStreamMessage[MsgType], StreamMessage[MsgType]],
        watcher: BaseWatcher,
        **extra_ack_args: Any,
    ) -> None:
        """Initialize a new instance of the class.

        Args:
            watcher: An instance of BaseWatcher.
            message: An instance of SyncStreamMessage or StreamMessage.
            **extra_ack_args: Additional arguments for acknowledgement.

        Attributes:
            watcher: An instance of BaseWatcher.
            message: An instance of SyncStreamMessage or StreamMessage.
            extra_ack_args: Additional arguments for acknowledgement.

        """
        self.watcher = watcher
        self.message = message
        self.extra_ack_args = extra_ack_args or {}

    async def __aenter__(self) -> None:
        self.watcher.add(self.message.message_id)

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        """Exit the asynchronous context manager.

        Args:
            exc_type: The type of the exception raised, if any.
            exc_val: The exception instance raised, if any.
            exc_tb: The traceback for the exception raised, if any.

        Returns:
            A boolean indicating whether the exit was successful or not.

        """
        if not exc_type:
            await self.__ack()

        elif isinstance(exc_val, SkipMessage):
            self.watcher.remove(self.message.message_id)

        elif isinstance(exc_val, HandlerException):
            if isinstance(exc_val, AckMessage):
                await self.__ack()
            elif isinstance(exc_val, NackMessage):
                if self.watcher.is_max(self.message.message_id):
                    await self.__reject()
                else:
                    await self.__nack()
            elif isinstance(exc_val, RejectMessage):  # pragma: no branch
                await self.__reject()
            return True

        elif self.watcher.is_max(self.message.message_id):
            await self.__reject()

        else:
            await self.__nack()

        return False

    async def __ack(self) -> None:
        await call_or_await(self.message.ack, **self.extra_ack_args)
        self.watcher.remove(self.message.message_id)

    async def __nack(self) -> None:
        await call_or_await(self.message.nack, **self.extra_ack_args)

    async def __reject(self) -> None:
        await call_or_await(self.message.reject, **self.extra_ack_args)
        self.watcher.remove(self.message.message_id)
