#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert the columns specified in the LinkML schema to RDF."""

from linkml_runtime.utils.schemaview import SchemaView
from linkml.utils.datautils import _get_context
from typing import List, Text, Dict, Optional
from urllib.parse import quote
import pandas as pd
import os
import click
import json
from rdflib import Graph
import multiprocessing as mp
from functools import partial


def get_default_base_iri(schema: str) -> str:
    """returns the base IRI of the schema's default prefix (used to mint record IRIs)

    Args:
        schema (str): path to the linkml schema file

    Returns:
        str: base IRI, e.g. https://w3id.org/OHD/DFA-study/superdataset/
    """
    view = SchemaView(schema)
    prefix = view.schema.default_prefix
    if prefix in view.schema.prefixes:
        return view.schema.prefixes[prefix].prefix_reference
    return prefix  # default_prefix may already be an IRI


def make_record_iris(df: pd.DataFrame, id_columns: List[str], base_iri: str) -> pd.Series:
    """creates an IRI for each record from the values in the id columns

    The values are joined with "-" and appended to base_iri, e.g. with
    id_columns ["source", "Participant_id"]: <base_iri>bph-17.
    Characters that are not allowed in an IRI (e.g., spaces) are percent-encoded.

    Args:
        df (pd.DataFrame): the data; must contain the id columns
        id_columns (List[str]): columns whose values identify a record
        base_iri (str): namespace for the record IRIs

    Raises:
        ValueError: if an id column is missing, a record has no value in an id column,
            or two records get the same IRI (they would be merged into one record)

    Returns:
        pd.Series: the record IRIs (same index as df)
    """
    missing_cols = [c for c in id_columns if c not in df.columns]
    if missing_cols:
        raise ValueError(f"id columns not found in the input data: {missing_cols}")

    def as_text(v):
        # numbers read as floats (e.g., 17.0 in a column with blanks) -> "17"
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v).strip()

    id_values = df[id_columns]
    missing = id_values.isna() | (id_values.astype(str).apply(lambda col: col.str.strip()) == "")
    if missing.any().any():
        rows = list(df.index[missing.any(axis=1)][:10])
        raise ValueError(f"{missing.any(axis=1).sum()} records have no value in the id columns "
                         f"{id_columns} (first rows, 0-based: {rows})")

    local_ids = id_values.apply(lambda row: "-".join(quote(as_text(v), safe="-._~") for v in row), axis=1)
    duplicated = local_ids[local_ids.duplicated(keep=False)]
    if not duplicated.empty:
        examples = duplicated.value_counts().head(10).to_dict()
        raise ValueError(f"{len(duplicated)} records share an IRI built from {id_columns}; "
                         f"use columns that identify each record uniquely (examples: {examples})")
    return base_iri + local_ids


def get_columns_from_schema(schema:str) -> List:
    """returns a list of the slots in the schema

    Args:
        schema (str): path to the linkml schema file

    Returns:
        List: a list of the slots in the schema
    """
    view = SchemaView(schema) # load schema
    return list(view.all_slots(imports=False).keys())


def get_string_columns_from_schema(schema:str) -> List:
    """returns a list of the slots in the schema whose range is string

    These columns are read as text so that values like IDs are not
    converted to numbers by pandas (e.g., an ID of 123 should be "123").

    Args:
        schema (str): path to the linkml schema file

    Returns:
        List: a list of the slots in the schema with range string
    """
    view = SchemaView(schema) # load schema
    default_range = view.schema.default_range or "string"
    return [
        name for name, slot in view.all_slots(imports=False).items()
        if (slot.range or default_range) == "string"
    ]


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


# output serializations: --format value -> rdflib serializer name
OUTPUT_FORMATS = {
    "ttl": "turtle", "turtle": "turtle",
    "rdfxml": "xml", "xml": "xml",
    "nt": "nt", "ntriples": "nt",
    "n3": "n3",
    "jsonld": "json-ld", "json-ld": "json-ld",
}


def df_to_rdf_multi_process(
        df: pd.DataFrame,
        schema: str,
        chunksize,
        rdf_format: str = "turtle",
) -> Text:
    """Transforms dataframe into rdf using multiprocessing.

    Args:
        df (pd.DataFrame): pandas dataframe holding the data to be transformed
        schema (str): path to linkml schema file
        chunksize (int): size of each data chunk for multiprocessing;
        rdf_format (str): rdflib serialization format (e.g., turtle, xml, nt, n3, json-ld)

    Returns:
        str: the data serialized in rdf_format
    """
    context_dict = json.loads(_get_context(schema)) # generate jsonld context
    context_dict.pop("comments", None) # remove comments section from context dict (if present)
    
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
    return merged_graph.serialize(format=rdf_format)


