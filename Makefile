DOCSDIR = docs
SRC = src

COHRA2_SCHEMA_DIR = $(SRC)/schema
COHRA2_SCHEMA = $(COHRA2_SCHEMA_DIR)/cohra2.yaml
COHRA2_DOCS_DIR = $(DOCSDIR)/cohra2

ADA_OHWB_SCHEMA_DIR = $(SRC)/schema
ADA_OHWB_SCHEMA = $(ADA_OHWB_SCHEMA_DIR)/ada_ohwb.yaml
ADA_OHWB_DOCS_DIR = $(DOCSDIR)/ada_ohwb

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
	mkdir -p docs/images

	@# copy existing markdown files (if they exist)
	@if ls src/docs/*.md 1> /dev/null 2>&1; then cp src/docs/*.md docs/; fi
	@if ls src/docs/images/*.* 1> /dev/null 2>&1; then cp src/docs/images/*.* docs/images/; fi

	@# generate documentation
	gen-doc -d $(COHRA2_DOCS_DIR) $(COHRA2_SCHEMA)
	gen-doc -d $(ADA_OHWB_DOCS_DIR) $(ADA_OHWB_SCHEMA)


## remove docs
clean-docs:
# don't delete README files
	find docs/ -type f -not -name 'README.md' -delete     
	find docs/images/ -type f -not -name 'README.md' -delete     
