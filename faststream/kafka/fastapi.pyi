import logging
from asyncio import AbstractEventLoop
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

import aiokafka
from aiokafka import ConsumerRecord
from aiokafka.producer.producer import _missing
from fast_depends.dependencies import Depends
from fastapi import params
from fastapi.datastructures import Default
from fastapi.routing import APIRoute
from fastapi.utils import generate_unique_id
from kafka.coordinator.assignors.abstract import AbstractPartitionAssignor
from kafka.coordinator.assignors.roundrobin import RoundRobinPartitionAssignor
from kafka.partitioner.default import DefaultPartitioner
from starlette import routing
from starlette.responses import JSONResponse, Response
from starlette.types import AppType, ASGIApp, Lifespan

from faststream.__about__ import __version__
from faststream._compat import override
from faststream.asyncapi import schema as asyncapi
from faststream.broker.core.asyncronous import default_filter
from faststream.broker.fastapi.router import StreamRouter
from faststream.broker.message import StreamMessage
from faststream.broker.middlewares import BaseMiddleware
from faststream.broker.security import BaseSecurity
from faststream.broker.types import (
    CustomDecoder,
    CustomParser,
    Filter,
    P_HandlerParams,
    T_HandlerReturn,
)
from faststream.broker.wrapper import HandlerCallWrapper
from faststream.kafka.asyncapi import Publisher
from faststream.kafka.broker import KafkaBroker
from faststream.kafka.message import KafkaMessage
from faststream.log import access_logger

Partition = TypeVar("Partition")

