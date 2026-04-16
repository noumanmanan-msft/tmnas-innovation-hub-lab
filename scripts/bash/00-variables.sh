#!/usr/bin/env bash
# Shared configuration for Bash lab provisioning scripts.
#
# Usage:
#   1) Update values below for your environment.
#   2) Run scripts in numeric order: 01 -> 04.

# Subscription (optional): leave empty to use current `az account show` context.
# Runtime overrides are supported, e.g.:
#   AZ_SUBSCRIPTION_ID="..." AZ_RESOURCE_GROUP="..." bash scripts/bash/01-login.sh
export AZ_SUBSCRIPTION_ID="${AZ_SUBSCRIPTION_ID:-}"

# Core deployment settings.
export AZ_LOCATION="${AZ_LOCATION:-eastus}"
export AZ_OPENAI_LOCATION="${AZ_OPENAI_LOCATION:-eastus2}"
export AZ_RESOURCE_GROUP="${AZ_RESOURCE_GROUP:-rg-tmnas-innovation-hub-lab}"

# IMPORTANT:
# - Use a unique suffix to avoid global naming conflicts.
# - Lowercase letters and numbers only are safest.
export AZ_LAB_SUFFIX="${AZ_LAB_SUFFIX:-001}"

# Resource names used by this lab.
export AZ_STORAGE_ACCOUNT_NAME="${AZ_STORAGE_ACCOUNT_NAME:-sttmnashub${AZ_LAB_SUFFIX}}"
export AZ_STORAGE_CONTAINER_NAME="${AZ_STORAGE_CONTAINER_NAME:-documents}"
export AZ_SEARCH_SERVICE_NAME="${AZ_SEARCH_SERVICE_NAME:-srch-tmnas-${AZ_LAB_SUFFIX}}"
export AZ_OPENAI_ACCOUNT_NAME="${AZ_OPENAI_ACCOUNT_NAME:-oai-tmnas-${AZ_LAB_SUFFIX}}"
export AZ_AISERVICES_ACCOUNT_NAME="${AZ_AISERVICES_ACCOUNT_NAME:-ais-tmnas-${AZ_LAB_SUFFIX}}"
export AZ_FOUNDRY_PROJECT_NAME="${AZ_FOUNDRY_PROJECT_NAME:-default-project}"
export AZ_FOUNDRY_PROJECT_API_VERSION="${AZ_FOUNDRY_PROJECT_API_VERSION:-2026-01-15-preview}"
export AZ_CU_ANALYZER_ID="${AZ_CU_ANALYZER_ID:-docreviewanalyzer}"

# Content Understanding defaults use Foundry-side model deployments.
export AZ_CU_LLM_DEPLOYMENT_NAME="${AZ_CU_LLM_DEPLOYMENT_NAME:-cu-gpt-4-1}"
export AZ_CU_LLM_MODEL_NAME="${AZ_CU_LLM_MODEL_NAME:-gpt-4.1}"
export AZ_CU_LLM_MODEL_VERSION="${AZ_CU_LLM_MODEL_VERSION:-2025-04-14}"
export AZ_CU_LLM_DEPLOYMENT_SKU_NAME="${AZ_CU_LLM_DEPLOYMENT_SKU_NAME:-Standard}"
export AZ_CU_LLM_DEPLOYMENT_SKU_CAPACITY="${AZ_CU_LLM_DEPLOYMENT_SKU_CAPACITY:-10}"
export AZ_CU_EMBEDDING_DEPLOYMENT_NAME="${AZ_CU_EMBEDDING_DEPLOYMENT_NAME:-cu-text-embedding-3-large}"
export AZ_CU_EMBEDDING_MODEL_NAME="${AZ_CU_EMBEDDING_MODEL_NAME:-text-embedding-3-large}"
export AZ_CU_EMBEDDING_MODEL_VERSION="${AZ_CU_EMBEDDING_MODEL_VERSION:-1}"
export AZ_CU_EMBEDDING_DEPLOYMENT_SKU_NAME="${AZ_CU_EMBEDDING_DEPLOYMENT_SKU_NAME:-Standard}"
export AZ_CU_EMBEDDING_DEPLOYMENT_SKU_CAPACITY="${AZ_CU_EMBEDDING_DEPLOYMENT_SKU_CAPACITY:-10}"

# Azure OpenAI deployment settings.
# Update model version if your subscription/region requires a different one.
export AZ_OPENAI_DEPLOYMENT_NAME="${AZ_OPENAI_DEPLOYMENT_NAME:-gpt-4o}"
export AZ_OPENAI_MODEL_NAME="${AZ_OPENAI_MODEL_NAME:-gpt-4o}"
export AZ_OPENAI_MODEL_VERSION="${AZ_OPENAI_MODEL_VERSION:-2024-11-20}"
export AZ_OPENAI_DEPLOYMENT_SKU_NAME="${AZ_OPENAI_DEPLOYMENT_SKU_NAME:-Standard}"
export AZ_OPENAI_DEPLOYMENT_SKU_CAPACITY="${AZ_OPENAI_DEPLOYMENT_SKU_CAPACITY:-10}"

# App-level settings written to .env.
export APP_NAME="${APP_NAME:-Doc-Review PoC}"
export APP_VERSION="${APP_VERSION:-0.1.0}"
