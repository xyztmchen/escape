import json
import logging

def process_wbs_data(wbs_json_data):
    """
    Process WBS JSON data and return the WBS structure with generated codes
    
    Args:
        wbs_json_data (str): JSON string containing WBS data
        
    Returns:
        tuple: (wbs_result, wbs_dict) where wbs_result is a list of WBS items
               and wbs_dict is a dictionary for quick lookup
    """
    try:
        # Parse JSON data
        task_data = json.loads(wbs_json_data)
        
        # Generate WBS codes and build the index
        wbs_result, wbs_dict = generate_wbs(task_data)
        
        return wbs_result, wbs_dict
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
        return [], {}
    except Exception as e:
        logging.error(f"Error processing WBS data: {e}")
        return [], {}

def get_hierarchy_options(tasks):
    """
    Build a dictionary of hierarchical options for cascading dropdowns
    
    Args:
        tasks (list): List of task dictionaries from the parsed JSON
        
    Returns:
        dict: A nested dictionary of task options by hierarchy level
    """
    options = {}
    
    # Process level 1 and their children
    for task in tasks:
        level1_name = task["name"]
        options[level1_name] = {}
        
        # Process level 2 and their children
        if "subtasks" in task:
            for subtask in task["subtasks"]:
                level2_name = subtask["name"]
                options[level1_name][level2_name] = []
                
                # Process level 3
                if "subtasks" in subtask:
                    for subsubtask in subtask["subtasks"]:
                        level3_name = subsubtask["name"]
                        options[level1_name][level2_name].append(level3_name)
    
    return options

def generate_wbs(tasks, prefix="", parent_path=""):
    """
    Recursively generate WBS codes and build an index
    
    Args:
        tasks (list): List of task dictionaries
        prefix (str): Prefix for the WBS code
        parent_path (str): Path of parent tasks
        
    Returns:
        tuple: (result, wbs_index) where result is a list of WBS items
               and wbs_index is a dictionary for quick lookup
    """
    result = []
    wbs_index = {}  # For quickly looking up items
    
    for index, task in enumerate(tasks, 1):
        # Format code properly: 01, 01.01, 01.01.01, etc.
        if prefix:
            code = f"{prefix}{index:02d}"
        else:
            code = f"{index:02d}"  # Top level items like 01, 02, etc.
            
        full_path = f"{parent_path} {task['name']}".strip()
        wbs_item = {
            "code": code,
            "name": task["name"],
            "cost": task["cost"],
            "days": task["days"],
            "full_path": full_path
        }
        result.append(wbs_item)
        wbs_index[full_path] = wbs_item  # Store in index
        
        # Process subtasks if they exist
        if "subtasks" in task:
            sub_result, sub_index = generate_wbs(task["subtasks"], code + ".", full_path)
            result.extend(sub_result)
            wbs_index.update(sub_index)

    return result, wbs_index

def search_wbs(wbs_index, query):
    """
    Search for a WBS item by query string and return all parent items
    
    Args:
        wbs_index (dict): Dictionary of WBS items indexed by their full path
        query (str): The query string to search for
        
    Returns:
        list: List of dictionaries containing search results
    """
    if not query or query not in wbs_index:
        return [{"error": "找不到該工項，請確認父階層是否已輸入"}]
    
    result = []
    query_parts = query.split()
    
    # Find all parent levels recursively
    for i in range(1, len(query_parts) + 1):
        sub_query = " ".join(query_parts[:i])
        if sub_query in wbs_index:
            task = wbs_index[sub_query]
            result.append({
                "code": task['code'],
                "name": task['name'],
                "cost": task['cost'],
                "days": task['days'],
                "full_path": task['full_path']
            })
    
    return result
