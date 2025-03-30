from abc import ABC, abstractmethod
import json
from openai import AsyncAzureOpenAI
import logging
from datetime import datetime
import os
from dotenv import load_dotenv
import instructor
from models import create_model_from_schema, DateEncoder
from typing import Type, Dict, Any
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_calls.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class BaseExtractor(ABC):
    def __init__(self, model_config):
        self.model_config = model_config
        self.openai_key = os.getenv("openai_key")
        self.openai_endpoint = os.getenv("openai_endpoint")
        self.openai_api_version = os.getenv("openai_api_version")
        self.client = AsyncAzureOpenAI(
            api_key=self.openai_key,
            api_version=self.openai_api_version,
            azure_endpoint=self.openai_endpoint
        )

    @abstractmethod
    async def extract(self, content: str, schema: dict, run_number: int) -> dict:
        """Extract information from content using the specified schema."""
        pass

class JsonModeExtractor(BaseExtractor):
    async def extract(self, content: str, schema: dict, run_number: int) -> dict:
        messages = [
            {"role": "system", "content": f"""
                You are a helpful assistant that extracts currency information from text. Return the response as a JSON based on this schema:
                {json.dumps(schema)}
             """},
            {"role": "user", "content": f"""
                IMPORTANT: the net amount should match the currency of the VAT amount.
                Extract the currency information from this text:
                {content}
            """}
        ]
        
        try:
            logger.info(f"Starting Run {run_number} using JSON mode")
            
            start_time = datetime.now()
            
            create_params = {
                "model": self.model_config['deployment'],
                "messages": messages,
                "response_format": { "type": "json_object" }
            }
            
            if 'temperature' in self.model_config:
                create_params['temperature'] = self.model_config['temperature']
            
            response = await self.client.chat.completions.create(**create_params)
            end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Run {run_number} completed in {duration:.2f} seconds")
            logger.info(f"Response: {response.choices[0].message.content}")
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error during API call for Run {run_number}: {str(e)}", exc_info=True)
            return None

class InstructorExtractor(BaseExtractor):
    def __init__(self, model_config):
        super().__init__(model_config)
        # Create an instructor-patched client
        self.client = instructor.from_openai(
            AsyncAzureOpenAI(
                api_key=self.openai_key,
                api_version=self.openai_api_version,
                azure_endpoint=self.openai_endpoint,
            )
        )

    async def extract(self, content: str, schema: dict, run_number: int) -> dict:
        try:
            logger.info(f"Starting Run {run_number} using Instructor mode")
            start_time = datetime.now()

            # Create the model from schema
            InvoiceModel = create_model_from_schema(schema)
            
            # Extract structured data
            invoice_data = await self.client.chat.completions.create(
                model=self.model_config['deployment'],
                response_model=InvoiceModel,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured data from invoices. Extract the data according to the provided schema."
                    },
                    {
                        "role": "user",
                        "content": f"Extract the invoice data from this markdown content:\n\n{content}"
                    }
                ],
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Run {run_number} completed in {duration:.2f} seconds")
            
            # Convert the Pydantic model to a dict
            result = invoice_data.model_dump()
            logger.info(f"Response: {json.dumps(result, indent=2, cls=DateEncoder)}")
            
            return result
        except Exception as e:
            logger.error(f"Error during API call for Run {run_number}: {str(e)}", exc_info=True)
            return None

class StructuredOutputExtractor(BaseExtractor):
    async def extract(self, content: str, schema: dict, run_number: int) -> dict:
        try:
            logger.info(f"Starting Run {run_number} using Structured Output mode")
            start_time = datetime.now()

            # Create the model from schema
            InvoiceModel = create_model_from_schema(schema)
            
            # Extract structured data using parse method
            invoice_data = await self.client.beta.chat.completions.parse(
                model=self.model_config['deployment'],
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured data from invoices. Extract the data according to the provided schema."
                    },
                    {
                        "role": "user",
                        "content": f"Extract the invoice data from this markdown content:\n\n{content}"
                    }
                ],
                response_format=InvoiceModel
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Run {run_number} completed in {duration:.2f} seconds")
            
            # Convert the Pydantic model to a dict
            result = invoice_data.choices[0].message.parsed.model_dump()
            logger.info(f"Response: {json.dumps(result, indent=2, cls=DateEncoder)}")
            
            return result
        except Exception as e:
            logger.error(f"Error during API call for Run {run_number}: {str(e)}", exc_info=True)
            return None

class ExtractorFactory:
    @staticmethod
    def create_extractor(method: str, model_config: dict) -> BaseExtractor:
        if method == "json_mode":
            return JsonModeExtractor(model_config)
        elif method == "instructor":
            return InstructorExtractor(model_config)
        elif method == "structured_output":
            return StructuredOutputExtractor(model_config)
        else:
            raise ValueError(f"Unknown extraction method: {method}") 