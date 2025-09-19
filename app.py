import streamlit as st
from docx import Document
from transformers import pipeline
import fitz  # PyMuPDF
import os
import tempfile
from google.cloud import texttospeech

# --- INITIALIZATION ---

# Load Google Cloud credentials from secrets and write to a temp file
# This part is crucial for authentication with Google's Text-to-Speech API
with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
    # st.secrets accesses the secrets configured in your Streamlit Cloud account
    f.write(st.secrets["gcp"]["credentials"].encode())
    # Set the environment variable to point to the temporary credentials file
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name

# Initialize the machine learning pipelines
# Summarizer for the document processing part
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
# Text generator for the new topic-based feature
text_generator = pipeline("text-generation", model="gpt-2")

# --- HELPER FUNCTIONS ---

def extract_text(file):
    """Extracts text from uploaded .txt, .pdf, or .docx files."""
    file_extension = os.path.splitext(file.name)[1]
    
    if file_extension == ".txt":
        return file.read().decode("utf-8")

    elif file_extension == ".pdf":
        # Open PDF from the file's byte stream
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "\n".join([page.get_text() for page in doc])

    elif file_extension in [".docx", ".doc"]:
        # python-docx can't read directly from a stream, so we save to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
            temp_file.write(file.read())
            temp_path = temp_file.name
        doc = Document(temp_path)
        os.remove(temp_path) # Clean up the temporary file
        return "\n".join([para.text for para in doc.paragraphs])
    
    return None

def summarize_large_text(text, chunk_size=1024, max_length=150, min_length=40):
    """Summarizes text by breaking it into chunks first."""
    # Pre-process text to ensure clean sentence breaks for chunking
    text = text.replace('.', '.<eos>')
    text = text.replace('?', '?<eos>')
    text = text.replace('!', '!<eos>')
    
    sentences = text.split('<eos>')
    current_chunk = ""
    chunks = []
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence
        else:
            chunks.append(current_chunk)
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk)

    # Summarize each chunk
    summaries = summarizer(chunks, max_length=max_length, min_length=min_length, do_sample=False)
    return " ".join([summary['summary_text'] for summary in summaries])

def generate_text_from_topic(topic, max_length=500):
    """Generates a short article on a given topic using GPT-2."""
    # We create a more descriptive prompt to guide the model
    prompt = f"A short article about {topic}:\n\n"
    generated_list = text_generator(prompt, max_length=max_length, num_return_sequences=1)
    return generated_list[0]['generated_text']


def synthesize_speech(text, output_path):
    """Synthesizes text into an MP3 audio file using Google Cloud TTS."""
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Wavenet-F", # Using a more natural-sounding WaveNet voice
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    with open(output_path, "wb") as out:
        out.write(response.audio_content)

# --- STREAMLIT UI ---

st.set_page_config(page_title="Content to Podcast", layout="wide")
st.title("📄 ➡️ 🎧 Content to Podcast Generator")
st.markdown("Turn any document or topic into a short, listenable audio podcast!")

# Create two tabs for the two different functionalities
tab1, tab2 = st.tabs(["▶️ From a Document", "▶️ From a Topic"])

# --- TAB 1: Process from a Document ---
with tab1:
    st.header("Upload a Document")
    uploaded_file = st.file_uploader(
        "Upload a .txt, .pdf, or .docx file to summarize and convert to audio.",
        type=["txt", "pdf", "docx", "doc"]
    )

    if uploaded_file:
        raw_text = extract_text(uploaded_file)

        if raw_text:
            st.subheader("📃 Document Preview")
            st.text_area("Preview of your document:", raw_text[:1500] + "...", height=200)

            if st.button("🔍 Summarize and 🎤 Generate Podcast", key="summarize_btn"):
                # Step 1: Summarize the text
                with st.spinner("Summarizing the document... This may take a moment. ⏳"):
                    summary = summarize_large_text(raw_text)
                st.success("Summary Ready!")
                st.subheader("✍️ Generated Summary")
                st.write(summary)

                # Step 2: Convert summary to audio
                with st.spinner("Generating audio podcast... 🎙️"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio_file:
                        synthesize_speech(summary, tmp_audio_file.name)
                        audio_path = tmp_audio_file.name
                
                st.success("🎧 Audio Ready!")
                
                # Display audio player and download button
                with open(audio_path, "rb") as f:
                    audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")
                st.download_button(
                    "⬇️ Download Podcast",
                    data=audio_bytes,
                    file_name=f"{os.path.splitext(uploaded_file.name)[0]}_summary.mp3",
                    mime="audio/mp3"
                )
                os.remove(audio_path) # Clean up the temporary audio file
        else:
            st.error("Unsupported file type or failed to extract text.")

# --- TAB 2: Process from a Topic ---
with tab2:
    st.header("Generate from a Topic")
    topic_input = st.text_input("Enter a topic you want to hear a podcast about (e.g., 'The history of coffee'):")

    if st.button("✍️ Generate Text & 🎤 Podcast", key="generate_btn"):
        if topic_input:
            # Step 1: Generate text from the topic
            with st.spinner(f"Generating an article about '{topic_input}'... 🧠"):
                generated_text = generate_text_from_topic(topic_input)
            st.success("Article Ready!")
            st.subheader("✍️ Generated Text")
            st.write(generated_text)

            # Step 2: Convert the generated text to audio
            with st.spinner("Generating audio podcast... 🎙️"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio_file:
                    synthesize_speech(generated_text, tmp_audio_file.name)
                    audio_path = tmp_audio_file.name

            st.success("🎧 Audio Ready!")

            # Display audio player and download button
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            st.audio(audio_bytes, format="audio/mp3")
            st.download_button(
                "⬇️ Download Podcast",
                data=audio_bytes,
                file_name=f"{topic_input.replace(' ', '_')}.mp3",
                mime="audio/mp3"
            )
            os.remove(audio_path) # Clean up the temporary audio file
        else:
            st.warning("Please enter a topic first!")
