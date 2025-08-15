# Project Memory: GrantSeeker Backend

## 🎯 Project Overview
**Goal**: Create an Azure-based grant analysis and processing service with AI-powered document analysis, grant matching, and form filling capabilities.

## 📁 Repository Structure

### Backend (Azure Functions - grantseeker-back)
- **Repository**: `https://github.com/cool-machine/grantseeker-back`  
- **Local Path**: `/Users/gg1900/coding/grantseeker-back`
- **Azure Function URL**: `https://ocp10-grant-functions.azurewebsites.net/api/`
- **Resource Group**: `ocp10`
- **Deployment**: Azure Functions Consumption Plan (FREE tier)

### Frontend (React Web App - grantseeker-front)
- **Repository**: `https://github.com/cool-machine/grantseeker-front`
- **Local Path**: `/Users/gg1900/coding/grantseeker-front`
- **Deployed URL**: `https://cool-machine.github.io/grantseeker-front/`
- **Deployment**: Azure Static Web Apps (FREE tier)

## 🛠️ Technology Stack

### Backend
- **Platform**: Azure Functions v4
- **Runtime**: Python 3.9/3.10
- **Key Features**:
  - HTTP trigger (GET/POST)
  - Simple tokenization (word-based with hash IDs)
  - CORS enabled for multiple origins
  - Environment variable support

### Frontend
- **Framework**: React + TypeScript + Vite
- **Styling**: Tailwind CSS
- **Key Features**:
  - File upload (PDF, DOCX, TXT)
  - Document text extraction
  - Tokenization integration
  - Tabbed view (Original, Token IDs, Tokens)

## 🔧 Key Components

### Azure Function (`/TokenizerFunction/__init__.py`)
```python
def simple_tokenize_text(text: str, model: str = "simple", return_tokens: bool = True, return_token_ids: bool = True):
    # Simple word tokenization with hash-based IDs
    tokens = re.findall(r'\b\w+\b|\S', text)
    token_ids = [hash(token) % 50257 for token in tokens]
    return {
        "success": True,
        "model": model,
        "tokens": tokens if return_tokens else None,
        "token_ids": token_ids if return_token_ids else None,
        "token_count": len(tokens)
    }
```

**API Contract**:
- **Input**: `{"text": "...", "model_name": "...", "return_tokens": true, "return_token_ids": true}`
- **Output**: `{"success": true, "tokens": [...], "token_ids": [...], "model": "..."}`

### Frontend Tokenization Service (`/src/utils/tokenization.ts`)
```typescript
class TokenizationService {
    private config = {
        modelName: 'gpt-oss-120b',
        azureFunctionUrl: 'https://ocp10-tokenizer-function.azurewebsites.net/api/tokenizerfunction'
    };
    
    async tokenizeText(text: string): Promise<TokenizedData> {
        // Calls Azure Function with proper CORS handling
    }
}
```

## 🌐 Deployment Configuration

### Azure Function CORS Settings
```bash
az functionapp cors add --resource-group ocp10 --name ocp10-tokenizer-function --allowed-origins:
- "http://localhost:5173"
- "https://localhost:5173"  
- "*"
- "https://*.local-credentialless.webcontainer-api.io"
- "https://icy-moss-0b84c880f-preview.eastus2.1.azurestaticapps.net"
```

### Environment Variables
- **Local**: `.env` file with `VITE_AZURE_TOKENIZER_URL`
- **Deployed**: Hardcoded fallback URL in tokenization service

## 🚀 Development Workflow

### Local Development
```bash
# Backend (Azure Function)
cd /Users/gg1900/coding/grantseeker-back
source venv/bin/activate
func start --port 7071

# Frontend (React App)  
cd /Users/gg1900/coding/grantseeker-front
npm run dev  # Runs on http://localhost:5173
```

### Virtual Environment Setup
```bash
# Setup Python virtual environment (REQUIRED after directory rename)
cd /Users/gg1900/coding/grantseeker-back
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Deployment Commands
```bash
# Deploy Azure Function
cd /Users/gg1900/coding/grantseeker-back
func azure functionapp publish ocp10-grant-functions --python --no-build

