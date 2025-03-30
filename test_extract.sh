#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to get model names from config.json
get_model_names() {
    # Extract model names from config.json using jq
    # Returns them as a space-separated string
    jq -r '.models | keys | join(" ")' config.json
}

# Function to get extractors from config.json
get_extractors() {
    # Extract extractor names from config.json using jq
    # Returns them as a space-separated string
    jq -r '.extractors | if type == "array" then join(" ") else keys | join(" ") end' config.json
}

# Get model names and extractors from config
MODELS=$(get_model_names)
EXTRACTORS=$(get_extractors)

# Convert space-separated strings to arrays
IFS=' ' read -ra MODEL_ARRAY <<< "$MODELS"
IFS=' ' read -ra EXTRACTOR_ARRAY <<< "$EXTRACTORS"

# Get first model and extractor as defaults
DEFAULT_MODEL=${MODEL_ARRAY[0]}
DEFAULT_EXTRACTOR=${EXTRACTOR_ARRAY[0]}

echo -e "${BLUE}Running tests with models:${NC} ${MODELS}"
echo -e "${BLUE}Running tests with extractors:${NC} ${EXTRACTORS}"
echo -e "${BLUE}Using default model:${NC} ${DEFAULT_MODEL}"
echo -e "${BLUE}Using default extractor:${NC} ${DEFAULT_EXTRACTOR}"
echo

# Test 1: Run with all defaults (-y flag)
echo -e "${GREEN}Test 1: Running with all defaults (-y flag)${NC}"
python extract.py -y

# Test 2: Run with specific model and extractor
echo -e "\n${GREEN}Test 2: Running with specific model and extractor${NC}"
python extract.py -y --model "${DEFAULT_MODEL}" --extractor "${DEFAULT_EXTRACTOR}"

# Test 3: Run with multiple iterations
echo -e "\n${GREEN}Test 3: Running with multiple iterations (-n flag)${NC}"
python extract.py -y -n 3

# Test 4: Run with all parameters specified
echo -e "\n${GREEN}Test 4: Running with all parameters specified${NC}"
python extract.py -y \
    --doc "invoice.md" \
    --schema "invoice.json" \
    --output-schema "invoice.json" \
    --model "${DEFAULT_MODEL}" \
    --extractor "${DEFAULT_EXTRACTOR}" \
    -n 2

echo -e "\n${GREEN}All tests completed!${NC}" 

# Same as 4 but o3-mini
echo -e "\n${GREEN}Running tests with o3-mini${NC}"
python extract.py -y \
    --doc "invoice.md" \
    --schema "invoice.json" \
    --output-schema "invoice.json" \
    --model "o3-mini" --extractor "instructor" -n 2