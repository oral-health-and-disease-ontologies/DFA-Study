#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert the columns specified in the LinkML schema to RDF."""

from linkml_runtime.utils.schemaview import SchemaView
from linkml.utils.datautils import _get_context
from typing import List, Text, Dict
import pandas as pd
import os
import click
import json
from rdflib import Graph
import multiprocessing as mp
from functools import partial


def get_columns_from_schema(schema:str) -> List:
    """returns a list of the slots in the schema

    Args:
        schema (str): path to the linkml schema file

    Returns:
        List: a list of the slots in the schema
    """
    view = SchemaView(schema) # load schema
    return list(view.all_slots(imports=False).keys())


def dataframe_row_dict_generator(df):
    """
    A generator that yields each row of a Pandas DataFrame as a dictionary.

    Args:
        df (pd.DataFrame): The input Pandas DataFrame.

    Yields:
        dict: A dictionary representing a row of the DataFrame, 
              where keys are column names and values are cell values.
    """
    for _, row in df.iterrows():
        rval =  {k:v for k,v in row.to_dict().items() if pd.notnull(v)} 
        yield rval


def process_rdf_chunk(record_chunk:List, context_dict:Dict) -> Graph:
        # add record chuck to context
        context_dict["@graph"] = record_chunk

        # parse record chunck and return graph
        g = Graph().parse(data=json.dumps(context_dict), format='json-ld')
        return g


def df_to_rdf_multi_process(
        df: pd.DataFrame,
        schema: str,
        chunksize
) -> Text:
    """Transforms dataframe into rdf using multiprocessing.

    Args:
        df (pd.DataFrame): pandas dataframe holding the data to be transformed
        schema (str): path to linkml schema file
        chunksize (int): size of each data chunk for multiprocessing; 

    Returns:
        str: nquads/ttl representation of data
    """
    context_dict = json.loads(_get_context(schema)) # generate jsonld context
    del context_dict["comments"] # comments section from context dict
    
    # use partial function to set the context and chunksize the same for all records
    partial_process_rdf_chunk = partial(
        process_rdf_chunk, 
        context_dict=context_dict
    )

    # create custome generator geting rows from dataframe
    record_iter = dataframe_row_dict_generator(df)
    
    # generate list of graphs using Pool
    with mp.Pool(mp.cpu_count()) as pool:
        results = pool.imap_unordered(partial_process_rdf_chunk, record_iter, chunksize=chunksize)

        # merge all graphs
        # note: this needs to be in the scope of the with statement
        merged_graph = Graph()
        for result in results:
            merged_graph += result
        
    
    # return rdf values
    return merged_graph.serialize(format='turtle')


def df_to_rdf(df: pd.DataFrame,
        schema: str, 
        
) -> Text:
    """Transforms dataframe into rdf.

    Args:
        df (pd.DataFrame): pandas dataframe holding the data to be transformed
        schema (str): path to linkml schema file

    Returns:
        str: nquads/ttl representation of data
    """
    context_dict = json.loads(_get_context(schema)) # generate jsonld context
    del context_dict["comments"] # comments section from context dict
    
    # create records (list of dicts) from dataframe and filter out null values
    records = [
        {k:v for k,v in rows.items() if pd.notnull(v)}  # keep non-null values
        for rows in df.to_dict(orient="records")        # get rows
    ]

    # add records to context (i.e., adds graph with data)
    context_dict["@graph"] = records

    # parse record chunck and return graph
    g = Graph().parse(data=json.dumps(context_dict), format='json-ld')

    # return rdf values
    return g.serialize(format='turtle')


def main(
        input: str, 
        schema: str, 
        multiprocessing: bool, 
        chunksize: int,
        output: str, 
) -> None:
    """Transforms the input file into RDF.

    Args:
        input (str): input data file; types: csv|tsv|xlxs
        schema (str): linkml schema file (.yml or .yaml)
        multiprocessing (bool): use multiprocessing when tranforming data 
        chunksize (int): size of each data chunk for multiprocessing 
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
    if multiprocessing:
        rdf = df_to_rdf_multi_process(df, schema, chunksize)
    else:
        rdf = df_to_rdf(df, schema)
    
    # save rdf to file
    if output is not None:
        with open(output, "w") as f:
            f.write(rdf)
    else:
        print(rdf)


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('-i', '--input', help="input data file; types: csv|tsv|xlxs", required=True)
@click.option('-s', '--schema', help="linkml schema file (.yml or .yaml)", required=True)
@click.option('-mp', '--multiprocessing', 
              help="""
                use multiprocessing when transforming data;
                this may be useful for large datasets
                [default: False]
              """, 
              required=False,
              default=False)
@click.option('--chunksize', 
              help="""
                when using multiprocessing, allows you to specify the size of the data in each process
                [default: 1,000]
              """, 
              required=False,
              default=1_000)
@click.option('-o', '--output', 
              help=""" \
                output file for transformed RDF data and the OWL schema;
                if not given, output is printed to terminal
              """,
              required=False,
              default=None)
def cli(input, schema, multiprocessing, chunksize, output):
    """transforms the input file into RDF
    
    Examples: 

    python spreadsheet-to-rdf.py -i input.csv -s shema.yml -o data.ttl  

    python spreadsheet-to-rdf.py -i input.csv -s shema.yml -o data.ttl -mp true  
    """
    # call main program
    main(input, schema, multiprocessing, chunksize, output)


if __name__ == "__main__":
    cli()