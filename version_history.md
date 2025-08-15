# MOEX Arbitrage Bot - Version History

## Version 0.0.2 (2025-08-15)

### Critical Fixes
- ✅ **Futures Multipliers Fixed**: Corrected price conversion coefficients for all Z5 contracts
- ✅ **Non-existent Tickers Removed**: Cleaned up 23 invalid pairs from configuration
- ✅ **Accurate Spreads**: Now calculates proper spreads with correct price ratios
- ✅ **Validation Scope**: Reduced from 56 to 33 working pairs for reliable operation

### Working Pairs (33)
- 8 Blue chips: SBER/SBERF, GAZP/GAZPF, LKOH/LKZ5, GMKN/GKZ5, VTBR/VBZ5, ROSN/RNZ5, TATN/TNZ5, ALRS/ALZ5
- 25 Z5 contracts: ABIO/ISZ5, AFKS/AKZ5, AFLT/AFZ5, AKRN/ANZ5, BANE/BNZ5, BSPB/BSZ5, CBOM/CMZ5, CHMF/CHZ5, ETLN/ETZ5, FEES/FSZ5, FLOT/FLZ5, HYDR/HYZ5, IRAO/IRZ5, KMAZ/KMZ5, MAGN/MAZ5, MGNT/MGZ5, MOEX/MEZ5, MTSS/MTZ5, NKNC/NKZ5, PHOR/PHZ5, RASP/RAZ5, RTKM/RTZ5, RUAL/RUZ5, SGZH/SZZ5, SNGS/SNZ5

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