#!/usr/bin/env bash
set -euo pipefail

# Step 02: Ensure required Azure providers are registered and create the resource group if needed.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"

echo "Registering required Azure resource providers (idempotent)..."
az provider register --namespace Microsoft.Storage --wait >/dev/null
az provider register --namespace Microsoft.Search --wait >/dev/null
az provider register --namespace Microsoft.CognitiveServices --wait >/dev/null

if [[ "$(az group exists --name "${AZ_RESOURCE_GROUP}")" == "true" ]]; then
  echo "Resource group already exists: ${AZ_RESOURCE_GROUP}"
else
  echo "Creating resource group: ${AZ_RESOURCE_GROUP} in ${AZ_LOCATION}"
  az group create \
    --name "${AZ_RESOURCE_GROUP}" \
    --location "${AZ_LOCATION}" \
    --output table
fi

echo "Step 02 complete."
