# MOEX Arbitrage Bot

## Overview

The MOEX Arbitrage Bot is a Telegram-based system designed to identify and alert users about arbitrage opportunities between stocks and futures on the Moscow Exchange (MOEX). It provides real-time monitoring of price spreads, generates trading signals, and tracks positions for Russian financial instruments. The bot is fully operational and production-ready, featuring intelligent data source management, persistent database storage, and scalability for over 100 users with advanced configuration options. Its core purpose is to empower users with timely and actionable insights into profitable arbitrage opportunities within the Russian financial market.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Components

**Bot Framework**: Utilizes the `python-telegram-bot` library for asynchronous Telegram bot functionality, handling user interaction via commands and buttons.

**Market Data Integration**: Interfaces with the MOEX ISS API for real-time price feeds, incorporating rate limiting and error handling for data reliability.

**Arbitrage Engine**: Calculates spread opportunities between stock and futures pairs, generating trading signals based on configurable thresholds. Critical calculations now correctly handle MOEX API price conversions and lot sizes, ensuring accurate spread identification.

**Monitoring System**: Operates continuously in the background, tracking numerous instrument pairs and sending alerts to subscribed users. Monitoring intervals and signal limits are user-configurable.

**Position Management**: Tracks open arbitrage positions and identifies closing opportunities as spreads converge.

### Key Design Patterns

**Async/Await Architecture**: Employs `asyncio` for non-blocking I/O, enabling concurrent monitoring and user interactions.

**Configuration-Driven**: A centralized system manages API endpoints, monitoring intervals, spread thresholds, and instrument mappings, supporting environment variables.

**Signal Processing**: Implements a three-tier urgency system (normal, green, bright green) based on spread magnitude to prioritize high-value opportunities.

**Subscriber Model**: Manages user subscriptions for customized signal delivery and notifications.

**Persistent Settings**: Integrates with a PostgreSQL database to store and automatically restore all user configurations and monitoring states across bot restarts.

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