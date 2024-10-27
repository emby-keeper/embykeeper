import json
import re

def parse_terminus_questions(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split the content into individual message blocks
    messages = re.split(r'\n\{', content)

    questions = []
    current_question = None

    for message in messages:
        message_data = json.loads('{' + message.strip() if not message.startswith('{') else message)
        
        if 'text' in message_data and '进度:' in message_data['text']:
            # This is a question message
            question_text = message_data['text'].split('\n\n')[0]
            current_question = {
                'question': question_text,
                'choices': []
            }
            questions.append(current_question)
        if current_question and 'reply_markup' in message_data:
            # This message contains the choices
            for row in message_data['reply_markup']['inline_keyboard']:
                for button in row:
                    current_question['choices'].append(button['text'])

    return questions

def main():
    file_path = 'terminus.updates.json'
    questions = parse_terminus_questions(file_path)
    
    # Output the result as JSON
    print(json.dumps(questions, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
