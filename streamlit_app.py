import streamlit as st
import assemblyai as aai
import requests
import json
import os
import tempfile
from moviepy.editor import VideoFileClip
from pytube import YouTube
import io

# Function to download YouTube audio
def download_youtube_audio(url):
    try:
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        buffer = io.BytesIO()
        audio_stream.stream_to_buffer(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Error downloading YouTube audio: {str(e)}")
        return None

# Function to transcribe with OpenAI API
def transcribe_with_openai(audio_file, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    url = "https://api.openai.com/v1/audio/transcriptions"
    
    files = {
        "file": ("audio.mp3", audio_file, "audio/mpeg"),
        "model": (None, "whisper-1")
    }
    
    response = requests.post(url, headers=headers, files=files)
    if response.status_code == 200:
        return response.json()['text']
    else:
        st.error(f"Error transcribing with OpenAI: {response.text}")
        return None

# Function to extract audio from video
def extract_audio_from_video(video_file):
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio_file:
            video = VideoFileClip(video_file.name)
            video.audio.write_audiofile(temp_audio_file.name)
        return temp_audio_file.name
    except Exception as e:
        st.error(f"Error extracting audio from video: {str(e)}")
        return None

# Function to summarize with OpenRouter
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
        return None

# Streamlit app
st.set_page_config(page_title="Audio Transcription and Analysis", layout="wide")

st.title("Audio Transcription and Analysis")

# Sidebar for API keys
with st.sidebar:
    st.header("API Keys")
    assemblyai_api_key = st.text_input("Enter your AssemblyAI API key:", type="password")
    openai_api_key = st.text_input("Enter your OpenAI API key:", type="password")
    openrouter_api_key = st.text_input("Enter your OpenRouter API key:", type="password")

# Main content
if assemblyai_api_key and openai_api_key and openrouter_api_key:
    aai.settings.api_key = assemblyai_api_key

    # File input options
    input_option = st.radio("Choose input method:", ["Upload File (up to 200MB)", "Provide YouTube URL"])

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
        youtube_url = st.text_input("Enter YouTube video URL:")

    # Transcription options
    st.subheader("Transcription and Analysis Options")
    
    speaker_labels = st.checkbox("Enable Speaker Diarization", help="Detect and label different speakers in the audio")
    sentiment_analysis = st.checkbox("Enable Sentiment Analysis", help="Detect the sentiment of each spoken sentence")
    topic_detection = st.checkbox("Enable Topic Detection", help="Identify different topics in the transcript")
    entity_detection = st.checkbox("Enable Entity Detection", help="Identify and categorize key information")
    auto_chapters = st.checkbox("Enable Auto Chapters", help="Summarize audio data over time into chapters")
    key_phrases = st.checkbox("Enable Key Phrases", help="Identify significant words and phrases")

    if st.button("Transcribe and Analyze"):
        with st.spinner("Processing..."):
            try:
                if input_option == "Upload File (up to 200MB)":
                    if uploaded_file:
                        if uploaded_file.type == "video/mp4":
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
                                temp_video_file.write(uploaded_file.getvalue())
                                temp_video_file.flush()
                                audio_file = extract_audio_from_video(temp_video_file)
                        else:
                            with tempfile.NamedTemporaryFile(delete=False, suffix="." + uploaded_file.name.split(".")[-1]) as temp_file:
                                temp_file.write(uploaded_file.getvalue())
                                temp_file.flush()
                                audio_file = temp_file.name
                        
                        transcriber = aai.Transcriber()
                        config = aai.TranscriptionConfig(
                            speaker_labels=speaker_labels,
                            sentiment_analysis=sentiment_analysis,
                            iab_categories=topic_detection,
                            entity_detection=entity_detection,
                            auto_chapters=auto_chapters,
                            auto_highlights=key_phrases
                        )
                        transcript = transcriber.transcribe(audio_file, config)
                        os.unlink(audio_file)
                        
                        st.session_state.transcript = transcript.text
                    else:
                        st.error("Please upload a file before transcribing.")
                        st.stop()
                else:
                    if youtube_url:
                        audio_buffer = download_youtube_audio(youtube_url)
                        if audio_buffer:
                            st.session_state.transcript = transcribe_with_openai(audio_buffer, openai_api_key)
                        else:
                            st.error("Failed to download YouTube audio.")
                            st.stop()
                    else:
                        st.error("Please enter a valid YouTube URL.")
                        st.stop()

                st.session_state.summary = summarize_with_openrouter(st.session_state.transcript, openrouter_api_key)
                st.success("Transcription and analysis completed!")
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

    # Display results
    if 'transcript' in st.session_state and st.session_state.transcript:
        st.subheader("Transcription Result")
        with st.expander("Show/Hide Transcript", expanded=True):
            st.write(st.session_state.transcript)
        
        # Download buttons
        st.download_button(
            label="Download Raw Transcript",
            data=st.session_state.transcript,
            file_name="raw_transcript.txt",
            mime="text/plain"
        )
        
        if 'summary' in st.session_state and st.session_state.summary:
            st.download_button(
                label="Download Summary",
                data=st.session_state.summary,
                file_name="summary.txt",
                mime="text/plain"
            )

        # Display analysis results
        if 'summary' in st.session_state and st.session_state.summary:
            st.subheader("Summary and Key Information")
            st.write(st.session_state.summary)

    # Chat interface
    st.subheader("Chat about the Transcript")
    user_input = st.text_input("Ask a question about the transcript:")
    if user_input and 'transcript' in st.session_state and st.session_state.transcript:
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
                        ]
                    }
                )
                response.raise_for_status()
                ai_response = response.json()['choices'][0]['message']['content']
                st.write(f"AI: {ai_response}")
            except requests.exceptions.RequestException as e:
                st.error(f"Error generating response: {str(e)}")

else:
    st.warning("Please enter your AssemblyAI, OpenAI, and OpenRouter API keys in the sidebar to proceed.")

st.sidebar.markdown("---")
st.sidebar.markdown("Powered by AssemblyAI, OpenAI, and OpenRouter")
