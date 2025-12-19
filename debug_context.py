import json

with open('data/ProofWriter.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    for i, item in enumerate(data):
        if item.get('id') == 'ProofWriter_AttNeg-OWA-D5-1015_Q3':
            print(f'Found item at index {i}')
            print(f'Has context: {"context" in item}')
            print(f'Keys: {list(item.keys())}')
            if 'context' in item:
                print(f'Context length: {len(item["context"])}')
                print(f'Context preview: {item["context"][:100]}...')
            break
    else:
        print('Item not found')
