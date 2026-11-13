# ---------------------------------------------------------------------------- #
# configuration
# ---------------------------------------------------------------------------- #
CATALOG = catalog-v001.xml
ROBOT   = robot --catalog $(CATALOG)
PYTHON ?= python

SRC        = src
SCHEMA_DIR = $(SRC)/schema
SCRIPTS    = $(SRC)/scripts
DOCSDIR    = docs
TEMP       = temp
DATA_DIR   = notebooks/DFA-data
SUPERDATASET_DATA = $(DATA_DIR)/merged_dfa_data_cleaned_2026_09_30.csv

# schemas that import core.yaml and share the standard OWL pipeline
SCHEMAS     = cohra1 cohra2 ada_ohwb dfs cq_sohea tic_clinical tic_provider mdas idaf
ALL_SCHEMAS = $(SCHEMAS) superdataset

PUN_SCRIPT = $(SCRIPTS)/pun-annotations-to-ttl.py

GENDOC_OPTS = --verbose --no-render-imports --no-mergeimports --truncate-descriptions False
GENOWL_OPTS = \
	--log_level ERROR \
	--skip-vacuous-min-zero-cardinality-axioms \
	--skip-vacuous-local-range-axioms \
	--consolidate-cardinality-axioms \
	--default-permissible-value-type rdfs:Literal

# delete partially written targets when a recipe fails (e.g. `gen-x $< > $@`)
.DELETE_ON_ERROR:

# ---------------------------------------------------------------------------- #
# aggregate targets
# ---------------------------------------------------------------------------- #
.PHONY: all jsonschema owl
all: jsonschema owl

jsonschema: $(ALL_SCHEMAS:%=jsonschema/%.json)
owl: $(ALL_SCHEMAS:%=owl/%.ttl) owl/superdataset.owl

$(TEMP):
	mkdir -p $@

# ---------------------------------------------------------------------------- #
# linkml products
# ---------------------------------------------------------------------------- #

# changes to the imported core schema must trigger a rebuild
$(SCHEMAS:%=jsonschema/%.json) $(SCHEMAS:%=owl/%.ttl): $(SCHEMA_DIR)/core.yaml

# JSON Schema, e.g. jsonschema/cohra1.json
jsonschema/%.json: $(SCHEMA_DIR)/%.yaml
	gen-json-schema $< > $@

# OWL, e.g. owl/cohra1.ttl (superdataset overrides this below)
owl/%.ttl: $(SCHEMA_DIR)/%.yaml $(PUN_SCRIPT) | $(TEMP)
	gen-owl $(GENOWL_OPTS) $< > $(TEMP)/$*.tmp.ttl
	$(PYTHON) $(PUN_SCRIPT) $< > $(TEMP)/$*.pun.tmp.ttl
	$(ROBOT) merge -i $(TEMP)/$*.tmp.ttl -i $(TEMP)/$*.pun.tmp.ttl -o $@

# superdataset OWL has an extra step converting enum ranges to xsd datatypes
owl/superdataset.ttl: $(SCHEMA_DIR)/superdataset.yaml $(PUN_SCRIPT) $(SRC)/sparql/enum-ranges-to-xsd.ru | $(TEMP)
	gen-owl $(GENOWL_OPTS) $< > $(TEMP)/superdataset.tmp.ttl
	$(PYTHON) $(SCRIPTS)/sparql-update.py $(TEMP)/superdataset.tmp.ttl $(word 3,$^) > $(TEMP)/superdataset.dl.tmp.ttl
	$(PYTHON) $(PUN_SCRIPT) $< > $(TEMP)/superdataset.pun.tmp.ttl
	$(ROBOT) merge -i $(TEMP)/superdataset.dl.tmp.ttl -i $(TEMP)/superdataset.pun.tmp.ttl -o $@

owl/superdataset.owl: owl/superdataset.ttl
	$(ROBOT) convert -i $< -o $@ --format owl

jsonld/superdataset.jsonld: $(SCHEMA_DIR)/superdataset.yaml
	gen-jsonld $< > $@

jsonld-context/superdataset.context.jsonld: $(SCHEMA_DIR)/superdataset.yaml
	gen-jsonld-context $< > $@

