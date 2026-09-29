"""Estado da partida: linha de lances, navegação, PGN e edição de posição."""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import chess
import chess.pgn

CASTLING_REQUIREMENTS = {
    "K": (chess.E1, chess.H1, chess.WHITE),
    "Q": (chess.E1, chess.A1, chess.WHITE),
    "k": (chess.E8, chess.H8, chess.BLACK),
    "q": (chess.E8, chess.A8, chess.BLACK),
}


@dataclass
class GameLine:
    """Uma linha principal de lances a partir de uma posição raiz."""

    root_fen: str = chess.STARTING_FEN
    moves: list[str] = field(default_factory=list)  # lances em UCI
    ply: int = 0
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.ply = max(0, min(self.ply, len(self.moves)))

    def board_at(self, ply: int) -> chess.Board:
        board = chess.Board(self.root_fen)
        for uci in self.moves[: max(0, min(ply, len(self.moves)))]:
            board.push(chess.Move.from_uci(uci))
        return board

    @property
    def board(self) -> chess.Board:
        return self.board_at(self.ply)

    @property
    def length(self) -> int:
        return len(self.moves)

    def san_moves(self) -> list[str]:
        """Lances em notação algébrica, na ordem em que foram jogados."""
        board = chess.Board(self.root_fen)
        sans = []
        for uci in self.moves:
            move = chess.Move.from_uci(uci)
            sans.append(board.san(move))
            board.push(move)
        return sans

    def move_labels(self) -> list[str]:
        """Rótulos ``1.e4`` / ``1...e5`` para exibir a lista de lances."""
        root = chess.Board(self.root_fen)
        number = root.fullmove_number
        white_to_move = root.turn == chess.WHITE
        labels = []
        for san in self.san_moves():
            labels.append(f"{number}.{san}" if white_to_move else f"{number}...{san}")
            if not white_to_move:
                number += 1
            white_to_move = not white_to_move
        return labels

    def legal_move(self, from_square: chess.Square, to_square: chess.Square,
                   promotion: chess.PieceType | None = None) -> chess.Move | None:
        """Devolve o lance legal correspondente ao par de casas, se existir."""
        board = self.board
        candidates = [
            move
            for move in board.legal_moves
            if move.from_square == from_square and move.to_square == to_square
        ]
        if not candidates:
            return None
        if promotion is not None:
            for move in candidates:
                if move.promotion == promotion:
                    return move
        return candidates[0]

    def push(self, move: chess.Move) -> None:
        """Joga um lance, descartando a continuação anterior a partir do ply atual."""
        self.moves = self.moves[: self.ply]
        self.moves.append(move.uci())
        self.ply = len(self.moves)

    def goto(self, ply: int) -> None:
        self.ply = max(0, min(ply, len(self.moves)))

    def step(self, delta: int) -> None:
        self.goto(self.ply + delta)

    def undo(self) -> None:
        """Remove o último lance da linha."""
        if not self.moves:
            return
        self.moves.pop()
        self.ply = min(self.ply, len(self.moves))

    def truncate_here(self) -> None:
        """Descarta os lances após a posição atual."""
        self.moves = self.moves[: self.ply]

    def to_pgn(self) -> str:
        game = chess.pgn.Game()
        for key, value in self.headers.items():
            game.headers[key] = value
        root = chess.Board(self.root_fen)
        if root.fen() != chess.STARTING_FEN:
            game.headers["SetUp"] = "1"
            game.headers["FEN"] = root.fen()
        node = game
        for uci in self.moves:
            node = node.add_variation(chess.Move.from_uci(uci))
        return str(game)


def line_from_fen(fen: str) -> GameLine:
    """Cria uma linha vazia a partir de um FEN (levanta ``ValueError`` se inválido)."""
    board = chess.Board(fen.strip())
    return GameLine(root_fen=board.fen())


