import streamlit as st
import requests
from io import BytesIO
import time
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AI Walkthrough", 
    page_icon="✨", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# CUSTOM CSS - Mobile Optimized
# ==========================================
st.markdown("""
<style>
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Full screen layout */
    .block-container {
        padding: 1rem 1rem 1rem 1rem;
        max-width: 100%;
    }
    
    /* Header styling */
    .app-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .app-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
    }
    
    .app-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 0.9rem;
    }
    
    /* Action card styling */
    .action-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 2px solid #f0f2f6;
    }
    
    .action-card:hover {
        border-color: #667eea;
        transition: all 0.3s ease;
    }
    
    .card-title {
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        color: #1f2937;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .card-subtitle {
        color: #6b7280;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    
    /* Status badge */
    .status-badge {
        display: inline-block;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.2rem;
    }
    
    .badge-success {
        background: #d1fae5;
        color: #065f46;
    }
    
    .badge-info {
        background: #dbeafe;
        color: #1e40af;
    }
    
    .badge-warning {
        background: #fef3c7;
        color: #92400e;
    }
    
    /* Quick stats */
    .stats-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 0.8rem;
        margin: 1rem 0;
    }
    
    .stat-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
    }
    
    .stat-label {
        font-size: 0.8rem;
        opacity: 0.9;
        margin-top: 0.3rem;
    }
    
    /* Recording indicator */
    .recording-indicator {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 1rem;
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        border-radius: 12px;
        font-weight: 600;
        font-size: 1rem;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
    }
    
    .pulse {
        width: 12px;
        height: 12px;
        background: white;
        border-radius: 50%;
        animation: pulse 1.5s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.2); }
    }
    
    /* Session info */
    .session-info {
        background: #f9fafb;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    
    .session-info-title {
        font-weight: 600;
        color: #374151;
        margin-bottom: 0.5rem;
    }
    
    .session-id {
        font-family: monospace;
        font-size: 0.85rem;
        color: #6b7280;
        word-break: break-all;
    }
    
    /* Transcription box */
    .transcription-box {
        background: #f0fdf4;
        border: 2px solid #86efac;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .transcription-title {
        font-weight: 600;
        color: #166534;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .transcription-text {
        color: #15803d;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    /* Success message */
    .success-message {
        background: #dcfce7;
        border: 2px solid #4ade80;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        color: #166534;
        font-weight: 600;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE
# ==========================================
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'photo_count' not in st.session_state:
    st.session_state.photo_count = 0
if 'audio_count' not in st.session_state:
    st.session_state.audio_count = 0
if 'report_data' not in st.session_state:
    st.session_state.report_data = None
if 'is_recording' not in st.session_state:
    st.session_state.is_recording = False
if 'continuous_recording' not in st.session_state:
    st.session_state.continuous_recording = False
if 'last_transcription' not in st.session_state:
    st.session_state.last_transcription = None
if 'show_report' not in st.session_state:
    st.session_state.show_report = False
if 'previous_camera_value' not in st.session_state:
    st.session_state.previous_camera_value = None
if 'previous_audio_value' not in st.session_state:
    st.session_state.previous_audio_value = None

# ==========================================
# API FUNCTIONS
# ==========================================

def check_api():
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=3)
        return r.status_code == 200
    except:
        return False

def start_session():
    try:
        r = requests.post(f"{API_BASE_URL}/walkthrough/start")
        if r.status_code == 200:
            data = r.json()
            st.session_state.session_id = data['session_id']
            st.session_state.photo_count = 0
            st.session_state.audio_count = 0
            st.session_state.report_data = None
            st.session_state.show_report = False
            return True, data
        return False, "Failed to start"
    except Exception as e:
        return False, str(e)

def upload_photos(files):
    try:
        files_payload = [('files', (f.name, f, f.type)) for f in files]
        r = requests.post(
            f"{API_BASE_URL}/walkthrough/{st.session_state.session_id}/upload/photo",
            files=files_payload
        )
        return r.status_code == 200, r.json() if r.status_code == 200 else r.text
    except Exception as e:
        return False, str(e)

def upload_audio(audio_file):
    try:
        files = {'file': (audio_file.name, audio_file, audio_file.type)}
        r = requests.post(
            f"{API_BASE_URL}/walkthrough/{st.session_state.session_id}/upload/audio",
            files=files
        )
        return r.status_code == 200, r.json() if r.status_code == 200 else r.text
    except Exception as e:
        return False, str(e)

def generate_report():
    try:
        r = requests.post(f"{API_BASE_URL}/walkthrough/{st.session_state.session_id}/generate")
        return r.status_code == 200, r.json() if r.status_code == 200 else r.text
    except Exception as e:
        return False, str(e)

def get_session_details():
    try:
        r = requests.get(f"{API_BASE_URL}/walkthrough/{st.session_state.session_id}")
        if r.status_code == 200:
            return True, r.json()
        return False, f"Failed to fetch details: {r.text}"
    except Exception as e:
        return False, str(e)

def download_pdf():
    try:
        r = requests.get(f"{API_BASE_URL}/walkthrough/{st.session_state.session_id}/report/download")
        return r.status_code == 200, BytesIO(r.content) if r.status_code == 200 else r.text
    except Exception as e:
        return False, str(e)

def get_photo_url(file_path):
    """Generate URL to fetch photo from backend"""
    return f"{API_BASE_URL}/uploads/{file_path}"

def render_report_with_photos(markdown_text, structured_data):
    """Render report and inject photos at [PHOTO_REF:Category] markers"""
    import re
    
    # Get categorized photos from structured data
    categorized_photos = structured_data.get('categorized_photos', {})
    
    # Split report by lines
    lines = markdown_text.split('\n')
    
    for line in lines:
        # Check if line contains photo reference
        photo_ref_match = re.search(r'\[PHOTO_REF:(.+?)\]', line)
        
        if photo_ref_match:
            category = photo_ref_match.group(1)
            st.markdown(f"**📸 Photos for {category} Section:**")
            
            # Find photos for this category
            if category in categorized_photos:
                photos = categorized_photos[category]
                
                # Display photos in grid
                cols = st.columns(min(len(photos), 3))  # Max 3 columns
                
                for idx, photo_data in enumerate(photos):
                    photo_index = photo_data.get('photo_index', 0)
                    
                    with cols[idx % 3]:
                        try:
                            # Fetch photo from API
                            success, details = get_session_details()
                            if success:
                                media_items = details.get('media_items', [])
                                if photo_index < len(media_items):
                                    file_path = media_items[photo_index]['file_path']
                                    photo_url = get_photo_url(file_path)
                                    
                                    # Display image
                                    response = requests.get(photo_url)
                                    if response.status_code == 200:
                                        st.image(
                                            BytesIO(response.content),
                                            caption=f"Photo {photo_index + 1}: {photo_data.get('description', 'No description')}",
                                            use_container_width=True
                                        )
                                    else:
                                        st.caption(f"Photo {photo_index + 1}: {photo_data.get('description', 'Image not available')}")
                        except Exception as e:
                            st.caption(f"Photo {photo_index + 1}: Could not load image")
                
                st.markdown("---")
        else:
            # Regular markdown line - render it
            if line.strip():
                st.markdown(line)

# ==========================================
# APP HEADER
# ==========================================

st.markdown("""
<div class="app-header">
    <h1>✨ AI Construction Walkthrough</h1>
    <p>Walk → Snap → Talk → Generate Report</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# API STATUS CHECK
# ==========================================

if not check_api():
    st.error("⚠️ Backend API is not running!")
    st.code("uvicorn app:app --reload --port 8000", language="bash")
    st.stop()

# ==========================================
# SESSION MANAGEMENT
# ==========================================

if not st.session_state.session_id:
    st.markdown("""
    <div class="action-card">
        <div class="card-title">🚀 Ready to Start?</div>
        <div class="card-subtitle">Begin a new walkthrough session to document your site inspection</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🆕 Start New Walkthrough", type="primary", use_container_width=True):
        with st.spinner("Initializing session..."):
            success, result = start_session()
            if success:
                st.success("✅ Session started!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"Failed: {result}")
    st.stop()

# ==========================================
# NAVIGATION - Show "See Report" button if report exists
# ==========================================

if st.session_state.report_data:
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("📄 See Report", type="primary", use_container_width=True):
            st.session_state.show_report = True
            st.rerun()

# If "See Report" is active, show report page
if st.session_state.show_report and st.session_state.report_data:
    st.markdown("""
    <div class="action-card">
        <div class="card-title">📊 Generated Report</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Back button
    if st.button("← Back to Capture", use_container_width=True):
        st.session_state.show_report = False
        st.rerun()
    
    # Report Stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Photos Analyzed", st.session_state.report_data.get('photos_analyzed', 0))
    with col2:
        categories = st.session_state.report_data.get('categories_found', [])
        st.metric("Categories", len(categories))
    with col3:
        st.metric("Status", st.session_state.report_data.get('status', 'Unknown').upper())
    
    # Categories Found
    if categories:
        st.markdown("**📂 Report Sections:**")
        for cat in categories:
            st.markdown(f"""<span class="status-badge badge-info">{cat}</span>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Display Report with Photos Embedded
    report_text = st.session_state.report_data.get('markdown_report', 'No report')
    structured_data = st.session_state.report_data.get('structured_data', {})
    
    render_report_with_photos(report_text, structured_data)
    
    st.markdown("---")
    
    # Direct PDF Download - Opens in New Tab
    pdf_url = f"{API_BASE_URL}/walkthrough/{st.session_state.session_id}/report/download"
    
    st.markdown(f"""
    <a href="{pdf_url}" target="_blank" style="text-decoration: none;">
        <button style="
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            font-size: 1rem;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
            📥 Download PDF Report
        </button>
    </a>
    """, unsafe_allow_html=True)
    
    st.caption("💡 Tip: PDF will open in a new tab. You can save it from there.")
    
    st.stop()

# ==========================================
# ACTIVE SESSION INTERFACE (CAPTURE MODE)
# ==========================================

# Session Info Bar
st.markdown(f"""
<div class="session-info">
    <div class="session-info-title">📋 Active Session</div>
    <div class="session-id">{st.session_state.session_id}</div>
</div>
""", unsafe_allow_html=True)

# Quick Stats
st.markdown(f"""
<div class="stats-container">
    <div class="stat-box">
        <div class="stat-number">{st.session_state.photo_count}</div>
        <div class="stat-label">📸 Photos</div>
    </div>
    <div class="stat-box">
        <div class="stat-number">{st.session_state.audio_count}</div>
        <div class="stat-label">🎙️ Voice Notes</div>
    </div>
    <div class="stat-box">
        <div class="stat-number">{'✅' if st.session_state.report_data else '⏳'}</div>
        <div class="stat-label">📄 Report</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 1. UNIFIED CAPTURE SECTION
# ==========================================

st.markdown("""
<div class="action-card">
    <div class="card-title">📸 Capture Photos</div>
    <div class="card-subtitle">Take photos - they'll upload automatically</div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    camera_photo = st.camera_input("📷 Take Photo", key="camera")
    
    # AUTO-UPLOAD when camera captures a new photo
    if camera_photo is not None and camera_photo != st.session_state.previous_camera_value:
        st.session_state.previous_camera_value = camera_photo
        with st.spinner("📤 Auto-uploading photo..."):
            success, result = upload_photos([camera_photo])
            if success:
                st.session_state.photo_count += 1
                st.markdown('<div class="success-message">✅ Photo uploaded automatically!</div>', unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ Upload failed: {result}")

with col2:
    uploaded_files = st.file_uploader(
        "📁 Or Upload Photos",
        type=['jpg', 'jpeg', 'png', 'heic'],
        accept_multiple_files=True,
        key="file_upload"
    )
    if uploaded_files:
        if st.button(f"📤 Upload {len(uploaded_files)} File(s)", key="upload_files", use_container_width=True):
            with st.spinner("Uploading..."):
                success, result = upload_photos(uploaded_files)
                if success:
                    st.session_state.photo_count += len(uploaded_files)
                    st.success(f"✅ {len(uploaded_files)} uploaded!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"Failed: {result}")

st.markdown("---")

# ==========================================
# 2. VOICE NOTES SECTION
# ==========================================

st.markdown("""
<div class="action-card">
    <div class="card-title">🎙️ Record Voice Notes</div>
    <div class="card-subtitle">Describe what you see - auto-transcribes when you stop</div>
</div>
""", unsafe_allow_html=True)

audio_file = st.audio_input("🎤 Record Voice Note", key="audio")

# AUTO-TRANSCRIBE when audio recording is completed
if audio_file is not None and audio_file != st.session_state.previous_audio_value:
    st.session_state.previous_audio_value = audio_file
    
    with st.spinner("🤖 Auto-transcribing audio..."):
        success, result = upload_audio(audio_file)
        if success:
            st.session_state.audio_count += 1
            st.session_state.last_transcription = result.get('text', 'No text')
            st.markdown('<div class="success-message">✅ Audio transcribed automatically!</div>', unsafe_allow_html=True)
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"❌ Transcription failed: {result}")

# Display last transcription
if st.session_state.last_transcription:
    st.markdown(f"""
    <div class="transcription-box">
        <div class="transcription-title">
            <span>📝</span>
            <span>Latest Transcription:</span>
        </div>
        <div class="transcription-text">{st.session_state.last_transcription}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 3. GENERATE REPORT SECTION
# ==========================================

st.markdown("""
<div class="action-card">
    <div class="card-title">📄 Generate AI Report</div>
    <div class="card-subtitle">Create a professional walkthrough report with AI analysis</div>
</div>
""", unsafe_allow_html=True)

total_content = st.session_state.photo_count + st.session_state.audio_count

if total_content == 0:
    st.warning("⚠️ Add at least one photo or voice note before generating a report")
else:
    st.info(f"✅ Ready to generate report with {st.session_state.photo_count} photos and {st.session_state.audio_count} voice notes")
    
    if st.button("🚀 Generate Report", type="primary", use_container_width=True):
        with st.spinner("🤖 AI is analyzing and categorizing content..."):
            success, result = generate_report()
            if success:
                st.session_state.report_data = result
                st.session_state.show_report = True  # Auto-navigate to report
                st.success("✅ Report generated!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"Failed: {result}")

# ==========================================
# FOOTER
# ==========================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #6b7280; padding: 1rem;'>
    <p style='margin: 0; font-size: 0.9rem;'>AI Construction Walkthrough System</p>
    <p style='margin: 0.3rem 0 0 0; font-size: 0.75rem;'>Powered by Gemini Vision & AssemblyAI</p>
</div>
""", unsafe_allow_html=True)