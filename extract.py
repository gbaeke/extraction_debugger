import os
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import print as rprint
from openai import AsyncAzureOpenAI
import json
from dotenv import load_dotenv
import logging
from datetime import datetime
from rich.table import Table
from statistics import mode, mean
import asyncio
from asyncio import Semaphore
from extractors import ExtractorFactory
import argparse

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

openai_key = os.getenv("openai_key")
openai_endpoint = os.getenv("openai_endpoint")
openai_api_version = os.getenv("openai_api_version")

# Initialize Rich console
console = Console()

def select_file(config):
    """Select a file from the outputs directory using Rich."""
    outputs_dir = "outputs"
    files = [f for f in os.listdir(outputs_dir) if f.endswith('.md')]
    
    if not files:
        console.print("[red]No markdown files found in outputs directory![/red]")
        return None
    
    # If there's only one file, automatically select it
    if len(files) == 1:
        console.print(f"\n[green]Only one file found:[/green] {files[0]}")
        return os.path.join(outputs_dir, files[0])
    
    # Check for default file in config
    default_file = config.get('default_doc')
    if default_file and default_file in files:
        console.print(f"\n[green]Using default file:[/green] {default_file}")
        return os.path.join(outputs_dir, default_file)
    
    console.print("\n[bold blue]Available files:[/bold blue]")
    for idx, file in enumerate(files, 1):
        is_default = file == default_file
        default_marker = " (default)" if is_default else ""
        console.print(f"{idx}. {file}{default_marker}")
    
    while True:
        try:
            default_idx = files.index(default_file) + 1 if default_file in files else 1
            choice = Prompt.ask("\n[bold green]Select a file number[/bold green]", default=str(default_idx))
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                return os.path.join(outputs_dir, files[idx])
            else:
                console.print("[red]Invalid selection. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")

def select_schema(config):
    """Select a schema file from the schemas directory using Rich."""
    schemas_dir = "schemas"
    files = [f for f in os.listdir(schemas_dir) if f.endswith('.json')]
    
    if not files:
        console.print("[red]No schema files found in schemas directory![/red]")
        return None
    
    # If there's only one file, automatically select it
    if len(files) == 1:
        console.print(f"\n[green]Only one schema found:[/green] {files[0]}")
        return os.path.join(schemas_dir, files[0])
    
    # Check for default schema in config
    default_schema = config.get('default_schema')
    if default_schema and default_schema in files:
        console.print(f"\n[green]Using default schema:[/green] {default_schema}")
        return os.path.join(schemas_dir, default_schema)
    
    console.print("\n[bold blue]Available schemas:[/bold blue]")
    for idx, file in enumerate(files, 1):
        is_default = file == default_schema
        default_marker = " (default)" if is_default else ""
        console.print(f"{idx}. {file}{default_marker}")
    
    while True:
        try:
            default_idx = files.index(default_schema) + 1 if default_schema in files else 1
            choice = Prompt.ask("\n[bold green]Select a schema number[/bold green]", default=str(default_idx))
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                return os.path.join(schemas_dir, files[idx])
            else:
                console.print("[red]Invalid selection. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")

def select_output_schema(config):
    """Select an output schema file from the output_schemas directory using Rich."""
    schemas_dir = "output_schemas"
    files = [f for f in os.listdir(schemas_dir) if f.endswith('.json')]
    
    if not files:
        console.print("[red]No output schema files found in output_schemas directory![/red]")
        return None
    
    # If there's only one file, automatically select it
    if len(files) == 1:
        console.print(f"\n[green]Only one output schema found:[/green] {files[0]}")
        return os.path.join(schemas_dir, files[0])
    
    # Check for default output schema in config
    default_schema = config.get('default_output_schema')
    if default_schema and default_schema in files:
        console.print(f"\n[green]Using default output schema:[/green] {default_schema}")
        return os.path.join(schemas_dir, default_schema)
    
    console.print("\n[bold blue]Available output schemas:[/bold blue]")
    for idx, file in enumerate(files, 1):
        is_default = file == default_schema
        default_marker = " (default)" if is_default else ""
        console.print(f"{idx}. {file}{default_marker}")
    
    while True:
        try:
            default_idx = files.index(default_schema) + 1 if default_schema in files else 1
            choice = Prompt.ask("\n[bold green]Select an output schema number[/bold green]", default=str(default_idx))
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                return os.path.join(schemas_dir, files[idx])
            else:
                console.print("[red]Invalid selection. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")

