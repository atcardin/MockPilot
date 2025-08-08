from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import random
import uuid
import string
import logging
from contextlib import asynccontextmanager
import uvicorn
import httpx
import yaml
from typing import Dict, Any
from datetime import timezone
from faker import Faker
import rstr

fake = Faker()

class DataGenerator:
    @staticmethod
    def generate_string(length=10, pattern=None, format_=None):
        if pattern:
            try:
                result = rstr.xeger(pattern)
                if length and len(result) > length:
                    return result[:length]
                if length and len(result) < length:
                    padding = ''.join(random.choices(string.ascii_letters + string.digits, k=length - len(result)))
                    return result + padding
                return result
            except Exception as e:
                print(f"Warning: regex generation failed: {e}")
        # Official OpenAPI formats
        if format_ == "email":
            return fake.email()
        elif format_ == "uuid":
            return str(uuid.uuid4())
        elif format_ == "date":
            return fake.date()
        elif format_ == "date-time":
            return fake.date_time(tzinfo=timezone.utc).isoformat()
        elif format_ == "hostname":
            return fake.domain_name()
        elif format_ == "ipv4":
            return fake.ipv4()
        elif format_ == "ipv6":
            return fake.ipv6()
        elif format_ in ("uri", "url"):
            return fake.url()
        elif format_ == "password":
            return fake.password(length=length or 12)
        elif format_ == "byte":
            return base64.b64encode(os.urandom(length or 10)).decode('ascii')
        elif format_ == "binary":
            return os.urandom(length or 10)  # bytes
        # Extended formats
        elif format_ in ("phone", "phone-number"):
            return fake.phone_number()
        elif format_ == "uuid1":
            return str(uuid.uuid1())
        elif format_ == "uuid3":
            return str(uuid.uuid3(uuid.NAMESPACE_DNS, fake.domain_name()))
        elif format_ == "uuid5":
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, fake.domain_name()))
        elif format_ == "credit-card":
            return fake.credit_card_number()
        elif format_ == "country-code":
            return fake.country_code()
        elif format_ == "currency":
            return fake.currency_code()
        elif format_ == "timezone":
            return fake.timezone()
        elif format_ in ("postal-code", "zip"):
            return fake.postcode()
        elif format_ == "slug":
            return fake.slug()
        elif format_ == "username":
            return fake.user_name()
        elif format_ == "ipv4-cidr":
            return f"{fake.ipv4()}/{random.randint(0,32)}"
        elif format_ == "ipv6-cidr":
            return f"{fake.ipv6()}/{random.randint(0,128)}"
        elif format_ == "mac-address":
            return fake.mac_address()
        elif format_ == "iban":
            return fake.iban()
        elif format_ in ("bic", "swift"):
            return fake.swift()
        elif format_ == "hex-color":
            return fake.hex_color()
        elif format_ == "rgb-color":
            r, g, b = [random.randint(0,255) for _ in range(3)]
            return f"rgb({r},{g},{b})"
        elif format_ == "address":
            return fake.address().replace("\n", ", ")
        elif format_ == "street-address":
            return fake.street_address()
        elif format_ == "city":
            return fake.city()
        elif format_ == "state":
            return fake.state()
        elif format_ == "country":
            return fake.country()
        elif format_ == "company-name":
            return fake.company()
        # Fallback random string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


    @staticmethod
    def generate_integer(min_val=1, max_val=100, multiple_of=None):
        value = random.randint(min_val, max_val)
        if multiple_of:
            value -= value % multiple_of
        return value

    @staticmethod
    def generate_float(min_val=1.0, max_val=100.0, multiple_of=None):
        value = random.uniform(min_val, max_val)
        if multiple_of:
            value -= value % multiple_of
        return round(value, 2)

    @staticmethod
    def generate_boolean():
        return random.choice([True, False])

    @staticmethod
    def generate_array(field_config: Dict[str, Any], schemas, size=None):
        min_items = field_config.get("minItems", 1)
        max_items = field_config.get("maxItems", max(10, min_items))
        unique = field_config.get("uniqueItems", False)

        if size is None:
            size = random.randint(min_items, max_items)

        item_schema = field_config.get('items', {'type': 'string'})
        items = [DataGenerator.generate_field_data(item_schema, schemas) for _ in range(size)]

        if unique:
            # Try making items unique
            items = list({str(i): i for i in items}.values())
        return items

    @staticmethod
    def generate_object(field_config: Dict[str, Any], schemas):
        obj = {}
        properties = field_config.get('properties', {})
        required = field_config.get('required', [])

        for prop_name, prop_schema in properties.items():
            # Always generate required fields; optionally skip some optional fields
            # if prop_name in required or random.random() > 0.3:
            #     obj[prop_name] = DataGenerator.generate_field_data(prop_schema, schemas)
            
            # Generate all fiels
            obj[prop_name] = DataGenerator.generate_field_data(prop_schema, schemas)

        return obj

    @staticmethod
    def generate_field_data(field_config: Dict[str, Any], schemas):
        if '$ref' in field_config:
            schema_name = field_config["$ref"].split("/")[-1]
            field_config = schemas[schema_name]

        # Handle enum
        if 'enum' in field_config:
            return random.choice(field_config['enum'])

        data_type = field_config.get('type', 'string')

        if data_type == 'string':
            min_len = field_config.get('minLength', 1)
            max_len = field_config.get('maxLength', max(10, min_len))
            length = random.randint(min_len, max_len)
            pattern = field_config.get('pattern')
            format_ = field_config.get('format')
            return DataGenerator.generate_string(length, pattern, format_)

        elif data_type == 'integer':
            min_val = field_config.get('minimum', 1)
            max_val = field_config.get('maximum', 100)
            if field_config.get('exclusiveMinimum') is True:
                min_val += 1
            if field_config.get('exclusiveMaximum') is True:
                max_val -= 1
            multiple_of = field_config.get('multipleOf')
            return DataGenerator.generate_integer(min_val, max_val, multiple_of)

        elif data_type in ['number', 'float']:
            min_val = field_config.get('minimum', 1.0)
            max_val = field_config.get('maximum', 100.0)
            if field_config.get('exclusiveMinimum') is True:
                min_val += 1e-6
            if field_config.get('exclusiveMaximum') is True:
                max_val -= 1e-6
            multiple_of = field_config.get('multipleOf')
            return DataGenerator.generate_float(min_val, max_val, multiple_of)

        elif data_type == 'boolean':
            return DataGenerator.generate_boolean()

        elif data_type == 'array':
            return DataGenerator.generate_array(field_config, schemas)

        elif data_type == 'object':
            return DataGenerator.generate_object(field_config, schemas)

        else:
            return DataGenerator.generate_string()

