import streamlit as st
from pytube import YouTube
import whisper
import assemblyai as aai
import requests
import os
import tempfile
from moviepy.editor import VideoFileClip

def download_youtube_audio(url):
    try:
        yt = YouTube(url)
        stream = yt.streams.filter(only_audio=True).first()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            stream.download(filename=temp_file.name)
        return temp_file.name
    except Exception as e:
        st.error(f"Error downloading YouTube audio: {str(e)}")
        return None

def transcribe_with_whisper(audio_file):
    model = whisper.load_model("base")
    result = model.transcribe(audio_file)
    return result['text']

def extract_audio_from_video(video_file):
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio_file:
            video = VideoFileClip(video_file.name)
            video.audio.write_audiofile(temp_audio_file.name)
        return temp_audio_file.name
    except Exception as e:
        st.error(f"Error extracting audio from video: {str(e)}")
        return None

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

st.set_page_config(page_title="Audio Transcription and Analysis", layout="wide")
st.title("Audio Transcription and Analysis")

with st.sidebar:
    st.header("API Keys")
    assemblyai_api_key = st.text_input("Enter your AssemblyAI API key:", type="password")
    openrouter_api_key = st.text_input("Enter your OpenRouter API key:", type="password")

if assemblyai_api_key and openrouter_api_key:
    aai.settings.api_key = assemblyai_api_key

    input_option = st.radio("Choose input method:", ["Upload File (up to 200MB)", "Provide YouTube URL"])

    if input_option == "Upload File (up to 200MB)":
        uploaded_file = st.file_uploader("Choose an audio or video file (up to 200MB)", type=["mp3", "wav", "m4a", "mp4"])
        if uploaded_file:
            st.audio(uploaded_file) if uploaded_file.type != "video/mp4" else st.video(uploaded_file)
    else:
        youtube_url = st.text_input("Enter YouTube video URL:")

    st.subheader("Transcription and Analysis Options")
    speaker_labels = st.checkbox("Enable Speaker Diarization")
    sentiment_analysis = st.checkbox("Enable Sentiment Analysis")
    topic_detection = st.checkbox("Enable Topic Detection")
    entity_detection = st.checkbox("Enable Entity Detection")
    auto_chapters = st.checkbox("Enable Auto Chapters")
    key_phrases = st.checkbox("Enable Key Phrases")

    if st.button("Transcribe and Analyze"):
        with st.spinner("Processing..."):
            try:
                if input_option == "Upload File (up to 200MB)" and uploaded_file:
                    with tempfile.NamedTemporaryFile(delete=False, suffix="." + uploaded_file.name.split(".")[-1]) as temp_file:
                        temp_file.write(uploaded_file.getvalue())
                        temp_file.flush()
                        audio_file = extract_audio_from_video(temp_file) if uploaded_file.type == "video/mp4" else temp_file.name
                    
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
                    transcript_text = transcript.text
                elif input_option == "Provide YouTube URL" and youtube_url:
                    audio_file = download_youtube_audio(youtube_url)
                    if audio_file:
                        transcript_text = transcribe_with_whisper(audio_file)
                        os.unlink(audio_file)
                    else:
                        st.error("Failed to download YouTube audio.")
                        st.stop()
                else:
                    st.error("Please provide input before transcribing.")
                    st.stop()

                st.subheader("Transcription Result")
                st.text_area("Transcript", transcript_text, height=300)
                
                st.download_button(
                    label="Download Raw Transcript",
                    data=transcript_text,
                    file_name="transcript.txt",
                    mime="text/plain"
                )

                summary = summarize_with_openrouter(transcript_text, openrouter_api_key)
                if summary:
                    st.subheader("Summary and Key Information")
                    st.write(summary)
                    st.download_button(
                        label="Download Summary",
                        data=summary,
                        file_name="summary.txt",
                        mime="text/plain"
                    )

                st.success("Transcription and analysis completed!")
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

    st.subheader("Chat about the Transcript")
    user_input = st.text_input("Ask a question about the transcript:")
    if user_input and 'transcript_text' in locals():
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
                            {"role": "user", "content": f"Here's the transcript for context:\n\n{transcript_text}\n\nNow, please answer the following question: {user_input}"}
                        ]
                    }
                )
                response.raise_for_status()
                ai_response = response.json()['choices'][0]['message']['content']
                st.write(f"AI: {ai_response}")
            except requests.exceptions.RequestException as e:
                st.error(f"Error generating response: {str(e)}")

else:
    st.warning("Please enter both your AssemblyAI API key and OpenRouter API key in the sidebar to proceed.")

st.sidebar.markdown("---")
st.sidebar.markdown("Powered by AssemblyAI, Whisper, and OpenRouter")
