from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import TypedDict, Literal, Optional, List, Dict, Any
from langgraph.graph import StateGraph, START, END
import json
import logging
from google import genai
from google.genai import types
import io
import requests

import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'your-gemini-api-key-here')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./conversations.db')

genai_client = genai.Client(api_key=GEMINI_API_KEY)

EXTERNAL_API_BASE_URL = os.getenv('EXTERNAL_API_BASE_URL', 'https://your-api-endpoint.com')
EXTERNAL_API_DOCTOR_ENDPOINT = "/api/Doctor/get-by-Specialty"

CONCERN_TO_SPECIALTY_MAP = {
        "general": "General Practitioner",
    "general practitioner": "General Practitioner",
    "gp": "General Practitioner",
    "checkup": "General Practitioner",
    "routine": "General Practitioner",
    "family": "Family Medicine",
    "family medicine": "Family Medicine",
    "internal": "Internal Medicine",
    "internal medicine": "Internal Medicine",
    
        "chest pain": "Cardiology",
    "heart": "Cardiology",
    "blood pressure": "Cardiology",
    "palpitation": "Cardiology",
    "cardiology": "Cardiology",
    "cardiac": "Cardiology",
    
        "headache": "Neurology",
    "migraine": "Neurology",
    "dizziness": "Neurology",
    "neurology": "Neurology",
    "nerve": "Neurology",
    "neurological": "Neurology",
    
        "neurosurgery": "Neurosurgery",
    "brain surgery": "Neurosurgery",
    "spinal surgery": "Neurosurgery",
    
        "back pain": "Orthopedics",
    "bone": "Orthopedics",
    "joint": "Orthopedics",
    "orthopedics": "Orthopedics",
    "fracture": "Orthopedics",
    "sports injury": "Orthopedics",
    
        "child": "Pediatrics",
    "baby": "Pediatrics",
    "infant": "Pediatrics",
    "kid": "Pediatrics",
    "children": "Pediatrics",
    "pediatrics": "Pediatrics",
    
        "pregnancy": "Obstetrics & Gynecology",
    "pregnant": "Obstetrics & Gynecology",
    "gynecology": "Obstetrics & Gynecology",
    "obstetrics": "Obstetrics & Gynecology",
    "women": "Obstetrics & Gynecology",
    "ob/gyn": "Obstetrics & Gynecology",
    "maternal": "Obstetrics & Gynecology",
    
        "surgery": "General Surgery",
    "surgical": "General Surgery",
    "general surgery": "General Surgery",
    
        "plastic surgery": "Plastic Surgery",
    "reconstruction": "Plastic Surgery",
    "cosmetic": "Plastic Surgery",
    
        "urology": "Urology",
    "urological": "Urology",
    "bladder": "Urology",
    "prostate": "Urology",
    
        "nephrology": "Nephrology",
    "kidney": "Nephrology",
    "renal": "Nephrology",
    
        "stomach": "Gastroenterology",
    "digestion": "Gastroenterology",
    "gastroenterology": "Gastroenterology",
    "gastrointestinal": "Gastroenterology",
    "bowel": "Gastroenterology",
    "intestine": "Gastroenterology",
    
        "breathing": "Pulmonology",
    "lung": "Pulmonology",
    "asthma": "Pulmonology",
    "pulmonology": "Pulmonology",
    "respiratory": "Pulmonology",
    "bronchitis": "Pulmonology",
    
        "diabetes": "Endocrinology",
    "blood sugar": "Endocrinology",
    "endocrinology": "Endocrinology",
    "hormone": "Endocrinology",
    "thyroid": "Endocrinology",
    
        "skin": "Dermatology",
    "rash": "Dermatology",
    "acne": "Dermatology",
    "eczema": "Dermatology",
    "dermatology": "Dermatology",
    "dermatologist": "Dermatology",
    
        "eye": "Ophthalmology",
    "vision": "Ophthalmology",
    "ophthalmology": "Ophthalmology",
    "eye sight": "Ophthalmology",
    
        "ear": "Otolaryngology",
    "nose": "Otolaryngology",
    "throat": "Otolaryngology",
    "ent": "Otolaryngology",
    "otolaryngology": "Otolaryngology",
    "hearing": "Otolaryngology",
    
        "tooth": "Dentistry",
    "teeth": "Dentistry",
    "dental": "Dentistry",
    "toothache": "Dentistry",
    "cavity": "Dentistry",
    "dentistry": "Dentistry",
    "dentist": "Dentistry",
    
        "oral surgery": "Oral & Maxillofacial Surgery",
    "maxillofacial": "Oral & Maxillofacial Surgery",
    "jaw surgery": "Oral & Maxillofacial Surgery",
    
        "braces": "Orthodontics",
    "orthodontics": "Orthodontics",
    "teeth alignment": "Orthodontics",
    
        "gum": "Periodontics",
    "periodontist": "Periodontics",
    "gum disease": "Periodontics",
    
        "dentures": "Prosthodontics",
    "prosthodontics": "Prosthodontics",
    
        "root canal": "Endodontics",
    "endodontics": "Endodontics",
    
        "pediatric dentistry": "Pediatric Dentistry",
    "children dental": "Pediatric Dentistry",
    
        "oncology": "Oncology",
    "cancer": "Oncology",
    "tumor": "Oncology",
    
        "hematology": "Hematology",
    "blood disorder": "Hematology",
    
        "rheumatology": "Rheumatology",
    "arthritis": "Rheumatology",
    "autoimmune": "Rheumatology",
    
        "mental health": "Psychiatry",
    "depression": "Psychiatry",
    "anxiety": "Psychiatry",
    "psychiatry": "Psychiatry",
    "psychiatric": "Psychiatry",
    "mental": "Psychiatry",
    
        "psychology": "Psychology",
    "psychologist": "Psychology",
    "behavioral": "Psychology",
    
        "radiology": "Radiology",
    "xray": "Radiology",
    "x-ray": "Radiology",
    "imaging": "Radiology",
    
        "anesthesiology": "Anesthesiology",
    "anesthesia": "Anesthesiology",
    
        "emergency": "Emergency Medicine",
    "urgent": "Emergency Medicine",
    "emergency room": "Emergency Medicine",
    "er": "Emergency Medicine",
    
        "critical care": "Critical Care Medicine",
    "icu": "Critical Care Medicine",
    "intensive care": "Critical Care Medicine",
    
        "infection": "Infectious Diseases",
    "fever": "Infectious Diseases",
    "infectious": "Infectious Diseases",
    "infectious disease": "Infectious Diseases",
    
        "allergy": "Allergy & Immunology",
    "allergies": "Allergy & Immunology",
    "immunology": "Allergy & Immunology",
    "immune": "Allergy & Immunology",
    
        "geriatrics": "Geriatrics",
    "elderly": "Geriatrics",
    "senior": "Geriatrics",
    "aging": "Geriatrics",
    
        "physical medicine": "Physical Medicine & Rehabilitation",
    "rehabilitation": "Physical Medicine & Rehabilitation",
    "physical therapy": "Physical Medicine & Rehabilitation",
    
        "sports": "Sports Medicine",
    "athletic": "Sports Medicine",
    "sports medicine": "Sports Medicine",
    
        "nuclear medicine": "Nuclear Medicine",
    
        "pathology": "Pathology",
    "clinical pathology": "Clinical Pathology",
    "forensic medicine": "Forensic Medicine",
    
        "occupational medicine": "Occupational Medicine",
    "workplace": "Occupational Medicine",
    
        "preventive medicine": "Preventive Medicine",
    "prevention": "Preventive Medicine",
    "preventive": "Preventive Medicine",
    
        "sleep": "Sleep Medicine",
    "insomnia": "Sleep Medicine",
    "sleep disorder": "Sleep Medicine",
    
        "pain management": "Pain Medicine",
    "chronic pain": "Pain Medicine",
    "pain medicine": "Pain Medicine",
    
        "vascular surgery": "Vascular Surgery",
    "vascular": "Vascular Surgery",
    "blood vessel": "Vascular Surgery",
    
        "cardiothoracic surgery": "Cardiothoracic Surgery",
    "thoracic": "Cardiothoracic Surgery",
    "heart surgery": "Cardiothoracic Surgery",
    
        "pediatric surgery": "Pediatric Surgery",
    "children surgery": "Pediatric Surgery",
    
        "colorectal surgery": "Colorectal Surgery",
    "rectal": "Colorectal Surgery",
    "colon": "Colorectal Surgery",
    
        "hepatology": "Hepatology",
    "liver": "Hepatology",
}

