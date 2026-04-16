#!/usr/bin/env bash
set -euo pipefail

# Step 03: Provision Azure resources required for the lab.
# Resources created:
# - Storage Account + Blob container
# - Azure AI Search service
# - Azure OpenAI account + model deployment
# - Azure AI Services account (used for Content Understanding endpoint/key)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"

# Ensure resource group exists before provisioning resources.
if [[ "$(az group exists --name "${AZ_RESOURCE_GROUP}")" != "true" ]]; then
  echo "ERROR: Resource group does not exist: ${AZ_RESOURCE_GROUP}"
  echo "Run 02-create-resource-group.sh first."
  exit 1
fi

# Create Storage Account if missing.
if az storage account show --name "${AZ_STORAGE_ACCOUNT_NAME}" --resource-group "${AZ_RESOURCE_GROUP}" >/dev/null 2>&1; then
  echo "Storage account already exists: ${AZ_STORAGE_ACCOUNT_NAME}"
else
  echo "Creating storage account: ${AZ_STORAGE_ACCOUNT_NAME}"
  az storage account create \
    --name "${AZ_STORAGE_ACCOUNT_NAME}" \
    --resource-group "${AZ_RESOURCE_GROUP}" \
    --location "${AZ_LOCATION}" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --min-tls-version TLS1_2 \
    --allow-blob-public-access false \
    --output table
fi

# Create Blob container.
STORAGE_KEY="$(az storage account keys list --resource-group "${AZ_RESOURCE_GROUP}" --account-name "${AZ_STORAGE_ACCOUNT_NAME}" --query "[0].value" -o tsv)"
az storage container create \
  --name "${AZ_STORAGE_CONTAINER_NAME}" \
  --account-name "${AZ_STORAGE_ACCOUNT_NAME}" \
  --account-key "${STORAGE_KEY}" \
  --output table >/dev/null

echo "Blob container ensured: ${AZ_STORAGE_CONTAINER_NAME}"

# Create Azure AI Search service if missing.
if az search service show --name "${AZ_SEARCH_SERVICE_NAME}" --resource-group "${AZ_RESOURCE_GROUP}" >/dev/null 2>&1; then
  echo "AI Search service already exists: ${AZ_SEARCH_SERVICE_NAME}"
else
  echo "Creating AI Search service: ${AZ_SEARCH_SERVICE_NAME}"
  az search service create \
    --name "${AZ_SEARCH_SERVICE_NAME}" \
    --resource-group "${AZ_RESOURCE_GROUP}" \
    --location "${AZ_LOCATION}" \
    --sku basic \
    --partition-count 1 \
    --replica-count 1 \
    --output table
fi

# Create Azure OpenAI account if missing.
if az cognitiveservices account show --name "${AZ_OPENAI_ACCOUNT_NAME}" --resource-group "${AZ_RESOURCE_GROUP}" >/dev/null 2>&1; then
  echo "Azure OpenAI account already exists: ${AZ_OPENAI_ACCOUNT_NAME}"
else
  echo "Creating Azure OpenAI account: ${AZ_OPENAI_ACCOUNT_NAME}"
  az cognitiveservices account create \
    --name "${AZ_OPENAI_ACCOUNT_NAME}" \
    --resource-group "${AZ_RESOURCE_GROUP}" \
    --location "${AZ_OPENAI_LOCATION}" \
    --kind OpenAI \
    --sku S0 \
    --yes \
    --output table
fi

# Create Azure AI Services account for Content Understanding if missing.
if az cognitiveservices account show --name "${AZ_AISERVICES_ACCOUNT_NAME}" --resource-group "${AZ_RESOURCE_GROUP}" >/dev/null 2>&1; then
  echo "Azure AI Services account already exists: ${AZ_AISERVICES_ACCOUNT_NAME}"
else
  echo "Creating Azure AI Services account: ${AZ_AISERVICES_ACCOUNT_NAME}"
  az cognitiveservices account create \
    --name "${AZ_AISERVICES_ACCOUNT_NAME}" \
    --resource-group "${AZ_RESOURCE_GROUP}" \
    --location "${AZ_LOCATION}" \
    --kind AIServices \
    --sku S0 \
    --yes \
    --output table
fi

# Create Azure OpenAI model deployment (idempotent check).
if az cognitiveservices account deployment show \
  --name "${AZ_OPENAI_ACCOUNT_NAME}" \
  --resource-group "${AZ_RESOURCE_GROUP}" \
  --deployment-name "${AZ_OPENAI_DEPLOYMENT_NAME}" >/dev/null 2>&1; then
  echo "OpenAI deployment already exists: ${AZ_OPENAI_DEPLOYMENT_NAME}"
else
  echo "Creating OpenAI deployment: ${AZ_OPENAI_DEPLOYMENT_NAME}"
  set +e
  az cognitiveservices account deployment create \
    --name "${AZ_OPENAI_ACCOUNT_NAME}" \
    --resource-group "${AZ_RESOURCE_GROUP}" \
    --deployment-name "${AZ_OPENAI_DEPLOYMENT_NAME}" \
    --model-name "${AZ_OPENAI_MODEL_NAME}" \
    --model-version "${AZ_OPENAI_MODEL_VERSION}" \
    --model-format OpenAI \
    --sku-name "${AZ_OPENAI_DEPLOYMENT_SKU_NAME}" \
    --sku-capacity "${AZ_OPENAI_DEPLOYMENT_SKU_CAPACITY}" \
    --output table
  DEPLOY_EXIT_CODE=$?
  set -e

  if [[ ${DEPLOY_EXIT_CODE} -ne 0 ]]; then
    echo "WARNING: OpenAI deployment creation failed."
    echo "This is usually quota/model availability related."
    echo "Update model/version/region in 00-variables.sh and retry this step."
  fi
fi

echo "Step 03 complete."
