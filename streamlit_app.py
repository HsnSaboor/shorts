import asyncio
import logging
import streamlit as st
from transcript import fetch_transcript, get_significant_transcript_sections
from heatmap import parse_svg_heatmap, analyze_heatmap_data, extract_video_data, extract_heatmap_svgs
from video_processing import download_video, create_clips, get_video_ids_from_playlist, get_video_ids_from_channel
from utils import download_clips_as_zip, save_json, download_clips_with_srt_as_zip

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Streamlit app
def main():
    st.title("YouTube Video Short Clips Generator")

    # Input fields for video URLs, playlist URLs, and channel URLs
    video_urls = st.text_area("Enter YouTube video URLs (comma-separated):")
    playlist_urls = st.text_area("Enter YouTube playlist URLs (comma-separated):")
    channel_urls = st.text_area("Enter YouTube channel URLs (comma-separated):")
    subtitle_language = st.text_input("Enter subtitle language code (e.g., 'tr' for Turkish):", value="tr")

    if st.button("Generate Clips"):
        if not video_urls and not playlist_urls and not channel_urls:
            st.warning("Please enter at least one video, playlist, or channel URL.")
        else:
            video_ids_list = []
            if video_urls:
                video_ids_list.extend([url.strip().split('v=')[-1] for url in video_urls.split(",")])
            if playlist_urls:
                for url in playlist_urls.split(","):
                    video_ids_list.extend(get_video_ids_from_playlist(url.strip()))
            if channel_urls:
                for url in channel_urls.split(","):
                    video_ids_list.extend(get_video_ids_from_channel(url.strip()))

            all_clips = []

            for video_id in video_ids_list:
                st.info(f"Processing video ID: {video_id}")
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                video_path = f"{video_id}.mp4"
                download_video(video_url, video_path)

                # Extract video data
                output_json = asyncio.run(extract_video_data(video_id))

                if output_json:
                    significant_sections = output_json.get('significant_transcript_sections', {'rises': []})
                    clips = create_clips(video_id, significant_sections, video_path, "clips")
                    all_clips.extend(clips)
                else:
                    st.error(f"Data extraction failed for video ID: {video_id}. Please check the video ID and try again.")

            if all_clips:
                zip_buffer = download_clips_with_srt_as_zip(all_clips)
                st.download_button(label="Download Clips with SRT as ZIP", data=zip_buffer, file_name="clips_with_srt.zip", mime="application/zip")

if __name__ == "__main__":
    main()