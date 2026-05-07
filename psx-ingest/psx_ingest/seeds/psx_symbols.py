# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk
#
# SEED DATA NOTE:
# This list is a starting point seeded from public knowledge of PSX-listed
# securities as of early 2026. It must be refreshed periodically from:
#   https://dps.psx.com.pk/symbols
# KMI compliance status reflects Meezan Bank KMI All-Share Index screening.
# Index membership (KSE-100 / KSE-30) is revised quarterly by PSX.
# Treat is_kse30 / is_kse100 flags as approximate until live DPS sync is active.

from typing import TypedDict


class SymbolSeed(TypedDict):
    symbol: str
    company_name: str
    sector: str
    is_kmi_compliant: bool
    is_kse100: bool
    is_kse30: bool


PSX_SYMBOLS: list[SymbolSeed] = [
    # ── Oil & Gas Exploration ─────────────────────────────────────────────────
    {"symbol": "OGDC", "company_name": "Oil & Gas Development Company Limited", "sector": "Oil & Gas Exploration Companies", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": True},
    {"symbol": "PPL",  "company_name": "Pakistan Petroleum Limited", "sector": "Oil & Gas Exploration Companies", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": True},
    {"symbol": "POL",  "company_name": "Pakistan Oilfields Limited", "sector": "Oil & Gas Exploration Companies", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "MARI", "company_name": "Mari Petroleum Company Limited", "sector": "Oil & Gas Exploration Companies", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},

    # ── Oil & Gas Marketing ───────────────────────────────────────────────────
    {"symbol": "PSO",    "company_name": "Pakistan State Oil Company Limited", "sector": "Oil & Gas Marketing Companies", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": True},
    {"symbol": "APL",    "company_name": "Attock Petroleum Limited", "sector": "Oil & Gas Marketing Companies", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": False},
    {"symbol": "HASCOL", "company_name": "Hascol Petroleum Limited", "sector": "Oil & Gas Marketing Companies", "is_kmi_compliant": False, "is_kse100": False, "is_kse30": False},

    # ── Refineries ────────────────────────────────────────────────────────────
    {"symbol": "NRL",  "company_name": "National Refinery Limited", "sector": "Refineries", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": False},
    {"symbol": "ATRL", "company_name": "Attock Refinery Limited", "sector": "Refineries", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": False},
    {"symbol": "PRL",  "company_name": "Pakistan Refinery Limited", "sector": "Refineries", "is_kmi_compliant": False, "is_kse100": False, "is_kse30": False},

    # ── Commercial Banks ──────────────────────────────────────────────────────
    # Note: conventional banks are NOT KMI-compliant (interest-based operations)
    # Exception: Meezan Bank (fully Islamic operations) is KMI-compliant
    {"symbol": "HBL",  "company_name": "Habib Bank Limited", "sector": "Commercial Banks", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": True},
    {"symbol": "UBL",  "company_name": "United Bank Limited", "sector": "Commercial Banks", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": True},
    {"symbol": "MCB",  "company_name": "MCB Bank Limited", "sector": "Commercial Banks", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": True},
    {"symbol": "ABL",  "company_name": "Allied Bank Limited", "sector": "Commercial Banks", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": False},
    {"symbol": "BAFL", "company_name": "Bank Alfalah Limited", "sector": "Commercial Banks", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": False},
    {"symbol": "NBP",  "company_name": "National Bank of Pakistan", "sector": "Commercial Banks", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": True},
    {"symbol": "BAHL", "company_name": "Bank Al-Habib Limited", "sector": "Commercial Banks", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": False},
    {"symbol": "MEBL", "company_name": "Meezan Bank Limited", "sector": "Commercial Banks", "is_kmi_compliant": True,  "is_kse100": True, "is_kse30": True},
    {"symbol": "AKBL", "company_name": "Askari Bank Limited", "sector": "Commercial Banks", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": False},
    {"symbol": "FABL", "company_name": "Faysal Bank Limited", "sector": "Commercial Banks", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": False},
    {"symbol": "JSBL", "company_name": "JS Bank Limited", "sector": "Commercial Banks", "is_kmi_compliant": False, "is_kse100": False, "is_kse30": False},
    {"symbol": "SNBL", "company_name": "Soneri Bank Limited", "sector": "Commercial Banks", "is_kmi_compliant": False, "is_kse100": False, "is_kse30": False},

    # ── Cement ────────────────────────────────────────────────────────────────
    {"symbol": "LUCK",  "company_name": "Lucky Cement Limited", "sector": "Cement", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": True},
    {"symbol": "DGKC",  "company_name": "D.G. Khan Cement Company Limited", "sector": "Cement", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "MLCF",  "company_name": "Maple Leaf Cement Factory Limited", "sector": "Cement", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "CHCC",  "company_name": "Cherat Cement Company Limited", "sector": "Cement", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "PIOC",  "company_name": "Pioneer Cement Limited", "sector": "Cement", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "KOHC",  "company_name": "Kohat Cement Company Limited", "sector": "Cement", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "FCCL",  "company_name": "Fauji Cement Company Limited", "sector": "Cement", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "ACPL",  "company_name": "Attock Cement Pakistan Limited", "sector": "Cement", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "BWCL",  "company_name": "Bestway Cement Limited", "sector": "Cement", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "THCCL", "company_name": "Thatta Cement Company Limited", "sector": "Cement", "is_kmi_compliant": True, "is_kse100": False, "is_kse30": False},

    # ── Fertilizer ────────────────────────────────────────────────────────────
    {"symbol": "ENGRO",  "company_name": "Engro Corporation Limited", "sector": "Fertilizer", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": True},
    {"symbol": "FFC",    "company_name": "Fauji Fertilizer Company Limited", "sector": "Fertilizer", "is_kmi_compliant": True,  "is_kse100": True, "is_kse30": True},
    {"symbol": "FATIMA", "company_name": "Fatima Fertilizer Company Limited", "sector": "Fertilizer", "is_kmi_compliant": True,  "is_kse100": True, "is_kse30": False},
    {"symbol": "EFERT",  "company_name": "Engro Fertilizers Limited", "sector": "Fertilizer", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": False},
    {"symbol": "DAWH",   "company_name": "Dawood Hercules Corporation Limited", "sector": "Fertilizer", "is_kmi_compliant": True,  "is_kse100": True, "is_kse30": False},

    # ── Power Generation & Distribution ───────────────────────────────────────
    {"symbol": "HUBC",  "company_name": "Hub Power Company Limited", "sector": "Power Generation & Distribution", "is_kmi_compliant": True,  "is_kse100": True, "is_kse30": True},
    {"symbol": "KAPCO", "company_name": "Kot Addu Power Company Limited", "sector": "Power Generation & Distribution", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": False},
    {"symbol": "KEL",   "company_name": "K-Electric Limited", "sector": "Power Generation & Distribution", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": True},
    {"symbol": "NCPL",  "company_name": "Nishat Chunian Power Limited", "sector": "Power Generation & Distribution", "is_kmi_compliant": True,  "is_kse100": True, "is_kse30": False},
    {"symbol": "PKGP",  "company_name": "PakGen Power Limited", "sector": "Power Generation & Distribution", "is_kmi_compliant": True,  "is_kse100": False, "is_kse30": False},
    {"symbol": "LUCA",  "company_name": "Lalpir Power Limited", "sector": "Power Generation & Distribution", "is_kmi_compliant": False, "is_kse100": False, "is_kse30": False},

    # ── Automobile Assembler ──────────────────────────────────────────────────
    {"symbol": "INDU", "company_name": "Indus Motor Company Limited", "sector": "Automobile Assembler", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "PSMC", "company_name": "Pak Suzuki Motor Company Limited", "sector": "Automobile Assembler", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "HCAR", "company_name": "Honda Atlas Cars (Pakistan) Limited", "sector": "Automobile Assembler", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "ATLH", "company_name": "Atlas Honda Limited", "sector": "Automobile Assembler", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "MTL",  "company_name": "Millat Tractors Limited", "sector": "Automobile Assembler", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},
    {"symbol": "AGTL", "company_name": "Al-Ghazi Tractors Limited", "sector": "Automobile Assembler", "is_kmi_compliant": True, "is_kse100": False, "is_kse30": False},
    {"symbol": "GADO", "company_name": "Ghandhara Industries Limited", "sector": "Automobile Assembler", "is_kmi_compliant": True, "is_kse100": False, "is_kse30": False},

    # ── Technology & Communication ────────────────────────────────────────────
    {"symbol": "TRG",    "company_name": "TRG Pakistan Limited", "sector": "Technology & Communication", "is_kmi_compliant": True,  "is_kse100": True,  "is_kse30": False},
    {"symbol": "SYS",    "company_name": "Systems Limited", "sector": "Technology & Communication", "is_kmi_compliant": True,  "is_kse100": True,  "is_kse30": False},
    {"symbol": "NETSOL", "company_name": "NetSol Technologies Limited", "sector": "Technology & Communication", "is_kmi_compliant": True,  "is_kse100": False, "is_kse30": False},
    {"symbol": "AVNCR",  "company_name": "Avanceon Limited", "sector": "Technology & Communication", "is_kmi_compliant": True,  "is_kse100": False, "is_kse30": False},
    {"symbol": "PTCL",   "company_name": "Pakistan Telecommunication Company Limited", "sector": "Technology & Communication", "is_kmi_compliant": False, "is_kse100": True,  "is_kse30": True},

    # ── Steel & Allied Products ───────────────────────────────────────────────
    {"symbol": "MUGHAL", "company_name": "Mughal Iron & Steel Industries Limited", "sector": "Steel & Allied Products", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "ISL",    "company_name": "International Steels Limited", "sector": "Steel & Allied Products", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "ASTL",   "company_name": "Aisha Steel Mills Limited", "sector": "Steel & Allied Products", "is_kmi_compliant": True, "is_kse100": False, "is_kse30": False},
    {"symbol": "AGHA",   "company_name": "Agha Steel Industries Limited", "sector": "Steel & Allied Products", "is_kmi_compliant": True, "is_kse100": False, "is_kse30": False},

    # ── Textile Composite ─────────────────────────────────────────────────────
    {"symbol": "NML",  "company_name": "Nishat Mills Limited", "sector": "Textile Composite", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "NCL",  "company_name": "Nishat Chunian Limited", "sector": "Textile Composite", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "GATM", "company_name": "Gul Ahmed Textile Mills Limited", "sector": "Textile Composite", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "KTML", "company_name": "Kohinoor Textile Mills Limited", "sector": "Textile Composite", "is_kmi_compliant": True, "is_kse100": False, "is_kse30": False},

    # ── Food & Personal Care Products ─────────────────────────────────────────
    {"symbol": "NESTLE", "company_name": "Nestle Pakistan Limited", "sector": "Food & Personal Care Products", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "COLG",   "company_name": "Colgate-Palmolive (Pakistan) Limited", "sector": "Food & Personal Care Products", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "UNITY",  "company_name": "Unity Foods Limited", "sector": "Food & Personal Care Products", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "QUICE",  "company_name": "Quice Food Industries Limited", "sector": "Food & Personal Care Products", "is_kmi_compliant": True, "is_kse100": False, "is_kse30": False},

    # ── Pharmaceuticals ───────────────────────────────────────────────────────
    {"symbol": "ABOT",   "company_name": "Abbott Laboratories (Pakistan) Limited", "sector": "Pharmaceuticals", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "GLAXO",  "company_name": "GlaxoSmithKline Pakistan Limited", "sector": "Pharmaceuticals", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "SEARL",  "company_name": "The Searle Company Limited", "sector": "Pharmaceuticals", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "HINOON", "company_name": "Highnoon Laboratories Limited", "sector": "Pharmaceuticals", "is_kmi_compliant": True, "is_kse100": False, "is_kse30": False},
    {"symbol": "FEROZ",  "company_name": "Ferozsons Laboratories Limited", "sector": "Pharmaceuticals", "is_kmi_compliant": True, "is_kse100": False, "is_kse30": False},

    # ── Chemicals ─────────────────────────────────────────────────────────────
    {"symbol": "LPCL", "company_name": "Lotte Chemical Pakistan Limited", "sector": "Chemicals", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "SITC", "company_name": "Sitara Chemical Industries Limited", "sector": "Chemicals", "is_kmi_compliant": True, "is_kse100": False, "is_kse30": False},

    # ── Cable & Electrical Goods ──────────────────────────────────────────────
    {"symbol": "PAEL",  "company_name": "Pak Elektron Limited", "sector": "Cable & Electrical Goods", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "WAVES", "company_name": "Waves Home Appliances Limited", "sector": "Cable & Electrical Goods", "is_kmi_compliant": True, "is_kse100": False, "is_kse30": False},

    # ── Engineering ───────────────────────────────────────────────────────────
    {"symbol": "SIEM", "company_name": "Siemens (Pakistan) Engineering Company Limited", "sector": "Engineering", "is_kmi_compliant": False, "is_kse100": True, "is_kse30": False},

    # ── Transport ─────────────────────────────────────────────────────────────
    {"symbol": "PNSC", "company_name": "Pakistan National Shipping Corporation", "sector": "Transport", "is_kmi_compliant": True, "is_kse100": True, "is_kse30": False},

    # ── Miscellaneous ─────────────────────────────────────────────────────────
    {"symbol": "THALL", "company_name": "Thal Limited", "sector": "Miscellaneous", "is_kmi_compliant": True, "is_kse100": True,  "is_kse30": False},
    {"symbol": "BATA",  "company_name": "Bata (Pakistan) Limited", "sector": "Leather & Tanneries", "is_kmi_compliant": True, "is_kse100": False, "is_kse30": False},

    # ── Insurance ─────────────────────────────────────────────────────────────
    {"symbol": "JSGCL", "company_name": "Jubilee General Insurance Company Limited", "sector": "Insurance", "is_kmi_compliant": False, "is_kse100": False, "is_kse30": False},
    {"symbol": "JGICL", "company_name": "Jubilee Life Insurance Company Limited", "sector": "Insurance", "is_kmi_compliant": False, "is_kse100": False, "is_kse30": False},
    {"symbol": "IGI",   "company_name": "IGI Holdings Limited", "sector": "Insurance", "is_kmi_compliant": False, "is_kse100": False, "is_kse30": False},

    # ── Paper & Board ─────────────────────────────────────────────────────────
    {"symbol": "CEPB", "company_name": "Century Paper & Board Mills Limited", "sector": "Paper & Board", "is_kmi_compliant": True, "is_kse100": False, "is_kse30": False},
]
