# csat_redcap
A script to generate an auto-scored Constitutional Self-Assessment Tool in REDCap

The script itself is `add_csat_scoring_fields.py`, which uses the files `inst_base.csv` and `csat_scoring.txt` to score the data.

Output is in the `output` folder; `output/csat.zip` is a finished instrument ready to upload into REDCap.

The `rebuild` script will build a new REDCap instrument zip file.

Written by [Nate Vack](mailto:njvack@wisc.edu). Yes, I know it is terrible.
