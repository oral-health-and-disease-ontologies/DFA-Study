import json
from typing import List
from git_root import git_root

def main():
    input = git_root('jsonld/trait-value.jsonld')
    output = git_root('field-mappings/field-mappings.csv')

    with open(input) as f:
        schema_dict  = json.load(f)

    with open(output, 'w') as f:
        f.write('field,mappings\n') # write header
        
        slots:List = schema_dict['slots']
        for slot in slots:
            # for each slot get name and mappings
            name = slot.get('name', '')
            mappings = \
                '|'.join(slot.get('related_mappings', []))
            
            if len(name) > 0:
                f.write(f'{name},{mappings}\n')
            # print(f"name: {name}, mappings: {mappings}")
            

if __name__ == "__main__":
    main()