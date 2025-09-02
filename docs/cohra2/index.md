# COHRA2 Study Schema

LinkML schema for defining data elements used in the COHRA2 study.

URI: https://w3id.org/OHD/DFA-study/cohra2

Name: cohra2



## Classes

| Class | Description |
| --- | --- |
| [Dataset](Dataset.md) | The dataset for the study |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[COHRA2Dataset](COHRA2Dataset.md) | The COHRA2 dataset |
| [Record](Record.md) | A record in the dataset |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[COHRA2Record](COHRA2Record.md) | A record in the COHRA2 dataset |



## Slots

| Slot | Description |
| --- | --- |
| [Age](Age.md) | The particpant's age at the time of the visit |
| [demRace](demRace.md) | What is your race/ethnicity? |
| [DF01](DF01.md) | Has fear of dental work ever caused you to put off making an appointment? |
| [DF02](DF02.md) | Has fear of dental work ever caused you to cancel or not appear for an appoin... |
| [DF03](DF03.md) | When having dental work done, my muscles become tense |
| [DF04](DF04.md) | When having dental work done, my breathing rate increases |
| [DF05](DF05.md) | When having dental work done, I perspire |
| [DF06](DF06.md) | When having dental work done, I feel nauseated and sick to my stomach |
| [DF07](DF07.md) | When having dental work done, my heart beats faster |
| [DF08](DF08.md) | Please rate how much fear, anxiety, or unpleasantness each of these dental si... |
| [DF09](DF09.md) | Please rate how much fear, anxiety, or unpleasantness each of these dental si... |
| [DF10](DF10.md) | Please rate how much fear, anxiety, or unpleasantness each of these dental si... |
| [DF11](DF11.md) | Please rate how much fear, anxiety, or unpleasantness each of these dental si... |
| [DF12](DF12.md) | Please rate how much fear, anxiety, or unpleasantness each of these dental si... |
| [DF13](DF13.md) | Please rate how much fear, anxiety, or unpleasantness each of these dental si... |
| [DF14](DF14.md) | Please rate how much fear, anxiety, or unpleasantness each of these dental si... |
| [DF15](DF15.md) | Please rate how much fear, anxiety, or unpleasantness each of these dental si... |
| [DF16](DF16.md) | Please rate how much fear, anxiety, or unpleasantness each of these dental si... |
| [DF17](DF17.md) | Please rate how much fear, anxiety, or unpleasantness each of these dental si... |
| [DF18](DF18.md) | Please rate how much fear, anxiety, or unpleasantness each of these dental si... |
| [DF19](DF19.md) | Please rate how much fear, anxiety, or unpleasantness each of these dental si... |
| [DF20](DF20.md) | Please rate how much fear, anxiety, or unpleasantness each of these dental si... |
| [DF21](DF21.md) | Choose the appropriate number for each item to rate your FEAR OF PAIN in rela... |
| [DF22](DF22.md) | Choose the appropriate number for each item to rate your FEAR OF PAIN in rela... |
| [DF23](DF23.md) | Choose the appropriate number for each item to rate your FEAR OF PAIN in rela... |
| [DF24](DF24.md) | Choose the appropriate number for each item to rate your FEAR OF PAIN in rela... |
| [DF25](DF25.md) | Choose the appropriate number for each item to rate your FEAR OF PAIN in rela... |
| [DF26](DF26.md) | Choose the appropriate number for each item to rate your FEAR OF PAIN in rela... |
| [DF27](DF27.md) | Choose the appropriate number for each item to rate your FEAR OF PAIN in rela... |
| [DF28](DF28.md) | Choose the appropriate number for each item to rate your FEAR OF PAIN in rela... |
| [DF29](DF29.md) | Choose the appropriate number for each item to rate your FEAR OF PAIN in rela... |
| [Ethnicity](Ethnicity.md) | Hispanic or Latino |
| [Participant_ID](Participant_ID.md) | The participant's study ID |
| [Pedigree_Name](Pedigree_Name.md) | The Family pedigree number assigned by genetic relationship |
| [records](records.md) | Slot for connecting the dataset to its records |
| [Sex](Sex.md) | The particpant's sex |
| [Site](Site.md) | The code for the study site where the assessment was given |
| [Timepoint](Timepoint.md) | The timepoint in the study when the visit occurred |
| [TimepointDesc](TimepointDesc.md) | Description of the timepoint |


## Enumerations

| Enumeration | Description |
| --- | --- |
| [DemRaceCOHRA2](DemRaceCOHRA2.md) | Enumeration of participant race/ethnicity in COHRA2 |
| [LikertFear](LikertFear.md) | Enumeration for respondant level of fear toward some situation |
| [LikertFearNH](LikertFearNH.md) | Enumeration for respondant level of fear toward some situation, including an ... |
| [NoYesCOHRA2](NoYesCOHRA2.md) | Enumeration for yes/no responses in COHRA2 |
| [SexCOHRA2](SexCOHRA2.md) | Enumeration for the sex of the participant |
| [Site](Site.md) | Enumeration for the study site where the assessment was given |
| [Timepoint](Timepoint.md) | Enumeration for the point in time at which the participant answered the quest... |


## Types

| Type | Description |
| --- | --- |
| [Boolean](Boolean.md) | A binary (true or false) value |
| [Curie](Curie.md) | a compact URI |
| [Date](Date.md) | a date (year, month and day) in an idealized calendar |
| [DateOrDatetime](DateOrDatetime.md) | Either a date or a datetime |
| [Datetime](Datetime.md) | The combination of a date and time |
| [Decimal](Decimal.md) | A real number with arbitrary precision that conforms to the xsd:decimal speci... |
| [Double](Double.md) | A real number that conforms to the xsd:double specification |
| [Float](Float.md) | A real number that conforms to the xsd:float specification |
| [Integer](Integer.md) | An integer |
| [Jsonpath](Jsonpath.md) | A string encoding a JSON Path |
| [Jsonpointer](Jsonpointer.md) | A string encoding a JSON Pointer |
| [Ncname](Ncname.md) | Prefix part of CURIE |
| [Nodeidentifier](Nodeidentifier.md) | A URI, CURIE or BNODE that represents a node in a model |
| [Objectidentifier](Objectidentifier.md) | A URI or CURIE that represents an object in the model |
| [Sparqlpath](Sparqlpath.md) | A string encoding a SPARQL Property Path |
| [String](String.md) | A character string |
| [Time](Time.md) | A time object represents a (local) time of day, independent of any particular... |
| [Uri](Uri.md) | a complete URI |
| [Uriorcurie](Uriorcurie.md) | a URI or a CURIE |


## Subsets

| Subset | Description |
| --- | --- |
