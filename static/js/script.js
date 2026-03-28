let recognition = null;
let isRecording = false;
let finalTranscript = "";

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("Speech Recognition Not Supported");
        return null;
    }
    
    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    
    rec.onresult = function(event) {
        let interimTranscript = '';
        let currentFinal = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript + " ";
                currentFinal = finalTranscript;
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }
        document.getElementById('goal-input').value = finalTranscript + interimTranscript;
        document.getElementById('output').innerText = "Listening...";
    };

    rec.onerror = function(event) {
        console.error("Speech error", event.error);
        stopRecording();
        document.getElementById('output').innerText = "Speech Error: " + event.error;
    };
    
    return rec;
}

function toggleMic() {
    const micBtn = document.getElementById('micBtn');
    const micText = document.getElementById('mic-text');
    const waveform = document.getElementById('waveform');
    const output = document.getElementById('output');
    
    if (!recognition) {
        recognition = initSpeechRecognition();
        if (!recognition) {
            output.innerText = "Speech API not supported in this browser.";
            return;
        }
    }

    if (!isRecording) {
        // Start Recording
        isRecording = true;
        finalTranscript = "";
        document.getElementById('goal-input').value = ""; // Clear box on new recording
        output.innerText = "Listening for Goal... Speak now.";
        micBtn.classList.add('recording');
        micText.innerText = "STOP REC";
        waveform.classList.remove('hidden');
        recognition.start();
    } else {
        // Stop Recording
        stopRecording();
        document.getElementById('goal-input').value = finalTranscript;
        output.innerText = "Speech captured. Edit your intent, then hit 'SET GOAL'.";
    }
}

function stopRecording() {
    if (recognition) {
        recognition.stop();
    }
    isRecording = false;
    const micBtn = document.getElementById('micBtn');
    const micText = document.getElementById('mic-text');
    const waveform = document.getElementById('waveform');
    
    micBtn.classList.remove('recording');
    micText.innerText = "DICTATE";
    waveform.classList.add('hidden');
}

function sendGoal() {
    const output = document.getElementById('output');
    const text = document.getElementById('goal-input').value.trim();
    
    if (!text) {
        output.innerText = "Please dictate or type a goal first.";
        return;
    }
    
    output.innerText = "Analyzing Goal: " + text + "...";
    
    fetch('/set_goal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: text })
    })
    .then(response => response.json())
    .then(data => {
        if(data.summary) {
            output.innerText = "> " + data.summary;
        } else {
            output.innerText = "Task acquired.";
        }
    })
    .catch(err => {
        console.error(err);
        output.innerText = "Error Setting Goal";
    });
}

function captureText() {
    const output = document.getElementById('output');
    output.innerText = "Scanning Text...";
    
    fetch('/capture', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            output.innerText = "> " + (data.text || "No clear text detected.");
        })
        .catch(err => {
            console.error(err);
            output.innerText = "Error Scanning";
        });
}

function describeScene() {
    const output = document.getElementById('output');
    output.innerText = "AI is analyzing layout...";
    
    fetch('/describe', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            output.innerText = "> " + data.summary;
        })
        .catch(err => {
            console.error(err);
            output.innerText = "AI Connection Failed";
        });
}

// Background Polling for live status (Hand detected, Current goal)
function updateStatusDisplay() {
    fetch('/status')
        .then(res => res.json())
        .then(data => {
            const goalDisplay = document.getElementById('current-goal-display');
            if (goalDisplay) goalDisplay.innerText = data.current_goal;
            
            const targetDisplay = document.getElementById('target-button-display');
            if (targetDisplay) targetDisplay.innerText = data.target_button;

            const handIndicator = document.getElementById('hand-indicator');
            if (handIndicator) {
                if (data.hand_detected) {
                    handIndicator.classList.add('active');
                } else {
                    handIndicator.classList.remove('active');
                }
            }
        })
        .catch(err => console.log(err));
}

// Poll every 1 second
setInterval(updateStatusDisplay, 1000);
updateStatusDisplay();