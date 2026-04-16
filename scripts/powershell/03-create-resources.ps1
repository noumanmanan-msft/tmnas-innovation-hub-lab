$ErrorActionPreference = "Stop"

# Step 03: Provision Azure resources required for the lab.
# Resources created:
# - Storage Account + Blob container
# - Azure AI Search service
# - Azure OpenAI account + model deployment
# - Azure AI Services account + Foundry project + CU model deployments

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

# Grant the current signed-in user Blob data-plane rights so the local app can upload with DefaultAzureCredential.
$currentUserObjectId = az ad signed-in-user show --query id -o tsv
$storageAccountScope = az storage account show --name $env:AZ_STORAGE_ACCOUNT_NAME --resource-group $env:AZ_RESOURCE_GROUP --query id -o tsv
$hasBlobOwnerRole = az role assignment list --assignee-object-id $currentUserObjectId --scope $storageAccountScope --query "[?roleDefinitionName=='Storage Blob Data Owner'] | length(@)" -o tsv

if ($hasBlobOwnerRole -eq "0") {
    Write-Host "Assigning 'Storage Blob Data Owner' to the signed-in user on $($env:AZ_STORAGE_ACCOUNT_NAME)"
    az role assignment create `
        --assignee-object-id $currentUserObjectId `
        --assignee-principal-type User `
        --role "Storage Blob Data Owner" `
        --scope $storageAccountScope `
        --output none
}
else {
    Write-Host "Signed-in user already has 'Storage Blob Data Owner' on $($env:AZ_STORAGE_ACCOUNT_NAME)"
}

# Create Blob container using Entra auth.
try {
    az storage container create `
        --name $env:AZ_STORAGE_CONTAINER_NAME `
        --account-name $env:AZ_STORAGE_ACCOUNT_NAME `
        --auth-mode login `
        --output table | Out-Null

    Write-Host "Blob container ensured: $($env:AZ_STORAGE_CONTAINER_NAME)"
}
catch {
    Write-Warning "Could not create container with login auth. Ensure your identity has 'Storage Blob Data Owner' on the storage account, then rerun step 03."
}

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
        --location $env:AZ_OPENAI_LOCATION `
        --kind AIServices `
        --sku S0 `
        --custom-domain $env:AZ_AISERVICES_ACCOUNT_NAME `
        --allow-project-management true `
        --yes `
        --output table
}

# Create Azure AI Foundry project under the AIServices account (idempotent).
$subscriptionId = az account show --query id -o tsv
$projectResourceId = "/subscriptions/$subscriptionId/resourceGroups/$($env:AZ_RESOURCE_GROUP)/providers/Microsoft.CognitiveServices/accounts/$($env:AZ_AISERVICES_ACCOUNT_NAME)/projects/$($env:AZ_FOUNDRY_PROJECT_NAME)"

try {
    az resource show --ids $projectResourceId --api-version $env:AZ_FOUNDRY_PROJECT_API_VERSION | Out-Null
    Write-Host "Foundry project already exists: $($env:AZ_FOUNDRY_PROJECT_NAME)"
}
catch {
    Write-Host "Creating Foundry project: $($env:AZ_FOUNDRY_PROJECT_NAME)"
    az rest `
        --method put `
        --url "https://management.azure.com$projectResourceId?api-version=$($env:AZ_FOUNDRY_PROJECT_API_VERSION)" `
        --body "{\"location\":\"$($env:AZ_OPENAI_LOCATION)\",\"kind\":\"AIServices\",\"identity\":{\"type\":\"SystemAssigned\"}}" `
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

function Ensure-AccountDeployment {
    param(
        [string]$AccountName,
        [string]$DeploymentName,
        [string]$ModelName,
        [string]$ModelVersion,
        [string]$SkuName,
        [string]$SkuCapacity,
        [string]$DeploymentLabel
    )

    $exists = $false
    try {
        az cognitiveservices account deployment show `
            --name $AccountName `
            --resource-group $env:AZ_RESOURCE_GROUP `
            --deployment-name $DeploymentName | Out-Null
        $exists = $true
    }
    catch {
        $exists = $false
    }

    if ($exists) {
        Write-Host "$DeploymentLabel already exists: $DeploymentName"
        return
    }

    Write-Host "Creating $DeploymentLabel: $DeploymentName"
    try {
        az cognitiveservices account deployment create `
            --name $AccountName `
            --resource-group $env:AZ_RESOURCE_GROUP `
            --deployment-name $DeploymentName `
            --model-name $ModelName `
            --model-version $ModelVersion `
            --model-format OpenAI `
            --sku-name $SkuName `
            --sku-capacity $SkuCapacity `
            --output table
    }
    catch {
        Write-Warning "$DeploymentLabel creation failed. Update the model/version/sku values in 00-variables.ps1 and rerun step 03."
    }
}

Ensure-AccountDeployment `
    -AccountName $env:AZ_AISERVICES_ACCOUNT_NAME `
    -DeploymentName $env:AZ_OPENAI_DEPLOYMENT_NAME `
    -ModelName $env:AZ_OPENAI_MODEL_NAME `
    -ModelVersion $env:AZ_OPENAI_MODEL_VERSION `
    -SkuName $env:AZ_OPENAI_DEPLOYMENT_SKU_NAME `
    -SkuCapacity $env:AZ_OPENAI_DEPLOYMENT_SKU_CAPACITY `
    -DeploymentLabel "GPT deployment on AI Services"

Ensure-AccountDeployment `
    -AccountName $env:AZ_AISERVICES_ACCOUNT_NAME `
    -DeploymentName $env:AZ_CU_LLM_DEPLOYMENT_NAME `
    -ModelName $env:AZ_CU_LLM_MODEL_NAME `
    -ModelVersion $env:AZ_CU_LLM_MODEL_VERSION `
    -SkuName $env:AZ_CU_LLM_DEPLOYMENT_SKU_NAME `
    -SkuCapacity $env:AZ_CU_LLM_DEPLOYMENT_SKU_CAPACITY `
    -DeploymentLabel "Content Understanding LLM deployment"

Ensure-AccountDeployment `
    -AccountName $env:AZ_AISERVICES_ACCOUNT_NAME `
    -DeploymentName $env:AZ_CU_EMBEDDING_DEPLOYMENT_NAME `
    -ModelName $env:AZ_CU_EMBEDDING_MODEL_NAME `
    -ModelVersion $env:AZ_CU_EMBEDDING_MODEL_VERSION `
    -SkuName $env:AZ_CU_EMBEDDING_DEPLOYMENT_SKU_NAME `
    -SkuCapacity $env:AZ_CU_EMBEDDING_DEPLOYMENT_SKU_CAPACITY `
    -DeploymentLabel "Content Understanding embedding deployment"

Write-Host "Step 03 complete."
