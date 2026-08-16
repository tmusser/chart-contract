import json

import pandas as pd

from chart_contract.cli import main


def test_cli_blocks_unrequested_scale_override(tmp_path, capsys) -> None:
    spec_path = tmp_path / "cut_scale.vl.json"
    data_path = tmp_path / "data.csv"

    spec_path.write_text(
        json.dumps(
            {
                "mark": "line",
                "title": "Observed conversion trend",
                "encoding": {
                    "x": {"field": "week", "type": "ordinal"},
                    "y": {
                        "field": "conversion_rate",
                        "type": "quantitative",
                        "scale": {"domain": [0.40, 0.44]},
                    },
                },
                "usermeta": {
                    "source": "synthetic.conversion",
                    "unit": "conversion rate",
                },
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "week": ["W1", "W2", "W3"],
            "conversion_rate": [0.41, 0.42, 0.43],
        }
    ).to_csv(data_path, index=False)

    exit_code = main(
        [
            "audit",
            "spec",
            str(spec_path),
            "--data",
            str(data_path),
            "--claim",
            "Observed conversion increased across the three weeks.",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Verdict: BLOCK" in output
    assert "scale.override.authorization" in output
