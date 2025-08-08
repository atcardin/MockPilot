import yaml
import json
import sys

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_json_file> <output_yaml_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            json_data = json.load(file)

        yaml_data = yaml.dump(json_data, sort_keys=False, allow_unicode=True)

        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(yaml_data)

        print(f"Converted {input_file} → {output_file} successfully.")

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in '{input_file}' — {e}")
