$ErrorActionPreference = "Stop"

# Step 03: Provision Azure resources required for the lab.
# Resources created:
# - Storage Account + Blob container
# - Azure AI Search service
# - Azure OpenAI account + model deployment
# - Azure AI Services account (used for Content Understanding endpoint/key)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$scriptDir/00-variables.ps1"

$rgExists = az group exists --name $env:AZ_RESOURCE_GROUP
if ($rgExists -ne "true") {
    Write-Error "Resource group does not exist: $($env:AZ_RESOURCE_GROUP). Run 02-create-resource-group.ps1 first."
}

# Create Storage Account if missing.
try {
    az storage account show --name $env:AZ_STORAGE_ACCOUNT_NAME --resource-group $env:AZ_RESOURCE_GROUP | Out-Null
    Write-Host "Storage account already exists: $($env:AZ_STORAGE_ACCOUNT_NAME)"
}
catch {
    Write-Host "Creating storage account: $($env:AZ_STORAGE_ACCOUNT_NAME)"
    az storage account create `
        --name $env:AZ_STORAGE_ACCOUNT_NAME `
        --resource-group $env:AZ_RESOURCE_GROUP `
        --location $env:AZ_LOCATION `
        --sku Standard_LRS `
        --kind StorageV2 `
        --min-tls-version TLS1_2 `
        --allow-blob-public-access false `
        --output table
}

# Create Blob container.
$storageKey = az storage account keys list --resource-group $env:AZ_RESOURCE_GROUP --account-name $env:AZ_STORAGE_ACCOUNT_NAME --query "[0].value" -o tsv
az storage container create `
    --name $env:AZ_STORAGE_CONTAINER_NAME `
    --account-name $env:AZ_STORAGE_ACCOUNT_NAME `
    --account-key $storageKey `
    --output table | Out-Null

Write-Host "Blob container ensured: $($env:AZ_STORAGE_CONTAINER_NAME)"

# Create Azure AI Search service if missing.
try {
    az search service show --name $env:AZ_SEARCH_SERVICE_NAME --resource-group $env:AZ_RESOURCE_GROUP | Out-Null
    Write-Host "AI Search service already exists: $($env:AZ_SEARCH_SERVICE_NAME)"
}
catch {
    Write-Host "Creating AI Search service: $($env:AZ_SEARCH_SERVICE_NAME)"
    az search service create `
        --name $env:AZ_SEARCH_SERVICE_NAME `
        --resource-group $env:AZ_RESOURCE_GROUP `
        --location $env:AZ_LOCATION `
        --sku basic `
        --partition-count 1 `
        --replica-count 1 `
        --output table
}

# Create Azure OpenAI account if missing.
try {
    az cognitiveservices account show --name $env:AZ_OPENAI_ACCOUNT_NAME --resource-group $env:AZ_RESOURCE_GROUP | Out-Null
    Write-Host "Azure OpenAI account already exists: $($env:AZ_OPENAI_ACCOUNT_NAME)"
}
catch {
    Write-Host "Creating Azure OpenAI account: $($env:AZ_OPENAI_ACCOUNT_NAME)"
    az cognitiveservices account create `
        --name $env:AZ_OPENAI_ACCOUNT_NAME `
        --resource-group $env:AZ_RESOURCE_GROUP `
        --location $env:AZ_OPENAI_LOCATION `
        --kind OpenAI `
        --sku S0 `
        --yes `
        --output table
}

# Create Azure AI Services account for Content Understanding if missing.
try {
    az cognitiveservices account show --name $env:AZ_AISERVICES_ACCOUNT_NAME --resource-group $env:AZ_RESOURCE_GROUP | Out-Null
    Write-Host "Azure AI Services account already exists: $($env:AZ_AISERVICES_ACCOUNT_NAME)"
}
catch {
    Write-Host "Creating Azure AI Services account: $($env:AZ_AISERVICES_ACCOUNT_NAME)"
    az cognitiveservices account create `
        --name $env:AZ_AISERVICES_ACCOUNT_NAME `
        --resource-group $env:AZ_RESOURCE_GROUP `
        --location $env:AZ_LOCATION `
        --kind AIServices `
        --sku S0 `
        --yes `
        --output table
}

# Create Azure OpenAI model deployment (idempotent check).
$deploymentExists = $false
try {
    az cognitiveservices account deployment show `
        --name $env:AZ_OPENAI_ACCOUNT_NAME `
        --resource-group $env:AZ_RESOURCE_GROUP `
        --deployment-name $env:AZ_OPENAI_DEPLOYMENT_NAME | Out-Null
    $deploymentExists = $true
}
catch {
    $deploymentExists = $false
}

if ($deploymentExists) {
    Write-Host "OpenAI deployment already exists: $($env:AZ_OPENAI_DEPLOYMENT_NAME)"
}
else {
    Write-Host "Creating OpenAI deployment: $($env:AZ_OPENAI_DEPLOYMENT_NAME)"
    try {
        az cognitiveservices account deployment create `
            --name $env:AZ_OPENAI_ACCOUNT_NAME `
            --resource-group $env:AZ_RESOURCE_GROUP `
            --deployment-name $env:AZ_OPENAI_DEPLOYMENT_NAME `
            --model-name $env:AZ_OPENAI_MODEL_NAME `
            --model-version $env:AZ_OPENAI_MODEL_VERSION `
            --model-format OpenAI `
            --sku-name $env:AZ_OPENAI_DEPLOYMENT_SKU_NAME `
            --sku-capacity $env:AZ_OPENAI_DEPLOYMENT_SKU_CAPACITY `
            --output table
    }
    catch {
        Write-Warning "OpenAI deployment creation failed. This is usually quota/model availability related."
        Write-Warning "Update model/version/region in 00-variables.ps1 and retry this step."
    }
}

Write-Host "Step 03 complete."
