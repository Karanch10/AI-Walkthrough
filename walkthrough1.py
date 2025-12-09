import streamlit as st
import assemblyai as aai
import google.generativeai as genai
import cv2
from PIL import Image
import io
import tempfile
import time
from datetime import datetime
import base64
from pathlib import Path
import os
from dotenv import load_dotenv
import json
import re

# Load environment variables
load_dotenv()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="AI Walkthrough Note",
    page_icon="👷",
    layout="wide"
)

# --- CONFIGURATION ---
AAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if AAI_API_KEY:
    aai.settings.api_key = AAI_API_KEY
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    vision_model = genai.GenerativeModel('gemini-2.5-flash')

# --- SESSION STATE INITIALIZATION ---
if 'photos' not in st.session_state:
    st.session_state.photos = []
if 'transcripts' not in st.session_state:
    st.session_state.transcripts = []
if 'is_recording' not in st.session_state:
    st.session_state.is_recording = False
if 'report_generated' not in st.session_state:
    st.session_state.report_generated = False
if 'final_report' not in st.session_state:
    st.session_state.final_report = ""
if 'structured_report' not in st.session_state:
    st.session_state.structured_report = None
if 'recording_text' not in st.session_state:
    st.session_state.recording_text = ""
if 'audio_file' not in st.session_state:
    st.session_state.audio_file = None
if 'camera_key' not in st.session_state:
    st.session_state.camera_key = 0

# --- HELPER FUNCTIONS ---
def add_photo(image, description=""):
    """Add photo to session"""
    st.session_state.photos.append({
        'timestamp': datetime.now(),
        'image': image,
        'description': description
    })

def add_transcript(text):
    """Add transcript to session"""
    st.session_state.transcripts.append({
        'timestamp': datetime.now(),
        'text': text
    })

def reset_session():
    """Clear all session data"""
    st.session_state.photos = []
    st.session_state.transcripts = []
    st.session_state.is_recording = False
    st.session_state.report_generated = False
    st.session_state.final_report = ""
    st.session_state.structured_report = None
    st.session_state.recording_text = ""
    st.session_state.audio_file = None
    
def transcribe_audio(audio_file):
    """Transcribe audio file using AssemblyAI"""
    try:
        if not AAI_API_KEY:
            st.error("AssemblyAI API key not configured!")
            return ""
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        tfile.write(audio_file.read())
        tfile.close()
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(tfile.name)
        Path(tfile.name).unlink()
        return transcript.text if transcript.text else ""
    except Exception as e:
        st.error(f"Transcription failed: {e}")
        return ""

def process_video(video_file, extract_audio=True):
    """Extract frames and audio from video"""
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(video_file.read())
    tfile.close()
    cap = cv2.VideoCapture(tfile.name)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames_to_extract = max(1, int(fps * 2))
    extracted_photos = []
    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frames_to_extract == 0:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)
            extracted_photos.append(pil_img)
        frame_idx += 1
    cap.release()
    transcript_text = ""
    if extract_audio and AAI_API_KEY:
        try:
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(tfile.name)
            transcript_text = transcript.text if transcript.text else ""
        except Exception as e:
            st.warning(f"Audio extraction failed: {e}")
    Path(tfile.name).unlink()
    return extracted_photos, transcript_text

