# MOEX Arbitrage Bot - Version History

## Version 0.0.3 (2025-08-15)

### Major Restoration
- ✅ **All Tickers Restored**: Re-added all 23 "missing" pairs - they exist on exchange
- ✅ **Complete Coverage**: Now monitoring all 56 pairs from user's original file
- ✅ **Validation Issue**: Problem was API search errors, not missing tickers
- ✅ **Full Functionality**: All pairs from user's exchange data now active

### All Trading Pairs (56)
- 8 Blue chips: SBER/SBERF, GAZP/GAZPF, LKOH/LKZ5, GMKN/GKZ5, VTBR/VBZ5, ROSN/RNZ5, TATN/TNZ5, ALRS/ALZ5
- 48 Z5 contracts: All pairs from user's file restored and active

## Version 0.0.2 (2025-08-15)

### Critical Fixes
- ✅ **Futures Multipliers Fixed**: Corrected price conversion coefficients for all Z5 contracts
- ✅ **Accurate Spreads**: Now calculates proper spreads with correct price ratios
- ❌ **Incorrect Removal**: Wrongly removed valid tickers (fixed in v0.0.3)

## Version 0.0.1 (2025-08-15)

### Initial Release
- ✅ Comprehensive subscription system (50 free signals + 10 USDT premium)
- ✅ Extended validation from 8 to 22 trading pairs
- ✅ Added all pairs from user's attached file (63+ instruments)
- ✅ Z5 futures contracts with proper kopeck-to-ruble conversion
- ✅ Sector-based navigation with "🎯 Рекомендованные" category
- ✅ Complete PostgreSQL integration for persistent settings
- ✅ Auto-reconnection and intelligent data source management
- ✅ Daily validation system for all trading pairs
- ✅ Telegram bot with comprehensive admin features

### Technical Features
- **Database**: PostgreSQL with subscription tracking
- **API Integration**: MOEX ISS API with rate limiting
- **Monitoring**: 22 validated trading pairs (20 working, 2 disabled)
- **Subscription Model**: Freemium with crypto payments
- **Data Sources**: 30+ backup sources with auto-failover
- **Validation**: Daily automated pair checking

### Trading Pairs Status
- **Total Configured**: 56 pairs from user's file
- **Daily Validation**: All 56 pairs checked automatically
- **Critical Fixes**: CBOM ticker corrected (CBZ5 → CMZ5), all is_market_open() calls fixed
- **Validation Scope**: Expanded from 22 to 56 pairs for comprehensive testing

### Ready for Production
✅ Ready for deployment on hosting platforms for 24/7 operation