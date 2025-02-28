from abc import abstractmethod
from typing import (
    Any,
    AsyncContextManager,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
)

from fast_depends.dependencies import Depends

from faststream.broker.message import StreamMessage
from faststream.broker.publisher import BasePublisher
from faststream.broker.types import (
    CustomDecoder,
    CustomParser,
    MsgType,
    P_HandlerParams,
    T_HandlerReturn,
)
from faststream.broker.wrapper import HandlerCallWrapper
from faststream.types import AnyDict, SendableMessage

PublisherKeyType = TypeVar("PublisherKeyType")


class BrokerRoute(Generic[MsgType, T_HandlerReturn]):
    """A generic class to represent a broker route.

    Attributes:
        call : callable object representing the route
        args : tuple of arguments for the route
        kwargs : dictionary of keyword arguments for the route

    Args:
        call : callable object representing the route
        *args : variable length arguments for the route
        **kwargs : variable length keyword arguments for the route

    """

    call: Callable[..., T_HandlerReturn]
    args: Tuple[Any, ...]
    kwargs: AnyDict

    def __init__(
        self,
        call: Callable[..., T_HandlerReturn],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize a callable object with arguments and keyword arguments.

        Args:
            call: A callable object.
            *args: Positional arguments to be passed to the callable object.
            **kwargs: Keyword arguments to be passed to the callable object.

        """
        self.call = call
        self.args = args
        self.kwargs = kwargs


class BrokerRouter(Generic[PublisherKeyType, MsgType]):
    """A generic class representing a broker router.

    Attributes:
        prefix : prefix for the router
        _handlers : list of broker routes
        _publishers : dictionary of publishers

    Methods:
        _get_publisher_key : abstract method to get the publisher key
        _update_publisher_prefix : abstract method to update the publisher prefix
        __init__ : constructor method
        subscriber : abstract method to define a subscriber
        _wrap_subscriber : method to wrap a subscriber function
        publisher : abstract method to define a publisher
        include_router : method to include a router
        include_routers : method to include multiple routers

    """

    prefix: str
    _handlers: List[BrokerRoute[MsgType, Any]]
    _publishers: Dict[PublisherKeyType, BasePublisher[MsgType]]

    @staticmethod
    @abstractmethod
    def _get_publisher_key(publisher: BasePublisher[MsgType]) -> PublisherKeyType:
        """This is a Python function.

        _get_publisher_key function:

        Args:
            publisher: An instance of BasePublisher class.

        Returns:
            The publisher key.

        Raises:
            NotImplementedError: This function is not implemented.

        """
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def _update_publisher_prefix(
        prefix: str,
        publisher: BasePublisher[MsgType],
    ) -> BasePublisher[MsgType]:
        """Updates the publisher prefix.

        Args:
            prefix: The new prefix to be set.
            publisher: The publisher to update.

        Returns:
            The updated publisher.

        Raises:
            NotImplementedError: If the function is not implemented.

        """
        raise NotImplementedError()

    def __init__(
        self,
        prefix: str = "",
        handlers: Sequence[BrokerRoute[MsgType, SendableMessage]] = (),
        dependencies: Sequence[Depends] = (),
        middlewares: Optional[
            Sequence[
                Callable[
                    [StreamMessage[MsgType]],
                    AsyncContextManager[None],
                ]
            ]
        ] = None,
        parser: Optional[CustomParser[MsgType, StreamMessage[MsgType]]] = None,
        decoder: Optional[CustomDecoder[StreamMessage[MsgType]]] = None,
        include_in_schema: Optional[bool] = None,
    ) -> None:
        """Initialize a class object.

        Args:
            prefix (str): Prefix for the object.
            handlers (Sequence[BrokerRoute[MsgType, SendableMessage]]): Handlers for the object.
            dependencies (Sequence[Depends]): Dependencies for the object.
            middlewares (Optional[Sequence[Callable[[StreamMessage[MsgType]], AsyncContextManager[None]]]]): Middlewares for the object.
            parser (Optional[CustomParser[MsgType]]): Parser for the object.
            decoder (Optional[CustomDecoder[StreamMessage[MsgType]]]): Decoder for the object.

        """
        self.prefix = prefix
        self.include_in_schema = include_in_schema
        self._handlers = list(handlers)
        self._publishers = {}
        self._dependencies = dependencies
        self._middlewares = middlewares
        self._parser = parser
        self._decoder = decoder

    @abstractmethod
    def subscriber(
        self,
        subj: str,
        *args: Any,
        dependencies: Sequence[Depends] = (),
        middlewares: Optional[
            Sequence[
                Callable[
                    [StreamMessage[MsgType]],
                    AsyncContextManager[None],
                ]
            ]
        ] = None,
        parser: Optional[CustomParser[MsgType, StreamMessage[MsgType]]] = None,
        decoder: Optional[CustomDecoder[StreamMessage[MsgType]]] = None,
        include_in_schema: Optional[bool] = None,
        **kwargs: Any,
    ) -> Callable[
        [Callable[P_HandlerParams, T_HandlerReturn]],
        HandlerCallWrapper[MsgType, P_HandlerParams, T_HandlerReturn],
    ]:
        """A function to subscribe to a subject.

        Args:
            subj : subject to subscribe to
            *args : additional arguments
            dependencies : sequence of dependencies
            middlewares : optional sequence of middlewares
            parser : optional custom parser
            decoder : optional custom decoder
            **kwargs : additional keyword arguments

        Returns:
            A callable handler function

        Raises:
            NotImplementedError: If the function is not implemented

        """
        raise NotImplementedError()

    def _wrap_subscriber(
        self,
        *args: Any,
        dependencies: Sequence[Depends] = (),
        middlewares: Optional[
            Sequence[
                Callable[
                    [StreamMessage[MsgType]],
                    AsyncContextManager[None],
                ]
            ]
        ] = None,
        parser: Optional[CustomParser[MsgType, StreamMessage[MsgType]]] = None,
        decoder: Optional[CustomDecoder[StreamMessage[MsgType]]] = None,
        include_in_schema: bool = True,
        **kwargs: Any,
    ) -> Callable[
        [Callable[P_HandlerParams, T_HandlerReturn]],
        HandlerCallWrapper[MsgType, P_HandlerParams, T_HandlerReturn],
    ]:
        """This is a function named `_wrap_subscriber` that returns a callable object. It is used as a decorator for another function.

        Args:
            *args: Variable length arguments
            dependencies: Sequence of dependencies
            middlewares: Optional sequence of middlewares
            parser: Optional custom parser
            decoder: Optional custom decoder
            **kwargs: Variable length keyword arguments

        Returns:
            A callable object that wraps the decorated function

        This function is decorated with `@abstractmethod`, indicating that it is an abstract method and must be implemented by any subclass.

        """

        def router_subscriber_wrapper(
            func: Callable[P_HandlerParams, T_HandlerReturn]
        ) -> HandlerCallWrapper[MsgType, P_HandlerParams, T_HandlerReturn]:
            """Wraps a function with a router subscriber.

            Args:
                func: The function to be wrapped.

            Returns:
                The wrapped function.
            !!! note

                The above docstring is autogenerated by docstring-gen library (https://docstring-gen.airt.ai)
            """
            wrapped_func: HandlerCallWrapper[
                MsgType, P_HandlerParams, T_HandlerReturn
            ] = HandlerCallWrapper(func)
            route: BrokerRoute[MsgType, T_HandlerReturn] = BrokerRoute(
                wrapped_func,
                *args,
                dependencies=(*self._dependencies, *dependencies),
                middlewares=(*(self._middlewares or ()), *(middlewares or ())) or None,
                parser=parser or self._parser,
                decoder=decoder or self._decoder,
                include_in_schema=(
                    include_in_schema
                    if self.include_in_schema is None
                    else self.include_in_schema
                ),
                **kwargs,
            )
            self._handlers.append(route)
            return wrapped_func

        return router_subscriber_wrapper

    @abstractmethod
    def publisher(
        self,
        subj: str,
        *args: Any,
        **kwargs: Any,
    ) -> BasePublisher[MsgType]:
        """Publishes a message.

        Args:
            subj: Subject of the message
            *args: Additional arguments
            **kwargs: Additional keyword arguments

        Returns:
            The published message

        Raises:
            NotImplementedError: If the method is not implemented

        """
        raise NotImplementedError()

    def include_router(self, router: "BrokerRouter[PublisherKeyType, MsgType]") -> None:
        """Includes a router in the current object.

        Args:
            router: The router to be included.

        Returns:
            None

        """
        for h in router._handlers:
            self.subscriber(*h.args, **h.kwargs)(h.call)

        for p in router._publishers.values():
            p = self._update_publisher_prefix(self.prefix, p)
            key = self._get_publisher_key(p)
            self._publishers[key] = self._publishers.get(key, p)

    def include_routers(
        self, *routers: "BrokerRouter[PublisherKeyType, MsgType]"
    ) -> None:
        """Includes routers in the object.

        Args:
            *routers: Variable length argument list of routers to include.

        Returns:
            None

        """
        for r in routers:
            self.include_router(r)
