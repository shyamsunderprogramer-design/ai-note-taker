"""
backfill_cognitive_graph.py - Backfill historical conversations into cognitive graph

This script reads all existing conversation JSON files and ingests them
into the Neo4j cognitive graph.

Usage:
    python backfill_cognitive_graph.py [conversations_directory]
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger("backfill")

# Import cognitive graph
try:
    from cognitive_graph import (
        cognitive_graph,
        initialize_graph,
        InterviewNode,
        ingest_conversation
    )
    from entity_extraction import entity_extractor
    COGNITIVE_GRAPH_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import cognitive graph: {e}")
    COGNITIVE_GRAPH_AVAILABLE = False
    sys.exit(1)


def get_default_conversations_dir():
    """Get the default conversations directory based on OS"""
    if sys.platform == "win32":
        # Windows: %APPDATA%/ai-note-taker/conversations
        app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
        return Path(app_data) / "ai-note-taker" / "conversations"
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/ai-note-taker/conversations
        return Path.home() / "Library/Application Support/ai-note-taker/conversations"
    else:
        # Linux: ~/.config/ai-note-taker/conversations
        return Path.home() / ".config/ai-note-taker/conversations"


def load_conversation_files(conversations_dir: Path) -> List[Dict]:
    """Load all conversation JSON files from directory"""
    conversations = []

    if not conversations_dir.exists():
        logger.error(f"Conversations directory not found: {conversations_dir}")
        return conversations

    json_files = list(conversations_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} conversation files")

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['_file'] = file_path.name
                conversations.append(data)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")

    return conversations


def process_conversation(conversation: Dict) -> bool:
    """Process and ingest a single conversation"""
    try:
        conversation_id = conversation.get('id')
        if not conversation_id:
            logger.warning("Conversation missing ID, skipping")
            return False

        # Prepare data for ingestion
        ingest_data = {
            'title': conversation.get('title', 'Untitled Interview'),
            'user_id': 'default',  # Historical conversations don't have user_id
            'updatedAt': conversation.get('updatedAt', datetime.now().timestamp() * 1000),
            'duration_ms': conversation.get('duration_ms', 0),
            'messages': conversation.get('messages', [])
        }

        # Ingest into cognitive graph
        success = ingest_conversation(conversation_id, ingest_data)

        if success:
            # Extract entities from full conversation text
            full_text = ' '.join([
                msg.get('content', msg.get('text', ''))
                for msg in conversation.get('messages', [])
            ])

            if len(full_text) > 50:
                entities = entity_extractor.extract_all(full_text)
                logger.info(f"Extracted {entities.get('entities_found', 0)} entities from {conversation_id}")

        return success

    except Exception as e:
        logger.error(f"Failed to process conversation: {e}")
        return False


def main():
    """Main entry point"""
    # Get conversations directory
    if len(sys.argv) > 1:
        conversations_dir = Path(sys.argv[1])
    else:
        conversations_dir = get_default_conversations_dir()

    logger.info(f"Looking for conversations in: {conversations_dir}")

    # Initialize cognitive graph
    logger.info("Initializing cognitive graph...")
    if not initialize_graph():
        logger.error("Failed to initialize cognitive graph. Is Neo4j running?")
        sys.exit(1)

    # Load conversations
    conversations = load_conversation_files(conversations_dir)

    if not conversations:
        logger.info("No conversations to backfill")
        sys.exit(0)

    # Process each conversation
    logger.info(f"Starting backfill of {len(conversations)} conversations...")
    success_count = 0
    fail_count = 0

    for i, conversation in enumerate(conversations, 1):
        file_name = conversation.get('_file', 'unknown')
        logger.info(f"[{i}/{len(conversations)}] Processing {file_name}...")

        if process_conversation(conversation):
            success_count += 1
        else:
            fail_count += 1

    logger.info(f"\nBackfill complete!")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Failed: {fail_count}")
    logger.info(f"  Total: {len(conversations)}")


if __name__ == "__main__":
    main()