def line_from_pgn(pgn_text: str) -> GameLine:
    """Lê o primeiro jogo de um PGN e devolve a linha principal."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("Nenhum jogo encontrado no PGN.")

    board = game.board()
    moves = [move.uci() for move in game.mainline_moves()]
    if not moves and not game.headers.get("FEN"):
        raise ValueError("O PGN não contém lances nem uma posição inicial (FEN).")

    headers = {
        key: value
        for key, value in game.headers.items()
        if key in ("Event", "Site", "Date", "Round", "White", "Black", "Result")
    }
    return GameLine(root_fen=board.fen(), moves=moves, ply=len(moves), headers=headers)


def sanitize_castling(board: chess.Board) -> None:
    """Remove direitos de roque impossíveis depois de editar a posição."""
    kept = ""
    for flag, (king_sq, rook_sq, color) in CASTLING_REQUIREMENTS.items():
        king = board.piece_at(king_sq)
        rook = board.piece_at(rook_sq)
        valid = (
            king is not None
            and king.piece_type == chess.KING
            and king.color == color
            and rook is not None
            and rook.piece_type == chess.ROOK
            and rook.color == color
        )
        if valid and flag in board.castling_xfen():
            kept += flag
    board.set_castling_fen(kept or "-")


def edit_square(fen: str, square: chess.Square, piece: chess.Piece | None) -> str:
    """Coloca ou remove uma peça e devolve o novo FEN, saneado."""
    board = chess.Board(fen)
    board.ep_square = None
    if piece is None:
        board.remove_piece_at(square)
    else:
        if piece.piece_type == chess.KING:
            # Só pode haver um rei de cada cor.
            for existing in list(board.pieces(chess.KING, piece.color)):
                board.remove_piece_at(existing)
        board.set_piece_at(square, piece)
    sanitize_castling(board)
    return board.fen()


def position_problems(fen: str) -> list[str]:
    """Descreve por que uma posição editada ainda não é jogável."""
    board = chess.Board(fen)
    problems = []
    if board.king(chess.WHITE) is None:
        problems.append("Faltam as brancas terem um rei.")
    if board.king(chess.BLACK) is None:
        problems.append("Faltam as pretas terem um rei.")
    for color, label in ((chess.WHITE, "brancas"), (chess.BLACK, "pretas")):
        if any(
            chess.square_rank(sq) in (0, 7) for sq in board.pieces(chess.PAWN, color)
        ):
            problems.append(f"Há peões das {label} na primeira ou na oitava fileira.")
    if board.king(not board.turn) is not None and board.was_into_check():
        problems.append("O lado que não tem o lance está em xeque.")
    return problems


def set_turn(fen: str, turn: chess.Color) -> str:
    board = chess.Board(fen)
    board.turn = turn
    board.ep_square = None
    return board.fen()


def clear_board(turn: chess.Color = chess.WHITE) -> str:
    board = chess.Board(None)
    board.turn = turn
    board.set_castling_fen("-")
    return board.fen()


def handle_setup_click(line: GameLine, square: chess.Square, symbol: str) -> GameLine:
    """Coloca, troca ou apaga a peça da casa clicada e devolve a nova linha."""
    piece = None if symbol == "erase" else chess.Piece.from_symbol(symbol)
    # Clicar de novo sobre a mesma peça remove-a.
    if piece is not None and line.board.piece_at(square) == piece:
        piece = None
    return GameLine(root_fen=edit_square(line.root_fen, square, piece))


def handle_play_click(
    line: GameLine,
    selected: chess.Square | None,
    square: chess.Square,
    promotion: chess.PieceType = chess.QUEEN,
) -> chess.Square | None:
    """Aplica o clique em modo de jogo (muta ``line``) e devolve a nova seleção."""
    board = line.board

    if selected is None:
        piece = board.piece_at(square)
        return square if piece is not None and piece.color == board.turn else None

    if square == selected:
        return None

    move = line.legal_move(selected, square, promotion=promotion)
    if move is not None:
        line.push(move)
        return None

    # Clique em outra peça própria troca a seleção; nos demais casos, cancela.
    piece = board.piece_at(square)
    return square if piece is not None and piece.color == board.turn else None
