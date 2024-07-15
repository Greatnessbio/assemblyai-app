import streamlit as st
import assemblyai as aai
import requests
import json
import os
import tempfile
from moviepy.editor import VideoFileClip
import yt_dlp
import traceback

def download_youtube_audio(url):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = os.path.join(temp_dir, f"{info['id']}.mp3")
                if not os.path.exists(filename):
                    raise Exception(f"Downloaded file not found: {filename}")
                with open(filename, 'rb') as file:
                    audio_data = file.read()
            return audio_data
    except Exception as e:
        st.error(f"Error downloading YouTube audio: {str(e)}")
        st.error(traceback.format_exc())
        return None

def extract_audio_from_video(video_file):
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio_file:
            video = VideoFileClip(video_file.name)
            video.audio.write_audiofile(temp_audio_file.name)
        return temp_audio_file.name
    except Exception as e:
        st.error(f"Error extracting audio from video: {str(e)}")
        st.error(traceback.format_exc())
        return None

@st.cache_data
def summarize_with_openrouter(transcript, api_key):
    YOUR_SITE_URL = "https://your-app-url.com"  # Replace with your actual URL
    YOUR_APP_NAME = "Transcription Analyzer"  # Replace with your app name

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": YOUR_SITE_URL,
                "X-Title": YOUR_APP_NAME,
            },
            json={
                "model": "anthropic/claude-3-sonnet",
                "messages": [
                    {"role": "system", "content": "You are an AI assistant that summarizes transcripts and extracts key information into a table."},
                    {"role": "user", "content": f"Please summarize the following transcript and extract key information into a table:\n\n{transcript}"}
                ]
            }
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling OpenRouter API: {str(e)}")
        st.error(traceback.format_exc())
        return None

# Initialize session state
if 'transcript' not in st.session_state:
    st.session_state.transcript = None
if 'summary' not in st.session_state:
    st.session_state.summary = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Streamlit app
st.set_page_config(page_title="Audio Transcription and Analysis", layout="wide")

st.title("Audio Transcription and Analysis with AssemblyAI and OpenRouter")

# Sidebar for API keys
with st.sidebar:
    st.header("API Keys")
    assemblyai_api_key = st.text_input("Enter your AssemblyAI API key:", type="password")
    openrouter_api_key = st.text_input("Enter your OpenRouter API key:", type="password")

