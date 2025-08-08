import azure.functions as func
import json
import logging
import os
from typing import Dict, Any, List, Optional

# Try to use Hugging Face Transformers if available
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSeq2SeqLM
    HF_AVAILABLE = True
    HF_IMPORT_ERROR = None
except Exception as e:
    HF_AVAILABLE = False
    HF_IMPORT_ERROR = str(e)

# Simple caches for tokenizers/models
TOKENIZER_CACHE: Dict[str, Any] = {}
MODEL_CACHE: Dict[str, Any] = {}


def get_default_model() -> str:
    return os.environ.get('DEFAULT_MODEL', 'gpt2')


def _load_tokenizer(model_name: str):
    if model_name in TOKENIZER_CACHE:
        return TOKENIZER_CACHE[model_name]
    if not HF_AVAILABLE:
        raise RuntimeError(f"Transformers not available: {HF_IMPORT_ERROR}")
    token = os.environ.get('HUGGINGFACE_TOKEN')
    tok = AutoTokenizer.from_pretrained(model_name, use_fast=True, token=token)
    TOKENIZER_CACHE[model_name] = tok
    return tok


def _load_model(model_name: str):
    if model_name in MODEL_CACHE:
        return MODEL_CACHE[model_name]
    if not HF_AVAILABLE:
        raise RuntimeError(f"Transformers not available: {HF_IMPORT_ERROR}")
    token = os.environ.get('HUGGINGFACE_TOKEN')
    try:
        model = AutoModelForCausalLM.from_pretrained(model_name, token=token)
    except Exception:
        # Fallback for seq2seq families (e.g., T5)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name, token=token)
    MODEL_CACHE[model_name] = model
    return model


def hf_tokenize_text(text: str, model: str = "gpt2", add_special_tokens: bool = True,
                     return_tokens: bool = True, return_token_ids: bool = True) -> dict:
    tok = _load_tokenizer(model)
    enc = tok(text, add_special_tokens=add_special_tokens, return_attention_mask=False)
    input_ids = enc["input_ids"]
    # Handle batch vs single
    if isinstance(input_ids[0], list):
        input_ids = input_ids[0]

    result: Dict[str, Any] = {
        "success": True,
        "engine": "hf-tokenizer",
        "model": model,
        "text": text,
        "token_count": len(input_ids),
        "vocab_size": getattr(tok, "vocab_size", None),
        "special_tokens": {
            "pad_token": getattr(tok, "pad_token", None),
            "unk_token": getattr(tok, "unk_token", None),
            "eos_token": getattr(tok, "eos_token", None),
            "bos_token": getattr(tok, "bos_token", None),
            "cls_token": getattr(tok, "cls_token", None),
            "sep_token": getattr(tok, "sep_token", None),
            "mask_token": getattr(tok, "mask_token", None),
        },
    }
    if return_tokens:
        result["tokens"] = _safe_convert_ids_to_tokens(tok, input_ids)
    if return_token_ids:
        result["token_ids"] = input_ids
    return result


def _safe_convert_ids_to_tokens(tok, ids: List[int]) -> List[str]:
    try:
        return tok.convert_ids_to_tokens(ids)
    except Exception:
        # Some tokenizers may not implement convert_ids_to_tokens fully
        return [str(i) for i in ids]


def hf_generate_text(text: str, model: str = "gpt2", options: Optional[Dict[str, Any]] = None) -> dict:
    options = options or {}
    tok = _load_tokenizer(model)
    mdl = _load_model(model)

    # Ensure pad token is defined for generation (e.g., GPT-2)
    if getattr(tok, "pad_token", None) is None and getattr(tok, "eos_token", None) is not None:
        tok.pad_token = tok.eos_token
    if getattr(mdl.config, "pad_token_id", None) is None and tok.pad_token_id is not None:
        mdl.config.pad_token_id = tok.pad_token_id

    inputs = tok(text, return_tensors="pt")

    max_new_tokens = int(options.get("max_new_tokens", 128))
    do_sample = bool(options.get("do_sample", False))
    temperature = float(options.get("temperature", 1.0))
    top_p = float(options.get("top_p", 1.0))
    top_k = int(options.get("top_k", 50))
    num_return_sequences = int(options.get("num_return_sequences", 1))

    gen_kwargs = dict(
        max_new_tokens=max_new_tokens,
        do_sample=do_sample,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        num_return_sequences=num_return_sequences,
        pad_token_id=tok.pad_token_id,
        eos_token_id=getattr(tok, "eos_token_id", None),
    )

    outputs = mdl.generate(**inputs, **gen_kwargs)
    # Handle single vs multiple sequences
    if outputs.dim() == 1:
        outputs = outputs.unsqueeze(0)

    input_len = inputs["input_ids"].shape[1]
    generations: List[Dict[str, Any]] = []
    for seq in outputs:
        seq_ids = seq.tolist()
        out_ids = seq_ids[input_len:]
        generations.append({
            "text": tok.decode(seq, skip_special_tokens=True),
            "new_token_count": len(out_ids),
        })

    return {
        "success": True,
        "engine": "hf-generate",
        "model": model,
        "input_token_count": input_len,
        "generations": generations,
    }

