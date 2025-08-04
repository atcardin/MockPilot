from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import random
import string
import requests
import logging
from datetime import datetime
import os
from contextlib import asynccontextmanager
import uvicorn
import httpx


class DataGenerator:
    @staticmethod
    def generate_string(length=10):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def generate_integer(min_val=1, max_val=100):
        return random.randint(min_val, max_val)
    
    @staticmethod
    def generate_float(min_val=1.0, max_val=100.0):
        return round(random.uniform(min_val, max_val), 2)
    
    @staticmethod
    def generate_boolean():
        return random.choice([True, False])
    
    @staticmethod
    def generate_array(field_config, nested_fields, size=None):
        if size is None:
            size = random.randint(1, 10)
        
        child_fields = [f for f in nested_fields if f.get('parentProperty') == field_config['name']]
        
        if len(child_fields) == 1 and child_fields[0]['dataType'] == "object":
            return [DataGenerator.generate_field_data(child_fields[0], nested_fields) for _ in range(size)]

        if not child_fields:
            data_type = field_config.get('itemType', 'string')
            if data_type == 'string':
                return [DataGenerator.generate_string() for _ in range(size)]
            elif data_type == 'integer':
                return [DataGenerator.generate_integer() for _ in range(size)]
            elif data_type == 'float':
                return [DataGenerator.generate_float() for _ in range(size)]
            else:
                return [DataGenerator.generate_string() for _ in range(size)]

        array_items = []
        for _ in range(size):
            item = {}
            for child_field in child_fields:
                item[child_field['name']] = DataGenerator.generate_field_data(child_field, nested_fields)
            array_items.append(item)
        
        return array_items
    
    @staticmethod
    def generate_object(field_config, nested_fields):
        obj = {}
        child_fields = [f for f in nested_fields if f.get('parentProperty') == field_config['name']]
        
        for child_field in child_fields:
            obj[child_field['name']] = DataGenerator.generate_field_data(child_field, nested_fields)
        
        return obj
    
    @staticmethod
    def generate_field_data(field_config, all_fields):
        data_type = field_config['dataType']
        min_val = field_config.get('minValue')
        max_val = field_config.get('maxValue')
        
        if data_type == 'string':
            return DataGenerator.generate_string()
        elif data_type == 'integer':
            return DataGenerator.generate_integer(min_val or 1, max_val or 100)
        elif data_type == 'float':
            return DataGenerator.generate_float(min_val or 1.0, max_val or 100.0)
        elif data_type == 'boolean':
            return DataGenerator.generate_boolean()
        elif data_type == 'array':
            return DataGenerator.generate_array(field_config, all_fields)
        elif data_type == 'object':
            return DataGenerator.generate_object(field_config, all_fields)
        else:
            return DataGenerator.generate_string()


class Sender:
    def __init__(self, config_path, logger=None):
        self.config_path = config_path
        self.config = self.load_config()
        self.logger = logger or logging.getLogger("APISender")
        self.app = None
        self.templates = None

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        self.logger.info("Sender server starting...")
        yield
        self.logger.info("Sender server stopping...")

    def initilize_sender(self) -> FastAPI:
        """Initializes the sender API"""
        self.app = FastAPI(
            title = self.config.get("description",""), 
            version = self.config.get("version","1.0.0"),
            lifespan = self._lifespan
        )
        # Templates and static files
        self.templates = Jinja2Templates(directory="templates")
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
        # Register routes
        self.app.get("/", response_class=HTMLResponse)(self.index)
        self.app.get("/generate_body/{endpoint_index}")(self.generate_body)
        self.app.post("/send_request")(self.send_request_handler)
        self.app.post("/reload_config")(self.reload_config_handler)
        self.app.get("/config")(self.reload_config_handler)
        return self.app
    
    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f).get("senderConfig", {})
        except FileNotFoundError:
            raise Exception(f"Config file not found at {self.config_path}!")

    def generate_request_body(self, endpoint):
        body = {}
        body_fields = endpoint.get('bodyFields', [])
        root_fields = [f for f in body_fields if f.get('parentProperty') is None]

        for field in root_fields:
            body[field['name']] = DataGenerator.generate_field_data(field, body_fields)
        
        return body
    
    # def send_request(self, endpoint, body=None, custom_host=None, custom_port=None):
    #     host = custom_host or self.config['externalHost']
    #     port = custom_port or self.config['externalPort']
    #     url = f"http://{host}:{port}{endpoint['url']}"
    #     method = endpoint['method'].upper()

    #     try:
    #         if method == 'GET':
    #             response = requests.get(url, json=body, timeout=10)
    #         elif method == 'POST':
    #             response = requests.post(url, json=body, timeout=10)
    #         elif method == 'PUT':
    #             response = requests.put(url, json=body, timeout=10)
    #         elif method == 'DELETE':
    #             response = requests.delete(url, json=body, timeout=10)
    #         else:
    #             return {'error': f'Unsupported HTTP method: {method}'}
            
    #         return {
    #             'status_code': response.status_code,
    #             'headers': dict(response.headers),
    #             'body': response.text,
    #             'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
    #         }
    #     except requests.exceptions.RequestException as e:
    #         return {'error': str(e)}
        
    async def send_request(self, endpoint, body=None, custom_host=None, custom_port=None):
        host = custom_host or self.config['targetHost']
        port = custom_port or self.config['targetPort']
        url = f"http://{host}:{port}{endpoint['url']}"
        method = endpoint['method'].upper()

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                if method == 'GET':
                    response = await client.get(url)
                elif method == 'POST':
                    response = await client.post(url, json=body)
                elif method == 'PUT':
                    response = await client.put(url, json=body)
                elif method == 'DELETE':
                    response = await client.delete(url, json=body)
                else:
                    return {'error': f'Unsupported HTTP method: {method}'}

                content_type = response.headers.get('content-type', '')
                return {
                    'status_code': response.status_code,
                    # 'headers': dict(response.headers),
                    # 'body': response.text,
                    'json': response.json() if content_type.startswith('application/json') else None
                }
            except httpx.RequestError as e:
                return {'error': str(e)}
        
    def run(self) -> None:
        uvicorn.run(
            self.initilize_sender(),
            host = self.config.get("host","127.0.0.1"),
            port = self.config.get("port","5000"),
            reload = False
        )

    async def index(self, request: Request):
        return self.templates.TemplateResponse("index.html", {"request": request, "config": self.config})

    async def generate_body(self, endpoint_index: int):
        if endpoint_index >= len(self.config['endpoints']):
            raise HTTPException(status_code=404, detail="Endpoint not found")

        endpoint = self.config['endpoints'][endpoint_index]
        body = self.generate_request_body(endpoint)
        return JSONResponse(content=body)

    async def send_request_handler(self, request: Request):
        data = await request.json()
        endpoint_index = data.get('endpoint_index')
        body = data.get('body')

        if endpoint_index >= len(self.config['endpoints']):
            raise HTTPException(status_code=404, detail="Endpoint not found")

        endpoint = self.config['endpoints'][endpoint_index]
        response = await self.send_request(endpoint, body)

        return JSONResponse(content={"response": response})

    async def reload_config_handler(self):
        self.config = self.load_config()
        return JSONResponse(content={"message": "Config reloaded", "config": self.config})