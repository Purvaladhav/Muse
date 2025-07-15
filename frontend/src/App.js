import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// YouTube Player Component
const YouTubePlayer = ({ videoId, onReady, onStateChange }) => {
  const playerRef = useRef(null);
  const [player, setPlayer] = useState(null);

  useEffect(() => {
    // Load YouTube API if not already loaded
    if (!window.YT) {
      const tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      const firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
      
      window.onYouTubeIframeAPIReady = () => {
        createPlayer();
      };
    } else {
      createPlayer();
    }

    function createPlayer() {
      if (playerRef.current && videoId) {
        const newPlayer = new window.YT.Player(playerRef.current, {
          height: '200',
          width: '100%',
          videoId: videoId,
          playerVars: {
            'playsinline': 1,
            'controls': 0,
            'modestbranding': 1,
            'rel': 0
          },
          events: {
            'onReady': (event) => {
              setPlayer(event.target);
              if (onReady) onReady(event.target);
            },
            'onStateChange': onStateChange
          }
        });
      }
    }
  }, [videoId, onReady, onStateChange]);

  return <div ref={playerRef} className="youtube-player"></div>;
};

// Search Component
const SearchBar = ({ onSearch, loading }) => {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="search-bar">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search for music..."
        className="search-input"
        disabled={loading}
      />
      <button type="submit" disabled={loading || !query.trim()} className="search-button">
        {loading ? 'Searching...' : 'Search'}
      </button>
    </form>
  );
};

// Video Item Component
const VideoItem = ({ video, onPlay, onAddToPlaylist, isCurrentVideo }) => {
  const formatDuration = (duration) => {
    const match = duration.match(/PT(\d+H)?(\d+M)?(\d+S)?/);
    const hours = (match[1] || '').replace('H', '');
    const minutes = (match[2] || '').replace('M', '');
    const seconds = (match[3] || '').replace('S', '');
    
    if (hours) {
      return `${hours}:${minutes.padStart(2, '0')}:${seconds.padStart(2, '0')}`;
    }
    return `${minutes || '0'}:${seconds.padStart(2, '0')}`;
  };

  const formatViewCount = (count) => {
    const num = parseInt(count);
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M views`;
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K views`;
    }
    return `${num} views`;
  };

  return (
    <div className={`video-item ${isCurrentVideo ? 'current-video' : ''}`}>
      <div className="video-thumbnail">
        <img src={video.thumbnail_url} alt={video.title} />
        <div className="video-duration">{formatDuration(video.duration)}</div>
      </div>
      <div className="video-info">
        <h3 className="video-title">{video.title}</h3>
        <p className="video-channel">{video.channel_title}</p>
        <p className="video-views">{formatViewCount(video.view_count)}</p>
      </div>
      <div className="video-actions">
        <button onClick={() => onPlay(video)} className="play-button">
          {isCurrentVideo ? '▶ Playing' : '▶ Play'}
        </button>
        <button onClick={() => onAddToPlaylist(video)} className="add-button">
          + Add to Playlist
        </button>
      </div>
    </div>
  );
};

