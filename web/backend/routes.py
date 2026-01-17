from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from web.backend.models import (
    ConversationRequest,
    HistoryResponse,
    LookupRequest,
)
from web.backend.session import SessionManager
from lookup.domain import SelectionData

router = APIRouter(prefix="/api")
sessions = SessionManager()


class ConfigUpdateRequest(BaseModel):
    source_lang: str
    target_lang: str


@router.post("/lookup")
async def lookup(request: LookupRequest, x_session_id: str = Header(...)):
    """Main translation endpoint - translates selection only (token-optimized)"""
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
    lookup_response = sessions.factory.lookup_service.lookup(selection_data)
    result = lookup_response.result
    from_cache = lookup_response.from_cache

    # Update session - store phrase and paragraph for later
    session = sessions.get_or_create(x_session_id)
    # Reset conversation for new translation (match CLI behavior)
    # Follow-up questions are meant for the current translation only
    session.reset_conversation()
    session.current_phrase = request.phrase
    session.current_paragraph = request.paragraph
    session.reset_context_flags()  # New selection, reset tracking
    session.add_translation(request.selection, result)

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

    lookup_response = sessions.factory.lookup_service.lookup(selection_data)
    result = lookup_response.result
    from_cache = lookup_response.from_cache

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

    lookup_response = sessions.factory.lookup_service.lookup(selection_data)
    result = lookup_response.result
    from_cache = lookup_response.from_cache

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
    session = sessions.get_or_create(x_session_id)
    answer = session.conversation_service.generate_response(request.question)
    session.add_conversation(request.question, answer or "")

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
    """Update language configuration"""
    import configparser
    from pathlib import Path

    # Validate languages
    valid_languages = ["Russian", "German", "French", "Spanish", "English"]
    if request.source_lang not in valid_languages:
        raise HTTPException(400, f"Invalid source language: {request.source_lang}")
    if request.target_lang not in valid_languages:
        raise HTTPException(400, f"Invalid target language: {request.target_lang}")
    if request.source_lang == request.target_lang:
        raise HTTPException(400, "Source and target languages must be different")

    # Find config file path
    config_path = Path(__file__).parent.parent.parent / "config.ini"

    # Read existing config
    parser = configparser.ConfigParser()
    if config_path.exists():
        parser.read(config_path)

    # Ensure translation section exists
    if "translation" not in parser:
        parser["translation"] = {}

    # Update languages
    parser["translation"]["source_lang"] = request.source_lang
    parser["translation"]["target_lang"] = request.target_lang

    # Write back
    with open(config_path, "w") as f:
        parser.write(f)

    # Reload the factory with new config
    sessions.reload_factory()

    return {
        "source_lang": request.source_lang,
        "target_lang": request.target_lang,
        "message": "Configuration updated successfully"
    }
