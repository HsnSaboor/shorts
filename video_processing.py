import subprocess
from typing import List, Dict, Any
import yt_dlp
from youtubesearchpython import Playlist, Channel

def download_video(video_url: str, output_path: str) -> str:
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
    return output_path

def create_clip(input_path: str, start_time: float, end_time: float, output_path: str) -> None:
    duration = end_time - start_time
    command = [
        'ffmpeg',
        '-i', input_path,
        '-ss', str(start_time),
        '-t', str(duration),
        '-c:v', 'libvpx-vp9',
        '-crf', '0',
        '-b:v', '0',
        '-c:a', 'libopus',
        output_path
    ]
    subprocess.run(command, check=True)

def create_clips(video_id: str, significant_sections: Dict[str, List[Dict[str, Any]]], input_path: str, output_dir: str) -> List[Dict[str, Any]]:
    clips = []
    for section in significant_sections['rises']:
        start = section['start']
        end = section['end']
        output_path = f"{output_dir}/{video_id}_{start}_{end}.webm"
        create_clip(input_path, start, end, output_path)
        clip = {
            'video_id': video_id,
            'start': start,
            'end': end,
            'transcript': section['text'],
            'output_path': output_path
        }
        clips.append(clip)
    return clips

def get_video_ids_from_playlist(playlist_url: str) -> List[str]:
    playlist = Playlist(playlist_url)
    return [video['id'] for video in playlist.videos]

def get_video_ids_from_channel(channel_url: str) -> List[str]:
    channel = Channel(channel_url)
    return [video['id'] for video in channel.videos]