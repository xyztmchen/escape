from models import Player  # 替換為實際的模組名稱
players = Player.query.all()
for p in players:
    print(p.id, p.name, p.game_id, p.ready_status)