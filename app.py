import os
import logging
import json
import uuid
import secrets
import string
from datetime import datetime
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.utils import secure_filename

# Import excel processing (existing functionality)
from excel_processor import process_excel_file, analyze_excel_file

# Set up logging for easier debugging
logging.basicConfig(level=logging.DEBUG)

# Create necessary directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("static/outputs", exist_ok=True)
os.makedirs("static/story_modules", exist_ok=True)

class Base(DeclarativeBase):
    pass

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure the database
'''app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}'''
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mygame.db"

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Import models after db is defined
from models import Game, Player, StoryModule, StoryProgress, Message
import story_parser

# Set up session handling
@app.before_request
def setup_session():
    """Set up a session identifier for new users"""
    if 'user_session_id' not in session:
        session['user_session_id'] = str(uuid.uuid4())

# Create all tables
with app.app_context():
    db.create_all()
    
    StoryModule.query.delete()
    db.session.commit()
    
    # Load sample story modules if none exist
    story_parser.load_story_modules()
    app.logger.info(f"Loaded story modules from files")

@app.route('/')
def index():
    """Render the main game page"""
    return render_template('game_index.html')

@app.route('/excel_tool')
def excel_tool():
    """Render the Excel tool page (original functionality)"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle the Excel file upload and processing"""
    if 'file' not in request.files:
        flash('沒有選擇檔案', 'error')
        return redirect(request.url)
        
    file = request.files['file']
    if file.filename == '':
        flash('沒有選擇檔案', 'error')
        return redirect(request.url)
        
    if not file.filename.endswith(('.xlsx', '.xls')):
        flash('只支援 Excel 檔案格式 (.xlsx, .xls)', 'error')
        return redirect(request.url)
    
    # 保存上傳的檔案
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"upload_{timestamp}_{file.filename}"
    file_path = os.path.join("uploads", filename)
    file.save(file_path)
    
    # 先分析Excel檔案，獲取階層設定
    detected_levels, error = analyze_excel_file(file_path)
    
    if error:
        flash(f'分析失敗: {error}', 'error')
        return redirect(request.url)
        
    # 儲存檔案路徑和偵測到的階層到session，以便後續處理
    session['upload_file_path'] = file_path
    session['detected_levels'] = json.dumps(detected_levels)
    
    # 顯示階層設定頁面讓使用者確認或修改
    return render_template('levels.html', 
                          detected_levels=json.dumps(detected_levels, ensure_ascii=False),
                          file_name=os.path.basename(file_path))
                          
@app.route('/process', methods=['POST'])
def process_file():
    """處理上傳的Excel檔案，使用使用者確認的階層設定"""
    file_path = session.get('upload_file_path')
    if not file_path or not os.path.exists(file_path):
        flash('請先上傳檔案', 'error')
        return redirect(url_for('index'))
    
    # 獲取使用者確認或修改後的階層設定
    custom_levels = request.form.get('custom_levels', '').strip()
    if custom_levels:
        try:
            custom_levels = json.loads(custom_levels)
        except json.JSONDecodeError:
            flash('階層設定格式不正確，請使用有效的 JSON 陣列格式', 'error')
            return redirect(url_for('index'))
    else:
        # 使用偵測到的階層
        custom_levels = json.loads(session.get('detected_levels', '[]'))
    
    # 處理 Excel 檔案
    output_filename, error = process_excel_file(file_path, custom_levels)
    
    if error:
        flash(f'處理失敗: {error}', 'error')
        return redirect(url_for('index'))
    
    # 儲存處理結果到 session
    session['output_filename'] = output_filename
    
    flash('檔案處理成功！', 'success')
    return render_template('index.html', processed=True, output_filename=output_filename)

@app.route('/download/<filename>')
def download_file(filename):
    """Provide the processed file for download"""
    return send_from_directory('static/outputs', filename, as_attachment=True)

