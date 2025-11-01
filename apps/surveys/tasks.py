from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from pathlib import Path
import subprocess
import logging

from .models import SurveySession

logger = logging.getLogger(__name__)


def transcode_webm_to_ts(webm_path, ts_output_path):
    """
    Transcode WebM video to MPEG-TS format using FFmpeg.
    
    Args:
        webm_path: Path to input WebM file
        ts_output_path: Path to output TS file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # FFmpeg command to transcode WebM to H.264 MPEG-TS
        # -i: input file
        # -c:v libx264: video codec H.264
        # -c:a aac: audio codec AAC
        # -f mpegts: output format MPEG-TS
        # -preset fast: encoding speed
        # -crf 23: quality (lower = better quality but larger file)
        # -hls_time 10: segment duration (10 seconds)
        cmd = [
            'ffmpeg',
            '-i', webm_path,
            '-c:v', 'libx264',      # H.264 video codec
            '-c:a', 'aac',          # AAC audio codec
            '-f', 'mpegts',         # MPEG-TS container
            '-preset', 'fast',      # Encoding speed
            '-crf', '23',           # Quality (lower = better quality)
            '-movflags', 'faststart',  # Fast start for streaming
            '-strict', '-2',        # Allow experimental codecs
            '-y',                   # Overwrite output file
            ts_output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f'FFmpeg error: {result.stderr}')
            return False
        
        logger.info(f'Successfully transcoded {webm_path} to {ts_output_path}')
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f'FFmpeg transcoding timeout for {webm_path}')
        return False
    except Exception as e:
        logger.error(f'Error transcoding {webm_path}: {str(e)}')
        return False


@shared_task()
def transcode_chunk_to_ts(chunk_id):
    """
    Asynchronously transcode a single video chunk from WebM to MPEG-TS.
    
    Args:
        chunk_id: ID of the VideoChunk instance to transcode
        
    Returns:
        dict with status and info
    """
    from .models import VideoChunk
    
    try:
        chunk = VideoChunk.objects.get(id=chunk_id)
    except VideoChunk.DoesNotExist:
        logger.error(f'VideoChunk {chunk_id} not found')
        return {'status': 'error', 'message': 'Chunk not found'}
    
    # Get WebM file path
    webm_path = chunk.chunk_file.path
    webm_file = Path(webm_path)
    
    if not webm_file.exists():
        logger.error(f'WebM file not found: {webm_path}')
        return {'status': 'error', 'message': 'WebM file not found'}
    
    # Generate TS path (same directory, different extension)
    ts_path = webm_path.replace('.webm', '.ts')
    ts_file = Path(ts_path)
    
    # Check if already transcoded
    if ts_file.exists():
        logger.info(f'TS file already exists for chunk {chunk_id}: {ts_path}')
        return {'status': 'exists', 'ts_path': str(ts_path)}
    
    # Create parent directory if needed
    ts_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Transcode WebM to TS
    logger.info(f'Starting transcoding for chunk {chunk_id}: {webm_path} -> {ts_path}')
    success = transcode_webm_to_ts(webm_path, ts_path)
    
    if success:
        logger.info(f'Successfully transcoded chunk {chunk_id}')
        return {'status': 'success', 'ts_path': str(ts_path)}
    else:
        logger.error(f'Failed to transcode chunk {chunk_id}')
        return {'status': 'error', 'message': 'Transcoding failed'}


@shared_task()
def create_hls_playlist(session_id):
    """
    Create M3U8 playlist from TS video chunks for a session.
    
    This creates an HLS M3U8 playlist from MPEG-TS chunks. The WebM chunks
    uploaded by the frontend are asynchronously transcoded to TS format via
    the transcode_chunk_to_ts task. This playlist references the TS files
    for proper HLS streaming playback.
    
    Args:
        session_id: UUID of the survey session
        
    Returns:
        dict with status and playlist info
    """
    try:
        session = SurveySession.objects.get(id=session_id)
    except SurveySession.DoesNotExist:
        return {'status': 'error', 'message': 'Session not found'}
    
    # Get all video chunks ordered by chunk number
    chunks = session.video_chunks.all().order_by('chunk_number')
    
    if not chunks.exists():
        return {'status': 'error', 'message': 'No video chunks found'}
    
    # Build M3U8 playlist content
    playlist_lines = [
        '#EXTM3U',
        '#EXT-X-VERSION:3',
        '#EXT-X-TARGETDURATION:10',  # Maximum chunk duration in seconds
        '#EXT-X-MEDIA-SEQUENCE:0',
        '#EXT-X-PLAYLIST-TYPE:VOD',  # Video on Demand
    ]
    
    # Add each chunk to the playlist
    total_duration = 0
    base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000').rstrip('/')
    
    for chunk in chunks:
        # Use TS file URL instead of WebM for HLS playback
        chunk_url = chunk.chunk_file.url.replace('.webm', '.ts')
        
        # Build absolute URL for M3U8 playlist
        if chunk_url.startswith('/'):
            chunk_url = f'{base_url}{chunk_url}'
        
        # Add segment info
        playlist_lines.append(f'#EXTINF:{chunk.duration_seconds:.3f},')
        playlist_lines.append(chunk_url)
        
        total_duration += chunk.duration_seconds
    
    # Add end marker
    playlist_lines.append('#EXT-X-ENDLIST')
    
    # Join all lines
    playlist_content = '\n'.join(playlist_lines) + '\n'
    
    # Create playlist file
    filename = f'session_{session_id}_playlist.m3u8'
    playlist_file = ContentFile(playlist_content.encode('utf-8'), name=filename)
    
    # Get or create recording
    from .models import SessionRecording
    
    try:
        recording = SessionRecording.objects.get(session=session)
        created = False
    except SessionRecording.DoesNotExist:
        recording = SessionRecording(
            session=session,
            file_size=sum(chunk.file_size for chunk in chunks),
            duration_seconds=int(total_duration),
            total_violations=session.violations_count,
            violation_summary={
                'total_chunks': chunks.count(),
                'created_at': timezone.now().isoformat(),
            }
        )
        created = True
    
    # Save playlist file
    recording.playlist_file = playlist_file
    recording.processed = True
    recording.save()
    
    # Mark chunks as processed
    chunks.update(processed=True)
    
    return {
        'status': 'success' if created else 'updated',
        'recording_id': recording.id,
        'playlist_url': recording.playlist_file.url if recording.playlist_file else '',
        'total_chunks': chunks.count(),
        'total_duration': total_duration
    }
