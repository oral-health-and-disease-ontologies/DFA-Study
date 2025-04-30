#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert the columns specified in the LinkML schema to RDF."""

from linkml_runtime.utils.schemaview import SchemaView
from linkml.utils.datautils import _get_context
from typing import List, Text
import pandas as pd
import os
import click
from pyld import jsonld
import json


def get_columns_from_schema(schema:str) -> List:
    """returns a list of the slots in the schema

    Args:
        schema (str): path to the linkml schema file

    Returns:
        List: a list of the slots in the schema
    """
    view = SchemaView(schema) # load schema
    return list(view.all_slots(imports=False).keys())


def df_to_rdf(
        df: pd.DataFrame,
        schema: str, 
        
) -> Text:
    """transforms dataframe into rdf

    Args:
        df (pd.DataFrame): pandas dataframe holding the data to be transformed
        schema (str): path to linkml schema file

    Returns:
        str: nquads/ttl representation of data
    """
    context = _get_context(schema) # generate jsonld context
    
    # create records (list of dicts) from dataframe and filter out null values
    records = [
        {k:v for k,v in rows.items() if pd.notnull(v)}  # keep non-null values
        for rows in df.to_dict(orient="records")        # get rows
    ]

    # generate rdf
    rdf = jsonld.to_rdf(
            {"@context": json.loads(context), "@graph": records},
            {'format': 'application/n-quads'} # must use application/n-quad
    )        

    return rdf


def main(
        input:str, 
        schema:str, 
        output:str, 
) -> None:
    """transforms the input file into RDF

    Args:
        input (str): input data file; types: csv|tsv|xlxs
        schema (str): linkml schema file (.yml or .yaml)
        output (str): file to save the RDF data and OWL schema
    Raises:
        Exception: if the extension of input data file is not recogized
    """
    # get the columns from the slots in the schema
    # this ensures that the data will only come from the slot in the schema
    cols = get_columns_from_schema(schema)

    # file extension of input file
    file_ext = os.path.splitext(input)[-1]

    # load dataframe
    if file_ext == '.xlsx':
        df = pd.read_excel(input, usecols=cols)
    elif file_ext == '.tsv':
        df = pd.read_table(input, usecols=cols)
    elif file_ext == '.csv':
        df = pd.read_csv(input, usecols=cols)
    else:
        raise Exception("Input file extension not recognized.")
        
    # transform data to ttl/nquads
    rdf = df_to_rdf(df, schema)

    # save rdf
    if output is not None:
        with open(output, "w") as f:
            f.write(rdf)
    else:
        print(rdf)

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('-i', '--input', help="input data file; types: csv|tsv|xlxs", required=True)
@click.option('-s', '--schema', help="linkml schema file (.yml or .yaml)", required=True)
@click.option('-o', '--output', 
              help="output file for transformed RDF data and the OWL schema",
              default=None)
def cli(input, schema, output):
    """transforms the input file into RDF
    
    e.g.: python spreadsheet-to-rdf.py -i input.csv -s shema.yml -o data.ttl   
    """
    # call main program
    main(input, schema, output)


if __name__ == "__main__":
    cli()