def get_number_of_runs():
    """Get the number of runs from the user."""
    while True:
        try:
            runs = Prompt.ask("\n[bold green]How many runs would you like to perform?[/bold green]", default="1")
            runs = int(runs)
            if runs > 0:
                return runs
            else:
                console.print("[red]Please enter a positive number.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")

def load_config():
    """Load and validate the configuration file."""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if 'models' not in config:
            console.print("[red]Error: config.json must contain a 'models' section[/red]")
            return None
        
        return config
    except FileNotFoundError:
        console.print("[red]Error: config.json not found[/red]")
        return None
    except json.JSONDecodeError:
        console.print("[red]Error: config.json is not valid JSON[/red]")
        return None

def select_model(config):
    """Select a model from the configuration."""
    models = list(config['models'].keys())
    
    if not models:
        console.print("[red]No models found in configuration![/red]")
        return None
    
    # If there's only one model, automatically select it
    if len(models) == 1:
        console.print(f"\n[green]Only one model found:[/green] {models[0]}")
        return models[0]
    
    # Check for default model in config
    default_model = config.get('default_model')
    if default_model and default_model in models:
        console.print(f"\n[green]Using default model:[/green] {default_model}")
        return default_model
    
    console.print("\n[bold blue]Available models:[/bold blue]")
    for idx, model in enumerate(models, 1):
        description = config['models'][model].get('description', '')
        is_default = model == default_model
        default_marker = " (default)" if is_default else ""
        console.print(f"{idx}. {model}{default_marker} - {description}")
    
    while True:
        try:
            default_idx = models.index(default_model) + 1 if default_model in models else 1
            choice = Prompt.ask("\n[bold green]Select a model number[/bold green]", default=str(default_idx))
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                return models[idx]
            else:
                console.print("[red]Invalid selection. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")

def select_extractor(config):
    """Select an extractor from the configuration."""
    # Get extractors list from config, ensuring it's a list
    extractors = config.get('extractors', [])
    if isinstance(extractors, dict):
        extractors = list(extractors.keys())
    
    if not extractors:
        console.print("[red]No extractors found in configuration![/red]")
        return None
    
    # If there's only one extractor, automatically select it
    if len(extractors) == 1:
        console.print(f"\n[green]Only one extractor found:[/green] {extractors[0]}")
        return extractors[0]
    
    # Check for default extractor in config
    default_extractor = config.get('default_extractor')
    if default_extractor and default_extractor in extractors:
        console.print(f"\n[green]Using default extractor:[/green] {default_extractor}")
        return default_extractor
    
    console.print("\n[bold blue]Available extractors:[/bold blue]")
    for idx, extractor in enumerate(extractors, 1):
        is_default = extractor == default_extractor
        default_marker = " (default)" if is_default else ""
        console.print(f"{idx}. {extractor}{default_marker}")

    # Print warning for structured output mode
    if "structured_output" in extractors:
        console.print("\n[red]Structured output mode is experimental and likely to fail[/red]")
    
    while True:
        try:
            default_idx = extractors.index(default_extractor) + 1 if default_extractor in extractors else 1
            choice = Prompt.ask("\n[bold green]Select an extractor number[/bold green]", default=str(default_idx))
            idx = int(choice) - 1
            if 0 <= idx < len(extractors):
                return extractors[idx]
            else:
                console.print("[red]Invalid selection. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")

def display_config(config, selected_model, selected_extractor):
    """Display the current configuration."""
    model_config = config['models'][selected_model]
    
    config_text = f"""
    Selected Model: {selected_model}
    Description: {model_config.get('description', 'N/A')}
    Temperature: {model_config.get('temperature', 'Not set')}
    Selected Extractor: {selected_extractor}
    """
    
    console.print(Panel.fit(config_text, title="Current Configuration", border_style="blue"))
    
    return Confirm.ask("\n[bold green]Proceed with this configuration?[/bold green]", default=True)

