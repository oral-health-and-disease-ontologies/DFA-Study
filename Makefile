CATALOG = catalog-v001.xml
ROBOT = robot --catalog $(CATALOG)

DOCSDIR = docs
SRC = src
DATA_DIR = notebooks/DFA-data
SUPERDATASET_DATA = $(DATA_DIR)/merged_dfa_data_cleaned_2026_09_30.csv

COHRA1_SCHEMA_DIR = $(SRC)/schema
COHRA1_SCHEMA = $(COHRA1_SCHEMA_DIR)/cohra1.yaml
COHRA1_DOCS_DIR = $(DOCSDIR)/cohra1

COHRA2_SCHEMA_DIR = $(SRC)/schema
COHRA2_SCHEMA = $(COHRA2_SCHEMA_DIR)/cohra2.yaml
COHRA2_DOCS_DIR = $(DOCSDIR)/cohra2

ADA_OHWB_SCHEMA_DIR = $(SRC)/schema
ADA_OHWB_SCHEMA = $(ADA_OHWB_SCHEMA_DIR)/ada_ohwb.yaml
ADA_OHWB_DOCS_DIR = $(DOCSDIR)/ada_ohwb

DFS_SCHEMA_DIR = $(SRC)/schema
DFS_SCHEMA = $(DFS_SCHEMA_DIR)/dfs.yaml
DFS_DOCS_DIR = $(DOCSDIR)/dfs

CQ_SOHEA_SCHEMA_DIR = $(SRC)/schema
CQ_SOHEA_SCHEMA = $(CQ_SOHEA_SCHEMA_DIR)/cq_sohea.yaml
CQ_SOHEA_DOCS_DIR = $(DOCSDIR)/cq_sohea

TIC_CLINICAL_SCHEMA_DIR = $(SRC)/schema
TIC_CLINICAL_SCHEMA = $(TIC_CLINICAL_SCHEMA_DIR)/tic_clinical.yaml
TIC_CLINICAL_DOCS_DIR = $(DOCSDIR)/tic_clinical

TIC_PROVIDER_SCHEMA_DIR = $(SRC)/schema
TIC_PROVIDER_SCHEMA = $(TIC_PROVIDER_SCHEMA_DIR)/tic_provider.yaml
TIC_PROVIDER_DOCS_DIR = $(DOCSDIR)/tic_provider
MDAS_SCHEMA_DIR = $(SRC)/schema
MDAS_SCHEMA = $(MDAS_SCHEMA_DIR)/mdas.yaml
MDAS_DOCS_DIR = $(DOCSDIR)/mdas

IDAF_SCHEMA_DIR = $(SRC)/schema
IDAF_SCHEMA = $(IDAF_SCHEMA_DIR)/idaf.yaml
IDAF_DOCS_DIR = $(DOCSDIR)/idaf

SUPERDATASET_SCHEMA_DIR = $(SRC)/schema
SUPERDATASET_SCHEMA = $(SUPERDATASET_SCHEMA_DIR)/superdataset.yaml
SUPERDATASET_DOCS_DIR = $(DOCSDIR)/superdataset

GENDOC_OPTS = --verbose --no-render-imports --no-mergeimports --truncate-descriptions False 
GENOWL_OPTS =\
	--log_level ERROR \
	--skip-vacuous-min-zero-cardinality-axioms \
	--skip-vacuous-local-range-axioms \
	--consolidate-cardinality-axioms \
	--default-permissible-value-type rdfs:Literal

# --- linkml products --- #
cohra1-jsonschema: $(COHRA1_SCHEMA)
	gen-json-schema $< > jsonschema/cohra1.json

cohra1-owl: $(COHRA1_SCHEMA)
	gen-owl $(GENOWL_OPTS) $< > temp/cohra1.tmp.ttl 
	src/scripts/pun-annotations-to-ttl.py $< > temp/$@.pun.tmp.ttl 
	$(ROBOT) merge -i temp/cohra1.tmp.ttl -i temp/$@.pun.tmp.ttl -o owl/cohra1.ttl 

cohra2-jsonschema: $(COHRA2_SCHEMA)
	gen-json-schema $< > jsonschema/cohra2.json

cohra2-owl: $(COHRA2_SCHEMA)
	gen-owl $(GENOWL_OPTS) $< > temp/cohra2.tmp.ttl 
	src/scripts/pun-annotations-to-ttl.py $< > temp/$@.pun.tmp.ttl 
	$(ROBOT) merge -i temp/cohra2.tmp.ttl -i temp/$@.pun.tmp.ttl -o owl/cohra2.ttl 

ada_ohwb-jsonschema: $(ADA_OHWB_SCHEMA)
	gen-json-schema $< > jsonschema/ada_ohwb.json

