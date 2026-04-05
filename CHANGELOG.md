# Changelog

All notable changes to ANT (AI Note Taker) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Phase 2: Real-Time Intelligence & Analytics
- Real-time suggestion engine with voice commands
- Hybrid ML + rule-based entity extraction (>90% accuracy)
- Conversation auto-categorization and quality analysis
- Graph analytics dashboard with 4 visualizations
- Interview performance insights (STAR method analysis)
- Personalized study plan generator with spaced repetition

## [1.0.0] - 2026-04-05

### Added - Phase 2 Features

#### Real-Time Suggestion Engine (#28)
- Contextual hints during live interviews
- Voice-activated commands ("What did I say about React?")
- Cooldown mechanism to prevent UI spam
- Confidence scoring for suggestion relevance

#### Hybrid Entity Extraction (#29)
- spaCy NER integration (en_core_web_sm)
- Combined rule-based + ML approach
- Confidence weighting system
- >90% extraction accuracy

#### Conversation Analysis (#30)
- Auto-tagging by type (practice, mock, real interview)
- Quality metrics (completeness, technical depth, clarity)
- Focus area detection
- Gap identification

#### Graph Analytics Dashboard (#31)
- Skill progression timeline with Chart.js
- Company comparison heatmap
- Topic network graph with D3.js
- Interview frequency calendar
- Performance trends (improving/declining/stable)

#### Interview Performance Insights (#32)
- STAR method pattern detection
- Code quality scoring
- Speaking pace analysis
- Filler word tracking
- Answer structure assessment

#### Study Plan Generator (#33)
- Spaced repetition scheduling (SM-2 algorithm)
- Weak area identification from cognitive graph
- Resource library (LeetCode, System Design Primer)
- Adaptive difficulty adjustment
- Export to JSON/iCal/Markdown

### Changed
- Enhanced main.py with 25+ new API endpoints
- Improved error handling across all modules
- Better logging for debugging

### Fixed
- Fixed undefined `query_graph()` in realtime_suggestions.py
- Fixed code quality scoring bug in performance_analyzer.py
- Fixed study plan JSON export double parsing
- Fixed iCal export formatting with proper escaping

## [0.9.0] - 2026-03-XX

### Added - Phase 1: Cognitive Graph
- Neo4j-powered personal knowledge graph
- Semantic search across interview history
- Entity extraction (companies, skills, topics)
- Company insights and question patterns
- Skill progression tracking
- Interview predictions for major tech companies
- Pre-interview preparation checklists

### Added - Core Features
- Local Whisper speech-to-text
- Real-time streaming transcription
- 10 AI modes (Instant, Auto, Fast, Turbo, etc.)
- Multi-provider AI routing (OpenAI, Anthropic, Google, etc.)
- Floating overlay UI with stealth mode
- Screen capture protection
- Always-on microphone mode
- Session management and history

## [0.1.0] - 2026-XX-XX

### Added - Initial Release
- Basic Electron app structure
- Voice recording and transcription
- Simple AI chat interface
- Local storage for conversations

---

## Release Schedule

| Version | Phase | Status |
|---------|-------|--------|
| 1.0.0 | Phase 2 Complete | 🚧 In Progress |
| 0.9.0 | Phase 1 Complete | ✅ Released |
| 0.1.0 | MVP | ✅ Released |

## Legend

- **Added** - New features
- **Changed** - Modifications to existing features
- **Deprecated** - Features marked for removal
- **Removed** - Deleted features
- **Fixed** - Bug fixes
- **Security** - Security-related changes
