import json
from abc import abstractmethod
from contextlib import asynccontextmanager
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    overload,
)

from fastapi import APIRouter, FastAPI, params
from fastapi.datastructures import Default
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute
from fastapi.utils import generate_unique_id
from starlette import routing
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute, _DefaultLifespan
from starlette.types import AppType, ASGIApp, Lifespan

from faststream.asyncapi import schema as asyncapi
from faststream.asyncapi.schema import Schema
from faststream.asyncapi.site import get_asyncapi_html
from faststream.broker.core.asyncronous import BrokerAsyncUsecase
from faststream.broker.fastapi.route import StreamRoute
from faststream.broker.publisher import BasePublisher
from faststream.broker.schemas import NameRequired
from faststream.broker.types import MsgType, P_HandlerParams, T_HandlerReturn
from faststream.broker.wrapper import HandlerCallWrapper
from faststream.types import AnyDict
from faststream.utils.functions import to_async


class StreamRouter(APIRouter, Generic[MsgType]):
    """A class to route streams.

    Attributes:
        broker_class : type of the broker
        broker : instance of the broker
        docs_router : optional APIRouter for documentation
        _after_startup_hooks : list of functions to be executed after startup
        schema : optional schema

        title : title of the router
        description : description of the router
        version : version of the router
        license : optional license information
        contact : optional contact information

    Methods:
        __init__ : initialize the StreamRouter
        add_api_mq_route : add a route for API and message queue
        subscriber : decorator to define a subscriber
        wrap_lifespan : wrap the lifespan of the router
        after_startup : decorator to define a function to be executed after startup
        publisher : create a publisher for the broker
        asyncapi_router : create an APIRouter for AsyncAPI documentation
        include_router : include another router in the StreamRouter
        _setup_log_context : setup log context for the broker

    """

    broker_class: Type[BrokerAsyncUsecase[MsgType, Any]]
    broker: BrokerAsyncUsecase[MsgType, Any]
    docs_router: Optional[APIRouter]
    _after_startup_hooks: List[
        Callable[[AppType], Awaitable[Optional[Mapping[str, Any]]]]
    ]
    schema: Optional[Schema]

    title: str
    description: str
    version: str
    license: Optional[AnyDict]
    contact: Optional[AnyDict]

    def __init__(
        self,
        *connection_args: Tuple[Any, ...],
        prefix: str = "",
        tags: Optional[List[Union[str, Enum]]] = None,
        dependencies: Optional[Sequence[params.Depends]] = None,
        default_response_class: Type[Response] = Default(JSONResponse),
        responses: Optional[Dict[Union[int, str], AnyDict]] = None,
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
        setup_state: bool = True,
        lifespan: Optional[Lifespan[Any]] = None,
        generate_unique_id_function: Callable[[APIRoute], str] = Default(
            generate_unique_id
        ),
        # AsyncAPI information
        asyncapi_tags: Optional[Sequence[Union[asyncapi.Tag, asyncapi.TagDict]]] = None,
        schema_url: Optional[str] = "/asyncapi",
        **connection_kwars: Any,
    ) -> None:
        """Initialize an instance of a class.

        Args:
            *connection_args: Variable length arguments for the connection
            prefix: Prefix for the class
            tags: Optional list of tags for the class
            dependencies: Optional sequence of dependencies for the class
            default_response_class: Default response class for the class
            responses: Optional dictionary of responses for the class
            callbacks: Optional list of callbacks for the class
            routes: Optional list of routes for the class
            redirect_slashes: Boolean value indicating whether to redirect slashes
            default: Optional default value for the class
            dependency_overrides_provider: Optional provider for dependency overrides
            route_class: Route class for the class
            on_startup: Optional sequence of functions to run on startup
            on_shutdown: Optional sequence of functions to run on shutdown
            deprecated: Optional boolean value indicating whether the class is deprecated
            include_in_schema: Boolean value indicating whether to include the class in the schema
            setup_state: Boolean value indicating whether to setup state
            lifespan: Optional lifespan for the class
            generate_unique_id_function: Function to generate unique ID for the class
            asyncapi_tags: Optional sequence of asyncapi tags for the class schema

        """
        assert (  # nosec B101
            self.broker_class
        ), "You should specify `broker_class` at your implementation"

        self.broker = self.broker_class(
            *connection_args,
            apply_types=False,
            tags=asyncapi_tags,
            **connection_kwars,
        )

        self.setup_state = setup_state

        # AsyncAPI information
        # Empty
        self.terms_of_service = None
        self.identifier = None
        self.asyncapi_tags = None
        self.external_docs = None
        # parse from FastAPI app on startup
        self.title = ""
        self.version = ""
        self.description = ""
        self.license = None
        self.contact = None

        self.schema = None

        super().__init__(
            prefix=prefix,
            tags=tags,
            dependencies=dependencies,
            default_response_class=default_response_class,
            responses=responses,
            callbacks=callbacks,
            routes=routes,
            redirect_slashes=redirect_slashes,
            default=default,
            dependency_overrides_provider=dependency_overrides_provider,
            route_class=route_class,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
            generate_unique_id_function=generate_unique_id_function,
            lifespan=self.wrap_lifespan(lifespan),
            on_startup=on_startup,
            on_shutdown=on_shutdown,
        )

        self.docs_router = self.asyncapi_router(schema_url)

        self._after_startup_hooks = []

    def add_api_mq_route(
        self,
        path: Union[NameRequired, str],
        *extra: Union[NameRequired, str],
        endpoint: Callable[P_HandlerParams, T_HandlerReturn],
        dependencies: Sequence[params.Depends],
        **broker_kwargs: Any,
    ) -> HandlerCallWrapper[MsgType, P_HandlerParams, T_HandlerReturn]:
        """Add an API message queue route.

        Args:
            path: The path of the route.
            *extra: Additional path segments.
            endpoint: The endpoint function to be called for this route.
            dependencies: The dependencies required by the endpoint function.
            **broker_kwargs: Additional keyword arguments to be passed to the broker.

        Returns:
            The handler call wrapper for the route.

        """
        route: StreamRoute[MsgType, P_HandlerParams, T_HandlerReturn] = StreamRoute(
            path,
            *extra,
            endpoint=endpoint,
            dependencies=dependencies,
            dependency_overrides_provider=self.dependency_overrides_provider,
            broker=self.broker,
            **broker_kwargs,
        )
        self.routes.append(route)
        return route.handler

    def subscriber(
        self,
        path: Union[str, NameRequired],
        *extra: Union[NameRequired, str],
        dependencies: Optional[Sequence[params.Depends]] = None,
        **broker_kwargs: Any,
    ) -> Callable[
        [Callable[P_HandlerParams, T_HandlerReturn]],
        HandlerCallWrapper[MsgType, P_HandlerParams, T_HandlerReturn],
    ]:
        """A function decorator for subscribing to a message queue.

        Args:
            path : The path to subscribe to. Can be a string or a `NameRequired` object.
            *extra : Additional path segments. Can be a `NameRequired` object or a string.
            dependencies : Optional sequence of dependencies.
            **broker_kwargs : Additional keyword arguments for the broker.

        Returns:
            A callable decorator that adds the decorated function as an endpoint for the specified path.

        Raises:
            NotImplementedError: If silent animals are not supported.

        """
        current_dependencies = self.dependencies.copy()
        if dependencies:
            current_dependencies.extend(dependencies)

        def decorator(
            func: Callable[P_HandlerParams, T_HandlerReturn],
        ) -> HandlerCallWrapper[MsgType, P_HandlerParams, T_HandlerReturn]:
            """A decorator function.

            Args:
                func: The function to be decorated.

            Returns:
                The decorated function.
            !!! note

                The above docstring is autogenerated by docstring-gen library (https://docstring-gen.airt.ai)
            """
            return self.add_api_mq_route(
                path,
                *extra,
                endpoint=func,
                dependencies=current_dependencies,
                **broker_kwargs,
            )

        return decorator

    def wrap_lifespan(self, lifespan: Optional[Lifespan[Any]] = None) -> Lifespan[Any]:
        """Wrap the lifespan of the application.

        Args:
            lifespan: Optional lifespan object.

        Returns:
            The wrapped lifespan object.

        Raises:
            NotImplementedError: If silent animals are not supported.

        """
        if lifespan is not None:
            lifespan_context = lifespan
        else:
            lifespan_context = _DefaultLifespan(self)

        @asynccontextmanager
        async def start_broker_lifespan(
            app: FastAPI,
        ) -> AsyncIterator[Mapping[str, Any]]:
            """Starts the lifespan of a broker.

            Args:
                app (FastAPI): The FastAPI application.

            Yields:
                AsyncIterator[Mapping[str, Any]]: A mapping of context information during the lifespan of the broker.

            Raises:
                NotImplementedError: If silent animals are not supported.
            !!! note

                The above docstring is autogenerated by docstring-gen library (https://docstring-gen.airt.ai)
            """
            from faststream.asyncapi.generate import get_app_schema

            self.title = app.title
            self.description = app.description
            self.version = app.version
            self.contact = app.contact
            self.license = app.license_info

            self.schema = get_app_schema(self)
            if self.docs_router:
                app.include_router(self.docs_router)

            async with lifespan_context(app) as maybe_context:
                if maybe_context is None:
                    context: AnyDict = {}
                else:
                    context = dict(maybe_context)

                context.update({"broker": self.broker})
                await self.broker.start()

                for h in self._after_startup_hooks:
                    h_context = await h(app)
                    if h_context:  # pragma: no branch
                        context.update(h_context)

                try:
                    if self.setup_state:
                        yield context
                    else:
                        # NOTE: old asgi compatibility
                        yield  # type: ignore

                finally:
                    await self.broker.close()

        return start_broker_lifespan

    @overload
    def after_startup(
        self,
        func: Callable[[AppType], Mapping[str, Any]],
    ) -> Callable[[AppType], Mapping[str, Any]]:
        """A function decorator to be used for executing a function after startup.

        Args:
            func: A function that takes an `AppType` argument and returns a mapping of strings to any type.

        Returns:
            A decorated function that takes an `AppType` argument and returns a mapping of strings to any type.

        """
        ...

    @overload
    def after_startup(
        self,
        func: Callable[[AppType], Awaitable[Mapping[str, Any]]],
    ) -> Callable[[AppType], Awaitable[Mapping[str, Any]]]:
        """A function decorator to be used for running a function after the startup of an application.

        Args:
            func: The function to be decorated. It should take an argument of type AppType and return an awaitable mapping of strings to any type.

        Returns:
            The decorated function.

        Note:
            This function can be used as a decorator for other functions.

        """
        ...

    @overload
    def after_startup(
        self,
        func: Callable[[AppType], None],
    ) -> Callable[[AppType], None]:
        """A function decorator to be used for running a function after the startup of an application.

        Args:
            func: The function to be executed after startup.

        Returns:
            A decorated function that will be executed after startup.

        """
        ...

    @overload
    def after_startup(
        self,
        func: Callable[[AppType], Awaitable[None]],
    ) -> Callable[[AppType], Awaitable[None]]:
        """Decorator to register a function to be executed after the application startup.

        Args:
            func: A callable that takes an `AppType` argument and returns an awaitable `None`.

        Returns:
            A decorated function that takes an `AppType` argument and returns an awaitable `None`.

        """
        ...

    def after_startup(
        self,
        func: Union[
            Callable[[AppType], Mapping[str, Any]],
            Callable[[AppType], Awaitable[Mapping[str, Any]]],
            Callable[[AppType], None],
            Callable[[AppType], Awaitable[None]],
        ],
    ) -> Union[
        Callable[[AppType], Mapping[str, Any]],
        Callable[[AppType], Awaitable[Mapping[str, Any]]],
        Callable[[AppType], None],
        Callable[[AppType], Awaitable[None]],
    ]:
        """Register a function to be executed after startup.

        Args:
            func: A function to be executed after startup. It can take an `AppType` argument and return a mapping of strings to any values, or it can take an `AppType` argument and return an awaitable that resolves to a mapping of strings to any values, or it can take an `AppType` argument and return nothing, or it can take an `AppType` argument and return an awaitable that resolves to nothing.

        Returns:
            The registered function.

        """
        self._after_startup_hooks.append(to_async(func))  # type: ignore
        return func

    def publisher(
        self,
        queue: Union[NameRequired, str],
        *publisher_args: Any,
        **publisher_kwargs: Any,
    ) -> BasePublisher[MsgType]:
        """Publishes messages to a queue.

        Args:
            queue: The queue to publish the messages to. Can be either a `NameRequired` object or a string.
            *publisher_args: Additional arguments to be passed to the publisher.
            **publisher_kwargs: Additional keyword arguments to be passed to the publisher.

        Returns:
            An instance of `BasePublisher` that can be used to publish messages to the specified queue.

        """
        return self.broker.publisher(
            queue,
            *publisher_args,
            **publisher_kwargs,
        )

    def asyncapi_router(self, schema_url: Optional[str]) -> Optional[APIRouter]:
        """Creates an API router for serving AsyncAPI documentation.

        Args:
            schema_url: The URL where the AsyncAPI schema will be served.

        Returns:
            An instance of APIRouter if include_in_schema and schema_url are both True, otherwise returns None.

        Raises:
            AssertionError: If self.schema is not set.

        Notes:
            This function defines three nested functions: download_app_json_schema, download_app_yaml_schema, and serve_asyncapi_schema. These functions are used to handle different routes for serving the AsyncAPI schema and documentation.

        """
        if not self.include_in_schema or not schema_url:
            return None

        def download_app_json_schema() -> Response:
            assert (  # nosec B101
                self.schema
            ), "You need to run application lifespan at first"

            return Response(
                content=json.dumps(self.schema.to_jsonable(), indent=4),
                headers={"Content-Type": "application/octet-stream"},
            )

        def download_app_yaml_schema() -> Response:
            assert (  # nosec B101
                self.schema
            ), "You need to run application lifespan at first"

            return Response(
                content=self.schema.to_yaml(),
                headers={
                    "Content-Type": "application/octet-stream",
                },
            )

        def serve_asyncapi_schema(
            sidebar: bool = True,
            info: bool = True,
            servers: bool = True,
            operations: bool = True,
            messages: bool = True,
            schemas: bool = True,
            errors: bool = True,
            expandMessageExamples: bool = True,
        ) -> HTMLResponse:
            """Serve the AsyncAPI schema as an HTML response.

            Args:
                sidebar (bool, optional): Whether to include the sidebar in the HTML. Defaults to True.
                info (bool, optional): Whether to include the info section in the HTML. Defaults to True.
                servers (bool, optional): Whether to include the servers section in the HTML. Defaults to True.
                operations (bool, optional): Whether to include the operations section in the HTML. Defaults to True.
                messages (bool, optional): Whether to include the messages section in the HTML. Defaults to True.
                schemas (bool, optional): Whether to include the schemas section in the HTML. Defaults to True.
                errors (bool, optional): Whether to include the errors section in the HTML. Defaults to True.
                expandMessageExamples (bool, optional): Whether to expand message examples in the HTML. Defaults to True.

            Returns:
                HTMLResponse: The HTML response containing the AsyncAPI schema.

            Raises:
                AssertionError: If the schema is not available.
            !!! note

                The above docstring is autogenerated by docstring-gen library (https://docstring-gen.airt.ai)
            """
            assert (  # nosec B101
                self.schema
            ), "You need to run application lifespan at first"

            return HTMLResponse(
                content=get_asyncapi_html(
                    self.schema,
                    sidebar=sidebar,
                    info=info,
                    servers=servers,
                    operations=operations,
                    messages=messages,
                    schemas=schemas,
                    errors=errors,
                    expand_message_examples=expandMessageExamples,
                    title=self.schema.info.title,
                )
            )

        docs_router = APIRouter(
            prefix=self.prefix,
            tags=["asyncapi"],
            redirect_slashes=self.redirect_slashes,
            default=self.default,
            deprecated=self.deprecated,
        )
        docs_router.get(schema_url)(serve_asyncapi_schema)
        docs_router.get(f"{schema_url}.json")(download_app_json_schema)
        docs_router.get(f"{schema_url}.yaml")(download_app_yaml_schema)
        return docs_router

    def include_router(
        self,
        router: "APIRouter",
        *,
        prefix: str = "",
        tags: Optional[List[Union[str, Enum]]] = None,
        dependencies: Optional[Sequence[params.Depends]] = None,
        default_response_class: Type[Response] = Default(JSONResponse),
        responses: Optional[Dict[Union[int, str], AnyDict]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        generate_unique_id_function: Callable[[APIRoute], str] = Default(
            generate_unique_id
        ),
    ) -> None:
        """Includes a router in the API.

        Args:
            router (APIRouter): The router to include.
            prefix (str, optional): The prefix to prepend to all paths defined in the router. Defaults to "".
            tags (List[Union[str, Enum]], optional): The tags to assign to all paths defined in the router. Defaults to None.
            dependencies (Sequence[params.Depends], optional): The dependencies to apply to all paths defined in the router. Defaults to None.
            default_response_class (Type[Response], optional): The default response class to use for all paths defined in the router. Defaults to Default(JSONResponse).
            responses (Dict[Union[int, str], AnyDict], optional): The responses to define for all paths defined in the router. Defaults to None.
            callbacks (List[BaseRoute], optional): The callbacks to apply to all paths defined in the router. Defaults to None.
            deprecated (bool, optional): Whether the router is deprecated. Defaults to None.
            include_in_schema (bool, optional): Whether to include the router in the API schema. Defaults to True.
            generate_unique_id_function (Callable[[APIRoute], str], optional): The function to generate unique IDs for

        """
        if isinstance(router, StreamRouter):  # pragma: no branch
            self._setup_log_context(self.broker, router.broker)
            self.broker.handlers = {**self.broker.handlers, **router.broker.handlers}
            self.broker._publishers = {
                **self.broker._publishers,
                **router.broker._publishers,
            }

        super().include_router(
            router=router,
            prefix=prefix,
            tags=tags,
            dependencies=dependencies,
            default_response_class=default_response_class,
            responses=responses,
            callbacks=callbacks,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
            generate_unique_id_function=generate_unique_id_function,
        )

    @staticmethod
    @abstractmethod
    def _setup_log_context(
        main_broker: BrokerAsyncUsecase[MsgType, Any],
        including_broker: BrokerAsyncUsecase[MsgType, Any],
    ) -> None:
        """Set up log context.

        Args:
            main_broker: The main broker.
            including_broker: The including broker.

        Returns:
            None

        Raises:
            NotImplementedError: If the function is not implemented.

        """
        raise NotImplementedError()
