# Enum: EmploymentStatus 




_Enumeration for employment status_



URI: [EmploymentStatus](EmploymentStatus.md)

## Permissible Values

| Value | Meaning | Description |
| --- | --- | --- |
| 1 | http://purl.obolibrary.org/obo/NCIT_C148254 | Employed full time |
| 2 | http://purl.obolibrary.org/obo/NCIT_C148255 | Employed part-time |
| 3 | None | Self-employed |
| 4 | None | Not employed, but looking for work |
| 5 | None | Not employed and not looking for work |
| 6 | None | Retired |
| 7 | http://purl.obolibrary.org/obo/NCIT_C198129 | Not employed, unable to work due to a disability or illness |
| 8 | None | Student |
| 9 | None | Stay-at-home spouse or partner |




## Slots

| Name | Description |
| ---  | --- |
| [Q410](Q410.md) | Which one of the following best describes your employment status? |






## Identifier and Mapping Information







### Schema Source


* from schema: https://w3id.org/OHD/DFA-study/ada_ohwb






## LinkML Source

<details>
```yaml
name: EmploymentStatus
description: Enumeration for employment status
from_schema: https://w3id.org/OHD/DFA-study/ada_ohwb
rank: 1000
permissible_values:
  '1':
    text: '1'
    description: Employed full time
    meaning: http://purl.obolibrary.org/obo/NCIT_C148254
  '2':
    text: '2'
    description: Employed part-time
    meaning: http://purl.obolibrary.org/obo/NCIT_C148255
  '3':
    text: '3'
    description: Self-employed
  '4':
    text: '4'
    description: Not employed, but looking for work
  '5':
    text: '5'
    description: Not employed and not looking for work
  '6':
    text: '6'
    description: Retired
  '7':
    text: '7'
    description: Not employed, unable to work due to a disability or illness
    meaning: http://purl.obolibrary.org/obo/NCIT_C198129
  '8':
    text: '8'
    description: Student
  '9':
    text: '9'
    description: Stay-at-home spouse or partner

```
</details>
