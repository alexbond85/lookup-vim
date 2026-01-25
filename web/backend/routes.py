import os
import subprocess
import sys

from fastapi import APIRouter, Header, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from web.backend.models import (
    ConversationRequest,
    HistoryResponse,
    LookupRequest,
)
from web.backend.session import SessionManager
from lookup.domain import SelectionData
from lookup.config import get_recent_files, add_recent_file

router = APIRouter(prefix="/api")
sessions = SessionManager()


def _check_api_key():
    """Check if OpenAI API key is configured"""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key or api_key.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key is not configured. Please set your API key in Settings (Menu → Settings)."
        )


class ConfigUpdateRequest(BaseModel):
    source_lang: str
    target_lang: str
    openai_api_key: str | None = None


@router.post("/lookup")
async def lookup(request: LookupRequest, x_session_id: str = Header(...)):
    """Main translation endpoint - translates selection only (token-optimized)"""
    # Check API key is configured
    _check_api_key()

    print(f"DEBUG /api/lookup received:")
    print(f"  selection: {request.selection!r}")
    print(f"  phrase: {request.phrase!r}")
    print(f"  paragraph: {request.paragraph!r}")
    print(f"  file: {request.file!r}")

    selection_data = SelectionData(
        selection=request.selection,
        phrase=request.phrase or "",
        paragraph=request.paragraph or "",
        file=request.file or ""
    )

    # Use existing LookupService - returns LookupResponse with from_cache
    try:
        lookup_response = sessions.factory.lookup_service.lookup(selection_data)
        result = lookup_response.result
        from_cache = lookup_response.from_cache
    except Exception as e:
        error_msg = str(e)
        # Check for common OpenAI errors
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            raise HTTPException(400, f"API key error: {error_msg}")
        elif "rate_limit" in error_msg.lower() or "rate limit" in error_msg.lower():
            raise HTTPException(429, f"Rate limit exceeded. Please wait a moment and try again.")
        elif "quota" in error_msg.lower():
            raise HTTPException(402, f"API quota exceeded. Please check your OpenAI billing.")
        else:
            raise HTTPException(500, f"Translation error: {error_msg}")

    # Update session - store phrase and paragraph for later
    session = sessions.get_or_create(x_session_id)
    # Reset conversation for new translation (match CLI behavior)
    # Follow-up questions are meant for the current translation only
    session.reset_conversation()
    session.current_phrase = request.phrase
    session.current_paragraph = request.paragraph
    session.reset_context_flags()  # New selection, reset tracking
    session.add_translation(request.selection, result)

    # Track recent file if provided
    if request.file:
        add_recent_file(sessions.factory.config.cache_dir, request.file)

    # Determine if we should show context buttons
    has_phrase = bool(
        request.phrase and
        request.phrase.strip() != request.selection.strip()
    )
    has_paragraph = bool(
        request.paragraph and
        request.paragraph.strip() != request.selection.strip() and
        request.paragraph.strip() != request.phrase.strip()
    )

    print(f"DEBUG context flags:")
    print(f"  has_phrase: {has_phrase}")
    print(f"  has_paragraph: {has_paragraph}")
    print(f"  from_cache: {from_cache}")

    # Return chat messages with context info
    return {
        "messages": session.messages,
        "has_phrase": has_phrase,
        "has_paragraph": has_paragraph,
        "from_cache": from_cache
    }


@router.post("/lookup/phrase")
async def lookup_phrase(x_session_id: str = Header(...)):
    """Translate the stored phrase/sentence (option 1)"""
    _check_api_key()

    session = sessions.get_or_create(x_session_id)

    if not session.current_phrase:
        raise HTTPException(400, "No phrase in context")

    # NEW lookup with phrase as selection
    selection_data = SelectionData(
        selection=session.current_phrase,
        phrase="",
        paragraph="",
        file=""
    )

    try:
        lookup_response = sessions.factory.lookup_service.lookup(selection_data)
        result = lookup_response.result
        from_cache = lookup_response.from_cache
    except Exception as e:
        raise HTTPException(500, f"Translation error: {str(e)}")

    session.add_translation(session.current_phrase, result)
    session.phrase_translated = True  # Mark as translated

    # Check if paragraph is still available (differs from phrase AND not yet translated)
    has_paragraph = bool(
        session.current_paragraph and
        session.current_paragraph.strip() != session.current_phrase.strip() and
        not session.paragraph_translated
    )

    return {
        "messages": session.messages,
        "has_phrase": False,  # Already translated
        "has_paragraph": has_paragraph,
        "from_cache": from_cache
    }


