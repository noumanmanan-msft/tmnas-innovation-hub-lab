#!/usr/bin/env bash
# Shared configuration for Bash lab provisioning scripts.
#
# Usage:
#   1) Update values below for your environment.
#   2) Run scripts in numeric order: 01 -> 04.

# Subscription (optional): leave empty to use current `az account show` context.
export AZ_SUBSCRIPTION_ID=""

# Core deployment settings.
export AZ_LOCATION="eastus"
export AZ_OPENAI_LOCATION="eastus2"
export AZ_RESOURCE_GROUP="rg-tmnas-innovation-hub-lab"

# IMPORTANT:
# - Use a unique suffix to avoid global naming conflicts.
# - Lowercase letters and numbers only are safest.
export AZ_LAB_SUFFIX="001"

# Resource names used by this lab.
export AZ_STORAGE_ACCOUNT_NAME="sttmnashub${AZ_LAB_SUFFIX}"
export AZ_STORAGE_CONTAINER_NAME="documents"
export AZ_SEARCH_SERVICE_NAME="srch-tmnas-${AZ_LAB_SUFFIX}"
export AZ_OPENAI_ACCOUNT_NAME="oai-tmnas-${AZ_LAB_SUFFIX}"
export AZ_AISERVICES_ACCOUNT_NAME="ais-tmnas-${AZ_LAB_SUFFIX}"

# Azure OpenAI deployment settings.
# Update model version if your subscription/region requires a different one.
export AZ_OPENAI_DEPLOYMENT_NAME="gpt-4o"
export AZ_OPENAI_MODEL_NAME="gpt-4o"
export AZ_OPENAI_MODEL_VERSION="2024-11-20"
export AZ_OPENAI_DEPLOYMENT_SKU_NAME="Standard"
export AZ_OPENAI_DEPLOYMENT_SKU_CAPACITY="10"

# App-level settings written to .env.
export APP_NAME="Doc-Review PoC"
export APP_VERSION="0.1.0"
