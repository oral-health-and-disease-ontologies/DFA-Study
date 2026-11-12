#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract field mappings from the jsonld file and write to a CSV file."""

import json
import click
from typing import List
from git_root import git_root

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    '-i', '--input', 
    help="input jsonld file", 
    default=git_root('jsonld/superdataset.jsonld'),
    show_default=True,
    required=False
)
@click.option('-o', '--output', 
    help="output csv file", 
    default=git_root('field-mappings/superdataset-field-mappings.csv'),
    show_default=True,
    required=False
)
def cli(input, output):
    with open(input) as f:
        schema_dict  = json.load(f)

    with open(output, 'w') as f:
        f.write('field,mappings\n') # write header
        
        slots:List = schema_dict['slots']
        for slot in slots:
            # for each slot get name and mappings
            name = slot.get('name', '')
            mappings = \
                '|'.join(slot.get('related_mappings', []))
            
            if len(name) > 0:
                f.write(f'{name},{mappings}\n')
            # print(f"name: {name}, mappings: {mappings}")
            

if __name__ == "__main__":
    cli()