class Sender:
    def __init__(self, config_path, logger=None):
        self.config_path = config_path
        self.config = self.load_config()
        self.logger = logger or logging.getLogger("APISender")
        self.app = None
        self.templates = None
        self.endpoints = self.load_endpoints()
        self.schemas = self.config.get("components", {}).get("schemas",{})

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        self.logger.info("Sender server starting...")
        yield
        self.logger.info("Sender server stopping...")

    def initilize_sender(self) -> FastAPI:
        """Initializes the sender API"""
        info = self.config.get("info","")
        self.app = FastAPI(
            title = info.get("title",""), 
            version = info.get("version","1.0.0"),
            lifespan = self._lifespan
        )
        # Templates and static files
        self.templates = Jinja2Templates(directory="templates")
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
        # Register routes
        self.app.get("/", response_class=HTMLResponse)(self.index)
        self.app.get("/generate_body/{endpoint_index}")(self.generate_body)
        self.app.get("/endpoint_schema/{endpoint_index}")(self.endpoint_schema)
        self.app.post("/send_request")(self.send_request_handler)
        self.app.post("/reload_config")(self.reload_config_handler)
        self.app.get("/config")(self.reload_config_handler)
        return self.app
    
    def load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise Exception(f"Config file not found at {self.config_path}!")
        
    def load_endpoints(self):
        endpoints = []
        path_config = self.config.get("paths", {})
        for path, methods in path_config.items():
            for method, details in methods.items():
                endpoints.append({
                    "path": path,
                    "method": method,
                    "details": details
                })
        return endpoints

    def generate_request_body(self, endpoint):
        body = {}
        # Empty request
        # if "requestBody" not in endpoint["details"] or "required" not in endpoint["details"]["requestBody"] or not endpoint["details"]["requestBody"]["required"]:
        if "requestBody" not in endpoint["details"]:
            return body
        # Get schema name
        # schema_name = endpoint["details"]["requestBody"]["content"]["application/json"]["schema"]["$ref"].split("/")[-1]
        # self.schemas[schema_name]
        # body = DataGenerator.generate_field_data(self.schemas[schema_name], self.schemas)
        schema = endpoint["details"]["requestBody"]["content"]["application/json"]["schema"]
        body = DataGenerator.generate_field_data(schema, self.schemas)

        return body

    async def send_request(self, endpoint, body=None):
        # Second server in the YAML is the target
        url = f"{self.config.get('servers',[])[1]['url']}{endpoint['path']}"
        print(url)
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
                    'json': response.json() if content_type.startswith('application/json') else None
                }
            except httpx.RequestError as e:
                return {'error': str(e)}

    def extract_schema_fields(self, schema_config, parent_name="", required_fields=None, visited_refs=None):
        """
        Recursively extract field information from OpenAPI schema
        """
        if visited_refs is None:
            visited_refs = set()
        
        if required_fields is None:
            required_fields = []
        
        fields = []
        
        # Handle $ref references
        if '$ref' in schema_config:
            ref_path = schema_config['$ref']
            schema_name = ref_path.split("/")[-1]
            
            # Prevent infinite recursion
            if schema_name in visited_refs:
                return fields
            
            visited_refs.add(schema_name)
            
            if schema_name in self.schemas:
                return self.extract_schema_fields(
                    self.schemas[schema_name], 
                    parent_name, 
                    required_fields, 
                    visited_refs
                )
        
        schema_type = schema_config.get('type', 'object')
        
        if schema_type == 'object':
            properties = schema_config.get('properties', {})
            required = schema_config.get('required', [])
            
            for prop_name, prop_schema in properties.items():
                field_path = f"{parent_name}.{prop_name}" if parent_name else prop_name
                is_required = prop_name in required
                
                # Handle nested objects and arrays
                if prop_schema.get('type') == 'object':
                    nested_fields = self.extract_schema_fields(
                        prop_schema, 
                        field_path, 
                        prop_schema.get('required', []),
                        visited_refs.copy()
                    )
                    fields.extend(nested_fields)
                elif prop_schema.get('type') == 'array':
                    # Add the array field itself
                    fields.append({
                        'name': field_path,
                        'type': 'array',
                        'required': is_required,
                        'description': prop_schema.get('description', ''),
                        'parent': parent_name if parent_name else None,
                        'items_type': prop_schema.get('items', {}).get('type', 'unknown')
                    })
                    
                    # If array items are objects, extract their fields too
                    items_schema = prop_schema.get('items', {})
                    if items_schema.get('type') == 'object' or '$ref' in items_schema:
                        nested_fields = self.extract_schema_fields(
                            items_schema,
                            f"{field_path}[*]",
                            items_schema.get('required', []),
                            visited_refs.copy()
                        )
                        fields.extend(nested_fields)
                else:
                    # Simple field
                    field_info = {
                        'name': field_path,
                        'type': prop_schema.get('type', 'string'),
                        'required': is_required,
                        'description': prop_schema.get('description', ''),
                        'parent': parent_name if parent_name else None
                    }
                    
                    # Add constraints
                    if 'format' in prop_schema:
                        field_info['format'] = prop_schema['format']
                    if 'minimum' in prop_schema:
                        field_info['minimum'] = prop_schema['minimum']
                    if 'maximum' in prop_schema:
                        field_info['maximum'] = prop_schema['maximum']
                    if 'minLength' in prop_schema:
                        field_info['minLength'] = prop_schema['minLength']
                    if 'maxLength' in prop_schema:
                        field_info['maxLength'] = prop_schema['maxLength']
                    if 'pattern' in prop_schema:
                        field_info['pattern'] = prop_schema['pattern']
                    if 'example' in prop_schema:
                        field_info['example'] = prop_schema['example']
                    if 'enum' in prop_schema:
                        field_info['enum'] = prop_schema['enum']
                    if 'nullable' in prop_schema:
                        field_info['nullable'] = prop_schema['nullable']
                    
                    fields.append(field_info)
        
        elif schema_type == 'array':
            # Top-level array
            items_schema = schema_config.get('items', {})
            if items_schema.get('type') == 'object' or '$ref' in items_schema:
                nested_fields = self.extract_schema_fields(
                    items_schema,
                    f"{parent_name}[*]" if parent_name else "[*]",
                    items_schema.get('required', []),
                    visited_refs.copy()
                )
                fields.extend(nested_fields)
        
        return fields

    def get_endpoint_schema_info(self, endpoint):
        """
        Extract schema information for an endpoint's request body
        """
        if "requestBody" not in endpoint["details"]:
            return []
        
        try:
            request_body = endpoint["details"]["requestBody"]
            content = request_body.get("content", {})
            
            # Look for JSON content
            json_content = content.get("application/json", {})
            if not json_content:
                return []
            
            schema = json_content.get("schema", {})
            if not schema:
                return []
            
            # Extract fields from schema
            fields = self.extract_schema_fields(schema)
            
            return fields
            
        except Exception as e:
            self.logger.error(f"Error extracting schema info: {e}")
            return []

    # Add this route handler to your initilize_sender method
    async def endpoint_schema(self, endpoint_index: int):
        """
        Get schema information for a specific endpoint
        """
        if endpoint_index >= len(self.endpoints):
            raise HTTPException(status_code=404, detail="Endpoint not found")
        
        endpoint = self.endpoints[endpoint_index]
        fields = self.get_endpoint_schema_info(endpoint)
        
        return JSONResponse(content={
            "endpoint": endpoint["path"],
            "method": endpoint["method"],
            "fields": fields
        })        

    def run(self) -> None:
        # First server in the YAML is the host 
        url = self.config.get("servers",[])[0]["url"]
        host = url.split("/")[2].split(":")[0]
        port = int(url.split("/")[2].split(":")[1])
        uvicorn.run(
            self.initilize_sender(),
            host = host,
            port = port,
            reload = False
        )

    async def index(self, request: Request):
        return self.templates.TemplateResponse("index.html", {"request": request, "config": self.config, "endpoints": self.endpoints, "schemas": self.schemas})

    async def generate_body(self, endpoint_index: int):
        if endpoint_index >= len(self.endpoints):
            raise HTTPException(status_code=404, detail="Endpoint not found")

        endpoint = self.endpoints[endpoint_index]
        body = self.generate_request_body(endpoint)
        return JSONResponse(content=body)

    async def send_request_handler(self, request: Request):
        data = await request.json()
        endpoint_index = data.get('endpoint_index')
        body = data.get('body')

        if endpoint_index >= len(self.endpoints):
            raise HTTPException(status_code=404, detail="Endpoint not found")

        endpoint = self.endpoints[endpoint_index]
        response = await self.send_request(endpoint, body)

        return JSONResponse(content={"response": response})

    async def reload_config_handler(self):
        self.config = self.load_config()
        self.endpoints = self.load_endpoints()
        self.schemas = self.config.get("components", {}).get("schemas",{})
        return JSONResponse(content={"message": "Config reloaded", "config": self.config})