$ErrorActionPreference = "Stop"

# Step 02: Ensure required Azure providers are registered and create the resource group if needed.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$scriptDir/00-variables.ps1"

Write-Host "Registering required Azure resource providers (idempotent)..."
az provider register --namespace Microsoft.Storage --wait | Out-Null
az provider register --namespace Microsoft.Search --wait | Out-Null
az provider register --namespace Microsoft.CognitiveServices --wait | Out-Null

$rgExists = az group exists --name $env:AZ_RESOURCE_GROUP
if ($rgExists -eq "true") {
    Write-Host "Resource group already exists: $($env:AZ_RESOURCE_GROUP)"
}
else {
    Write-Host "Creating resource group: $($env:AZ_RESOURCE_GROUP) in $($env:AZ_LOCATION)"
    az group create `
        --name $env:AZ_RESOURCE_GROUP `
        --location $env:AZ_LOCATION `
        --output table
}

Write-Host "Step 02 complete."
