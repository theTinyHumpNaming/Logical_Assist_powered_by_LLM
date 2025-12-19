import json
import os

data_dir = 'data'
for file in os.listdir(data_dir):
    if file.endswith('.json'):
        print(f'Checking {file}...')
        try:
            with open(os.path.join(data_dir, file), 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    first_item = data[0]
                    has_context = 'context' in first_item
                    print(f'  Has context key: {has_context}')
                    if not has_context:
                        print(f'  Keys: {list(first_item.keys())}')
                    else:
                        print(f'  Context type: {type(first_item["context"])}')
                        print(f'  Context preview: {first_item["context"][:50]}...' if first_item["context"] else '  Context is empty')
                elif isinstance(data, list):
                    print(f'  Empty list')
                else:
                    print(f'  Not a list, type: {type(data)}')
        except Exception as e:
            print(f'  Error loading file: {e}')
