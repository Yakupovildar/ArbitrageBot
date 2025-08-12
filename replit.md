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

✅ **Major improvements based on user feedback:**
- **Controlled monitoring**: Users must explicitly start monitoring with /start_monitoring
- **No automatic API calls**: Bot only monitors when users request it, preventing unnecessary API usage
- **Market-aware prompts**: Interactive prompts when market is closed with yes/no options
- **Individual user control**: Each user has their own monitoring state, shared global monitoring only when needed
- **Demo functionality**: /demo command shows example signals without real data
- **Support system**: /support command and message forwarding to admin
- **Error notifications**: Admin receives alerts for API failures and critical errors
- **Scalable for 100+ users**: Efficient architecture that doesn't duplicate monitoring cycles

✅ **Latest optimizations (Aug 12, 8:41 PM):**
- **Fixed /start_monitoring issue**: Command now works properly without showing welcome message
- **Removed /positions command**: Bot only sends notifications/signals, no trading execution tracking
- **Updated trading hours**: Corrected MOEX schedule - stocks 8am, futures 9am, monitoring starts 9am
- **Eliminated Forex functionality**: Completely removed /forex command as requested
- **Cleaner signals**: Removed all broker/exchange links from signals for minimal, focused messages
- **Enhanced schedule display**: Shows separate hours for stocks, futures, and arbitrage monitoring
- **Admin source checking**: /check_sources command for admins to verify 6 data sources
- **Source restart**: Admins can restart problematic data sources with inline buttons

✅ **Core features implemented:**
- Automatic monitoring every 5-7 minutes (randomized) - ONLY when users opt-in
- Signal generation for spreads >1% only during trading hours
- Color-coded urgency levels (normal, green, bright green)
- Position tracking and close signals
- Subscription management
- All major Russian stocks and futures pairs
- Spread history storage (last 10 records)
- Market hours validation and notifications
- Individual user monitoring control
- Admin notification system

✅ **MOEX API compliance - All 7 rules implemented:**
- Rate limiting: max 60 requests/minute, 3 concurrent
- Proper authorization and error handling  
- Retry logic with exponential backoff
- Prevention of duplicate requests
- Request type limitations
- Failed request tracking
- Smart monitoring activation (only when users want it)

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