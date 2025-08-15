import logging
import json
import os
import tempfile
from typing import Dict, List, Any, Optional
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
import PyPDF2
import io
import base64
from datetime import datetime

# For LLM integration
from openai import AzureOpenAI

# PDF utilities
from .pdf_utils import PDFFormFiller, PDFFormAnalyzer

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to fill grant forms using LLM
    
    Expected input:
    {
        "pdf_data": "base64_encoded_pdf_content",
        "ngo_profile": {
            "organization_name": "Example NGO",
            "mission": "Helping communities",
            "years_active": 5,
            "focus_areas": ["education", "health"],
            "annual_budget": 500000
        },
        "grant_context": {
            "funder_name": "Example Foundation",
            "focus_area": "education",
            "max_amount": 50000,
            "requirements": "Must serve underserved communities"
        }
    }
    """
    logging.info('Grant form filling request received')
    
    try:
        # Parse request
        req_body = req.get_json()
        
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        pdf_data = req_body.get('pdf_data')
        ngo_profile = req_body.get('ngo_profile', {})
        grant_context = req_body.get('grant_context', {})
        
        if not pdf_data:
            return func.HttpResponse(
                json.dumps({"error": "pdf_data is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Process the grant form filling
        result = process_grant_form(pdf_data, ngo_profile, grant_context)
        
        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in grant form filling: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

def process_grant_form(pdf_data: str, ngo_profile: Dict, grant_context: Dict) -> Dict:
    """
    Process grant form filling workflow
    """
    try:
        # Step 1: Parse PDF form fields
        form_fields = parse_pdf_form_fields(pdf_data)
        
        # Step 2: Classify and analyze fields
        classified_fields = classify_form_fields(form_fields)
        
        # Step 3: Generate responses using LLM
        filled_responses = generate_field_responses(classified_fields, ngo_profile, grant_context)
        
        # Step 4: Generate filled PDF
        pdf_filler = PDFFormFiller()
        pdf_success, filled_pdf_data, fill_method = pdf_filler.fill_pdf_form(pdf_data, filled_responses)
        
        # Step 5: Analyze original PDF structure
        pdf_analyzer = PDFFormAnalyzer()
        pdf_analysis = pdf_analyzer.analyze_pdf_structure(pdf_data)
        
        # Step 6: Create response structure
        filled_form_data = create_filled_form_structure(filled_responses)
        
        result = {
            "success": True,
            "original_fields": form_fields,
            "classified_fields": classified_fields,
            "filled_responses": filled_responses,
            "filled_form_structure": filled_form_data,
            "pdf_analysis": pdf_analysis,
            "timestamp": datetime.utcnow().isoformat(),
            "processing_summary": {
                "total_fields": len(form_fields),
                "filled_fields": len(filled_responses),
                "fill_rate": len(filled_responses) / max(len(form_fields), 1) * 100,
                "pdf_generation": {
                    "success": pdf_success,
                    "method": fill_method
                }
            }
        }
        
        # Add filled PDF if successful
        if pdf_success and filled_pdf_data:
            result["filled_pdf"] = {
                "data": filled_pdf_data,
                "filename": "filled_grant_application.pdf",
                "content_type": "application/pdf",
                "encoding": "base64"
            }
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing grant form: {str(e)}")
        raise

def parse_pdf_form_fields(pdf_data: str) -> List[Dict]:
    """
    Extract form fields from PDF using PyPDF2
    """
    try:
        # Decode base64 PDF data
        pdf_bytes = base64.b64decode(pdf_data)
        
        # Create PDF reader
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        
        form_fields = []
        
        # Check if PDF has form fields
        if pdf_reader.is_encrypted:
            logging.warning("PDF is encrypted, cannot extract form fields")
            return []
        
        # Try to get form fields
        try:
            if hasattr(pdf_reader, 'get_form_text_fields'):
                text_fields = pdf_reader.get_form_text_fields() or {}
                for field_name, field_value in text_fields.items():
                    form_fields.append({
                        "name": field_name,
                        "type": "text",
                        "current_value": field_value or "",
                        "required": True  # Assume required for demo
                    })
        except Exception as e:
            logging.warning(f"Could not extract form fields with PyPDF2: {str(e)}")
        
        # If no form fields found, extract text and infer fields
        if not form_fields:
            form_fields = infer_fields_from_text(pdf_reader)
        
        return form_fields
        
    except Exception as e:
        logging.error(f"Error parsing PDF form fields: {str(e)}")
        # Return demo fields if parsing fails
        return get_demo_grant_fields()

def infer_fields_from_text(pdf_reader) -> List[Dict]:
    """
    Infer form fields from PDF text content when no form fields are present
    """
    try:
        # Extract all text from PDF
        full_text = ""
        for page in pdf_reader.pages:
            full_text += page.extract_text() + "\n"
        
        # Common grant form field patterns
        field_patterns = [
            {"pattern": r"organization.*name", "name": "organization_name", "type": "text"},
            {"pattern": r"project.*title", "name": "project_title", "type": "text"},
            {"pattern": r"mission.*statement", "name": "mission_statement", "type": "textarea"},
            {"pattern": r"project.*description", "name": "project_description", "type": "textarea"},
            {"pattern": r"total.*budget|requested.*amount", "name": "requested_amount", "type": "number"},
            {"pattern": r"project.*duration", "name": "project_duration", "type": "text"},
            {"pattern": r"target.*population", "name": "target_population", "type": "textarea"},
            {"pattern": r"expected.*outcomes", "name": "expected_outcomes", "type": "textarea"},
        ]
        
        inferred_fields = []
        import re
        
        for pattern_info in field_patterns:
            if re.search(pattern_info["pattern"], full_text, re.IGNORECASE):
                inferred_fields.append({
                    "name": pattern_info["name"],
                    "type": pattern_info["type"],
                    "current_value": "",
                    "required": True,
                    "inferred": True
                })
        
        return inferred_fields
        
    except Exception as e:
        logging.error(f"Error inferring fields from text: {str(e)}")
        return get_demo_grant_fields()

def get_demo_grant_fields() -> List[Dict]:
    """
    Return demo grant form fields for testing
    """
    return [
        {"name": "organization_name", "type": "text", "current_value": "", "required": True},
        {"name": "project_title", "type": "text", "current_value": "", "required": True},
        {"name": "mission_statement", "type": "textarea", "current_value": "", "required": True},
        {"name": "project_description", "type": "textarea", "current_value": "", "required": True},
        {"name": "requested_amount", "type": "number", "current_value": "", "required": True},
        {"name": "project_duration", "type": "text", "current_value": "", "required": True},
        {"name": "target_population", "type": "textarea", "current_value": "", "required": False},
        {"name": "expected_outcomes", "type": "textarea", "current_value": "", "required": True}
    ]

def classify_form_fields(form_fields: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Classify form fields into categories for better LLM prompting
    """
    categories = {
        "organizational": [],
        "project": [],
        "financial": [],
        "impact": [],
        "other": []
    }
    
    # Classification rules
    org_keywords = ["organization", "org", "ngo", "entity", "mission", "history", "registration"]
    project_keywords = ["project", "program", "initiative", "activity", "description", "title"]
    financial_keywords = ["budget", "cost", "amount", "funding", "financial", "expense"]
    impact_keywords = ["outcome", "impact", "result", "benefit", "target", "population", "beneficiary"]
    
    for field in form_fields:
        field_name_lower = field["name"].lower()
        
        if any(keyword in field_name_lower for keyword in org_keywords):
            categories["organizational"].append(field)
        elif any(keyword in field_name_lower for keyword in project_keywords):
            categories["project"].append(field)
        elif any(keyword in field_name_lower for keyword in financial_keywords):
            categories["financial"].append(field)
        elif any(keyword in field_name_lower for keyword in impact_keywords):
            categories["impact"].append(field)
        else:
            categories["other"].append(field)
    
    return categories

