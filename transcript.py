from typing import List, Dict, Any, Optional
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import yt_dlp
import streamlit as st

def fetch_transcript(video_id: str) -> Optional[List[Dict[str, Any]]]:
    """Fetches transcript data from YouTube with fallback for 'TranscriptsDisabled'."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # Try to get a manually created Turkish transcript
        if 'tr' in transcript_list._manually_created_transcripts:
            transcript = transcript_list.find_manually_created_transcript(['tr'])
            st.success("Turkish manually created transcript found.")
            transcript_data = transcript.fetch()
            return transcript_data
        # Try to get a manually created English transcript
        elif 'en' in transcript_list._manually_created_transcripts:
            transcript = transcript_list.find_manually_created_transcript(['en'])
            st.success("English manually created transcript found.")
            transcript_data = transcript.fetch()
            return transcript_data
        # Try to get auto-generated Turkish transcript
        elif 'tr' in transcript_list._generated_transcripts:
            transcript = transcript_list.find_generated_transcript(['tr'])
            st.success("Turkish auto-generated transcript found.")
            transcript_data = transcript.fetch()
            return transcript_data
        else:
            st.error("No manually created or auto-generated transcripts found in Turkish or English.")
            return None

    except TranscriptsDisabled:
        st.warning("Transcripts are disabled using list_transcripts method, attempting fallback method...")
        return fetch_transcript_fallback(video_id)
    except NoTranscriptFound:
        st.error("No transcripts found for this video.")
        return None
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

def fetch_transcript_fallback(video_id: str) -> Optional[List[Dict[str, Any]]]:
    """Fallback method to fetch transcript using get_transcript."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        if 'tr' in transcript_list._manually_created_transcripts:
            transcript = transcript_list.find_manually_created_transcript(['tr'])
            st.success("Turkish manually created transcript found using fallback method.")
            transcript_data = transcript.fetch()
            return transcript_data
        elif 'en' in transcript_list._manually_created_transcripts:
            transcript = transcript_list.find_manually_created_transcript(['en'])
            st.success("English manually created transcript found using fallback method.")
            transcript_data = transcript.fetch()
            return transcript_data
        else:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['tr'])
            st.success("Turkish transcript fetched using fallback method.")
            return transcript

    except TranscriptsDisabled:
        st.warning("Transcripts are disabled even using fallback method, attempting yt-dlp fallback method...")
        return fetch_transcript_yt_dlp(video_id)
    except NoTranscriptFound:
        st.error("No transcripts found using fallback method.")
        return None
    except Exception as e:
        st.error(f"An error occurred in fallback method: {e}")
        return None

def fetch_transcript_yt_dlp(video_id: str) -> Optional[List[Dict[str, Any]]]:
    """Fallback method to fetch transcript using yt-dlp."""
    try:
        ydl_opts = {
            'writesubtitles': True,
            'subtitleslangs': ['tr'],
            'skip_download': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

            if 'subtitles' in info_dict and 'tr' in info_dict['subtitles']:
                subtitles = info_dict['subtitles']['tr']
                srt_content = yt_dlp.utils.get_first(subtitles, {}).get('data', '')
                if srt_content:
                    st.success("Turkish transcript fetched using yt_dlp fallback method.")
                    return parse_srt(srt_content)
                else:
                    st.error("No subtitles found in yt_dlp output.")
                    return None
            else:
                st.error("No Turkish subtitles found using yt_dlp")
                return None

    except Exception as e:
        st.error(f"An error occurred in yt_dlp fallback method: {e}")
        return None

def parse_srt(srt_content: str) -> List[Dict[str, Any]]:
    """Parses SRT content into a list of transcript entries."""
    import re
    pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)\n\n', re.DOTALL)
    matches = pattern.findall(srt_content)
    transcript = []
    for match in matches:
        start_time = match[1]
        end_time = match[2]
        text = match[3].replace('\n', ' ')
        transcript.append({
            'start': start_time,
            'end': end_time,
            'text': text
        })
    return transcript

def get_significant_transcript_sections(transcript: Optional[List[Dict[str, any]]], analysis_data: Dict[str, any]) -> Dict[str, List[List[Dict[str, any]]]]:
    if not transcript:
        print("Transcript is unavailable. Returning empty significant sections.")
        return {'rises': [], 'falls': []}
    significant_sections = {'rises': [], 'falls': []}
    for rise in analysis_data.get('significant_rises', []):
        rise_transcript = [entry for entry in transcript if rise['start'] <= entry['start'] <= rise['end']]
        significant_sections['rises'].append(rise_transcript)
    for fall in analysis_data.get('significant_falls', []):
        fall_transcript = [entry for entry in transcript if fall['start'] <= entry['start'] <= fall['end']]
        significant_sections['falls'].append(fall_transcript)
    return significant_sections