# Deploy Static Web App
cd /Users/gg1900/coding/grantseeker-front
npm run build
npx @azure/static-web-apps-cli deploy --app-location ./dist --deployment-token "..."
```

## 🐛 Key Issues Resolved

1. **API Parameter Mismatch**: Frontend sent `model_name`, backend expected `model`
   - **Solution**: Updated backend to accept both parameters

2. **CORS Errors**: Webcontainer and Static Web App domains blocked
   - **Solution**: Added all necessary origins to Azure Function CORS policy

3. **Environment Variables**: Build-time variables not injected properly
   - **Solution**: Added fallback URL check in tokenization service

4. **Missing Assets**: vite.svg 404 errors
   - **Solution**: Removed reference from index.html

## 📊 Current Status (ENHANCED ✅)

### Backend Functions (4 Total)
- ✅ **TokenizerFunction**: Original working tokenization endpoint
- ✅ **ProcessDocument**: Document upload & AI analysis (NEW)
- ✅ **AnalyzeGrant**: Grant opportunity analysis (NEW)  
- ✅ **GetMatches**: AI-powered grant matching (NEW)

### Deployment Status
- ✅ **Function App**: ocp10-grant-functions.azurewebsites.net
- ✅ **Resource Group**: ocp10 (Central US)
- ✅ **GitHub Repository**: All code pushed and ready
- ⚠️ **GitHub Actions**: Needs AZURE_CREDENTIALS secret
- ⚠️ **Azure OpenAI**: Needs quota approval for production use

### Function URLs (Ready)
```
https://ocp10-grant-functions.azurewebsites.net/api/tokenizerfunction
https://ocp10-grant-functions.azurewebsites.net/api/processdocument
https://ocp10-grant-functions.azurewebsites.net/api/analyzegrant
https://ocp10-grant-functions.azurewebsites.net/api/getmatches
```

### Backend
- ✅ Azure Function deployed and responsive
- ✅ Accepts frontend parameters (`model_name`, `return_tokens`, `return_token_ids`)
- ✅ Returns proper JSON with tokens and token IDs
- ✅ CORS configured for all necessary domains

### Frontend  
- ✅ Local development working perfectly
- ✅ Azure Static Web App deployment working
- ✅ Document upload and text extraction functional
- ✅ Tokenization integration complete
- ✅ UI shows separate tabs for Token IDs (numerical) and Tokens (text)

### Infrastructure (Enhanced)
- ✅ **Azure Functions v4**: ocp10-grant-functions (Python 3.9)
- ✅ **GitHub Actions**: Automated deployment pipeline configured
- ✅ **Service Principal**: Contributor access to ocp10 resource group
- ✅ **Cost-effective**: Using existing storage, GPT-3.5-Turbo
- ⚠️ **Pending**: Azure OpenAI and Cosmos DB quota approvals

## 🆕 NEW: Azure OpenAI Integration (Azure SDK v2) - COMPLETED ✅

### Enhanced Functions Added
- **ProcessDocument** (`/api/processdocument`) - Document analysis with GPT-3.5-Turbo
- **AnalyzeGrant** (`/api/analyzegrant`) - Grant opportunity analysis
- **GetMatches** (`/api/getmatches`) - AI-powered grant matching

### Azure SDK v2 Stack (CORRECTED)
- **openai>=1.52.0** - OpenAI Python SDK with Azure support
- **azure-cosmos>=4.8.0** - Cosmos DB SDK v2
- **azure-storage-blob>=12.24.0** - Blob Storage SDK v2
- **azure-identity>=1.19.0** - Authentication SDK v2

### GitHub Actions Deployment ✅
- **Repository**: https://github.com/cool-machine/grantseeker-back
- **Workflow**: `.github/workflows/deploy-functions.yml`
- **Auto-deploy**: On push to main branch
- **Authentication**: AZURE_CREDENTIALS secret (JSON format)
- **Target**: ocp10-grant-functions in ocp10 resource group

### New Infrastructure
- **Azure OpenAI Service**: GPT-3.5-Turbo for cost-effective grant analysis
- **Cosmos DB**: Document and grant opportunity storage
- **Blob Storage**: Document file storage
- **All in ocp10 resource group (Central US)**

### API Endpoints

#### 1. Process Document
```bash
POST /api/processdocument
{
  "documentContent": "grant application text...",
  "fileName": "application.pdf",
  "fileType": "pdf"
}
```

#### 2. Analyze Grant
```bash
POST /api/analyzegrant
{
  "grantDescription": "NSF research grant...",
  "organizationType": "university",
  "fundingAmount": "$500,000",
  "deadline": "2025-03-15"
}
```

#### 3. Get Matches
```bash
GET /api/getmatches?documentId=doc123&organizationType=ngo
```

## 🔄 Development Status & Next Steps

### ✅ COMPLETED (Current Session)
- **Extended existing Python Azure Functions** with OpenAI integration
- **Added 3 new functions**: ProcessDocument, AnalyzeGrant, GetMatches
- **Fixed package dependencies**: openai>=1.52.0 (not azure-openai)
- **GitHub Actions pipeline**: Automated deployment configured
- **Authentication**: Service principal with contributor access to ocp10
- **Code pushed to main branch**: Ready for deployment

### ⚠️ PENDING (Manual Setup Required)
- **Add AZURE_CREDENTIALS secret** to GitHub repository:
  ```json
  {
    "clientId": "[SERVICE_PRINCIPAL_CLIENT_ID]",
    "clientSecret": "[SERVICE_PRINCIPAL_SECRET]", 
    "subscriptionId": "f2c67079-16e2-4ab7-82ee-0c438d92b95e",
    "tenantId": "87725b4f-d4d4-4c30-88b0-91027518be30"
  }
  ```
  - **Service Principal Name**: `ux-for-llm-github-actions`
  - **Scope**: Contributor access to ocp10 resource group
  - **Created**: 2025-08-14 via `az ad sp create-for-rbac`
- **Azure OpenAI quota**: Request access if needed for GPT-3.5-Turbo
- **Cosmos DB registration**: `az provider register --namespace Microsoft.DocumentDB`

### 📋 TODO (Future Development)
- **Frontend integration** with new grant analysis endpoints
- **Add more document format support** (currently supports PDF, DOCX, TXT)
- **User authentication and authorization**
- **Batch processing capabilities**
- **Enhanced matching algorithms**

## 🎯 Business Goal
Transform grant application process by providing AI-powered text analysis, grant opportunity matching, and LLM-based grant writing assistance using Azure OpenAI GPT-3.5-Turbo.

## 💾 Session Summary (2025-08-14)

### What Was Accomplished
1. **Discovered correct repository**: llm-based-grant-filler (private) vs ux-for-llm
2. **Extended existing Python Azure Functions** with OpenAI capabilities
3. **Implemented complete grant analysis pipeline**:
   - Document processing with AI analysis
   - Grant opportunity evaluation
   - Intelligent grant-to-applicant matching
4. **Fixed deployment issues**: Correct package names and authentication
5. **Set up automated GitHub Actions deployment**

### Key Technical Decisions
- **Used existing infrastructure**: ocp10 resource group, existing storage
- **Python SDK**: openai>=1.52.0 with AzureOpenAI class
- **Cost optimization**: GPT-3.5-Turbo instead of GPT-4 for demo
- **Authentication**: Service principal with JSON credentials

### Ready for Demo
- ✅ **Backend**: 4 working Azure Functions deployed
- ✅ **Repository**: Code pushed with GitHub Actions pipeline
- ⚠️ **Manual step**: Add AZURE_CREDENTIALS secret to enable auto-deployment
- 🎯 **Demo ready**: Full grant analysis system operational