def df_to_rdf(df: pd.DataFrame,
        schema: str,
        rdf_format: str = "turtle",
) -> Text:
    """Transforms dataframe into rdf.

    Args:
        df (pd.DataFrame): pandas dataframe holding the data to be transformed
        schema (str): path to linkml schema file
        rdf_format (str): rdflib serialization format (e.g., turtle, xml, nt, n3, json-ld)

    Returns:
        str: the data serialized in rdf_format
    """
    context_dict = json.loads(_get_context(schema)) # generate jsonld context
    context_dict.pop("comments", None) # remove comments section from context dict (if present)
    
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
    return g.serialize(format=rdf_format)


def main(
        input: str, 
        schema: str, 
        multiprocessing: bool, 
        chunksize: int,
        output: str,
        id_columns: Optional[List[str]] = None,
        id_base: Optional[str] = None,
        rdf_format: str = "ttl",
) -> None:
    """Transforms the input file into RDF.

    Args:
        input (str): input data file; types: csv|tsv|xlxs
        schema (str): linkml schema file (.yml or .yaml)
        multiprocessing (bool): use multiprocessing when tranforming data
        chunksize (int): size of each data chunk for multiprocessing
        output (str): file to save the RDF data and OWL schema
        id_columns (List[str]): columns whose values (joined with "-") give each record
            an IRI; if not given, records are blank nodes
        id_base (str): namespace for the record IRIs; default: the schema's default prefix
        rdf_format (str): output serialization, one of OUTPUT_FORMATS
            (ttl, rdfxml, nt, n3, jsonld, or an alias); default: ttl (Turtle)
    Raises:
        Exception: if the extension of input data file is not recogized
        ValueError: if rdf_format is not recognized
    """
    if rdf_format.lower() not in OUTPUT_FORMATS:
        raise ValueError(f"unknown output format {rdf_format!r}; use one of {sorted(OUTPUT_FORMATS)}")
    serializer = OUTPUT_FORMATS[rdf_format.lower()]
    # get the columns from the slots in the schema
    # this ensures that the data will only come from the slot in the schema
    # (slots without a matching column, e.g. container slots like 'records', are ignored)
    slot_cols = set(get_columns_from_schema(schema))
    id_columns = id_columns or []
    cols = slot_cols | set(id_columns)  # id columns are also read, even if they are not slots
    usecols = lambda c: c in cols

    # read string slots as text (e.g., keeps IDs from being converted to numbers)
    dtype = {c: str for c in get_string_columns_from_schema(schema)}

    # file extension of input file
    file_ext = os.path.splitext(input)[-1]

    # load dataframe
    if file_ext == '.xlsx':
        df = pd.read_excel(input, usecols=usecols, dtype=dtype)
    elif file_ext == '.tsv':
        df = pd.read_table(input, usecols=usecols, dtype=dtype)
    elif file_ext == '.csv':
        df = pd.read_csv(input, usecols=usecols, dtype=dtype)
    else:
        raise Exception("Input file extension not recognized.")

    # give each record an IRI from the id columns (JSON-LD "@id"); otherwise records are blank nodes
    if id_columns:
        record_iris = make_record_iris(df, id_columns, id_base or get_default_base_iri(schema))
        df = df.drop(columns=[c for c in id_columns if c not in slot_cols])  # not part of the RDF
        df.insert(0, "@id", record_iris)

    # transform data to ttl/nquads
    if multiprocessing:
        rdf = df_to_rdf_multi_process(df, schema, chunksize, rdf_format=serializer)
    else:
        rdf = df_to_rdf(df, schema, rdf_format=serializer)
    
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
@click.option('--id-columns',
              help="""
                comma-separated column(s) whose values give each record an IRI;
                values are joined with "-" (e.g., --id-columns source,Participant_id
                gives <base>bph-17); the combination must be unique for each record;
                if not given, records are blank nodes
              """,
              required=False,
              default=None)
@click.option('--id-base',
              help="""
                namespace for the record IRIs
                [default: the schema's default prefix]
              """,
              required=False,
              default=None)
@click.option('-f', '--format', 'rdf_format',
              type=click.Choice(list(OUTPUT_FORMATS), case_sensitive=False),
              help="""
                output serialization: ttl (Turtle), rdfxml (RDF/XML), nt (N-Triples),
                n3, or jsonld (JSON-LD); aliases: turtle, xml, ntriples, json-ld
              """,
              required=False,
              default="ttl",
              show_default=True)
def cli(input, schema, multiprocessing, chunksize, output, id_columns, id_base, rdf_format):
    """transforms the input file into RDF

    Examples:

    python spreadsheet-to-rdf.py -i input.csv -s shema.yml -o data.ttl

    python spreadsheet-to-rdf.py -i input.csv -s shema.yml -o data.ttl -mp true

    python spreadsheet-to-rdf.py -i input.csv -s shema.yml -o data.ttl --id-columns source,Participant_id

    python spreadsheet-to-rdf.py -i input.csv -s shema.yml -o data.owl -f rdfxml
    """
    id_cols = [c.strip() for c in id_columns.split(",") if c.strip()] if id_columns else None
    # call main program
    main(input, schema, multiprocessing, chunksize, output, id_columns=id_cols, id_base=id_base,
         rdf_format=rdf_format)


if __name__ == "__main__":
    cli()