async def extract_currency_async(file_path, schema_path, semaphore, run_number, model_config, extraction_method="json_mode"):
    """Extract currency information using OpenAI API with semaphore for rate limiting."""
    async with semaphore:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Read selected schema
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        try:
            # Create extractor using factory
            extractor = ExtractorFactory.create_extractor(extraction_method, model_config)
            
            # Perform extraction
            result = await extractor.extract(content, schema, run_number)
            return result
        except Exception as e:
            logger.error(f"Error during extraction for Run {run_number}: {str(e)}", exc_info=True)
            return None

async def process_runs(file_path, schema_path, num_runs, model_config, extraction_method="json_mode"):
    """Process multiple runs in parallel with a semaphore."""
    semaphore = Semaphore(5)  # Limit to 5 concurrent requests
    tasks = []
    
    for run in range(num_runs):
        console.print(f"\n[bold green]Starting Run {run + 1}/{num_runs}[/bold green]")
        task = asyncio.create_task(extract_currency_async(file_path, schema_path, semaphore, run + 1, model_config, extraction_method))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]

def display_results(results, output_schema_path):
    """Display individual results and summary based on the selected output schema."""
    # Read the output schema
    with open(output_schema_path, 'r', encoding='utf-8') as f:
        output_schema = json.load(f)
    
    # Create a table for individual results
    table = Table(title="Individual Results")
    
    # Add run number as first column
    table.add_column("Run", style="bold magenta")
    
    # Add columns based on the output schema fields
    for field in output_schema['fields']:
        table.add_column(field['description'], style="cyan")
    
    # Add rows with data from results
    for idx, result in enumerate(results, 1):
        row_data = [str(idx)]  # Start with run number
        for field in output_schema['fields']:
            # Try different variations of the field name
            field_name = field['name']
            # Try exact match first
            value = result.get(field_name)
            if value is None:
                # Try with spaces replaced by underscores
                value = result.get(field_name.replace(' ', '_'))
            if value is None:
                # Try with lowercase
                value = result.get(field_name.lower())
            if value is None:
                # Try with lowercase and spaces replaced by underscores
                value = result.get(field_name.lower().replace(' ', '_'))
            if value is None:
                value = 'N/A'
            row_data.append(str(value))
        table.add_row(*row_data)
    
    console.print(table)
    
    # Calculate summary statistics for numeric fields
    summary_text = f"Total Runs: {len(results)}\n"
    
    for field in output_schema['fields']:
        field_name = field['name']
        # Try different variations of the field name
        values = []
        for result in results:
            value = result.get(field_name)
            if value is None:
                value = result.get(field_name.replace(' ', '_'))
            if value is None:
                value = result.get(field_name.lower())
            if value is None:
                value = result.get(field_name.lower().replace(' ', '_'))
            values.append(value)
        
        # Only calculate statistics for numeric values
        numeric_values = [v for v in values if isinstance(v, (int, float))]
        if numeric_values:
            try:
                avg = mean(numeric_values)
                summary_text += f"Average {field['description']}: {avg:.2f}\n"
            except:
                pass
        
        # For non-numeric fields, show most common value
        try:
            most_common = mode(values)
            summary_text += f"Most Common {field['description']}: {most_common}\n"
        except:
            pass
    
    console.print(Panel.fit(summary_text, title="Summary Statistics", border_style="blue"))

def validate_defaults(config):
    """Validate that all required defaults are set in the config."""
    required_defaults = ['default_doc', 'default_schema', 'default_output_schema', 'default_model', 'default_extractor']
    missing_defaults = [default for default in required_defaults if default not in config]
    
    if missing_defaults:
        console.print("[red]Missing required defaults in config.json:[/red]")
        for default in missing_defaults:
            console.print(f"  - {default}")
        return False
    return True

def get_default_paths(config):
    """Get default paths based on config."""
    outputs_dir = "outputs"
    schemas_dir = "schemas"
    output_schemas_dir = "output_schemas"
    
    file_path = os.path.join(outputs_dir, config['default_doc'])
    schema_path = os.path.join(schemas_dir, config['default_schema'])
    output_schema_path = os.path.join(output_schemas_dir, config['default_output_schema'])
    
    # Validate that all files exist
    if not os.path.exists(file_path):
        console.print(f"[red]Default document not found: {file_path}[/red]")
        return None, None, None
    if not os.path.exists(schema_path):
        console.print(f"[red]Default schema not found: {schema_path}[/red]")
        return None, None, None
    if not os.path.exists(output_schema_path):
        console.print(f"[red]Default output schema not found: {output_schema_path}[/red]")
        return None, None, None
    
    return file_path, schema_path, output_schema_path

