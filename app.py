import streamlit as st
from docx import Document
import fitz  # PyMuPDF
import os
import tempfile
from google.cloud import texttospeech
import google.generativeai as genai

# --- INITIALIZATION ---

# Configure Google APIs
try:
    # Used for Text-to-Speech
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        f.write(st.secrets["gcp"]["credentials"].encode())
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name
    
    # Used for Text Generation & Summarization
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
except KeyError as e:
    st.error(f"Secret not found: {e}. Please check your .streamlit/secrets.toml file.")
except Exception as e:
    st.error(f"Failed to configure Google APIs: {e}")


# --- HELPER FUNCTIONS ---

def extract_text(file):
    """Extracts text from uploaded .txt, .pdf, or .docx files."""
    file_extension = os.path.splitext(file.name)[1]
    
    if file_extension == ".txt":
        return file.read().decode("utf-8")
    elif file_extension == ".pdf":
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "\n".join([page.get_text() for page in doc])
    elif file_extension in [".docx", ".doc"]:
        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    return None

# NEW FUNCTION: Uses Gemini API for summarization
def summarize_with_gemini(text_to_summarize):
    """Summarizes text using the Gemini API."""
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"Please summarize the following text in a concise and clear manner, suitable for a short podcast script:\n\n---\n\n{text_to_summarize}"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"An error occurred during summarization: {e}")
        return None

# MODIFIED FUNCTION: Uses Gemini API for text generation
def generate_text_from_topic(topic):
    """Generates a short article on a given topic using the Gemini API."""
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"Generate a short, engaging article about '{topic}', suitable for a mini-podcast. Aim for about 300 words."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"An error occurred while generating text: {e}")
        return None

def synthesize_speech(text, output_path):
    """Synthesizes text into an MP3 audio file using Google Cloud TTS."""
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", name="en-US-Wavenet-F")
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    with open(output_path, "wb") as out:
        out.write(response.audio_content)

# --- STREAMLIT UI ---

st.set_page_config(page_title="Content to Podcast", layout="wide")
st.title("📄 ➡️ 🎧 Content to Podcast Generator")
st.markdown("Turn any document or topic into a short, listenable audio podcast!")

tab1, tab2 = st.tabs(["▶️ From a Document", "▶️ From a Topic"])

# --- TAB 1: Process from a Document (Now using Gemini for summary) ---
with tab1:
    st.header("Upload a Document")
    uploaded_file = st.file_uploader("Upload a .txt, .pdf, or .docx file.", type=["txt", "pdf", "docx", "doc"])
    if uploaded_file:
        raw_text = extract_text(uploaded_file)
        if raw_text:
            st.subheader("📃 Document Preview")
            st.text_area("Preview:", raw_text[:1500] + "...", height=200)
            if st.button("🔍 Summarize and 🎤 Generate Podcast", key="summarize_btn"):
                with st.spinner("Summarizing the document with Gemini... ⏳"):
                    summary = summarize_with_gemini(raw_text)
                
                if summary:
                    st.success("Summary Ready!")
                    st.subheader("✍️ Generated Summary")
                    st.write(summary)
                    with st.spinner("Generating audio podcast... 🎙️"):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio_file:
                            synthesize_speech(summary, tmp_audio_file.name)
                            audio_path = tmp_audio_file.name
                    st.success("🎧 Audio Ready!")
                    with open(audio_path, "rb") as f:
                        st.audio(f.read(), format="audio/mp3")
                    os.remove(audio_path)
        else:
            st.error("Unsupported file type or failed to extract text.")

# --- TAB 2: Process from a Topic ---
with tab2:
    st.header("Generate from a Topic")
    topic_input = st.text_input("Enter a topic:", placeholder="e.g., The history of coffee")
    if st.button("✍️ Generate Text & 🎤 Podcast", key="generate_btn"):
        if topic_input:
            with st.spinner(f"Generating an article about '{topic_input}' with Gemini... 🧠"):
                generated_text = generate_text_from_topic(topic_input)
            if generated_text:
                st.success("Article Ready!")
                st.subheader("✍️ Generated Text")
                st.write(generated_text)
                with st.spinner("Generating audio podcast... 🎙️"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio_file:
                        synthesize_speech(generated_text, tmp_audio_file.name)
                        audio_path = tmp_audio_file.name
                st.success("🎧 Audio Ready!")
                with open(audio_path, "rb") as f:
                    audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")
                st.download_button("⬇️ Download Podcast", data=audio_bytes, file_name=f"{topic_input.replace(' ', '_')}.mp3", mime="audio/mp3")
                os.remove(audio_path)
        else:
            st.warning("Please enter a topic first!")
