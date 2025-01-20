import json
from zipfile import ZipFile
from io import BytesIO
from typing import List, Dict, Any

def download_clips_as_zip(clips: List[Dict[str, Any]]) -> BytesIO:
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zip_file:
        for clip in clips:
            clip_filename = f"{clip['video_id']}_{clip['start']}_{clip['end']}.txt"
            clip_content = f"Transcript:\n{clip['transcript']}"
            zip_file.writestr(clip_filename, clip_content)
    zip_buffer.seek(0)
    return zip_buffer

def save_json(data: Dict[str, Any], file_path: str) -> None:
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4)

def generate_srt(transcript: List[Dict[str, Any]]) -> str:
    srt_content = ""
    for i, entry in enumerate(transcript):
        start_time = entry['start']
        end_time = entry['end']
        text = entry['text']
        srt_content += f"{i+1}\n{start_time} --> {end_time}\n{text}\n\n"
    return srt_content

def download_clips_with_srt_as_zip(clips: List[Dict[str, Any]]) -> BytesIO:
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zip_file:
        for clip in clips:
            clip_filename = f"{clip['video_id']}_{clip['start']}_{clip['end']}.webm"
            srt_filename = f"{clip['video_id']}_{clip['start']}_{clip['end']}.srt"
            clip_content = f"Transcript:\n{clip['transcript']}"
            srt_content = generate_srt(clip['transcript'])
            zip_file.writestr(clip_filename, clip_content)
            zip_file.writestr(srt_filename, srt_content)
    zip_buffer.seek(0)
    return zip_buffer