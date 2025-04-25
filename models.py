import secrets
import string
from datetime import datetime
from app import db

def generate_room_code(length=6):
    """Generate a random alphanumeric room code of specified length"""
    # Use uppercase letters and digits (avoiding 0, O, 1, I for readability)
    alphabet = string.ascii_uppercase + string.digits
    alphabet = alphabet.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
    return ''.join(secrets.choice(alphabet) for _ in range(length))

class Game(db.Model):
    """Game session model"""
    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(10), unique=True, nullable=False, 
                          default=generate_room_code)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    current_chapter = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    is_complete = db.Column(db.Boolean, default=False)
    
    # Relationships
    players = db.relationship('Player', backref='game', lazy=True, 
                              cascade='all, delete-orphan')
    story_progress = db.relationship('StoryProgress', backref='game', lazy=True, 
                                    cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Game {self.room_code}>'
    
    def player_count(self):
        """Return the number of players in the game"""
        return len(self.players)
    
    def is_full(self):
        """Check if the game has two players already"""
        return self.player_count() >= 2
    
    def get_current_story_segment(self):
        """Get the current story segment based on the game progress"""
        chapter_number = self.current_chapter + 1
        return StoryModule.query.filter_by(chapter=chapter_number).first()
    
    def advance_chapter(self):
        """Move to the next chapter"""
        self.current_chapter += 1
        chapter_number = self.current_chapter + 1
        next_chapter = StoryModule.query.filter_by(chapter=self.current_chapter).first()
        if not next_chapter:
            self.is_complete = True
        db.session.commit()
        return next_chapter

class Player(db.Model):
    """Player model for each participant in a game"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), nullable=False)  # User's session ID
    nickname = db.Column(db.String(30), nullable=True)
    is_host = db.Column(db.Boolean, default=False)  # Whether this player created the game
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    role = db.Column(db.String(20), default='role1')  # 'role1' or 'role2'
    ready_status = db.Column(db.Boolean, default=False)  # If player is ready to continue
    
    def __repr__(self):
        return f'<Player {self.nickname or self.session_id}>'
    
    def mark_ready(self):
        """Mark player as ready to continue"""
        self.ready_status = True
        db.session.commit()
    
    def mark_not_ready(self):
        """Mark player as not ready"""
        self.ready_status = False
        db.session.commit()

class StoryModule(db.Model):
    """Model for story chapters and puzzle modules"""
    id = db.Column(db.Integer, primary_key=True)
    chapter = db.Column(db.Integer, nullable=False)  # Chapter number (sequential)
    title = db.Column(db.String(100), nullable=False)
    story_text = db.Column(db.Text, nullable=False)  # Story narrative text
    has_puzzle = db.Column(db.Boolean, default=True)
    puzzle_description = db.Column(db.Text, nullable=True)  # General puzzle description
    role1_hint = db.Column(db.Text, nullable=True)  # Hint specific to player role 1
    role2_hint = db.Column(db.Text, nullable=True)  # Hint specific to player role 2
    current_answerer = db.Column(db.String(100), nullable=True)
    solution = db.Column(db.String(100), nullable=True)  # The puzzle answer
    after_text = db.Column(db.Text, nullable=True)  # Text after puzzle is solved
    
    def __repr__(self):
        return f'<StoryModule Ch.{self.chapter}: {self.title}>'
    
    @property
    def has_role_specific_hints(self):
        """Check if this module has role-specific hints"""
        return bool(self.role1_hint and self.role2_hint)
    
    def get_hint_for_role(self, role):
        """Get the appropriate hint for a specific role"""
        if role == 'role1':
            return self.role1_hint
        elif role == 'role2':
            return self.role2_hint
        return self.puzzle_description  # Fallback to general description

class StoryProgress(db.Model):
    """Tracks progress through the story for each game"""
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    chapter = db.Column(db.Integer, nullable=False)
    is_story_complete = db.Column(db.Boolean, default=False)  # Story part completed
    is_puzzle_complete = db.Column(db.Boolean, default=False)  # Puzzle solved
    attempt_count = db.Column(db.Integer, default=0)  # Number of puzzle attempts
    last_attempt = db.Column(db.String(100), nullable=True)  # Last attempted solution
    completed_at = db.Column(db.DateTime, nullable=True)  # When this chapter was completed
    
    def __repr__(self):
        return f'<Progress Game:{self.game_id} Ch:{self.chapter}>'
    
    def record_attempt(self, attempt):
        """Record a puzzle solution attempt"""
        self.attempt_count += 1
        self.last_attempt = attempt
        db.session.commit()
    
    def mark_story_complete(self):
        """Mark the story part as complete"""
        self.is_story_complete = True
        db.session.commit()
    
    def mark_puzzle_complete(self):
        """Mark the puzzle as solved and chapter as complete"""
        self.is_puzzle_complete = True
        self.completed_at = datetime.utcnow()
        db.session.commit()
    
    def is_chapter_complete(self):
        """Check if both story and puzzle parts are complete"""
        return self.is_story_complete and self.is_puzzle_complete

class Message(db.Model):
    """Model for in-game messages between players"""
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('Player', backref='messages')
    
    def __repr__(self):
        return f'<Message from {self.sender_id} at {self.sent_at}>'