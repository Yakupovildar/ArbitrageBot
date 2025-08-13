# MOEX Arbitrage Bot

## Overview

Successfully deployed Telegram bot for monitoring arbitrage opportunities between stocks and futures on the Moscow Exchange (MOEX). The system continuously tracks price spreads between related instruments and alerts users when profitable arbitrage opportunities arise. The bot provides real-time monitoring, signal generation, and position tracking capabilities for Russian financial instruments.

**Status: ✅ FULLY OPERATIONAL & PRODUCTION-READY**
- Bot successfully running and monitoring markets
- All core functionality implemented and optimized
- Scalable for 100+ users with API protection
- Modern button-based interface
- User can now interact with the bot via Telegram

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes (August 13, 2025)

✅ **DATABASE INTEGRATION & PERSISTENT SETTINGS (COMPLETE)**
- **PostgreSQL database**: Added full database integration with asyncpg
- **Persistent user settings**: All user configurations survive bot restarts
- **Automatic recovery**: Bot restores monitoring states and user settings on restart
- **Database schema**: Comprehensive tables for user settings, source status, and monitoring history

✅ **GRANULAR CONFIGURATION OPTIONS (COMPLETE)**
- **Enhanced spread thresholds**: Added 0.2%, 0.3%, 0.4% options for high-frequency trading
- **Signal batch control**: Users can choose 1-5 signals per batch with 3-second intervals
- **Individual settings**: Each user has personal thresholds and signal limits
- **Real-time updates**: Settings changes apply immediately and persist in database

✅ **AUTO-RECONNECTION SYSTEM (COMPLETE)**
- **30-minute cycles**: Automatic reconnection attempts every 30 minutes during trading hours
- **Source monitoring**: Tracks status of all 10 data sources in database
- **Smart recovery**: Prevents excessive reconnection attempts (15-min cooldown per source)
- **Status tracking**: /reconnect_stats command shows real-time source health

✅ **TIMEZONE & MARKET HOURS FIX (COMPLETE)**
- **Moscow timezone**: Fixed timezone calculation using pytz Europe/Moscow
- **Accurate trading hours**: Bot correctly detects MOEX hours (9:00-18:45 MSK weekdays)
- **Market awareness**: All monitoring respects actual trading schedule

✅ **Previous optimizations (Aug 12, 2025):**
- **Scaled to 10 data sources**: Added Tinkoff, Sberbank, BCS, VTB APIs for better redundancy
- **Smart signal limiting**: Maximum 5 signals per batch with 3-second intervals to prevent spam
- **Advanced monitoring scheduler**: Different user groups run on their own schedules (30s, 1min, 3min, 5min, 15min)
- **Source rotation system**: Fast intervals (<5min) automatically rotate through available sources to prevent API blocks
- **API blocking protection**: 5-7 minute pause after cycling through all sources prevents rate limiting
- **Fixed navigation**: All settings buttons work correctly with proper message editing
- **Quick access menu**: /menu command provides instant button-based interface
- **Button-based interface**: Start screen and main menu use interactive buttons instead of text commands
- **Personalized filtering**: Each user gets signals only above their personal spread threshold
- **Scalable architecture**: System now handles 100+ users with different settings without overload

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