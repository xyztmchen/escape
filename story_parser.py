import os
import re
from app import db
from models import StoryModule

def parse_story_file(file_path):
    """
    Parse a story file in the specified format and return structured data
    
    Format expected:
    [STORY]
    Story text...
    [PUZZLE]
    role1: Role 1 specific hint
    role2: Role 2 specific hint
    answer: The correct answer
    [STORY_AFTER]
    Text after puzzle is solved...
    
    Args:
        file_path (str): Path to the story file
        
    Returns:
        dict: Structured story data or None if parsing failed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Initialize story data structure
        story_data = {
            'story_text': '',
            'puzzle_description': '',
            'role1_hint': '',
            'role2_hint': '',
            'solution': '',
            'after_text': ''
        }
        
        # Extract story section
        story_match = re.search(r'\[STORY\](.*?)(?=\[PUZZLE\]|\[STORY_AFTER\]|$)', content, re.DOTALL)
        if story_match:
            story_data['story_text'] = story_match.group(1).strip()
        
        # Extract puzzle section
        puzzle_match = re.search(r'\[PUZZLE\](.*?)(?=\[STORY_AFTER\]|$)', content, re.DOTALL)
        if puzzle_match:
            puzzle_text = puzzle_match.group(1).strip()
            
            # Extract role-specific hints and answer
            role1_match = re.search(r'role1:\s*(.*?)(?=role2:|answerer:|answer:|$)', puzzle_text, re.DOTALL)
            if role1_match:
                story_data['role1_hint'] = role1_match.group(1).strip()
            
            role2_match = re.search(r'role2:\s*(.*?)(?=answerer:|answer:|$)', puzzle_text, re.DOTALL)
            if role2_match:
                story_data['role2_hint'] = role2_match.group(1).strip()
            
            answerer_match = re.search(r'answerer:\s*(.*?)(?=answer:|$)', puzzle_text, re.DOTALL)
            if answerer_match:
                story_data['current_answerer'] = answerer_match.group(1).strip()
            print("test "+story_data['current_answerer'])    
            
            answer_match = re.search(r'answer:\s*(.*?)(?=$)', puzzle_text, re.DOTALL)
            if answer_match:
                story_data['solution'] = answer_match.group(1).strip()                
            
            # If no role-specific hints were found, use the whole puzzle text as description
            if not story_data['role1_hint'] and not story_data['role2_hint']:
                story_data['puzzle_description'] = puzzle_text
        
        # Extract story after section
        after_match = re.search(r'\[STORY_AFTER\](.*?)$', content, re.DOTALL)
        if after_match:
            story_data['after_text'] = after_match.group(1).strip()
        
        return story_data
    
    except Exception as e:
        print(f"Error parsing story file {file_path}: {e}")
        return None

def load_story_modules():
    """
    Load all story modules from the story_modules directory into the database
    
    Returns:
        int: Number of modules loaded
    """
    story_dir = os.path.join('static', 'story_modules')
    count = 0
    
    # Get all .txt files
    story_files = sorted([f for f in os.listdir(story_dir) if f.endswith('.txt')])
    
    # Clear existing modules
    db.session.query(StoryModule).delete()
    db.session.commit()
    
    for chapter, filename in enumerate(story_files, 1):
        file_path = os.path.join(story_dir, filename)
        story_data = parse_story_file(file_path)
        
        if story_data:
            # Create title from filename (remove extension and replace underscores)
            title = os.path.splitext(filename)[0].replace('_', ' ').capitalize()
            
            # Create story module
            module = StoryModule(
                chapter=chapter,
                title=title,
                story_text=story_data['story_text'],
                has_puzzle=bool(story_data['puzzle_description'] or 
                                story_data['role1_hint'] or 
                                story_data['role2_hint']),
                puzzle_description=story_data['puzzle_description'],
                role1_hint=story_data['role1_hint'],
                role2_hint=story_data['role2_hint'],
                current_answerer=story_data['current_answerer'],
                solution=story_data['solution'],
                after_text=story_data['after_text']
            )
            
            db.session.add(module)
            count += 1
    
    db.session.commit()
    return count

def save_story_module(chapter_data, filename):
    """
    Save story module data to a file in the proper format
    
    Args:
        chapter_data (dict): The story chapter data
        filename (str): The filename to save to (without path)
        
    Returns:
        str: Path to the saved file or None if failed
    """
    story_dir = os.path.join('static', 'story_modules')
    file_path = os.path.join(story_dir, filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("[STORY]\n")
            f.write(chapter_data.get('story_text', '') + "\n\n")
            
            f.write("[PUZZLE]\n")
            if chapter_data.get('role1_hint'):
                f.write(f"role1: {chapter_data['role1_hint']}\n")
            if chapter_data.get('role2_hint'):
                f.write(f"role2: {chapter_data['role2_hint']}\n")
            if chapter_data.get('solution'):
                f.write(f"answer: {chapter_data['solution']}\n\n")
            
            f.write("[STORY_AFTER]\n")
            f.write(chapter_data.get('after_text', ''))
        
        return file_path
    
    except Exception as e:
        print(f"Error saving story module to {file_path}: {e}")
        return None

def create_sample_story_module():
    """
    Create a sample story module file to demonstrate the format
    
    Returns:
        str: Path to the created file or None if failed
    """
    sample_data = {
        'story_text': '在黑夜中，你們來到了一棟破舊的洋樓。寒風呼嘯，大門在風中吱呀作響。\n'
                      '「就是這裡了，」你對同伴說，「傳說中藏有寶藏的鬼屋。」',
        'role1_hint': '你看到一張殘破的地圖，上面標示著「地下室」的入口在東側走廊。',
        'role2_hint': '你注意到牆上刻著奇怪的符號，底下寫著：「4×2=？才能通過」',
        'solution': '8',
        'after_text': '當你們輸入「8」後，密碼門發出喀噠一聲打開了。\n'
                      '你們小心翼翼地走進地下室，聽見地板下方傳來嘎吱聲...'
    }
    
    return save_story_module(sample_data, 'chapter_1_sample.txt')