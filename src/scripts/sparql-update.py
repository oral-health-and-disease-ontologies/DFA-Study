#!/usr/bin/env python3
"""Apply a SPARQL Update file to an RDF file and print the result as Turtle.

Uses rdflib rather than ROBOT so the update runs on the raw triples, before
the OWL API reinterprets them (e.g., gen-owl enums typed as both owl:Class
and rdfs:Datatype).
"""

import click
from rdflib import Graph


@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("update_file", type=click.Path(exists=True))
@click.option("--input-format", default="turtle", show_default=True)
def main(input_file: str, update_file: str, input_format: str) -> None:
    g = Graph()
    g.parse(input_file, format=input_format)
    with open(update_file) as f:
        g.update(f.read())
    click.echo(g.serialize(format="turtle"))


if __name__ == "__main__":
    main()
