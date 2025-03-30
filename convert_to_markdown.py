import os
import logging
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentContentFormat

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

endpoint = os.getenv("di_enpoint")
key = os.getenv("di_key")


def analyze_document(endpoint, key, doc_bytes):
    logger.info("Starting document analysis")
    document_intelligence_client = DocumentIntelligenceClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    logger.info("Sending document to Azure Document Intelligence")
    poller = document_intelligence_client.begin_analyze_document(
        "prebuilt-layout", AnalyzeDocumentRequest(bytes_source=doc_bytes), output_content_format=DocumentContentFormat.MARKDOWN
    )
    result = poller.result()
    logger.info("Document analysis completed successfully")
    # Access the markdown content through the content property
    return result.content

def read_docs():
    logger.info("Starting to read documents from docs directory")
    docs_bytes = {}
    docs_dir = "docs"
    
    # Check if directory exists
    if not os.path.exists(docs_dir):
        logger.warning(f"Directory {docs_dir} does not exist")
        return docs_bytes
        
    # Iterate through all files in docs directory
    for filename in os.listdir(docs_dir):
        file_path = os.path.join(docs_dir, filename)
        
        # Read file as bytes if it's a file (not a directory)
        if os.path.isfile(file_path):
            logger.info(f"Reading file: {filename}")
            with open(file_path, 'rb') as f:
                docs_bytes[filename] = f.read()
    
    logger.info(f"Found {len(docs_bytes)} documents to process")
    return docs_bytes

def save_to_outputs(filename, content):
    logger.info("Saving content to outputs directory")
    output_dir = "outputs"
    
    # Create outputs directory if it doesn't exist
    if not os.path.exists(output_dir):
        logger.info("Creating outputs directory")
        os.makedirs(output_dir)
    
    # Create output filename by replacing extension with .md
    output_filename = os.path.splitext(filename)[0] + '.md'
    output_path = os.path.join(output_dir, output_filename)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Successfully saved content to {output_path}")
    except Exception as e:
        logger.error(f"Error saving file {output_path}: {str(e)}", exc_info=True)


if __name__ == "__main__":
    logger.info("Starting document processing")
    # Read all documents from docs directory
    documents = read_docs()
    
    # Process each document
    for filename, doc_bytes in documents.items():
        try:
            logger.info(f"Processing document: {filename}")
            result = analyze_document(endpoint, key, doc_bytes)
            logger.info(f"Successfully analyzed {filename}")
            
            save_to_outputs(filename, result)

        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}", exc_info=True)
    
    logger.info("Document processing completed")