# ===== 雙人劇情解謎遊戲路由 =====

@app.route('/create_game', methods=['POST'])
def create_game():
    """建立新遊戲並產生6碼隨機房號"""
    # 獲取使用者暱稱（可選）
    nickname = request.form.get('nickname', '')
    
    # 創建新遊戲
    new_game = Game()
    db.session.add(new_game)
    db.session.commit()
    
    # 創建主機玩家
    host_player = Player(
        session_id=session['user_session_id'],
        nickname=nickname if nickname else None,
        is_host=True,
        game_id=new_game.id,
        role='role1'  # 主機預設為角色1
    )
    db.session.add(host_player)
    db.session.commit()
    
    # 將遊戲ID存入session
    session['current_game_id'] = new_game.id
    session['player_id'] = host_player.id
    
    # 重導向到等待頁面
    return redirect(url_for('game_lobby', room_code=new_game.room_code))

@app.route('/join_game', methods=['POST'])
def join_game():
    """加入現有遊戲"""
    room_code = request.form.get('room_code', '').strip().upper()
    nickname = request.form.get('nickname', '')
    
    if not room_code:
        flash('請輸入房間代碼', 'error')
        return redirect(url_for('index'))
    
    # 查找遊戲
    game = Game.query.filter_by(room_code=room_code, is_active=True).first()
    if not game:
        flash('找不到指定的遊戲房間', 'error')
        return redirect(url_for('index'))
    
    # 檢查遊戲是否已滿
    if game.is_full():
        flash('此遊戲房間已滿', 'error')
        return redirect(url_for('index'))
    
    # 創建加入的玩家
    join_player = Player(
        session_id=session['user_session_id'],
        nickname=nickname if nickname else None,
        is_host=False,
        game_id=game.id,
        role='role2'  # 加入者預設為角色2
    )
    db.session.add(join_player)
    db.session.commit()
    
    # 將遊戲ID存入session
    session['current_game_id'] = game.id
    session['player_id'] = join_player.id
    
    # 重導向到遊戲頁面
    return redirect(url_for('game_lobby', room_code=game.room_code))

@app.route('/game/lobby/<room_code>')
def game_lobby(room_code):
    """遊戲大廳/等待頁面"""
    # 找到遊戲
    game = Game.query.filter_by(room_code=room_code).first_or_404()
    
    # 檢查玩家是否屬於此遊戲
    player = Player.query.filter_by(
        session_id=session.get('user_session_id'),
        game_id=game.id
    ).first()
    
    if not player:
        flash('你不是此遊戲的玩家', 'error')
        return redirect(url_for('index'))
    
    # 如果遊戲已有兩位玩家，重導向到遊戲開始頁面
    if game.player_count() >= 2:
        return redirect(url_for('game_start', room_code=room_code))
    
    # 傳遞資料到大廳模板
    return render_template('game_lobby.html', 
                          game=game, 
                          player=player,
                          is_host=player.is_host)

@app.route('/game/start/<room_code>')
def game_start(room_code):
    """開始遊戲"""
    # 找到遊戲
    game = Game.query.filter_by(room_code=room_code).first_or_404()
    
    # 檢查玩家是否屬於此遊戲
    player = Player.query.filter_by(
        session_id=session.get('user_session_id'),
        game_id=game.id
    ).first()
    
    if not player:
        flash('你不是此遊戲的玩家', 'error')
        return redirect(url_for('index'))
    
    # 獲取目前章節
    current_module = game.get_current_story_segment()
    if not current_module:
        flash('無法載入遊戲內容', 'error')
        return redirect(url_for('index'))
    
    # 檢查是否已存在進度記錄，如果沒有則創建
    chapter_number = game.current_chapter + 1
    progress = StoryProgress.query.filter_by(
        game_id=game.id,
        chapter=game.current_chapter
    ).first()
    
    if not progress:
        progress = StoryProgress(
            game_id=game.id,
            chapter=game.current_chapter
        )
        db.session.add(progress)
        db.session.commit()
    
    # 決定顯示的提示基於玩家角色
    hint = current_module.get_hint_for_role(player.role)
    
    # 傳遞資料到遊戲頁面
    return render_template('game.html', 
                          game=game, 
                          player=player,
                          module=current_module,
                          progress=progress,
                          hint=hint)