# Main content
if assemblyai_api_key and openrouter_api_key:
    aai.settings.api_key = assemblyai_api_key

    # File input options
    input_option = st.radio("Choose input method:", ["Upload File (up to 200MB)", "Provide URL (including YouTube)"])

    if input_option == "Upload File (up to 200MB)":
        uploaded_file = st.file_uploader("Choose an audio or video file (up to 200MB)", type=["mp3", "wav", "m4a", "mp4"])
        if uploaded_file:
            file_size = uploaded_file.size
            st.write(f"File size: {file_size / (1024 * 1024):.2f} MB")
            if uploaded_file.type == "video/mp4":
                st.video(uploaded_file)
            else:
                st.audio(uploaded_file)
    else:
        file_url = st.text_input("Enter the URL of the audio, video, or YouTube video:")

    # Transcription options
    st.subheader("Transcription and Analysis Options")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        speaker_labels = st.checkbox("Enable Speaker Diarization", help="Detect and label different speakers in the audio")
        sentiment_analysis = st.checkbox("Enable Sentiment Analysis", help="Detect the sentiment of each spoken sentence")
    with col2:
        topic_detection = st.checkbox("Enable Topic Detection", help="Identify different topics in the transcript")
        entity_detection = st.checkbox("Enable Entity Detection", help="Identify and categorize key information")
    with col3:
        auto_chapters = st.checkbox("Enable Auto Chapters", help="Summarize audio data over time into chapters")
        key_phrases = st.checkbox("Enable Key Phrases", help="Identify significant words and phrases")

    if st.button("Transcribe and Analyze"):
        with st.spinner("Processing..."):
            try:
                transcriber = aai.Transcriber()
                
                config = aai.TranscriptionConfig(
                    speaker_labels=speaker_labels,
                    sentiment_analysis=sentiment_analysis,
                    iab_categories=topic_detection,
                    entity_detection=entity_detection,
                    auto_chapters=auto_chapters,
                    auto_highlights=key_phrases
                )
                
                if input_option == "Upload File (up to 200MB)":
                    if uploaded_file:
                        if uploaded_file.type == "video/mp4":
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
                                temp_video_file.write(uploaded_file.getvalue())
                                temp_video_file.flush()
                                audio_file = extract_audio_from_video(temp_video_file)
                            if audio_file:
                                transcript = transcriber.transcribe(audio_file, config)
                                os.unlink(audio_file)
                            os.unlink(temp_video_file.name)
                        else:
                            with tempfile.NamedTemporaryFile(delete=False, suffix="." + uploaded_file.name.split(".")[-1]) as temp_file:
                                temp_file.write(uploaded_file.getvalue())
                                temp_file.flush()
                                transcript = transcriber.transcribe(temp_file.name, config)
                            os.unlink(temp_file.name)
                    else:
                        st.error("Please upload a file before transcribing.")
                        st.stop()
                else:
                    if file_url:
                        if "youtube.com" in file_url or "youtu.be" in file_url:
                            youtube_audio_data = download_youtube_audio(file_url)
                            if youtube_audio_data:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                                    temp_file.write(youtube_audio_data)
                                    temp_file.flush()
                                    transcript = transcriber.transcribe(temp_file.name, config)
                                os.unlink(temp_file.name)
                            else:
                                st.error("Failed to download YouTube audio.")
                                st.stop()
                        else:
                            transcript = transcriber.transcribe(file_url, config)
                    else:
                        st.error("Please enter a valid URL before transcribing.")
                        st.stop()

                # Store transcript in session state
                st.session_state.transcript = transcript.text

                # OpenRouter summarization
                st.session_state.summary = summarize_with_openrouter(transcript.text, openrouter_api_key)

                st.success("Transcription and analysis completed!")
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.error(traceback.format_exc())

    # Display results
    if st.session_state.transcript:
        st.subheader("Transcription Result")
        with st.expander("Show/Hide Transcript", expanded=True):
            st.write(st.session_state.transcript)
        
        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="Download Raw Transcript",
                data=st.session_state.transcript,
                file_name="raw_transcript.txt",
                mime="text/plain"
            )
        with col2:
            if st.session_state.summary:
                st.download_button(
                    label="Download Summary",
                    data=st.session_state.summary,
                    file_name="summary.txt",
                    mime="text/plain"
                )

        # Display analysis results
        if st.session_state.summary:
            st.subheader("Summary and Key Information")
            st.write(st.session_state.summary)

    # Chat interface
    st.subheader("Chat about the Transcript")
    user_input = st.text_input("Ask a question about the transcript:")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        with st.spinner("Generating response..."):
            try:
                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openrouter_api_key}",
                        "HTTP-Referer": "https://your-app-url.com",
                        "X-Title": "Transcription Analyzer",
                    },
                    json={
                        "model": "anthropic/claude-3-sonnet",
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant. Use the provided transcript to answer questions."},
                            {"role": "user", "content": f"Here's the transcript for context:\n\n{st.session_state.transcript}\n\nNow, please answer the following question: {user_input}"}
                        ] + st.session_state.chat_history
                    }
                )
                response.raise_for_status()
                ai_response = response.json()['choices'][0]['message']['content']
                st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
            except requests.exceptions.RequestException as e:
                st.error(f"Error generating response: {str(e)}")
                st.error(traceback.format_exc())

    # Display chat history
    for message in st.session_state.chat_history:
        if message['role'] == 'user':
            st.write(f"You: {message['content']}")
        else:
            st.write(f"AI: {message['content']}")

else:
    st.warning("Please enter both your AssemblyAI and OpenRouter API keys in the sidebar to proceed.")

st.sidebar.markdown("---")
st.sidebar.markdown("Powered by AssemblyAI and OpenRouter")
