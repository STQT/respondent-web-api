from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import SurveySession


@shared_task()
def create_hls_playlist(session_id):
    """
    Create HLS M3U8 playlist from video chunks for a session.
    
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
    for chunk in chunks:
        # Get the chunk file URL
        chunk_url = chunk.chunk_file.url
        
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
