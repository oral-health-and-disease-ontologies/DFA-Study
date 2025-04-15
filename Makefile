DOCSDIR = docs
SRC = src

COHRA2_SCHEMA_DIR = $(SRC)/schema/cohra2
COHRA2_SCHEMA = $(COHRA2_SCHEMA_DIR)/cohra2-schema.yaml
COHRA2_DOCS_DIR = $(DOCSDIR)/cohra2

# --- linkml products --- #
cohra2-jsonschema: $(COHRA2_SCHEMA)
	gen-json-schema $< > jsonschema/cohra2/cohra2-jsonschema.json

cohra2-owl: $(COHRA2_SCHEMA)
	gen-owl $< > temp/cohra2.tmp.ttl 
	src/scripts/pun-annotations-to-ttl.py $< > temp/pun.tmp.ttl 
	robot merge -i temp/cohra2.tmp.ttl -i temp/pun.tmp.ttl -o owl/cohra2/cohra2-schema.ttl 

## remove products
clean-products:
# don't delete README files
	find jsonschema/ -type f -not -name 'README.md' -delete     
	find jsonld/ -type f -not -name 'README.md' -delete     
	find jsonld-context/ -type f -not -name 'README.md' -delete     
	find shacl/ -type f -not -name 'README.md' -delete     
	find owl/ -type f -not -name 'README.md' -delete     

# --- schema documentation --- #
gendoc: $(DOCSDIR)
# copy existing files (if they exist) 
# note: there is no space after the ',' in ($(wildcard src/docs/*.md),)
# condition is the true if the wildcard returns non-empty content (i.e, not equal)
ifneq ($(wildcard src/docs/*.md),)
	cp src/docs/*.md docs/
endif
ifneq ($(wildcard src/docs/images/*.*),)
	cp src/docs/images/*.* docs/images
endif
# generate documentation
	gen-doc -d $(DOCSDIR) $(COHRA2_SCHEMA)

## remove docs
clean-docs:
# don't delete README files
	find docs/ -type f -not -name 'README.md' -delete     
	find docs/images/ -type f -not -name 'README.md' -delete     