@app.route('/api/mark_ready', methods=['POST'])
def mark_ready():
    """標記玩家已準備好進入下一階段"""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({"error": "未登入遊戲"}), 403
    
    player = Player.query.get_or_404(player_id)
    player.mark_ready()
    
    # 檢查所有玩家是否都準備好
    game = Game.query.get_or_404(player.game_id)
    all_players = Player.query.filter_by(game_id=game.id).all()
    all_ready = all(p.ready_status for p in all_players)
    
    return jsonify({
        "status": "success", 
        "all_ready": all_ready,
        "ready_count": sum(1 for p in all_players if p.ready_status),
        "total_players": len(all_players)
    })

@app.route('/api/check_all_ready', methods=['GET'])
def check_all_ready():
    """檢查所有玩家是否都已準備好"""
    game_id = session.get('current_game_id')
    if not game_id:
        return jsonify({"error": "未加入遊戲"}), 403
    
    # 獲取所有玩家
    players = Player.query.filter_by(game_id=game_id).all()
    all_ready = all(player.ready_status for player in players)
    
    return jsonify({
        "all_ready": all_ready,
        "ready_count": sum(1 for p in players if p.ready_status),
        "total_players": len(players)
    })

@app.route('/api/submit_answer', methods=['POST'])
def submit_answer():
    """提交謎題答案"""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({"error": "未登入遊戲"}), 403
    
    player = Player.query.get_or_404(player_id)
    game = Game.query.get_or_404(player.game_id)
    
    # 獲取答案
    answer = request.form.get('answer', '').strip()
    if not answer:
        return jsonify({"error": "未提供答案"}), 400
    
    # 獲取當前章節和進度
    current_module = game.get_current_story_segment()
    chapter_number = game.current_chapter + 1
    progress = StoryProgress.query.filter_by(
        game_id=game.id,
        chapter=game.current_chapter
    ).first()
    
    if not progress:
        return jsonify({"error": "找不到遊戲進度"}), 404
    
    # 記錄答案嘗試
    progress.record_attempt(answer)
    
    # 檢查答案是否正確
    if answer.lower() == current_module.solution.lower():
        # 標記謎題為已解開
        progress.mark_puzzle_complete()
        
        # 如果故事部分已完成，則進入下一章
        if progress.is_story_complete:
            next_module = game.advance_chapter()
            return jsonify({
                "status": "success",
                "correct": True,
                "message": "答案正確！",
                "next_chapter": next_module is not None,
                "game_complete": game.is_complete
            })
        else:
            return jsonify({
                "status": "success",
                "correct": True,
                "message": "答案正確！請繼續閱讀故事。",
                "next_chapter": False
            })
    else:
        return jsonify({
            "status": "success",
            "correct": False,
            "message": "答案不正確，請再試一次。",
            "attempt_count": progress.attempt_count
        })

@app.route('/api/mark_story_complete', methods=['POST'])
def mark_story_complete():
    """標記故事部分為已閱讀完畢"""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({"error": "未登入遊戲"}), 403
    
    player = Player.query.get_or_404(player_id)
    game = Game.query.get_or_404(player.game_id)
    
    # 獲取當前進度
    progress = StoryProgress.query.filter_by(
        game_id=game.id,
        chapter=game.current_chapter
    ).first()
    
    if not progress:
        return jsonify({"error": "找不到遊戲進度"}), 404
    
    # 標記故事為已完成
    progress.mark_story_complete()
    
    # 如果謎題也已解決，則進入下一章
    if progress.is_puzzle_complete:
        next_module = game.advance_chapter()
        return jsonify({
            "status": "success",
            "next_chapter": next_module is not None,
            "game_complete": game.is_complete
        })
    else:
        return jsonify({
            "status": "success",
            "message": "故事閱讀完成，請解開謎題以繼續。"
        })

