# MOEX Arbitrage Bot

## Overview

Successfully deployed Telegram bot for monitoring arbitrage opportunities between stocks and futures on the Moscow Exchange (MOEX). The system continuously tracks price spreads between related instruments and alerts users when profitable arbitrage opportunities arise. The bot provides real-time monitoring, signal generation, and position tracking capabilities for Russian financial instruments.

**Status: ✅ FULLY OPERATIONAL**
- Bot successfully running and monitoring markets
- All core functionality implemented
- User can now interact with the bot via Telegram

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes (August 12, 2025)

✅ **Complete bot implementation with custom HTTP API approach**
- Resolved python-telegram-bot library conflicts by implementing direct Telegram Bot API integration
- Created fully functional bot with all requested features
- Successfully deployed and tested with real TELEGRAM_BOT_TOKEN

✅ **Core features implemented:**
- Automatic monitoring every 5 minutes
- Signal generation for spreads >1% 
- Color-coded urgency levels (normal, green, bright green)
- Position tracking and close signals
- Subscription management
- All major Russian stocks and futures pairs

## System Architecture

### Core Components

**Bot Framework**: Built on python-telegram-bot library providing async Telegram bot functionality with command handlers for user interaction.

**Market Data Integration**: Uses MOEX ISS API for real-time price feeds with built-in rate limiting and error handling to ensure reliable data access.

**Arbitrage Engine**: Central calculation engine that identifies spread opportunities between stock/futures pairs and generates trading signals based on configurable thresholds.

**Monitoring System**: Continuous background monitoring with configurable intervals that tracks multiple instrument pairs simultaneously and sends alerts to subscribed users.

**Position Management**: Tracks open arbitrage positions and monitors for closing opportunities based on spread convergence.

### Key Design Patterns

**Async/Await Architecture**: All I/O operations use asyncio for non-blocking execution, allowing concurrent monitoring of multiple instruments and user interactions.

**Configuration-Driven**: Centralized configuration system managing API endpoints, monitoring intervals, spread thresholds, and instrument mappings with environment variable support.

**Signal Processing**: Three-tier urgency system (normal, green, bright green) based on spread magnitude to prioritize high-value opportunities.

**Subscriber Model**: User subscription system allowing selective notification delivery with admin controls for bot management.

### Data Flow

Market data flows from MOEX API through the arbitrage calculator which generates signals based on spread analysis. Signals are then distributed to subscribed users via Telegram with formatted messages including position details and urgency indicators.

## External Dependencies

**MOEX ISS API**: Primary data source for stock and futures prices with RESTful JSON interface requiring rate limiting compliance.

**Telegram Bot API**: Message delivery and user interaction platform accessed through python-telegram-bot wrapper library.

**aiohttp**: HTTP client for async API communications with configurable timeouts and session management.

**Environment Variables**: 
- `TELEGRAM_BOT_TOKEN`: Bot authentication token
- `ADMIN_USER_IDS`: Comma-separated list of admin user IDs for bot management

**Python Libraries**: Standard asyncio, logging, datetime, and dataclasses for core functionality without external database requirements.