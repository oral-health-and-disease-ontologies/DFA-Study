DOCSDIR = docs
SRC = src

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

# --- linkml products --- #
cohra2-jsonschema: $(COHRA2_SCHEMA)
	gen-json-schema $< > jsonschema/cohra2.json

cohra2-owl: $(COHRA2_SCHEMA)
	gen-owl $< > temp/cohra2.tmp.ttl 
	src/scripts/pun-annotations-to-ttl.py $< > temp/pun.tmp.ttl 
	robot merge -i temp/cohra2.tmp.ttl -i temp/pun.tmp.ttl -o owl/cohra2.ttl 

ada_ohwb-jsonschema: $(ADA_OHWB_SCHEMA)
	gen-json-schema $< > jsonschema/ada_ohwb.json

ada_ohwb-owl: $(ADA_OHWB_SCHEMA)
	gen-owl $< > temp/ada_ohwb.tmp.ttl 
	src/scripts/pun-annotations-to-ttl.py $< > temp/pun.tmp.ttl 
	robot merge -i temp/ada_ohwb.tmp.ttl -i temp/pun.tmp.ttl -o owl/ada_ohwb.ttl 

dfs-jsonschema: $(DFS_SCHEMA)
	gen-json-schema $< > jsonschema/dfs.json

dfs-owl: $(DFS_SCHEMA)
	gen-owl $< > temp/dfs.tmp.ttl
	src/scripts/pun-annotations-to-ttl.py $< > temp/pun.tmp.ttl 
	robot merge -i temp/dfs.tmp.ttl -i temp/pun.tmp.ttl

cq_sohea-jsonschema: $(CQ_SOHEA_SCHEMA)
	gen-json-schema $< > jsonschema/cq_sohea.json

cq_sohea-owl: $(CQ_SOHEA_SCHEMA)
	gen-owl $< > temp/cq_sohea.tmp.ttl 
	src/scripts/pun-annotations-to-ttl.py $< > temp/pun.tmp.ttl 
	robot merge -i temp/cq_sohea.tmp.ttl -i temp/pun.tmp.ttl -o owl/cq_sohea.ttl

tic_clinical-jsonschema: $(TIC_CLINICAL_SCHEMA)
	gen-json-schema $< > jsonschema/tic_clinical.json

tic_clinical-owl: $(TIC_CLINICAL_SCHEMA)
	gen-owl $< > temp/tic_clinical.tmp.ttl
	src/scripts/pun-annotations-to-ttl.py $< > temp/pun.tmp.ttl
	robot merge -i temp/tic_clinical.tmp.ttl -i temp/pun.tmp.ttl -o owl/tic_clinical.ttl

tic_provider-jsonschema: $(TIC_PROVIDER_SCHEMA)
	gen-json-schema $< > jsonschema/tic_provider.json

tic_provider-owl: $(TIC_PROVIDER_SCHEMA)
	gen-owl $< > temp/tic_provider.tmp.ttl
	src/scripts/pun-annotations-to-ttl.py $< > temp/pun.tmp.ttl
	robot merge -i temp/tic_provider.tmp.ttl -i temp/pun.tmp.ttl -o owl/tic_provider.ttl
mdas-jsonschema: $(MDAS_SCHEMA)
	gen-json-schema $< > jsonschema/mdas.json

mdas-owl: $(MDAS_SCHEMA)
	gen-owl $< > temp/mdas.tmp.ttl 
	src/scripts/pun-annotations-to-ttl.py $< > temp/pun.tmp.ttl 
	robot merge -i temp/mdas.tmp.ttl -i temp/pun.tmp.ttl -o owl/mdas.ttl

idaf-jsonschema: $(IDAF_SCHEMA)
	gen-json-schema $< > jsonschema/idaf.json

idaf-owl: $(IDAF_SCHEMA)
	gen-owl $< > temp/idaf.tmp.ttl
	src/scripts/pun-annotations-to-ttl.py $< > temp/pun.tmp.ttl 
	robot merge -i temp/idaf.tmp.ttl -i temp/pun.tmp.ttl

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
	mkdir -p $(COHRA2_DOCS_DIR)
	mkdir -p $(ADA_OHWB_DOCS_DIR)
	mkdir -p $(DFS_DOCS_DIR)
	mkdir -p $(CQ_SOHEA_DOCS_DIR)
	mkdir -p $(TIC_CLINICAL_DOCS_DIR)
	mkdir -p $(TIC_PROVIDER_DOCS_DIR)
	mkdir -p $(MDAS_DOCS_DIR)
	mkdir -p $(IDAF_DOCS_DIR)
	mkdir -p docs/images

	@# copy existing markdown files (if they exist)
	@if ls src/docs/*.md 1> /dev/null 2>&1; then cp src/docs/*.md docs/; fi
	@if ls src/docs/images/*.* 1> /dev/null 2>&1; then cp src/docs/images/*.* docs/images/; fi

	@# generate documentation
	gen-doc -d $(COHRA2_DOCS_DIR) $(COHRA2_SCHEMA)
	gen-doc -d $(ADA_OHWB_DOCS_DIR) $(ADA_OHWB_SCHEMA)
	gen-doc -d $(DFS_DOCS_DIR) $(DFS_SCHEMA)
	gen-doc -d $(CQ_SOHEA_DOCS_DIR) $(CQ_SOHEA_SCHEMA)
	gen-doc -d $(TIC_CLINICAL_DOCS_DIR) $(TIC_CLINICAL_SCHEMA)
	gen-doc -d $(TIC_PROVIDER_DOCS_DIR) $(TIC_PROVIDER_SCHEMA)
	gen-doc -d $(MDAS_DOCS_DIR) $(MDAS_SCHEMA)
	gen-doc -d $(IDAF_DOCS_DIR) $(IDAF_SCHEMA)


## remove docs
clean-docs:
# don't delete README files
	find docs/ -type f -not -name 'README.md' -delete     
	find docs/images/ -type f -not -name 'README.md' -delete     