class KafkaRouter(StreamRouter[ConsumerRecord]):
    broker_class: Type[KafkaBroker]
    broker: KafkaBroker

    def __init__(
        self,
        bootstrap_servers: Union[str, Iterable[str]] = "localhost",
        *,
        # both
        client_id: str = "faststream-" + __version__,
        request_timeout_ms: int = 40 * 1000,
        retry_backoff_ms: int = 100,
        metadata_max_age_ms: int = 5 * 60 * 1000,
        api_version: str = "auto",
        connections_max_idle_ms: int = 540000,
        security: Optional[BaseSecurity] = None,
        # publisher
        acks: Union[Literal[0, 1, -1, "all"], object] = _missing,
        key_serializer: Optional[Callable[[Any], bytes]] = None,
        value_serializer: Optional[Callable[[Any], bytes]] = None,
        compression_type: Optional[Literal["gzip", "snappy", "lz4", "zstd"]] = None,
        max_batch_size: int = 16384,
        partitioner: Callable[
            [bytes, List[Partition], List[Partition]],
            Partition,
        ] = DefaultPartitioner(),
        max_request_size: int = 1048576,
        linger_ms: int = 0,
        send_backoff_ms: int = 100,
        enable_idempotence: bool = False,
        transactional_id: Optional[str] = None,
        transaction_timeout_ms: int = 60000,
        loop: Optional[AbstractEventLoop] = None,
        # FastAPI kwargs
        prefix: str = "",
        tags: Optional[List[Union[str, Enum]]] = None,
        dependencies: Optional[Sequence[params.Depends]] = None,
        default_response_class: Type[Response] = Default(JSONResponse),
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[routing.BaseRoute]] = None,
        routes: Optional[List[routing.BaseRoute]] = None,
        redirect_slashes: bool = True,
        default: Optional[ASGIApp] = None,
        dependency_overrides_provider: Optional[Any] = None,
        route_class: Type[APIRoute] = APIRoute,
        on_startup: Optional[Sequence[Callable[[], Any]]] = None,
        on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        lifespan: Optional[Lifespan[Any]] = None,
        generate_unique_id_function: Callable[[APIRoute], str] = Default(
            generate_unique_id
        ),
        # broker kwargs
        graceful_timeout: Optional[float] = None,
        apply_types: bool = True,
        validate: bool = True,
        decoder: Optional[CustomDecoder[KafkaMessage]] = None,
        parser: Optional[CustomParser[aiokafka.ConsumerRecord, KafkaMessage]] = None,
        middlewares: Optional[
            Sequence[
                Callable[
                    [aiokafka.ConsumerRecord],
                    BaseMiddleware,
                ]
            ]
        ] = None,
        # AsyncAPI information
        asyncapi_url: Union[str, List[str], None] = None,
        protocol: str = "kafka",
        protocol_version: str = "auto",
        description: Optional[str] = None,
        asyncapi_tags: Optional[Sequence[asyncapi.Tag]] = None,
        schema_url: Optional[str] = "/asyncapi",
        setup_state: bool = True,
        # logging args
        logger: Optional[logging.Logger] = access_logger,
        log_level: int = logging.INFO,
        log_fmt: Optional[str] = None,
        **kwargs: Any,
    ) -> None: ...
    @overload  # type: ignore[override]
    @override
    def subscriber(
        self,
        *topics: str,
        group_id: Optional[str] = None,
        key_deserializer: Optional[Callable[[bytes], Any]] = None,
        value_deserializer: Optional[Callable[[bytes], Any]] = None,
        fetch_max_wait_ms: int = 500,
        fetch_max_bytes: int = 52428800,
        fetch_min_bytes: int = 1,
        max_partition_fetch_bytes: int = 1 * 1024 * 1024,
        auto_offset_reset: Literal[
            "latest",
            "earliest",
            "none",
        ] = "latest",
        auto_commit: bool = True,
        auto_commit_interval_ms: int = 5000,
        check_crcs: bool = True,
        partition_assignment_strategy: Sequence[AbstractPartitionAssignor] = (
            RoundRobinPartitionAssignor,
        ),
        max_poll_interval_ms: int = 300000,
        rebalance_timeout_ms: Optional[int] = None,
        session_timeout_ms: int = 10000,
        heartbeat_interval_ms: int = 3000,
        consumer_timeout_ms: int = 200,
        max_poll_records: Optional[int] = None,
        exclude_internal_topics: bool = True,
        isolation_level: Literal[
            "read_uncommitted",
            "read_committed",
        ] = "read_uncommitted",
        # broker arguments
        dependencies: Sequence[Depends] = (),
        parser: Optional[
            CustomParser[Tuple[aiokafka.ConsumerRecord, ...], KafkaMessage]
        ] = None,
        decoder: Optional[CustomDecoder[KafkaMessage]] = None,
        middlewares: Optional[
            Sequence[
                Callable[
                    [aiokafka.ConsumerRecord],
                    BaseMiddleware,
                ]
            ]
        ] = None,
        filter: Filter[
            StreamMessage[Tuple[aiokafka.ConsumerRecord, ...]]
        ] = default_filter,
        batch: Literal[True] = True,
        max_records: Optional[int] = None,
        batch_timeout_ms: int = 200,
        retry: Union[bool, int] = False,
        no_ack: bool = False,
        # AsyncAPI information
        title: Optional[str] = None,
        description: Optional[str] = None,
        include_in_schema: bool = True,
        **__service_kwargs: Any,
    ) -> Callable[
        [Callable[P_HandlerParams, T_HandlerReturn]],
        HandlerCallWrapper[
            Tuple[aiokafka.ConsumerRecord, ...], P_HandlerParams, T_HandlerReturn
        ],
    ]: ...
    @overload
    def subscriber(
        self,
        *topics: str,
        group_id: Optional[str] = None,
        key_deserializer: Optional[Callable[[bytes], Any]] = None,
        value_deserializer: Optional[Callable[[bytes], Any]] = None,
        fetch_max_wait_ms: int = 500,
        fetch_max_bytes: int = 52428800,
        fetch_min_bytes: int = 1,
        max_partition_fetch_bytes: int = 1 * 1024 * 1024,
        auto_offset_reset: Literal[
            "latest",
            "earliest",
            "none",
        ] = "latest",
        auto_commit: bool = True,
        auto_commit_interval_ms: int = 5000,
        check_crcs: bool = True,
        partition_assignment_strategy: Sequence[AbstractPartitionAssignor] = (
            RoundRobinPartitionAssignor,
        ),
        max_poll_interval_ms: int = 300000,
        rebalance_timeout_ms: Optional[int] = None,
        session_timeout_ms: int = 10000,
        heartbeat_interval_ms: int = 3000,
        consumer_timeout_ms: int = 200,
        max_poll_records: Optional[int] = None,
        exclude_internal_topics: bool = True,
        isolation_level: Literal[
            "read_uncommitted",
            "read_committed",
        ] = "read_uncommitted",
        # broker arguments
        dependencies: Sequence[Depends] = (),
        parser: Optional[CustomParser[aiokafka.ConsumerRecord, KafkaMessage]] = None,
        decoder: Optional[CustomDecoder[KafkaMessage]] = None,
        middlewares: Optional[
            Sequence[
                Callable[
                    [aiokafka.ConsumerRecord],
                    BaseMiddleware,
                ]
            ]
        ] = None,
        filter: Filter[KafkaMessage] = default_filter,
        batch: Literal[False] = False,
        max_records: Optional[int] = None,
        batch_timeout_ms: int = 200,
        retry: Union[bool, int] = False,
        no_ack: bool = False,
        # AsyncAPI information
        title: Optional[str] = None,
        description: Optional[str] = None,
        include_in_schema: bool = True,
        **__service_kwargs: Any,
    ) -> Callable[
        [Callable[P_HandlerParams, T_HandlerReturn]],
        HandlerCallWrapper[aiokafka.ConsumerRecord, P_HandlerParams, T_HandlerReturn],
    ]: ...
    @overload  # type: ignore[override]
    @override
    def add_api_mq_route(
        self,
        *topics: str,
        endpoint: Callable[..., T_HandlerReturn],
        group_id: Optional[str] = None,
        key_deserializer: Optional[Callable[[bytes], Any]] = None,
        value_deserializer: Optional[Callable[[bytes], Any]] = None,
        fetch_max_wait_ms: int = 500,
        fetch_max_bytes: int = 52428800,
        fetch_min_bytes: int = 1,
        max_partition_fetch_bytes: int = 1 * 1024 * 1024,
        auto_offset_reset: Literal[
            "latest",
            "earliest",
            "none",
        ] = "latest",
        auto_commit: bool = True,
        auto_commit_interval_ms: int = 5000,
        check_crcs: bool = True,
        partition_assignment_strategy: Sequence[AbstractPartitionAssignor] = (
            RoundRobinPartitionAssignor,
        ),
        max_poll_interval_ms: int = 300000,
        rebalance_timeout_ms: Optional[int] = None,
        session_timeout_ms: int = 10000,
        heartbeat_interval_ms: int = 3000,
        consumer_timeout_ms: int = 200,
        max_poll_records: Optional[int] = None,
        exclude_internal_topics: bool = True,
        isolation_level: Literal[
            "read_uncommitted",
            "read_committed",
        ] = "read_uncommitted",
        # broker arguments
        dependencies: Sequence[Depends] = (),
        parser: Optional[
            CustomParser[Tuple[aiokafka.ConsumerRecord, ...], KafkaMessage]
        ] = None,
        decoder: Optional[CustomDecoder[KafkaMessage]] = None,
        middlewares: Optional[
            Sequence[
                Callable[
                    [aiokafka.ConsumerRecord],
                    BaseMiddleware,
                ]
            ]
        ] = None,
        filter: Filter[
            StreamMessage[Tuple[aiokafka.ConsumerRecord, ...]]
        ] = default_filter,
        batch: Literal[True] = True,
        max_records: Optional[int] = None,
        batch_timeout_ms: int = 200,
        retry: Union[bool, int] = False,
        # AsyncAPI information
        title: Optional[str] = None,
        description: Optional[str] = None,
        **__service_kwargs: Any,
    ) -> Callable[
        [Tuple[aiokafka.ConsumerRecord, ...], bool], Awaitable[T_HandlerReturn]
    ]: ...
    @overload
    def add_api_mq_route(
        self,
        *topics: str,
        endpoint: Callable[..., T_HandlerReturn],
        group_id: Optional[str] = None,
        key_deserializer: Optional[Callable[[bytes], Any]] = None,
        value_deserializer: Optional[Callable[[bytes], Any]] = None,
        fetch_max_wait_ms: int = 500,
        fetch_max_bytes: int = 52428800,
        fetch_min_bytes: int = 1,
        max_partition_fetch_bytes: int = 1 * 1024 * 1024,
        auto_offset_reset: Literal[
            "latest",
            "earliest",
            "none",
        ] = "latest",
        auto_commit: bool = True,
        auto_commit_interval_ms: int = 5000,
        check_crcs: bool = True,
        partition_assignment_strategy: Sequence[AbstractPartitionAssignor] = (
            RoundRobinPartitionAssignor,
        ),
        max_poll_interval_ms: int = 300000,
        rebalance_timeout_ms: Optional[int] = None,
        session_timeout_ms: int = 10000,
        heartbeat_interval_ms: int = 3000,
        consumer_timeout_ms: int = 200,
        max_poll_records: Optional[int] = None,
        exclude_internal_topics: bool = True,
        isolation_level: Literal[
            "read_uncommitted",
            "read_committed",
        ] = "read_uncommitted",
        # broker arguments
        dependencies: Sequence[Depends] = (),
        parser: Optional[CustomParser[aiokafka.ConsumerRecord, KafkaMessage]] = None,
        decoder: Optional[CustomDecoder[KafkaMessage]] = None,
        middlewares: Optional[
            Sequence[
                Callable[
                    [aiokafka.ConsumerRecord],
                    BaseMiddleware,
                ]
            ]
        ] = None,
        filter: Filter[KafkaMessage] = default_filter,
        batch: Literal[False] = False,
        max_records: Optional[int] = None,
        batch_timeout_ms: int = 200,
        retry: Union[bool, int] = False,
        # AsyncAPI information
        title: Optional[str] = None,
        description: Optional[str] = None,
        **__service_kwargs: Any,
    ) -> Callable[[aiokafka.ConsumerRecord, bool], Awaitable[T_HandlerReturn]]: ...
    @override
    def publisher(  # type: ignore[override]
        self,
        topic: str,
        key: Optional[bytes] = None,
        partition: Optional[int] = None,
        timestamp_ms: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        reply_to: str = "",
        batch: bool = False,
        # AsyncAPI information
        title: Optional[str] = None,
        description: Optional[str] = None,
        schema: Optional[Any] = None,
        include_in_schema: bool = True,
    ) -> Publisher: ...
    @overload
    def after_startup(
        self,
        func: Callable[[AppType], Mapping[str, Any]],
    ) -> Callable[[AppType], Mapping[str, Any]]: ...
    @overload
    def after_startup(
        self,
        func: Callable[[AppType], Awaitable[Mapping[str, Any]]],
    ) -> Callable[[AppType], Awaitable[Mapping[str, Any]]]: ...
    @overload
    def after_startup(
        self,
        func: Callable[[AppType], None],
    ) -> Callable[[AppType], None]: ...
    @overload
    def after_startup(
        self,
        func: Callable[[AppType], Awaitable[None]],
    ) -> Callable[[AppType], Awaitable[None]]: ...
    @override
    @staticmethod
    def _setup_log_context(  # type: ignore[override]
        main_broker: KafkaBroker,
        including_broker: KafkaBroker,
    ) -> None: ...
