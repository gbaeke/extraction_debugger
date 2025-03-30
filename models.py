import json
from datetime import date
from typing import List, Optional, Dict, Any, Type, Union
from pydantic import BaseModel, Field, create_model
import instructor
from openai import AzureOpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


class DateEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle date objects."""
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


def create_model_from_schema(schema_path_or_dict: Union[str, Dict[str, Any]]) -> Type[BaseModel]:
    """Creates Pydantic models dynamically from any JSON schema file or dictionary."""
    # If schema_path_or_dict is a string, treat it as a file path
    if isinstance(schema_path_or_dict, str):
        with open(schema_path_or_dict, 'r') as f:
            schema = json.load(f)
    else:
        schema = schema_path_or_dict

    def get_field_type(field_schema: Dict[str, Any]) -> Type:
        """Recursively determine the Python type from a JSON schema field."""
        field_type = field_schema.get('type')
        
        if field_type == 'string':
            if field_schema.get('format') == 'date':
                return date
            return str
        elif field_type == 'number':
            return float
        elif field_type == 'boolean':
            return bool
        elif field_type == 'array':
            if 'items' in field_schema:
                item_schema = field_schema['items']
                if item_schema.get('type') == 'object':
                    # Create a model for array items
                    item_field_definitions: Dict[str, tuple] = {}
                    for item_field_name, item_field_schema in item_schema['properties'].items():
                        item_python_field_name = item_field_name.lower().replace(' ', '_')
                        item_field_definitions[item_python_field_name] = (
                            get_field_type(item_field_schema),
                            Field(
                                alias=item_field_name,
                                description=item_field_schema.get('description', '')
                            )
                        )
                    
                    ItemModel = create_model(
                        f'{item_schema.get("title", "Item")}',
                        **item_field_definitions
                    )
                    return List[ItemModel]
                else:
                    return List[get_field_type(item_schema)]
        elif field_type == 'object':
            # Create a nested model
            nested_field_definitions: Dict[str, tuple] = {}
            for nested_field_name, nested_field_schema in field_schema.get('properties', {}).items():
                nested_python_field_name = nested_field_name.lower().replace(' ', '_')
                nested_field_definitions[nested_python_field_name] = (
                    get_field_type(nested_field_schema),
                    Field(
                        alias=nested_field_name,
                        description=nested_field_schema.get('description', '')
                    )
                )
            
            NestedModel = create_model(
                f'{field_schema.get("title", "NestedModel")}',
                **nested_field_definitions
            )
            return NestedModel
        
        return Any  # Default fallback type

    # Create field definitions for the main model
    field_definitions: Dict[str, tuple] = {}
    
    # Get the list of required fields from the schema
    required_fields = schema.get('required', [])
    
    # Process each property from the schema
    for field_name, field_schema in schema.get('properties', {}).items():
        # Convert field name to Python-friendly name
        python_field_name = field_name.lower().replace(' ', '_')
        
        # Get the field type
        field_type = get_field_type(field_schema)
        
        # Create the field definition
        field_definitions[python_field_name] = (
            Optional[field_type] if field_name not in required_fields else field_type,
            Field(
                alias=field_name,
                description=field_schema.get('description', '')
            )
        )

    # Create the model with Pydantic v2 config
    Model = create_model(
        schema.get('title', 'DynamicModel'),
        **field_definitions,
        __config__=type('Config', (), {'validate_by_name': True})
    )
    
    return Model


def extract_invoice_data(markdown_path: str, schema_path: str) -> tuple[Type[BaseModel], BaseModel]:
    """Extract invoice data from markdown file using Instructor.
    
    Returns:
        tuple: A tuple containing (InvoiceModel, invoice_data) where:
            - InvoiceModel is the Pydantic model class
            - invoice_data is the extracted data instance
    """
    # Create the model from schema
    InvoiceModel = create_model_from_schema(schema_path)
    
    # Read the markdown content
    with open(markdown_path, 'r') as f:
        markdown_content = f.read()
    
    # Create an instructor-patched Azure OpenAI client
    client = instructor.from_openai(
        AzureOpenAI(
            api_key=os.getenv("openai_key"),
            api_version=os.getenv("openai_api_version"),
            azure_endpoint=os.getenv("openai_endpoint"),
        )
    )
    
    # Extract structured data
    invoice_data = client.chat.completions.create(
        model="gpt-4o-global",
        response_model=InvoiceModel,
        messages=[
            {
                "role": "system",
                "content": "You are an expert at extracting structured data from invoices. Extract the data according to the provided schema."
            },
            {
                "role": "user",
                "content": f"Extract the invoice data from this markdown content:\n\n{markdown_content}"
            }
        ],
    )
    
    return InvoiceModel, invoice_data


# Example usage:
if __name__ == "__main__":
    # Extract data from the markdown file
    InvoiceModel, invoice_data = extract_invoice_data(
        "outputs/Factuur002.md",
        "schemas/cronos-boekhouding.json"
    )
    # print the model schema
    print(InvoiceModel.model_json_schema())

    # Print the extracted data using the custom encoder
    print(json.dumps(invoice_data.model_dump(), indent=2, cls=DateEncoder))

    