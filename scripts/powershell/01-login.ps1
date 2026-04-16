$ErrorActionPreference = "Stop"

# Step 01: Authenticate with Azure CLI and select the target subscription.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$scriptDir/00-variables.ps1"

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI is not installed. Install it first: https://learn.microsoft.com/cli/azure/install-azure-cli"
}

try {
    az account show | Out-Null
    Write-Host "Azure CLI session already active."
}
catch {
    Write-Host "No Azure CLI session found. Opening login..."
    az login | Out-Null
}

if (-not [string]::IsNullOrWhiteSpace($env:AZ_SUBSCRIPTION_ID)) {
    Write-Host "Setting subscription to: $($env:AZ_SUBSCRIPTION_ID)"
    az account set --subscription $env:AZ_SUBSCRIPTION_ID
}

Write-Host "Current Azure account context:"
az account show --query "{subscriptionId:id, subscriptionName:name, tenantId:tenantId, user:user.name}" -o table

Write-Host "Step 01 complete."
