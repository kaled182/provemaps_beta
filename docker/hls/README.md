# Video HLS Gateway

This container accepts RTMP publishes and exposes the resulting HLS playlist for the browser preview.

## Ports

- RTMP ingest: `rtmp://localhost:1935/live/<stream_key>`
- HLS playback: `http://localhost:8082/hls/<stream_key>.m3u8`

Both ports are exposed by the container and work across the Docker network using the service name `video-hls`.

## Usage

1. Start the service:
   ```bash
   docker compose up -d video-hls
   ```
2. Publish a stream, e.g. with FFmpeg:
   ```bash
   ffmpeg -i rtmp://camera/input -c:v copy -f flv rtmp://localhost:1935/live/camera01
   ```
3. Configure the gateway preview with the resulting HLS URL:
   ```
   http://localhost:8082/hls/camera01.m3u8
   ```

The playlist uses 4 second segments with a 60 second sliding window for smooth playback. Cross-origin headers are enabled so the SPA can request the stream directly.