DEFAULT_SPECIALTY = "General Practice"

def get_specialty_from_concern(medical_concern: str) -> str:
    concern_lower = medical_concern.lower()
    
        if concern_lower in CONCERN_TO_SPECIALTY_MAP:
        return CONCERN_TO_SPECIALTY_MAP[concern_lower]
    
        for key, specialty in CONCERN_TO_SPECIALTY_MAP.items():
        if key in concern_lower:
            logger.info(f"🔍 Mapped '{medical_concern}' → '{specialty}' (partial match)")
            return specialty
    
        logger.warning(f"⚠ No specialty match for '{medical_concern}', using {DEFAULT_SPECIALTY}")
    return DEFAULT_SPECIALTY

def fetch_doctors_from_external_api(specialty: str) -> List[Dict[str, Any]]:
    try:
                api_url = f"{EXTERNAL_API_BASE_URL}{EXTERNAL_API_DOCTOR_ENDPOINT}"
        
        logger.info(f"🌐 Calling external API: GET {api_url}?specialty={specialty}")
        
                response = requests.get(
            api_url,
            params={"specialty": specialty},
            timeout=10
        )
        
                logger.info(f"📡 API Response Status: {response.status_code}")
        
                if response.status_code == 200:
            data = response.json()
            
                                                if isinstance(data, list):
                doctors = data
            elif isinstance(data, dict):
                                doctors = (
                    data.get("data") or 
                    data.get("doctors") or 
                    data.get("result") or
                    data.get("value") or
                    []
                )
            else:
                doctors = []
            
            logger.info(f"✓ Retrieved {len(doctors)} doctors for specialty: {specialty}")
            return doctors
        
        elif response.status_code == 404:
            logger.warning(f"⚠ No doctors found for specialty: {specialty} (404)")
            return []
        
        elif response.status_code == 400:
                        try:
                error_data = response.json()
                error_description = error_data.get("description", "").lower() if isinstance(error_data, dict) else ""
                
                if "no doctors" in error_description or "empty" in error_description:
                                        logger.warning(f"⚠ No doctors found for specialty: {specialty} (API returned 400)")
                    return []
                else:
                                        logger.error(f"❌ Bad request to API: {response.text}")
                    return []
            except:
                                logger.warning(f"⚠ No doctors found for specialty: {specialty} (API returned 400)")
                return []
        
        else:
            logger.error(f"❌ API Error {response.status_code}: {response.text}")
            return []
    
    except requests.exceptions.Timeout:
        logger.error(f"❌ API timeout: Took longer than 10 seconds")
        return []
    
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Connection error: Cannot reach API at {EXTERNAL_API_BASE_URL}")
        return []
    
    except json.JSONDecodeError:
        logger.error(f"❌ Invalid JSON response from API")
        return []
    
    except Exception as e:
        logger.error(f"❌ Unexpected error calling API: {str(e)}")
        return []