// Player Controls Component
const PlayerControls = ({ 
  isPlaying, 
  onPlayPause, 
  onVolumeChange, 
  volume, 
  onSeek, 
  currentTime, 
  duration,
  onNext,
  onPrevious,
  hasNext,
  hasPrevious
}) => {
  const formatTime = (time) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="player-controls">
      <div className="control-buttons">
        <button onClick={onPrevious} disabled={!hasPrevious} className="control-btn">
          ⏮
        </button>
        <button onClick={onPlayPause} className="play-pause-btn">
          {isPlaying ? '⏸' : '▶'}
        </button>
        <button onClick={onNext} disabled={!hasNext} className="control-btn">
          ⏭
        </button>
      </div>
      
      <div className="progress-container">
        <span className="time">{formatTime(currentTime)}</span>
        <input
          type="range"
          min="0"
          max={duration}
          value={currentTime}
          onChange={onSeek}
          className="progress-bar"
        />
        <span className="time">{formatTime(duration)}</span>
      </div>
      
      <div className="volume-container">
        <span>🔊</span>
        <input
          type="range"
          min="0"
          max="100"
          value={volume}
          onChange={onVolumeChange}
          className="volume-slider"
        />
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [searchResults, setSearchResults] = useState([]);
  const [currentVideo, setCurrentVideo] = useState(null);
  const [player, setPlayer] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(50);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [loading, setLoading] = useState(false);
  const [playlists, setPlaylists] = useState([]);
  const [currentPlaylist, setCurrentPlaylist] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Search for music
  const searchMusic = async (query) => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/search`, {
        params: { q: query, max_results: 20 }
      });
      setSearchResults(response.data);
    } catch (error) {
      console.error('Search failed:', error);
      alert('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Play video
  const playVideo = (video) => {
    setCurrentVideo(video);
    setCurrentPlaylist([video]);
    setCurrentIndex(0);
  };

  // Player ready event
  const onPlayerReady = (playerInstance) => {
    setPlayer(playerInstance);
    playerInstance.setVolume(volume);
  };

  // Player state change event
  const onPlayerStateChange = (event) => {
    if (event.data === window.YT.PlayerState.PLAYING) {
      setIsPlaying(true);
    } else if (event.data === window.YT.PlayerState.PAUSED) {
      setIsPlaying(false);
    } else if (event.data === window.YT.PlayerState.ENDED) {
      playNext();
    }
  };

  // Play/Pause toggle
  const togglePlayPause = () => {
    if (player) {
      if (isPlaying) {
        player.pauseVideo();
      } else {
        player.playVideo();
      }
    }
  };

  // Volume control
  const handleVolumeChange = (e) => {
    const newVolume = parseInt(e.target.value);
    setVolume(newVolume);
    if (player) {
      player.setVolume(newVolume);
    }
  };

  // Seek control
  const handleSeek = (e) => {
    const seekTime = parseInt(e.target.value);
    if (player) {
      player.seekTo(seekTime);
    }
  };

  // Next/Previous controls
  const playNext = () => {
    if (currentIndex < currentPlaylist.length - 1) {
      const nextIndex = currentIndex + 1;
      setCurrentIndex(nextIndex);
      setCurrentVideo(currentPlaylist[nextIndex]);
    }
  };

  const playPrevious = () => {
    if (currentIndex > 0) {
      const prevIndex = currentIndex - 1;
      setCurrentIndex(prevIndex);
      setCurrentVideo(currentPlaylist[prevIndex]);
    }
  };

  // Add to playlist (simple implementation)
  const addToPlaylist = (video) => {
    setCurrentPlaylist(prev => [...prev, video]);
    alert(`Added "${video.title}" to current playlist`);
  };

  // Update current time
  useEffect(() => {
    const interval = setInterval(() => {
      if (player && isPlaying) {
        setCurrentTime(player.getCurrentTime());
        setDuration(player.getDuration());
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [player, isPlaying]);

  // Load playlists on component mount
  useEffect(() => {
    const loadPlaylists = async () => {
      try {
        const response = await axios.get(`${API}/playlists`);
        setPlaylists(response.data);
      } catch (error) {
        console.error('Failed to load playlists:', error);
      }
    };
    loadPlaylists();
  }, []);

  return (
    <div className="App">
      <header className="app-header">
        <h1 className="app-title">🎵 Muse</h1>
        <p className="app-subtitle">Your YouTube Music Player</p>
      </header>

      <main className="app-main">
        {/* Search Section */}
        <div className="search-section">
          <SearchBar onSearch={searchMusic} loading={loading} />
        </div>

        {/* Player Section */}
        {currentVideo && (
          <div className="player-section">
            <div className="current-video-info">
              <img src={currentVideo.thumbnail_url} alt={currentVideo.title} className="current-thumbnail" />
              <div className="current-details">
                <h2 className="current-title">{currentVideo.title}</h2>
                <p className="current-channel">{currentVideo.channel_title}</p>
              </div>
            </div>
            
            <div className="youtube-player-container">
              <YouTubePlayer
                videoId={currentVideo.id}
                onReady={onPlayerReady}
                onStateChange={onPlayerStateChange}
              />
            </div>
            
            <PlayerControls
              isPlaying={isPlaying}
              onPlayPause={togglePlayPause}
              onVolumeChange={handleVolumeChange}
              volume={volume}
              onSeek={handleSeek}
              currentTime={currentTime}
              duration={duration}
              onNext={playNext}
              onPrevious={playPrevious}
              hasNext={currentIndex < currentPlaylist.length - 1}
              hasPrevious={currentIndex > 0}
            />
          </div>
        )}

        {/* Search Results */}
        {searchResults.length > 0 && (
          <div className="search-results">
            <h2>Search Results</h2>
            <div className="video-list">
              {searchResults.map((video) => (
                <VideoItem
                  key={video.id}
                  video={video}
                  onPlay={playVideo}
                  onAddToPlaylist={addToPlaylist}
                  isCurrentVideo={currentVideo?.id === video.id}
                />
              ))}
            </div>
          </div>
        )}

        {/* Current Playlist */}
        {currentPlaylist.length > 1 && (
          <div className="current-playlist">
            <h2>Current Playlist ({currentPlaylist.length} songs)</h2>
            <div className="playlist-items">
              {currentPlaylist.map((video, index) => (
                <div 
                  key={`${video.id}-${index}`} 
                  className={`playlist-item ${index === currentIndex ? 'active' : ''}`}
                  onClick={() => {
                    setCurrentIndex(index);
                    setCurrentVideo(video);
                  }}
                >
                  <img src={video.thumbnail_url} alt={video.title} className="playlist-thumbnail" />
                  <div className="playlist-info">
                    <h4>{video.title}</h4>
                    <p>{video.channel_title}</p>
                  </div>
                  {index === currentIndex && <span className="playing-indicator">▶</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;