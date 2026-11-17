"""
superdataset_analysis_utils.py
------------------------------
Helper functions for analysing the DFA superdataset as RDF / OWL, used by the notebooks
superdataset-to-rdf.ipynb, superdataset-term-enrichment.ipynb and superdataset-semsql.ipynb.

Usage (from the notebooks directory):

    from lib.superdataset_analysis_utils import sparql_df, run_enrichment, plot_enrichment

Contents
  files and timing      head, timed
  queries               sparql_df (rdflib graph or SPARQL endpoint), sql_df (SQLite)
  semantic-sql          detect_rdf_format, build_semsql_db
  term enrichment       record_curie, run_enrichment, plot_enrichment, ENRICHMENT_STYLE
  visualization         plot_sparql_graph (draw a SPARQL CONSTRUCT result)
  display               show_image

Dependencies used by only some functions (oaklib, scipy, SPARQLWrapper, pyoxigraph,
semsql, matplotlib, IPython, PIL) are imported inside those functions, so the module can
be imported without all of them installed.
"""

import json
import re
import shutil
import sqlite3
import subprocess
import tempfile
import textwrap
import time
from decimal import Decimal
from itertools import islice
from pathlib import Path

import pandas as pd
from rdflib import OWL, RDF, BNode, Graph, Literal, URIRef

__all__ = [
    "head", "timed",
    "sparql_df", "sql_df",
    "detect_rdf_format", "build_semsql_db",
    "record_curie", "run_enrichment", "plot_enrichment", "ENRICHMENT_STYLE",
    "plot_sparql_graph",
    "show_image",
]

SUPERDATASET_BASE = "https://w3id.org/OHD/DFA-study/superdataset/"   # IRI base of the records


def _check_choice(name, value, choices):
    """Raise ValueError if `value` is not one of `choices`."""
    if value not in choices:
        options = ", ".join(repr(c) for c in choices[:-1]) + f" or {choices[-1]!r}"
        raise ValueError(f"{name} must be {options}, not {value!r}")


# ------------------------------------------------------------------------------
# files and timing
# ------------------------------------------------------------------------------

def head(path, start=1, stop=None):
    """Return lines start..stop of a file (1-based, inclusive) as a string.

    Defaults: start at the first line; stop 5 lines later.
    """
    if start < 1:
        raise ValueError("start must be >= 1")
    if stop is None:
        stop = start + 4
    if stop < start:
        raise ValueError("stop must be >= start")
    with open(path) as f:
        return "".join(islice(f, start - 1, stop))


