# Changelog

All notable changes to BuddAI will be documented in this file.

## [4.5.0] - 2026-01-10

### Added

- Enhanced Learning: Deterministic output capabilities.
- Context-Aware Rule Filtering.
- Integration Merge Tool.
- Fine-Tuning on corrections support.

## [4.0.0] - 2026-01-10

### Added

- 17 production-ready tools (calculator, file search, code analyzer, doc generator, test generator, project scaffolder, weather, base64, color converter, hash generator, JSON formatter, regex tester, system info, timer, test runner, and more)
- Memory decay system with three components:
  - Pattern Scorer: Exponential decay-based relevance scoring
  - Pattern Pruner: Safe deletion with automatic backups
  - Pattern Merger: Similarity detection using Jaccard and Levenshtein algorithms
- AI fallback system with multi-provider support (GPT-4, Claude, Gemini)
- Confidence-based escalation mechanism
- Automatic learning from corrections
- 10 modular validators for code quality and safety
- Auto-discovery registry patterns for tools and validators
- Comprehensive error handling and logging

### Changed

- Refactored to modular architecture with clean separation of concerns
- Improved test coverage from 129 to 265 tests
- Enhanced memory management with decay algorithms
- Upgraded database efficiency with pattern merging
- Better code organization with registry patterns

### Improved

- Test runtime optimized to 51.289 seconds
- Accuracy validated at 90% on ESP32 (14-hour test)
- More extensible design for easy feature additions
- Professional-grade code quality
- Comprehensive documentation

### Technical

- 265 comprehensive tests (100% passing)
- Modular architecture
- Exponential decay algorithms
- Levenshtein distance matching
- Jaccard similarity calculations
- Auto-discovery patterns
- Registry-based extensibility

## [3.1.0] - [Previous Date]

[Previous changelog entries...]

---

For detailed release information, see Releases.