def simple_tokenize_text(text: str, model: str = "simple", return_tokens: bool = True, return_token_ids: bool = True) -> dict:
    """Simple word-based tokenization for testing"""
    try:
        # Simple word tokenization (split by spaces and punctuation)
        import re
        tokens = re.findall(r'\b\w+\b|\S', text)
        token_ids = [hash(token) % 50257 for token in tokens]  # Simple hash-based IDs
        
        result = {
            "success": True,
            "model": model,
            "text": text,
            "token_count": len(tokens),
            "vocab_size": 50257,
            "special_tokens": {
                "pad_token": "<PAD>",
                "unk_token": "<UNK>",
                "cls_token": None,
                "sep_token": None,
                "mask_token": None
            },
            "note": "Using simple tokenizer fallback (Transformers not available or error)."
        }
        
        # Add tokens and token_ids based on request parameters
        if return_tokens:
            result["tokens"] = tokens
        if return_token_ids:
            result["token_ids"] = token_ids
        
        return result
        
    except Exception as e:
        logging.error(f"Simple tokenization failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "model": model,
            "text": text
        }

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Main Azure Function entry point"""
    logging.info('Python HTTP trigger function processed a request.')
    
    try:
        method = req.method
        
        if method == "GET":
            default_model = get_default_model()
            return func.HttpResponse(
                json.dumps({
                    "message": "Tokenizer API is running",
                    "status": ("OK - HF available" if HF_AVAILABLE else f"DEGRADED - HF unavailable: {HF_IMPORT_ERROR}"),
                    "default_model": default_model,
                    "supported_methods": ["GET", "POST"],
                    "usage": {
                        "POST": "/api/tokenizerfunction",
                        "body": {
                            "text": "Text to tokenize (required)",
                            "model": "Hugging Face model name (optional; defaults to DEFAULT_MODEL)",
                            "task": "tokenize | generate (default: tokenize)",
                            "return_tokens": "bool (default: true)",
                            "return_token_ids": "bool (default: true)",
                            "options": {
                                "add_special_tokens": "bool (default: true)",
                                "max_new_tokens": "int (generate only)",
                                "do_sample": "bool (generate only)",
                                "temperature": "float (generate only)",
                                "top_p": "float (generate only)",
                                "top_k": "int (generate only)",
                                "num_return_sequences": "int (generate only)"
                            }
                        }
                    }
                }, indent=2),
                mimetype="application/json",
                status_code=200
            )
        
        elif method == "POST":
            try:
                req_body = req.get_json()
                if not req_body:
                    return func.HttpResponse(
                        json.dumps({"error": "Request body must be JSON"}),
                        mimetype="application/json",
                        status_code=400
                    )
                
                text = req_body.get('text', '')
                if not text:
                    return func.HttpResponse(
                        json.dumps({"error": "Text parameter is required"}),
                        mimetype="application/json",
                        status_code=400
                    )
                
                # Accept both 'model' and 'model_name' parameters for compatibility
                model_name = req_body.get('model_name') or req_body.get('model') or get_default_model()
                return_tokens = req_body.get('return_tokens', True)
                return_token_ids = req_body.get('return_token_ids', True)
                task = (req_body.get('task') or 'tokenize').lower()
                options = req_body.get('options') or {}
                
                # Tokenization or generation via HF if available; fallback to simple tokenization
                if task == 'tokenize':
                    if HF_AVAILABLE:
                        add_special = bool(options.get('add_special_tokens', True))
                        try:
                            result = hf_tokenize_text(
                                text,
                                model=model_name,
                                add_special_tokens=add_special,
                                return_tokens=return_tokens,
                                return_token_ids=return_token_ids,
                            )
                        except Exception as e:
                            logging.exception("HF tokenization failed; falling back to simple")
                            result = simple_tokenize_text(text, model_name, return_tokens, return_token_ids)
                            result["engine"] = "simple"
                            result["hf_error"] = str(e)
                    else:
                        result = simple_tokenize_text(text, model_name, return_tokens, return_token_ids)
                        result["engine"] = "simple"
                elif task == 'generate':
                    if not HF_AVAILABLE:
                        return func.HttpResponse(
                            json.dumps({
                                "success": False,
                                "error": f"Transformers not available: {HF_IMPORT_ERROR}",
                                "model": model_name,
                                "note": "Install transformers to enable generation."
                            }),
                            mimetype="application/json",
                            status_code=501
                        )
                    try:
                        result = hf_generate_text(text, model=model_name, options=options)
                    except Exception as e:
                        logging.exception("HF generation failed")
                        return func.HttpResponse(
                            json.dumps({
                                "success": False,
                                "error": f"Generation failed: {str(e)}",
                                "model": model_name
                            }),
                            mimetype="application/json",
                            status_code=500
                        )
                else:
                    return func.HttpResponse(
                        json.dumps({"error": f"Unsupported task '{task}'"}),
                        mimetype="application/json",
                        status_code=400
                    )
                
                status_code = 200 if result.get('success') else 500
                return func.HttpResponse(
                    json.dumps(result, indent=2),
                    mimetype="application/json",
                    status_code=status_code
                )
                
            except ValueError as e:
                return func.HttpResponse(
                    json.dumps({"error": "Invalid JSON in request body"}),
                    mimetype="application/json",
                    status_code=400
                )
            except Exception as e:
                logging.error(f"POST request error: {str(e)}")
                return func.HttpResponse(
                    json.dumps({"error": f"Request processing failed: {str(e)}"}),
                    mimetype="application/json",
                    status_code=500
                )
        
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Method {method} not allowed"}),
                mimetype="application/json",
                status_code=405
            )
            
    except Exception as e:
        logging.error(f"Function execution error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Function execution failed: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )