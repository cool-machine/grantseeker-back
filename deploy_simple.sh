#!/bin/bash

# Simplified Azure Functions Deployment - Use Existing Infrastructure
# Works around quota and storage naming issues

set -e

# Configuration
RESOURCE_GROUP="ocp10"
FUNCTION_APP_NAME="ocp10-grant-functions"
EXISTING_STORAGE="ocp10storage1754580790"  # Use your existing storage
LOCATION="centralus"
PYTHON_VERSION="3.9"

echo "🚀 Starting simplified Azure Functions deployment..."

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    echo "❌ Please login to Azure first: az login"
    exit 1
fi

echo "✅ Azure CLI authenticated"
echo "📦 Using existing storage account: $EXISTING_STORAGE"

# Create Function App (using existing storage)
echo "⚡ Creating Function App with existing storage..."
az functionapp create \
    --resource-group $RESOURCE_GROUP \
    --consumption-plan-location $LOCATION \
    --runtime python \
    --runtime-version $PYTHON_VERSION \
    --functions-version 4 \
    --name $FUNCTION_APP_NAME \
    --storage-account $EXISTING_STORAGE \
    --os-type linux \
    --disable-app-insights \
    --only-show-errors || echo "Function app may already exist"

# Set basic application settings (without OpenAI for now)
echo "⚙️ Configuring basic application settings..."
az functionapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP_NAME \
    --settings \
        "DEFAULT_MODEL=openai/gpt-oss-120b" \
        "AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo" \
        "COSMOS_DATABASE_NAME=GrantAnalysis" \
    --only-show-errors

# Deploy function code
echo "📁 Deploying function code..."
func azure functionapp publish $FUNCTION_APP_NAME --python --no-build

echo "🎉 Basic deployment completed!"
echo ""
echo "📋 Function App Information:"
echo "- Function App: $FUNCTION_APP_NAME"
echo "- Storage: $EXISTING_STORAGE (existing)"
echo ""
echo "📡 Function URLs:"
echo "- Tokenizer: https://$FUNCTION_APP_NAME.azurewebsites.net/api/TokenizerFunction"
echo "- Process Document: https://$FUNCTION_APP_NAME.azurewebsites.net/api/processdocument"
echo "- Analyze Grant: https://$FUNCTION_APP_NAME.azurewebsites.net/api/analyzegrant"
echo "- Get Matches: https://$FUNCTION_APP_NAME.azurewebsites.net/api/getmatches"
echo ""
echo "⚠️  NOTE: OpenAI and Cosmos DB services need manual setup due to quota restrictions."
echo "   The functions are deployed but will need Azure OpenAI configuration."
echo ""
echo "💡 Next steps:"
echo "1. Test tokenizer function (should work immediately)"
echo "2. Request Azure OpenAI quota increase if needed"
echo "3. Manually create OpenAI service when quota available"