#!/usr/bin/env bash
set -euo pipefail

# Step 03: Provision Azure resources required for the lab.
# Resources created:
# - Storage Account + Blob container
# - Azure AI Search service
# - Azure OpenAI account + model deployment
# - Azure AI Services account + Foundry project + CU model deployments

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

# Grant the current signed-in user Blob data-plane rights so the local app can upload with DefaultAzureCredential.
CURRENT_USER_OBJECT_ID="$(az ad signed-in-user show --query id -o tsv)"
STORAGE_ACCOUNT_SCOPE="$(az storage account show --name "${AZ_STORAGE_ACCOUNT_NAME}" --resource-group "${AZ_RESOURCE_GROUP}" --query id -o tsv)"
HAS_BLOB_OWNER_ROLE="$(az role assignment list --assignee-object-id "${CURRENT_USER_OBJECT_ID}" --scope "${STORAGE_ACCOUNT_SCOPE}" --query "[?roleDefinitionName=='Storage Blob Data Owner'] | length(@)" -o tsv)"

if [[ "${HAS_BLOB_OWNER_ROLE}" == "0" ]]; then
  echo "Assigning 'Storage Blob Data Owner' to the signed-in user on ${AZ_STORAGE_ACCOUNT_NAME}"
  az role assignment create \
    --assignee-object-id "${CURRENT_USER_OBJECT_ID}" \
    --assignee-principal-type User \
    --role "Storage Blob Data Owner" \
    --scope "${STORAGE_ACCOUNT_SCOPE}" \
    --output none
else
  echo "Signed-in user already has 'Storage Blob Data Owner' on ${AZ_STORAGE_ACCOUNT_NAME}"
fi

# Create Blob container using Entra auth (works when shared keys are disabled by policy).
set +e
az storage container create \
  --name "${AZ_STORAGE_CONTAINER_NAME}" \
  --account-name "${AZ_STORAGE_ACCOUNT_NAME}" \
  --auth-mode login \
  --output table >/dev/null
CONTAINER_EXIT_CODE=$?
set -e

if [[ ${CONTAINER_EXIT_CODE} -ne 0 ]]; then
  echo "WARNING: Could not create container with login auth."
  echo "Ensure your identity has 'Storage Blob Data Owner' on the storage account, then rerun step 03."
else
  echo "Blob container ensured: ${AZ_STORAGE_CONTAINER_NAME}"
fi

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
    --location "${AZ_OPENAI_LOCATION}" \
    --kind AIServices \
    --sku S0 \
    --custom-domain "${AZ_AISERVICES_ACCOUNT_NAME}" \
    --allow-project-management true \
    --yes \
    --output table
fi

# Create Azure AI Foundry project under the AIServices account (idempotent).
PROJECT_RESOURCE_ID="/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${AZ_RESOURCE_GROUP}/providers/Microsoft.CognitiveServices/accounts/${AZ_AISERVICES_ACCOUNT_NAME}/projects/${AZ_FOUNDRY_PROJECT_NAME}"

if az resource show --ids "${PROJECT_RESOURCE_ID}" --api-version "${AZ_FOUNDRY_PROJECT_API_VERSION}" >/dev/null 2>&1; then
  echo "Foundry project already exists: ${AZ_FOUNDRY_PROJECT_NAME}"
else
  echo "Creating Foundry project: ${AZ_FOUNDRY_PROJECT_NAME}"
  az rest \
    --method put \
    --url "https://management.azure.com${PROJECT_RESOURCE_ID}?api-version=${AZ_FOUNDRY_PROJECT_API_VERSION}" \
    --body '{"location":"'"${AZ_OPENAI_LOCATION}"'","kind":"AIServices","identity":{"type":"SystemAssigned"}}' \
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

create_account_deployment() {
  local account_name="$1"
  local deployment_name="$2"
  local model_name="$3"
  local model_version="$4"
  local sku_name="$5"
  local sku_capacity="$6"
  local deployment_label="$7"

  if az cognitiveservices account deployment show \
    --name "${account_name}" \
    --resource-group "${AZ_RESOURCE_GROUP}" \
    --deployment-name "${deployment_name}" >/dev/null 2>&1; then
    echo "${deployment_label} already exists: ${deployment_name}"
    return
  fi

  echo "Creating ${deployment_label}: ${deployment_name}"
  set +e
  az cognitiveservices account deployment create \
    --name "${account_name}" \
    --resource-group "${AZ_RESOURCE_GROUP}" \
    --deployment-name "${deployment_name}" \
    --model-name "${model_name}" \
    --model-version "${model_version}" \
    --model-format OpenAI \
    --sku-name "${sku_name}" \
    --sku-capacity "${sku_capacity}" \
    --output table
  local deploy_exit_code=$?
  set -e

  if [[ ${deploy_exit_code} -ne 0 ]]; then
    echo "WARNING: ${deployment_label} creation failed."
    echo "Update the model/version/sku variables in 00-variables.sh and rerun step 03."
  fi
}

create_account_deployment \
  "${AZ_AISERVICES_ACCOUNT_NAME}" \
  "${AZ_OPENAI_DEPLOYMENT_NAME}" \
  "${AZ_OPENAI_MODEL_NAME}" \
  "${AZ_OPENAI_MODEL_VERSION}" \
  "${AZ_OPENAI_DEPLOYMENT_SKU_NAME}" \
  "${AZ_OPENAI_DEPLOYMENT_SKU_CAPACITY}" \
  "GPT deployment on AI Services"

create_account_deployment \
  "${AZ_AISERVICES_ACCOUNT_NAME}" \
  "${AZ_CU_LLM_DEPLOYMENT_NAME}" \
  "${AZ_CU_LLM_MODEL_NAME}" \
  "${AZ_CU_LLM_MODEL_VERSION}" \
  "${AZ_CU_LLM_DEPLOYMENT_SKU_NAME}" \
  "${AZ_CU_LLM_DEPLOYMENT_SKU_CAPACITY}" \
  "Content Understanding LLM deployment"

create_account_deployment \
  "${AZ_AISERVICES_ACCOUNT_NAME}" \
  "${AZ_CU_EMBEDDING_DEPLOYMENT_NAME}" \
  "${AZ_CU_EMBEDDING_MODEL_NAME}" \
  "${AZ_CU_EMBEDDING_MODEL_VERSION}" \
  "${AZ_CU_EMBEDDING_DEPLOYMENT_SKU_NAME}" \
  "${AZ_CU_EMBEDDING_DEPLOYMENT_SKU_CAPACITY}" \
  "Content Understanding embedding deployment"

echo "Step 03 complete."
