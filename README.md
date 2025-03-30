# Document Field Extraction Debugger

![Document Field Extraction Tool Architecture](image.png)
(Note: this tool is a command line tool. Image is just for illustration purposes.)

This tool helps you extract specific fields from documents (PDFs, etc.) using AI-powered extraction. It converts documents to markdown format first and then uses AI to identify and extract the required fields based on your schema definitions.

Extraction can be done in three ways:

1. OpenAI JSON mode
2. Instructor: see https://github.com/jxnl/instructor
3. OpenAI structured outputs (results may vary because this does not support all the features in a JSON schema like Instructor does)

Extractors are implemented as classes in `extractors.py` to add new extractors in the future.

Note that the JSON schema you define in `/schemas' is used as is in JSON mode. For instructor, the schema is converted to a Pydantic model on the fly.

## What is this?

This tool provides a workflow to:
1. Convert various document formats to markdown
2. Define the fields you want to extract using JSON schemas
3. Use AI to extract the specified fields from the documents
4. Output the extracted data in a structured format

## Requirements

- Python 3.x
- Required Python packages (install via `pip install -r requirements.txt`):
  - See requirements.txt for the complete list of dependencies
- Azure subscription with Azure OpenAI service and Document Intelligence service
  - see .env.example for the required environment variables in your .env file

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd extraction_debugger
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory and add the required environment variables:
```bash
cp .env.example .env
```

## Usage Steps

### 1. Prepare Documents
Place your documents (PDFs, etc.) in the `/docs` directory.

### 2. Define Extraction Schema
Create a JSON schema in the `/schemas` directory that defines the fields you want to extract. The schema should specify:
- Field names
- Field descriptions

Here is an example:

```json
{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "customer_name": {
            "type": "string",
            "description": "Customer name"
        },
        "total_amount": {
            "type": "number",
            "description": "Total amount"
        },
        "invoice_number": {
            "type": "string",
            "description": "Invoice number"
        },
        "due_date": {
            "type": "string",
            "description": "Due date",
            "format": "date"
        }
    },
    "required": ["customer_name", "total_amount", "invoice_number", "due_date"]
} 
```


### 3. Define Output Schema
Create a JSON schema in the `/output_schemas` directory that defines the structure of your output data. This schema should match the fields you want to extract.

Here is an example:

```json
{
    "fields": [
        {
            "name": "customer_name",
            "description": "Customer name"
        },
        {
            "name": "total_amount",
            "description": "Total amount"
        },
        {
            "name": "invoice_number",
            "description": "Invoice number"
        },
        {
            "name": "due_date", 
            "description": "Due date"
        }
    ]
}
```


### 4. Convert Documents
Run the document conversion script:
```bash
python convert_to_markdown.py
```
This will:
- Process all documents in the `/docs` directory
- Convert them to markdown format
- Save the output in the `/outputs` directory

### 5. Extract Fields
Run the extraction script:
```bash
python extract.py
```

The script will:
- Ask interactive questions about the extraction process
- Use AI to identify and extract the specified fields
- Output the results according to your output schema

You can specify multiple runs to see how consistent the results are.

### Configuration
You can configure the extraction process by creating a `config.json` file. This allows you to:
- Skip interactive questions
- Set specific parameters for the extraction
- Configure AI model settings

Example config.json:

```json
{
    "models": {
        "gpt-4o": {
            "deployment": "gpt-4o",
            "temperature": 0.0,
            "description": "gpt-4o model"
        },
        "o3-mini": {
            "deployment": "o3-mini",
            "description": "o3-mini Model"
        }
    },
    "extractors": {
        "instructor": {
            "description": "Uses instructor and function calling to extract data"
        },
        "json_mode": {
            "description": "Uses JSON mode to extract data"
        },
        "structured_output": {
            "description": "Uses structured output parsing to extract data"
        }
    },
    "default_extractor": "instructor",
    "default_model": "gpt-4o",
    "default_doc": "invoice.md",
    "default_schema": "invoice.json",
    "default_output_schema": "invoice.json"
} 
```

When you add a model, ensure the deployment name in config matches the deployment name of the model in the Azure OpenAI service.

If you want to remove structured output, you can do so by removing the "structured_output" entry in the `config.json` file.

Set the default to match the model name and extractor you want. The model name is the key in the `models` object, not the deployment name. The extractor is the key in the `extractors` object. Setting the default means you can just press enter when asked to select a model or extractor.


## Directory Structure

```
.
├── docs/               # Place your input documents here
├── schemas/           # Define your extraction schemas here
├── output_schemas/    # Define your output schemas here
├── outputs/           # Contains converted markdown files
├── convert_to_markdown.py
├── extract.py
└── config.json        # Optional configuration file
```

## Example

1. Place a PDF invoice in `/docs`
2. Create a schema in `/schemas` defining fields like "invoice_number", "total_amount", etc.
3. Create an output schema in `/output_schemas` matching your desired output format
4. Run `convert_to_markdown.py`
5. Run `extract.py`
6. Get your extracted fields in the specified output format

## Command line examples

Run interactively:

```bash
python extract.py
```

**Note:** if you want to choose files from a list, remove the defaults from config.json.

Use defaults in config and use -y and -n to get n outputs:

```bash
python extract.py -y -n 2
```


Ensure you have a config.json with defaults. Defaults can be overridden on command line as below. With -y and -n, you will not be asked questions and you get n outputs.

```bash
python extract.py -y --model "o3-mini" --extractor "instructor" -n 2
```

For all supported command line arguments, run:

```bash
python extract.py -h
```

