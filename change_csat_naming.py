#!/usr/bin/env python

import sys
import pandas as pd
import add_csat_scoring_fields


def main(score_file, instrument_file):
    blocks = add_csat_scoring_fields.parse_score_file(score_file)

    inst = pd.read_csv(instrument_file)

    for i, block in enumerate(blocks):
        old_name = inst.loc[i, 'Variable / Field Name']
        qnum = f"{(i+1):02d}"
        new_name = f"csat_q{qnum}_{block['new_name']}"
        print(f"{old_name}\t{new_name}")

if __name__ == '__main__':
    # instrument_file = sys.argv[1]
    score_file = sys.argv[1]
    instrument_file = sys.argv[2]
    main(score_file, instrument_file)
