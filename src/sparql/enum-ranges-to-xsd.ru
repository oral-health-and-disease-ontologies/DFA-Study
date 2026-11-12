# Post-process gen-owl output so it is in the OWL 2 DL profile.
#
# gen-owl (with --default-permissible-value-type rdfs:Literal) types each enum
# as both owl:Class and rdfs:Datatype with an owl:oneOf list of literals, and
# uses the enum as the rdfs:range of data properties. This is not valid OWL DL.
#
# 1. Replace enum ranges on data properties with xsd:integer
#    (or xsd:string if any of the enum's codes is not an integer).
# 2. Remove the rdfs:Datatype typing and owl:oneOf list from enums, leaving
#    them as owl:Class with their labels, definitions and permissible values
#    as annotations.

PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:   <http://www.w3.org/2002/07/owl#>
PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>
PREFIX linkml: <https://w3id.org/linkml/>

DELETE { ?p rdfs:range ?enum }
INSERT { ?p rdfs:range ?xsd }
WHERE {
  ?p a owl:DatatypeProperty ;
     rdfs:range ?enum .
  ?enum a rdfs:Datatype , owl:Class .
  BIND(IF(EXISTS { ?enum linkml:permissible_values ?v
                   FILTER(!REGEX(STR(?v), "^-?[0-9]+$")) },
          xsd:string, xsd:integer) AS ?xsd)
} ;

DELETE { ?n ?np ?no }
WHERE {
  ?enum a rdfs:Datatype , owl:Class ;
        owl:oneOf ?list .
  ?list rdf:rest* ?n .
  ?n ?np ?no .
  FILTER(isBlank(?n))
} ;

DELETE { ?enum owl:oneOf ?list }
WHERE {
  ?enum a rdfs:Datatype , owl:Class ;
        owl:oneOf ?list .
} ;

DELETE { ?enum a rdfs:Datatype }
WHERE {
  ?enum a rdfs:Datatype , owl:Class .
}
