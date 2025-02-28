import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from faststream.asyncapi.schema import Schema


def get_asyncapi_html(
    schema: "Schema",
    sidebar: bool = True,
    info: bool = True,
    servers: bool = True,
    operations: bool = True,
    messages: bool = True,
    schemas: bool = True,
    errors: bool = True,
    expand_message_examples: bool = True,
    title: str = "FastStream",
) -> str:
    """Generate HTML for displaying an AsyncAPI document.

    Args:
        schema (Schema): The AsyncAPI schema object.
        sidebar (bool, optional): Whether to show the sidebar. Defaults to True.
        info (bool, optional): Whether to show the info section. Defaults to True.
        servers (bool, optional): Whether to show the servers section. Defaults to True.
        operations (bool, optional): Whether to show the operations section. Defaults to True.
        messages (bool, optional): Whether to show the messages section. Defaults to True.
        schemas (bool, optional): Whether to show the schemas section. Defaults to True.
        errors (bool, optional): Whether to show the errors section. Defaults to True.
        expand_message_examples (bool, optional): Whether to expand message examples. Defaults to True.
        title (str, optional): The title of the HTML document. Defaults to "FastStream".

    Returns:
        str: The generated HTML document.

    Raises:
        NotImplementedError: If silent animals are not supported.

    """
    schema_json = schema.to_json()

    config = {
        "schema": schema_json,
        "config": {
            "show": {
                "sidebar": sidebar,
                "info": info,
                "servers": servers,
                "operations": operations,
                "messages": messages,
                "schemas": schemas,
                "errors": errors,
            },
            "expand": {
                "messageExamples": expand_message_examples,
            },
            "sidebar": {
                "showServers": "byDefault",
                "showOperations": "byDefault",
            },
        },
    }

    return (
        """
    <!DOCTYPE html>
    <html>
        <head>
    """
        f"""
        <title>{title} AsyncAPI</title>
    """
        """
        <link rel="icon" href="https://www.asyncapi.com/favicon.ico">
        <link rel="icon" type="image/png" sizes="16x16" href="https://www.asyncapi.com/favicon-16x16.png">
        <link rel="icon" type="image/png" sizes="32x32" href="https://www.asyncapi.com/favicon-32x32.png">
        <link rel="icon" type="image/png" sizes="194x194" href="https://www.asyncapi.com/favicon-194x194.png">
        <link rel="stylesheet" href="https://unpkg.com/@asyncapi/react-component@1.0.0-next.46/styles/default.min.css">
        </head>

        <style>
        html {
            font-family: ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica Neue,Arial,Noto Sans,sans-serif,Apple Color Emoji,Segoe UI Emoji,Segoe UI Symbol,Noto Color Emoji;
            line-height: 1.5;
        }
        </style>

        <body>
        <div id="asyncapi"></div>

        <script src="https://unpkg.com/@asyncapi/react-component@1.0.0-next.47/browser/standalone/index.js"></script>
        <script>
    """
        f"""
            AsyncApiStandalone.render({json.dumps(config)}, document.getElementById('asyncapi'));
    """
        """
        </script>
        </body>
    </html>
    """
    )


def serve_app(
    schema: "Schema",
    host: str,
    port: int,
) -> None:
    """Serve the FastAPI application.

    Args:
        schema: The schema object representing the API specification.
        host: The host address to run the application on.
        port: The port number to run the application on.

    Returns:
        None

    """
    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse

    app = FastAPI()

    @app.get("/")
    def asyncapi(
        sidebar: bool = True,
        info: bool = True,
        servers: bool = True,
        operations: bool = True,
        messages: bool = True,
        schemas: bool = True,
        errors: bool = True,
        expandMessageExamples: bool = True,
    ) -> HTMLResponse:  # pragma: no cover
        """Generate an AsyncAPI HTML response.

        Args:
            sidebar (bool): Whether to include the sidebar. Default is True.
            info (bool): Whether to include the info section. Default is True.
            servers (bool): Whether to include the servers section. Default is True.
            operations (bool): Whether to include the operations section. Default is True.
            messages (bool): Whether to include the messages section. Default is True.
            schemas (bool): Whether to include the schemas section. Default is True.
            errors (bool): Whether to include the errors section. Default is True.
            expandMessageExamples (bool): Whether to expand message examples. Default is True.

        Returns:
            HTMLResponse: The generated HTML response.

        """
        return HTMLResponse(
            content=get_asyncapi_html(
                schema,
                sidebar=sidebar,
                info=info,
                servers=servers,
                operations=operations,
                messages=messages,
                schemas=schemas,
                errors=errors,
                expand_message_examples=expandMessageExamples,
                title=schema.info.title,
            )
        )

    uvicorn.run(app, host=host, port=port)
