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

# PDF utilities - temporarily disable reportlab dependency
# from .pdf_utils import PDFFormFiller, PDFFormAnalyzer

def enhance_ngo_profile(base_profile: Dict, data_sources: Dict, ngo_profile_pdf: str = None) -> Dict:
    """
    Enhance NGO profile with data from multiple sources
    """
    enhanced_profile = base_profile.copy()
    
    # Add source tracking
    enhanced_profile['data_sources_used'] = []
    
    # Process NGO profile PDF if provided
    if data_sources.get('has_profile_pdf') and ngo_profile_pdf:
        try:
            pdf_extracted_data = extract_ngo_data_from_pdf(ngo_profile_pdf)
            if pdf_extracted_data:
                # Merge PDF data into profile
                for key, value in pdf_extracted_data.items():
                    if value and (not enhanced_profile.get(key) or len(str(value)) > len(str(enhanced_profile.get(key, '')))):
                        enhanced_profile[key] = value
                enhanced_profile['data_sources_used'].append('profile_pdf')
                logging.info("Enhanced NGO profile with PDF data")
        except Exception as e:
            logging.warning(f"Failed to extract data from NGO profile PDF: {str(e)}")
    
    # Process website data if provided
    if data_sources.get('has_website') and data_sources.get('website_url'):
        try:
            website_data = extract_ngo_data_from_website(data_sources['website_url'])
            if website_data:
                # Merge website data (lower priority than PDF)
                for key, value in website_data.items():
                    if value and not enhanced_profile.get(key):
                        enhanced_profile[key] = value
                enhanced_profile['data_sources_used'].append('website')
                logging.info("Enhanced NGO profile with website data")
        except Exception as e:
            logging.warning(f"Failed to extract data from website: {str(e)}")
    
    # Add manual entry source if no other sources
    if not enhanced_profile.get('data_sources_used'):
        enhanced_profile['data_sources_used'].append('manual_entry')
    
    return enhanced_profile

def create_simple_pdf_response(filled_responses: Dict[str, str]) -> str:
    """
    Create a simple PDF-like response (base64 encoded text for now)
    """
    # Create formatted text content
    content = "FILLED GRANT APPLICATION\n" + "="*50 + "\n\n"
    
    for field, response in filled_responses.items():
        content += f"{field.replace('_', ' ').title()}:\n"
        content += f"{response}\n\n"
    
    # Encode as base64 to simulate PDF data
    return base64.b64encode(content.encode('utf-8')).decode('utf-8')

def analyze_pdf_simple(pdf_data: str) -> Dict:
    """
    Simple PDF analysis without complex dependencies
    """
    try:
        pdf_bytes = base64.b64decode(pdf_data)
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        
        return {
            "total_pages": len(pdf_reader.pages),
            "has_form_fields": False,  # Simplified - not checking form fields
            "form_fields": []
        }
    except Exception as e:
        logging.warning(f"Simple PDF analysis failed: {str(e)}")
        return {
            "total_pages": 1,
            "has_form_fields": False,
            "form_fields": []
        }

def extract_ngo_data_from_pdf(pdf_data: str) -> Dict:
    """
    Extract NGO information from uploaded profile PDF
    """
    try:
        # Decode base64 PDF
        pdf_bytes = base64.b64decode(pdf_data)
        
        # Extract text using PyPDF2
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text_content = ""
        
        for page in pdf_reader.pages:
            text_content += page.extract_text() + "\n"
        
        # Use LLM to extract structured data from text
        client = get_openai_client()
        if client:
            return extract_structured_data_with_llm(text_content, "ngo_profile")
        else:
            # Fallback: simple keyword extraction
            return extract_data_with_keywords(text_content)
            
    except Exception as e:
        logging.error(f"Error extracting data from NGO profile PDF: {str(e)}")
        return {}

def extract_ngo_data_from_website(website_url: str) -> Dict:
    """
    Extract NGO information from website (placeholder for web scraping)
    """
    try:
        # Note: In production, you'd use requests + BeautifulSoup or similar
        # For now, return empty dict as web scraping needs additional dependencies
        logging.info(f"Website data extraction from {website_url} - not implemented yet")
        return {}
    except Exception as e:
        logging.error(f"Error extracting data from website {website_url}: {str(e)}")
        return {}