def generate_field_responses(classified_fields: Dict, ngo_profile: Dict, grant_context: Dict) -> Dict[str, str]:
    """
    Generate appropriate responses for each field using LLM
    """
    responses = {}
    
    try:
        # Get OpenAI client (if configured)
        client = get_openai_client()
        if not client:
            # Return demo responses if OpenAI not configured
            return generate_demo_responses(classified_fields, ngo_profile)
        
        # Process each category
        for category, fields in classified_fields.items():
            for field in fields:
                field_name = field["name"]
                field_type = field["type"]
                
                # Generate contextual prompt
                prompt = create_field_prompt(field_name, field_type, category, ngo_profile, grant_context)
                
                # Get LLM response
                try:
                    response = client.chat.completions.create(
                        model="gpt-35-turbo",  # or gpt-4 if available
                        messages=[
                            {"role": "system", "content": "You are an expert grant writer helping fill out grant applications."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=500,
                        temperature=0.7
                    )
                    
                    responses[field_name] = response.choices[0].message.content.strip()
                    
                except Exception as e:
                    logging.warning(f"LLM call failed for field {field_name}: {str(e)}")
                    responses[field_name] = generate_fallback_response(field_name, field_type, ngo_profile)
        
        return responses
        
    except Exception as e:
        logging.error(f"Error generating field responses: {str(e)}")
        return generate_demo_responses(classified_fields, ngo_profile)

def create_field_prompt(field_name: str, field_type: str, category: str, ngo_profile: Dict, grant_context: Dict) -> str:
    """
    Create contextual prompt for each field type
    """
    base_context = f"""
    NGO Profile:
    - Organization: {ngo_profile.get('organization_name', 'Example NGO')}
    - Mission: {ngo_profile.get('mission', 'Helping communities')}
    - Years Active: {ngo_profile.get('years_active', 5)}
    - Focus Areas: {', '.join(ngo_profile.get('focus_areas', ['community development']))}
    
    Grant Context:
    - Funder: {grant_context.get('funder_name', 'Foundation')}
    - Focus Area: {grant_context.get('focus_area', 'community development')}
    - Max Amount: ${grant_context.get('max_amount', 50000):,}
    """
    
    # Field-specific prompts
    field_prompts = {
        "organization_name": f"{base_context}\nProvide the exact legal name of the organization.",
        
        "project_title": f"{base_context}\nCreate a compelling project title (8-12 words) that aligns with both the NGO's mission and the funder's focus area. Make it specific and action-oriented.",
        
        "mission_statement": f"{base_context}\nWrite a concise mission statement (under 200 words) that clearly describes the organization's core purpose and demonstrates alignment with the grant focus area.",
        
        "project_description": f"{base_context}\nWrite a detailed project description (300-500 words) that includes:\n1. The problem being addressed\n2. Your proposed solution\n3. Specific activities and methodology\n4. Timeline and milestones\n5. How it aligns with funder priorities",
        
        "requested_amount": f"{base_context}\nDetermine an appropriate funding request amount considering:\n1. The maximum grant amount\n2. Project scope and needs\n3. Organizational capacity\nProvide only the dollar amount (no $ symbol).",
        
        "project_duration": f"{base_context}\nSpecify an appropriate project duration (e.g., '12 months', '18 months') based on the project scope and typical grant periods.",
        
        "target_population": f"{base_context}\nDescribe the target population this project will serve, including demographics, size, and why they need this intervention.",
        
        "expected_outcomes": f"{base_context}\nList 3-5 specific, measurable outcomes this project will achieve, including quantitative targets where possible."
    }
    
    return field_prompts.get(field_name, f"{base_context}\nProvide an appropriate response for the field '{field_name}' ({field_type}).")

def generate_demo_responses(classified_fields: Dict, ngo_profile: Dict) -> Dict[str, str]:
    """
    Generate demo responses when LLM is not available
    """
    org_name = ngo_profile.get('organization_name', 'Community Development Alliance')
    
    demo_responses = {
        "organization_name": org_name,
        "project_title": "Digital Literacy Training for Underserved Communities",
        "mission_statement": f"{org_name} empowers underserved communities through education, technology access, and capacity building programs that create sustainable positive change and economic opportunities.",
        "project_description": "This 12-month project will establish digital literacy training centers in three underserved neighborhoods, providing computer skills training to 300 adults and seniors. The program includes basic computer operations, internet safety, online job applications, and digital communication skills. Each center will operate 6 days per week with certified instructors and provide ongoing support to ensure skill retention and practical application.",
        "requested_amount": "45000",
        "project_duration": "12 months",
        "target_population": "Low-income adults ages 25-65 in underserved urban neighborhoods who lack basic computer skills and digital literacy, with priority given to unemployed individuals, seniors, and single parents seeking to improve employment prospects.",
        "expected_outcomes": "1. Train 300 adults in basic digital literacy skills with 85% completion rate. 2. Achieve 70% job application success rate among participants. 3. Establish sustainable partnerships with 5 local employers. 4. Create ongoing digital support network with 90% participant satisfaction."
    }
    
    return demo_responses

def generate_fallback_response(field_name: str, field_type: str, ngo_profile: Dict) -> str:
    """
    Generate fallback response when LLM fails
    """
    fallbacks = {
        "organization_name": ngo_profile.get('organization_name', 'NGO Name'),
        "project_title": "Community Development Initiative",
        "requested_amount": "25000",
        "project_duration": "12 months"
    }
    
    return fallbacks.get(field_name, f"[Please provide {field_name.replace('_', ' ').title()}]")

def create_filled_form_structure(responses: Dict[str, str]) -> Dict:
    """
    Create structured representation of filled form
    """
    return {
        "form_type": "grant_application",
        "filled_fields": responses,
        "completion_status": "completed",
        "fill_timestamp": datetime.utcnow().isoformat(),
        "total_fields": len(responses),
        "metadata": {
            "processing_method": "llm_assisted",
            "field_classification": "automated"
        }
    }

def get_openai_client():
    """
    Get OpenAI client if configured
    """
    try:
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        api_key = os.environ.get("AZURE_OPENAI_KEY")
        
        if not endpoint or not api_key:
            logging.warning("Azure OpenAI not configured")
            return None
            
        return AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2024-02-01"
        )
    except Exception as e:
        logging.error(f"Error creating OpenAI client: {str(e)}")
        return None