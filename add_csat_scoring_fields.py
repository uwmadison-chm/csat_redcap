#!/usr/bin/env python

import sys
import re
import csv
import pandas as pd
from collections import defaultdict


BLANK = re.compile(r'^$', re.MULTILINE)
NEW_FINDER = re.compile(r'\{(.*)\}')
NON_STR = re.compile("\W")

MENS_Q_PRE = [
    "csat_q16_natural_menstruation_quality",
    "csat_q17_occurrences_during_menstruation"
]

MENS_Q = {
    "Variable / Field Name": "csat_q_menstruate",
    "Form Name": "csat",
    "Field Type": "yesno",
    "Field Label": "Do you menstruate?",
    "Required Field?": "y"
}

MENS_BRANCH_LOGIC = '[csat_q_menstruate] = "1"'

CALC_ROW_PROTOTYPE = {
    'Form Name': 'csat',
    'Field Type': 'calc',
    'Required Field?': 'y'
}

# Denominator is 50 if you answer menstuation questions, 48 otherwise
DENOM = CALC_ROW_PROTOTYPE.copy()
DENOM['Variable / Field Name'] = "csat_denomimator"
DENOM['Field Label'] = "Denominator"
DENOM['Choices, Calculations, OR Slider Labels'] = 'if([csat_q_menstruate] = "1", 50, 48)'

def parse_question_block(block):
    # Blocks look like
    # lifestyle\t{lifestyle tendency}
    # organized = L
    # stable = T
    # unplanned = B
    lines = block.strip().split("\n")
    name_line = lines[0]
    names = name_line.split("\t")
    cur_name = names[0]
    new_part = names[1]
    new_name = NEW_FINDER.match(new_part).groups()[0]
    new_name = re.sub(r'\W+', '_', new_name)
    multi = False
    if len(names) > 2:
        if names[2] == "multi":
            multi = True
    value_lines = lines[1:]
    value_arr = [vline.split(" = ") for vline in value_lines]
    value_map = defaultdict(list)
    for choice, category in value_arr:
        cat_lower = category.lower()
        value_map[cat_lower].append(choice)

    # value_map = { v[0]: v[1] for v in value_arr }
    return {
        "cur_name": cur_name,
        "new_name": new_name,
        "value_map": value_map,
        "multi": multi
    }


def parse_score_file(score_file):
    file_data = ""
    with open(score_file, "r") as sf:
        file_data = sf.read()

    question_blocks = BLANK.split(file_data)
    question_blocks = [qb for qb in question_blocks if len(qb) > 0]

    parsed_blocks = [parse_question_block(qb) for qb in question_blocks]
    return parsed_blocks


def col_found(col, names):
    for name in names:
        if col.endswith(name):
            return True
    return False


def make_check_calc(row, category, values):
    orig_field = row['Variable / Field Name']
    # They'll look like
    # csat_q44_reactions_to_change(anxious)
    bracketed_fields = [
        f"[{orig_field}({val})]"
        for val in values
    ]
    calculation = f'mean({", ".join(bracketed_fields)})'
    cat_field = f"{orig_field}_{category}"
    new_field = CALC_ROW_PROTOTYPE.copy()
    new_field['Variable / Field Name'] = cat_field
    new_field['Field Label'] = cat_field
    new_field['Choices, Calculations, OR Slider Labels'] = calculation

    return new_field


def make_radio_calc(row, category, values):
    orig_field = row['Variable / Field Name']
    conditions = [
        f"[{orig_field}] = \"{val}\""
        for val in values
    ]
    all_conds = f"( {' or '.join(conditions)} )"
    calculation = f"if({all_conds}, 1, 0)"
    cat_field = f"{orig_field}_{category}"

    new_field = CALC_ROW_PROTOTYPE.copy()
    new_field['Variable / Field Name'] = cat_field
    new_field['Field Label'] = cat_field
    new_field['Choices, Calculations, OR Slider Labels'] = calculation

    return new_field


def question_calc_fields(row, score_entry):
    # Takes a row (a dictlike thing) and returns a dict containing:
    # {"L": {row definition}, "B": {row definition}, "T": {row def}}
    # The rows will be calculated rows that return a number to sum on that
    # letter's score if matching answers are selected
    fields = {}
    categories = sorted(
        [cat for cat in score_entry['value_map'].keys() if len(cat) == 1])
    for category in categories:
        values = score_entry['value_map'][category]
        if score_entry['multi']:
            fields[category] = make_check_calc(row, category, values)
        else:
            fields[category] = make_radio_calc(row, category, values)
    return fields


def make_upgraded_instrument(score_inst, instrument_df):
    output = []

    category_fields = defaultdict(list)

    # Put the regular rows
    for inst, (_rownum, row) in zip(score_inst, instrument_df.iterrows()):
        if row['Variable / Field Name'] == MENS_Q_PRE[0]:
            output.append(MENS_Q)
        if row['Variable / Field Name'] in MENS_Q_PRE:
            row['Branching Logic (Show field only if...)'] = MENS_BRANCH_LOGIC
        output.append(row)
        calc_fields = question_calc_fields(row, inst)
        for cat, field in calc_fields.items():
            output.append(field)
            category_fields[cat].append(field['Variable / Field Name'])

    # Sum up each subscale
    for cat, field_list in category_fields.items():
        fields_bracketed = [f"[{field}]" for field in field_list]
        calc = f'sum({", ".join(fields_bracketed)})'
        sum_field = CALC_ROW_PROTOTYPE.copy()
        sum_field['Variable / Field Name'] = f"csat_sum_{cat}"
        sum_field['Field Label'] = f"csat_sum_{cat}"
        sum_field['Choices, Calculations, OR Slider Labels'] = calc
        output.append(sum_field)

    output.append(DENOM)

    for cat in category_fields.keys():
        perc_field = CALC_ROW_PROTOTYPE.copy()
        perc_field['Variable / Field Name'] = f"csat_perc_{cat}"
        perc_field['Field Label'] = f"csat_sum_{cat}"
        calc = f'round(([csat_sum_{cat}] / [csat_denomimator]) * 100, 0)'
        perc_field['Choices, Calculations, OR Slider Labels'] = calc
        output.append(perc_field)

    output = [dict(row) for row in output]
    return output


def main(score_file, instrument_file):
    score_inst = parse_score_file(score_file)
    names = [inst['new_name'] for inst in score_inst]
    instrument_df = pd.read_csv(instrument_file)
    new_instrument = make_upgraded_instrument(score_inst, instrument_df)

    new_df = pd.DataFrame(new_instrument, columns=instrument_df.columns)
    new_df.to_csv(sys.stdout, index=False)


if __name__ == '__main__':
    score_file = "csat_scoring.txt"
    instrument_file = "inst_base.csv"
    main(score_file, instrument_file)