def classify_photos_with_ai():
    """Classify photos into categories using Gemini Vision"""
    if not st.session_state.photos or not GOOGLE_API_KEY:
        return {}
    classification_prompt = """Analyze these construction site photos and classify each one into ONE of these categories:
CATEGORIES:
- Safety Issues (hazards, PPE violations, unsafe conditions)
- Structural Work (framing, concrete, foundation, walls)
- Electrical (wiring, panels, outlets, lighting)
- Plumbing (pipes, fixtures, drainage)
- HVAC (ductwork, units, vents)
- Finishes (paint, flooring, trim, tile)
- Exterior (roofing, siding, landscaping)
- Equipment (tools, machinery, vehicles)
- Materials (stored materials, deliveries)
- Progress Overview (wide shots, before/after)
- Quality Issues (defects, rework needed)
- Other

For each photo, respond in this EXACT JSON format:
{
  "classifications": [
    {
      "photo_index": 0,
      "category": "Safety Issues",
      "confidence": "high",
      "description": "Worker without hard hat near scaffolding"
    },
    {
      "photo_index": 1,
      "category": "Structural Work",
      "confidence": "high",
      "description": "Completed concrete foundation"
    }
  ]
}
Respond ONLY with valid JSON, no other text."""
    try:
        content = [classification_prompt] + [photo['image'] for photo in st.session_state.photos]
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        response = vision_model.generate_content(content, safety_settings=safety_settings)        
        response_text = response.text.strip()        
        if response_text.startswith('```'):
            response_text = re.sub(r'^```json?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
        classifications = json.loads(response_text)        
        categorized_photos = {}
        for item in classifications.get('classifications', []):
            idx = item['photo_index']
            category = item['category']
            if 0 <= idx < len(st.session_state.photos):
                if category not in categorized_photos:
                    categorized_photos[category] = []
                confidence = item.get('confidence', 'medium').lower()
                if confidence == "low":
                    continue
                categorized_photos.setdefault(category, []).append({
                    'photo': st.session_state.photos[idx],
                    'description': item.get('description', ''),
                    'confidence': confidence,
                    'index': idx
                })
        return categorized_photos
    
    except Exception as e:
        st.warning(f"Photo classification failed: {e}")
        # Fallback: put all photos in "Progress Overview"
        return {
            "Progress Overview": [
                {
                    'photo': photo,
                    'description': photo.get('description', ''),
                    'confidence': 'low',
                    'index': idx
                }
                for idx, photo in enumerate(st.session_state.photos)
            ]
        }

def map_voice_to_sections(transcript, photo_categories):
    # 1. Handle empty transcript immediately
    if not transcript or not transcript.strip():
        return {}

    # 2. Handle empty categories
    if not photo_categories:
        return {"General Notes": [transcript]}

    categories_list = list(photo_categories.keys())
    
    prompt = f"""
    Map these voice notes to the most relevant construction categories.
    
    Available categories:
    {json.dumps(categories_list, indent=2)}
    
    Voice transcript:
    {transcript}
    
    Return JSON:
    {{
      "mappings": [
        {{
          "segment": "voice sentence",
          "category": "category name"
        }}
      ]
    }}
    Respond ONLY with valid JSON. Do not write "Here is the JSON" or use markdown blocks.
    """
    
    try:
        # Add safety settings to prevent blocking
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        response = vision_model.generate_content(prompt, safety_settings=safety_settings)
        response_text = response.text.strip()
        
        # 3. Clean Markdown formatting (The specific fix for your error)
        if response_text.startswith('```'):
            response_text = re.sub(r'^```json?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            
        result = json.loads(response_text)
        
        voice_by_category = {}
        for item in result.get("mappings", []):
            cat = item.get("category", "General Notes")
            seg = item.get("segment", "")
            voice_by_category.setdefault(cat, []).append(seg)
        return voice_by_category

    except Exception as e:
        print(f"Mapping Error: {e}")
        # Fallback: Just return the whole text under General Notes
        return {"General Notes": [transcript]}

def render_report_with_photos():
    """Render report with photos embedded in sections"""
    if not st.session_state.structured_report:
        return
    
    report_text = st.session_state.structured_report['report_text']
    categorized_photos = st.session_state.structured_report['categorized_photos']
    
    # Split report by [PHOTO_REF:Category] markers
    sections = re.split(r'\[PHOTO_REF:(.*?)\]', report_text)
    
    for i, section in enumerate(sections):
        if i % 2 == 0:
            # Regular text section
            st.markdown(section)
        else:
            # Photo reference - show photos for this category
            category = section.strip()
            if category in categorized_photos:
                photos = categorized_photos[category]
                
                # Display photos in grid
                cols = st.columns(min(3, len(photos)))
                for idx, photo_data in enumerate(photos):
                    with cols[idx % len(cols)]:
                        st.image(
                            photo_data['photo']['image'],
                            caption=f"{photo_data['description'][:50]}..." if photo_data['description'] else f"Photo {photo_data['index'] + 1}",
                            use_container_width=True
                        )


def generate_companycam_report(grouped_photos, voice_by_category):
    sections_payload = []
    for category, photos in grouped_photos.items():
        sections_payload.append({
            "category": category,
            "photo_count": len(photos),
            "photo_descriptions": [p["description"] for p in photos],
            "voice_notes": voice_by_category.get(category, [])
        })
    for category, notes in voice_by_category.items():
        if category not in grouped_photos:
            sections_payload.append({
                "category": category,
                "photo_count": 0,
                "photo_descriptions": [],
                "voice_notes": notes
            })
    final_prompt = f"""
You are writing a professional construction walkthrough report.
Use ONLY this structured input:
{json.dumps(sections_payload, indent=2)}
Instructions:
- Start with Executive Summary
- For each category:
  - Use heading: ## 🔧 Category Name
  - Write 3–5 professional bullet points
  - Add: [PHOTO_REF:Category Name] on a NEW LINE
- End with Action Items and Next Steps
- No filler content
- No hallucination beyond the data provided
"""
    response = vision_model.generate_content(final_prompt)
    return response.text

def generate_structured_report():
    """Main function: batch photo classify → voice map → structured report."""
    if len(st.session_state.photos) == 0 and len(st.session_state.transcripts) == 0:
        st.error("No data to generate report. Please capture photos or record audio.")
        return
    if not GOOGLE_API_KEY:
        st.error("Google API key not configured!")
        return
    with st.spinner("🤖 Classifying photos & generating report..."):
        # 1️⃣ Batch photo classification (FAST)
        categorized_photos = classify_photos_with_ai()
        # 2️⃣ Voice → category mapping
        full_transcript = "\n".join([t["text"] for t in st.session_state.transcripts])
        voice_by_category = map_voice_to_sections(full_transcript, categorized_photos)
        # 3️⃣ CompanyCam-style report
        report_body = generate_companycam_report(categorized_photos, voice_by_category)
        # ✅ Header
        header = f"""# 👷Job Site Walkthrough Report

**Date:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}  
**Photos Captured:** {len(st.session_state.photos)}  
**Categories:** {len(categorized_photos)}  

---

"""
        full_report = header + report_body
        # ✅ Store everything consistently
        st.session_state.final_report = full_report
        st.session_state.structured_report = {
            "report_text": full_report,
            "categorized_photos": categorized_photos,
            "voice_by_category": voice_by_category,
            "timestamp": datetime.now(),
        }
        st.session_state.report_generated = True
        st.success("✅ Report generated successfully!")

def download_report_as_html_enhanced():
    """Create enhanced HTML with photos in sections"""
    if not st.session_state.structured_report:
        return download_report_as_html_simple()
    
    report_text = st.session_state.structured_report['report_text']
    categorized_photos = st.session_state.structured_report['categorized_photos']
    
    # Convert markdown to HTML sections
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Walkthrough Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 1000px; margin: 40px auto; padding: 20px; background: #f5f5f5; }}
        .container {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 4px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 40px; padding-top: 20px; border-top: 2px solid #ecf0f1; }}
        h3 {{ color: #3498db; margin-top: 30px; }}
        .photo-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
        .photo-item {{ background: #f8f9fa; padding: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .photo-item img {{ width: 100%; height: auto; border-radius: 6px; }}
        .photo-caption {{ margin-top: 8px; font-size: 0.9em; color: #555; text-align: center; }}
        ul {{ line-height: 1.8; }}
        li {{ margin-bottom: 8px; }}
        .metadata {{ background: #ecf0f1; padding: 15px; border-radius: 6px; margin: 20px 0; }}
    </style>
</head>
<body>
<div class="container">
"""
    
    # Process report text and insert photos
    sections = re.split(r'\[PHOTO_REF:(.*?)\]', report_text)
    
    for i, section in enumerate(sections):
        if i % 2 == 0:
            # Regular markdown text - simple conversion
            html_section = section.replace('\n## ', '\n<h2>').replace('\n### ', '\n<h3>')
            html_section = html_section.replace('\n# ', '\n<h1>')
            html_section = html_section.replace('\n- ', '\n<li>').replace('\n* ', '\n<li>')
            html_section = html_section.replace('**', '<strong>').replace('**', '</strong>')
            html_content += html_section
        else:
            # Photo section
            category = section.strip()
            if category in categorized_photos:
                html_content += '<div class="photo-grid">'
                for photo_data in categorized_photos[category]:
                    buffered = io.BytesIO()
                    photo_data['photo']['image'].save(buffered, format="JPEG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    
                    html_content += f"""
                    <div class="photo-item">
                        <img src="data:image/jpeg;base64,{img_str}" alt="Photo {photo_data['index'] + 1}"/>
                        <div class="photo-caption">{photo_data['description'] if photo_data['description'] else f"Photo {photo_data['index'] + 1}"}</div>
                    </div>
                    """
                html_content += '</div>'
    
    html_content += """
</div>
</body>
</html>
"""
    return html_content

def download_report_as_html_simple():
    """Fallback simple HTML export"""
    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Walkthrough Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .photo-gallery {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 20px 0; }}
        .photo-item {{ max-width: 300px; }}
        img {{ max-width: 100%; height: auto; border-radius: 8px; }}
    </style>
</head>
<body>
{st.session_state.final_report}
<div class="photo-gallery">
"""
    
    for idx, photo in enumerate(st.session_state.photos, 1):
        buffered = io.BytesIO()
        photo['image'].save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        html_template += f'<div class="photo-item"><img src="data:image/jpeg;base64,{img_str}" alt="Photo {idx}"/><p>Photo {idx}</p></div>'
    
    html_template += """
</div>
</body>
</html>
"""
    return html_template

# --- MAIN UI ---
st.title("👷 AI Walkthrough Note")
st.markdown("**Walk, Talk, Snap Photos → AI Generates Professional Reports with Smart Photo Organization**")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    if not AAI_API_KEY or not GOOGLE_API_KEY:
        st.error("⚠️ API keys not configured!")
        st.markdown("""
        **Setup Instructions:**
        
        1. Create a `.env` file
        2. Add your API keys:
        ```
        ASSEMBLYAI_API_KEY=your_key
        GOOGLE_API_KEY=your_key
        ```
        3. Restart the app
        """)
    else:
        st.success("✅ API Keys Configured")
    
    st.markdown("---")
    st.header("📊 Session Stats")
    st.metric("Photos Captured", len(st.session_state.photos))
    st.metric("Voice Notes", len(st.session_state.transcripts))
    
    if st.session_state.structured_report:
        st.metric("Categories", len(st.session_state.structured_report['categorized_photos']))
    
    st.markdown("---")
    if st.button("🔄 Reset Session", type="secondary", use_container_width=True):
        reset_session()
        st.rerun()

# Main tabs
tab1, tab2, tab3 = st.tabs(["📹 Live Walkthrough", "📤 Upload Files", "📄 Generated Report"])

# --- TAB 1: LIVE WALKTHROUGH ---
with tab1:
    st.header("Live Walkthrough Mode")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎤 Voice Recording")
        
        if not AAI_API_KEY:
            st.warning("⚠️ AssemblyAI API key required")
        
        audio_file = st.audio_input("Record audio")
        
        if audio_file is not None:
            if st.button("📝 Transcribe Audio", use_container_width=True):
                with st.spinner("Transcribing..."):
                    transcript = transcribe_audio(audio_file)
                    if transcript:
                        add_transcript(transcript)
                        st.success("✅ Transcribed!")
                        st.rerun()
        
        if st.session_state.transcripts:
            st.markdown("---")
            st.markdown("**Recent Transcripts:**")
            for t in st.session_state.transcripts[-5:]:
                st.markdown(f"**[{t['timestamp'].strftime('%H:%M:%S')}]** {t['text']}")
            last_text = st.session_state.transcripts[-1]["text"]
            st.write("Last transcript length:", len(last_text))
    with col2:
        st.subheader("📷 Photo Capture")
        input_method = st.radio("Input Method", ["Live Camera", "Native Mobile Camera"], horizontal=True, label_visibility="collapsed")
        if input_method == "Live Camera":
            camera_photo = st.camera_input("Click Photo", key=f"camera_{st.session_state.camera_key}")
            if camera_photo is not None:
                img = Image.open(camera_photo)
                add_photo(img)
                st.toast(f"📸 Photo {len(st.session_state.photos)} captured!", icon="✅")
                st.session_state.camera_key += 1
                st.rerun()
        else:
            mobile_photo = st.file_uploader("Click Photo", type=['jpg', 'jpeg', 'png'], key=f"uploader_{st.session_state.camera_key}")
            if mobile_photo is not None:
                img = Image.open(mobile_photo)
                add_photo(img)
                st.toast(f"📸 Photo {len(st.session_state.photos)} captured!", icon="✅")
                st.session_state.camera_key += 1 
                st.rerun()
    
    if st.session_state.photos:
        st.markdown("---")
        st.subheader(f"📸 Captured Photos ({len(st.session_state.photos)})")
        cols = st.columns(4)
        for idx, photo in enumerate(st.session_state.photos):
            with cols[idx % 4]:
                st.image(photo['image'], caption=f"Photo {idx+1}", use_container_width=True)
    
    st.markdown("---")
    if st.button("🤖 Generate AI Report", type="primary", use_container_width=True, disabled=len(st.session_state.photos)==0 and len(st.session_state.transcripts)==0):
        generate_structured_report()
        st.rerun()

# --- TAB 2: UPLOAD FILES ---
with tab2:
    st.header("Upload Pre-recorded Content")
    
    upload_type = st.radio("Select upload type:", ["🖼️ Multiple Images", "🎤 Audio File"], horizontal=True)
    if upload_type == "🎤 Audio File":
        st.markdown("**Upload an audio recording**")
        audio_upload = st.file_uploader("Choose audio file", type=['wav', 'mp3', 'm4a', 'ogg'])
        
        if audio_upload:
            st.audio(audio_upload)
            
            if st.button("📝 Transcribe", type="primary"):
                with st.spinner("Transcribing..."):
                    transcript = transcribe_audio(audio_upload)
                    if transcript:
                        add_transcript(transcript)
                        st.success("✅ Transcribed!")
                        st.rerun()
    
    else:  # Multiple Images
        st.markdown("**Upload photos from your walkthrough**")
        uploaded_files = st.file_uploader("Choose images", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
        
        if uploaded_files:
            st.info(f"📤 {len(uploaded_files)} images selected")
            
            cols = st.columns(4)
            for idx, file in enumerate(uploaded_files):
                with cols[idx % 4]:
                    img = Image.open(file)
                    st.image(img, caption=file.name, use_container_width=True)
            
            if st.button("✅ Add All Images", type="primary"):
                for file in uploaded_files:
                    img = Image.open(file)
                    add_photo(img, f"Uploaded: {file.name}")
                st.success(f"✅ Added {len(uploaded_files)} photos!")
                st.rerun()
    
    st.markdown("---")
    st.subheader("📝 Add Manual Notes")
    manual_notes = st.text_area("Type your observations:", height=150)
    if st.button("Add Notes"):
        if manual_notes:
            add_transcript(manual_notes)
            st.success("Notes added!")
            st.rerun()

# --- TAB 3: GENERATED REPORT ---
with tab3:
    st.header("Generated Report")
    
    if st.session_state.report_generated:
        # Render report with embedded photos
        render_report_with_photos()
        
        # Download options
        st.markdown("---")
        st.subheader("📥 Download Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            md_content = st.session_state.final_report
            st.download_button(
                label="📄 Download as Markdown",
                data=md_content,
                file_name=f"walkthrough_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        with col2:
            html_content = download_report_as_html_enhanced()
            st.download_button(
                label="🌐 Download as HTML (with photos)",
                data=html_content,
                file_name=f"walkthrough_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                mime="text/html",
                use_container_width=True
            )
        
        # Show photo classification summary
        if st.session_state.structured_report:
            st.markdown("---")
            st.subheader("📊 Photo Classification Summary")
            
            categorized = st.session_state.structured_report['categorized_photos']
            
            cols = st.columns(min(4, len(categorized)))
            for idx, (category, photos) in enumerate(categorized.items()):
                with cols[idx % len(cols)]:
                    st.metric(category, len(photos))
    
    else:
        st.info("👈 Generate a report from the other tabs first!")
        st.markdown("""
        ### 🚀 New Features:
        
        ✅ **Smart Photo Classification**
        - AI automatically categorizes photos (Safety, Structural, Electrical, etc.)
        
        ✅ **Section-Based Photo Layout**
        - Photos appear in relevant report sections (like CompanyCam)
        
        ✅ **Professional Formatting**
        - Clean bullet points and structured sections
        
        ✅ **Enhanced HTML Export**
        - Photos embedded in sections for easy sharing
        """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
        Built with ❤️ using Streamlit, AssemblyAI & Google Gemini<br>
        <small>Enhanced with AI Photo Classification & Structured Reporting</small>
    </div>
    """,
    unsafe_allow_html=True
)