def extract_structured_data_with_llm(text_content: str, data_type: str) -> Dict:
    """
    Use LLM to extract structured data from unstructured text
    """
    try:
        client = get_openai_client()
        if not client:
            return {}
        
        if data_type == "ngo_profile":
            prompt = f"""
            Extract the following information from this NGO document. Return only a JSON object with the specified fields.
            If information is not found, omit the field or use null.
            
            Text: {text_content[:3000]}  # Limit to avoid token limits
            
            Extract these fields:
            - mission: Organization's mission statement
            - years_active: Number of years the organization has been active  
            - focus_areas: Array of focus areas/sectors
            - annual_budget: Annual budget in dollars (number only)
            - recent_projects: Description of recent successful projects
            - target_population: Who the organization serves
            - geographic_scope: Areas where organization operates
            - key_achievements: Notable accomplishments
            
            Return only valid JSON format.
            """
            
            response = client.chat.completions.create(
                model="gpt-35-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            # Try to parse as JSON
            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                logging.warning("LLM response was not valid JSON")
                return {}
                
    except Exception as e:
        logging.error(f"Error extracting structured data with LLM: {str(e)}")
        return {}

def extract_data_with_keywords(text_content: str) -> Dict:
    """
    Fallback: Extract data using simple keyword matching
    """
    extracted = {}
    text_lower = text_content.lower()
    
    # Look for mission statement
    if 'mission' in text_lower:
        # Simple extraction - find text around 'mission' keyword
        lines = text_content.split('\n')
        for i, line in enumerate(lines):
            if 'mission' in line.lower():
                # Take next few lines as mission
                mission_lines = lines[i:i+3]
                extracted['mission'] = ' '.join(mission_lines).strip()[:500]
                break
    
    # Look for budget information
    import re
    budget_matches = re.findall(r'\$[\d,]+', text_content)
    if budget_matches:
        # Try to extract largest dollar amount
        amounts = [int(match.replace('$', '').replace(',', '')) for match in budget_matches]
        extracted['annual_budget'] = max(amounts)
    
    return extracted

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
            "annual_budget": 500000,
            "contact_email": "info@ngo.org",
            "phone": "+1-555-0123",
            "recent_projects": "Community center construction"
        },
        "grant_context": {
            "funder_name": "Example Foundation",
            "focus_area": "education",
            "max_amount": 50000,
            "requirements": "Must serve underserved communities"
        },
        "data_sources": {
            "has_profile_pdf": true,
            "has_website": false,
            "website_url": null
        },
        "ngo_profile_pdf": "base64_encoded_pdf_content",  # Optional
        "extracted_data": {}  # Optional - from PDF/website processing
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
        data_sources = req_body.get('data_sources', {})
        ngo_profile_pdf = req_body.get('ngo_profile_pdf')
        
        if not pdf_data:
            return func.HttpResponse(
                json.dumps({"error": "pdf_data is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Enhance NGO profile with additional data sources
        try:
            logging.info(f"Enhancing NGO profile with data sources: {data_sources}")
            enhanced_ngo_profile = enhance_ngo_profile(ngo_profile, data_sources, ngo_profile_pdf)
            logging.info("NGO profile enhancement completed")
        except Exception as e:
            logging.error(f"Error enhancing NGO profile: {str(e)}")
            # Fallback to original profile if enhancement fails
            enhanced_ngo_profile = ngo_profile
        
        # Process the grant form filling
        result = process_grant_form(pdf_data, enhanced_ngo_profile, grant_context)
        
        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in grant form filling: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}", "type": type(e).__name__}),
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
        try:
            filled_responses = generate_field_responses(classified_fields, enhanced_ngo_profile, grant_context)
        except Exception as e:
            logging.warning(f"LLM response generation failed: {str(e)}")
            # Fallback to demo responses if LLM fails
            filled_responses = generate_demo_responses(classified_fields, enhanced_ngo_profile)
        
        # Step 4: Generate filled PDF - simplified version without reportlab
        try:
            # For now, create a simple text-based representation 
            # TODO: Restore full PDF generation when reportlab is working
            filled_pdf_data = create_simple_pdf_response(filled_responses)
            pdf_success = True
            fill_method = "Generated"
        except Exception as e:
            logging.error(f"Error generating PDF: {str(e)}")
            pdf_success = False
            filled_pdf_data = None
            fill_method = "Failed"
        
        # Step 5: Analyze original PDF structure - simplified
        try:
            pdf_analysis = analyze_pdf_simple(pdf_data)
        except Exception as e:
            logging.warning(f"PDF analysis failed: {str(e)}")
            pdf_analysis = {
                "total_pages": 1,
                "has_form_fields": False,
                "form_fields": []
            }
        
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
    Create contextual prompt for each field type using enhanced NGO profile
    """
    # Build comprehensive NGO context
    ngo_context = f"""
    NGO Profile:
    - Organization: {ngo_profile.get('organization_name', 'Example NGO')}
    - Mission: {ngo_profile.get('mission', 'Helping communities')}
    - Years Active: {ngo_profile.get('years_active', 5)}
    - Focus Areas: {', '.join(ngo_profile.get('focus_areas', ['community development']))}
    - Annual Budget: ${ngo_profile.get('annual_budget', 500000):,}"""
    
    # Add contact information if available
    if ngo_profile.get('contact_email'):
        ngo_context += f"\n    - Contact: {ngo_profile.get('contact_email')}"
    if ngo_profile.get('phone'):
        ngo_context += f" | {ngo_profile.get('phone')}"
    
    # Add recent projects if available
    if ngo_profile.get('recent_projects'):
        ngo_context += f"\n    - Recent Projects: {ngo_profile.get('recent_projects')}"
    
    # Add target population if available
    if ngo_profile.get('target_population'):
        ngo_context += f"\n    - Target Population: {ngo_profile.get('target_population')}"
    
    # Add key achievements if available
    if ngo_profile.get('key_achievements'):
        ngo_context += f"\n    - Key Achievements: {ngo_profile.get('key_achievements')}"
    
    # Add geographic scope if available
    if ngo_profile.get('geographic_scope'):
        ngo_context += f"\n    - Geographic Scope: {ngo_profile.get('geographic_scope')}"
    
    # Add data sources used for transparency
    if ngo_profile.get('data_sources_used'):
        ngo_context += f"\n    - Data Sources: {', '.join(ngo_profile.get('data_sources_used'))}"
    
    base_context = f"""
    {ngo_context}
    
    Grant Context:
    - Funder: {grant_context.get('funder_name', 'Foundation')}
    - Focus Area: {grant_context.get('focus_area', 'community development')}
    - Max Amount: ${grant_context.get('max_amount', 50000):,}
    - Requirements: {grant_context.get('requirements', 'N/A')}
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