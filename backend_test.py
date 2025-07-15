#!/usr/bin/env python3
"""
Backend API Testing for Muse Music Player
Tests YouTube API integration, search endpoints, playlist management, and database operations
"""

import requests
import json
import time
from typing import Dict, List, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Get backend URL from environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE_URL = f"{BACKEND_URL}/api"

class MuseBackendTester:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.session = requests.Session()
        self.test_results = {
            'youtube_api_integration': {'passed': False, 'details': ''},
            'music_search_endpoint': {'passed': False, 'details': ''},
            'playlist_management': {'passed': False, 'details': ''},
            'database_models': {'passed': False, 'details': ''}
        }
        self.created_playlist_ids = []  # Track created playlists for cleanup
        
    def log_test(self, test_name: str, message: str, success: bool = True):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
    def test_api_health(self) -> bool:
        """Test if the API is accessible"""
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                self.log_test("API Health", f"API is accessible at {self.base_url}")
                return True
            else:
                self.log_test("API Health", f"API returned status {response.status_code}", False)
                return False
        except Exception as e:
            self.log_test("API Health", f"Failed to connect to API: {str(e)}", False)
            return False
    
    def test_youtube_api_integration(self) -> bool:
        """Test YouTube API Integration"""
        print("\n🔍 Testing YouTube API Integration...")
        
        try:
            # Test with a simple search query
            response = self.session.get(f"{self.base_url}/search", params={'q': 'test music', 'max_results': 5})
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Check if response has expected YouTube video structure
                    video = data[0]
                    required_fields = ['id', 'title', 'description', 'thumbnail_url', 'duration', 'channel_title', 'view_count', 'published_at']
                    
                    missing_fields = [field for field in required_fields if field not in video]
                    if not missing_fields:
                        self.test_results['youtube_api_integration']['passed'] = True
                        self.test_results['youtube_api_integration']['details'] = f"Successfully retrieved {len(data)} videos with all required fields"
                        self.log_test("YouTube API Integration", f"Successfully retrieved {len(data)} videos with proper structure")
                        return True
                    else:
                        self.test_results['youtube_api_integration']['details'] = f"Missing fields in response: {missing_fields}"
                        self.log_test("YouTube API Integration", f"Missing fields in response: {missing_fields}", False)
                        return False
                else:
                    self.test_results['youtube_api_integration']['details'] = "Empty or invalid response format"
                    self.log_test("YouTube API Integration", "Empty or invalid response format", False)
                    return False
            elif response.status_code == 429:
                self.test_results['youtube_api_integration']['details'] = "YouTube API quota exceeded"
                self.log_test("YouTube API Integration", "YouTube API quota exceeded", False)
                return False
            elif response.status_code == 500:
                self.test_results['youtube_api_integration']['details'] = f"Server error: {response.text}"
                self.log_test("YouTube API Integration", f"Server error: {response.text}", False)
                return False
            else:
                self.test_results['youtube_api_integration']['details'] = f"Unexpected status code: {response.status_code}"
                self.log_test("YouTube API Integration", f"Unexpected status code: {response.status_code}", False)
                return False
                
        except Exception as e:
            self.test_results['youtube_api_integration']['details'] = f"Exception occurred: {str(e)}"
            self.log_test("YouTube API Integration", f"Exception occurred: {str(e)}", False)
            return False
    
    def test_music_search_endpoint(self) -> bool:
        """Test Music Search API Endpoint with various queries"""
        print("\n🎵 Testing Music Search API Endpoint...")
        
        test_queries = [
            {'query': 'pop music', 'expected_min_results': 1},
            {'query': 'rock songs', 'expected_min_results': 1},
            {'query': 'classical music', 'expected_min_results': 1},
            {'query': 'jazz piano', 'expected_min_results': 1}
        ]
        
        all_passed = True
        results_summary = []
        
        for test_case in test_queries:
            try:
                response = self.session.get(f"{self.base_url}/search", params={
                    'q': test_case['query'], 
                    'max_results': 10
                })
                
                if response.status_code == 200:
                    data = response.json()
                    if len(data) >= test_case['expected_min_results']:
                        self.log_test("Music Search", f"Query '{test_case['query']}' returned {len(data)} results")
                        results_summary.append(f"'{test_case['query']}': {len(data)} results")
                        
                        # Validate response structure for first result
                        if data:
                            video = data[0]
                            if all(field in video for field in ['id', 'title', 'thumbnail_url', 'duration']):
                                self.log_test("Music Search", f"Response structure valid for '{test_case['query']}'")
                            else:
                                self.log_test("Music Search", f"Invalid response structure for '{test_case['query']}'", False)
                                all_passed = False
                    else:
                        self.log_test("Music Search", f"Query '{test_case['query']}' returned insufficient results", False)
                        all_passed = False
                elif response.status_code == 429:
                    self.log_test("Music Search", f"API quota exceeded for query '{test_case['query']}'", False)
                    all_passed = False
                    break
                else:
                    self.log_test("Music Search", f"Query '{test_case['query']}' failed with status {response.status_code}", False)
                    all_passed = False
                    
            except Exception as e:
                self.log_test("Music Search", f"Exception for query '{test_case['query']}': {str(e)}", False)
                all_passed = False
        
        # Test edge cases
        try:
            # Test empty query
            response = self.session.get(f"{self.base_url}/search", params={'q': '', 'max_results': 5})
            if response.status_code in [400, 422]:  # Expected to fail
                self.log_test("Music Search", "Empty query properly rejected")
            else:
                self.log_test("Music Search", "Empty query should be rejected", False)
                all_passed = False
                
            # Test max_results parameter
            response = self.session.get(f"{self.base_url}/search", params={'q': 'music', 'max_results': 3})
            if response.status_code == 200:
                data = response.json()
                if len(data) <= 3:
                    self.log_test("Music Search", "max_results parameter working correctly")
                else:
                    self.log_test("Music Search", "max_results parameter not working correctly", False)
                    all_passed = False
                    
        except Exception as e:
            self.log_test("Music Search", f"Edge case testing failed: {str(e)}", False)
            all_passed = False
        
        if all_passed:
            self.test_results['music_search_endpoint']['passed'] = True
            self.test_results['music_search_endpoint']['details'] = f"All search queries passed: {', '.join(results_summary)}"
        else:
            self.test_results['music_search_endpoint']['details'] = "Some search queries failed or returned invalid responses"
            
        return all_passed
    
    def test_playlist_management(self) -> bool:
        """Test Playlist Management CRUD Operations"""
        print("\n📝 Testing Playlist Management API...")
        
        all_passed = True
        
        try:
            # Test 1: Create a playlist
            playlist_data = {'name': 'Test Rock Playlist'}
            response = self.session.post(f"{self.base_url}/playlists", json=playlist_data)
            
            if response.status_code == 200:
                playlist = response.json()
                playlist_id = playlist['id']
                self.created_playlist_ids.append(playlist_id)
                self.log_test("Playlist Management", f"Created playlist '{playlist['name']}' with ID {playlist_id}")
                
                # Validate playlist structure
                required_fields = ['id', 'name', 'videos', 'created_at', 'updated_at']
                if all(field in playlist for field in required_fields):
                    self.log_test("Playlist Management", "Playlist creation response has correct structure")
                else:
                    self.log_test("Playlist Management", "Playlist creation response missing required fields", False)
                    all_passed = False
            else:
                self.log_test("Playlist Management", f"Failed to create playlist: {response.status_code}", False)
                all_passed = False
                return False
            
            # Test 2: Get all playlists
            response = self.session.get(f"{self.base_url}/playlists")
            if response.status_code == 200:
                playlists = response.json()
                if isinstance(playlists, list) and len(playlists) > 0:
                    self.log_test("Playlist Management", f"Retrieved {len(playlists)} playlists")
                else:
                    self.log_test("Playlist Management", "No playlists found or invalid response", False)
                    all_passed = False
            else:
                self.log_test("Playlist Management", f"Failed to get playlists: {response.status_code}", False)
                all_passed = False
            
            # Test 3: Get specific playlist
            response = self.session.get(f"{self.base_url}/playlists/{playlist_id}")
            if response.status_code == 200:
                playlist = response.json()
                if playlist['id'] == playlist_id:
                    self.log_test("Playlist Management", f"Retrieved specific playlist {playlist_id}")
                else:
                    self.log_test("Playlist Management", "Retrieved playlist ID mismatch", False)
                    all_passed = False
            else:
                self.log_test("Playlist Management", f"Failed to get specific playlist: {response.status_code}", False)
                all_passed = False
            
            # Test 4: Add video to playlist
            video_data = {
                'video_id': 'dQw4w9WgXcQ',
                'title': 'Test Song',
                'description': 'A test song for playlist testing',
                'thumbnail_url': 'https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg',
                'duration': 'PT3M33S',
                'channel_title': 'Test Channel',
                'view_count': '1000000',
                'published_at': '2023-01-01T00:00:00Z'
            }
            
            response = self.session.post(f"{self.base_url}/playlists/{playlist_id}/videos", json=video_data)
            if response.status_code == 200:
                self.log_test("Playlist Management", "Successfully added video to playlist")
                
                # Verify video was added
                response = self.session.get(f"{self.base_url}/playlists/{playlist_id}")
                if response.status_code == 200:
                    playlist = response.json()
                    if len(playlist['videos']) == 1 and playlist['videos'][0]['id'] == video_data['video_id']:
                        self.log_test("Playlist Management", "Video correctly added to playlist")
                    else:
                        self.log_test("Playlist Management", "Video not found in playlist after adding", False)
                        all_passed = False
            else:
                self.log_test("Playlist Management", f"Failed to add video to playlist: {response.status_code}", False)
                all_passed = False
            
            # Test 5: Remove video from playlist
            response = self.session.delete(f"{self.base_url}/playlists/{playlist_id}/videos/{video_data['video_id']}")
            if response.status_code == 200:
                self.log_test("Playlist Management", "Successfully removed video from playlist")
                
                # Verify video was removed
                response = self.session.get(f"{self.base_url}/playlists/{playlist_id}")
                if response.status_code == 200:
                    playlist = response.json()
                    if len(playlist['videos']) == 0:
                        self.log_test("Playlist Management", "Video correctly removed from playlist")
                    else:
                        self.log_test("Playlist Management", "Video still found in playlist after removal", False)
                        all_passed = False
            else:
                self.log_test("Playlist Management", f"Failed to remove video from playlist: {response.status_code}", False)
                all_passed = False
            
            # Test 6: Delete playlist
            response = self.session.delete(f"{self.base_url}/playlists/{playlist_id}")
            if response.status_code == 200:
                self.log_test("Playlist Management", "Successfully deleted playlist")
                self.created_playlist_ids.remove(playlist_id)
                
                # Verify playlist was deleted
                response = self.session.get(f"{self.base_url}/playlists/{playlist_id}")
                if response.status_code == 404:
                    self.log_test("Playlist Management", "Playlist correctly deleted")
                else:
                    self.log_test("Playlist Management", "Playlist still exists after deletion", False)
                    all_passed = False
            else:
                self.log_test("Playlist Management", f"Failed to delete playlist: {response.status_code}", False)
                all_passed = False
                
        except Exception as e:
            self.log_test("Playlist Management", f"Exception occurred: {str(e)}", False)
            all_passed = False
        
        if all_passed:
            self.test_results['playlist_management']['passed'] = True
            self.test_results['playlist_management']['details'] = "All CRUD operations passed successfully"
        else:
            self.test_results['playlist_management']['details'] = "Some CRUD operations failed"
            
        return all_passed
    
    def test_database_models(self) -> bool:
        """Test Database Models and Operations"""
        print("\n🗄️ Testing Database Models...")
        
        all_passed = True
        
        try:
            # Test status check model (basic database operation)
            status_data = {'client_name': 'test_client'}
            response = self.session.post(f"{self.base_url}/status", json=status_data)
            
            if response.status_code == 200:
                status = response.json()
                required_fields = ['id', 'client_name', 'timestamp']
                if all(field in status for field in required_fields):
                    self.log_test("Database Models", "StatusCheck model working correctly")
                    
                    # Test retrieving status checks
                    response = self.session.get(f"{self.base_url}/status")
                    if response.status_code == 200:
                        statuses = response.json()
                        if isinstance(statuses, list) and len(statuses) > 0:
                            self.log_test("Database Models", f"Retrieved {len(statuses)} status checks")
                        else:
                            self.log_test("Database Models", "Failed to retrieve status checks", False)
                            all_passed = False
                    else:
                        self.log_test("Database Models", f"Failed to get status checks: {response.status_code}", False)
                        all_passed = False
                else:
                    self.log_test("Database Models", "StatusCheck model missing required fields", False)
                    all_passed = False
            else:
                self.log_test("Database Models", f"Failed to create status check: {response.status_code}", False)
                all_passed = False
            
            # Test playlist model (already tested in playlist management, but verify structure)
            playlist_data = {'name': 'Model Test Playlist'}
            response = self.session.post(f"{self.base_url}/playlists", json=playlist_data)
            
            if response.status_code == 200:
                playlist = response.json()
                self.created_playlist_ids.append(playlist['id'])
                
                # Verify Playlist model structure
                required_fields = ['id', 'name', 'videos', 'created_at', 'updated_at']
                if all(field in playlist for field in required_fields):
                    self.log_test("Database Models", "Playlist model structure correct")
                    
                    # Test adding video to verify YouTubeVideo model
                    video_data = {
                        'video_id': 'test123',
                        'title': 'Model Test Video',
                        'description': 'Testing video model',
                        'thumbnail_url': 'https://example.com/thumb.jpg',
                        'duration': 'PT4M20S',
                        'channel_title': 'Test Channel',
                        'view_count': '500000',
                        'published_at': '2023-06-01T12:00:00Z'
                    }
                    
                    response = self.session.post(f"{self.base_url}/playlists/{playlist['id']}/videos", json=video_data)
                    if response.status_code == 200:
                        # Verify video was stored correctly
                        response = self.session.get(f"{self.base_url}/playlists/{playlist['id']}")
                        if response.status_code == 200:
                            updated_playlist = response.json()
                            if len(updated_playlist['videos']) == 1:
                                video = updated_playlist['videos'][0]
                                video_required_fields = ['id', 'title', 'description', 'thumbnail_url', 'duration', 'channel_title', 'view_count', 'published_at']
                                if all(field in video for field in video_required_fields):
                                    self.log_test("Database Models", "YouTubeVideo model structure correct")
                                else:
                                    self.log_test("Database Models", "YouTubeVideo model missing required fields", False)
                                    all_passed = False
                            else:
                                self.log_test("Database Models", "Video not properly stored in playlist", False)
                                all_passed = False
                        else:
                            self.log_test("Database Models", "Failed to retrieve updated playlist", False)
                            all_passed = False
                    else:
                        self.log_test("Database Models", "Failed to add video for model testing", False)
                        all_passed = False
                else:
                    self.log_test("Database Models", "Playlist model missing required fields", False)
                    all_passed = False
            else:
                self.log_test("Database Models", f"Failed to create playlist for model testing: {response.status_code}", False)
                all_passed = False
                
        except Exception as e:
            self.log_test("Database Models", f"Exception occurred: {str(e)}", False)
            all_passed = False
        
        if all_passed:
            self.test_results['database_models']['passed'] = True
            self.test_results['database_models']['details'] = "All database models working correctly with proper structure"
        else:
            self.test_results['database_models']['details'] = "Some database model issues found"
            
        return all_passed
    
    def cleanup(self):
        """Clean up created test data"""
        print("\n🧹 Cleaning up test data...")
        for playlist_id in self.created_playlist_ids:
            try:
                response = self.session.delete(f"{self.base_url}/playlists/{playlist_id}")
                if response.status_code == 200:
                    self.log_test("Cleanup", f"Deleted test playlist {playlist_id}")
                else:
                    self.log_test("Cleanup", f"Failed to delete playlist {playlist_id}", False)
            except Exception as e:
                self.log_test("Cleanup", f"Error deleting playlist {playlist_id}: {str(e)}", False)
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Muse Backend API Tests")
        print(f"Testing API at: {self.base_url}")
        print("=" * 60)
        
        # Check API health first
        if not self.test_api_health():
            print("\n❌ API is not accessible. Cannot proceed with tests.")
            return False
        
        # Run all tests
        tests = [
            ('YouTube API Integration', self.test_youtube_api_integration),
            ('Music Search Endpoint', self.test_music_search_endpoint),
            ('Playlist Management', self.test_playlist_management),
            ('Database Models', self.test_database_models)
        ]
        
        all_passed = True
        for test_name, test_func in tests:
            try:
                result = test_func()
                if not result:
                    all_passed = False
            except Exception as e:
                self.log_test(test_name, f"Test failed with exception: {str(e)}", False)
                all_passed = False
        
        # Cleanup
        self.cleanup()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"{status} {test_name.replace('_', ' ').title()}: {result['details']}")
        
        print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
        return all_passed

if __name__ == "__main__":
    tester = MuseBackendTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)