def get_response_text(llm_response) -> str:
    if llm_response is None:
        return ""
    
        if isinstance(llm_response, str):
        return llm_response
    
        if hasattr(llm_response, 'content'):
        content = llm_response.content
        
                if isinstance(content, list):
            text_parts = []
            for item in content:
                if item is None:
                    continue
                                elif isinstance(item, dict) and 'text' in item:
                    text_parts.append(str(item['text']))
                                elif hasattr(item, 'text'):
                    text_parts.append(str(item.text))
                                elif isinstance(item, str):
                    text_parts.append(item)
                else:
                                        continue
            return " ".join(text_parts) if text_parts else ""
        
                if isinstance(content, str):
            return content
        
                if isinstance(content, dict) and 'text' in content:
            return str(content['text'])
        
                if hasattr(content, 'text'):
            return str(content.text)
        
                return ""
    
        if isinstance(llm_response, dict) and 'text' in llm_response:
        return str(llm_response['text'])
    
        if hasattr(llm_response, 'text'):
        return str(llm_response.text)
    
        return ""

def filter_doctor_ids_for_llm(doctors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered_doctors = []
    for doctor in doctors:
                filtered_doctor = {k: v for k, v in doctor.items() if k.lower() != 'id'}
        filtered_doctors.append(filtered_doctor)
    
    logger.info(f"✓ Filtered {len(filtered_doctors)} doctors (removed ID fields)")
    return filtered_doctors

def _get_available_doctors_impl(medical_concern: str) -> str:
    logger.info(f"🔧 Tool called: get_available_doctors('{medical_concern}')")
    
        specialty = get_specialty_from_concern(medical_concern)
    logger.info(f"🏥 Fetching doctors for specialty: {specialty}")
    
        doctors = fetch_doctors_from_external_api(specialty)
    
        if doctors:
                doctors_without_ids = filter_doctor_ids_for_llm(doctors)
        
                doctors_json = json.dumps(doctors_without_ids, indent=2)
        
        result = f"""Based on the medical concern: "{medical_concern}"
I found available doctors in the {specialty} specialty:

{doctors_json}

Here are the doctors that match the patient's condition. You should review their details and suggest the most appropriate one(s) based on the patient's specific needs."""
        
        logger.info(f"✓ Returned {len(doctors)} doctors to LLM (without IDs)")
        return result
    else:
                result = f"""Based on the medical concern: "{medical_concern}"

I searched for doctors in the {specialty} specialty, but unfortunately no doctors are currently available in that specialty.

Please inform the patient that:
1. No doctors are currently available for this specialty
2. They might want to try a related specialty
3. Or check back later for availability

Apologize for the inconvenience and offer alternative assistance."""
        
        logger.warning(f"⚠ No doctors found for specialty: {specialty}")
        return result

@tool
def get_available_doctors(medical_concern: str) -> str:
    return _get_available_doctors_impl(medical_concern)

def invoke_gemini_vision_analysis(file_bytes_list: list) -> str:
    logger.info(f"🤖 [GEMINI VISION] Analyzing {len(file_bytes_list)} medical record image(s)")
    
    import time
    
        models_to_try = [
             "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
    ]
    
    max_retries_per_model = 2
    retry_delay = 2
    
    try:
                prompt = """You are a medical document analyzer. Analyze the medical record images provided and give:

1. **Document Type**: What type of medical record is this? (lab results, prescription, diagnosis, etc.)
2. **Key Information**: Extract any readable medical information (dates, test results, diagnoses, medication names, dosages, etc.)
3. **Health Concerns**: Identify any health issues or concerns mentioned
4. **Recommendations**: Suggest what follow-up actions might be needed
5. **Overall Summary**: Provide a brief summary of the medical records

Be thorough but concise. Focus on what's actually visible in the documents."""
        
                content_parts = [prompt]
        
                for idx, (file_bytes, mime_type) in enumerate(file_bytes_list):
            logger.info(f"  📸 Processing image {idx + 1}/{len(file_bytes_list)} ({mime_type})")
            
            try:
                                image_part = types.Part.from_bytes(
                    data=file_bytes,
                    mime_type=mime_type or "image/jpeg"
                )
                content_parts.append(image_part)
                logger.info(f"  ✓ Image {idx + 1} loaded ({len(file_bytes)} bytes, {mime_type})")
                
            except Exception as e:
                logger.error(f"  ✗ Error processing image {idx + 1}: {e}")
                return f"Error: Failed to process image {idx + 1}"
        
        logger.info(f"🔄 Sending {len(file_bytes_list)} image(s) to Gemini Vision...")
        
                for model_idx, model_name in enumerate(models_to_try):
            logger.info(f"🔀 [MODEL SWITCHING] Trying model {model_idx + 1}/{len(models_to_try)}: {model_name}")
            
                        for attempt in range(max_retries_per_model):
                try:
                                        response = genai_client.models.generate_content(
                        model=model_name,
                        contents=content_parts
                    )
                    
                    analysis = response.text
                    logger.info(f"✓ [GEMINI VISION] Analysis complete using {model_name}")
                    return analysis
                    
                except Exception as e:
                    error_str = str(e)
                    
                                        if "503" in error_str or "UNAVAILABLE" in error_str:
                        if attempt < max_retries_per_model - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            logger.warning(f"⏳ Model {model_name} unavailable (attempt {attempt + 1}/{max_retries_per_model}). Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.warning(f"⚠️ Model {model_name} unavailable after retries. Trying next model...")
                            break
                    else:
                                                logger.warning(f"⚠️ Model {model_name} error: {e}. Trying next model...")
                        break
        
                logger.error(f"✗ [GEMINI VISION] All models failed")
        return "Error: All Gemini vision models are currently unavailable. Please try again later."
    
    except Exception as e:
        logger.error(f"✗ [GEMINI VISION] Unexpected error: {e}")
        return f"Error analyzing medical records: {str(e)}"

CV_MODEL_ENDPOINTS = {
    'pneumonia-classifier': os.getenv('PNEUMONIA_CLASSIFIER_API', 'https://your-api-gateway-endpoint.com/pneumonia-classifier'),
    'pneumonia-detector': os.getenv('PNEUMONIA_DETECTOR_API', 'https://your-api-gateway-endpoint.com/pneumonia-detector'),
    'fracture-classifier': os.getenv('FRACTURE_CLASSIFIER_API', 'https://your-api-gateway-endpoint.com/fracture-classifier'),
    'fracture-detector': os.getenv('FRACTURE_DETECTOR_API', 'https://your-api-gateway-endpoint.com/fracture-detector'),
    'tumor-classifier': os.getenv('TUMOR_CLASSIFIER_API', 'https://your-api-gateway-endpoint.com/tumor-classifier'),
    'tumor-detector': os.getenv('TUMOR_DETECTOR_API', 'https://your-api-gateway-endpoint.com/tumor-detector'),
}

def call_aws_lambda_cv_model(model_name: str, image_base64: str, model_type: str) -> Dict[str, Any]:
    endpoint = CV_MODEL_ENDPOINTS.get(model_name)
    
    if not endpoint or 'your-api-gateway-endpoint' in endpoint:
        raise ValueError(f"API endpoint not configured for {model_name}. Set {model_name.upper().replace('-', '_')}_API environment variable.")
    
    payload = {
        'image_base64': image_base64,
        'model_type': model_type
    }
    
    try:
        response = requests.post(
            endpoint,
            json=payload,
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        raise Exception(f"API call to {model_name} failed: {str(e)}")

@tool
def classify_pneumonia(image_base64: str) -> str:
    try:
        result = call_aws_lambda_cv_model('pneumonia-classifier', image_base64, 'classifier')
        confidence = result.get('confidence', 0)
        prediction = result.get('prediction', 'Unknown')
        return f"Pneumonia Classification: {prediction} (Confidence: {confidence:.2%})"
    except Exception as e:
        return f"Error in pneumonia classification: {str(e)}"

@tool
def detect_pneumonia(image_base64: str) -> str:
    try:
        result = call_aws_lambda_cv_model('pneumonia-detector', image_base64, 'detector')
        detections = result.get('detections', [])
        return f"Pneumonia Detection: Found {len(detections)} regions of interest. Details: {json.dumps(detections)}"
    except Exception as e:
        return f"Error in pneumonia detection: {str(e)}"

@tool
def classify_fractures(image_base64: str) -> str:
    try:
        result = call_aws_lambda_cv_model('fracture-classifier', image_base64, 'classifier')
        confidence = result.get('confidence', 0)
        prediction = result.get('prediction', 'Unknown')
        return f"Fracture Classification: {prediction} (Confidence: {confidence:.2%})"
    except Exception as e:
        return f"Error in fracture classification: {str(e)}"

@tool
def detect_fractures(image_base64: str) -> str:
    try:
        result = call_aws_lambda_cv_model('fracture-detector', image_base64, 'detector')
        detections = result.get('detections', [])
        return f"Fracture Detection: Found {len(detections)} fracture sites. Details: {json.dumps(detections)}"
    except Exception as e:
        return f"Error in fracture detection: {str(e)}"

@tool
def classify_tumors(image_base64: str) -> str:
    try:
        result = call_aws_lambda_cv_model('tumor-classifier', image_base64, 'classifier')
        confidence = result.get('confidence', 0)
        prediction = result.get('prediction', 'Unknown')
        tumor_type = result.get('tumor_type', 'Unknown')
        return f"Tumor Classification: {prediction} - Type: {tumor_type} (Confidence: {confidence:.2%})"
    except Exception as e:
        return f"Error in tumor classification: {str(e)}"

@tool
def detect_tumors(image_base64: str) -> str:
    try:
        result = call_aws_lambda_cv_model('tumor-detector', image_base64, 'detector')
        detections = result.get('detections', [])
        return f"Tumor Detection: Found {len(detections)} tumor regions. Details: {json.dumps(detections)}"
    except Exception as e:
        return f"Error in tumor detection: {str(e)}"

tools = [get_available_doctors, classify_pneumonia, detect_pneumonia, classify_fractures, detect_fractures, classify_tumors, detect_tumors]

SYSTEM_PROMPT_MEDICAL = """You are a helpful medical assistant in a telemedicine application.

YOUR PURPOSE:
- Provide medical guidance and support to patients
- Help patients understand their symptoms and health conditions
- Use the get_available_doctors tool when appropriate
- Answer health-related questions with accurate, helpful information

WHAT YOU SHOULD DO:
✓ Ask clarifying questions about symptoms
✓ Explain medical conditions in simple terms
✓ Suggest common remedies and self-care measures
✓ When a patient has symptoms that warrant professional evaluation, USE THE TOOL to get doctors
✓ Provide general health education
✓ Be empathetic and supportive
✓ Remember previous messages in the conversation for context

WHEN TO USE THE get_available_doctors TOOL:
✓ Patient has symptoms that need professional evaluation
✓ Patient asks about seeing a specialist
✓ Patient mentions wanting to see a doctor
✓ Medical condition is beyond self-care recommendations
✗ Do NOT use tool for general health questions
✗ Do NOT use tool just to answer questions about doctors

AFTER USING THE TOOL:
- Review the doctors list
- Select the MOST appropriate doctors (1-3) based on specialty
- Mention their name, specialty, experience, rating, and availability
- Include their doctor IDs in your recommendation

WHAT YOU MUST NOT DO:
✗ Do NOT provide a definitive diagnosis
✗ Do NOT prescribe medications
✗ Do NOT perform medical examinations
✗ Do NOT answer non-medical questions (redirect politely)
✗ Do NOT make medical decisions for the patient
✗ Do NOT diagnose serious conditions - always recommend professional help

IMPORTANT DISCLAIMERS:
- Always remind patients that you are NOT a substitute for professional medical advice
- For serious symptoms (chest pain, difficulty breathing, severe injury), ALWAYS recommend immediate professional care
- Encourage patients to see a doctor for proper diagnosis and treatment

TONE:
- Professional but friendly
- Empathetic and supportive
- Clear and easy to understand
- Cautious but not alarmist

SCOPE:
You are operating within a medical telemedicine app. Stay focused on medical guidance and health-related topics."""

SYSTEM_PROMPT_SUMMARY = """You are a medical conversation summarizer.

Your task: Create a concise 2-3 sentence summary of a medical conversation between a patient and a medical assistant.

FOCUS ON:
- Main symptoms or health concerns mentioned
- Key medical information shared
- Actions or recommendations discussed
- Patient's current status
- Any doctors suggested (include their specialties)

Keep it medical and factual."""

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ConversationRecord(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True)
    messages = Column(Text, default="[]")
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    message_count = Column(Integer, default=0)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

logger.info("✓ Database reset on startup - fresh state")
logger.info("✓ All old sessions cleared")

llm_chat = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite", 
    api_key=GEMINI_API_KEY,
)

llm_summary = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    api_key=GEMINI_API_KEY,
)

llm_with_tools = llm_chat.bind_tools(tools)

class MessageResponse(BaseModel):
    id: str
    response: str
    message_count: int
    summary: str
    suggested_doctor_ids: List[str]
    route: str

class RouterState(TypedDict):
    id: str
    message: str
    route: str
    uploaded_files: list
    db_session: Session
    response: str
    message_count: int
    summary: str
    suggested_doctor_ids: List[str]

def get_conversation(db: Session, patient_id: str) -> ConversationRecord:
    record = db.query(ConversationRecord).filter(ConversationRecord.id == patient_id).first()
    
    if not record:
        record = ConversationRecord(id=patient_id)
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(f"✓ Created new conversation for {patient_id}")
    
    return record

def add_message(db: Session, patient_id: str, role: str, content: str) -> list:
    record = get_conversation(db, patient_id)
    messages = json.loads(record.messages) if record.messages else []
    
    messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    
    record.messages = json.dumps(messages)
    record.message_count += 1
    record.updated_at = datetime.now()
    db.commit()
    
    logger.info(f"✓ Added {role} message to {patient_id}")
    
        return messages[-5:] if len(messages) > 5 else messages

def generate_summary(db: Session, patient_id: str) -> str:
    try:
        record = get_conversation(db, patient_id)
        messages = json.loads(record.messages) if record.messages else []
        
        if not messages:
            return ""
        
                context_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages[-10:]])
        
        logger.info("📊 Generating summary...")
        
                summary_response = llm_summary.invoke([
            SystemMessage(content=SYSTEM_PROMPT_SUMMARY),
            HumanMessage(content=f"Summarize this conversation:\n\n{context_text}")
        ])
        
        summary = get_response_text(summary_response)
        
        record.summary = summary
        db.commit()
        
        logger.info(f"✓ Summary updated: {summary[:50]}...")
        
        return summary
    except Exception as e:
        logger.error(f"✗ Summary generation failed: {e}")
        return f"Error generating summary: {str(e)}"