def timed(label, func, *args, **kwargs):
    """Call func(*args, **kwargs), print how long it took, and return its result."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    print(f"{label}: {time.perf_counter() - start:.3f} s")
    return result


# ------------------------------------------------------------------------------
# queries
# ------------------------------------------------------------------------------

def sparql_df(query, source="http://127.0.0.1:8000/", to_python=True):
    """Run a SPARQL SELECT query and return the results as a pandas DataFrame.

    Args:
        query: SPARQL SELECT query.
        source: an rdflib Graph, or the URL of a SPARQL endpoint.
        to_python: convert literals to Python values (e.g., xsd:integer -> int);
            if False, every value is returned as a string.
    """
    def convert(term):
        if term is None:
            return None
        if to_python and isinstance(term, Literal):
            value = term.toPython()
            return float(value) if isinstance(value, Decimal) else value
        return str(term)

    if isinstance(source, Graph):
        res = source.query(query)
        cols = [str(v) for v in res.vars]
        rows = [[convert(term) for term in row] for row in res]
    else:
        from SPARQLWrapper import JSON, SPARQLWrapper

        sw = SPARQLWrapper(source)
        sw.setQuery(query)
        sw.setReturnFormat(JSON)
        res = sw.query().convert()
        cols = res["head"]["vars"]
        rows = [[convert(_binding_to_term(b.get(c))) for c in cols]
                for b in res["results"]["bindings"]]

    df = pd.DataFrame(rows, columns=cols)
    # use nullable types so integer columns with missing values stay integers
    return df.convert_dtypes() if to_python else df


def _binding_to_term(binding):
    """Convert a value from a SPARQL JSON result to an rdflib term."""
    if binding is None:
        return None
    if binding["type"] == "uri":
        return URIRef(binding["value"])
    if binding["type"] == "bnode":
        return BNode(binding["value"])
    return Literal(binding["value"], lang=binding.get("xml:lang"),
                   datatype=binding.get("datatype"))


def sql_df(query, con, params=None):
    """Run a SQL query and return the results as a pandas DataFrame."""
    return pd.read_sql(query, con, params=params)


# ------------------------------------------------------------------------------
# semantic-sql (SQLite) databases
# ------------------------------------------------------------------------------

def _keywords(*words):
    return "|".join(words)


# patterns used by detect_rdf_format, matched at the start of the first content line
# (except _XML_ROOT, _OBO_STANZA and _NTRIPLES_LINE)
_XML_START = re.compile(r"<[\w:]+[\s>]")
_XML_ROOT = re.compile(r"<(?!\?|!)([\w.-]+:)?([\w.-]+)[\s>/]")       # first element
_FUNCTIONAL_START = re.compile(rf"({_keywords('Prefix', 'Ontology', 'Import', 'Declaration')})\(")
_MANCHESTER_START = re.compile(rf"""({_keywords(
    'Prefix', 'Ontology', 'Import', 'Class', 'ObjectProperty', 'DataProperty',
    'AnnotationProperty', 'Individual', 'Datatype')}):""")
_OBO_HEADER = re.compile(rf"""({_keywords(
    'format-version', 'data-version', 'ontology', 'default-namespace', 'date', 'saved-by',
    'auto-generated-by', 'subsetdef', 'synonymtypedef', 'import', 'idspace', 'remark')}):""")
_OBO_STANZA = re.compile(r"^\[(Term|Typedef|Instance)\]", re.M)
_TURTLE_DIRECTIVE = re.compile(r"(@prefix|@base)\b")
_SPARQL_DIRECTIVE = re.compile(r"(PREFIX|BASE)\s", re.I)
_NTRIPLES_LINE = re.compile(
    r'^(<[^>]*>|_:\S+)\s+<[^>]*>\s+(<[^>]*>|_:\S+|".*"(\^\^<[^>]*>|@[\w-]+)?)\s*\.$')
_TURTLE_TRIPLE_START = re.compile(r"(<[^>]*>|_:\S+|[\w-]*:\S*)\s")


def detect_rdf_format(path, sample_size=65536):
    """Detect the serialization of an RDF/OWL file from its content (not its extension).

    Returns one of:
      "rdfxml"     RDF/XML (e.g., ROBOT/Protégé .owl files)
      "turtle"     Turtle (also covers N3-style files)
      "ntriples"   N-Triples
      "jsonld"     JSON-LD
      "functional" OWL Functional Syntax (sometimes saved as .owl or .ofn)
      "manchester" OWL Manchester Syntax (.omn)
      "owlxml"     OWL/XML (.owx, sometimes .owl)
      "obo"        OBO format (.obo)
    Raises ValueError if the format is not recognized.
    """
    with open(path, "rb") as f:
        text = f.read(sample_size).decode("utf-8", errors="replace").lstrip("\ufeff")  # BOM
    stripped = text.lstrip()
    # lines that are not blank or comments ("#" for Turtle/N-Triples, "!" for OBO)
    content = [line.strip() for line in text.splitlines()
               if line.strip() and not line.lstrip().startswith(("#", "!"))]
    first = content[0] if content else ""

    if stripped.startswith(("<?xml", "<!DOCTYPE")) or _XML_START.match(stripped):
        # RDF/XML has an rdf:RDF root element; OWL/XML has an Ontology root element
        root = _XML_ROOT.search(stripped)
        root_name = root.group(2) if root else None
        if root_name == "RDF":
            return "rdfxml"
        if root_name == "Ontology":
            return "owlxml"
        raise ValueError(f"{path}: XML file, but neither RDF/XML nor OWL/XML")
    if first.startswith(("{", "[")):
        return "jsonld"
    if _FUNCTIONAL_START.match(first):
        return "functional"
    if _MANCHESTER_START.match(first):
        return "manchester"
    if _OBO_HEADER.match(first) or _OBO_STANZA.search(text):
        return "obo"
    if _TURTLE_DIRECTIVE.match(first) or _SPARQL_DIRECTIVE.match(first):
        return "turtle"
    if content and all(_NTRIPLES_LINE.match(line) for line in content[:50]):
        return "ntriples"
    if _TURTLE_TRIPLE_START.match(first):
        return "turtle"      # Turtle without prefix declarations at the top
    raise ValueError(f"{path}: unrecognized RDF/OWL serialization")


# formats build_semsql_db converts to RDF/XML with pyoxigraph and with ROBOT
_PYOXIGRAPH_FORMATS = {"turtle": "TURTLE", "ntriples": "N_TRIPLES", "jsonld": "JSON_LD"}
_ROBOT_FORMATS = {"functional", "manchester", "owlxml", "obo"}


def build_semsql_db(data_path, db_path, extra_prefixes=None, method="rdftab",
                    input_format=None, rebuild=False):
    """Build a semantic-sql (SQLite) database from an RDF or OWL file.

    The serialization is detected from the file's content (see detect_rdf_format), so
    the extension does not matter; set `input_format` to skip detection. rdftab and
    semsql read RDF/XML, so:
      RDF/XML                               is used as is (no conversion);
      Turtle, N-Triples, JSON-LD            are converted with pyoxigraph (fast);
      OWL Functional, Manchester, OWL/XML, OBO   are converted with ROBOT.
    The RDF/XML is then loaded in one of two ways:
      "rdftab" (default): create the semsql tables and views, load the triples into
          `statements` with rdftab, and add the statements indexes. No reasoning, so
          `entailed_edge` is empty; `edge` (asserted relationships) still works.
      "semsql": the full `semsql make` build, which also runs ROBOT and relation-graph
          to fill `entailed_edge` (all inferred ancestors).
    Both use semsql's standard prefixes plus any in `extra_prefixes` ({prefix: base IRI}).

    Args:
        data_path: RDF/OWL file to load (any of the formats above).
        db_path: SQLite database to create (its folder is used for working files).
        extra_prefixes: additional prefixes, e.g. {"superdataset": "https://w3id.org/..."}.
        method: "rdftab" or "semsql".
        input_format: serialization of data_path (a detect_rdf_format value); detected if None.
        rebuild: rebuild the database even if it already exists.
    """
    import semsql

    _check_choice("method", method, ("rdftab", "semsql"))
    data_path, db_path = Path(data_path), Path(db_path)
    if db_path.exists() and not rebuild:
        return db_path
    fmt = input_format or detect_rdf_format(data_path)
    if fmt not in _PYOXIGRAPH_FORMATS and fmt not in _ROBOT_FORMATS and fmt != "rdfxml":
        raise ValueError(f"unsupported input_format {fmt!r}")
    print(f"{data_path.name}: {fmt}")

    work = db_path.parent
    work.mkdir(parents=True, exist_ok=True)
    builder = Path(semsql.__file__).parent / "builder"

    # semsql make X.db expects the RDF/XML in X.owl next to it
    owl_path = work / (db_path.stem + ".owl")
    rdfxml_path, created = _as_rdfxml(data_path, fmt, owl_path,
                                      copy_rdfxml=(method == "semsql"))
    prefixes_csv = work / "prefixes.csv"
    prefix_lines = _write_prefixes(builder, prefixes_csv, extra_prefixes)

    try:
        db_path.unlink(missing_ok=True)
        if method == "semsql":
            _semsql_make(work, prefixes_csv, db_path)
        else:
            _load_with_rdftab(builder, rdfxml_path, db_path, prefix_lines)
    finally:
        for f in created:                            # never deletes the input file
            f.unlink(missing_ok=True)
    return db_path


def _as_rdfxml(data_path, fmt, owl_path, copy_rdfxml):
    """Return the path of an RDF/XML version of data_path (converted or copied to
    owl_path if needed) and the list of files created, to delete when done."""
    if fmt == "rdfxml":
        if not copy_rdfxml or data_path.resolve() == owl_path.resolve():
            return data_path, []                     # use the input file directly
        shutil.copy(data_path, owl_path)
        return owl_path, [owl_path]

    if data_path.resolve() == owl_path.resolve():
        raise ValueError(f"{data_path} is {fmt}; it would be overwritten by the RDF/XML conversion")
    if fmt in _PYOXIGRAPH_FORMATS:
        import pyoxigraph

        in_format = getattr(pyoxigraph.RdfFormat, _PYOXIGRAPH_FORMATS[fmt])
        with open(data_path, "rb") as src, open(owl_path, "wb") as rdfxml:
            pyoxigraph.serialize(pyoxigraph.parse(src, format=in_format),
                                 rdfxml, format=pyoxigraph.RdfFormat.RDF_XML)
    else:
        subprocess.run(["robot", "convert", "-i", str(data_path), "--format", "owl",
                        "-o", str(owl_path)],
                       check=True, capture_output=True, text=True)
    return owl_path, [owl_path]


def _write_prefixes(builder, prefixes_csv, extra_prefixes):
    """Write semsql's standard prefixes plus extra_prefixes to prefixes_csv; return
    its lines (the first line is the header)."""
    lines = (builder / "prefixes" / "prefixes.csv").read_text().rstrip("\n").split("\n")
    lines += [f"{prefix},{base}" for prefix, base in (extra_prefixes or {}).items()]
    prefixes_csv.write_text("\n".join(lines) + "\n")
    return lines


def _semsql_make(work, prefixes_csv, db_path):
    """Build db_path with `semsql make` (runs in `work`, next to the .owl file)."""
    build = subprocess.run(["semsql", "make", "-P", prefixes_csv.name, db_path.name],
                           cwd=work, capture_output=True, text=True)
    if build.returncode != 0:
        raise RuntimeError(f"semsql failed:\n{build.stderr[-3000:]}")


def _load_with_rdftab(builder, rdfxml_path, db_path, prefix_lines):
    """Create the semsql tables and views, load the triples with rdftab, and add the
    statements indexes. The database is built in a temporary file and renamed at the end."""
    tmp = db_path.with_suffix(".db.tmp")
    tmp.unlink(missing_ok=True)
    with sqlite3.connect(tmp) as db:
        db.executescript((builder / "sql_schema" / "semsql.sql").read_text())
        rows = [line.split(",", 1) for line in prefix_lines[1:] if "," in line]  # skip header
        db.executemany("INSERT INTO prefix (prefix, base) VALUES (?, ?)", rows)
    with open(rdfxml_path, "rb") as rdfxml:
        load = subprocess.run(["rdftab", str(tmp)], stdin=rdfxml, capture_output=True, text=True)
    if load.returncode != 0:
        raise RuntimeError(f"rdftab failed:\n{load.stderr[-3000:]}")
    with sqlite3.connect(tmp) as db:
        db.executescript("""
            CREATE INDEX statements_spo ON statements(subject, predicate, object);
            CREATE INDEX statements_spv ON statements(subject, predicate, value);
            CREATE INDEX statements_p ON statements(predicate);
        """)
    tmp.rename(db_path)


# ------------------------------------------------------------------------------
# term enrichment
# ------------------------------------------------------------------------------

def record_curie(iris):
    """Convert record IRIs (e.g., https://w3id.org/OHD/DFA-study/superdataset/1234)
    to CURIEs (superdataset:1234), the form used for record IDs with OAK.

    Records get their IRIs from their Participant_id when the RDF is created
    (spreadsheet-to-rdf.py --id-columns Participant_id).
    """
    return iris.str.replace(SUPERDATASET_BASE, "superdataset:", regex=False)


_ENRICHMENT_COLUMNS = [
    "rank", "class_id", "class_label", "direction", "sample_count", "sample_total",
    "background_count", "background_total", "p_value", "p_value_adjusted",
    "ancestor_of_more_informative_result", "descendant_of_more_informative_result",
    "sample_pct", "background_pct"]


def run_enrichment(adapter, sample, background, direction="greater", cutoff=0.05,
                   filter_redundant=False):
    """Test OHD classes for over- and/or under-representation in a sample of records.

    Follows OAK's class enrichment (`adapter.enriched_classes`): the same association
    counts (records count under their classes and all ancestors), the background
    always includes the sample, Bonferroni-adjusted p-values, the same ordering and
    the same redundancy flags. OAK only tests over-representation (its `direction`
    argument is ignored in oaklib 0.7.4), so the test itself is done here with
    Fisher's exact test, which is the same as the hypergeometric test OAK uses.

    Args:
        adapter: OAK sqlite adapter for the OHD database with the associations.
        sample: list of record IDs to test (the test set).
        background: list of record IDs to compare against.
        direction: "greater" (over-representation, the same as OAK), "less"
            (under-representation) or "two-sided" (either).
        cutoff: maximum adjusted p-value to report.
        filter_redundant: drop classes that are ancestors/descendants of a more
            significant result (otherwise they are flagged); for two-sided tests,
            over- and under-represented classes are compared separately.

    Classes tested:
        "greater": classes with at least 2 sample records (as in OAK).
        "less" and "two-sided": every class with at least 1 background record,
           so classes with no sample records can be found to be under-represented.
    """
    from oaklib.datamodels.vocabulary import IS_A
    from scipy.stats import fisher_exact

    _check_choice("direction", direction, ("greater", "less", "two-sided"))

    sample = list(dict.fromkeys(sample))                 # drop duplicates, keep order
    if not sample:
        raise ValueError("the sample is empty: no records to test")
    background = set(background) | set(sample)          # background includes the sample
    n_sample, n_bg = len(sample), len(background)

    sample_counts = dict(adapter.association_subject_counts(
        sample, object_closure_predicates=[IS_A]))
    if not any(sample_counts.values()):
        raise ValueError("No associations found for the sample records. Check that the sample "
                         "IDs are record CURIEs (superdataset:<Participant_id>) and that the "
                         "association and database cells were run on the current data.")
    bg_counts = dict(adapter.association_subject_counts(
        background, object_closure_predicates=[IS_A]))

    if direction == "greater":
        hypotheses = [c for c, k in sample_counts.items() if k > 1]
    else:
        hypotheses = list(bg_counts)

    rows = []
    for cls in hypotheses:
        k, bg = sample_counts.get(cls, 0), bg_counts[cls]
        # 2x2 table: sample vs rest of background, with vs without the class
        table = [[k, n_sample - k], [bg - k, (n_bg - n_sample) - (bg - k)]]
        p = fisher_exact(table, alternative=direction)[1]
        rows.append({"class_id": cls, "sample_count": k, "sample_total": n_sample,
                     "background_count": bg, "background_total": n_bg, "p_value": p,
                     "direction": "over" if k / n_sample > bg / n_bg else "under"})
    df = pd.DataFrame(rows, columns=_ENRICHMENT_COLUMNS)
    df["p_value_adjusted"] = (df["p_value"] * len(hypotheses)).clip(upper=1.0)
    df = df[df["p_value_adjusted"] <= cutoff]

    # order as OAK does: by p-value, then more specific classes (more ancestors) first
    ancestors = {c: set(adapter.ancestors([c], predicates=[IS_A])) for c in df["class_id"]}
    df = df.assign(_n_anc=df["class_id"].map(lambda c: len(ancestors[c])))
    df = df.sort_values(["p_value", "_n_anc"], ascending=[True, False]).drop(columns="_n_anc")
    df = df.reset_index(drop=True)

    # redundancy flags, as in OAK; for two-sided tests, over- and under-represented
    # classes are compared separately
    groups = df["direction"] if direction == "two-sided" else ["all"] * len(df)
    (df["ancestor_of_more_informative_result"],
     df["descendant_of_more_informative_result"]) = _redundancy_flags(
        df["class_id"], groups, ancestors)
    df["rank"] = range(1, len(df) + 1)

    if filter_redundant:
        redundant = (df["ancestor_of_more_informative_result"].fillna(False).astype(bool)
                     | df["descendant_of_more_informative_result"].fillna(False).astype(bool))
        df = df[~redundant].reset_index(drop=True)

    df["class_label"] = [adapter.label(c) for c in df["class_id"]]
    df["sample_pct"] = (100 * df["sample_count"] / df["sample_total"]).round(1)
    df["background_pct"] = (100 * df["background_count"] / df["background_total"]).round(1)
    return df[_ENRICHMENT_COLUMNS]


def _redundancy_flags(class_ids, groups, ancestors):
    """OAK's redundancy flags for results sorted from most to least significant.

    A class is flagged as an ancestor (or descendant) of a more informative result if a
    more significant class in the same group is its descendant (or ancestor).
    Returns two lists of True / None: ancestor flags and descendant flags.
    """
    earlier, earlier_ancestors = {}, {}      # per group: classes seen so far, their ancestors
    anc_flags, desc_flags = [], []
    for cls, group in zip(class_ids, groups):
        seen = earlier.setdefault(group, set())
        seen_ancestors = earlier_ancestors.setdefault(group, set())
        desc_flags.append(bool(seen & (ancestors[cls] - {cls})) or None)
        anc_flags.append((cls in seen_ancestors) or None)
        seen.add(cls)
        seen_ancestors.update(ancestors[cls])
    return anc_flags, desc_flags


# ------------------------------------------------------------------------------
# drawing graphs with OAK's viz (og2dot)
# ------------------------------------------------------------------------------

def _kgviz_meta(attrs):
    """OboGraph metadata that sets Graphviz attributes on a node or edge: og2dot passes
    https://w3id.org/kgviz/<attribute> values to Graphviz, over its own defaults.
    Attributes whose value is None are left out."""
    from oaklib.datamodels import obograph

    return obograph.Meta(basicPropertyValues=[
        obograph.BasicPropertyValue(pred=f"https://w3id.org/kgviz/{k}", val=str(v))
        for k, v in attrs.items() if v is not None])


def _display_png(path):
    """Display a PNG file in the notebook."""
    from IPython.display import Image, display

    display(Image(filename=str(path)))


def _combine_images(main_png, side_png, out_png, position, gap=20):
    """Place side_png (e.g., a legend) to the right/left/top/bottom of main_png, centred,
    on a white background, and save the result as out_png."""
    from PIL import Image as PILImage

    main, side = PILImage.open(main_png).convert("RGB"), PILImage.open(side_png).convert("RGB")
    if position in ("right", "left"):
        width, height = main.width + gap + side.width, max(main.height, side.height)
        main_xy = (0 if position == "right" else side.width + gap, (height - main.height) // 2)
        side_xy = (main.width + gap if position == "right" else 0, (height - side.height) // 2)
    else:
        width, height = max(main.width, side.width), main.height + gap + side.height
        main_xy = ((width - main.width) // 2, 0 if position == "bottom" else side.height + gap)
        side_xy = ((width - side.width) // 2, main.height + gap if position == "bottom" else 0)
    canvas = PILImage.new("RGB", (width, height), "white")
    canvas.paste(main, main_xy)
    canvas.paste(side, side_xy)
    canvas.save(out_png)


# ------------------------------------------------------------------------------
# term enrichment figure
# ------------------------------------------------------------------------------

# Colors for plot_enrichment. Orange = over-represented, blue = under-represented
# (a diverging pair that stays distinguishable with all common types of colour blindness).
# Significance (adjusted p) is shown by 4 shades, light -> dark, on the box border
# ("border-width", "border-rings", "border-tint", "border") or the box fill ("fill"),
# plus border width ("border-width") or number of outlines ("border-rings"); the ramps were
# checked for monotone lightness, a single hue and readable label text.
#   borders, tint:  border shades and box colour in the "border" styles
#   fills, border:  fill shades and border colour in the "fill" style
#   fill_text:      label colour on each fill shade
ENRICHMENT_STYLE = {
    "p_levels": [0.05, 1e-3, 1e-6, 1e-12],     # adj. p at or below -> shade 0, 1, 2, 3
    "over": {                                  # orange
        "symbol": "\u25b2",
        "borders": ["#ff9067", "#da5821", "#9e3703", "#611f01"], "tint": "#fed3c4",
        "fills": ["#fea98b", "#fb7744", "#da5821", "#b43f01"], "border": "#9e3703",
        "fill_text": ["#0b0b0b", "#ffffff", "#ffffff", "#ffffff"],
    },
    "under": {                                 # blue
        "symbol": "\u25bc",
        "borders": ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"], "tint": "#cce0f9",
        "fills": ["#9ec5f4", "#6da7ec", "#3987e5", "#256abf"], "border": "#1c5cab",
        "fill_text": ["#0b0b0b", "#0b0b0b", "#ffffff", "#ffffff"],
    },
    "border_text": "#0b0b0b",                  # label colour in the "border" styles
    "penwidth": {"fill": "2", "border": "4", "rings": "2"},
    "border_widths": ["1.5", "3", "5", "7"],   # "border-width": width for each shade
    "context": {"fillcolor": "#ffffff", "color": "#898781", "fontcolor": "#52514e",
                "penwidth": "1"},
}

_SIGNIFICANCE_STYLES = ("border-width", "border-rings", "border-tint", "border", "fill")
_DIRECTION_NAMES = {"over": "over-represented", "under": "under-represented"}

# og2dot settings: no "is a" labels; invisible edges that stack the legend boxes
_ENRICHMENT_CONFIGURE = json.dumps({"relationProperties": {
    "rdfs:subClassOf": {"label": ""},
    "legend:next": {"style": "invis", "arrowhead": "none", "label": ""}}})


def plot_enrichment(adapter, enrichment, imgfile, top_class="OHD:0008011", width=30,
                    show=True, legend=True, legend_orientation="vertical",
                    legend_position=None,
                    significance_style="border-width",
                    style=None, short_labels=False):
    """Draw the enriched OHD classes and their ancestors with OAK's viz (og2dot).

    Significant classes are orange (over-represented) or blue (under-represented), with
    darker shades for smaller adjusted p-values (see ENRICHMENT_STYLE), and are labelled
    with a direction symbol (▲ over, ▼ under), the percentage of sample vs background
    records, and the adjusted p-value. Classes in the results that are not significant
    (adjusted p above the first p level, e.g. from run_enrichment(..., cutoff=1.0)) are
    white with their statistics and "(n.s.)"; ancestor classes that are not in the results
    are white. Ancestors above `top_class` (default: 'question') are left out.

    Args:
        adapter: OAK sqlite adapter for the OHD database.
        enrichment: DataFrame returned by run_enrichment.
        imgfile: path of the PNG file to write.
        top_class: highest ancestor to show.
        width: maximum number of characters per label line.
        show: display the image in the notebook; if False, only save the PNG
            (display it later with show_image).
        legend: add a legend (shades and directions) to the figure.
        legend_orientation: "vertical" (legend boxes in a column, default) or
            "horizontal" (legend boxes in a row).
        legend_position: where the legend goes: "right", "left", "top" or "bottom";
            default: "right" for a vertical legend, "bottom" for a horizontal one.
            The graph and the legend are drawn separately and combined, so any
            position works with either orientation.
        significance_style: how significance is shown (boxes are light orange / light
            blue except in "border" and "fill"):
            "border-width": shaded border that also gets thicker (default);
            "border-rings": shaded border with 1-4 outlines (countable; works in black
                and white);
            "border-tint": shaded border of constant width;
            "border": white box with a shaded border;
            "fill": shaded box fill.
        style: colours, shades and widths to use (same structure as ENRICHMENT_STYLE);
            default: ENRICHMENT_STYLE.
        short_labels: label the classes with the text before the first "." only, e.g.
            "DFS 17" for "DFS 17. Hearing the drill." and "IDAF-4C+ 1a" for
            "IDAF-4C+ 1a. I feel anxious ..."; labels without a "." (e.g., "question
            about tooth drilling") are kept as they are.
    """
    from oaklib.datamodels.vocabulary import IS_A
    from oaklib.utilities.obograph_utils import graph_to_image

    _check_choice("legend_orientation", legend_orientation, ("horizontal", "vertical"))
    if legend_position is None:
        legend_position = "right" if legend_orientation == "vertical" else "bottom"
    _check_choice("legend_position", legend_position, ("right", "left", "top", "bottom"))
    _check_choice("significance_style", significance_style, _SIGNIFICANCE_STYLES)
    cfg = style or ENRICHMENT_STYLE

    graph = adapter.ancestor_graph(enrichment["class_id"].tolist(), predicates=[IS_A])
    # drop the upper-level ancestors (BFO, IAO, ...) and the predicate node OAK adds
    keep = set(adapter.descendants(top_class, predicates=[IS_A]))
    graph.nodes = [n for n in graph.nodes if n.id in keep]
    graph.edges = [e for e in graph.edges if e.sub in keep and e.obj in keep]

    # label and colour the nodes
    stats = enrichment.set_index("class_id")
    directions_used = set()
    any_not_significant = False      # any results above the significance cutoff?
    for node in graph.nodes:
        name = node.lbl or node.id
        if short_labels:
            name = _short_label(name)
        label = _wrap_label(name, width)
        node.meta = _kgviz_meta(cfg["context"])
        if node.id in stats.index:
            r = stats.loc[node.id]
            direction = r.get("direction") or (
                "over" if r.sample_pct >= r.background_pct else "under")
            significant = r.p_value_adjusted <= cfg["p_levels"][0]
            symbol = cfg[direction]["symbol"]
            percentages = f"{symbol} {r.sample_pct:.1f}% vs {r.background_pct:.1f}%"
            p_value = f"adj. p = {r.p_value_adjusted:.1e}" + ("" if significant else " (n.s.)")
            label += "\n" + _no_break(percentages) + "\n" + _no_break(p_value)
            if significant:
                directions_used.add(direction)
                shade = _shade(cfg, r.p_value_adjusted)
                node.meta = _kgviz_meta(_significance_attrs(cfg, significance_style,
                                                            direction, shade))
            else:
                any_not_significant = True
        node.lbl = label

    if not legend:
        graph_to_image(graph, configure=_ENRICHMENT_CONFIGURE, imgfile=str(imgfile))
    else:
        legend_graph = _enrichment_legend(cfg, significance_style, directions_used,
                                          any_not_significant, legend_orientation)
        # draw the graph and the legend separately, then place the legend next to the graph
        with tempfile.TemporaryDirectory() as tmp:
            graph_png, legend_png = Path(tmp) / "graph.png", Path(tmp) / "legend.png"
            graph_to_image(graph, configure=_ENRICHMENT_CONFIGURE, imgfile=str(graph_png))
            graph_to_image(legend_graph, configure=_ENRICHMENT_CONFIGURE, imgfile=str(legend_png))
            _combine_images(graph_png, legend_png, imgfile, legend_position)
    if show:
        _display_png(imgfile)


def _short_label(label):
    """The text of a label before the first "." (e.g., "DFS 17" for "DFS 17. Hearing the
    drill."); labels without a "." are returned unchanged."""
    return label.split(".", 1)[0].strip() or label


def _no_break(text):
    """Replace the spaces with non-breaking spaces: og2dot puts every word of a label on
    its own line, so labels keep their line breaks only with these."""
    return text.replace(" ", "\u00a0")


def _wrap_label(text, width):
    """Wrap a label at `width` characters (see _no_break)."""
    return "\n".join(_no_break(line) for line in textwrap.wrap(text, width))


def _shade(cfg, p):
    """Index of the shade for an adjusted p-value (the last p level it is at or below)."""
    return max(i for i, cut in enumerate(cfg["p_levels"]) if p <= cut)


def _significance_attrs(cfg, significance_style, direction, shade):
    """Graphviz attributes for a significant class (see plot_enrichment)."""
    d = cfg[direction]
    if significance_style == "fill":
        return {"fillcolor": d["fills"][shade], "color": d["border"],
                "fontcolor": d["fill_text"][shade], "penwidth": cfg["penwidth"]["fill"]}

    attrs = {"fillcolor": "#ffffff" if significance_style == "border" else d["tint"],
             "color": d["borders"][shade], "fontcolor": cfg["border_text"],
             "penwidth": cfg["penwidth"]["border"]}
    if significance_style == "border-width":
        attrs["penwidth"] = cfg["border_widths"][shade]
    elif significance_style == "border-rings":
        attrs["peripheries"] = str(shade + 1)      # Graphviz: number of outlines
        attrs["penwidth"] = cfg["penwidth"]["rings"]
    return attrs


def _enrichment_legend(cfg, significance_style, directions, any_not_significant, orientation):
    """OboGraph for the legend: one box per shade for each direction in `directions`,
    plus the white box."""
    from oaklib.datamodels import obograph

    legend = obograph.Graph(id="legend", nodes=[], edges=[])
    for direction in ("over", "under"):
        if direction not in directions:
            continue
        for shade, cut in enumerate(cfg["p_levels"]):
            attrs = _significance_attrs(cfg, significance_style, direction, shade)
            legend.nodes.append(obograph.Node(
                id=f"legend:{direction}{shade}",
                lbl=(_no_break(f"{cfg[direction]['symbol']} {_DIRECTION_NAMES[direction]}")
                     + "\n" + _no_break(f"adj. p \u2264 {cut:g}")),
                meta=_kgviz_meta(attrs)))
    legend.nodes.append(obograph.Node(
        id="legend:context",
        lbl=_no_break("not significant" if any_not_significant else "ancestor, not significant"),
        meta=_kgviz_meta(cfg["context"])))

    if orientation == "vertical":
        # invisible edges stack the legend boxes in a column (first box on top)
        ids = [n.id for n in legend.nodes]
        legend.edges = [obograph.Edge(sub=lower, pred="legend:next", obj=upper)
                        for upper, lower in zip(ids, ids[1:])]
    return legend


# ------------------------------------------------------------------------------
# visualizing SPARQL query results
# ------------------------------------------------------------------------------

# names of the is_a (rdfs:subClassOf) relationship; og2dot calls it "rdfs:subClassOf"
_IS_A_KEYS = ("rdfs:subClassOf", "is_a", "http://www.w3.org/2000/01/rdf-schema#subClassOf")


def plot_sparql_graph(source, root, imgfile, query=None, predicates=None, edge_labels=None,
                      node_color="lightgray", node_border_color="black", node_border_width=1,
                      edge_color="black", edge_arrowhead="normal", include_is_a=True,
                      draw_is_a=True,
                      configure=None, highlight_root=True, root_border_width=5, show=True,
                      return_graph=False):
    """Draw the class hierarchy (and other relationships) in a SPARQL CONSTRUCT result.

    The triples are written to a temporary OWL file, loaded with OAK (pronto) and drawn
    with OAK's viz (og2dot). The image shows `root`, its is_a descendants and, for each
    predicate in `predicates`, the classes those descendants point to with that
    predicate (e.g., what the questions are about).

    With include_is_a=False no is_a edges are drawn, and the image shows only the
    relationships in `predicates` (e.g., parthood): `root`, the classes linked to it by
    a chain of those relationships in either direction (e.g., its parts, their parts,
    and the wholes it is part of), and the classes those point to with them.

    With draw_is_a=False is_a is still used to find the classes below `root`, but the
    is_a edges are not drawn, e.g. to show only what each question is about.

    Args:
        source: an rdflib Graph, or the result of `graph.query(construct_query)`.
            If `query` is given, `source` must be an rdflib Graph and the query is run on it.
        root: CURIE of the top class to draw (e.g., "OHD:0008044").
        imgfile: path of the PNG file to write.
        query: optional SPARQL CONSTRUCT query to run on `source`.
        predicates: CURIEs of relationships to draw besides is_a (e.g., ["IAO:0000136"]);
            is_a is drawn unless include_is_a=False, so it doesn't need to be listed (it is
            ignored if it is); in the CONSTRUCT they must be some-values-from restrictions
            on the class (e.g., `?part rdfs:subClassOf [owl:onProperty BFO:0000050 ;
            owl:someValuesFrom ?whole]`). Required if include_is_a=False.
        edge_labels: dict renaming edge labels, e.g.
            {"rdfs:subClassOf": "is a", "IAO:0000136": "is about"}.
            Keys may be a predicate CURIE or IRI ("is_a" and rdfs:subClassOf both mean
            the subclass edges) or the label og2dot would otherwise show for the
            predicate (e.g. "is about"). Use "" to hide a label.
        node_color: fill colour of the nodes (any Graphviz colour name or "#rrggbb").
        node_border_color: colour of the node borders.
        node_border_width: width of the node borders (Graphviz penwidth).
        edge_color: colour of the edges: one colour for all edges, or a dict with a
            colour per relation (keys as in `edge_labels`, e.g.
            {"rdfs:subClassOf": "black", "IAO:0000136": "#1c5cab"}); relations not in
            the dict are black.
        edge_arrowhead: Graphviz arrowhead of the edges ("normal", "empty", "vee",
            "open", "dot", "odot", "diamond", "odiamond", "box", "tee", "none", ...): one
            arrowhead for all edges, or a dict with one per relation (keys as in
            `edge_labels`, e.g. {"rdfs:subClassOf": "empty", "IAO:0000136": "vee"});
            relations not in the dict get "normal".
        include_is_a: draw the is_a (subclass) edges and use them to find the classes
            below `root` (default). If False, draw only the `predicates` relationships,
            e.g. predicates=["BFO:0000050"] for a partonomy.
        draw_is_a: draw the is_a edges (default). If False, the classes are still found
            with is_a (as with include_is_a=True), but only the `predicates` edges are
            drawn, and classes with none of those edges are left out.
        configure: extra og2dot style settings (dict), merged over the defaults.
        highlight_root: highlight the root node with a thicker border (default True);
            if False, the root is drawn like the other nodes.
        root_border_width: border width of the root node when it is highlighted
            (default 5).
        show: display the image in the notebook; if False, only save the PNG.
        return_graph: return the OboGraph that was drawn (by default nothing is
            returned, so the notebook doesn't print the graph after the image).

    Returns:
        The OboGraph that was drawn if `return_graph` is True, else None.

    Example:
        res = ohd_graph.query(construct_q)
        plot_sparql_graph(res, "OHD:0008044", "DFA-data/temp.hierarchy.png",
                          predicates=["IAO:0000136"],
                          edge_labels={"rdfs:subClassOf": "is a", "IAO:0000136": "is about"},
                          edge_arrowhead={"rdfs:subClassOf": "empty", "IAO:0000136": "vee"},
                          edge_color={"IAO:0000136": "#1c5cab"})

        # parthood only: the parts of the mouth, without the subclass edges
        plot_sparql_graph(res, "UBERON:0000165", "DFA-data/temp.parts.png",
                          predicates=["BFO:0000050"], include_is_a=False)

        # only what each question is about (questions found with is_a, edges hidden)
        plot_sparql_graph(res, "OHD:0008044", "DFA-data/temp.about.png",
                          predicates=["IAO:0000136"], draw_is_a=False)
    """
    from oaklib import get_adapter
    from oaklib.datamodels.vocabulary import IS_A
    from oaklib.utilities.obograph_utils import graph_to_image

    rdf = _for_pronto(_construct_graph(source, query))

    # is_a is handled by include_is_a / draw_is_a; drop it from the extra relationships
    predicates = [p for p in dict.fromkeys(predicates or []) if p not in _IS_A_KEYS]
    if not (include_is_a and draw_is_a) and not predicates:
        raise ValueError("include_is_a=False and draw_is_a=False need at least one "
                         "relationship in `predicates`")

    with tempfile.TemporaryDirectory() as tmp:
        owl_file = Path(tmp) / "viz.tmp.owl"
        rdf.serialize(owl_file, format="pretty-xml")
        adapter = get_adapter(f"pronto:{owl_file}")

        classes = _select_classes(adapter, root, predicates, include_is_a)
        edge_predicates = ([IS_A] if include_is_a else []) + predicates
        graph = adapter.extract_graph(list(classes), predicates=edge_predicates)

        # the labels og2dot shows for the predicates: their label, else the CURIE
        node_labels = {n.id: n.lbl for n in graph.nodes if n.lbl}
        predicate_labels = {p: node_labels.get(p) or adapter.label(p) for p in predicates}

    # don't draw the predicates themselves (e.g., an "is about" box) as nodes
    graph.nodes = [n for n in graph.nodes if n.id not in predicates]

    # hide the is_a edges, and the classes left without edges
    if include_is_a and not draw_is_a:
        graph.edges = [e for e in graph.edges if e.pred not in _IS_A_KEYS]
        connected = {e.sub for e in graph.edges} | {e.obj for e in graph.edges}
        graph.nodes = [n for n in graph.nodes if n.id in connected]

    # node styles; the root gets a thicker border if highlighted
    for node in graph.nodes:
        is_highlighted = highlight_root and node.id == root
        node.meta = _kgviz_meta({
            "fillcolor": node_color,
            "color": node_border_color,
            "penwidth": root_border_width if is_highlighted else node_border_width})

    # edge styles and labels (a label set here is used over og2dot's default)
    def for_relation(edge, value, default=None):
        return _value_for_relation(edge.pred, value, predicate_labels, default)

    for edge in graph.edges:
        edge.meta = _kgviz_meta({
            "label": for_relation(edge, edge_labels or {}),
            "color": for_relation(edge, edge_color, "black"),
            "arrowhead": for_relation(edge, edge_arrowhead, "normal")})

    graph_to_image(graph, configure=json.dumps(configure) if configure else None,
                   imgfile=str(imgfile))
    if show:
        _display_png(imgfile)
    return graph if return_graph else None


def _construct_graph(source, query):
    """The rdflib Graph to draw: `source` itself, the graph of a CONSTRUCT result, or
    the result of running `query` on `source`."""
    if query is not None:
        if not isinstance(source, Graph):
            raise TypeError("source must be an rdflib Graph when a query is given")
        source = source.query(query)
    rdf = source if isinstance(source, Graph) else getattr(source, "graph", None)
    if rdf is None:
        raise TypeError("source must be an rdflib Graph or the result of a CONSTRUCT query")
    if len(rdf) == 0:
        raise ValueError("the graph is empty; check the CONSTRUCT query")
    return rdf


def _for_pronto(rdf):
    """Copy of `rdf` (so the original isn't changed) with what pronto needs to load it:
    an ontology header, and a declaration of each property used in a restriction."""
    rdf = Graph() + rdf
    if not any(rdf.subjects(RDF.type, OWL.Ontology)):
        rdf.add((URIRef("http://purl.obolibrary.org/obo/viz.tmp.owl"), RDF.type, OWL.Ontology))
    for prop in set(rdf.objects(None, OWL.onProperty)):
        if isinstance(prop, URIRef) and (prop, RDF.type, OWL.ObjectProperty) not in rdf:
            rdf.add((prop, RDF.type, OWL.ObjectProperty))
    return rdf


def _select_classes(adapter, root, predicates, include_is_a):
    """The classes to draw (see plot_sparql_graph)."""
    from oaklib.datamodels.vocabulary import IS_A

    if include_is_a:
        classes = set(adapter.descendants(root, predicates=[IS_A], reflexive=True))
        if not classes - {root}:
            raise ValueError(f"no is_a descendants of {root} in the graph; "
                             "check the root CURIE")
    else:
        classes = (set(adapter.descendants(root, predicates=predicates, reflexive=True))
                   | set(adapter.ancestors(root, predicates=predicates, reflexive=True)))
        if not classes - {root}:
            raise ValueError(f"no {', '.join(predicates)} relationships of {root} in the "
                             "graph; check the root CURIE and the CONSTRUCT query")
    # plus the classes they point to with the other relationships
    if predicates:
        classes |= {o for c in list(classes)
                    for _, o in adapter.outgoing_relationships(c, predicates=predicates)}
    return classes


def _value_for_relation(pred, value, predicate_labels, default=None):
    """The style value for edges of relationship `pred`: `value` itself, or, if `value`
    is a dict, the entry for `pred`, whose key can be the predicate's CURIE, IRI or
    label (any name of is_a for the is_a edges); `default` if there is none."""
    if not isinstance(value, dict):
        return value
    if pred in _IS_A_KEYS:
        keys = _IS_A_KEYS
    else:
        keys = (pred, _obo_iri(pred), predicate_labels.get(pred))
    return next((value[k] for k in keys if k is not None and k in value), default)


def _obo_iri(curie):
    """Expand an OBO-style CURIE (e.g., IAO:0000136) to its PURL; return other values unchanged."""
    if curie and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*:\d+", curie):
        prefix, local = curie.split(":")
        return f"http://purl.obolibrary.org/obo/{prefix}_{local}"
    return curie


# ------------------------------------------------------------------------------
# display
# ------------------------------------------------------------------------------

def show_image(path, scale=1.0, dpi=100):
    """Display an image file with matplotlib at (roughly) its actual pixel size."""
    import matplotlib.pyplot as plt

    img = plt.imread(path)
    height, width = img.shape[:2]
    fig = plt.figure(figsize=(scale * width / dpi, scale * height / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])   # image fills the figure (no margins)
    ax.imshow(img)
    ax.axis("off")
    plt.show()
