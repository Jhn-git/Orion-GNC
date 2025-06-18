document.addEventListener('DOMContentLoaded', () => {
    // Legacy command interface elements
    const commandInput = document.getElementById('commandInput');
    const sendCommandBtn = document.getElementById('sendCommand');
    const commandQueue = document.getElementById('commandQueue');

    // Mission plan builder elements
    const missionName = document.getElementById('missionName');
    const commandType = document.getElementById('commandType');
    const commandValue = document.getElementById('commandValue');
    const addCommandBtn = document.getElementById('addCommand');
    const submitMissionBtn = document.getElementById('submitMission');
    const clearMissionBtn = document.getElementById('clearMission');
    const commandSequence = document.getElementById('commandSequence');
    const activeMissions = document.getElementById('activeMissions');
    const refreshStatusBtn = document.getElementById('refreshStatus');

    // Mission Analysis elements
    const missionLogSelector = document.getElementById('missionLogSelector');
    const refreshLogsBtn = document.getElementById('refreshLogsBtn');
    const analysisQuestion = document.getElementById('analysisQuestion');
    const analyzeMissionBtn = document.getElementById('analyzeMissionBtn');
    const analysisResult = document.getElementById('analysisResult');

    // Mission plan data
    let currentMissionSequence = [];
    let activeMissionIds = new Set();

    // Legacy command functionality
    sendCommandBtn.addEventListener('click', () => {
        const command = commandInput.value;
        if (command) {
            fetch('/send_command', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command: command }),
            })
            .then(response => response.json())
            .then(data => {
                console.log('Success:', data);
                displayMessage('Command sent successfully', 'success');
            })
            .catch((error) => {
                console.error('Error:', error);
                displayMessage('Error sending command', 'error');
            });
            const listItem = document.createElement('li');
            listItem.textContent = command;
            commandQueue.appendChild(listItem);
            commandInput.value = '';
        }
    });

    // Mission plan builder functionality
    addCommandBtn.addEventListener('click', () => {
        const command = commandType.value;
        const value = commandValue.value;

        const commandObj = { 
            command: command,
            parameters: {}  // Always include parameters object
        };
        
        if (command === 'WAIT' && value) {
            // Use delay_ms for WAIT commands
            commandObj.delay_ms = parseInt(value) || 0;
        } else if (value && !['STAGE', 'WAIT_UNTIL_APOAPSIS', 'ACTIVATE_RCS', 'DEACTIVATE_RCS'].includes(command)) {
            // For other commands with values, add to parameters
            commandObj.parameters.value = parseFloat(value) || value;
        }

        currentMissionSequence.push(commandObj);
        renderCommandSequence();
        
        // Clear value input
        commandValue.value = '';
    });

    submitMissionBtn.addEventListener('click', () => {
        if (!missionName.value.trim()) {
            displayMessage('Please enter a mission name', 'error');
            return;
        }

        if (currentMissionSequence.length === 0) {
            displayMessage('Please add at least one command to the sequence', 'error');
            return;
        }

        const missionPlan = {
            mission_id: missionName.value.trim() || generateUUID(),
            flight_plan: currentMissionSequence
        };

        fetch('/submit_mission', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(missionPlan),
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayMessage(`Mission submitted successfully! ID: ${data.mission_id}`, 'success');
                activeMissionIds.add(data.mission_id);
                clearMissionBuilder();
                setTimeout(refreshMissionStatus, 1000); // Refresh status after a delay
            } else {
                displayMessage(`Error: ${data.message}`, 'error');
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            displayMessage('Error submitting mission plan', 'error');
        });
    });

    clearMissionBtn.addEventListener('click', () => {
        clearMissionBuilder();
    });

    refreshStatusBtn.addEventListener('click', () => {
        refreshMissionStatus();
    });

    // Helper functions
    function renderCommandSequence() {
        commandSequence.innerHTML = '';
        currentMissionSequence.forEach((cmd, index) => {
            const div = document.createElement('div');
            div.className = 'command-row';
            div.innerHTML = `
                <strong>${index + 1}.</strong> ${cmd.command}
                ${cmd.parameters.value !== undefined ? ` (${cmd.parameters.value})` : 
                  cmd.delay_ms !== undefined ? ` (${cmd.delay_ms}ms)` : ''}
                <button class="button danger" onclick="removeCommand(${index})">Remove</button>
            `;
            commandSequence.appendChild(div);
        });
    }

    function clearMissionBuilder() {
        missionName.value = '';
        currentMissionSequence = [];
        renderCommandSequence();
    }

    function displayMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.textContent = message;
        messageDiv.style.padding = '10px';
        messageDiv.style.margin = '10px 0';
        messageDiv.style.borderRadius = '3px';
        messageDiv.style.backgroundColor = type === 'success' ? '#d4edda' : '#f8d7da';
        messageDiv.style.color = type === 'success' ? '#155724' : '#721c24';
        messageDiv.style.border = type === 'success' ? '1px solid #c3e6cb' : '1px solid #f5c6cb';
        
        const container = document.querySelector('.container');
        container.insertBefore(messageDiv, container.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            messageDiv.remove();
        }, 5000);
    }

    function refreshMissionStatus() {
        activeMissions.innerHTML = 'Loading...';
        // In a real implementation, we would fetch active missions
        setTimeout(() => {
            if (activeMissionIds.size > 0) {
                activeMissions.innerHTML = Array.from(activeMissionIds)
                    .map(id => `<div>Mission ID: ${id} - Status: <span class="status-queued">QUEUED</span></div>`)
                    .join('');
            } else {
                activeMissions.innerHTML = 'No active missions';
            }
        }, 1000);
    }

    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    // Expose removeCommand globally for button onclick
    window.removeCommand = function(index) {
        currentMissionSequence.splice(index, 1);
        renderCommandSequence();
    };

    // Load sample missions
    document.getElementById('loadOrbitalInsertion').addEventListener('click', () => loadSampleMission('orbital_insertion'));
    document.getElementById('loadSimpleAscent').addEventListener('click', () => loadSampleMission('simple_ascent'));

    function loadSampleMission(missionType) {
        clearMissionBuilder();
        
        switch (missionType) {
            case 'orbital_insertion':
                missionName.value = 'Orbital Insertion Test';
                currentMissionSequence = [
                    { command: 'SET_THROTTLE', parameters: { value: 1.0 } },
                    { command: 'WAIT', parameters: {}, delay_ms: 10000 },
                    { command: 'STAGE', parameters: {} },
                    { command: 'SET_THROTTLE', parameters: { value: 0.8 } },
                    { command: 'SET_PITCH', parameters: { value: 45 } },
                    { command: 'WAIT_UNTIL_APOAPSIS', parameters: {} },
                    { command: 'SET_THROTTLE', parameters: { value: 0.0 } },
                    { command: 'ACTIVATE_RCS', parameters: {} }
                ];
                break;
            case 'simple_ascent':
                missionName.value = 'Simple Ascent Test';
                currentMissionSequence = [
                    { command: 'SET_THROTTLE', parameters: { value: 1.0 } },
                    { command: 'WAIT', parameters: {}, delay_ms: 5000 },
                    { command: 'SET_PITCH', parameters: { value: 80 } },
                    { command: 'WAIT', parameters: {}, delay_ms: 5000 },
                    { command: 'STAGE', parameters: {} },
                    { command: 'SET_THROTTLE', parameters: { value: 0.0 } }
                ];
                break;
        }
        
        renderCommandSequence();
    }

    // Mission analysis functionality
    refreshLogsBtn.addEventListener('click', refreshMissionLogs);
    analyzeMissionBtn.addEventListener('click', performMissionAnalysis);

    function refreshMissionLogs() {
        fetch('/list_mission_logs')
            .then(response => response.json())
            .then(logs => {
                missionLogSelector.innerHTML = '';
                if (logs.length > 0) {
                    logs.forEach(log => {
                        const option = document.createElement('option');
                        option.value = log;
                        option.textContent = log;
                        missionLogSelector.appendChild(option);
                    });
                } else {
                    const option = document.createElement('option');
                    option.textContent = 'No logs found';
                    missionLogSelector.appendChild(option);
                }
            });
    }

    function performMissionAnalysis() {
        const logFile = missionLogSelector.value;
        const question = analysisQuestion.value;
        
        if (!logFile || logFile === 'No logs found') {
            displayMessage('Please select a mission log first', 'error');
            return;
        }
        
        if (!question) {
            displayMessage('Please enter a question about the mission log', 'error');
            return;
        }
        
        fetch('/analyze_mission', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                log_file: logFile,
                question: question
            }),
        })
        .then(response => response.json())
        .then(data => {
            analysisResult.innerHTML = data.results.map(result => `<p>${result}</p>`).join('');
        })
        .catch((error) => {
            console.error('Error:', error);
            analysisResult.innerHTML = '<p>Error performing analysis</p>';
        });
    }

    // Initial setup
    refreshMissionLogs();
});