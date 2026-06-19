# AI Creative Factory

AI Creative Factory is a local AI-powered video production pipeline for generating short educational talking-avatar videos.

## Main Workflow

`	ext
n8n Simple Trigger
-> Production Pipeline Server
-> Voice Generation
-> Talking Avatar Generation
-> Final Video Rendering
-> Episode Logging
`

## Features

- Local Python production server on port 8110
- Arabic educational short video generation
- Topic matrix with up to 200 ideas
- Fixed character library support
- Edge TTS voice generation
- Wav2Lip talking-avatar generation
- FFmpeg final rendering
- Unique archived video per episode
- Written outro card
- Optional Google Sheet logging

## Public Repository Notice

This public version does not include private character images, generated videos, voice files, AI model checkpoints, API keys, or n8n credentials.

## Default Endpoints

Health check:

`	ext
http://127.0.0.1:8110/health
`

Produce episode:

`	ext
http://127.0.0.1:8110/produce-episode
`

## Author

Developed by Ehab Shehab.
