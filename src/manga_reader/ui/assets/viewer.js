"use strict";

// Global state
let bridge = null;

// Initialize WebChannel
document.addEventListener("DOMContentLoaded", () => {
    if (typeof qt !== 'undefined' && qt.webChannelTransport) {
        new QWebChannel(qt.webChannelTransport, function(channel) {
            console.log("QWebChannel connected.");
            
            bridge = channel.objects.connector;
            if (!bridge) {
                console.error("Connector object not found in WebChannel objects:", channel.objects);
                return;
            }
            
            console.log("Bridge object found:", bridge);
            // We no longer connect to Python signals here.
            // Python will call updateView() directly via runJavaScript.
        });
    } else {
        console.error("Qt WebChannel not found! Ensure this is running inside QWebEngineView.");
    }
    
    // Handle window resize
    window.addEventListener("resize", () => {
        if (lastData) {
            renderPages(lastData);
        }
    });
});

function requestUpdate() {
    if (bridge) {
        // Optional: ask python for state if needed
    }
}

let lastData = null;

// This function is called directly by Python
function updateView(data) {
    try {
        console.log("Received data update via runJavaScript.");
        lastData = data;
        renderPages(data);
    } catch (e) {
        console.error("Failed to render pages:", e);
    }
}

function renderPages(data) {
    const wrapper = document.getElementById("content-wrapper");
    if (!wrapper) return;
    wrapper.innerHTML = ""; // Clear current content
    
    const pages = data.pages;
    const gap = data.gap || 20;
    
    let totalWidth = 0;
    let maxHeight = 0;
    
    pages.forEach((page, index) => {
        const pageEl = createPageElement(page);
        wrapper.appendChild(pageEl);
        
        totalWidth += page.width;
        maxHeight = Math.max(maxHeight, page.height);
        
        // Add gap if not last
        if (index < pages.length - 1) {
            pageEl.style.marginRight = gap + "px";
            totalWidth += gap;
        }
    });
    
    // Update CSS variables / scaling
    const viewport = document.getElementById("viewport");
    const vWidth = viewport.clientWidth;
    const vHeight = viewport.clientHeight;
    
    // Calculate Scale
    let scale = Math.min(vWidth / totalWidth, vHeight / maxHeight);
    if (scale <= 0) scale = 1.0;
    
    // Apply layout
    wrapper.style.width = totalWidth + "px";
    wrapper.style.height = maxHeight + "px";
    wrapper.style.transform = `scale(${scale})`;
}

function createPageElement(pageData) {
    const container = document.createElement("div");
    container.className = "page-container";
    container.style.width = pageData.width + "px";
    container.style.height = pageData.height + "px";
    
    // Image
    const img = document.createElement("img");
    img.className = "page-image";
    img.src = pageData.imageUrl; 
    container.appendChild(img);
    
    // OCR Blocks
    if (pageData.blocks) {
        pageData.blocks.forEach(block => {
            const blockEl = createBlockElement(block);
            container.appendChild(blockEl);
        });
    }
    
    return container;
}

function createBlockElement(block) {
    const el = document.createElement("div");
    el.className = "ocr-block";
    el.style.left = block.x + "px";
    el.style.top = block.y + "px";
    el.style.width = block.width + "px";
    el.style.height = block.height + "px";
    
    // Add click listener to notify Python
    el.onclick = (e) => {
        // e.stopPropagation();
        // Provide empty callback to force message ID generation, 
        // which prevents "JSON message object is missing the id property" error
        if (bridge) bridge.blockClicked(block.id, () => {});
    };
    
    // Lines
    if (block.lines) {
        block.lines.forEach(lineText => {
            const lineEl = document.createElement("div");
            lineEl.className = "ocr-line";
            lineEl.textContent = lineText;
            lineEl.style.fontSize = block.fontSize + "px";
            el.appendChild(lineEl);
        });
    }
    
    return el;
}