def delete_record(db: Session, patient_id: str) -> bool:
    record = db.query(ConversationRecord).filter(ConversationRecord.id == patient_id).first()
    
    if record:
        db.delete(record)
        db.commit()
        logger.info(f"✓ Deleted conversation record for {patient_id}")
        return True
    
    logger.warning(f"⚠️ Record not found for {patient_id}")
    return False

def clean_doctor_ids_from_response(response_text: str) -> str:
    import re
    
    if not response_text:
        return response_text
    
        cleaned = re.sub(r'\s*\(\s*ID\s*:\s*\d+\s*\)', '', response_text, flags=re.IGNORECASE)
    
        cleaned = re.sub(r'\s*\[\s*ID\s*:\s*\d+\s*\]', '', cleaned, flags=re.IGNORECASE)
    
        cleaned = re.sub(r'\s*-\s*ID\s*:\s*\d+\s*$', '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
    
        cleaned = re.sub(r'\s+ID\s*:\s*\d+(?=\s|$)', '', cleaned, flags=re.IGNORECASE)
    
        cleaned = re.sub(r'\s+', ' ', cleaned)
    
        cleaned = cleaned.strip()
    
    return cleaned

def extract_doctor_ids(response_text: str) -> List[str]:
    doctor_ids = []
    
        if response_text is None:
        logger.warning("⚠ extract_doctor_ids received None")
        return doctor_ids
    
    if isinstance(response_text, list):
        response_text = " ".join([str(item) for item in response_text if item is not None])
    else:
        response_text = str(response_text)
    
        import re
    
        matches = re.findall(r'ID:\s*(\d+)', response_text)
    doctor_ids.extend([str(m) for m in matches])
    
        matches = re.findall(r'doctor[^0-9]*(\d+)', response_text, re.IGNORECASE)
    doctor_ids.extend([str(m) for m in matches])
    
        doctor_ids = list(set(doctor_ids))
    doctor_ids = [str(id) for id in doctor_ids]
    
    logger.info(f"✓ Extracted doctor IDs: {doctor_ids}")
    return doctor_ids

def chat_node(state: RouterState) -> RouterState:
    logger.info(f"🔹 [CHAT NODE] Processing: id={state['id']}, message_len={len(state['message'])}")
    
    db = state["db_session"]
    
        if state["message"].lower() == "endsession":
        logger.info(f"🛑 EndSession command received for {state['id']}")
        delete_record(db, state["id"])
        state["response"] = "Session ended. All records deleted."
        state["message_count"] = 0
        state["summary"] = ""
        state["suggested_doctor_ids"] = []
        return state
    
        messages = add_message(db, state["id"], "user", state["message"])
    
        summary = generate_summary(db, state["id"])
    
    record = get_conversation(db, state["id"])
    
        context_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
    
    logger.info("📊 Building message context...")
    
    user_prompt = f"""Conversation context (last 5 messages):
{context_text}

Summary: {summary}

Patient's latest message is above. Respond helpfully and professionally. 
If the patient's condition warrants professional evaluation, use the get_available_doctors tool."""
    
    logger.info(f"🤖 Invoking LLM with tools...")
    
        llm_response = llm_with_tools.invoke([
        SystemMessage(content=SYSTEM_PROMPT_MEDICAL),
        HumanMessage(content=user_prompt)
    ])
    
    logger.info(f"✓ LLM responded (tool-capable)")
    
        response_text = None
    if hasattr(llm_response, 'tool_calls') and llm_response.tool_calls:
        logger.info(f"🔧 LLM called tool: {llm_response.tool_calls[0]['name']}")
        
                for tool_call in llm_response.tool_calls:
            if tool_call['name'] == 'get_available_doctors':
                                medical_concern = tool_call['args']['medical_concern']
                logger.info(f"📋 Getting doctors for: {medical_concern}")
                
                tool_result = _get_available_doctors_impl(medical_concern)
                
                                messages_for_continuation = [
                    SystemMessage(content=SYSTEM_PROMPT_MEDICAL),
                    HumanMessage(content=user_prompt),
                    llm_response,
                    ToolMessage(content=tool_result, tool_call_id=tool_call['id'])
                ]
                
                                final_response = llm_with_tools.invoke(messages_for_continuation)
                response_text = get_response_text(final_response)
                logger.info(f"✓ LLM final response after tool use")
    
        if response_text is None:
        response_text = get_response_text(llm_response)
        logger.info(f"✓ LLM responded without tools")
    
        suggested_doctor_ids = extract_doctor_ids(response_text)
    
        add_message(db, state["id"], "assistant", response_text)
    
        final_summary = generate_summary(db, state["id"])
    
    record = get_conversation(db, state["id"])
    
        state["response"] = response_text
    state["message_count"] = record.message_count
    state["summary"] = final_summary
    state["suggested_doctor_ids"] = suggested_doctor_ids
    
    logger.info(f"✓ [CHAT NODE] Completed for {state['id']}")
    
    return state

def medical_records_node(state: RouterState) -> RouterState:
    logger.info(f"🔹 [MEDICAL RECORDS NODE] Processing: id={state['id']}")
    
    db = state["db_session"]
    patient_id = state["id"]
    user_message = state["message"]
    uploaded_files = state["uploaded_files"]
    
                messages = add_message(db, patient_id, "user", user_message)
    logger.info(f"✓ Added user message to DB")
    
                logger.info(f"📸 Received {len(uploaded_files)} uploaded file(s)")
    
    if not uploaded_files:
        logger.warning(f"⚠️ No files uploaded")
        response_text = """To analyze your medical records, please upload image files using the 'Choose Files' button.

Supported formats:
- JPG/JPEG
- PNG
- GIF
- WebP

Medical records can include:
- Prescriptions
- Lab results
- Diagnostic reports
- Medical bills
- Appointment letters
- Hospital discharge summaries"""
        add_message(db, patient_id, "assistant", response_text)
        state["response"] = response_text
        state["message_count"] = 2
        state["summary"] = "User requested medical record analysis but no files uploaded"
        state["suggested_doctor_ids"] = []
        return state
    
                logger.info(f"⛓️  [CHAIN] Starting medical records image analysis chain...")
    gemini_analysis = invoke_gemini_vision_analysis(uploaded_files)
    
    logger.info(f"✓ [GEMINI VISION] Analysis received")
    
                    record = get_conversation(db, patient_id)
    summary = generate_summary(db, patient_id)
    
    context_text = "\n".join([
        f"{msg['role']}: {msg['content']}" 
        for msg in messages
    ])
    
    user_prompt = f"""Conversation context:
{context_text}

Summary: {summary}

A Gemini AI model has analyzed the patient's uploaded medical record images:

=== GEMINI VISION ANALYSIS ===
{gemini_analysis}

=== YOUR TASK ===
Read the Gemini analysis of the medical record images and provide:
1. A clear summary of what the medical records show
2. Any health concerns identified
3. Recommendations for follow-up
4. Suggestions to discuss with their doctor

Be professional, empathetic, and patient-friendly."""
    
    logger.info(f"🤖 [MAIN LLM] Building response based on Gemini Vision analysis...")
    
                    llm_response = llm_chat.invoke([
        SystemMessage(content=SYSTEM_PROMPT_MEDICAL),
        HumanMessage(content=user_prompt)
    ])
    
    response_text = get_response_text(llm_response)
    logger.info(f"✓ [MAIN LLM] Generated response based on Gemini Vision analysis")
    
                    add_message(db, patient_id, "assistant", response_text)
    logger.info(f"✓ Stored ONLY main LLM response in DB")
    logger.info(f"  (Gemini Vision analysis not persisted to DB)")
    logger.info(f"  (Uploaded file data not stored in DB)")
    
                final_summary = generate_summary(db, patient_id)
    
    record = get_conversation(db, patient_id)
    
                state["response"] = response_text
    state["message_count"] = record.message_count
    state["summary"] = final_summary
    state["suggested_doctor_ids"] = []
    
    logger.info(f"✓ [MEDICAL RECORDS NODE] Completed for {state['id']}")
    
    return state

def route_handler(state: RouterState) -> str:
    route = state["route"]
    logger.info(f"🔀 [ROUTER] Routing to: {route}")
    
        route_map = {
        "chat": "chat",
        "medical_records": "medical_records",
    }
    
    return route_map.get(route, "chat")

def route_decision(state: RouterState) -> str:
    route = state.get("route", "chat")
    logger.info(f"🔀 [ROUTER] Route decision: {route}")
    
    if route == "medical_records":
        return "medical_records"
    else:
        return "chat"

graph = StateGraph(RouterState)

graph.add_node("chat", chat_node)
graph.add_node("medical_records", medical_records_node)

graph.add_conditional_edges(
    START,
    route_decision,
    {
        "chat": "chat",
        "medical_records": "medical_records"
    }
)

graph.add_edge("chat", END)
graph.add_edge("medical_records", END)

router_app = graph.compile()

logger.info("✓ LangGraph router compiled successfully")

app = FastAPI(title="Telemedicine v6 - With LangGraph Router")

@app.get("/")
def root():
    return {
        "status": "✓ Running",
        "description": "Brick 1 with LangGraph Router - Medical Telemedicine",
        "database": "SQLite",
        "llm": "Google Gemini 2.0 Flash (Main LLM - Orchestration & Response)",
        "summary_model": "Google Gemini 2.0 Flash (Summary Generation)",
        "vision_model": "Google Gemini 1.5 Flash (Medical Image Analysis)",
        "router": "LangGraph with multi-route support",
        "routes_available": [
            {
                "name": "chat",
                "description": "Medical chat with doctor suggestions"
            },
            {
                "name": "medical_records",
                "description": "Analyze medical record images with Gemini Vision"
            }
        ],
        "routes_coming_soon": ["booking", "analytics", "appointment_checking"],
        "doctor_database": "Dynamic (fetched from external API based on patient's medical concern)",
        "tools": [
            "get_available_doctors (Chat route - dynamically calls external API)"
        ],
        "note": "All models powered by Google Gemini API. Doctors are fetched dynamically from your database."
    }

@app.post("/chat", response_model=MessageResponse)
async def chat(
    id: str = Form(...),
    message: str = Form(...),
    route: str = Form(default="chat"),
    files: List[UploadFile] = File(default=[])
):
    logger.info(f"🔹 Request: id={id}, message_len={len(message)}, route={route}, files={len(files) if files else 0}")
    
    db = SessionLocal()
    
    try:
                uploaded_files = []
        
        if files:
            for file in files:
                logger.info(f"📸 Processing uploaded file: {file.filename}")
                
                                content = await file.read()
                
                                mime_type = file.content_type or "image/jpeg"
                
                logger.info(f"  ✓ File loaded: {file.filename} ({len(content)} bytes, {mime_type})")
                
                uploaded_files.append((content, mime_type))
        
                result = router_app.invoke({
            "id": id,
            "message": message,
            "route": route,
            "uploaded_files": uploaded_files,
            "db_session": db,
            "response": "",
            "message_count": 0,
            "summary": "",
            "suggested_doctor_ids": []
        })
        
                        doctor_ids = result["suggested_doctor_ids"]
        if not isinstance(doctor_ids, list):
            doctor_ids = list(doctor_ids) if doctor_ids else []
                doctor_ids = [str(id) for id in doctor_ids]
        
                cleaned_response = clean_doctor_ids_from_response(str(result["response"]))
        
        return MessageResponse(
            id=str(result["id"]),
            response=cleaned_response,
            message_count=int(result["message_count"]),
            summary=str(result["summary"]),
            suggested_doctor_ids=doctor_ids,
            route=str(result["route"])
        )
    
    except Exception as e:
        logger.error(f"✗ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()

@app.get("/debug/{patient_id}")
def debug_conversation(patient_id: str):
    db = SessionLocal()
    
    try:
        record = get_conversation(db, patient_id)
        messages = json.loads(record.messages)
        
        return {
            "patient_id": patient_id,
            "total_messages_ever": record.message_count,
            "last_5_messages": messages,
            "summary": record.summary,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat()
        }
    
    finally:
        db.close()

@app.delete("/debug/{patient_id}")
def delete_conversation(patient_id: str):
    db = SessionLocal()
    
    try:
        deleted = delete_record(db, patient_id)
        
        return {
            "patient_id": patient_id,
            "deleted": deleted
        }
    
    finally:
        db.close()

@app.get("/doctors")
def list_doctors():
    return {
        "status": "✓ Dynamic doctor fetching enabled",
        "source": f"{EXTERNAL_API_BASE_URL}{EXTERNAL_API_DOCTOR_ENDPOINT}",
        "description": "Doctors are fetched dynamically based on patient's medical concern",
        "how_it_works": {
            "step_1": "Patient sends message with medical concern",
            "step_2": "System maps concern to medical specialty",
            "step_3": "External API is queried for doctors in that specialty",
            "step_4": "LLM reviews results and suggests appropriate doctor"
        },
        "example_flow": {
            "patient_message": "I have chest pain",
            "mapped_specialty": "Cardiology",
            "api_called": f"{EXTERNAL_API_BASE_URL}{EXTERNAL_API_DOCTOR_ENDPOINT}?specialty=Cardiology",
            "result": "List of available cardiologists"
        },
        "supported_specialties": list(set(CONCERN_TO_SPECIALTY_MAP.values())),
        "note": "To see doctors, send a message to /chat endpoint with a medical concern"
    }

@app.get("/prompts")
def view_prompts():
    return {
        "system_prompt_medical": SYSTEM_PROMPT_MEDICAL,
        "system_prompt_summary": SYSTEM_PROMPT_SUMMARY,
        "tools": [
            "get_available_doctors (Chat route - calls external API dynamically)"
        ],
        "vision_analysis": "Gemini Vision (not a tool, invoked directly in medical_records_node)",
        "doctor_fetching": "Dynamic (fetched from external API based on patient concern)",
        "medical_concern_mappings": CONCERN_TO_SPECIALTY_MAP,
        "architecture": {
            "chat_route": "Main LLM → Optional tool calls to get_available_doctors → Doctor suggestions",
            "medical_records_route": "User uploads images → Gemini Vision analyzes → Main LLM summarizes → DB stores Main LLM response only"
        }
    }

@app.get("/routes")
def view_routes():
    return {
        "available_routes": [
            {
                "name": "chat",
                "description": "Medical chat with doctor suggestions",
                "tool_use": "get_available_doctors (optional)",
                "status": "✅ Active",
                "example": '{"id": "user1", "message": "I have a headache", "route": "chat"}'
            },
            {
                "name": "medical_records",
                "description": "Analyze medical record images with Gemini Vision",
                "vision_model": "Gemini Pro Vision (NOT optional, always used)",
                "flow": "User uploads images → Gemini Vision analyzes → Main LLM reads analysis → Main LLM builds response → DB stores ONLY Main LLM response",
                "status": "✅ Active",
                "example": '{"id": "user1", "message": "analyze|/path/to/prescription.jpg,/path/to/lab.png", "route": "medical_records"}',
                "supported_formats": ["JPG", "PNG", "JPEG"]
            }
        ],
        "coming_soon": [
            "booking - Book appointments",
            "analytics - View health analytics",
            "appointment_checking - Check existing appointments"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)