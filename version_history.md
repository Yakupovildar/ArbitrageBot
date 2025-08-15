# MOEX Arbitrage Bot - Version History

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
- **Working (20)**: SBER/SBERF, GAZP/GAZPF, LKOH/LKZ5, GMKN/GKZ5, VTBR/VBZ5, ROSN/RNZ5, TATN/TNZ5, ALRS/ALZ5, FEES/FSZ5, HYDR/HYZ5, IRAO/IRZ5, MTSS/MTZ5, PHOR/PHZ5, SNGS/SNZ5, CHMF/CHZ5, MAGN/MAZ5, ABIO/ISZ5, AFKS/AKZ5, AFLT/AFZ5, BANE/BNZ5
- **Disabled (2)**: NLMK/NLZ5, NVTK/NVZ5 (futures tickers not found)

### Ready for Production
✅ Ready for deployment on hosting platforms for 24/7 operation