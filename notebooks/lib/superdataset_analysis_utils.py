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
  display               show_image

Dependencies used by only some functions (oaklib, scipy, SPARQLWrapper, pyoxigraph,
semsql, matplotlib, IPython) are imported inside those functions, so the module can be
imported without all of them installed.
"""

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
from rdflib import BNode, Graph, Literal, URIRef

__all__ = [
    "head", "timed",
    "sparql_df", "sql_df",
    "detect_rdf_format", "build_semsql_db",
    "record_curie", "run_enrichment", "plot_enrichment", "ENRICHMENT_STYLE",
    "show_image",
]



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
    from SPARQLWrapper import JSON, SPARQLWrapper   # only needed for endpoints
    def convert(term):
        if term is None:
            return None
        if to_python and isinstance(term, Literal):
            value = term.toPython()
            return float(value) if isinstance(value, Decimal) else value
        return str(term)

    def to_term(b):
        # JSON result binding -> rdflib term
        if b is None:
            return None
        if b["type"] == "uri":
            return URIRef(b["value"])
        if b["type"] == "bnode":
            return BNode(b["value"])
        return Literal(b["value"], lang=b.get("xml:lang"), datatype=b.get("datatype"))

    if isinstance(source, Graph):
        res = source.query(query)
        cols = [str(v) for v in res.vars]
        rows = [[convert(term) for term in row] for row in res]
    else:
        sw = SPARQLWrapper(source)
        sw.setQuery(query)
        sw.setReturnFormat(JSON)
        res = sw.query().convert()
        cols = res["head"]["vars"]
        rows = [[convert(to_term(b.get(c))) for c in cols] for b in res["results"]["bindings"]]

    df = pd.DataFrame(rows, columns=cols)
    # use nullable types so integer columns with missing values stay integers
    return df.convert_dtypes() if to_python else df


def sql_df(query, con, params=None):
    """Run a SQL query and return the results as a pandas DataFrame."""
    return pd.read_sql(query, con, params=params)

# ------------------------------------------------------------------------------
# semantic-sql (SQLite) databases
# ------------------------------------------------------------------------------

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
        text = f.read(sample_size).decode("utf-8", errors="replace").lstrip("﻿")
    stripped = text.lstrip()
    # first line that is not blank or a comment ("#" for Turtle/N-Triples, "!" for OBO)
    content = [line.strip() for line in text.splitlines()
               if line.strip() and not line.lstrip().startswith(("#", "!"))]
    first = content[0] if content else ""

    if stripped.startswith("<?xml") or stripped.startswith("<!DOCTYPE") or re.match(r"<[\w:]+[\s>]", stripped):
        # XML: RDF/XML has an rdf:RDF root element; OWL/XML has an Ontology root element
        root = re.search(r"<(?!\?|!)([\w.-]+:)?([\w.-]+)[\s>/]", stripped)
        if root and root.group(2) == "RDF":
            return "rdfxml"
        if root and root.group(2) == "Ontology":
            return "owlxml"
        raise ValueError(f"{path}: XML file, but neither RDF/XML nor OWL/XML")
    if first.startswith(("{", "[")):
        return "jsonld"
    if re.match(r"(Prefix|Ontology|Import|Declaration)\(", first):
        return "functional"
    if re.match(r"(Prefix|Ontology|Import|Class|ObjectProperty|DataProperty|AnnotationProperty|Individual|Datatype):", first):
        return "manchester"
    if re.match(r"(format-version|data-version|ontology|default-namespace|date|saved-by|auto-generated-by|subsetdef|synonymtypedef|import|idspace|remark):", first) \
            or re.search(r"^\[(Term|Typedef|Instance)\]", text, re.M):
        return "obo"
    if re.match(r"(@prefix|@base)\b", first) or re.match(r"(PREFIX|BASE)\s", first, re.I):
        return "turtle"
    ntriple = re.compile(r'^(<[^>]*>|_:\S+)\s+<[^>]*>\s+(<[^>]*>|_:\S+|".*"(\^\^<[^>]*>|@[\w-]+)?)\s*\.$')
    if content and all(ntriple.match(line) for line in content[:50]):
        return "ntriples"
    if re.match(r"(<[^>]*>|_:\S+|[\w-]*:\S*)\s", first):
        return "turtle"      # Turtle without prefix declarations at the top
    raise ValueError(f"{path}: unrecognized RDF/OWL serialization")


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
    import pyoxigraph
    import semsql
    
    pyoxigraph_formats = {"turtle": pyoxigraph.RdfFormat.TURTLE, "ntriples": pyoxigraph.RdfFormat.N_TRIPLES,
                          "jsonld": pyoxigraph.RdfFormat.JSON_LD}
    robot_formats = {"functional", "manchester", "owlxml", "obo"}
    if method not in ("rdftab", "semsql"):
        raise ValueError(f"method must be 'rdftab' or 'semsql', not {method!r}")
    data_path, db_path = Path(data_path), Path(db_path)
    if db_path.exists() and not rebuild:
        return db_path
    fmt = input_format or detect_rdf_format(data_path)
    if fmt not in pyoxigraph_formats and fmt not in robot_formats and fmt != "rdfxml":
        raise ValueError(f"unsupported input_format {fmt!r}")
    print(f"{data_path.name}: {fmt}")

    work = db_path.parent
    work.mkdir(parents=True, exist_ok=True)
    builder = Path(semsql.__file__).parent / "builder"

    # RDF/XML for rdftab / semsql (semsql make X.db expects X.owl next to it)
    owl_path = work / (db_path.stem + ".owl")
    created = []                                     # temporary files to remove at the end
    if fmt == "rdfxml":
        if method == "rdftab":
            rdfxml_path = data_path                  # use the input file directly
        elif data_path.resolve() == owl_path.resolve():
            rdfxml_path = owl_path
        else:
            shutil.copy(data_path, owl_path); created.append(owl_path); rdfxml_path = owl_path
    else:
        if data_path.resolve() == owl_path.resolve():
            raise ValueError(f"{data_path} is {fmt}; it would be overwritten by the RDF/XML conversion")
        if fmt in pyoxigraph_formats:
            with open(data_path, "rb") as src, open(owl_path, "wb") as rdfxml:
                pyoxigraph.serialize(pyoxigraph.parse(src, format=pyoxigraph_formats[fmt]),
                                     rdfxml, format=pyoxigraph.RdfFormat.RDF_XML)
        else:
            subprocess.run(["robot", "convert", "-i", str(data_path), "--format", "owl", "-o", str(owl_path)],
                           check=True, capture_output=True, text=True)
        created.append(owl_path); rdfxml_path = owl_path

    # semsql's standard prefixes + extra prefixes
    prefixes = work / "prefixes.csv"
    lines = (builder / "prefixes" / "prefixes.csv").read_text().rstrip("\n").split("\n")
    lines += [f"{p},{base}" for p, base in (extra_prefixes or {}).items()]
    prefixes.write_text("\n".join(lines) + "\n")

    try:
        db_path.unlink(missing_ok=True)
        if method == "semsql":
            build = subprocess.run(["semsql", "make", "-P", prefixes.name, db_path.name],
                                   cwd=work, capture_output=True, text=True)
            if build.returncode != 0:
                raise RuntimeError(f"semsql failed:\n{build.stderr[-3000:]}")
        else:
            tmp = db_path.with_suffix(".db.tmp")
            tmp.unlink(missing_ok=True)
            with sqlite3.connect(tmp) as db:
                db.executescript((builder / "sql_schema" / "semsql.sql").read_text())   # tables and views
                rows = [line.split(",", 1) for line in lines[1:] if "," in line]       # skip the header
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
    finally:
        for f in created:                            # never deletes the input file
            f.unlink(missing_ok=True)
    return db_path

# ------------------------------------------------------------------------------
# term enrichment
# ------------------------------------------------------------------------------

def record_curie(iris):
    """Convert record IRIs (e.g., https://w3id.org/OHD/DFA-study/superdataset/1234)
    to CURIEs (superdataset:1234), the form used for record IDs with OAK.

    Records get their IRIs from their Participant_id when the RDF is created
    (spreadsheet-to-rdf.py --id-columns Participant_id).
    """
    return iris.str.replace("https://w3id.org/OHD/DFA-study/superdataset/", "superdataset:", regex=False)


def run_enrichment(adapter, sample, background, direction="greater", cutoff=0.05, filter_redundant=False):
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
    
    if direction not in ("greater", "less", "two-sided"):
        raise ValueError(f"direction must be 'greater', 'less' or 'two-sided', not {direction!r}")
    cols = ["rank", "class_id", "class_label", "direction", "sample_count", "sample_total",
            "background_count", "background_total", "p_value", "p_value_adjusted",
            "ancestor_of_more_informative_result", "descendant_of_more_informative_result",
            "sample_pct", "background_pct"]

    sample = list(dict.fromkeys(sample))                 # drop duplicates, keep order
    if not sample:
        raise ValueError("the sample is empty: no records to test")
    background = set(background) | set(sample)          # background includes the sample
    n_sample, n_bg = len(sample), len(background)

    sample_counts = dict(adapter.association_subject_counts(sample, object_closure_predicates=[IS_A]))
    if not any(sample_counts.values()):
        raise ValueError("No associations found for the sample records. Check that the sample IDs are "
                         "record CURIEs (superdataset:<Participant_id>) and that the association and "
                         "database cells were run on the current data.")
    bg_counts = dict(adapter.association_subject_counts(background, object_closure_predicates=[IS_A]))

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
    df = pd.DataFrame(rows, columns=cols)
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
    seen, seen_ancestors = {}, {}
    anc_flags, desc_flags = [], []
    for cls, d in zip(df["class_id"], groups):
        s, sa = seen.setdefault(d, set()), seen_ancestors.setdefault(d, set())
        desc_flags.append(bool(s & (ancestors[cls] - {cls})) or None)
        anc_flags.append((cls in sa) or None)
        s.add(cls)
        sa.update(ancestors[cls])
    df["ancestor_of_more_informative_result"] = anc_flags
    df["descendant_of_more_informative_result"] = desc_flags
    df["rank"] = range(1, len(df) + 1)
    
    if filter_redundant:
        redundant = df["ancestor_of_more_informative_result"].fillna(False).astype(bool) | \
                    df["descendant_of_more_informative_result"].fillna(False).astype(bool)
        df = df[~redundant].reset_index(drop=True)

    df["class_label"] = [adapter.label(c) for c in df["class_id"]]
    df["sample_pct"] = (100 * df["sample_count"] / df["sample_total"]).round(1)
    df["background_pct"] = (100 * df["background_count"] / df["background_total"]).round(1)
    return df[cols]


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


# Colors for plot_enrichment. Orange = over-represented, blue = under-represented
# (a diverging pair that stays distinguishable with all common types of colour blindness).
# Significance (adjusted p) is shown by 4 shades, light -> dark, on the box border
# ("border-width", "border-rings", "border-tint", "border") or the box fill ("fill"),
# plus border width ("border-width") or number of outlines ("border-rings"); the ramps were
# checked for monotone lightness, a single hue and readable label text.
ENRICHMENT_STYLE = {
    "p_levels": [0.05, 1e-3, 1e-6, 1e-12],     # adj. p at or below -> shade 0, 1, 2, 3
    "over":  {"symbol": "\u25b2",                                                             # orange
              "borders": ["#ff9067", "#da5821", "#9e3703", "#611f01"], "tint": "#fed3c4",       # "border" styles
              "fills": ["#fea98b", "#fb7744", "#da5821", "#b43f01"], "border": "#9e3703",       # "fill" style
              "fill_text": ["#0b0b0b", "#ffffff", "#ffffff", "#ffffff"]},                       # label ink on each fill
    "under": {"symbol": "\u25bc",                                                             # blue
              "borders": ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"], "tint": "#cce0f9",
              "fills": ["#9ec5f4", "#6da7ec", "#3987e5", "#256abf"], "border": "#1c5cab",
              "fill_text": ["#0b0b0b", "#0b0b0b", "#ffffff", "#ffffff"]},
    "border_text": "#0b0b0b",                                     # label ink in the "border" styles
    "penwidth": {"fill": "2", "border": "4", "rings": "2"},
    "border_widths": ["1.5", "3", "5", "7"],                      # "border-width": width for each shade
    "context": {"fillcolor": "#ffffff", "color": "#898781", "fontcolor": "#52514e", "penwidth": "1"},
}


def plot_enrichment(adapter, enrichment, imgfile, top_class="OHD:0008011", width=30,
                    show=True, legend=True, legend_orientation="vertical",
                    legend_position=None,
                    significance_style="border-width",
                    style=None):
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
            "border-rings": shaded border with 1-4 outlines (countable; works in black and white);
            "border-tint": shaded border of constant width;
            "border": white box with a shaded border;
            "fill": shaded box fill.
        style: colours, shades and widths to use (same structure as ENRICHMENT_STYLE);
            default: ENRICHMENT_STYLE.
    """
    from IPython.display import Image, display
    from oaklib.datamodels import obograph
    from oaklib.datamodels.vocabulary import IS_A
    from oaklib.utilities.obograph_utils import graph_to_image
    
    if legend_orientation not in ("horizontal", "vertical"):
        raise ValueError(f"legend_orientation must be 'horizontal' or 'vertical', not {legend_orientation!r}")
    if legend_position is None:
        legend_position = "right" if legend_orientation == "vertical" else "bottom"
    if legend_position not in ("right", "left", "top", "bottom"):
        raise ValueError(f"legend_position must be 'right', 'left', 'top' or 'bottom', not {legend_position!r}")
    styles = ("border-width", "border-rings", "border-tint", "border", "fill")
    if significance_style not in styles:
        raise ValueError(f"significance_style must be one of {styles}, not {significance_style!r}")
    cfg = style or ENRICHMENT_STYLE
    ids = enrichment["class_id"].tolist()
    graph = adapter.ancestor_graph(ids, predicates=[IS_A])

    # drop the upper-level ancestors (BFO, IAO, ...) and the predicate node OAK adds
    keep = set(adapter.descendants(top_class, predicates=[IS_A]))
    graph.nodes = [n for n in graph.nodes if n.id in keep]
    graph.edges = [e for e in graph.edges if e.sub in keep and e.obj in keep]

    def level(p):
        # index of the shade for an adjusted p-value
        return max(i for i, cut in enumerate(cfg["p_levels"]) if p <= cut)

    def node_style(attrs):
        # og2dot passes https://w3id.org/kgviz/<attribute> values to Graphviz
        return obograph.Meta(basicPropertyValues=[
            obograph.BasicPropertyValue(pred=f"https://w3id.org/kgviz/{k}", val=str(v))
            for k, v in attrs.items()])

    def significant_style(direction, step):
        d = cfg[direction]
        if significance_style == "fill":
            attrs = {"fillcolor": d["fills"][step], "color": d["border"],
                     "fontcolor": d["fill_text"][step], "penwidth": cfg["penwidth"]["fill"]}
        else:
            attrs = {"fillcolor": "#ffffff" if significance_style == "border" else d["tint"],
                     "color": d["borders"][step], "fontcolor": cfg["border_text"],
                     "penwidth": cfg["penwidth"]["border"]}
            if significance_style == "border-width":
                attrs["penwidth"] = cfg["border_widths"][step]
            elif significance_style == "border-rings":
                attrs["peripheries"] = str(step + 1)      # Graphviz: number of outlines
                attrs["penwidth"] = cfg["penwidth"]["rings"]
        return node_style(attrs)

    def wrap(text):
        # og2dot puts every word on its own line; wrap the labels ourselves and use
        # non-breaking spaces within a line
        return "\n".join(line.replace(" ", " ") for line in textwrap.wrap(text, width))

    stats = enrichment.set_index("class_id")
    used = set()
    not_significant = False      # any results above the significance cutoff?
    for node in graph.nodes:
        label = wrap(node.lbl or node.id)
        if node.id in stats.index:
            r = stats.loc[node.id]
            direction = r.get("direction") or ("over" if r.sample_pct >= r.background_pct else "under")
            significant = r.p_value_adjusted <= cfg["p_levels"][0]
            label += (f"\n{cfg[direction]['symbol']} {r.sample_pct:.1f}% vs {r.background_pct:.1f}%"
                      f"\nadj. p = {r.p_value_adjusted:.1e}" + ("" if significant else f" (n.s.)"))
            if significant:
                used.add(direction)
                node.meta = significant_style(direction, level(r.p_value_adjusted))
            else:
                not_significant = True
                node.meta = node_style(cfg["context"])     # in the results, but not significant
        else:
            node.meta = node_style(cfg["context"])
        node.lbl = label

    configure = ('{"relationProperties": {"rdfs:subClassOf": {"label": ""}, '
                 '"legend:next": {"style": "invis", "arrowhead": "none", "label": ""}}}')
    if not legend:
        graph_to_image(graph, configure=configure, imgfile=str(imgfile))
    else:
        # legend: one box per shade for each direction in the results, plus the white style
        names = {"over": "over-represented", "under": "under-represented"}
        legend_graph = obograph.Graph(id="legend", nodes=[], edges=[])
        for direction in ("over", "under"):
            if direction not in used:
                continue
            for step, cut in enumerate(cfg["p_levels"]):
                legend_graph.nodes.append(obograph.Node(
                    id=f"legend:{direction}{step}",
                    lbl=f"{cfg[direction]['symbol']} {names[direction]}\nadj. p \u2264 {cut:g}",
                    meta=significant_style(direction, step)))
        legend_graph.nodes.append(obograph.Node(
            id="legend:context", lbl="not significant" if not_significant else "ancestor, not significant",
            meta=node_style(cfg["context"])))
        if legend_orientation == "vertical":
            # invisible edges stack the legend boxes in a column (first box on top)
            legend_ids = [n.id for n in legend_graph.nodes]
            legend_graph.edges = [obograph.Edge(sub=lower, pred="legend:next", obj=upper)
                                  for upper, lower in zip(legend_ids, legend_ids[1:])]

        # draw the graph and the legend separately, then place the legend next to the graph
        with tempfile.TemporaryDirectory() as tmp:
            graph_png, legend_png = Path(tmp) / "graph.png", Path(tmp) / "legend.png"
            graph_to_image(graph, configure=configure, imgfile=str(graph_png))
            graph_to_image(legend_graph, configure=configure, imgfile=str(legend_png))
            _combine_images(graph_png, legend_png, imgfile, legend_position)
    if show:
        display(Image(filename=str(imgfile)))

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
