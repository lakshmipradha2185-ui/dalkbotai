import streamlit as st
import os
import io
import base64
import json
import speech_recognition as sr
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from PyPDF2 import PdfReader
from docx import Document
from gtts import gTTS
from audio_recorder_streamlit import audio_recorder
from pptx import Presentation
from PIL import Image
import pytesseract
import time

# Load environment variables
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# Set page configuration
st.set_page_config(
    page_title="DalkBot AI | Academic OS",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"
if "is_guest" not in st.session_state:
    st.session_state.is_guest = False

# User Data Management
def load_users():
    try:
        if os.path.exists("users.json"):
            with open("users.json", "r") as f:
                return json.load(f)
    except:
        pass
    return []

def save_user(email, password):
    users = load_users()
    if any(u['email'] == email for u in users):
        return False
    users.append({"email": email, "password": password})
    with open("users.json", "w") as f:
        json.dump(users, f)
    return True

def authenticate_user(email, password):
    users = load_users()
    return any(u['email'] == email and u['password'] == password for u in users)

def show_entrance():
    # Branded Header
    cols = st.columns([1, 2, 1])
    with cols[1]:
        if os.path.exists("logo.png"):
            with open("logo.png", "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                st.markdown(f'<div style="text-align:center;"><img src="data:image/png;base64,{b64}" style="width:180px; border-radius:50%; border:4px solid #000080; box-shadow:0 10px 20px rgba(0,0,0,0.2);"></div>', unsafe_allow_html=True)
        
        st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>DalkBot AI</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 1.2rem; color: #666;'>Your Professional Academic OS</p>", unsafe_allow_html=True)
        
        # Entrance Card
        with st.container(border=True):
            if st.session_state.auth_mode == "login":
                st.subheader("Welcome Back! 🤖")
                email = st.text_input("Email", placeholder="name@email.com")
                password = st.text_input("Password", type="password")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Login"):
                        if authenticate_user(email, password):
                            st.session_state.authenticated = True
                            st.session_state.user_email = email
                            st.rerun()
                        else:
                            st.error("Wrong details!")
                with c2:
                    if st.button("Sign Up"):
                        st.session_state.auth_mode = "signup"
                        st.rerun()
            
            else:
                st.subheader("Create Account 🎓")
                new_email = st.text_input("New Email", placeholder="name@email.com")
                new_pass = st.text_input("New Password", type="password")
                if st.button("Register Now"):
                    if "@" in new_email and len(new_pass) >= 6:
                        if save_user(new_email, new_pass):
                            st.success("Success! Please Login.")
                            st.session_state.auth_mode = "login"
                            st.rerun()
                        else:
                            st.error("User exists.")
                    else:
                        st.error("Invalid email/password.")
                if st.button("Back to Login"):
                    st.session_state.auth_mode = "login"
                    st.rerun()
            
            st.divider()
            if st.button("🚀 Skip Login / Continue as Guest", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.user_email = "Guest User"
                st.session_state.is_guest = True
                st.rerun()

# Custom Global Styling
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    h1, h2, h3 { color: #000080 !important; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #E0F7FA !important; }
    
    /* Login Page Styling */
    .auth-container {
        max-width: 450px;
        margin: auto;
        padding: 40px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        text-align: center;
        margin-top: 50px;
    }
    .auth-logo { width: 150px; border-radius: 50%; margin-bottom: 20px; border: 3px solid #000080; }
    
    /* Sidebar Logo */
    .sidebar-logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 25px;
    }
    .sidebar-logo {
        width: 160px;
        height: 160px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #000080;
        box-shadow: 0 0 15px rgba(0,0,128,0.2);
    }
    .stButton>button { width: 100%; border-radius: 10px; height: 45px; background-color: #000080; color: white; border: none; font-weight: bold; }
    .stButton>button:hover { background-color: #0000CD; border: none; color: white; }
    
</style>
""", unsafe_allow_html=True)

# Authentication logic
if not st.session_state.authenticated:
    show_entrance()
    st.stop()

# --- MAIN APP UI --- (Only shown if logged in)

# Application Title and description
st.title("🤖 DalkBot AI")
st.markdown(f"**Welcome, {st.session_state.user_email}! Your personalized academic companion.**")

# Helper functions
def get_content_as_string(content):
    if isinstance(content, list):
        text = ""
        for part in content:
            if isinstance(part, dict) and "text" in part:
                text += part["text"]
            elif isinstance(part, str):
                text += part
        return text
    return str(content) if content is not None else ""

def extract_text_from_files(uploaded_files):
    text = ""
    for file in uploaded_files:
        try:
            if file.name.endswith(".pdf"):
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    extracted = page.extract_text()
                    if extracted: text += extracted + "\n"
            elif file.name.endswith(".docx"):
                doc = Document(file)
                for para in doc.paragraphs: text += para.text + "\n"
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")
    return text

# Sidebar
with st.sidebar:
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
            st.markdown(f'<div class="sidebar-logo-container"><img src="data:image/png;base64,{data}" class="sidebar-logo"></div>', unsafe_allow_html=True)
    
    st.write(f"Logged in: **{st.session_state.user_email}**")
    if st.button("Logout / Sign In"):
        st.session_state.authenticated = False
        st.session_state.user_email = ""
        st.session_state.is_guest = False
        st.rerun()
    st.divider()

    st.header("⚙️ Academic Tools")
    mode = st.selectbox("Select Mode", ["📝 General Chat", "💻 Coding Assistant", "📊 Study Planner", "📄 Document Chat (PDF/Word)", "📸 Image Assistant"])
    
    if mode == "📸 Image Assistant":
        st.header("📸 Image Upload")
        uploaded_image = st.file_uploader("Upload Problem", type=['png', 'jpg', 'jpeg'])
        if uploaded_image:
            image = Image.open(uploaded_image)
            st.image(image, use_container_width=True)
            if st.button("Analyze Image"):
                ocr_text = ""
                try: ocr_text = pytesseract.image_to_string(image)
                except: pass
                if not ocr_text.strip(): ocr_text = "[IMAGE_VISION_REQUIRED]"
                st.session_state.image_context = ocr_text
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                st.session_state.current_image_bytes = img_byte_arr.getvalue()
                trigger_prompt = f"Analyze this image: '{ocr_text}'" if ocr_text != "[IMAGE_VISION_REQUIRED]" else "Analyze the attached image."
                if "messages" not in st.session_state: st.session_state.messages = []
                st.session_state.messages.append(HumanMessage(content=trigger_prompt))
                st.success("Ready!")

    st.header("📂 Document Upload")
    uploaded_files = st.file_uploader("Upload (.pdf, .docx)", accept_multiple_files=True, type=['pdf', 'docx'])
    if st.button("Process Docs"):
        if uploaded_files:
            with st.spinner("Processing..."):
                doc_text = extract_text_from_files(uploaded_files)
                if doc_text.strip():
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                    chunks = text_splitter.split_text(doc_text)
                    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", transport="rest")
                    vectors = FAISS.from_texts(chunks, embedding=embeddings)
                    st.session_state.vector_store = vectors
                    st.success("Processed!")
        else: st.warning("Upload files.")

    st.sidebar.info("🌍 Supports English & Tamil\n\n💡 Creative Enhancement: Enabled")
    
    if st.sidebar.button("🗑️ Clear Chat History"):
        st.session_state.messages = [AIMessage(content="Hello! I am DalkBot AI. How can I assist you today?")]
        st.rerun()
    
    auto_tts = st.sidebar.checkbox("🔊 Enable Voice Response", value=False)
    st.sidebar.divider()
    audio_bytes = audio_recorder(text="Voice Input", recording_color="#e83e8c", icon_size="2x")

# Main Chat
if "messages" not in st.session_state:
    st.session_state.messages = [AIMessage(content="Hello! I am DalkBot AI. How can I assist you today?")]

for message in st.session_state.messages:
    role = "assistant" if isinstance(message, AIMessage) else "user" if isinstance(message, HumanMessage) else "system"
    if role != "system":
        with st.chat_message(role):
            # Safe extraction for linter and runtime stability
            msg_text = getattr(message, "content", "")
            st.markdown(get_content_as_string(msg_text))

@st.cache_resource
def get_llm(api_key):
    if not api_key:
        return None
    try:
        # Priority 1: High-availability Gemma
        return ChatGoogleGenerativeAI(model="gemma-3-1b-it", temperature=0.7)
    except Exception:
        try:
            return ChatGoogleGenerativeAI(model="gemini-1.5-flash-8b", temperature=0.7, transport="rest")
        except Exception:
            try:
                return ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", temperature=0.7, transport="rest")
            except Exception:
                return None

# Read key and pass to cached function
api_key_val = os.getenv("GOOGLE_API_KEY")
llm_instance = get_llm(api_key_val)
system_text = """You are DalkBot AI, a premium academic tutor. 
1. Multilingual: Expertly support English, Tamil, and other languages.
2. Clarity: Provide clean, clear, step-by-step academic solutions.
3. Creativity: If a user's idea is vague, enhance it creatively and provide structured guidance.
4. Tone: Professional, encouraging, and highly educational."""

prompt = st.chat_input("Ask anything in English or Tamil...")
if audio_bytes and ("last_audio" not in st.session_state or st.session_state.last_audio != audio_bytes):
    st.session_state.last_audio = audio_bytes
    r = sr.Recognizer()
    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            prompt = r.recognize_google(r.record(source))
    except: pass

if prompt:
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        placeholder = st.empty()
        if not llm_instance: placeholder.error("API Key missing.")
        else:
            try:
                msg_content = prompt
                if mode == "📄 Document Chat (PDF/Word)" and "vector_store" in st.session_state:
                    # Reducing k from 4 to 2 to save input tokens and quota
                    docs = st.session_state.vector_store.similarity_search(prompt, k=2)
                    msg_content = f"Context: {' '.join([d.page_content for d in docs])}\nQuestion: {prompt}"
                
                # Ultra-aggressive history limit (last 3 messages)
                limited_history = st.session_state.messages[-3:]
                
                # Special handling for Gemma: Prepend system prompt to the first human message
                # because Gemma-3-1b does not support standard 'SystemMessage' (Developer Instructions)
                if llm_instance and "gemma" in llm_instance.model:
                    messages = []
                    for i, m in enumerate(limited_history):
                        if i == 0 and isinstance(m, HumanMessage):
                            messages.append(HumanMessage(content=f"{system_text}\n\nUser Question: {m.content}"))
                        else:
                            messages.append(m)
                    # If history is empty or first isn't human, just add it
                    if not messages:
                        messages = [HumanMessage(content=f"{system_text}\n\nStart conversation.")]
                else:
                    messages = [SystemMessage(content=system_text)] + limited_history
                    
                current_retry: int = 0
                max_retries: int = 3
                
                while current_retry < max_retries:
                    try:
                        # Ensure llm exists
                        if llm_instance is None:
                            placeholder.error("AI Model initialization failed.")
                            break
                            
                        temp_response: str = ""
                        for chunk in llm_instance.stream(messages):
                            # Ensure chunk.content exists and is string
                            chunk_text = ""
                            if hasattr(chunk, "content"):
                                chunk_text = get_content_as_string(chunk.content)
                            
                            temp_response = temp_response + chunk_text
                            placeholder.markdown(temp_response + "▌")
                        
                        full_response = temp_response
                        placeholder.markdown(full_response)
                        break # Success!
                        
                    except Exception as e:
                        err_msg = str(e)
                        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                            current_retry = current_retry + 1
                            if current_retry < max_retries:
                                wait = current_retry * 25 # Increased wait to 25s for stable reset
                                placeholder.warning(f"⏳ Free Tier Limit. Resetting in {wait}s... ({current_retry}/{max_retries})")
                                time.sleep(wait)
                            else:
                                placeholder.error("🚫 API Quota exhausted. Please try again in 1 minute.")
                                full_response = ""
                        else:
                            # Propagate non-quota errors
                            placeholder.error(f"⚠️ AI Error: {err_msg}")
                            full_response = ""
                            break
                
                if full_response:
                    st.session_state.messages.append(AIMessage(content=full_response))
                    if auto_tts:
                        try:
                            audio_text = full_response[:500]
                            tts = gTTS(text=audio_text, lang='en')
                            fp = io.BytesIO()
                            tts.write_to_fp(fp)
                            fp.seek(0)
                            b64 = base64.b64encode(fp.read()).decode()
                            st.markdown(f'<audio autoplay="true" style="display:none;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
                        except Exception:
                            pass
                    st.rerun() # Only rerun if response was successful
            except Exception as e: placeholder.error(f"Error: {e}")
