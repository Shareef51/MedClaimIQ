from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_release57_documented_ui_contract_exists():
    text=(ROOT/'docs/REGULATORY_CONTINUOUS_CONTROL_TESTING.md').read_text()
    for label in ['Continuous Control Testing Center','Evidence Sampling Queue','Independent Assurance Review','Retest Calendar']:
        assert label in text
