# Project Memory: LLM-Based Grant Filler & Tokenizer

## 🎯 Project Overview
**Goal**: Create an Azure-based tokenization service with a web frontend for processing grant documents and extracting tokenized text for LLM applications.

## 📁 Repository Structure

### 1. Backend (Azure Function)
- **Repository**: `https://github.com/cool-machine/llm-based-grant-filler`  
- **Local Path**: `/Users/gg1900/coding/ocp10`
- **Azure Function URL**: `https://ocp10-tokenizer-function.azurewebsites.net/api/tokenizerfunction`
- **Resource Group**: `ocp10`
- **Deployment**: Azure Functions Consumption Plan (FREE tier)

### 2. Frontend (React Web App)
- **Repository**: `https://github.com/cool-machine/ux-for-llm`
- **Local Path**: `/Users/gg1900/coding/ux-for-llm`
- **Deployed URL**: `https://icy-moss-0b84c880f-preview.eastus2.1.azurestaticapps.net`
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
cd /Users/gg1900/coding/ocp10
func start --port 7071

# Frontend (React App)  
cd /Users/gg1900/coding/ux-for-llm
npm run dev  # Runs on http://localhost:5173
```

### Deployment Commands
```bash
# Deploy Azure Function
cd /Users/gg1900/coding/ocp10
func azure functionapp publish ocp10-tokenizer-function --python --no-build

# Deploy Static Web App
cd /Users/gg1900/coding/ux-for-llm
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

## 📊 Current Status (WORKING ✅)

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

### Infrastructure
- ✅ Both services on FREE Azure tiers
- ✅ All code pushed to GitHub repositories
- ✅ Deployments automated and documented

## 🔄 Next Development Steps
- Integrate full Hugging Face transformers (currently using simple tokenization)
- Add more document format support
- Implement batch processing
- Add user authentication
- Optimize for larger documents

## 🎯 Business Goal
Transform grant application process by providing AI-powered text analysis and tokenization for LLM-based grant writing assistance.