from fastapi import FastAPI
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field, create_model
from typing import Any, Dict, List, Optional, Type, Annotated
import uvicorn
import logging
import json

class Receiver:
    def __init__(self, config_path, logger=None):
        self.config_path = config_path
        self.config = self.load_config()
        self.app = None
        self.logger = logger or logging.getLogger("APIReceiver")

    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f).get("receiverConfig", {})
        except FileNotFoundError:
            raise Exception(f"Config file not found at {self.config_path}!")
    
    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        self.logger.info("Receiver server starting...")
        yield
        self.logger.info("Receiver server stopping...")

    def parse_type(self, dataType: str, field: dict) -> Type:
        """Map JSON data type to Python type, adding constraints as specified."""
        if dataType == "string":
            return str
        elif dataType == "float":
            if "minValue" in field or "maxValue" in field:
                return Annotated[float, Field(ge=field.get("minValue"), le=field.get("maxValue"))]
            return float
        elif dataType == "integer":
            if "minValue" in field or "maxValue" in field:
                return Annotated[int, Field(ge=field.get("minValue", None), le=field.get("maxValue", None))] 
            return int
        elif dataType == "boolean":
            return bool
        elif dataType == "array":
            return list
        elif dataType == "object":
            return dict  # will get overridden with nested model
        else:
            raise Exception(f"Unrecognized propety type {dataType} in field {field}!")

    def _build_nested_model(self, name: str, fields: list) -> Type[BaseModel]:
        """Builds the nested model"""
        children_map: Dict[str, list] = {}

        for field in fields:
            parent = field["parentProperty"]
            children_map.setdefault(parent, []).append(field)

        def _build_model(model_name: str, parent: Optional[str]) -> Type[BaseModel]:
            model_fields = {}

            for field in children_map.get(parent, []):
                field_type = self.parse_type(field["dataType"], field)
                required = field.get("required", False)
                field_name = field["name"]

                # Nested object
                if field["dataType"] == "object":
                    nested_model = _build_model(field_name.capitalize(), field_name)
                    field_type = nested_model
                elif field["dataType"] == "array":
                    # If it's an array of objects, check if children exist
                    child_items = children_map.get(field_name, [])
                    if len(child_items) == 1 and child_items[0]["dataType"] == "object":
                        wrapper_field = child_items[0]
                        wrapper_name = wrapper_field["name"]
                        # Build model using children of that synthetic wrapper
                        item_model = _build_model(field_name.capitalize() + "Item", wrapper_name)
                        field_type = List[item_model]
                    else:
                        field_type = List[Any]

                default = ... if required else None
                model_fields[field_name] = (field_type, Field(default, description=field.get("description", "")))

            return create_model(model_name, **model_fields)

        return _build_model(name, None)

    def _make_handler(self, model):
        """Create a handler function for the model specified"""
        async def _handler(payload: model):
            return {
                "message": "Valid",
                "data": payload.dict()
                }
        return _handler

    def _make_handler_without_body(self):
        """Create a handler function for the model specified"""
        async def _handler():
            return {
                "message": "Valid"
                }
        return _handler

    def _initialize_endpoint(self, endpoint_config) -> None:
        """Initializes a single endpoint"""
        path = endpoint_config.get("url",None)
        method = endpoint_config.get("method",None)
        body = endpoint_config.get("bodyFields",[])
        if path is None or method is None:
            return
        
        if method == "GET":
            # No model needed
            model = None
            # Dummy handler
            handler = self._make_handler_without_body()
        else:
            # Create the model
            model = self._build_nested_model("RequestModel", endpoint_config["bodyFields"])
            # Create the handler function
            handler = self._make_handler(model)
        # Add the endpoint the API
        self.app.add_api_route(path, handler, methods=[method])
        self.logger.info(f"API route added: {method} {path}")
        return

    def _initialize_endpoints(self) -> None:
        """Initializes all endpoints"""
        self.logger.info("Initializing endpoints...")
        endpoints = self.config.get("endpoints", [])
        for endpoint_config in endpoints:
            self._initialize_endpoint(endpoint_config)

    def initilize_receiver(self) -> FastAPI:
        """Initializes the receiver API"""
        self.app = FastAPI(
            title = self.config.get("description",""), 
            version = self.config.get("version","1.0.0"),
            lifespan = self._lifespan
        )
        self._initialize_endpoints()
        return self.app
    
    def run(self) -> None:
        uvicorn.run(
            self.initilize_receiver(),
            host = self.config.get("host","127.0.0.1"),
            port = self.config.get("port","8000"),
            reload = False
        )