# short aliases, e.g. `make cohra1-owl`, `make superdataset-jsonschema`
.PHONY: $(ALL_SCHEMAS:%=%-jsonschema) $(ALL_SCHEMAS:%=%-owl) superdataset-jsonld superdataset-jsonld-context
$(ALL_SCHEMAS:%=%-jsonschema): %-jsonschema: jsonschema/%.json
$(SCHEMAS:%=%-owl): %-owl: owl/%.ttl
superdataset-owl: owl/superdataset.ttl owl/superdataset.owl
superdataset-jsonld: jsonld/superdataset.jsonld
superdataset-jsonld-context: jsonld-context/superdataset.context.jsonld

# ---------------------------------------------------------------------------- #
# superdataset data products (for use in Jupyter notebooks)
# ---------------------------------------------------------------------------- #

# convert records from spreadsheet to RDF
# (each record gets an IRI from its Participant_id, e.g. superdataset:<Participant_id>)
$(DATA_DIR)/superdataset-records.ttl: $(SUPERDATASET_DATA) $(SCHEMA_DIR)/superdataset.yaml owl/superdataset.ttl $(SCRIPTS)/spreadsheet-to-rdf.py
	$(PYTHON) $(SCRIPTS)/spreadsheet-to-rdf.py \
		-i $< \
		-s $(word 2,$^) \
		-o $@ \
		--id-columns Participant_id

# create punning statements from pun annotations in the LinkML schema
$(DATA_DIR)/superdataset-puns.ttl: $(SCHEMA_DIR)/superdataset.yaml $(PUN_SCRIPT)
	$(PYTHON) $(PUN_SCRIPT) $< > $@

# merge schema, punning statements, and records
$(DATA_DIR)/superdataset-data.ttl: owl/superdataset.ttl $(DATA_DIR)/superdataset-puns.ttl $(DATA_DIR)/superdataset-records.ttl
	$(ROBOT) merge $(addprefix -i ,$^) -o $@

$(DATA_DIR)/%.owl: $(DATA_DIR)/%.ttl
	$(ROBOT) convert -i $< -o $@ --format owl

# short aliases, e.g. `make superdataset-data.ttl`
DATA_PRODUCTS = \
	superdataset-records.ttl superdataset-records.owl \
	superdataset-puns.ttl \
	superdataset-data.ttl superdataset-data.owl
.PHONY: $(DATA_PRODUCTS)
$(DATA_PRODUCTS): %: $(DATA_DIR)/%

# ---------------------------------------------------------------------------- #
# utilities
# ---------------------------------------------------------------------------- #
.PHONY: field-mappings
field-mappings:
	$(PYTHON) $(SCRIPTS)/field-mappings-info.py

# ---------------------------------------------------------------------------- #
# documentation
# ---------------------------------------------------------------------------- #
.PHONY: gendoc gendoc-static $(ALL_SCHEMAS:%=gendoc-%)
gendoc: gendoc-static $(ALL_SCHEMAS:%=gendoc-%)

# copy hand-written markdown and images (if they exist)
gendoc-static:
	mkdir -p $(DOCSDIR)/images
	@if ls $(SRC)/docs/*.md 1> /dev/null 2>&1; then cp $(SRC)/docs/*.md $(DOCSDIR)/; fi
	@if ls $(SRC)/docs/images/*.* 1> /dev/null 2>&1; then cp $(SRC)/docs/images/*.* $(DOCSDIR)/images/; fi

# generate docs for one schema, e.g. `make gendoc-cohra1`
$(ALL_SCHEMAS:%=gendoc-%): gendoc-%:
	mkdir -p $(DOCSDIR)/$*
	gen-doc $(GENDOC_OPTS) -d $(DOCSDIR)/$* $(SCHEMA_DIR)/$*.yaml

# ---------------------------------------------------------------------------- #
# cleanup (README files are preserved)
# ---------------------------------------------------------------------------- #
PRODUCT_DIRS = jsonschema jsonld jsonld-context shacl owl

# delete all non-README files in the given dirs, skipping dirs that don't exist
# (guard prevents `find` from defaulting to `.` when no dirs exist)
clean_dirs = $(if $(wildcard $(1)),find $(wildcard $(1)) -type f -not -name 'README.md' -delete)

.PHONY: clean clean-products clean-docs clean-temp
clean: clean-products clean-docs clean-temp

clean-products:
	$(call clean_dirs,$(PRODUCT_DIRS))

clean-docs:
	$(call clean_dirs,$(DOCSDIR))

clean-temp:
	$(call clean_dirs,$(TEMP))
