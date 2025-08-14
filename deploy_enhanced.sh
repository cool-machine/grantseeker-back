#!/bin/bash

# Azure Functions v2 + OpenAI Grant Analysis Deployment Script
# Make sure you're logged in to Azure CLI: az login

set -e

# Configuration - Enhanced for Grant Analysis with Azure SDK v2
RESOURCE_GROUP="ocp10"
FUNCTION_APP_NAME="ocp10-grant-functions"
STORAGE_ACCOUNT_NAME="ocp10grantstorage$(date +%s)"
COSMOS_ACCOUNT="ocp10-grant-cosmos"
OPENAI_ACCOUNT="ocp10-grant-openai"
LOCATION="centralus"
PYTHON_VERSION="3.9"

echo "🚀 Starting Azure Functions v2 + OpenAI deployment..."

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    echo "❌ Please login to Azure first: az login"
    exit 1
fi

echo "✅ Azure CLI authenticated"

# Create storage account if it doesn't exist
echo "📦 Creating storage account..."
az storage account create \
    --name $STORAGE_ACCOUNT_NAME \
    --location $LOCATION \
    --resource-group $RESOURCE_GROUP \
    --sku Standard_LRS \
    --only-show-errors || echo "Storage account may already exist"

# Create Azure OpenAI Service
echo "🤖 Creating Azure OpenAI service..."
az cognitiveservices account create \
    --name $OPENAI_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --kind OpenAI \
    --sku S0 \
    --only-show-errors || echo "OpenAI service may already exist"

# Create Cosmos DB Account
echo "🗄️ Creating Cosmos DB account..."
az cosmosdb create \
    --name $COSMOS_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --default-consistency-level Session \
    --locations regionName=$LOCATION failoverPriority=0 isZoneRedundant=False \
    --only-show-errors || echo "Cosmos DB may already exist"

# Create Cosmos DB Database and Containers
echo "📊 Setting up Cosmos DB database..."
az cosmosdb sql database create \
    --account-name $COSMOS_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --name "GrantAnalysis" \
    --only-show-errors || echo "Database may already exist"

echo "📋 Creating Cosmos DB containers..."
az cosmosdb sql container create \
    --account-name $COSMOS_ACCOUNT \
    --database-name "GrantAnalysis" \
    --resource-group $RESOURCE_GROUP \
    --name "Documents" \
    --partition-key-path "/id" \
    --throughput 400 \
    --only-show-errors || echo "Documents container may already exist"

az cosmosdb sql container create \
    --account-name $COSMOS_ACCOUNT \
    --database-name "GrantAnalysis" \
    --resource-group $RESOURCE_GROUP \
    --name "GrantOpportunities" \
    --partition-key-path "/id" \
    --throughput 400 \
    --only-show-errors || echo "GrantOpportunities container may already exist"

# Create Function App (Consumption Plan - FREE TIER)
echo "⚡ Creating Function App with Consumption Plan (FREE)..."
az functionapp create \
    --resource-group $RESOURCE_GROUP \
    --consumption-plan-location $LOCATION \
    --runtime python \
    --runtime-version $PYTHON_VERSION \
    --functions-version 4 \
    --name $FUNCTION_APP_NAME \
    --storage-account $STORAGE_ACCOUNT_NAME \
    --os-type linux \
    --disable-app-insights \
    --only-show-errors

# Get service endpoints and keys
echo "🔑 Retrieving service credentials..."
OPENAI_ENDPOINT=$(az cognitiveservices account show \
    --name $OPENAI_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --query properties.endpoint \
    --output tsv)

OPENAI_KEY=$(az cognitiveservices account keys list \
    --name $OPENAI_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --query key1 \
    --output tsv)

COSMOS_ENDPOINT=$(az cosmosdb show \
    --name $COSMOS_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --query documentEndpoint \
    --output tsv)

COSMOS_KEY=$(az cosmosdb keys list \
    --name $COSMOS_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --query primaryMasterKey \
    --output tsv)

# Set application settings with Azure SDK v2 configuration
echo "⚙️ Configuring application settings..."
az functionapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP_NAME \
    --settings \
        "AZURE_OPENAI_ENDPOINT=$OPENAI_ENDPOINT" \
        "AZURE_OPENAI_KEY=$OPENAI_KEY" \
        "AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo" \
        "COSMOS_ENDPOINT=$COSMOS_ENDPOINT" \
        "COSMOS_KEY=$COSMOS_KEY" \
        "COSMOS_DATABASE_NAME=GrantAnalysis" \
        "DEFAULT_MODEL=openai/gpt-oss-120b" \
    --only-show-errors

# Deploy function code
echo "📁 Deploying function code..."
func azure functionapp publish $FUNCTION_APP_NAME --python

echo "🎉 Deployment completed!"
echo ""
echo "📋 Resource Information:"
echo "- Function App: $FUNCTION_APP_NAME"
echo "- Azure OpenAI: $OPENAI_ACCOUNT"
echo "- Cosmos DB: $COSMOS_ACCOUNT"
echo "- Storage: $STORAGE_ACCOUNT_NAME"
echo ""
echo "📡 Function URLs:"
echo "- Tokenizer: https://$FUNCTION_APP_NAME.azurewebsites.net/api/TokenizerFunction"
echo "- Process Document: https://$FUNCTION_APP_NAME.azurewebsites.net/api/processdocument"
echo "- Analyze Grant: https://$FUNCTION_APP_NAME.azurewebsites.net/api/analyzegrant"
echo "- Get Matches: https://$FUNCTION_APP_NAME.azurewebsites.net/api/getmatches"
echo ""
echo "⚠️  IMPORTANT: Deploy GPT-3.5-Turbo model in Azure OpenAI:"
echo "   az cognitiveservices account deployment create \\"
echo "     --name $OPENAI_ACCOUNT \\"
echo "     --resource-group $RESOURCE_GROUP \\"
echo "     --deployment-name gpt-35-turbo \\"
echo "     --model-name gpt-35-turbo \\"
echo "     --model-version 0125 \\"
echo "     --model-format OpenAI \\"
echo "     --scale-type Standard"
echo ""
echo "💰 Estimated monthly cost: ~$30-50 (dev environment)"