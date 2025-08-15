# Version History - MOEX Arbitrage Bot

## Version 0.1.8 - STABLE BACKUP (2024-08-15)

**Status: ✅ PRODUCTION READY**

### Key Features:
- Production deployment on Reserved VM hosting
- Subscription system with 7-day trial period (NEW)
- Admin commands security protection
- 25+ active trading pairs with validated spreads
- Sector-based instrument selection
- Real-time signal delivery system

### Recent Changes:
- **SUBSCRIPTION OVERHAUL**: Changed from 50 signal limit to 7-day free trial
- **SECURITY**: Admin commands protected, only accessible via /admin
- **UI/UX**: Clean subscription interface, updated demo signals
- **HOSTING**: Successfully deployed to Reserved VM, resolved API conflicts

### Technical Architecture:
- Database: PostgreSQL with trial period tracking
- Bot Framework: Python-telegram-bot with HTTP API
- Data Sources: MOEX ISS API with rotation system
- Monitoring: Multi-interval scheduling system

### Files Structure:
- `telegram_bot.py` - Main bot logic and handlers
- `subscription_manager.py` - Trial period and subscription management
- `database.py` - PostgreSQL integration with user settings
- `arbitrage_calculator.py` - Spread calculation engine
- `moex_api.py` - Market data integration
- `config.py` - System configuration and settings

### Deployment:
- Platform: Replit Reserved VM
- Cost: ~$7-15/month (covered by user's Core credits)
- Status: 24/7 operation with automatic scaling
- URL: Production deployment active

### Rollback Instructions:
1. Copy files from `versions/v0.1.8_stable_backup/`
2. Redeploy to Reserved VM via Replit interface
3. Verify database schema includes trial fields
4. Test subscription flow and admin commands

This version represents a fully functional production-ready arbitrage bot with modern subscription management and secure admin controls.