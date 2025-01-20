import subprocess
from typing import List, Dict, Any
import yt_dlp
from youtubesearchpython import Playlist, Channel, ResultMode
from pytube import YouTube

def download_video(video_url: str, output_path: str) -> str:
    try:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_path,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return output_path
    except yt_dlp.utils.DownloadError as e:
        print(f"yt-dlp failed: {e}. Falling back to pytube.")
        return download_video_pytube(video_url, output_path)

def download_video_pytube(video_url: str, output_path: str) -> str:
    try:
        yt = YouTube(video_url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        stream.download(output_path)
        return output_path
    except Exception as e:
        print(f"pytube failed: {e}")
        return None

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
    playlist = Playlist.getVideos(playlist_url)
    video_ids = [video['id'] for video in playlist['videos']]
    while playlist['hasMoreVideos']:
        playlist = Playlist.getNextVideos()
        video_ids.extend([video['id'] for video in playlist['videos']])
    return video_ids

def get_video_ids_from_channel(channel_url: str) -> List[str]:
    channel_id = channel_url.split('/')[-1]
    playlist = Playlist(playlist_from_channel_id(channel_id))
    video_ids = [video['id'] for video in playlist.videos]
    while playlist.hasMoreVideos:
        playlist.getNextVideos()
        video_ids.extend([video['id'] for video in playlist.videos])
    return video_ids
