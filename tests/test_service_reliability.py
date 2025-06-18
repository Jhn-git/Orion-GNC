"""
Test suite for Orion GNC Service Reliability
Tests the critical findings from the Playwright browser automation testing.
"""
import pytest
import requests
import websocket
import json
from typing import Dict, Any
import time

class TestOrionGNCReliability:
    """Test suite validating service reliability findings."""
    
    BASE_URLS = {
        'mission_control': 'http://localhost:5000',
        'telemetry_dashboard': 'http://localhost:5002',
        'mission_sequencer': 'http://localhost:5001',
        'gnc_flight_control': 'ws://localhost:8765'
    }
    
    def test_mission_control_ui_loads(self):
        """Test that Mission Control UI loads successfully."""
        response = requests.get(self.BASE_URLS['mission_control'])
        assert response.status_code == 200
        assert "Mission Control" in response.text
        
    def test_telemetry_dashboard_loads(self):
        """Test that Telemetry Dashboard loads successfully."""
        response = requests.get(self.BASE_URLS['telemetry_dashboard'])
        assert response.status_code == 200
        assert "Live Telemetry" in response.text
        
    def test_mission_control_static_assets(self):
        """Test that Mission Control static assets are accessible."""
        response = requests.get(f"{self.BASE_URLS['mission_control']}/main.js")
        assert response.status_code in [200, 304]  # OK or Not Modified
        
    def test_telemetry_dashboard_static_assets(self):
        """Test that Telemetry Dashboard static assets are accessible."""
        response = requests.get(f"{self.BASE_URLS['telemetry_dashboard']}/main.js")
        assert response.status_code == 200
        
    def test_mission_logs_endpoint(self):
        """Test that mission logs endpoint is accessible."""
        response = requests.get(f"{self.BASE_URLS['mission_control']}/list_mission_logs")
        assert response.status_code == 200
        
    def test_mission_submission_fails_with_502(self):
        """Test that mission submission currently fails with 502 (known issue)."""
        mission_data = {
            "mission_name": "Test Mission Alpha",
            "commands": [{"command": "SET_THROTTLE", "value": 75}]
        }
        response = requests.post(
            f"{self.BASE_URLS['mission_control']}/submit_mission",
            json=mission_data
        )
        # This test expects the current failure state
        assert response.status_code == 502, "Mission submission should fail with 502 Bad Gateway"
        
    def test_mission_sequencer_accessibility(self):
        """Test if mission sequencer service is accessible."""
        try:
            response = requests.get(self.BASE_URLS['mission_sequencer'], timeout=5)
            # If this passes, the service is up
            assert response.status_code in [200, 404, 405], "Service should respond"
        except requests.exceptions.RequestException:
            # This is expected based on our findings
            pytest.fail("Mission Sequencer service not accessible - expected based on 502 errors")
            
    def test_websocket_connection_attempt(self):
        """Test WebSocket connection to GNC Flight Control."""
        try:
            ws = websocket.create_connection(
                self.BASE_URLS['gnc_flight_control'],
                timeout=5
            )
            # If connection succeeds, it should stay open briefly
            time.sleep(1)
            ws.close()
            # Connection established successfully
            assert True
        except Exception as e:
            # WebSocket connection issues expected based on findings
            pytest.fail(f"WebSocket connection failed: {e}")
            
    def test_service_health_indicators(self):
        """Test that services provide some form of health indication."""
        # Mission Control should at least load
        mc_response = requests.get(self.BASE_URLS['mission_control'])
        assert mc_response.status_code == 200
        
        # Telemetry Dashboard should at least load  
        td_response = requests.get(self.BASE_URLS['telemetry_dashboard'])
        assert td_response.status_code == 200
        
        # Both should have basic content
        assert len(mc_response.text) > 100, "Mission Control should have substantial content"
        assert len(td_response.text) > 100, "Telemetry Dashboard should have substantial content"

class TestExpectedFailures:
    """Tests that document known failure states for tracking fixes."""
    
    BASE_URLS = {
        'mission_control': 'http://localhost:5000',
        'telemetry_dashboard': 'http://localhost:5002',
        'mission_sequencer': 'http://localhost:5001'
    }
    
    @pytest.mark.xfail(reason="Mission submission currently fails with 502 Bad Gateway")
    def test_mission_submission_should_succeed(self):
        """Test that mission submission should work (currently failing)."""
        mission_data = {
            "mission_name": "Test Mission Alpha", 
            "commands": [{"command": "SET_THROTTLE", "value": 75}]
        }
        response = requests.post(
            f"{self.BASE_URLS['mission_control']}/submit_mission",
            json=mission_data
        )
        assert response.status_code == 200
        
    @pytest.mark.xfail(reason="Mission Sequencer service communication failing")
    def test_mission_sequencer_should_be_accessible(self):
        """Test that mission sequencer should be accessible (currently failing)."""
        response = requests.get(self.BASE_URLS['mission_sequencer'])
        assert response.status_code == 200
        
    @pytest.mark.xfail(reason="WebSocket connections not stable")
    def test_websocket_should_maintain_connection(self):
        """Test that WebSocket connections should be stable (currently failing)."""
        ws = websocket.create_connection("ws://localhost:8765")
        time.sleep(10)  # Should maintain connection for 10 seconds
        # Send ping to test connection
        ws.send(json.dumps({"type": "ping"}))
        response = ws.recv()
        ws.close()
        assert response is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])