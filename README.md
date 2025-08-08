# Azure Function Tokenizer Service

This Azure Function provides HTTP-triggered tokenization services using Hugging Face transformers library.

## Features

- **HTTP API**: GET for info, POST for tokenization
- **Default Model**: `gpt2` (configurable via `DEFAULT_MODEL`)
- **Flexible Models**: Supports any Hugging Face transformers model
- **Caching**: Tokenizer caching for better performance
- **Detailed Output**: Tokens, token IDs, counts, and special tokens

## Project Structure

```
ocp10/
├── TokenizerFunction/
│   ├── __init__.py          # Main function code
│   └── function.json        # Function configuration
├── host.json                # Function app configuration
├── local.settings.json      # Local development settings
├── requirements.txt         # Python dependencies
├── deploy.sh               # Deployment script
└── README.md               # This file
```

## Quick Setup

### 1. Prerequisites

- Python 3.9+
- Azure CLI installed and logged in
- Azure subscription with `ocp10` resource group

### 2. Local Development

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Azure Functions Core Tools (if not already installed)
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Start local development server
func start
```

### 3. Deploy to Azure

```bash
# Make sure you're logged in
az login

# Run deployment script
./deploy.sh
```

## API Usage

### GET Request - API Information

```bash
curl https://your-function-app.azurewebsites.net/api/TokenizerFunction
```

### POST Request - Tokenize Text

```bash
curl -X POST https://your-function-app.azurewebsites.net/api/TokenizerFunction \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world! How are you today?",
    "model": "gpt2",
    "options": {
      "add_special_tokens": true,
      "include_decoded": false
    }
  }'
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | Yes | Text to tokenize |
| `model` | string | No | HuggingFace model name (default: `gpt2`) |
| `options.add_special_tokens` | boolean | No | Add special tokens (default: true) |
| `options.include_decoded` | boolean | No | Include decoded text in response (default: false) |

### Response Format

```json
{
  "success": true,
  "model": "gpt2",
  "text": "Hello, world!",
  "tokens": ["Hello", ",", " world", "!"],
  "token_ids": [15496, 11, 1917, 0],
  "token_count": 4,
  "vocab_size": 50257,
  "special_tokens": {
    "pad_token": "<|endoftext|>",
    "unk_token": "<|endoftext|>",
    "cls_token": null,
    "sep_token": null,
    "mask_token": null
  }
}
```

## Configuration

### Environment Variables

Set these in Azure Function App Configuration:

- `DEFAULT_MODEL`: Default tokenizer model (default: `gpt2`)
- `HUGGINGFACE_TOKEN`: HuggingFace API token (optional, for private models)

### Local Development Settings

Edit `local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "DEFAULT_MODEL": "gpt2",
    "HUGGINGFACE_TOKEN": "your_token_here"
  }
}
```

## Supported Models

Any model from Hugging Face transformers library, including:

- `gpt2`
- `microsoft/DialoGPT-medium`
- `facebook/blenderbot-400M-distill`
- `google/flan-t5-base`
- And many more...

## Performance Considerations

- **First Request**: May take 30-60 seconds for model loading
- **Subsequent Requests**: Fast due to tokenizer caching
- **Memory**: Large models require more memory (consider Premium plan)
- **Timeout**: Set to 10 minutes in `host.json`

## Error Handling

The API returns detailed error messages:

```json
{
  "success": false,
  "error": "Model 'invalid/model' not found",
  "model": "invalid/model",
  "text": "sample text"
}
```

## Testing

### Local Testing

```bash
# Start local server
func start

# Test GET
curl http://localhost:7071/api/TokenizerFunction

# Test POST
curl -X POST http://localhost:7071/api/TokenizerFunction \
  -H "Content-Type: application/json" \
  -d '{"text": "Test tokenization"}'
```

### Azure Testing

After deployment, test using the provided URLs from the deployment script.

## Troubleshooting

### Common Issues

1. **Model Loading Errors**
   - Check model name spelling
   - Ensure model exists on Hugging Face
   - Check if model requires authentication token

2. **Memory Issues**
   - Use smaller models for Consumption plan
   - Consider Premium plan for large models

3. **Timeout Issues**
   - Increase `functionTimeout` in `host.json`
   - Consider model size vs. plan limitations

### Logs

View logs in Azure Portal:
1. Go to Function App → Functions → TokenizerFunction
2. Click "Monitor" to view execution logs
3. Check Application Insights for detailed diagnostics

## Development

### Adding New Features

1. Modify `TokenizerFunction/__init__.py`
2. Update tests
3. Deploy with `./deploy.sh`

### Custom Models

To use private or custom models:
1. Set `HUGGINGFACE_TOKEN` environment variable
2. Use full model path in API requests

## License

MIT License - feel free to modify and use for your projects.