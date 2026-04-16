#!/usr/bin/env bash
set -euo pipefail

# Step 01: Authenticate with Azure CLI and select the target subscription.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"

if ! command -v az >/dev/null 2>&1; then
  echo "ERROR: Azure CLI is not installed. Install it first: https://learn.microsoft.com/cli/azure/install-azure-cli"
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "No Azure CLI session found. Opening login..."
  az login
else
  echo "Azure CLI session already active."
fi

if [[ -n "${AZ_SUBSCRIPTION_ID}" ]]; then
  echo "Setting subscription to: ${AZ_SUBSCRIPTION_ID}"
  az account set --subscription "${AZ_SUBSCRIPTION_ID}"
fi

echo "Current Azure account context:"
az account show --query "{subscriptionId:id, subscriptionName:name, tenantId:tenantId, user:user.name}" -o table

echo "Step 01 complete."