@router.post("/lookup/paragraph")
async def lookup_paragraph(x_session_id: str = Header(...)):
    """Translate the stored paragraph (option 2)"""
    _check_api_key()

    session = sessions.get_or_create(x_session_id)

    if not session.current_paragraph:
        raise HTTPException(400, "No paragraph in context")

    # NEW lookup with paragraph as selection
    selection_data = SelectionData(
        selection=session.current_paragraph,
        phrase="",
        paragraph="",
        file=""
    )

    try:
        lookup_response = sessions.factory.lookup_service.lookup(selection_data)
        result = lookup_response.result
        from_cache = lookup_response.from_cache
    except Exception as e:
        raise HTTPException(500, f"Translation error: {str(e)}")

    session.add_translation(session.current_paragraph, result)
    session.paragraph_translated = True  # Mark as translated

    # Check if phrase is still available (differs from paragraph AND not yet translated)
    has_phrase = bool(
        session.current_phrase and
        session.current_phrase.strip() != session.current_paragraph.strip() and
        not session.phrase_translated
    )

    return {
        "messages": session.messages,
        "has_phrase": has_phrase,
        "has_paragraph": False,  # Already translated
        "from_cache": from_cache
    }


@router.post("/conversation")
async def conversation(
    request: ConversationRequest,
    x_session_id: str = Header(...)
):
    """Follow-up questions"""
    _check_api_key()

    session = sessions.get_or_create(x_session_id)
    try:
        answer = session.conversation_service.generate_response(request.question)
        session.add_conversation(request.question, answer or "")
    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            raise HTTPException(400, f"API key error: {error_msg}")
        else:
            raise HTTPException(500, f"Error generating response: {error_msg}")

    return {"messages": session.messages}


@router.get("/history")
async def get_history(file: str | None = None):
    """Get cached selections from JSONL"""
    cache = sessions.factory.cache
    entries = list(cache._cache.values())

    if file:
        entries = [
            e for e in entries
            if e.get("context", {}).get("file", "").endswith(file)
        ]

    return {"entries": entries}


@router.get("/session/messages")
async def get_session_messages(x_session_id: str = Header(...)):
    """Get current session's chat messages"""
    session = sessions.get_or_create(x_session_id)
    return {"messages": session.messages}


@router.get("/config")
async def get_config():
    """Return current configuration"""
    config = sessions.factory.config
    return {
        "source_lang": sessions.factory.source_lang,
        "target_lang": sessions.factory.target_lang,
        "cache_dir": str(config.cache_dir) if config else ""
    }


@router.post("/config")
async def update_config(request: ConfigUpdateRequest):
    """Update language configuration and API key"""
    import configparser
    import json
    import os
    from pathlib import Path

    # Validate languages
    valid_languages = ["Russian", "German", "French", "Spanish", "English"]
    if request.source_lang not in valid_languages:
        raise HTTPException(400, f"Invalid source language: {request.source_lang}")
    if request.target_lang not in valid_languages:
        raise HTTPException(400, f"Invalid target language: {request.target_lang}")
    if request.source_lang == request.target_lang:
        raise HTTPException(400, "Source and target languages must be different")

    # Set OpenAI API key as environment variable if provided
    if request.openai_api_key:
        os.environ["OPENAI_API_KEY"] = request.openai_api_key
        print("OpenAI API key updated")

    # Save to the correct location based on mode
    if sessions._production:
        # Production mode: save to settings.json in app data directory
        data_dir = sessions.factory.config.cache_dir
        settings_file = data_dir / "settings.json"

        # Load existing settings
        settings = {}
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            except Exception:
                pass

        # Update language settings
        settings["source_lang"] = request.source_lang
        settings["target_lang"] = request.target_lang

        # Write back
        data_dir.mkdir(parents=True, exist_ok=True)
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

        print(f"Settings saved to {settings_file}")
    else:
        # Development mode: save to config.ini
        config_path = Path(__file__).parent.parent.parent / "config.ini"

        parser = configparser.ConfigParser()
        if config_path.exists():
            parser.read(config_path)

        if "translation" not in parser:
            parser["translation"] = {}

        parser["translation"]["source_lang"] = request.source_lang
        parser["translation"]["target_lang"] = request.target_lang

        with open(config_path, "w") as f:
            parser.write(f)

        print(f"Config saved to {config_path}")

    # Reload the factory with new config
    sessions.reload_factory()

    return {
        "source_lang": request.source_lang,
        "target_lang": request.target_lang,
        "message": "Configuration updated successfully"
    }


