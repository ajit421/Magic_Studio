// SETUP DROP ZONE
const zone = document.getElementById('image-drop-zone');
const input = document.getElementById('image-file');
const preview = document.getElementById('image-preview');

zone.addEventListener('click', () => input.click());

input.addEventListener('change', () => {
    if (input.files.length) {
        const file = input.files[0];
        // Show preview immediately
        preview.src = URL.createObjectURL(file);
        preview.classList.remove('hidden');
        document.querySelector('.drop-zone p').innerText = "✅ Image Selected: " + file.name;
    }
});

// GENERATE FUNCTION
async function generateImage() {
    const prompt = document.getElementById('image-prompt').value;
    const style = document.getElementById('image-style').value;
    const fileInput = document.getElementById('image-file');

    if (!prompt && fileInput.files.length === 0) {
        alert("Please upload an image OR enter a prompt!");
        return;
    }

    // UI Updates
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('result-area').classList.add('hidden');
    
    // Create FormData
    const formData = new FormData();
    formData.append('prompt', prompt);
    formData.append('style', style);
    if (fileInput.files.length > 0) {
        formData.append('image', fileInput.files[0]);
    }

    try {
        const response = await fetch('/generate-image', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        document.getElementById('loading').classList.add('hidden');

        if (data.status === 'success') {
            document.getElementById('result-area').classList.remove('hidden');
            
            // Show Original Image (if uploaded)
            const originalContainer = document.getElementById('original-image-container');
            if (fileInput.files.length > 0) {
                originalContainer.innerHTML = `<img src="${preview.src}" alt="Original">`;
            } else {
                originalContainer.innerHTML = `<p style="color:#666;">(Text-to-Image used)</p>`;
            }

            // Show AI Result
            const outputContainer = document.getElementById('generated-result-container');
            outputContainer.innerHTML = `<img src="${data.image_url}" alt="Generated Image">`;
            
            const downloadBtn = document.getElementById('download-btn');
            downloadBtn.href = data.image_url;
            downloadBtn.classList.remove('hidden');
        } else {
            alert("Error: " + data.message);
        }
    } catch (error) {
        console.error(error);
        document.getElementById('loading').classList.add('hidden');
        alert("Server Error. Check console.");
    }
}