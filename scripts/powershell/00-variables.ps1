# Shared configuration for PowerShell lab provisioning scripts.
#
# Usage:
#   1) Update values below for your environment.
#   2) Run scripts in numeric order: 01 -> 04.

# Subscription (optional): leave empty to use current `az account show` context.
$env:AZ_SUBSCRIPTION_ID = ""

# Core deployment settings.
$env:AZ_LOCATION = "eastus"
$env:AZ_OPENAI_LOCATION = "eastus2"
$env:AZ_RESOURCE_GROUP = "rg-tmnas-innovation-hub-lab"

# IMPORTANT:
# - Use a unique suffix to avoid global naming conflicts.
# - Lowercase letters and numbers only are safest.
$env:AZ_LAB_SUFFIX = "001"

# Resource names used by this lab.
$env:AZ_STORAGE_ACCOUNT_NAME = "sttmnashub$($env:AZ_LAB_SUFFIX)"
$env:AZ_STORAGE_CONTAINER_NAME = "documents"
$env:AZ_SEARCH_SERVICE_NAME = "srch-tmnas-$($env:AZ_LAB_SUFFIX)"
$env:AZ_OPENAI_ACCOUNT_NAME = "oai-tmnas-$($env:AZ_LAB_SUFFIX)"
$env:AZ_AISERVICES_ACCOUNT_NAME = "ais-tmnas-$($env:AZ_LAB_SUFFIX)"

# Azure OpenAI deployment settings.
# Update model version if your subscription/region requires a different one.
$env:AZ_OPENAI_DEPLOYMENT_NAME = "gpt-4o"
$env:AZ_OPENAI_MODEL_NAME = "gpt-4o"
$env:AZ_OPENAI_MODEL_VERSION = "2024-11-20"
$env:AZ_OPENAI_DEPLOYMENT_SKU_NAME = "Standard"
$env:AZ_OPENAI_DEPLOYMENT_SKU_CAPACITY = "10"

# App-level settings written to .env.
$env:APP_NAME = "Doc-Review PoC"
$env:APP_VERSION = "0.1.0"
