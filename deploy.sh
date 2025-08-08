#!/bin/bash

# Azure Function Deployment Script
# Make sure you're logged in to Azure CLI: az login

set -e

# Configuration
RESOURCE_GROUP="ocp10"
FUNCTION_APP_NAME="ocp10-tokenizer-function"
STORAGE_ACCOUNT_NAME="ocp10storage$(date +%s)"
LOCATION="eastus"
PYTHON_VERSION="3.9"

echo "🚀 Starting Azure Function deployment..."

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

# Set application settings
echo "⚙️ Configuring application settings..."
az functionapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP_NAME \
    --settings "DEFAULT_MODEL=gpt2" \
    --only-show-errors

# Deploy function code
echo "📁 Deploying function code..."
func azure functionapp publish $FUNCTION_APP_NAME --python

echo "🎉 Deployment completed!"
echo "📡 Function URL: https://$FUNCTION_APP_NAME.azurewebsites.net/api/TokenizerFunction"
echo ""
echo "🧪 Test with:"
echo "GET  https://$FUNCTION_APP_NAME.azurewebsites.net/api/TokenizerFunction"
echo "POST https://$FUNCTION_APP_NAME.azurewebsites.net/api/TokenizerFunction"
echo "     Body: {\"text\": \"Hello world\", \"model\": \"gpt2\"}"