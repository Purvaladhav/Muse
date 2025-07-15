from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import httpx
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# YouTube API configuration
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
youtube_service = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class YouTubeVideo(BaseModel):
    id: str
    title: str
    description: str
    thumbnail_url: str
    duration: str
    channel_title: str
    view_count: str
    published_at: str

class Playlist(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    videos: List[YouTubeVideo] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PlaylistCreate(BaseModel):
    name: str

class PlaylistAddVideo(BaseModel):
    video_id: str
    title: str
    description: str
    thumbnail_url: str
    duration: str
    channel_title: str
    view_count: str
    published_at: str

# YouTube API Functions
def search_youtube_videos(query: str, max_results: int = 20):
    """Search YouTube for videos"""
    try:
        request = youtube_service.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=max_results,
            order="relevance"
        )
        search_response = request.execute()
        
        video_ids = []
        for item in search_response['items']:
            video_ids.append(item['id']['videoId'])
        
        # Get video statistics and details
        video_details = youtube_service.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids)
        ).execute()
        
        videos = []
        for item in video_details['items']:
            video = YouTubeVideo(
                id=item['id'],
                title=item['snippet']['title'],
                description=item['snippet']['description'][:500],  # Truncate description
                thumbnail_url=item['snippet']['thumbnails']['medium']['url'],
                duration=item['contentDetails']['duration'],
                channel_title=item['snippet']['channelTitle'],
                view_count=item['statistics'].get('viewCount', '0'),
                published_at=item['snippet']['publishedAt']
            )
            videos.append(video)
        
        return videos
    
    except HttpError as e:
        if "quotaExceeded" in str(e):
            raise HTTPException(status_code=429, detail="YouTube API quota exceeded")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Welcome to Muse Music Player API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

@api_router.get("/search", response_model=List[YouTubeVideo])
async def search_music(
    q: str = Query(..., description="Search query for music"),
    max_results: int = Query(20, ge=1, le=50, description="Number of results to return")
):
    """Search for music videos on YouTube"""
    if not YOUTUBE_API_KEY:
        raise HTTPException(status_code=500, detail="YouTube API key not configured")
    
    videos = search_youtube_videos(q, max_results)
    return videos

@api_router.post("/playlists", response_model=Playlist)
async def create_playlist(playlist: PlaylistCreate):
    """Create a new playlist"""
    playlist_obj = Playlist(name=playlist.name)
    await db.playlists.insert_one(playlist_obj.dict())
    return playlist_obj

@api_router.get("/playlists", response_model=List[Playlist])
async def get_playlists():
    """Get all playlists"""
    playlists = await db.playlists.find().to_list(1000)
    return [Playlist(**playlist) for playlist in playlists]

@api_router.get("/playlists/{playlist_id}", response_model=Playlist)
async def get_playlist(playlist_id: str):
    """Get a specific playlist"""
    playlist = await db.playlists.find_one({"id": playlist_id})
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return Playlist(**playlist)

@api_router.post("/playlists/{playlist_id}/videos")
async def add_video_to_playlist(playlist_id: str, video: PlaylistAddVideo):
    """Add a video to a playlist"""
    playlist = await db.playlists.find_one({"id": playlist_id})
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    # Convert video to YouTubeVideo object
    youtube_video = YouTubeVideo(
        id=video.video_id,
        title=video.title,
        description=video.description,
        thumbnail_url=video.thumbnail_url,
        duration=video.duration,
        channel_title=video.channel_title,
        view_count=video.view_count,
        published_at=video.published_at
    )
    
    # Add video to playlist
    await db.playlists.update_one(
        {"id": playlist_id},
        {
            "$push": {"videos": youtube_video.dict()},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return {"message": "Video added to playlist"}

@api_router.delete("/playlists/{playlist_id}/videos/{video_id}")
async def remove_video_from_playlist(playlist_id: str, video_id: str):
    """Remove a video from a playlist"""
    playlist = await db.playlists.find_one({"id": playlist_id})
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    await db.playlists.update_one(
        {"id": playlist_id},
        {
            "$pull": {"videos": {"id": video_id}},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return {"message": "Video removed from playlist"}

@api_router.delete("/playlists/{playlist_id}")
async def delete_playlist(playlist_id: str):
    """Delete a playlist"""
    result = await db.playlists.delete_one({"id": playlist_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return {"message": "Playlist deleted"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()