@router.get("/settings")
async def get_settings():
    """Load app settings from disk"""
    import json
    config = sessions.factory.config
    settings_file = config.cache_dir / "app_settings.json"

    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")

    return {}


@router.post("/settings")
async def save_settings(request: Request):
    """Save app settings to disk"""
    import json
    config = sessions.factory.config
    settings_file = config.cache_dir / "app_settings.json"

    try:
        settings = await request.json()
        config.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return {"message": "Settings saved"}
    except Exception as e:
        print(f"Error saving settings: {e}")
        raise HTTPException(500, f"Error saving settings: {str(e)}")


@router.post("/cache/open")
async def open_cache_file():
    """Open the cache JSONL file in the default text editor"""
    try:
        config = sessions.factory.config
        if not config:
            raise HTTPException(500, "Configuration not loaded")

        cache_file = config.selections_file
        print(f"Opening cache file: {cache_file}")

        if not cache_file.exists():
            # Create empty file if it doesn't exist
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.touch()
            print(f"Created new cache file: {cache_file}")

        # Use 'open -t' on macOS to open in default text editor
        if sys.platform == "darwin":
            result = subprocess.run(["open", "-t", str(cache_file)], capture_output=True)
            if result.returncode != 0:
                print(f"open command failed: {result.stderr}")
        elif sys.platform == "win32":
            subprocess.run(["start", str(cache_file)], shell=True)
        else:
            # Linux - try xdg-open
            subprocess.run(["xdg-open", str(cache_file)])

        return {"path": str(cache_file), "message": "Opened in default editor"}
    except Exception as e:
        print(f"Error opening cache: {e}")
        raise HTTPException(500, f"Error opening cache: {str(e)}")


@router.get("/recent-files")
async def list_recent_files():
    """Get list of recently opened files"""
    config = sessions.factory.config
    recent = get_recent_files(config.cache_dir)
    return {
        "files": [
            {"path": r.path, "name": r.name, "last_opened": r.last_opened}
            for r in recent
        ]
    }


class AddRecentFileRequest(BaseModel):
    path: str


@router.post("/recent-files")
async def track_recent_file(request: AddRecentFileRequest):
    """Add a file to the recent files list"""
    config = sessions.factory.config
    recent = add_recent_file(config.cache_dir, request.path)
    return {
        "files": [
            {"path": r.path, "name": r.name, "last_opened": r.last_opened}
            for r in recent
        ]
    }


@router.get("/data-dir")
async def get_data_dir():
    """Get the app data directory path (for debugging/info)"""
    config = sessions.factory.config
    return {
        "path": str(config.cache_dir),
        "selections_file": str(config.selections_file)
    }


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe audio using OpenAI Whisper API"""
    import httpx

    _check_api_key()

    api_key = os.environ.get("OPENAI_API_KEY", "")

    # Read the uploaded file
    audio_data = await file.read()

    if len(audio_data) == 0:
        raise HTTPException(400, "Empty audio file")

    # Send to OpenAI Whisper API
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={
                    "Authorization": f"Bearer {api_key}"
                },
                files={
                    "file": (file.filename or "audio.webm", audio_data, file.content_type or "audio/webm")
                },
                data={
                    "model": "whisper-1"
                }
            )

            if response.status_code != 200:
                error_text = response.text
                print(f"Whisper API error: {response.status_code} - {error_text}")
                raise HTTPException(response.status_code, f"Whisper API error: {error_text}")

            result = response.json()
            return {"text": result.get("text", "")}

    except httpx.TimeoutException:
        raise HTTPException(504, "Transcription timed out")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        print(f"Transcription error: {e}")
        raise HTTPException(500, f"Transcription error: {str(e)}")
