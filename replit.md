# MOEX Arbitrage Bot

## Overview

**Version 0.1.1** - The MOEX Arbitrage Bot with CRITICALLY FIXED futures price conversion and complete signal blocking for problematic pairs. Only SBERF/GAZPF trade in rubles, ALL other futures converted from points (0.01 multiplier). System now prevents sending 900%+ spread signals to users through pre-filtering and automatic pair blocking. Features sector-based interface with 15 economic sectors and professional company classification.

## Recent Changes (v0.1.1)

- **CRITICAL FIX**: Corrected futures conversion - only SBERF/GAZPF in rubles, rest in points with 0.01 conversion
- **Signal Protection**: Complete blocking of signals for pairs with anomalous spreads >100%
- **Accurate Calculations**: LKZ5 64128 points → 641.28₽ producing normal -90% spread instead of 904%
- **Emergency Restart**: Immediately stopped incorrect signal delivery to users
- **User Safety**: Pre-filtering system prevents selection and monitoring of blocked pairs

## Versioning System

- **Current Version**: 0.0.1 (Ready for hosting deployment)
- **Version Storage**: All versions saved in `versions/` directory
- **Next Version**: 0.0.2 (will be created on next deployment)
- **Version History**: Tracked in `version_history.md`

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Components

**Bot Framework**: Utilizes the `python-telegram-bot` library for asynchronous Telegram bot functionality, handling user interaction via commands and buttons.

**Market Data Integration**: Interfaces with the MOEX ISS API for real-time price feeds, incorporating rate limiting and error handling for data reliability.

**Arbitrage Engine**: Calculates spread opportunities between stock and futures pairs, generating trading signals based on configurable thresholds. Critical calculations now correctly handle MOEX API price conversions and lot sizes, ensuring accurate spread identification. Fixed to use PREVPRICE field instead of LAST for reliable data retrieval. Futures price conversion coefficients calibrated for each instrument to ensure accurate spread calculations.

**Monitoring System**: Operates continuously in the background, tracking numerous instrument pairs and sending alerts to subscribed users. Monitoring intervals and signal limits are user-configurable.

**Position Management**: Tracks open arbitrage positions and identifies closing opportunities as spreads converge.

### Key Design Patterns

**Async/Await Architecture**: Employs `asyncio` for non-blocking I/O, enabling concurrent monitoring and user interactions.

**Configuration-Driven**: A centralized system manages API endpoints, monitoring intervals, spread thresholds, and instrument mappings, supporting environment variables.

**Signal Processing**: Implements a three-tier urgency system (normal, green, bright green) based on spread magnitude to prioritize high-value opportunities.

**Subscriber Model**: Manages user subscriptions for customized signal delivery and notifications.

**Persistent Settings**: Integrates with a PostgreSQL database to store and automatically restore all user configurations and monitoring states across bot restarts. Maximum signals per user increased from 5 to 10.

**Automatic Pair Validation**: Features a comprehensive daily validation system that checks all trading pairs every 24 hours, automatically detecting ticker changes, trading halts, and configuration errors, logging problematic pairs to console and notifying administrators.

**Auto-Reconnection and Source Management**: Features an intelligent system that automatically selects the best working data sources from a library of 30+, replaces failed sources, and tracks their reliability.

**Sector-based Instrument Navigation**: Allows users to select from over 100 verified trading pairs organized into 18 economic sectors, with intuitive navigation and mass operation capabilities.

### Data Flow

Market data from the MOEX API is processed by the arbitrage calculator to generate signals. These signals are then distributed to subscribed users via Telegram, presented with formatted messages including position details and urgency indicators. User settings and historical data are managed within a PostgreSQL database.

## External Dependencies

**MOEX ISS API**: The primary data source for real-time stock and futures prices, accessed via a RESTful JSON interface.

**Telegram Bot API**: Used for all message delivery and user interaction, accessed through the `python-telegram-bot` library.

**PostgreSQL**: Employed for persistent storage of user settings, monitoring states, and other critical data.

**aiohttp**: An HTTP client library used for asynchronous API communications.

**Environment Variables**:
- `TELEGRAM_BOT_TOKEN`: For bot authentication.
- `ADMIN_USER_IDS`: A comma-separated list of admin user IDs.

**Python Libraries**: `pytz` for timezone handling, along with standard libraries like `asyncio`, `logging`, `datetime`, and `dataclasses`.