def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Extract fields from documents using AI')
        parser.add_argument('-y', '--yes', action='store_true', help='Run with all defaults without prompting')
        parser.add_argument('-n', '--num-runs', type=int, help='Number of runs to perform')
        parser.add_argument('--doc', help='Default document to use')
        parser.add_argument('--schema', help='Default schema to use')
        parser.add_argument('--output-schema', help='Default output schema to use')
        parser.add_argument('--model', help='Default model to use')
        parser.add_argument('--extractor', help='Default extractor to use')
        args = parser.parse_args()
        
        console.print(Panel.fit("[bold blue]Currency Extraction Tool[/bold blue]", border_style="blue"))
        
        # Load configuration
        config = load_config()
        if not config:
            return
        
        # Override config defaults with command line arguments
        if args.doc:
            config['default_doc'] = args.doc
        if args.schema:
            config['default_schema'] = args.schema
        if args.output_schema:
            config['default_output_schema'] = args.output_schema
        if args.model:
            config['default_model'] = args.model
        if args.extractor:
            config['default_extractor'] = args.extractor
        
        # If -y flag is used, validate all defaults
        if args.yes:
            if not validate_defaults(config):
                console.print("[red]Cannot run with defaults: missing configuration[/red]")
                return
            
            file_path, schema_path, output_schema_path = get_default_paths(config)
            if not all([file_path, schema_path, output_schema_path]):
                console.print("[red]Cannot run with defaults: missing files[/red]")
                return
            
            selected_model = config['default_model']
            selected_extractor = config['default_extractor']
            num_runs = args.num_runs if args.num_runs is not None else 1  # Use -n value or default to 1
            
            console.print("[green]Running with all defaults:[/green]")
            console.print(f"Document: {os.path.basename(file_path)}")
            console.print(f"Schema: {os.path.basename(schema_path)}")
            console.print(f"Output Schema: {os.path.basename(output_schema_path)}")
            console.print(f"Model: {selected_model}")
            console.print(f"Extractor: {selected_extractor}")
            console.print(f"Number of runs: {num_runs}")
            
            # Perform runs in parallel
            with console.status("[bold green]Processing runs in parallel...[/bold green]"):
                results = asyncio.run(process_runs(file_path, schema_path, num_runs, config['models'][selected_model], selected_extractor))
            
            if results:
                display_results(results, output_schema_path)
            else:
                console.print("[red]No successful results to display.[/red]")
            return
        
        # Interactive mode
        selected_model = select_model(config)
        if not selected_model:
            return
        
        selected_extractor = select_extractor(config)
        if not selected_extractor:
            return
        
        if not display_config(config, selected_model, selected_extractor):
            console.print("[yellow]Operation cancelled by user[/yellow]")
            return
        
        file_path = select_file(config)
        if not file_path:
            return
        
        console.print(f"\n[green]Selected file:[/green] {file_path}")
        
        schema_path = select_schema(config)
        if not schema_path:
            return
        
        console.print(f"\n[green]Selected schema:[/green] {schema_path}")
        
        output_schema_path = select_output_schema(config)
        if not output_schema_path:
            return
        
        console.print(f"\n[green]Selected output schema:[/green] {output_schema_path}")
        
        # Use -n value if provided, otherwise prompt
        num_runs = args.num_runs if args.num_runs is not None else get_number_of_runs()
        
        with console.status("[bold green]Processing runs in parallel...[/bold green]"):
            results = asyncio.run(process_runs(file_path, schema_path, num_runs, config['models'][selected_model], selected_extractor))
        
        if results:
            display_results(results, output_schema_path)
        else:
            console.print("[red]No successful results to display.[/red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        return
    except Exception as e:
        console.print(f"\n[red]An error occurred: {str(e)}[/red]")
        return

if __name__ == "__main__":
    main()
