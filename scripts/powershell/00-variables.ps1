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
$env:AZ_FOUNDRY_PROJECT_NAME = "default-project"
$env:AZ_FOUNDRY_PROJECT_API_VERSION = "2026-01-15-preview"
$env:AZ_CU_ANALYZER_ID = "docreviewanalyzer"

# Content Understanding defaults use Foundry-side model deployments.
$env:AZ_CU_LLM_DEPLOYMENT_NAME = "cu-gpt-4-1"
$env:AZ_CU_LLM_MODEL_NAME = "gpt-4.1"
$env:AZ_CU_LLM_MODEL_VERSION = "2025-04-14"
$env:AZ_CU_LLM_DEPLOYMENT_SKU_NAME = "Standard"
$env:AZ_CU_LLM_DEPLOYMENT_SKU_CAPACITY = "10"
$env:AZ_CU_EMBEDDING_DEPLOYMENT_NAME = "cu-text-embedding-3-large"
$env:AZ_CU_EMBEDDING_MODEL_NAME = "text-embedding-3-large"
$env:AZ_CU_EMBEDDING_MODEL_VERSION = "1"
$env:AZ_CU_EMBEDDING_DEPLOYMENT_SKU_NAME = "Standard"
$env:AZ_CU_EMBEDDING_DEPLOYMENT_SKU_CAPACITY = "10"

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