@app.route('/api/send_message', methods=['POST'])
def send_message():
    """發送消息給其他玩家"""
    player_id = session.get('player_id')
    if not player_id:
        return jsonify({"error": "未登入遊戲"}), 403
    
    player = Player.query.get_or_404(player_id)
    content = request.form.get('content', '').strip()
    
    if not content:
        return jsonify({"error": "訊息不能為空"}), 400
    
    # 創建新消息
    message = Message(
        game_id=player.game_id,
        sender_id=player.id,
        content=content
    )
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "message_id": message.id,
        "sender": player.nickname or f"玩家{player.id}",
        "content": content,
        "timestamp": message.sent_at.strftime("%H:%M:%S")
    })

@app.route('/api/get_messages', methods=['GET'])
def get_messages():
    """獲取遊戲消息"""
    game_id = session.get('current_game_id')
    if not game_id:
        return jsonify({"error": "未加入遊戲"}), 403
    
    # 獲取消息時間戳
    last_msg_time = request.args.get('since')
    if last_msg_time:
        last_time = datetime.fromisoformat(last_msg_time)
        messages = Message.query.filter(
            Message.game_id == game_id,
            Message.sent_at > last_time
        ).order_by(Message.sent_at).all()
    else:
        # 限制獲取最近的10條消息
        messages = Message.query.filter_by(
            game_id=game_id
        ).order_by(Message.sent_at.desc()).limit(10).all()
        messages.reverse()
    
    # 格式化消息
    result = []
    for msg in messages:
        sender = Player.query.get(msg.sender_id)
        result.append({
            "id": msg.id,
            "sender": sender.nickname or f"玩家{sender.id}",
            "sender_id": sender.id,
            "content": msg.content,
            "timestamp": msg.sent_at.isoformat(),
            "formatted_time": msg.sent_at.strftime("%H:%M:%S")
        })
    
    return jsonify({"messages": result})

@app.route('/api/check_player_status', methods=['GET'])
def check_player_status():
    """檢查遊戲玩家狀態"""
    game_id = session.get('current_game_id')
    if not game_id:
        return jsonify({"error": "未加入遊戲"}), 403
    
    game = Game.query.get_or_404(game_id)
    players = Player.query.filter_by(game_id=game_id).all()
    
    player_data = []
    for p in players:
        player_data.append({
            "id": p.id,
            "nickname": p.nickname or f"玩家{p.id}",
            "is_host": p.is_host,
            "role": p.role,
            "ready": p.ready_status
        })
    
    return jsonify({
        "room_code": game.room_code,
        "player_count": len(players),
        "game_full": game.is_full(),
        "players": player_data
    })
    
@app.route('/api/check_answer_status', methods=['GET'])
def check_answer_status():
    """檢查遊戲玩家狀態"""
    player_id = session.get('player_id')
    current_chapter = session.get('current_chapter')
    
    print(current_chapter)
    
    if not player_id:
        return jsonify({"error": "未加入遊戲"}), 403
        
    player = Player.query.get_or_404(player_id)
    game = Game.query.get_or_404(player.game_id)
    
    # 確保 current_chapter 是數字格式
    if current_chapter is None:
        current_chapter = 0
    
    current_chapter = int(current_chapter)
    
    # 判斷回答是否正確
    if game.current_chapter > current_chapter:
        is_answer_ok = True
    else:
        is_answer_ok = False
        
    # 更新玩家的章節狀態
    session['current_chapter'] = game.current_chapter
       
    return jsonify({
        "is_answer_ok": is_answer_ok
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)