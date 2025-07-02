

# Slot: records 


_Slot for connecting the dataset to its records_





URI: [ada_ohwb:records](https://w3id.org/OHD/DFA-study/ada_ohwb/records)
Alias: records

<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ADAOHWBDataset](ADAOHWBDataset.md) | The ADA OHWB dataset |  yes  |
| [Dataset](Dataset.md) | The dataset for the study |  no  |







## Properties

* Range: [Record](Record.md)

* Multivalued: True





## Identifier and Mapping Information







### Schema Source


* from schema: https://w3id.org/OHD/DFA-study/ada_ohwb




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | ada_ohwb:records |
| native | ada_ohwb:records |




## LinkML Source

<details>
```yaml
name: records
description: Slot for connecting the dataset to its records
from_schema: https://w3id.org/OHD/DFA-study/ada_ohwb
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