# Web-Based Random Slideshow (V4.1 - Development)

**Cél**: Kiegészítés Spotify-val


This project is a high-performance, web-based random photo slideshow that pulls images from Backblaze B2. It is designed to be flicker-free and works on any device with a modern web browser.

## Key Features

### 1. Flicker-Free Transitions
- Uses a dual-buffer strategy in the browser.
- Smooth CSS `opacity` transitions (cross-fade).
- Background preloading of the next image to eliminate loading gaps.

### 2. B2 API Optimization
- **Client Reuse**: Dramatically reduces authorization calls to Backblaze.
- **Token Caching**: Caches download authorization tokens for 2 hours.
- **Improved Reliability**: Fixes "transaction cap exceeded" errors even with fast image switching.

### 3. Customizable Filename Display
- Optional filename overlay at the bottom of the screen.
- Toggleable directly from the Dashboard.
- Clean, semi-transparent badge design for maximum readability.

### 4. Simplified Web Dashboard
- Easy management of B2 bucket connections.
- Global start/stop controls.
- Adjustable slideshow interval.
- Direct link to the Slideshow Receiver.

## How to use

1.  **Requirement**: Run all commands from the project root directory:
    `C:\Users\zsolt.tuske\.gemini\antigravity\playground\swift-newton\`

2.  **Installation**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Start the server**:
    ```bash
    python -m backend.main
    ```
3.  **Configure**:
    - Open `http://localhost:8080`.
    - Connect your Backblaze B2 bucket (Key ID, Application Key, Bucket Name).
    - Click "Resync" to index your photos.
4.  **Run Slideshow**:
    - Click "Start" on the Dashboard.
    - Click the "Open Slideshow Receiver" link or open `http://<your-ip>:8080/receiver` on any device.

## Versions
- **V4.1**: Development branch (Spotify integration - in progress).
- **V3.2**: Current stable release (Refined UX design).
- **V3.1**: GoogleCast integration via `catt`, Consolidated UI, Dynamic Settings.
- **V3.0**: Stable release (Optimized B2, Web-based, Flicker-free).
- **v1.0-chromecast**: Legacy version for direct Chromecast casting (deprecated).

