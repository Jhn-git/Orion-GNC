class WebSocketManager {
    constructor(url) {
        this.url = url;
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000; // Start with 1 second

        this.altitudeElement = document.getElementById("altitude");
        this.speedElement = document.getElementById("speed");
        this.fuelElement = document.getElementById("fuel");
        this.apoapsisElement = document.getElementById("apoapsis");
        this.periapsisElement = document.getElementById("periapsis");
        this.statusElement = document.getElementById("connection-status");
    }

    updateStatusUI(status, color) {
        this.statusElement.textContent = `Status: ${status}`;
        this.statusElement.style.color = color;
        console.log(`WebSocket Status: ${status}`);
    }

    connect() {
        this.updateStatusUI('CONNECTING', 'orange');
        this.websocket = new WebSocket(this.url);

        this.websocket.onopen = () => {
            this.updateStatusUI('OPEN', 'green');
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000; // Reset delay on successful connection
            console.log('WebSocket connection established.');
        };

        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.altitudeElement.textContent = `${data.altitude.toFixed(2)} m`;
                this.speedElement.textContent = `${data.velocity.toFixed(2)} m/s`;
                // Assuming stage_resources gives fuel info
                if (data.stage_resources && data.stage_resources.length > 0) {
                    const liquidFuel = data.stage_resources.find(r => r.name === 'LiquidFuel');
                    if (liquidFuel) {
                        const fuelPercentage = (liquidFuel.amount / liquidFuel.max) * 100;
                        this.fuelElement.textContent = `${fuelPercentage.toFixed(2)}%`;
                    }
                }
                this.apoapsisElement.textContent = `${data.apoapsis.toFixed(2)} m`;
                this.periapsisElement.textContent = `${data.periapsis.toFixed(2)} m`;
            } catch (error) {
                console.error("Error parsing telemetry data:", error);
            }
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateStatusUI('ERROR', 'red');
        };

        this.websocket.onclose = (event) => {
            this.updateStatusUI(`CLOSED (Code: ${event.code})`, 'red');
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const delay = this.reconnectDelay;
                this.updateStatusUI(`RECONNECTING (Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay / 1000}s)`, 'orange');
                setTimeout(() => this.connect(), delay);
                this.reconnectDelay = Math.min(30000, this.reconnectDelay * 2); // Cap at 30s
            } else {
                this.updateStatusUI('DISCONNECTED (Max retries reached)', 'red');
                console.error('WebSocket reconnection failed after max attempts.');
            }
        };
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const socketManager = new WebSocketManager('ws://localhost:8765');
    socketManager.connect();
});