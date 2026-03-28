document.getElementById('captureBtn').addEventListener('click', function () {
    const status = document.getElementById('status');
    const resultDisplay = document.getElementById('resultText');

    status.innerText = "Scanning...";

    fetch('/capture', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.text) {
                resultDisplay.innerText = data.text;
                status.innerText = "Capture Successful!";
            } else {
                resultDisplay.innerText = "No text found.";
                status.innerText = "Scan failed.";
            }
        })
        .catch(err => {
            console.error(err);
            status.innerText = "Error!";
        });
});