ada_ohwb-owl: $(ADA_OHWB_SCHEMA)
	gen-owl $(GENOWL_OPTS) $< > temp/ada_ohwb.tmp.ttl 
	src/scripts/pun-annotations-to-ttl.py $< > temp/$@.pun.tmp.ttl 
	$(ROBOT) merge -i temp/ada_ohwb.tmp.ttl -i temp/$@.pun.tmp.ttl -o owl/ada_ohwb.ttl 

dfs-jsonschema: $(DFS_SCHEMA)
	gen-json-schema $< > jsonschema/dfs.json

dfs-owl: $(DFS_SCHEMA)
	gen-owl $(GENOWL_OPTS) $< > temp/dfs.tmp.ttl
	src/scripts/pun-annotations-to-ttl.py $< > temp/$@.pun.tmp.ttl 
	$(ROBOT) merge -i temp/dfs.tmp.ttl -i temp/$@.pun.tmp.ttl -o owl/dfs.ttl

cq_sohea-jsonschema: $(CQ_SOHEA_SCHEMA)
	gen-json-schema $< > jsonschema/cq_sohea.json

cq_sohea-owl: $(CQ_SOHEA_SCHEMA)
	gen-owl $(GENOWL_OPTS) $< > temp/cq_sohea.tmp.ttl 
	src/scripts/pun-annotations-to-ttl.py $< > temp/$@.pun.tmp.ttl 
	$(ROBOT) merge -i temp/cq_sohea.tmp.ttl -i temp/$@.pun.tmp.ttl -o owl/cq_sohea.ttl

tic_clinical-jsonschema: $(TIC_CLINICAL_SCHEMA)
	gen-json-schema $< > jsonschema/tic_clinical.json

tic_clinical-owl: $(TIC_CLINICAL_SCHEMA)
	gen-owl $(GENOWL_OPTS) $< > temp/tic_clinical.tmp.ttl
	src/scripts/pun-annotations-to-ttl.py $< > temp/$@.pun.tmp.ttl
	$(ROBOT) merge -i temp/tic_clinical.tmp.ttl -i temp/$@.pun.tmp.ttl -o owl/tic_clinical.ttl

tic_provider-jsonschema: $(TIC_PROVIDER_SCHEMA)
	gen-json-schema $< > jsonschema/tic_provider.json

tic_provider-owl: $(TIC_PROVIDER_SCHEMA)
	gen-owl $(GENOWL_OPTS) $< > temp/tic_provider.tmp.ttl
	src/scripts/pun-annotations-to-ttl.py $< > temp/$@.pun.tmp.ttl
	$(ROBOT) merge -i temp/tic_provider.tmp.ttl -i temp/$@.pun.tmp.ttl -o owl/tic_provider.ttl
mdas-jsonschema: $(MDAS_SCHEMA)
	gen-json-schema $< > jsonschema/mdas.json

mdas-owl: $(MDAS_SCHEMA)
	gen-owl $(GENOWL_OPTS) $< > temp/mdas.tmp.ttl 
	src/scripts/pun-annotations-to-ttl.py $< > temp/$@.pun.tmp.ttl 
	$(ROBOT) merge -i temp/mdas.tmp.ttl -i temp/$@.pun.tmp.ttl -o owl/mdas.ttl

idaf-jsonschema: $(IDAF_SCHEMA)
	gen-json-schema $< > jsonschema/idaf.json

idaf-owl: $(IDAF_SCHEMA)
	gen-owl $(GENOWL_OPTS) $< > temp/idaf.tmp.ttl
	src/scripts/pun-annotations-to-ttl.py $< > temp/$@.pun.tmp.ttl 
	$(ROBOT) merge -i temp/idaf.tmp.ttl -i temp/$@.pun.tmp.ttl -o owl/idaf.ttl

superdataset-jsonschema: $(SUPERDATASET_SCHEMA)
	gen-json-schema $< > jsonschema/superdataset.json

superdataset-jsonld: $(SUPERDATASET_SCHEMA)
	gen-jsonld $< > jsonld/superdataset.jsonld

superdataset-jsonld-context: $(SUPERDATASET_SCHEMA)
	gen-jsonld-context $< > jsonld-context/superdataset.context.jsonld

superdataset-owl: $(SUPERDATASET_SCHEMA)
	gen-owl $(GENOWL_OPTS) $< > temp/superdataset.tmp.ttl
	src/scripts/sparql-update.py temp/superdataset.tmp.ttl src/sparql/enum-ranges-to-xsd.ru > temp/superdataset.dl.tmp.ttl
	src/scripts/pun-annotations-to-ttl.py $< > temp/$@.pun.tmp.ttl
	$(ROBOT) merge -i temp/superdataset.dl.tmp.ttl -i temp/$@.pun.tmp.ttl -o owl/superdataset.ttl
	$(ROBOT) convert -i owl/superdataset.ttl -o owl/superdataset.owl --format owl

