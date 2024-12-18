import re

def create_colored_handout(input_path, output_path):
    try:
        # Read the markdown file
        with open(input_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Replace **text** with <span style="color: gold">**text**</span>
        # Pattern matches **text** and captures the text part
        pattern = r'\*\*(.*?)\*\*'
        colored_content = re.sub(pattern, r'<span style="color: gold">**\1**</span>', content)
        
        # Write the modified content to the output file
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(colored_content)
            
        print(f"Created colored handout at {output_path}")
            
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    input_path = "Reference_answer.md"
    output_path = "Exquisite_handout.md"
    create_colored_handout(input_path, output_path)