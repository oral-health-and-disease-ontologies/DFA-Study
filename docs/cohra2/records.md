

# Slot: records 


_Slot for connecting the dataset to its records_





URI: [cohra2:records](https://w3id.org/OHD/DFA-study/cohra2/records)
Alias: records

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [COHRA2Dataset](COHRA2Dataset.md) | The COHRA2 dataset |  yes  |
| [Dataset](Dataset.md) | The dataset for the study |  no  |







## Properties

* Range: [Record](Record.md)

* Multivalued: True





## Identifier and Mapping Information







### Schema Source


* from schema: https://w3id.org/OHD/DFA-study/cohra2




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | cohra2:records |
| native | cohra2:records |




## LinkML Source

<details>
```yaml
name: records
description: Slot for connecting the dataset to its records
from_schema: https://w3id.org/OHD/DFA-study/cohra2
rank: 1000
alias: records
domain_of:
- Dataset
range: Record
multivalued: true
inlined: true
inlined_as_list: true

```
</details>