"""
Validation tests for the PSX symbol seed data.
These run without a database — they test the seed list itself for correctness.
"""

import pytest

from psx_ingest.seeds.psx_symbols import PSX_SYMBOLS

REQUIRED_KEYS = {"symbol", "company_name", "sector", "is_kmi_compliant", "is_kse100", "is_kse30"}

# Conventional banks must not be KMI-compliant (Shariah screener)
CONVENTIONAL_BANK_SYMBOLS = {"UBL", "HBL", "ABL", "BOP", "BAFL", "MEBL"}

# KSE-30 must be a subset of KSE-100
# (every KSE-30 member is also a KSE-100 member by definition)

# Known large-caps that must appear
MUST_INCLUDE = {"ENGRO", "LUCK", "PPL", "OGDC", "MCB", "HBL", "TRG", "EFERT", "PSO", "SYS"}


class TestSeedDataStructure:
    def test_seed_list_is_not_empty(self) -> None:
        assert len(PSX_SYMBOLS) > 0

    def test_seed_list_has_sufficient_coverage(self) -> None:
        # The plan calls for ~100 symbols; enforce a reasonable minimum
        assert len(PSX_SYMBOLS) >= 50, f"Only {len(PSX_SYMBOLS)} symbols seeded — expected ≥50"

    def test_each_entry_has_required_keys(self) -> None:
        for entry in PSX_SYMBOLS:
            missing = REQUIRED_KEYS - set(entry.keys())
            assert not missing, f"Entry {entry.get('symbol', '?')} missing keys: {missing}"

    def test_symbols_are_uppercase_strings(self) -> None:
        for entry in PSX_SYMBOLS:
            sym = entry["symbol"]
            assert isinstance(sym, str), f"Symbol must be str, got {type(sym)}"
            assert sym == sym.upper(), f"Symbol '{sym}' is not uppercase"
            assert len(sym) <= 20, f"Symbol '{sym}' exceeds 20-char limit"
            assert len(sym) >= 1, f"Empty symbol found"

    def test_company_names_are_non_empty_strings(self) -> None:
        for entry in PSX_SYMBOLS:
            name = entry["company_name"]
            assert isinstance(name, str) and name.strip(), (
                f"company_name for {entry['symbol']} is empty"
            )

    def test_sectors_are_non_empty_strings(self) -> None:
        for entry in PSX_SYMBOLS:
            sector = entry["sector"]
            assert isinstance(sector, str) and sector.strip(), (
                f"sector for {entry['symbol']} is empty"
            )

    def test_boolean_flags_are_bools(self) -> None:
        for entry in PSX_SYMBOLS:
            for flag in ("is_kmi_compliant", "is_kse100", "is_kse30"):
                assert isinstance(entry[flag], bool), (
                    f"{flag} for {entry['symbol']} is not bool: {entry[flag]!r}"
                )

    def test_no_duplicate_symbols(self) -> None:
        symbols = [e["symbol"] for e in PSX_SYMBOLS]
        duplicates = [s for s in set(symbols) if symbols.count(s) > 1]
        assert not duplicates, f"Duplicate symbols found: {duplicates}"


class TestSeedDataLogic:
    def test_kse30_is_subset_of_kse100(self) -> None:
        for entry in PSX_SYMBOLS:
            if entry["is_kse30"]:
                assert entry["is_kse100"], (
                    f"{entry['symbol']} is KSE-30 but not KSE-100 — invalid"
                )

    def test_known_large_caps_are_present(self) -> None:
        symbols_in_seed = {e["symbol"] for e in PSX_SYMBOLS}
        missing = MUST_INCLUDE - symbols_in_seed
        assert not missing, f"Large-cap symbols missing from seed: {missing}"

    def test_multiple_sectors_represented(self) -> None:
        sectors = {e["sector"] for e in PSX_SYMBOLS}
        assert len(sectors) >= 5, f"Only {len(sectors)} distinct sectors — expected ≥5"

    def test_some_kmi_compliant_symbols_exist(self) -> None:
        kmi_count = sum(1 for e in PSX_SYMBOLS if e["is_kmi_compliant"])
        assert kmi_count >= 10, f"Only {kmi_count} KMI-compliant symbols — expected ≥10"

    def test_some_kse100_symbols_exist(self) -> None:
        kse100_count = sum(1 for e in PSX_SYMBOLS if e["is_kse100"])
        assert kse100_count >= 20, f"Only {kse100_count} KSE-100 symbols — expected ≥20"

    @pytest.mark.parametrize("symbol", sorted(CONVENTIONAL_BANK_SYMBOLS))
    def test_conventional_banks_are_not_kmi_compliant(self, symbol: str) -> None:
        entry = next((e for e in PSX_SYMBOLS if e["symbol"] == symbol), None)
        if entry is None:
            pytest.skip(f"{symbol} not in seed — skipping")
        assert entry["is_kmi_compliant"] is False, (
            f"Conventional bank {symbol} incorrectly marked KMI-compliant"
        )