superdataset-records.ttl: $(SUPERDATASET_DATA) $(SUPERDATASET_SCHEMA) owl/superdataset.ttl
# convert superdataset records from spreadsheet to RDF for use in Jupyter notebooks
# (each record gets an IRI from its Participant_id, e.g. superdataset:<Participant_id>)
	python src/scripts/spreadsheet-to-rdf.py \
		-i $< \
		-s $(word 2,$^) \
		-o $(DATA_DIR)/$@ \
		--id-columns Participant_id

superdataset-records.owl: $(DATA_DIR)/superdataset-records.ttl
	$(ROBOT) convert -i $< -o $(DATA_DIR)/$@ --format owl

superdataset-puns.ttl: $(SUPERDATASET_SCHEMA)
# use pun annotations in the LinkML schema to create punning statements for use in Jupyter notebooks
	python src/scripts/pun-annotations-to-ttl.py $< > $(DATA_DIR)/$@ 

superdataset-data.ttl: owl/superdataset.ttl superdataset-puns.ttl superdataset-records.ttl
# merge superdataset records and punning statements for use in Jupyter notebooks
	$(ROBOT) merge \
		-i $< \
		-i $(DATA_DIR)/$(word 2,$^) \
		-i $(DATA_DIR)/$(word 3,$^) \
		-o $(DATA_DIR)/$@

superdataset-data.owl: $(DATA_DIR)/superdataset-data.ttl
	$(ROBOT) convert -i $< -o $(DATA_DIR)/$@ --format owl

field-mappings:
	python src/scripts/field-mappings-info.py

## remove products
clean-products:
# don't delete README files
	find jsonschema/ -type f -not -name 'README.md' -delete     
	find jsonld/ -type f -not -name 'README.md' -delete     
	find jsonld-context/ -type f -not -name 'README.md' -delete     
	find shacl/ -type f -not -name 'README.md' -delete     
	find owl/ -type f -not -name 'README.md' -delete     

gendoc:
	@# create target folders
	mkdir -p $(COHRA1_DOCS_DIR)
	mkdir -p $(COHRA2_DOCS_DIR)
	mkdir -p $(ADA_OHWB_DOCS_DIR)
	mkdir -p $(DFS_DOCS_DIR)
	mkdir -p $(CQ_SOHEA_DOCS_DIR)
	mkdir -p $(TIC_CLINICAL_DOCS_DIR)
	mkdir -p $(TIC_PROVIDER_DOCS_DIR)
	mkdir -p $(MDAS_DOCS_DIR)
	mkdir -p $(IDAF_DOCS_DIR)
	mkdir -p $(SUPERDATASET_DOCS_DIR)
	mkdir -p docs/images

	@# copy existing markdown files (if they exist)
	@if ls src/docs/*.md 1> /dev/null 2>&1; then cp src/docs/*.md docs/; fi
	@if ls src/docs/images/*.* 1> /dev/null 2>&1; then cp src/docs/images/*.* docs/images/; fi

	@# generate documentation
	gen-doc $(GENDOC_OPTS) -d $(COHRA1_DOCS_DIR) $(COHRA1_SCHEMA)
	gen-doc $(GENDOC_OPTS) -d $(COHRA2_DOCS_DIR) $(COHRA2_SCHEMA)
	gen-doc $(GENDOC_OPTS) -d $(ADA_OHWB_DOCS_DIR) $(ADA_OHWB_SCHEMA)
	gen-doc $(GENDOC_OPTS) -d $(DFS_DOCS_DIR) $(DFS_SCHEMA)
	gen-doc $(GENDOC_OPTS) -d $(CQ_SOHEA_DOCS_DIR) $(CQ_SOHEA_SCHEMA)
	gen-doc $(GENDOC_OPTS) -d $(TIC_CLINICAL_DOCS_DIR) $(TIC_CLINICAL_SCHEMA)
	gen-doc $(GENDOC_OPTS) -d $(TIC_PROVIDER_DOCS_DIR) $(TIC_PROVIDER_SCHEMA)
	gen-doc $(GENDOC_OPTS) -d $(MDAS_DOCS_DIR) $(MDAS_SCHEMA)
	gen-doc $(GENDOC_OPTS) -d $(IDAF_DOCS_DIR) $(IDAF_SCHEMA)
	gen-doc $(GENDOC_OPTS) -d $(SUPERDATASET_DOCS_DIR) $(SUPERDATASET_SCHEMA)


## remove docs
clean-docs:
# don't delete README files
	find docs/ -type f -not -name 'README.md' -delete     
	find docs/images/ -type f -not -name 'README.md' -delete     