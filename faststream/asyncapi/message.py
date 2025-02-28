from inspect import isclass
from typing import Any, Dict, Optional, Sequence, Type, overload

from fast_depends.core import CallModel
from pydantic import BaseModel

from faststream._compat import PYDANTIC_V2, get_model_fields, model_schema


def parse_handler_params(call: CallModel[Any, Any], prefix: str = "") -> Dict[str, Any]:
    """Parses the handler parameters.

    Args:
        call: The call model.
        prefix: The prefix for the model schema.

    Returns:
        A dictionary containing the parsed parameters.

    """
    body = get_model_schema(
        call.model,
        prefix=prefix,
        exclude=tuple(call.custom_fields.keys()),
    )

    if body is None:
        return {"title": "EmptyPayload", "type": "null"}

    return body


@overload
def get_response_schema(call: None, prefix: str = "") -> None:
    """Get the response schema for a call.

    Args:
        call: The call object
        prefix: The prefix to add to the response schema

    Returns:
        None

    """
    ...


@overload
def get_response_schema(call: CallModel[Any, Any], prefix: str = "") -> Dict[str, Any]:
    """Get the response schema for a given call.

    Args:
        call: The call model object.
        prefix: Optional prefix to be added to the schema keys.

    Returns:
        A dictionary representing the response schema.

    """
    ...


def get_response_schema(
    call: Optional[CallModel[Any, Any]],
    prefix: str = "",
) -> Optional[Dict[str, Any]]:
    """Get the response schema for a given call.

    Args:
        call: The call model.
        prefix: A prefix to add to the schema keys.

    Returns:
        The response schema as a dictionary.

    """
    return get_model_schema(
        getattr(
            call, "response_model", None
        ),  # NOTE: FastAPI Dependant object compatibility
        prefix=prefix,
    )


@overload
def get_model_schema(
    call: None,
    prefix: str = "",
    exclude: Sequence[str] = (),
) -> None:
    """Get the model schema.

    Args:
        call: The call object.
        prefix: The prefix string.
        exclude: A sequence of strings to exclude.

    Returns:
        None

    """
    ...


@overload
def get_model_schema(
    call: Type[BaseModel],
    prefix: str = "",
    exclude: Sequence[str] = (),
) -> Dict[str, Any]:
    """Get the model schema.

    Args:
        call: Type of the base model.
        prefix: Prefix for the model schema.
        exclude: Sequence of strings to exclude from the model schema.

    Returns:
        A dictionary representing the model schema.

    Note:
        The function signature is incomplete and requires additional information.

    """
    ...


def get_model_schema(
    call: Optional[Type[BaseModel]],
    prefix: str = "",
    exclude: Sequence[str] = (),
) -> Optional[Dict[str, Any]]:
    """Get the schema of a model.

    Args:
        call: The model class to get the schema for.
        prefix: A prefix to add to the schema title.
        exclude: A sequence of field names to exclude from the schema.

    Returns:
        The schema of the model as a dictionary, or None if the model has no fields.

    Raises:
        NotImplementedError: If the model is a silent animal.

    """
    if call is None:
        return None

    params = {k: v for k, v in get_model_fields(call).items() if k not in exclude}
    params_number = len(params)

    if params_number == 0:
        return None

    model = None
    use_original_model = False
    if params_number == 1:
        name, param = tuple(params.items())[0]

        if (
            param.annotation
            and isclass(param.annotation)
            and issubclass(param.annotation, BaseModel)  # NOTE: 3.7-3.10 compatibility
        ):
            model = param.annotation
            use_original_model = True

    if model is None:
        model = call

    body: Dict[str, Any] = model_schema(model)
    body["properties"] = body.get("properties", {})
    for i in exclude:
        body["properties"].pop(i, None)
    if required := body.get("required"):
        body["required"] = list(filter(lambda x: x not in exclude, required))

    if params_number == 1 and not use_original_model:
        param_body: Dict[str, Any] = body.get("properties", {})
        param_body = param_body[name]

        if PYDANTIC_V2:
            original_title = param.title
        else:
            original_title = param.field_info.title  # type: ignore[attr-defined]

        if original_title:
            use_original_model = True
            param_body["title"] = original_title
        else:
            param_body["title"] = name

        body = param_body

    if not use_original_model:
        body["title"] = f"{prefix}:Payload"

    return body
