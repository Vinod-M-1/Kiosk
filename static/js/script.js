function captureText() {
    const output = document.getElementById('output');
    const status = document.getElementById('status');
    
    status.innerText = "Scanning Text...";
    
    fetch('/capture', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            output.innerText = data.text || "No clear text detected.";
            status.innerText = "Text Captured!";
        })
        .catch(err => {
            console.error(err);
            status.innerText = "Error Scanning";
        });
}

function describeScene() {
    const output = document.getElementById('output');
    const status = document.getElementById('status');
    
    status.innerText = "AI is thinking...";
    
    fetch('/describe', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            output.innerText = data.summary;
            status.innerText = "Scene Described";
        })
        .catch(err => {
            console.error(err);
            status.innerText = "AI Connection Failed";
        });
}